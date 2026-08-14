import Link from "next/link";
import { PostFeed } from "@/components/PostFeed";

// 首页始终动态渲染，确保帖子列表实时更新
export const dynamic = "force-dynamic";

/**
 * 首页：Server Component 获取首屏帖子列表（SSR），
 * 交由 PostFeed 客户端组件处理排序切换与分页。
 */
export default async function Home() {
  return (
    <div className="space-y-6">
      {/* 欢迎标语 */}
      <section className="rounded-lg border border-aidev-border bg-gradient-to-br from-aidev-primary-50 to-aidev-card p-6 sm:p-8">
        <h1 className="text-display text-aidev-foreground">AI开发者论坛</h1>
        <p className="mt-2 max-w-2xl text-body text-aidev-muted-foreground">
          面向 AI 开发者的技术交流与互助社区。在这里提问、分享、成长。
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/ask"
            className="inline-flex items-center rounded-md bg-aidev-primary px-4 py-2 text-sm font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90"
          >
            发起提问
          </Link>
          <Link
            href="/auth?mode=register"
            className="inline-flex items-center rounded-md border border-aidev-border bg-aidev-card px-4 py-2 text-sm font-medium text-aidev-foreground transition hover:bg-aidev-muted"
          >
            加入社区
          </Link>
        </div>
      </section>

      {/* 帖子列表 */}
      <PostFeed apiPath="/api/feed" feedModes emptyMessage="还没有内容，成为第一个发帖的人" />
    </div>
  );
}
