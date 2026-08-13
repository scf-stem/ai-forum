"""双路检索服务。

Phase 1 检索能力：论坛路（PostgreSQL 全文检索）+ 联网路（可插拔 Web Search API），
双路并行调度后输出统一来源列表与检索路径，供 AI 答案生成消费。

- 论坛路：利用已建好的 ix_posts_content_fts GIN 索引检索 posts，并扫描 replies；
- 联网路：通过 httpx 调用外部 Web Search API，未配置 URL 则跳过；
- retrieve：asyncio.gather 并行双路，并据命中情况判定 retrieval_path；
- assess_confidence：基于来源数量与权威性给出置信度。
"""
import asyncio
import logging

import httpx
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# 权威来源类型：用于置信度评估（论坛帖、官方文档）
AUTHORITATIVE_TYPES = ("forum", "docs")

# 各路检索超时阈值（秒）
FORUM_SEARCH_TIMEOUT = 3
WEB_SEARCH_TIMEOUT = 5


def _make_snippet(content: str, length: int = 200) -> str:
    """截取内容前 length 字符并折叠空白，生成单行摘要。"""
    if not content:
        return ""
    return " ".join(content[:length].split())


async def _search_forum_impl(query: str, limit: int) -> list[dict]:
    """论坛路检索实现：搜索 posts 与 replies，排除已删除/已折叠内容。"""
    results: list[dict] = []
    seen_post_ids: set[str] = set()

    async with AsyncSessionLocal() as session:
        # 1) 帖子全文检索：to_tsvector 表达式须与 ix_posts_content_fts 索引定义完全一致，否则无法命中索引
        posts_sql = text(
            """
            SELECT id, title, content
            FROM posts
            WHERE deleted_at IS NULL
              AND is_folded = false
              AND to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))
                  @@ plainto_tsquery('simple', :query)
            ORDER BY ts_rank(
                to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, '')),
                plainto_tsquery('simple', :query)
            ) DESC
            LIMIT :limit
            """
        )
        posts_res = await session.execute(posts_sql, {"query": query, "limit": limit})
        for row in posts_res:
            post_id = str(row.id)
            results.append({
                "type": "forum",
                "title": row.title,
                "snippet": _make_snippet(row.content),
                "url": f"/posts/{post_id}",
                "post_id": post_id,
            })
            seen_post_ids.add(post_id)

        # 2) 回复全文检索：JOIN posts 取帖子标题作为展示标题，命中同一帖子的回复跳过避免重复链接
        replies_sql = text(
            """
            SELECT r.post_id, r.content, p.title AS post_title
            FROM replies r
            JOIN posts p ON p.id = r.post_id
            WHERE r.deleted_at IS NULL
              AND to_tsvector('simple', coalesce(r.content, ''))
                  @@ plainto_tsquery('simple', :query)
            ORDER BY ts_rank(
                to_tsvector('simple', coalesce(r.content, '')),
                plainto_tsquery('simple', :query)
            ) DESC
            LIMIT :limit
            """
        )
        replies_res = await session.execute(replies_sql, {"query": query, "limit": limit})
        for row in replies_res:
            post_id = str(row.post_id)
            if post_id in seen_post_ids:
                continue
            results.append({
                "type": "forum",
                "title": row.post_title,
                "snippet": _make_snippet(row.content),
                "url": f"/posts/{post_id}",
                "post_id": post_id,
            })
            seen_post_ids.add(post_id)
            if len(results) >= limit:
                break

    return results


def _infer_web_type(url: str) -> str:
    """根据 URL 特征推断来源类型：issue / blog / docs。"""
    host = url.lower()
    if "github.com" in host and "/issues/" in host:
        return "issue"
    if any(k in host for k in ("blog", "medium.com", "dev.to", "juejin.cn")):
        return "blog"
    return "docs"


def _parse_web_results(data, limit: int) -> list[dict]:
    """解析 Web Search API 响应为统一来源格式。

    因外部 API 格式未知，按常见结构兼容解析（results / organic / data / 顶层数组），
    便于后续替换为具体适配器而无需改动调用方。
    """
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = []
        for key in ("results", "organic", "data", "items"):
            val = data.get(key)
            if isinstance(val, list):
                items = val
                break
    else:
        return []

    results: list[dict] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link") or item.get("href") or ""
        if not url:
            # 无链接的条目无法作为来源引用，跳过
            continue
        title = item.get("title") or item.get("name") or item.get("heading") or url
        snippet = (
            item.get("snippet")
            or item.get("description")
            or item.get("content")
            or item.get("abstract")
            or ""
        )
        source_type = item.get("type") or _infer_web_type(url)
        results.append({
            "type": source_type,
            "title": title,
            "snippet": _make_snippet(snippet),
            "url": url,
        })
    return results


async def _search_web_impl(query: str, limit: int) -> list[dict]:
    """联网路检索实现：调用 Web Search API 并解析结果。"""
    headers = {"Accept": "application/json"}
    if settings.WEB_SEARCH_API_KEY:
        headers["Authorization"] = f"Bearer {settings.WEB_SEARCH_API_KEY}"
    params = {"q": query, "count": limit}

    async with httpx.AsyncClient(timeout=WEB_SEARCH_TIMEOUT) as client:
        resp = await client.get(settings.WEB_SEARCH_API_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    return _parse_web_results(data, limit)


class RetrievalService:
    """双路检索服务入口。

    对外暴露四个方法：
    - search_forum：论坛路检索（全文检索 + 超时保护）
    - search_web：联网路检索（可插拔，未配置则跳过）
    - retrieve：双路并行调度，返回 (sources, retrieval_path)
    - assess_confidence：基于来源数量与权威性的置信度评估
    """

    @staticmethod
    async def search_forum(query: str, limit: int = 5) -> list[dict]:
        """论坛路检索：基于 PostgreSQL 全文检索搜索帖子与回复，超时返回空列表。"""
        try:
            return await asyncio.wait_for(
                _search_forum_impl(query, limit),
                timeout=FORUM_SEARCH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("论坛检索超时（%ss），query=%s", FORUM_SEARCH_TIMEOUT, query)
            return []
        except Exception:
            logger.exception("论坛检索异常，query=%s", query)
            return []

    @staticmethod
    async def search_web(query: str, limit: int = 5) -> list[dict]:
        """联网路检索：调用可插拔 Web Search API，未配置或超时则返回空列表。"""
        if not settings.WEB_SEARCH_API_URL:
            logger.info("未配置 WEB_SEARCH_API_URL，跳过联网检索")
            return []
        try:
            return await asyncio.wait_for(
                _search_web_impl(query, limit),
                timeout=WEB_SEARCH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("联网检索超时（%ss），query=%s", WEB_SEARCH_TIMEOUT, query)
            return []
        except Exception:
            logger.exception("联网检索异常，query=%s", query)
            return []

    @staticmethod
    async def retrieve(query: str) -> tuple[list[dict], str]:
        """双路并行检索，返回来源列表与检索路径。

        retrieval_path 判定：
        - 论坛与联网均有结果 → "hybrid"
        - 仅论坛有结果 → "forum"
        - 仅联网有结果 → "web"
        - 均无结果 → "hybrid"（已尝试双路，后续走通识模式）
        """
        forum_results, web_results = await asyncio.gather(
            RetrievalService.search_forum(query),
            RetrievalService.search_web(query),
        )
        sources = forum_results + web_results

        if forum_results and web_results:
            retrieval_path = "hybrid"
        elif forum_results:
            retrieval_path = "forum"
        elif web_results:
            retrieval_path = "web"
        else:
            retrieval_path = "hybrid"

        logger.info(
            "检索完成 query=%s path=%s forum=%d web=%d",
            query, retrieval_path, len(forum_results), len(web_results),
        )
        return sources, retrieval_path

    @staticmethod
    def assess_confidence(sources: list[dict]) -> str:
        """基于来源数量与权威性评估置信度。

        - 无来源 → low
        - 1-2 个来源 → medium
        - ≥3 个来源且其中 ≥2 个为权威类型（forum/docs）→ high
        - ≥3 个来源但不满足权威条件 → medium
        """
        if not sources:
            return "low"
        if len(sources) < 3:
            return "medium"
        authoritative = sum(1 for s in sources if s.get("type") in AUTHORITATIVE_TYPES)
        return "high" if authoritative >= 2 else "medium"
