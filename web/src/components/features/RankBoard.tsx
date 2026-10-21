"use client";

import React, { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { useAuth, useUser } from "@clerk/nextjs";
import { Trophy, Filter, Loader2, Sparkles, RefreshCw } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { api, getDevAuthToken } from "@/lib/api";

export interface RankedStudent {
  rank: number;
  student_id: string;
  name: string;
  avatar_url?: string | null;
  points: number;
  tasks_completed: number;
}

interface LeaderboardApiResponse {
  updated_at: string;
  scope: string;
  course_id?: string | null;
  items: RankedStudent[];
}

interface MyRankApiResponse {
  student_id: string;
  rank?: number | null;
  points: number;
  tasks_completed: number;
}

interface CourseOption {
  id: string;
  code: string;
  title: string;
}

interface EnrollmentOption {
  id: string;
  course_id: string;
  code?: string;
  title?: string;
  course?: {
    code: string;
    title: string;
  } | null;
}

const RANK_TIERS = [
  {
    rank: 1,
    title: "Champion Rank",
    asset: "/ranks/rank-1.png",
    tag: "#1 Grandmaster",
    pillBg: "bg-gradient-to-r from-amber-500 to-purple-600 text-white",
    cardBorder: "border-2 border-amber-400 shadow-xl bg-gradient-to-b from-white via-amber-50/20 to-purple-50/20",
    glow: "shadow-amber-400/20",
  },
  {
    rank: 2,
    title: "Master Rank",
    asset: "/ranks/rank-2.png",
    tag: "#2 Master",
    pillBg: "bg-amber-600 text-white",
    cardBorder: "border-t-4 border-t-amber-500 border-cream-200 shadow-md bg-white",
    glow: "shadow-amber-500/10",
  },
  {
    rank: 3,
    title: "Emerald Rank",
    asset: "/ranks/rank-3.png",
    tag: "#3 Elite",
    pillBg: "bg-emerald-600 text-white",
    cardBorder: "border-t-4 border-t-emerald-500 border-cream-200 shadow-md bg-white",
    glow: "shadow-emerald-500/10",
  },
  {
    rank: 4,
    title: "Challenger Rank",
    asset: "/ranks/rank-4.png",
    tag: "#4 Honors",
    pillBg: "bg-orange-700 text-cream-50",
    cardBorder: "border-t-4 border-t-orange-600 border-cream-200 shadow-md bg-white",
    glow: "shadow-orange-500/10",
  },
];

const initials = (n: string) =>
  n
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export function RankBoard({
  initialStudents,
  meId,
}: {
  initialStudents?: RankedStudent[];
  meId?: string;
}) {
  const { getToken } = useAuth();
  const { user } = useUser();

  const [courses, setCourses] = useState<CourseOption[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState<string>("overall");
  const [students, setStudents] = useState<RankedStudent[]>(initialStudents ?? []);
  const [myRank, setMyRank] = useState<MyRankApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Authenticated token resolver
  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("student");
    }
    return token;
  }, [getToken]);

  // Fetch leaderboard data
  const fetchData = useCallback(
    async (showLoading = true) => {
      if (showLoading) setLoading(true);
      else setRefreshing(true);

      try {
        const token = await resolveToken();
        const scope = selectedCourseId === "overall" ? "overall" : "course";
        const queryParams = new URLSearchParams({
          scope,
          limit: "25",
        });
        if (selectedCourseId !== "overall") {
          queryParams.set("course_id", selectedCourseId);
        }

        const [lbData, meData] = await Promise.all([
          api<LeaderboardApiResponse>(`/ranking/top?${queryParams.toString()}`, token ?? undefined).catch(() => ({
            updated_at: new Date().toISOString(),
            scope: "overall",
            items: [],
          })),
          api<MyRankApiResponse>(`/ranking/me?scope=${scope}${selectedCourseId !== "overall" ? `&course_id=${selectedCourseId}` : ""}`, token ?? undefined).catch(
            () => null
          ),
        ]);

        if (lbData?.items) {
          setStudents(lbData.items);
        }
        if (meData) {
          setMyRank(meData);
        }
      } catch (err) {
        console.error("Failed to load live ranking:", err);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [resolveToken, selectedCourseId]
  );

  // Fetch courses on mount for dropdown
  useEffect(() => {
    async function loadCourses() {
      try {
        const token = await resolveToken();
        const data = await api<EnrollmentOption[]>("/student/courses", token ?? undefined).catch(() => []);
        if (data && Array.isArray(data)) {
          setCourses(
            data.map((c) => ({
              id: c.course_id || c.id,
              code: c.course?.code || c.code || "COURSE",
              title: c.course?.title || c.title || "Course",
            }))
          );
        }
      } catch {
        // keep empty courses
      }
    }
    loadCourses();
  }, [resolveToken]);

  // Fetch ranking when filter changes
  useEffect(() => {
    fetchData(true);
  }, [fetchData]);

  // SSE or Poll every 10 seconds for real-time live ranking
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData(false);
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const top = students.slice(0, 4);
  const getStudentAvatar = (student: RankedStudent) => {
    const signedInStudentId = meId || myRank?.student_id;
    return student.student_id === signedInStudentId
      ? user?.imageUrl || student.avatar_url
      : student.avatar_url;
  };

  return (
    <div className="space-y-6">
      {/* Filters & Live Status Bar */}
      <div className="flex flex-col items-stretch justify-between gap-3 rounded-xl border border-cream-300 bg-white p-3.5 shadow-sm sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Filter size={16} className="text-green-700" />
          <span className="text-xs font-semibold text-green-900">Leaderboard Scope:</span>
          <select
            value={selectedCourseId}
            onChange={(e) => setSelectedCourseId(e.target.value)}
            className="h-11 w-full min-w-0 rounded-lg border border-cream-300 bg-cream-50 px-3 text-xs font-medium text-ink focus:border-green-700 focus:outline-none sm:w-auto sm:max-w-[min(24rem,55vw)]"
          >
            <option value="overall">All Courses (University Overall)</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} – {c.title}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 sm:justify-end">
          <button
            onClick={() => fetchData(false)}
            disabled={refreshing}
            className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-2 text-xs font-medium text-ink-muted transition-colors hover:text-green-900"
          >
            <RefreshCw size={12} className={clsx(refreshing && "animate-spin text-green-700")} />
            <span>Sync</span>
          </button>
          <div className="flex items-center gap-2 text-xs font-semibold text-green-700">
            <span className="h-2.5 w-2.5 rounded-full bg-success animate-pulse" />
            <span>Live Auto-Sync Active</span>
          </div>
        </div>
      </div>

      {/* Top 4 Live Podium with 3D Rank Badges */}
      {loading && students.length === 0 ? (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white">
          <Loader2 className="h-8 w-8 animate-spin text-green-700" />
        </div>
      ) : top.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-cream-300 bg-white p-6 text-center sm:p-12">
          <Trophy className="mx-auto h-12 w-12 text-cream-400" />
          <h3 className="mt-3 font-heading text-lg font-bold text-green-900">Leaderboard Initializing</h3>
          <p className="mt-1 text-sm text-ink-muted">
            Complete active tasks and examinations to earn Task Points and rank on the live university podium!
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2 lg:grid-cols-4 lg:items-end" aria-live="polite">
          {top.map((s, i) => {
            const isRank1 = i === 0;
            const podiumRank = i + 1;
            const tier = RANK_TIERS[i] || RANK_TIERS[3];
            const avatarUrl = getStudentAvatar(s);

            return (
              <Card
                key={s.student_id || i}
                className={clsx(
                  "relative min-w-0 p-4 text-center transition-all duration-200 hover:-translate-y-1 hover:shadow-xl sm:p-6",
                  tier.cardBorder,
                  tier.glow,
                  isRank1 && "min-[420px]:col-span-2 py-6 lg:col-span-1 lg:order-none order-first sm:py-8"
                )}
              >
                {/* 3D Rank Level Badge Emblem */}
                <div className="relative mx-auto -mt-2 mb-3 flex flex-col items-center">
                  <div className="relative group">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={tier.asset}
                      alt={tier.title}
                      className={clsx(
                        "object-contain drop-shadow-md transition-transform duration-300 group-hover:scale-110",
                        isRank1 ? "h-20 w-20" : "h-16 w-16"
                      )}
                    />
                  </div>
                  <span
                    className={clsx(
                      "mt-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider shadow-sm",
                      tier.pillBg
                    )}
                  >
                    {tier.tag}
                  </span>
                </div>

                {/* Student Avatar / Initials */}
                <div className="mx-auto mb-2">
                  {avatarUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={avatarUrl}
                      alt={s.name}
                      className="mx-auto h-12 w-12 rounded-full object-cover ring-2 ring-cream-300 shadow-sm"
                    />
                  ) : (
                    <div
                      className={clsx(
                        "mx-auto grid place-items-center rounded-full font-heading font-bold shadow-sm",
                        isRank1
                          ? "h-12 w-12 bg-cream-200 text-green-900 ring-2 ring-rank-gold/40 text-base"
                          : "h-10 w-10 bg-cream-100 text-green-700 text-sm"
                      )}
                    >
                      {initials(s.name)}
                    </div>
                  )}
                </div>

                <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-muted">
                  Rank #{podiumRank}
                </p>
                <h3 className="break-words font-heading text-base font-bold text-green-900">
                  {s.name}
                </h3>

                {/* Points value */}
                <p
                  className={clsx(
                    "font-heading font-bold mt-1.5",
                    isRank1 ? "text-3xl text-bordo-700" : "text-2xl text-green-700"
                  )}
                >
                  {s.points} pts
                </p>

                <p className="mt-1 text-xs text-ink-muted font-medium">
                  {s.tasks_completed} tasks completed
                </p>
              </Card>
            );
          })}
        </div>
      )}

      {/* "Your Rank" Sticky Banner Card */}
      {myRank && myRank.points > 0 && (
        <div className="flex flex-col items-start justify-between gap-4 rounded-2xl bg-gradient-to-r from-green-800 to-green-700 px-4 py-4 text-cream-50 shadow-lg sm:flex-row sm:items-center sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-xl bg-cream-200 text-green-900 font-heading text-lg font-bold shadow-inner">
              #{myRank.rank ?? "-"}
            </span>
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-wider text-cream-300 font-semibold">
                Your Current University Ranking Standing
              </p>
              <p className="break-words font-heading text-lg font-bold text-cream-50">
                {user?.fullName ?? "You"} (Student)
              </p>
            </div>
          </div>

          <div className="text-left sm:text-right">
            <p className="font-heading text-2xl font-bold text-cream-200">
              {myRank.points} pts
            </p>
            <p className="text-xs text-cream-300">
              {myRank.tasks_completed} tasks completed
            </p>
          </div>
        </div>
      )}

      {/* Full Leaderboard Table */}
      <div className="space-y-2 md:hidden" aria-label="Leaderboard">
        {students.length === 0 ? (
          <div className="rounded-xl border border-cream-300 bg-white p-5 text-center text-xs text-ink-muted">
            No ranked students recorded for this scope yet.
          </div>
        ) : (
          students.map((s, idx) => {
            const rankNum = idx + 1;
            const isMe = s.student_id === myRank?.student_id;
            const avatarUrl = getStudentAvatar(s);
            return (
              <Card
                key={s.student_id || idx}
                className={clsx(
                  "flex min-w-0 items-center gap-3 p-3",
                  isMe && "border-green-700 bg-green-50/90",
                )}
              >
                <span
                  className={clsx(
                    "grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold",
                    rankNum === 1
                      ? "bg-rank-gold text-white"
                      : rankNum === 2
                        ? "bg-rank-silver text-white"
                        : rankNum === 3
                          ? "bg-rank-bronze text-white"
                          : "bg-cream-200 text-green-900",
                  )}
                >
                  {rankNum}
                </span>
                {avatarUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={avatarUrl} alt="" className="h-9 w-9 shrink-0 rounded-full object-cover" />
                ) : null}
                <div className="min-w-0 flex-1">
                  <p className="break-words text-sm font-semibold text-green-900">
                    {s.name} {isMe && <span className="text-[10px] font-bold text-green-700">YOU</span>}
                  </p>
                  <p className="text-xs text-ink-muted">{s.tasks_completed} tasks completed</p>
                </div>
                <span className="shrink-0 text-right font-heading text-sm font-bold text-green-900">
                  {s.points} pts
                </span>
              </Card>
            );
          })
        )}
      </div>

      <div className="hidden overflow-x-auto rounded-xl border border-cream-300 bg-white shadow-sm md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Comprehensive University Task Points Leaderboard</caption>
          <thead className="bg-cream-100 text-xs font-semibold uppercase text-green-900">
            <tr>
              <th className="px-5 py-3.5">Rank</th>
              <th className="px-5 py-3.5">Student Name</th>
              <th className="px-5 py-3.5">Tasks Done</th>
              <th className="px-5 py-3.5 text-right">Total Task Points</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-cream-300">
            {students.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-5 py-8 text-center text-ink-muted text-xs">
                  No ranked students recorded for this scope yet.
                </td>
              </tr>
            ) : (
              students.map((s, idx) => {
                const rankNum = idx + 1;
                const isMe = s.student_id === myRank?.student_id;
                const avatarUrl = getStudentAvatar(s);

                return (
                  <tr
                    key={s.student_id || idx}
                    className={clsx(
                      "transition-colors",
                      isMe
                        ? "bg-green-50/90 font-semibold text-green-900"
                        : "hover:bg-cream-50/50 text-ink"
                    )}
                  >
                    <td className="px-5 py-3.5 font-heading">
                      <span
                        className={clsx(
                          "inline-grid h-7 w-7 place-items-center rounded-full text-xs font-bold",
                          rankNum === 1
                            ? "bg-rank-gold text-white"
                            : rankNum === 2
                            ? "bg-rank-silver text-white"
                            : rankNum === 3
                            ? "bg-rank-bronze text-white"
                            : "bg-cream-200 text-green-900"
                        )}
                      >
                        {rankNum}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        {avatarUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={avatarUrl}
                            alt=""
                            className="h-6 w-6 rounded-full object-cover"
                          />
                        ) : null}
                        <span>{s.name}</span>
                        {isMe && (
                          <span className="rounded-full bg-green-700 px-2 py-0.5 text-[10px] font-bold text-cream-50">
                            YOU
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-ink-muted">{s.tasks_completed}</td>
                    <td className="px-5 py-3.5 text-right font-heading font-bold text-green-900">
                      {s.points} pts
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
