# Meridian Architecture Decisions

> Living document — updated with each significant decision.

---

## ADR-001: Supabase for Auth + Multi-Tenant Data

**Decision:** Use Supabase Auth for authentication and Supabase PostgreSQL with Row Level Security for multi-tenant data isolation.

**Why:**
- Supabase Auth provides email/password, magic links, OAuth, and JWT out of the box
- RLS enforces data isolation at the database layer — impossible to bypass from the application
- Reduces custom auth code to near zero
- Scales to thousands of business tenants without schema changes
- Built-in rate limiting, audit logging, and session management

**Trade-off:** Vendor lock-in on Supabase. Mitigated by using standard PostgreSQL — can migrate to self-hosted Supabase or raw Postgres if needed.

---

## ADR-002: Token-Based Portal Provisioning

**Decision:** Sales team generates a single-use access token per business. Customer redeems the token to activate their portal.

**Why:**
- Decouples the sales process from engineering — no manual database work needed
- Token is the handoff artifact between sales and the customer
- Single-use + 30-day expiry prevents token sharing or stale invites
- Works for both during-sale setup (sales rep enters token) and post-sale self-service (customer uses link from email)

**Alternative considered:** Direct signup without token. Rejected because we need to tie each account to a specific plan tier, max locations, and billing agreement before portal access.

---

## ADR-003: Three Authentication Paths

**Decision:** Support three ways for a business to access their portal:

1. **Email + Password** — standard login for returning users
2. **Access Token** — first-time activation during/after sale
3. **Demo mode** — no auth required, uses client-side mock data

**Why:**
- Path 1 handles 95% of daily logins
- Path 2 handles the critical onboarding moment
- Path 3 lets prospects explore without commitment
- `/demo` routes are always open; `/app` routes require auth; `/portal` is the gate

---

## ADR-004: Business-Scoped Data Namespace

**Decision:** Every data query is scoped to `business_id`. No global queries exist in the customer-facing app.

**Why:**
- Prevents any possibility of data leakage between tenants
- RLS policies on every table enforce this at the DB level
- Application code always passes `business_id` from the auth context
- Demo mode uses a synthetic `org_id = 'demo'` that returns client-side mock data

---

## ADR-005: Role-Based Access (Owner / Manager / Staff)

**Decision:** Three roles per business with decreasing access levels.

**Why:**
- Owner: full access including billing, user management, data upload
- Manager: can see all analytics but cannot change billing or add users
- Staff: can only see their assigned location's performance data
- Keeps the dashboard relevant per role — staff don't need to see billing; managers don't need user management

**Implementation:** `business_users.role` column, checked in the React auth context. RLS policies filter data by role where needed.

---

## ADR-006: Automated Onboarding Pipeline

**Decision:** The onboarding sequence is fully automated from token generation through first insights.

**Why:**
- Reduces time-to-value from days to hours
- No manual engineering work required per customer
- `onboarding_progress` table tracks each step with timestamps
- If any step stalls (e.g., no data upload after 72h), automated alerts trigger

**Sequence:** Token generated → Welcome email → Token redeemed → Portal created → POS connected → Data imported → Agents run → Insights delivered → Customer marked Active

---

## ADR-007: Client-Side Demo Data with Server-Side Production Data

**Decision:** Demo mode generates all data client-side in `demo-data.ts` and `agent-data.ts`. Production mode hits the FastAPI backend which queries Supabase.

**Why:**
- Zero server cost for demos and prospects
- Demo works offline and loads instantly
- Production data flows through proper API with auth headers
- Same React components render both — only the data source changes
- `isDemo(orgId)` check in `api.ts` routes to the correct path

---

## ADR-008: 15-Agent Swarm Triggered on First Data

**Decision:** All 15 AI agents run automatically when a business's first batch of POS data is imported.

**Why:**
- Delivers immediate value — customer sees insights within hours of connecting
- Agents run in dependency order (transaction-analyst first, action-prioritizer last)
- Results stored in the business's isolated data namespace
- Subsequent runs are scheduled (hourly for critical agents, daily for others)

---

## ADR-009: Session Security Model

**Decision:** 24-hour standard sessions, 30-day "Remember Me" sessions, 60-minute inactivity timeout.

**Why:**
- 24h default balances security and convenience for daily users
- 30-day "Remember Me" prevents re-login fatigue for trusted devices
- 60-minute inactivity timeout protects shared/public computers
- "Log out all devices" in settings provides emergency session revocation
- All sessions stored in `customer_sessions` with device info for audit trail

---

## ADR-010: Login Rate Limiting

**Decision:** 5 failed attempts per 15 minutes per email or IP address.

**Why:**
- Prevents brute force attacks
- Per-email protects individual accounts
- Per-IP prevents credential stuffing across accounts
- Implemented as a PostgreSQL function (`check_login_rate_limit`) for server-side enforcement
- `login_attempts` table provides full audit trail

---

## ADR-011: In-Store Vision Intelligence

**Date:** 2026-04-30

**Status:** Accepted (Implemented)

**Decision:** Add computer vision capabilities for foot traffic analytics, dwell time measurement, customer recognition, demographic profiling, and queue monitoring. Processing runs on-premise at the edge; only anonymized metrics flow to Meridian's cloud.

**Why:**
- POS data alone misses the 70% of visitors who browse but don't buy (conversion rate, traffic patterns, dwell time)
- Brick-and-mortar merchants have no equivalent of web analytics — vision fills that gap
- Edge processing keeps video/images on merchant hardware, satisfying privacy requirements
- Competitive advantage: most POS analytics platforms are transaction-only

### Processing Pipeline

```
Camera (RTSP) → YOLO v8 (person detection) → ByteTrack (multi-object tracking)
  → DeepFace (optional: age/gender, repeat visitor embedding)
  → Meridian DB (anonymized metrics only)
```

**Runtime**: CompreFace self-hosted in Docker on merchant edge hardware. No cloud inference.

### Why Edge-First (Not Cloud)

- **Privacy:** Face embeddings stay on the merchant's local network. Only anonymized analytics (counts, demographics, dwell times) are sent to Meridian's cloud.
- **Latency:** Real-time tracking requires <100ms inference. Edge GPU delivers this; cloud roundtrip cannot.
- **Bandwidth:** Streaming raw video to cloud is expensive and unreliable. Processing locally and sending only metadata is 1000x cheaper.
- **Compliance:** GDPR/CCPA require data minimization. Face embeddings never leave the premise.

### Deployment Model: CompreFace on Edge

**Why CompreFace over cloud APIs (AWS Rekognition, Azure Face):**
- Self-hosted = zero per-call cost at scale
- Data sovereignty — face data never leaves merchant's network
- Docker deployment = consistent setup across merchants
- REST API makes integration clean from our processing pipeline
- Supports multiple recognition models (ArcFace, FaceNet, MobileFace)

### Privacy Model

| Mode | What's stored | Embeddings | Use case |
|------|--------------|------------|----------|
| `anonymous` (default) | Aggregate counts only | None | Foot traffic, queue length |
| `opt_in_identity` | Anonymized visit records | On-prem only, 90-day auto-delete | Repeat visitor detection, dwell time |
| `disabled` | Nothing | Nothing | Camera connected but vision off |

**Hard rules:**
- No raw images or video frames are ever stored or transmitted to cloud
- Face embeddings never leave merchant hardware — cloud receives only visit IDs and timestamps
- Consent signage is required in camera field of view (enforced during setup wizard)
- 90-day automatic deletion of all embeddings and visit-level records
- Customer can request immediate deletion (CCPA/GDPR right to erasure)
- `vision_cameras.compliance_mode` field enforces the selected privacy level at the edge

### Camera Integration

**Protocol:** RTSP (Real Time Streaming Protocol) — industry standard for IP cameras.

**Supported cameras:** Any IP camera with RTSP output. Recommended:
- Reolink RLC-810A ($55) — 4K, PoE, RTSP native
- Amcrest IP8M-T2599EW ($70) — 4K, PoE, AI detection built-in
- Hikvision DS-2CD2143G2-I ($90) — enterprise grade

### Database Schema (4 tables — implemented)

```sql
-- Camera registration and health
CREATE TABLE vision_cameras (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    location_id     UUID REFERENCES locations(id),
    name            TEXT NOT NULL,
    rtsp_url        TEXT NOT NULL,                    -- encrypted at rest
    zone_config     JSONB DEFAULT '{}',              -- drawn zones (entry, checkout, browse)
    compliance_mode TEXT NOT NULL DEFAULT 'anonymous', -- anonymous | opt_in_identity | disabled
    active_hours    JSONB DEFAULT '{}',              -- {"start": "07:00", "end": "22:00"}
    status          TEXT NOT NULL DEFAULT 'offline',  -- online | offline | error
    last_heartbeat  TIMESTAMPTZ,
    edge_device_id  TEXT,                            -- Jetson serial number
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Anonymized visitor sessions (opt_in_identity mode only)
CREATE TABLE vision_visitors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    embedding_hash  TEXT NOT NULL,                    -- SHA-256 of on-prem embedding (NOT the embedding itself)
    first_seen      TIMESTAMPTZ NOT NULL,
    last_seen       TIMESTAMPTZ NOT NULL,
    visit_count     INTEGER DEFAULT 1,
    demographic     JSONB DEFAULT '{}',              -- {"age_range": "25-34", "gender_est": "F"}
    expires_at      TIMESTAMPTZ NOT NULL             -- 90-day auto-delete
);

-- Individual visit records
CREATE TABLE vision_visits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    visitor_id      UUID REFERENCES vision_visitors(id) ON DELETE SET NULL,
    camera_id       UUID NOT NULL REFERENCES vision_cameras(id),
    entered_at      TIMESTAMPTZ NOT NULL,
    exited_at       TIMESTAMPTZ,
    dwell_seconds   INTEGER,
    zones_visited   TEXT[],                          -- ["entry", "browse", "checkout"]
    converted       BOOLEAN DEFAULT FALSE,           -- matched to a POS transaction?
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Aggregated traffic metrics (TimescaleDB hypertable for time-series queries)
CREATE TABLE vision_traffic (
    org_id          UUID NOT NULL REFERENCES organizations(id),
    location_id     UUID REFERENCES locations(id),
    camera_id       UUID NOT NULL REFERENCES vision_cameras(id),
    bucket          TIMESTAMPTZ NOT NULL,            -- 15-minute intervals
    entries         INTEGER DEFAULT 0,
    exits           INTEGER DEFAULT 0,
    occupancy_avg   FLOAT DEFAULT 0,
    occupancy_peak  INTEGER DEFAULT 0,
    queue_length_avg FLOAT DEFAULT 0,
    queue_wait_avg_sec FLOAT DEFAULT 0,
    conversion_rate FLOAT DEFAULT 0,
    demographic_breakdown JSONB DEFAULT '{}',
    PRIMARY KEY (org_id, camera_id, bucket)
);
```

**RLS:** All tables enforce `org_id = auth.uid()` — same pattern as existing tables.

### 5 New AI Agents

| Agent | Tier | Input | Output |
|-------|------|-------|--------|
| `foot_traffic` | 1 | `vision_traffic` | Hourly/daily footfall, entry patterns, conversion rate vs POS transactions |
| `dwell_time` | 2 | `vision_visits` | Average dwell by zone, zone flow heatmaps, browse-to-buy funnel |
| `customer_recognizer` | 2 | `vision_visitors` | Repeat visitor frequency, new vs returning ratio, loyalty without a card |
| `demographic_profiler` | 3 | `vision_visitors.demographic` | Age/gender distribution, segment-specific conversion rates, daypart demographics |
| `queue_monitor` | 1 | `vision_traffic.queue_*` | Real-time queue length, wait time estimates, staffing alert triggers |

**Agent integration:** Agents follow existing 3-phase pattern (DataAvailability → path selection → dynamic calculation). Vision agents are Tier 1-3 and run in the same `asyncio.gather` swarm as existing agents. They contribute to `money_left` score: "You're losing $X/month from long queue wait times" etc.

### Hardware Requirements

| Tier | Device | Cost | Cameras | FPS | Use Case |
|------|--------|------|---------|-----|----------|
| Basic | Jetson Nano (8GB) | $149 | 2-3 | 10 | Small shop, single entrance |
| Standard | Jetson Orin Nano | $249 | 4-6 | 15 | Restaurant, multiple zones |
| Premium | Jetson Orin NX | $499 | 8-12 | 30 | Large retail, full coverage |

Edge software is containerized (Docker Compose): CompreFace + YOLO + ByteTrack + Meridian edge agent. Auto-updates via Watchtower.

### Frontend: "Connect Cameras" Button

**Location:** Customer Intelligence page, top-right action area.

**States:**

1. **No cameras connected:**
   - Button: `[Camera icon] Connect Cameras`
   - Click → Setup Wizard modal (5 steps: Device → Camera → Zones → Privacy → Confirm)

2. **Cameras connected and live:**
   - Badge: `[Green dot] 3 cameras • Live`
   - Click → Camera management panel

3. **Camera offline:**
   - Badge: `[Yellow warning] 2 of 3 cameras offline`
   - Click → Troubleshooting panel

**Tier gating:** Vision features available on Growth ($250/mo) and Enterprise plans only.

### Libraries (edge only)

| Library | Role | Package |
|---------|------|---------|
| ultralytics | YOLO v8 person detection | `ultralytics` (edge only) |
| ByteTrack | Multi-object tracking | `boxmot` (edge only) |
| DeepFace | Face embedding + demographics | `deepface` (edge only) |
| CompreFace | Self-hosted face API | Docker container (edge only) |
| supervision | Visual analytics toolkit | `supervision` (edge only) |
| insightface | Alternative face embeddings | `insightface` (edge only) |

**Note:** All CV libraries run on edge hardware only. No CV dependencies in the cloud `requirements.txt`.

### Alternatives Considered

**Cloud-based video analytics (AWS Rekognition, Google Cloud Vision):**
- Rejected: $1-4 per 1,000 API calls. A single camera at 1fps = 86,400 calls/day = $86-345/day. Economically impossible for $250/mo merchants.

**No face recognition, just counting (thermal/IR sensors):**
- Rejected: Misses the key insight — repeat vs. new visitors. Counting is commodity. Identity is the moat.

### Trade-offs

- **Edge-first vs cloud:** Edge is harder to manage (firmware updates, hardware failures) but eliminates the privacy/bandwidth problem. Worth it for merchant trust.
- **CompreFace vs raw DeepFace:** Adds Docker complexity but provides face collection CRUD we need without building our own.
- **Anonymous default:** Limits analytics value but dramatically simplifies compliance.
- **90-day auto-delete:** Reduces long-term analytics but keeps us CCPA/GDPR safe by default. Aggregate metrics in `vision_traffic` retained indefinitely (no PII).

### Implementation Order

1. Database migrations (4 tables + RLS policies + hypertable)
2. Edge agent Docker image (YOLO + ByteTrack + heartbeat)
3. `vision_traffic` agent + `/api/vision/traffic/{org_id}` endpoint
4. `queue_monitor` agent + real-time alerting
5. Frontend: Connect Cameras wizard + traffic dashboard
6. DeepFace integration (opt_in_identity mode)
7. `dwell_time`, `customer_recognizer`, `demographic_profiler` agents
8. Frontend: Customer Intelligence page with vision data
# ADR-012: Cline — Self-Healing IT Agent + Karpathy Reasoning Framework

## Status: Proposed
## Date: 2026-05-01
## Authors: Viktor AI, Aidan Pierce

---

## Context

Meridian business owners (restaurant/retail operators) are not technical. When something goes wrong — a dashboard page fails to load, a POS sync stalls, an agent produces stale data — they have no way to fix it. Today, they'd need to contact IT, file a ticket, and wait. This is unacceptable for a premium analytics platform.

We also want our 27 AI agents to reason more deeply about their analyses — not just pattern-match, but think step-by-step like a researcher. Inspired by Andrej Karpathy's autoresearch loop architecture, we'll embed a structured reasoning framework into every agent.

## Decision

### Part 1: Cline — The Self-Healing IT Agent

A persistent, always-on AI agent embedded in the Meridian dashboard that:
1. **Detects errors** before the business owner even notices
2. **Auto-patches** what it can (config, cache, retry, resync)
3. **Communicates** with the owner in plain English
4. **Escalates** to the Meridian IT team only when necessary

#### Architecture

```
┌─────────────────────────────────────────────────┐
│                  Business Owner                  │
│              "Hey, my revenue page               │
│               isn't loading today"                │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│              Cline Chat Widget                   │
│        (floating button, every page)             │
│                                                  │
│  • Natural language conversation                 │
│  • Screenshot capture (owner can paste image)    │
│  • Error context auto-attached                   │
│  • Proactive alerts pushed to owner              │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│           Cline Reasoning Engine                 │
│        (Karpathy-style deep thinking)            │
│                                                  │
│  THINK → PLAN → ACT → OBSERVE → REFLECT         │
│                                                  │
│  1. THINK: What is the root cause?               │
│  2. PLAN: What remediation steps exist?           │
│  3. ACT: Execute the safest fix                  │
│  4. OBSERVE: Did the fix work?                   │
│  5. REFLECT: What should we learn?               │
└─────────────┬───────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────┐
│           Remediation Actions                    │
│                                                  │
│  Level 1 — Auto-Fix (no human needed):           │
│    • Clear stale cache / retry failed request    │
│    • Re-trigger POS sync                         │
│    • Restart failed agent run                    │
│    • Reset user session                          │
│    • Fix corrupt/missing data records            │
│                                                  │
│  Level 2 — Fix + Notify:                         │
│    • Patch config values                         │
│    • Adjust agent parameters                     │
│    • Re-run full analysis pipeline               │
│    • Log + notify IT dashboard                   │
│                                                  │
│  Level 3 — Escalate to IT:                       │
│    • Create GitHub issue with repro steps        │
│    • Suggest code fix in issue body              │
│    • Alert IT team via Slack/webhook             │
│    • Provide full diagnostic bundle              │
│                                                  │
│  Level 4 — Page Human:                           │
│    • PagerDuty/SMS alert to on-call engineer     │
│    • Include all context + attempted fixes       │
└─────────────────────────────────────────────────┘
```

#### Error Detection Sources

| Source | What It Catches | Collection Method |
|--------|----------------|-------------------|
| Frontend Error Boundary | React crashes, white screens | `window.onerror` + ErrorBoundary component |
| Console Error Interceptor | JS errors, failed imports | `console.error` override |
| Network Monitor | Failed API calls, timeouts, 4xx/5xx | `fetch` wrapper + Highlight.io |
| Agent Health Monitor | Stale/failed agent runs | Cron check on `agent_runs` table |
| POS Sync Watchdog | Sync failures, stale data | Celery task monitoring |
| Performance Monitor | Slow page loads, memory leaks | Performance Observer API |
| User Behavior | Rage clicks, rapid refreshes | PostHog + custom events |

#### Database Schema

```sql
-- Cline conversation history
CREATE TABLE cline_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    user_id UUID REFERENCES auth.users(id),
    started_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    status TEXT DEFAULT 'open', -- open, resolved, escalated
    satisfaction_rating INT, -- 1-5 after resolution
    summary TEXT
);

-- Individual messages in a Cline conversation
CREATE TABLE cline_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES cline_conversations(id),
    role TEXT NOT NULL, -- 'user', 'cline', 'system'
    content TEXT NOT NULL,
    thinking TEXT, -- Karpathy-style inner monologue (hidden from user)
    attachments JSONB DEFAULT '[]', -- screenshots, error logs
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Auto-detected errors
CREATE TABLE cline_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    error_type TEXT NOT NULL, -- 'frontend', 'api', 'agent', 'sync', 'performance'
    severity TEXT DEFAULT 'medium', -- low, medium, high, critical
    source TEXT, -- page URL, agent name, endpoint
    error_message TEXT,
    stack_trace TEXT,
    context JSONB DEFAULT '{}',
    remediation_level INT, -- 1-4
    remediation_action TEXT,
    remediation_result TEXT, -- 'success', 'failed', 'escalated'
    detected_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

-- IT Dashboard aggregate health
CREATE TABLE merchant_health (
    org_id UUID PRIMARY KEY REFERENCES organizations(id),
    health_score INT DEFAULT 100, -- 0-100
    open_errors INT DEFAULT 0,
    auto_fixed_today INT DEFAULT 0,
    escalated_today INT DEFAULT 0,
    last_sync_at TIMESTAMPTZ,
    last_agent_run_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### Frontend Components

1. **ClineChatWidget** — Floating button (bottom-right), expands to chat panel
   - Auto-attaches current page URL, recent console errors, user context
   - Owner types in plain English
   - Cline responds with diagnosis + fix status
   - "Was this helpful?" rating after resolution

2. **ClineProactiveAlert** — Toast notification
   - "I noticed your Square sync hasn't run in 6 hours. I'm restarting it now."
   - "Your revenue forecast agent found unusual data — I'm re-running with cleaned inputs."

3. **ITDashboard** — Admin-only page (`/admin/it-health`)
   - Health scores per merchant
   - Error timeline
   - Auto-fix success rate
   - Escalation queue
   - Cline conversation history (for IT team review)

### Part 2: Karpathy Reasoning Framework for All Agents

Inspired by Karpathy's autoresearch loop and his emphasis on "thinking before acting," we embed a structured reasoning framework into every Meridian AI agent.

#### The Karpathy Loop

```python
class KarpathyReasoning:
    """
    5-phase reasoning loop for deep analysis.
    Every agent runs this before producing output.
    """
    
    async def reason(self, context: AnalysisContext) -> AgentOutput:
        # Phase 1: THINK — Understand the data landscape
        thinking = await self.think(context)
        # "What patterns exist? What's unusual? What's missing?"
        
        # Phase 2: HYPOTHESIZE — Form testable theories
        hypotheses = await self.hypothesize(thinking, context)
        # "Revenue dropped 15% — could be: seasonal, menu change, competitor, data error"
        
        # Phase 3: EXPERIMENT — Test each hypothesis against data
        experiments = await self.experiment(hypotheses, context)
        # "Seasonal? No — same period last year was flat."
        # "Menu change? Yes — removed top seller 3 days ago."
        
        # Phase 4: SYNTHESIZE — Combine findings into actionable insight
        synthesis = await self.synthesize(experiments, context)
        # "Revenue dropped because item X was removed. It was 12% of sales."
        
        # Phase 5: REFLECT — Meta-cognition
        reflection = await self.reflect(synthesis, context)
        # "Confidence: HIGH. Data quality: GOOD. Suggestion: restore item X."
        # "What I might be wrong about: could also be a POS reporting delay."
        
        return AgentOutput(
            data=synthesis.findings,
            thinking=thinking.inner_monologue,  # Stored but hidden from dashboard
            confidence=reflection.confidence,
            caveats=reflection.caveats,
            reasoning_chain=self._build_chain(thinking, hypotheses, experiments, synthesis, reflection),
        )
```

#### Agent System Prompt Template (Karpathy-Enhanced)

```
You are {agent_name}, a specialized Meridian AI agent for {domain}.

## Reasoning Protocol (MANDATORY)

Before producing ANY output, you MUST complete all 5 phases:

### Phase 1: THINK (Inner Monologue)
- What data am I looking at? How much? What time range?
- What's the baseline/expected behavior?
- What immediately stands out? What DOESN'T stand out but should?
- What data quality issues might affect my analysis?
- Rate data quality: EXCELLENT / GOOD / FAIR / POOR / INSUFFICIENT

### Phase 2: HYPOTHESIZE
- Generate at least 3 competing hypotheses for any significant finding
- Rank hypotheses by prior probability
- Identify what evidence would confirm/refute each
- Include at least 1 "null hypothesis" (nothing is actually wrong)

### Phase 3: EXPERIMENT
- Test each hypothesis against the actual data
- Use specific numbers, not vague trends
- Cross-reference with other data sources when available
- Document which hypotheses survived and which were eliminated

### Phase 4: SYNTHESIZE
- Combine surviving hypotheses into a coherent narrative
- Quantify impact: revenue, customers, time, percentage
- Generate specific, actionable recommendations
- Rank recommendations by expected impact and effort

### Phase 5: REFLECT (Meta-Cognition)
- Confidence level: HIGH / MEDIUM / LOW
- What could I be wrong about?
- What additional data would increase my confidence?
- What assumptions am I making?
- If my confidence is LOW, say so explicitly — never fake certainty

## Output Format
Provide your analysis in structured JSON with ALL phases documented.
The 'thinking' field contains your full inner monologue (Phases 1-3).
The 'data' field contains your synthesized findings (Phase 4).
The 'confidence' and 'caveats' fields contain your reflection (Phase 5).

NEVER skip phases. NEVER produce output without reasoning. Think deeply.
```

#### Benefits

1. **Transparency** — Every insight has a reasoning chain. If an owner asks "why did you recommend this?", the chain is right there.
2. **Accuracy** — Forced hypothesis testing catches false positives. Agents that consider "maybe nothing is wrong" produce fewer false alarms.
3. **Learning** — Stored reasoning chains become training data. Over time, agents get better at each domain.
4. **Debugging** — When an agent is wrong, the reasoning chain shows exactly where the logic broke down.
5. **Trust** — Business owners see that the AI actually "thought about it" rather than pattern-matching.

## Consequences

### Positive
- Business owners get instant IT support without calling anyone
- Error resolution time drops from hours/days to seconds/minutes
- Meridian appears "intelligent" — it fixes itself and communicates
- IT team focuses on real issues, not "my page won't load" tickets
- Agent outputs become dramatically more reliable and trustworthy
- Reasoning chains provide audit trail for compliance-heavy industries

### Negative
- Cline's auto-fix actions need careful guardrails to prevent cascading failures
- Karpathy reasoning adds ~2-3x to agent token usage (but dramatically improves quality)
- Need to handle the edge case where Cline itself has a bug
- IT dashboard is a new surface to maintain

### Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| Cline auto-fix breaks something worse | Rollback mechanism + dry-run mode for Level 2+ |
| Owner confused by Cline responses | Keep language simple, offer "Talk to a human" escape hatch |
| Token cost increase from reasoning | Cache reasoning chains, use cheaper models for repeat patterns |
| Privacy — IT team sees owner conversations | RBAC scoping, audit logs on admin access |

---

## ADR-011-v2: Advanced Vision Intelligence — Palantir-Grade Customer Tracking & Insights

### Status: Approved (supersedes ADR-011 camera section)
### Date: 2026-05-01

### Context

ADR-011 established the foundation for in-store vision intelligence. This revision specifies the exact repository stack, camera topology, and analytics pipeline to deliver Palantir-grade customer tracking: passerby counting, walk-in conversion, gender/age demographics, repeat vs first-time detection, non-customer identification, and sentiment analysis.

### Camera Topology

```
                    ┌──────────────────────────┐
                    │      SIDEWALK/STREET      │
                    │                           │
                    │   Camera 1 (Exterior)     │
                    │   ● Passerby counting     │
                    │   ● Window shoppers        │
                    │   ● "Looked but didn't    │
                    │     enter" detection       │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │       ENTRANCE            │
                    │                           │
                    │   Camera 2 (Door)         │
                    │   ● Entry/exit counting   │
                    │   ● Face capture (best    │
                    │     quality, eye-level)    │
                    │   ● Repeat detection      │
                    │   ● Gender/age/emotion    │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼──────────┐ ┌────────▼──────────┐ ┌────────▼──────────┐
│   ZONE A (Bar)     │ │   ZONE B (Tables) │ │   ZONE C (Menu)   │
│                    │ │                   │ │                   │
│   Camera 3+        │ │   Camera 4+        │ │   Camera 5+        │
│   ● Dwell time     │ │   ● Dwell time    │ │   ● Dwell time    │
│   ● Path tracking  │ │   ● Group size    │ │   ● Conversion    │
│   ● Heatmap        │ │   ● Sentiment     │ │     (looked at    │
│                    │ │                   │ │      menu→ordered) │
└────────────────────┘ └───────────────────┘ └───────────────────┘
```

### Technology Stack (Final Selections)

| Layer | Repository | Stars | Role |
|-------|-----------|-------|------|
| Person Detection | `ultralytics/ultralytics` (YOLOv8) | 40K+ | Detect people in every frame |
| Multi-Object Tracking | `mikel-brostrom/boxmot` | 8.1K | Track person across frames, assign track IDs |
| Face Recognition | `deepinsight/insightface` (ArcFace/buffalo_l) | 25K+ | Primary face matching engine (99.8% accuracy) |
| Face Analysis | `serengil/deepface` | 22.6K | Age, gender, emotion, ethnicity classification |
| Zone Analytics | `roboflow/supervision` | 25K+ | Zone crossing, counting, heatmaps, dwell time |
| Cross-Camera ReID | `mikel-brostrom/boxmot` ReID module | — | Re-identify same person across different cameras |
| Identity Graph | `apache/age` (Postgres extension) | 3K+ | Customer knowledge graph on Supabase |
| Edge Processing | NVIDIA Jetson / Raspberry Pi 5 | — | All inference on-premises |

### Analytics Pipeline

```
Frame (30fps) ──┬──▶ YOLOv8 Person Detection
                │      └──▶ BoxMOT Multi-Object Tracking
                │             └──▶ Track ID per person per frame
                │
                ├──▶ InsightFace ArcFace (every 5th frame per track)
                │      └──▶ 512-dim face embedding
                │      └──▶ Match against customer_embeddings table
                │      └──▶ Result: known_customer | returning_anonymous | new_face
                │
                ├──▶ DeepFace Analysis (on first clear face per track)
                │      └──▶ age_range, gender, dominant_emotion
                │
                └──▶ Supervision Zone Analytics
                       └──▶ zone_entered, zone_exited, dwell_seconds
                       └──▶ path_coordinates (for heatmap)
                       └──▶ zone_crossing_events (sidewalk→door→interior)

Every 60 seconds, edge device sends batch to cloud:
{
  "store_id": "...",
  "window_start": "2026-05-01T14:00:00Z",
  "window_end": "2026-05-01T14:01:00Z",
  "passerby_count": 34,
  "window_shoppers": 8,      // looked toward store, slowed down
  "walk_ins": 5,              // crossed door zone
  "walk_outs": 3,
  "demographics": {
    "male": 18, "female": 14, "unknown": 2,
    "age_buckets": {"18-25": 6, "26-35": 12, "36-50": 10, "51+": 6}
  },
  "returning_customers": 2,   // face matched from previous visits
  "new_faces": 3,
  "avg_dwell_seconds": {"entrance": 4.2, "bar": 840, "tables": 1200, "menu": 22},
  "zone_heatmap": [[x, y, intensity], ...],
  "sentiment_snapshot": {"happy": 3, "neutral": 1, "surprised": 1},
  "tracks": [
    {
      "track_id": "t-4782",
      "embedding_hash": "abc123",
      "is_returning": true,
      "visit_number": 14,
      "gender": "female",
      "age_range": "26-35",
      "emotion_at_entry": "happy",
      "emotion_at_exit": "neutral",
      "zones_visited": ["entrance", "menu", "bar"],
      "total_dwell_seconds": 2520,
      "matched_pos_transaction": "$47.50"
    }
  ]
}
```

### Database Schema Additions

```sql
-- Passerby / foot traffic events
CREATE TABLE foot_traffic (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    camera_id UUID REFERENCES cameras(id),
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    passerby_count INT DEFAULT 0,
    window_shoppers INT DEFAULT 0,
    walk_ins INT DEFAULT 0,
    walk_outs INT DEFAULT 0,
    male_count INT DEFAULT 0,
    female_count INT DEFAULT 0,
    age_buckets JSONB DEFAULT '{}',
    returning_count INT DEFAULT 0,
    new_face_count INT DEFAULT 0,
    non_customer_count INT DEFAULT 0,    -- entered but no POS match
    sentiment_summary JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Individual customer profiles (anonymous until opt-in)
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    embedding_hash TEXT NOT NULL,         -- hash of face embedding (not the embedding itself)
    visit_count INT DEFAULT 1,
    first_seen_at TIMESTAMPTZ DEFAULT now(),
    last_seen_at TIMESTAMPTZ DEFAULT now(),
    avg_dwell_seconds FLOAT DEFAULT 0,
    favorite_zone TEXT,
    visit_pattern JSONB DEFAULT '{}',     -- {"weekday_counts": {}, "hour_counts": {}}
    gender TEXT,                           -- male/female/unknown
    age_range TEXT,                        -- "26-35"
    avg_sentiment TEXT,                    -- happy/neutral/negative
    total_pos_spend FLOAT DEFAULT 0,      -- linked from POS if opted in
    predicted_ltv FLOAT DEFAULT 0,
    is_opted_in BOOLEAN DEFAULT false,    -- linked to loyalty/name
    opted_in_name TEXT,
    opted_in_email TEXT,
    tags TEXT[] DEFAULT '{}',             -- VIP, regular, window_shopper, etc.
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Visit log per customer
CREATE TABLE customer_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID REFERENCES customer_profiles(id),
    org_id UUID REFERENCES organizations(id),
    entered_at TIMESTAMPTZ NOT NULL,
    exited_at TIMESTAMPTZ,
    dwell_seconds INT,
    zones_visited TEXT[],
    emotion_at_entry TEXT,
    emotion_at_exit TEXT,
    pos_transaction_id TEXT,              -- linked POS sale if any
    pos_amount_cents INT,
    was_window_shopper BOOLEAN DEFAULT false,  -- looked but didn't enter
    converted_later BOOLEAN DEFAULT false,     -- window shopped, came back later
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Insights generated by Karpathy reasoning
CREATE TABLE vision_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    insight_type TEXT NOT NULL,           -- conversion, demographic, timing, sentiment, loyalty
    title TEXT NOT NULL,                  -- "21 people looked in but didn't enter"
    body TEXT NOT NULL,                   -- full analysis
    data JSONB DEFAULT '{}',
    confidence TEXT DEFAULT 'MEDIUM',
    reasoning_chain_id UUID,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Apache AGE graph for identity resolution
-- (run after installing AGE extension)
-- SELECT create_graph('customer_graph');
-- Nodes: Customer, Visit, Zone, Transaction, TimeSlot
-- Edges: VISITED, BOUGHT, DWELLED_IN, RETURNED_AFTER, CONVERTED_FROM_WINDOW
```

### Insight Examples (Generated by Karpathy Reasoning Agents)

```
📊 "21 people looked into your store between 12-2pm but didn't walk in.
    12 were women aged 25-35. Your lunch menu sign isn't visible from the sidewalk."

🔄 "Customer #4782 has visited 14 times (every Fri/Sat). Average spend $47.
    Last 2 visits she seemed less happy (neutral vs usual happy).
    She hasn't been in for 9 days — longest gap in 3 months. Risk of churn."

📈 "Walk-in conversion rate: 14.7% (up from 11.2% last month).
    The new A-frame sign you added is working — window shoppers converting 31% more."

👥 "Tuesday evenings are 73% male, 26-35. Friday nights flip to 58% female, 21-30.
    Your Tuesday cocktail menu doesn't match Tuesday's demographic."

⏱️ "Average dwell time dropped from 52min to 38min this week.
    Customers spending 22% less time at tables. Possible causes:
    service speed changed, or ambient temp (it hit 95°F this week)."

🆕 "You had 34 first-time visitors this week (up 15%).
    But only 8 came back for a second visit (23% retention).
    Industry benchmark is 35% — consider a first-visit loyalty offer."
```
