"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PointsChip, Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";
import {
  Check,
  X,
  ExternalLink,
  FileText,
  CheckCircle2,
  Loader2,
  Clock,
} from "lucide-react";

export interface PendingTaskReview {
  id: string;
  task_id: string;
  student_id: string;
  task_title?: string;
  student_name?: string;
  points_awarded: number;
  points_available?: number | null;
  status: string;
  submission_note?: string | null;
  submission_url?: string | null;
  submitted_at?: string | null;
}

export function ApprovalQueue({ initial }: { initial?: PendingTaskReview[] }) {
  const { getToken } = useAuth();
  const toast = useToast();

  const [rows, setRows] = useState<PendingTaskReview[]>(initial ?? []);
  const [loading, setLoading] = useState(!initial || initial.length === 0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("teacher");
    }
    return token;
  }, [getToken]);

  const loadPending = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      const data = await api<PendingTaskReview[]>("/tasks/reviews", token ?? undefined);
      setRows(data);
    } catch (err) {
      console.error("Failed to load review queue:", err);
      setLoadError(err instanceof Error ? err.message : "Failed to load task reviews.");
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    loadPending();
  }, [loadPending]);

  const decide = async (item: PendingTaskReview, approve: boolean) => {
    setProcessingId(item.id);
    try {
      const token = await resolveToken();
      const result = await api<{ points_awarded?: number }>(
        `/tasks/completions/${item.id}/${approve ? "approve" : "reject"}`,
        token ?? undefined,
        {
          method: "POST",
          body: JSON.stringify({
            review_note: approve ? "Approved by faculty." : "Needs revision.",
          }),
        }
      );

      setRows((r) => r.filter((x) => x.id !== item.id));
      toast(
        approve
          ? `Approved "${item.task_title || "Task"}". +${result.points_awarded ?? item.points_available ?? item.points_awarded} Task Points credited to ${item.student_name}!`
          : `Submission from ${item.student_name} rejected.`
      );
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to process review.");
    } finally {
      setProcessingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white">
        <Loader2 className="h-8 w-8 animate-spin text-green-700" />
      </div>
    );
  }

  if (loadError) {
    return (
      <Card className="p-4 text-center sm:p-8">
        <p className="break-words text-sm text-danger">{loadError}</p>
        <Button variant="secondary" size="sm" className="mt-4 min-h-11" onClick={() => void loadPending()}>
          Try Again
        </Button>
      </Card>
    );
  }

  if (!rows.length) {
    return (
      <Card className="px-4 py-12 text-center sm:py-16">
        <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-full bg-green-50 text-green-700">
          <CheckCircle2 size={24} />
        </div>
        <h3 className="font-heading text-lg font-bold text-green-900">
          Approval Queue is Empty
        </h3>
        <p className="mx-auto mt-1 max-w-xl text-sm text-ink-muted">
          All student lab and assignment submissions have been reviewed and awarded.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-1 px-1 text-xs text-ink-muted sm:flex-row sm:items-center sm:justify-between">
        <span>{rows.length} pending student submission{rows.length !== 1 ? "s" : ""}</span>
        <span className="sm:text-right">Approving instantly updates student points on the Live Ranking</span>
      </div>

      {rows.map((s) => {
        const student = s.student_name || "Student";
        const task = s.task_title || "Course Assignment";
        const pointsAvailable = s.points_available ?? s.points_awarded;

        return (
          <Card
            key={s.id}
            className="flex min-w-0 flex-col justify-between gap-4 p-4 transition-all hover:shadow-md sm:flex-row sm:items-center sm:p-5"
          >
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="break-words font-heading text-base font-bold text-green-900">
                  {student}
                </span>
                <span className="text-ink-muted">·</span>
                <span className="text-xs font-semibold text-green-700">{task}</span>
              </div>

              {s.submission_note && (
                <p className="flex min-w-0 items-center gap-1.5 text-xs text-ink-muted">
                  <FileText size={13} className="text-green-700 shrink-0" />
                  <span className="min-w-0 truncate max-w-md">{s.submission_note}</span>
                </p>
              )}

              {s.submission_url && (
                <div className="pt-0.5">
                  <a
                    href={s.submission_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-semibold text-green-700 hover:underline"
                  >
                    <span>View Submission Project</span>
                    <ExternalLink size={11} />
                  </a>
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-2 sm:shrink-0 sm:pt-0">
              <PointsChip points={pointsAvailable} />
              <Button
                variant="danger"
                size="sm"
                className="min-h-11 flex-1 sm:flex-none"
                onClick={() => decide(s, false)}
                disabled={processingId === s.id}
              >
                <X size={14} /> Reject
              </Button>
              <Button
                variant="primary"
                size="sm"
                className="min-h-11 flex-1 sm:flex-none"
                onClick={() => decide(s, true)}
                disabled={processingId === s.id}
              >
                {processingId === s.id ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <>
                    <Check size={14} /> Approve (+{pointsAvailable} pts)
                  </>
                )}
              </Button>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
