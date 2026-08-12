"use client";

import Link from "next/link";
import type { PostListItem } from "@/lib/types";
import { cn, formatCount, formatRelativeTime, getAvatarColor, getInitials } from "@/lib/utils";

/**
 * 帖子卡片：用于帖子列表中的单条展示。
 * 展示标题、作者、版块、投票/回复/浏览数、时间。
 * 折叠帖显示"该内容因被举报已折叠"。
 */
interface PostCardProps {
  post: PostListItem;
}

/** 帖子类型标签：提问=橙色，分享=蓝色 */
function PostTypeBadge({ type }: { type: PostListItem["type"] }) {
  const isQuestion = type === "question";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        isQuestion
          ? "bg-orange-50 text-orange-700"
          : "bg-blue-50 text-blue-700"
      )}
    >
      {isQuestion ? "提问" : "分享"}
    </span>
  );
}

/** 版块标签 */
function BoardBadge({ board }: { board: PostListItem["board"] }) {
  return (
    <Link
      href={`/boards/${board.id}`}
      className="inline-flex items-center rounded-full bg-aidev-primary-50 px-2 py-0.5 text-xs font-medium text-aidev-primary-700 transition hover:bg-aidev-primary-100"
    >
      {board.name}
    </Link>
  );
}

/** 作者头像（带 fallback 首字母） */
function Avatar({ username, avatar }: { username: string; avatar: string | null }) {
  if (avatar) {
    return (
      <img
        src={avatar}
        alt={username}
        className="h-6 w-6 rounded-full object-cover"
        loading="lazy"
      />
    );
  }
  return (
    <span
      className="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium text-white"
      style={{ backgroundColor: getAvatarColor(username) }}
      aria-hidden="true"
    >
      {getInitials(username)}
    </span>
  );
}

export function PostCard({ post }: PostCardProps) {
  return (
    <article className="rounded-lg border border-aidev-border bg-aidev-card p-4 shadow-sm transition hover:shadow-md sm:p-5">
      {post.isFolded ? (
        // 折叠帖：仅显示折叠提示
        <div className="py-4 text-center text-caption text-aidev-muted-foreground">
          该内容因被举报已折叠
        </div>
      ) : (
        <div className="space-y-3">
          {/* 标签行 */}
          <div className="flex flex-wrap items-center gap-2">
            <PostTypeBadge type={post.type} />
            <BoardBadge board={post.board} />
            {post.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center rounded-full bg-aidev-muted px-2 py-0.5 text-xs text-aidev-muted-foreground"
              >
                #{tag}
              </span>
            ))}
          </div>

          {/* 标题 */}
          <h3 className="text-base font-semibold leading-snug">
            <Link
              href={`/posts/${post.id}`}
              className="text-aidev-foreground transition hover:text-aidev-primary"
            >
              {post.title}
            </Link>
          </h3>

          {/* 元信息行 */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-caption text-aidev-muted-foreground">
            {/* 作者 */}
            <Link
              href={`/users/${post.author.username}`}
              className="flex items-center gap-1.5 transition hover:text-aidev-primary"
            >
              <Avatar username={post.author.username} avatar={post.author.avatar} />
              <span>{post.author.username}</span>
            </Link>

            <span aria-hidden="true">·</span>
            <time dateTime={post.createdAt}>{formatRelativeTime(post.createdAt)}</time>

            {/* 统计数据 */}
            <div className="flex items-center gap-3" aria-label="帖子统计">
              <span className="flex items-center gap-1" title="投票数">
                <span aria-hidden="true">▲</span> {formatCount(post.voteCount)}
              </span>
              <span className="flex items-center gap-1" title="回复数">
                <span aria-hidden="true">💬</span> {formatCount(post.replyCount)}
              </span>
              <span className="flex items-center gap-1" title="浏览数">
                <span aria-hidden="true">👁</span> {formatCount(post.viewCount)}
              </span>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
