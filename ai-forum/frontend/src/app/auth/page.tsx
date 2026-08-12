"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiPost, ApiRequestError } from "@/lib/api";
import type { AuthResponse, UserRole } from "@/lib/types";
import {
  cn,
  isValidEmail,
  isValidPassword,
  isValidUsername,
} from "@/lib/utils";
import { LoadingSpinner } from "@/components/LoadingSpinner";

/**
 * 登录/注册页：通过 URL search param ?mode=login|register 切换模式。
 * 居中卡片布局，最大宽度 480px。
 */

/** 技术栈标签池 */
const TECH_STACK_OPTIONS = [
  "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java",
  "LLM", "RAG", "Agent", "向量数据库", "LangChain", "LlamaIndex",
  "FastAPI", "Next.js",
];

function AuthContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  // 初始模式：默认登录
  const initialMode = searchParams.get("mode") === "register" ? "register" : "login";
  const redirect = searchParams.get("redirect") || "/";

  const [mode, setMode] = useState<"login" | "register">(initialMode);

  // 表单字段
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("developer");
  const [techStack, setTechStack] = useState<string[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  /** 切换技术栈标签选中状态 */
  function toggleTechStack(tag: string) {
    setTechStack((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  /** 表单校验：返回错误信息，无错误返回 null */
  function validate(): string | null {
    if (!isValidEmail(email)) return "请输入有效的邮箱地址";
    if (!isValidPassword(password))
      return "密码至少 8 位，且需包含字母与数字";
    if (mode === "register" && !isValidUsername(username))
      return "用户名需 2-50 个字符";
    return null;
  }

  /** 提交登录 */
  async function handleLogin() {
    const data = await apiPost<AuthResponse>("/api/auth/login", { email, password });
    await login(data.accessToken, data.user);
    router.push(redirect);
  }

  /** 提交注册 */
  async function handleRegister() {
    const data = await apiPost<AuthResponse>("/api/auth/register", {
      email,
      username,
      password,
      role,
      tech_stack: techStack,
    });
    await login(data.accessToken, data.user);
    router.push("/");
  }

  /** 表单提交 */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      if (mode === "login") {
        await handleLogin();
      } else {
        await handleRegister();
      }
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError("操作失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-200px)] max-w-md flex-col justify-center py-8">
      <div className="rounded-lg border border-aidev-border bg-aidev-card p-6 shadow-md sm:p-8">
        {/* 模式切换 Tab */}
        <div className="mb-6 flex gap-1 rounded-md bg-aidev-muted p-1" role="tablist">
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              type="button"
              role="tab"
              aria-selected={mode === m}
              className={cn(
                "flex-1 rounded-md px-4 py-2 text-sm font-medium transition",
                mode === m
                  ? "bg-aidev-card text-aidev-foreground shadow-sm"
                  : "text-aidev-muted-foreground hover:text-aidev-foreground"
              )}
              onClick={() => {
                setMode(m);
                setError(null);
              }}
            >
              {m === "login" ? "登录" : "注册"}
            </button>
          ))}
        </div>

        <h1 className="mb-1 text-headline text-aidev-foreground">
          {mode === "login" ? "欢迎回来" : "加入社区"}
        </h1>
        <p className="mb-6 text-caption text-aidev-muted-foreground">
          {mode === "login"
            ? "登录后参与讨论与投票"
            : "注册后即可发帖、回复与投票"}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 邮箱 */}
          <div>
            <label htmlFor="auth-email" className="mb-1 block text-caption font-medium text-aidev-foreground">
              邮箱
            </label>
            <input
              id="auth-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
              placeholder="you@example.com"
              required
            />
          </div>

          {/* 用户名（仅注册） */}
          {mode === "register" && (
            <div>
              <label htmlFor="auth-username" className="mb-1 block text-caption font-medium text-aidev-foreground">
                用户名
              </label>
              <input
                id="auth-username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
                placeholder="2-50 个字符"
                required
              />
            </div>
          )}

          {/* 密码 */}
          <div>
            <label htmlFor="auth-password" className="mb-1 block text-caption font-medium text-aidev-foreground">
              密码
            </label>
            <input
              id="auth-password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
              placeholder="至少 8 位，含字母与数字"
              required
            />
          </div>

          {/* 角色选择（仅注册） */}
          {mode === "register" && (
            <div>
              <label className="mb-1 block text-caption font-medium text-aidev-foreground">
                角色
              </label>
              <div className="grid grid-cols-2 gap-2">
                {([
                  { value: "developer", label: "开发者", desc: "有 AI 开发经验" },
                  { value: "beginner", label: "零基础", desc: "正在学习 AI" },
                ] as const).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    className={cn(
                      "rounded-md border px-3 py-2 text-left transition",
                      role === opt.value
                        ? "border-aidev-primary bg-aidev-primary-50"
                        : "border-aidev-input hover:border-aidev-primary-300"
                    )}
                    onClick={() => setRole(opt.value)}
                    aria-pressed={role === opt.value}
                  >
                    <span className="block text-sm font-medium text-aidev-foreground">
                      {opt.label}
                    </span>
                    <span className="block text-xs text-aidev-muted-foreground">
                      {opt.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 技术栈（仅注册） */}
          {mode === "register" && (
            <div>
              <label className="mb-1.5 block text-caption font-medium text-aidev-foreground">
                技术栈 <span className="text-aidev-muted-foreground">（可选，多选）</span>
              </label>
              <div className="flex flex-wrap gap-1.5">
                {TECH_STACK_OPTIONS.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    className={cn(
                      "rounded-full px-3 py-1 text-xs font-medium transition",
                      techStack.includes(tag)
                        ? "bg-aidev-primary text-aidev-primary-foreground"
                        : "bg-aidev-muted text-aidev-muted-foreground hover:bg-aidev-primary-100 hover:text-aidev-primary-700"
                    )}
                    onClick={() => toggleTechStack(tag)}
                    aria-pressed={techStack.includes(tag)}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 错误提示 */}
          {error && (
            <p role="alert" className="rounded-md bg-aidev-state-error-bg px-3 py-2 text-caption text-aidev-error">
              {error}
            </p>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-aidev-primary px-4 py-2.5 text-body font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90 disabled:opacity-50"
          >
            {loading && <LoadingSpinner size={16} />}
            {loading
              ? mode === "login" ? "登录中…" : "注册中…"
              : mode === "login" ? "登录" : "注册"
            }
          </button>
        </form>

        {/* 底部切换链接 */}
        <p className="mt-4 text-center text-caption text-aidev-muted-foreground">
          {mode === "login" ? (
            <>
              还没有账号？{" "}
              <button
                type="button"
                className="font-medium text-aidev-primary hover:underline"
                onClick={() => {
                  setMode("register");
                  setError(null);
                }}
              >
                去注册
              </button>
            </>
          ) : (
            <>
              已有账号？{" "}
              <button
                type="button"
                className="font-medium text-aidev-primary hover:underline"
                onClick={() => {
                  setMode("login");
                  setError(null);
                }}
              >
                去登录
              </button>
            </>
          )}
        </p>
      </div>

      {/* 返回首页 */}
      <p className="mt-4 text-center text-caption text-aidev-muted-foreground">
        <Link href="/" className="hover:text-aidev-primary">← 返回首页</Link>
      </p>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[400px] items-center justify-center">
          <LoadingSpinner size={32} />
        </div>
      }
    >
      <AuthContent />
    </Suspense>
  );
}
