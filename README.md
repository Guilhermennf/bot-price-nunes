# bot-price-nunes

Free-tier Telegram bot that surfaces **genuine** price drops from Brazilian
e-commerce. Runs as a single stateless script on GitHub Actions cron; all state
lives in Supabase.

## Pipeline

```
GitHub Actions cron
  → 1. Extract   aggregators (Promobit/Pelando) + direct price confirm (ML/Amazon)
  → 2. Validate  price-history vs stored median (rejects fake "de/por")
                 + checkout-sim stub (flagged off)
  → 3. AI        Gemini Flash: legit? score + PT-BR copy
  → 4. DB        Supabase: dedupe + price history
  → 5. Notify    Telegram sendMessage → private chat
```

## Stack (all free tier)

- Python 3.12 · `httpx` + `selectolax` · `playwright` (fallback only)
- Supabase (Postgres) · Google Gemini (`gemini-flash-latest`) · Telegram Bot API
- GitHub Actions scheduled workflow

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

> **Note on scrapers:** aggregator parsers (`app/sources/promobit.py`,
> `pelando.py`) read the sites' Next.js `__NEXT_DATA__` payload and guess deal
> fields heuristically. If a site changes its internal schema, adjust the key
> candidates at the top of each file — that's the only expected maintenance
> point.

## Not in v1

Affiliate link wrapping · interactive bot commands · working checkout
simulation (stub only) · multi-user distribution.
