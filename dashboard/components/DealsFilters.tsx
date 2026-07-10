"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ALL_STORES = "__all__";

export default function DealsFilters({
  stores,
  current,
}: {
  stores: string[];
  current: { store: string; q: string; minScore: string };
}) {
  const router = useRouter();
  const [store, setStore] = useState(current.store || ALL_STORES);

  // A plain onSubmit + preventDefault (not the `action` prop) so this never
  // risks a native browser POST to the current route — that route has no
  // POST handler and would otherwise round-trip through the server.
  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const params = new URLSearchParams();
    const q = String(formData.get("q") ?? "").trim();
    const minScore = String(formData.get("minScore") ?? "").trim();
    if (q) params.set("q", q);
    if (minScore) params.set("minScore", minScore);
    if (store !== ALL_STORES) params.set("store", store);
    router.push(`/deals?${params.toString()}`);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="min-w-48 flex-1 space-y-1">
        <Label htmlFor="q">Buscar</Label>
        <Input id="q" name="q" placeholder="título do produto…"
               defaultValue={current.q} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="store-trigger">Loja</Label>
        <Select value={store} onValueChange={(v) => setStore(v ?? ALL_STORES)}>
          <SelectTrigger id="store-trigger" className="w-40">
            <SelectValue placeholder="Todas">
              {store === ALL_STORES ? "Todas" : store}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_STORES}>Todas</SelectItem>
            {stores.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
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
