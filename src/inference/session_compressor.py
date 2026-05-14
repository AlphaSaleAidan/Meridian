"""
Session Memory Compressor — Post-session extraction via local LLM.

After each Claude session, reads the conversation log and extracts:
- Decisions made (architectural, technical, design)
- Patterns learned (what worked, what didn't)
- Things to avoid (mistakes, dead ends, anti-patterns)

Writes structured memory files that replace 20K+ tokens of exploration
with a dense ~500-token summary.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("meridian.inference.session_compressor")

SESSION_DIR = Path("/root/.claude/projects/-root-Meridian")
MEMORY_DIR = Path("/root/.claude/projects/-root-Meridian/memory")

MAX_SESSION_TOKENS = 6000


def find_session_logs() -> list[Path]:
    """Find Claude session JSONL files, newest first."""
    if not SESSION_DIR.exists():
        return []

    logs = sorted(
        SESSION_DIR.glob("*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return logs


def _extract_conversation(log_path: Path, max_chars: int = 24000) -> str:
    """Extract user/assistant messages from a session log."""
    messages = []
    total_chars = 0

    try:
        with open(log_path) as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                msg = obj.get("message", {})
                role = msg.get("role", "")
                if role not in ("user", "assistant"):
                    continue

                content = msg.get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                            elif part.get("type") == "thinking":
                                pass
                            elif part.get("type") == "tool_use":
                                tool = part.get("name", "unknown")
                                inp = str(part.get("input", {}))[:200]
                                text_parts.append(f"[Tool: {tool} — {inp}]")
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content = "\n".join(text_parts)
                elif not isinstance(content, str):
                    content = str(content)

                if not content.strip():
                    continue

                if len(content) > 1500:
                    content = content[:750] + "\n...(truncated)...\n" + content[-500:]

                prefix = "USER" if role == "user" else "CLAUDE"
                entry = f"[{prefix}]: {content}"
                total_chars += len(entry)

                if total_chars > max_chars:
                    break

                messages.append(entry)
    except Exception as e:
        logger.warning(f"Failed to read session log {log_path}: {e}")

    return "\n\n".join(messages)


def _get_processed_sessions() -> set[str]:
    """Get set of already-processed session file names."""
    marker_path = MEMORY_DIR / ".processed_sessions"
    if not marker_path.exists():
        return set()
    return set(marker_path.read_text().strip().split("\n"))


def _mark_session_processed(session_name: str):
    """Mark a session as processed."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    marker_path = MEMORY_DIR / ".processed_sessions"
    processed = _get_processed_sessions()
    processed.add(session_name)
    recent = sorted(processed)[-50:]
    marker_path.write_text("\n".join(recent) + "\n")


def _compress_session(conversation: str) -> dict:
    """Use local LLM to extract key learnings from a session."""
    prompt = f"""Analyze this Claude Code conversation and extract what a developer needs to know for future sessions. Be extremely specific — include file paths, function names, and exact decisions.

Format your response as three sections:
DECISIONS: (technical/architectural decisions made — bullet list, 3-5 items max)
PATTERNS: (what approaches worked well — bullet list, 3-5 items max)
AVOID: (mistakes, dead ends, or anti-patterns discovered — bullet list, 3-5 items max)

If a section has nothing notable, write "None."

CONVERSATION:
{conversation}

ANALYSIS:"""

    try:
        from .local_llm import generate
        raw = generate(
            prompt,
            system="You are a technical knowledge extractor. Pull out only non-obvious, actionable learnings. Skip obvious things. Be specific with file paths and function names.",
            max_tokens=500,
            temperature=0.2,
        )
    except Exception as e:
        logger.warning(f"LLM unavailable for session compression: {e}")
        return {"decisions": "LLM unavailable", "patterns": "LLM unavailable", "avoid": "LLM unavailable"}

    sections = {"decisions": "", "patterns": "", "avoid": ""}
    current_section = None

    for line in raw.split("\n"):
        upper = line.strip().upper()
        if upper.startswith("DECISIONS"):
            current_section = "decisions"
        elif upper.startswith("PATTERNS") or upper.startswith("WHAT WORKED"):
            current_section = "patterns"
        elif upper.startswith("AVOID") or upper.startswith("MISTAKES") or upper.startswith("DEAD ENDS"):
            current_section = "avoid"
        elif current_section:
            sections[current_section] += line + "\n"

    for key in sections:
        sections[key] = sections[key].strip()
        if not sections[key]:
            sections[key] = "None."

    return sections


def compress_recent_sessions(max_sessions: int = 3, use_llm: bool = True) -> dict:
    """Compress recent unprocessed sessions."""
    logger.info("Compressing recent sessions...")

    logs = find_session_logs()
    if not logs:
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "sessions": [], "count": 0}

    processed = _get_processed_sessions()
    to_process = [log for log in logs if log.name not in processed][:max_sessions]

    if not to_process:
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "sessions": [], "count": 0, "reason": "all sessions already processed"}

    results = []
    for log_path in to_process:
        logger.info(f"Compressing session: {log_path.name}")
        conversation = _extract_conversation(log_path)

        if len(conversation) < 500:
            logger.info(f"Session {log_path.name} too short, skipping")
            _mark_session_processed(log_path.name)
            continue

        if use_llm:
            extracted = _compress_session(conversation)
        else:
            extracted = {
                "decisions": "(LLM disabled — raw session available)",
                "patterns": "(LLM disabled)",
                "avoid": "(LLM disabled)",
            }

        results.append({
            "session_id": log_path.stem,
            "file": log_path.name,
            "size_kb": round(log_path.stat().st_size / 1024, 1),
            "extracted": extracted,
        })

        _mark_session_processed(log_path.name)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sessions": results,
        "count": len(results),
    }


def write_compression_memory(data: dict) -> str:
    """Write compressed session learnings to Claude memory file."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    out_path = MEMORY_DIR / "auto_session_learnings.md"
    existing_content = ""
    if out_path.exists():
        existing = out_path.read_text()
        marker = "## Session Learnings"
        idx = existing.find(marker)
        if idx >= 0:
            existing_content = existing[idx + len(marker):].strip()

    new_sections = []
    for s in data["sessions"]:
        section = f"""### Session `{s['session_id'][:8]}` ({s['size_kb']}KB)

**Decisions:**
{s['extracted']['decisions']}

**Patterns:**
{s['extracted']['patterns']}

**Avoid:**
{s['extracted']['avoid']}"""
        new_sections.append(section)

    all_sections = "\n\n".join(new_sections)
    if existing_content:
        all_sections = all_sections + "\n\n" + existing_content

    section_lines = all_sections.split("\n")
    if len(section_lines) > 200:
        all_sections = "\n".join(section_lines[:200]) + "\n\n(older entries truncated)"

    content = f"""---
name: auto-session-learnings
description: Compressed learnings from past Claude sessions — decisions, patterns, things to avoid (auto-rebuilt)
metadata:
  type: feedback
---

Last updated: {data['generated_at']}
Sessions compressed: {data['count']}

## Session Learnings

{all_sections}
"""

    out_path.write_text(content)
    logger.info(f"Wrote session learnings: {out_path}")
    return str(out_path)


def store_compression_vectors(data: dict):
    """Store session learnings in vector DB."""
    try:
        from .embeddings import embed_and_store
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

        for s in data["sessions"]:
            ext = s["extracted"]
            full_text = f"Decisions:\n{ext['decisions']}\n\nPatterns:\n{ext['patterns']}\n\nAvoid:\n{ext['avoid']}"
            embed_and_store(
                doc_id=f"session_learning_{s['session_id'][:8]}_{ts}",
                source_key="session_learning",
                title=f"Session {s['session_id'][:8]} learnings",
                content=full_text,
                domain_tags=["session", "learning", "decisions", "patterns"],
                word_count=len(full_text.split()),
            )
        logger.info(f"Stored {len(data['sessions'])} session learnings in vector DB")
    except Exception as e:
        logger.warning(f"Vector DB storage failed (non-critical): {e}")


def rebuild_session_learnings(max_sessions: int = 3, use_llm: bool = True) -> dict:
    """Full rebuild: compress sessions, write memory, store vectors."""
    data = compress_recent_sessions(max_sessions=max_sessions, use_llm=use_llm)
    if data["count"] > 0:
        path = write_compression_memory(data)
        store_compression_vectors(data)
        return {"status": "complete", "sessions_compressed": data["count"], "memory_file": path}
    reason = data.get("reason", "no unprocessed sessions")
    return {"status": "skipped", "reason": reason}
