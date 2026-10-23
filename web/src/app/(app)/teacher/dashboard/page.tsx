"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth, useUser } from "@clerk/nextjs";
import {
  BookOpen,
  FileText,
  ClipboardCheck,
  Plus,
  ArrowRight,
  Loader2,
  Presentation,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, StatCard } from "@/components/ui/Card";
import { Badge, PointsChip } from "@/components/ui/Badge";
import { api, getDevAuthToken } from "@/lib/api";
import LearningStreak from "@/components/features/LearningStreak";
import StudyTimeChart from "@/components/features/StudyTimeChart";
import { ActivityDataProvider } from "@/components/features/ActivityDataProvider";

interface TeacherDashboardResponse {
  my_courses: { id: string; code: string; title: string; is_published: boolean }[];
  total_exams: number;
  total_submissions: number;
  average_score: number;
  pass_rate: number;
  pending_task_approvals: number;
  recent_notices: { id: string; title: string; audience: string; priority: string; created_at: string }[];
}

interface TeacherExamItem {
  id: string;
  course_id: string;
  course_title?: string;
  title: string;
  duration_minutes: number;
  total_marks: number;
  questions_count?: number;
  task_points?: number;
  status: string;
  start_at: string;
  end_at: string;
}

export default function TeacherDashboard() {
  const { getToken } = useAuth();
  const { user } = useUser();

  const [data, setData] = useState<TeacherDashboardResponse | null>(null);
  const [exams, setExams] = useState<TeacherExamItem[]>([]);
  const [loading, setLoading] = useState(true);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("teacher");
    }
    return token;
  }, [getToken]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const [dashRes, examsRes] = await Promise.all([
        api<TeacherDashboardResponse>("/teacher/dashboard", token ?? undefined).catch(() => null),
        api<TeacherExamItem[]>("/exams", token ?? undefined).catch(() => []),
      ]);

      if (dashRes) setData(dashRes);
      if (examsRes) setExams(examsRes);
    } catch (err) {
      console.error("Failed to load teacher dashboard:", err);
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const coursesCount = data?.my_courses?.length ?? 0;
  const examsCount = data?.total_exams ?? exams.length;
  const pendingApprovals = data?.pending_task_approvals ?? 0;
  const passRate = data?.pass_rate ?? 0;

  return (
    <div className="space-y-6">
      {/* Welcome & Quick Action Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-cream-300 bg-gradient-to-r from-cream-100 to-cream-200 p-4 shadow-sm sm:p-6">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-green-700 px-2.5 py-0.5 text-[11px] font-bold text-cream-50 uppercase tracking-wider">
              Faculty Portal
            </span>
            <span className="text-xs font-semibold text-green-900">
              Department Faculty Control
            </span>
          </div>
          <h1 className="break-words font-heading text-2xl font-bold text-green-900 sm:text-3xl">
            Welcome, {user?.fullName || "Faculty Member"}!
          </h1>
          <p className="text-sm text-ink-muted">
            Managing {coursesCount} active course{coursesCount === 1 ? "" : "s"} with live evaluation workflows.
          </p>
        </div>

        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center sm:gap-3">
          <Button href="/teacher/exams/new" variant="primary" size="md" className="min-h-11 w-full sm:w-auto">
            <Plus size={16} /> Create Exam
          </Button>
          <Button href="/teacher/tasks" variant="secondary" size="md" className="min-h-11 w-full sm:w-auto">
            <ClipboardCheck size={16} /> Review Submissions
          </Button>
          <Button href="/whiteboard" variant="secondary" size="md" className="min-h-11 w-full sm:w-auto">
            <Presentation size={16} /> Create Live Classroom
          </Button>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          value={coursesCount}
          label="Assigned Courses"
          hint="Active curriculum"
        />
        <StatCard
          value={examsCount}
          label="Published Exams"
          hint="Auto-evaluated"
        />
        <StatCard
          value={pendingApprovals}
          label="Awaiting Approval"
          hint={pendingApprovals > 0 ? "Action required" : "All reviewed"}
        />
        <StatCard
          value={`${passRate}%`}
          label="Average Pass Rate"
          hint="Automated exam results"
        />
      </div>

      <ActivityDataProvider role="teacher">
        <div className="grid min-w-0 gap-4 lg:grid-cols-2">
          <StudyTimeChart />
          <LearningStreak />
        </div>
      </ActivityDataProvider>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Managed Exams List */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="min-w-0 p-4 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-cream-200 pb-3">
              <div className="flex min-w-0 items-center gap-2">
                <FileText size={18} className="text-green-700" />
                <h2 className="break-words font-heading text-base font-bold text-green-900">
                  Active Course Examinations
                </h2>
              </div>
              <Link
                href="/teacher/exams"
                className="text-xs font-bold text-green-700 hover:underline flex items-center gap-1"
              >
                <span>Manage all</span>
                <ArrowRight size={13} />
              </Link>
            </div>

            {loading ? (
              <div className="flex h-36 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-green-700" />
              </div>
            ) : exams.length === 0 ? (
              <div className="py-6 text-center text-xs text-ink-muted">
                No active exams created yet. Click &quot;Create Exam&quot; to schedule your first assessment.
              </div>
            ) : (
              <div className="space-y-3">
                {exams.slice(0, 4).map((e) => {
                  const startStr = new Date(e.start_at).toLocaleDateString("en-US", { month: "short", day: "numeric" });
                  const endStr = new Date(e.end_at).toLocaleDateString("en-US", { month: "short", day: "numeric" });

                  return (
                    <div
                      key={e.id}
                      className="flex flex-col justify-between gap-3 rounded-xl border border-cream-200 bg-cream-50/50 p-4 transition-all hover:bg-cream-100/50 sm:flex-row sm:items-center"
                    >
                      <div className="min-w-0">
                        <h3 className="break-words font-semibold text-sm text-green-900">{e.title}</h3>
                        <p className="break-words text-xs text-ink-muted">
                          {e.course_title || "Course"} · Window: {startStr} – {endStr}
                        </p>
                        <p className="text-[11px] text-ink-muted pt-1">
                          {e.questions_count ?? 10} questions · {e.duration_minutes} mins duration
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <PointsChip points={e.task_points ?? 0} />
                        <Button href={`/student/exams/${e.id}`} variant="secondary" size="sm">
                          Preview
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Assigned Courses and Notices */}
        <div className="lg:col-span-5 space-y-6">
          <Card className="min-w-0 p-4 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-cream-200 pb-3">
              <div className="flex min-w-0 items-center gap-2">
                <BookOpen size={18} className="text-green-700" />
                <h2 className="break-words font-heading text-base font-bold text-green-900">
                  Assigned Teaching Courses
                </h2>
              </div>
            </div>

            {loading ? (
              <div className="flex h-24 items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-green-700" />
              </div>
            ) : data?.my_courses?.length === 0 ? (
              <p className="py-4 text-center text-xs text-ink-muted">No courses currently assigned.</p>
            ) : (
              <div className="space-y-3">
                {data?.my_courses?.map((c) => (
                  <div key={c.id} className="flex min-w-0 flex-wrap items-center justify-between gap-2 rounded-lg bg-cream-50 p-3">
                    <div className="min-w-0">
                      <p className="break-words text-sm font-semibold text-green-900">{c.code} – {c.title}</p>
                      <span className="text-[10px] text-ink-muted">
                        Status: {c.is_published ? "Published & Enrolled" : "Draft"}
                      </span>
                    </div>
                    <Badge tone="success">Active</Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
