"use client";

import { useState } from "react";
import { SignUp } from "@clerk/nextjs";
import { Shield, Sparkles } from "lucide-react";
import Link from "next/link";
import { DemoLogin } from "@/components/features/DemoLogin";

const clerkAppearance = {
  variables: {
    colorPrimary: "#0F3D3A",
    colorText: "#092A28",
    colorTextSecondary: "#4B5F5D",
    colorInputBackground: "#FFFFFF",
    colorInputText: "#092A28",
    borderRadius: "0.75rem",
    fontFamily: "Inter, sans-serif",
    fontFamilyButtons: "Inter, sans-serif",
  },
  layout: {
    socialButtonsPlacement: "bottom" as const,
  },
  elements: {
    rootBox: "sb-auth-clerk-root",
    cardBox: "sb-auth-clerk-card-box",
    card: "sb-auth-clerk-card",
    headerTitle: "sb-auth-clerk-header-title",
    headerSubtitle: "sb-auth-clerk-header-subtitle",
    footer: "sb-auth-clerk-footer",
    formFieldLabel: "sb-auth-clerk-label",
    formFieldInput: "sb-auth-clerk-input",
    formFieldInputShowPasswordButton: "sb-auth-clerk-password-toggle",
    formFieldAction: "sb-auth-clerk-field-action",
    formButtonPrimary: "sb-auth-clerk-primary",
    socialButtonsBlockButton: "sb-auth-clerk-social-button",
    socialButtonsBlockButtonText: "sb-auth-clerk-social-button-text",
    dividerLine: "sb-auth-clerk-divider-line",
    dividerText: "sb-auth-clerk-divider-text",
    alertText: "sb-auth-clerk-alert",
  },
};

export default function SignUpPage() {
  const [useDemoMode, setUseDemoMode] = useState(false);

  return (
    <div className="auth-page">
      <main className="auth-panel">
        <header className="auth-panel-header">
          <h1>Sign up</h1>
          <Link href="/sign-in" className="auth-switch-link">Log in</Link>
        </header>
        <p className="auth-panel-caption">
          Create your account to join the learning platform.
        </p>

        {useDemoMode ? (
          <section className="auth-demo-panel" aria-label="Demo account sign in">
            <div className="auth-demo-note">
              <Sparkles size={16} aria-hidden />
              <span>Development accounts — no Google OAuth required</span>
            </div>
            <DemoLogin error={false} />
          </section>
        ) : (
          <section className="auth-clerk-panel" aria-label="Sign up">
            <SignUp
              routing="hash"
              signInUrl="/sign-in"
              fallbackRedirectUrl="/portal"
              appearance={clerkAppearance}
            />
          </section>
        )}

        <div className="auth-panel-tools">
          <button type="button" className="auth-demo-toggle" onClick={() => setUseDemoMode(!useDemoMode)}>
            {useDemoMode ? "Use Clerk sign in" : "Try a demo account"}
          </button>
          {!useDemoMode && (
            <details className="auth-help">
              <summary>
                <Shield size={14} aria-hidden />
                Having trouble?
              </summary>
              <p>
                If the form stays on a loading spinner, disable Brave Shields or your ad blocker
                for this site. Already have an account? <Link href="/sign-in">Log in</Link>.
              </p>
            </details>
          )}
        </div>
      </main>
    </div>
  );
}
