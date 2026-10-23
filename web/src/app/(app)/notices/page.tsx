"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  Pin,
  Megaphone,
  Search,
  User,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card, PageHeader } from "@/components/ui/Card";
import { api, getDevAuthToken } from "@/lib/api";

interface ApiNotice {
  id: string;
  author_id: string;
  course_id?: string | null;
  title: string;
  body: string;
  audience: "all" | "students" | "teachers" | "course";
  priority: "normal" | "important" | "urgent";
  status: "draft" | "published" | "archived";
  is_pinned: boolean;
  published_at?: string | null;
  expires_at?: string | null;
  author_name?: string | null;
  course_title?: string | null;
  created_at: string;
}

const tone = { normal: "neutral", important: "info", urgent: "urgent" } as const;

export default function NoticesPage() {
  const { getToken } = useAuth();
  const [notices, setNotices] = useState<ApiNotice[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "pinned" | "urgent" | "important">("all");
  const [search, setSearch] = useState("");

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken("student");
    }
    return token;
  }, [getToken]);

  const loadNotices = useCallback(async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const data = await api<ApiNotice[]>("/notices", token ?? undefined).catch(() => []);
      setNotices(data || []);
    } catch (err) {
      console.error("Failed to load notices:", err);
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    loadNotices();
  }, [loadNotices]);

  const filtered = notices.filter((n) => {
    const author = n.author_name || "University Administration";
    const matchesSearch =
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.body.toLowerCase().includes(search.toLowerCase()) ||
      author.toLowerCase().includes(search.toLowerCase());

    if (!matchesSearch) return false;
    if (filter === "pinned") return n.is_pinned;
    if (filter === "urgent") return n.priority === "urgent";
    if (filter === "important") return n.priority === "important";
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="University Notice Board"
        subtitle="Official communications, exam circulars, and departmental announcements from the University Database."
        action={
          <span className="flex items-center gap-2 text-sm text-ink-muted">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-success" />
            Live Sync
          </span>
        }
      />

      {/* Filter and Search Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {(["all", "pinned", "urgent", "important"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`min-h-11 rounded-full px-3.5 text-xs font-semibold capitalize transition-colors ${
                filter === f
                  ? "bg-green-700 text-cream-50"
                  : "bg-white text-green-700 ring-1 ring-cream-300 hover:bg-green-50"
              }`}
            >
              {f === "all" ? "All Notices" : f}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:max-w-xs">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-ink-placeholder">
            <Search size={15} />
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search announcements..."
            className="h-11 w-full rounded-lg border border-cream-300 bg-white pl-9 pr-3 text-sm text-ink placeholder:text-ink-placeholder focus:border-green-700 focus:outline-none"
          />
        </div>
      </div>

      {/* Notices List */}
      {loading ? (
        <div className="flex h-56 items-center justify-center rounded-2xl border border-cream-300 bg-white shadow-sm">
          <Loader2 className="h-8 w-8 animate-spin text-green-700" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-cream-300 bg-white p-6 text-center sm:p-12">
          <Megaphone className="mx-auto h-12 w-12 text-cream-400" />
          <h3 className="mt-3 font-heading text-lg font-bold text-green-900">No Announcements Found</h3>
          <p className="mt-1 text-sm text-ink-muted">
            No circulars match your current filter criteria or query.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((n) => {
            const dateStr = n.created_at
              ? new Date(n.created_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })
              : "Recent";

            return (
              <Card
                key={n.id}
                className={`p-4 transition-all hover:shadow-md sm:p-6 ${
                  n.priority === "urgent" ? "border-l-4 border-l-bordo-700" : ""
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2 border-b border-cream-200 pb-3">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <h2 className="min-w-0 break-words font-heading text-base font-bold text-green-900">{n.title}</h2>
                    {n.is_pinned && (
                      <Badge tone="info">
                        <Pin size={11} className="mr-0.5" /> Pinned
                      </Badge>
                    )}
                    <Badge tone={tone[n.priority]}>{n.priority}</Badge>
                    {n.course_title && (
                      <span className="rounded bg-cream-200 px-2 py-0.5 text-[10px] font-semibold text-green-900">
                        {n.course_title}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-ink-muted">{dateStr}</span>
                </div>

                <p className="mt-3 whitespace-pre-line break-words text-sm leading-relaxed text-ink">{n.body}</p>

                <div className="mt-4 flex flex-col items-start justify-between gap-3 border-t border-cream-200 pt-3 text-xs text-ink-muted sm:flex-row sm:items-center">
                  <span className="flex min-w-0 items-start gap-1.5">
                    <User size={13} className="text-green-700" />
                    <span>
                      Posted by <b className="text-green-900">{n.author_name || "Administration"}</b>
                    </span>
                  </span>
                  <span className="rounded bg-cream-100 px-2 py-0.5 text-[10px] font-semibold text-green-900">
                    Official University Circular
                  </span>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
