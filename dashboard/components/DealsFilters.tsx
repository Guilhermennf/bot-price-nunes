"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function DealsFilters({
  stores,
  current,
}: {
  stores: string[];
  current: { store: string; q: string; minScore: string };
}) {
  const router = useRouter();

  function apply(formData: FormData) {
    const params = new URLSearchParams();
    for (const key of ["q", "store", "minScore"] as const) {
      const v = String(formData.get(key) ?? "").trim();
      if (v) params.set(key, v);
    }
    router.push(`/deals?${params.toString()}`);
  }

  return (
    <form action={apply} className="flex flex-wrap items-end gap-3">
      <div className="min-w-48 flex-1 space-y-1">
        <Label htmlFor="q">Buscar</Label>
        <Input id="q" name="q" placeholder="título do produto…"
               defaultValue={current.q} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="store">Loja</Label>
        <select
          id="store"
          name="store"
          defaultValue={current.store}
          className="border-input bg-transparent h-9 rounded-md border px-3 text-sm"
        >
          <option value="">Todas</option>
          {stores.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1">
        <Label htmlFor="minScore">Score mín.</Label>
        <Input id="minScore" name="minScore" type="number" min={0} max={100}
               className="w-24" defaultValue={current.minScore} />
      </div>
      <Button type="submit" size="sm">
        Filtrar
      </Button>
    </form>
  );
}
