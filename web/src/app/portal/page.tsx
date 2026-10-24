import Link from "next/link";
import { redirect } from "next/navigation";
import { getSession, ROLE_HOME, DEMO } from "@/lib/auth";

export default async function PortalPage() {
  const session = await getSession();
  if (session) redirect(ROLE_HOME[session.role]);
  if (DEMO) redirect("/sign-in");

  const { auth } = await import("@clerk/nextjs/server");
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  // Do not send an authenticated user back to Clerk sign-in when role lookup
  // is temporarily unavailable; that creates a portal/sign-in redirect loop.
  return (
    <main className="grid min-h-dvh place-items-center bg-cream-50 px-4">
      <section className="max-w-md rounded-2xl border border-cream-300 bg-white p-6 text-center shadow-sm">
        <h1 className="font-heading text-xl font-bold text-green-900">
          Your portal is temporarily unavailable
        </h1>
        <p className="mt-2 text-sm text-ink-muted">
          We couldn’t load your account role from the university database. Please try again shortly.
        </p>
        <Link
          href="/portal"
          className="mt-5 inline-flex min-h-10 items-center justify-center rounded-lg bg-green-700 px-4 text-sm font-semibold text-white hover:bg-green-800"
        >
          Try again
        </Link>
      </section>
    </main>
  );
}
