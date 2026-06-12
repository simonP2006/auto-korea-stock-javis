#!/usr/bin/env python3
"""
Cross-reference integrity validator.

Phase 0.9 GATE: Must pass with zero errors before Phase 1 begins.
Validates that all generated infrastructure is internally consistent.

Usage: python3 validate_infra.py
  Exit 0: all checks pass
  Exit 1: integrity errors found
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infra_schema import (
    WORKFLOW_STATUS_ENUM, TRANSLATION_STATUS_ENUM,
    KRT_ROOT, AW_ROOT, AGENT_ROSTER, STEP_DISPATCH,
    FILTER_MODULES, get_output_keys, get_translation_tasks,
)
from generate_infra import generate_manifest_list

AW = Path(AW_ROOT)
errors = []


def check(condition, msg):
    if not condition:
        errors.append(msg)


# V-1: Every STEP_DISPATCH agent exists in AGENT_ROSTER
def v1_dispatch_agents_in_roster():
    roster_names = {a["name"] for a in AGENT_ROSTER}
    for step in STEP_DISPATCH:
        for agent in step["agents"]:
            check(agent in roster_names,
                  f"V-1: Step {step['step']} references unknown agent '{agent}'")


# V-2: Every AGENT_ROSTER agent appears in at least one STEP_DISPATCH
def v2_all_agents_dispatched():
    dispatched = {a for s in STEP_DISPATCH for a in s["agents"]}
    roster_names = {a["name"] for a in AGENT_ROSTER}
    for name in roster_names:
        check(name in dispatched,
              f"V-2: Agent '{name}' in roster but never dispatched")


# V-3: Output keys are unique across entire roster
def v3_unique_output_keys():
    keys = [a["output_key"] for a in AGENT_ROSTER]
    seen = set()
    for k in keys:
        check(k not in seen, f"V-3: Duplicate output_key: {k}")
        seen.add(k)


# V-4: Generated state.yaml output keys match AGENT_ROSTER
def v4_state_yaml_keys():
    path = AW / "prompt" / ".claude" / "state.yaml"
    if not path.exists():
        errors.append("V-4: state.yaml not found")
        return
    content = path.read_text(encoding='utf-8')
    expected_keys = get_output_keys()
    for key in expected_keys:
        check(key in content,
              f"V-4: state.yaml missing output key '{key}'")


# V-5: Agent definition files exist and frontmatter matches schema
def v5_agent_files():
    agents_dir = AW / ".claude" / "agents"
    for agent in AGENT_ROSTER:
        filepath = agents_dir / f"{agent['name']}.md"
        check(filepath.exists(),
              f"V-5: Agent file missing: {filepath.name}")
        if filepath.exists():
            content = filepath.read_text(encoding='utf-8')
            check(f"model: {agent['model']}" in content,
                  f"V-5: {agent['name']}.md model mismatch (expected {agent['model']})")
            check(f"maxTurns: {agent['maxTurns']}" in content,
                  f"V-5: {agent['name']}.md maxTurns mismatch (expected {agent['maxTurns']})")


# V-6: step-dispatch.md table matches STEP_DISPATCH
def v6_step_dispatch_md():
    path = AW / ".claude" / "skills" / "workflow-executor" / "references" / "step-dispatch.md"
    if not path.exists():
        errors.append("V-6: step-dispatch.md not found")
        return
    content = path.read_text(encoding='utf-8')
    for step in STEP_DISPATCH:
        check(f"| {step['step']} |" in content,
              f"V-6: step-dispatch.md missing row for step {step['step']}")


# V-7: conftest.py [CODEGEN] constants match schema
def v7_conftest_constants():
    path = AW / "prompt" / ".claude" / "tests" / "conftest.py"
    if not path.exists():
        errors.append("V-7: conftest.py not found")
        return
    content = path.read_text(encoding='utf-8')
    check(KRT_ROOT in content, "V-7: conftest.py missing KRT_ROOT")
    check(AW_ROOT in content, "V-7: conftest.py missing AW_ROOT")
    for mod in FILTER_MODULES:
        check(mod in content, f"V-7: conftest.py missing filter module '{mod}'")


# V-8: validate_state_yaml.py imports enums from infra_schema
def v8_hook_enum_import():
    path = AW / ".claude" / "hooks" / "scripts" / "validate_state_yaml.py"
    if not path.exists():
        errors.append("V-8: validate_state_yaml.py not found")
        return
    content = path.read_text(encoding='utf-8')
    check("from infra_schema import" in content,
          "V-8: validate_state_yaml.py does not import from infra_schema")


# V-9: File manifest completeness
def v9_file_manifest():
    manifest = generate_manifest_list()
    for rel_path in manifest:
        full_path = AW / rel_path
        check(full_path.exists(),
              f"V-9: Expected file missing: {rel_path}")


# V-10: Translation eligibility consistency
def v10_translation_consistency():
    for agent in AGENT_ROSTER:
        step_entry = next((s for s in STEP_DISPATCH if s["step"] == agent["step"]), None)
        if step_entry and agent["translate"] != step_entry["translate"]:
            errors.append(
                f"V-10: Agent '{agent['name']}' translate={agent['translate']} "
                f"but Step {agent['step']} translate={step_entry['translate']}"
            )


def main():
    print("validate_infra.py — Cross-reference integrity check")
    print("=" * 60)

    v1_dispatch_agents_in_roster()
    v2_all_agents_dispatched()
    v3_unique_output_keys()
    v4_state_yaml_keys()
    v5_agent_files()
    v6_step_dispatch_md()
    v7_conftest_constants()
    v8_hook_enum_import()
    v9_file_manifest()
    v10_translation_consistency()

    if errors:
        print(f"\nFAILED — {len(errors)} error(s):\n")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("\nPASSED — all V-1 through V-10 checks OK.")
        sys.exit(0)


if __name__ == "__main__":
    main()
