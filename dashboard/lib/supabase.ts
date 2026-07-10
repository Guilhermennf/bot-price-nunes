// Server-only Supabase client. The service key never reaches the browser:
// this module is imported exclusively from Server Components / lib code.
import "server-only";
import { createClient } from "@supabase/supabase-js";

export function db() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_KEY;
  if (!url || !key) {
    throw new Error("SUPABASE_URL / SUPABASE_KEY not configured");
  }
  return createClient(url, key, { auth: { persistSession: false } });
}
