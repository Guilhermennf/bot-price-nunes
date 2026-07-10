import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { compare } from "bcryptjs";
import { z } from "zod";
import { db } from "@/lib/supabase";

const CredentialsSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  callbacks: {
    // Drives the middleware: unauthenticated hits on protected routes
    // get redirected to the sign-in page.
    authorized: ({ auth }) => Boolean(auth?.user),
  },
  providers: [
    Credentials({
      credentials: { email: {}, password: {} },
      async authorize(credentials) {
        const parsed = CredentialsSchema.safeParse(credentials);
        if (!parsed.success) return null;
        const { email, password } = parsed.data;

        const { data, error } = await db()
          .from("admin_users")
          .select("id,email,password_hash")
          .eq("email", email.toLowerCase())
          .limit(1);
        if (error || !data?.length) return null;

        const admin = data[0];
        const ok = await compare(password, admin.password_hash);
        if (!ok) return null;
        return { id: String(admin.id), email: admin.email };
      },
    }),
  ],
});
