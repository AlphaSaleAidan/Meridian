"""Path-traversal guard on the cold-storage archive read (2026-07-22 sweep)."""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from src.workers import cold_storage as cs


def test_traversal_table_rejected():
    assert cs.read_archive("org1", 2026, 7, "../../../../etc/passwd") == []
    assert cs.read_archive("org1", 2026, 7, "transactions/../../secret") == []


def test_unknown_table_rejected():
    assert cs.read_archive("org1", 2026, 7, "not_a_real_table") == []


def test_traversal_org_rejected():
    assert cs.read_archive("../../etc", 2026, 7, "transactions") == []
    assert cs.read_archive("a/b", 2026, 7, "transactions") == []


def test_valid_table_and_org_pass_the_guard(tmp_path, monkeypatch):
    # A whitelisted table + clean org gets past the guard (returns [] because no
    # archive file exists, but it does NOT get rejected by the guard).
    monkeypatch.setattr(cs, "ARCHIVE_DIR", tmp_path)
    assert "transactions" in cs._ARCHIVABLE_TABLE_NAMES
    assert cs.read_archive("biz_clean", 2026, 7, "transactions") == []
