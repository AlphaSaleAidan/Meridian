"""
Garry AI — Meridian's agentic AI assistant powered by local Qwen 2.5 7B.

Admin-only. Can read code, search the codebase, propose patches (staged for
approval), query the database, and check system status.

Uses text-based tool calling (Qwen outputs <tool_call> tags, server parses
and executes them, feeds results back).

Endpoints:
  POST /api/garry/chat     → Stream a Garry response (with tool use)
  GET  /api/garry/history  → Get conversation history for a thread
"""
import json
import logging
import os
import re
import time
from collections import defaultdict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ..auth import require_admin
from ...ai.security.input_sanitizer import sanitize_for_llm
from ...ai.garry_tools import execute_tool

logger = logging.getLogger("meridian.api.garry")

router = APIRouter(prefix="/api/garry", tags=["garry"], dependencies=[Depends(require_admin)])

QWEN_URL = os.getenv("GARRY_LLM_URL", "http://localhost:8002")

GARRY_SYSTEM = """You are Garry, Meridian's AI operations assistant. Admin-only access.

Meridian is a POS analytics platform for independent businesses (restaurants, smoke shops, cafes, salons, retail) in Canada and the US. Brand: teal/dark-green (#00d4aa), voice: "the smart operator's unfair advantage."

## TOOLS
You have tools. To use one, output EXACTLY this format on its own line:

<tool_call>{"name": "tool_name", "args": {...}}</tool_call>

After you output a tool call, STOP writing. The system will execute it and give you the result. Then continue your response.

Available tools:

1. read_file — Read a file from the codebase
   Args: {"path": "src/api/routes/garry.py", "start_line": 1, "end_line": 50}

2. search_code — Grep for a pattern across the codebase
   Args: {"pattern": "require_admin", "file_glob": "*.py"}

3. propose_patch — Propose a code change (staged for admin approval, NOT applied immediately)
   Args: {"file_path": "src/api/routes/billing.py", "description": "Fix invoice query", "old_content": "exact old code", "new_content": "exact new code", "priority": "high"}

4. system_status — Check running processes, memory, disk
   Args: {}

5. list_patches — List proposed patches
   Args: {"status": "pending"}

6. run_query — Read-only database query
   Args: {"table": "sales_reps", "select": "id,name,email,is_active", "filters": "is_active=eq.true", "limit": 10}

## RULES
- When asked to fix or change something: READ the file first, then PROPOSE a patch
- Patches are NOT applied immediately — they go to a review queue
- Always explain what you found and what the patch does
- For marketing content: be confident, direct, data-driven. Use CA$ for Canadian content.
- Keep responses concise."""

MAX_HISTORY = 40
MAX_THREADS = 500
MAX_TOOL_ROUNDS = 5

_conversations: dict[str, list[dict]] = defaultdict(list)
_thread_access: dict[str, float] = {}

TOOL_CALL_RE = re.compile(r'<tool_call>\s*(\{.*\})\s*(?:</tool_call>)?', re.DOTALL)


def _get_thread(thread_id: str) -> list[dict]:
    _thread_access[thread_id] = time.monotonic()
    if len(_conversations) > MAX_THREADS:
        oldest = sorted(_thread_access, key=_thread_access.get)[:MAX_THREADS // 4]
        for tid in oldest:
            _conversations.pop(tid, None)
            _thread_access.pop(tid, None)
    return _conversations[thread_id]


class GarryChatRequest(BaseModel):
    message: str
    thread_id: str


async def _qwen_complete(messages: list[dict]) -> str:
    """Non-streaming completion from Qwen."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{QWEN_URL}/v1/chat/completions",
            json={"messages": messages, "max_tokens": 2048, "temperature": 0.5},
        )
        if resp.status_code != 200:
            logger.error("Qwen error: %s %s", resp.status_code, resp.text[:300])
            return f"[Error: LLM returned {resp.status_code}]"
        data = resp.json()
        return data["choices"][0]["message"].get("content", "")


@router.post("/chat")
async def garry_chat(request: Request, req: GarryChatRequest):
    if not req.message.strip():
        raise HTTPException(422, "Message cannot be empty")
    safe_message = sanitize_for_llm(req.message, field_name="garry_chat", wrap_as_data=False)
    history = _get_thread(req.thread_id)
    history.append({"role": "user", "content": safe_message})

    if len(history) > MAX_HISTORY:
        history[:] = history[-MAX_HISTORY:]

    async def stream():
        accumulated = ""
        messages = [{"role": "system", "content": GARRY_SYSTEM}] + list(history)

        try:
            for tool_round in range(MAX_TOOL_ROUNDS + 1):
                response_text = await _qwen_complete(messages)

                if not response_text:
                    yield f"data: {json.dumps({'error': 'Garry is busy — please wait a moment and try again'})}\n\n"
                    break

                match = TOOL_CALL_RE.search(response_text)

                if not match:
                    # No tool call — stream the final response word by word
                    for word in response_text.split(" "):
                        chunk = word if not accumulated else " " + word
                        accumulated += chunk
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                    yield "data: [DONE]\n\n"
                    break

                # Text before tool call
                before_text = response_text[:match.start()].strip()
                if before_text:
                    for word in before_text.split(" "):
                        chunk = word if not accumulated else " " + word
                        accumulated += chunk
                        yield f"data: {json.dumps({'content': chunk})}\n\n"

                # Parse and execute tool call
                try:
                    raw_json = match.group(1).strip()
                    logger.info("Tool call raw: %s", raw_json[:200])
                    tool_data = json.loads(raw_json)
                    tool_name = tool_data.get("name", "unknown")
                    tool_args = tool_data.get("args", {})
                except (json.JSONDecodeError, AttributeError) as parse_err:
                    logger.error("Tool parse error: %s — raw: %s", parse_err, match.group(1)[:200] if match else "no match")
                    accumulated += "\n[Failed to parse tool call — retrying without tools]"
                    _msg = json.dumps({"content": "\n[Retrying...]"})
                    yield f"data: {_msg}\n\n"
                    yield "data: [DONE]\n\n"
                    break

                yield f"data: {json.dumps({'tool_call': {'name': tool_name, 'args': tool_args}})}\n\n"

                tool_result = await execute_tool(tool_name, tool_args)
                if len(tool_result) > 3000:
                    tool_result = tool_result[:3000] + "\n... [truncated]"

                yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'preview': tool_result[:300]}})}\n\n"

                # Add to conversation and loop
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": f"[Tool result for {tool_name}]:\n{tool_result}"})

            else:
                accumulated += "\n\n_[Reached tool use limit]_"
                _msg = json.dumps({"content": "\n\n_[Reached tool use limit]_"})
                yield f"data: {_msg}\n\n"
                yield "data: [DONE]\n\n"

        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': 'Garry is starting up — try again in 30 seconds'})}\n\n"
        except Exception as e:
            logger.exception("Garry stream error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if accumulated:
                history.append({"role": "assistant", "content": accumulated})
            else:
                history.pop()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history")
async def garry_history(thread_id: str = Query(...)):
    return {"thread_id": thread_id, "messages": _conversations.get(thread_id, [])}
