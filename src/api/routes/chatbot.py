"""Owner-customizable customer-facing chatbot (Workstream 1d).

  GET  /api/chatbot/config?org_id            → fetch this org's bot config (member)
  PUT  /api/chatbot/config                    → owner customizes the bot (manage_chatbot)
  POST /api/chatbot/send                       → visitor-facing send endpoint

The send endpoint routes LLM calls through the EXISTING LiteLLM gateway
(src/ai/llm_layer) so the shared rpm/budget guards apply. The system prompt is
assembled from the owner's config (business name/tone, allowed topics, canned
answers, escalation). Canned answers are matched BEFORE any LLM call (cheap +
deterministic), and escalation short-circuits to a human hand-off message.

SECURITY:
  - config GET/PUT are org-gated (member read; manage_chatbot to write).
  - /send is intentionally UNAUTHENTICATED (it's the public widget on the
    merchant's own site) but is keyed by a required, existing, ENABLED org
    config — an unknown/disabled org gets a 404/disabled response, never an LLM
    call. Transcript rows are org-scoped. Input is length-capped.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import require_service_auth
from .. import rbac
from ...db import get_db

logger = logging.getLogger("meridian.api.chatbot")
router = APIRouter(prefix="/api/chatbot", tags=["team-management"])

_MAX_MSG = 1000
_TONE_HINT = {
    "friendly": "warm, upbeat, and approachable",
    "professional": "polished, concise, and professional",
    "casual": "relaxed and conversational",
    "formal": "formal and precise",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatbotConfig(BaseModel):
    org_id: str
    enabled: bool = False
    business_name: str = ""
    tone: str = "friendly"
    greeting: str = ""
    allowed_topics: list = Field(default_factory=list)
    canned_answers: list = Field(default_factory=list)
    escalation_to_human: bool = False
    escalation_contact: str = ""


class ChatSend(BaseModel):
    org_id: str
    session_id: str = ""
    message: str


def _sanitize_config(body: ChatbotConfig) -> dict:
    tone = body.tone if body.tone in _TONE_HINT else "friendly"
    topics = [str(t).strip()[:64] for t in (body.allowed_topics or []) if str(t).strip()][:40]
    canned = []
    for c in (body.canned_answers or [])[:100]:
        if isinstance(c, dict) and c.get("q") and c.get("a"):
            canned.append({"q": str(c["q"])[:200], "a": str(c["a"])[:1000]})
    return {
        "enabled": bool(body.enabled),
        "business_name": (body.business_name or "").strip()[:120],
        "tone": tone,
        "greeting": (body.greeting or "").strip()[:400],
        "allowed_topics": topics,
        "canned_answers": canned,
        "escalation_to_human": bool(body.escalation_to_human),
        "escalation_contact": (body.escalation_contact or "").strip()[:200],
    }


@router.get("/config")
async def get_config(org_id: str = Query(...), principal=Depends(require_service_auth)):
    # Any member may view the config; only manage_chatbot may write.
    await rbac.resolve_access(principal, org_id)
    db = get_db()
    rows = await db.select("chatbot_config", filters={"org_id": f"eq.{org_id}"}, limit=1)
    if rows:
        return {"config": rows[0]}
    return {"config": {
        "org_id": org_id, "enabled": False, "business_name": "", "tone": "friendly",
        "greeting": "", "allowed_topics": [], "canned_answers": [],
        "escalation_to_human": False, "escalation_contact": "",
    }}


@router.put("/config")
async def put_config(body: ChatbotConfig, principal=Depends(require_service_auth)):
    await rbac.require_action(principal, body.org_id, "manage_chatbot")
    db = get_db()
    payload = {"org_id": body.org_id, "updated_at": _now_iso(), **_sanitize_config(body)}
    await db.upsert("chatbot_config", payload, on_conflict="org_id")
    return {"config": payload}


def _match_canned(message: str, canned: list) -> Optional[str]:
    msg = (message or "").lower()
    for c in canned or []:
        q = str(c.get("q", "")).lower().strip()
        if q and (q in msg or msg in q):
            return c.get("a")
    return None


def _build_system_prompt(cfg: dict) -> str:
    name = cfg.get("business_name") or "this business"
    tone = _TONE_HINT.get(cfg.get("tone", "friendly"), _TONE_HINT["friendly"])
    topics = cfg.get("allowed_topics") or []
    topics_line = (
        f"You may ONLY discuss: {', '.join(topics)}. If asked about anything else, "
        "politely say you can only help with those topics."
        if topics else
        "Keep answers focused on helping this business's customers."
    )
    esc = ""
    if cfg.get("escalation_to_human"):
        contact = cfg.get("escalation_contact") or "a team member"
        esc = (
            f" If the customer needs a human or you cannot help, direct them to {contact} "
            "and set \"escalate\" to true."
        )
    return (
        f"You are the customer-service assistant for {name}. "
        f"Speak in a {tone} tone. {topics_line}{esc} "
        "Respond ONLY with a JSON object: "
        '{"reply": "<your answer>", "escalate": <true|false>}. No markdown.'
    )


async def _llm_reply(cfg: dict, message: str, org_id: str) -> dict:
    """Route through the shared LiteLLM gateway. Returns {reply, escalate}."""
    try:
        from ...ai.llm_layer import _call_llm  # shared Router + rpm/budget guards
    except Exception:  # noqa: BLE001
        return {"reply": "", "escalate": bool(cfg.get("escalation_to_human"))}
    messages = [
        {"role": "system", "content": _build_system_prompt(cfg)},
        {"role": "user", "content": message[:_MAX_MSG]},
    ]
    result = await _call_llm(
        messages,
        response_format={"type": "json_object"},
        org_id=org_id,
        agent_name="customer_chatbot",
    )
    if isinstance(result, dict) and result.get("reply"):
        return {"reply": str(result["reply"]), "escalate": bool(result.get("escalate", False))}
    return {"reply": "", "escalate": bool(cfg.get("escalation_to_human"))}


async def _log_transcript(org_id: str, session_id: str, role: str, content: str, escalated: bool = False):
    try:
        db = get_db()
        await db.insert("chatbot_messages", {
            "id": str(uuid4()),
            "org_id": org_id,
            "session_id": session_id or "anon",
            "role": role,
            "content": content[:4000],
            "escalated": escalated,
            "created_at": _now_iso(),
        })
    except Exception as exc:  # noqa: BLE001
        logger.debug("chatbot transcript write failed: %s", exc)


@router.post("/send")
async def send(body: ChatSend):
    """Public widget endpoint — NO auth (it's the merchant's own site widget).

    Gated instead by a required, ENABLED org config. Unknown/disabled orgs never
    reach the LLM.
    """
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(400, "message required")
    if len(message) > _MAX_MSG:
        message = message[:_MAX_MSG]

    db = get_db()
    rows = await db.select("chatbot_config", filters={"org_id": f"eq.{body.org_id}"}, limit=1)
    cfg = rows[0] if rows else None
    if not cfg or not cfg.get("enabled"):
        raise HTTPException(404, "Chatbot is not enabled for this business")

    await _log_transcript(body.org_id, body.session_id, "user", message)

    # 1) Canned answers first (deterministic, no LLM cost).
    canned = _match_canned(message, cfg.get("canned_answers") or [])
    if canned:
        await _log_transcript(body.org_id, body.session_id, "assistant", canned)
        return {"reply": canned, "source": "canned", "escalate": False}

    # 2) LLM via the shared gateway.
    out = await _llm_reply(cfg, message, body.org_id)
    reply = out["reply"] or (
        f"Sorry, I couldn't answer that. Please reach out to {cfg.get('escalation_contact') or 'our team'}."
        if cfg.get("escalation_to_human") else
        "Sorry, I couldn't answer that right now. Please try again shortly."
    )
    escalate = out["escalate"] and bool(cfg.get("escalation_to_human"))
    await _log_transcript(body.org_id, body.session_id, "assistant", reply, escalated=escalate)
    resp = {"reply": reply, "source": "llm", "escalate": escalate}
    if escalate and cfg.get("escalation_contact"):
        resp["escalation_contact"] = cfg["escalation_contact"]
    return resp
