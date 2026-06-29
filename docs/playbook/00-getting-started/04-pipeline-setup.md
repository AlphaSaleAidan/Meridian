# Pipeline Setup

Your pipeline lives in the rep portal under **Leads**. Every prospect moves through these stages:

```
Prospecting → Contacted → Demo Scheduled → Proposal Sent → Negotiation → Closed Won/Lost
```

## Stage definitions

| Stage | Definition | Update trigger |
|-------|-----------|----------------|
| Prospecting | Identified as a fit, not yet contacted | You added them as a lead |
| Contacted | Made first outreach (visit/call/email) | You logged the outreach |
| Demo Scheduled | They agreed to a 15-min demo, date is on calendar | Demo booked |
| Proposal Sent | You sent a plan recommendation in writing | Email/DocuSign sent |
| Negotiation | They've engaged with price or terms | They pushed back or asked for changes |
| Closed Won | Signed + paid | Stripe webhook confirmed payment |
| Closed Lost | No, or stalled >30 days | You marked them dead |

## Lead sources that work

1. **Walk-ins** — Visit the business. Ask what POS they use. Open with: *"I noticed you're on [their POS] — most [POS] merchants are leaving money on the table they don't see. Got 60 seconds?"*
2. **Referrals** — Ask every closed client for 3 introductions within 48 hours of the close (highest satisfaction window).
3. **Local associations** — BIAs, chambers of commerce, restaurant associations, local cannabis trade groups.
4. **POS-specific** — once you've closed 2–3 in a vertical, pattern-match: same POS + same vertical + same neighborhood = ICP. Hunt clones.

## Required notes per lead

Don't skip these. They drive your follow-up and they're what the team lead reviews:

| Field | Why it matters |
|-------|---------------|
| POS system | Routes the integration path and the objection handler |
| Vertical | Drives which features you emphasize in demo |
| Number of locations | Single vs multi-location (multi-location add-on) |
| Decision maker | Owner / GM / manager — don't pitch to non-deciders |
| Pain points | Verbatim quotes from discovery — use these in the demo |
| Objections raised | Tells you the close blocker |
| Next step + date | Forces a real follow-up, not "I'll circle back" |

## Weekly cadence

Target rhythm if you're full-time:

| Day | Focus |
|-----|-------|
| Monday | Prospecting + new leads (aim for 20 new leads/wk) |
| Tue–Thu | Demos + follow-ups (5 demos → 2–3 proposals → 1 close per 20 leads) |
| Friday | Pipeline review + admin + referral asks on recent closes |

## Numbers to watch

- **Lead → demo rate**: target 25%+. Below = your outreach script needs work.
- **Demo → proposal rate**: target 50%+. Below = discovery is too thin or demo isn't matching their pain.
- **Proposal → close rate**: target 30%+. Below = pricing/objection handling.
- **30-day churn**: target <10%. Above = you're closing the wrong fit; check that the POS is one we actually support live (not just "in registry").

Pricing is custom per deal. At a CA$343/mo deal price (70% commission = CA$240/mo), four closes = CA$960+/mo passive within 60 days. Your actual numbers depend on the prices you negotiate.

## What kills pipelines

- Not logging interactions (the next conversation can't reference the last one)
- Not setting a real next-step date (leads decay fast — 7 days max between touches when they're warm)
- Pitching to non-deciders (always confirm decision authority in discovery)
- Promising features that don't ship yet — destroys trust, kills retention, costs you recurring commission

## When to disqualify

Mark Closed Lost and move on if:
- POS is on the deprecated list (Upserve, Harbortouch, Leaf Logix, iZettle as standalone) — we can't actually serve them; lying loses the brand more than the deal is worth. Route them with empathy.
- Deal value is genuinely too low (your custom proposal price is under CA$150/mo and they won't move) — they're not ICP, you'll churn them in 30 days.
- They want a custom build — not our model. Polite no.

---

_Last updated: 2026-06-29_
_Sourced from: services/training_video_pipeline/lesson_content.json (lessons 1.4, 5.4) + docs/playbook/_status/phase-2-decisions.md (deprecate list)_
