"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { Badge, PointsChip } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";
import {
  CheckCircle2,
  Clock,
  Link as LinkIcon,
  Send,
  X,
  Loader2,
  AlertCircle,
  Play,
  BookOpen,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { YoutubeVideoTracker } from "@/components/features/YoutubeVideoTracker";

export interface TaskItem {
  id: string;
  course_id: string;
  course_title?: string;
  title: string;
  description?: string | null;
  resource_type?: "video" | "learning_source" | null;
  resource_url?: string | null;
  type: "exam" | "assignment";
  verification: "auto" | "teacher_approval";
  points: number;
  due_at?: string | null;
  my_status?: "pending_review" | "completed" | "rejected" | "revoked" | null;
  points_earned?: number;
  my_video_progress?: number | null;
}

const filters = ["all", "open", "pending", "done"] as const;
const label = {
  all: "All Tasks",
  open: "Open Tasks",
  pending: "Pending Faculty Review",
  done: "Completed & Awarded",
};

export function TaskList({ initial }: { initial?: TaskItem[] }) {
  const { getToken } = useAuth();
  const toast = useToast();

  const [items, setItems] = useState<TaskItem[]>(initial ?? []);
  const [loading, setLoading] = useState(!initial || initial.length === 0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<(typeof filters)[number]>("all");
  const [hiddenCourses, setHiddenCourses] = useState<Set<string>>(() => new Set());
  const [courseId, setCourseId] = useState<string | null>(null);
  const [routeReady, setRouteReady] = useState(false);

  const [submittingTask, setSubmittingTask] = useState<TaskItem | null>(null);
  const [submissionNote, setSubmissionNote] = useState("");
  const [submissionUrl, setSubmissionUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeVideoTaskId, setActiveVideoTaskId] = useState<string | null>(null);
  const [videoProgressError, setVideoProgressError] = useState<string | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("student");
    }
    return token;
  }, [getToken]);

  const loadTasks = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      const query = courseId ? `?course_id=${encodeURIComponent(courseId)}` : "";
      const data = await api<TaskItem[]>(`/tasks${query}`, token ?? undefined);
      setItems(data);
    } catch (err) {
      console.error("Failed to fetch tasks:", err);
      setLoadError(err instanceof Error ? err.message : "Failed to load tasks.");
    } finally {
      setLoading(false);
    }
  }, [courseId, resolveToken]);

  const reportVideoProgress = useCallback(
    (taskId: string, progressPercent: number, videoDurationSeconds: number) => {
      void (async () => {
        try {
          const token = await resolveToken();
          const result = await api<{ progress_percent: number }>(
            `/tasks/${taskId}/video-progress`,
            token ?? undefined,
            {
              method: "POST",
              body: JSON.stringify({
                progress_percent: progressPercent,
                video_duration_seconds: videoDurationSeconds,
              }),
            },
          );
          setVideoProgressError(null);
          setItems((current) =>
            current.map((task) =>
              task.id === taskId
                ? {
                    ...task,
                    my_video_progress: Math.max(
                      task.my_video_progress ?? 0,
                      result.progress_percent,
                    ),
                  }
                : task,
            ),
          );
        } catch (error) {
          console.error("Failed to save video progress:", error);
          setVideoProgressError(
            error instanceof Error ? error.message : "Could not save video progress.",
          );
        }
      })();
    },
    [resolveToken],
  );

  useEffect(() => {
    const requestedCourseId = new URLSearchParams(window.location.search).get("course_id");
    setCourseId(requestedCourseId);
    setRouteReady(true);
  }, []);

  useEffect(() => {
    if (routeReady) void loadTasks();
  }, [loadTasks, routeReady]);

  function getComputedStatus(t: TaskItem): "open" | "pending" | "done" {
    if (t.my_status === "completed") return "done";
    if (t.my_status === "pending_review") return "pending";
    return "open";
  }

  const shown = items.filter((t) => {
    const s = getComputedStatus(t);
    return filter === "all" || s === filter;
  });
  const courseGroups = Object.values(shown.reduce<Record<string, { id: string; title: string; tasks: TaskItem[] }>>((groups, task) => {
    const key = task.course_id || "unassigned";
    if (!groups[key]) groups[key] = { id: key, title: task.course_title || "Other Tasks", tasks: [] };
    groups[key].tasks.push(task);
    return groups;
  }, {})).sort((a, b) => a.title.localeCompare(b.title));

  function handleOpenSubmit(task: TaskItem) {
    setSubmittingTask(task);
    setSubmissionNote("");
    setSubmissionUrl("");
  }

  async function handleConfirmSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!submittingTask) return;

    setIsSubmitting(true);
    try {
      const token = await resolveToken();
      const result = await api<{ status: string; points_awarded: number }>(
        `/tasks/${submittingTask.id}/complete`,
        token ?? undefined,
        {
          method: "POST",
          body: JSON.stringify({
            note: submissionNote.trim() || undefined,
            url: submissionUrl.trim() || undefined,
          }),
        }
      );

      // Refresh list from DB
      await loadTasks();
      toast(
        result.status === "completed"
          ? `Completed "${submittingTask.title}". +${result.points_awarded} points added to your rank!`
          : `Submitted "${submittingTask.title}" for teacher review.`
      );
      setSubmittingTask(null);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to submit task.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      {/* Filter Tabs */}
      {courseId && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cream-200 bg-white px-4 py-3">
          <p className="text-sm text-ink-muted">Showing tasks for the selected course.</p>
          <Link href="/student/tasks" className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-semibold text-green-800 hover:bg-cream-100">Show all course tasks</Link>
        </div>
      )}
      <div className="mb-6 flex flex-wrap gap-2" role="tablist" aria-label="Filter tasks">
        {filters.map((f) => (
          <button
            key={f}
            role="tab"
            aria-selected={filter === f}
            onClick={() => setFilter(f)}
            className={`min-h-11 rounded-full px-4 text-xs font-semibold transition-all ${
              filter === f
                ? "bg-green-700 text-cream-50 shadow-sm"
                : "bg-white text-green-700 ring-1 ring-cream-300 hover:bg-green-50"
            }`}
          >
            {label[f]}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white">
          <Loader2 className="h-8 w-8 animate-spin text-green-700" />
        </div>
      ) : loadError ? (
        <Card className="p-5 text-center sm:p-8">
          <p className="text-sm text-danger">{loadError}</p>
          <Button variant="secondary" size="sm" className="mt-4" onClick={() => void loadTasks()}>
            Try Again
          </Button>
        </Card>
      ) : shown.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-cream-300 bg-white p-6 text-center sm:p-12">
          <CheckCircle2 className="mx-auto h-12 w-12 text-cream-400" />
          <h3 className="mt-3 font-heading text-lg font-bold text-green-900">No Tasks in this category</h3>
          <p className="mt-1 text-sm text-ink-muted">
            All caught up or no active tasks available under the selected filter.
          </p>
        </div>
      ) : (
        <div className="space-y-7">
          {courseGroups.map((group) => (
            <section key={group.id} aria-label={`${group.title} tasks`}>
              <div className="mb-3 flex items-center justify-between gap-3 rounded-xl border border-cream-200 bg-cream-100/70 px-3 py-2.5 sm:px-4">
                <div className="flex min-w-0 items-center gap-2.5">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white text-green-700 shadow-sm">
                    <BookOpen size={17} />
                  </span>
                  <h2 className="truncate font-heading text-sm font-bold text-green-900 sm:text-base">{group.title}</h2>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-ink-muted">
                    {group.tasks.length} task{group.tasks.length === 1 ? "" : "s"}
                  </span>
                  <button
                    type="button"
                    aria-expanded={!hiddenCourses.has(group.id)}
                    aria-controls={`course-tasks-${group.id}`}
                    onClick={() => setHiddenCourses((current) => {
                      const next = new Set(current);
                      if (next.has(group.id)) next.delete(group.id);
                      else next.add(group.id);
                      return next;
                    })}
                    className="inline-flex min-h-11 items-center gap-1 rounded-lg px-2 text-xs font-semibold text-green-800 hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-green-700"
                  >
                    {hiddenCourses.has(group.id) ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
                    <span>{hiddenCourses.has(group.id) ? "Show" : "Hide"}</span>
                  </button>
                </div>
              </div>
              {!hiddenCourses.has(group.id) && <div id={`course-tasks-${group.id}`} className="grid gap-4 md:grid-cols-2">
          {group.tasks.map((t) => {
            const status = getComputedStatus(t);
            const dueStr = t.due_at
              ? new Date(t.due_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })
              : "Ongoing";

            return (
              <Card
                key={t.id}
                className="flex min-w-0 flex-col justify-between gap-3 p-4 transition-all hover:shadow-md sm:p-6"
              >
                <div className="space-y-1.5">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="min-w-0 break-words font-heading text-base font-bold text-green-900">{t.title}</h3>
                    {status === "open" && <Badge tone="info">Open</Badge>}
                    {status === "pending" && <Badge tone="warning">Pending Review</Badge>}
                    {status === "done" && <Badge tone="success">Completed</Badge>}
                  </div>

                  <p className="break-words text-xs text-ink-muted">
                    Due: {dueStr} ·{" "}
                    {t.type === "exam"
                      ? "Awarded on passing exam"
                      : t.verification === "auto"
                        ? "Points awarded immediately on completion"
                        : "Requires faculty approval"}
                  </p>

                  {t.description && (
                    <p className="text-xs text-ink line-clamp-2 mt-1">{t.description}</p>
                  )}
                  {t.resource_url && t.resource_type === "learning_source" && (
                    <a
                      href={t.resource_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-flex min-h-11 items-center gap-1.5 text-xs font-semibold text-green-700 hover:underline"
                    >
                      <LinkIcon size={13} />
                      Open learning resource
                    </a>
                  )}
                  {t.resource_url && t.resource_type === "video" && status === "open" && (
                    <div className="mt-2">
                      <button
                        type="button"
                        onClick={() =>
                          setActiveVideoTaskId((activeId) => activeId === t.id ? null : t.id)
                        }
                        className="inline-flex min-h-11 items-center gap-1.5 text-xs font-semibold text-green-700 hover:underline"
                      >
                        <Play size={13} />
                        {activeVideoTaskId === t.id ? "Hide video" : "Watch video"}
                      </button>
                      {activeVideoTaskId === t.id && (
                        <YoutubeVideoTracker
                          videoUrl={t.resource_url}
                          initialProgress={t.my_video_progress ?? 0}
                          onProgress={(progress, duration) =>
                            reportVideoProgress(t.id, progress, duration)
                          }
                        />
                      )}
                      <p className="mt-1 text-xs text-ink-muted">
                        {Math.floor(t.my_video_progress ?? 0)}% watched · Watch at least 80% to submit.
                      </p>
                    </div>
                  )}
                </div>

                <div className="mt-auto flex flex-col items-stretch gap-3 border-t border-cream-200 pt-3 sm:flex-row sm:items-center sm:justify-between">
                  <PointsChip points={t.points} earned={status === "done"} />
                  {status === "open" &&
                    (t.type === "exam" ? (
                      <Button href="/student/exams" size="sm" variant="secondary" className="w-full justify-center sm:w-auto">
                        Go to Exam
                      </Button>
                    ) : (
                      <Button
                        variant="primary"
                        size="sm"
                        className="w-full justify-center sm:w-auto"
                        disabled={t.resource_type === "video" && (t.my_video_progress ?? 0) < 80}
                        onClick={() => handleOpenSubmit(t)}
                      >
                        {t.resource_type === "video" && (t.my_video_progress ?? 0) < 80
                          ? "Watch 80% to Unlock"
                          : t.verification === "auto"
                            ? "Complete Task"
                            : "Submit for Review"}
                      </Button>
                    ))}
                  {status === "pending" && (
                    <span className="text-xs font-medium text-warning flex items-center gap-1">
                      <Clock size={13} /> Awaiting Faculty
                    </span>
                  )}
                  {status === "done" && (
                    <span className="text-xs font-medium text-success flex items-center gap-1">
                      <CheckCircle2 size={13} /> Points Credited
                    </span>
                  )}
                </div>
              </Card>
            );
          })}
              </div>}
            </section>
          ))}
        </div>
      )}

      {videoProgressError && (
        <div className="fixed inset-x-3 bottom-3 z-40 flex items-start gap-2 rounded-xl border border-danger/20 bg-white p-3 text-sm text-danger shadow-lg sm:inset-x-auto sm:right-4 sm:bottom-4 sm:max-w-sm">
          <AlertCircle size={16} />
          <span>{videoProgressError}</span>
        </div>
      )}

      {/* Task Submission Modal */}
      {submittingTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-3 sm:p-4">
          <div
            className="absolute inset-0 bg-green-900/50 backdrop-blur-sm"
            onClick={() => setSubmittingTask(null)}
          />
          <div className="relative my-auto max-h-[calc(100dvh-1.5rem)] w-full max-w-lg overflow-y-auto rounded-2xl border border-cream-300 bg-white p-4 shadow-2xl sm:max-h-[calc(100dvh-2rem)] sm:p-6">
            <div className="flex items-start justify-between gap-3 border-b border-cream-200 pb-3">
              <div className="min-w-0">
                <h3 className="font-heading text-lg font-bold text-green-900">
                  Submit Task for Faculty Review
                </h3>
                <p className="break-words text-xs text-ink-muted">{submittingTask.title}</p>
              </div>
              <button
                onClick={() => setSubmittingTask(null)}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-lg text-ink-muted hover:bg-cream-100 hover:text-ink"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleConfirmSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Submission Notes / Text Summary
                </label>
                <textarea
                  rows={3}
                  required
                  value={submissionNote}
                  onChange={(e) => setSubmissionNote(e.target.value)}
                  placeholder="Describe your solution, methodology, or answers..."
                  className="w-full rounded-lg border border-cream-300 p-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-green-900 mb-1">
                  Project / Repository / Drive URL (Optional)
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-ink-muted">
                    <LinkIcon size={14} />
                  </span>
                  <input
                    type="url"
                    value={submissionUrl}
                    onChange={(e) => setSubmissionUrl(e.target.value)}
                    placeholder="https://github.com/... or Google Drive link"
                    className="h-11 w-full rounded-lg border border-cream-300 pl-9 pr-3 text-sm text-ink focus:border-green-700 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-col-reverse items-stretch justify-end gap-2 border-t border-cream-200 pt-3 sm:flex-row sm:items-center sm:gap-3">
                <button
                  type="button"
                  onClick={() => setSubmittingTask(null)}
                  className="min-h-11 rounded-lg border border-cream-300 px-4 text-xs font-semibold text-ink-muted hover:bg-cream-100 sm:min-h-9"
                >
                  Cancel
                </button>
                <Button type="submit" variant="primary" size="sm" disabled={isSubmitting} className="w-full justify-center sm:w-auto">
                  {isSubmitting ? (
                    <>
                      <Loader2 size={14} className="animate-spin mr-1.5" /> Submitting...
                    </>
                  ) : (
                    <>
                      <Send size={14} /> Submit Task
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
