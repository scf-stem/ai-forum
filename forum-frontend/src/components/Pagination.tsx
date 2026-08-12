"use client";

import { cn } from "@/lib/utils";

/**
 * 分页组件：展示页码与上一页/下一页按钮。
 * 自动计算可见页码范围，当前页高亮。
 */
interface PaginationProps {
  /** 当前页码（从 1 开始） */
  page: number;
  /** 每页条数 */
  pageSize: number;
  /** 总条数 */
  total: number;
  /** 页码变更回调 */
  onChange: (page: number) => void;
}

/** 计算可见页码列表：当前页附近 ±2，始终包含首末页 */
function getPageRange(current: number, totalPages: number): (number | "...")[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | "...")[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(totalPages - 1, current + 1);

  if (start > 2) pages.push("...");
  for (let i = start; i <= end; i++) pages.push(i);
  if (end < totalPages - 1) pages.push("...");

  pages.push(totalPages);
  return pages;
}

export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;

  const pages = getPageRange(page, totalPages);
  const hasPrev = page > 1;
  const hasNext = page < totalPages;

  const baseBtn =
    "inline-flex h-9 min-w-9 items-center justify-center rounded-md px-3 text-sm transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-aidev-ring";
  const idleBtn =
    "text-aidev-foreground hover:bg-aidev-muted disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent";
  const activeBtn = "bg-aidev-primary text-aidev-primary-foreground font-semibold";

  return (
    <nav aria-label="分页" className="flex items-center gap-1">
      {/* 上一页 */}
      <button
        type="button"
        className={cn(baseBtn, idleBtn)}
        onClick={() => hasPrev && onChange(page - 1)}
        disabled={!hasPrev}
        aria-label="上一页"
      >
        ‹
      </button>

      {/* 页码 */}
      {pages.map((p, idx) =>
        p === "..." ? (
          <span key={`ellipsis-${idx}`} className="px-2 text-aidev-muted-foreground" aria-hidden="true">
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            className={cn(baseBtn, p === page ? activeBtn : idleBtn)}
            onClick={() => onChange(p)}
            aria-label={`第 ${p} 页`}
            aria-current={p === page ? "page" : undefined}
          >
            {p}
          </button>
        )
      )}

      {/* 下一页 */}
      <button
        type="button"
        className={cn(baseBtn, idleBtn)}
        onClick={() => hasNext && onChange(page + 1)}
        disabled={!hasNext}
        aria-label="下一页"
      >
        ›
      </button>
    </nav>
  );
}
