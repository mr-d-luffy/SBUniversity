import { NextResponse, type NextRequest } from "next/server";
import { clerkMiddleware } from "@clerk/nextjs/server";

const SCOPED = ["student", "teacher", "admin"];
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
    `connect-src 'self' ${apiOrigin} https://*.clerk.accounts.dev https://*.clerk.com https://*.client.protect.clerk.com:* https://api.clerk.com https://clerk-telemetry.com https://*.clerk-telemetry.com https://challenges.cloudflare.com https://www.youtube.com https://*.googleapis.com https://*.googlevideo.com wss:`,
    "frame-src https://www.youtube.com https://www.youtube-nocookie.com https://*.clerk.accounts.dev https://*.clerk.com https://challenges.cloudflare.com",
    "form-action 'self' https://*.clerk.accounts.dev https://*.clerk.com",
    "worker-src 'self' blob:",
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

/** Require a signed-in user; the app layout checks the authoritative DB role. */
function decide(req: NextRequest, authenticated: boolean) {
  const path = req.nextUrl.pathname;
  const scope = SCOPED.find(
    (r) => path === `/${r}` || path.startsWith(`/${r}/`),
  );
  const isShared = SHARED.some((p) => path.startsWith(p));

  // Not a protected path — let it through
  if (!scope && !isShared) return null;

  if (!authenticated) return secureRedirect(new URL("/sign-in", req.url));

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
  decide(req, Boolean(req.cookies.get("sbu_demo")?.value)) ??
  nextWithHeaders(req);

// Production mode: Clerk establishes authentication; the database supplies roles.
const prodMiddleware = clerkMiddleware(async (auth, req) => {
  const { userId } = await auth();
  return decide(req, Boolean(userId)) ?? nextWithHeaders(req);
});

export const proxy = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
  ? demoMiddleware
  : prodMiddleware;

export const config = { matcher: ["/((?!_next|.*\\..*).*)" ] };
