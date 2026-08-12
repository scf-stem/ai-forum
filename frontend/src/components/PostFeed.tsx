"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, ApiRequestError } from "@/lib/api";
import type { PaginatedResponse, PostListItem } from "@/lib/types";
import { cn } from "@/lib/utils";
import { PostCard } from "./PostCard";
import { Pagination } from "./Pagination";
import { LoadingSpinner } from "./LoadingSpinner";
import { EmptyState } from "./EmptyState";

/**
 * 帖子列表流：封装排序切换、分页、加载/空状态。
 * 被首页和版块详情页复用。
 * 支持通过 initialPosts 传入 SSR 首屏数据，后续交互客户端获取。
 */
interface PostFeedProps {
  /** API 路径，如 /api/posts 或 /api/boards/{id}/posts */
  apiPath: string;
  /** SSR 首屏数据（帖子列表） */
  initialPosts?: PostListItem[];
  /** SSR 首屏数据（总数） */
  initialTotal?: number;
  /** 是否展示排序切换（默认 true） */
  showSortToggle?: boolean;
  /** 空状态文案 */
  emptyMessage?: string;
  /** 每页条数 */
  pageSize?: number;
}

type SortMode = "latest" | "hot";

export function PostFeed({
  apiPath,
  initialPosts,
  initialTotal,
  showSortToggle = true,
  emptyMessage = "还没有内容",
  pageSize = 20,
}: PostFeedProps) {
  const [posts, setPosts] = useState<PostListItem[]>(initialPosts ?? []);
  const [total, setTotal] = useState<number>(initialTotal ?? 0);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortMode>("hot");
  const [loading, setLoading] = useState(!initialPosts);
  const [error, setError] = useState<string | null>(null);

  /** 获取帖子列表 */
  const fetchPosts = useCallback(
    async (targetPage: number, targetSort: SortMode) => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiGet<PaginatedResponse<PostListItem>>(apiPath, {
          page: targetPage,
          page_size: pageSize,
          sort: targetSort,
        });
        setPosts(data.items);
        setTotal(data.total);
      } catch (err) {
        if (err instanceof ApiRequestError) {
          setError(err.message);
        } else {
          setError("加载失败，请刷新重试");
        }
      } finally {
        setLoading(false);
      }
    },
    [apiPath, pageSize]
  );

  // 初始数据为空时客户端获取（如版块页）
  useEffect(() => {
    if (!initialPosts) {
      fetchPosts(page, sort);
    }
    // 仅在挂载时执行
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 排序切换 */
  function handleSortChange(newSort: SortMode) {
    if (newSort === sort) return;
    setSort(newSort);
    setPage(1);
    fetchPosts(1, newSort);
  }

  /** 翻页 */
  function handlePageChange(newPage: number) {
    setPage(newPage);
    fetchPosts(newPage, sort);
    // 滚动到顶部
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // 加载中
  if (loading) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <LoadingSpinner size={32} />
      </div>
    );
  }

  // 加载失败
  if (error) {
    return (
      <EmptyState
        message={error}
        action={
          <button
            type="button"
            className="rounded-md bg-aidev-primary px-4 py-2 text-sm font-medium text-aidev-primary-foreground"
            onClick={() => fetchPosts(page, sort)}
          >
            重试
          </button>
        }
      />
    );
  }

  // 空列表
  if (posts.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="space-y-4">
      {/* 排序切换 */}
      {showSortToggle && (
        <div className="flex items-center gap-1" role="tablist" aria-label="排序方式">
          {(["hot", "latest"] as SortMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              role="tab"
              aria-selected={sort === mode}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm font-medium transition",
                sort === mode
                  ? "bg-aidev-primary text-aidev-primary-foreground"
                  : "text-aidev-muted-foreground hover:bg-aidev-muted hover:text-aidev-foreground"
              )}
              onClick={() => handleSortChange(mode)}
            >
              {mode === "hot" ? "热门" : "最新"}
            </button>
          ))}
        </div>
      )}

      {/* 帖子列表 */}
      <div className="space-y-3">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} />
        ))}
      </div>

      {/* 分页 */}
      {total > pageSize && (
        <div className="flex justify-center pt-4">
          <Pagination
            page={page}
            pageSize={pageSize}
            total={total}
            onChange={handlePageChange}
          />
        </div>
      )}
    </div>
  );
}
