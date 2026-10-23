"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import {
  ArrowUp,
  ArrowLeft,
  Clock3,
  LoaderCircle,
  Mic,
  MessageCircle,
  MessagesSquare,
  Play,
  Search,
  Send,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";
import { api, getBaseUrl, getDevAuthToken } from "@/lib/api";

type ConversationKind =
  | "student_room"
  | "peer_direct"
  | "admin_support"
  | "teacher_support";

interface Conversation {
  id: string;
  kind: ConversationKind;
  title: string;
  other_user_id?: string | null;
  other_user_role?: "student" | "teacher" | "admin" | null;
  last_message?: string | null;
  last_message_at?: string | null;
  expires_at: string;
  is_shared_room: boolean;
}

interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_name: string;
  sender_role: "student" | "teacher" | "admin";
  sender_avatar_url?: string | null;
  is_mine: boolean;
  content: string;
  audio_url?: string | null;
  audio_mime_type?: string | null;
  audio_size_bytes?: number | null;
  created_at: string;
}

interface StudentOption {
  id: string;
  full_name: string;
  avatar_url?: string | null;
}

const ROLE_TOKENS = {
  student: "student",
  teacher: "teacher",
  admin: "admin",
} as const;

function displayTime(value?: string | null): string {
  if (!value) return "";
  return new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function avatarInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function CommunityChat({ role }: { role: "student" | "teacher" | "admin" }) {
  const { getToken } = useAuth();
  const isStudent = role === "student";
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [studentSearch, setStudentSearch] = useState("");
  const [messageText, setMessageText] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [uploadingAudio, setUploadingAudio] = useState(false);
  const [loadingAudioIds, setLoadingAudioIds] = useState<Record<string, boolean>>({});
  const [startingConversation, setStartingConversation] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageEndRef = useRef<HTMLDivElement>(null);
  const selectedConversationIdRef = useRef<string | null>(null);
  const messagesRequestRef = useRef(new Set<string>());
  const conversationsRequestRef = useRef(false);
  const conversationRevisionRef = useRef(0);
  const messageRevisionRef = useRef(new Map<string, number>());
  const nearMessageBottomRef = useRef(true);
  const lastMessageIdRef = useRef<string | null>(null);
  const manuallyDismissedSelectionRef = useRef(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const sendRecordingRef = useRef(false);
  const audioUrlsRef = useRef<Record<string, string>>({});
  const audioLoadingRef = useRef(new Set<string>());
  const mountedRef = useRef(true);
  const [audioUrls, setAudioUrls] = useState<Record<string, string>>({});
  selectedConversationIdRef.current = selectedId;

  const resolveToken = useCallback(async () => {
    let token = await getToken();
    if (
      !token &&
      (process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.NODE_ENV === "development")
    ) {
      token = getDevAuthToken(ROLE_TOKENS[role]);
    }
    return token;
  }, [getToken, role]);

  const loadConversations = useCallback(async () => {
    if (conversationsRequestRef.current) return;
    conversationsRequestRef.current = true;
    const requestRevision = conversationRevisionRef.current;
    try {
      const token = await resolveToken();
      const data = await api<Conversation[]>("/community-chat/conversations", token ?? undefined);
      if (requestRevision !== conversationRevisionRef.current) return;
      setConversations((current) => {
        const unchanged = current.length === data.length && current.every((item, index) => {
          const next = data[index];
          return item.id === next.id && item.title === next.title &&
            item.last_message === next.last_message &&
            item.last_message_at === next.last_message_at &&
            item.expires_at === next.expires_at;
        });
        return unchanged ? current : data;
      });
      setSelectedId((current) =>
        current ?? (manuallyDismissedSelectionRef.current ? null : data[0]?.id ?? null),
      );
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Could not load your chats.");
    } finally {
      conversationsRequestRef.current = false;
      setLoadingConversations(false);
    }
  }, [resolveToken]);

  const loadMessages = useCallback(
    async (conversationId: string, showSpinner = false) => {
      if (messagesRequestRef.current.has(conversationId)) return;
      messagesRequestRef.current.add(conversationId);
      const requestRevision = messageRevisionRef.current.get(conversationId) ?? 0;
      if (showSpinner) setLoadingMessages(true);
      try {
        const token = await resolveToken();
        const data = await api<Message[]>(
          `/community-chat/conversations/${conversationId}/messages`,
          token ?? undefined,
        );
        if (
          selectedConversationIdRef.current === conversationId &&
          requestRevision === (messageRevisionRef.current.get(conversationId) ?? 0)
        ) {
          setMessages((current) => {
            const pending = current.filter(
              (message) => message.conversation_id === conversationId && message.id.startsWith("pending:"),
            );
            const nextMessages = pending.length
              ? [...data, ...pending].sort(
                  (left, right) => Date.parse(left.created_at) - Date.parse(right.created_at),
                )
              : data;
            const unchanged = current.length === nextMessages.length && current.every((message, index) => {
              const next = nextMessages[index];
              return message.id === next.id && message.content === next.content &&
                message.created_at === next.created_at &&
                message.sender_name === next.sender_name &&
                message.sender_avatar_url === next.sender_avatar_url &&
                message.audio_url === next.audio_url;
            });
            return unchanged ? current : nextMessages;
          });
        }
      } catch (loadError) {
        if (selectedConversationIdRef.current === conversationId) {
          setError(loadError instanceof Error ? loadError.message : "Could not load messages.");
        }
      } finally {
        messagesRequestRef.current.delete(conversationId);
        if (selectedConversationIdRef.current === conversationId) {
          setLoadingMessages(false);
        }
      }
    },
    [resolveToken],
  );

  useEffect(() => {
    void loadConversations();
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void loadConversations();
    };
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void loadConversations();
    }, 10000);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [loadConversations]);

  useEffect(() => {
    nearMessageBottomRef.current = true;
    lastMessageIdRef.current = null;
    setMessages([]);
    if (!selectedId) {
      setLoadingMessages(false);
      return;
    }
    setLoadingMessages(true);
    void loadMessages(selectedId, true);
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void loadMessages(selectedId);
    };
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void loadMessages(selectedId);
    }, 3000);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [loadMessages, selectedId]);

  useEffect(() => {
    const latestMessageId = messages.at(-1)?.id ?? null;
    if (latestMessageId === lastMessageIdRef.current) return;
    lastMessageIdRef.current = latestMessageId;
    if (latestMessageId && nearMessageBottomRef.current) {
      messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages]);

  useEffect(
    () => {
      mountedRef.current = true;
      const audioUrls = audioUrlsRef.current;
      return () => {
        mountedRef.current = false;
        if (recorderRef.current) {
          recorderRef.current.onstop = null;
          recorderRef.current.stop();
        }
        recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
        Object.values(audioUrls).forEach((url) => URL.revokeObjectURL(url));
      };
    },
    [],
  );

  useEffect(() => {
    let active = true;
    const loadStudents = async () => {
      try {
        const token = await resolveToken();
        const data = await api<StudentOption[]>(
          `/community-chat/students?search=${encodeURIComponent(studentSearch)}`,
          token ?? undefined,
        );
        if (active) setStudents(data);
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Could not load students.");
        }
      }
    };
    const timer = window.setTimeout(() => void loadStudents(), studentSearch ? 250 : 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [resolveToken, studentSearch]);

  const selectedConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === selectedId) ?? null,
    [conversations, selectedId],
  );

  async function startDirectChat(student: StudentOption) {
    setStartingConversation(true);
    setError(null);
    try {
      const token = await resolveToken();
      const conversation = await api<Conversation>(
        `/community-chat/direct/${student.id}`,
        token ?? undefined,
        { method: "POST" },
      );
      conversationRevisionRef.current += 1;
      setConversations((current) => [
        conversation,
        ...current.filter((item) => item.id !== conversation.id),
      ]);
      manuallyDismissedSelectionRef.current = false;
      setSelectedId(conversation.id);
      setStudentSearch("");
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Could not start this chat.");
    } finally {
      setStartingConversation(false);
    }
  }

  async function startStaffChat(staffRole: "admin" | "teacher") {
    setStartingConversation(true);
    setError(null);
    try {
      const token = await resolveToken();
      const conversation = await api<Conversation>(
        `/community-chat/staff/${staffRole}`,
        token ?? undefined,
        { method: "POST" },
      );
      conversationRevisionRef.current += 1;
      setConversations((current) => [
        conversation,
        ...current.filter((item) => item.id !== conversation.id),
      ]);
      manuallyDismissedSelectionRef.current = false;
      setSelectedId(conversation.id);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Could not open staff support.");
    } finally {
      setStartingConversation(false);
    }
  }

  function acceptSentMessage(message: Message) {
    conversationRevisionRef.current += 1;
    const conversationRevision = messageRevisionRef.current.get(message.conversation_id) ?? 0;
    messageRevisionRef.current.set(message.conversation_id, conversationRevision + 1);
    if (selectedConversationIdRef.current === message.conversation_id) {
      setMessages((current) => {
        const withoutPending = current.filter((item) => !item.id.startsWith("pending:"));
        if (withoutPending.some((item) => item.id === message.id)) return withoutPending;
        return [...withoutPending, message].slice(-100);
      });
    }
    setConversations((current) => {
      const conversation = current.find((item) => item.id === message.conversation_id);
      if (!conversation) return current;
      const updated = {
        ...conversation,
        last_message: message.content,
        last_message_at: message.created_at,
      };
      return [updated, ...current.filter((item) => item.id !== message.conversation_id)];
    });
  }

  async function sendAudioFile(file: File) {
    if (!selectedId || uploadingAudio) return;
    setUploadingAudio(true);
    setError(null);
    try {
      const token = await resolveToken();
      const form = new FormData();
      form.append("file", file);
      const sentMessage = await api<Message>(
        `/community-chat/conversations/${selectedId}/audio`,
        token ?? undefined,
        { method: "POST", body: form },
      );
      acceptSentMessage(sentMessage);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Could not send voice message.");
    } finally {
      setUploadingAudio(false);
    }
  }

  function finishRecording(shouldSend: boolean) {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    sendRecordingRef.current = shouldSend;
    recorder.stop();
  }

  async function toggleRecording() {
    if (recording) {
      finishRecording(true);
      return;
    }
    if (
      !selectedId ||
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError("Audio recording is not supported in this browser.");
      return;
    }
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingStreamRef.current = stream;
      const preferredType = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(
        stream,
        preferredType ? { mimeType: preferredType } : undefined,
      );
      recorderRef.current = recorder;
      recordingChunksRef.current = [];
      sendRecordingRef.current = false;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordingChunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const shouldSend = sendRecordingRef.current;
        sendRecordingRef.current = false;
        const blob = new Blob(recordingChunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        stream.getTracks().forEach((track) => track.stop());
        recordingStreamRef.current = null;
        recorderRef.current = null;
        setRecording(false);
        if (!shouldSend) {
          recordingChunksRef.current = [];
          return;
        }
        if (!blob.size) {
          setError("The recording was empty. Try recording again.");
          return;
        }
        const extension = blob.type.includes("mp4")
          ? "m4a"
          : blob.type.includes("ogg")
            ? "ogg"
            : "webm";
        void sendAudioFile(new File([blob], `voice-message.${extension}`, { type: blob.type }));
      };
      recorder.start();
      setRecording(true);
    } catch (recordError) {
      recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
      recordingStreamRef.current = null;
      setError(
        recordError instanceof Error
          ? recordError.message
          : "Microphone access was denied or unavailable.",
      );
    }
  }

  async function loadAudioMessage(message: Message) {
    if (
      !message.audio_url ||
      audioUrlsRef.current[message.id] ||
      audioLoadingRef.current.has(message.id)
    ) {
      return;
    }
    audioLoadingRef.current.add(message.id);
    setLoadingAudioIds((current) => ({ ...current, [message.id]: true }));
    try {
      const token = await resolveToken();
      const response = await fetch(`${getBaseUrl()}${message.audio_url}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      if (!response.ok) throw new Error("Could not load this voice message.");
      const url = URL.createObjectURL(await response.blob());
      if (mountedRef.current) {
        audioUrlsRef.current[message.id] = url;
        setAudioUrls((current) => ({ ...current, [message.id]: url }));
      } else {
        URL.revokeObjectURL(url);
      }
    } catch (audioError) {
      if (mountedRef.current) {
        setError(audioError instanceof Error ? audioError.message : "Could not load voice message.");
      }
    } finally {
      audioLoadingRef.current.delete(message.id);
      if (mountedRef.current) {
        setLoadingAudioIds((current) => ({ ...current, [message.id]: false }));
      }
    }
  }

  async function sendMessage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedId || !messageText.trim() || sending) return;
    const conversationId = selectedId;
    const content = messageText.trim();
    const pendingId = `pending:${Date.now()}:${Math.random().toString(36).slice(2)}`;
    const pendingMessage: Message = {
      id: pendingId,
      conversation_id: conversationId,
      sender_id: "current-user",
      sender_name: "You",
      sender_role: role,
      is_mine: true,
      content,
      created_at: new Date().toISOString(),
    };
    const conversationRevision = messageRevisionRef.current.get(conversationId) ?? 0;
    messageRevisionRef.current.set(conversationId, conversationRevision + 1);
    setMessages((current) => [...current, pendingMessage].slice(-100));
    setMessageText("");
    setSending(true);
    setError(null);
    try {
      const token = await resolveToken();
      const sentMessage = await api<Message>(
        `/community-chat/conversations/${conversationId}/messages`,
        token ?? undefined,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        },
      );
      acceptSentMessage(sentMessage);
    } catch (sendError) {
      if (selectedConversationIdRef.current === conversationId) {
        setMessages((current) => current.filter((message) => message.id !== pendingId));
        setMessageText((current) => current || content);
      }
      setError(sendError instanceof Error ? sendError.message : "Could not send your message.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="flex h-[calc(100dvh-8.75rem)] min-h-[32rem] min-w-0 flex-col overflow-hidden rounded-2xl border border-cream-300 bg-white shadow-sm lg:h-[calc(100dvh-10rem)]">
      <div className="flex min-h-0 flex-1">
        <aside
          className={`w-full shrink-0 flex-col border-r border-cream-200 lg:flex lg:w-[21rem] ${
            selectedConversation ? "hidden" : "flex"
          }`}
          aria-label="Chat conversations"
        >
          <div className="border-b border-cream-200 px-4 py-4">
            <div className="flex items-center gap-2">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-green-50 text-green-700">
                <MessagesSquare size={20} />
              </span>
              <div>
                <h1 className="font-heading text-lg font-bold text-green-900">Community Chat</h1>
                <p className="text-xs text-ink-muted">
                  {isStudent
                    ? "Connect with your university"
                    : role === "teacher"
                      ? "Student community · student chats"
                      : "Support inbox · student chats"}
                </p>
              </div>
            </div>
            {(isStudent || role === "teacher") && (
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  disabled={startingConversation}
                  onClick={() => void startStaffChat("admin")}
                  className="flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-cream-300 bg-cream-50 px-2 text-xs font-semibold text-green-900 transition hover:bg-cream-100 disabled:opacity-50"
                >
                  <ShieldCheck size={15} /> Admin
                </button>
                {isStudent && (
                  <button
                    type="button"
                    disabled={startingConversation}
                    onClick={() => void startStaffChat("teacher")}
                    className="flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-cream-300 bg-cream-50 px-2 text-xs font-semibold text-green-900 transition hover:bg-cream-100 disabled:opacity-50"
                  >
                    <UsersRound size={15} /> Teacher
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="space-y-1 p-2">
              {loadingConversations && (
                <p className="px-3 py-4 text-sm text-ink-muted">Loading conversations…</p>
              )}
              {!loadingConversations && conversations.length === 0 && (
                <p className="px-3 py-4 text-sm text-ink-muted">No conversations yet.</p>
              )}
              {conversations.map((conversation) => (
                <button
                  type="button"
                  key={conversation.id}
                  onClick={() => setSelectedId(conversation.id)}
                  className={`flex min-h-[4.5rem] w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition ${
                    selectedId === conversation.id
                      ? "bg-green-50 ring-1 ring-green-100"
                      : "hover:bg-cream-50"
                  }`}
                >
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-green-100 text-green-800">
                    {conversation.is_shared_room ? (
                      <UsersRound size={18} />
                    ) : conversation.kind === "admin_support" ? (
                      <ShieldCheck size={18} />
                    ) : conversation.kind === "teacher_support" ? (
                      <MessageCircle size={18} />
                    ) : (
                      <span className="text-xs font-bold">{avatarInitials(conversation.title)}</span>
                    )}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-semibold text-green-900">
                        {conversation.title}
                      </span>
                      <span className="shrink-0 text-[10px] text-ink-muted">
                        {displayTime(conversation.last_message_at)}
                      </span>
                    </span>
                    <span className="mt-1 block truncate text-xs text-ink-muted">
                      {conversation.last_message || "Start the conversation"}
                    </span>
                  </span>
                </button>
              ))}
            </div>

            <div className="border-t border-cream-200 p-3">
                <label className="relative block">
                  <Search
                    size={15}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted"
                  />
                  <input
                    value={studentSearch}
                    onChange={(event) => setStudentSearch(event.target.value)}
                    placeholder={isStudent ? "Find a student" : "Start a chat with a student"}
                    aria-label={isStudent ? "Find a student to chat with" : "Find a student to message"}
                    className="h-11 w-full rounded-xl border border-cream-300 bg-white pl-9 pr-3 text-sm text-ink"
                  />
                </label>
                {(studentSearch || students.length > 0) && (
                  <div className="mt-2 max-h-[calc(100dvh-18rem)] space-y-1 overflow-y-auto">
                    {students.map((student) => (
                      <button
                        type="button"
                        key={student.id}
                        onClick={() => void startDirectChat(student)}
                        disabled={startingConversation}
                        className="flex min-h-11 w-full items-center gap-2 rounded-lg px-2 text-left text-sm text-green-900 hover:bg-cream-50 disabled:opacity-50"
                      >
                        <span className="grid h-8 w-8 shrink-0 place-items-center overflow-hidden rounded-full bg-cream-200 text-[10px] font-bold">
                          {student.avatar_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={student.avatar_url} alt="" className="h-full w-full object-cover" />
                          ) : (
                            avatarInitials(student.full_name)
                          )}
                        </span>
                        <span className="min-w-0 truncate">{student.full_name}</span>
                        <MessageCircle size={14} className="ml-auto shrink-0 text-ink-muted" />
                      </button>
                    ))}
                    {studentSearch && students.length === 0 && (
                      <p className="px-2 py-3 text-xs text-ink-muted">
                        No students match that search.
                      </p>
                    )}
                  </div>
                )}
            </div>
          </div>
        </aside>

        <div
          className={`min-w-0 flex-1 flex-col ${
            selectedConversation ? "flex" : "hidden lg:flex"
          }`}
        >
          {selectedConversation ? (
            <>
              <header className="flex min-h-[4.25rem] items-center gap-3 border-b border-cream-200 px-3 py-2 sm:px-5">
                <button
                  type="button"
                  onClick={() => {
                    manuallyDismissedSelectionRef.current = true;
                    setSelectedId(null);
                  }}
                  className="grid h-11 w-11 shrink-0 place-items-center rounded-xl text-green-700 hover:bg-green-50 lg:hidden"
                  aria-label="Back to conversations"
                >
                  <ArrowLeft size={19} />
                </button>
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-green-100 text-green-800">
                  {selectedConversation.is_shared_room ? (
                    <UsersRound size={18} />
                  ) : (
                    <span className="text-xs font-bold">
                      {avatarInitials(selectedConversation.title)}
                    </span>
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="truncate font-heading text-sm font-bold text-green-900">
                    {selectedConversation.title}
                  </h2>
                  <p className="text-[11px] text-ink-muted">
                    {selectedConversation.is_shared_room
                      ? "Shared university community room"
                      : selectedConversation.kind === "admin_support"
                        ? "Private conversation with the admin team"
                        : selectedConversation.kind === "teacher_support"
                          ? "Private conversation with the teacher team"
                          : "Private student conversation"}
                  </p>
                </div>
                <span className="hidden items-center gap-1 text-[11px] text-ink-muted sm:flex">
                  <Clock3 size={13} /> Clears 10 hours after latest message
                </span>
              </header>

              <div
                onScroll={(event) => {
                  const list = event.currentTarget;
                  nearMessageBottomRef.current =
                    list.scrollHeight - list.scrollTop - list.clientHeight < 120;
                }}
                className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto bg-cream-50/60 px-3 py-4 sm:px-5"
                aria-live="polite"
                aria-label="Messages"
              >
                {loadingMessages && messages.length === 0 && (
                  <p className="m-auto text-sm text-ink-muted">Loading messages…</p>
                )}
                {!loadingMessages && messages.length === 0 && (
                  <div className="m-auto max-w-xs text-center">
                    <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-white text-green-700 shadow-sm">
                      <MessageCircle size={22} />
                    </span>
                    <p className="mt-3 font-semibold text-green-900">Start the conversation</p>
                    <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                      Send a message. This chat and its messages are automatically cleared after
                      10 hours without new activity.
                    </p>
                  </div>
                )}
                {messages.map((message) => {
                  const ownMessage = message.is_mine;
                  return (
                    <div
                      key={message.id}
                      className={`chat-message-enter flex w-full ${ownMessage ? "justify-end" : "justify-start"}`}
                    >
                      <article
                        className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 shadow-sm sm:max-w-[75%] ${
                          ownMessage
                            ? "rounded-br-md bg-green-700 text-white"
                            : "rounded-bl-md border border-cream-200 bg-white text-ink"
                        }`}
                      >
                        {!ownMessage && (
                          <p className="mb-1 text-[10px] font-semibold text-green-700">
                            {message.sender_name}
                            <span className="ml-1 capitalize text-ink-muted">
                              · {message.sender_role}
                            </span>
                          </p>
                        )}
                        {message.audio_url && (
                          audioUrls[message.id] ? (
                            <audio
                              controls
                              preload="none"
                              src={audioUrls[message.id]}
                              aria-label={`Voice message from ${message.sender_name}`}
                              className="my-1 h-10 max-w-full"
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() => void loadAudioMessage(message)}
                              disabled={loadingAudioIds[message.id]}
                              className="my-1 inline-flex min-h-10 items-center gap-2 rounded-full bg-green-600/15 px-3 text-sm font-semibold text-current transition hover:bg-green-600/25 disabled:opacity-60"
                            >
                              {loadingAudioIds[message.id] ? (
                                <LoaderCircle size={16} className="animate-spin" />
                              ) : (
                                <Play size={16} fill="currentColor" />
                              )}
                              {loadingAudioIds[message.id] ? "Loading audio…" : "Load voice message"}
                            </button>
                          )
                        )}
                        {message.content !== "Voice message" && (
                          <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                            {message.content}
                          </p>
                        )}
                        <time
                          dateTime={message.created_at}
                          className={`mt-1 block text-right text-[10px] ${
                            ownMessage ? "text-cream-200" : "text-ink-muted"
                          }`}
                        >
                          {displayTime(message.created_at)}
                        </time>
                      </article>
                    </div>
                  );
                })}
                <div ref={messageEndRef} />
              </div>

              <form
                onSubmit={sendMessage}
                className="border-t border-cream-200 bg-white p-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] sm:px-5"
              >
                {error && (
                  <p role="alert" className="mb-2 text-xs text-danger">
                    {error}
                  </p>
                )}
                {recording ? (
                  <div className="flex justify-center">
                    <div className="flex min-h-[4.5rem] w-full max-w-md items-center gap-4 rounded-full border border-sky-200 bg-gradient-to-r from-sky-200 via-cyan-300 to-sky-200 px-3 py-2 shadow-inner shadow-sky-400/20 sm:px-5">
                      <button
                        type="button"
                        onClick={() => finishRecording(false)}
                        aria-label="Cancel voice recording"
                        className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-black text-white shadow-sm transition hover:bg-slate-800"
                      >
                        <X size={25} strokeWidth={2.5} />
                      </button>
                      <div
                        className="flex min-w-0 flex-1 items-center justify-center gap-1"
                        role="img"
                        aria-label="Recording voice message"
                      >
                        {[10, 16, 23, 13, 30, 38, 24, 16, 26, 12, 20, 9, 15].map(
                          (height, index) => (
                            <span
                              key={index}
                              className="w-1 shrink-0 animate-pulse rounded-full bg-slate-900 sm:w-1.5"
                              style={{
                                height: `${height}px`,
                                animationDelay: `${index * 65}ms`,
                                animationDuration: "700ms",
                              }}
                            />
                          ),
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => finishRecording(true)}
                        aria-label="Send voice recording"
                        className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-white/70 text-slate-900 shadow-sm transition hover:bg-white"
                      >
                        <ArrowUp size={25} strokeWidth={2.5} />
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-end gap-2">
                      <textarea
                        value={messageText}
                        onChange={(event) => setMessageText(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" && !event.shiftKey) {
                            event.preventDefault();
                            event.currentTarget.form?.requestSubmit();
                          }
                        }}
                        rows={1}
                        maxLength={4000}
                        placeholder="Write a message…"
                        aria-label="Message"
                        className="max-h-32 min-h-11 min-w-0 flex-1 resize-y rounded-xl border border-cream-300 bg-cream-50 px-3.5 py-3 text-sm text-ink"
                      />
                      <button
                        type="button"
                        onClick={() => void toggleRecording()}
                        disabled={sending || uploadingAudio}
                        aria-label="Record voice message"
                        title="Record voice message"
                        className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-cream-300 bg-white text-green-800 transition hover:bg-cream-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {uploadingAudio ? (
                          <LoaderCircle size={17} className="animate-spin" />
                        ) : (
                          <Mic size={17} />
                        )}
                      </button>
                      <button
                        type="submit"
                        disabled={sending || !messageText.trim()}
                        aria-label="Send message"
                        className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-bordo-700 text-white transition hover:bg-bordo-500 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Send size={17} />
                      </button>
                    </div>
                    <p className="mt-1.5 flex items-center justify-between gap-2 text-[10px] text-ink-muted">
                      <span>
                        {uploadingAudio
                          ? "Sending voice message…"
                          : "Enter to send · Shift+Enter for a new line · Mic to record"}
                      </span>
                      <span>{messageText.length}/4000</span>
                    </p>
                  </>
                )}
              </form>
            </>
          ) : (
            <div className="m-auto hidden max-w-sm px-6 text-center lg:block">
              <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-green-50 text-green-700">
                <MessagesSquare size={26} />
              </span>
              <h2 className="mt-4 font-heading text-lg font-bold text-green-900">
                Your university conversations
              </h2>
              <p className="mt-1 text-sm leading-relaxed text-ink-muted">
                Select a conversation or start a new chat from the list.
              </p>
            </div>
          )}
        </div>
      </div>
      {error && !selectedConversation && (
        <p role="alert" className="border-t border-danger/20 bg-danger-bg px-4 py-2 text-xs text-danger">
          {error}
        </p>
      )}
    </section>
  );
}
