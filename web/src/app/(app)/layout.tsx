import { redirect } from "next/navigation";
import { headers } from "next/headers";
import { Shell } from "@/components/shell/Shell";
import { DEMO, getSession, ROLE_HOME } from "@/lib/auth";
import type { Metadata } from "next";

export const metadata: Metadata = {
  robots: { index: false, follow: false, googleBot: { index: false, follow: false } },
};

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session) redirect("/portal");

  const pathname = (await headers()).get("x-pathname") ?? "";
  const requiredRole = (["student", "teacher", "admin"] as const).find(
    (role) => pathname === `/${role}` || pathname.startsWith(`/${role}/`),
  );
  if (requiredRole && requiredRole !== session.role) {
    redirect(ROLE_HOME[session.role]);
  }

  return <Shell role={session.role} name={session.name} demo={DEMO}>{children}</Shell>;
}
