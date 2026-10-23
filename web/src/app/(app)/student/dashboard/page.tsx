"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  
  BookOpen,
  CheckCircle2,
  Clock,
  ExternalLink,
  IdCard,
  Megaphone,
  Sparkles,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, StatCard } from "@/components/ui/Card";
import { PointsChip, Badge } from "@/components/ui/Badge";
import { api, getDevAuthToken } from "@/lib/api";
import StudyTimeChart from "@/components/features/StudyTimeChart";
import LearningStreak from "@/components/features/LearningStreak";
import { ActivityDataProvider } from "@/components/features/ActivityDataProvider";

interface EnrolledCourse {
  id: string;
  code: string;
  title: string;
  progress_percent: number;
}

interface OpenTask {
  id: string;
  title: string;
  course: string;
  points: number;
  type: string;
  due?: string | null;
  status: string;
}

interface UpcomingExam {
  id: string;
  title: string;
  course: string;
  duration: number;
  questions: number;
  points: number;
  start_at: string;
}

interface RecentResult {
  id: string;
  exam_title: string;
  course_title: string;
  score: number;
  total_marks: number;
  percentage: number;
  passed: boolean;
  grade: string;
  created_at: string;
}

interface DashboardData {
  enrolled_courses: EnrolledCourse[];
  upcoming_exams: UpcomingExam[];
  recent_results: RecentResult[];
  open_tasks: OpenTask[];
  total_task_points: number;
  tasks_completed: number;
  rank?: number | null;
  certificates_earned: number;
}

interface NoticeItem {
  id: string;
  title: string;
  body: string;
  priority: "normal" | "important" | "urgent";
}

export default function StudentDashboard() {
  const { getToken } = useAuth();
  const { user } = useUser();

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [urgentNotice, setUrgentNotice] = useState<NoticeItem | null>(null);
  const [loading, setLoading] = useState(true);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("student");
    }
    return token;
  }, [getToken]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const [dashRes, noticesRes] = await Promise.all([
        api<DashboardData>("/student/dashboard", token ?? undefined).catch(() => null),
        api<NoticeItem[]>("/notices", token ?? undefined).catch(() => []),
      ]);

      if (dashRes) {
        setDashboard(dashRes);
      }
      if (noticesRes && Array.isArray(noticesRes)) {
        const urgent = noticesRes.find((n) => n.priority === "urgent" || n.priority === "important");
        if (urgent) setUrgentNotice(urgent);
      }
    } catch (err) {
      console.error("Failed to load student dashboard:", err);
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const totalPoints = dashboard?.total_task_points ?? 0;
  const currentRank = dashboard?.rank ? `#${dashboard.rank}` : "Unranked";
  const openTasksList = dashboard?.open_tasks?.filter((t) => t.status === "open") ?? [];
  const certsCount = dashboard?.certificates_earned ?? 0;
  const coursesList = dashboard?.enrolled_courses ?? [];

  return (
    <div className="space-y-6">
      {/* Top Welcome Header */}
      <div className="flex flex-col items-stretch justify-between gap-5 rounded-2xl border border-cream-300 bg-gradient-to-r from-cream-100 to-cream-200 p-4 shadow-sm sm:flex-row sm:items-center sm:p-6">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-green-700 px-2.5 py-0.5 text-[11px] font-bold text-cream-50 uppercase tracking-wider">
              Enrolled Student
            </span>
            <span className="font-mono text-xs font-semibold text-green-900">
              Active Session
            </span>
          </div>
          <h1 className="font-heading text-2xl font-bold text-green-900 sm:text-3xl">
            Welcome back, {user?.firstName || user?.fullName?.split(" ")[0] || "Student"}!
          </h1>
          <p className="text-sm text-ink-muted">
            You are enrolled in {coursesList.length} course{coursesList.length === 1 ? "" : "s"}. Complete tasks and pass exams to climb the live leaderboard!
          </p>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:flex sm:shrink-0 sm:items-center sm:gap-3">
          <Button href="/student/profile" variant="secondary" size="md" className="w-full justify-center sm:w-auto">
            <IdCard size={16} /> View Virtual ID
          </Button>
          <Button href="/student/exams" variant="primary" size="md" className="w-full justify-center sm:w-auto">
            Take Live Exam
          </Button>
        </div>
      </div>

      {/* Urgent Notice Alert Banner */}
      {urgentNotice && (
        <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-bordo-200 bg-bordo-50 p-4 text-xs text-bordo-800 shadow-sm sm:flex-row sm:items-center">
          <div className="flex min-w-0 items-start gap-2">
            <Megaphone size={16} className="shrink-0 text-bordo-700" />
            <span className="min-w-0 break-words">
              <b>{urgentNotice.title}:</b> {urgentNotice.body}
            </span>
          </div>
          <Link href="/notices" className="min-h-11 inline-flex items-center font-bold underline shrink-0 hover:text-bordo-900">
            View All Notices
          </Link>
        </div>
      )}

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          value={`${totalPoints} pts`}
          label="Total Task Points"
          hint="Awarded automatically on completion"
        />
        <StatCard
          value={currentRank}
          label="University Rank"
          hint="Live Task Point standing"
        />
        <StatCard
          value={openTasksList.length}
          label="Pending Tasks"
          hint="Ready for submission"
        />
        <StatCard
          value={certsCount}
          label="Course Certificates"
          hint="Verified digital credentials"
        />
      </div>

      <ActivityDataProvider role="student">
        <div className="grid min-w-0 gap-4 lg:grid-cols-2">
          <StudyTimeChart />
          <LearningStreak />
        </div>
      </ActivityDataProvider>

      {/* Courses & Action Tasks Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Enrolled Courses */}
        <Card className="flex min-w-0 flex-col justify-between p-4 sm:p-6">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cream-200 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <BookOpen size={18} className="text-green-700" />
                <h2 className="font-heading text-base font-bold text-green-900">
                  Enrolled Course Progress
                </h2>
              </div>
              <span className="text-xs text-ink-muted">Certificates issued at 100%</span>
            </div>

            {loading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-green-700" />
              </div>
            ) : coursesList.length === 0 ? (
              <p className="py-6 text-center text-xs text-ink-muted">
                No active course enrollments found.
              </p>
            ) : (
              <ul className="space-y-4">
                {coursesList.map((c) => (
                  <li key={c.id} className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="min-w-0 flex-1 truncate font-semibold text-green-900 sm:max-w-[220px]">
                        {c.code} – {c.title}
                      </span>
                      <span className="font-mono text-xs font-bold text-green-700">
                        {Math.round(c.progress_percent)}%
                      </span>
                    </div>
                    <div
                      className="h-2.5 w-full overflow-hidden rounded-full bg-cream-100"
                      role="progressbar"
                      aria-valuenow={c.progress_percent}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    >
                      <div
                        className="h-full rounded-full bg-green-700 transition-all duration-500"
                        style={{ width: `${Math.min(100, Math.max(0, c.progress_percent))}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-2 border-t border-cream-200 pt-4">
            <span className="text-xs text-ink-muted">
              {certsCount} Certificate{certsCount === 1 ? "" : "s"} earned
            </span>
            <Link
              href="/student/certificates"
              className="text-xs font-bold text-green-700 hover:underline inline-flex items-center gap-1"
            >
              <span>View Credentials</span>
              <ExternalLink size={12} />
            </Link>
          </div>
        </Card>

        {/* Next Up: Upcoming Exams & Tasks */}
        <Card className="flex min-w-0 flex-col justify-between p-4 sm:p-6">
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cream-200 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <Clock size={18} className="text-green-700" />
                <h2 className="font-heading text-base font-bold text-green-900">
                  Open Tasks & Assignments
                </h2>
              </div>
              <Badge tone="info">Live Sync</Badge>
            </div>

            {loading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-green-700" />
              </div>
            ) : openTasksList.length === 0 ? (
              <div className="py-6 text-center text-xs text-ink-muted">
                <CheckCircle2 size={24} className="mx-auto mb-2 text-green-600" />
                All assigned course tasks are completed!
              </div>
            ) : (
              <ul className="divide-y divide-cream-200">
                {openTasksList.slice(0, 3).map((t) => (
                  <li key={t.id} className="flex min-w-0 items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="font-semibold text-sm text-green-900 truncate">{t.title}</p>
                      <p className="text-xs text-ink-muted">
                        {t.course} {t.due ? `· Due ${t.due}` : ""}
                      </p>
                    </div>
                    <PointsChip points={t.points} />
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="mt-4 grid grid-cols-1 gap-2 border-t border-cream-200 pt-4 sm:flex sm:items-center sm:justify-between">
            <Button href="/student/tasks" variant="primary" size="sm" className="w-full justify-center sm:w-auto">
              Open Task List
            </Button>
            <Button href="/student/exams" variant="secondary" size="sm" className="w-full justify-center sm:w-auto">
              Scheduled Exams
            </Button>
          </div>
        </Card>
      </div>

      {/* Aarsh Intelligence Helper Banner */}
      <div className="flex flex-col items-stretch justify-between gap-4 rounded-2xl border border-green-700/20 bg-green-50 p-4 shadow-sm sm:flex-row sm:items-center sm:p-5">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-green-700 text-cream-50 shadow-sm">
            <Sparkles size={20} />
          </div>
          <div>
            <h3 className="font-heading text-sm font-bold text-green-900">
              Need assistance with your studies?
            </h3>
            <p className="text-xs text-green-800">
              Aarsh Intelligence can explain difficult topics, clarify exam questions, or guide your preparation.
            </p>
          </div>
        </div>
        <Button href="/assistant" variant="primary" size="sm" className="w-full justify-center sm:w-auto">
          Chat with Aarsh
        </Button>
      </div>
    </div>
  );
}
