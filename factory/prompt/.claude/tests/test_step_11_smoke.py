"""Step 11: Smoke test results verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import OUTPUTS


def test_smoke_test_exists():
    f = OUTPUTS / "step-11-smoke-test.md"
    assert f.exists()
    assert f.stat().st_size > 200


def test_smoke_test_has_scenarios():
    content = (OUTPUTS / "step-11-smoke-test.md").read_text()
    assert content.count("scenario") >= 5 or content.count("Scenario") >= 5 or content.count("|") > 30


def test_smoke_test_covers_key_chains():
    content = (OUTPUTS / "step-11-smoke-test.md").read_text()
    key_chains = ["SCAN_TODAY", "SHOW_RESULTS", "SHOW_PARAMS", "RESTORE"]
    found = sum(1 for c in key_chains if c in content)
    assert found >= 3, f"Only {found}/4 key chains covered in smoke test"


def test_step_11_translation():
    en = OUTPUTS / "step-11-smoke-test.md"
    ko = OUTPUTS / "step-11-smoke-test.ko.md"
    assert en.exists()
    assert ko.exists()
    assert ko.stat().st_size >= 100
