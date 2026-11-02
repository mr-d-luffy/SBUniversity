"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Image from "next/image";
import {
  Pin,
  Megaphone,
  Search,
  User,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/Card";
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
const stickerArtworks = [
  "100753-earlyverifiedbotdeveloper.png",
  "12071-cybercubs-yas.png",
  "135775-security.png",
  "136927-cookiebiscuit.png",
  "140447-gamemakerlogo.png",
  "15158-lucyfacepalm.png",
  "166628-isro.png",
  "188088-googleplay.png",
  "215782-neon-twitter-bird.png",
  "23232-googleit.png",
  "23556-rebfoff.png",
  "23571-google-cat-upset.png",
  "267825-neon-heart.png",
  "27096-cc-grind.png",
  "29552-nvidia.png",
  "300997-neon-youtube-playbutton.png",
  "30427-doxbinlogo.png",
  "309313-neon-peach.png",
  "314514-githubcopilot.png",
  "3203-reactjs.png",
  "3225_kali.png",
  "32496-lucypadoru.png",
  "331825-visualstudiocode.png",
  "335262-neon-pinterest-logo.png",
  "335262-neon-reddit-icon.png",
  "34104-googlechrome.png",
  "378513-unreal.png",
  "38870-cybercubs-dj.png",
  "4092-linux.png",
  "4161-rebpadoru.png",
  "419890-edgerunners.png",
  "42588-cybercubs-hangry.png",
  "472033-neon-spotify-icon.png",
  "47272-flutter.png",
  "4744_arch.png",
  "487065-serverdeveloper.png",
  "51316-google-cat-smirk.png",
  "515686-developer.png",
  "522527-owner.png",
  "52619-google-cat-cry-laugh.png",
  "52798-google-cat-angry.png",
  "565953-neon-pizza.png",
  "580334-earlyverifiedbotdevelopermagenta.png",
  "599047-siriintelligence.png",
  "60330-developer.png",
  "604557-python.png",
  "622731-typescript.png",
  "625646-developericon.png",
  "625830-redbull.png",
  "635956-heartbiscuit.png",
  "63762-google-cat-smile.png",
  "64442-cybercubs-bigmood.png",
  "647233-neon-play-button.png",
  "66471-brave.png",
  "6808-couronnecyberpunk.png",
  "701524-neon-gmail-icon.png",
  "70540-google-cat-kiss.png",
  "719878-lightgreenbanhammer.png",
  "721586-neon-kick-logo.png",
  "7269-dart.png",
  "72844-google-cat-heart-eyes.png",
  "74472-c-lang.png",
  "754310-neon-steam-icon.png",
  "764347-neon-food.png",
  "774598-javascript.png",
  "778366-claudeicon.png",
  "780069-neon-screenshot.png",
  "79185-dev.png",
  "7941-apple-intelligence.png",
  "812213-neonviolet-key.png",
  "817740-isro-badge.png",
  "8589_raspbian.png",
  "862785-nitro-lootbox-cyberwave.png",
  "880005-nasalogo.png",
  "88713-cybercubs-letsgo.png",
  "88766-cybercubs-sorry.png",
  "916991-gemini.png",
  "921655-ai.png",
  "925608-fundedforyoudeveloper.png",
  "943972-shield.png",
  "9493-cybercubs-pie.png",
  "97287-ask-google-not-me.png",
  "97772-cybercubs-gwenchana.png",
  "98617-google-cat-cry.png",
  "996204-lightbluebanhammer.png",
  "99753-google-cat-face.png",
].map((filename) => `/stickers/${filename}`);
const noteStyles = [
  {
    paper: "border-[#99CDD8] bg-[#99CDD8]",
    number: "text-[#657166]",
    heading: "text-[#657166]",
    body: "text-[#657166]",
    meta: "border-[#657166]/20 text-[#657166]",
    author: "text-[#657166]",
    chip: "bg-white/60 text-[#657166]",
    pin: "bg-[#99CDD8]",
  },
  {
    paper: "border-[#DAEBE3] bg-[#DAEBE3]",
    number: "text-[#657166]",
    heading: "text-[#657166]",
    body: "text-[#657166]",
    meta: "border-[#657166]/20 text-[#657166]",
    author: "text-[#657166]",
    chip: "bg-white/60 text-[#657166]",
    pin: "bg-[#DAEBE3]",
  },
  {
    paper: "border-[#FDE8D3] bg-[#FDE8D3]",
    number: "text-[#657166]",
    heading: "text-[#657166]",
    body: "text-[#657166]",
    meta: "border-[#657166]/20 text-[#657166]",
    author: "text-[#657166]",
    chip: "bg-white/60 text-[#657166]",
    pin: "bg-[#FDE8D3]",
  },
  {
    paper: "border-[#F3C3B2] bg-[#F3C3B2]",
    number: "text-[#657166]",
    heading: "text-[#657166]",
    body: "text-[#657166]",
    meta: "border-[#657166]/20 text-[#657166]",
    author: "text-[#657166]",
    chip: "bg-white/60 text-[#657166]",
    pin: "bg-[#F3C3B2]",
  },
  {
    paper: "border-[#CFD6C4] bg-[#CFD6C4]",
    number: "text-[#657166]",
    heading: "text-[#657166]",
    body: "text-[#657166]",
    meta: "border-[#657166]/20 text-[#657166]",
    author: "text-[#657166]",
    chip: "bg-white/60 text-[#657166]",
    pin: "bg-[#CFD6C4]",
  },
  {
    paper: "border-[#657166] bg-[#657166]",
    number: "text-[#DAEBE3]",
    heading: "text-[#FDF6EE]",
    body: "text-[#DAEBE3]",
    meta: "border-[#DAEBE3]/25 text-[#DAEBE3]",
    author: "text-[#FDF6EE]",
    chip: "bg-white/15 text-[#FDF6EE]",
    pin: "bg-[#657166]",
  },
] as const;

export default function NoticesPage() {
  const { getToken } = useAuth();
  const [notices, setNotices] = useState<ApiNotice[]>([]);
  const [noticeStickers, setNoticeStickers] = useState<Record<string, string>>({});
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
      const loadedNotices = data || [];
      setNotices(loadedNotices);
      setNoticeStickers(
        Object.fromEntries(
          loadedNotices.map((notice) => [
            notice.id,
            stickerArtworks[Math.floor(Math.random() * stickerArtworks.length)],
          ]),
        ),
      );
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

      {/* Notices */}
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
        <div className="notice-board-surface relative overflow-hidden rounded-3xl border border-cream-300 px-4 py-8 shadow-inner sm:px-8 sm:py-10">
          <div className="mb-8 flex flex-wrap items-center justify-between gap-2">
            <p className="font-heading text-sm font-bold text-green-900">Notice timeline</p>
            <p className="text-xs text-ink-muted">
              {filtered.length} {filtered.length === 1 ? "notice" : "notices"}
            </p>
          </div>
          <ol className="relative flex flex-col gap-y-9 before:absolute before:inset-y-0 before:left-4 before:border-l-2 before:border-dashed before:border-cream-400/60 md:gap-y-12 md:before:left-1/2">
            {filtered.map((n, index) => {
              const dateStr = n.created_at
                ? new Date(n.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })
                : "Recent";
              const noteStyle = noteStyles[index % noteStyles.length];
              const sticker = noticeStickers[n.id];
              const isLeft = index % 2 === 0;
              return (
                <li
                  key={n.id}
                  className={`relative flex w-full pl-8 after:absolute after:left-4 after:top-1/2 after:w-4 after:border-t-2 after:border-dashed after:border-cream-400/60 md:w-1/2 md:pl-0 md:after:top-1/2 md:after:w-8 ${
                    isLeft
                      ? "md:self-start md:justify-end md:pr-8 md:after:left-auto md:after:right-0"
                      : "md:self-end md:justify-start md:pl-8 md:after:left-0"
                  }`}
                >
                  {sticker && (
                    <Image
                      aria-hidden="true"
                      alt=""
                      src={sticker}
                      className={`pointer-events-none absolute top-1/2 z-0 hidden h-[108px] w-[108px] -translate-y-1/2 object-contain opacity-90 mix-blend-multiply md:block ${
                        isLeft ? "left-[175%]" : "left-[-75%]"
                      }`}
                      width={108}
                      height={108}
                    />
                  )}
                  <article
                    className={`relative z-10 w-full max-w-[30rem] rounded-[1.4rem] border border-white/90 bg-white p-3 shadow-[0_14px_32px_rgba(9,42,40,0.12)] transition duration-200 hover:-translate-y-1 hover:shadow-xl ${
                      isLeft ? "md:-rotate-1" : "md:rotate-1"
                    } ${n.priority === "urgent" ? "ring-2 ring-bordo-500/30" : ""}`}
                  >
                    <span
                      aria-hidden="true"
                      className={`absolute left-1/2 top-0 z-10 h-6 w-6 -translate-x-1/2 rounded-full shadow-[0_5px_9px_rgba(9,42,40,0.24)] ${noteStyle.pin}`}
                    >
                      <span className="absolute left-1/2 top-1 h-1 w-3 -translate-x-1/2 rounded-full bg-white/70" />
                    </span>
                    <div className={`h-full rounded-[1rem] border p-4 pt-7 sm:p-5 sm:pt-8 ${noteStyle.paper}`}>
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <span className={`font-heading text-2xl font-semibold leading-none ${noteStyle.number}`}>
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <div className="flex flex-wrap justify-end gap-1.5">
                          {n.is_pinned && (
                            <Badge tone="info">
                              <Pin size={11} className="mr-0.5" /> Pinned
                            </Badge>
                          )}
                          <Badge tone={tone[n.priority]}>{n.priority}</Badge>
                        </div>
                      </div>

                      <h2 className={`mt-3 break-words font-heading text-lg font-bold leading-snug ${noteStyle.heading}`}>
                        {n.title}
                      </h2>
                      <p className={`mt-2 whitespace-pre-line break-words text-sm leading-relaxed ${noteStyle.body}`}>
                        {n.body}
                      </p>

                      <div className={`mt-5 flex flex-wrap items-center justify-between gap-2 border-t pt-3 text-xs ${noteStyle.meta}`}>
                        <span className="flex min-w-0 items-center gap-1.5">
                          <User size={13} className="shrink-0" />
                          <span className="truncate">
                            <b className={noteStyle.author}>{n.author_name || "Administration"}</b>
                          </span>
                        </span>
                        <span>{dateStr}</span>
                      </div>
                      {(n.course_title || n.priority === "urgent") && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {n.course_title && (
                            <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${noteStyle.chip}`}>
                              {n.course_title}
                            </span>
                          )}
                          {n.priority === "urgent" && (
                            <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${noteStyle.chip}`}>
                              Action required
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </article>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </div>
  );
}
