"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Award, IdCard, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function CredentialLookupForm({ showSamples = false }: { showSamples?: boolean }) {
  const [code, setCode] = useState("");
  const router = useRouter();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedCode = code.trim();
    if (normalizedCode) router.push(`/verify/${encodeURIComponent(normalizedCode)}`);
  }

  return (
    <>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label htmlFor="credential-code" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-green-900">
            Credential Verification Code
          </label>
          <div className="relative">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-ink-placeholder">
              <Search size={18} aria-hidden />
            </span>
            <input
              id="credential-code"
              type="text"
              required
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="e.g. SBU-CERT-2026-PY01 or SBU-2026-0001"
              className="h-12 w-full rounded-xl border border-cream-300 bg-white pl-11 pr-4 text-base font-mono text-ink placeholder:text-ink-placeholder focus:border-green-700 focus:outline-none"
            />
          </div>
        </div>
        <Button type="submit" variant="primary" size="lg" className="w-full">
          Verify Credential Authenticity
        </Button>
      </form>
      {showSamples && (
        <div className="mt-6 border-t border-cream-200 pt-5">
          <p className="mb-3 text-xs font-medium text-ink-muted">Try checking sample credentials:</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setCode("SBU-CERT-2026-PY01")}
              className="inline-flex min-h-11 max-w-full items-center gap-1.5 rounded-lg border border-cream-300 bg-cream-50 px-3 py-1.5 text-left text-xs font-mono font-medium text-green-900 hover:bg-cream-100"
            >
              <Award size={13} className="text-green-700" aria-hidden />
              SBU-CERT-2026-PY01
            </button>
            <button
              type="button"
              onClick={() => setCode("SBU-2026-0001")}
              className="inline-flex min-h-11 items-center gap-1.5 rounded-lg border border-cream-300 bg-cream-50 px-3 py-1.5 text-xs font-mono font-medium text-green-900 hover:bg-cream-100"
            >
              <IdCard size={13} className="text-green-700" aria-hidden />
              SBU-2026-0001
            </button>
          </div>
        </div>
      )}
    </>
  );
}

export function CredentialInlineLookup({ initialCode }: { initialCode: string }) {
  const [code, setCode] = useState(initialCode);
  const router = useRouter();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedCode = code.trim();
    if (normalizedCode) router.push(`/verify/${encodeURIComponent(normalizedCode)}`);
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row">
      <label className="sr-only" htmlFor="another-credential-code">Another credential code</label>
      <input
        id="another-credential-code"
        type="text"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        placeholder="Enter Certificate Code or Student ID"
        className="h-11 min-w-0 flex-1 rounded-lg border border-cream-300 bg-white px-3 text-sm text-ink focus:border-green-700 focus:outline-none"
      />
      <Button variant="primary" size="sm" type="submit" className="w-full sm:w-auto">
        <Search size={15} aria-hidden /> Verify
      </Button>
    </form>
  );
}
