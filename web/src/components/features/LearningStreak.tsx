"use client";

import { useState } from "react";
import { Check, Zap } from "lucide-react";
import { useActivityData } from "@/components/features/ActivityDataProvider";

function parseLocalDay(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export default function LearningStreak() {
  const { activity, error, collectBadge } = useActivityData();
  const [claiming, setClaiming] = useState(false);

  const claim = async () => {
    if (!activity?.can_collect_badge || claiming) return;
    setClaiming(true);
    try {
      await collectBadge();
    } finally {
      setClaiming(false);
    }
  };

  return (
    <section className="relative min-w-0 overflow-hidden rounded-2xl border border-white bg-gradient-to-br from-white via-white to-green-50 px-4 pb-4 pt-7 text-center shadow-md sm:p-5 sm:pt-8" aria-label="Learning streak">
      <div className="absolute left-1/2 top-0 grid h-12 w-12 -translate-x-1/2 -translate-y-1/4 place-items-center drop-shadow-[0_6px_9px_rgba(34,197,94,0.22)]" aria-hidden="true">
        <svg viewBox="0 0 72 82" className="h-full w-full">
          <path d="M3 2h66v53L36 80 3 55z" fill="#39bd20" />
          <path d="M3 2h66L36 26z" fill="#65db38" />
          <path d="M3 2v53l33-29z" fill="#51ce29" />
        </svg>
      </div>

      <h2 className="font-heading text-lg font-bold text-slate-900">
        {!activity ? "Learning Streak" : activity.streak_days >= 3 ? `${activity.streak_days}-Day Streak Achieved` : activity.streak_days > 0 ? `${activity.streak_days}-Day Streak` : "Start a Learning Streak"}
      </h2>
      <p className="mt-1 text-xs text-slate-500">
        {!activity ? "Loading your activity…" : activity.streak_days >= 3 ? "Staying consistent — keep it up!" : "Spend a minute learning each day to build your streak."}
      </p>

      <div className="mx-auto mt-4 grid max-w-[520px] grid-cols-7 gap-1 sm:gap-2">
        {(activity?.days ?? []).slice(-7).map(({ date, active }) => {
          const parsed = parseLocalDay(date);
          const isToday = parsed.toDateString() === new Date().toDateString();
          const dayLetter = parsed.toLocaleDateString(undefined, { weekday: "short" }).slice(0, 1);
          return (
            <div key={date} className={`flex min-w-0 flex-col items-center justify-center gap-1.5 rounded-2xl border py-2 sm:py-2.5 ${active ? "border-green-100 bg-green-50/70" : "border-slate-100 bg-slate-50/60"} ${isToday ? "ring-2 ring-green-200 shadow-[0_0_16px_rgba(74,222,128,0.16)]" : ""}`} aria-label={`${parsed.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}${active ? ", streak day" : ", not active"}`}>
              <span className={`grid h-6 w-6 place-items-center rounded-full ${active ? "bg-green-600 text-white" : "bg-slate-200 text-slate-300"}`}>
                <Zap size={15} fill="currentColor" strokeWidth={active ? 2.5 : 1.5} />
              </span>
              <span className={`text-sm font-semibold ${active || isToday ? "text-slate-900" : "text-slate-600"}`}>{dayLetter}</span>
            </div>
          );
        })}
      </div>

      <button type="button" onClick={claim} disabled={!activity?.can_collect_badge || claiming} className={`mt-4 inline-flex min-h-11 w-full max-w-[250px] items-center justify-center gap-2 rounded-full text-sm font-semibold text-white shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-600 focus-visible:ring-offset-2 disabled:cursor-default ${activity?.can_collect_badge ? "bg-gradient-to-b from-slate-800 to-black hover:from-slate-700 hover:to-slate-900" : "bg-slate-300"}`}>
        {activity?.streak_badge_collected ? <><Check size={16} /> Collected</> : claiming ? "Collecting…" : activity?.can_collect_badge ? "Collect streak badge" : "Keep learning"}
      </button>
      {activity && activity.streak_days < 3 && <p className="mt-1 text-[11px] text-slate-500">{3 - activity.streak_days} more consecutive active day{3 - activity.streak_days === 1 ? "" : "s"} to earn your badge</p>}
      {error && <p role="status" className="mt-2 text-[11px] text-bordo-700">{error}</p>}
    </section>
  );
}
