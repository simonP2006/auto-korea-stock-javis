"""Step 6: Skill design blueprints verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import OUTPUTS


def test_stock_scan_blueprint_exists():
    f = OUTPUTS / "step-6-stock-scan-blueprint.md"
    assert f.exists()
    assert f.stat().st_size > 500


def test_stock_scan_has_8_chains():
    content = (OUTPUTS / "step-6-stock-scan-blueprint.md").read_text()
    chains = ["SCAN_TODAY", "SCAN_SEPARATED", "SCAN_RANGE", "SHOW_RESULTS",
              "WHY_REJECTED", "COMPARE", "COMPARE_PARAMS", "RERUN_FILTERS"]
    found = sum(1 for c in chains if c in content)
    assert found >= 7, f"Only {found}/8 execution chains found"


def test_filter_tune_blueprint_exists():
    f = OUTPUTS / "step-6-filter-tune-blueprint.md"
    assert f.exists()
    assert f.stat().st_size > 500


def test_filter_tune_has_branches():
    content = (OUTPUTS / "step-6-filter-tune-blueprint.md").read_text()
    branches = ["SHOW_PARAMS", "CONFIRM", "RESTORE", "THEORY_GUIDE", "ASK_MODULE", "COMPARE_EXPERIMENTS"]
    found = sum(1 for b in branches if b in content)
    assert found >= 5, f"Only {found}/6 branches found"


def test_filter_tune_has_backup_protocol():
    content = (OUTPUTS / "step-6-filter-tune-blueprint.md").read_text()
    assert "backup" in content.lower() or "bak" in content.lower()


def test_step_6_translations():
    for name in ["step-6-stock-scan-blueprint.md", "step-6-filter-tune-blueprint.md"]:
        en = OUTPUTS / name
        ko = OUTPUTS / name.replace(".md", ".ko.md")
        assert en.exists(), f"English source missing: {name}"
        assert ko.exists(), f"Korean translation missing: {ko.name}"
        assert ko.stat().st_size >= 100
