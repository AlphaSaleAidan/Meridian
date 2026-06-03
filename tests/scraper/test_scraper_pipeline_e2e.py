"""
End-to-end test of the Meridian web-knowledge scraper pipeline.

Target: tools/scraper/scraper.py (one-shot scraper) + tools/scraper/sources.py
        (source registry) + scripts/scraper-daemon.py (load_manifest only).

After PR (a): the broken-as-documented pins (#2 substring overmatch and
#1 silent swallow-all-exceptions) have been FIXED, and these tests now
assert the CORRECTED behavior — green = right, not green = still-broken.

Constraint: ZERO live HTTP. crawl4ai's AsyncWebCrawler.arun is the sole
external IO in this pipeline; stubbed via the SCRAPER_MODULE namespace.

Run:
    cd <repo-root> && python -m pytest tests/scraper/test_scraper_pipeline_e2e.py -v
"""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

# tools/scraper uses `from sources import SOURCES`, so the dir itself must
# be on sys.path (it's not a package).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRAPER_DIR = REPO_ROOT / "tools" / "scraper"
DAEMON_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRAPER_DIR))
sys.path.insert(0, str(DAEMON_DIR))

import scraper as SCRAPER_MODULE  # noqa: E402
import sources as SOURCES_MODULE  # noqa: E402
SOURCES = SOURCES_MODULE.SOURCES


# ─── Helpers ─────────────────────────────────────────────────────────────

def _run(coro):
    """Bare-stdlib async driver — no pytest-asyncio added."""
    return asyncio.run(coro)


def _fake_result(*, success: bool, markdown: str, title: str | None = "Untitled", error: str | None = None):
    metadata = {"title": title} if title is not None else None
    return SimpleNamespace(
        success=success, markdown=markdown, error_message=error, metadata=metadata,
    )


class _FakeCrawler:
    def __init__(self, arun_side_effect=None):
        self._side_effect = arun_side_effect
        self.calls: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def arun(self, url: str, config=None):
        self.calls.append(url)
        if callable(self._side_effect):
            return self._side_effect(url)
        if isinstance(self._side_effect, Exception):
            raise self._side_effect
        return self._side_effect


def _install_fake_crawler(monkeypatch, crawler_instance: _FakeCrawler):
    """Replace AsyncWebCrawler in the scraper module's namespace.

    raising=False because scraper.py guards crawl4ai import with try/except
    ImportError — when crawl4ai isn't installed, these attrs aren't bound
    on the module yet.
    """
    def factory(config=None):
        return crawler_instance
    monkeypatch.setattr(SCRAPER_MODULE, "AsyncWebCrawler", factory, raising=False)
    monkeypatch.setattr(SCRAPER_MODULE, "HAS_CRAWL4AI", True)
    monkeypatch.setattr(SCRAPER_MODULE, "BrowserConfig", lambda **kw: object(), raising=False)
    monkeypatch.setattr(SCRAPER_MODULE, "CrawlerRunConfig", lambda **kw: object(), raising=False)


# ───────────────────────────────────────────────────────────────────────
# STAGE 1: source registry load
# ───────────────────────────────────────────────────────────────────────

def test_stage_01_source_registry_load():
    assert isinstance(SOURCES, dict)
    assert len(SOURCES) > 0
    assert "mckinsey" in SOURCES
    mck = SOURCES["mckinsey"]
    assert mck["base_url"].startswith("https://")
    assert len(mck["start_paths"]) > 0
    bad = [k for k, v in SOURCES.items() if "base_url" not in v or "start_paths" not in v]
    assert bad == [], f"sources missing base_url or start_paths: {bad}"


# ───────────────────────────────────────────────────────────────────────
# STAGE 4: clean_text
# ───────────────────────────────────────────────────────────────────────

def test_stage_04_clean_text_strips_html_and_collapses_whitespace():
    raw = (
        "<header>X</header>"
        "<script>evil()</script>"
        "<style>.a{}</style>"
        "<nav>Home</nav>"
        "<footer>(c)</footer>"
        "<!-- comment -->"
        "<p>Real <b>content</b>   with    spaces</p>"
    )
    cleaned = SCRAPER_MODULE.clean_text(raw)
    assert "evil()" not in cleaned
    assert ".a{}" not in cleaned
    assert "<" not in cleaned and ">" not in cleaned
    assert "  " not in cleaned
    assert "Real content with spaces" in cleaned


# ───────────────────────────────────────────────────────────────────────
# STAGE 5: length gate (49 drops, 50 keeps)
# ───────────────────────────────────────────────────────────────────────

def test_stage_05_length_gate_49_drops(tmp_path, monkeypatch):
    short = " ".join(["word"] * 49)
    crawler = _FakeCrawler(arun_side_effect=_fake_result(success=True, markdown=short))
    _install_fake_crawler(monkeypatch, crawler)
    monkeypatch.setitem(SOURCES, "mckinsey", {**SOURCES["mckinsey"], "start_paths": ["/p"]})

    results, errors = _run(SCRAPER_MODULE.crawl_source("mckinsey", max_pages=1, output_dir=tmp_path))
    assert results == []
    assert errors == 0
    assert list(tmp_path.glob("*.json")) == []


def test_stage_05_length_gate_50_keeps(tmp_path, monkeypatch):
    fifty = " ".join(["word"] * 50)
    crawler = _FakeCrawler(arun_side_effect=_fake_result(success=True, markdown=fifty))
    _install_fake_crawler(monkeypatch, crawler)
    monkeypatch.setitem(SOURCES, "mckinsey", {**SOURCES["mckinsey"], "start_paths": ["/p"]})

    results, errors = _run(SCRAPER_MODULE.crawl_source("mckinsey", max_pages=1, output_dir=tmp_path))
    assert len(results) == 1
    assert errors == 0
    assert len(list(tmp_path.glob("*.json"))) == 1


# ───────────────────────────────────────────────────────────────────────
# STAGE 6: tag_metadata — CORRECTED behavior assertions
# ───────────────────────────────────────────────────────────────────────

def test_stage_06_tag_metadata_shape():
    """Format pin — fields present, hash 16 hex chars."""
    meta = SCRAPER_MODULE.tag_metadata("hello world " * 30, "mckinsey", "http://x")
    assert set(meta.keys()) >= {"source", "source_key", "url", "domain_tags", "word_count", "content_hash", "scraped_at"}
    assert len(meta["content_hash"]) == 16


def test_stage_06_tag_metadata_NO_overmatch_on_said():
    """PIN #2 regression guard — the headline bug.

    Pre-fix: text containing 'said' was tagged 'analytics' because the bare
    'ai' keyword substring-matched s-AI-d. Audit showed 44 files mistagged
    via this mechanism. Post-fix: word-boundary regex + 'ai' dropped from
    analytics_keywords. 'analytics' must NOT appear in domain_tags for
    plain restaurant-flavored text containing 'said'.
    """
    src_topics = set(SOURCES["mckinsey"].get("topics", []))
    assert "analytics" not in src_topics, "test setup: mckinsey topics must not include analytics"

    meta = SCRAPER_MODULE.tag_metadata(
        "The chef said the kitchen would close at midnight.",
        "mckinsey",
        "http://example.com/restaurant",
    )
    assert "analytics" not in meta["domain_tags"], (
        f"PIN #2 regression: 'said' triggered analytics tag again. tags={meta['domain_tags']!r}"
    )


def test_stage_06_tag_metadata_real_keyword_still_matches():
    """Word-boundary fix must not lose real matches. 'Analytics dashboard
    forecast' must still tag analytics."""
    src_topics = set(SOURCES["mckinsey"].get("topics", []))
    assert "analytics" not in src_topics

    meta = SCRAPER_MODULE.tag_metadata(
        "Analytics dashboard with revenue forecast.",
        "mckinsey",
        "http://example.com/data",
    )
    assert "analytics" in meta["domain_tags"]
    assert "finance" in meta["domain_tags"]  # via 'revenue'


def test_stage_06_tag_metadata_artificial_intelligence_still_tags():
    """Dropped bare 'ai' but kept 'artificial intelligence' — the latter
    must still trigger analytics for AI content."""
    src_topics = set(SOURCES["mckinsey"].get("topics", []))
    assert "analytics" not in src_topics

    meta = SCRAPER_MODULE.tag_metadata(
        "Artificial intelligence is reshaping retail operations.",
        "mckinsey",
        "http://example.com/ai",
    )
    assert "analytics" in meta["domain_tags"]


# ───────────────────────────────────────────────────────────────────────
# STAGE 7: write JSON + silent hash-collision overwrite
# ───────────────────────────────────────────────────────────────────────

def test_stage_07_writes_one_json(tmp_path, monkeypatch):
    text = "x " * 60
    crawler = _FakeCrawler(arun_side_effect=_fake_result(success=True, markdown=text, title="Page Title"))
    _install_fake_crawler(monkeypatch, crawler)
    monkeypatch.setitem(SOURCES, "mckinsey", {**SOURCES["mckinsey"], "start_paths": ["/p1"]})

    results, errors = _run(SCRAPER_MODULE.crawl_source("mckinsey", max_pages=1, output_dir=tmp_path))
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    assert errors == 0
    payload = json.loads(files[0].read_text())
    assert payload["title"] == "Page Title"
    assert payload["metadata"]["word_count"] == 60


def test_stage_07_PIN4_silent_hash_collision_still_present(tmp_path, monkeypatch):
    """KNOWN-BUG PIN — DO NOT "FIX" THIS TEST BY FLIPPING THE ASSERTION.

    This pins the CURRENT (broken) behavior: two URLs with identical cleaned
    content produce identical content_hash → identical entry id → identical
    output filename → second write silently overwrites first. Both results
    are appended with the same id and nothing signals the collision.

    Tracked in GitHub issue #30. When that issue is closed and the underlying
    bug is fixed, this test will start failing — that failure means
    "bug fixed, update this test", NOT regression. At that point:
      - flip `assert len(files) == 1`         → `assert len(files) == 2`
      - flip `assert results[0]["id"] == results[1]["id"]`  → `!=`
      - drop this KNOWN-BUG header
    """
    text = "duplicate content " * 30
    crawler = _FakeCrawler(arun_side_effect=_fake_result(success=True, markdown=text))
    _install_fake_crawler(monkeypatch, crawler)
    monkeypatch.setitem(SOURCES, "mckinsey", {**SOURCES["mckinsey"], "start_paths": ["/page-a", "/page-b"]})

    results, errors = _run(SCRAPER_MODULE.crawl_source("mckinsey", max_pages=2, output_dir=tmp_path))
    files = list(tmp_path.glob("*.json"))
    assert len(results) == 2
    assert len(files) == 1, "PIN #4 still present — separate PR will address"
    assert results[0]["id"] == results[1]["id"]
    assert errors == 0


# ───────────────────────────────────────────────────────────────────────
# CROSS-CUTTING: PIN #1 — error_count now surfaces (CORRECTED)
# ───────────────────────────────────────────────────────────────────────

def test_PIN1_crawl_source_now_surfaces_error_count(tmp_path, monkeypatch, capsys):
    """PIN #1 — FIXED. crawl_source now returns (results, error_count).
    Caller can distinguish 'no content' (results == [] AND errors == 0)
    from 'all errored' (results == [] AND errors > 0).
    """
    crawler = _FakeCrawler(arun_side_effect=RuntimeError("boom"))
    _install_fake_crawler(monkeypatch, crawler)
    monkeypatch.setitem(SOURCES, "mckinsey", {**SOURCES["mckinsey"], "start_paths": ["/p1", "/p2", "/p3"]})

    results, errors = _run(SCRAPER_MODULE.crawl_source("mckinsey", max_pages=3, output_dir=tmp_path))

    assert results == []
    assert errors == 3, "PIN #1 fix: all-error path now surfaces error_count=3"
    assert list(tmp_path.glob("*.json")) == []


def test_PIN1_run_all_aggregates_total_errors(tmp_path, monkeypatch):
    """run_all's manifest now carries total_errors and per-source errors."""
    text = "ok content " * 30
    # mckinsey returns ok; bcg raises
    def side_effect(url):
        if "mckinsey.com" in url:
            return _fake_result(success=True, markdown=text)
        raise RuntimeError("bcg down")

    crawler = _FakeCrawler(arun_side_effect=side_effect)
    _install_fake_crawler(monkeypatch, crawler)
    monkeypatch.setitem(SOURCES, "mckinsey", {**SOURCES["mckinsey"], "start_paths": ["/m1"]})
    monkeypatch.setitem(SOURCES, "bcg", {**SOURCES["bcg"], "start_paths": ["/b1", "/b2"]})

    manifest = _run(SCRAPER_MODULE.run_all(["mckinsey", "bcg"], max_pages=2, output_dir=tmp_path))

    assert manifest["total_errors"] == 2
    assert manifest["sources"]["mckinsey"]["errors"] == 0
    assert manifest["sources"]["bcg"]["errors"] == 2


# ───────────────────────────────────────────────────────────────────────
# DAEMON (lite): PIN #7 — load_manifest crashes on corrupt JSON
# ───────────────────────────────────────────────────────────────────────

def test_daemon_PIN7_load_manifest_crashes_on_corrupt_json(tmp_path, monkeypatch):
    """KNOWN-BUG PIN — DO NOT "FIX" THIS TEST BY FLIPPING THE ASSERTION.

    This pins the CURRENT (broken) behavior: scraper-daemon's load_manifest()
    calls json.loads(MANIFEST.read_text()) with NO try/except. A manifest
    that got truncated/half-written (kill during write, disk full, etc.)
    crashes the next daemon cycle until the file is manually deleted.

    Tracked in GitHub issue #28 (manifest-shape coexist — same surface area).
    When that issue is closed and load_manifest gains a graceful fallback,
    this test will start failing — that failure means "bug fixed, update
    this test", NOT regression. At that point:
      - replace `with pytest.raises(json.JSONDecodeError)` with the new
        expected behavior (probably: returns a default dict + logs a warning)
      - drop this KNOWN-BUG header
    """
    import importlib.util
    daemon_path = REPO_ROOT / "scripts" / "scraper-daemon.py"
    spec = importlib.util.spec_from_file_location("_daemon_under_test", str(daemon_path))
    DAEMON = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(DAEMON)

    bad_manifest = tmp_path / "manifest.json"
    bad_manifest.write_text("{ this is not valid json")
    monkeypatch.setattr(DAEMON, "MANIFEST", bad_manifest)
    with pytest.raises(json.JSONDecodeError):
        DAEMON.load_manifest()
