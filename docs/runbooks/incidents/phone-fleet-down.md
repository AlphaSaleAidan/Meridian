# SEV-1 — Phone fleet down / dead air

Symptom: demo or merchant lines ring to silence, calls drop, callers report a
robotic/broken agent, or Vapi shows errored calls. The chain is
**PSTN → Telnyx → Vapi → assistant-request → api.meridian.tips**; a break at
any hop kills calls.

## First 5 minutes — walk the chain backwards from the symptom

### Probe: does the backend serve a valid assistant?
```bash
source /root/.secrets/vapi.env
curl -s -X POST https://api.meridian.tips/api/vapi/webhook \
  -H "content-type: application/json" -H "x-vapi-secret: $VAPI_SERVER_SECRET" \
  -d '{"message":{"type":"assistant-request","phoneNumber":{"number":"+15068017904"},"call":{"id":"probe","customer":{"number":"+19495067494"}}}}' \
  | python3 -c "import json,sys; a=json.load(sys.stdin).get('assistant',{}); print('assistant:',a.get('name'),'| voice:',a.get('voice',{}).get('provider'))"
```
- **Returns an assistant** → backend + webhook + auth are fine; the break is
  Telnyx routing or Vapi (go to §Telnyx / §Vapi).
- **401** → the `x-vapi-secret` mismatch: `VAPI_SERVER_SECRET` in Railway ≠ what
  the numbers send. Re-sync (see §Secret).
- **5xx / no response** → backend down → [server-down.md](server-down.md) §B.

### §Telnyx routing (a line rings but no agent answers = dead air)
The classic failure: a DID routed to a dead voice connection (the retired
Pipecat "Cheap Voice" conn). Correct Vapi connection id: `2990417629031695653`.
```bash
source /root/.secrets/telnyx.env
curl -s -H "Authorization: Bearer $TELNYX_API_KEY" "https://api.telnyx.com/v2/phone_numbers?page%5Bsize%5D=50" \
 | python3 -c "import json,sys; [print(p['phone_number'],p.get('connection_name')) for p in json.load(sys.stdin)['data']]"
```
Any customer/demo line NOT on the "Vapi" connection → PATCH it:
`PATCH /v2/phone_numbers/{id}/voice` body `{"connection_id":"2990417629031695653"}`.

### §Vapi (calls error before the agent speaks)
- `dashboard.vapi.ai` → billing. **Out of credits stops the whole fleet** —
  see [vendor-billing.md](vendor-billing.md) §Vapi. This is the most common
  non-obvious cause.
- Concurrency cap hit (10) during a spike → calls queue/drop; usually transient.
- "sounds robotic" is a DIFFERENT bug, not an outage: Vapi TTS cache replaying a
  flat take. Check the call's `costBreakdown.ttsCharacters` — `0` = cache hit.
  Fix: `cachingEnabled:false` on the persona voice (already set fleet-wide;
  re-verify if a new voice was added).

### §Secret (re-sync serverUrl secret without breaking auth)
Vapi REDACTS the stored server secret on GETs but still stores it. Re-point ONE
number first, secret re-supplied in the same PATCH, verify with a live call
before touching the rest. Never blind-PATCH all 10 — a cleared secret breaks auth.

## Mitigate while diagnosing
Merchant line dead, fix not immediate → the assistant-request inactive/fallback
path keeps SOMETHING answering; for a paying merchant, forward their DID to a
staff cell at the Telnyx level as a stopgap and note it in the timeline.

## Verify
Real inbound call to the affected number (or ask Aidan to dial +1 506 801 7904
for the demo line) — greeting plays, agent responds. `railway logs | grep vapi`
shows the assistant-request 200.

## Prevent
The pool DIDs point at `api.meridian.tips` directly (not the Contabo nginx SPOF)
since 2026-08-06 — keep it that way. Add new merchant DIDs on the "Vapi"
connection from the start.
