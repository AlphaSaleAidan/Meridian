# Open Questions for Aidan

Items flagged during Phase 3 content rebuild where the source-of-truth wasn't sufficient to write rep-facing content with confidence. None block the playbook going live; all are improvements.

---

## 1. ~~Phase 1 source-of-truth POS/camera markdown directories don't exist~~ — RESOLVED 2026-05-31

**Resolution:** The Phase 1 files (80 POS entries + matrices) existed on the unmerged branch `feat/playbook-phase-1-research` but weren't on `main` when Phase 3 ran. Restored after Phase 3 completion via `git checkout`. Phase 3's POS entries are therefore registry-sourced (auth, endpoints, categories from `registry.py`) rather than research-sourced (partner gates, failure modes, strategic notes from `_status/pos/*.md`).

**Follow-up:** The 12 Wave 1 POS entries should be enhanced with Phase 1 research (partner program URLs, failure modes, recommendation rationale) when bandwidth allows — content is now available at `docs/playbook/_status/pos/*.md`. Tracked as a separate task; not blocking portal rollout.

---

## 2. Refund authority limits (rep / CS Manager / CS Director)

**File:** `40-troubleshooting/billing-issues.md`

**Context:** Used placeholder thresholds (<CA$50 rep-approved, CA$50–CA$500 CS Manager, >CA$500 CS Director).

**Action needed:** Confirm or correct the actual policy. Without this, reps may either refund too aggressively (margin hit) or escalate too often (CS bottleneck).

---

## 3. "How to connect any IP camera" diagnostic depth

**File:** `20-camera-integrations/_how-to-connect-any-camera.md`

**Context:** Wrote detailed RTSP URL formats, VLC test instructions, ONVIF discovery flow.

**Action needed:** Confirm reps are technical enough to run this, or whether it should be a CS-only escalation path. Most reps don't know what VLC is.

---

## 4. Square data quality claim ("highest of any POS we connect to")

**File:** `10-pos-integrations/square.md`

**Context:** Stated this as a positioning point. Likely true based on data field coverage in `_data-requirements-matrix.md`, but it's a claim that should be empirically verified before reps lean on it heavily in pitches.

**Action needed:** Confirm or adjust.

---

## 5. Average "CA$2,800/mo Money Left on Table" claim

**Files:** Used in multiple places (00-getting-started, cheat sheets, objection handlers).

**Context:** Pulled from existing `lesson_content.json` (lesson 1.1, 2.1, etc.). It's the headline hook.

**Action needed:** Confirm this is still a defensible average based on current customer-base outputs from the `money_left_on_table` agent. If the average has shifted, update once across all docs. Compliance lesson 6.3 (`lesson_content.json`) explicitly says reps must use accurate averages — this needs to stay current.

---

## 6. Clover token-refresh bug — "fix pending" status

**Files:** `10-pos-integrations/clover.md`, `40-troubleshooting/pos-connection-failures.md`, `30-features/_data-requirements-matrix.md`.

**Context:** Documented per Phase 2 decisions (production issue #1). Mentioned the workaround (reconnect from portal).

**Action needed:** Once the fix ships (`src/clover/oauth.py`), update docs to remove the "pending" warnings.

---

## 7. Phone agent product positioning

**File:** `00-getting-started/03-pricing-commission.md` (mentioned briefly as "separate product, separate pricing — ask if interested, route to product team").

**Context:** I deliberately didn't document phone agent as a feature because it's not in `src/ai/agents/`. There's a `services/phone_agent/` directory and references in commits (`fix(phone-agent): pin pipecat<1`), but no rep-facing pricing/positioning info in the Phase 2 decisions.

**Action needed:** Provide a one-pager on what phone agent does + pricing + how reps should position it, or confirm reps shouldn't mention it at all.

---

## 8. "Posture purchase" cross-reference agent — which add-on?

**Files:** `30-features/cross-reference/posture_purchase.md`, `30-features/_data-requirements-matrix.md`, `50-cheatsheets/tier-feature-comparison.md`.

**Context:** With tiers removed, posture_purchase is documented as part of the camera intelligence add-on alongside the other 9 cross-reference agents. However, it requires a skeletal-tracking module (freemocap dependency) that the others don't. It may be a separate add-on or have additional cost.

**Action needed:** Confirm whether posture_purchase is included in the camera intelligence add-on at no extra cost, or is a separate line item. Update `_data-requirements-matrix.md` and `tier-feature-comparison.md` once confirmed.

---

## 9. Agent count discrepancy vs task spec

**File:** `30-features/_index.md`

**Context:** Task spec said "20 pos_analytics + 5 vision + 13 cross-reference + 2 coordination = 40." Actual code has 30 + 5 + 10 + 2 = 47. Documented what's real per anti-goal #3 ("don't speculate about features that don't exist in `src/ai/agents/`").

**Action needed:** No action — just a flag that the spec was off by a few. Real-world is what's documented.

---

## 10. SkyTab "Revel migration tailwind" — ~18,000 merchants

**File:** `10-pos-integrations/skytab.md`, `50-cheatsheets/pos-by-vertical.md`.

**Context:** Used the ~18k number from Phase 2 decisions. It's a public-ish figure but the rep angle assumes it stays accurate.

**Action needed:** Confirm the number is current; update if it's drifted significantly.

---

## 11. Cannabis vertical compliance details

**Files:** `10-pos-integrations/cova-pos.md`, `dutchie.md`, `treez.md`, `flowhub.md`, `meadow.md`, `blaze.md`, `biotrack.md`, `indica-online.md`.

**Context:** Mentioned "separate banking/insurance posture (federal Schedule I), PII per state HIPAA-adjacent rules, no Google/Facebook/LinkedIn ads" per Phase 2.

**Action needed:** Confirm whether reps need a deeper compliance one-pager for cannabis prospects, or whether the current per-doc mention is sufficient. Compliance has real legal exposure here.

---

## 12. ~~Plan tier dollar amounts~~ — RESOLVED 2026-06-29

**Resolution:** Tiers (Standard/Premium/Command) and their fixed dollar amounts have been removed from all training docs. Pricing is now fully custom per deal. Illustrative examples in commission tables (CA$350/CA$600/CA$1,200) remain to show the commission math at different price points but are not published as prices. No further action needed.

---

## 13. CSV-only — SFTP automation add-on (ship status)

**File:** `10-pos-integrations/_csv-only-systems.md`

**Context:** Previously documented as a Premium tier feature. With tiers removed, SFTP automation is now framed as an add-on. The script has been updated to say "confirm with product team before promising." However, the underlying question remains.

**Action needed:** Confirm whether SFTP automation is actually shipped today, or is still roadmap. If shipped, remove the FLAG note from `_csv-only-systems.md` and let reps sell it confidently. If roadmap, current "confirm first" framing is correct.

---

## 14. Federal/Section 889 — Axis as the only compliant camera

**File:** `20-camera-integrations/axis.md`

**Context:** Claimed Axis is the only NDAA/TAA + CAGE-coded brand on our supported list. This drives potential federal/critical-infra deals.

**Action needed:** Confirm we actually have the Axis-specific implementation working in production (not just the Hikvision/Dahua handler that happens to also handle Axis). Federal customers will scrutinize this.

---

## 15. Phone agent SMS fallback for CSV-only POSes (`sms_fallback: True`)

**File:** `10-pos-integrations/_csv-only-systems.md` + `cake.md` + `talech.md` + `rezku.md`.

**Context:** Mentioned that systems with `sms_fallback: True` in registry can route phone agent orders via SMS. Listed Cake, Talech, Rezku, Harbortouch.

**Action needed:** Confirm SMS fallback is shipped and reps can confidently mention it. If not, soften the language.

---

## 16. Where to put the "Last updated" date going forward

All files end with `_Last updated: 2026-05-31_`. Without ownership / refresh cadence, these will go stale.

**Action needed:** Decide:
- Who owns refresh? (CS? Engineering? Sales ops?)
- Refresh cadence? (Monthly? Quarterly? On vendor change?)
- Automation possible? (CI check that flags any file >180 days old?)

---

_This file collects items flagged with `[NEEDS AIDAN INPUT]` during Phase 3. As items are answered, remove them and update the affected file(s)._

_Last updated: 2026-06-29_
