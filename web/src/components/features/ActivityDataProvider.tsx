"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { api, getDevAuthToken } from "@/lib/api";

export type ActivityDay = { date: string; seconds: number; active: boolean };
export type ActivityData = {
  days: ActivityDay[];
  streak_days: number;
  streak_badge_collected: boolean;
  can_collect_badge: boolean;
  today_seconds: number;
};
type Role = "student" | "teacher";
type ContextValue = {
  activity: ActivityData | null;
  error: string;
  refresh: () => Promise<void>;
  collectBadge: () => Promise<void>;
};

const ActivityContext = createContext<ContextValue | null>(null);
const formatDate = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

export function useActivityData() {
  const value = useContext(ActivityContext);
  if (!value) throw new Error("Activity cards must be rendered inside ActivityDataProvider.");
  return value;
}

export function ActivityDataProvider({ role, children }: { role: Role; children: ReactNode }) {
  const { getToken } = useAuth();
  const [activity, setActivity] = useState<ActivityData | null>(null);
  const [error, setError] = useState("");

  const authToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken(role);
    }
    return token ?? undefined;
  }, [getToken, role]);

  const refresh = useCallback(async () => {
    try {
      const today = formatDate(new Date());
      const result = await api<ActivityData>(`/activity?days=30&today=${today}`, await authToken());
      setActivity(result);
      setError("");
    } catch {
      setError("Activity data is temporarily unavailable.");
    }
  }, [authToken]);

  const collectBadge = useCallback(async () => {
    try {
      const result = await api<ActivityData>(`/activity/collect?days=30&today=${formatDate(new Date())}`, await authToken(), { method: "POST" });
      setActivity(result);
      setError("");
    } catch {
      setError("Could not collect the badge. Please try again.");
    }
  }, [authToken]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, 30_000);
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void refresh();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [refresh]);

  const value = useMemo(() => ({ activity, error, refresh, collectBadge }), [activity, error, refresh, collectBadge]);
  return <ActivityContext.Provider value={value}>{children}</ActivityContext.Provider>;
}
