"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Board } from "@/lib/types";
import { LoadingSpinner } from "@/components/LoadingSpinner";

type Job = { id: string; type: string; status: string; progress: number; attempts: number; error: string | null };
type Metric = { date: string; metricName: string; value: number; dimensions: Record<string, unknown> };
type CrawlItem = { id: string; sourceTitle: string; canonicalUrl: string; summary: string; tags: string[]; status: string };
type CrawlSource = { id: string; name: string; baseUrl: string; active: boolean };

export default function OpsPage() {
  const router = useRouter();
  const { currentUser, loading: authLoading } = useAuth();
  const [days, setDays] = useState<7 | 30 | 90>(30);
  const [comparisons, setComparisons] = useState<Record<string, { current: number; previous: number; changeRate: number | null }>>({});
  const [jobs, setJobs] = useState<Job[]>([]);
  const [crawlItems, setCrawlItems] = useState<CrawlItem[]>([]);
  const [sources, setSources] = useState<CrawlSource[]>([]);
  const [boards, setBoards] = useState<Board[]>([]);
  const [source, setSource] = useState({ name: "", base_url: "", entry_url: "", terms_url: "", compliance_confirmed: false, rate_limit_seconds: 2, max_pages: 20 });
  const [invites, setInvites] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    const [metricData, jobData, crawlData, boardData, sourceData] = await Promise.all([
      apiGet<{ items: Metric[]; comparisons: Record<string, { current: number; previous: number; changeRate: number | null }> }>("/api/ops/metrics", { days }),
      apiGet<Job[]>("/api/ops/jobs"),
      apiGet<{ items: CrawlItem[] }>("/api/ops/crawl-items", { status: "pending" }),
      apiGet<{ entry: Board[]; deep: Board[] }>("/api/boards"),
      apiGet<CrawlSource[]>("/api/ops/crawl-sources"),
    ]);
    setComparisons(metricData.comparisons); setJobs(jobData); setCrawlItems(crawlData.items);
    setBoards([...boardData.entry, ...boardData.deep]);
    setSources(sourceData);
  }, [days]);

  useEffect(() => {
    if (!authLoading && !currentUser?.isAdmin) router.replace("/");
    if (currentUser?.isAdmin) load().catch(() => setMessage("运营数据加载失败"));
  }, [authLoading, currentUser, router, load]);

  async function createSource(event: React.FormEvent) {
    event.preventDefault();
    await apiPost("/api/ops/crawl-sources", source);
    setMessage("抓取来源已创建"); await load();
  }

  async function review(item: CrawlItem, action: "approve" | "reject") {
    const boardId = action === "approve" ? boards[0]?.id : undefined;
    await apiPatch(`/api/ops/crawl-items/${item.id}/review`, { action, board_id: boardId });
    await load();
  }

  async function importInvites() {
    const rows = invites.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).map((line) => {
      const [email, username, role = "developer", tech = ""] = line.split(",");
      return { email, username, role, tech_stack: tech.split("|").filter(Boolean) };
    });
    const result = await apiPost<{ items: Array<{ email: string; activationUrl: string }> }>("/api/ops/seed-invitations", rows);
    setMessage(`已生成 ${result.items.length} 条一次性激活链接`);
  }

  if (authLoading || !currentUser?.isAdmin) return <div className="flex min-h-[360px] items-center justify-center"><LoadingSpinner size={30} /></div>;

  return (
    <div className="space-y-8">
      <div><h1 className="text-headline text-aidev-foreground">运营后台</h1><p className="mt-1 text-sm text-aidev-muted-foreground">统一查看指标、抓取审核、种子邀请、任务与 AI 评测。</p></div>
      {message && <p className="rounded-md bg-aidev-info-bg p-3 text-sm text-aidev-info">{message}</p>}
      <section><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><h2 className="text-title">核心指标</h2><div className="flex gap-2">{([7,30,90] as const).map((value) => <button key={value} onClick={() => setDays(value)} className={`rounded-full px-3 py-1 text-xs ${days === value ? 'bg-aidev-primary text-white' : 'bg-aidev-muted'}`}>{value} 天</button>)}</div></div><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{["dau", "organic_posts", "seed_posts", "search_documents", "organic_content_share_bp", "human_reply_24h_bp", "high_confidence_helpful_rate_bp", "retention_d7_bp"].map((name) => { const comparison = comparisons[name]; const isRate = name.endsWith('_bp'); return <div key={name} className="rounded-lg border border-aidev-border bg-aidev-card p-4"><p className="text-xs text-aidev-muted-foreground">{name}</p><strong className="mt-2 block text-2xl">{comparison ? (isRate ? `${(comparison.current / 100).toFixed(1)}%` : comparison.current) : "—"}</strong>{comparison?.changeRate != null && <small className={comparison.changeRate >= 0 ? 'text-green-700' : 'text-red-600'}>环比 {comparison.changeRate >= 0 ? '+' : ''}{(comparison.changeRate * 100).toFixed(1)}%</small>}</div>; })}</div></section>
      <section><div className="mb-3 flex items-center justify-between"><h2 className="text-title">后台任务</h2><button onClick={() => apiPost("/api/ops/metrics/rollup", {}).then(load)} className="rounded bg-aidev-primary px-3 py-1.5 text-sm text-white">聚合昨日指标</button></div><div className="overflow-x-auto rounded-lg border border-aidev-border"><table className="w-full text-left text-sm"><thead className="bg-aidev-muted"><tr><th className="p-3">类型</th><th>状态</th><th>进度</th><th>尝试</th><th>操作</th></tr></thead><tbody>{jobs.map((job) => <tr key={job.id} className="border-t border-aidev-border"><td className="p-3">{job.type}</td><td>{job.status}</td><td>{job.progress}%</td><td>{job.attempts}/3</td><td>{job.status === "failed" && <button onClick={() => apiPost(`/api/ops/jobs/${job.id}/retry`, {}).then(load)} className="text-aidev-primary">重试</button>}</td></tr>)}</tbody></table></div></section>
      <section className="grid gap-5 lg:grid-cols-2"><form onSubmit={createSource} className="space-y-3 rounded-lg border border-aidev-border bg-aidev-card p-5"><h2 className="text-title">新增抓取来源</h2>{([['name','来源名称'],['base_url','HTTPS 域名'],['entry_url','入口 URL'],['terms_url','站点条款 URL']] as const).map(([key, label]) => <input key={key} required value={source[key]} onChange={(event) => setSource((value) => ({ ...value, [key]: event.target.value }))} placeholder={label} className="w-full rounded border border-aidev-input px-3 py-2" />)}<label className="flex gap-2 text-xs text-aidev-muted-foreground"><input type="checkbox" checked={source.compliance_confirmed} onChange={(event) => setSource((value) => ({ ...value, compliance_confirmed: event.target.checked }))}/>已核对 robots.txt、站点条款、著作权与个人信息最小化要求</label><button className="rounded bg-aidev-primary px-4 py-2 text-sm text-white">保存白名单来源</button></form><div className="space-y-3 rounded-lg border border-aidev-border bg-aidev-card p-5"><h2 className="text-title">CSV 种子邀请</h2><textarea value={invites} onChange={(event) => setInvites(event.target.value)} rows={5} placeholder="邮箱,用户名,developer,Python|RAG" className="w-full rounded border border-aidev-input p-3 font-mono text-xs"/><button onClick={importInvites} className="rounded bg-aidev-primary px-4 py-2 text-sm text-white">生成激活链接</button></div></section>
      {sources.length > 0 && <section><h2 className="mb-3 text-title">抓取来源与任务</h2><div className="grid gap-3 sm:grid-cols-2">{sources.map((item) => <div key={item.id} className="rounded-lg border border-aidev-border bg-aidev-card p-4"><p className="font-medium">{item.name}</p><p className="truncate text-xs text-aidev-muted-foreground">{item.baseUrl}</p><button onClick={() => apiPost(`/api/ops/crawl-sources/${item.id}/run`, {}).then(() => { setMessage('抓取任务已入队'); load(); })} className="mt-3 rounded bg-aidev-primary px-3 py-1.5 text-xs text-white">运行抓取</button></div>)}</div></section>}
      <section><h2 className="mb-3 text-title">待审核摘要</h2><div className="space-y-3">{crawlItems.length === 0 ? <p className="text-sm text-aidev-muted-foreground">暂无待审核内容</p> : crawlItems.map((item) => <article key={item.id} className="rounded-lg border border-aidev-border bg-aidev-card p-4"><a href={item.canonicalUrl} target="_blank" className="font-medium text-aidev-primary">{item.sourceTitle}</a><p className="mt-2 text-sm text-aidev-muted-foreground">{item.summary}</p><div className="mt-3 flex gap-2"><button onClick={() => review(item, "approve")} className="rounded bg-green-600 px-3 py-1 text-sm text-white">批准发布</button><button onClick={() => review(item, "reject")} className="rounded border px-3 py-1 text-sm">拒绝</button></div></article>)}</div></section>
      <section className="rounded-lg border border-aidev-border bg-aidev-card p-5"><h2 className="text-title">AI 金标评测</h2><p className="my-2 text-sm text-aidev-muted-foreground">在同一金标版本与模型配置下创建可断点续跑任务；结果须完成双人独立评分。</p><button onClick={() => apiPost("/api/ops/evaluation-runs", { prompt_version: "answer-v1", dataset_version: "v1" }).then(() => { setMessage("评测任务已创建"); load(); })} className="rounded bg-aidev-primary px-4 py-2 text-sm text-white">运行 v1 金标评测</button></section>
    </div>
  );
}
