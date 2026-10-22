import Link from "next/link";
import type { Metadata } from "next";
import {
  Award,
  BarChart3,
  CheckCircle2,
  FileCheck2,
  GraduationCap,
  IdCard,
  ShieldCheck,
  Sparkles,
  Trophy,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CredentialVerifyForm } from "@/components/features/CredentialVerifyForm";

export const metadata: Metadata = {
  title: "Online Learning, Exams & Academic Credentials",
  description: "SiliconBrains University brings online courses, secure exams, assignments, student progress, live rankings and verifiable academic credentials together in one learning platform.",
  alternates: { canonical: "/" },
};

const features = [
  {
    icon: FileCheck2,
    title: "Timed Exams You Can Trust",
    text: "Server-authoritative timers and autosave keep every attempt tamper-proof and resilient, even on intermittent connectivity.",
  },
  {
    icon: Trophy,
    title: "Automated Live Ranking",
    text: "Earn Task Points by passing exams and completing approved assignments, then follow the live Top-4 ranking.",
  },
  {
    icon: Award,
    title: "Cryptographically Verified Certificates",
    text: "Course credentials include a unique code that can be checked through the public verification service.",
  },
  {
    icon: IdCard,
    title: "Official Virtual Student ID",
    text: "Every learner receives a digital student credential complete with verified student code, department, and scan-ready QR code.",
  },
  {
    icon: Sparkles,
    title: "Aarsh Intelligence AI Tutor",
    text: "An AI study assistant powered by Gemini that can help learners review topics and clarify concepts.",
  },
  {
    icon: BarChart3,
    title: "Actionable Faculty & Admin Analytics",
    text: "Monitor student progress, exam results, submission queues, and course completion across your institution.",
  },
];

const steps = [
  {
    step: "01",
    title: "Enroll & Sign In",
    desc: "Access your personalized portal with single sign-on via Clerk and obtain your official Virtual ID.",
  },
  {
    step: "02",
    title: "Master Course Exams & Tasks",
    desc: "Complete coursework, participate in timed MCQ assessments, and submit practical assignments for faculty review.",
  },
  {
    step: "03",
    title: "Climb Rankings & Earn Credentials",
    desc: "Accumulate Task Points, ascend the Live Top-4 podium, and automatically receive verified course completion certificates.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-cream-50 text-ink">
      {/* Top Header */}
      <header className="sticky top-0 z-30 border-b border-cream-300 bg-cream-50/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-2 px-3 sm:gap-4 sm:px-6">
          <Link href="/" className="flex min-w-0 items-center gap-2 font-heading text-sm font-bold text-green-700 sm:gap-2.5 sm:text-lg">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-green-700 text-cream-200 shadow-sm">
              <GraduationCap size={20} aria-hidden />
            </span>
            <span>SiliconBrains University</span>
          </Link>

          <div className="flex shrink-0 items-center gap-1 sm:gap-2.5">
            <Link
              href="/verify"
              className="hidden text-xs font-semibold text-green-700 hover:text-green-900 sm:inline-flex items-center gap-1"
            >
              <ShieldCheck size={14} /> Verify Credential
            </Link>
            <Button href="/sign-in" variant="secondary" size="sm" className="px-2 text-xs sm:px-3 sm:text-sm">
              <span className="sm:hidden">Sign in</span>
              <span className="hidden sm:inline">Sign In</span>
            </Button>
            <Button href="/sign-up" variant="primary" size="sm" className="px-2 text-xs sm:px-3 sm:text-sm">
              <span className="sm:hidden">Sign up</span>
              <span className="hidden sm:inline">Sign Up</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="page-enter">
        {/* Hero Section */}
        <section className="relative overflow-hidden bg-gradient-to-b from-cream-100 to-cream-50 pb-12 pt-10 sm:pb-16 sm:pt-12 lg:pt-20 lg:pb-24">
          <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-12">
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border border-cream-300 bg-white px-3.5 py-1 text-xs font-semibold text-green-900 shadow-sm">
                <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
                <span>Next-Generation Academic Platform · v2026</span>
              </div>

              <h1 className="font-heading text-3xl font-bold leading-tight text-green-900 min-[400px]:text-4xl sm:text-5xl lg:text-5xl">
                Online learning and exams for students and teachers.
              </h1>

              <p className="max-w-xl text-base leading-relaxed text-ink-muted sm:text-lg">
                SiliconBrains University is an academic learning platform for course management, online examinations, assignments, student progress and academic credentials. Students, teachers and administrators can use role-based tools in one portal.
              </p>

              <div className="flex flex-col items-stretch gap-2.5 pt-2 min-[400px]:flex-row min-[400px]:flex-wrap min-[400px]:items-center sm:gap-3.5">
                <Button href="/sign-up" variant="primary" size="lg" className="w-full min-[400px]:w-auto">
                  Create Account (Sign Up)
                </Button>
                <Button href="/sign-in" variant="secondary" size="lg" className="w-full min-[400px]:w-auto">
                  Portal Sign In
                </Button>
                <Button href="#verify-section" variant="ghost" size="lg" className="w-full min-[400px]:w-auto">
                  Verify a Certificate
                </Button>
              </div>

            </div>

            {/* Academic platform overview */}
            <div className="lg:col-span-5">
              <div className="relative rounded-2xl border border-cream-300 bg-white p-6 shadow-xl">
                <div className="mb-4 flex items-center justify-between border-b border-cream-200 pb-3">
                  <div className="flex items-center gap-2">
                    <GraduationCap size={18} className="text-green-700" />
                    <h2 className="font-heading text-base font-bold text-green-900">
                      Your academic portal
                    </h2>
                  </div>
                </div>

                <div className="space-y-3">
                  {[
                    { icon: FileCheck2, title: "Course examinations", detail: "Take scheduled, timed assessments." },
                    { icon: CheckCircle2, title: "Tasks and progress", detail: "Keep course work and achievements together." },
                    { icon: Award, title: "Academic credentials", detail: "Access course records and credential tools." },
                  ].map(({ icon: Icon, title, detail }) => (
                    <div
                      key={title}
                      className="flex items-center gap-3.5 rounded-xl border border-cream-200 bg-cream-50/60 p-3"
                    >
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-green-100 text-green-700">
                        <Icon size={18} aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-sm text-green-900">{title}</p>
                        <p className="text-[11px] text-ink-muted">{detail}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 rounded-xl bg-green-50 p-3 text-center text-xs text-green-900">
                  <span>Students, teachers and administrators each have role-based portal tools.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Public Credential Verification Section (PRD §7.2 requirement) */}
        <section id="verify-section" className="border-y border-cream-300 bg-cream-200 py-12 sm:py-16">
          <div className="mx-auto max-w-4xl px-4 text-center sm:px-6">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-semibold text-green-900 shadow-sm mb-3">
              <ShieldCheck size={14} className="text-green-700" /> Tamper-Evident Verification
            </span>
            <h2 className="font-heading text-2xl font-bold text-green-900 sm:text-3xl">
              Verify Any University Credential
            </h2>
            <p className="mx-auto mt-2 max-w-xl text-sm text-ink-muted">
              Check a SiliconBrains University credential using its verification code.
            </p>

            <CredentialVerifyForm />
          </div>
        </section>

        {/* Features Grid */}
        <section className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-20">
          <div className="text-center">
            <h2 className="font-heading text-3xl font-bold text-green-900 sm:text-4xl">
              Engineered for Modern Academic Excellence
            </h2>
            <p className="mx-auto mt-2 max-w-2xl text-ink-muted text-sm sm:text-base">
              A single platform eliminating manual exam paper grading, forged certificates, and disconnected tools.
            </p>
          </div>

          <div className="mt-8 grid gap-4 sm:mt-12 sm:grid-cols-2 sm:gap-6 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, text }) => (
              <Card key={title} className="flex flex-col p-6 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5">
                <span className="grid h-12 w-12 place-items-center rounded-xl bg-green-50 text-green-700 shadow-sm">
                  <Icon size={24} aria-hidden />
                </span>
                <h3 className="mt-4 font-heading text-lg font-bold text-green-900">{title}</h3>
                <p className="mt-2 text-sm text-ink-muted leading-relaxed">{text}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* How It Works Section */}
        <section id="how" className="bg-green-700 py-12 text-cream-50 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="text-center">
              <span className="text-xs uppercase font-bold tracking-widest text-cream-300">
                Seamless Learner Journey
              </span>
              <h2 className="mt-1 font-heading text-3xl font-bold !text-cream-50 sm:text-4xl">
                How SiliconBrains University Works
              </h2>
            </div>

            <div className="mt-8 grid gap-4 md:mt-12 md:grid-cols-3 md:gap-6">
              {steps.map((s) => (
                <div key={s.step} className="rounded-2xl bg-green-600/90 p-6 border border-green-500/40 shadow-lg">
                  <span className="font-heading text-3xl font-bold text-cream-200">{s.step}</span>
                  <h3 className="mt-3 font-heading text-lg font-bold !text-cream-50">{s.title}</h3>
                  <p className="mt-2 text-sm text-cream-100/90 leading-relaxed">{s.desc}</p>
                </div>
              ))}
            </div>

            <div className="mt-12 flex flex-wrap justify-center gap-3.5">
              <Button
                href="/sign-up"
                className="border-cream-200 bg-cream-200 text-green-900 hover:bg-cream-100 font-bold"
                size="lg"
              >
                Create Student Account (Sign Up)
              </Button>
              <Button
                href="/sign-in"
                className="border border-cream-200 bg-transparent text-cream-50 hover:bg-green-600 font-bold"
                size="lg"
              >
                Portal Sign In
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-cream-300 bg-white py-10 text-xs text-ink-muted">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
          <div className="flex flex-wrap items-center justify-center gap-2 text-center sm:justify-start">
            <span className="grid h-6 w-6 place-items-center rounded bg-green-700 text-cream-200 text-xs font-bold">
              SBU
            </span>
            <span className="font-semibold text-green-900">SiliconBrains University Academic Platform</span>
          </div>
          <div className="flex flex-wrap justify-center gap-x-5 gap-y-3 sm:justify-end">
            <Link href="/verify" className="hover:underline">Verify Credential</Link>
            <Link href="/about" className="hover:underline">About & Policies</Link>
            <Link href="/ranking" className="hover:underline">Live Leaderboard</Link>
            <Link href="/notices" className="hover:underline">University Notices</Link>
            <Link href="/sign-in" className="hover:underline">Sign In</Link>
            <Link href="/sign-up" className="font-semibold text-green-900 hover:underline">Sign Up</Link>
          </div>
          <p>© 2026 SiliconBrains University.</p>
        </div>
      </footer>
    </div>
  );
}
