"use client";

import { useAuth } from "@clerk/nextjs";
import {
  AlignLeft,
  CalendarDays,
  Check,
  CheckCircle2,
  Circle,
  Clock3,
  Cloud,
  FileAudio2,
  LoaderCircle,
  Mic,
  Music2,
  Pencil,
  Play,
  Plus,
  Search,
  Shapes,
  Square,
  Star,
  StickyNote,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, getBaseUrl, getDevAuthToken } from "@/lib/api";

type PlannerKind = "learning_plan" | "note" | "sticky_note" | "event" | "voice_note";
type PlannerShape = "rectangle" | "rounded" | "circle" | "cloud" | "star";
type Role = "student" | "teacher" | "admin";

interface PlannerEntry {
  id: string;
  owner_id: string;
  kind: PlannerKind;
  title: string;
  content: string | null;
  due_at: string | null;
  is_completed: boolean;
  color: string;
  shape: PlannerShape;
  emoji: string | null;
  audio_mime_type: string | null;
  audio_size_bytes: number | null;
  audio_url: string | null;
  created_at: string;
  updated_at: string;
}

type EntryDraft = {
  kind: Exclude<PlannerKind, "voice_note">;
  title: string;
  content: string;
  due_at: string;
  color: string;
  shape: PlannerShape;
  emoji: string;
};

const COLORS = [
  { value: "#fce7f3", label: "Rose" },
  { value: "#ede9fe", label: "Lavender" },
  { value: "#dbeafe", label: "Sky" },
  { value: "#dcfce7", label: "Mint" },
  { value: "#fef3c7", label: "Sunshine" },
  { value: "#ffedd5", label: "Peach" },
];
const EMOJIS = ["📚", "🎯", "💡", "🌱", "✨", "🧠", "🎨", "☕", "⭐", "📝"];
const SHAPES: { value: PlannerShape; label: string }[] = [
  { value: "rounded", label: "Rounded" },
  { value: "rectangle", label: "Rectangle" },
  { value: "circle", label: "Circle" },
  { value: "cloud", label: "Cloud" },
  { value: "star", label: "Star" },
];
const TABS: { id: "learning_plan" | "note" | "sticky_note" | "voice_note"; label: string; icon: typeof AlignLeft }[] = [
  { id: "learning_plan", label: "Learning plan", icon: AlignLeft },
  { id: "note", label: "Notes", icon: Pencil },
  { id: "sticky_note", label: "Sticky notes", icon: StickyNote },
  { id: "voice_note", label: "Voice notes", icon: FileAudio2 },
];

const emptyDraft = (kind: EntryDraft["kind"]): EntryDraft => ({
  kind,
  title: "",
  content: "",
  due_at: "",
  color: kind === "sticky_note" ? COLORS[0].value : "#fef3c7",
  shape: "rounded",
  emoji: "",
});

function localDateTime(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function prettyDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function formatBytes(value: number | null): string {
  if (!value) return "";
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function shapeClass(shape: PlannerShape): string {
  if (shape === "circle") return "rounded-[2rem]";
  if (shape === "cloud") return "rounded-[2rem_1rem_2rem_1rem]";
  if (shape === "star") return "rounded-[1.5rem_0.7rem_1.5rem_0.7rem]";
  if (shape === "rectangle") return "rounded-xl";
  return "rounded-3xl";
}

export function LearnPlanner({ role }: { role: Role }) {
  const { getToken } = useAuth();
  const [entries, setEntries] = useState<PlannerEntry[]>([]);
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]["id"]>("learning_plan");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draft, setDraft] = useState<EntryDraft>(emptyDraft("learning_plan"));
  const [editing, setEditing] = useState<PlannerEntry | null>(null);
  const [recording, setRecording] = useState(false);
  const [uploadingAudio, setUploadingAudio] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [audioUrls, setAudioUrls] = useState<Record<string, string>>({});
  const audioUrlsRef = useRef<Record<string, string>>({});
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (!token && (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")) {
      token = getDevAuthToken(role);
    }
    return token;
  }, [getToken, role]);

  const loadEntries = useCallback(async () => {
    try {
      const token = await resolveToken();
      const data = await api<PlannerEntry[]>("/planner/entries", token ?? undefined);
      setEntries(data);
      setError("");
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load your planner.");
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    void loadEntries();
  }, [loadEntries]);

  useEffect(() => {
    const audioUrlsOnMount = audioUrlsRef.current;
    return () => {
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      Object.values(audioUrlsOnMount).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  const plans = useMemo(() => entries.filter((entry) => entry.kind === "learning_plan"), [entries]);
  const upcomingEvents = useMemo(
    () =>
      entries
        .filter((entry) => entry.kind === "event" && entry.due_at && !entry.is_completed)
        .sort((a, b) => new Date(a.due_at!).getTime() - new Date(b.due_at!).getTime()),
    [entries],
  );
  const visibleEntries = useMemo(
    () =>
      entries.filter((entry) => {
        if (entry.kind !== activeTab) return false;
        const query = search.trim().toLowerCase();
        return !query || entry.title.toLowerCase().includes(query) || (entry.content ?? "").toLowerCase().includes(query);
      }),
    [activeTab, entries, search],
  );

  function openCreate(kind: EntryDraft["kind"]) {
    setEditing(null);
    setDraft(emptyDraft(kind));
    setDialogOpen(true);
  }

  function openEdit(entry: PlannerEntry) {
    if (entry.kind === "voice_note") return;
    setEditing(entry);
    setDraft({
      kind: entry.kind,
      title: entry.title,
      content: entry.content ?? "",
      due_at: localDateTime(entry.due_at),
      color: entry.color,
      shape: entry.shape,
      emoji: entry.emoji ?? "",
    });
    setDialogOpen(true);
  }

  async function saveEntry(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const token = await resolveToken();
      const { due_at: draftDueAt, ...draftFields } = draft;
      const body: Record<string, unknown> = {
        ...draftFields,
        title: draft.title.trim(),
        content: draft.content.trim() || null,
        emoji: draft.emoji || null,
      };
      if (draft.kind === "event") {
        body.due_at = draftDueAt ? new Date(draftDueAt).toISOString() : null;
      }
      if (editing) {
        const updated = await api<PlannerEntry>(
          `/planner/entries/${editing.id}`,
          token ?? undefined,
          { method: "PATCH", body: JSON.stringify(body) },
        );
        setEntries((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      } else {
        const created = await api<PlannerEntry>(
          "/planner/entries",
          token ?? undefined,
          { method: "POST", body: JSON.stringify(body) },
        );
        setEntries((current) => [created, ...current]);
      }
      setDialogOpen(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save this planner item.");
    } finally {
      setSaving(false);
    }
  }

  async function toggleComplete(entry: PlannerEntry) {
    try {
      const token = await resolveToken();
      const updated = await api<PlannerEntry>(
        `/planner/entries/${entry.id}`,
        token ?? undefined,
        { method: "PATCH", body: JSON.stringify({ is_completed: !entry.is_completed }) },
      );
      setEntries((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : "Could not update this item.");
    }
  }

  async function deleteEntry(entry: PlannerEntry) {
    if (!window.confirm(`Delete “${entry.title}”? This cannot be undone.`)) return;
    try {
      const token = await resolveToken();
      await api<void>(`/planner/entries/${entry.id}`, token ?? undefined, { method: "DELETE" });
      setEntries((current) => current.filter((item) => item.id !== entry.id));
      const objectUrl = audioUrls[entry.id];
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        delete audioUrlsRef.current[entry.id];
        setAudioUrls((current) => {
          const next = { ...current };
          delete next[entry.id];
          return next;
        });
      }
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Could not delete this item.");
    }
  }

  async function uploadVoiceNote(file: File, title = file.name.replace(/\.[^.]+$/, "")) {
    if (file.size > 25 * 1024 * 1024) {
      setError("Voice notes cannot exceed 25 MB.");
      return;
    }
    setUploadingAudio(true);
    setError("");
    try {
      const token = await resolveToken();
      const form = new FormData();
      form.append("file", file);
      const item = await api<PlannerEntry>(
        `/planner/entries/voice-note?title=${encodeURIComponent(title || "Voice note")}`,
        token ?? undefined,
        { method: "POST", body: form },
      );
      setEntries((current) => [item, ...current]);
      setActiveTab("voice_note");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not save this voice note.");
    } finally {
      setUploadingAudio(false);
      setRecording(false);
    }
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Audio recording is not supported in this browser. You can upload an audio file instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const supportedMime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]
        .find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = supportedMime
        ? new MediaRecorder(stream, { mimeType: supportedMime })
        : new MediaRecorder(stream);
      const chunks: BlobPart[] = [];
      let totalBytes = 0;
      let recordingTooLarge = false;
      recorder.ondataavailable = (event) => {
        if (!event.data.size || recordingTooLarge) return;
        if (totalBytes + event.data.size > 25 * 1024 * 1024) {
          recordingTooLarge = true;
          setError("Voice notes cannot exceed 25 MB. This recording was stopped.");
          if (recorder.state === "recording") recorder.stop();
          return;
        }
        totalBytes += event.data.size;
        chunks.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        if (timerRef.current !== null) window.clearInterval(timerRef.current);
        timerRef.current = null;
        setRecording(false);
        if (recordingTooLarge) return;
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        const extension = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
        void uploadVoiceNote(new File([blob], `voice-note.${extension}`, { type: blob.type }));
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecordingSeconds(0);
      timerRef.current = window.setInterval(() => setRecordingSeconds((seconds) => seconds + 1), 1000);
      setRecording(true);
      setError("");
    } catch (recordError) {
      setError(recordError instanceof Error ? recordError.message : "Microphone permission was not granted.");
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  }

  async function playVoiceNote(entry: PlannerEntry) {
    if (audioUrls[entry.id]) return;
    try {
      const token = await resolveToken();
      const response = await fetch(`${getBaseUrl()}${entry.audio_url}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) throw new Error(response.statusText || "Could not load audio.");
      const url = URL.createObjectURL(await response.blob());
      audioUrlsRef.current[entry.id] = url;
      setAudioUrls((current) => ({ ...current, [entry.id]: url }));
    } catch (audioError) {
      setError(audioError instanceof Error ? audioError.message : "Could not play this voice note.");
    }
  }

  const activeLabel = TABS.find((tab) => tab.id === activeTab)?.label ?? "Learning plan";
  const completedPlans = plans.filter((entry) => entry.is_completed).length;
  const completion = plans.length ? Math.round((completedPlans / plans.length) * 100) : 0;

  return (
    <div className="overflow-hidden rounded-[2rem] border border-[#d9efec] bg-[#f7fbfa] shadow-[0_16px_60px_-32px_rgba(15,70,65,0.35)]">
      <header className="flex flex-wrap items-center justify-between gap-4 bg-[#102f32] px-5 py-4 text-white sm:px-8">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl bg-[#d9f6ec] text-[#1c5b4c]">
            <CalendarDays size={21} />
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#9dd8c8]">SiliconBrains University</p>
            <h1 className="font-heading text-xl font-bold sm:text-2xl">SB Learn Planner</h1>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-2 text-xs font-medium capitalize text-white/85">
          <span className="h-2 w-2 rounded-full bg-emerald-300" />
          {role} workspace · private to you
        </div>
      </header>

      <div className="grid gap-5 p-4 sm:p-6 xl:grid-cols-[minmax(0,1fr)_300px] xl:gap-6 xl:p-7">
        <section className="min-w-0">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#56847b]">Make today count</p>
              <h2 className="mt-1 font-heading text-2xl font-bold text-[#153c3a] sm:text-3xl">My Learning Plan <span aria-hidden>📚</span></h2>
              <p className="mt-1 max-w-xl text-sm text-[#69817d]">Plan a little, learn a lot. Keep your study goals, notes and ideas in one calm space.</p>
            </div>
            <button
              type="button"
              onClick={() => openCreate(activeTab === "voice_note" ? "note" : activeTab)}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-[#174c43] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#0f3c35]"
            >
              <Plus size={17} /> Add {activeTab === "learning_plan" ? "learning goal" : activeTab === "sticky_note" ? "sticky note" : activeTab === "note" ? "note" : "item"}
            </button>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
            <label className="relative block">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#809692]" size={17} />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search your planner..."
                className="h-11 w-full rounded-2xl border border-[#dcebe8] bg-white pl-10 pr-4 text-sm text-[#173d39] outline-none transition focus:border-[#5a9b8e] focus:ring-2 focus:ring-[#d1ebe4]"
              />
            </label>
            <div className="flex items-center justify-between gap-3 rounded-2xl bg-[#e9f5f1] px-4 py-2 sm:min-w-44">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#63837a]">Goals completed</p>
                <p className="text-sm font-bold text-[#174c43]">{completedPlans} / {plans.length}</p>
              </div>
              <div className="grid h-10 w-10 place-items-center rounded-full border-[3px] border-[#a9d5c8] bg-white text-xs font-bold text-[#174c43]">{completion}%</div>
            </div>
          </div>

          <div className="mt-5 flex gap-1 overflow-x-auto rounded-2xl bg-[#eaf3f1] p-1" role="tablist" aria-label="Planner sections">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={activeTab === id}
                onClick={() => setActiveTab(id)}
                className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-3 text-xs font-semibold transition sm:px-4 sm:text-sm ${
                  activeTab === id ? "bg-white text-[#174c43] shadow-sm" : "text-[#67817c] hover:bg-white/60"
                }`}
              >
                <Icon size={16} /> {label}
                <span className="rounded-full bg-[#eef5f2] px-1.5 py-0.5 text-[10px]">
                  {entries.filter((entry) => entry.kind === id).length}
                </span>
              </button>
            ))}
          </div>

          {error && (
            <div role="alert" className="mt-4 flex items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              <span>{error}</span>
              <button type="button" onClick={() => setError("")} aria-label="Dismiss error"><X size={17} /></button>
            </div>
          )}

          {activeTab === "voice_note" && (
            <div className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-[#e7f4f5] p-4 sm:p-5">
              <div className="flex items-center gap-3">
                <div className="grid h-12 w-12 place-items-center rounded-2xl bg-white text-[#35747a]"><Music2 /></div>
                <div>
                  <p className="font-semibold text-[#214b4d]">Capture a thought, hands-free</p>
                  <p className="text-xs text-[#668386]">Audio stays private in your planner. Up to 25 MB per recording.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.currentTarget.files?.[0];
                    if (file) void uploadVoiceNote(file);
                    event.currentTarget.value = "";
                  }}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingAudio}
                  className="min-h-10 rounded-xl border border-[#c5dddd] bg-white px-3 text-xs font-semibold text-[#34666a] hover:bg-[#f5fbfa] disabled:opacity-50"
                >
                  Upload audio
                </button>
                <button
                  type="button"
                  onClick={recording ? stopRecording : startRecording}
                  disabled={uploadingAudio}
                  className={`inline-flex min-h-10 items-center gap-2 rounded-xl px-4 text-xs font-bold text-white disabled:opacity-50 ${recording ? "bg-rose-600 hover:bg-rose-700" : "bg-[#286d72] hover:bg-[#205c60]"}`}
                >
                  {uploadingAudio ? <LoaderCircle size={16} className="animate-spin" /> : recording ? <Square size={14} fill="currentColor" /> : <Mic size={16} />}
                  {uploadingAudio ? "Saving..." : recording ? `Stop · ${Math.floor(recordingSeconds / 60)}:${String(recordingSeconds % 60).padStart(2, "0")}` : "Record"}
                </button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="grid min-h-64 place-items-center text-[#598078]"><LoaderCircle className="animate-spin" /></div>
          ) : visibleEntries.length === 0 ? (
            <div className="mt-5 grid min-h-64 place-items-center rounded-3xl border border-dashed border-[#cbded9] bg-white/70 px-5 py-10 text-center">
              <div>
                <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[#e8f4ef] text-[#478475]">
                  {activeTab === "sticky_note" ? <StickyNote /> : activeTab === "voice_note" ? <FileAudio2 /> : activeTab === "note" ? <Pencil /> : <Shapes />}
                </div>
                <h3 className="mt-3 font-heading text-lg font-bold text-[#234c47]">Your {activeLabel.toLowerCase()} starts here</h3>
                <p className="mx-auto mt-1 max-w-sm text-sm text-[#758c87]">
                  {activeTab === "voice_note" ? "Record a quick idea or upload an audio note to keep it close." : "Add your first item and make this planner your own."}
                </p>
                {activeTab !== "voice_note" && (
                  <button type="button" onClick={() => openCreate(activeTab)} className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-full bg-[#174c43] px-4 text-sm font-semibold text-white">
                    <Plus size={16} /> Create {activeLabel.toLowerCase()}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className={`mt-5 grid gap-3 ${activeTab === "sticky_note" ? "sm:grid-cols-2 lg:grid-cols-3" : ""}`}>
              {visibleEntries.map((entry) => {
                const isSticky = entry.kind === "sticky_note";
                const isVoice = entry.kind === "voice_note";
                return (
                  <article
                    key={entry.id}
                    className={`group relative border border-black/[0.04] p-4 shadow-[0_6px_18px_-14px_rgba(18,62,54,0.5)] transition hover:-translate-y-0.5 hover:shadow-md ${
                      isSticky ? `min-h-48 ${shapeClass(entry.shape)}` : "rounded-2xl"
                    } ${entry.is_completed ? "opacity-70" : ""}`}
                    style={{ backgroundColor: entry.color }}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-start gap-2.5">
                        {entry.emoji && <span aria-hidden className="text-xl">{entry.emoji}</span>}
                        {entry.kind === "learning_plan" && (
                          <button type="button" onClick={() => void toggleComplete(entry)} className="mt-0.5 text-[#478476]" aria-label={entry.is_completed ? "Mark as in progress" : "Mark as completed"}>
                            {entry.is_completed ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                          </button>
                        )}
                        <div className="min-w-0">
                          <h3 className={`break-words font-heading font-bold text-[#1d3e3c] ${isSticky ? "text-lg" : "text-base"} ${entry.is_completed ? "line-through" : ""}`}>{entry.title}</h3>
                          {entry.due_at && (
                            <p className="mt-1 flex items-center gap-1 text-[11px] font-medium text-[#57726e]">
                              <Clock3 size={12} /> {prettyDate(entry.due_at)}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
                        {!isVoice && <button type="button" onClick={() => openEdit(entry)} className="grid h-8 w-8 place-items-center rounded-full bg-white/70 text-[#45655f] hover:bg-white" aria-label={`Edit ${entry.title}`}><Pencil size={14} /></button>}
                        <button type="button" onClick={() => void deleteEntry(entry)} className="grid h-8 w-8 place-items-center rounded-full bg-white/70 text-[#8b5555] hover:bg-white" aria-label={`Delete ${entry.title}`}><Trash2 size={14} /></button>
                      </div>
                    </div>
                    {entry.content && <p className={`mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed text-[#45615c] ${isSticky ? "line-clamp-6" : "line-clamp-3"}`}>{entry.content}</p>}
                    {isSticky && (
                      <div className="mt-4 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#718681]">
                        <span className="h-2 w-2 rounded-full border border-[#829792]" /> Sticky note
                      </div>
                    )}
                    {isVoice && (
                      <div className="mt-4">
                        {audioUrls[entry.id] ? (
                          <audio controls preload="none" src={audioUrls[entry.id]} className="h-10 w-full" />
                        ) : (
                          <button type="button" onClick={() => void playVoiceNote(entry)} className="inline-flex min-h-10 items-center gap-2 rounded-full bg-white/75 px-4 text-sm font-semibold text-[#315d5e] hover:bg-white">
                            <Play size={15} fill="currentColor" /> Load & play
                          </button>
                        )}
                        <p className="mt-2 text-[11px] text-[#718681]">{formatBytes(entry.audio_size_bytes)} · {entry.audio_mime_type}</p>
                      </div>
                    )}
                    {entry.kind === "learning_plan" && (
                      <button type="button" onClick={() => void toggleComplete(entry)} className={`mt-4 inline-flex min-h-8 items-center gap-1.5 rounded-full px-3 text-[11px] font-semibold ${entry.is_completed ? "bg-white/75 text-[#4a7469]" : "bg-white/55 text-[#526c67] hover:bg-white"}`}>
                        {entry.is_completed ? <><Check size={13} /> Completed</> : "Mark complete"}
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <aside className="min-w-0">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#56847b]">Stay on track</p>
              <h2 className="mt-1 font-heading text-xl font-bold text-[#153c3a]">My Events <span aria-hidden>🗓️</span></h2>
            </div>
            <button type="button" onClick={() => openCreate("event")} aria-label="Add event" className="grid h-10 w-10 place-items-center rounded-full bg-[#174c43] text-white hover:bg-[#0f3c35]"><Plus size={18} /></button>
          </div>
          <div className="mt-4 space-y-3">
            {upcomingEvents.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-[#cbded9] bg-white/75 p-5 text-center">
                <CalendarDays className="mx-auto text-[#7c9b94]" size={23} />
                <p className="mt-2 text-sm font-semibold text-[#42675f]">Nothing scheduled yet</p>
                <p className="mt-1 text-xs text-[#7b908b]">Add a study session, deadline or reminder.</p>
                <button type="button" onClick={() => openCreate("event")} className="mt-3 text-xs font-bold text-[#21695b] hover:underline">Add your first event</button>
              </div>
            ) : upcomingEvents.map((event) => (
              <article key={event.id} className="group rounded-3xl border border-black/[0.04] p-4 shadow-sm" style={{ backgroundColor: event.color }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="grid h-8 w-8 place-items-center rounded-xl bg-white/75 text-[#4a766c]"><CalendarDays size={16} /></span>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#627d76]">{prettyDate(event.due_at!)}</span>
                  </div>
                  <div className="flex gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100">
                    <button type="button" onClick={() => openEdit(event)} aria-label={`Edit event ${event.title}`} className="grid h-7 w-7 place-items-center rounded-full bg-white/70 text-[#45655f]"><Pencil size={13} /></button>
                    <button type="button" onClick={() => void deleteEntry(event)} aria-label={`Delete event ${event.title}`} className="grid h-7 w-7 place-items-center rounded-full bg-white/70 text-[#8b5555]"><Trash2 size={13} /></button>
                  </div>
                </div>
                <h3 className="mt-3 font-heading font-bold text-[#244541]">{event.emoji ? `${event.emoji} ` : ""}{event.title}</h3>
                {event.content && <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-[#56706a]">{event.content}</p>}
                <button type="button" onClick={() => void toggleComplete(event)} className="mt-3 inline-flex min-h-8 items-center gap-1.5 rounded-full bg-white/70 px-3 text-[11px] font-semibold text-[#4c7067] hover:bg-white">
                  <CheckCircle2 size={13} /> Mark done
                </button>
              </article>
            ))}
          </div>
          <div className="mt-4 rounded-3xl bg-[#e7f3ed] p-4">
            <div className="flex items-center gap-2 text-[#34675b]"><CheckCircle2 size={17} /><span className="text-sm font-bold">A little progress adds up</span></div>
            <p className="mt-1.5 text-xs leading-relaxed text-[#66847b]">{completion === 100 && plans.length ? "All your learning goals are complete. Amazing work!" : `${completion}% of your learning goals are complete. Keep going at your own pace.`}</p>
          </div>
        </aside>
      </div>

      {dialogOpen && (
        <div className="fixed inset-0 z-[70] flex items-end justify-center bg-[#0c2624]/55 p-0 backdrop-blur-sm sm:items-center sm:p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setDialogOpen(false); }}>
          <form onSubmit={saveEntry} className="max-h-[92dvh] w-full max-w-xl overflow-y-auto rounded-t-[2rem] bg-white p-5 shadow-2xl sm:rounded-[2rem] sm:p-7">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#56847b]">{editing ? "Edit item" : "Add to your planner"}</p>
                <h2 className="mt-1 font-heading text-2xl font-bold text-[#193d39]">{editing ? "Update your entry" : draft.kind === "learning_plan" ? "New learning goal" : draft.kind === "sticky_note" ? "Create sticky note" : draft.kind === "event" ? "Add an event" : "Write a note"}</h2>
              </div>
              <button type="button" onClick={() => setDialogOpen(false)} aria-label="Close dialog" className="grid h-10 w-10 place-items-center rounded-full bg-[#f0f5f3] text-[#52716a]"><X size={19} /></button>
            </div>

            {!editing && (
              <div className="mt-5 flex flex-wrap gap-2">
                {(["learning_plan", "note", "sticky_note", "event"] as const).map((kind) => (
                  <button key={kind} type="button" onClick={() => setDraft(emptyDraft(kind))} className={`min-h-9 rounded-full px-3 text-xs font-semibold capitalize ${draft.kind === kind ? "bg-[#174c43] text-white" : "bg-[#eff5f2] text-[#52716a]"}`}>
                    {kind.replace("_", " ")}
                  </button>
                ))}
              </div>
            )}

            <label className="mt-5 block text-sm font-semibold text-[#31544d]">
              Title
              <input required maxLength={160} autoFocus value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder={draft.kind === "learning_plan" ? "e.g. Review anatomy chapters" : draft.kind === "event" ? "e.g. Biology study session" : "Give it a name"} className="mt-1.5 h-11 w-full rounded-xl border border-[#d7e4e0] px-3.5 text-sm outline-none focus:border-[#589a8d] focus:ring-2 focus:ring-[#dceee8]" />
            </label>
            {draft.kind === "event" && (
              <label className="mt-4 block text-sm font-semibold text-[#31544d]">
                Date and time
                <input required type="datetime-local" value={draft.due_at} onChange={(event) => setDraft({ ...draft, due_at: event.target.value })} className="mt-1.5 h-11 w-full rounded-xl border border-[#d7e4e0] px-3.5 text-sm outline-none focus:border-[#589a8d]" />
              </label>
            )}
            <label className="mt-4 block text-sm font-semibold text-[#31544d]">
              {draft.kind === "learning_plan" ? "Plan details" : draft.kind === "event" ? "Details (optional)" : "Your note"}
              <textarea maxLength={20000} rows={4} value={draft.content} onChange={(event) => setDraft({ ...draft, content: event.target.value })} placeholder={draft.kind === "learning_plan" ? "Break the goal into a few steps..." : "Write a few details..."} className="mt-1.5 w-full resize-y rounded-xl border border-[#d7e4e0] px-3.5 py-3 text-sm outline-none focus:border-[#589a8d] focus:ring-2 focus:ring-[#dceee8]" />
            </label>

            {(draft.kind === "sticky_note" || draft.kind === "event") && (
              <div className="mt-4 space-y-4">
                <fieldset>
                  <legend className="text-sm font-semibold text-[#31544d]">Color</legend>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {COLORS.map((color) => (
                      <button key={color.value} type="button" onClick={() => setDraft({ ...draft, color: color.value })} aria-label={`${color.label} note color`} aria-pressed={draft.color === color.value} className={`grid h-9 w-9 place-items-center rounded-full border-2 ${draft.color === color.value ? "border-[#174c43]" : "border-white shadow ring-1 ring-[#d7e4e0]"}`} style={{ backgroundColor: color.value }}>
                        {draft.color === color.value && <Check size={15} className="text-[#174c43]" />}
                      </button>
                    ))}
                  </div>
                </fieldset>
                {draft.kind === "sticky_note" && (
                  <>
                    <fieldset>
                      <legend className="text-sm font-semibold text-[#31544d]">Shape</legend>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {SHAPES.map(({ value, label }) => {
                          const Icon = value === "circle" ? Circle : value === "cloud" ? Cloud : value === "star" ? Star : Square;
                          return <button key={value} type="button" onClick={() => setDraft({ ...draft, shape: value })} aria-pressed={draft.shape === value} className={`inline-flex min-h-9 items-center gap-1.5 rounded-full px-3 text-xs font-semibold ${draft.shape === value ? "bg-[#174c43] text-white" : "bg-[#eff5f2] text-[#52716a]"}`}><Icon size={14} />{label}</button>;
                        })}
                      </div>
                    </fieldset>
                    <fieldset>
                      <legend className="text-sm font-semibold text-[#31544d]">Add an emoji</legend>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        <button type="button" onClick={() => setDraft({ ...draft, emoji: "" })} aria-label="No emoji" className={`grid h-9 w-9 place-items-center rounded-lg text-xs ${!draft.emoji ? "bg-[#174c43] text-white" : "bg-[#eff5f2] text-[#52716a]"}`}><X size={14} /></button>
                        {EMOJIS.map((emoji) => <button key={emoji} type="button" onClick={() => setDraft({ ...draft, emoji })} aria-label={`Use ${emoji} emoji`} aria-pressed={draft.emoji === emoji} className={`grid h-9 w-9 place-items-center rounded-lg text-lg ${draft.emoji === emoji ? "bg-[#dceee8] ring-1 ring-[#72a99c]" : "bg-[#f3f7f5] hover:bg-[#e5f1ec]"}`}>{emoji}</button>)}
                      </div>
                    </fieldset>
                  </>
                )}
              </div>
            )}

            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button type="button" onClick={() => setDialogOpen(false)} className="min-h-11 rounded-full border border-[#d7e4e0] px-5 text-sm font-semibold text-[#52716a]">Cancel</button>
              <button type="submit" disabled={saving} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-full bg-[#174c43] px-6 text-sm font-semibold text-white disabled:opacity-60">
                {saving && <LoaderCircle size={16} className="animate-spin" />}
                {saving ? "Saving..." : editing ? "Save changes" : "Add to planner"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
