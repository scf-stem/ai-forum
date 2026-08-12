import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "AI开发者论坛",
  description: "面向 AI 开发者的技术交流与互助社区",
};

/**
 * 根布局：注入品牌设计 Token 并挂载认证状态上下文。
 * 全站所有页面共享此布局：顶部固定 Header + 居中内容区。
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="font-sans antialiased">
        {/* 认证上下文 Provider：管理全局 currentUser 与 token */}
        <AuthProvider>
          <Header />
          <main className="mx-auto max-w-content px-4 py-6">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
