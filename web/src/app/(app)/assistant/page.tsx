"use client";
import React, { useState, useRef, useEffect } from "react";
import Image from "next/image";
import { Send, Sparkles, ShieldAlert, BookOpen, Trophy, Award, RefreshCw } from "lucide-react";
import { PageHeader, Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: string;
}

const STARTER_TOPICS = [
  {
    icon: BookOpen,
    title: "Exam Preparation",
    prompt: "Give me key study points for Binary Search Trees and Algorithm Complexity.",
  },
  {
    icon: Trophy,
    title: "Task Points Strategy",
    prompt: "How can I maximize my Task Points to reach the Top 4 on the Live Ranking?",
  },
  {
    icon: Award,
    title: "Certificate Verification",
    prompt: "How do employers or academic bodies verify SiliconBrains University certificates?",
  },
  {
    icon: Sparkles,
    title: "Notice Summary",
    prompt: "Summarize all active and urgent university announcements for this week.",
  },
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      sender: "assistant",
      text: "Greetings! I am **Aarsh Intelligence**, your AI academic mentor powered by Google Gemini.\n\nI can explain difficult course concepts, guide you through your exam preparation, help you navigate your Task Points, and answer questions about your enrolled courses.\n\n*Note: In accordance with academic integrity guidelines, I will never reveal answers during an active exam attempt.*",
      timestamp: "Today",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = (text?: string) => {
    const q = (text ?? input).trim();
    if (!q) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!text) setInput("");
    setIsTyping(true);

    setTimeout(() => {
      let reply = "";
      const lower = q.toLowerCase();
      if (lower.includes("binary search") || lower.includes("tree") || lower.includes("algorithm")) {
        reply = "### Key Study Points: Binary Search Trees (BST)\n\n1. **BST Invariant**: For every node $X$, all keys in its left subtree are $< X$, and all keys in its right subtree are $> X$.\n2. **Time Complexity**:\n   - **Average case**: $O(\\log n)$ for search, insertion, and deletion.\n   - **Worst case**: $O(n)$ if the tree degenerates into a linked list (unbalanced).\n3. **In-order Traversal**: Yields all elements in strictly ascending sorted order.\n\n💡 *Tip for Midterm*: Make sure you can trace AVL rotations (single LL/RR, double LR/RL) to maintain $O(\\log n)$ balance!";
      } else if (lower.includes("point") || lower.includes("rank") || lower.includes("leaderboard")) {
        reply = "### Live Ranking Strategy\n\n- **1. Prioritize High-Yield Tasks**: Check **My Tasks** for assignments worth 50+ Task Points.\n- **2. Pass Every Course Exam**: When teachers publish exams with linked Task Points, passing the exam awards points immediately upon submission.\n- **3. Submit Early for Review**: For assignment tasks, submit clean code or repository URLs so teachers can approve them promptly in the queue.\n- **4. Tie-Breaker**: Remember, students who reach a points threshold earlier rank higher on the Top-4 leaderboard!";
      } else if (lower.includes("certif")) {
        reply = "### Certificate Verification\n\nSiliconBrains University certificates include a unique credential code and can be checked on the public verification page.\n\nEnter the code printed on the credential at `/verify` to look up its current status.";
      } else if (lower.includes("notice")) {
        reply = "### Active University Notices Summary\n\n1. **Midterm Schedule Published**: Data Structures midterm opens inside its scheduled window. Single 45-minute timed attempt.\n2. **Scheduled Maintenance**: Portal services will undergo brief routine updates tonight from 1 AM to 2 AM.\n3. **Library Hours**: Central library adjusted schedule on Friday at 4 PM.";
      } else {
        reply = `Thank you for asking about **${q}**!\n\nAs your academic guide, I encourage you to check your course modules in the Dashboard. For assignments, be sure to include clear reasoning and documentation. If you need step-by-step problem walkthroughs, feel free to ask!`;
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
    }, 600);
  };

  const clearChat = () => {
    setMessages([
      {
        id: "fresh",
        sender: "assistant",
        text: "Chat history cleared. How can I assist you with your courses today?",
        timestamp: "Just now",
      },
    ]);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Aarsh Intelligence"
        subtitle="Your personalized AI study companion powered by Google Gemini."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="info">
              <ShieldAlert size={12} className="mr-1" /> Anti-Cheat Guarded
            </Badge>
            <button
              onClick={clearChat}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-cream-300 bg-white px-3 py-1.5 text-xs font-semibold text-green-700 hover:bg-cream-100"
            >
              <RefreshCw size={13} /> Clear chat
            </button>
          </div>
        }
      />

      {/* Suggested Topic Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STARTER_TOPICS.map((st) => {
          const Icon = st.icon;
          return (
            <button
              key={st.title}
              onClick={() => handleSend(st.prompt)}
              className="flex min-h-11 flex-col items-start rounded-xl border border-cream-300 bg-white p-4 text-left transition-all hover:border-green-700 hover:shadow-md"
            >
              <div className="mb-2 grid h-8 w-8 place-items-center rounded-lg bg-green-50 text-green-700">
                <Icon size={16} />
              </div>
              <p className="font-heading text-sm font-semibold text-green-900">{st.title}</p>
              <p className="mt-1 line-clamp-2 text-xs text-ink-muted">{st.prompt}</p>
            </button>
          );
        })}
      </div>

      {/* Main Chat Workspace */}
      <Card className="flex h-[min(620px,calc(100dvh-13rem))] min-h-[420px] flex-col overflow-hidden p-0">
        {/* Chat Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cream-300 bg-green-700 px-4 py-3 text-cream-50 sm:px-6 sm:py-4">
          <div className="flex min-w-0 items-center gap-3">
            <Image
              src="/aarsh-ai-orb.gif"
              alt=""
              aria-hidden="true"
              width={48}
              height={48}
              unoptimized
              className="h-12 w-12 shrink-0 rounded-full object-contain mix-blend-screen"
            />
            <div className="min-w-0">
              <h2 className="break-words font-heading text-sm font-bold !text-cream-50 sm:text-base">Aarsh Intelligence Workspace</h2>
              <p className="text-xs text-cream-200">Interactive Academic Assistant</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-green-800 px-3 py-1 text-xs text-cream-200">
            <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
            Online
          </span>
        </div>

        {/* Messages Stream */}
        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-cream-50/50 p-3 sm:p-6">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex flex-col ${m.sender === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[90%] break-words rounded-2xl px-3 py-3 shadow-sm leading-relaxed sm:max-w-[85%] sm:px-5 sm:py-3.5 ${
                  m.sender === "user"
                    ? "bg-green-700 text-cream-50 rounded-br-none"
                    : "bg-white text-ink border border-cream-300 rounded-bl-none"
                }`}
              >
                <div className="whitespace-pre-line text-sm">{m.text}</div>
              </div>
              <span className="mt-1 px-1 text-[11px] text-ink-muted">{m.timestamp}</span>
            </div>
          ))}

          {isTyping && (
            <div className="flex items-center gap-2 rounded-2xl border border-cream-300 bg-white px-4 py-3 text-xs text-ink-muted">
              <Image
                src="/aarsh-ai-orb.gif"
                alt=""
                aria-hidden="true"
                width={32}
                height={32}
                unoptimized
                className="h-8 w-8 shrink-0 rounded-full object-contain mix-blend-screen"
              />
              <span>Aarsh Intelligence is synthesizing guidance...</span>
            </div>
          )}
          <div ref={scrollRef} />
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2 border-t border-cream-300 bg-white p-3 sm:gap-3 sm:p-4"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your question for Aarsh (e.g. explain dynamic programming or how certificates work)..."
            className="h-11 min-w-0 flex-1 rounded-xl border border-cream-300 bg-cream-50/40 px-3 text-sm text-ink placeholder:text-ink-placeholder focus:border-green-700 focus:outline-none sm:h-12 sm:px-4"
          />
          <button
            type="submit"
            disabled={!input.trim()}
            className="inline-flex h-11 shrink-0 items-center gap-2 rounded-xl bg-bordo-700 px-4 font-heading text-sm font-semibold text-cream-50 transition-colors hover:bg-bordo-500 disabled:opacity-40 sm:h-12 sm:px-6"
          >
            <span>Ask</span>
            <Send size={16} />
          </button>
        </form>
      </Card>
    </div>
  );
}
