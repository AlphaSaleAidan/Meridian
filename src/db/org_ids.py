"""
Org-id shaping for the uuid-keyed org tables (organizations, pos_connections).

Merchants authenticated off a `businesses` row carry TEXT ids shaped
`biz_<hex>` (frontend auth.tsx passes them as org_id verbatim), but
organizations.id and pos_connections.org_id are UUID columns — so a biz_
merchant could never complete OAuth connect storage: the insert failed the
uuid cast and every one-click connect ended in "Connected but failed to
save". UUID-keyed merchants were unaffected.

The fix is a deterministic companion UUID: uuid5(_NS, biz_id). Same biz_ id →
same UUID forever, computed identically at store time and at every lookup, so
no mapping table is needed. The businesses row keeps its own TEXT id
everywhere else (phone_agent_config.merchant_id, businesses updates, etc.) —
ONLY reads/writes against the uuid-keyed org tables go through this mapping.
"""
import re
import uuid

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_BIZ_RE = re.compile(r"^biz_[0-9a-f]{16,40}$", re.I)

# Fixed application namespace for the uuid5 derivation. NEVER change this
# value: every stored biz_-merchant connection is keyed by it, and a new
# namespace would orphan them all.
_NS = uuid.UUID("a3c1b2d4-5e6f-4a70-9b81-2c3d4e5f6a70")


def is_biz_id(org_id: str) -> bool:
    return bool(_BIZ_RE.match(org_id or ""))


def connection_org_id(org_id: str) -> str:
    """The id to use against uuid-keyed org tables for this caller org id.

    - UUID-shaped ids pass through unchanged (the common organizations case).
    - biz_ ids map to their deterministic companion UUID.
    - Anything else returns "" — callers keep their existing invalid-shape
      handling (report not-connected / reject), nothing new reaches the DB.
    """
    oid = (org_id or "").strip()
    if _UUID_RE.match(oid):
        return oid.lower()
    if _BIZ_RE.match(oid):
        return str(uuid.uuid5(_NS, oid.lower()))
    return ""
