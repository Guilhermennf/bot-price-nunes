export { auth as middleware } from "@/auth";

// Node runtime: the auth config imports bcryptjs + supabase-js (not edge-safe).
export const runtime = "nodejs";

// Protect everything except the login page, auth API and static assets.
export const config = {
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
