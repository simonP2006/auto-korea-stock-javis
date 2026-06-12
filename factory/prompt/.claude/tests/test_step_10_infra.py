"""Step 10: Infrastructure validation report verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import OUTPUTS


def test_validation_report_exists():
    f = OUTPUTS / "step-10-validation-report.md"
    assert f.exists()
    assert f.stat().st_size > 300


def test_validation_report_has_sections():
    content = (OUTPUTS / "step-10-validation-report.md").read_text()
    expected = ["cross-reference", "path", "completeness", "safety", "quality"]
    found = sum(1 for s in expected if s.lower() in content.lower())
    assert found >= 3, f"Only {found}/5 validation sections found"


def test_step_10_translation():
    en = OUTPUTS / "step-10-validation-report.md"
    ko = OUTPUTS / "step-10-validation-report.ko.md"
    assert en.exists()
    assert ko.exists()
    assert ko.stat().st_size >= 100
