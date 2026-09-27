# bot-price-nunes

[![ci](https://github.com/Guilhermennf/bot-price-nunes/actions/workflows/ci.yml/badge.svg)](https://github.com/Guilhermennf/bot-price-nunes/actions/workflows/ci.yml)
[![deals](https://github.com/Guilhermennf/bot-price-nunes/actions/workflows/deals.yml/badge.svg)](https://github.com/Guilhermennf/bot-price-nunes/actions/workflows/deals.yml)

Free-tier Telegram bot behind **[@nunestechpromos](https://t.me/nunestechpromos)** —
surfaces **genuine** tech price drops from Brazilian e-commerce (Amazon,
Mercado Livre, AliExpress, Shopee, Magalu). Runs as a single stateless script
on GitHub Actions cron; all state lives in Supabase. Admin dashboard in
Next.js (Auth.js) deployed on Vercel.

## Pipeline

```
GitHub Actions cron
  → 1. Extract   aggregators (Promobit/Pelando) + direct price confirm (ML/Amazon)
  → 2. Validate  price-history vs stored median (rejects fake "de/por")
                 + checkout-sim stub (flagged off)
  → 3. AI        Gemini Flash: legit? score + PT-BR copy
  → 4. DB        Supabase: dedupe + price history
  → 5. Notify    Telegram sendPhoto (+ text fallback) → private chat
```

## Stack (all free tier)

- **Bot:** Python 3.12 · `httpx` + `selectolax` · `playwright` (fallback only) ·
  pytest · ruff · mypy · Sentry · Docker
- **Data/AI:** Supabase (Postgres + RLS) · Google Gemini (`gemini-flash-latest`) ·
  Telegram Bot API
- **Dashboard:** Next.js (App Router) · Auth.js v5 · shadcn/ui · TanStack Table ·
  Zod · Recharts · Vitest + Testing Library · Playwright e2e · Vercel
- **CI/CD:** GitHub Actions (pipeline cron + quality gate) · Dependabot

## Quality gate

```bash
# bot
pytest && ruff check app tests && mypy
# dashboard
cd dashboard && npm run test && npm run typecheck && npm run build
```

Both run on every push via [`ci.yml`](.github/workflows/ci.yml).

## Dashboard auth & pagination

- Login em `/login` (Auth.js Credentials + bcrypt); todas as rotas protegidas
  por middleware. Crie o primeiro admin:
  `cd dashboard && npm run seed:admin -- voce@email.com "senha-forte"`
- `/deals`: tabela paginada server-side (TanStack Table) com filtros de loja,
  busca e score mínimo.
- e2e local: seed um admin de teste e `npm run e2e`.

## Docker

```bash
docker compose run bot-dry   # dry-run containerizado
docker compose run bot       # run real
```

## Setup

1. **Clone + install**
   ```bash
   python -m venv .venv && . .venv/Scripts/activate   # Windows
   pip install -r requirements.txt
   python -m playwright install chromium
   cp .env.example .env      # then fill in the values
   ```

2. **Telegram** — talk to [@BotFather](https://t.me/BotFather), create a bot,
   copy the token into `TELEGRAM_BOT_TOKEN`. Get your chat id by messaging the
   bot then visiting `https://api.telegram.org/bot<TOKEN>/getUpdates` and
   reading `chat.id` → `TELEGRAM_CHAT_ID`.

3. **Supabase** — create a free project, open the SQL editor, run
   [`app/db/schema.sql`](app/db/schema.sql). Copy the project URL + the
   **service_role** key into `SUPABASE_URL` / `SUPABASE_KEY`.

4. **Gemini** — get a free key at [AI Studio](https://aistudio.google.com/apikey)
   → `GEMINI_API_KEY`.

## Run

```bash
python -m app.main --dry-run     # scrape + validate + AI, prints candidates, sends nothing
python -m app.notify.telegram "test ✅"   # Telegram smoke test
python -m app.main               # full run: posts + writes to DB
```

## Deploy (GitHub Actions)

1. Push to a **public** GitHub repo (free unlimited Actions minutes).
2. Repo → Settings → Secrets and variables → Actions → add:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SUPABASE_URL`, `SUPABASE_KEY`,
   `GEMINI_API_KEY`.
3. Actions tab → **deals** → *Run workflow* to trigger manually the first time.
4. After that it runs every ~30 min via cron.

### Free-tier caveats

- **Scheduled workflows auto-disable after 60 days of no commits** — push
  occasionally, or re-enable from the Actions tab.
- **Supabase pauses a project after 7 days of inactivity** — the recurring bot
  traffic keeps it awake.
- **Gemini free tier** is rate-limited (~15 rpm / daily cap). AI is only called
  on deals that already passed price-history validation, to stay under it.

## Tuning

Thresholds live in `.env` (see [`.env.example`](.env.example)):
`MIN_SCORE`, `MIN_DISCOUNT_PCT`, `HISTORY_WINDOW_DAYS`, `REPOST_COOLDOWN_DAYS`,
`MAX_DEALS_PER_RUN`, `ENABLE_CHECKOUT_SIM`.

### How each source works (verified against live sites)

- **Promobit** — reads the homepage Next.js `__NEXT_DATA__` payload; deal fields
  are `offerTitle` / `offerPrice` / `offerOldPrice` / `offerCoupon` / `offerSlug`.
- **Pelando** — the site is client-rendered, so we call its internal REST feed
  `api-web.pelando.com.br/feed/highlights` directly (needs only an anonymous
  `x-sosho-unlogged-id` UUID header, no login).
- **Direct confirm (ML/Amazon)** — best-effort only. Both stores wall datacenter
  IPs (so it usually fails on GitHub Actions and we just trust the aggregator
  price). A headless-browser fallback exists but is **off by default**
  (`ENABLE_BROWSER_CONFIRM`) since the wall blocks it too.

> **Maintenance point:** if a site changes its schema, update the field names at
> the top of `app/sources/promobit.py` / `pelando.py`. That's the only expected
> upkeep. Both parsers fail soft (log + return `[]`), so a break never crashes
> the run.

## Not in v1

Affiliate link wrapping · interactive bot commands · working checkout
simulation (stub only) · multi-user distribution.
