import DealsDataTable from "@/components/DealsDataTable";
import DealsFilters from "@/components/DealsFilters";
import SiteNav from "@/components/SiteNav";
import { pagedDeals, storeNames } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function DealsPage({
  searchParams,
}: {
  searchParams: Promise<{
    page?: string;
    store?: string;
    q?: string;
    minScore?: string;
  }>;
}) {
  const params = await searchParams;
  const [result, stores] = await Promise.all([
    pagedDeals({
      page: Number(params.page) || 1,
      store: params.store || undefined,
      q: params.q || undefined,
      minScore: Number(params.minScore) || undefined,
    }),
    storeNames(),
  ]);

  return (
    <main className="mx-auto max-w-6xl space-y-4 p-4 sm:p-6">
      <SiteNav active="deals" />
      <section className="card p-4">
        <DealsFilters
          stores={stores}
          current={{
            store: params.store ?? "",
            q: params.q ?? "",
            minScore: params.minScore ?? "",
          }}
        />
      </section>
      <section className="card p-2">
        <DealsDataTable
          rows={result.rows}
          total={result.total}
          page={result.page}
          pageSize={result.pageSize}
        />
      </section>
    </main>
  );
}
