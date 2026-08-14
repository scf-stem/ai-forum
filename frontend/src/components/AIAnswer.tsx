"use client";

/**
 * AI 答案展示组件。
 * - generating：流式渲染 token + 脉冲加载动画 + 闪烁光标
 * - published：置信度标签 + 风险提示（低置信度）+ Markdown 内容 + 来源卡片
 * - error：错误提示 + 重新生成按钮
 * 仅帖子作者可见"重新生成"按钮。
 */
import { useState } from "react";
import Link from "next/link";
import { useAIAnswerStream } from "@/hooks/useAIAnswerStream";
import { regenerateAIAnswer, ApiRequestError } from "@/lib/api";
import { MarkdownRenderer } from "./MarkdownRenderer";
import { cn, formatDateTime } from "@/lib/utils";
import type { AIAnswer, AnswerSource, AIConfidence } from "@/lib/types";

interface AIAnswerProps {
  postId: string;
  initialAIAnswer: AIAnswer | null;
  /** 当前用户是否是帖子作者（控制重新生成按钮可见性） */
  isAuthor: boolean;
}

/** 置信度标签配置：文案 + 样式 */
const CONFIDENCE_CONFIG: Record<
  AIConfidence,
  { label: string; className: string }
> = {
  high: { label: "高置信度", className: "bg-green-50 text-green-700" },
  medium: { label: "中置信度", className: "bg-yellow-50 text-yellow-700" },
  low: { label: "低置信度", className: "bg-red-50 text-red-700" },
};

/** 来源类型标签 */
const SOURCE_TYPE_LABELS: Record<AnswerSource["type"], string> = {
  forum: "站内帖子",
  docs: "文档",
  blog: "博客",
  issue: "Issue",
};

/** 截断文本到指定长度 */
function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "…";
}

/** 从 URL 提取域名 */
function extractDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export function AIAnswer({ postId, initialAIAnswer, isAuthor }: AIAnswerProps) {
  const { aiAnswer, isStreaming, error, reconnect } = useAIAnswerStream({
    postId,
    initialAIAnswer,
  });
  const [regenerating, setRegenerating] = useState(false);

  // 无 AI 答案时不渲染
  if (!aiAnswer) return null;

  const isGenerating = aiAnswer.status === "generating" || isStreaming;
  const confidenceConfig =
    CONFIDENCE_CONFIG[aiAnswer.confidence] ?? CONFIDENCE_CONFIG.medium;

  /** 重新生成 AI 答案 */
  async function handleRegenerate() {
    setRegenerating(true);
    try {
      await regenerateAIAnswer(postId);
      reconnect();
    } catch (err) {
      // 重新生成请求失败时，保留原答案，仅提示错误
      if (err instanceof ApiRequestError && err.status === 401) {
        // 未登录或 token 过期，交由上层处理
      }
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <section
      className="rounded-lg border border-aidev-info/30 bg-aidev-info-bg p-5 shadow-sm"
      aria-label="AI 答案"
    >
      <style jsx>{`
        @keyframes ai-blink {
          0%,
          100% {
            opacity: 1;
          }
          50% {
            opacity: 0;
          }
        }
        .ai-cursor {
          animation: ai-blink 1s step-end infinite;
        }
      `}</style>

      {/* 标题栏 */}
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {isGenerating ? (
            <>
              {/* 脉冲点动画 */}
              <span className="flex items-center gap-1" aria-hidden="true">
                <span
                  className="h-2 w-2 animate-pulse rounded-full bg-aidev-info"
                  style={{ animationDelay: "0ms" }}
                />
                <span
                  className="h-2 w-2 animate-pulse rounded-full bg-aidev-info"
                  style={{ animationDelay: "150ms" }}
                />
                <span
                  className="h-2 w-2 animate-pulse rounded-full bg-aidev-info"
                  style={{ animationDelay: "300ms" }}
                />
              </span>
              <h2 className="text-title text-aidev-foreground">AI 正在生成答案…</h2>
            </>
          ) : (
            <>
              <span className="text-base" aria-hidden="true">
                🤖
              </span>
              <h2 className="text-title text-aidev-foreground">AI 答案</h2>
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  confidenceConfig.className
                )}
              >
                {confidenceConfig.label}
              </span>
            </>
          )}
        </div>

        {/* 重新生成按钮：仅作者可见 */}
        {isAuthor && (
          <button
            type="button"
            disabled={isGenerating || regenerating}
            onClick={handleRegenerate}
            className="inline-flex items-center gap-1 rounded-md border border-aidev-border bg-aidev-card px-3 py-1.5 text-sm text-aidev-foreground transition hover:bg-aidev-muted disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-aidev-ring"
            aria-label="重新生成 AI 答案"
          >
            {regenerating ? "生成中…" : "重新生成"}
          </button>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-3 rounded-md border border-aidev-error/30 bg-aidev-error-bg px-4 py-2.5 text-sm text-aidev-error">
          <p>{error}</p>
          {isAuthor && !isGenerating && (
            <button
              type="button"
              onClick={handleRegenerate}
              disabled={regenerating}
              className="mt-1.5 text-xs font-medium text-aidev-error underline hover:no-underline disabled:opacity-50"
            >
              重新生成
            </button>
          )}
        </div>
      )}

      {/* 低置信度风险提示横幅 */}
      {!isGenerating &&
        aiAnswer.confidence === "low" &&
        aiAnswer.status === "published" && (
          <div className="mb-3 rounded-md border border-orange-200 bg-orange-50 px-4 py-2.5 text-sm text-orange-800">
            ⚠ 本答案未检索到权威来源，由 AI 基于通识生成，可能存在偏差，请社区核实。
          </div>
        )}

      {/* 答案内容 */}
      {isGenerating && !aiAnswer.content ? (
        // 生成中且尚未收到任何 token：显示等待提示
        <p className="py-4 text-caption text-aidev-muted-foreground">
          正在分析问题并检索相关资料…
        </p>
      ) : (
        <div className="min-w-0">
          <MarkdownRenderer content={aiAnswer.content} className="text-body" />
          {/* 流式生成时末尾显示闪烁光标 */}
          {isGenerating && (
            <span
              className="ai-cursor ml-0.5 inline-block font-mono text-aidev-info"
              aria-hidden="true"
            >
              ▋
            </span>
          )}
        </div>
      )}

      {/* 来源标注卡片 */}
      {!isGenerating &&
        aiAnswer.status === "published" &&
        aiAnswer.sources.length > 0 && (
          <div className="mt-5 border-t border-aidev-border pt-4">
            <p className="mb-2 text-caption font-medium text-aidev-foreground">
              参考来源（{aiAnswer.sources.length}）
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {aiAnswer.sources.map((source, idx) => (
                <SourceCard key={`${source.url}-${idx}`} source={source} />
              ))}
            </div>
          </div>
        )}

      {/* 底部：模型名 + 生成时间 */}
      {!isGenerating && aiAnswer.status === "published" && aiAnswer.modelName && (
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-aidev-border pt-3 text-caption text-aidev-muted-foreground">
          <span>模型：{aiAnswer.modelName}</span>
          <span aria-hidden="true">·</span>
          <time dateTime={aiAnswer.updatedAt}>
            生成于 {formatDateTime(aiAnswer.updatedAt)}
          </time>
        </div>
      )}
    </section>
  );
}

/* ======================== 来源卡片子组件 ======================== */

interface SourceCardProps {
  source: AnswerSource;
}

/** 单个来源标注卡片 */
function SourceCard({ source }: SourceCardProps) {
  const snippet = truncate(source.snippet, 150);
  const isForum = source.type === "forum" && source.postId;

  // 站内帖子：内链跳转；外部来源：新标签页打开
  const href = isForum ? `/posts/${source.postId}` : source.url;
  const isExternal = !isForum;

  return (
    <Link
      href={href}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer" : undefined}
      className="block rounded-md border border-aidev-border bg-aidev-card p-3 transition hover:border-aidev-primary-300 hover:shadow-sm"
    >
      <div className="mb-1 flex items-center gap-2">
        <span
          className={cn(
            "inline-flex shrink-0 items-center rounded px-1.5 py-0.5 text-[10px] font-medium",
            isForum
              ? "bg-aidev-primary-50 text-aidev-primary-700"
              : "bg-aidev-muted text-aidev-muted-foreground"
          )}
        >
          {SOURCE_TYPE_LABELS[source.type]}
        </span>
        <span className="min-w-0 truncate text-sm font-medium text-aidev-foreground">
          {source.title}
        </span>
      </div>
      {snippet && (
        <p className="line-clamp-2 text-caption text-aidev-muted-foreground">
          {snippet}
        </p>
      )}
      {isExternal && (
        <p className="mt-1 truncate text-[10px] text-aidev-muted-foreground">
          {extractDomain(source.url)}
        </p>
      )}
    </Link>
  );
}
