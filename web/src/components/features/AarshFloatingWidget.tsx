"use client";
import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import clsx from "clsx";
import { Maximize2, Send, Sparkles, X, ShieldAlert, BookOpen, Trophy, Award } from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
}

const PRESET_PROMPTS = [
  "How do I earn Task Points?",
  "How do I get my course certificate?",
  "What is the passing mark for exams?",
  "Where can I find my Virtual ID Card?",
];

const KNOWLEDGE_RESPONSES: Record<string, string> = {
  "How do I earn Task Points?":
    "You earn **Task Points** automatically in two ways:\n1. **Exams**: When a teacher publishes an exam with Task Points, passing the exam instantly awards the points.\n2. **Assignments**: Submit your project note or link for course tasks. When your teacher approves the submission, points are awarded right away!\n\nAll your Task Points reflect in real-time on the **Live Ranking** board.",
  "How do I get my course certificate?":
    "Certificates are **automatically issued** as soon as you achieve passing marks on all published exams in an enrolled course! Once issued, you can view your certificate and download the official high-resolution PDF from your **Certificates** page.",
  "What is the passing mark for exams?":
    "Each exam specifies its passing marks on the exam details card before you start. Typically, you need 50% or higher to pass. Passing also awards the exam's linked Task Points!",
  "Where can I find my Virtual ID Card?":
    "Your official university **Virtual ID Card** is accessible from the sidebar under **Virtual ID Card** (`/student/profile`). It displays your student code, department, photo, validity, and a secure verification QR code that can be scanned anywhere.",
};

export function AarshFloatingWidget({ userRole, userName }: { userRole: string; userName: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "m0",
      sender: "assistant",
      text: `Hello ${userName.split(" ")[0]}! I'm **Aarsh Intelligence**, your AI academic assistant. Ask me anything about your courses, exam preparation, certificates, or platform rankings.`,
      timestamp: "Just now",
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend ?? input).trim();
    if (!query) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setIsTyping(true);

    // Check knowledge base or simulate response with academic guidance
    setTimeout(() => {
      let reply = KNOWLEDGE_RESPONSES[query];
      if (!reply) {
        if (query.toLowerCase().includes("point") || query.toLowerCase().includes("rank")) {
          reply = "Your ranking is determined purely by your total **Task Points**. Unlike simple exam grades, Task Points reward consistent completion of lab assignments and exams!";
        } else if (query.toLowerCase().includes("certif")) {
          reply = "Your certificates are verified cryptographically and bear a unique tamper-evident verification code and QR. You can download the ReportLab PDF from your Certificates tab.";
        } else if (query.toLowerCase().includes("exam") || query.toLowerCase().includes("test")) {
          reply = "Exams feature server-authoritative timers. Answers autosave per question so you won't lose work even if your network disconnects. Remember: anti-cheat guardrails block live exam question lookups during active attempts!";
        } else {
          reply = `That's a great question regarding ${query}. As Aarsh Intelligence, I'm here to support your studies at SiliconBrains University. You can also view the full AI study workspace on the dedicated **Aarsh AI** page.`;
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          sender: "assistant",
          text: reply,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      setIsTyping(false);
    }, 550);
  };

  return (
    <div className="fixed bottom-3 right-3 z-50 sm:bottom-5 sm:right-5">
      {/* Floating Launcher Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="group flex min-h-14 items-center gap-2.5 rounded-full bg-green-700 px-4 text-cream-50 shadow-xl transition-all duration-200 hover:bg-green-600 hover:scale-105 active:scale-95 sm:px-5"
          aria-label="Open Aarsh Intelligence Assistant"
        >
          <div className="relative h-9 w-9 shrink-0">
            <Image
              src="/aarsh-ai-orb.gif"
              alt=""
              aria-hidden="true"
              width={36}
              height={36}
              unoptimized
              className="h-9 w-9 rounded-full object-contain mix-blend-screen"
            />
            <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-bordo-500 ring-2 ring-green-700" />
          </div>
          <span className="font-heading font-semibold text-sm">Aarsh AI</span>
        </button>
      )}

      {/* Floating Chat Drawer */}
      {isOpen && (
        <div className="flex h-[min(520px,calc(100dvh-1.5rem))] min-h-[min(400px,calc(100dvh-1.5rem))] w-[calc(100vw-1.5rem)] max-w-[410px] flex-col overflow-hidden rounded-2xl border border-cream-300 bg-white shadow-2xl transition-all">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-green-900/20 bg-green-700 px-4 py-3 text-cream-50">
            <div className="flex min-w-0 items-center gap-2.5">
              <Image
                src="/aarsh-ai-orb.gif"
                alt=""
                aria-hidden="true"
                width={40}
                height={40}
                unoptimized
                className="h-10 w-10 shrink-0 rounded-full object-contain mix-blend-screen"
              />
              <div className="min-w-0">
                <p className="font-heading text-sm font-bold leading-tight">Aarsh Intelligence</p>
                <p className="text-[11px] text-cream-200">Gemini Academic Assistant</p>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <Link
                href="/assistant"
                className="grid h-11 w-11 place-items-center rounded-lg text-cream-200 hover:bg-green-600 hover:text-cream-50"
                title="Open full page assistant"
              >
                <Maximize2 size={16} />
              </Link>
              <button
                onClick={() => setIsOpen(false)}
                className="grid h-11 w-11 place-items-center rounded-lg text-cream-200 hover:bg-green-600 hover:text-cream-50"
                aria-label="Close assistant"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Anti-cheat Guardrail Banner */}
          <div className="flex items-center gap-1.5 bg-green-50 px-3 py-2 text-[11px] font-medium text-green-900 border-b border-cream-200">
            <ShieldAlert size={13} className="text-bordo-700 shrink-0" />
            <span>Academic integrity guardrails active</span>
          </div>

          {/* Messages Container */}
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto bg-cream-50/60 p-3 text-xs sm:p-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={clsx(
                  "flex flex-col",
                  m.sender === "user" ? "items-end" : "items-start"
                )}
              >
                <div
                  className={clsx(
                    "max-w-[85%] rounded-xl px-3.5 py-2.5 leading-relaxed shadow-sm",
                    m.sender === "user"
                      ? "bg-green-700 text-cream-50 rounded-br-none"
                      : "bg-white text-ink border border-cream-300 rounded-bl-none"
                  )}
                >
                  <p className="whitespace-pre-line">{m.text}</p>
                </div>
                <span className="mt-1 text-[10px] text-ink-muted px-1">{m.timestamp}</span>
              </div>
            ))}

            {isTyping && (
              <div className="flex items-center gap-1 rounded-xl border border-cream-300 bg-white px-3 py-2 text-ink-muted">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-green-700" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-green-700 [animation-delay:0.2s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-green-700 [animation-delay:0.4s]" />
                <span className="ml-1 text-[11px]">Aarsh is thinking...</span>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Quick Preset Prompts */}
          <div className="border-t border-cream-200 bg-cream-100/50 p-2">
            <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
              {PRESET_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => handleSend(p)}
                  className="shrink-0 rounded-full border border-cream-300 bg-white px-2.5 py-1 text-[11px] font-medium text-green-900 transition-colors hover:bg-cream-200"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2 border-t border-cream-300 bg-white p-3"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask Aarsh about courses, exams, tasks..."
              className="h-10 flex-1 rounded-lg border border-cream-300 bg-cream-50/50 px-3 text-xs text-ink placeholder:text-ink-placeholder focus:border-green-700 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="grid h-10 w-10 place-items-center rounded-lg bg-bordo-700 text-cream-50 transition-colors hover:bg-bordo-500 disabled:opacity-40"
              aria-label="Send message"
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
