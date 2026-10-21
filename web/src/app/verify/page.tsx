import Link from "next/link";
import { GraduationCap, ShieldCheck, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CredentialLookupForm } from "@/components/features/CredentialLookupForm";

export default function VerifyIndexPage() {
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
          <CredentialLookupForm showSamples />
        </Card>
      </main>
    </div>
  );
}
