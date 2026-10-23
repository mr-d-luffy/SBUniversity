"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Award,
  BarChart3,
  BookOpenCheck,
  CheckCircle2,
  FileCheck2,
  GraduationCap,
  UsersRound,
} from "lucide-react";

const roleViews = {
  Student: {
    description: "A clear view of your learning and progress.",
    items: [
      { icon: BookOpenCheck, title: "Course tasks", detail: "See what to learn and submit next." },
      { icon: FileCheck2, title: "Exams", detail: "Prepare for scheduled assessments." },
      { icon: Award, title: "Progress & credentials", detail: "Track achievements as you learn." },
    ],
    href: "/sign-up",
    action: "Explore student access",
  },
  Teacher: {
    description: "Course tools that keep teaching work together.",
    items: [
      { icon: BookOpenCheck, title: "Course tasks", detail: "Create and update learning activities." },
      { icon: CheckCircle2, title: "Student approvals", detail: "Review submitted assignment work." },
      { icon: FileCheck2, title: "Assessments", detail: "Manage exams and student progress." },
    ],
    href: "/sign-in",
    action: "Open faculty sign in",
  },
  Admin: {
    description: "Tools for managing the academic platform.",
    items: [
      { icon: UsersRound, title: "People & courses", detail: "Manage university accounts and classes." },
      { icon: BarChart3, title: "Academic analytics", detail: "Review activity and course outcomes." },
      { icon: Award, title: "Credentials", detail: "Support trusted academic records." },
    ],
    href: "/sign-in",
    action: "Open administrator sign in",
  },
} as const;

type PortalRole = keyof typeof roleViews;

export function LandingPortalPreview() {
  const [role, setRole] = useState<PortalRole>("Student");
  const view = roleViews[role];

  return (
    <div className="landing-preview relative">
      <div aria-hidden="true" className="landing-orbit landing-orbit-one" />
      <div aria-hidden="true" className="landing-orbit landing-orbit-two" />
      <div className="relative rounded-2xl border border-cream-300 bg-white/95 p-5 shadow-xl backdrop-blur sm:p-6">
        <div className="mb-4 flex items-center justify-between gap-3 border-b border-cream-200 pb-3">
          <div className="flex items-center gap-2">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-green-700 text-cream-100 shadow-sm">
              <GraduationCap size={19} aria-hidden />
            </span>
            <div>
              <h2 className="font-heading text-sm font-bold text-green-900">Your academic portal</h2>
              <p className="text-[11px] text-ink-muted">One university, connected tools</p>
            </div>
          </div>
          <span className="flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-1 text-[10px] font-semibold text-green-800">
            <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" /> Ready to learn
          </span>
        </div>

        <div className="mb-4 grid grid-cols-3 gap-1 rounded-xl bg-cream-100 p-1" role="group" aria-label="Choose a portal role">
          {(Object.keys(roleViews) as PortalRole[]).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={role === option}
              className={`min-h-10 rounded-lg px-2 text-xs font-semibold transition-colors ${role === option ? "bg-white text-green-900 shadow-sm" : "text-ink-muted hover:text-green-900"}`}
              onClick={() => setRole(option)}
            >
              {option}
            </button>
          ))}
        </div>

        <div key={role} className="landing-role-content" aria-live="polite" aria-label={`${role} portal preview`}>
          <p className="mb-3 text-xs text-ink-muted">{view.description}</p>
          <div className="space-y-2">
            {view.items.map(({ icon: Icon, title, detail }, index) => (
              <div key={title} className="landing-preview-row flex items-center gap-3 rounded-xl border border-cream-200 bg-cream-50/60 p-3" style={{ animationDelay: `${index * 70}ms` }}>
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-green-100 text-green-700">
                  <Icon size={17} aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-green-900">{title}</p>
                  <p className="text-[11px] text-ink-muted">{detail}</p>
                </div>
                <CheckCircle2 size={15} className="shrink-0 text-green-600" aria-hidden />
              </div>
            ))}
          </div>
          <Link href={view.href} className="mt-4 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-xl bg-green-700 px-4 text-xs font-semibold text-white transition-colors hover:bg-green-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-700 focus-visible:ring-offset-2">
            {view.action}
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
