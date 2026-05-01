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

## ADR-011: In-Store Vision Intelligence (Camera-Based Customer Tracking)

**Date:** 2026-04-30

**Status:** Accepted

**Decision:** Add a camera-based customer tracking system that enables face recognition, foot traffic analytics, dwell time analysis, demographic insights, and queue monitoring for merchants with physical locations.

### Architecture

```
In-Store Cameras (RTSP/USB/IP)
    ↓ Stream
Edge Processing Node (merchant's network)
    ├── YOLOv8 (person detection)
    ├── ByteTrack/BoxMOT (multi-object tracking)
    └── DeepFace/InsightFace (face embedding + demographics)
    ↓ API (encrypted)
Meridian Backend (FastAPI)
    ↓ Store
Supabase (vision_customers, vision_visits, vision_zones, vision_traffic)
    ↓ Analyze
AI Agents (5 new agents)
    ↓ Display
React Dashboard → Customer Intelligence page
```

### Why Edge-First (Not Cloud)

- **Privacy:** Face embeddings stay on the merchant's local network. Only anonymized analytics (counts, demographics, dwell times) are sent to Meridian's cloud.
- **Latency:** Real-time tracking requires <100ms inference. Edge GPU delivers this; cloud roundtrip cannot.
- **Bandwidth:** Streaming raw video to cloud is expensive and unreliable. Processing locally and sending only metadata is 1000x cheaper.
- **Compliance:** GDPR/CCPA require data minimization. Face embeddings never leave the premise.

### Deployment Model: CompreFace on Edge

**Decision:** Use CompreFace (self-hosted Docker) as the face recognition API running on the merchant's local hardware.

**Why CompreFace over cloud APIs (AWS Rekognition, Azure Face):**
- Self-hosted = zero per-call cost at scale
- Data sovereignty — face data never leaves merchant's network
- Docker deployment = consistent setup across merchants
- REST API makes integration clean from our processing pipeline
- Supports multiple recognition models (ArcFace, FaceNet, MobileFace)

**Hardware requirements (per location):**
- Minimum: NVIDIA Jetson Nano ($149) — handles 2-3 cameras at 15fps
- Recommended: NVIDIA Jetson Orin Nano ($249) — handles 4-6 cameras at 30fps
- Alternative: Any Linux box with NVIDIA GPU (GTX 1060+) or Apple Silicon Mac

### Privacy & Consent Model

**This is non-negotiable. Every feature must respect these rules:**

1. **Opt-in signage required.** Merchants must display a clearly visible sign: _"This business uses camera-based analytics. By entering, you consent to anonymous visit tracking. No personally identifiable images are stored."_

2. **No image storage.** Raw camera frames are never saved to disk or cloud. Only 512-dimensional face embeddings (cannot be reversed to a face) are stored locally.

3. **Anonymized by default.** Cloud analytics only receive: visitor count, estimated age range, estimated gender, dwell time per zone, queue length. No embeddings. No images.

4. **Customer opt-in for identity.** If a merchant wants to link face embeddings to customer names/loyalty accounts, the customer must explicitly opt in (e.g., sign up at a kiosk). Without opt-in, visitors are tracked as anonymous recurring IDs.

5. **Data retention:** Face embeddings auto-delete after 90 days of no visits. Zone/traffic data retained per standard data retention policy.

6. **Compliance flags:** `organizations.vision_consent_model` field: `'anonymous'` (default), `'opt_in_identity'`, or `'disabled'`.

### Camera Integration

**Protocol:** RTSP (Real Time Streaming Protocol) — industry standard for IP cameras.

**Supported cameras:** Any IP camera with RTSP output. Recommended:
- Reolink RLC-810A ($55) — 4K, PoE, RTSP native
- Amcrest IP8M-T2599EW ($70) — 4K, PoE, AI detection built-in
- Hikvision DS-2CD2143G2-I ($90) — enterprise grade

**Connection flow:**
1. Merchant purchases/connects IP cameras to local network
2. Merchant clicks "Connect Cameras" in Customer Intelligence page
3. Meridian app shows setup wizard:
   - Enter camera RTSP URL(s)
   - Define zones (drag-to-draw on camera preview)
   - Set operating hours
   - Accept privacy/consent terms
4. Edge processing node starts consuming camera streams
5. Analytics appear in Customer Intelligence within minutes

### Database Schema (New Tables)

```sql
-- Camera configurations per location
CREATE TABLE vision_cameras (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES organizations(id),
  location_id UUID REFERENCES locations(id),
  name TEXT NOT NULL,           -- "Front Entrance", "Checkout Area"
  rtsp_url TEXT NOT NULL,       -- encrypted at rest
  zones JSONB DEFAULT '[]',     -- [{name, polygon_points}]
  operating_hours JSONB,        -- {start: "08:00", end: "22:00"}
  status TEXT DEFAULT 'active', -- active, paused, disconnected
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Anonymous visitor profiles (face embeddings stored on-prem only)
CREATE TABLE vision_visitors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES organizations(id),
  visitor_hash TEXT NOT NULL,    -- hash of on-prem embedding ID (not the embedding itself)
  first_seen TIMESTAMPTZ NOT NULL,
  last_seen TIMESTAMPTZ NOT NULL,
  total_visits INTEGER DEFAULT 1,
  est_age_range TEXT,            -- "25-34"
  est_gender TEXT,               -- "M", "F", "unknown"
  linked_customer_id UUID,       -- optional: if customer opts in to identity link
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Individual visit records
CREATE TABLE vision_visits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id UUID NOT NULL REFERENCES organizations(id),
  visitor_hash TEXT NOT NULL,
  entered_at TIMESTAMPTZ NOT NULL,
  exited_at TIMESTAMPTZ,
  dwell_seconds INTEGER,
  zones_visited JSONB DEFAULT '[]',  -- [{zone, entered_at, duration_sec}]
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Aggregated traffic counts (hypertable)
CREATE TABLE vision_traffic (
  business_id UUID NOT NULL,
  location_id UUID,
  bucket TIMESTAMPTZ NOT NULL,   -- 15-minute buckets
  visitors_in INTEGER DEFAULT 0,
  visitors_out INTEGER DEFAULT 0,
  avg_dwell_seconds NUMERIC,
  avg_queue_length NUMERIC,
  demographics JSONB,            -- {"age_ranges": {...}, "gender": {...}}
  created_at TIMESTAMPTZ DEFAULT now()
);
SELECT create_hypertable('vision_traffic', 'bucket');
```

### New AI Agents

| Agent | Level | Input | Output |
|-------|-------|-------|--------|
| `foot_traffic_analyst` | 1 | vision_traffic | Hourly/daily/weekly visit trends, peak detection |
| `dwell_time_optimizer` | 2 | vision_visits | Zone efficiency, layout recommendations |
| `customer_recognizer` | 2 | vision_visitors | Repeat visit patterns, loyalty scoring without POS data |
| `demographic_profiler` | 2 | vision_visitors | Age/gender distribution by time, marketing targeting |
| `queue_monitor` | 1 | vision_traffic | Real-time wait times, staffing alerts |

### Frontend: "Connect Cameras" Button

Location: `CustomersPage.tsx` → header section, next to "Customer Intelligence" title.

**States:**
1. **No cameras connected:** Show "Connect Cameras" button with camera icon → opens setup wizard
2. **Cameras connected:** Show "3 cameras • Live" badge with green dot → click opens camera management
3. **Camera offline:** Show "1 camera offline" warning badge → click opens troubleshooting

### Alternative Considered

**Cloud-based video analytics (AWS Rekognition, Google Cloud Vision):**
- Rejected: $1-4 per 1,000 API calls. A single camera at 1fps = 86,400 calls/day = $86-345/day. Economically impossible for $250/mo merchants.
- Rejected: Requires streaming video to cloud. Privacy nightmare + bandwidth costs.

**No face recognition, just counting (thermal/IR sensors):**
- Rejected: Misses the key insight — repeat vs. new visitors. Counting is commodity. Identity is the moat.

### Implementation Priority

1. Schema migration + RLS policies
2. Edge processing Docker image (YOLO + ByteTrack + CompreFace)
3. Camera setup wizard in frontend
4. Vision data ingestion API endpoint
5. 5 new AI agents
6. Customer Intelligence page integration
