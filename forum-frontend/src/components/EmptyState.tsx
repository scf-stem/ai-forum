import type { ReactNode } from "react";

/**
 * 空状态占位：展示提示信息与可选的操作按钮。
 */
interface EmptyStateProps {
  /** 提示文案 */
  message: string;
  /** 可选操作（如"去发帖"按钮） */
  action?: ReactNode;
  /** 图标（可选，默认展示空圆圈） */
  icon?: ReactNode;
}

export function EmptyState({ message, action, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-aidev-border bg-aidev-card px-6 py-16 text-center">
      <div aria-hidden="true" className="text-aidev-muted-foreground">
        {icon ?? (
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M8 12h8" strokeLinecap="round" />
          </svg>
        )}
      </div>
      <p className="text-body text-aidev-muted-foreground">{message}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
