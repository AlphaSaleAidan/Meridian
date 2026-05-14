"""
File Digest — Pre-session file summaries via local LLM.

Reads recently changed files, generates compact summaries (function signatures,
key logic, recent changes), and writes them to Claude memory files.

Saves 5-15K tokens/session by eliminating file Read calls.
"""

import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger("meridian.inference.file_digest")

REPO_ROOT = Path(__file__).parent.parent.parent
MEMORY_DIR = Path("/root/.claude/projects/-root-Meridian/memory")

SKIP_EXTENSIONS = {".json", ".lock", ".png", ".jpg", ".svg", ".ico", ".woff", ".woff2", ".map"}
SKIP_DIRS = {"node_modules", "__pycache__", ".git", "dist", "build", ".next", "data/scraped"}
MAX_FILE_SIZE = 30_000
MAX_FILES = 15


def _run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip()
    except Exception as e:
        logger.warning(f"git {' '.join(args)} failed: {e}")
        return ""


def get_recently_changed_files(commits_back: int = 10) -> list[Path]:
    """Get files changed in the last N commits, ordered by most recent change."""
    raw = _run_git(["log", f"-{commits_back}", "--name-only", "--pretty=format:"])
    if not raw:
        return []

    seen = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        path = REPO_ROOT / line
        if path in seen:
            continue
        if not path.exists() or not path.is_file():
            continue
        if path.suffix in SKIP_EXTENSIONS:
            continue
        if any(skip in str(path) for skip in SKIP_DIRS):
            continue
        if path.stat().st_size > MAX_FILE_SIZE:
            continue
        seen.append(path)

    return seen[:MAX_FILES]


def get_uncommitted_files() -> list[Path]:
    """Get files with uncommitted changes (staged + unstaged)."""
    raw = _run_git(["diff", "--name-only", "HEAD"])
    if not raw:
        return []

    files = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        path = REPO_ROOT / line
        if not path.exists() or not path.is_file():
            continue
        if path.suffix in SKIP_EXTENSIONS:
            continue
        if any(skip in str(path) for skip in SKIP_DIRS):
            continue
        if path.stat().st_size > MAX_FILE_SIZE:
            continue
        files.append(path)

    return files


def _summarize_file(file_path: Path) -> dict:
    """Read a file and generate a compact summary via local LLM."""
    rel_path = file_path.relative_to(REPO_ROOT)
    content = file_path.read_text(errors="replace")

    if len(content) > 8000:
        content = content[:4000] + "\n\n... (truncated) ...\n\n" + content[-2000:]

    ext = file_path.suffix
    if ext in (".py",):
        lang = "Python"
    elif ext in (".tsx", ".ts"):
        lang = "TypeScript/React"
    elif ext in (".js", ".jsx"):
        lang = "JavaScript"
    else:
        lang = ext.lstrip(".")

    prompt = f"""Summarize this {lang} file in 3-5 bullet points. Include:
- What the file does (one sentence)
- Key exports/functions/components (list names + one-line purpose)
- Any important patterns or dependencies

FILE: {rel_path}
```
{content}
```

SUMMARY:"""

    try:
        from .local_llm import generate
        summary = generate(
            prompt,
            system="You are a code documentation assistant. Be extremely concise. List function/component names exactly as written.",
            max_tokens=350,
            temperature=0.2,
        )
    except Exception as e:
        logger.warning(f"LLM unavailable for {rel_path}: {e}")
        summary = _fallback_summary(content, ext)

    return {
        "path": str(rel_path),
        "size": file_path.stat().st_size,
        "lang": lang,
        "summary": summary,
    }


def _fallback_summary(content: str, ext: str) -> str:
    """Extract key identifiers without LLM."""
    lines = content.split("\n")
    exports = []

    for line in lines:
        stripped = line.strip()
        if ext == ".py":
            if stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("async def "):
                name = stripped.split("(")[0].replace("def ", "").replace("async ", "").replace("class ", "")
                if not name.startswith("_"):
                    exports.append(name)
        elif ext in (".ts", ".tsx", ".js", ".jsx"):
            if "export " in stripped and ("function " in stripped or "const " in stripped or "class " in stripped):
                exports.append(stripped[:80])

    if exports:
        return "Key exports: " + ", ".join(exports[:10])
    return f"({len(lines)} lines, no public exports extracted)"


def build_file_digest(use_llm: bool = True) -> dict:
    """Build digest of recently changed files."""
    logger.info("Building file digest...")

    changed = get_recently_changed_files(10)
    uncommitted = get_uncommitted_files()

    all_files = list(dict.fromkeys(uncommitted + changed))[:MAX_FILES]

    if not all_files:
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "files": [], "count": 0}

    digests = []
    for f in all_files:
        logger.info(f"Digesting {f.relative_to(REPO_ROOT)}")
        if use_llm:
            digests.append(_summarize_file(f))
        else:
            rel = f.relative_to(REPO_ROOT)
            content = f.read_text(errors="replace")
            digests.append({
                "path": str(rel),
                "size": f.stat().st_size,
                "lang": f.suffix,
                "summary": _fallback_summary(content, f.suffix),
            })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": digests,
        "count": len(digests),
    }


def write_digest_memory(digest: dict) -> str:
    """Write file digest to Claude memory file."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    file_sections = []
    for f in digest["files"]:
        file_sections.append(f"### `{f['path']}` ({f['lang']}, {f['size']:,}b)\n{f['summary']}")

    content = f"""---
name: auto-file-digest
description: Compact summaries of recently changed files — eliminates need for Claude to Read them (auto-rebuilt)
metadata:
  type: reference
---

Last rebuilt: {digest['generated_at']}
Files summarized: {digest['count']}

{chr(10).join(file_sections)}
"""

    out_path = MEMORY_DIR / "auto_file_digest.md"
    out_path.write_text(content)
    logger.info(f"Wrote file digest: {out_path}")
    return str(out_path)


def store_digest_vectors(digest: dict):
    """Store file digests in vector DB for semantic search."""
    try:
        from .embeddings import embed_and_store
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")

        for f in digest["files"]:
            embed_and_store(
                doc_id=f"file_digest_{f['path'].replace('/', '_')}_{ts}",
                source_key="file_digest",
                title=f"File: {f['path']}",
                content=f['summary'],
                domain_tags=["file_digest", f['lang'].lower(), f['path'].split('/')[0]],
                word_count=len(f['summary'].split()),
            )
        logger.info(f"Stored {len(digest['files'])} file digests in vector DB")
    except Exception as e:
        logger.warning(f"Vector DB storage failed (non-critical): {e}")


def rebuild_file_digest(use_llm: bool = True) -> dict:
    """Full rebuild: generate digests, write memory, store vectors."""
    digest = build_file_digest(use_llm=use_llm)
    if digest["count"] > 0:
        path = write_digest_memory(digest)
        store_digest_vectors(digest)
        return {"status": "complete", "files_digested": digest["count"], "memory_file": path}
    return {"status": "skipped", "reason": "no recently changed files"}
