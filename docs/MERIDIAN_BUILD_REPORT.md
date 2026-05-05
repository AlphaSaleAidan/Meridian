# MERIDIAN BUILD REPORT — 2026-05-05

## Section 1: Canadian Portal Isolation

### 1.1 Landing Page Cleanup
- **Removed** Canadian Portal button from `LandingPage.tsx` footer (lines 452-460)
- **Reverted** `space-y-6` class on footer container to original layout
- **Verified** zero remaining Canadian Portal references in LandingPage.tsx via grep

### 1.2 Standalone Canadian Portal
Already complete from prior session:
- `/canada/login` — dedicated login page (`CanadaLoginPage.tsx`) with Canada branding
- `/canada/*` — auth-gated via `CanadaProtectedRoute` with `allowSalesReps=true`
- `CanadaLayout` — standalone layout with Canada branding, full sidebar nav
- Sales reps (Enoch, Aidan) authenticate via `supabase.auth.signInWithPassword` directly, bypassing the SR block in `useAuth().login()`
- No dependency on main landing page — portal is fully standalone

---

## Section 2: Portal Functional Audit

### Pages Audited (18 total)

| Page | Status | Data Source | Notes |
|------|--------|------------|-------|
| OverviewPage | Working | Real API | Full dashboard with live metrics |
| RevenuePage | Working | Real API | Revenue charts, period comparison |
| ProductsPage | Working | Real API | Product analytics, rankings |
| InsightsPage | Working | Real API | AI-generated insights |
| ForecastsPage | Working | Real API | Predictive forecasting |
| SettingsPage | Working | Real API | User/org settings |
| InventoryPage | Working | Real API | Stock tracking |
| AdminPage | Working | Real API | Admin controls |
| ITDashboardPage | Working | Real API | IT health monitoring |
| NotificationsPage | **Fixed** | Real API | Was using hardcoded `VITE_ORG_ID` fallback; now uses `useOrgId()` hook |
| AgentDashboardPage | Stubbed | Demo data | Shows "Analyzing..." in production |
| ActionsPage | Stubbed | Demo data | Shows "Analyzing..." in production |
| CustomersPage | Stubbed | Demo data | Shows "Analyzing..." in production |
| StaffPage | Stubbed | Demo data | Shows "Analyzing..." in production |
| PeakHoursPage | Stubbed | Demo data | Shows "Analyzing..." in production |
| MarginsPage | Stubbed | Demo data | Shows "Analyzing..." in production |
| MenuEngineeringPage | Stubbed | Demo data | Shows "Analyzing..." in production |
| AnomaliesPage | Stubbed | Demo data | Shows "Analyzing..." in production |

### Customer Signup Flow
- `CustomerSignupPage.tsx` — email, password (min 8 chars), full name, business name
- Token validation for SR-provisioned accounts
- Creates Supabase Auth user + business row
- Redirects to `/app` on success
- Email confirmation flow supported

### Auth Flow
- Login: `supabase.auth.signInWithPassword` → check SR status → fetch business → set org
- Session: Supabase `onAuthStateChange` listener with 5s timeout guard
- Role guards: `ProtectedRoute` blocks SRs from customer portal (unless `allowSalesReps`)
- Canada portal: bypasses SR check, allows all authenticated users

### Fix Applied
- **NotificationsPage**: Replaced `const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'` with `useOrgId()` hook — now correctly resolves org from auth context or path

---

## Section 3: LiDAR Scan Button

### Capability Detection
New `useScanCapability()` hook in `ScanControls.tsx`:
- Checks `navigator.mediaDevices.getUserMedia` availability
- Enumerates video input devices via `navigator.mediaDevices.enumerateDevices()`
- Probes WebXR Depth API via `navigator.xr.isSessionSupported('immersive-ar')`
- Returns one of: `ready` | `camera-only` | `not-supported` | `checking`

### Status Indicator Badge
Inline badge next to scan button shows real-time capability status:
- **LiDAR Ready** (green) — depth sensor detected
- **Camera Only** (amber) — camera but no depth sensor, photogrammetry fallback
- **Not Supported** (red) — no camera access at all
- **Detecting...** (gray) — probe in progress

### Demo vs Production Behavior
- **Demo portal**: "New Scan" opens a modal explaining LiDAR simulation, device requirements, and scan output format
- **Production portal (no scan)**: `ProductionSpaceSetup` shows setup instructions with capability badge and contextual warnings
- **Production portal (scan exists)**: Shows scan viewer with re-scan option

### Native Dependencies Flagged
- WebXR Depth API is **not** a substitute for Apple RoomPlan — real LiDAR scanning requires native iOS app
- Camera-only fallback uses photogrammetry, which produces lower-quality meshes
- `ScanControls.tsx` documents the XR type interface instead of using `any`

---

## Section 4: 3D Space Generation Pipeline

### Existing Infrastructure (Audited)
- `SpaceViewer.tsx` — Three.js point cloud viewer with orbit controls, hot zones, sweep animation
- `SpaceTab.tsx` — tab with 3D/Heatmap/Zones view modes, zone analytics table, AI recommendations
- Polycam iframe embed already working for demo scans
- Three.js deps: `@react-three/fiber`, `@react-three/drei`, `three`

### New: Scan Ingestion Handler
`src/api/routes/spaces.py` — 5 endpoints:
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/spaces/upload` | POST | Register a new LiDAR scan with metadata |
| `/api/spaces/{org_id}` | GET | List all spaces for an organization |
| `/api/spaces/{org_id}/{id}` | GET | Get single space with zone data |
| `/api/spaces/{id}/status` | PATCH | Update processing status |
| `/api/spaces/{id}/zones` | POST | Store zone mapping data |

Registered in `app.py` with `spaces_router`.

### New: Database Schema
`supabase/migrations/20260505_spaces.sql`:
- `spaces` table — id, org_id, scan_type, device_model, file_format, source_url, model_url, thumbnail_url, status, metadata
- `space_zones` table — zone_id, label, position (x/y/z), radius, category, traffic, dwell, conversion, revenue
- RLS enabled on both tables with service role policies
- `space_summary` view aggregating per-org stats
- Indexes on org_id, status, space_id

### Customer Profile Linking
- Spaces linked to customer profiles via `org_id` foreign key
- Zone data stored per-space with analytics fields (traffic, dwell, conversion, revenue/sqft)
- Demo fallback data included in API for graceful degradation

### Storage Architecture
- **Current**: Polycam iframe embeds via `source_url` field
- **Future**: Supabase Storage bucket `store-scans/{org_id}/` for USDZ/GLB uploads
- **Model URL**: `model_url` field for processed GLB models
- **Thumbnails**: `thumbnail_url` for preview images

---

## Section 5: Business Knowledge Web Scraper

### Location
`tools/scraper/scraper.py`

### Setup
```bash
cd tools/scraper
pip install -r requirements.txt
python scraper.py --sources all --output ./data
```

### Target Sources (5 configured)
| Source | Key | Topics |
|--------|-----|--------|
| McKinsey & Company | `mckinsey` | retail, restaurant, supply-chain, operations |
| Harvard Business Review | `hbr` | analytics, management, customer-experience |
| Deloitte Insights | `deloitte` | retail, restaurant, food-service, technology |
| MIT Sloan Management Review | `mit_sloan` | analytics, digital-transformation, ai |
| Andreessen Horowitz | `a16z` | fintech, marketplace, saas, ai, growth |

### Data Pipeline
1. **Crawl**: Crawl4AI async browser with configurable `max_pages` per source
2. **Clean**: Strip scripts, styles, nav, footer, headers, HTML tags, collapse whitespace
3. **Tag**: Auto-classify into domains (restaurant, retail, analytics) via keyword matching
4. **Store**: Individual JSON files per article with full metadata

### Output Format
Each document:
```json
{
  "id": "mckinsey_abc12345",
  "title": "Article Title",
  "content": "Cleaned text...",
  "metadata": {
    "source": "McKinsey & Company",
    "url": "https://...",
    "domain_tags": ["restaurant", "analytics"],
    "word_count": 1234,
    "content_hash": "abc12345deadbeef",
    "scraped_at": "2026-05-05T..."
  }
}
```

### Manifest
`manifest.json` generated after crawl with per-source stats and document IDs.

---

## CLAUDE.md Compliance Check

| Rule | Status | Details |
|------|--------|---------|
| No hardcoded merchant IDs/keys | Pass | All API routes use request params |
| New routes in `src/api/routes/` | Pass | `spaces.py` created there |
| Routes registered in `app.py` | Pass | `spaces_router` added |
| RLS on new tables | Pass | Both `spaces` and `space_zones` have RLS + policies |
| TypeScript strict — no `any` | Pass | WebXR uses typed `XRSystem` interface |
| Python type hints | Pass | All functions have type annotations |
| Component files max 300 lines | Pass | SpaceTab: 255, ScanControls: 218 |
| API error handling | Pass | HTTPException for 404/400 cases |
| Demo portal mirrors production | Pass | Demo fallback data in all new endpoints |

---

## Files Changed

### Modified
- `frontend/src/pages/LandingPage.tsx` — removed Canadian Portal button
- `frontend/src/pages/NotificationsPage.tsx` — fixed hardcoded ORG_ID
- `frontend/src/pages/SpaceTab.tsx` — refactored, extracted scan controls
- `src/api/app.py` — registered spaces router

### Created
- `frontend/src/components/space/ScanControls.tsx` — capability detection, scan button, production setup
- `src/api/routes/spaces.py` — 3D space management API (5 endpoints)
- `supabase/migrations/20260505_spaces.sql` — spaces + space_zones tables with RLS
- `tools/scraper/scraper.py` — Crawl4AI business knowledge scraper
- `tools/scraper/requirements.txt` — scraper dependencies
- `docs/MERIDIAN_BUILD_REPORT.md` — this file

### Pending (requires user action)
- Run `20260505_spaces.sql` migration in Supabase SQL editor
- Install `crawl4ai` and run scraper when ready
- Deploy frontend to Vercel + backend to Railway
- Verify Canadian Portal login works for Enoch/Aidan post-deploy
