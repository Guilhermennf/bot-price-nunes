/**
 * Create (or update the password of) a dashboard admin.
 *   npm run seed:admin -- admin@example.com "senha-forte"
 * Uses SUPABASE_URL/SUPABASE_KEY from .env.local (service key, server-side).
 */
import { readFileSync } from "node:fs";
import { createClient } from "@supabase/supabase-js";
import { hash } from "bcryptjs";
import { z } from "zod";

// minimal .env.local loader (no dotenv dependency)
try {
  for (const line of readFileSync(".env.local", "utf-8").split(/\r?\n/)) {
    const m = line.trim().match(/^([A-Z_]+)=(.*)$/);
    if (m && !process.env[m[1]]) process.env[m[1]] = m[2].trim();
  }
} catch {
  /* .env.local optional when vars come from the shell */
}

const Args = z.tuple([z.string().email(), z.string().min(8)]);

async function main() {
  const parsed = Args.safeParse(process.argv.slice(2));
  if (!parsed.success) {
    console.error('Usage: npm run seed:admin -- <email> "<password >= 8 chars>"');
    process.exit(1);
  }
  const [email, password] = parsed.data;

  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_KEY;
  if (!url || !key) {
    console.error("SUPABASE_URL / SUPABASE_KEY not set (.env.local)");
    process.exit(1);
  }

  const db = createClient(url, key, { auth: { persistSession: false } });
  const password_hash = await hash(password, 12);
  const { error } = await db
    .from("admin_users")
    .upsert({ email: email.toLowerCase(), password_hash }, { onConflict: "email" });
  if (error) {
    console.error("seed failed:", error.message);
    process.exit(1);
  }
  console.log(`admin ready: ${email}`);
}

main();
