"use client";

import { useAuth } from "@clerk/nextjs";
import {
  Check,
  Circle,
  Eraser,
  LoaderCircle,
  MessageCircle,
  Minus,
  PenLine,
  Presentation,
  Send,
  Square,
  Trash2,
  Undo2,
  UsersRound,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { api, getDevAuthToken } from "@/lib/api";

type Role = "student" | "teacher" | "admin";
type Tool = "pen" | "eraser" | "line" | "rectangle" | "ellipse";
type Point = { x: number; y: number };

interface WhiteboardCourse {
  id: string;
  code: string;
  title: string;
  is_live: boolean;
}

interface Stroke {
  id: string;
  session_id: string;
  author_id: string;
  tool: Tool;
  color: string;
  width: number;
  points: Point[];
  created_at: string;
}

interface LiveSession {
  id: string;
  course_id: string;
  created_by: string;
  is_active: boolean;
  board_generation: number;
  started_at: string;
  ended_at: string | null;
  strokes: Stroke[];
  strokes_are_snapshot: boolean;
}

interface ChatMessage {
  id: string;
  session_id: string;
  sender_id: string;
  sender_name: string;
  sender_role: Role;
  is_mine: boolean;
  content: string;
  created_at: string;
  expires_at: string;
}

const PALETTE = ["#173f38", "#2563eb", "#dc2626", "#7c3aed", "#d97706", "#111827"];
const TOOL_LABELS: Record<Tool, string> = {
  pen: "Pen",
  eraser: "Eraser",
  line: "Line",
  rectangle: "Rectangle",
  ellipse: "Oval",
};

function initials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function drawStroke(
  context: CanvasRenderingContext2D,
  stroke: Pick<Stroke, "tool" | "color" | "width" | "points">,
  width: number,
  height: number,
) {
  if (stroke.points.length < 2) return;
  const first = stroke.points[0];
  const last = stroke.points[stroke.points.length - 1];
  const x1 = first.x * width;
  const y1 = first.y * height;
  const x2 = last.x * width;
  const y2 = last.y * height;

  context.save();
  context.strokeStyle = stroke.tool === "eraser" ? "#ffffff" : stroke.color;
  context.lineWidth = stroke.tool === "eraser" ? Math.max(stroke.width * 3, 14) : stroke.width;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.beginPath();

  if (stroke.tool === "rectangle") {
    context.rect(x1, y1, x2 - x1, y2 - y1);
  } else if (stroke.tool === "ellipse") {
    context.ellipse(
      (x1 + x2) / 2,
      (y1 + y2) / 2,
      Math.abs(x2 - x1) / 2,
      Math.abs(y2 - y1) / 2,
      0,
      0,
      Math.PI * 2,
    );
  } else if (stroke.tool === "line") {
    context.moveTo(x1, y1);
    context.lineTo(x2, y2);
  } else {
    context.moveTo(x1, y1);
    for (const point of stroke.points.slice(1)) {
      context.lineTo(point.x * width, point.y * height);
    }
  }
  context.stroke();
  context.restore();
}

export function LiveWhiteboard({ role }: { role: Role }) {
  const { getToken } = useAuth();
  const isTeacher = role === "teacher";
  const isAdmin = role === "admin";
  const canControlBoard = isTeacher || isAdmin;
  const [courses, setCourses] = useState<WhiteboardCourse[]>([]);
  const [selectedCourseId, setSelectedCourseId] = useState("");
  const [session, setSession] = useState<LiveSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageDraft, setMessageDraft] = useState("");
  const [tool, setTool] = useState<Tool>("pen");
  const [inkColor, setInkColor] = useState(PALETTE[0]);
  const [inkWidth, setInkWidth] = useState(4);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [joining, setJoining] = useState(false);
  const [hasJoined, setHasJoined] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeStroke, setActiveStroke] = useState<Omit<Stroke, "id" | "session_id" | "author_id" | "created_at"> | null>(null);
  const course = useMemo(
    () => courses.find((item) => item.id === selectedCourseId) ?? null,
    [courses, selectedCourseId],
  );
  const boardCanvasRef = useRef<HTMLCanvasElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const paintedBoardRef = useRef<{
    generation: number;
    strokeIds: string[];
  } | null>(null);
  const drawingRef = useRef(false);
  const previewFrameRef = useRef<number | null>(null);
  const strokeRef = useRef<Omit<Stroke, "id" | "session_id" | "author_id" | "created_at"> | null>(null);
  const messageEndRef = useRef<HTMLDivElement>(null);
  const syncCursorRef = useRef<{
    sessionId: string;
    generation: number;
    strokeId: string | null;
  } | null>(null);

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (
      !token &&
      (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")
    ) {
      token = getDevAuthToken(role);
    }
    return token;
  }, [getToken, role]);

  const loadCourses = useCallback(async () => {
    try {
      const token = await resolveToken();
      const items = await api<WhiteboardCourse[]>("/whiteboard/courses", token ?? undefined);
      setCourses(items);
      setSelectedCourseId((selected) => {
        if (items.some((item) => item.id === selected)) return selected;
        return items.find((item) => item.is_live)?.id ?? items[0]?.id ?? "";
      });
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load your courses.");
    } finally {
      setLoading(false);
    }
  }, [resolveToken]);

  useEffect(() => {
    let active = true;
    let inFlight = false;
    const poll = async () => {
      if (!active || inFlight || document.visibilityState !== "visible") return;
      inFlight = true;
      await loadCourses();
      inFlight = false;
    };
    void poll();
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void poll();
    };
    const timer = window.setInterval(() => void poll(), 20000);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [loadCourses]);

  useEffect(() => {
    if (!selectedCourseId) {
      setSession(null);
      setMessages([]);
      return;
    }
    if (role === "student" && !hasJoined) {
      setSession(null);
      setMessages([]);
      return;
    }
    setSession(null);
    setMessages([]);
    syncCursorRef.current = null;
    let active = true;
    let inFlight = false;
    const poll = async () => {
      if (!active || inFlight || document.visibilityState !== "visible") return;
      inFlight = true;
      try {
        const token = await resolveToken();
        const cursor = syncCursorRef.current;
        const params = new URLSearchParams();
        if (cursor) {
          params.set("board_generation", String(cursor.generation));
          if (cursor.strokeId) params.set("after_stroke_id", cursor.strokeId);
        }
        const query = params.size ? `?${params.toString()}` : "";
        const current = await api<LiveSession | null>(
          `/whiteboard/courses/${selectedCourseId}/session${query}`,
          token ?? undefined,
        );
        if (active) {
          if (!current) {
            syncCursorRef.current = null;
            setSession(null);
          } else {
            const previousCursor = syncCursorRef.current;
            const sameSession = previousCursor?.sessionId === current.id;
            const cursor = {
              sessionId: current.id,
              generation: current.board_generation,
              strokeId: current.strokes.length
                ? current.strokes[current.strokes.length - 1].id
                : (sameSession ? previousCursor.strokeId : null),
            };
            syncCursorRef.current = cursor;
            setSession((previous) => {
              if (!sameSession || current.strokes_are_snapshot || !previous || previous.id !== current.id) {
                return current;
              }
              if (!current.strokes.length && previous.is_active === current.is_active) {
                return previous;
              }
              const existingIds = new Set(previous.strokes.map((stroke) => stroke.id));
              const mergedStrokes = [...previous.strokes, ...current.strokes.filter(
                (stroke) => !existingIds.has(stroke.id),
              )].sort((left, right) => (
                left.created_at.localeCompare(right.created_at) ||
                left.id.localeCompare(right.id)
              ));
              return {
                ...previous,
                is_active: current.is_active,
                board_generation: current.board_generation,
                strokes: mergedStrokes,
              };
            });
          }
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Could not sync the whiteboard.");
        }
      } finally {
        inFlight = false;
      }
    };
    void poll();
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void poll();
    };
    const timer = window.setInterval(() => void poll(), 2500);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [hasJoined, resolveToken, role, selectedCourseId]);

  useEffect(() => {
    if (role === "admin" || !session?.is_active) {
      setMessages([]);
      return;
    }
    let active = true;
    let inFlight = false;
    const poll = async () => {
      if (!active || inFlight || document.visibilityState !== "visible") return;
      inFlight = true;
      try {
        const token = await resolveToken();
        const current = await api<ChatMessage[]>(
          `/whiteboard/sessions/${session.id}/messages`,
          token ?? undefined,
        );
        if (active) {
          setMessages((previous) => {
            if (
              previous.length === current.length &&
              previous.every((message, index) => message.id === current[index]?.id)
            ) {
              return previous;
            }
            return current;
          });
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Could not load class chat.");
        }
      } finally {
        inFlight = false;
      }
    };
    void poll();
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") void poll();
    };
    const timer = window.setInterval(() => void poll(), 5000);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [resolveToken, role, session?.id, session?.is_active]);

  const strokes = session?.strokes ?? [];
  const paintBoard = useCallback(() => {
    const canvas = boardCanvasRef.current;
    const overlay = canvasRef.current;
    if (!canvas || !overlay) return;
    const bounds = overlay.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const ratio = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(bounds.width * ratio);
    const pixelHeight = Math.round(bounds.height * ratio);
    const resized = canvas.width !== pixelWidth || canvas.height !== pixelHeight;
    if (resized) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
      overlay.width = pixelWidth;
      overlay.height = pixelHeight;
      paintedBoardRef.current = null;
    }
    const context = canvas.getContext("2d");
    if (!context) return;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    let painted = paintedBoardRef.current;
    const generation = session?.board_generation ?? 0;
    const reset =
      painted === null ||
      painted.generation !== generation ||
      painted.strokeIds.length > strokes.length ||
      painted.strokeIds.some((id, index) => strokes[index]?.id !== id);
    if (reset) {
      context.clearRect(0, 0, bounds.width, bounds.height);
      context.fillStyle = "#ffffff";
      context.fillRect(0, 0, bounds.width, bounds.height);
      context.fillStyle = "#e9efec";
      for (let x = 22; x < bounds.width; x += 24) {
        for (let y = 22; y < bounds.height; y += 24) {
          context.beginPath();
          context.arc(x, y, 0.8, 0, Math.PI * 2);
          context.fill();
        }
      }
      for (const stroke of strokes) {
        drawStroke(context, stroke, bounds.width, bounds.height);
      }
      painted = {
        generation,
        strokeIds: strokes.map((stroke) => stroke.id),
      };
      paintedBoardRef.current = painted;
      return;
    }
    if (!painted) return;
    for (const stroke of strokes.slice(painted.strokeIds.length)) {
      drawStroke(context, stroke, bounds.width, bounds.height);
    }
    if (painted.strokeIds.length !== strokes.length) {
      paintedBoardRef.current = {
        ...painted,
        strokeIds: strokes.map((stroke) => stroke.id),
      };
    }
  }, [session?.board_generation, strokes]);

  useEffect(() => {
    paintBoard();
  }, [paintBoard]);

  const paintPreview = useCallback(() => {
    const canvas = canvasRef.current;
    const board = boardCanvasRef.current;
    if (!canvas || !board) return;
    const bounds = canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const ratio = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(bounds.width * ratio);
    const pixelHeight = Math.round(bounds.height * ratio);
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    const context = canvas.getContext("2d");
    if (!context) return;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, bounds.width, bounds.height);
    if (activeStroke) drawStroke(context, activeStroke, bounds.width, bounds.height);
  }, [activeStroke]);

  useEffect(() => {
    paintPreview();
  }, [paintPreview]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const observer = new ResizeObserver(() => {
      paintedBoardRef.current = null;
      paintBoard();
      paintPreview();
    });
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [paintBoard, paintPreview]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  async function startSession() {
    if (!course) {
      setError(
        isTeacher
          ? "No course is assigned to your teacher account yet. Ask an administrator to assign you to a course."
          : "Select a course before starting a live class.",
      );
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const token = await resolveToken();
      const started = await api<LiveSession>(
        `/whiteboard/courses/${course.id}/sessions`,
        token ?? undefined,
        { method: "POST" },
      );
      syncCursorRef.current = {
        sessionId: started.id,
        generation: started.board_generation,
        strokeId: started.strokes.at(-1)?.id ?? null,
      };
      setSession(started);
      setCourses((current) => current.map((item) => (
        item.id === course.id ? { ...item, is_live: true } : item
      )));
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Could not start this class.");
    } finally {
      setStarting(false);
    }
  }

  async function joinSession() {
    if (!course) return;
    setJoining(true);
    setError(null);
    try {
      const token = await resolveToken();
      const joined = await api<LiveSession>(
        `/whiteboard/courses/${course.id}/join`,
        token ?? undefined,
        { method: "POST" },
      );
      syncCursorRef.current = {
        sessionId: joined.id,
        generation: joined.board_generation,
        strokeId: joined.strokes.at(-1)?.id ?? null,
      };
      setSession(joined);
      setHasJoined(true);
    } catch (joinError) {
      setError(joinError instanceof Error ? joinError.message : "Could not join this class.");
      void loadCourses();
    } finally {
      setJoining(false);
    }
  }

  async function endSession() {
    if (!session || !window.confirm("End this live class? Students will lose access to the board and chat.")) return;
    setError(null);
    try {
      const token = await resolveToken();
      await api<void>(`/whiteboard/sessions/${session.id}/end`, token ?? undefined, { method: "POST" });
      syncCursorRef.current = null;
      setSession(null);
      setMessages([]);
      setCourses((current) => current.map((item) => (
        item.id === session.course_id ? { ...item, is_live: false } : item
      )));
    } catch (endError) {
      setError(endError instanceof Error ? endError.message : "Could not end this class.");
    }
  }

  function pointFromEvent(event: ReactPointerEvent<HTMLCanvasElement>): Point {
    const bounds = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width)),
      y: Math.min(1, Math.max(0, (event.clientY - bounds.top) / bounds.height)),
    };
  }

  function beginStroke(event: ReactPointerEvent<HTMLCanvasElement>) {
    if (!canControlBoard || !session?.is_active || event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drawingRef.current = true;
    const point = pointFromEvent(event);
    const next = {
      tool,
      color: inkColor,
      width: inkWidth,
      points: [point, point],
    };
    strokeRef.current = next;
    setActiveStroke({ ...next, points: [...next.points] });
  }

  function moveStroke(event: ReactPointerEvent<HTMLCanvasElement>) {
    const previous = strokeRef.current;
    if (!drawingRef.current || !previous) return;
    const point = pointFromEvent(event);
    if (previous.tool === "pen" || previous.tool === "eraser") {
      previous.points.push(point);
    } else {
      previous.points[1] = point;
    }
    if (previewFrameRef.current === null) {
      previewFrameRef.current = window.requestAnimationFrame(() => {
        previewFrameRef.current = null;
        const current = strokeRef.current;
        if (current) setActiveStroke({ ...current, points: [...current.points] });
      });
    }
  }

  async function finishStroke(event: ReactPointerEvent<HTMLCanvasElement>) {
    const draft = strokeRef.current;
    if (!drawingRef.current || !draft || !session) return;
    const canvas = event.currentTarget;
    const pointerId = event.pointerId;
    drawingRef.current = false;
    strokeRef.current = null;
    if (previewFrameRef.current !== null) {
      window.cancelAnimationFrame(previewFrameRef.current);
      previewFrameRef.current = null;
    }
    setActiveStroke(null);
    try {
      const token = await resolveToken();
      const saved = await api<Stroke>(
        `/whiteboard/sessions/${session.id}/strokes`,
        token ?? undefined,
        { method: "POST", body: JSON.stringify(draft) },
      );
      setSession((current) => {
        if (!current || current.id !== saved.session_id) return current;
        const mergedStrokes = [...current.strokes, saved].sort((left, right) => (
          left.created_at.localeCompare(right.created_at) ||
          left.id.localeCompare(right.id)
        ));
        syncCursorRef.current = {
          sessionId: current.id,
          generation: current.board_generation,
          strokeId: mergedStrokes.at(-1)?.id ?? null,
        };
        return { ...current, strokes: mergedStrokes };
      });
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save your drawing.");
    } finally {
      if (canvas.isConnected && canvas.hasPointerCapture(pointerId)) {
        canvas.releasePointerCapture(pointerId);
      }
    }
  }

  async function clearBoard() {
    if (!session || !window.confirm("Clear the entire whiteboard for everyone?")) return;
    try {
      const token = await resolveToken();
      await api<void>(`/whiteboard/sessions/${session.id}/strokes`, token ?? undefined, { method: "DELETE" });
      const nextGeneration = session.board_generation + 1;
      syncCursorRef.current = {
        sessionId: session.id,
        generation: nextGeneration,
        strokeId: null,
      };
      setSession((current) => current ? { ...current, board_generation: nextGeneration, strokes: [] } : current);
      setError(null);
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "Could not clear the board.");
    }
  }

  async function undoStroke() {
    if (!session) return;
    try {
      const token = await resolveToken();
      await api<void>(`/whiteboard/sessions/${session.id}/undo`, token ?? undefined, { method: "POST" });
      const nextGeneration = session.board_generation + 1;
      const nextStrokes = session.strokes.slice(0, -1);
      syncCursorRef.current = {
        sessionId: session.id,
        generation: nextGeneration,
        strokeId: nextStrokes.at(-1)?.id ?? null,
      };
      setSession((current) => current ? { ...current, board_generation: nextGeneration, strokes: nextStrokes } : current);
      setError(null);
    } catch (undoError) {
      setError(undoError instanceof Error ? undoError.message : "Could not undo the last stroke.");
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = messageDraft.trim();
    if (!session || !content || sending) return;
    setSending(true);
    try {
      const token = await resolveToken();
      const created = await api<ChatMessage>(
        `/whiteboard/sessions/${session.id}/messages`,
        token ?? undefined,
        { method: "POST", body: JSON.stringify({ content }) },
      );
      setMessages((current) => [...current, created].slice(-100));
      setMessageDraft("");
      setError(null);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Could not send your message.");
    } finally {
      setSending(false);
    }
  }

  const tools: { id: Tool; label: string; icon: typeof PenLine }[] = [
    { id: "pen", label: "Pen", icon: PenLine },
    { id: "eraser", label: "Eraser", icon: Eraser },
    { id: "line", label: "Line", icon: Minus },
    { id: "rectangle", label: "Rectangle", icon: Square },
    { id: "ellipse", label: "Oval", icon: Circle },
  ];

  if (loading) {
    return (
      <div className="grid min-h-[60vh] place-items-center text-sm text-slate-500">
        <span className="flex items-center gap-2"><LoaderCircle className="animate-spin" size={18} /> Loading your classroom…</span>
      </div>
    );
  }

  return (
    <main className="mx-auto w-full max-w-[1600px] min-w-0 space-y-6">
      <header className="flex flex-col gap-4 rounded-2xl bg-green-900 px-5 py-6 text-white shadow-sm sm:flex-row sm:items-center sm:justify-between sm:px-7">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-200">SiliconBrains University · Live learning</p>
          <h1 className="mt-1 flex items-center gap-2 font-heading text-2xl font-bold sm:text-3xl">
            <Presentation size={27} aria-hidden /> Live Classroom
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-emerald-50/80">
            A shared teaching board with a focused class discussion alongside it.
          </p>
        </div>
        <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-end">
          {courses.length > 0 && (
            <label className="w-full sm:min-w-64 sm:max-w-xs">
              <span className="mb-1.5 block text-xs font-semibold text-emerald-100">Course</span>
              <select
                value={selectedCourseId}
                onChange={(event) => {
                  setHasJoined(false);
                  setSession(null);
                  setSelectedCourseId(event.target.value);
                }}
                className="h-11 w-full rounded-xl border border-white/20 bg-white px-3 text-sm font-medium text-green-950 outline-none focus:ring-2 focus:ring-emerald-300"
              >
                {courses.map((item) => (
                  <option key={item.id} value={item.id}>{item.code} · {item.title}{item.is_live ? " · LIVE" : ""}</option>
                ))}
              </select>
            </label>
          )}
          {isTeacher && (
            <button
              type="button"
              onClick={() => void startSession()}
              disabled={starting}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-white px-4 text-sm font-semibold text-green-900 shadow-sm transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {starting ? <LoaderCircle className="animate-spin" size={17} /> : <Presentation size={17} />}
              {course?.is_live ? "Open Live Classroom" : "Create Live Classroom"}
            </button>
          )}
        </div>
      </header>

      {error && (
        <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} aria-label="Dismiss error"><X size={18} /></button>
        </div>
      )}

      {courses.length === 0 ? (
        <section className="grid min-h-72 place-items-center rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <div>
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-emerald-50 text-green-800"><UsersRound size={25} /></div>
            <h2 className="mt-4 font-heading text-xl font-bold text-slate-900">No course classrooms yet</h2>
            <p className="mt-2 max-w-md text-sm text-slate-500">
              {isTeacher
                ? "A live classroom will appear here for each course assigned to you."
                : isAdmin
                  ? "Choose a course to start or manage its live classroom."
                  : "Join a course to access its live whiteboard and class chat."}
            </p>
          </div>
        </section>
      ) : session?.course_id !== selectedCourseId || !session?.is_active ? (
        <section className="grid min-h-72 place-items-center rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <div>
            <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-emerald-50 text-green-800"><Presentation size={25} /></div>
            <h2 className="mt-4 font-heading text-xl font-bold text-slate-900">
              {role === "student" && course?.is_live
                ? "Your live class is ready"
                : canControlBoard
                  ? "Ready when you are"
                  : "Your teacher hasn’t started class yet"}
            </h2>
            <p className="mt-2 max-w-md text-sm text-slate-500">
              {role === "student" && course?.is_live
                ? `Join ${course.title} to view the teacher’s board and participate in class chat.`
                : isTeacher
                  ? `Start a live session for ${course?.title ?? "this course"} to share your board and open class chat.`
                  : isAdmin
                    ? `Create a live session for ${course?.title ?? "this course"}. Enrolled students and the assigned teacher can join it.`
                    : `The board and class chat for ${course?.title ?? "this course"} will appear here when the teacher goes live.`}
            </p>
            {role === "student" && course?.is_live ? (
              <button
                type="button"
                onClick={() => void joinSession()}
                disabled={joining}
                className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-green-800 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-green-900 disabled:cursor-wait disabled:opacity-60"
              >
                {joining ? <LoaderCircle className="animate-spin" size={17} /> : <UsersRound size={17} />}
                Join live class
              </button>
            ) : canControlBoard && (
              <button
                type="button"
                onClick={() => void startSession()}
                disabled={starting || !course}
                className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-green-800 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-green-900 disabled:cursor-wait disabled:opacity-60"
              >
                {starting ? <LoaderCircle className="animate-spin" size={17} /> : <Presentation size={17} />}
                Start live class
              </button>
            )}
          </div>
        </section>
      ) : (
        <section className={`grid min-w-0 gap-4 ${isAdmin ? "" : "xl:grid-cols-[minmax(0,1fr)_360px]"}`}>
          <div className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 sm:px-5">
              <div className="flex min-w-0 items-center gap-2.5">
                <span className="relative flex h-2.5 w-2.5 shrink-0">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-slate-900">{course?.title ?? "Live whiteboard"}</p>
                  <p className="text-xs text-slate-500">{canControlBoard ? "You’re hosting · students have read-only access" : "Live with your class · board is read-only"}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {canControlBoard && (
                  <button
                    type="button"
                    onClick={() => void endSession()}
                    className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-rose-200 px-3 text-xs font-semibold text-rose-700 transition hover:bg-rose-50"
                  >
                    <X size={15} /> End class
                  </button>
                )}
              </div>
            </div>
            {canControlBoard && (
              <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 bg-slate-50/80 px-3 py-2.5 sm:px-4">
                <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1" aria-label="Drawing tools">
                  {tools.map(({ id, label, icon: Icon }) => (
                    <button
                      type="button"
                      key={id}
                      title={TOOL_LABELS[id]}
                      aria-label={TOOL_LABELS[id]}
                      aria-pressed={tool === id}
                      onClick={() => setTool(id)}
                      className={`grid h-9 w-9 place-items-center rounded-lg transition ${tool === id ? "bg-green-800 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"}`}
                    >
                      <Icon size={17} />
                    </button>
                  ))}
                </div>
                <div className="flex h-11 items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-2">
                  {PALETTE.map((color) => (
                    <button
                      key={color}
                      type="button"
                      onClick={() => setInkColor(color)}
                      aria-label={`Use ${color} ink`}
                      aria-pressed={inkColor === color}
                      className={`h-5 w-5 rounded-full border border-black/10 ${inkColor === color ? "ring-2 ring-green-700 ring-offset-2" : ""}`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                  <label className="relative ml-1 grid h-6 w-6 cursor-pointer place-items-center overflow-hidden rounded-full border border-slate-300 text-xs font-bold text-slate-600" title="Choose another ink color">
                    +
                    <input type="color" value={inkColor} onChange={(event) => setInkColor(event.target.value)} className="absolute inset-0 h-full w-full cursor-pointer opacity-0" aria-label="Custom ink color" />
                  </label>
                </div>
                <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-medium text-slate-600">
                  <span>Size</span>
                  <input type="range" min={1} max={16} value={inkWidth} onChange={(event) => setInkWidth(Number(event.target.value))} className="w-20 accent-green-800" aria-label="Pen size" />
                </label>
                <div className="ml-auto flex items-center gap-1">
                  <button type="button" onClick={() => void undoStroke()} disabled={strokes.length === 0} className="grid h-9 w-9 place-items-center rounded-lg text-slate-600 hover:bg-white disabled:opacity-40" aria-label="Undo last stroke" title="Undo"><Undo2 size={17} /></button>
                  <button type="button" onClick={() => void clearBoard()} disabled={strokes.length === 0} className="grid h-9 w-9 place-items-center rounded-lg text-rose-700 hover:bg-rose-50 disabled:opacity-40" aria-label="Clear whiteboard" title="Clear board"><Trash2 size={17} /></button>
                </div>
              </div>
            )}

            <div className="bg-slate-100 p-2 sm:p-4">
              <div className="relative aspect-[16/10] min-h-[300px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-inner sm:aspect-[16/9]">
                <canvas
                  ref={boardCanvasRef}
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-0 h-full w-full"
                />
                <canvas
                  ref={canvasRef}
                  aria-label={canControlBoard ? "Teaching whiteboard canvas" : "Read-only class whiteboard"}
                  onPointerDown={beginStroke}
                  onPointerMove={moveStroke}
                  onPointerUp={(event) => void finishStroke(event)}
                  onPointerCancel={(event) => void finishStroke(event)}
                  className={`absolute inset-0 h-full w-full touch-none ${canControlBoard ? "cursor-crosshair" : "cursor-default"}`}
                />
                {!canControlBoard && (
                  <span className="pointer-events-none absolute bottom-3 right-3 rounded-lg bg-white/90 px-2.5 py-1.5 text-[11px] font-medium text-slate-500 shadow-sm">
                    Read only
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between px-1 pt-2 text-[11px] text-slate-500">
                <span>{canControlBoard ? `Tool: ${TOOL_LABELS[tool]}` : "Your teacher is presenting"}</span>
                <span className="inline-flex items-center gap-1"><Check size={13} className="text-emerald-700" /> Synced live</span>
              </div>
            </div>
          </div>

          {!isAdmin && <aside className="flex min-h-[480px] min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm xl:sticky xl:top-5 xl:h-[calc(100dvh-2.5rem)] xl:min-h-[600px]">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-green-800"><MessageCircle size={19} /></span>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Class chat</h2>
                  <p className="text-xs text-slate-500">Visible to this class only</p>
                </div>
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-green-800">LIVE</span>
            </div>
            <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50/60 p-4" aria-live="polite" aria-label="Class chat messages">
              {messages.length === 0 ? (
                <div className="grid h-full min-h-48 place-items-center text-center">
                  <div>
                    <span className="mx-auto grid h-11 w-11 place-items-center rounded-full bg-white text-slate-400 shadow-sm"><MessageCircle size={19} /></span>
                    <p className="mt-3 text-sm font-semibold text-slate-700">Start the conversation</p>
                    <p className="mt-1 text-xs text-slate-500">Questions and answers disappear after 10 minutes.</p>
                  </div>
                </div>
              ) : messages.map((message) => {
                const ownMessage = message.is_mine;
                return (
                  <article key={message.id} className={`flex gap-2.5 ${ownMessage ? "flex-row-reverse" : ""}`}>
                    <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-[10px] font-bold ${message.sender_role === "teacher" ? "bg-green-800 text-white" : "bg-sky-100 text-sky-800"}`}>
                      {initials(message.sender_name)}
                    </span>
                    <div className={`min-w-0 max-w-[85%] ${ownMessage ? "text-right" : ""}`}>
                      <div className={`mb-1 flex items-center gap-1.5 text-[10px] text-slate-500 ${ownMessage ? "justify-end" : ""}`}>
                        <span className="max-w-36 truncate font-semibold text-slate-700">{message.sender_name}</span>
                        <span className="capitalize">{message.sender_role}</span>
                        <time dateTime={message.created_at}>{new Date(message.created_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time>
                      </div>
                      <p className={`whitespace-pre-wrap break-words rounded-2xl px-3 py-2 text-left text-sm leading-relaxed ${ownMessage ? "rounded-tr-sm bg-green-800 text-white" : "rounded-tl-sm border border-slate-100 bg-white text-slate-800 shadow-sm"}`}>
                        {message.content}
                      </p>
                    </div>
                  </article>
                );
              })}
              <div ref={messageEndRef} />
            </div>
            <form onSubmit={(event) => void sendMessage(event)} className="border-t border-slate-100 bg-white p-3">
              <label htmlFor="whiteboard-chat-message" className="sr-only">Message your class</label>
              <div className="flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50 p-1.5 focus-within:border-emerald-600 focus-within:ring-2 focus-within:ring-emerald-100">
                <textarea
                  id="whiteboard-chat-message"
                  value={messageDraft}
                  onChange={(event) => setMessageDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                  maxLength={1000}
                  rows={1}
                  placeholder="Ask or share something…"
                  className="max-h-28 min-h-10 flex-1 resize-y bg-transparent px-2 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400"
                />
                <button
                  type="submit"
                  disabled={!messageDraft.trim() || sending}
                  className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-green-800 text-white transition hover:bg-green-900 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="Send message"
                >
                  {sending ? <LoaderCircle className="animate-spin" size={16} /> : <Send size={16} />}
                </button>
              </div>
              <p className="mt-2 px-1 text-[10px] text-slate-400">Messages are deleted automatically after 10 minutes.</p>
            </form>
          </aside>}
        </section>
      )}
      {isAdmin && (
        <p className="text-center text-xs text-slate-400">Admins can start and manage live course boards. Class chat is available to the assigned teacher and enrolled students.</p>
      )}
    </main>
  );
}
