"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";

type Leader = { id: string; username: string; avatar: string | null; reputation: number; level: number; windowScore?: number };

export default function LeaderboardPage() {
  const [windowName, setWindowName] = useState<"week" | "month" | "all">("week");
  const [items, setItems] = useState<Leader[]>([]);
  const load = useCallback(() => apiGet<{ items: Leader[] }>("/api/reputation/leaderboard", { window: windowName }).then((data) => setItems(data.items)), [windowName]);
  useEffect(() => { load(); }, [load]);
  return <div className="mx-auto max-w-2xl space-y-5"><h1 className="text-headline">声望排行榜</h1><div className="flex gap-2">{([['week','周榜'],['month','月榜'],['all','总榜']] as const).map(([value, label]) => <button key={value} onClick={() => setWindowName(value)} className={`rounded-full px-3 py-1 text-sm ${windowName === value ? 'bg-aidev-primary text-white' : 'bg-aidev-muted'}`}>{label}</button>)}</div><ol className="overflow-hidden rounded-lg border border-aidev-border bg-aidev-card">{items.map((item, index) => <li key={item.id} className="flex items-center gap-4 border-b border-aidev-border p-4 last:border-0"><strong className="w-8 text-center text-lg">{index + 1}</strong><Link href={`/users/${item.username}`} className="min-w-0 flex-1 font-medium text-aidev-primary">{item.username}</Link><span className="text-sm text-aidev-muted-foreground">Lv{item.level}</span><span className="w-24 text-right font-semibold">{windowName === 'all' ? item.reputation : item.windowScore || 0} 声望</span></li>)}</ol></div>;
}
