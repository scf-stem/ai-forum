"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiGet, ApiRequestError } from "@/lib/api";
import type { Board } from "@/lib/types";
import { PostFeed } from "@/components/PostFeed";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { cn } from "@/lib/utils";

/**
 * 版块详情页：展示版块信息与版块下的帖子列表。
 * 支持最新/热度排序切换与分页。
 */
export default function BoardDetailPage() {
  const params = useParams<{ boardId: string }>();
  const boardId = params.boardId;

  const [board, setBoard] = useState<Board | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 获取版块信息
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<Board>(`/api/boards/${boardId}`)
      .then((data) => {
        if (!cancelled) setBoard(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError ? err.message : "加载版块信息失败"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [boardId]);

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (error || !board) {
    return (
      <div className="rounded-lg border border-aidev-border bg-aidev-card p-8 text-center">
        <p className="text-body text-aidev-muted-foreground">
          {error || "版块不存在"}
        </p>
        <Link
          href="/"
          className="mt-4 inline-block text-sm font-medium text-aidev-primary hover:underline"
        >
          ← 返回首页
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 版块信息头 */}
      <section className="rounded-lg border border-aidev-border bg-aidev-card p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  board.tier === "entry"
                    ? "bg-green-50 text-green-700"
                    : "bg-purple-50 text-purple-700"
                )}
              >
                {board.tier === "entry" ? "入门区" : "深度区"}
              </span>
            </div>
            <h1 className="mt-2 text-headline text-aidev-foreground">{board.name}</h1>
            {board.description && (
              <p className="mt-1 text-body text-aidev-muted-foreground">
                {board.description}
              </p>
            )}
            <div className="mt-3 flex gap-4 text-caption text-aidev-muted-foreground">
              <span>{board.postCount} 篇帖子</span>
              <span>{board.followerCount} 人关注</span>
            </div>
          </div>

          {/* 发帖按钮 */}
          <Link
            href={`/ask?board=${board.id}`}
            className="inline-flex shrink-0 items-center rounded-md bg-aidev-primary px-4 py-2 text-sm font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90"
          >
            发帖
          </Link>
        </div>
      </section>

      {/* 帖子列表 */}
      <PostFeed
        apiPath={`/api/boards/${boardId}/posts`}
        emptyMessage="该版块还没有帖子，快来发第一篇吧"
      />
    </div>
  );
}
