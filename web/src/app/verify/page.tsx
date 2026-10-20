"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { GraduationCap, ShieldCheck, Search, ArrowLeft, Award, IdCard, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function VerifyIndexPage() {
  const [code, setCode] = useState("");
  const router = useRouter();

  const handleVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.trim()) {
      router.push(`/verify/${encodeURIComponent(code.trim())}`);
    }
  };

  return (
    <div className="min-h-screen bg-cream-50">
      <header className="border-b border-cream-300 bg-white px-4 py-4 sm:px-8">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-green-700 text-cream-200">
              <GraduationCap size={20} />
            </span>
            <span className="font-heading text-lg font-bold text-green-700">SiliconBrains University</span>
          </Link>
          <Button href="/" variant="secondary" size="sm" className="max-w-full">
            <ArrowLeft size={14} /> Back to University
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-3 py-10 sm:px-6 sm:py-16">
        <div className="text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700 mb-3">
            <ShieldCheck size={14} /> Official Credential Registry
          </span>
          <h1 className="font-heading text-2xl font-bold text-green-900 sm:text-4xl">
            Verify a Certificate or Student ID
          </h1>
          <p className="mt-2 text-sm text-ink-muted">
            Enter the verification code printed on a SiliconBrains University credential or scanned from its QR code.
          </p>
        </div>

        <Card className="mt-6 p-4 shadow-xl sm:mt-8 sm:p-8">
          <form onSubmit={handleVerify} className="space-y-4">
            <div>
              <label htmlFor="verify-code" className="block text-xs font-semibold uppercase tracking-wider text-green-900 mb-2">
                Credential Verification Code
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-ink-placeholder">
                  <Search size={18} />
                </span>
                <input
                  id="verify-code"
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="e.g. SBU-CERT-2026-PY01 or SBU-2026-0001"
                  className="h-12 w-full rounded-xl border border-cream-300 bg-white pl-11 pr-4 text-base font-mono text-ink placeholder:text-ink-placeholder focus:border-green-700 focus:outline-none"
                />
              </div>
            </div>

            <Button type="submit" variant="primary" size="lg" className="w-full">
              Verify Credential Authenticity
            </Button>
          </form>

          {/* Quick Sample Links */}
          <div className="mt-6 border-t border-cream-200 pt-5">
            <p className="text-xs text-ink-muted font-medium mb-3">Try checking sample credentials:</p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setCode("SBU-CERT-2026-PY01")}
                className="inline-flex min-h-11 max-w-full items-center gap-1.5 rounded-lg border border-cream-300 bg-cream-50 px-3 py-1.5 text-left text-xs font-mono font-medium text-green-900 hover:bg-cream-100"
              >
                <Award size={13} className="text-green-700" />
                SBU-CERT-2026-PY01
              </button>
              <button
                onClick={() => setCode("SBU-2026-0001")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-cream-300 bg-cream-50 px-3 py-1.5 text-xs font-mono font-medium text-green-900 hover:bg-cream-100"
              >
                <IdCard size={13} className="text-green-700" />
                SBU-2026-0001
              </button>
            </div>
          </div>
        </Card>
      </main>
    </div>
  );
}
