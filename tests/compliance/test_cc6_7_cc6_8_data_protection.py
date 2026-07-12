"""
CC6.7 — Transmission security: external service calls ride TLS.
CC6.8 / PCI-adjacent — Cardholder data: no primary account number (PAN) or
CVV is ever persisted; only brand + last-4 may be stored.

Static checks over src/ and services/phone_agent/ — the code-level complement
to the platform posture docs (PR #196 /compliance package).
"""
import re
from pathlib import Path

CONTROL = "CC6.7/CC6.8"

REPO = Path(__file__).parents[2]
CODE_DIRS = [REPO / "src", REPO / "services" / "phone_agent"]

_HTTP_URL_RE = re.compile(r"[\"'](http://[^\"'\s]+)[\"']")
_LOCAL_OK = re.compile(r"http://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\]|host\.docker\.internal|.*\.local\b|.*\{)")
# W3C/XML namespace identifiers etc. are not network calls.
_SCHEMA_OK = re.compile(r"http://(www\.w3\.org|schemas\.|xml\.|purl\.org|ns\.adobe)")


def _py_files():
    for d in CODE_DIRS:
        yield from d.rglob("*.py")


def test_no_plaintext_http_to_external_services():
    violations = []
    for path in _py_files():
        for m in _HTTP_URL_RE.finditer(path.read_text(errors="ignore")):
            url = m.group(1)
            if _LOCAL_OK.match(url) or _SCHEMA_OK.match(url):
                continue
            violations.append(f"{path.relative_to(REPO)}: {url}")
    assert not violations, (
        "Plaintext http:// URLs to non-local hosts (credentials/PII would "
        "transit unencrypted):\n  " + "\n  ".join(sorted(set(violations))[:20])
    )


def test_no_pan_or_cvv_persistence():
    """Nothing may write full card numbers or CVV to storage.

    Heuristic: any dict-literal key / SQL column named like a full PAN or CVV
    in code that also touches persistence (supabase/insert/update/execute).
    card_last4 / card_brand are the only permitted card artifacts.
    """
    pan_key = re.compile(r"[\"'](card_number|full_pan|pan|cvv|cvc|security_code)[\"']\s*[:=]", re.IGNORECASE)
    persist_hint = re.compile(r"supabase|/rest/v1/|insert|upsert|\.execute\(|INSERT INTO", re.IGNORECASE)
    violations = []
    for path in _py_files():
        text = path.read_text(errors="ignore")
        if not persist_hint.search(text):
            continue
        for m in pan_key.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            line = text.splitlines()[line_no - 1].strip()
            # Reading a value out of a provider payload is fine; storing is not.
            # Flag either way — reviewed exclusions go below, explicitly.
            violations.append(f"{path.relative_to(REPO)}:{line_no}: {line[:100]}")
    reviewed_ok: set[str] = set()  # add "path:line: snippet" here only in review
    remaining = [v for v in violations if v not in reviewed_ok]
    assert not remaining, (
        "Possible PAN/CVV persistence (only brand + last-4 may be stored):\n  "
        + "\n  ".join(remaining)
    )


def test_card_on_phone_stores_only_last4():
    """The DTMF card-capture module must only expose last-4 for storage."""
    module = REPO / "services" / "phone_agent" / "card_on_phone.py"
    if not module.exists():
        return  # module retired — nothing to check
    text = module.read_text()
    assert "last4" in text or "last_4" in text, (
        "card_on_phone.py no longer references last4 — verify storage shape."
    )
    assert not re.search(r"card_number[\"']?\s*:", text), (
        "card_on_phone.py appears to store a full card number."
    )
