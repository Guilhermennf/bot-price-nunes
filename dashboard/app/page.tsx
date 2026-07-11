import DealsTable from "@/components/DealsTable";
import FunnelChart from "@/components/FunnelChart";
import PostsChart from "@/components/PostsChart";
import RunsTable from "@/components/RunsTable";
import SiteNav from "@/components/SiteNav";
import StatTiles from "@/components/StatTiles";
import {
  dealsSince,
  lastRuns,
  pendingQueue,
  postsPerDay,
  recentDeals,
} from "@/lib/queries";

// auth() in SiteNav reads cookies -> the route is dynamic by nature.
export const dynamic = "force-dynamic";

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
        style={{ borderColor: "var(--viz-border)" }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

export default async function Page() {
  const [deals14d, latest, runs, queue] = await Promise.all([
    dealsSince(14),
    recentDeals(20),
    lastRuns(12),
    pendingQueue(),
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

  const subscribers = runs.find((r) => r.subscribers != null)?.subscribers;

  const tiles = [
    {
      label: "Inscritos no canal",
      value: subscribers != null ? String(subscribers) : "—",
      hint: "@nunestechpromos",
    },
    {
      label: "Na fila",
      value: String(queue.length),
      hint: "aguardando postagem",
    },
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
      <SiteNav active="overview" />
      <p className="text-sm" style={{ color: "var(--ink-2)" }}>
        Pipeline de ofertas tech · Promobit + Pelando → Telegram ·{" "}
        <a
          href="https://github.com/Guilhermennf/bot-price-nunes"
          className="underline"
          style={{ color: "var(--series-1)" }}
        >
          repo
        </a>
      </p>

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
              <p className="p-4 text-sm" style={{ color: "var(--viz-muted)" }}>
                Sem dados de runs ainda — rode o schema.sql atualizado no
                Supabase.
              </p>
            )}
          </div>
        </Section>
      </div>

      {queue.length > 0 && (
        <Section title={`Fila de postagem (${queue.length} pendente${queue.length > 1 ? "s" : ""})`}>
          <ul className="divide-y" style={{ borderColor: "var(--viz-border)" }}>
            {queue.map((q) => (
              <li key={q.id} className="flex items-center justify-between px-4 py-2 text-sm">
                <span className="truncate">{q.short_title || q.title}</span>
                <span className="tnum ml-4 shrink-0" style={{ color: "var(--ink-2)" }}>
                  {q.store} ·{" "}
                  {q.price != null
                    ? q.price.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })
                    : "—"}
                </span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Últimas ofertas postadas">
        <DealsTable deals={latest} />
      </Section>

      <Section title="Saúde do pipeline (últimas runs)">
        <RunsTable runs={runs} />
      </Section>

      <footer className="pb-4 text-xs" style={{ color: "var(--viz-muted)" }}>
        Atualiza a cada 2 min · GitHub Actions cron a cada 30 min · Supabase +
        Gemini + Telegram, tudo free tier
      </footer>
    </main>
  );
}
