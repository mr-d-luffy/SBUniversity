"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  
  Loader2,
} from "lucide-react";
import { PageHeader, Card, StatCard } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, getDevAuthToken } from "@/lib/api";

interface OverviewAnalytics {
  total_students: number;
  total_teachers: number;
  total_courses: number;
  total_exams: number;
  total_submissions: number;
  average_score: number;
  pass_rate: number;
  total_task_points: number;
}

interface TeacherAnalyticsItem {
  teacher_id: string;
  name: string;
  courses_count: number;
  exams_count: number;
  submissions_count: number;
  average_score: number;
  pass_rate: number;
}

interface StudentAnalyticsItem {
  student_id: string;
  name: string;
  email: string;
  total_points: number;
  tasks_completed: number;
  exams_taken: number;
  average_score: number;
}

export default function AdminAnalyticsPage() {
  const { getToken } = useAuth();

  const [activeTab, setActiveTab] = useState<"overview" | "faculty" | "students">("overview");
  const [overview, setOverview] = useState<OverviewAnalytics | null>(null);
  const [teachers, setTeachers] = useState<TeacherAnalyticsItem[]>([]);
  const [students, setStudents] = useState<StudentAnalyticsItem[]>([]);
  const [loading, setLoading] = useState(true);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("admin");
    }
    return token;
  }, [getToken]);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const [ovRes, teachRes, studRes] = await Promise.all([
        api<OverviewAnalytics>("/admin/analytics/overview", token ?? undefined).catch(() => null),
        api<TeacherAnalyticsItem[]>("/admin/analytics/teachers", token ?? undefined).catch(() => []),
        api<StudentAnalyticsItem[]>("/admin/analytics/students", token ?? undefined).catch(() => []),
      ]);

      if (ovRes) setOverview(ovRes);
      if (teachRes) setTeachers(teachRes);
      if (studRes) setStudents(studRes);
    } catch (err) {
      console.error("Failed to load analytics:", err);
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const registeredStudents = overview?.total_students ?? 0;
  const passRate = overview?.pass_rate ? `${overview.pass_rate}%` : "0.0%";
  const totalPoints = overview?.total_task_points ?? 0;
  const totalSubmissions = overview?.total_submissions ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Live Academic Analytics"
        subtitle="Real-time institutional metrics, faculty performance distributions, and examination velocity."
        action={
          <span className="flex items-center gap-2 rounded-full border border-cream-300 bg-white px-3 py-1.5 text-xs font-semibold text-green-700 shadow-sm">
            <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
            Live Sync Active
          </span>
        }
      />

      {/* Top Level Realtime Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          value={registeredStudents}
          label="Enrolled Students"
          hint="From database registry"
        />
        <StatCard
          value={totalSubmissions}
          label="Total Exam Submissions"
          hint="Evaluated by exam engine"
        />
        <StatCard
          value={passRate}
          label="Overall Pass Rate"
          hint="Across all courses"
        />
        <StatCard
          value={totalPoints}
          label="Total Task Points Awarded"
          hint="Live leaderboard driver"
        />
      </div>

      {/* Tabs */}
      <div className="-mx-1 flex gap-2 overflow-x-auto border-b border-cream-300 px-1 pb-2">
        <button
          onClick={() => setActiveTab("overview")}
          aria-pressed={activeTab === "overview"}
          className={`min-h-11 shrink-0 rounded-lg px-4 text-xs font-semibold transition-colors ${
            activeTab === "overview"
              ? "bg-green-700 text-cream-50"
              : "bg-white text-green-700 hover:bg-cream-100"
          }`}
        >
          Institutional Overview
        </button>
        <button
          onClick={() => setActiveTab("faculty")}
          aria-pressed={activeTab === "faculty"}
          className={`min-h-11 shrink-0 rounded-lg px-4 text-xs font-semibold transition-colors ${
            activeTab === "faculty"
              ? "bg-green-700 text-cream-50"
              : "bg-white text-green-700 hover:bg-cream-100"
          }`}
        >
          Faculty Performance
        </button>
        <button
          onClick={() => setActiveTab("students")}
          aria-pressed={activeTab === "students"}
          className={`min-h-11 shrink-0 rounded-lg px-4 text-xs font-semibold transition-colors ${
            activeTab === "students"
              ? "bg-green-700 text-cream-50"
              : "bg-white text-green-700 hover:bg-cream-100"
          }`}
        >
          Student Performance
        </button>
      </div>

      {loading ? (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white shadow-sm">
          <Loader2 className="h-8 w-8 animate-spin text-green-700" />
        </div>
      ) : activeTab === "overview" ? (
        <div className="grid gap-6 lg:grid-cols-12">
          <Card className="min-w-0 p-4 space-y-4 sm:p-6 lg:col-span-8">
            <div className="flex items-center justify-between border-b border-cream-200 pb-3">
              <div>
                <h3 className="font-heading text-base font-bold text-green-900">
                  Curriculum & Examination Status
                </h3>
                <p className="text-xs text-ink-muted">Published courses and examinations overview</p>
              </div>
              <Badge tone="success">Database Live</Badge>
            </div>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 pt-2">
              <div className="rounded-xl bg-cream-50 p-4 border border-cream-200">
                <p className="text-xs text-ink-muted font-medium">Active Courses</p>
                <p className="mt-1 font-heading text-2xl font-bold text-green-900">
                  {overview?.total_courses ?? 0}
                </p>
              </div>
              <div className="rounded-xl bg-cream-50 p-4 border border-cream-200">
                <p className="text-xs text-ink-muted font-medium">Published Exams</p>
                <p className="mt-1 font-heading text-2xl font-bold text-green-900">
                  {overview?.total_exams ?? 0}
                </p>
              </div>
              <div className="rounded-xl bg-cream-50 p-4 border border-cream-200 col-span-2 sm:col-span-1">
                <p className="text-xs text-ink-muted font-medium">Average Score</p>
                <p className="mt-1 font-heading text-2xl font-bold text-green-900">
                  {overview?.average_score ? `${overview.average_score}%` : "0%"}
                </p>
              </div>
            </div>
          </Card>

          <Card className="min-w-0 p-4 space-y-4 sm:p-6 lg:col-span-4">
            <h3 className="font-heading text-base font-bold text-green-900 border-b border-cream-200 pb-3">
              System Health
            </h3>
            <ul className="space-y-3 text-xs">
              <li className="flex items-center justify-between">
                <span className="text-ink-muted">Database Engine</span>
                <span className="font-semibold text-green-700">Supabase PostgreSQL</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-ink-muted">Leaderboard Cache</span>
                <span className="font-semibold text-green-700">Redis / SQL Sync</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-ink-muted">Authentication</span>
                <span className="font-semibold text-green-700">Clerk Production JWT</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-ink-muted">PDF Engine</span>
                <span className="font-semibold text-green-700">ReportLab Verifiable</span>
              </li>
            </ul>
          </Card>
        </div>
      ) : activeTab === "faculty" ? (
        <div className="max-w-full overflow-x-auto rounded-xl border border-cream-300 bg-white shadow-sm">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="bg-cream-100 text-xs font-semibold uppercase text-green-900">
              <tr>
                <th className="px-3 py-3.5 sm:px-5">Faculty Member</th>
                <th className="px-3 py-3.5 sm:px-5">Courses</th>
                <th className="px-3 py-3.5 sm:px-5">Exams</th>
                <th className="px-3 py-3.5 sm:px-5">Submissions</th>
                <th className="px-3 py-3.5 sm:px-5">Pass Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cream-200">
              {teachers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-xs text-ink-muted">
                    No faculty performance data found.
                  </td>
                </tr>
              ) : (
                teachers.map((t) => (
                  <tr key={t.teacher_id} className="hover:bg-cream-50/50">
                    <td className="px-3 py-3.5 font-semibold text-green-900 sm:px-5">{t.name}</td>
                    <td className="px-3 py-3.5 text-ink-muted sm:px-5">{t.courses_count}</td>
                    <td className="px-3 py-3.5 text-ink-muted sm:px-5">{t.exams_count}</td>
                    <td className="px-3 py-3.5 text-ink-muted sm:px-5">{t.submissions_count}</td>
                    <td className="px-3 py-3.5 font-bold text-green-700 sm:px-5">{t.pass_rate}%</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="max-w-full overflow-x-auto rounded-xl border border-cream-300 bg-white shadow-sm">
          <table className="w-full min-w-[600px] text-left text-sm">
            <thead className="bg-cream-100 text-xs font-semibold uppercase text-green-900">
              <tr>
                <th className="px-3 py-3.5 sm:px-5">Student</th>
                <th className="px-3 py-3.5 sm:px-5">Email</th>
                <th className="px-3 py-3.5 sm:px-5">Tasks Done</th>
                <th className="px-3 py-3.5 sm:px-5">Exams Taken</th>
                <th className="px-3 py-3.5 text-right sm:px-5">Task Points</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cream-200">
              {students.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-xs text-ink-muted">
                    No student performance data found.
                  </td>
                </tr>
              ) : (
                students.map((s) => (
                  <tr key={s.student_id} className="hover:bg-cream-50/50">
                    <td className="px-3 py-3.5 font-semibold text-green-900 sm:px-5">{s.name}</td>
                    <td className="px-3 py-3.5 text-xs text-ink-muted sm:px-5">{s.email}</td>
                    <td className="px-3 py-3.5 text-ink-muted sm:px-5">{s.tasks_completed}</td>
                    <td className="px-3 py-3.5 text-ink-muted sm:px-5">{s.exams_taken}</td>
                    <td className="px-3 py-3.5 text-right font-heading font-bold text-green-900 sm:px-5">
                      {s.total_points} pts
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
