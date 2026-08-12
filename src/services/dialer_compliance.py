"""Dial-time compliance gate for the SR auto dialer.

Two hard blocks, evaluated BEFORE any call leg is created (sim or real):

  1. Internal DNC — checked by the router against dialer_dnc (store layer).
  2. Calling-hours window in the LEAD's local time, derived from the NANP
     area code:
       Canada (CRTC Unsolicited Telecommunications Rules):
         Mon-Fri 09:00-21:30, Sat-Sun 10:00-18:00 local.
       US (TCPA/TSR): 08:00-21:00 local, all days.

Fail-safe posture: an area code we cannot place (toll-free, unknown, non-NANP)
is BLOCKED, not warned. Provincial overrides (e.g. Quebec) and the national
DNCL scrub are org-level follow-ups tracked in docs/AUTODIALER_PLAN.md —
this gate is necessary, not sufficient.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .phone_safety import normalize_e164

# ── Area code → IANA timezone ─────────────────────────────────────────────────
# Split-zone codes use the majority zone; the window math stays conservative
# enough that a one-hour skew cannot land outside the legal envelope by more
# than the split itself. Unknown codes fail closed.

_CA_ZONES: dict[str, tuple[str, ...]] = {
    "America/Vancouver": ("236", "250", "604", "672", "778"),
    "America/Edmonton": ("368", "403", "587", "780", "825", "867"),
    "America/Regina": ("306", "639", "474"),
    "America/Winnipeg": ("204", "431", "584"),
    "America/Toronto": (
        # Ontario
        "226", "249", "289", "343", "365", "382", "416", "437", "519", "548",
        "613", "647", "683", "705", "742", "753", "807", "905", "942",
        # Quebec
        "263", "354", "367", "418", "438", "450", "468", "514", "579", "581",
        "819", "873",
    ),
    "America/Halifax": ("428", "506", "782", "902"),
    "America/St_Johns": ("709", "879"),
}

_US_ZONES: dict[str, tuple[str, ...]] = {
    "America/New_York": (
        "201", "202", "203", "207", "212", "215", "216", "220", "223", "229",
        "231", "234", "239", "240", "248", "252", "260", "267", "269", "272",
        "276", "301", "302", "304", "305", "313", "315", "317", "321", "326",
        "330", "332", "336", "339", "347", "351", "352", "380", "386", "401",
        "404", "407", "410", "412", "413", "419", "423", "434", "440", "443",
        "445", "463", "470", "475", "478", "484", "502", "508", "513", "516",
        "517", "518", "540", "551", "561", "567", "570", "571", "574", "585",
        "586", "603", "606", "607", "609", "610", "614", "616", "617", "631",
        "640", "646", "667", "678", "679", "680", "681", "689", "703", "704",
        "706", "716", "717", "718", "724", "727", "732", "734", "740", "743",
        "754", "757", "762", "765", "770", "772", "774", "781", "786", "802",
        "803", "804", "810", "812", "813", "814", "826", "828", "838", "839",
        "843", "845", "848", "854", "856", "857", "859", "860", "862", "863",
        "864", "865", "878", "904", "906", "908", "910", "912", "914", "917",
        "919", "929", "930", "934", "937", "941", "943", "947",
        "948", "954", "959", "973", "978", "980", "984", "989",
    ),
    "America/Chicago": (
        "205", "210", "214", "217", "218", "219", "224", "225", "228", "251",
        "254", "256", "262", "270", "274", "281", "308", "309", "312", "314",
        "316", "318", "319", "320", "325", "327", "331", "334", "337", "346",
        "361", "364", "402", "405", "409", "414", "417", "430", "432", "447",
        "469", "479", "501", "504", "507", "512", "515", "531", "534", "539",
        "563", "572", "573", "580", "601", "605", "608", "612", "615", "618",
        "620", "629", "630", "636", "641", "651", "659", "660", "662", "682",
        "701", "708", "712", "713", "715", "726", "731", "737", "763", "769",
        "773", "779", "785", "806", "815", "816", "817", "830", "832", "847",
        "850", "870", "872", "901", "903", "913", "918", "920", "931", "936",
        "938", "940", "945", "952", "956", "972", "979", "985",
    ),
    "America/Denver": (
        "208", "303", "307", "385", "406", "435", "505", "575", "719", "720",
        "801", "915", "970", "983", "986",
    ),
    "America/Phoenix": ("480", "520", "602", "623", "928"),
    "America/Los_Angeles": (
        "206", "209", "213", "253", "279", "310", "323", "341", "350", "360",
        "408", "415", "424", "425", "442", "458", "503", "509", "510", "530",
        "541", "559", "562", "564", "619", "626", "628", "650", "657", "661",
        "669", "702", "707", "714", "725", "747", "760", "775", "805", "818",
        "820", "831", "840", "858", "909", "916", "925", "949", "951", "971",
    ),
    "America/Anchorage": ("907",),
    "Pacific/Honolulu": ("808",),
}

_TOLL_FREE = {"800", "822", "833", "844", "855", "866", "877", "880", "888"}

AREA_CODE_TZ: dict[str, str] = {}
CA_AREA_CODES: set[str] = set()
for _tz, _codes in _CA_ZONES.items():
    for _c in _codes:
        AREA_CODE_TZ[_c] = _tz
        CA_AREA_CODES.add(_c)
for _tz, _codes in _US_ZONES.items():
    for _c in _codes:
        AREA_CODE_TZ.setdefault(_c, _tz)

# (start, end) minutes-since-midnight, inclusive start / exclusive end.
_CRTC_WEEKDAY = (9 * 60, 21 * 60 + 30)
_CRTC_WEEKEND = (10 * 60, 18 * 60)
_TCPA_ALL_DAYS = (8 * 60, 21 * 60)


@dataclass(frozen=True)
class CallWindowCheck:
    allowed: bool
    reason: str            # "" when allowed; else calling_window | invalid_number | unknown_area_code
    country: str           # "CA" | "US" | ""
    tz: str                # IANA zone or ""
    local_time: str        # lead-local ISO timestamp or ""
    window_label: str      # human-readable window for the UI


def area_code_of(phone_e164: str) -> str:
    """NANP area code of an E.164 number, or "" when not a +1 NANP number."""
    norm = normalize_e164(phone_e164)
    if not norm.startswith("+1") or len(norm) != 12:
        return ""
    return norm[2:5]


def _window_for(country: str, local: datetime) -> tuple[tuple[int, int], str]:
    if country == "CA":
        if local.weekday() >= 5:  # Sat/Sun
            return _CRTC_WEEKEND, "CRTC weekend window 10:00-18:00 local"
        return _CRTC_WEEKDAY, "CRTC weekday window 09:00-21:30 local"
    return _TCPA_ALL_DAYS, "TCPA window 08:00-21:00 local"


def check_calling_window(phone: str, now: datetime | None = None) -> CallWindowCheck:
    """Hard dial-time gate. Unknown/toll-free/non-NANP numbers are BLOCKED."""
    code = area_code_of(phone)
    if not code:
        return CallWindowCheck(False, "invalid_number", "", "", "", "")
    if code in _TOLL_FREE or code not in AREA_CODE_TZ:
        return CallWindowCheck(False, "unknown_area_code", "", "", "",
                               "no local-time mapping for this area code")
    country = "CA" if code in CA_AREA_CODES else "US"
    tz_name = AREA_CODE_TZ[code]
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    local = now_utc.astimezone(ZoneInfo(tz_name))
    (start, end), label = _window_for(country, local)
    minutes = local.hour * 60 + local.minute
    allowed = start <= minutes < end
    return CallWindowCheck(
        allowed=allowed,
        reason="" if allowed else "calling_window",
        country=country,
        tz=tz_name,
        local_time=local.isoformat(timespec="minutes"),
        window_label=label,
    )
