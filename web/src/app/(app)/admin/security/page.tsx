"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Activity, Clock3, RefreshCw, ShieldAlert, Users, ShieldCheck, TrendingUp, Zap } from "lucide-react";
import { PageHeader } from "@/components/ui/Card";
import { api, getDevAuthToken } from "@/lib/api";

type EventItem = {
  id: string;
  actor_name: string;
  actor_role: string | null;
  path: string;
  method: string;
  status_code: number;
  duration_ms: number;
  client_ip: string | null;
  created_at: string;
};
type Summary = { requests: number; active_users: number; errors: number; average_duration_ms: number };
type EventResponse = { items: EventItem[]; total: number };

const SERIES_BUCKETS = 12;

function buildTrafficSeries(events: EventItem[], minutes: number) {
  const now = Date.now();
  const start = now - minutes * 60_000;
  const bucketSize = (minutes * 60_000) / SERIES_BUCKETS;
  const points = Array.from({ length: SERIES_BUCKETS }, (_, index) => ({
    label: `−${formatOffset(Math.round((SERIES_BUCKETS - index) * minutes / SERIES_BUCKETS))}`,
    requests: 0,
    errors: 0,
  }));

  for (const event of events) {
    const index = Math.floor((new Date(event.created_at).getTime() - start) / bucketSize);
    if (index >= 0 && index < points.length) {
      points[index].requests += 1;
      if (event.status_code >= 400) points[index].errors += 1;
    }
  }
  return points;
}

function formatOffset(minutes: number) {
  if (minutes >= 1440) return `${Math.round(minutes / 1440)}d`;
  if (minutes >= 60) return `${Math.round(minutes / 60)}h`;
  return `${minutes}m`;
}

function percentile(values: number[], fraction: number) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * fraction) - 1)];
}

export default function AdminSecurityPage() {
  const { getToken } = useAuth();
  const [events, setEvents] = useState<EventItem[]>([]);
  const [summary, setSummary] = useState<Summary>({ requests: 0, active_users: 0, errors: 0, average_duration_ms: 0 });
  const [minutes, setMinutes] = useState(60);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      let token = await getToken();
      if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) token = getDevAuthToken("admin");
      const [eventData, summaryData] = await Promise.all([
        api<EventResponse>(`/admin/security/events?since_minutes=${minutes}&page_size=100`, token ?? undefined),
        api<Summary>(`/admin/security/summary?since_minutes=${minutes}`, token ?? undefined),
      ]);
      setEvents(eventData.items);
      setSummary(summaryData);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load security activity.");
    } finally {
      setLoading(false);
    }
  }, [getToken, minutes]);

  useEffect(() => { void refresh(true); }, [refresh]);
  useEffect(() => {
    const timer = window.setInterval(() => void refresh(), 15_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const analytics = useMemo(() => {
    const series = buildTrafficSeries(events, minutes);
    const maxRequests = Math.max(1, ...series.map((point) => point.requests));
    const routes = new Map<string, number>();
    const latencies = events.map((event) => event.duration_ms);
    let clientErrors = 0;
    let serverErrors = 0;
    let successes = 0;
    for (const event of events) {
      routes.set(event.path, (routes.get(event.path) ?? 0) + 1);
      if (event.status_code >= 500) serverErrors += 1;
      else if (event.status_code >= 400) clientErrors += 1;
      else successes += 1;
    }
    const topRoutes = [...routes.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
    const maxRouteCount = Math.max(1, ...topRoutes.map(([, count]) => count));
    const sampleErrors = clientErrors + serverErrors;
    const errorRate = events.length ? Math.round((sampleErrors / events.length) * 100) : 0;
    const latencyValues = events.slice(0, 24).reverse().map((event) => event.duration_ms);
    const latencyMax = Math.max(1, ...latencyValues);
    const latencyPoints = latencyValues.map((value, index, sample) => {
      const x = sample.length <= 1 ? 50 : (index / (sample.length - 1)) * 100;
      const y = 35 - (value / latencyMax) * 30;
      return `${x},${y}`;
    }).join(" ");
    return { series, maxRequests, topRoutes, maxRouteCount, clientErrors, serverErrors, successes, errorRate, p95: percentile(latencies, 0.95), latencyPoints };
  }, [events, minutes]);

  const stats = [
    { label: "Total requests", value: summary.requests.toLocaleString(), icon: Activity, detail: "Across selected time range", tint: "text-blue-700 bg-blue-50" },
    { label: "Active accounts", value: summary.active_users.toLocaleString(), icon: Users, detail: "Authenticated users seen", tint: "text-green-700 bg-green-50" },
    { label: "Failed requests", value: summary.errors.toLocaleString(), icon: ShieldAlert, detail: `${analytics.errorRate}% of sampled events`, tint: "text-rose-700 bg-rose-50" },
    { label: "Average latency", value: `${summary.average_duration_ms} ms`, icon: Clock3, detail: `Sample p95 · ${analytics.p95} ms`, tint: "text-violet-700 bg-violet-50" },
  ];
  const statusTotal = Math.max(1, analytics.successes + analytics.clientErrors + analytics.serverErrors);
  const successPercent = Math.round((analytics.successes / statusTotal) * 100);
  const clientPercent = Math.round((analytics.clientErrors / statusTotal) * 100);
  const serverPercent = Math.max(0, 100 - successPercent - clientPercent);
  const statusGradient = `conic-gradient(#15803d 0 ${successPercent}%, #f59e0b ${successPercent}% ${successPercent + clientPercent}%, #e11d48 ${successPercent + clientPercent}% 100%)`;

  return (
    <div className="security-dashboard space-y-6 pb-8">
      <PageHeader title="Security & Activity" subtitle="Live traffic patterns, response health, and route-level activity." action={
        <div className="flex flex-wrap items-center gap-2">
          <span className="hidden items-center gap-2 rounded-full border border-green-200 bg-green-50 px-3 py-2 text-xs font-semibold text-green-800 sm:flex"><span className="h-2 w-2 animate-pulse rounded-full bg-green-600" /> Live · 15 sec</span>
          <select aria-label="Activity time range" value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} className="min-h-11 rounded-xl border border-cream-300 bg-white px-3 text-sm text-green-900 outline-none focus:ring-2 focus:ring-green-600">
            <option value={15}>Last 15 min</option><option value={60}>Last hour</option><option value={1440}>Last 24 hours</option><option value={10080}>Last 7 days</option>
          </select>
          <button onClick={() => void refresh(true)} aria-label="Refresh activity" className="grid h-11 w-11 place-items-center rounded-xl border border-cream-300 bg-white text-green-800 hover:bg-cream-100"><RefreshCw size={17} className={loading ? "animate-spin" : ""} /></button>
        </div>
      } />

      {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, detail, tint }, index) => <section key={label} className="security-card-in rounded-2xl border border-cream-300 bg-white p-4 shadow-sm sm:p-5" style={{ animationDelay: `${index * 75}ms` }}>
          <div className="flex items-center justify-between"><span className="text-xs font-medium text-ink-muted sm:text-sm">{label}</span><span className={`grid h-9 w-9 place-items-center rounded-xl ${tint}`}><Icon size={17} /></span></div>
          <p className="mt-3 font-heading text-2xl font-bold text-green-950 sm:text-3xl">{value}</p>
          <p className="mt-1 text-[11px] text-ink-muted">{detail}</p>
        </section>)}
      </div>

      <section className="overflow-hidden rounded-2xl border border-green-900 p-5 text-white shadow-sm sm:p-7" style={{ background: "linear-gradient(135deg, #052e24 0%, #064e3b 56%, #065f46 100%)" }}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em]" style={{ color: "#d1fae5" }}><Zap size={12} /> Traffic pulse</p><h2 className="mt-3 font-heading text-xl font-bold sm:text-2xl" style={{ color: "#fdf6ee" }}>Request activity over time</h2><p className="mt-1 text-xs" style={{ color: "#d1fae5" }}>Timeline built from the latest {events.length} events in this range</p></div>
          <div className="flex items-center gap-4 text-[11px] font-medium" style={{ color: "#ecfdf5" }}><span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-emerald-300" />Requests</span><span className="inline-flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-rose-300" />Failed</span></div>
        </div>
        <div className="mt-7 grid h-44 grid-cols-12 items-end gap-2 border-b border-white/15 pb-2 sm:h-56 sm:gap-3">
          {analytics.series.map((point, index) => {
            const height = Math.max(point.requests ? 12 : 3, (point.requests / analytics.maxRequests) * 100);
            const failedHeight = point.requests ? Math.max(0, (point.errors / point.requests) * height) : 0;
            return <div key={`${point.label}-${index}`} className="group relative flex h-full items-end justify-center" title={`${point.label}: ${point.requests} sampled requests, ${point.errors} failed`}>
              <div className="relative w-full max-w-8 overflow-hidden rounded-t-lg bg-white/10 transition-all duration-500 group-hover:bg-white/20" style={{ height: `${height}%` }}>
                <div className="absolute inset-0 bg-gradient-to-t from-emerald-300/70 to-emerald-100/90 security-bar-shimmer" />
                {failedHeight > 0 && <div className="absolute inset-x-0 top-0 rounded-t-lg bg-rose-300 transition-all duration-500" style={{ height: `${(failedHeight / height) * 100}%` }} />}
              </div>
              <span className="absolute -bottom-5 hidden whitespace-nowrap text-[9px] first:block last:block sm:block" style={{ color: "#a7f3d0" }}>{index % 3 === 0 ? point.label : ""}</span>
            </div>;
          })}
        </div>
        <div className="mt-7 flex items-center justify-between gap-3 text-[11px]" style={{ color: "#a7f3d0" }}><span>{events.length} sampled events</span><span>Higher bars mean more activity</span><span>{minutes >= 1440 ? `${minutes / 1440} day window` : `${minutes} min window`}</span></div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-2xl border border-cream-300 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-start justify-between gap-3"><div><h2 className="font-heading text-base font-bold text-green-950">Route activity</h2><p className="mt-1 text-xs text-ink-muted">Most requested paths in the sampled events</p></div><TrendingUp size={19} className="text-green-700" /></div>
          {analytics.topRoutes.length ? <div className="mt-6 space-y-4">
            {analytics.topRoutes.map(([route, count], index) => <div key={route} className="security-route-in" style={{ animationDelay: `${index * 90}ms` }}>
              <div className="mb-1.5 flex items-center justify-between gap-3"><code className="min-w-0 truncate text-xs font-medium text-green-950">{route}</code><span className="shrink-0 text-xs font-bold tabular-nums text-ink-muted">{count}</span></div>
              <div className="h-2.5 overflow-hidden rounded-full bg-cream-100"><div className="h-full rounded-full bg-gradient-to-r from-green-700 to-emerald-400 transition-[width] duration-700 ease-out" style={{ width: `${Math.max(4, (count / analytics.maxRouteCount) * 100)}%` }} /></div>
            </div>)}
          </div> : <EmptyAnalysis loading={loading} />}
        </section>

        <section className="rounded-2xl border border-cream-300 bg-white p-5 shadow-sm sm:p-6">
          <div><h2 className="font-heading text-base font-bold text-green-950">Response health</h2><p className="mt-1 text-xs text-ink-muted">Status distribution and latency profile</p></div>
          <div className="mt-5 flex items-center gap-5">
            <div className="security-donut grid h-28 w-28 shrink-0 place-items-center rounded-full" style={{ background: statusGradient }}><div className="grid h-[78px] w-[78px] place-items-center rounded-full bg-white text-center"><span className="font-heading text-xl font-bold text-green-950">{successPercent}%</span><span className="-mt-2 text-[9px] uppercase tracking-wide text-ink-muted">successful</span></div></div>
            <div className="min-w-0 flex-1 space-y-2.5 text-xs">
              <StatusLegend color="bg-green-700" label="Successful" count={analytics.successes} />
              <StatusLegend color="bg-amber-400" label="Client errors" count={analytics.clientErrors} />
              <StatusLegend color="bg-rose-600" label="Server errors" count={analytics.serverErrors} />
            </div>
          </div>
          <div className="mt-6 rounded-xl border border-cream-200 bg-cream-50 p-3.5">
            <div className="flex items-center justify-between gap-3"><div><p className="text-xs font-semibold text-green-950">Response-time sample</p><p className="mt-0.5 text-[10px] text-ink-muted">Last {Math.min(events.length, 24)} events · p95 {analytics.p95} ms</p></div><span className="rounded-full bg-violet-50 px-2 py-1 text-[10px] font-bold text-violet-700">avg {summary.average_duration_ms} ms</span></div>
            {analytics.latencyPoints ? <svg className="mt-3 h-16 w-full overflow-visible" viewBox="0 0 100 40" preserveAspectRatio="none" role="img" aria-label="Response time trend for recent events">
              <defs><linearGradient id="latency-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#7c3aed" stopOpacity="0.22" /><stop offset="100%" stopColor="#7c3aed" stopOpacity="0" /></linearGradient></defs>
              <polygon points={`0,40 ${analytics.latencyPoints} 100,40`} fill="url(#latency-fill)" />
              <polyline points={analytics.latencyPoints} fill="none" stroke="#7c3aed" strokeWidth="1.8" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" className="security-line-draw" />
            </svg> : <p className="mt-3 py-4 text-center text-xs text-ink-muted">Waiting for response-time samples…</p>}
          </div>
        </section>
      </div>

      <p className="rounded-xl border border-cream-200 bg-cream-50 px-4 py-3 text-[11px] leading-5 text-ink-muted">Charts use the latest 100 event records returned by the monitor, while headline totals come from the full selected period. Query strings, credentials, request bodies, and full IP addresses are not stored.</p>

      <style jsx>{`
        @keyframes security-card-in { from { opacity: 0; transform: translateY(12px) scale(.985); } to { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes security-route-in { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes security-donut-in { from { transform: scale(.78) rotate(-35deg); opacity: .55; } to { transform: scale(1) rotate(0); opacity: 1; } }
        @keyframes security-line-draw { from { stroke-dasharray: 0 200; opacity: .4; } to { stroke-dasharray: 200 0; opacity: 1; } }
        @keyframes security-shimmer { from { transform: translateY(16%); opacity: .65; } to { transform: translateY(0); opacity: 1; } }
        .security-card-in { animation: security-card-in .48s cubic-bezier(.2,.75,.25,1) both; }
        .security-route-in { animation: security-route-in .45s ease-out both; }
        .security-donut { animation: security-donut-in .7s cubic-bezier(.2,.75,.25,1) both; }
        .security-line-draw { animation: security-line-draw 1.1s ease-out both; }
        .security-bar-shimmer { animation: security-shimmer .65s ease-out both; }
        @media (prefers-reduced-motion: reduce) { .security-card-in, .security-route-in, .security-donut, .security-line-draw, .security-bar-shimmer { animation: none; } }
      `}</style>
    </div>
  );
}

function StatusLegend({ color, label, count }: { color: string; label: string; count: number }) {
  return <div className="flex items-center justify-between gap-3"><span className="inline-flex items-center gap-2 text-ink-muted"><i className={`h-2.5 w-2.5 rounded-full ${color}`} />{label}</span><span className="font-semibold tabular-nums text-green-950">{count}</span></div>;
}

function EmptyAnalysis({ loading }: { loading: boolean }) {
  return <div className="mt-6 grid min-h-40 place-items-center rounded-xl border border-dashed border-cream-300 bg-cream-50 text-center"><div><ShieldCheck size={24} className="mx-auto text-green-700" /><p className="mt-2 text-sm font-semibold text-green-950">{loading ? "Loading route signals…" : "No route activity yet"}</p><p className="mt-1 text-xs text-ink-muted">Route patterns appear here as events arrive.</p></div></div>;
}
