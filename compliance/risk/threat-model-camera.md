# Threat Model — Camera / Vision Stack & POS Cross-Reference

> STRIDE-lite + privacy threat model for the highest-sensitivity flow: in-store camera analytics and its
> cross-reference to POS transactions and identity. v0.1 — 2026-06-28. Feeds risk register (R-01, R-05, R-06)
> and controls `CC6.1-RLS`, `CC6.7-ENCRYPTION`, `P-PRIVACY`. **Cannabis-dispensary clients raise the stakes
> on every privacy item below.**

## Data flow
```
Camera (RTSP) → Edge agent (Jetson, MERCHANT premises): YOLO detect → ByteTrack →
   PersonReID embedding (FastReID)  [+ optional DeepFace demographics, +optional CompreFace VIP face-match]
   → JourneyTracker.process_sighting()
   → on POS txn: JourneyTracker.correlate_transaction()  (src/ai/reid/journey_tracker.py:145, 120s window)
   → CustomerJourney {person_id + transaction_id + total_cents}
   → CrossReferenceOrchestrator.persist_journeys() → Supabase customer_journeys
Live view: edge → Cloudflare Stream (WHIP/WHEP, TLS) → browser   (video never transits Meridian infra)
Retention: vision_visitors.expires_at = now()+90d; cleanup_expired_visitors() (UNSCHEDULED)
```

## Key design strengths (state honestly)
- **No video frames stored or transmitted** — embeddings stay on merchant hardware (`edge/edge_agent.py:7-9`).
- Live view relays edge→Cloudflare→browser; **video never touches Meridian's own infra**.
- Sensitive analyses (`demographics`, `vip`, `live_view`) **default OFF** (`src/api/routes/vision.py:46-50`);
  three compliance modes (`anonymous` / `opt_in_identity` / `disabled`) enforced at registration.
- Consent-signage checkbox gates camera activation (`CameraSetupWizard.tsx:365`); `camera_disclosure` doc
  served only when `has_camera=True` (`acceptance_gate.py:83`).

## Trust boundaries
1. Physical camera ↔ edge device — RTSP, on merchant LAN.
2. Edge device ↔ Supabase — writes visit/journey records (no frames).
3. Edge device ↔ CompreFace / Cloudflare Stream — face crops to CompreFace (if VIP on); video to Cloudflare.
4. App ↔ Supabase — `vision_*` + `customer_journeys` reads (RLS).

## Threats

| # | STRIDE / Privacy | Threat | Current control | Gap / Risk | Action |
|---|---|---|---|---|---|
| V1 | Info disclosure | **Cross-tenant read of camera + journey data** — `vision_*` on `FOR ALL USING(true)` (named "service role", no `TO service_role`) → public | RLS intended; original `20260501_004` had org-scope but later `20260516` added wide-open policies; P0 fix migration **absent from main** | **CRITICAL (R-01)** — another tenant's footfall/identity/spend readable | R0 confirm live; R1 restore fix migration + denial test |
| V2 | Info disclosure (biometric) | VIP face-match builds a facial-recognition identity index | CompreFace gated behind `vip:false` default; **not yet wired to prod frame loop** (TODO `edge_agent.py:186`) | No PIA, no biometric consent, no Quebec/cannabis block (R-05) | PIA + biometric consent flow **before** enabling; jurisdiction gate |
| V3 | Privacy (minors) | DeepFace buckets apparent age incl. `age_0-17` | Aggregate buckets only, not per-individual; off by default | Processing minors' apparent age needs heightened basis (Law 25) | Justify or suppress minor bucket; document basis |
| V4 | Privacy (purpose) | `customer_journeys` (person_id+txn+spend) classified `resale_tier:"premium"` and potentially resold | — | **Not disclosed** to merchants; SLA says only "improve the Services" (R-04) | Legal: disclose secondary purpose or stop resale classification |
| V5 | Info disclosure | RTSP camera→edge stream unencrypted on LAN | On merchant premises LAN | No RTSPS/VPN; risk if LAN untrusted | DECISION: RTSPS or VPN tunnel; document network assumption |
| V6 | Tampering/Spoofing | Rogue device posts fake vision records to another org | Edge auth to Supabase; RLS | If `vision_*` writable cross-tenant (V1), spoofing possible | Org-scoped write RLS + device auth |
| V7 | Privacy (retention) | 90-day deletion never runs → indefinite retention of identity-linked records | `expires_at` + `cleanup_expired_visitors()` defined | **Function UNSCHEDULED** (R-06); posture doc says 30d, schema says 90d (inconsistent) | Schedule via pg_cron/Celery; reconcile the period |
| V8 | Repudiation | Merchant/customer disputes whether consent existed | SHA-256 acceptance gate; consent-signage checkbox | Acceptance IP not captured (`ComplianceGate.tsx:82`); cookie consent localStorage-only | Capture IP; server-side consent record |
| V9 | Physical | Edge Jetson on merchant premises stolen/tampered | Embeddings auto-expire; no frames stored | Device physical security is merchant's; document boundary | Tamper guidance in physical-security policy |

## Lawful basis (must be documented before `opt_in_identity`/VIP is enabled)
The codebase has **no lawful-basis register** for the camera↔identity overlay. `anonymous` mode is defensible
as aggregate analytics; `opt_in_identity` + VIP face-match crosses into biometric processing requiring an
explicit lawful basis, PIA, and consent under PIPEDA / Quebec Law 25 — **especially for cannabis clients.**

## Residual risk
The architecture is privacy-forward (no frames, defaults-off, on-prem embeddings). The exposures are
**operational**: the live RLS state (V1), the unscheduled deletion (V7), and the undisclosed resale purpose
(V4). Close those and the camera stack is a readiness strength rather than the biggest liability.
