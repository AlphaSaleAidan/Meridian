"""Cline → Garry patch pipeline.

When Cline detects an error with a stack trace, this module:
  1. Reads the relevant source file
  2. Sends the error + code to DeepSeek to generate a fix
  3. Creates a Garry patch (staged for review, never auto-applied)
  4. Triggers Garry's review to assess scope and root cause
"""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("meridian.cline.patch_generator")

PROJECT_ROOT = Path("/root/Meridian")

PATCH_SYSTEM_PROMPT = """You are a code repair agent for Meridian Intelligence, a POS analytics platform.
You receive an error report (message, stack trace, affected file) and the current source code.
Your job: generate an exact code patch that fixes the error.

RULES:
- Return ONLY valid JSON with exactly these keys: "old_content", "new_content", "description"
- "old_content" must be an EXACT substring of the current file (copy-paste, do not paraphrase)
- "new_content" is the replacement that fixes the error
- "description" explains what the fix does and why (1-2 sentences)
- Keep patches minimal — fix the bug, don't refactor surrounding code
- If you cannot determine a fix from the information given, return {"skip": true, "reason": "..."}
- Do NOT add comments referencing the error or ticket number"""

REVIEW_SYSTEM_PROMPT = """You are Garry, the code review agent for Meridian Intelligence.
You receive a patch proposed by Cline (the error-detection agent) along with the original error.

Your job: review the patch and assess THREE things:

1. SCOPE: Is this error unique to one user/merchant, or could it affect all users?
   - "user_specific" = caused by bad data, edge-case input, or one merchant's POS config
   - "global" = a code bug that could hit any user under the right conditions

2. ROOT CAUSE: Why did this error happen? (1-2 sentences)

3. RECOMMENDATION: What should be pushed to the repo?
   - "apply_patch" = this patch fixes a real bug, push it
   - "apply_patch_plus" = apply this patch AND add a broader fix (explain what)
   - "skip" = don't apply, this was a transient/data issue
   - "investigate" = need more info before deciding

Return ONLY valid JSON:
{
  "scope": "user_specific" | "global",
  "root_cause": "...",
  "recommendation": "apply_patch" | "apply_patch_plus" | "skip" | "investigate",
  "additional_fix": "description of broader fix if apply_patch_plus, else null",
  "confidence": 0.0-1.0
}"""


async def _call_deepseek(messages: list[dict], max_tokens: int = 1000) -> str | None:
    """Call DeepSeek for patch generation / review."""
    import httpx
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                },
            )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        logger.warning("DeepSeek returned %d: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("DeepSeek patch call failed: %s", e)
    return None


def _extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response."""
    import re
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


def _resolve_file_from_stack(stack_trace: str) -> str | None:
    """Extract the most likely source file path from a Python or JS stack trace."""
    import re
    patterns = [
        r'File "(/root/Meridian/[^"]+)"',
        r'at .+\((/root/Meridian/[^:)]+)',
        r'(/root/Meridian/(?:src|frontend/src)/[^\s:]+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, stack_trace)
        if matches:
            return matches[-1]

    relative_patterns = [
        r'(?:frontend/src|src)/[a-zA-Z0-9_/.-]+\.(?:py|tsx?|jsx?)',
        r'at \S+ \(([^:)]+\.(?:tsx?|jsx?))',
        r'([a-zA-Z0-9_/.-]+\.(?:tsx?|jsx?)):\d+:\d+',
    ]
    for pattern in relative_patterns:
        matches = re.findall(pattern, stack_trace)
        for m in reversed(matches):
            candidate = m.strip()
            for prefix in ["", "frontend/src/", "src/"]:
                full = PROJECT_ROOT / prefix / candidate
                if full.is_file():
                    return str(full)
    return None


async def generate_patch(
    error_type: str,
    error_message: str,
    stack_trace: str,
    business_id: str = "",
) -> dict | None:
    """Generate a code patch for an error using DeepSeek.

    Returns the patch dict (with garry patch_id) or None if no patch could be made.
    """
    file_path = _resolve_file_from_stack(stack_trace)
    if not file_path:
        logger.info("No source file found in stack trace — skipping patch generation")
        return None

    path = Path(file_path)
    if not path.is_file():
        logger.info("File %s does not exist — skipping", file_path)
        return None

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Cannot read %s: %s", file_path, e)
        return None

    if len(source) > 15000:
        source = source[:15000] + "\n... (truncated)"

    relative_path = str(path.relative_to(PROJECT_ROOT))

    messages = [
        {"role": "system", "content": PATCH_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace[:3000],
            "file_path": relative_path,
            "source_code": source,
        })},
    ]

    raw = await _call_deepseek(messages, max_tokens=1500)
    if not raw:
        logger.info("DeepSeek returned no response for patch generation")
        return None

    patch_data = _extract_json(raw)
    if not patch_data:
        logger.warning("Could not parse patch JSON from DeepSeek response")
        return None

    if patch_data.get("skip"):
        logger.info("DeepSeek skipped patch: %s", patch_data.get("reason", "no reason"))
        return None

    old_content = patch_data.get("old_content", "")
    new_content = patch_data.get("new_content", "")
    description = patch_data.get("description", "Auto-generated fix")

    if not old_content or not new_content or old_content == new_content:
        logger.warning("Invalid patch content — skipping")
        return None

    from ..ai.garry_tools import _tool_propose_patch
    result_str = _tool_propose_patch({
        "file_path": relative_path,
        "description": f"[Cline auto-fix] {description}",
        "old_content": old_content,
        "new_content": new_content,
        "priority": "high",
    })
    result = json.loads(result_str)

    if result.get("error"):
        logger.warning("Garry rejected patch proposal: %s", result["error"])
        return None

    patch_id = result.get("patch_id")
    logger.info("Patch %s proposed for %s: %s", patch_id, relative_path, description)

    review = await review_patch(
        patch_id=patch_id,
        error_type=error_type,
        error_message=error_message,
        stack_trace=stack_trace,
        file_path=relative_path,
        old_content=old_content,
        new_content=new_content,
        description=description,
        business_id=business_id,
    )

    return {
        "patch_id": patch_id,
        "file": relative_path,
        "description": description,
        "review": review,
    }


async def review_patch(
    patch_id: str,
    error_type: str,
    error_message: str,
    stack_trace: str,
    file_path: str,
    old_content: str,
    new_content: str,
    description: str,
    business_id: str = "",
) -> dict:
    """Have Garry review a Cline-generated patch.

    Assesses: scope (user-specific vs global), root cause, and recommendation.
    """
    messages = [
        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({
            "patch_id": patch_id,
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace[:2000],
            "file_path": file_path,
            "patch_description": description,
            "old_content": old_content,
            "new_content": new_content,
            "business_id": business_id,
        })},
    ]

    raw = await _call_deepseek(messages, max_tokens=500)
    if not raw:
        return {"scope": "unknown", "root_cause": "Review unavailable", "recommendation": "investigate", "confidence": 0}

    review = _extract_json(raw)
    if not review:
        return {"scope": "unknown", "root_cause": "Could not parse review", "recommendation": "investigate", "confidence": 0}

    from ..ai.garry_tools import update_patch
    update_patch(patch_id, {
        "garry_review": review,
        "reviewed_by": "garry_ai",
    })

    logger.info(
        "Garry review for patch %s: scope=%s, rec=%s, confidence=%.2f",
        patch_id, review.get("scope"), review.get("recommendation"), review.get("confidence", 0),
    )

    return review
