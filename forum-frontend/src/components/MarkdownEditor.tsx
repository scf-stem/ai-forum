"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { MarkdownRenderer } from "./MarkdownRenderer";

/**
 * 简化版 Markdown 编辑器：textarea + 写作/预览切换。
 * 用于发帖页与回帖输入。
 */
interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder = "支持 Markdown 语法…",
  rows = 6,
  className,
}: MarkdownEditorProps) {
  const [mode, setMode] = useState<"write" | "preview">("write");

  return (
    <div className={cn("rounded-md border border-aidev-input bg-aidev-card overflow-hidden", className)}>
      {/* 工具栏：写作/预览切换 */}
      <div className="flex items-center gap-1 border-b border-aidev-border bg-aidev-muted px-2 py-1">
        {(["write", "preview"] as const).map((m) => (
          <button
            key={m}
            type="button"
            className={cn(
              "rounded px-2.5 py-1 text-xs font-medium transition",
              mode === m
                ? "bg-aidev-card text-aidev-foreground shadow-sm"
                : "text-aidev-muted-foreground hover:text-aidev-foreground"
            )}
            onClick={() => setMode(m)}
            aria-pressed={mode === m}
          >
            {m === "write" ? "写作" : "预览"}
          </button>
        ))}
        <span className="ml-auto text-xs text-aidev-muted-foreground" aria-hidden="true">
          Markdown
        </span>
      </div>

      {mode === "write" ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          rows={rows}
          className="w-full resize-y bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none placeholder:text-aidev-muted-foreground"
          aria-label="Markdown 编辑器"
        />
      ) : (
        <div className="min-h-[120px] px-3 py-2">
          {value.trim() ? (
            <MarkdownRenderer content={value} />
          ) : (
            <p className="text-body text-aidev-muted-foreground">暂无内容可预览</p>
          )}
        </div>
      )}
    </div>
  );
}
