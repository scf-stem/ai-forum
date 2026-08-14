"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiGet, ApiRequestError } from "@/lib/api";
import type {
  User,
  PostListItem,
  Reply,
  PaginatedResponse,
} from "@/lib/types";
import {
  cn,
  formatDate,
  formatRelativeTime,
  getAvatarColor,
  getInitials,
  formatCount,
} from "@/lib/utils";
import { PostCard } from "@/components/PostCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";

/**
 * 个人主页：展示用户资料与提问/分享/回复 Tab。
 */

type Tab = "question" | "share" | "reply";

export default function UserProfilePage() {
  const { currentUser } = useAuth();
  const params = useParams<{ username: string }>();
  const username = decodeURIComponent(params.username);

  const [user, setUser] = useState<User | null>(null);
  const [tab, setTab] = useState<Tab>("question");
  const [posts, setPosts] = useState<PostListItem[]>([]);
  const [replies, setReplies] = useState<Reply[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 20;

  // 获取用户资料
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiGet<User>(`/api/users/${username}`)
      .then((data) => {
        if (!cancelled) setUser(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiRequestError ? err.message : "用户不存在"
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [username]);

  // Tab 切换时获取数据
  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setListLoading(true);
    setPage(1);

    const fetcher =
      tab === "reply"
        ? apiGet<PaginatedResponse<Reply>>(`/api/users/${username}/replies`, {
            page: 1,
            page_size: pageSize,
          })
        : apiGet<PaginatedResponse<PostListItem>>(
            `/api/users/${username}/posts`,
            { type: tab, page: 1, page_size: pageSize }
          );

    fetcher
      .then((data) => {
        if (cancelled) return;
        if (tab === "reply") {
          setReplies((data as PaginatedResponse<Reply>).items);
          setPosts([]);
        } else {
          setPosts((data as PaginatedResponse<PostListItem>).items);
          setReplies([]);
        }
        setTotal(data.total);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setListLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [user, tab, username]);

  /** 翻页 */
  async function handlePageChange(newPage: number) {
    setPage(newPage);
    setListLoading(true);
    try {
      if (tab === "reply") {
        const data = await apiGet<PaginatedResponse<Reply>>(
          `/api/users/${username}/replies`,
          { page: newPage, page_size: pageSize }
        );
        setReplies(data.items);
        setTotal(data.total);
      } else {
        const data = await apiGet<PaginatedResponse<PostListItem>>(
          `/api/users/${username}/posts`,
          { type: tab, page: newPage, page_size: pageSize }
        );
        setPosts(data.items);
        setTotal(data.total);
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setListLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="rounded-lg border border-aidev-border bg-aidev-card p-8 text-center">
        <p className="text-body text-aidev-muted-foreground">
          {error || "用户不存在"}
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
      {/* 资料卡 */}
      <section className="rounded-lg border border-aidev-border bg-aidev-card p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          {/* 头像 */}
          {user.avatar ? (
            <img
              src={user.avatar}
              alt={user.username}
              className="h-20 w-20 rounded-full object-cover"
            />
          ) : (
            <span
              className="inline-flex h-20 w-20 shrink-0 items-center justify-center rounded-full text-2xl font-bold text-white"
              style={{ backgroundColor: getAvatarColor(user.username) }}
            >
              {getInitials(user.username)}
            </span>
          )}

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-headline text-aidev-foreground">{user.username}</h1>
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  user.role === "developer"
                    ? "bg-blue-50 text-blue-700"
                    : "bg-green-50 text-green-700"
                )}
              >
                {user.role === "developer" ? "开发者" : "零基础"}
              </span>
            </div>

            {user.bio && (
              <p className="mt-2 text-body text-aidev-muted-foreground">{user.bio}</p>
            )}

            {/* 技术栈 */}
            {user.techStack.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {user.techStack.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center rounded-full bg-aidev-primary-50 px-2.5 py-0.5 text-xs font-medium text-aidev-primary-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* 时间信息 */}
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-caption text-aidev-muted-foreground">
              <span>注册于 {formatDate(user.createdAt)}</span>
              <span>最近活跃 {formatRelativeTime(user.lastActiveAt)}</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <div className="rounded-md bg-aidev-muted p-3"><strong className="block text-lg text-aidev-foreground">Lv{user.level}</strong><span className="text-xs text-aidev-muted-foreground">等级</span></div>
              <div className="rounded-md bg-aidev-muted p-3"><strong className="block text-lg text-aidev-foreground">{formatCount(user.reputation)}</strong><span className="text-xs text-aidev-muted-foreground">声望</span></div>
              <div className="rounded-md bg-aidev-muted p-3"><strong className="block text-lg text-aidev-foreground">{formatCount(user.receivedUpvotes || 0)}</strong><span className="text-xs text-aidev-muted-foreground">获赞</span></div>
              <div className="rounded-md bg-aidev-muted p-3"><strong className="block text-lg text-aidev-foreground">{formatCount(user.acceptedCount || 0)}</strong><span className="text-xs text-aidev-muted-foreground">被采纳</span></div>
            </div>
            {user.badges && user.badges.length > 0 && <div className="mt-4"><p className="mb-2 text-sm font-medium text-aidev-foreground">徽章墙</p><div className="flex flex-wrap gap-2">{user.badges.map((badge) => <span key={badge.code} className="rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs text-amber-800">🏅 {badge.code}</span>)}</div></div>}
            {currentUser?.id === user.id && <p className="mt-3 text-sm font-medium text-aidev-primary">可用积分：{user.pointsBalance}</p>}
          </div>
        </div>
      </section>

      {/* Tab 切换 */}
      <div className="flex gap-1 border-b border-aidev-border" role="tablist">
        {([
          { value: "question", label: "提问" },
          { value: "share", label: "分享" },
          { value: "reply", label: "回复" },
        ] as const).map((t) => (
          <button
            key={t.value}
            type="button"
            role="tab"
            aria-selected={tab === t.value}
            className={cn(
              "border-b-2 px-4 py-2 text-sm font-medium transition",
              tab === t.value
                ? "border-aidev-primary text-aidev-primary"
                : "border-transparent text-aidev-muted-foreground hover:text-aidev-foreground"
            )}
            onClick={() => setTab(t.value)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* 内容列表 */}
      {listLoading ? (
        <div className="flex min-h-[200px] items-center justify-center">
          <LoadingSpinner size={28} />
        </div>
      ) : tab === "reply" ? (
        // 回复列表
        replies.length === 0 ? (
          <EmptyState message="还没有回复" />
        ) : (
          <div className="space-y-3">
            {replies.map((reply) => (
              <article
                key={reply.id}
                className="rounded-lg border border-aidev-border bg-aidev-card p-4 shadow-sm"
              >
                <div className="mb-2 flex items-center gap-2 text-caption text-aidev-muted-foreground">
                  <span>回复了</span>
                  <Link
                    href={`/posts/${reply.postId}`}
                    className="font-medium text-aidev-primary hover:underline"
                  >
                    查看原帖 →
                  </Link>
                  <span aria-hidden="true">·</span>
                  <time dateTime={reply.createdAt}>{formatRelativeTime(reply.createdAt)}</time>
                  <span aria-hidden="true">·</span>
                  <span>▲ {formatCount(reply.voteCount)}</span>
                </div>
                <div className="text-body text-aidev-foreground line-clamp-3">
                  {reply.content}
                </div>
              </article>
            ))}
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
        )
      ) : (
        // 帖子列表
        posts.length === 0 ? (
          <EmptyState
            message={tab === "question" ? "还没有提问" : "还没有分享"}
          />
        ) : (
          <div className="space-y-3">
            {posts.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
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
        )
      )}
    </div>
  );
}
