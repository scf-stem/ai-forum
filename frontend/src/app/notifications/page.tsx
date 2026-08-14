"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Notification, PaginatedResponse } from "@/lib/types";
import { formatRelativeTime } from "@/lib/utils";
import { LoadingSpinner } from "@/components/LoadingSpinner";

const FILTERS = ["all", "reply", "upvote", "accepted", "reward", "reputation", "system"] as const;

export default function NotificationsPage() {
  const router = useRouter();
  const { token, loading: authLoading } = useAuth();
  const [type, setType] = useState<(typeof FILTERS)[number]>("all");
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiGet<PaginatedResponse<Notification>>("/api/notifications", {
        type: type === "all" ? undefined : type,
        page: 1,
        page_size: 100,
      });
      setItems(data.items);
    } finally {
      setLoading(false);
    }
  }, [type]);

  useEffect(() => {
    if (!authLoading && !token) router.replace("/auth?mode=login&redirect=/notifications");
    if (token) load();
  }, [authLoading, token, router, load]);

  async function markRead(item: Notification) {
    if (!item.readAt) {
      await apiPatch(`/api/notifications/${item.id}/read`);
      setItems((current) => current.map((value) => value.id === item.id
        ? { ...value, readAt: new Date().toISOString() } : value));
    }
  }

  async function markAll() {
    await apiPost("/api/notifications/read-all");
    setItems((current) => current.map((item) => ({ ...item, readAt: item.readAt || new Date().toISOString() })));
  }

  if (authLoading || (loading && items.length === 0)) {
    return <div className="flex min-h-[360px] items-center justify-center"><LoadingSpinner size={30} /></div>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-headline text-aidev-foreground">通知</h1>
        <button type="button" onClick={markAll} className="text-sm font-medium text-aidev-primary hover:underline">全部标为已读</button>
      </div>
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((value) => (
          <button key={value} type="button" onClick={() => setType(value)}
            className={`rounded-full px-3 py-1 text-xs ${type === value ? "bg-aidev-primary text-white" : "bg-aidev-muted text-aidev-muted-foreground"}`}>
            {value === "all" ? "全部" : value}
          </button>
        ))}
      </div>
      <div className="divide-y divide-aidev-border overflow-hidden rounded-lg border border-aidev-border bg-aidev-card">
        {items.length === 0 ? <p className="p-10 text-center text-aidev-muted-foreground">暂无通知</p> : items.map((item) => (
          <Link key={item.id} href={item.postId ? `/posts/${item.postId}` : "#"} onClick={() => markRead(item)}
            className={`block p-4 transition hover:bg-aidev-muted ${item.readAt ? "opacity-70" : "border-l-4 border-l-aidev-primary"}`}>
            <div className="flex items-start justify-between gap-4">
              <div><p className="font-medium text-aidev-foreground">{item.title}</p>{item.body && <p className="mt-1 text-sm text-aidev-muted-foreground">{item.body}</p>}</div>
              <time className="shrink-0 text-xs text-aidev-muted-foreground">{formatRelativeTime(item.createdAt)}</time>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
