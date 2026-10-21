"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function CredentialVerifyForm() {
  const [verifyCode, setVerifyCode] = useState("");
  const router = useRouter();

  function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = verifyCode.trim();
    if (code) router.push(`/verify/${encodeURIComponent(code)}`);
  }

  return (
    <form onSubmit={handleVerify} className="mx-auto mt-6 flex max-w-xl flex-col gap-2 sm:flex-row">
      <label className="sr-only" htmlFor="landing-credential-code">Credential verification code</label>
      <div className="relative flex-1">
        <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-ink-placeholder">
          <Search size={18} aria-hidden />
        </span>
        <input
          id="landing-credential-code"
          type="text"
          required
          value={verifyCode}
          onChange={(event) => setVerifyCode(event.target.value)}
          placeholder="Enter Certificate Code (e.g. SBU-CERT-2026-PY01)"
          className="h-12 w-full rounded-xl border border-cream-300 bg-white pl-11 pr-4 text-sm font-mono text-ink placeholder:text-ink-placeholder shadow-sm focus:border-green-700 focus:outline-none"
        />
      </div>
      <Button type="submit" variant="primary" size="lg">
        Verify Credential
      </Button>
    </form>
  );
}
