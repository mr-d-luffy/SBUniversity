import { cookies } from "next/headers";
import { getBaseUrl } from "@/lib/api";

export type Role = "student" | "teacher" | "admin";
export const DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
export const DEMO_COOKIE = "sbu_demo";

export const DEMO_USERS: Record<Role, { name: string; email: string; password: string }> = {
  student: { name: "Aarav Sharma", email: "student@sbu.demo", password: "Student@123" },
  teacher: { name: "Dr. Meera Iyer", email: "teacher@sbu.demo", password: "Teacher@123" },
  admin: { name: "Rohan Desai", email: "admin@sbu.demo", password: "Admin@123" },
};

export const ROLE_HOME: Record<Role, string> = {
  student: "/student/dashboard",
  teacher: "/teacher/dashboard",
  admin: "/admin/users",
};

export interface Session { role: Role; name: string }

function isRole(value: unknown): value is Role {
  return typeof value === "string" && Object.hasOwn(ROLE_HOME, value);
}

async function getDatabaseSession(token: string): Promise<Session | null> {
  let baseUrl = getBaseUrl();
  if (baseUrl.startsWith("/")) {
    if (process.env.NODE_ENV === "production") return null;
    // The development API is exposed through Next's local-backend rewrite.
    baseUrl = new URL(baseUrl, process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").toString();
  }

  const response = await fetch(`${baseUrl}/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) return null;

  const profile = await response.json() as { role?: unknown; full_name?: unknown };
  if (!isRole(profile.role)) return null;
  return {
    role: profile.role,
    name: typeof profile.full_name === "string" && profile.full_name.trim()
      ? profile.full_name
      : "User",
  };
}

/** Server-side session. Clerk proves identity; the database (or demo cookie) supplies the role. */
export async function getSession(): Promise<Session | null> {
  if (DEMO) {
    const role = (await cookies()).get(DEMO_COOKIE)?.value as Role | undefined;
    return role && Object.hasOwn(DEMO_USERS, role) ? { role, name: DEMO_USERS[role].name } : null;
  }
  const { auth } = await import("@clerk/nextjs/server");
  const { userId, sessionClaims, getToken } = await auth();
  if (!userId) return null;

  const claims = sessionClaims as Record<string, unknown> | null;
  const name =
    (claims?.name as string | undefined) ??
    (claims?.first_name as string | undefined) ??
    "User";

  // The database is authoritative for roles. Clerk claims can be missing or
  // stale after an administrator changes a user's role.
  try {
    const token = await getToken();
    const databaseSession = token ? await getDatabaseSession(token) : null;
    return databaseSession
      ? { ...databaseSession, name: databaseSession.name === "User" ? name : databaseSession.name }
      : null;
  } catch {
    return null;
  }
}
