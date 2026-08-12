"use client";

import { useMemo } from "react";

/**
 * Markdown 渲染组件。
 * 由于项目未安装 react-markdown / remark-gfm / react-syntax-highlighter，
 * 这里实现一个轻量的 Markdown → HTML 转换器，
 * 支持：标题、粗体、斜体、行内代码、代码块、链接、有序/无序列表、引用、分隔线、段落。
 *
 * 安全策略：所有输入先经过 HTML 转义，再应用 Markdown 语法替换，
 * 避免注入风险。链接仅允许 http/https 协议。
 */

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/** HTML 特殊字符转义 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** 校验 URL 协议：仅允许 http/https/mailto */
function safeUrl(url: string): string {
  const trimmed = url.trim();
  if (/^(https?:|mailto:)/i.test(trimmed)) return trimmed;
  // 相对路径允许
  if (trimmed.startsWith("/") || trimmed.startsWith("#")) return trimmed;
  return "#";
}

/**
 * 将 Markdown 文本转换为安全的 HTML 字符串。
 * 处理顺序：转义 → 提取代码块 → 提取行内代码 → 块级元素 → 行内元素 → 还原代码
 */
function markdownToHtml(md: string): string {
  if (!md.trim()) return "";

  // 1. 转义 HTML
  let text = escapeHtml(md);

  // 2. 提取代码块（```lang ... ```），用占位符替换
  const codeBlocks: string[] = [];
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, lang, code) => {
    const idx = codeBlocks.length;
    const langLabel = lang ? lang.toLowerCase() : "text";
    codeBlocks.push(
      `<pre class="md-code-block" data-lang="${langLabel}"><code>${code.replace(/\n$/, "")}</code></pre>`
    );
    return `\u0000CB${idx}\u0000`;
  });

  // 3. 提取行内代码（`code`）
  const inlineCodes: string[] = [];
  text = text.replace(/`([^`\n]+)`/g, (_match, code) => {
    const idx = inlineCodes.length;
    inlineCodes.push(`<code class="md-code-inline">${code}</code>`);
    return `\u0000IC${idx}\u0000`;
  });

  // 4. 按行处理块级元素
  const lines = text.split("\n");
  const html: string[] = [];
  let listType: "ul" | "ol" | null = null;
  let paragraph: string[] = [];

  /** 将当前段落缓冲区刷新为 <p> */
  const flushParagraph = () => {
    if (paragraph.length > 0) {
      const content = paragraph.join("<br />").trim();
      if (content) html.push(`<p>${content}</p>`);
      paragraph = [];
    }
  };

  /** 关闭当前列表 */
  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  for (const line of lines) {
    // 代码块占位符单独成行
    if (/^\u0000CB\d+\u0000$/.test(line.trim())) {
      flushParagraph();
      closeList();
      html.push(line.trim());
      continue;
    }

    // 空行：结束当前段落/列表
    if (line.trim() === "") {
      flushParagraph();
      closeList();
      continue;
    }

    // 标题（# ~ ######）
    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      closeList();
      const level = headingMatch[1].length;
      html.push(`<h${level}>${headingMatch[2].trim()}</h${level}>`);
      continue;
    }

    // 分隔线（---、***、___）
    if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      flushParagraph();
      closeList();
      html.push("<hr />");
      continue;
    }

    // 引用（> ...）
    if (/^>\s?/.test(line)) {
      flushParagraph();
      closeList();
      const content = line.replace(/^>\s?/, "");
      html.push(`<blockquote>${content}</blockquote>`);
      continue;
    }

    // 无序列表（-、*、+ 开头）
    if (/^[-*+]\s+/.test(line)) {
      flushParagraph();
      if (listType !== "ul") {
        closeList();
        html.push("<ul>");
        listType = "ul";
      }
      html.push(`<li>${line.replace(/^[-*+]\s+/, "")}</li>`);
      continue;
    }

    // 有序列表（数字. 开头）
    if (/^\d+\.\s+/.test(line)) {
      flushParagraph();
      if (listType !== "ol") {
        closeList();
        html.push("<ol>");
        listType = "ol";
      }
      html.push(`<li>${line.replace(/^\d+\.\s+/, "")}</li>`);
      continue;
    }

    // 普通文本行：加入段落缓冲区
    closeList();
    paragraph.push(line);
  }

  flushParagraph();
  closeList();

  let result = html.join("\n");

  // 5. 行内元素替换：粗体、斜体、链接、删除线
  // 粗体 **text** 或 __text__
  result = result.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  result = result.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  // 斜体 *text* 或 _text_
  result = result.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  result = result.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, "$1<em>$2</em>");
  // 删除线 ~~text~~
  result = result.replace(/~~([^~]+)~~/g, "<del>$1</del>");
  // 链接 [text](url)
  result = result.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_m, label, url) => `<a href="${safeUrl(url)}" target="_blank" rel="noopener noreferrer">${label}</a>`
  );

  // 6. 还原代码块和行内代码
  result = result.replace(/\u0000CB(\d+)\u0000/g, (_m, idx) => codeBlocks[Number(idx)] || "");
  result = result.replace(/\u0000IC(\d+)\u0000/g, (_m, idx) => inlineCodes[Number(idx)] || "");

  return result;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  const html = useMemo(() => markdownToHtml(content), [content]);

  return (
    <div className={className}>
      <style jsx>{`
        .md-body {
          font-size: 0.9375rem;
          line-height: 1.75;
          color: var(--aidev-foreground);
          word-break: break-word;
        }
        .md-body > :first-child {
          margin-top: 0;
        }
        .md-body > :last-child {
          margin-bottom: 0;
        }
        .md-body h1,
        .md-body h2,
        .md-body h3,
        .md-body h4,
        .md-body h5,
        .md-body h6 {
          font-weight: 700;
          line-height: 1.3;
          margin: 1.5em 0 0.75em;
        }
        .md-body h1 {
          font-size: 1.5rem;
        }
        .md-body h2 {
          font-size: 1.3rem;
        }
        .md-body h3 {
          font-size: 1.15rem;
        }
        .md-body h4 {
          font-size: 1rem;
        }
        .md-body p {
          margin: 0.75em 0;
        }
        .md-body strong {
          font-weight: 700;
        }
        .md-body em {
          font-style: italic;
        }
        .md-body del {
          text-decoration: line-through;
          opacity: 0.7;
        }
        .md-body a {
          color: var(--aidev-primary-600);
          text-decoration: none;
          border-bottom: 1px solid transparent;
          transition: border-color 0.15s;
        }
        .md-body a:hover {
          border-bottom-color: var(--aidev-primary-600);
        }
        .md-body ul,
        .md-body ol {
          margin: 0.75em 0;
          padding-left: 1.5em;
        }
        .md-body ul {
          list-style: disc;
        }
        .md-body ol {
          list-style: decimal;
        }
        .md-body li {
          margin: 0.25em 0;
        }
        .md-body blockquote {
          margin: 1em 0;
          padding: 0.5em 1em;
          border-left: 3px solid var(--aidev-primary-300);
          background: var(--aidev-muted);
          border-radius: 0 4px 4px 0;
          color: var(--aidev-muted-foreground);
        }
        .md-body hr {
          margin: 1.5em 0;
          border: none;
          border-top: 1px solid var(--aidev-border);
        }
        .md-body .md-code-block {
          margin: 1em 0;
          padding: 1em;
          background: var(--aidev-code-bg);
          color: var(--aidev-code-ink);
          border-radius: 8px;
          overflow-x: auto;
          font-family: var(--aidev-font-mono);
          font-size: 0.85rem;
          line-height: 1.6;
        }
        .md-body .md-code-block code {
          font-family: inherit;
        }
        .md-body .md-code-inline {
          padding: 0.15em 0.4em;
          background: var(--aidev-muted);
          border-radius: 4px;
          font-family: var(--aidev-font-mono);
          font-size: 0.85em;
          color: var(--aidev-primary-700);
        }
      `}</style>
      <div
        className="md-body"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
