import Link from "next/link";
import { auth, signOut } from "@/auth";
import { Button } from "@/components/ui/button";

export default async function SiteNav({
  active,
}: {
  active: "overview" | "deals";
}) {
  const session = await auth();

  async function logout() {
    "use server";
    await signOut({ redirectTo: "/login" });
  }

  const link = (href: string, label: string, key: string) => (
    <Link
      href={href}
      className="rounded-md px-3 py-1.5 text-sm font-medium"
      style={
        active === key
          ? { background: "var(--grid)", color: "var(--ink)" }
          : { color: "var(--ink-2)" }
      }
    >
      {label}
    </Link>
  );

  return (
    <header className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold">⚡ Deal Bot</span>
        <nav className="ml-4 flex gap-1">
          {link("/", "Visão geral", "overview")}
          {link("/deals", "Ofertas", "deals")}
        </nav>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs" style={{ color: "var(--viz-muted)" }}>
          {session?.user?.email}
        </span>
        <form action={logout}>
          <Button variant="outline" size="sm" type="submit">
            Sair
          </Button>
        </form>
      </div>
    </header>
  );
}
