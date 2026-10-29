"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen, Compass, GraduationCap, Sparkles, Trophy } from "lucide-react";

const clues = [
  "Aha! You found a bookmark. The right page is still out there.",
  "Nice exploring! This trail leads back to the learning hub.",
  "Bonus clue unlocked: every great learner knows when to ask for directions.",
];

export default function NotFound() {
  const [score, setScore] = useState(0);
  const [clue, setClue] = useState("");

  function findClue() {
    setScore((current) => current + 10);
    setClue(clues[Math.floor(Math.random() * clues.length)]);
  }

  return (
    <main className="relative grid min-h-dvh place-items-center overflow-hidden bg-cream-50 px-4 py-10 text-center">
      <div aria-hidden className="pointer-events-none absolute -left-24 top-12 h-64 w-64 rounded-full bg-green-100/70 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -right-24 bottom-4 h-72 w-72 rounded-full bg-cream-200/80 blur-3xl" />

      <section className="page-enter relative w-full max-w-xl">
        <Link href="/" aria-label="SiliconBrains University home" className="mx-auto mb-8 inline-flex items-center gap-2 font-heading text-sm font-bold text-green-700">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-green-700 text-cream-100"><GraduationCap size={20} aria-hidden /></span>
          SiliconBrains University
        </Link>

        <div className="rounded-3xl border border-cream-300 bg-white/90 p-6 shadow-xl sm:p-10">
          <div className="mx-auto mb-5 grid h-20 w-20 place-items-center rounded-2xl bg-green-50 text-green-700 ring-1 ring-green-100">
            <Compass size={38} strokeWidth={1.7} aria-hidden />
          </div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.25em] text-green-600">Campus quest · Level 404</p>
          <h1 className="mt-3 font-heading text-6xl font-bold tracking-tight text-green-900 sm:text-7xl">404</h1>
          <h2 className="mt-2 text-xl font-bold text-green-700 sm:text-2xl">You’ve wandered off the syllabus.</h2>
          <p className="mx-auto mt-3 max-w-md leading-relaxed text-ink-muted">
            This page isn’t in today’s reading list. Explore for a clue, or head back to campus.
          </p>

          <div className="mx-auto mt-7 flex w-fit items-center gap-3 rounded-2xl border border-cream-300 bg-cream-50 px-4 py-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-cream-200 text-rank-gold"><Trophy size={21} aria-hidden /></span>
            <span className="text-left"><span className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">Quest points</span><span aria-live="polite" className="font-heading text-lg font-bold text-green-900">{score} XP</span></span>
          </div>

          {clue && <p aria-live="polite" className="mx-auto mt-4 max-w-sm rounded-xl bg-green-50 px-4 py-3 text-sm font-medium text-green-900">{clue}</p>}

          <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
            <button type="button" onClick={findClue} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-cream-300 bg-white px-5 py-2.5 text-sm font-semibold text-green-700 shadow-sm hover:bg-cream-50">
              {score === 0 ? <><BookOpen size={17} aria-hidden /> Search for a clue</> : <><Sparkles size={17} aria-hidden /> Search again (+10 XP)</>}
            </button>
            <Link href="/" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-green-700 px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-green-900">
              <ArrowLeft size={17} aria-hidden /> Back to campus
            </Link>
          </div>
          <p className="mt-5 text-xs text-ink-muted">Need your portal? <Link href="/sign-in" className="font-semibold text-green-700 underline decoration-green-300 underline-offset-4 hover:text-green-900">Sign in</Link></p>
        </div>
        <p className="mt-5 text-xs text-ink-muted">Keep exploring. Every detour earns experience.</p>
      </section>
    </main>
  );
}
