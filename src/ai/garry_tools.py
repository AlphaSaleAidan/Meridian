"""
Garry AI Tool System — gives Garry the ability to read code, search, propose patches, and check system status.

Tools are defined in OpenAI function-calling format for Qwen 2.5 compatibility.
Tool executors run server-side and return results to the conversation.
"""
import json
import logging
import os
import subprocess
import time
import uuid
from pathlib import Path

logger = logging.getLogger("meridian.ai.garry_tools")

PATCHES_DIR = Path("/root/Meridian/data/garry_patches")
PROJECT_ROOT = Path("/root/Meridian")
SAFE_DIRS = [PROJECT_ROOT / "src", PROJECT_ROOT / "frontend/src", PROJECT_ROOT / "services"]

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the Meridian codebase. Use this to understand existing code before proposing changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root, e.g. 'src/api/routes/garry.py'"
                    },
                    "start_line": {"type": "integer", "description": "Start line (1-indexed). Omit to read from beginning."},
                    "end_line": {"type": "integer", "description": "End line (inclusive). Omit to read to end (max 200 lines)."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern across the codebase using grep. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex supported)"},
                    "file_glob": {"type": "string", "description": "File pattern to search, e.g. '*.py' or '*.tsx'. Default: all files."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_patch",
            "description": "Propose a code change as a patch. The patch will be staged for admin review and approval before being applied to production. Use this when you want to fix a bug, add a feature, or modify configuration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path to the file to modify, e.g. 'src/api/routes/billing.py'"},
                    "description": {"type": "string", "description": "Human-readable description of what this patch does and why"},
                    "old_content": {"type": "string", "description": "The exact existing content to replace (must match the file exactly)"},
                    "new_content": {"type": "string", "description": "The new content to replace it with"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Priority level for review"},
                },
                "required": ["file_path", "description", "old_content", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "system_status",
            "description": "Check the current system status — running processes, memory, disk, and recent API errors.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_patches",
            "description": "List all proposed patches and their status (pending, approved, rejected, applied).",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "approved", "rejected", "applied", "all"], "description": "Filter by status. Default: 'pending'."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_query",
            "description": "Run a read-only query against the Supabase database. Only SELECT queries are allowed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name to query"},
                    "select": {"type": "string", "description": "Columns to select, e.g. 'id,name,email' or '*'"},
                    "filters": {"type": "string", "description": "PostgREST filter string, e.g. 'is_active=eq.true&region=eq.canada'"},
                    "limit": {"type": "integer", "description": "Max rows to return. Default: 10."},
                },
                "required": ["table"],
            },
        },
    },
]


def _is_safe_path(path_str: str) -> bool:
    """Ensure path stays within allowed directories."""
    resolved = (PROJECT_ROOT / path_str).resolve()
    return any(str(resolved).startswith(str(d.resolve())) for d in SAFE_DIRS)


def _is_readable_path(path_str: str) -> bool:
    """Broader check for read-only operations — allow anything under project root."""
    resolved = (PROJECT_ROOT / path_str).resolve()
    return str(resolved).startswith(str(PROJECT_ROOT.resolve()))


async def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if name == "read_file":
            return _tool_read_file(arguments)
        elif name == "search_code":
            return _tool_search_code(arguments)
        elif name == "propose_patch":
            return _tool_propose_patch(arguments)
        elif name == "system_status":
            return await _tool_system_status()
        elif name == "list_patches":
            return _tool_list_patches(arguments)
        elif name == "run_query":
            return await _tool_run_query(arguments)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.exception("Tool execution error: %s", name)
        return json.dumps({"error": str(e)})


def _tool_read_file(args: dict) -> str:
    path_str = args.get("path", "")
    if not _is_readable_path(path_str):
        return json.dumps({"error": "Path outside project directory"})

    full_path = PROJECT_ROOT / path_str
    if not full_path.is_file():
        return json.dumps({"error": f"File not found: {path_str}"})

    try:
        lines = full_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        return json.dumps({"error": f"Cannot read file: {e}"})

    start = max(1, args.get("start_line", 1))
    end = min(len(lines), args.get("end_line", start + 79))
    selected = lines[start - 1:end]

    numbered = "\n".join(f"{i}: {line}" for i, line in enumerate(selected, start=start))
    return json.dumps({
        "file": path_str,
        "lines": f"{start}-{end}",
        "total_lines": len(lines),
        "content": numbered,
    })


def _tool_search_code(args: dict) -> str:
    pattern = args.get("pattern", "")
    file_glob = args.get("file_glob", "")
    if not pattern:
        return json.dumps({"error": "Pattern is required"})

    cmd = ["grep", "-rn", "--include", file_glob or "*", "-l" if len(pattern) > 100 else "", pattern]
    cmd = [c for c in cmd if c]
    try:
        result = subprocess.run(
            cmd, cwd=str(PROJECT_ROOT / "src"), capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()[:50]
        return json.dumps({"matches": len(lines), "results": lines})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Search timed out"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def _tool_propose_patch(args: dict) -> str:
    file_path = args.get("file_path", "")
    description = args.get("description", "")
    old_content = args.get("old_content", "")
    new_content = args.get("new_content", "")
    priority = args.get("priority", "medium")

    if not _is_safe_path(file_path):
        return json.dumps({"error": "Cannot modify files outside src/, frontend/src/, or services/"})

    full_path = PROJECT_ROOT / file_path
    if not full_path.is_file():
        return json.dumps({"error": f"File not found: {file_path}"})

    current = full_path.read_text(encoding="utf-8")
    if old_content not in current:
        return json.dumps({"error": "old_content not found in file — read the file first to get the exact content"})

    patch_id = str(uuid.uuid4())[:8]
    patch = {
        "id": patch_id,
        "file_path": file_path,
        "description": description,
        "old_content": old_content,
        "new_content": new_content,
        "priority": priority,
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewed_at": None,
        "reviewed_by": None,
    }

    PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    patch_file = PATCHES_DIR / f"{patch_id}.json"
    patch_file.write_text(json.dumps(patch, indent=2))

    logger.info("Patch proposed: %s — %s", patch_id, description)
    return json.dumps({
        "status": "proposed",
        "patch_id": patch_id,
        "file": file_path,
        "description": description,
        "message": "Patch staged for admin review. It will be applied once approved.",
    })


async def _tool_system_status() -> str:
    try:
        pm2 = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
        processes = json.loads(pm2.stdout) if pm2.stdout else []
        pm2_summary = ", ".join(
            f"{p['name']}={p['pm2_env']['status']}({round(p['monit']['memory']/1024/1024)}MB)"
            for p in processes
        )
    except Exception:
        pm2_summary = "unavailable"

    try:
        disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        d = disk.stdout.strip().splitlines()[-1].split()
        disk_summary = f"{d[4]} used ({d[2]} of {d[1]})"
    except Exception:
        disk_summary = "unavailable"

    try:
        mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        m = mem.stdout.strip().splitlines()[1].split()
        mem_summary = f"{m[2]} used of {m[1]}, {m[6]} available"
    except Exception:
        mem_summary = "unavailable"

    pending_patches = len(list(PATCHES_DIR.glob("*.json"))) if PATCHES_DIR.exists() else 0

    return json.dumps({
        "processes": pm2_summary,
        "disk": disk_summary,
        "memory": mem_summary,
        "pending_patches": pending_patches,
    })


def _tool_list_patches(args: dict) -> str:
    status_filter = args.get("status", "pending")
    if not PATCHES_DIR.exists():
        return json.dumps({"patches": [], "count": 0})

    patches = []
    for f in sorted(PATCHES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            patch = json.loads(f.read_text())
            if status_filter == "all" or patch.get("status") == status_filter:
                patches.append({
                    "id": patch["id"],
                    "file": patch["file_path"],
                    "description": patch["description"],
                    "priority": patch.get("priority", "medium"),
                    "status": patch["status"],
                    "created_at": patch["created_at"],
                })
        except (json.JSONDecodeError, KeyError):
            continue

    return json.dumps({"patches": patches, "count": len(patches)})


async def _tool_run_query(args: dict) -> str:
    import httpx

    table = args.get("table", "")
    select = args.get("select", "*")
    filters = args.get("filters", "")
    limit = min(args.get("limit", 10), 50)

    if not table or not table.replace("_", "").isalnum():
        return json.dumps({"error": "Invalid table name"})

    supabase_url = os.environ.get("SUPABASE_URL", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not supabase_url or not service_key:
        return json.dumps({"error": "Database not configured"})

    url = f"{supabase_url}/rest/v1/{table}?select={select}&limit={limit}"
    if filters:
        url += f"&{filters}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
            })
            if resp.status_code != 200:
                return json.dumps({"error": f"Query failed: {resp.status_code}", "detail": resp.text[:200]})
            rows = resp.json()
            return json.dumps({"table": table, "rows": rows, "count": len(rows)})
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_patch(patch_id: str) -> dict | None:
    patch_file = PATCHES_DIR / f"{patch_id}.json"
    if not patch_file.exists():
        return None
    try:
        return json.loads(patch_file.read_text())
    except (json.JSONDecodeError, KeyError):
        return None


def update_patch(patch_id: str, updates: dict) -> dict | None:
    patch = get_patch(patch_id)
    if not patch:
        return None
    patch.update(updates)
    (PATCHES_DIR / f"{patch_id}.json").write_text(json.dumps(patch, indent=2))
    return patch


def apply_patch(patch_id: str) -> dict:
    """Apply a single approved patch to the filesystem."""
    patch = get_patch(patch_id)
    if not patch:
        return {"error": "Patch not found"}
    if patch["status"] != "approved":
        return {"error": f"Patch is {patch['status']}, not approved"}

    full_path = PROJECT_ROOT / patch["file_path"]
    if not full_path.is_file():
        update_patch(patch_id, {"status": "failed", "error": "File not found"})
        return {"error": f"File not found: {patch['file_path']}"}

    current = full_path.read_text(encoding="utf-8")
    if patch["old_content"] not in current:
        update_patch(patch_id, {"status": "failed", "error": "Content changed since patch was proposed"})
        return {"error": "File has changed since patch was proposed — old_content no longer matches"}

    new_content = current.replace(patch["old_content"], patch["new_content"], 1)
    full_path.write_text(new_content, encoding="utf-8")

    update_patch(patch_id, {
        "status": "applied",
        "applied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    logger.info("Patch applied: %s — %s", patch_id, patch["description"])
    return {"status": "applied", "patch_id": patch_id, "file": patch["file_path"]}
