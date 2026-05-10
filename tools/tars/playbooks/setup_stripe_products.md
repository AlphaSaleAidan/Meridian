# Playbook: Set Up Stripe Products & Pricing

## Goal
Create or update Stripe products and price objects for Meridian billing.

## Steps

1. Open https://dashboard.stripe.com
2. Log in (aidanpierce72@gmail.com or team account)
3. Ensure you're in the correct mode:
   - **Test mode** for development (toggle in top-right)
   - **Live mode** for production

### Create a Product

4. Go to **Products** → **+ Add Product**
5. Fill in:
   - **Name**: e.g., "Meridian Pro Plan"
   - **Description**: what's included
   - **Pricing model**: Recurring or One-time
   - **Price**: amount and currency (USD)
   - **Billing period**: Monthly / Yearly
6. Click **Save Product**
7. Copy the **Price ID** (starts with `price_`)

### Create a Webhook Endpoint

8. Go to **Developers** → **Webhooks**
9. Click **+ Add endpoint**
10. URL: `https://api.meridian.tips/webhooks/stripe`
11. Select events:
    - `checkout.session.completed`
    - `invoice.paid`
    - `invoice.payment_failed`
    - `customer.subscription.updated`
    - `customer.subscription.deleted`
12. Click **Add endpoint**
13. Copy the **Signing secret** (starts with `whsec_`)

### Update Environment Variables

Add to Railway (see add_railway_env_vars.md):
```
STRIPE_SECRET_KEY=sk_live_... (or sk_test_...)
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO_MONTHLY=price_...
STRIPE_PRICE_PRO_YEARLY=price_...
```

## Verification

```bash
# Test webhook connectivity
stripe trigger checkout.session.completed --webhook-endpoint https://api.meridian.tips/webhooks/stripe

# Or via curl
curl https://api.meridian.tips/health
```

## Notes
- Payouts are handled via ACH, marked complete by admin in-app
- Stripe is for subscription billing, not payout processing
