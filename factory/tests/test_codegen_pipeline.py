#!/usr/bin/env python3
"""
Codegen Pipeline Integrity Tests

Validates that the infra_schema → generate_infra → validate_infra chain
produces consistent, cross-referenced infrastructure. No API calls.

Execution: pytest tests/test_codegen_pipeline.py -v
"""
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
CODEGEN_DIR = PROJECT_DIR / "prompt" / ".claude" / "codegen"

sys.path.insert(0, str(CODEGEN_DIR))
from infra_schema import (
    WORKFLOW_STATUS_ENUM, TRANSLATION_STATUS_ENUM,
    KRT_ROOT, AW_ROOT, AGENT_ROSTER, STEP_DISPATCH,
    FILTER_MODULES, get_output_keys, get_translation_tasks,
)


class TestInfraSchemaIntegrity:
    def test_status_enums_nonempty(self):
        assert len(WORKFLOW_STATUS_ENUM) >= 3
        assert len(TRANSLATION_STATUS_ENUM) >= 3

    def test_status_enums_are_sets(self):
        assert isinstance(WORKFLOW_STATUS_ENUM, set)
        assert isinstance(TRANSLATION_STATUS_ENUM, set)

    def test_required_workflow_statuses(self):
        required = {"not_started", "in_progress", "completed", "failed"}
        assert required.issubset(WORKFLOW_STATUS_ENUM)

    def test_required_translation_statuses(self):
        required = {"pending", "in_progress", "completed", "retry"}
        assert required.issubset(TRANSLATION_STATUS_ENUM)

    def test_path_constants_are_strings(self):
        assert isinstance(KRT_ROOT, str)
        assert isinstance(AW_ROOT, str)

    def test_aw_root_matches_project(self):
        assert AW_ROOT == str(PROJECT_DIR)

    def test_agent_roster_structure(self):
        required_keys = {"name", "model", "tools", "maxTurns", "phase", "step", "output_key", "translate"}
        for agent in AGENT_ROSTER:
            missing = required_keys - set(agent.keys())
            assert len(missing) == 0, f"Agent {agent['name']} missing keys: {missing}"

    def test_agent_models_valid(self):
        valid_models = {"opus", "sonnet", "haiku"}
        for agent in AGENT_ROSTER:
            assert agent["model"] in valid_models, \
                f"Agent {agent['name']} has invalid model: {agent['model']}"

    def test_step_dispatch_structure(self):
        required_keys = {"step", "type", "agents", "review", "translate"}
        for entry in STEP_DISPATCH:
            missing = required_keys - set(entry.keys())
            assert len(missing) == 0, f"Step {entry['step']} missing keys: {missing}"

    def test_step_types_valid(self):
        valid_types = {"team", "single", "sequential", "human"}
        for entry in STEP_DISPATCH:
            assert entry["type"] in valid_types, \
                f"Step {entry['step']} invalid type: {entry['type']}"

    def test_translation_eligibility_consistent(self):
        for agent in AGENT_ROSTER:
            step_entry = next((s for s in STEP_DISPATCH if s["step"] == agent["step"]), None)
            if step_entry:
                assert agent["translate"] == step_entry["translate"], \
                    f"Agent {agent['name']} translate={agent['translate']} " \
                    f"vs Step {agent['step']} translate={step_entry['translate']}"


class TestValidateInfraExecution:
    def test_validate_infra_passes(self):
        r = subprocess.run(
            [sys.executable, str(CODEGEN_DIR / "validate_infra.py")],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0, f"validate_infra.py failed:\n{r.stdout}\n{r.stderr}"
        assert "PASSED" in r.stdout


class TestConftestCodegenSync:
    def test_conftest_filter_modules_match(self):
        conftest = PROJECT_DIR / "prompt" / ".claude" / "tests" / "conftest.py"
        content = conftest.read_text(encoding="utf-8")
        for mod in FILTER_MODULES:
            assert mod in content, f"conftest.py missing filter module: {mod}"

    def test_conftest_paths_match(self):
        conftest = PROJECT_DIR / "prompt" / ".claude" / "tests" / "conftest.py"
        content = conftest.read_text(encoding="utf-8")
        assert KRT_ROOT in content, "conftest.py KRT_ROOT mismatch"
        assert AW_ROOT in content, "conftest.py AW_ROOT mismatch"


class TestStepDispatchFileSync:
    def test_step_dispatch_md_exists(self):
        f = PROJECT_DIR / ".claude" / "skills" / "workflow-executor" / "references" / "step-dispatch.md"
        assert f.exists(), "step-dispatch.md not found"

    def test_step_dispatch_md_has_all_steps(self):
        f = PROJECT_DIR / ".claude" / "skills" / "workflow-executor" / "references" / "step-dispatch.md"
        content = f.read_text(encoding="utf-8")
        for s in STEP_DISPATCH:
            assert f"| {s['step']} |" in content, \
                f"step-dispatch.md missing step {s['step']}"

    def test_step_registry_yaml_exists(self):
        f = PROJECT_DIR / "prompt" / ".claude" / "step-registry.yaml"
        assert f.exists(), "step-registry.yaml not found"
