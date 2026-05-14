"""Inference API — local LLM, smart routing, vector search, and system stats."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/inference", tags=["inference"])


class InferenceRequest(BaseModel):
    prompt: str
    system: Optional[str] = "You are a helpful business analytics assistant."
    max_tokens: int = 1024
    temperature: float = 0.7
    target: Optional[str] = "auto"
    source: str = "api"


class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    source_filter: Optional[str] = None
    tag_filter: Optional[str] = None


@router.post("/generate")
async def generate(req: InferenceRequest):
    from src.inference.router import route_inference, InferenceTarget

    target_map = {
        "auto": InferenceTarget.AUTO,
        "local": InferenceTarget.LOCAL,
        "openai": InferenceTarget.OPENAI,
    }
    target = target_map.get(req.target, InferenceTarget.AUTO)

    result = await route_inference(
        prompt=req.prompt,
        system=req.system,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        source=req.source,
        target=target,
    )
    return result


@router.post("/search")
async def vector_search(req: SearchRequest):
    from src.inference.embeddings import search
    results = search(
        query=req.query,
        limit=req.limit,
        source_filter=req.source_filter,
        tag_filter=req.tag_filter,
    )
    return {"results": results, "count": len(results)}


@router.get("/stats")
async def inference_stats():
    from src.inference.embeddings import stats
    from pathlib import Path

    model_dir = Path(__file__).parent.parent.parent.parent / "data" / "models"
    models = []
    if model_dir.exists():
        for f in model_dir.glob("*.gguf"):
            models.append({
                "name": f.name,
                "size_gb": round(f.stat().st_size / 1024**3, 2),
            })

    vector_stats = stats()
    return {
        "models": models,
        "vector_store": vector_stats,
        "routing": {
            "default": "local (Qwen 2.5 7B, zero cost)",
            "fallback": "openai api (only if local fails)",
        },
    }


@router.post("/ingest")
async def trigger_ingestion():
    from src.workers.celery_app import celery_app
    task = celery_app.send_task(
        "src.workers.tasks.ingest_scraped_data",
        queue="analysis",
    )
    return {"status": "dispatched", "task_id": task.id}


@router.post("/rebuild-context")
async def rebuild_context(use_llm: bool = True):
    """Trigger a context engine rebuild — updates Claude memory files + vector DB."""
    from src.inference.context_engine import rebuild_context as _rebuild
    result = _rebuild(use_llm=use_llm)
    return result


@router.post("/rebuild-context/async")
async def rebuild_context_async(use_llm: bool = True):
    """Dispatch context rebuild as a background Celery task."""
    from src.workers.celery_app import celery_app
    task = celery_app.send_task(
        "src.workers.tasks.rebuild_session_context",
        kwargs={"use_llm": use_llm},
        queue="analysis",
    )
    return {"status": "dispatched", "task_id": task.id}


@router.post("/rebuild-all")
async def rebuild_all(use_llm: bool = True):
    """Full token-saving pipeline: context + file digests + diff summaries + session compression."""
    from src.inference.context_engine import rebuild_all as _rebuild_all
    result = _rebuild_all(use_llm=use_llm)
    return result


@router.post("/rebuild-all/async")
async def rebuild_all_async(use_llm: bool = True):
    """Dispatch full pipeline as background Celery task."""
    from src.workers.celery_app import celery_app
    task = celery_app.send_task(
        "src.workers.tasks.rebuild_all_context",
        kwargs={"use_llm": use_llm},
        queue="analysis",
    )
    return {"status": "dispatched", "task_id": task.id}


@router.post("/file-digest")
async def file_digest(use_llm: bool = True):
    """Generate compact summaries of recently changed files."""
    from src.inference.file_digest import rebuild_file_digest
    return rebuild_file_digest(use_llm=use_llm)


@router.post("/diff-summaries")
async def diff_summaries(use_llm: bool = True, count: int = 10):
    """Summarize recent commit diffs."""
    from src.inference.diff_summarizer import rebuild_diff_summaries
    return rebuild_diff_summaries(count=count, use_llm=use_llm)


@router.post("/compress-sessions")
async def compress_sessions(use_llm: bool = True, max_sessions: int = 3):
    """Compress Claude sessions into learnings."""
    from src.inference.session_compressor import rebuild_session_learnings
    return rebuild_session_learnings(max_sessions=max_sessions, use_llm=use_llm)


@router.get("/token-savings")
async def token_savings():
    """Report on token savings from the local LLM pipeline."""
    from pathlib import Path

    memory_dir = Path("/root/.claude/projects/-root-Meridian/memory")
    auto_files = {}
    total_tokens_saved = 0

    file_info = {
        "auto_session_context.md": {"saves": "10-20K", "desc": "Session context pre-loading"},
        "auto_codebase_map.md": {"saves": "3-5K", "desc": "Module map pre-loading"},
        "auto_file_digest.md": {"saves": "5-15K", "desc": "File read elimination"},
        "auto_diff_summaries.md": {"saves": "3-8K", "desc": "Git exploration elimination"},
        "auto_session_learnings.md": {"saves": "10-20K", "desc": "Cross-session memory"},
        "auto_decision_log.md": {"saves": "2-5K", "desc": "Decision re-discovery elimination"},
    }

    for filename, info in file_info.items():
        path = memory_dir / filename
        if path.exists():
            size = path.stat().st_size
            token_est = size // 4
            auto_files[filename] = {
                "exists": True,
                "size_bytes": size,
                "tokens_loaded": token_est,
                "tokens_saved_estimate": info["saves"],
                "purpose": info["desc"],
            }
            low_str = info["saves"].split("-")[0]
            saves_low = int(low_str) * 1000
            total_tokens_saved += saves_low
        else:
            auto_files[filename] = {"exists": False, "purpose": info["desc"]}

    from src.inference.embeddings import stats as vector_stats
    vs = vector_stats()

    return {
        "memory_files": auto_files,
        "active_files": sum(1 for f in auto_files.values() if f.get("exists")),
        "total_files": len(auto_files),
        "estimated_tokens_saved_per_session": f"{total_tokens_saved // 1000}-{total_tokens_saved * 2 // 1000}K",
        "vector_store": vs,
        "pipeline_schedule": "Every 6 hours (context + digests + diffs), every 12 hours (session compression)",
    }
