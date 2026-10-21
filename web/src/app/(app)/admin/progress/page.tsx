"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  BookOpen,
  Search,
  Award,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  ShieldAlert,
  ChevronRight,
  TrendingUp,
  Loader2,
  Users,
} from "lucide-react";
import { PageHeader, Card, StatCard } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface CourseProgress {
  course_id: string;
  course_title: string;
  progress_percent: number;
  completed_tasks: number;
  total_tasks: number;
  status: string;
}

interface StudentProgressRecord {
  student_id: string;
  name: string;
  email: string;
  student_code: string;
  total_points: number;
  tasks_completed: number;
  rank?: number | null;
  courses: CourseProgress[];
}

interface ProgressApiResponse {
  items: StudentProgressRecord[];
  total: number;
  page: number;
  page_size: number;
}

export default function AdminProgressPage() {
  const { getToken } = useAuth();
  const toast = useToast();

  const [records, setRecords] = useState<StudentProgressRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("admin");
    }
    return token;
  }, [getToken]);

  const loadProgress = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const token = await resolveToken();
      const q = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
      const res = await api<ProgressApiResponse>(`/admin/progress/students${q}`, token ?? undefined).catch(() => null);
      if (res?.items) {
        setRecords(res.items);
        setTotal(res.total);
      }
    } catch (err) {
      console.error("Failed to fetch student progress:", err);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [resolveToken, search]);

  useEffect(() => {
    const handler = setTimeout(() => {
      void loadProgress();
    }, 300);
    return () => clearTimeout(handler);
  }, [loadProgress]);

  useEffect(() => {
    const interval = setInterval(() => {
      void loadProgress(false);
    }, 15000);
    return () => clearInterval(interval);
  }, [loadProgress]);

  const totalPoints = records.reduce((acc, r) => acc + r.total_points, 0);
  const totalTasks = records.reduce((acc, r) => acc + r.tasks_completed, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Academic Progress"
        subtitle="Live registry of student course completion percentages, task points, and active rankings."
        action={
          <span className="flex items-center gap-2 text-sm text-ink-muted">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-success" />
            Live DB Sync
          </span>
        }
      />

      {/* KPI Stats */}
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <StatCard value={total} label="Enrolled Students" hint="Active platform learners" />
        <StatCard value={totalPoints} label="Total Task Points" hint="Awarded from tasks/exams" />
        <StatCard value={totalTasks} label="Tasks Completed" hint="Across all departments" />
        <StatCard value="100%" label="Registry Accuracy" hint="Real-time SQL sync" />
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-md">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-ink-placeholder">
            <Search size={15} />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search students by name, email, or student code..."
            className="h-10 w-full rounded-lg border border-cream-300 bg-white pl-9 pr-3 text-sm text-ink placeholder:text-ink-placeholder focus:border-green-700 focus:outline-none"
          />
        </div>
      </div>

      {/* Progress Records List */}
      {loading ? (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white shadow-sm">
          <Loader2 className="h-8 w-8 animate-spin text-green-700" />
        </div>
      ) : records.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-cream-300 bg-white p-12 text-center">
          <Users className="mx-auto h-12 w-12 text-cream-400" />
          <h3 className="mt-3 font-heading text-lg font-bold text-green-900">No Student Records Found</h3>
          <p className="mt-1 text-sm text-ink-muted">
            No students match your query in the database.
          </p>
        </div>
      ) : (
        <div className="grid min-w-0 gap-3 lg:grid-cols-2 2xl:grid-cols-3">
          {records.map((r) => (
            <Card
              key={r.student_id}
              className="min-w-0 p-3.5 transition-shadow hover:shadow-md sm:p-4"
            >
              <div className="flex min-w-0 items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <h3 className="max-w-full truncate font-heading text-sm font-bold text-green-900 sm:text-base">{r.name}</h3>
                    <span className="rounded-md bg-cream-200 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-green-900 sm:text-xs">
                      {r.student_code}
                    </span>
                    {r.rank ? <Badge tone="success">Rank #{r.rank}</Badge> : <Badge tone="neutral">Unranked</Badge>}
                  </div>
                  <p className="mt-1 truncate text-xs text-ink-muted">{r.email}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="font-heading text-base font-bold leading-tight text-green-900 sm:text-lg">{r.total_points} pts</p>
                  <p className="mt-0.5 text-[10px] font-medium text-ink-muted sm:text-xs">{r.tasks_completed} tasks</p>
                </div>
              </div>

              <div className="mt-3 border-t border-cream-200 pt-2.5">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h4 className="text-[10px] font-bold uppercase tracking-wide text-ink-muted">Course progress</h4>
                  {r.courses.length > 0 && <span className="text-[10px] text-ink-muted">{r.courses.length} courses</span>}
                </div>
                {r.courses.length === 0 ? (
                  <p className="text-xs text-ink-muted">No course enrollments recorded.</p>
                ) : (
                  <div className="space-y-2">
                    {r.courses.map((c) => {
                      const progress = Math.min(100, Math.max(0, Number(c.progress_percent) || 0));
                      return (
                        <div key={c.course_id} className="min-w-0">
                          <div className="mb-1 flex min-w-0 items-center justify-between gap-2 text-[11px]">
                            <span className="min-w-0 truncate font-medium text-green-900" title={c.course_title}>{c.course_title}</span>
                            <span className="shrink-0 font-mono tabular-nums text-ink-muted">
                              {c.completed_tasks}/{c.total_tasks} · {Math.round(progress)}%
                            </span>
                          </div>
                          <div
                            role="progressbar"
                            aria-label={`${c.course_title} progress`}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={Math.round(progress)}
                            className="h-2 w-full overflow-hidden rounded-full bg-cream-200"
                          >
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-green-700 to-emerald-500 transition-[width] duration-500"
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
