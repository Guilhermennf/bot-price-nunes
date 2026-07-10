import DealsTable from "@/components/DealsTable";
import FunnelChart from "@/components/FunnelChart";
import PostsChart from "@/components/PostsChart";
import RunsTable from "@/components/RunsTable";
import StatTiles from "@/components/StatTiles";
import {
  dealsSince,
  lastRuns,
  postsPerDay,
  recentDeals,
} from "@/lib/queries";

export const revalidate = 120;

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card">
      <h2
        className="border-b px-4 py-3 text-sm font-semibold"
        style={{ borderColor: "var(--border)" }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

export default async function Page() {
  const [deals14d, latest, runs] = await Promise.all([
    dealsSince(14),
    recentDeals(20),
    lastRuns(12),
  ]);

  const deals7d = deals14d.filter(
    (d) => new Date(d.posted_at).getTime() > Date.now() - 7 * 24 * 3600 * 1000,
  );
  const runs24h = runs.filter(
    (r) => new Date(r.started_at).getTime() > Date.now() - 24 * 3600 * 1000,
  );
  const scores = deals7d.map((d) => d.score).filter((s): s is number => s != null);
  const avgScore = scores.length
    ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
    : null;
  const lastRun = runs[0];
  const funnelRate =
    lastRun && lastRun.gathered > 0
      ? `${((lastRun.posted / lastRun.gathered) * 100).toFixed(0)}%`
      : "—";

  const tiles = [
    {
      label: "Ofertas (7 dias)",
      value: String(deals7d.length),
      hint: `${deals14d.length} em 14 dias`,
    },
    {
      label: "Runs (24h)",
      value: runs.length ? String(runs24h.length) : "—",
      hint: lastRun
        ? `última: ${new Date(lastRun.started_at).toLocaleTimeString("pt-BR", {
            hour: "2-digit",
            minute: "2-digit",
          })}`
        : "aguardando tabela runs",
    },
    {
      label: "Score médio (7d)",
      value: avgScore != null ? String(avgScore) : "—",
      hint: "nota do Gemini 0–100",
    },
    {
      label: "Funil (última run)",
      value: funnelRate,
      hint: lastRun
        ? `${lastRun.posted}/${lastRun.gathered} coletadas`
        : undefined,
    },
  ];

  const funnel = lastRun
    ? [
        { stage: "Coletadas", count: lastRun.gathered },
        { stage: "Loja ✗", count: lastRun.skipped_store },
        { stage: "Não-tech ✗", count: lastRun.skipped_tech },
        { stage: "Preço ✗", count: lastRun.skipped_validation },
        { stage: "IA ✗", count: lastRun.skipped_ai },
        { stage: "Duplicada ✗", count: lastRun.skipped_dupe },
        { stage: "Sem link ✗", count: lastRun.skipped_resolve },
        { stage: "Postadas", count: lastRun.posted },
      ]
    : [];

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <header className="flex items-baseline justify-between">
        <div>
          <h1 className="text-xl font-bold">Deal Bot — Dashboard</h1>
          <p className="text-sm" style={{ color: "var(--ink-2)" }}>
            Pipeline de ofertas tech · Promobit + Pelando → Telegram
          </p>
        </div>
        <a
          href="https://github.com/Guilhermennf/bot-price-nunes"
          className="text-sm underline"
          style={{ color: "var(--series-1)" }}
        >
          repo
        </a>
      </header>

      <StatTiles tiles={tiles} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Section title="Ofertas postadas por dia (14 dias)">
          <div className="p-3">
            <PostsChart data={postsPerDay(deals14d, 14)} />
          </div>
        </Section>
        <Section title="Funil da última run">
          <div className="p-3">
            {funnel.length ? (
              <FunnelChart data={funnel} />
            ) : (
              <p className="p-4 text-sm" style={{ color: "var(--muted)" }}>
                Sem dados de runs ainda — rode o schema.sql atualizado no
                Supabase.
              </p>
            )}
          </div>
        </Section>
      </div>

      <Section title="Últimas ofertas postadas">
        <DealsTable deals={latest} />
      </Section>

      <Section title="Saúde do pipeline (últimas runs)">
        <RunsTable runs={runs} />
      </Section>

      <footer className="pb-4 text-xs" style={{ color: "var(--muted)" }}>
        Atualiza a cada 2 min · GitHub Actions cron a cada 30 min · Supabase +
        Gemini + Telegram, tudo free tier
      </footer>
    </main>
  );
}
