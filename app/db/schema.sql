-- Run this once in the Supabase SQL editor.
-- Two tables: deals (dedupe / posted history) and price_history (series).

create table if not exists deals (
    id          bigint generated always as identity primary key,
    url_key     text not null,
    title       text not null,
    store       text,
    price       numeric,
    coupon      text,
    score       int,
    posted_at   timestamptz not null default now()
);

-- One product may legitimately be posted more than once over time (when it
-- gets cheaper), so url_key is indexed but NOT unique.
create index if not exists deals_url_key_idx on deals (url_key);
create index if not exists deals_posted_at_idx on deals (posted_at desc);

create table if not exists price_history (
    id           bigint generated always as identity primary key,
    product_key  text not null,
    price        numeric not null,
    captured_at  timestamptz not null default now()
);

create index if not exists price_history_key_idx
    on price_history (product_key, captured_at desc);

-- One row per pipeline run (feeds the dashboard's health view).
create table if not exists runs (
    id                  bigint generated always as identity primary key,
    started_at          timestamptz not null,
    finished_at         timestamptz not null default now(),
    gathered            int not null default 0,
    posted              int not null default 0,
    skipped_store       int not null default 0,
    skipped_tech        int not null default 0,
    skipped_validation  int not null default 0,
    skipped_ai          int not null default 0,
    skipped_dupe        int not null default 0,
    skipped_resolve     int not null default 0,
    sources             jsonb
);

create index if not exists runs_started_idx on runs (started_at desc);

-- ---------------------------------------------------------------------------
-- Row Level Security: the dashboard reads with the public anon key, so lock
-- every table to SELECT-only for anon. The bot uses the service_role key,
-- which bypasses RLS entirely.
-- ---------------------------------------------------------------------------
alter table deals          enable row level security;
alter table price_history  enable row level security;
alter table runs           enable row level security;

drop policy if exists anon_read_deals on deals;
create policy anon_read_deals on deals
    for select to anon using (true);

drop policy if exists anon_read_price_history on price_history;
create policy anon_read_price_history on price_history
    for select to anon using (true);

drop policy if exists anon_read_runs on runs;
create policy anon_read_runs on runs
    for select to anon using (true);
