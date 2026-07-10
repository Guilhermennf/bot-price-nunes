import type { RunRow } from "@/lib/queries";

const when = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

export default function RunsTable({ runs }: { runs: RunRow[] }) {
  if (!runs.length) {
    return (
      <p className="p-4 text-sm" style={{ color: "var(--muted)" }}>
        Sem dados de runs ainda — rode o schema.sql atualizado no Supabase.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr
            className="text-left text-xs uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            <th className="px-4 py-2 font-medium">Início</th>
            <th className="px-4 py-2 font-medium text-right">Coletadas</th>
            <th className="px-4 py-2 font-medium text-right">Postadas</th>
            <th className="px-4 py-2 font-medium text-right">Loja ✗</th>
            <th className="px-4 py-2 font-medium text-right">Tech ✗</th>
            <th className="px-4 py-2 font-medium text-right">Preço ✗</th>
            <th className="px-4 py-2 font-medium text-right">IA ✗</th>
            <th className="px-4 py-2 font-medium text-right">Dup ✗</th>
            <th className="px-4 py-2 font-medium text-right">Link ✗</th>
            <th className="px-4 py-2 font-medium">Fontes</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr
              key={r.id}
              className="border-t"
              style={{ borderColor: "var(--border)" }}
            >
              <td className="tnum whitespace-nowrap px-4 py-2">
                {when(r.started_at)}
              </td>
              <td className="tnum px-4 py-2 text-right">{r.gathered}</td>
              <td
                className="tnum px-4 py-2 text-right font-semibold"
                style={{ color: r.posted > 0 ? "var(--good)" : "var(--ink-2)" }}
              >
                {r.posted}
              </td>
              <td className="tnum px-4 py-2 text-right">{r.skipped_store}</td>
              <td className="tnum px-4 py-2 text-right">{r.skipped_tech}</td>
              <td className="tnum px-4 py-2 text-right">
                {r.skipped_validation}
              </td>
              <td className="tnum px-4 py-2 text-right">{r.skipped_ai}</td>
              <td className="tnum px-4 py-2 text-right">{r.skipped_dupe}</td>
              <td className="tnum px-4 py-2 text-right">{r.skipped_resolve}</td>
              <td className="px-4 py-2 text-xs" style={{ color: "var(--ink-2)" }}>
                {r.sources
                  ? Object.entries(r.sources)
                      .map(([k, v]) => `${k}:${v}`)
                      .join(" ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
