import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Verify Academic Credentials",
  robots: { index: false, follow: false, googleBot: { index: false, follow: false } },
};

export default function VerificationLayout({ children }: { children: React.ReactNode }) {
  return <div className="page-enter">{children}</div>;
}
