"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Check, Clipboard, KeyRound, Loader2, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { api, getDevAuthToken } from "@/lib/api";

interface CourseKeyRequest {
  id: string;
  course_id: string;
  course_title: string;
  status: "pending" | "approved" | "rejected" | "activated";
  requested_at: string;
  student_id: string;
  student_name: string;
  student_email: string;
  access_key?: string | null;
}

type RequestFilter = "pending" | "all";

export function AdminCourseKeyRequests() {
  const { getToken } = useAuth();
  const toast = useToast();
  const [requests, setRequests] = useState<CourseKeyRequest[]>([]);
  const [filter, setFilter] = useState<RequestFilter>("pending");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (
      !token &&
      (process.env.NEXT_PUBLIC_DEMO_MODE === "true" ||
        process.env.NODE_ENV === "development")
    ) {
      token = getDevAuthToken("admin");
    }
    return token;
  }, [getToken]);

  const loadRequests = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const token = await resolveToken();
      const loadedRequests = await api<CourseKeyRequest[]>(
        "/admin/courses/key-requests",
        token ?? undefined,
      );
      setRequests(loadedRequests);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Failed to load key requests.",
      );
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    void loadRequests();
  }, [loadRequests]);

  async function reviewRequest(
    request: CourseKeyRequest,
    action: "approve" | "reject",
  ) {
    setReviewingId(request.id);
    try {
      const token = await resolveToken();
      const reviewed = await api<CourseKeyRequest>(
        `/admin/courses/key-requests/${request.id}/${action}`,
        token ?? undefined,
        { method: "POST" },
      );
      setRequests((current) =>
        current.map((item) => (item.id === reviewed.id ? reviewed : item)),
      );
      toast(
        action === "approve"
          ? `Approved ${request.student_name}'s request.`
          : `Rejected ${request.student_name}'s request.`,
      );
    } catch (error) {
      toast(error instanceof Error ? error.message : "Could not review the request.");
    } finally {
      setReviewingId(null);
    }
  }

  async function copyAccessKey(key: string) {
    try {
      await navigator.clipboard.writeText(key);
      toast("Course key copied.");
    } catch {
      toast("Could not copy the key. Select and copy it manually.");
    }
  }

  const pendingCount = requests.filter(
    (request) => request.status === "pending",
  ).length;
  const visibleRequests =
    filter === "pending"
      ? requests.filter((request) => request.status === "pending")
      : requests;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-lg font-bold text-green-900">
            {pendingCount} pending request{pendingCount === 1 ? "" : "s"}
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            Approve a request to generate a single-use course activation key.
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          onClick={() => void loadRequests()}
          disabled={loading}
        >
          <RotateCw size={15} className={loading ? "animate-spin" : ""} />
          Refresh
        </Button>
      </div>

      <div className="flex gap-2" role="group" aria-label="Filter course key requests">
        <Button
          type="button"
          size="sm"
          variant={filter === "pending" ? "primary" : "secondary"}
          onClick={() => setFilter("pending")}
        >
          Pending ({pendingCount})
        </Button>
        <Button
          type="button"
          size="sm"
          variant={filter === "all" ? "primary" : "secondary"}
          onClick={() => setFilter("all")}
        >
          All requests ({requests.length})
        </Button>
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center rounded-2xl border border-cream-300 bg-white">
          <Loader2 className="h-7 w-7 animate-spin text-green-700" />
        </div>
      ) : loadError ? (
        <Card className="p-8 text-center">
          <p role="alert" className="text-sm text-danger">{loadError}</p>
          <Button
            variant="secondary"
            size="sm"
            className="mt-4"
            onClick={() => void loadRequests()}
          >
            Retry
          </Button>
        </Card>
      ) : visibleRequests.length === 0 ? (
        <Card className="p-10 text-center">
          <KeyRound className="mx-auto h-10 w-10 text-cream-400" />
          <h2 className="mt-3 font-heading text-lg font-bold text-green-900">
            {filter === "pending" ? "No pending requests" : "No key requests yet"}
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            {filter === "pending"
              ? "New student course-key requests will appear here."
              : "Student course-key requests will appear here."}
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {visibleRequests.map((request) => (
            <Card
              key={request.id}
              className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"
            >
              <div className="min-w-0">
                <p className="font-semibold text-green-900">{request.course_title}</p>
                <p className="text-sm text-ink-muted">
                  {request.student_name} · {request.student_email}
                </p>
                <p className="text-xs capitalize text-ink-muted">
                  {request.status} · {new Date(request.requested_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {request.access_key && (
                  <>
                    <code className="rounded bg-cream-100 px-2 py-1 text-sm font-bold tracking-wide text-green-900">
                      {request.access_key}
                    </code>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        request.access_key && void copyAccessKey(request.access_key)
                      }
                    >
                      <Clipboard size={14} /> Copy key
                    </Button>
                  </>
                )}
                {request.status === "pending" && (
                  <>
                    <Button
                      type="button"
                      size="sm"
                      variant="primary"
                      disabled={reviewingId === request.id}
                      onClick={() => void reviewRequest(request, "approve")}
                    >
                      {reviewingId === request.id ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Check size={14} />
                      )}
                      Approve
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={reviewingId === request.id}
                      onClick={() => void reviewRequest(request, "reject")}
                    >
                      Reject
                    </Button>
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
