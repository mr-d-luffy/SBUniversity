"use client";

import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useActivityData } from "@/components/features/ActivityDataProvider";

type RangeDays = 7 | 14 | 30;
function parseLocalDay(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export default function StudyTimeChart() {
  const [range, setRange] = useState<RangeDays>(7);
  const { activity } = useActivityData();

  const days = useMemo(() => (activity?.days ?? []).slice(-range).map((day) => ({ ...day, parsed: parseLocalDay(day.date) })), [activity, range]);
  const maxMinutes = Math.max(60, ...days.map((day) => day.seconds / 60));
  const axisMax = Math.ceil(maxMinutes / 60) * 60;
  const today = activity?.today_seconds ?? 0;
  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
  };
  const dateRange = days.length
    ? `${days[0].parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${days.at(-1)!.parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`
    : "Loading activity…";
  const todayKey = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}-${String(new Date().getDate()).padStart(2, "0")}`;

  return (
    <section className="min-w-0 overflow-hidden rounded-2xl border border-slate-700/70 bg-[#252b3c] p-4 text-white shadow-md sm:p-5" aria-label="Study time statistics">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-heading text-lg font-bold text-white">Time Spent</h2>
          <p className="mt-0.5 text-sm text-slate-300">{dateRange}</p>
        </div>
        <label className="relative flex min-h-10 shrink-0 items-center rounded-xl border border-slate-600 bg-slate-700/60 pl-3 pr-9 text-sm text-slate-100 focus-within:ring-2 focus-within:ring-orange-400">
          <span className="sr-only">Time period</span>
          <select value={range} onChange={(event) => setRange(Number(event.target.value) as RangeDays)} className="absolute inset-0 h-full w-full cursor-pointer appearance-none opacity-0" aria-label="Time period">
            <option value={7}>7 Days</option><option value={14}>14 Days</option><option value={30}>30 Days</option>
          </select>
          <span aria-hidden="true">{range} Days</span><ChevronDown size={16} className="pointer-events-none absolute right-3 text-slate-300" />
        </label>
      </div>

      <div className="mt-4 grid grid-cols-[30px_minmax(0,1fr)] gap-2 sm:grid-cols-[34px_minmax(0,1fr)]">
        <div className="flex h-28 flex-col justify-between pb-5 text-[11px] text-slate-400" aria-hidden="true">
          {[1, 0.75, 0.5, 0.25, 0].map((fraction) => <span key={fraction}>{Math.round(axisMax * fraction)}m</span>)}
        </div>
        <div className="relative h-28">
          <div className="absolute inset-x-0 top-0 bottom-5 flex flex-col justify-between" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((line) => <div key={line} className="border-t border-dashed border-slate-500/60" />)}
          </div>
          <div className="relative flex h-full items-stretch justify-around gap-1 border-b border-slate-500/80 px-1">
            {days.map(({ date, seconds, parsed }) => {
              const active = date === todayKey;
              const height = Math.min(100, (seconds / 60 / axisMax) * 100);
              return (
                <div key={date} className="flex min-w-0 flex-1 flex-col items-center justify-end">
                  <div className="group relative flex h-[calc(100%-20px)] w-full items-end justify-center">
                    <div
                      className={`w-[min(100%,28px)] rounded-t-xl border transition-all ${active ? "border-orange-300 bg-gradient-to-t from-orange-500 to-orange-300 shadow-[0_0_18px_rgba(251,146,60,0.28)]" : "border-slate-500/70 bg-slate-700/70"}`}
                      style={{ height: `${height}%`, minHeight: seconds > 0 ? 8 : 0 }}
                      title={`${parsed.toLocaleDateString()}: ${formatTime(seconds)}`}
                    />
                    {seconds > 0 && <span className="pointer-events-none absolute bottom-full mb-2 hidden whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-[10px] text-white group-hover:block">{formatTime(seconds)}</span>}
                  </div>
                  <span className={`h-5 pt-1 text-xs ${active ? "font-semibold text-orange-300" : "text-slate-300"}`}>{range === 7 ? parsed.getDate() : parsed.toLocaleDateString(undefined, { month: "numeric", day: "numeric" })}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <p className="mt-2 text-[11px] text-slate-300"><span className="font-semibold text-white">Today: {formatTime(today)}</span><span className="ml-2 text-slate-400">Live while visible</span></p>
    </section>
  );
}
