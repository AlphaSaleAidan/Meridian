"""DEFCON pager — the single fan-out for a "DEFCON moment".

Every high-severity detector (edge watchdog, billing monitor, settlement
reconciliation, and anything added later) routes through `notify_defcon(...)`
so a DEFCON-1/2 event pages EVERY responder at once — today Aidan and Nathan —
with the level, what happened, and the exact protocol to open.

Design contract:
  - Pages only at or above the threshold (default DEFCON 2, i.e. levels 1-2).
    Lower levels are logged and returned but not paged, so noise never trains
    people to ignore the pager.
  - Recipients come from env `MERIDIAN_DEFCON_RESPONDERS` (comma-separated);
    defaults to the two operators so it works before anything is configured.
  - Optional SMS to `MERIDIAN_DEFCON_SMS` numbers for DEFCON-1 only (env-gated;
    silent no-op when unset).
  - Dedupe: the same (level, event-key) doesn't re-page within a cooldown
    window, so a flapping detector can't spam the pager.
  - Fail-quiet EVERYWHERE: paging never raises and never blocks the detector
    that called it. A missing email transport logs and moves on.

Env:
  MERIDIAN_DEFCON_RESPONDERS   comma emails (default Aidan + Nathan)
  MERIDIAN_DEFCON_PAGE_LEVEL   page at this level or worse (default 2)
  MERIDIAN_DEFCON_COOLDOWN_S   per-event re-page cooldown (default 1800)
  MERIDIAN_DEFCON_SMS          comma phone numbers for DEFCON-1 SMS (optional)
"""
import logging
import os
import time

logger = logging.getLogger("meridian.services.defcon_alert")

DEFAULT_RESPONDERS = "aidanpierce72@gmail.com,nathaniel.t.wong@gmail.com"
DEFAULT_PAGE_LEVEL = 2
DEFAULT_COOLDOWN_S = 1800

_LEVEL_NAME = {1: "CATASTROPHIC", 2: "CRITICAL", 3: "MAJOR", 4: "MINOR", 5: "NORMAL"}

# (level, event_key) -> last paged epoch, for the cooldown.
_last_paged: dict[tuple[int, str], float] = {}


def responders() -> list[str]:
    raw = os.environ.get("MERIDIAN_DEFCON_RESPONDERS", DEFAULT_RESPONDERS)
    return [e.strip() for e in raw.split(",") if e.strip()]


def _page_level() -> int:
    try:
        return int(os.environ.get("MERIDIAN_DEFCON_PAGE_LEVEL", str(DEFAULT_PAGE_LEVEL)))
    except ValueError:
        return DEFAULT_PAGE_LEVEL


def _cooldown_s() -> int:
    try:
        return int(os.environ.get("MERIDIAN_DEFCON_COOLDOWN_S", str(DEFAULT_COOLDOWN_S)))
    except ValueError:
        return DEFAULT_COOLDOWN_S


def _sms_numbers() -> list[str]:
    raw = os.environ.get("MERIDIAN_DEFCON_SMS", "")
    return [n.strip() for n in raw.split(",") if n.strip()]


def _should_page(level: int, event_key: str, now: float) -> bool:
    if level > _page_level():
        return False
    last = _last_paged.get((level, event_key))
    if last is not None and (now - last) < _cooldown_s():
        return False
    _last_paged[(level, event_key)] = now
    return True


def _protocol_url(protocol: str) -> str:
    if not protocol:
        return "docs/runbooks/incidents/DEFCON.md"
    if "/" in protocol:
        return protocol
    return f"docs/runbooks/incidents/{protocol}"


async def notify_defcon(level: int, event: str, detail: str = "",
                        protocol: str = "", *, event_key: str = "",
                        now: float | None = None) -> dict:
    """Page all responders for a DEFCON `level` (1 worst .. 5 normal) event.

    Returns {"paged": bool, "level": int, "recipients": [...], "reason": str}.
    Never raises.
    """
    result = {"paged": False, "level": level, "recipients": [], "reason": ""}
    try:
        key = event_key or event
        ts = now if now is not None else time.time()
        if not _should_page(level, key, ts):
            result["reason"] = ("below page threshold" if level > _page_level()
                                else "cooldown")
            logger.info("DEFCON %s (%s) — not paging (%s)", level, event, result["reason"])
            return result

        name = _LEVEL_NAME.get(level, "UNKNOWN")
        proto = _protocol_url(protocol)
        title = f"DEFCON {level} — {name}: {event}"
        body = (
            f"DEFCON {level} ({name}) declared.\n\n"
            f"Event: {event}\n"
            f"Detail: {detail}\n\n"
            f"RUN: {proto}\n"
            f"Full readiness catalog: docs/runbooks/incidents/DEFCON.md\n\n"
            f"This is an automated page to all DEFCON responders. First: scope, "
            f"then mitigate (the protocol's mitigation restores service before "
            f"root-cause), then log the timeline.")
        to = responders()
        sev = "high" if level <= 2 else "medium"

        sent = 0
        for addr in to:
            try:
                from ..email.send import send_anomaly_alert
                await send_anomaly_alert(addr, "Meridian DEFCON", title, body,
                                         severity=sev)
                sent += 1
            except Exception as e:  # noqa: BLE001 — one bad recipient never blocks the rest
                logger.error("DEFCON page to %s failed: %s", addr, e)

        # DEFCON-1 also fires SMS to any configured responder numbers.
        if level == 1 and _sms_numbers():
            for num in _sms_numbers():
                try:
                    from ..sms.client import send_sms
                    await send_sms(num, f"DEFCON 1 {event} — RUN {proto}")
                except Exception as e:  # noqa: BLE001
                    logger.error("DEFCON SMS to %s failed: %s", num, e)

        logger.critical("DEFCON %s PAGED: %s — %d/%d responders, protocol %s",
                        level, event, sent, len(to), proto)
        result.update(paged=True, recipients=to, reason=f"paged {sent}/{len(to)}")
        return result
    except Exception as e:  # noqa: BLE001 — the pager never breaks its caller
        logger.error("notify_defcon failed for '%s': %s", event, e)
        result["reason"] = f"error: {e}"
        return result
