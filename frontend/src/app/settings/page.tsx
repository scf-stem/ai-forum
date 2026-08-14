"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiGet, apiPatch, ApiRequestError } from "@/lib/api";
import type { User } from "@/lib/types";
import { cn, getAvatarColor, getInitials } from "@/lib/utils";
import { LoadingSpinner } from "@/components/LoadingSpinner";

/**
 * 设置页：编辑头像 URL、简介、技术栈标签。
 * 调用 PATCH /api/users/me 保存。
 */

/** 技术栈标签池 */
const TECH_STACK_OPTIONS = [
  "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java",
  "LLM", "RAG", "Agent", "向量数据库", "LangChain", "LlamaIndex",
  "FastAPI", "Next.js",
];

export default function SettingsPage() {
  const router = useRouter();
  const { currentUser, token, loading: authLoading, updateUser } = useAuth();

  const [avatar, setAvatar] = useState("");
  const [bio, setBio] = useState("");
  const [techStack, setTechStack] = useState<string[]>([]);
  const [personalization, setPersonalization] = useState(true);
  const [notificationPrefs, setNotificationPrefs] = useState<Record<string, boolean>>({
    replyEnabled: true, upvoteEnabled: true, acceptedEnabled: true,
    rewardEnabled: true, reputationEnabled: true, systemEnabled: true,
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // 未登录跳转登录页
  useEffect(() => {
    if (!authLoading && !token) {
      router.replace("/auth?mode=login&redirect=/settings");
    }
  }, [authLoading, token, router]);

  // 从当前用户信息填充表单
  useEffect(() => {
    if (currentUser) {
      setAvatar(currentUser.avatar || "");
      setBio(currentUser.bio || "");
      setTechStack(currentUser.techStack || []);
      setPersonalization(currentUser.personalizationEnabled ?? true);
      apiGet<Record<string, boolean>>("/api/notification-preferences")
        .then(setNotificationPrefs).catch(() => undefined);
    }
  }, [currentUser]);

  /** 切换技术栈标签 */
  function toggleTechStack(tag: string) {
    setTechStack((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }

  /** 保存设置 */
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setSaving(true);

    try {
      const data = await apiPatch<User>("/api/users/me", {
        avatar: avatar.trim() || null,
        bio: bio.trim() || null,
        tech_stack: techStack,
        personalization_enabled: personalization,
      });
      await apiPatch("/api/notification-preferences", Object.fromEntries(
        Object.entries(notificationPrefs).map(([key, value]) => [key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`), value])
      ));
      updateUser(data);
      setSuccess(true);
      // 3 秒后清除成功提示
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(
        err instanceof ApiRequestError ? err.message : "保存失败，请稍后重试"
      );
    } finally {
      setSaving(false);
    }
  }

  // 等待认证状态加载
  if (authLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (!token || !currentUser) return null;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-headline text-aidev-foreground">设置</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 头像预览 + URL 输入 */}
        <div>
          <label className="mb-2 block text-caption font-medium text-aidev-foreground">
            头像
          </label>
          <div className="flex items-center gap-4">
            {/* 预览 */}
            {avatar ? (
              <img
                src={avatar}
                alt="头像预览"
                className="h-16 w-16 rounded-full object-cover border border-aidev-border"
              />
            ) : (
              <span
                className="inline-flex h-16 w-16 items-center justify-center rounded-full text-xl font-bold text-white"
                style={{ backgroundColor: getAvatarColor(currentUser.username) }}
              >
                {getInitials(currentUser.username)}
              </span>
            )}
            <input
              type="url"
              value={avatar}
              onChange={(e) => setAvatar(e.target.value)}
              className="flex-1 rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
              placeholder="输入头像图片 URL"
            />
          </div>
        </div>

        {/* 简介 */}
        <div>
          <label htmlFor="settings-bio" className="mb-1 block text-caption font-medium text-aidev-foreground">
            简介
          </label>
          <textarea
            id="settings-bio"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            rows={3}
            maxLength={200}
            className="w-full resize-y rounded-md border border-aidev-input bg-aidev-card px-3 py-2 text-body text-aidev-foreground outline-none transition focus:border-aidev-primary"
            placeholder="一句话介绍自己"
          />
          <p className="mt-1 text-right text-xs text-aidev-muted-foreground">
            {bio.length}/200
          </p>
        </div>

        {/* 技术栈 */}
        <div>
          <label className="mb-1.5 block text-caption font-medium text-aidev-foreground">
            技术栈
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

        {/* 错误提示 */}
        <div className="space-y-3 rounded-lg border border-aidev-border p-4">
          <label className="flex items-center justify-between gap-4 text-sm font-medium text-aidev-foreground">
            <span>个性化推荐 <small className="block font-normal text-aidev-muted-foreground">关闭后只展示全站热度，行为不进入个性画像</small></span>
            <input type="checkbox" checked={personalization} onChange={(event) => setPersonalization(event.target.checked)} className="h-4 w-4" />
          </label>
          <div className="border-t border-aidev-border pt-3">
            <p className="mb-2 text-sm font-medium text-aidev-foreground">站内通知</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(notificationPrefs).map(([key, enabled]) => (
                <label key={key} className="flex items-center gap-2 text-sm text-aidev-muted-foreground">
                  <input type="checkbox" checked={enabled} onChange={(event) => setNotificationPrefs((current) => ({ ...current, [key]: event.target.checked }))} />
                  {{ replyEnabled: "回复", upvoteEnabled: "点赞", acceptedEnabled: "采纳", rewardEnabled: "打赏", reputationEnabled: "声望", systemEnabled: "系统" }[key] || key}
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <p role="alert" className="rounded-md bg-aidev-state-error-bg px-3 py-2 text-caption text-aidev-error">
            {error}
          </p>
        )}

        {/* 成功提示 */}
        {success && (
          <p role="status" className="rounded-md bg-aidev-state-success-bg px-3 py-2 text-caption text-aidev-success">
            保存成功
          </p>
        )}

        {/* 保存按钮 */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-aidev-primary px-6 py-2 text-sm font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90 disabled:opacity-50"
          >
            {saving && <LoadingSpinner size={16} />}
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </form>
    </div>
  );
}
