import type { DealRow } from "@/lib/queries";

const brl = (v: number | null) =>
  v == null
    ? "—"
    : v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const when = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

export default function DealsTable({ deals }: { deals: DealRow[] }) {
  if (!deals.length) {
    return (
      <p className="p-4 text-sm" style={{ color: "var(--viz-muted)" }}>
        Nenhuma oferta postada ainda.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr
            className="text-left text-xs uppercase tracking-wide"
            style={{ color: "var(--viz-muted)" }}
          >
            <th className="px-4 py-2 font-medium">Produto</th>
            <th className="px-4 py-2 font-medium">Loja</th>
            <th className="px-4 py-2 font-medium text-right">Preço</th>
            <th className="px-4 py-2 font-medium text-right">Score</th>
            <th className="px-4 py-2 font-medium">Cupom</th>
            <th className="px-4 py-2 font-medium">Quando</th>
          </tr>
        </thead>
        <tbody>
          {deals.map((d) => (
            <tr
              key={d.id}
              className="border-t"
              style={{ borderColor: "var(--viz-border)" }}
            >
              <td className="max-w-md truncate px-4 py-2" title={d.title}>
                {d.title}
              </td>
              <td className="whitespace-nowrap px-4 py-2">
                <span
                  className="rounded-full px-2 py-0.5 text-xs"
                  style={{
                    background: "var(--grid)",
                    color: "var(--ink-2)",
                  }}
                >
                  {d.store ?? "?"}
                </span>
              </td>
              <td className="tnum whitespace-nowrap px-4 py-2 text-right">
                {brl(d.price)}
              </td>
              <td className="tnum px-4 py-2 text-right">{d.score ?? "—"}</td>
              <td className="px-4 py-2">
                {d.coupon ? (
                  <code className="text-xs">{d.coupon}</code>
                ) : (
                  <span style={{ color: "var(--viz-muted)" }}>—</span>
                )}
              </td>
              <td
                className="tnum whitespace-nowrap px-4 py-2"
                style={{ color: "var(--ink-2)" }}
              >
                {when(d.posted_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
