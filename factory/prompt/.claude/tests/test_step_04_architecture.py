"""Step 4: Architecture output verification."""
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import OUTPUTS, KRT_ROOT


def test_architecture_exists():
    f = OUTPUTS / "step-4-architecture.md"
    assert f.exists()
    assert f.stat().st_size > 500


def test_architecture_has_path_verification():
    content = (OUTPUTS / "step-4-architecture.md").read_text()
    assert "kiwoom-rest-trader" in content


def test_architecture_has_screener_state_schema():
    content = (OUTPUTS / "step-4-architecture.md").read_text()
    assert "screener_state" in content.lower()


def test_architecture_has_preflight():
    content = (OUTPUTS / "step-4-architecture.md").read_text()
    assert "pre-flight" in content.lower() or "preflight" in content.lower()


def test_step_4_translation():
    en = OUTPUTS / "step-4-architecture.md"
    ko = OUTPUTS / "step-4-architecture.ko.md"
    assert en.exists()
    assert ko.exists()
    assert ko.stat().st_size >= 100
