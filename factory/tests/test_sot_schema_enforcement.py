#!/usr/bin/env python3
"""
SOT Schema Enforcement Tests — validate_state_yaml.py

Tests that the PostToolUse hook correctly blocks invalid writes to state.yaml
and allows valid writes. This is the primary guardian of 절대 기준 2 (SOT integrity).

Execution: pytest tests/test_sot_schema_enforcement.py -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
HOOK_SCRIPT = PROJECT_DIR / ".claude" / "hooks" / "scripts" / "validate_state_yaml.py"
SOT_SUFFIX = os.path.join("prompt", ".claude", "state.yaml")


def _run_validator(yaml_content: str, *, expect_file_match: bool = True) -> subprocess.CompletedProcess:
    """Run validate_state_yaml.py with a temporary state.yaml file."""
    tmp_base = tempfile.mkdtemp(prefix="sot_test_")
    try:
        if expect_file_match:
            sot_dir = Path(tmp_base) / "prompt" / ".claude"
            sot_dir.mkdir(parents=True)
            sot_file = sot_dir / "state.yaml"
        else:
            sot_file = Path(tmp_base) / "other_file.yaml"

        sot_file.write_text(yaml_content, encoding="utf-8")

        env = os.environ.copy()
        env["CLAUDE_TOOL_INPUT"] = json.dumps({"file_path": str(sot_file)})
        env["CLAUDE_PROJECT_DIR"] = str(PROJECT_DIR)

        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            capture_output=True, text=True, env=env, timeout=10,
        )
        return result
    finally:
        shutil.rmtree(tmp_base, ignore_errors=True)


VALID_STATE_YAML = """\
workflow:
  name: "stock-filtering-collector"
  version: "1.0.0"
  current_step: 1
  status: "not_started"
  degradation_notes: []
  outputs:
    step-1-param-inventory: null
    step-2-research-report: null
  translation_tasks:
    step-1-param-inventory: {status: "pending", attempt: 0, pacs_score: null}
  autopilot:
    mode: "enabled"
    decisions: []
"""


class TestValidWrites:
    def test_valid_state_yaml_passes(self):
        r = _run_validator(VALID_STATE_YAML)
        assert r.returncode == 0, f"Valid state.yaml blocked: {r.stderr}"

    def test_status_not_started(self):
        r = _run_validator(VALID_STATE_YAML.replace('"not_started"', '"not_started"'))
        assert r.returncode == 0

    def test_status_in_progress(self):
        r = _run_validator(VALID_STATE_YAML.replace('"not_started"', '"in_progress"'))
        assert r.returncode == 0

    def test_status_completed(self):
        r = _run_validator(VALID_STATE_YAML.replace('"not_started"', '"completed"'))
        assert r.returncode == 0

    def test_status_completed_degraded(self):
        r = _run_validator(VALID_STATE_YAML.replace('"not_started"', '"completed_degraded"'))
        assert r.returncode == 0

    def test_status_failed(self):
        r = _run_validator(VALID_STATE_YAML.replace('"not_started"', '"failed"'))
        assert r.returncode == 0

    def test_current_step_1(self):
        r = _run_validator(VALID_STATE_YAML)
        assert r.returncode == 0

    def test_current_step_12(self):
        r = _run_validator(VALID_STATE_YAML.replace("current_step: 1", "current_step: 12"))
        assert r.returncode == 0

    def test_translation_status_in_progress(self):
        r = _run_validator(VALID_STATE_YAML.replace('"pending"', '"in_progress"'))
        assert r.returncode == 0

    def test_translation_status_completed(self):
        r = _run_validator(VALID_STATE_YAML.replace('"pending"', '"completed"'))
        assert r.returncode == 0

    def test_translation_status_retry(self):
        r = _run_validator(VALID_STATE_YAML.replace('"pending"', '"retry"'))
        assert r.returncode == 0

    def test_translation_status_timeout(self):
        r = _run_validator(VALID_STATE_YAML.replace('"pending"', '"timeout"'))
        assert r.returncode == 0

    def test_translation_status_degraded(self):
        r = _run_validator(VALID_STATE_YAML.replace('"pending"', '"degraded"'))
        assert r.returncode == 0


class TestInvalidWrites:
    def test_invalid_status_blocks(self):
        r = _run_validator(VALID_STATE_YAML.replace('"not_started"', '"bogus_status"'))
        assert r.returncode == 2, f"Invalid status not blocked (exit {r.returncode})"
        assert "BLOCK" in r.stderr

    def test_current_step_0_blocks(self):
        r = _run_validator(VALID_STATE_YAML.replace("current_step: 1", "current_step: 0"))
        assert r.returncode == 2, f"current_step=0 not blocked (exit {r.returncode})"

    def test_current_step_13_blocks(self):
        r = _run_validator(VALID_STATE_YAML.replace("current_step: 1", "current_step: 13"))
        assert r.returncode == 2, f"current_step=13 not blocked (exit {r.returncode})"

    def test_current_step_negative_blocks(self):
        r = _run_validator(VALID_STATE_YAML.replace("current_step: 1", "current_step: -1"))
        assert r.returncode == 2, f"current_step=-1 not blocked (exit {r.returncode})"

    def test_invalid_translation_status_blocks(self):
        r = _run_validator(VALID_STATE_YAML.replace('"pending"', '"invalid_status"'))
        assert r.returncode == 2, f"Invalid translation status not blocked (exit {r.returncode})"

    def test_invalid_output_key_blocks(self):
        yaml_with_bad_key = VALID_STATE_YAML.replace(
            "step-1-param-inventory: null",
            "bad-key-no-step-prefix: null"
        )
        r = _run_validator(yaml_with_bad_key)
        assert r.returncode == 2, f"Invalid output key not blocked (exit {r.returncode})"


class TestNonMatchingFiles:
    def test_non_state_yaml_ignored(self):
        r = _run_validator("garbage: content\nstatus: bogus", expect_file_match=False)
        assert r.returncode == 0, "Non-state.yaml file should be ignored"


class TestProductionSOTReadOnly:
    """Verify the REAL state.yaml is valid (read-only, no modification)."""

    def test_production_state_yaml_is_valid(self):
        sot_path = PROJECT_DIR / "prompt" / ".claude" / "state.yaml"
        if not sot_path.exists():
            pytest.skip("state.yaml not yet created")

        env = os.environ.copy()
        env["CLAUDE_TOOL_INPUT"] = json.dumps({"file_path": str(sot_path)})
        env["CLAUDE_PROJECT_DIR"] = str(PROJECT_DIR)

        r = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            capture_output=True, text=True, env=env, timeout=10,
        )
        assert r.returncode == 0, f"Production state.yaml is INVALID: {r.stderr}"
