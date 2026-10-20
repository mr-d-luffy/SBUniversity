import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/+$/, "");
const siteName = "SiliconBrains University";
const siteDescription = "SiliconBrains University brings online exams, course tasks, student progress, live rankings and verifiable academic credentials together in one learning platform.";

export const metadata: Metadata = {
  ...(siteUrl ? { metadataBase: new URL(siteUrl), alternates: { canonical: "/" } } : {}),
  title: { default: "SiliconBrains University | Online Learning & Exams", template: "%s | SiliconBrains University" },
  description: siteDescription,
  applicationName: siteName,
  keywords: ["SiliconBrains University", "online learning platform", "online exams", "academic portal", "student progress", "course management", "verified academic certificates"],
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName,
    title: "SiliconBrains University | Online Learning & Exams",
    description: siteDescription,
    images: ["/opengraph-image"],
    ...(siteUrl ? { url: siteUrl } : {}),
  },
  twitter: {
    card: "summary",
    title: "SiliconBrains University | Online Learning & Exams",
    description: siteDescription,
    images: ["/opengraph-image"],
  },
  robots: { index: true, follow: true, googleBot: { index: true, follow: true, "max-image-preview": "large", "max-snippet": -1, "max-video-preview": -1 } },
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#FDF6EE" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const body = (
    <html lang="en">
      <head>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
          "@context": "https://schema.org",
          "@type": "WebSite",
          name: "SiliconBrains University",
          alternateName: "SiliconBrains",
          ...(siteUrl ? { url: siteUrl } : {}),
          description: siteDescription,
          inLanguage: "en",
        }) }} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
  return process.env.NEXT_PUBLIC_DEMO_MODE === "true" ? body : <ClerkProvider>{body}</ClerkProvider>;
}
