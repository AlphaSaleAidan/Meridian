# Library Integration Guide

Quick-start recipes for adding each library to Meridian. See CLAUDE.md "Library Skills" for full API patterns and gotchas.

## Priority Order

1. **Stripe** (billing) — unblocks tier upgrades
2. **Sentry** (monitoring) — unblocks production launch
3. **statsforecast** (forecasting) — replaces hand-rolled forecasts
4. **Anthropic** (LLM) — adds Claude as insight enhancer
5. **PostHog** (analytics) — tracks merchant usage
6. **OpenTelemetry** (tracing) — distributed observability
7. **DuckDB** (analytics SQL) — complex analytical queries
8. **Polars** (DataFrames) — performance-critical transforms

---

## 1. Stripe Integration

### Backend (`src/billing/`)

```bash
pip install stripe
```

```python
# src/billing/stripe_service.py
import stripe
import asyncio
from ..config import app as config

stripe.api_key = config.STRIPE_SECRET_KEY
stripe.api_version = "2024-12-18.acacia"

async def create_checkout_session(org_id: str, price_id: str) -> str:
    session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{config.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{config.FRONTEND_URL}/billing/cancel",
        metadata={"org_id": org_id},
    )
    return session.url
```

### Webhook (`src/api/routes/billing.py`)

```python
@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(payload, sig, ENDPOINT_SECRET)
    # Handle: checkout.session.completed, invoice.payment_succeeded,
    #         customer.subscription.deleted
```

### Frontend

```bash
cd frontend && npm install @stripe/stripe-js @stripe/react-stripe-js
```

- Create `frontend/src/components/billing/CheckoutForm.tsx`
- Wrap in `<Elements stripe={stripePromise} options={{clientSecret, appearance: {theme: 'night'}}}>` 
- Use `<PaymentElement />` + `useStripe()` + `useElements()`

### Price IDs (create in Stripe Dashboard)

| Plan | Monthly (cents) | Price ID |
|------|----------------|----------|
| Starter | 25000 | `price_starter_monthly` |
| Growth | 25000 | `price_growth_monthly` |
| Enterprise | Custom | Contact sales |

---

## 2. Sentry Integration

### Backend

```bash
pip install "sentry-sdk[fastapi]"
```

In `src/api/app.py`, add BEFORE the FastAPI import:
```python
import sentry_sdk
sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"), traces_sample_rate=0.2,
                release="meridian@0.2.0", send_default_pii=False)
```

### Frontend

```bash
cd frontend && npm install @sentry/react @sentry/vite-plugin
```

In `frontend/src/main.tsx`, add at the very top:
```typescript
import * as Sentry from '@sentry/react';
Sentry.init({ dsn: import.meta.env.VITE_SENTRY_DSN, tracesSampleRate: 0.2 });
```

Replace `ErrorBoundary.tsx` with `<Sentry.ErrorBoundary>`.

Add to `vite.config.ts`:
```typescript
import { sentryVitePlugin } from '@sentry/vite-plugin';
// In plugins: sentryVitePlugin({ org: 'meridian', project: 'dashboard' })
```

---

## 3. statsforecast Integration

```bash
pip install statsforecast
```

Replace `src/ai/generators/forecasts.py` weighted-average logic with:
```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS

sf = StatsForecast(
    models=[AutoARIMA(season_length=7), AutoETS(season_length=7)],
    freq='D', n_jobs=-1,
)
# Input: DataFrame with columns unique_id, ds, y
forecasts = sf.forecast(df=df, h=7, level=[80, 95])
```

Warm up numba JIT at startup (first call takes 30-60s).

---

## 4. Anthropic Integration

```bash
pip install anthropic
```

Add to `src/ai/llm_layer.py` as Claude fallback:
```python
import anthropic
client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env

async def enhance_with_claude(raw_insight: dict) -> str:
    message = await client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1024,
        system="You are a POS analytics assistant for small businesses.",
        messages=[{"role": "user", "content": json.dumps(raw_insight)}],
    )
    return message.content[0].text
```

---

## 5. PostHog Integration

```bash
pip install posthog
```

```python
from posthog import Posthog
posthog = Posthog(project_api_key=os.environ["POSTHOG_KEY"], host="https://us.i.posthog.com")

# Track in API routes
posthog.capture(distinct_id=org_id, event='analysis_run',
    properties={'vertical': 'restaurant', 'agents_count': 22})

# Shutdown in lifespan
posthog.shutdown()
```

---

## Environment Variables Needed

```bash
# .env additions
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
SENTRY_DSN=https://...@sentry.io/...
SENTRY_AUTH_TOKEN=sntrys_...          # for source maps
ANTHROPIC_API_KEY=sk-ant-...
POSTHOG_KEY=phc_...
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Frontend (.env)
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...
VITE_SENTRY_DSN=https://...@sentry.io/...
```
