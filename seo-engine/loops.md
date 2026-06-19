# Meridian SEO Engine — Autonomous Loops

Three flows. Two are deterministic scripts (best as cron). One needs the model (best as `/loop`).
**Hard rule: nothing auto-publishes to the live site.** The content loop writes *drafts* to a
branch; a human reviews and runs the manual Contabo build to publish. This keeps accuracy and
compliance claims under human control.

```
topics.json ──► [1] content-draft loop ──► guide draft on branch ──► content-queue.json (status: drafted)
                                                                              │
                                                   [2] daily-report ──────────┘──► Telegram / email (you)
reddit (read-only) ──► [3] reddit-monitor ──► Telegram / email (you reply as yourself)
```

## [1] Content-draft loop  (model-driven → `/loop`)
Picks the highest-priority `queued` topic, drafts it as a new `GuideData` entry in
`frontend/src/data/seo-guides.ts` (matching existing shape + schema), registers it in the
guides index + sitemap + llms.txt, flips the topic to `drafted` in `topics.json`, and appends
to `content-queue.json`. **Never** commits to main, **never** deploys.

Launch (self-paced, ~1/day):
```
/loop draft the next queued Meridian SEO topic from seo-engine/topics.json into a guide on
branch feat/canada-compliance-seo, true-to-product only, then update the queue + sitemap + llms.txt
```

## [2] Daily report  (deterministic → cron)
```
node seo-engine/daily-report.mjs        # delivers if TELEGRAM_* or RESEND_* set, else dry-run
```
Suggested: daily 13:00 UTC (08:00 ET). Reports pages live, drafted today, awaiting review,
backlog, and Search Console metrics (once GSC_* env is set).

## [3] Reddit mention monitor  (deterministic, READ-ONLY → cron)
```
node seo-engine/reddit-monitor.mjs      # alerts on new mentions; never posts
```
Suggested: every 4–6h. You reply manually, disclosed as the founder. No bots, no sockpuppets.

## Delivery channel (pick one or both)
Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
Email (Resend): `RESEND_API_KEY`, `REPORT_EMAIL_TO`, `REPORT_EMAIL_FROM`
Search Console: `GSC_SITE_URL` + either `GSC_SA_KEY_FILE` (service account, best for cron)
or `GSC_ACCESS_TOKEN` (bearer token, for quick manual testing)

Secrets live in env only — never commit them.
```
