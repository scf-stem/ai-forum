"""AI 答案生成服务。

封装 DeepSeek API（OpenAI 兼容格式）的调用逻辑，提供流式与非流式两种答案生成方式。
基于检索上下文构建 system prompt，生成带来源标注的 Markdown 技术答案。
"""
import logging
from typing import AsyncGenerator

import httpx
import openai
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

PROMPT_INSTRUCTIONS = {
    "answer-v1": "保持简洁，直击要点，不要过多寒暄",
    "answer-v2-citations": "先核对来源能否支持每项事实；无法由来源支持的事实必须明确标为推测。保持简洁，不要寒暄",
}

# API 调用失败时的降级文案
DEGRADED_ANSWER = (
    "抱歉，AI 答案生成服务暂时不可用。请稍后重试，或等待社区成员补充答案。\n\n"
    "如果您的问题紧急，请尝试重新生成或直接在下方发布补充说明。"
)

# 模块级初始化 AsyncOpenAI 客户端（DeepSeek 使用 OpenAI 兼容格式）
client = AsyncOpenAI(
    base_url=settings.DEEPSEEK_BASE_URL,
    api_key=settings.DEEPSEEK_API_KEY,
)


def build_system_prompt(sources: list[dict], prompt_version: str | None = None) -> str:
    """构建包含检索上下文的 system prompt。

    将 sources 列表格式化为文本，引导模型生成带来源标注的 Markdown 答案。
    每个来源预期字段：type（来源类型）、title（标题）、snippet（摘要）、url（链接）。
    """
    # 格式化检索来源列表，逐条展示类型、标题、摘要与链接
    if sources:
        source_lines = []
        for idx, source in enumerate(sources, start=1):
            source_type = source.get("type", "未知")
            title = source.get("title", "无标题")
            snippet = source.get("snippet", "")
            url = source.get("url", "")
            line = f"[{idx}] 类型：{source_type} | 标题：{title}"
            if snippet:
                line += f"\n    摘要：{snippet}"
            if url:
                line += f"\n    链接：{url}"
            source_lines.append(line)
        formatted_sources = "\n".join(source_lines)
    else:
        formatted_sources = "（无可用检索上下文）"

    version = prompt_version or settings.AI_PROMPT_VERSION
    if version not in PROMPT_INSTRUCTIONS:
        raise ValueError(f"未知 Prompt 版本：{version}")
    return f"""你是一个 AI 技术问答助手，为开发者社区生成准确、结构化的技术答案。

请基于以下检索上下文生成答案：

{formatted_sources}

要求：
1. 答案格式为 Markdown，包含分步骤说明和代码示例（如适用）
2. 在答案末尾以 ## 来源 标题列出引用的来源（标注来源类型和标题）
3. 如果检索上下文不足以回答问题，基于通识生成但明确标注"以下内容基于 AI 通识生成，未经权威来源验证"
4. 使用中文回答
5. {PROMPT_INSTRUCTIONS[version]}"""


async def generate_answer_stream(
    title: str, content: str, sources: list[dict]
) -> AsyncGenerator[str, None]:
    """流式生成 AI 答案。

    以异步生成器形式逐 chunk 返回 token 文本，调用方可通过 `async for` 消费。
    任何异常都会被捕获并记录日志，最终 yield 一次完整降级文案以保证流不中断。
    """
    messages = [
        {"role": "system", "content": build_system_prompt(sources)},
        {"role": "user", "content": f"帖子标题：{title}\n\n帖子内容：{content}"},
    ]

    try:
        # DeepSeek 使用 OpenAI 兼容格式，非思考模式不传 thinking 参数
        stream = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            stream=True,
            temperature=settings.AI_ANSWER_TEMPERATURE,
            max_tokens=settings.AI_ANSWER_MAX_TOKENS,
        )
        async for chunk in stream:
            # 过滤空 delta 与 None content，仅返回有效文本
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except (openai.APIError, openai.APITimeoutError, httpx.TimeoutException):
        logger.exception("DeepSeek 流式答案生成失败")
        yield DEGRADED_ANSWER
    except Exception:  # noqa: BLE001 - 兜底捕获所有未知异常，保证流式接口不抛出
        logger.exception("DeepSeek 流式答案生成出现未知异常")
        yield DEGRADED_ANSWER


async def generate_answer(
    title: str, content: str, sources: list[dict], prompt_version: str | None = None,
) -> tuple[str, dict]:
    """非流式生成 AI 答案（流式不可用时降级使用）。

    返回 (content, token_usage) 元组。
    token_usage 格式：{"prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}
    调用失败时返回降级文案与全零的 token 统计。
    """
    messages = [
        {"role": "system", "content": build_system_prompt(sources, prompt_version)},
        {"role": "user", "content": f"帖子标题：{title}\n\n帖子内容：{content}"},
    ]

    try:
        response = await client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            stream=False,
            temperature=settings.AI_ANSWER_TEMPERATURE,
            max_tokens=settings.AI_ANSWER_MAX_TOKENS,
        )
        content = response.choices[0].message.content or ""
        usage = response.usage
        token_usage = {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }
        return content, token_usage
    except (openai.APIError, openai.APITimeoutError, httpx.TimeoutException):
        logger.exception("DeepSeek 非流式答案生成失败")
        return DEGRADED_ANSWER, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    except Exception:  # noqa: BLE001 - 兜底捕获未知异常，保证调用方不中断
        logger.exception("DeepSeek 非流式答案生成出现未知异常")
        return DEGRADED_ANSWER, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }


async def generate_specialized(system_prompt: str, user_content: str,
                               max_tokens: int = 1200) -> tuple[str, dict]:
    """Run a non-streaming, versioned helper prompt and surface failures to callers."""
    if not settings.DEEPSEEK_API_KEY:
        raise RuntimeError("AI 服务未配置")
    response = await client.chat.completions.create(
        model=settings.DEEPSEEK_MODEL,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_content}],
        stream=False, temperature=0.2, max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or ""
    usage = response.usage
    return content, {
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
    }
