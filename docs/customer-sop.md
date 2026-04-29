# Meridian Customer Operations — Standard Operating Procedures

> Version 1.0 — 2026-04-29
> Owner: Operations Team
> Review Cadence: Monthly

---

## 1. Sales-to-Onboarding Handoff

### Required Information Before Account Creation

| Field | Required | Example |
|-------|----------|---------|
| Business legal name | Yes | The Daily Grind LLC |
| Owner / primary contact | Yes | John Smith |
| Email (owner) | Yes | john@dailygrind.com |
| Phone | Yes | (555) 123-4567 |
| Business type | Yes | Coffee Shop / Restaurant / Retail |
| Number of locations | Yes | 1 (or 3 if multi-location) |
| POS system in use | Yes | Square / Clover / Toast / Other |
| Plan tier | Yes | Starter / Growth / Enterprise |
| Signed agreement | Yes | DocuSign link or PDF |
| Payment confirmed | Yes | Stripe payment ID |

### Account Creation Triggers

Account creation begins when **ALL** of the following are true:
1. Sales agreement signed (DocuSign or equivalent)
2. First payment confirmed (Stripe webhook or manual verification)
3. All required fields collected in the intake form

### Responsibility Matrix

| Step | Owner | SLA |
|------|-------|-----|
| Collect customer info | Sales Rep | Before close |
| Submit intake form | Sales Rep | Within 1 hour of payment confirmation |
| Generate access token | System (auto) | Immediate |
| Send welcome email | System (auto) | Within 5 minutes of token generation |
| Schedule onboarding call | Customer Success | Within 24 hours |
| Complete POS connection | Customer + CS Rep | Within 48 hours of onboarding call |
| First insights delivered | AI Agents (auto) | Within 48 hours of data connection |
| Mark customer as Active | Customer Success | After first insights confirmed |

### Escalation Path

| Condition | Escalation | Deadline |
|-----------|-----------|----------|
| Intake form not submitted within 2 hours | Sales Manager notified | 2 hours |
| Welcome email not received | CS Manager investigates | 1 hour |
| Onboarding call not scheduled within 24h | CS Manager assigns backup | 24 hours |
| POS not connected after 72 hours | CS Director + follow-up call | 72 hours |
| No data after 7 days | Account flagged for review | 7 days |

---

## 2. Account Creation Sequence

### Step 1: Sales Rep Submits New Customer Form

Sales rep fills out `/admin/new-customer` form with all required fields. System validates all fields are present.

### Step 2: System Auto-Generates Access Token

- Format: `mtk_` + 32 hex characters (cryptographically random)
- Token tied to: `business_id`, `plan_tier`, `max_locations`, `expiry_date` (30 days)
- Token stored in `businesses` table with `token_status: pending`
- Token can only be redeemed **once** — single-use by design

### Step 3: Access Token Triggers Portal Creation

On token redemption (customer visits `/portal?token=mtk_xxx`):
1. Validate token exists, is not expired, is not already redeemed
2. Create `business_profile` record with isolated data namespace
3. Create admin user account for business owner (email from intake)
4. Set `onboarding_progress.step = account_created`
5. Generate default dashboard configuration based on business type
6. Set `welcome_tour = true` flag for first-login guided tour
7. Mark token as `redeemed` with timestamp

### Step 4: Welcome Email Sent

Automated email includes:
- Business-branded Meridian welcome
- Direct login link: `https://meridian.tips/portal`
- Setup guide PDF attachment
- Support contact info
- Link to book onboarding call

### Step 5: Onboarding Call (Within 24 Hours)

CS rep walks customer through:
1. Logging in and navigating the dashboard
2. Connecting their POS system (Square OAuth / Clover / Toast)
3. Explaining what each agent does
4. Setting expectations for when first insights arrive
5. Answering questions

### Step 6: POS Data Connection

- Customer authorizes POS via OAuth (Square, Clover, Toast)
- System begins historical data import (up to 12 months)
- Progress shown on Settings > POS Connections page
- Historical import flagged as complete when done

### Step 7: First Insights Generated

- All 15 agents triggered automatically on first data batch
- Transaction Analyst runs first → feeds other agents
- Action Prioritizer runs last → ranks all findings by ROI
- Insight Narrator generates executive summary
- Customer notified via email: "Your first Meridian insights are ready"

### Step 8: Customer Marked Active

CS rep verifies:
- Customer can log in
- POS data is flowing
- At least 3 insights generated
- Customer confirms they can see their dashboard

Then marks `businesses.status = active` in the system.

---

## 3. Data Upload SOP

### Accepted Formats

| Format | Method | Notes |
|--------|--------|-------|
| Direct POS API | OAuth connection | Preferred — automatic, real-time |
| CSV upload | Manual via dashboard | For initial historical data or non-API POS |
| Excel (.xlsx) | Manual via dashboard | Converted to CSV internally |

### Required Data Fields

| Field | Type | Required | Example |
|-------|------|----------|---------|
| transaction_id | string | Yes | txn_abc123 |
| created_at | ISO datetime | Yes | 2026-04-15T14:32:00Z |
| total_cents | integer | Yes | 1250 |
| line_items | array | Yes | [{name, qty, price}] |
| payment_method | string | No | card / cash / mobile |
| tip_cents | integer | No | 200 |
| discount_cents | integer | No | 0 |
| customer_id | string | No | cust_xyz (for RFM analysis) |

### Validation Rules

1. `transaction_id` must be unique per business
2. `created_at` must be a valid ISO 8601 datetime
3. `total_cents` must be a positive integer
4. `line_items` must have at least 1 item with name and quantity
5. Dates cannot be in the future
6. Duplicate transaction_ids are skipped (idempotent)

### Error Handling

| Error | Response | Action |
|-------|----------|--------|
| Missing required field | Row rejected, error logged | Customer shown which rows failed |
| Invalid date format | Row rejected | Suggest correct format |
| Negative total | Row rejected | Flag for review |
| Duplicate transaction | Row skipped (no error) | Silent dedup |
| File too large (>50MB) | Upload rejected | Suggest splitting or API |
| Corrupt file | Upload rejected | Ask customer to re-export |

### Timeline After Upload

| Event | Time |
|-------|------|
| Data validation | < 30 seconds |
| Transaction ingestion | 1-5 minutes (depends on volume) |
| Agent analysis begins | Automatic after ingestion |
| First insights available | 15-60 minutes |
| Full analysis complete | 2-6 hours |
| Customer notified | Immediately after first insights |

---

## 4. Support SOP

### How Customers Submit Issues

1. **In-app**: Settings > Support > New Ticket
2. **Email**: support@meridian.tips
3. **During onboarding call**: CS rep creates ticket on their behalf

### Response Time SLAs

| Severity | Definition | First Response | Resolution Target |
|----------|-----------|---------------|-------------------|
| Critical | Dashboard down, data breach, login impossible | 1 hour | 4 hours |
| High | Incorrect data displayed, agent errors, sync failures | 4 hours | 24 hours |
| Medium | Feature request, minor UI issue, slow performance | 24 hours | 5 business days |
| Low | Question, documentation request, nice-to-have | 48 hours | 10 business days |

### Escalation Path

```
Level 1: Customer Success Rep (first response, basic troubleshooting)
  ↓ if unresolved after 2 hours (Critical) / 8 hours (High)
Level 2: Engineering Team (technical investigation)
  ↓ if unresolved after 4 hours (Critical) / 24 hours (High)
Level 3: CTO / Lead Engineer (architecture-level resolution)
```

### Agent Swarm for Diagnostics

When a support ticket involves data quality or insight accuracy:
1. CS rep triggers diagnostic swarm via admin panel
2. Transaction Analyst re-scans affected date range
3. Insight Narrator compares before/after
4. Action Prioritizer re-ranks if findings changed
5. Results attached to ticket as diagnostic report

---

## 5. Security Protocols

### Data Isolation

- Every business has a unique `business_id`
- ALL database queries filter by `business_id`
- Supabase Row Level Security (RLS) enforces isolation at the database layer
- No API endpoint returns data without `business_id` validation
- Cross-business data access is impossible by design

### Authentication Security

- Passwords hashed with bcrypt (Supabase default)
- Login rate limited: 5 attempts per 15 minutes per IP
- All login attempts logged with IP address and user agent
- JWT tokens: 24h standard, 30-day for "Remember me"
- Auto-logout after 60 minutes of inactivity
- "Log out all devices" available in account settings

### Access Token Security

- Tokens are 128-bit cryptographically random
- Single-use: redeemed tokens cannot be reused
- 30-day expiry: expired tokens rejected with clear error
- Tokens do not contain any business data (opaque identifiers)

---

## 6. Role-Based Access

| Role | Dashboard | Insights | Settings | Billing | User Mgmt | Data Upload |
|------|-----------|----------|----------|---------|-----------|-------------|
| Owner | Full | All | Full | Yes | Yes | Yes |
| Manager | Full | All | View only | No | No | Yes |
| Staff | Location only | Location only | No | No | No | No |

---

## 7. Email Sequence

| Email | Trigger | Content |
|-------|---------|---------|
| Welcome | Token generated | Access token + setup link + setup guide |
| Day 1 | 24h after welcome | How to connect your POS + video walkthrough |
| Day 3 (if no data) | No data uploaded by day 3 | Reminder + offer of live setup help |
| Day 7 (if data) | First insights generated | "Your insights are ready" + top 3 actions |
| Day 30 | Monthly | Performance summary + month-over-month trends |
| Ongoing | Weekly | Weekly digest of new insights and actions |
