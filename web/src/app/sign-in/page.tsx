"use client";
import React, { useState } from "react";
import { SignIn } from "@clerk/nextjs";
import { GraduationCap, Sparkles, Shield } from "lucide-react";
import Link from "next/link";
import { DemoLogin } from "@/components/features/DemoLogin";

export default function SignInPage() {
  const [useDemoMode, setUseDemoMode] = useState(false);

  return (
    <div className="page-enter grid min-h-dvh lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-green-700 p-12 text-cream-100 lg:flex">
        <Link href="/" className="flex items-center gap-2 font-heading text-lg font-bold text-cream-50">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-cream-200 text-green-900">
            <GraduationCap size={20} aria-hidden />
          </span>
          SiliconBrains University
        </Link>
        <div>
          <h2 className="max-w-md font-heading text-3xl font-bold leading-snug !text-cream-50">
            Your courses, exams and certificates are waiting.
          </h2>
          <p className="mt-3 max-w-md text-cream-200">
            Sign in to see your tasks, your points and where you stand on the live ranking.
          </p>
        </div>
        <p className="text-sm text-cream-200">© 2026 SiliconBrains University</p>
      </aside>

      <main className="flex min-w-0 items-center justify-center px-4 py-8 sm:py-12">
        <div className="w-full max-w-md space-y-4">
          <Link href="/" className="inline-flex items-center gap-2 font-heading text-base font-bold text-green-700 lg:hidden">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-green-700 text-cream-200">
              <GraduationCap size={19} aria-hidden />
            </span>
            SiliconBrains University
          </Link>
          <div className="flex flex-col items-stretch gap-3 border-b border-cream-200 pb-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <h1 className="text-2xl font-bold text-green-900">Welcome back</h1>
              <p className="text-xs text-ink-muted">Sign in to continue to your academic portal.</p>
            </div>

            {/* Quick Mode Toggle for Local Testing */}
            <button
              type="button"
              onClick={() => setUseDemoMode(!useDemoMode)}
              className="min-h-11 w-full rounded-lg border border-cream-300 bg-cream-100 px-3 py-2 text-xs font-semibold text-green-900 transition-colors hover:bg-cream-200 sm:w-auto"
            >
              {useDemoMode ? "Use Clerk OAuth" : "1-Click Demo Accounts"}
            </button>
          </div>

          {useDemoMode ? (
            <div className="space-y-3 rounded-xl border border-cream-300 bg-white p-4 shadow-sm sm:p-5">
              <div className="flex items-center gap-2 text-xs font-semibold text-green-700 bg-green-50 p-2 rounded-lg">
                <Sparkles size={14} className="text-bordo-700" />
                <span>One-Click Development Accounts (No Google OAuth required)</span>
              </div>
              <DemoLogin error={false} />
            </div>
          ) : (
            <div className="space-y-4">
              <SignIn
                routing="hash"
                signUpUrl="/sign-up"
                fallbackRedirectUrl="/portal"
                appearance={{
                  variables: {
                    colorPrimary: "#6C151E",
                  },
                }}
              />

              {/* Helpful hint for Clerk External Account error */}
              <div className="rounded-xl border border-cream-300 bg-cream-100/60 p-3.5 text-xs leading-relaxed text-ink-muted">
                <p className="font-semibold text-green-900 mb-1 flex items-center gap-1.5">
                  <Shield size={13} className="text-green-700" />
                  First time signing in with Google?
                </p>
                <p>
                  If you haven&apos;t registered this Google account yet in your Clerk project, visit{" "}
                  <Link href="/sign-up" className="font-bold text-green-700 underline">
                    Sign Up
                  </Link>{" "}
                  first or switch to <b>1-Click Demo Accounts</b> above.
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
