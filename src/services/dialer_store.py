"""Storage layer for the SR auto dialer.

Two implementations behind one async interface:

  * SupabaseDialerStore — PostgREST with the service-role key (all dialer
    writes are backend-only by design; the RLS plane gives reps/managers
    scoped SELECT for Realtime).
  * MemoryDialerStore — in-process store for previews and tests, selected by
    DIALER_DEV_STORE=1. Lets the whole workflow run BEFORE the
    20260812_autodialer.sql migration is hand-applied to live (doctrine: no
    automatic schema changes). Leads still come from the real DB via the
    caller's JWT — nothing here fabricates business data.

The router is the only caller; it owns auth/scoping. This layer is dumb CRUD.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("meridian.services.dialer_store")

_TABLES = ("dialer_sessions", "dialer_calls", "dialer_callbacks", "dialer_dnc")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _supabase_env() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.environ.get("SUPABASE_SERVICE_KEY", "")
    )
    return url, key


class SupabaseDialerStore:
    """PostgREST CRUD with the service key. Every method returns plain dicts."""

    async def _req(self, method: str, table: str, params: dict | None = None,
                   json: dict | list | None = None) -> list[dict]:
        import httpx

        url, key = _supabase_env()
        if not url or not key:
            raise RuntimeError("Supabase env missing for dialer store")
        headers = {
            "Authorization": f"Bearer {key}",
            "apikey": key,
            "Prefer": "return=representation",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method, f"{url}/rest/v1/{table}", headers=headers,
                params=params or {}, json=json,
            )
        if resp.status_code not in (200, 201, 204):
            logger.error("dialer store %s %s failed: %s %s",
                         method, table, resp.status_code, resp.text[:300])
            raise RuntimeError(f"dialer store {table} {resp.status_code}")
        if resp.status_code == 204 or not resp.text:
            return []
        body = resp.json()
        return body if isinstance(body, list) else [body]

    # Sessions
    async def create_session(self, fields: dict) -> dict:
        rows = await self._req("POST", "dialer_sessions", json=fields)
        return rows[0]

    async def current_session(self, rep_id: str) -> dict | None:
        rows = await self._req("GET", "dialer_sessions", params={
            "rep_id": f"eq.{rep_id}", "status": "neq.ended",
            "order": "started_at.desc", "limit": "1", "select": "*",
        })
        return rows[0] if rows else None

    async def get_session(self, session_id: str) -> dict | None:
        rows = await self._req("GET", "dialer_sessions",
                               params={"id": f"eq.{session_id}", "select": "*"})
        return rows[0] if rows else None

    async def update_session(self, session_id: str, fields: dict) -> dict | None:
        rows = await self._req("PATCH", "dialer_sessions",
                               params={"id": f"eq.{session_id}"},
                               json={**fields, "updated_at": _now_iso()})
        return rows[0] if rows else None

    async def live_sessions(self) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(hours=16)).isoformat()
        return await self._req("GET", "dialer_sessions", params={
            "status": "neq.ended", "started_at": f"gte.{since}",
            "order": "started_at.desc", "select": "*",
        })

    # Calls
    async def create_call(self, fields: dict) -> dict:
        rows = await self._req("POST", "dialer_calls", json=fields)
        return rows[0]

    async def get_call(self, call_id: str) -> dict | None:
        rows = await self._req("GET", "dialer_calls",
                               params={"id": f"eq.{call_id}", "select": "*"})
        return rows[0] if rows else None

    async def update_call(self, call_id: str, fields: dict) -> dict | None:
        rows = await self._req("PATCH", "dialer_calls",
                               params={"id": f"eq.{call_id}"}, json=fields)
        return rows[0] if rows else None

    async def list_calls(self, rep_ids: list[str] | None = None,
                         disposition: str | None = None,
                         since: str | None = None, live_only: bool = False,
                         limit: int = 200) -> list[dict]:
        params: dict = {"order": "created_at.desc", "limit": str(limit), "select": "*"}
        if rep_ids is not None:
            if not rep_ids:
                return []
            params["rep_id"] = f"in.({','.join(rep_ids)})"
        if disposition:
            params["disposition"] = f"eq.{disposition}"
        if since:
            params["created_at"] = f"gte.{since}"
        if live_only:
            params["status"] = "in.(dialing,ringing,connected)"
        return await self._req("GET", "dialer_calls", params=params)

    async def last_attempts(self, rep_id: str, since: str) -> dict[str, str]:
        rows = await self._req("GET", "dialer_calls", params={
            "rep_id": f"eq.{rep_id}", "created_at": f"gte.{since}",
            "select": "lead_id,created_at", "order": "created_at.desc", "limit": "500",
        })
        out: dict[str, str] = {}
        for r in rows:
            lid = r.get("lead_id")
            if lid and lid not in out:
                out[lid] = r.get("created_at") or ""
        return out

    # Callbacks
    async def create_callback(self, fields: dict) -> dict:
        rows = await self._req("POST", "dialer_callbacks", json=fields)
        return rows[0]

    async def list_callbacks(self, rep_ids: list[str] | None = None,
                             status: str = "pending", limit: int = 200) -> list[dict]:
        params: dict = {"order": "due_at.asc", "limit": str(limit), "select": "*"}
        if status:
            params["status"] = f"eq.{status}"
        if rep_ids is not None:
            if not rep_ids:
                return []
            params["rep_id"] = f"in.({','.join(rep_ids)})"
        return await self._req("GET", "dialer_callbacks", params=params)

    async def update_callback(self, callback_id: str, fields: dict) -> dict | None:
        rows = await self._req("PATCH", "dialer_callbacks",
                               params={"id": f"eq.{callback_id}"},
                               json={**fields, "updated_at": _now_iso()})
        return rows[0] if rows else None

    # DNC
    async def dnc_filter(self, phones: list[str]) -> set[str]:
        if not phones:
            return set()
        rows = await self._req("GET", "dialer_dnc", params={
            "phone_e164": f"in.({','.join(phones)})", "select": "phone_e164",
        })
        return {r["phone_e164"] for r in rows}

    async def dnc_add(self, phone: str, market: str, reason: str,
                      rep_id: str | None) -> None:
        try:
            await self._req("POST", "dialer_dnc", params={"on_conflict": "phone_e164"},
                            json={"phone_e164": phone, "market": market,
                                  "reason": reason, "added_by_rep_id": rep_id})
        except RuntimeError:
            # Duplicate without merge preference — the number is already listed.
            pass

    async def dnc_list(self, limit: int = 500) -> list[dict]:
        return await self._req("GET", "dialer_dnc",
                               params={"order": "created_at.desc",
                                       "limit": str(limit), "select": "*"})

    async def dnc_remove(self, phone: str) -> None:
        await self._req("DELETE", "dialer_dnc", params={"phone_e164": f"eq.{phone}"})


class MemoryDialerStore:
    """Preview/test store — same interface, plain dicts in process memory."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.calls: dict[str, dict] = {}
        self.callbacks: dict[str, dict] = {}
        self.dnc: dict[str, dict] = {}

    @staticmethod
    def _new(fields: dict) -> dict:
        return {"id": str(uuid.uuid4()), "created_at": _now_iso(), **fields}

    async def create_session(self, fields: dict) -> dict:
        row = self._new({"status": "active", "dials": 0, "connects": 0,
                         "talk_seconds": 0, "started_at": _now_iso(),
                         "ended_at": None, "updated_at": _now_iso(), **fields})
        self.sessions[row["id"]] = row
        return row

    async def current_session(self, rep_id: str) -> dict | None:
        live = [s for s in self.sessions.values()
                if s["rep_id"] == rep_id and s["status"] != "ended"]
        live.sort(key=lambda s: s["started_at"], reverse=True)
        return live[0] if live else None

    async def get_session(self, session_id: str) -> dict | None:
        return self.sessions.get(session_id)

    async def update_session(self, session_id: str, fields: dict) -> dict | None:
        row = self.sessions.get(session_id)
        if row:
            row.update(fields)
            row["updated_at"] = _now_iso()
        return row

    async def live_sessions(self) -> list[dict]:
        rows = [s for s in self.sessions.values() if s["status"] != "ended"]
        rows.sort(key=lambda s: s["started_at"], reverse=True)
        return rows

    async def create_call(self, fields: dict) -> dict:
        row = self._new({"status": "queued", "notes": "", "sim": False,
                         "started_at": _now_iso(), "answered_at": None,
                         "ended_at": None, "duration_seconds": None,
                         "talk_seconds": None, "disposition": None,
                         "telnyx_call_id": None, "blocked_reason": None,
                         "disposition_by": None, "disposition_at": None, **fields})
        self.calls[row["id"]] = row
        return row

    async def get_call(self, call_id: str) -> dict | None:
        return self.calls.get(call_id)

    async def update_call(self, call_id: str, fields: dict) -> dict | None:
        row = self.calls.get(call_id)
        if row:
            row.update(fields)
        return row

    async def list_calls(self, rep_ids: list[str] | None = None,
                         disposition: str | None = None,
                         since: str | None = None, live_only: bool = False,
                         limit: int = 200) -> list[dict]:
        rows = list(self.calls.values())
        if rep_ids is not None:
            rows = [r for r in rows if r["rep_id"] in rep_ids]
        if disposition:
            rows = [r for r in rows if r.get("disposition") == disposition]
        if since:
            rows = [r for r in rows if (r.get("created_at") or "") >= since]
        if live_only:
            rows = [r for r in rows if r["status"] in ("dialing", "ringing", "connected")]
        rows.sort(key=lambda r: r["created_at"], reverse=True)
        return rows[:limit]

    async def last_attempts(self, rep_id: str, since: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for r in sorted(self.calls.values(), key=lambda r: r["created_at"], reverse=True):
            if r["rep_id"] == rep_id and r["created_at"] >= since and r.get("lead_id"):
                out.setdefault(r["lead_id"], r["created_at"])
        return out

    async def create_callback(self, fields: dict) -> dict:
        row = self._new({"status": "pending", "note": "", "timezone": "",
                         "updated_at": _now_iso(), **fields})
        self.callbacks[row["id"]] = row
        return row

    async def list_callbacks(self, rep_ids: list[str] | None = None,
                             status: str = "pending", limit: int = 200) -> list[dict]:
        rows = list(self.callbacks.values())
        if status:
            rows = [r for r in rows if r["status"] == status]
        if rep_ids is not None:
            rows = [r for r in rows if r["rep_id"] in rep_ids]
        rows.sort(key=lambda r: r["due_at"])
        return rows[:limit]

    async def update_callback(self, callback_id: str, fields: dict) -> dict | None:
        row = self.callbacks.get(callback_id)
        if row:
            row.update(fields)
            row["updated_at"] = _now_iso()
        return row

    async def dnc_filter(self, phones: list[str]) -> set[str]:
        return {p for p in phones if p in self.dnc}

    async def dnc_add(self, phone: str, market: str, reason: str,
                      rep_id: str | None) -> None:
        self.dnc[phone] = self._new({"phone_e164": phone, "market": market,
                                     "reason": reason, "added_by_rep_id": rep_id})

    async def dnc_list(self, limit: int = 500) -> list[dict]:
        rows = sorted(self.dnc.values(), key=lambda r: r["created_at"], reverse=True)
        return rows[:limit]

    async def dnc_remove(self, phone: str) -> None:
        self.dnc.pop(phone, None)


_memory_store: MemoryDialerStore | None = None


def dev_store_active() -> bool:
    return os.environ.get("DIALER_DEV_STORE", "").strip() in ("1", "true", "yes")


def get_store() -> SupabaseDialerStore | MemoryDialerStore:
    global _memory_store
    if dev_store_active():
        if _memory_store is None:
            _memory_store = MemoryDialerStore()
        return _memory_store
    return SupabaseDialerStore()
