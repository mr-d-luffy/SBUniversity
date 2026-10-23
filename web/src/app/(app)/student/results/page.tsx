"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  FileCheck,
  Download,
  Award,
  CheckCircle2,
  XCircle,
  Clock,
  Trophy,
  Loader2,
} from "lucide-react";
import { PageHeader, Card, StatCard } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { api, downloadAndOpenPdf, getDevAuthToken } from "@/lib/api";

interface ApiResult {
  id: string;
  attempt_id: string;
  exam_id: string;
  student_id: string;
  score: number;
  total_marks: number;
  percentage: number;
  grade: string;
  passed: boolean;
  time_taken_sec: number;
  rank_in_exam?: number | null;
  created_at: string;
  exam_title?: string | null;
  course_title?: string | null;
  student_name?: string | null;
}

export default function StudentResultsPage() {
  const { getToken } = useAuth();
  const toast = useToast();

  const [results, setResults] = useState<ApiResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("student");
    }
    return token;
  }, [getToken]);

  const loadResults = useCallback(async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const data = await api<ApiResult[]>("/results", token ?? undefined).catch(() => []);
      setResults(data || []);
    } catch (err) {
      console.error("Failed to load results:", err);
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  const handleDownloadPdf = async (result: ApiResult) => {
    setDownloadingId(result.id);
    try {
      const token = await resolveToken();
      const examTitle = result.exam_title || "Exam";
      const filename = `Result_${examTitle.replace(/\s+/g, "_")}.pdf`;

      await downloadAndOpenPdf(`/results/${result.id}/pdf`, filename, token ?? undefined);
      toast(`Result Statement opened in new tab and downloaded for ${examTitle}!`);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Failed to download Result Statement.");
    } finally {
      setDownloadingId(null);
    }
  };

  const totalExams = results.length;
  const passedExams = results.filter((r) => r.passed).length;
  const avgPercentage = totalExams > 0
    ? (results.reduce((acc, r) => acc + r.percentage, 0) / totalExams).toFixed(1)
    : "0.0";
  const passRate = totalExams > 0 ? Math.round((passedExams / totalExams) * 100) : 100;

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Results"
        subtitle="Official performance records and downloadable Result Statements."
      />

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard value={totalExams} label="Exams Taken" />
        <StatCard value={passedExams} label="Exams Passed" hint={`${passRate}% pass record`} />
        <StatCard value={`${avgPercentage}%`} label="Average Score" />
        <StatCard value={passedExams > 0 ? "A+" : "-"} label="Top Grade Earned" />
      </div>

      {/* Results List */}
      {loading ? (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white shadow-sm">
          <Loader2 className="h-8 w-8 animate-spin text-green-700" />
        </div>
      ) : results.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-cream-300 bg-white p-6 text-center shadow-sm sm:p-12">
          <FileCheck className="mx-auto h-12 w-12 text-cream-400" />
          <h3 className="mt-3 font-heading text-lg font-bold text-green-900">No Exam Results Yet</h3>
          <p className="mt-1 text-sm text-ink-muted">
            You haven&apos;t completed any course examinations yet. Take an active exam to receive your official statement.
          </p>
          <div className="mt-4">
            <Button href="/student/exams" variant="primary" size="sm">
              View Available Exams
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {results.map((res) => {
            const examTitle = res.exam_title || "Course Examination";
            const courseTitle = res.course_title || "Academic Course";
            const dateStr = new Date(res.created_at).toLocaleDateString("en-US", {
              month: "long",
              day: "numeric",
              year: "numeric",
            });
            const minutes = Math.floor(res.time_taken_sec / 60);
            const seconds = res.time_taken_sec % 60;
            const timeStr = `${minutes}m ${seconds}s`;

            return (
              <Card
                key={res.id}
                className="flex flex-col justify-between gap-4 transition-all duration-150 hover:shadow-md sm:flex-row sm:items-center"
              >
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="min-w-0 break-words font-heading text-base font-bold text-green-900">
                      {examTitle}
                    </h3>
                    {res.passed ? (
                      <Badge tone="success">
                        <CheckCircle2 size={12} className="mr-0.5" /> Passed
                      </Badge>
                    ) : (
                      <Badge tone="danger">
                        <XCircle size={12} className="mr-0.5" /> Failed
                      </Badge>
                    )}
                    <span className="rounded-md bg-cream-200 px-2 py-0.5 font-mono text-xs font-bold text-green-900">
                      Grade {res.grade}
                    </span>
                  </div>

                  <p className="text-xs text-ink-muted">
                    {courseTitle} · Taken on {dateStr}
                  </p>

                  <div className="flex flex-wrap items-center gap-4 text-xs font-medium text-ink-muted">
                    <span className="flex items-center gap-1">
                      <Clock size={13} className="text-green-700" /> {timeStr}
                    </span>
                    <span className="flex items-center gap-1 font-bold text-green-900">
                      <Award size={13} className="text-bordo-700" /> {res.score} / {res.total_marks} ({res.percentage}%)
                    </span>
                    {res.rank_in_exam && (
                      <span className="flex items-center gap-1 text-green-700 font-semibold">
                        <Trophy size={13} /> Rank #{res.rank_in_exam}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex w-full items-center gap-2 pt-2 sm:w-auto sm:shrink-0 sm:pt-0">
                  <Button
                    variant="primary"
                    size="sm"
                    className="w-full justify-center sm:w-auto"
                    onClick={() => handleDownloadPdf(res)}
                    disabled={downloadingId === res.id}
                  >
                    {downloadingId === res.id ? (
                      <>
                        <Loader2 size={14} className="animate-spin mr-1.5" /> Generating...
                      </>
                    ) : (
                      <>
                        <Download size={14} /> Download PDF (New Tab)
                      </>
                    )}
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
