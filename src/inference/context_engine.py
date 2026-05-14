"""
Context Engine — Local LLM-powered session context builder.

Runs Qwen locally to:
1. Summarize recent git changes into a compact digest
2. Build a living codebase module map
3. Track architectural decisions
4. Store everything in vector DB + Claude memory files

This eliminates the 10-20K tokens Claude burns per session re-exploring
the codebase. The local LLM does the grunt work at $0.
"""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("meridian.inference.context_engine")

REPO_ROOT = Path(__file__).parent.parent.parent
MEMORY_DIR = Path("/root/.claude/projects/-root-Meridian/memory")
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"

MODULE_DIRS = [
    ("src/api", "FastAPI backend — routes, middleware, app setup"),
    ("src/billing", "Square billing — checkout, invoices, subscriptions"),
    ("src/email", "Transactional email — Postal/Resend templates and send functions"),
    ("src/inference", "Local LLM inference, vector search, context engine"),
    ("src/workers", "Celery tasks — background jobs, sync, analysis"),
    ("src/analytics", "Business analytics, burn rate, reporting"),
    ("src/db", "Database layer — Supabase client, Redis cache"),
    ("src/security", "Encryption, token management"),
    ("src/services", "POS connectors, external service integrations"),
    ("frontend/src/pages/canada/portal", "Canada sales rep portal pages"),
    ("frontend/src/pages/customer", "Customer-facing onboarding and login"),
    ("frontend/src/lib", "Shared frontend libs — auth, supabase, services"),
    ("frontend/src/components", "Reusable UI components"),
    ("tools/scraper", "Web scraper for industry data"),
]


def _run_git(args: list[str], max_lines: int = 100) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        lines = result.stdout.strip().split("\n")
        return "\n".join(lines[:max_lines])
    except Exception as e:
        logger.warning(f"git {' '.join(args)} failed: {e}")
        return ""


def get_recent_commits(count: int = 15) -> str:
    return _run_git(["log", f"--oneline", f"-{count}", "--no-decorate"])


def get_changed_files(commits_back: int = 5) -> str:
    return _run_git(["diff", f"HEAD~{commits_back}", "--stat", "--stat-width=120"])


def get_branch_status() -> str:
    branch = _run_git(["branch", "--show-current"])
    status = _run_git(["status", "--short"])
    ahead_behind = _run_git(["rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
    return f"Branch: {branch}\n{status}\nAhead/behind: {ahead_behind}"


def get_file_tree(max_depth: int = 2) -> str:
    """Get a compact file tree of key directories."""
    lines = []
    for dir_path, description in MODULE_DIRS:
        full_path = REPO_ROOT / dir_path
        if not full_path.exists():
            continue
        file_count = sum(1 for _ in full_path.rglob("*.py")) + sum(1 for _ in full_path.rglob("*.tsx"))
        lines.append(f"  {dir_path}/ ({file_count} files) — {description}")
    return "\n".join(lines)


def build_session_context(use_llm: bool = True) -> dict:
    """
    Build a compact session context. If use_llm=True, uses local Qwen
    to generate summaries. Otherwise builds a structured-but-raw context.
    """
    logger.info("Building session context...")

    commits = get_recent_commits(15)
    changes = get_changed_files(5)
    branch = get_branch_status()
    tree = get_file_tree()

    raw_context = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "branch_status": branch,
        "recent_commits": commits,
        "recent_changes": changes,
        "module_map": tree,
    }

    if not use_llm:
        return raw_context

    summary = _llm_summarize_changes(commits, changes)
    active_work = _llm_extract_active_work(commits, changes, branch)
    decisions = _llm_extract_decisions(commits)

    raw_context["summary"] = summary
    raw_context["active_work"] = active_work
    raw_context["decisions"] = decisions

    return raw_context


def _llm_summarize_changes(commits: str, changes: str) -> str:
    """Use local LLM to create a 3-5 sentence summary of recent work."""
    prompt = f"""Summarize these recent git commits and file changes in 3-5 sentences.
Focus on: what features were added, what bugs were fixed, and what's the current state.
Be specific — mention file names and feature names.

COMMITS:
{commits}

CHANGED FILES:
{changes}

SUMMARY:"""

    return _run_local_llm(prompt, max_tokens=300)


def _llm_extract_active_work(commits: str, changes: str, branch: str) -> str:
    """Extract what's actively being worked on."""
    prompt = f"""Based on these git commits and branch status, list what's actively being worked on.
Format as a short bullet list (3-5 items max). Be specific.

BRANCH STATUS:
{branch}

RECENT COMMITS:
{commits}

ACTIVE WORK:"""

    return _run_local_llm(prompt, max_tokens=250)


def _llm_extract_decisions(commits: str) -> str:
    """Extract architectural/design decisions from commit messages."""
    prompt = f"""Look at these commit messages and extract any non-obvious technical decisions.
Only list decisions that a developer would need to know to avoid re-doing work.
Format as a short bullet list. If there are no clear decisions, say "None extracted."

COMMITS:
{commits}

DECISIONS:"""

    return _run_local_llm(prompt, max_tokens=250)


def _run_local_llm(prompt: str, max_tokens: int = 256) -> str:
    """Run prompt through local Qwen. Falls back to raw text if LLM unavailable."""
    try:
        from .local_llm import generate
        return generate(
            prompt,
            system="You are a concise technical assistant. Give short, specific answers. No filler.",
            max_tokens=max_tokens,
            temperature=0.3,
        )
    except Exception as e:
        logger.warning(f"Local LLM unavailable ({e}), using raw context")
        return "(LLM unavailable — raw context only)"


def write_memory_files(context: dict) -> list[str]:
    """Write context to Claude Code memory files so they load on session start."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    written = []

    # 1. Session context file
    session_file = MEMORY_DIR / "auto_session_context.md"
    session_content = f"""---
name: auto-session-context
description: Auto-generated session context — recent changes, active work, codebase state (rebuilt by local LLM)
metadata:
  type: project
---

Last rebuilt: {context['generated_at']}

## Recent Work Summary
{context.get('summary', 'N/A')}

## Active Work
{context.get('active_work', 'N/A')}

## Recent Commits
```
{context['recent_commits']}
```

## Branch Status
```
{context['branch_status']}
```
"""
    session_file.write_text(session_content)
    written.append(str(session_file))

    # 2. Codebase map file
    map_file = MEMORY_DIR / "auto_codebase_map.md"
    map_content = f"""---
name: auto-codebase-map
description: Living codebase module index — what each directory does, file counts (auto-rebuilt)
metadata:
  type: reference
---

Last rebuilt: {context['generated_at']}

## Module Map
{context['module_map']}

## Recently Changed Files
```
{context['recent_changes']}
```
"""
    map_file.write_text(map_content)
    written.append(str(map_file))

    # 3. Decision log (only if LLM extracted decisions)
    decisions = context.get("decisions", "")
    if decisions and "none extracted" not in decisions.lower() and "llm unavailable" not in decisions.lower():
        decision_file = MEMORY_DIR / "auto_decision_log.md"
        decision_content = f"""---
name: auto-decision-log
description: Technical decisions extracted from recent commits — prevents re-doing work (auto-rebuilt)
metadata:
  type: project
---

Last rebuilt: {context['generated_at']}

## Recent Decisions
{decisions}
"""
        decision_file.write_text(decision_content)
        written.append(str(decision_file))

    # 4. Update MEMORY.md index
    _update_memory_index()

    logger.info(f"Wrote {len(written)} memory files")
    return written


def store_in_vector_db(context: dict):
    """Store context chunks in vector DB for semantic search during sessions."""
    try:
        from .embeddings import embed_and_store

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

        if context.get("summary"):
            embed_and_store(
                doc_id=f"session_context_{ts}",
                source_key="context_engine",
                title="Session Context Summary",
                content=context["summary"],
                domain_tags=["context", "session", "summary"],
                word_count=len(context["summary"].split()),
            )

        if context.get("active_work"):
            embed_and_store(
                doc_id=f"active_work_{ts}",
                source_key="context_engine",
                title="Active Work Items",
                content=context["active_work"],
                domain_tags=["context", "active_work"],
                word_count=len(context["active_work"].split()),
            )

        if context.get("decisions"):
            embed_and_store(
                doc_id=f"decisions_{ts}",
                source_key="context_engine",
                title="Technical Decisions",
                content=context["decisions"],
                domain_tags=["context", "decisions"],
                word_count=len(context["decisions"].split()),
            )

        embed_and_store(
            doc_id=f"commits_{ts}",
            source_key="context_engine",
            title="Recent Commits",
            content=context["recent_commits"],
            domain_tags=["context", "git", "commits"],
            word_count=len(context["recent_commits"].split()),
        )

        logger.info("Stored context in vector DB")
    except Exception as e:
        logger.warning(f"Vector DB storage failed (non-critical): {e}")


def _update_memory_index():
    """Ensure auto-generated memory files are listed in MEMORY.md."""
    if not MEMORY_INDEX.exists():
        return

    current = MEMORY_INDEX.read_text()

    auto_entries = {
        "auto_session_context.md": "- [Session Context](auto_session_context.md) — Auto-rebuilt: recent changes, active work, branch status",
        "auto_codebase_map.md": "- [Codebase Map](auto_codebase_map.md) — Auto-rebuilt: module index, file counts, recent file changes",
        "auto_decision_log.md": "- [Decision Log](auto_decision_log.md) — Auto-rebuilt: technical decisions from recent commits",
        "auto_file_digest.md": "- [File Digest](auto_file_digest.md) — Auto-rebuilt: compact summaries of recently changed files",
        "auto_diff_summaries.md": "- [Diff Summaries](auto_diff_summaries.md) — Auto-rebuilt: LLM summaries of recent commit diffs",
        "auto_session_learnings.md": "- [Session Learnings](auto_session_learnings.md) — Auto-rebuilt: decisions, patterns, and anti-patterns from past sessions",
    }

    lines = current.strip().split("\n")
    existing_auto = {l for l in lines if "auto_" in l or "Auto-rebuilt" in l}

    for filename, entry in auto_entries.items():
        file_path = MEMORY_DIR / filename
        if not file_path.exists():
            continue
        already_listed = any(filename in l for l in lines)
        if not already_listed:
            lines.append(entry)

    # Remove stale entries for files that no longer exist
    final_lines = []
    for line in lines:
        if "auto_" in line:
            fname = None
            for fn in auto_entries:
                if fn in line:
                    fname = fn
                    break
            if fname and not (MEMORY_DIR / fname).exists():
                continue
        final_lines.append(line)

    MEMORY_INDEX.write_text("\n".join(final_lines) + "\n")


def rebuild_context(use_llm: bool = True) -> dict:
    """Full rebuild: generate context, write memory files, store in vector DB."""
    context = build_session_context(use_llm=use_llm)
    files = write_memory_files(context)
    store_in_vector_db(context)
    return {
        "status": "complete",
        "generated_at": context["generated_at"],
        "files_written": files,
        "has_summary": bool(context.get("summary")),
        "has_decisions": bool(context.get("decisions")),
    }


def rebuild_all(use_llm: bool = True) -> dict:
    """Full pipeline: context + file digests + diff summaries + session compression."""
    results = {}

    results["context"] = rebuild_context(use_llm=use_llm)

    try:
        from .file_digest import rebuild_file_digest
        results["file_digest"] = rebuild_file_digest(use_llm=use_llm)
    except Exception as e:
        logger.warning(f"File digest failed: {e}")
        results["file_digest"] = {"status": "error", "error": str(e)}

    try:
        from .diff_summarizer import rebuild_diff_summaries
        results["diff_summaries"] = rebuild_diff_summaries(count=10, use_llm=use_llm)
    except Exception as e:
        logger.warning(f"Diff summaries failed: {e}")
        results["diff_summaries"] = {"status": "error", "error": str(e)}

    try:
        from .session_compressor import rebuild_session_learnings
        results["session_learnings"] = rebuild_session_learnings(max_sessions=3, use_llm=use_llm)
    except Exception as e:
        logger.warning(f"Session compression failed: {e}")
        results["session_learnings"] = {"status": "error", "error": str(e)}

    _update_memory_index()

    return results
