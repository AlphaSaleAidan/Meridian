"""
Diff Summarizer — Commit diff summaries via local LLM.

Summarizes each recent commit's diff into 2-3 sentences and stores
in vector DB. When Claude needs to understand recent changes, it
searches the vector DB instead of running git log + git diff + reading files.

Saves 3-8K tokens/session.
"""

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("meridian.inference.diff_summarizer")

REPO_ROOT = Path(__file__).parent.parent.parent
MEMORY_DIR = Path("/root/.claude/projects/-root-Meridian/memory")


def _run_git(args: list[str], max_output: int = 8000) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        out = result.stdout.strip()
        if len(out) > max_output:
            out = out[:max_output] + "\n... (truncated)"
        return out
    except Exception as e:
        logger.warning(f"git {' '.join(args)} failed: {e}")
        return ""


def get_recent_commits(count: int = 10) -> list[dict]:
    """Get recent commits with hash, message, and author."""
    raw = _run_git(["log", f"-{count}", "--format=%H|%s|%an|%aI"])
    if not raw:
        return []

    commits = []
    for line in raw.strip().split("\n"):
        parts = line.split("|", 3)
        if len(parts) >= 3:
            commits.append({
                "hash": parts[0],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3] if len(parts) > 3 else "",
            })
    return commits


def get_commit_diff(commit_hash: str) -> str:
    """Get the diff for a specific commit."""
    return _run_git(["show", commit_hash, "--stat", "--format="])


def get_commit_patch(commit_hash: str, max_lines: int = 150) -> str:
    """Get actual code changes for a commit (truncated)."""
    raw = _run_git(["show", commit_hash, "--format=", "-p", "--no-color"])
    lines = raw.split("\n")
    return "\n".join(lines[:max_lines])


def _summarize_commit(commit: dict, diff_stat: str, patch: str) -> str:
    """Use local LLM to summarize a commit's changes."""
    prompt = f"""Summarize this git commit in 2-3 sentences. Be specific about what changed and why.

COMMIT: {commit['message']}
AUTHOR: {commit['author']}

FILES CHANGED:
{diff_stat}

CODE CHANGES (excerpt):
{patch[:3000]}

SUMMARY:"""

    try:
        from .local_llm import generate
        return generate(
            prompt,
            system="You are a git commit analyst. Write extremely concise, specific summaries. No filler. Focus on WHAT changed and WHY.",
            max_tokens=200,
            temperature=0.2,
        )
    except Exception as e:
        logger.warning(f"LLM unavailable: {e}")
        return f"{commit['message']} — {diff_stat.split(chr(10))[-1].strip() if diff_stat else 'no stats'}"


def _already_summarized(commit_hash: str) -> bool:
    """Check if this commit was already summarized in vector DB."""
    try:
        from .embeddings import search
        results = search(f"commit {commit_hash[:8]}", limit=1, source_filter="diff_summary")
        return any(commit_hash[:8] in r.get("id", "") for r in results)
    except Exception:
        return False


def build_diff_summaries(count: int = 10, use_llm: bool = True, force: bool = False) -> dict:
    """Build summaries for recent commits."""
    logger.info(f"Building diff summaries for last {count} commits...")

    commits = get_recent_commits(count)
    if not commits:
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "summaries": [], "count": 0}

    summaries = []
    for commit in commits:
        if not force and _already_summarized(commit["hash"]):
            logger.info(f"Skipping {commit['hash'][:8]} — already summarized")
            continue

        diff_stat = get_commit_diff(commit["hash"])

        if use_llm:
            patch = get_commit_patch(commit["hash"])
            summary = _summarize_commit(commit, diff_stat, patch)
        else:
            summary = f"{commit['message']} — {diff_stat.split(chr(10))[-1].strip() if diff_stat else 'no stats'}"

        summaries.append({
            "hash": commit["hash"],
            "short_hash": commit["hash"][:8],
            "message": commit["message"],
            "author": commit["author"],
            "date": commit["date"],
            "summary": summary,
            "files_changed": diff_stat,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summaries": summaries,
        "count": len(summaries),
        "total_commits": len(commits),
    }


def write_summary_memory(data: dict) -> str:
    """Write diff summaries to Claude memory file."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    sections = []
    for s in data["summaries"]:
        sections.append(f"### `{s['short_hash']}` — {s['message']}\n{s['summary']}")

    content = f"""---
name: auto-diff-summaries
description: LLM-generated summaries of recent commits — replaces git log/diff exploration (auto-rebuilt)
metadata:
  type: project
---

Last rebuilt: {data['generated_at']}
Commits summarized: {data['count']} / {data['total_commits']}

{chr(10).join(sections)}
"""

    out_path = MEMORY_DIR / "auto_diff_summaries.md"
    out_path.write_text(content)
    logger.info(f"Wrote diff summaries: {out_path}")
    return str(out_path)


def store_summary_vectors(data: dict):
    """Store commit summaries in vector DB."""
    try:
        from .embeddings import embed_and_store

        for s in data["summaries"]:
            full_text = f"{s['message']}\n{s['summary']}\n\nFiles: {s['files_changed']}"
            embed_and_store(
                doc_id=f"diff_summary_{s['short_hash']}",
                source_key="diff_summary",
                title=f"Commit {s['short_hash']}: {s['message'][:60]}",
                content=full_text,
                domain_tags=["diff", "commit", "git"],
                word_count=len(full_text.split()),
            )
        logger.info(f"Stored {len(data['summaries'])} diff summaries in vector DB")
    except Exception as e:
        logger.warning(f"Vector DB storage failed (non-critical): {e}")


def rebuild_diff_summaries(count: int = 10, use_llm: bool = True) -> dict:
    """Full rebuild: summarize commits, write memory, store vectors."""
    data = build_diff_summaries(count=count, use_llm=use_llm)
    if data["count"] > 0:
        path = write_summary_memory(data)
        store_summary_vectors(data)
        return {"status": "complete", "commits_summarized": data["count"], "memory_file": path}
    return {"status": "skipped", "reason": "no new commits to summarize"}
