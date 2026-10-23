"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Activity, Clock3, RefreshCw, ShieldAlert, Users, ShieldCheck } from "lucide-react";
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

const relativeTime = (value: string) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
};

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
        api<EventResponse>(`/admin/security/events?since_minutes=${minutes}&page_size=60`, token ?? undefined),
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

  const stats = [
    { label: "Requests", value: summary.requests, icon: Activity, color: "text-blue-700 bg-blue-50" },
    { label: "Active accounts", value: summary.active_users, icon: Users, color: "text-green-700 bg-green-50" },
    { label: "Failed requests", value: summary.errors, icon: ShieldAlert, color: "text-rose-700 bg-rose-50" },
    { label: "Avg. response", value: `${summary.average_duration_ms} ms`, icon: Clock3, color: "text-violet-700 bg-violet-50" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader title="Security & Activity" subtitle="Live API traffic and student/teacher page navigation." action={
        <div className="flex items-center gap-2">
          <span className="hidden items-center gap-2 rounded-full border border-green-200 bg-green-50 px-3 py-2 text-xs font-semibold text-green-800 sm:flex"><span className="h-2 w-2 animate-pulse rounded-full bg-green-600" /> Live · 15 sec</span>
          <select aria-label="Activity time range" value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} className="min-h-11 rounded-xl border border-cream-300 bg-white px-3 text-sm text-green-900 outline-none focus:ring-2 focus:ring-green-600">
            <option value={15}>Last 15 min</option><option value={60}>Last hour</option><option value={1440}>Last 24 hours</option><option value={10080}>Last 7 days</option>
          </select>
          <button onClick={() => void refresh(true)} aria-label="Refresh activity" className="grid h-11 w-11 place-items-center rounded-xl border border-cream-300 bg-white text-green-800 hover:bg-cream-100"><RefreshCw size={17} className={loading ? "animate-spin" : ""} /></button>
        </div>
      } />

      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color }) => <section key={label} className="rounded-2xl border border-cream-300 bg-white p-4 shadow-sm sm:p-5">
          <div className="flex items-center justify-between"><span className="text-xs font-medium text-ink-muted sm:text-sm">{label}</span><span className={`grid h-9 w-9 place-items-center rounded-xl ${color}`}><Icon size={17} /></span></div>
          <p className="mt-3 font-heading text-2xl font-bold text-green-950 sm:text-3xl">{value}</p>
          <p className="mt-1 text-[11px] text-ink-muted">Selected period</p>
        </section>)}
      </div>

      <section className="overflow-hidden rounded-2xl border border-cream-300 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-cream-200 px-4 py-4 sm:px-6">
          <div><h2 className="font-heading text-base font-bold text-green-950">Recent activity</h2><p className="mt-1 text-xs text-ink-muted">{events.length} of {summary.requests} events · newest first</p></div>
          <ShieldCheck size={20} className="text-green-700" />
        </div>
        {error && <div role="alert" className="m-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{error}</div>}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-cream-50 text-[11px] uppercase tracking-wide text-ink-muted"><tr><th className="px-5 py-3 font-semibold">Account</th><th className="px-5 py-3 font-semibold">Activity</th><th className="px-5 py-3 font-semibold">Result</th><th className="px-5 py-3 font-semibold">Client network</th><th className="px-5 py-3 font-semibold">Time</th></tr></thead>
            <tbody className="divide-y divide-cream-200">
              {events.map((item) => <tr key={item.id} className="hover:bg-cream-50/70">
                <td className="px-5 py-3.5"><p className="max-w-48 truncate font-semibold text-green-950">{item.actor_name}</p><p className="mt-0.5 text-[11px] capitalize text-ink-muted">{item.actor_role ?? "Guest"}</p></td>
                <td className="px-5 py-3.5"><div className="flex items-center gap-2"><span className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold ${item.method === "NAV" ? "bg-violet-50 text-violet-700" : "bg-blue-50 text-blue-700"}`}>{item.method}</span><code className="max-w-[360px] truncate text-xs text-ink">{item.path}</code></div><p className="mt-1 text-[11px] text-ink-muted">{item.duration_ms} ms</p></td>
                <td className="px-5 py-3.5"><span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.status_code >= 400 ? "bg-rose-50 text-rose-700" : "bg-green-50 text-green-800"}`}>{item.status_code}</span></td>
                <td className="px-5 py-3.5 font-mono text-xs text-ink-muted">{item.client_ip ?? "—"}</td>
                <td className="px-5 py-3.5 whitespace-nowrap text-xs text-ink-muted" title={new Date(item.created_at).toLocaleString()}>{relativeTime(item.created_at)}</td>
              </tr>)}
              {!loading && events.length === 0 && <tr><td colSpan={5} className="px-5 py-12 text-center"><p className="font-semibold text-green-950">No activity in this period</p><p className="mt-1 text-xs text-ink-muted">New API and portal route events will appear here.</p></td></tr>}
              {loading && events.length === 0 && <tr><td colSpan={5} className="px-5 py-12 text-center text-sm text-ink-muted">Loading security activity…</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="border-t border-cream-200 bg-cream-50/60 px-4 py-3 text-[11px] text-ink-muted sm:px-6">Query strings, credentials, request bodies, and full IP addresses are not stored.</div>
      </section>
    </div>
  );
}
