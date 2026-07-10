type Tile = { label: string; value: string; hint?: string };

export default function StatTiles({ tiles }: { tiles: Tile[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.label} className="card p-4">
          <div className="text-xs font-medium" style={{ color: "var(--muted)" }}>
            {t.label}
          </div>
          <div className="mt-1 text-2xl font-semibold">{t.value}</div>
          {t.hint && (
            <div className="mt-1 text-xs" style={{ color: "var(--ink-2)" }}>
              {t.hint}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
