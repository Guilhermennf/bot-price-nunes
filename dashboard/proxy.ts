// Proxy always runs on Node.js — no separate runtime declaration needed
// (unlike the old middleware.ts, which had to opt in explicitly).
export { auth as proxy } from "@/auth";

// Protect everything except the login page, auth API and static assets.
export const config = {
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
