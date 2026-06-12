"""Step 5: CLAUDE.md blueprint verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import OUTPUTS


def test_blueprint_exists():
    f = OUTPUTS / "step-5-claude-md-blueprint.md"
    assert f.exists()
    assert f.stat().st_size > 300


def test_blueprint_has_10_sections():
    content = (OUTPUTS / "step-5-claude-md-blueprint.md").read_text()
    headings = [line for line in content.split("\n") if line.startswith("## ") or line.startswith("### ")]
    assert len(headings) >= 8, f"Only {len(headings)} section headings found (expect ≥8)"


def test_blueprint_has_intent_clusters():
    content = (OUTPUTS / "step-5-claude-md-blueprint.md").read_text()
    assert "intent" in content.lower() or "cluster" in content.lower() or "routing" in content.lower()


def test_blueprint_has_safety_rules():
    content = (OUTPUTS / "step-5-claude-md-blueprint.md").read_text()
    ts_count = sum(1 for ts in ["TS-1", "TS-2", "TS-3", "TS-4", "TS-5"] if ts in content)
    assert ts_count >= 4, f"Only {ts_count}/5 safety rules found"


def test_step_5_translation():
    en = OUTPUTS / "step-5-claude-md-blueprint.md"
    ko = OUTPUTS / "step-5-claude-md-blueprint.ko.md"
    assert en.exists()
    assert ko.exists()
    assert ko.stat().st_size >= 100
