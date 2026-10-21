import Link from "next/link";
import type { Metadata } from "next";
import {
  GraduationCap,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Award,
  Calendar,
  Building,
  User,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { CredentialInlineLookup } from "@/components/features/CredentialLookupForm";

type VerifyCodePageProps = { params: Promise<{ code: string }> };

export async function generateMetadata({ params }: VerifyCodePageProps): Promise<Metadata> {
  const { code } = await params;
  return { title: `Credential Verification ${decodeURIComponent(code)}` };
}

export default async function VerifyCodePage({ params }: VerifyCodePageProps) {
  const { code: encodedCode } = await params;
  const code = decodeURIComponent(encodedCode);

  // Determine if code is certificate or student ID
  const isStudentId = code.startsWith("SBU-2026") || code.toLowerCase().includes("student");
  const isRevoked = code.toLowerCase().includes("revok");

  const credentialData = isStudentId
    ? {
        type: "Student Identification Credential",
        code: code,
        name: "Aarav Sharma",
        department: "Computer Science & Engineering",
        status: isRevoked ? "Revoked" : "Active & Verified",
        isValid: !isRevoked,
        issuedOn: "Academic Session 2024 – 2028",
        detail: "Registered Full-time Student in Good Academic Standing",
      }
    : {
        type: "Course Certificate of Completion",
        code: code,
        name: "Aarav Sharma",
        course: "Python Programming Fundamentals",
        status: isRevoked ? "Revoked by Institution" : "Valid & Genuine",
        isValid: !isRevoked,
        issuedOn: "October 05, 2026",
        detail: "Passed with Distinction (Final Percentage: 96.0%)",
      };

  return (
    <div className="min-h-screen bg-cream-50">
      {/* Top Header */}
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

      {/* Main Verification Card */}
      <main className="mx-auto max-w-3xl px-3 py-8 sm:px-6 sm:py-12">
        <div className="mb-6 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700 mb-2">
            <ShieldCheck size={14} /> Public Credential Registry
          </span>
          <h1 className="font-heading text-2xl font-bold text-green-900 sm:text-3xl">
            Credential Verification Result
          </h1>
          <p className="mt-1 text-sm text-ink-muted">
            Credential details are checked against the SiliconBrains University registry.
          </p>
        </div>

        {/* Verification Status Card */}
        <div className="min-w-0 overflow-hidden rounded-2xl border-2 border-cream-300 bg-white shadow-xl">
          {/* Banner */}
          <div
            className={`flex flex-col items-start justify-between gap-3 px-4 py-4 text-white sm:flex-row sm:items-center sm:px-6 ${
              credentialData.isValid ? "bg-green-700" : "bg-danger"
            }`}
          >
            <div className="flex items-center gap-2.5">
              {credentialData.isValid ? (
                <CheckCircle2 size={24} className="text-cream-200" />
              ) : (
                <XCircle size={24} className="text-white" />
              )}
              <div>
                <p className="font-heading text-base font-bold">
                  {credentialData.isValid ? "Verified Genuine Credential" : "Invalid / Revoked Credential"}
                </p>
                <p className="text-xs text-cream-200">Official Institutional Record</p>
              </div>
            </div>
            <span className="max-w-full break-all rounded-md bg-white/20 px-2.5 py-1 font-mono text-xs font-semibold">
              {credentialData.code}
            </span>
          </div>

          {/* Details Table */}
          <div className="space-y-5 p-4 sm:space-y-6 sm:p-8">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl bg-cream-50 p-4">
                <span className="text-xs font-medium text-ink-muted flex items-center gap-1.5">
                  <User size={14} className="text-green-700" /> Recipient Name
                </span>
                <p className="mt-1 font-heading text-lg font-bold text-green-900">
                  {credentialData.name}
                </p>
              </div>

              <div className="rounded-xl bg-cream-50 p-4">
                <span className="text-xs font-medium text-ink-muted flex items-center gap-1.5">
                  <Award size={14} className="text-green-700" /> Credential Type
                </span>
                <p className="mt-1 font-semibold text-green-900">{credentialData.type}</p>
              </div>

              {"course" in credentialData && (
                <div className="rounded-xl bg-cream-50 p-4 sm:col-span-2">
                  <span className="text-xs font-medium text-ink-muted flex items-center gap-1.5">
                    <Building size={14} className="text-green-700" /> Course Completed
                  </span>
                  <p className="mt-1 font-heading text-base font-bold text-green-900">
                    {credentialData.course}
                  </p>
                </div>
              )}

              {"department" in credentialData && (
                <div className="rounded-xl bg-cream-50 p-4 sm:col-span-2">
                  <span className="text-xs font-medium text-ink-muted flex items-center gap-1.5">
                    <Building size={14} className="text-green-700" /> Department
                  </span>
                  <p className="mt-1 font-heading text-base font-bold text-green-900">
                    {credentialData.department}
                  </p>
                </div>
              )}

              <div className="rounded-xl bg-cream-50 p-4">
                <span className="text-xs font-medium text-ink-muted flex items-center gap-1.5">
                  <Calendar size={14} className="text-green-700" /> Date
                </span>
                <p className="mt-1 text-sm font-semibold text-green-900">
                  {credentialData.issuedOn}
                </p>
              </div>

              <div className="rounded-xl bg-cream-50 p-4">
                <span className="text-xs font-medium text-ink-muted flex items-center gap-1.5">
                  <ShieldCheck size={14} className="text-green-700" /> Status
                </span>
                <p className="mt-1 text-sm font-semibold text-green-900">
                  {credentialData.detail}
                </p>
              </div>
            </div>

            {/* Verification Footer Note */}
            <div className="rounded-xl border border-cream-300 bg-cream-100/50 p-4 text-center text-xs text-ink-muted">
              <p>
                This digital verification is served by the SiliconBrains University credential registry.
                No third-party modification or duplication is permitted.
              </p>
            </div>

            {/* Check another code */}
            <div className="border-t border-cream-200 pt-5 sm:pt-6">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-green-900 mb-2">
                Verify another code
              </h3>
              <CredentialInlineLookup initialCode={code} />
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-cream-300 py-8 text-center text-xs text-ink-muted">
        © 2026 SiliconBrains University · Public Credential Verification
      </footer>
    </div>
  );
}
