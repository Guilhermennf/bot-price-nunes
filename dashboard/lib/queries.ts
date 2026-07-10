import { unstable_cache } from "next/cache";
import { db } from "./supabase";

// Data cache (independent of the route's dynamic rendering, which auth()
// forces): re-hits Supabase at most once per window per unique arg set,
// so navigating between pages within the window is instant. The bot posts
// every ~30min, so a 60s window is fresh enough.
const REVALIDATE_SECONDS = 60;

export type DealRow = {
  id: number;
  title: string;
  store: string | null;
  price: number | null;
  coupon: string | null;
  score: number | null;
  posted_at: string;
};

export type RunRow = {
  id: number;
  started_at: string;
  finished_at: string;
  gathered: number;
  posted: number;
  skipped_store: number;
  skipped_tech: number;
  skipped_validation: number;
  skipped_ai: number;
  skipped_dupe: number;
  skipped_resolve: number;
  sources: Record<string, number> | null;
};

const daysAgo = (n: number) =>
  new Date(Date.now() - n * 24 * 3600 * 1000).toISOString();

export const recentDeals = unstable_cache(
  async (limit = 20): Promise<DealRow[]> => {
    const { data, error } = await db()
      .from("deals")
      .select("id,title,store,price,coupon,score,posted_at")
      .order("posted_at", { ascending: false })
      .limit(limit);
    if (error) throw error;
    return data ?? [];
  },
  ["recent-deals"],
  { revalidate: REVALIDATE_SECONDS, tags: ["deals"] },
);

export const dealsSince = unstable_cache(
  async (days: number): Promise<DealRow[]> => {
    const { data, error } = await db()
      .from("deals")
      .select("id,title,store,price,coupon,score,posted_at")
      .gte("posted_at", daysAgo(days));
    if (error) throw error;
    return data ?? [];
  },
  ["deals-since"],
  { revalidate: REVALIDATE_SECONDS, tags: ["deals"] },
);

export const lastRuns = unstable_cache(
  async (limit = 12): Promise<RunRow[]> => {
    const { data, error } = await db()
      .from("runs")
      .select("*")
      .order("started_at", { ascending: false })
      .limit(limit);
    // The runs table may not exist until the updated schema.sql is applied —
    // degrade to an empty health view rather than crashing the page.
    if (error) return [];
    return data ?? [];
  },
  ["last-runs"],
  { revalidate: REVALIDATE_SECONDS, tags: ["runs"] },
);

export type DealsPage = {
  rows: DealRow[];
  total: number;
  page: number;
  pageSize: number;
};

export type DealsFilter = {
  page?: number;
  pageSize?: number;
  store?: string;
  q?: string;
  minScore?: number;
};

/** Server-side paginated deals with optional filters. */
export const pagedDeals = unstable_cache(
  async (filter: DealsFilter): Promise<DealsPage> => {
    const page = Math.max(1, filter.page ?? 1);
    const pageSize = Math.min(100, Math.max(5, filter.pageSize ?? 20));
    const from = (page - 1) * pageSize;

    let query = db()
      .from("deals")
      .select("id,title,store,price,coupon,score,posted_at", { count: "exact" })
      .order("posted_at", { ascending: false })
      .range(from, from + pageSize - 1);

    if (filter.store) query = query.eq("store", filter.store);
    if (filter.minScore) query = query.gte("score", filter.minScore);
    if (filter.q) query = query.ilike("title", `%${filter.q}%`);

    const { data, error, count } = await query;
    if (error) throw error;
    return { rows: data ?? [], total: count ?? 0, page, pageSize };
  },
  ["paged-deals"],
  { revalidate: REVALIDATE_SECONDS, tags: ["deals"] },
);

/** Distinct store names present in the deals table (for the filter select). */
export const storeNames = unstable_cache(
  async (): Promise<string[]> => {
    const { data, error } = await db()
      .from("deals")
      .select("store")
      .not("store", "is", null)
      .limit(1000);
    if (error) return [];
    return [...new Set((data ?? []).map((r) => r.store as string))].sort();
  },
  ["store-names"],
  { revalidate: REVALIDATE_SECONDS, tags: ["deals"] },
);

/** deals posted per calendar day (UTC) over the trailing `days`. */
export function postsPerDay(deals: DealRow[], days: number) {
  const counts = new Map<string, number>();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(Date.now() - i * 24 * 3600 * 1000);
    counts.set(d.toISOString().slice(0, 10), 0);
  }
  for (const deal of deals) {
    const day = deal.posted_at.slice(0, 10);
    if (counts.has(day)) counts.set(day, (counts.get(day) ?? 0) + 1);
  }
  return [...counts.entries()].map(([day, count]) => ({
    day: day.slice(5), // MM-DD
    count,
  }));
}
