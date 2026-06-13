#!/usr/bin/env python3
"""
Deterministic infrastructure file generator.

Reads infra_schema.py and produces/updates generated files.
Phase 0.2-0.7: Generates state.yaml, agent frontmatter, step-dispatch.md,
conftest.py constants, command path refs.

Usage: python3 generate_infra.py [--target TARGET]
  Targets: all, state-yaml, agents, step-dispatch, conftest, commands
  Default: all
"""

import os
import sys
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from infra_schema import (
    WORKFLOW_STATUS_ENUM, TRANSLATION_STATUS_ENUM,
    KRT_ROOT, AW_ROOT, AGENT_ROSTER, STEP_DISPATCH,
    FILTER_MODULES, get_output_keys, get_translation_tasks,
)

AW = Path(AW_ROOT)

# === G-1: state.yaml ===
def generate_state_yaml():
    output_keys = get_output_keys()
    translation_tasks = get_translation_tasks()

    lines = [
        'workflow:',
        '  name: "stock-filtering-collector"',
        '  version: "1.0.0"',
        '  current_step: 1',
        '  status: "not_started"',
        '  degradation_notes: []',
        '  parent_genome:',
        '    version: "2026-05-26"',
        '    source: "AgenticWorkflow"',
        '  outputs:',
    ]
    for key in output_keys:
        lines.append(f'    {key}: null')

    lines.append('  translation_tasks:')
    for key in translation_tasks:
        lines.append(f'    {key}: {{status: "pending", attempt: 0, pacs_score: null, duration_sec: null}}')

    lines.extend([
        '  autopilot:',
        '    mode: "enabled"',
        '    decisions: []',
        '  active_team: null',
        '  completed_teams: []',
    ])

    path = AW / "prompt" / ".claude" / "state.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"  G-1: {path}")


# === G-2: Agent definition frontmatter ===
def generate_agent_frontmatter():
    agents_dir = AW / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    for agent in AGENT_ROSTER:
        filepath = agents_dir / f"{agent['name']}.md"
        tools_str = ", ".join(agent["tools"])
        frontmatter = (
            f"---\n"
            f"model: {agent['model']}\n"
            f"tools: [{tools_str}]\n"
            f"maxTurns: {agent['maxTurns']}\n"
            f"---\n\n"
        )

        if filepath.exists():
            content = filepath.read_text(encoding='utf-8')
            fm_pattern = r'^---\n.*?\n---\n\n?'
            if re.match(fm_pattern, content, re.DOTALL):
                content = re.sub(fm_pattern, frontmatter, content, count=1, flags=re.DOTALL)
            else:
                content = frontmatter + content
            filepath.write_text(content, encoding='utf-8')
        else:
            filepath.write_text(
                frontmatter + f"# {agent['name'].replace('-', ' ').title()}\n\n"
                f"## Purpose\n[LLM-authored content]\n\n"
                f"## Context (Injected by Orchestrator)\n[LLM-authored content]\n\n"
                f"## Output Specification\n- File: `prompt/outputs/{agent['output_key']}.md`\n\n"
                f"## Verification Criteria\n[LLM-authored content]\n\n"
                f"## Failure Behavior\n[LLM-authored content]\n",
                encoding='utf-8'
            )
    print(f"  G-2: {len(AGENT_ROSTER)} agent files in {agents_dir}")


# === G-3: step-dispatch.md ===
def generate_step_dispatch():
    path = AW / ".claude" / "skills" / "workflow-executor" / "references" / "step-dispatch.md"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Step Dispatch Table",
        "",
        "> Auto-generated from infra_schema.py. DO NOT EDIT manually.",
        "",
        "| Step | Type | Agent(s) | Review | Translation |",
        "|------|------|----------|--------|-------------|",
    ]

    for step in STEP_DISPATCH:
        agents_str = ", ".join(step["agents"]) if step["agents"] else "—"
        review_str = f"@{step['review']}" if step["review"] else "—"
        translate_str = "Yes" if step["translate"] else "No"
        lines.append(
            f"| {step['step']} | {step['type']} | {agents_str} | {review_str} | {translate_str} |"
        )

    lines.extend([
        "",
        "## Context Injection Reference",
        "",
    ])

    for step in STEP_DISPATCH:
        if step["agents"]:
            lines.append(f"### Step {step['step']} ({step['type']})")
            for agent_name in step["agents"]:
                agent = next(a for a in AGENT_ROSTER if a["name"] == agent_name)
                lines.append(f"- **{agent_name}**: output → `prompt/outputs/{agent['output_key']}.md`")
            lines.append("")

    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"  G-3: {path}")


# === G-4: conftest.py [CODEGEN] section ===
def generate_conftest_constants():
    path = AW / "prompt" / ".claude" / "tests" / "conftest.py"
    path.parent.mkdir(parents=True, exist_ok=True)

    codegen_section = (
        "# === [CODEGEN:START — from infra_schema.py] ===\n"
        "# ... generated content — DO NOT EDIT ...\n"
        f'KRT_ROOT = Path(os.environ.get("KRT_ROOT", "{KRT_ROOT}"))\n'
        f'AW_ROOT = Path(os.environ.get("AW_ROOT", "{AW_ROOT}"))\n'
        'OUTPUTS = AW_ROOT / "prompt" / "outputs"\n'
        'GLOSSARY = AW_ROOT / "translations" / "glossary.yaml"\n'
        'KRT_PYTHON = KRT_ROOT / ".venv" / "bin" / "python"\n'
        'KRT_FILTERS = KRT_ROOT / "src" / "kiwoom" / "itemFilter"\n'
        'KRT_REPORTS = KRT_ROOT / "reports"\n'
        'KRT_SCRIPTS = KRT_ROOT / "scripts"\n'
        f'FILTER_MODULES = {FILTER_MODULES!r}\n'
        "# === [CODEGEN:END] ===\n"
    )

    if path.exists():
        content = path.read_text(encoding='utf-8')
        pattern = r'# === \[CODEGEN:START.*?\n.*?# === \[CODEGEN:END\] ===\n'
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, codegen_section, content, flags=re.DOTALL)
        else:
            content = content + '\n' + codegen_section
        path.write_text(content, encoding='utf-8')
    else:
        content = (
            '"""Shared test fixtures and constants for workflow step verification."""\n'
            'import os\n'
            'import re\n'
            'import pytest\n'
            'from pathlib import Path\n'
            '\n'
            + codegen_section +
            '\n\n'
            '@pytest.fixture\n'
            'def outputs_dir():\n'
            '    return OUTPUTS\n'
            '\n\n'
            '@pytest.fixture\n'
            'def krt_root():\n'
            '    return KRT_ROOT\n'
            '\n\n'
            '@pytest.fixture\n'
            'def glossary_terms():\n'
            '    """Load Korean terms from glossary.yaml for consistency verification."""\n'
            '    if not GLOSSARY.exists():\n'
            '        return {}\n'
            '    content = GLOSSARY.read_text(encoding="utf-8")\n'
            '    terms = dict(re.findall(r\'"([^"]+)":\\s*"([^"]+)"\', content))\n'
            '    return terms\n'
        )
        path.write_text(content, encoding='utf-8')
    print(f"  G-4: {path}")


# === G-5: enum imports in validate_state_yaml.py (handled at creation time) ===
# validate_state_yaml.py imports directly from infra_schema — no codegen marker needed.
# This target verifies the import path is correct.
def verify_enum_import_path():
    hook_path = AW / ".claude" / "hooks" / "scripts" / "validate_state_yaml.py"
    if hook_path.exists():
        content = hook_path.read_text(encoding='utf-8')
        if "from infra_schema import" in content:
            print(f"  G-5: enum import verified in {hook_path}")
        else:
            print(f"  G-5: WARNING — {hook_path} missing infra_schema import")
    else:
        print(f"  G-5: SKIP — {hook_path} not yet created")


# === G-6: File manifest for validate_infra.py (built into that script) ===
def generate_manifest_list():
    """Return expected file paths for validate_infra.py to check."""
    manifest = []
    # Agent definitions
    for agent in AGENT_ROSTER:
        manifest.append(f".claude/agents/{agent['name']}.md")
    # Skill files
    manifest.extend([
        ".claude/skills/workflow-executor/SKILL.md",
        ".claude/skills/workflow-executor/references/step-dispatch.md",
        ".claude/skills/workflow-executor/references/fallback-paths.md",
    ])
    # Commands
    manifest.extend([
        ".claude/commands/review-research.md",
        ".claude/commands/review-design.md",
        ".claude/commands/accept-system.md",
        ".claude/commands/review-translation.md",
    ])
    # Hooks
    manifest.extend([
        ".claude/hooks/scripts/validate_state_yaml.py",
        ".claude/hooks/scripts/monitor_translation_output.py",
    ])
    # SOT
    manifest.append("prompt/.claude/state.yaml")
    # Tests
    manifest.extend([
        "prompt/.claude/tests/conftest.py",
        "prompt/.claude/tests/test_step_01_research.py",
        "prompt/.claude/tests/test_step_02_integration.py",
        "prompt/.claude/tests/test_step_04_architecture.py",
        "prompt/.claude/tests/test_step_05_blueprint.py",
        "prompt/.claude/tests/test_step_06_skill_design.py",
        "prompt/.claude/tests/test_step_08_claude_md.py",
        "prompt/.claude/tests/test_step_09_skills.py",
        "prompt/.claude/tests/test_step_10_infra.py",
        "prompt/.claude/tests/test_step_11_smoke.py",
        "prompt/.claude/tests/run_tests.py",
    ])
    # Evaluation criteria
    manifest.extend([
        "docs/code-convention.md",
        "docs/architectural-decision-records.md",
        "docs/code-quality-guide.md",
    ])
    # Codegen
    manifest.extend([
        "prompt/.claude/codegen/infra_schema.py",
        "prompt/.claude/codegen/generate_infra.py",
        "prompt/.claude/codegen/validate_infra.py",
    ])
    return manifest


# === G-7: Command file path refs ===
def generate_command_path_refs():
    """Generate [CODEGEN] sections for command files with correct output paths."""
    commands_dir = AW / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    # review-research paths
    step1_agents = [a for a in AGENT_ROSTER if a["step"] == 1]
    step2_agents = [a for a in AGENT_ROSTER if a["step"] == 2]

    research_paths = []
    for a in step2_agents:
        research_paths.append(f"prompt/outputs/{a['output_key']}.ko.md")
        research_paths.append(f"prompt/outputs/{a['output_key']}.md")

    # review-design paths
    design_agents = [a for a in AGENT_ROSTER if a["step"] in (4, 5, 6)]
    design_paths = []
    for a in design_agents:
        design_paths.append(f"prompt/outputs/{a['output_key']}.ko.md")
        design_paths.append(f"prompt/outputs/{a['output_key']}.md")

    print(f"  G-7: command path references generated for {commands_dir}")
    return {
        "review-research": research_paths,
        "review-design": design_paths,
    }


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    target = target.lstrip('-').replace('-', '_')

    print(f"generate_infra.py — target: {target}")

    if target in ("all", "state_yaml"):
        generate_state_yaml()
    if target in ("all", "agents"):
        generate_agent_frontmatter()
    if target in ("all", "step_dispatch"):
        generate_step_dispatch()
    if target in ("all", "conftest"):
        generate_conftest_constants()
    if target in ("all", "enum_verify"):
        verify_enum_import_path()
    if target in ("all", "commands"):
        generate_command_path_refs()

    if target == "all":
        print("\nAll generation targets complete.")


if __name__ == "__main__":
    main()
