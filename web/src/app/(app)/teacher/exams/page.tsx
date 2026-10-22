"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  Plus,
  Clock,
  HelpCircle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Trash2,
  Pencil,
} from "lucide-react";
import { PageHeader, Card, StatCard } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge, PointsChip } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface TeacherExam {
  id: string;
  title: string;
  course_title?: string | null;
  status: "draft" | "published" | "closed";
  duration_minutes: number;
  questions_count: number;
  task_points?: number | null;
  start_at: string;
  end_at: string;
}

export default function TeacherExamsPage() {
  const { getToken } = useAuth();
  const toast = useToast();
  const [exams, setExams] = useState<TeacherExam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("teacher");
    }
    return token;
  }, [getToken]);

  const loadExams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await resolveToken();
      const data = await api<TeacherExam[]>("/exams", token ?? undefined);
      setExams(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load exams.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    void loadExams();
  }, [loadExams]);

  const changeExamStatus = async (exam: TeacherExam, action: "publish" | "close") => {
    setProcessingId(exam.id);
    try {
      const token = await resolveToken();
      await api(
        `/exams/${exam.id}/${action}`,
        token ?? undefined,
        {
          method: "POST",
          ...(action === "publish" ? { body: JSON.stringify({ task_points: exam.task_points ?? 0 }) } : {}),
        }
      );
      await loadExams();
      toast(action === "publish" ? `Published "${exam.title}".` : `Stopped "${exam.title}".`);
    } catch (err) {
      toast(err instanceof Error ? err.message : `Failed to ${action} exam.`);
    } finally {
      setProcessingId(null);
    }
  };

  const deleteExam = async (exam: TeacherExam) => {
    if (!window.confirm(`Delete "${exam.title}"? This cannot be undone.`)) return;

    setProcessingId(exam.id);
    try {
      const token = await resolveToken();
      await api(`/exams/${exam.id}`, token ?? undefined, { method: "DELETE" });
      setExams((current) => current.filter((item) => item.id !== exam.id));
      toast(`Deleted "${exam.title}".`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to delete exam.");
    } finally {
      setProcessingId(null);
    }
  };

  const publishedCount = exams.filter((exam) => exam.status === "published").length;
  const draftCount = exams.filter((exam) => exam.status === "draft").length;

  return (
    <div className="min-w-0 space-y-6">
      <PageHeader
        title="Manage Course Examinations"
        subtitle="Create, configure, and monitor timed MCQ exams with automated Task Points."
        action={
          <Button href="/teacher/exams/new" variant="primary" size="md">
            <Plus size={16} /> Create New Exam
          </Button>
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatCard value={exams.length} label="Total Managed Exams" />
        <StatCard value={publishedCount} label="Published Exams" />
        <StatCard value={draftCount} label="Draft Exams" />
      </div>

      {loading ? (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white">
          <Loader2 className="h-8 w-8 animate-spin text-green-700" />
        </div>
      ) : error ? (
        <Card className="p-8 text-center">
          <p className="text-sm text-danger">{error}</p>
          <Button variant="secondary" size="sm" className="mt-4" onClick={() => void loadExams()}>
            <RefreshCw size={14} /> Try Again
          </Button>
        </Card>
      ) : exams.length === 0 ? (
        <Card className="p-10 text-center">
          <h3 className="font-heading text-lg font-bold text-green-900">No Exams Yet</h3>
          <p className="mt-1 text-sm text-ink-muted">Create an exam to see it here.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {exams.map((exam) => {
            const start = new Date(exam.start_at);
            const end = new Date(exam.end_at);
            const window = `${start.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })} – ${end.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`;

            return (
              <Card key={exam.id} className="min-w-0 p-4 transition-all hover:shadow-md sm:p-6">
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                  <div className="min-w-0 space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="break-words font-heading text-lg font-bold text-green-900">{exam.title}</h3>
                      {exam.status === "published" && (
                        <Badge tone="success"><CheckCircle2 size={12} className="mr-1" /> Published</Badge>
                      )}
                      {exam.status === "draft" && <Badge tone="warning">Draft</Badge>}
                      {exam.status === "closed" && <Badge tone="danger">Closed</Badge>}
                      <PointsChip points={exam.task_points ?? 0} />
                    </div>

                    <p className="break-words text-xs text-ink-muted">
                      Course: <b className="text-ink">{exam.course_title || "Course"}</b> · Scheduled: {window}
                    </p>

                    <div className="flex flex-wrap gap-4 pt-2 text-xs text-ink-muted">
                      <span className="inline-flex items-center gap-1.5">
                        <HelpCircle size={14} className="text-green-700" />
                        {exam.questions_count} Questions
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <Clock size={14} className="text-green-700" />
                        {exam.duration_minutes} Minutes
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 pt-2 sm:pt-0">
                    {exam.status === "draft" && (
                      <Button
                        variant="primary"
                        size="sm"
                        className="min-h-11"
                        disabled={processingId === exam.id}
                        onClick={() => void changeExamStatus(exam, "publish")}
                      >
                        {processingId === exam.id ? <Loader2 size={14} className="animate-spin" /> : "Publish Now"}
                      </Button>
                    )}
                    {exam.status === "published" && (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="min-h-11"
                        disabled={processingId === exam.id}
                        onClick={() => void changeExamStatus(exam, "close")}
                      >
                        {processingId === exam.id ? <Loader2 size={14} className="animate-spin" /> : "Stop Exam"}
                      </Button>
                    )}
                    {exam.status !== "closed" && (
                      <Button
                        href={`/teacher/exams/new?edit=${exam.id}`}
                        variant="secondary"
                        size="sm"
                        className="min-h-11"
                        aria-label={`Edit ${exam.title}`}
                      >
                        <Pencil size={14} /> Edit
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="danger"
                      size="sm"
                      className="min-h-11"
                      disabled={processingId === exam.id}
                      aria-label={`Delete ${exam.title}`}
                      onClick={() => void deleteExam(exam)}
                    >
                      {processingId === exam.id ? <Loader2 size={14} className="animate-spin" /> : <><Trash2 size={14} /> Delete</>}
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
