"""Step 8: Deployed CLAUDE.md verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import KRT_ROOT

CLAUDE_MD = KRT_ROOT / "CLAUDE.md"


def test_file_exists():
    assert CLAUDE_MD.exists(), "CLAUDE.md not deployed"


def test_line_count():
    lines = CLAUDE_MD.read_text().splitlines()
    assert 80 <= len(lines) <= 130, f"CLAUDE.md is {len(lines)} lines (expected 80-130)"


def test_no_placeholders():
    content = CLAUDE_MD.read_text()
    for placeholder in ["TODO", "PLACEHOLDER", "TBD", "XXX"]:
        assert placeholder not in content, f"Placeholder '{placeholder}' found"


def test_routing_table_clusters():
    content = CLAUDE_MD.read_text()
    clusters = content.count("stock-scan") + content.count("filter-tune")
    assert clusters >= 12, f"Only {clusters} skill references found (expect ≥12)"


def test_safety_rules():
    content = CLAUDE_MD.read_text()
    for ts in ["TS-1", "TS-2", "TS-3", "TS-4", "TS-5"]:
        assert ts in content, f"Safety rule {ts} missing"


def test_path_constants_resolve():
    content = CLAUDE_MD.read_text()
    assert str(KRT_ROOT) in content or "kiwoom-rest-trader" in content


def test_settings_local_preserved():
    settings = KRT_ROOT / ".claude" / "settings.local.json"
    assert settings.exists(), "settings.local.json was removed or missing"
