"""Shared post-OAuth return-path allowlist for the POS connect callbacks.

Both the Square (`oauth.py`) and Clover (`clover_oauth.py`) callbacks redirect the
merchant back to an on-site wizard after the provider round-trip. The target path
must be allowlisted so the callback can't be turned into an open redirect.

This logic was duplicated as `_safe_return_to` in both files and drifted — the US
`/onboard` flow was never added, so US merchants got bounced to `/app/settings`
after authorizing. Centralizing it here keeps one allowlist for both callers.
"""

# On-site path prefixes a post-OAuth redirect may target. Prefix-match only; the
# callbacks prepend FRONTEND_URL, so an allowlisted value always resolves
# same-origin. Add a prefix here (not in the callback files) to enable a surface.
ALLOWED_RETURN_PREFIXES = (
    # Canada
    "/canada/merchant",
    "/canada/onboard",
    "/canada/dashboard",
    "/canada/setup",
    # US
    "/us/onboard",
    "/us/dashboard",
    "/us/setup",
    # shared surfaces
    "/onboard",
    "/app",
    "/dashboard",
    "/settings",
)


def safe_return_to(return_to: str | None) -> str:
    """Return ``return_to`` if it's an allowlisted on-site path, else ``""`` (the
    caller then falls back to its default target).

    Rejects empty values, protocol-relative (``//host``) and absolute
    (``scheme://``) URLs so this can't become an open redirect.
    """
    if not return_to or return_to.startswith("//") or "://" in return_to:
        return ""
    if any(return_to.startswith(p) for p in ALLOWED_RETURN_PREFIXES):
        return return_to
    return ""
