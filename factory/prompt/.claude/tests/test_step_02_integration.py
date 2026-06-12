"""Step 2: Research integration output verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import OUTPUTS


def test_research_report_exists():
    f = OUTPUTS / "step-2-research-report.md"
    assert f.exists()
    assert f.stat().st_size > 500, "Research report suspiciously small"


def test_research_report_sections():
    content = (OUTPUTS / "step-2-research-report.md").read_text()
    expected_sections = ["Summary", "Parameter", "Pipeline", "Error"]
    found = sum(1 for s in expected_sections if s.lower() in content.lower())
    assert found >= 3, f"Only {found}/4 expected sections found"


def test_research_report_references_step1():
    content = (OUTPUTS / "step-2-research-report.md").read_text()
    assert "step-1" in content.lower() or "param-inventory" in content.lower() or "pipeline" in content.lower()


def test_step_2_translation():
    en = OUTPUTS / "step-2-research-report.md"
    ko = OUTPUTS / "step-2-research-report.ko.md"
    assert en.exists(), "English source missing"
    assert ko.exists(), "Korean translation missing"
    assert ko.stat().st_size >= 100
