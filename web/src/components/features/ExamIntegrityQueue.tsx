"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { AlertTriangle, Check, Clock, Loader2, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface IntegrityReview {
  attempt_id: string;
  exam_id: string;
  exam_title: string;
  course_title: string;
  student_id: string;
  student_name: string;
  attempt_no: number;
  reason: "tab_hidden" | "window_blur" | string;
  flagged_at: string;
}

export function ExamIntegrityQueue() {
  const { getToken } = useAuth();
  const toast = useToast();
  const [reviews, setReviews] = useState<IntegrityReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processingId, setProcessingId] = useState<string | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("teacher");
    }
    return token;
  }, [getToken]);

  const loadReviews = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const token = await resolveToken();
      setReviews(await api<IntegrityReview[]>("/exam-integrity/reviews", token ?? undefined));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load exam integrity reviews.");
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => { void loadReviews(); }, [loadReviews]);

  const approveReexam = async (review: IntegrityReview) => {
    setProcessingId(review.attempt_id);
    try {
      const token = await resolveToken();
      await api(`/exam-integrity/reviews/${review.attempt_id}/approve-reexam`, token ?? undefined, { method: "POST" });
      setReviews((current) => current.filter((item) => item.attempt_id !== review.attempt_id));
      toast(`Re-exam approved for ${review.student_name}. They can start a new attempt from their exam list.`);
    } catch (cause) {
      toast(cause instanceof Error ? cause.message : "Could not approve this re-exam.");
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <section className="space-y-3" aria-labelledby="exam-integrity-queue-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <AlertTriangle size={18} className="text-warning" />
          <h2 id="exam-integrity-queue-title" className="font-heading text-lg font-bold text-green-900">Exam Integrity Reviews</h2>
          {!loading && <Badge tone={reviews.length ? "warning" : "success"}>{reviews.length} pending</Badge>}
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={() => void loadReviews()} disabled={loading}>
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Refresh
        </Button>
      </div>

      {loading ? (
        <Card className="flex h-24 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-green-700" /></Card>
      ) : error ? (
        <Card className="p-4 text-sm text-danger" role="alert">{error}</Card>
      ) : reviews.length === 0 ? (
        <Card className="p-4 text-sm text-ink-muted">No exam integrity reviews are waiting for you.</Card>
      ) : (
        <div className="space-y-3">
          {reviews.map((review) => (
            <Card key={review.attempt_id} className="flex flex-col justify-between gap-4 border-warning/30 p-4 sm:flex-row sm:items-center">
              <div className="min-w-0 space-y-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-green-900">{review.student_name}</p>
                  <span className="text-xs text-ink-muted">· {review.exam_title}</span>
                  <Badge tone="warning">Auto-submitted · flagged</Badge>
                </div>
                <p className="text-xs text-ink-muted">{review.course_title} · Attempt {review.attempt_no} · {review.reason === "tab_hidden" ? "Switched tabs or minimized the exam" : "Exam window lost focus"}</p>
                <p className="inline-flex items-center gap-1 text-[11px] text-ink-muted"><Clock size={12} />{new Date(review.flagged_at).toLocaleString()}</p>
              </div>
              <Button
                type="button"
                variant="primary"
                size="sm"
                className="min-h-11 shrink-0"
                disabled={processingId === review.attempt_id}
                onClick={() => void approveReexam(review)}
              >
                {processingId === review.attempt_id ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                Approve re-exam
              </Button>
            </Card>
          ))}
        </div>
      )}
      <p className="text-[11px] text-ink-muted">Browser focus signals are recorded for faculty review. Approving grants one extra attempt for the selected student.</p>
    </section>
  );
}
