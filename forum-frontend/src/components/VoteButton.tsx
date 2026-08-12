"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiPost, ApiRequestError } from "@/lib/api";
import type { VoteDirection } from "@/lib/types";
import { cn, formatCount } from "@/lib/utils";
import { LoginModal } from "./LoginModal";

/**
 * 投票组件：支持帖子与回复的赞/踩。
 * - 未登录点击弹出 LoginModal
 * - 已登录点击调用 POST /api/vote，处理切换/取消逻辑
 * - 乐观更新：先更新 UI，失败回退
 */
interface VoteButtonProps {
  targetType: "post" | "reply";
  targetId: string;
  initialVote: VoteDirection | null;
  initialCount: number;
  /** 紧凑模式：竖排（用于帖子侧栏） */
  vertical?: boolean;
}

/** 投票响应结构（响应已被 api.ts 转换为 camelCase） */
interface VoteApiResponse {
  detail: string;
  voteCount: number;
  direction: VoteDirection | null;
}

export function VoteButton({
  targetType,
  targetId,
  initialVote,
  initialCount,
  vertical = false,
}: VoteButtonProps) {
  const { token } = useAuth();
  const [vote, setVote] = useState<VoteDirection | null>(initialVote);
  const [count, setCount] = useState(initialCount);
  const [showLogin, setShowLogin] = useState(false);
  const [loading, setLoading] = useState(false);

  /**
   * 处理投票点击：
   * - 未投票 → 投 up/down（count +1/-1）
   * - 已投同方向 → 取消（count 反向 ±1，vote → null）
   * - 已投反方向 → 切换（count ±2，vote → 新方向）
   */
  async function handleVote(direction: VoteDirection) {
    // 未登录：弹出登录浮层
    if (!token) {
      setShowLogin(true);
      return;
    }

    // 乐观更新：先计算新状态
    const prevVote = vote;
    const prevCount = count;
    let newVote: VoteDirection | null;
    let newCount: number;

    if (prevVote === direction) {
      // 取消投票
      newVote = null;
      newCount = prevCount + (direction === "up" ? -1 : 1);
    } else if (prevVote === null) {
      // 新增投票
      newVote = direction;
      newCount = prevCount + (direction === "up" ? 1 : -1);
    } else {
      // 切换投票方向
      newVote = direction;
      newCount = prevCount + (direction === "up" ? 2 : -2);
    }

    setVote(newVote);
    setCount(newCount);
    setLoading(true);

    try {
      const data = await apiPost<VoteApiResponse>("/api/vote", {
        target_type: targetType,
        target_id: targetId,
        direction,
      });
      // 以服务端返回为准
      setVote(data.direction);
      setCount(data.voteCount);
    } catch (err) {
      // 失败回退
      setVote(prevVote);
      setCount(prevCount);
      if (err instanceof ApiRequestError && err.status === 401) {
        setShowLogin(true);
      }
    } finally {
      setLoading(false);
    }
  }

  const upActive = vote === "up";
  const downActive = vote === "down";

  const btnBase =
    "inline-flex items-center justify-center transition disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-aidev-ring";

  if (vertical) {
    // 竖排：用于帖子详情页侧栏
    return (
      <>
        <div className="flex flex-col items-center gap-1">
          <button
            type="button"
            className={cn(
              btnBase,
              "h-8 w-8 rounded-md text-lg",
              upActive
                ? "bg-orange-50 text-orange-600"
                : "text-aidev-muted-foreground hover:bg-aidev-muted hover:text-aidev-foreground"
            )}
            onClick={() => handleVote("up")}
            disabled={loading}
            aria-label="赞同"
            aria-pressed={upActive}
          >
            ▲
          </button>
          <span
            className="min-w-6 text-center text-sm font-semibold tabular-nums text-aidev-foreground"
            aria-label={`投票数 ${count}`}
          >
            {formatCount(count)}
          </span>
          <button
            type="button"
            className={cn(
              btnBase,
              "h-8 w-8 rounded-md text-lg",
              downActive
                ? "bg-blue-50 text-blue-600"
                : "text-aidev-muted-foreground hover:bg-aidev-muted hover:text-aidev-foreground"
            )}
            onClick={() => handleVote("down")}
            disabled={loading}
            aria-label="反对"
            aria-pressed={downActive}
          >
            ▼
          </button>
        </div>
        <LoginModal open={showLogin} onClose={() => setShowLogin(false)} />
      </>
    );
  }

  // 横排：用于帖子卡片和回复
  return (
    <>
      <div className="inline-flex items-center gap-1">
        <button
          type="button"
          className={cn(
            btnBase,
            "h-7 w-7 rounded-md text-sm",
            upActive
              ? "bg-orange-50 text-orange-600"
              : "text-aidev-muted-foreground hover:bg-aidev-muted hover:text-aidev-foreground"
          )}
          onClick={() => handleVote("up")}
          disabled={loading}
          aria-label="赞同"
          aria-pressed={upActive}
        >
          ▲
        </button>
        <span
          className="min-w-6 text-center text-sm font-medium tabular-nums text-aidev-foreground"
          aria-label={`投票数 ${count}`}
        >
          {formatCount(count)}
        </span>
        <button
          type="button"
          className={cn(
            btnBase,
            "h-7 w-7 rounded-md text-sm",
            downActive
              ? "bg-blue-50 text-blue-600"
              : "text-aidev-muted-foreground hover:bg-aidev-muted hover:text-aidev-foreground"
          )}
          onClick={() => handleVote("down")}
          disabled={loading}
          aria-label="反对"
          aria-pressed={downActive}
        >
          ▼
        </button>
      </div>
      <LoginModal open={showLogin} onClose={() => setShowLogin(false)} />
    </>
  );
}
