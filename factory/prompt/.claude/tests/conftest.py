"""Shared test fixtures and constants for workflow step verification."""
import os
import re
import pytest
from pathlib import Path

# === [CODEGEN:START — from infra_schema.py] ===
# ... generated content — DO NOT EDIT ...
KRT_ROOT = Path(os.environ.get("KRT_ROOT", "/Users/tajun/spJavis/auto-korea-stock-javis/engine"))
AW_ROOT = Path(os.environ.get("AW_ROOT", "/Users/tajun/spJavis/auto-korea-stock-javis/factory"))
OUTPUTS = AW_ROOT / "prompt" / "outputs"
GLOSSARY = AW_ROOT / "translations" / "glossary.yaml"
KRT_PYTHON = KRT_ROOT / ".venv" / "bin" / "python"
KRT_FILTERS = KRT_ROOT / "src" / "kiwoom" / "itemFilter"
KRT_REPORTS = KRT_ROOT / "reports"
KRT_SCRIPTS = KRT_ROOT / "scripts"
FILTER_MODULES = ['chart60_120Filter', 'chart240Filter', 'chartDayPreFilter', 'chartDayFilter', 'investorFilter', 'financeFilter', 'chart60Filter']
# === [CODEGEN:END] ===


@pytest.fixture
def outputs_dir():
    return OUTPUTS


@pytest.fixture
def krt_root():
    return KRT_ROOT


@pytest.fixture
def glossary_terms():
    """Load Korean terms from glossary.yaml for consistency verification."""
    if not GLOSSARY.exists():
        return {}
    content = GLOSSARY.read_text(encoding="utf-8")
    terms = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', content))
    return terms
