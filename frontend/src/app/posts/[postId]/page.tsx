"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  ApiRequestError,
} from "@/lib/api";
import type {
  PostDetail,
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
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { MarkdownEditor } from "@/components/MarkdownEditor";
import { VoteButton } from "@/components/VoteButton";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Pagination } from "@/components/Pagination";
import { AIAnswer } from "@/components/AIAnswer";

/**
 * 帖子详情页：展示帖子正文、作者信息卡、回复列表。
 * 布局：桌面端两栏（正文 + 作者卡），移动端单栏。
 */

/** 举报理由选项 */
const REPORT_REASONS = [
  { value: "spam", label: "垃圾广告" },
  { value: "unfriendly", label: "不友善" },
  { value: "violation", label: "违规内容" },
  { value: "other", label: "其他" },
];

export default function PostDetailPage() {
  const params = useParams<{ postId: string }>();
  const router = useRouter();
  const { currentUser, token } = useAuth();
  const postId = params.postId;

  const [post, setPost] = useState<PostDetail | null>(null);
  const [replies, setReplies] = useState<Reply[]>([]);
  const [replyTotal, setReplyTotal] = useState(0);
  const [replyPage, setReplyPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [relatedPosts, setRelatedPosts] = useState<Array<{ postId: string; title: string }>>([]);

  // 回复输入
  const [mainReplyContent, setMainReplyContent] = useState("");
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [subReplyContents, setSubReplyContents] = useState<Record<string, string>>({});
  const [submittingReply, setSubmittingReply] = useState(false);
  const [mainReplyKind, setMainReplyKind] = useState<"supplement" | "correction" | "discussion">("supplement");

  // 折叠的回复（点击展开）
  const [expandedFolded, setExpandedFolded] = useState<Set<string>>(new Set());

  // 删除确认
  const [deleteConfirm, setDeleteConfirm] = useState<"post" | string | null>(null);

  // 举报弹窗
  const [reportTarget, setReportTarget] = useState<{ type: "post" | "reply"; id: string } | null>(null);
  const [reportReason, setReportReason] = useState("");
  const [reporting, setReporting] = useState(false);

  /** 获取帖子详情 */
  const fetchPost = useCallback(async () => {
    try {
      const data = await apiGet<PostDetail>(`/api/posts/${postId}`);
      setPost(data);
      apiGet<{ items: Array<{ postId: string; title: string }> }>("/api/posts/similar", {
        title: data.title, content: data.content.slice(0, 500), tags: data.tags.join(","),
        exclude_post_id: data.id,
      }).then((result) => setRelatedPosts(result.items)).catch(() => undefined);
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.message : "加载帖子失败"
      );
    }
  }, [postId]);

  /** 获取回复列表 */
  const fetchReplies = useCallback(
    async (page: number) => {
      try {
        const data = await apiGet<PaginatedResponse<Reply>>(
          `/api/posts/${postId}/replies`,
          { page, page_size: 20 }
        );
        // 按 vote_count 降序排列
        const sorted = [...data.items].sort((a, b) => Number(b.isAccepted) - Number(a.isAccepted) || b.voteCount - a.voteCount);
        setReplies(sorted);
        setReplyTotal(data.total);
      } catch {
        // 回复加载失败不阻塞帖子展示
      }
    },
    [postId]
  );

  // 初始加载
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([fetchPost(), fetchReplies(1)])
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postId]);

  /** 提交回复（主回复或子回复） */
  async function handleSubmitReply(parentId?: string) {
    const content = parentId ? subReplyContents[parentId] : mainReplyContent;
    if (!content || !content.trim()) return;

    setSubmittingReply(true);
    try {
      await apiPost<Reply>(`/api/posts/${postId}/replies`, {
        content: content.trim(),
        parent_id: parentId || undefined,
        kind: parentId ? "discussion" : mainReplyKind,
        target_ai_answer_id: !parentId && mainReplyKind !== "discussion" ? post?.aiAnswer?.id : undefined,
      });
      // 清空输入
      if (parentId) {
        setSubReplyContents((prev) => ({ ...prev, [parentId]: "" }));
        setReplyingTo(null);
      } else {
        setMainReplyContent("");
      }
      // 刷新回复列表
      await fetchReplies(replyPage);
    } catch (err) {
      if (err instanceof ApiRequestError && err.status === 401) {
        router.push(`/auth?mode=login&redirect=/posts/${postId}`);
      }
    } finally {
      setSubmittingReply(false);
    }
  }

  async function handleAccept(replyId: string | null) {
    await apiPut(`/api/posts/${postId}/accepted-reply`, { reply_id: replyId });
    await Promise.all([fetchPost(), fetchReplies(replyPage)]);
  }

  async function handleReward(targetType: "post" | "reply", targetId: string) {
    if (!token) {
      router.push(`/auth?mode=login&redirect=/posts/${postId}`);
      return;
    }
    const raw = window.prompt("打赏积分（1-500）", "10");
    if (!raw) return;
    const amount = Number(raw);
    if (!Number.isInteger(amount) || amount < 1 || amount > 500) return;
    await apiPost("/api/rewards", { target_type: targetType, target_id: targetId, amount },
      { "Idempotency-Key": crypto.randomUUID() });
  }

  /** 删除帖子 */
  async function handleDeletePost() {
    try {
      await apiDelete(`/api/posts/${postId}`);
      router.push("/");
    } catch {
      // 删除失败保留确认状态
    }
  }

  /** 删除回复 */
  async function handleDeleteReply(replyId: string) {
    try {
      await apiDelete(`/api/replies/${replyId}`);
      await fetchReplies(replyPage);
      setDeleteConfirm(null);
    } catch {
      // 忽略
    }
  }

  /** 提交举报 */
  async function handleReport() {
    if (!reportTarget || !reportReason) return;
    setReporting(true);
    try {
      await apiPost("/api/reports", {
        target_type: reportTarget.type,
        target_id: reportTarget.id,
        reason: reportReason,
      });
      setReportTarget(null);
      setReportReason("");
    } catch {
      // 忽略
    } finally {
      setReporting(false);
    }
  }

  /** 切换折叠回复展开状态 */
  function toggleFolded(replyId: string) {
    setExpandedFolded((prev) => {
      const next = new Set(prev);
      if (next.has(replyId)) next.delete(replyId);
      else next.add(replyId);
      return next;
    });
  }

  // 加载中
  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner size={32} />
      </div>
    );
  }

  // 加载失败
  if (error || !post) {
    return (
      <div className="rounded-lg border border-aidev-border bg-aidev-card p-8 text-center">
        <p className="text-body text-aidev-muted-foreground">
          {error || "帖子不存在"}
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

  const isAuthor = currentUser?.id === post.authorId;

  return (
    <div className="space-y-6">
      {/* 面包屑 */}
      <nav className="flex items-center gap-2 text-caption text-aidev-muted-foreground" aria-label="面包屑">
        <Link href="/" className="hover:text-aidev-primary">首页</Link>
        <span aria-hidden="true">/</span>
        <Link href={`/boards/${post.board.id}`} className="hover:text-aidev-primary">
          {post.board.name}
        </Link>
      </nav>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        {/* 左栏：帖子正文 + 回复 */}
        <div className="min-w-0 space-y-6">
          {/* 帖子正文 */}
          <article className="rounded-lg border border-aidev-border bg-aidev-card p-6 shadow-sm">
            {/* 标签行 */}
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  post.type === "question"
                    ? "bg-orange-50 text-orange-700"
                    : "bg-blue-50 text-blue-700"
                )}
              >
                {post.type === "question" ? "提问" : "分享"}
              </span>
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center rounded-full bg-aidev-muted px-2 py-0.5 text-xs text-aidev-muted-foreground"
                >
                  #{tag}
                </span>
              ))}
            </div>

            {/* 标题 */}
            <h1 className="text-headline text-aidev-foreground">{post.title}</h1>

            {/* 元信息 */}
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-aidev-muted-foreground">
              <Link
                href={`/users/${post.author.username}`}
                className="flex items-center gap-1.5 hover:text-aidev-primary"
              >
                {post.author.avatar ? (
                  <img
                    src={post.author.avatar}
                    alt={post.author.username}
                    className="h-5 w-5 rounded-full object-cover"
                  />
                ) : (
                  <span
                    className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-medium text-white"
                    style={{ backgroundColor: getAvatarColor(post.author.username) }}
                  >
                    {getInitials(post.author.username)}
                  </span>
                )}
                <span>{post.author.username}</span>
              </Link>
              <span aria-hidden="true">·</span>
              <time dateTime={post.createdAt}>{formatRelativeTime(post.createdAt)}</time>
              <span aria-hidden="true">·</span>
              <span>{formatCount(post.viewCount)} 次浏览</span>
            </div>

            {/* 投票 + 正文 */}
            <div className="mt-4 flex gap-4">
              {/* 投票栏（竖排） */}
              <div className="shrink-0">
                <VoteButton
                  targetType="post"
                  targetId={post.id}
                  initialVote={post.myVote}
                  initialCount={post.voteCount}
                  vertical
                />
              </div>

              {/* 正文内容 */}
              <div className="min-w-0 flex-1">
                {post.isFolded ? (
                  <p className="rounded-md bg-aidev-muted px-4 py-3 text-caption text-aidev-muted-foreground">
                    该内容因被举报已折叠
                  </p>
                ) : (
                  <MarkdownRenderer content={post.content} />
                )}
              </div>
            </div>

            {/* 操作栏 */}
            <div className="mt-6 flex items-center gap-2 border-t border-aidev-border pt-4">
              {isAuthor && (
                <>
                  <Link
                    href={`/ask?edit=${post.id}`}
                    className="inline-flex items-center rounded-md border border-aidev-border px-3 py-1.5 text-sm text-aidev-foreground transition hover:bg-aidev-muted"
                  >
                    编辑
                  </Link>
                  {deleteConfirm === "post" ? (
                    <>
                      <span className="text-sm text-aidev-error">确认删除？</span>
                      <button
                        type="button"
                        className="rounded-md bg-aidev-error px-3 py-1.5 text-sm text-white transition hover:opacity-90"
                        onClick={handleDeletePost}
                      >
                        确认
                      </button>
                      <button
                        type="button"
                        className="rounded-md border border-aidev-border px-3 py-1.5 text-sm text-aidev-foreground transition hover:bg-aidev-muted"
                        onClick={() => setDeleteConfirm(null)}
                      >
                        取消
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="inline-flex items-center rounded-md border border-aidev-border px-3 py-1.5 text-sm text-aidev-error transition hover:bg-aidev-state-error-bg"
                      onClick={() => setDeleteConfirm("post")}
                    >
                      删除
                    </button>
                  )}
                </>
              )}
              {!isAuthor && (
                <>
                  <button type="button" className="inline-flex items-center rounded-md border border-aidev-border px-3 py-1.5 text-sm text-aidev-foreground transition hover:bg-aidev-muted" onClick={() => handleReward("post", post.id)}>打赏积分</button>
                  <button
                    type="button"
                    className="inline-flex items-center rounded-md border border-aidev-border px-3 py-1.5 text-sm text-aidev-foreground transition hover:bg-aidev-muted"
                    onClick={() => setReportTarget({ type: "post", id: post.id })}
                  >
                    举报
                  </button>
                </>
              )}
            </div>
          </article>

          {/* AI 答案区：仅提问帖展示 */}
          {post.type === "question" && (
            <AIAnswer
              postId={post.id}
              initialAIAnswer={post.aiAnswer}
              isAuthor={isAuthor}
              correctedReply={replies.find((reply) => reply.id === post.aiAnswer?.correctedByReplyId)}
            />
          )}

          {/* 回复区 */}
          <section className="space-y-4" aria-label="回复">
            <h2 className="text-title text-aidev-foreground">
              回复 <span className="text-aidev-muted-foreground">({replyTotal})</span>
            </h2>

            {/* 回帖输入框 */}
            {token ? (
              <div className="space-y-2">
                <MarkdownEditor
                  value={mainReplyContent}
                  onChange={setMainReplyContent}
                  placeholder="写下你的回复…"
                  rows={4}
                />
                <div className="flex flex-wrap gap-2">
                  {([['supplement', '补充答案'], ['correction', '纠错 AI'], ['discussion', '参与讨论']] as const).map(([value, label]) => (
                    <button key={value} type="button" onClick={() => setMainReplyKind(value)} className={cn("rounded-full px-3 py-1 text-xs", mainReplyKind === value ? "bg-aidev-primary text-white" : "bg-aidev-muted text-aidev-muted-foreground")}>{label}</button>
                  ))}
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    disabled={!mainReplyContent.trim() || submittingReply}
                    onClick={() => handleSubmitReply()}
                    className="inline-flex items-center gap-2 rounded-md bg-aidev-primary px-4 py-2 text-sm font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90 disabled:opacity-50"
                  >
                    {submittingReply && <LoadingSpinner size={14} />}
                    发布回复
                  </button>
                </div>
              </div>
            ) : (
              <div className="rounded-md border border-aidev-border bg-aidev-muted px-4 py-3 text-center text-sm text-aidev-muted-foreground">
                <Link href={`/auth?mode=login&redirect=/posts/${postId}`} className="font-medium text-aidev-primary hover:underline">
                  登录
                </Link>
                后参与回复
              </div>
            )}

            {/* 回复列表 */}
            {replies.length === 0 ? (
              <p className="py-8 text-center text-caption text-aidev-muted-foreground">
                还没有回复，成为第一个回复的人
              </p>
            ) : (
              <div className="space-y-3">
                {replies.map((reply) => (
                  <ReplyItem
                    key={reply.id}
                    reply={reply}
                    currentUserId={currentUser?.id}
                    expandedFolded={expandedFolded}
                    onToggleFolded={toggleFolded}
                    replyingTo={replyingTo}
                    onSetReplyingTo={setReplyingTo}
                    subReplyContents={subReplyContents}
                    onSubReplyChange={(id, val) =>
                      setSubReplyContents((prev) => ({ ...prev, [id]: val }))
                    }
                    onSubmitSubReply={handleSubmitReply}
                    submittingReply={submittingReply}
                    onDeleteReply={(id) => setDeleteConfirm(id)}
                    onReport={(id) => setReportTarget({ type: "reply", id })}
                    canAccept={Boolean(isAuthor && reply.authorId !== currentUser?.id && reply.parentId === null && reply.kind !== "discussion")}
                    onAccept={() => handleAccept(reply.isAccepted ? null : reply.id)}
                    onReward={(id) => handleReward("reply", id)}
                  />
                ))}

                {/* 回复分页 */}
                {replyTotal > 20 && (
                  <div className="flex justify-center pt-2">
                    <Pagination
                      page={replyPage}
                      pageSize={20}
                      total={replyTotal}
                      onChange={(p) => {
                        setReplyPage(p);
                        fetchReplies(p);
                      }}
                    />
                  </div>
                )}
              </div>
            )}
          </section>
          {relatedPosts.length > 0 && (
            <section className="rounded-lg border border-aidev-border bg-aidev-card p-5">
              <h2 className="mb-3 text-title text-aidev-foreground">相关问题</h2>
              <ul className="space-y-2 text-sm">{relatedPosts.map((item) => <li key={item.postId}><Link className="text-aidev-primary hover:underline" href={`/posts/${item.postId}`}>{item.title}</Link></li>)}</ul>
            </section>
          )}
        </div>

        {/* 右栏：作者信息卡 */}
        <aside className="hidden lg:block">
          <div className="sticky top-20 rounded-lg border border-aidev-border bg-aidev-card p-5 shadow-sm">
            <p className="mb-3 text-xs font-semibold text-aidev-muted-foreground">作者</p>
            <Link
              href={`/users/${post.author.username}`}
              className="flex items-center gap-3"
            >
              {post.author.avatar ? (
                <img
                  src={post.author.avatar}
                  alt={post.author.username}
                  className="h-12 w-12 rounded-full object-cover"
                />
              ) : (
                <span
                  className="inline-flex h-12 w-12 items-center justify-center rounded-full text-lg font-medium text-white"
                  style={{ backgroundColor: getAvatarColor(post.author.username) }}
                >
                  {getInitials(post.author.username)}
                </span>
              )}
              <span className="font-medium text-aidev-foreground hover:text-aidev-primary">
                {post.author.username}
              </span>
            </Link>
            <div className="mt-4 space-y-2 text-caption text-aidev-muted-foreground">
              <p>发布于 {formatDate(post.createdAt)}</p>
            </div>
          </div>
        </aside>
      </div>

      {/* 删除回复确认 */}
      {deleteConfirm && deleteConfirm !== "post" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDeleteConfirm(null)} />
          <div className="relative rounded-lg bg-aidev-card p-6 shadow-lg">
            <p className="mb-4 text-body text-aidev-foreground">确认删除这条回复？</p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-aidev-border px-3 py-1.5 text-sm text-aidev-foreground hover:bg-aidev-muted"
                onClick={() => setDeleteConfirm(null)}
              >
                取消
              </button>
              <button
                type="button"
                className="rounded-md bg-aidev-error px-3 py-1.5 text-sm text-white hover:opacity-90"
                onClick={() => handleDeleteReply(deleteConfirm)}
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 举报弹窗 */}
      {reportTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/40" onClick={() => setReportTarget(null)} />
          <div className="relative w-full max-w-sm rounded-lg bg-aidev-card p-6 shadow-lg">
            <h2 className="mb-4 text-title text-aidev-foreground">举报</h2>
            <p className="mb-3 text-caption text-aidev-muted-foreground">请选择举报理由</p>
            <div className="space-y-2">
              {REPORT_REASONS.map((r) => (
                <label
                  key={r.value}
                  className={cn(
                    "flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm transition",
                    reportReason === r.value
                      ? "border-aidev-primary bg-aidev-primary-50"
                      : "border-aidev-input hover:border-aidev-primary-300"
                  )}
                >
                  <input
                    type="radio"
                    name="report-reason"
                    value={r.value}
                    checked={reportReason === r.value}
                    onChange={(e) => setReportReason(e.target.value)}
                    className="accent-aidev-primary"
                  />
                  {r.label}
                </label>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-md border border-aidev-border px-3 py-1.5 text-sm text-aidev-foreground hover:bg-aidev-muted"
                onClick={() => {
                  setReportTarget(null);
                  setReportReason("");
                }}
              >
                取消
              </button>
              <button
                type="button"
                disabled={!reportReason || reporting}
                className="rounded-md bg-aidev-primary px-3 py-1.5 text-sm text-aidev-primary-foreground hover:opacity-90 disabled:opacity-50"
                onClick={handleReport}
              >
                {reporting ? "提交中…" : "提交举报"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ======================== 回复条目组件 ======================== */

interface ReplyItemProps {
  reply: Reply;
  currentUserId?: string;
  expandedFolded: Set<string>;
  onToggleFolded: (id: string) => void;
  replyingTo: string | null;
  onSetReplyingTo: (id: string | null) => void;
  subReplyContents: Record<string, string>;
  onSubReplyChange: (id: string, val: string) => void;
  onSubmitSubReply: (parentId: string) => void;
  submittingReply: boolean;
  onDeleteReply: (id: string) => void;
  onReport: (id: string) => void;
  canAccept: boolean;
  onAccept: () => void;
  onReward: (id: string) => void;
}

function ReplyItem({
  reply,
  currentUserId,
  expandedFolded,
  onToggleFolded,
  replyingTo,
  onSetReplyingTo,
  subReplyContents,
  onSubReplyChange,
  onSubmitSubReply,
  submittingReply,
  onDeleteReply,
  onReport,
  canAccept,
  onAccept,
  onReward,
}: ReplyItemProps) {
  const isAuthor = currentUserId === reply.authorId;
  const isFolded = reply.isFolded && !expandedFolded.has(reply.id);
  const isReplying = replyingTo === reply.id;

  return (
    <div
      className={cn(
        "rounded-lg border bg-aidev-card p-4 shadow-sm",
        reply.isAccepted ? "border-green-300" : "border-aidev-border"
      )}
    >
      {/* 采纳标记 */}
      {reply.isAccepted && (
        <span className="mb-2 inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
          ✓ 已采纳
        </span>
      )}

      {/* 作者信息 */}
      <div className="mb-2 flex items-center gap-2">
        <Link href={`/users/${reply.author.username}`} className="flex items-center gap-1.5">
          {reply.author.avatar ? (
            <img
              src={reply.author.avatar}
              alt={reply.author.username}
              className="h-6 w-6 rounded-full object-cover"
            />
          ) : (
            <span
              className="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium text-white"
              style={{ backgroundColor: getAvatarColor(reply.author.username) }}
            >
              {getInitials(reply.author.username)}
            </span>
          )}
          <span className="text-sm font-medium text-aidev-foreground hover:text-aidev-primary">
            {reply.author.username}
          </span>
        </Link>
        <span className="text-caption text-aidev-muted-foreground">
          {formatRelativeTime(reply.createdAt)}
        </span>
      </div>

      {/* 内容 */}
      {isFolded ? (
        <button
          type="button"
          className="text-caption text-aidev-muted-foreground hover:text-aidev-primary"
          onClick={() => onToggleFolded(reply.id)}
        >
          该回复因被举报已折叠，点击展开
        </button>
      ) : (
        <MarkdownRenderer content={reply.content} className="text-body" />
      )}

      {/* 操作栏 */}
      {!isFolded && (
        <div className="mt-3 flex items-center gap-3">
          <VoteButton
            targetType="reply"
            targetId={reply.id}
            initialVote={reply.myVote}
            initialCount={reply.voteCount}
          />
          <button
            type="button"
            className="text-caption text-aidev-muted-foreground transition hover:text-aidev-primary"
            onClick={() => onSetReplyingTo(isReplying ? null : reply.id)}
          >
            回复
          </button>
          {canAccept && (
            <button type="button" className="text-caption font-medium text-green-700 hover:underline" onClick={onAccept}>
              {reply.isAccepted ? "取消采纳" : "采纳"}
            </button>
          )}
          {!isAuthor && (
            <button type="button" className="text-caption text-aidev-muted-foreground hover:text-aidev-primary" onClick={() => onReward(reply.id)}>打赏</button>
          )}
          {isAuthor && (
            <button
              type="button"
              className="text-caption text-aidev-muted-foreground transition hover:text-aidev-error"
              onClick={() => onDeleteReply(reply.id)}
            >
              删除
            </button>
          )}
          {!isAuthor && (
            <button
              type="button"
              className="text-caption text-aidev-muted-foreground transition hover:text-aidev-primary"
              onClick={() => onReport(reply.id)}
            >
              举报
            </button>
          )}
        </div>
      )}

      {/* 子回复输入框 */}
      {isReplying && (
        <div className="mt-3 space-y-2">
          <MarkdownEditor
            value={subReplyContents[reply.id] || ""}
            onChange={(val) => onSubReplyChange(reply.id, val)}
            placeholder={`回复 @${reply.author.username}…`}
            rows={3}
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="rounded-md border border-aidev-border px-3 py-1 text-sm text-aidev-foreground hover:bg-aidev-muted"
              onClick={() => onSetReplyingTo(null)}
            >
              取消
            </button>
            <button
              type="button"
              disabled={!(subReplyContents[reply.id] || "").trim() || submittingReply}
              className="rounded-md bg-aidev-primary px-3 py-1 text-sm text-aidev-primary-foreground hover:opacity-90 disabled:opacity-50"
              onClick={() => onSubmitSubReply(reply.id)}
            >
              回复
            </button>
          </div>
        </div>
      )}

      {/* 二级回复（子回复） */}
      {reply.children && reply.children.length > 0 && (
        <div className="mt-4 space-y-3 border-l-2 border-aidev-border pl-4">
          {reply.children.map((child) => {
            const childIsAuthor = currentUserId === child.authorId;
            const childFolded = child.isFolded && !expandedFolded.has(child.id);
            return (
              <div key={child.id} className="rounded-md bg-aidev-muted/50 p-3">
                <div className="mb-1.5 flex items-center gap-2">
                  <Link href={`/users/${child.author.username}`} className="flex items-center gap-1.5">
                    {child.author.avatar ? (
                      <img
                        src={child.author.avatar}
                        alt={child.author.username}
                        className="h-5 w-5 rounded-full object-cover"
                      />
                    ) : (
                      <span
                        className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-medium text-white"
                        style={{ backgroundColor: getAvatarColor(child.author.username) }}
                      >
                        {getInitials(child.author.username)}
                      </span>
                    )}
                    <span className="text-sm font-medium text-aidev-foreground hover:text-aidev-primary">
                      {child.author.username}
                    </span>
                  </Link>
                  <span className="text-caption text-aidev-muted-foreground">
                    {formatRelativeTime(child.createdAt)}
                  </span>
                </div>

                {childFolded ? (
                  <button
                    type="button"
                    className="text-caption text-aidev-muted-foreground hover:text-aidev-primary"
                    onClick={() => onToggleFolded(child.id)}
                  >
                    该回复因被举报已折叠，点击展开
                  </button>
                ) : (
                  <MarkdownRenderer content={child.content} className="text-sm" />
                )}

                {!childFolded && (
                  <div className="mt-2 flex items-center gap-3">
                    <VoteButton
                      targetType="reply"
                      targetId={child.id}
                      initialVote={child.myVote}
                      initialCount={child.voteCount}
                    />
                    {childIsAuthor && (
                      <button
                        type="button"
                        className="text-caption text-aidev-muted-foreground transition hover:text-aidev-error"
                        onClick={() => onDeleteReply(child.id)}
                      >
                        删除
                      </button>
                    )}
                    {!childIsAuthor && (
                      <button
                        type="button"
                        className="text-caption text-aidev-muted-foreground transition hover:text-aidev-primary"
                        onClick={() => onReport(child.id)}
                      >
                        举报
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
