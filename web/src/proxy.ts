import { NextResponse, type NextRequest } from "next/server";
import { clerkMiddleware } from "@clerk/nextjs/server";

type Role = "student" | "teacher" | "admin";
const HOME: Record<Role, string> = {
  student: "/student/dashboard",
  teacher: "/teacher/dashboard",
  admin: "/admin/users",
};
const SCOPED: Role[] = ["student", "teacher", "admin"];
const SHARED = ["/ranking", "/notices", "/assistant"];

function createNonce() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return btoa(String.fromCharCode(...bytes));
}

function createCsp(nonce: string) {
  const configuredApi = process.env.NEXT_PUBLIC_API_BASE_URL;
  let apiOrigin = "'self'";
  if (configuredApi) {
    try {
      apiOrigin = new URL(configuredApi).origin;
    } catch {
      apiOrigin = "'self'";
    }
  }
  const directives = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic' https://*.clerk.accounts.dev https://*.clerk.com https://challenges.cloudflare.com https://www.youtube.com https://s.ytimg.com`,
    `style-src 'self' 'nonce-${nonce}' https://fonts.googleapis.com`,
    "style-src-attr 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data: https://fonts.gstatic.com",
    `connect-src 'self' ${apiOrigin} https://*.clerk.accounts.dev https://*.clerk.com https://api.clerk.com https://challenges.cloudflare.com https://www.youtube.com https://*.googleapis.com https://*.googlevideo.com wss:`,
    "frame-src https://www.youtube.com https://www.youtube-nocookie.com https://*.clerk.accounts.dev https://*.clerk.com https://challenges.cloudflare.com",
    "form-action 'self' https://*.clerk.accounts.dev https://*.clerk.com",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
  ];
  if (process.env.NODE_ENV === "production") directives.push("upgrade-insecure-requests");
  return directives.join("; ");
}

function addSecurityHeaders(response: NextResponse, nonce?: string) {
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  response.headers.set("Cross-Origin-Opener-Policy", "same-origin-allow-popups");
  response.headers.set("Cross-Origin-Resource-Policy", "same-site");
  if (process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_SITE_URL?.startsWith("https://")) {
    response.headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains");
  }
  if (nonce) response.headers.set("Content-Security-Policy", createCsp(nonce));
  return response;
}

function secureRedirect(url: URL) {
  const nonce = process.env.NODE_ENV === "production" ? createNonce() : undefined;
  const response = NextResponse.redirect(url);
  return addSecurityHeaders(response, nonce);
}

/**
 * Returns a redirect response when the visitor should not view `path`.
 *
 * @param role  - Role from JWT claims. `undefined` means authenticated but
 *                no role in the JWT yet (page-level guard will handle it).
 *                `null` means not signed in at all.
 */
function decide(req: NextRequest, role: Role | null | undefined) {
  const path = req.nextUrl.pathname;
  const scope = SCOPED.find(
    (r) => path === `/${r}` || path.startsWith(`/${r}/`),
  );
  const isShared = SHARED.some((p) => path.startsWith(p));

  // Not a protected path — let it through
  if (!scope && !isShared) return null;

  // Not authenticated at all → sign-in
  if (role === null) return secureRedirect(new URL("/sign-in", req.url));

  // Authenticated but JWT has no role yet → let through; page guard handles it
  if (role === undefined) return null;

  // Authenticated with a role, but in the wrong scope → redirect to their home
  if (scope && scope !== role)
    return secureRedirect(new URL(HOME[role], req.url));

  return null;
}

function nextWithHeaders(req: NextRequest) {
  const requestHeaders = new Headers(req.headers);
  requestHeaders.set("x-pathname", req.nextUrl.pathname);
  if (process.env.NODE_ENV === "production") {
    const nonce = createNonce();
    requestHeaders.set("x-nonce", nonce);
    requestHeaders.set("Content-Security-Policy", createCsp(nonce));
    const response = NextResponse.next({ request: { headers: requestHeaders } });
    return addSecurityHeaders(response, nonce);
  }
  return addSecurityHeaders(
    NextResponse.next({ request: { headers: requestHeaders } }),
  );
}

// Demo mode: role comes from a cookie
const demoMiddleware = (req: NextRequest) =>
  decide(req, req.cookies.get("sbu_demo")?.value as Role | undefined) ??
  nextWithHeaders(req);

// Production mode: role comes from Clerk JWT claims
const prodMiddleware = clerkMiddleware(async (auth, req) => {
  const { sessionClaims } = await auth();
  const claims = sessionClaims as Record<string, unknown> | undefined;

  // Not signed in
  if (!claims) return decide(req, null) ?? nextWithHeaders(req);

  // Read role only from JWT — never assume "student" as fallback.
  // If role isn't in the JWT, it stays `undefined` and the page component
  // (which calls currentUser()) will do the authoritative role check.
  const metadata = (
    claims?.metadata ?? claims?.publicMetadata ?? claims?.public_metadata
  ) as Record<string, unknown> | undefined;
  const role: Role | undefined =
    (metadata?.role as Role | undefined) ??
    (claims?.role as Role | undefined) ??
    undefined;

  return decide(req, role) ?? nextWithHeaders(req);
});

export const proxy = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
  ? demoMiddleware
  : prodMiddleware;

export const config = { matcher: ["/((?!_next|.*\\..*).*)" ] };
