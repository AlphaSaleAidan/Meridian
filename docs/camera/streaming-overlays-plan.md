# Meridian Camera — Live Streaming + Intelligence Overlays · Implementation Plan

Status: **PLAN — no code yet.** Branch `feat/camera-streaming-overlays` off `session-2-canada-prep`.
Read alongside the task brief. This plan reflects a read-only recon of the existing stack
(see "Recon findings"). Nothing here is built until each phase's PR is reviewed and merged by Aidan.

---

## TL;DR

The vision intelligence **already exists** (detection, pose, zones, counting, FastReID, journeys,
10 cross-reference agents, anomaly, edge agent). This project adds the **three missing pieces**:
1. a **software-only connector** that dials outbound from the customer's site,
2. **live video** to the phone (WebRTC, HLS fallback),
3. **toggleable intelligence overlays** rendered over that video from existing agent output.

Plus one security fix we found along the way (a P0 tenancy hole on the current vision tables) and
per-province retention settings.

---

## Recon findings (what's real vs missing)

**Already built — consume, do not rebuild:**
- `src/camera/detector.py` — YOLO11n + ByteTrack → person boxes + tracker_id + zone. (Layer 1, 5)
- `src/ai/freemocap/skeletal_tracker.py` — pose landmarks + gesture (optional). (Layer 2)
- `src/camera/{zone_loader,line_counter,people_counter}.py` — zones, crossings, occupancy. (Layer 5)
- `src/ai/reid/person_reid_service.py` — FastReID anonymous cross-camera ID (optional). (Layer 3)
- `src/ai/reid/journey_tracker.py` — journeys / zone stops / dwell. (Layer 4, 6)
- `src/ai/agents/cross_ref/*` (10 agents) → `cross_reference_insights`. (Layer 7)
- `src/ai/alerts/revenue_anomaly.py`, `anomaly_detector_upgraded.py`. (Layer 8)
- `src/camera/rtsp_handler.py` — RTSP ingest (cv2.VideoCapture). `edge/edge_agent.py` — connector base.
- FastAPI `src/api/routes/vision.py` — camera CRUD + heartbeat + ingest, `require_org_access`
  (JWT + org membership) and `X-Device-Token` for edge ingest.
- Supabase: `vision_cameras`, `vision_traffic`, `vision_visits/visitors`, `customer_journeys`,
  `cross_reference_insights`, `zone_purchase_correlation`, `anonymous_customer_profiles`.
- Frontend: `pages/CameraIntelligencePage.tsx` (demo dashboard), `components/vision/CameraSetupWizard.tsx`.

**Missing — the build:**
- No WebRTC / WHIP / WHEP / HLS / MediaMTX / go2rtc / coturn anywhere.
- No live frame → browser path (today it's 15-min aggregates pushed to the cloud).
- No per-frame timestamp on the frame queue (overlay time-sync needs a monotonic `frame_ts`).

**🚨 P0 tenancy hole:** `supabase/migrations/20260516_vision_cameras.sql` uses
`FOR ALL USING (true)` on `vision_cameras/traffic/visitors/visits` → cross-tenant readable.
The brief forbids exactly this. Fixed in Phase 1 with a passing denial test.

**Design tokens (decision: MATCH EXISTING):** real app uses Geist/Inter + near-black `#0A0A0B`/
`#111113`, blue `#1A8FD6`, teal `#17C5B0`, amber for warnings — NOT the brief's Archivo/Hanken/
Martian. We match the existing portal (and can reuse the warm Schedule treatment if desired).

---

## GPU strategy (Aidan has a GPU box, not yet set up)

Re-ID (FastReID) is the only layer that needs a GPU at scale (~8ms/crop GPU vs ~200ms CPU; a
frame with 20+ people stalls on CPU). Everything else — detection, pose, zones, counts, heatmap,
journeys, POS x-ref, exceptions — is fine on CPU at the current edge cadence.

Three ways to get GPU, in order of laziness:

1. **CPU-first now, GPU later (recommended start).** Ship every layer on CPU; cap the Re-ID/
   Identity overlay to small crowds and show an "identity needs GPU" chip past a threshold. Nothing
   blocks on the GPU box. The Re-ID service already degrades gracefully (tracker-only fallback).
2. **Your GPU box as the on-site inference node.** When you set it up, run the existing camera
   pipeline + FastReID on it on the customer site (or your site for the design partner). The
   connector publishes video to the cloud gateway for viewing; heavy inference stays on your GPU box
   and writes detections/insights to Supabase exactly as today. This is the cleanest — frame-level
   access stays on hardware we control, no per-frame egress cost. Needs: CUDA + the repo's vision
   extras installed, outbound network to Supabase + gateway.
3. **Cloud GPU route (when neither is on-site).** Stand up a GPU worker (rented cloud GPU, or a
   serverless GPU endpoint) that the gateway's frame-fork calls for Re-ID embeddings only — send
   person crops, get back vectors. Keeps the rest CPU-local. Higher latency + egress; use only if
   on-site GPU isn't available. `StreamGateway`/inference stays behind an interface so this is a
   swap, not a rewrite.

**Plan:** build CPU-first (option 1) so progress isn't gated; wire the Re-ID overlay behind a
`REID_GPU_ENABLED` flag + an inference-endpoint env so option 2 or 3 is a config change, not new code.

---

## Phases (one PR each, reviewed + merged by Aidan)

**Phase 0 — Compliance recon (parallel, doc-only).** Produce `docs/compliance/camera-compliance-
gap-report.md` from on-file Canadian docs (PIPEDA, Law 25, AB/BC PIPA, provincial cannabis
retention). Fills the ⚠️ per-province retention rows from our docs, not web guesses. No code.

**Phase 1 — Data model + tenancy (safe, no infra).**
- New tenant-scoped tables: `sites`, `cameras`, `camera_streams`, `stream_tokens`,
  `user_overlay_prefs` — mirror the proven `org_id UUID REFERENCES organizations(id)` + RLS pattern
  (the 20260501 migration), NOT `FOR ALL USING (true)`.
- **Fix the P0 hole** on `vision_cameras/traffic/visitors/visits` → real org isolation.
- Add per-location `surveillance_required` + `surveillance_retention_days` to the existing
  per-location settings (province-defaulted; strictest-unknown = 60d).
- Ship the **cross-tenant denial e2e test** in this PR. Back up + export schema first; print sha256.

**Phase 2 — Gateway (off-the-shelf, LIVE-BOX INFRA — gated on Aidan go).**
- MediaMTX as PM2 `meridian-gateway` (WHIP/RTSP ingest, WebRTC/WHEP + LL-HLS egress, auth hook →
  FastAPI). coturn with rotating shared secret. Pin nginx version + healthcheck (recall the prior
  silent nginx-upgrade outage). Frame-fork to the existing pipeline; tag frames with monotonic
  `frame_ts`. `StreamGateway` interface: `MediaMtxGateway` impl + `KvsGateway` stub.
- **Risk:** new daemons on the live Contabo edge host. Staged carefully, resource-capped, behind
  health checks; does not touch nginx/PM2 for the existing sites.

**Phase 3 — FastAPI endpoints.** `POST /sites/:id/cameras`, `POST /cameras/:id/live-token`
(≤60s single-camera JWT), `GET /cameras/:id/clip?from=&to=`, `GET /overlays/:camera_id/feed`
(tenant-scoped overlay stream via Supabase realtime/WS), `POST /gateway/auth` (internal). All
tenant-scoped; cross-tenant → 404.

**Phase 4 — Software-only connector.** Extend `edge/edge_agent.py` → `meridian-connector` Docker
image (one-line `docker run` / small Windows installer). Pairing code → scoped device token →
go2rtc ONVIF discovery → register cameras → publish each outbound (WHIP/RTSP-over-TLS). Camera creds
stay on the connector only. Auto-reconnect, local buffer on drop, heartbeat. No hardware, no router
changes. gitleaks pattern for `rtsp://user:pass@`.

**Phase 5 — Live view + overlay manager (portal).** Onboarding "Connect your cameras" step
(pairing code/QR + connector download + realtime-populating list). Live grid → WHEP player + HLS.js
fallback → the toggleable overlay layer manager (8 layers, presets Raw/Operations/Loss-Prevention/
All, prefs persisted, time-sync with "analysis catching up" chip, permission-gated re-ID/x-ref/
exceptions). **Match existing tokens.** Mobile-first; test iOS Safari + Android Chrome on cellular.

**Phase 6 — POS x-ref glue + exceptions.** Wire `cross_reference_insights` into the POS x-ref
overlay + flagged-transaction "view evidence" (txn timestamp → `/clip`).

**Phase 7 — Per-province retention + compliance enforcement.** Apply the Phase 0 values; enforce
the auto-purge floor (never below provincial minimum); surface "Compliant retention: N days
(Province minimum)" in onboarding.

---

## Open confirmations (Aidan)
- **Connector = software-only only** (no optional shipped appliance)? Default assumed: yes.
- **GPU:** confirmed you have a box to set up → we build CPU-first and flag the Re-ID overlay for
  GPU (your box as on-site node, or cloud-route). See GPU strategy.
- **Overlay disclosure:** are re-ID badges / basket tags / segment labels merchant-visible or
  internal-only? (privacy + product decision — also feeds the compliance report).
- **Data residency:** do Pacific Revenue Systems / any QC-resident-data tenants require a Canadian
  storage region for footage? (Phase 0 will flag if Law 25 forces it.)
- **Retention "strictest-if-unknown = 60d" default** OK?

---

## Analytics audit per overlay toggle (verified against code + manifests)

The heavy models run on the **edge/GPU node** (`edge/requirements.txt`), not the cloud — the
Railway app deliberately ships **no torch/ultralytics** (`requirements.txt` comments them out,
"~2GB OOM"). So the overlay feed *consumes* analytics output; it never runs the models.

| # | Toggle | Repo / lib | Manifest | Runtime today | Overlay-ready |
|---|--------|------------|----------|---------------|---------------|
| 1 | Detections | `ultralytics` YOLO11 + `supervision` | edge ✓ | real (edge) | ✅ boxes + tracker_id + conf |
| 2 | Pose / skeleton | `skellytracker`→`mediapipe` | commented / lazy | **OFF unless installed** | ⚠️ install mediapipe (CPU-OK) |
| 3 | Identity (cross-cam Re-ID) | `fastreid` (Apache-2.0) | **not in any manifest** | **OFF → tracker-id only** | ⚠️ needs fastreid on the **GPU box** (or boxmot ReID) — this is the GPU-gated layer |
| 4 | Journey trails | `journey_tracker.py` (pure) + `boxmot` tracks | boxmot ✓ | real | ✅ |
| 5 | Zones & counts | `supervision` (MIT) | edge ✓ | real | ✅ |
| 6 | Heatmap | derived from people_counter/journey dwell | n/a | real | ✅ derive grid |
| 7 | POS x-ref | `cross_ref/*` agents → `cross_reference_insights` | pure ✓ | real | ✅ table |
| 8 | Exceptions | `pyod` + `luminol` + anomaly agents | ml ✓ | real | ✅ alerts |

**Takeaways**
- **6 of 8 layers (1,4,5,6,7,8) are ready to surface today.** Pose (2) just needs mediapipe
  installed; cross-camera Identity (3) is the only one truly inactive — `fastreid` isn't installed,
  so re-ID currently falls back to single-camera tracker-id. (3) is exactly the **GPU-gated** layer,
  which matches the GPU strategy above — light up on your GPU box / cloud-route.
- **Per-frame output gap:** detection/pose/zone/journey output is consumed in-memory and today only
  persisted as **15-min aggregates**. For live overlays the feed (Phase 3) must tap the pipeline's
  **per-frame** output and publish it (Supabase realtime/WS) tagged with `frame_ts` — emit from the
  existing pipeline, don't add a parallel one. x-ref (7) + exceptions (8) already persist to tables,
  so those layers read straight from Supabase.

**⚠️ LICENSING — confirm with Aidan/Enoch (pre-existing, not introduced here):**
`ultralytics` YOLO (Layer 1) and `boxmot` (Layers 3/4 tracking) are **AGPL-3.0** (network-copyleft).
Using them in a hosted commercial product typically needs an Ultralytics commercial license (or a
non-AGPL detector/tracker). `supervision`/`fastreid`/`mediapipe`/`pyod`/`luminol` are permissive.
This is the existing vision stack — flagging so it's a conscious decision before we scale cameras.

---

## Confirmations status
- ✅ **Connector software-only** — confirmed by Aidan.
- ✅ **Design tokens** — match existing portal.
- ✅ **GPU** — CPU-first; Re-ID/Identity is the GPU-gated layer (Aidan's GPU box → on-site node, or cloud-route).
- ⏳ **AGPL licensing** (YOLO/boxmot) — needs Aidan/Enoch decision (new flag from this audit).
- ⏳ Overlay disclosure (re-ID/basket tags merchant-visible?) · Canada data residency · retention 60d-strictest default.

## Definition of done — see brief §11 (unchanged).
