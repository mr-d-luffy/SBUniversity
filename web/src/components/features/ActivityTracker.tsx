"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { usePathname } from "next/navigation";
import { api, getDevAuthToken } from "@/lib/api";

type Role = "student" | "teacher" | "admin";
const localDate = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

/** Records foreground time throughout the signed-in student/teacher portal. */
export default function ActivityTracker({ role }: { role: Role }) {
  const { getToken } = useAuth();
  const pathname = usePathname();

  useEffect(() => {
    if (role === "admin" || !pathname) return;
    let cancelled = false;
    void (async () => {
      try {
        let token = await getToken();
        if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
          token = getDevAuthToken(role);
        }
        if (!cancelled) {
          await api<void>("/security/navigation", token ?? undefined, {
            method: "POST",
            body: JSON.stringify({ path: pathname }),
          });
        }
      } catch {
        // Navigation telemetry is best-effort and never blocks page transitions.
      }
    })();
    return () => { cancelled = true; };
  }, [getToken, pathname, role]);

  useEffect(() => {
    if (role === "admin") return;

    let lastMark = Date.now();
    let wasVisible = document.visibilityState === "visible";
    let pendingMs = 0;
    let sending = false;

    const sendPending = async () => {
      if (sending || pendingMs < 1000) return;
      const seconds = Math.min(60, Math.floor(pendingMs / 1000));
      const amountMs = seconds * 1000;
      const activityDate = localDate(new Date());
      sending = true;
      try {
        let token = await getToken();
        if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
          token = getDevAuthToken(role);
        }
        await api<void>("/activity/time", token ?? undefined, {
          method: "POST",
          body: JSON.stringify({ activity_date: activityDate, seconds }),
        });
        pendingMs = Math.max(0, pendingMs - amountMs);
      } catch {
        // Keep the elapsed time queued and retry on the next foreground heartbeat.
      } finally {
        sending = false;
      }
    };

    const tick = () => {
      const current = Date.now();
      if (wasVisible) pendingMs += Math.max(0, Math.min(current - lastMark, 60_000));
      wasVisible = document.visibilityState === "visible";
      lastMark = current;
      if (pendingMs >= 30_000 || !wasVisible) void sendPending();
    };

    const interval = window.setInterval(tick, 30_000);
    document.addEventListener("visibilitychange", tick);
    return () => {
      tick();
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [getToken, role]);

  return null;
}
