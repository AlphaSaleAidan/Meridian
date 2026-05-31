# Camera Offline

When the dashboard shows a camera as offline or "stream failed."

## Quick triage

1. Is the camera physically powered on? (Check the camera, the PoE switch, the merchant's network)
2. Can the merchant access the camera's admin UI from their local network? (`http://camera-ip` in a browser)
3. Can VLC play the RTSP URL from a computer on the same network as Meridian's edge?

If any of those fail, the problem is upstream of Meridian.

## Symptom: "Camera shows offline immediately after adding it"

| Cause | Fix |
|-------|-----|
| Wrong RTSP URL format | Test in VLC first — see [/20-camera-integrations/_how-to-connect-any-camera.md](../20-camera-integrations/_how-to-connect-any-camera.md) |
| Password has special characters | URL-encode the password (`@` → `%40`, `#` → `%23`, etc.) |
| Wrong port | RTSP is usually 554; UniFi RTSPS is **7441**; some cameras use non-standard ports |
| Camera credentials wrong | Re-enter; default `admin/admin` or `admin/12345` if never changed (force them to set a real password) |
| Camera doesn't have RTSP enabled | Camera admin UI → Network → enable RTSP / ONVIF |

## Symptom: "Camera was online for hours/days, now offline"

| Cause | Fix |
|-------|-----|
| Network blip (most common) | Camera auto-reconnects within 60 sec. If persistent, check merchant's internet |
| Camera firmware update changed RTSP path | Especially Hikvision — recheck path in camera admin |
| Concurrent stream limit hit | Some cameras max 2–3 concurrent RTSP clients; merchant viewing in their app + us = limit | Close their viewer or upgrade camera |
| Password changed | If merchant rotated camera password, update in Meridian |
| Camera physically disconnected | PoE cable, power outage at merchant location |
| RTSP service crashed on camera | Reboot the camera (power cycle) |

## Symptom: "VLC plays the stream, but Meridian says offline"

This means the camera is fine; the connection from Meridian's edge to the camera is the problem.

| Cause | Fix |
|-------|-----|
| Firewall blocking port from Meridian's edge | Whitelist Meridian edge IP, port 554 (or 7441 for RTSPS) |
| Camera on private network, merchant didn't expose it | Set up port forwarding OR install Meridian edge device on-site |
| NAT/CGNAT (cellular ISPs especially) | Port forwarding won't work; needs reverse-proxy or edge install |
| ISP blocking inbound RTSP | Some residential-grade ISPs block; needs business-class connection |

## Symptom: "Stream connects, but 0 people detected even when busy"

This is a detection problem, not a connection problem. Camera is fine.

| Cause | Fix |
|-------|-----|
| Camera angle wrong | Should be overhead 45° at entrance; straight-on misses people |
| Poor lighting | Increase camera exposure; consider IR-capable camera for low-light |
| Frame resolution too low | Some substreams are 480p — switch to higher substream or main stream |
| YOLO confidence threshold too high for conditions | Engineering can tune `confidence` in `src/camera/detector.py` (currently 0.35) |
| Camera is pointed at a wall/ceiling/floor | Sounds obvious; happens more than you'd think |

## Symptom: "Stream choppy / frames dropping"

| Cause | Fix |
|-------|-----|
| Bandwidth insufficient | Need 2–4 Mbps per camera; switch to substream (lower bitrate) |
| WiFi camera with weak signal | Switch to PoE/Ethernet |
| Camera CPU overloaded (running too many concurrent streams) | Reduce concurrent viewers; downgrade resolution |
| Our edge service overloaded (rare) | Engineering escalation |

## Symptom: "Camera is supported, but the brand isn't in your list"

Probably an OEM rebrand. Common ones:

| Their brand | Use this handler |
|-------------|------------------|
| LaView, ANNKE, EmpireTech, older Lorex, older Honeywell | Hikvision |
| Amcrest, newer Lorex (post-Dahua acquisition) | Dahua |
| Ubiquiti, AmpliFi cameras | UniFi |

If you can't figure out the OEM lineage, try Hikvision handler first (most common), then Dahua. If both fail, try the generic ONVIF discovery path in [/20-camera-integrations/_how-to-connect-any-camera.md](../20-camera-integrations/_how-to-connect-any-camera.md).

## Symptom: "Unsupported camera — Wyze, Nest, or Arlo"

Don't try to make these work. See:
- [/20-camera-integrations/wyze.md](../20-camera-integrations/wyze.md)
- [/20-camera-integrations/nest.md](../20-camera-integrations/nest.md)
- [/20-camera-integrations/arlo.md](../20-camera-integrations/arlo.md)

Recommend a $60 Reolink alongside what they've got.

## Escalation triggers

| Situation | Action |
|-----------|--------|
| Multiple cameras offline at same merchant simultaneously | Network issue, not Meridian — guide them to check their internet, then refer to their IT |
| Camera worked in VLC last week, still works in VLC, Meridian says offline | Likely Meridian-side; **High ticket** + engineering |
| Customer threatens cancel over camera issue | Critical ticket; if hardware is the root cause, offer to credit the Premium-tier difference for the month while they resolve |

---

_Last updated: 2026-05-31_
_Sourced from: src/camera/rtsp_handler.py + src/camera/detector.py + docs/playbook/_status/phase-2-decisions.md (supported + not-supported camera list) + recent fix commits (camera step path mismatch — `7d9ea4c fix(tour): camera step path matches the actual route`)_
