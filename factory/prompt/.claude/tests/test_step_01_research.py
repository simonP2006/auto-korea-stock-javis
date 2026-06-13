"""Step 1: Research output verification."""
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))
from conftest import OUTPUTS, GLOSSARY, FILTER_MODULES


def test_param_inventory_exists():
    f = OUTPUTS / "step-1-param-inventory.md"
    assert f.exists(), "param-inventory output missing"
    assert f.stat().st_size > 100, "param-inventory suspiciously small"


def test_param_inventory_covers_all_modules():
    content = (OUTPUTS / "step-1-param-inventory.md").read_text()
    for mod in FILTER_MODULES:
        mod_lower = mod.lower().replace("filter", "")
        assert mod_lower in content.lower(), f"Module {mod} not found in inventory"


def test_pipeline_analysis_exists():
    f = OUTPUTS / "step-1-pipeline-analysis.md"
    assert f.exists()
    assert f.stat().st_size > 200


def test_pipeline_analysis_call_chain():
    content = (OUTPUTS / "step-1-pipeline-analysis.md").read_text()
    assert "run_full_research_flow" in content or "research_flow" in content


def test_error_patterns_exists():
    f = OUTPUTS / "step-1-error-patterns.md"
    assert f.exists()
    content = f.read_text()
    assert content.count("|") > 20, "Error table seems too small"


def test_error_patterns_minimum_types():
    content = (OUTPUTS / "step-1-error-patterns.md").read_text()
    error_keywords = ["KiwoomAuthError", "KiwoomApiError", "httpx", "Error", "Exception"]
    found = sum(1 for kw in error_keywords if kw in content)
    assert found >= 3, f"Only {found}/5 error keywords found"


def _verify_translation(english_filename):
    en_file = OUTPUTS / english_filename
    ko_file = OUTPUTS / english_filename.replace(".md", ".ko.md")
    assert en_file.exists(), f"English source missing: {english_filename}"
    assert ko_file.exists(), f"Korean translation missing: {ko_file.name}"
    assert ko_file.stat().st_size >= 100, f"Translation too small: {ko_file.name}"


def test_step_1_translations():
    for f in ["step-1-param-inventory.md", "step-1-pipeline-analysis.md", "step-1-error-patterns.md"]:
        _verify_translation(f)
