"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiPost, ApiRequestError } from "@/lib/api";
import type { AuthResponse } from "@/lib/types";
import { isValidEmail } from "@/lib/utils";
import { LoadingSpinner } from "./LoadingSpinner";

/**
 * 登录浮层：模态对话框，可从任意页面触发。
 * 登录成功后调用 AuthContext.login 持久化状态。
 */
interface LoginModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function LoginModal({ open, onClose, onSuccess }: LoginModalProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  // ESC 键关闭
  useEffect(() => {
    if (!open) return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [open, onClose]);

  // 打开时聚焦邮箱输入框
  useEffect(() => {
    if (open) {
      setError(null);
      // 延迟聚焦，等待 DOM 渲染
      const timer = setTimeout(() => {
        dialogRef.current?.querySelector<HTMLInputElement>("input[type=email]")?.focus();
      }, 50);
      return () => clearTimeout(timer);
    }
  }, [open]);

  // 锁定背景滚动
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [open]);

  if (!open) return null;

  /** 提交登录表单 */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // 前端校验
    if (!isValidEmail(email)) {
      setError("请输入有效的邮箱地址");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }

    setLoading(true);
    try {
      const data = await apiPost<AuthResponse>("/api/auth/login", {
        email,
        password,
      });
      await login(data.accessToken, data.user);
      onClose();
      onSuccess?.();
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError("登录失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="login-modal-title"
    >
      {/* 遮罩层 */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* 对话框内容 */}
      <div
        ref={dialogRef}
        className="relative w-full max-w-sm rounded-lg bg-aidev-card p-6 shadow-lg"
      >
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 text-aidev-muted-foreground transition hover:text-aidev-foreground"
          aria-label="关闭"
        >
          ✕
        </button>

        <h2 id="login-modal-title" className="mb-1 text-headline text-aidev-foreground">
          登录
        </h2>
        <p className="mb-6 text-caption text-aidev-muted-foreground">
          登录后参与讨论与投票
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="login-email" className="mb-1 block text-caption font-medium text-aidev-foreground">
              邮箱
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
              placeholder="you@example.com"
              required
            />
          </div>

          <div>
            <label htmlFor="login-password" className="mb-1 block text-caption font-medium text-aidev-foreground">
              密码
            </label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <p role="alert" className="rounded-md bg-aidev-state-error-bg px-3 py-2 text-caption text-aidev-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-aidev-primary px-4 py-2.5 text-body font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90 disabled:opacity-50"
          >
            {loading && <LoadingSpinner size={16} />}
            {loading ? "登录中…" : "登录"}
          </button>
        </form>

        <p className="mt-4 text-center text-caption text-aidev-muted-foreground">
          还没有账号？{" "}
          <Link
            href="/auth?mode=register"
            className="font-medium text-aidev-primary hover:underline"
            onClick={onClose}
          >
            去注册
          </Link>
        </p>
      </div>
    </div>
  );
}
