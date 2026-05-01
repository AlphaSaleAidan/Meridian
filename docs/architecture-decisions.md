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

**Decision:** Add computer vision capabilities for foot traffic analytics, dwell time measurement, customer recognition, demographic profiling, and queue monitoring. Processing runs on-premise at the edge; only anonymized metrics flow to Meridian's cloud.

**Why:**
- POS data alone misses the 70% of visitors who browse but don't buy (conversion rate, traffic patterns, dwell time)
- Brick-and-mortar merchants have no equivalent of web analytics — vision fills that gap
- Edge processing keeps video/images on merchant hardware, satisfying privacy requirements
- Competitive advantage: most POS analytics platforms are transaction-only

### Processing Pipeline (v2 — Palantir-Grade)

```
Camera (RTSP)
  → YOLO v8 nano (person detection, bounding boxes)
  → BoxMOT/DeepOCSORT (multi-object tracking, persistent track_id)
  → InsightFace ArcFace buffalo_l (512-dim face embeddings, match/recognize)
  → DeepFace (demographics: age, gender, emotion)
  → Supervision (zone polygons, crossings, dwell time, heatmaps)
  → Apache AGE (customer identity graph in Postgres)
  → Karpathy Reasoning ("what does this mean for the business?")
  → Meridian DB (anonymized metrics only — embeddings stay on-prem)
```

**Primary face engine:** InsightFace ArcFace (buffalo_l model, 512-dim embeddings). Chosen over DeepFace embeddings for superior accuracy on LFW benchmark (99.83%) and speed (single-pass detection+embedding).

**Graph layer:** Apache AGE (A Graph Extension for PostgreSQL). Customer identity graph lives in the same Supabase Postgres — no separate graph DB needed. Edges model relationships: VISITED_ZONE, PURCHASED_WITH, VISITED_SAME_DAY_AS, RETURNED_AFTER.

**Demographics:** DeepFace handles age/gender/emotion classification only (not embeddings). Runs on face crops extracted by InsightFace.

**Runtime**: Edge Docker stack (YOLO + BoxMOT + InsightFace + DeepFace + Supervision). No cloud inference.

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

### Database Schema (4 new tables)

```sql
-- Camera registration and health
CREATE TABLE vision_cameras (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id),
    location_id     UUID REFERENCES locations(id),
    name            TEXT NOT NULL,                    -- "Front Door", "Checkout Area"
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
    conversion_rate FLOAT DEFAULT 0,                 -- entries that led to POS transaction
    demographic_breakdown JSONB DEFAULT '{}',
    PRIMARY KEY (org_id, camera_id, bucket)
);
-- SELECT create_hypertable('vision_traffic', 'bucket');
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

### Frontend: "Connect Cameras" Button Spec

**Location:** Customer Intelligence page, top-right action area (next to existing "Connect POS" button)

**States:**

1. **No cameras connected:**
   - Button: `[Camera icon] Connect Cameras`
   - Click → Setup Wizard modal:
     - Step 1: Select edge device (auto-detect or manual)
     - Step 2: Add camera (RTSP URL, test connection, name it)
     - Step 3: Draw zones on preview frame (entry, checkout, browse areas)
     - Step 4: Set active hours and compliance mode
     - Step 5: Confirm consent signage placement → activate

2. **Cameras connected and live:**
   - Badge: `[Green dot] 3 cameras • Live`
   - Click → Camera management panel (status, zone editor, compliance settings)

3. **Camera offline:**
   - Badge: `[Yellow warning] 2 of 3 cameras offline`
   - Click → Troubleshooting panel (last heartbeat, connection test, edge device status)

**Tier gating:** Vision features available on Growth ($250/mo) and Enterprise plans only. Trial/Starter see a locked preview with sample data.

### Libraries (Locked-In Choices)

| Library | Role | Package | Status |
|---------|------|---------|--------|
| ultralytics | YOLO v8 nano person detection | `ultralytics` (edge only) | **Primary** |
| BoxMOT | DeepOCSORT multi-object tracking | `boxmot` (edge only) | **Primary** — replaces ByteTrack |
| InsightFace | ArcFace buffalo_l 512-dim face embeddings | `insightface` (edge only) | **Primary face engine** |
| DeepFace | Demographics only (age, gender, emotion) | `deepface` (edge only) | **Secondary** — demographics only |
| supervision | Zone analytics, heatmaps, counting | `supervision` (edge only) | **Primary** |
| Apache AGE | Customer identity graph in Postgres | `age` (Postgres extension) | **Primary graph layer** |
| httpx | Async batch upload from edge | `httpx` (edge only) | **Transport** |
| opencv | Frame capture from RTSP | `opencv-python-headless` (edge only) | **Capture** |

**Note:** All CV libraries run on edge hardware only. The Meridian cloud backend receives only structured metrics via the edge agent's HTTPS push. No CV dependencies in the cloud `requirements.txt`. Apache AGE runs as a Postgres extension in Supabase.

### Trade-offs

- **Edge-first vs cloud:** Edge is harder to manage (firmware updates, hardware failures) but eliminates the privacy/bandwidth problem of streaming video to cloud. Worth it for merchant trust.
- **CompreFace vs raw DeepFace:** CompreFace adds a REST API layer with collection management, but adds Docker complexity. Chose it because it provides the face collection CRUD we need without building our own.
- **Anonymous default:** Limits analytics value (no repeat visitor tracking) but dramatically simplifies compliance. Merchants who want identity features explicitly opt in.
- **90-day auto-delete:** Reduces long-term analytics but keeps us CCPA/GDPR safe by default. Aggregate metrics in `vision_traffic` are retained indefinitely since they contain no PII.

### Customer Profile Builder (Layer 4)

Each recognized face gets an indexed profile that grows over time:

```
Customer #4782 (anonymous until opt-in)
├── Visit count: 14
├── Avg dwell time: 42 min
├── Favorite zone: Bar area (68% of time)
├── Visit pattern: Fri/Sat evenings, 7-10pm
├── Estimated age: 28-35
├── Sentiment trend: happy → happy → neutral (last visit neutral)
├── Spend correlation: $47 avg (from POS data)
└── Predicted LTV: $2,340/year
```

**Privacy model:**
- Cameras detect faces but store only anonymous 512-dim embeddings by default
- Identity linking: Only when customer opts in (loyalty program, QR scan) does face → name
- Right to forget: One click deletes all face embeddings for a customer
- Consent signage: Auto-generated signs for the store ("This location uses AI analytics")
- Data retention: Embeddings auto-purge after configurable period (90 days default)

### Vision Insights Matrix (20 Insights)

| # | Insight | How We Build It | Stack |
|---|---------|----------------|-------|
| 1 | **Passerby count** — "21 people looked in but didn't walk in" | Sidewalk camera + YOLO person detection + Supervision zone crossing (sidewalk → did NOT cross door zone) | YOLO + Supervision |
| 2 | **Walk-in conversion** — "38% of passersby entered today" | Zone crossing: sidewalk→entrance events / total sidewalk detections | Supervision zones |
| 3 | **Men vs Women breakdown** | DeepFace gender classification on every detected person | DeepFace |
| 4 | **Age demographic split** | DeepFace age estimation bucketed into ranges (18-24, 25-34, etc.) | DeepFace |
| 5 | **Peak foot traffic times** | Hourly person count aggregation from YOLO + BoxMOT tracking | YOLO + BoxMOT |
| 6 | **Repeat vs first-time visitors** | InsightFace ArcFace embeddings matched against on-prem customer index | InsightFace |
| 7 | **Non-customers (browsed, didn't buy)** | Face seen by camera but no matching POS transaction in time window | InsightFace + POS correlation |
| 8 | **Window shoppers who later convert** | "Looked in Tuesday, came in Friday" via embedding match over time | InsightFace + temporal matching |
| 9 | **Dwell time by zone** | Supervision zone tracking per track_id (bar, entrance, menu board, etc.) | BoxMOT + Supervision |
| 10 | **Sentiment at entry vs exit** | DeepFace emotion detection comparing first and last detection per visit | DeepFace |
| 11 | **Queue length + wait time** | Person count in checkout zone over time, correlated with POS transaction timestamps | YOLO + Supervision + POS |
| 12 | **Staff-to-customer ratio** | Detect staff (uniform/badge zone) vs customers, alert when ratio drops below threshold | YOLO + zone classification |
| 13 | **Menu board engagement** | Dwell time in menu_board zone — how long do people stare at the menu before ordering? | Supervision zone dwell |
| 14 | **Group size detection** | Track proximity clustering — solo, pair, group (3+), family (mixed age) | BoxMOT + DeepFace age |
| 15 | **Table turnover rate** | Dwell time in table zones: seated→departed cycles per table area per hour | Supervision zone timing |
| 16 | **Loyalty without a card** | Repeat visitor frequency + spend correlation via POS match, no physical card needed | InsightFace + POS |
| 17 | **Lost customer alerts** | Regular visitor (4+ visits) not seen in 2+ weeks → churn risk notification | InsightFace temporal + alerting |
| 18 | **Zone flow heatmaps** | Aggregate movement paths across all tracks → visual heatmap overlay | Supervision + numpy |
| 19 | **Daypart demographics** | Which age/gender groups visit at which hours? Lunch crowd vs dinner crowd profiling | DeepFace + temporal bucketing |
| 20 | **Cross-location visitor overlap** | Same embedding hash seen at multiple locations → multi-location customer mapping | InsightFace + Apache AGE graph |

### Customer Graph (Apache AGE)

```cypher
-- Customer identity graph in Postgres via Apache AGE
SELECT * FROM cypher('meridian', $$
  MATCH (c:Customer {hash: '4a7b2c...'})-[:VISITED]->(z:Zone)
  RETURN z.name, count(*) AS visits
  ORDER BY visits DESC
$$) AS (zone agtype, visits agtype);

-- Find customers who visit the same zones
SELECT * FROM cypher('meridian', $$
  MATCH (c1:Customer)-[:VISITED]->(z:Zone)<-[:VISITED]-(c2:Customer)
  WHERE c1 <> c2
  RETURN c1.hash, c2.hash, collect(z.name) AS shared_zones
$$) AS (c1 agtype, c2 agtype, zones agtype);
```

Graph edges:
- `VISITED_ZONE` — customer→zone with timestamp + dwell
- `PURCHASED` — customer→product (from POS correlation)
- `VISITED_SAME_DAY_AS` — customer→customer (co-occurrence)
- `RETURNED_AFTER` — customer→self (gap between visits)

### Implementation Order

1. Database migrations (4 tables + RLS policies + hypertable)
2. Edge vision engine (detector, tracker, face engine, zones, pipeline)
3. Edge agent Docker image (YOLO + BoxMOT + InsightFace + heartbeat)
4. `vision_traffic` agent + `/api/vision/traffic/{org_id}` endpoint
5. `queue_monitor` agent + real-time alerting
6. Frontend: Connect Cameras wizard + traffic dashboard
7. InsightFace/DeepFace integration (opt_in_identity mode)
8. Apache AGE graph schema + customer profile builder
9. `dwell_time`, `customer_recognizer`, `demographic_profiler` agents
10. Frontend: Customer Intelligence page with vision data
11. Cross-location visitor mapping + advanced graph queries
