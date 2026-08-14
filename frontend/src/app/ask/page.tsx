"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiGet, apiPost, apiPatch, ApiRequestError } from "@/lib/api";
import type { Board, PostDetail, PostType } from "@/lib/types";
import { cn } from "@/lib/utils";
import { MarkdownEditor } from "@/components/MarkdownEditor";
import { LoadingSpinner } from "@/components/LoadingSpinner";

/**
 * 发帖/编辑页：
 * - 需登录（未登录跳转 /auth?mode=login&redirect=/ask）
 * - 编辑模式：?edit={postId} 加载已有帖子，调用 PATCH
 * - ?board={boardId} 预填版块
 */

/** 版块列表响应 */
interface BoardsResponse {
  entry: Board[];
  deep: Board[];
}

function AskContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { currentUser, token, loading: authLoading } = useAuth();

  const editId = searchParams.get("edit");
  const presetBoardId = searchParams.get("board");
  const isEditMode = Boolean(editId);

  // 表单字段
  const [title, setTitle] = useState("");
  const [boardId, setBoardId] = useState(presetBoardId || "");
  const [type, setType] = useState<PostType>("question");
  const [tagsInput, setTagsInput] = useState("");
  const [content, setContent] = useState("");
  const [summary, setSummary] = useState<string | null>(null);
  const [similar, setSimilar] = useState<Array<{ postId: string; title: string; snippet: string }>>([]);
  const [assistResult, setAssistResult] = useState<{ action: string; content?: string | null; tags?: string[] } | null>(null);
  const [assisting, setAssisting] = useState(false);

  const [boards, setBoards] = useState<BoardsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 未登录跳转登录页
  useEffect(() => {
    if (!authLoading && !token) {
      router.replace("/auth?mode=login&redirect=/ask");
    }
  }, [authLoading, token, router]);

  // 获取版块列表
  useEffect(() => {
    apiGet<BoardsResponse>("/api/boards")
      .then(setBoards)
      .catch(() => {})
      .finally(() => {
        if (!isEditMode) setLoading(false);
      });
  }, [isEditMode]);

  // 编辑模式：加载已有帖子
  useEffect(() => {
    if (!editId || !token) return;
    setLoading(true);
    apiGet<PostDetail>(`/api/posts/${editId}`)
      .then((data) => {
        setTitle(data.title);
        setBoardId(data.boardId);
        setType(data.type);
        setTagsInput(data.tags.join(", "));
        setContent(data.content);
        setSummary(data.summary);
      })
      .catch((err) => {
        setError(
          err instanceof ApiRequestError ? err.message : "加载帖子失败"
        );
      })
      .finally(() => setLoading(false));
  }, [editId, token]);

  useEffect(() => {
    if (title.trim().length < 10) {
      setSimilar([]);
      return;
    }
    const timer = window.setTimeout(() => {
      apiGet<{ items: Array<{ postId: string; title: string; snippet: string }> }>("/api/posts/similar", {
        title: title.trim(), content: content.slice(0, 500), tags: tagsInput,
        exclude_post_id: editId || undefined,
      }).then((data) => setSimilar(data.items)).catch(() => setSimilar([]));
    }, 450);
    return () => window.clearTimeout(timer);
  }, [title, content, tagsInput, editId]);

  async function runAssist(action: "polish" | "format_code" | "summarize" | "suggest_tags") {
    setAssisting(true);
    setError(null);
    try {
      const result = await apiPost<{ action: string; content: string | null; tags: string[] }>("/api/ai/writing-assist", {
        action, title, content,
      });
      setAssistResult(result);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "AI 写作辅助暂不可用");
    } finally {
      setAssisting(false);
    }
  }

  function applyAssist() {
    if (!assistResult) return;
    if (assistResult.action === "suggest_tags") setTagsInput((assistResult.tags || []).join(", "));
    else if (assistResult.action === "summarize") setSummary(assistResult.content || null);
    else if (assistResult.content) setContent(assistResult.content);
    setAssistResult(null);
  }

  /** 解析标签输入：逗号分隔，去空格去重 */
  function parseTags(input: string): string[] {
    return [
      ...new Set(
        input
          .split(/[,，]/)
          .map((t) => t.trim())
          .filter(Boolean)
      ),
    ];
  }

  /** 表单校验 */
  function validate(): string | null {
    if (title.trim().length < 5) return "标题至少 5 个字符";
    if (content.trim().length < 10) return "内容至少 10 个字符";
    if (!boardId) return "请选择版块";
    return null;
  }

  /** 提交表单 */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        board_id: boardId,
        type,
        tags: parseTags(tagsInput),
        summary,
      };

      if (isEditMode && editId) {
        // 编辑模式：PATCH
        const data = await apiPatch<PostDetail>(`/api/posts/${editId}`, {
          title: payload.title,
          content: payload.content,
          tags: payload.tags,
          summary: payload.summary,
        });
        router.push(`/posts/${data.id}`);
      } else {
        // 新建模式：POST
        const data = await apiPost<PostDetail>("/api/posts", payload);
        router.push(`/posts/${data.id}`);
      }
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.message : "提交失败，请稍后重试"
      );
    } finally {
      setSubmitting(false);
    }
  }

  // 等待认证状态加载
  if (authLoading || loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (!token) return null;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-headline text-aidev-foreground">
        {isEditMode ? "编辑帖子" : "发起提问"}
      </h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* 标题 */}
        <div>
          <label htmlFor="post-title" className="mb-1 block text-caption font-medium text-aidev-foreground">
            标题 <span className="text-aidev-error">*</span>
          </label>
          <input
            id="post-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
            placeholder="简要描述你的问题或分享主题（至少 5 个字符）"
            required
          />
        </div>

        {/* 版块 + 类型 */}
        {similar.length > 0 && !isEditMode && (
          <aside className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-medium text-amber-900">发布前看看这些相似问题</p>
            <ul className="mt-2 space-y-1 text-sm">
              {similar.map((item) => <li key={item.postId}><a className="text-aidev-primary hover:underline" href={`/posts/${item.postId}`} target="_blank">{item.title}</a></li>)}
            </ul>
          </aside>
        )}

        {/* 版块 + 类型 */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="post-board" className="mb-1 block text-caption font-medium text-aidev-foreground">
              版块 <span className="text-aidev-error">*</span>
            </label>
            <select
              id="post-board"
              value={boardId}
              onChange={(e) => setBoardId(e.target.value)}
              className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
              required
            >
              <option value="">请选择版块</option>
              {boards && (
                <>
                  {boards.entry.length > 0 && (
                    <optgroup label="入门区">
                      {boards.entry.map((b) => (
                        <option key={b.id} value={b.id}>{b.name}</option>
                      ))}
                    </optgroup>
                  )}
                  {boards.deep.length > 0 && (
                    <optgroup label="深度区">
                      {boards.deep.map((b) => (
                        <option key={b.id} value={b.id}>{b.name}</option>
                      ))}
                    </optgroup>
                  )}
                </>
              )}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-caption font-medium text-aidev-foreground">
              类型
            </label>
            <div className="flex gap-2">
              {([
                { value: "question", label: "提问" },
                { value: "share", label: "分享" },
              ] as const).map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={cn(
                    "flex-1 rounded-md border px-3 py-2 text-sm font-medium transition",
                    type === opt.value
                      ? "border-aidev-primary bg-aidev-primary-50 text-aidev-primary-700"
                      : "border-aidev-input text-aidev-muted-foreground hover:border-aidev-primary-300"
                  )}
                  onClick={() => setType(opt.value)}
                  aria-pressed={type === opt.value}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 标签 */}
        <div>
          <label htmlFor="post-tags" className="mb-1 block text-caption font-medium text-aidev-foreground">
            标签 <span className="text-aidev-muted-foreground">（逗号分隔，可选）</span>
          </label>
          <input
            id="post-tags"
            type="text"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
            placeholder="如：Python, RAG, Agent"
          />
        </div>

        {/* 内容编辑器 */}
        <div>
          <label className="mb-1 block text-caption font-medium text-aidev-foreground">
            内容 <span className="text-aidev-error">*</span>
          </label>
          <MarkdownEditor
            value={content}
            onChange={setContent}
            placeholder="详细描述你的问题或分享内容（至少 10 个字符）…"
            rows={12}
          />
        </div>

        {/* 错误提示 */}
        <div className="rounded-lg border border-aidev-border bg-aidev-card p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-aidev-foreground">AI 写作辅助</span>
            {([['polish', '润色'], ['format_code', '整理代码块'], ['summarize', '生成摘要'], ['suggest_tags', '建议标签']] as const).map(([action, label]) => (
              <button key={action} type="button" disabled={assisting || content.length === 0} onClick={() => runAssist(action)} className="rounded-md border border-aidev-border px-3 py-1.5 text-xs text-aidev-foreground hover:bg-aidev-muted disabled:opacity-50">{label}</button>
            ))}
          </div>
          {assistResult && (
            <div className="mt-3 rounded-md bg-aidev-muted p-3 text-sm">
              <pre className="max-h-48 whitespace-pre-wrap font-sans text-aidev-foreground">{assistResult.content || (assistResult.tags || []).join(", ")}</pre>
              <div className="mt-2 flex gap-2"><button type="button" onClick={applyAssist} className="rounded bg-aidev-primary px-3 py-1 text-white">应用结果</button><button type="button" onClick={() => setAssistResult(null)} className="px-3 py-1 text-aidev-muted-foreground">放弃</button></div>
            </div>
          )}
          {summary && <p className="mt-2 text-xs text-aidev-muted-foreground">已应用摘要：{summary}</p>}
        </div>

        {/* 错误提示 */}
        {error && (
          <p role="alert" className="rounded-md bg-aidev-state-error-bg px-3 py-2 text-caption text-aidev-error">
            {error}
          </p>
        )}

        {/* 提交按钮 */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            className="rounded-md border border-aidev-border px-4 py-2 text-sm font-medium text-aidev-foreground transition hover:bg-aidev-muted"
            onClick={() => router.back()}
          >
            取消
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-md bg-aidev-primary px-6 py-2 text-sm font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90 disabled:opacity-50"
          >
            {submitting && <LoadingSpinner size={16} />}
            {submitting ? "提交中…" : isEditMode ? "保存修改" : "发布"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function AskPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[400px] items-center justify-center">
          <LoadingSpinner size={32} />
        </div>
      }
    >
      <AskContent />
    </Suspense>
  );
}
