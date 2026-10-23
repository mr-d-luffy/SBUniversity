"use client";

import { useEffect, useRef, useState } from "react";

interface WatchedRange {
  start: number;
  end: number;
}

interface YoutubePlayer {
  getCurrentTime(): number;
  getDuration(): number;
  getPlayerState(): number;
  destroy(): void;
}

interface YoutubeApi {
  PlayerState: { PLAYING: number };
  Player: new (
    element: HTMLElement,
    options: {
      videoId: string;
      playerVars: { origin: string; rel: number };
      events: { onReady: () => void; onError: () => void };
    },
  ) => YoutubePlayer;
}

declare global {
  interface Window {
    YT?: YoutubeApi;
    onYouTubeIframeAPIReady?: () => void;
  }
}

let youtubeApiPromise: Promise<void> | undefined;

function loadYoutubeApi(): Promise<void> {
  if (window.YT) return Promise.resolve();
  if (youtubeApiPromise) return youtubeApiPromise;

  youtubeApiPromise = new Promise((resolve, reject) => {
    const previousReady = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      previousReady?.();
      resolve();
    };
    let script = document.getElementById("youtube-iframe-api") as HTMLScriptElement | null;
    if (!script) {
      script = document.createElement("script");
      script.id = "youtube-iframe-api";
      script.src = "https://www.youtube.com/iframe_api";
      script.onerror = () => reject(new Error("Could not load the YouTube video player."));
      document.head.appendChild(script);
    }
  });
  return youtubeApiPromise;
}

function getVideoId(url: string): string | null {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    const parts = parsed.pathname.split("/").filter(Boolean);
    const id =
      host === "youtu.be"
        ? parts[0]
        : parsed.pathname === "/watch"
          ? parsed.searchParams.get("v")
          : ["embed", "shorts", "live"].includes(parts[0]) && parts.length > 1
            ? parts[1]
            : null;
    return id && /^[A-Za-z0-9_-]{11}$/.test(id) ? id : null;
  } catch {
    return null;
  }
}

function mergeRange(ranges: WatchedRange[], start: number, end: number): WatchedRange[] {
  const sorted = [...ranges, { start, end }].sort((a, b) => a.start - b.start);
  return sorted.reduce<WatchedRange[]>((merged, range) => {
    const previous = merged[merged.length - 1];
    if (previous && range.start <= previous.end + 0.25) {
      previous.end = Math.max(previous.end, range.end);
    } else {
      merged.push({ ...range });
    }
    return merged;
  }, []);
}

function watchedSeconds(ranges: WatchedRange[]): number {
  return ranges.reduce((total, range) => total + range.end - range.start, 0);
}

export function YoutubeVideoTracker({
  videoUrl,
  initialProgress,
  onProgress,
}: {
  videoUrl: string;
  initialProgress: number;
  onProgress: (progress: number, durationSeconds: number) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rangesRef = useRef<WatchedRange[]>([]);
  const previousSampleRef = useRef<{ time: number; sampledAt: number } | null>(null);
  const lastReportedRef = useRef(Math.floor(initialProgress / 5) * 5);
  const initialProgressRef = useRef(initialProgress);
  const onProgressRef = useRef(onProgress);
  onProgressRef.current = onProgress;
  const [progress, setProgress] = useState(initialProgress);
  const [error, setError] = useState<string | null>(null);
  const videoId = getVideoId(videoUrl);

  useEffect(() => {
    if (!videoId || !containerRef.current) return;
    let player: YoutubePlayer | null = null;
    let timer: ReturnType<typeof setInterval> | undefined;
    let disposed = false;

    void loadYoutubeApi()
      .then(() => {
        if (disposed || !containerRef.current || !window.YT) return;
        player = new window.YT.Player(containerRef.current, {
          videoId,
          playerVars: { origin: window.location.origin, rel: 0 },
          events: {
            onReady: () => {
              if (!player) return;
              timer = setInterval(() => {
                if (!player || !window.YT || player.getPlayerState() !== window.YT.PlayerState.PLAYING) {
                  previousSampleRef.current = null;
                  return;
                }

                const time = player.getCurrentTime();
                const duration = player.getDuration();
                const sampledAt = Date.now();
                const previous = previousSampleRef.current;
                if (previous) {
                  const elapsed = (sampledAt - previous.sampledAt) / 1000;
                  const advanced = time - previous.time;
                  if (advanced > 0 && advanced <= elapsed * 2.25 + 0.5) {
                    rangesRef.current = mergeRange(rangesRef.current, previous.time, time);
                  }
                }
                previousSampleRef.current = { time, sampledAt };

                if (duration > 0) {
                  const observedProgress = Math.min(
                    100,
                    (watchedSeconds(rangesRef.current) / duration) * 100,
                  );
                  const nextProgress = Math.max(
                    initialProgressRef.current,
                    Math.min(100, initialProgressRef.current + observedProgress),
                  );
                  setProgress(nextProgress);
                  const reportAt = Math.floor(nextProgress / 5) * 5;
                  if (reportAt > lastReportedRef.current) {
                    lastReportedRef.current = reportAt;
                    onProgressRef.current(reportAt, duration);
                  }
                }
              }, 1000);
            },
            onError: () => setError("This YouTube video cannot be embedded. Ask your teacher to check its sharing settings."),
          },
        });
      })
      .catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : "Could not load the YouTube player.");
      });

    return () => {
      disposed = true;
      if (timer) clearInterval(timer);
      player?.destroy();
    };
  }, [videoId]);

  if (!videoId) {
    return <p className="mt-3 text-sm text-danger">This video link is not a supported YouTube URL.</p>;
  }

  return (
    <div className="mt-3 space-y-2">
      <div className="aspect-video w-full max-w-full overflow-hidden rounded-lg bg-black">
        <div ref={containerRef} className="h-full w-full" />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs text-ink-muted">
        <span>Watched progress</span>
        <span>{Math.floor(progress)}% · 80% required</span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-cream-200"
        role="progressbar"
        aria-label="Video watched progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.floor(progress)}
      >
        <div className="h-full rounded-full bg-green-700 transition-[width]" style={{ width: `${progress}%` }} />
      </div>
      {error && <p className="break-words text-xs text-danger">{error}</p>}
    </div>
  );
}
