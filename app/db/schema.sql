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
