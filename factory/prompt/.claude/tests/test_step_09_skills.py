"""Step 9: Deployed skills verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import KRT_ROOT

STOCK_SCAN = KRT_ROOT / ".claude" / "skills" / "stock-scan"
FILTER_TUNE = KRT_ROOT / ".claude" / "skills" / "filter-tune"


def test_stock_scan_directory_exists():
    assert STOCK_SCAN.exists(), "stock-scan skill directory missing"


def test_stock_scan_skill_md():
    skill = STOCK_SCAN / "SKILL.md"
    assert skill.exists(), "stock-scan SKILL.md missing"
    assert skill.stat().st_size > 200


def test_stock_scan_references():
    refs = STOCK_SCAN / "references"
    assert refs.exists(), "stock-scan references/ directory missing"
    ref_files = list(refs.glob("*.md"))
    assert len(ref_files) >= 5, f"Only {len(ref_files)} reference files (expect ≥5)"


def test_stock_scan_no_placeholders():
    skill = STOCK_SCAN / "SKILL.md"
    content = skill.read_text()
    for p in ["TODO", "PLACEHOLDER", "TBD", "XXX"]:
        assert p not in content, f"Placeholder '{p}' in stock-scan SKILL.md"


def test_filter_tune_directory_exists():
    assert FILTER_TUNE.exists(), "filter-tune skill directory missing"


def test_filter_tune_skill_md():
    skill = FILTER_TUNE / "SKILL.md"
    assert skill.exists(), "filter-tune SKILL.md missing"
    assert skill.stat().st_size > 200


def test_filter_tune_references():
    refs = FILTER_TUNE / "references"
    assert refs.exists(), "filter-tune references/ directory missing"
    ref_files = list(refs.glob("*.md"))
    assert len(ref_files) >= 6, f"Only {len(ref_files)} reference files (expect ≥6)"


def test_filter_tune_no_placeholders():
    skill = FILTER_TUNE / "SKILL.md"
    content = skill.read_text()
    for p in ["TODO", "PLACEHOLDER", "TBD", "XXX"]:
        assert p not in content, f"Placeholder '{p}' in filter-tune SKILL.md"


def test_cross_references_resolve():
    """Every references/*.md mentioned in SKILL.md exists on disk."""
    for skill_dir in [STOCK_SCAN, FILTER_TUNE]:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text()
        refs_dir = skill_dir / "references"
        if not refs_dir.exists():
            continue
        import re
        mentioned = re.findall(r'references/([a-z0-9_-]+\.md)', content)
        for ref_name in mentioned:
            ref_path = refs_dir / ref_name
            assert ref_path.exists(), f"Referenced file missing: {skill_dir.name}/references/{ref_name}"
