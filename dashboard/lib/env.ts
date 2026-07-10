// Zod-validated server environment. Imported only from server code.
import "server-only";
import { z } from "zod";

const EnvSchema = z.object({
  SUPABASE_URL: z.string().url(),
  SUPABASE_KEY: z.string().min(20),
  AUTH_SECRET: z.string().min(16),
});

let cached: z.infer<typeof EnvSchema> | null = null;

export function env() {
  if (!cached) {
    const parsed = EnvSchema.safeParse(process.env);
    if (!parsed.success) {
      const missing = parsed.error.issues.map((i) => i.path.join(".")).join(", ");
      throw new Error(`Invalid/missing environment variables: ${missing}`);
    }
    cached = parsed.data;
  }
  return cached;
}
