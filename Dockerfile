# Runtime image for the deal-bot pipeline (one stateless run per invocation).
# Production runs on GitHub Actions directly; this image is for local dev,
# portability, and running the pipeline anywhere a container runs.
FROM python:3.12-slim

WORKDIR /bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

# Chromium/Playwright intentionally NOT installed: browser features
# (ENABLE_BROWSER_CONFIRM / ENABLE_CHECKOUT_SIM) default to off.

ENTRYPOINT ["python", "-m", "app.main"]
