#!/usr/bin/env python3
"""
PostToolUse hook: Enforce SOT schema integrity on every write to state.yaml.

Trigger: PostToolUse on Write|Edit where file path matches prompt/.claude/state.yaml
Exit 2: blocks invalid writes (model must self-correct)
Exit 0: valid write or non-matching file

Imports enums from infra_schema.py (NOT _context_lib — different schema per C-3).
"""

import sys
import json
import os
import re

WORKFLOW_SOT_SUFFIX = os.path.join("prompt", ".claude", "state.yaml")


def validate():
    tool_input = json.loads(os.environ.get("CLAUDE_TOOL_INPUT", "{}"))
    file_path = tool_input.get("file_path", "")

    if not file_path.endswith(WORKFLOW_SOT_SUFFIX):
        sys.exit(0)

    # Primary path: import enums from infra_schema
    try:
        import yaml
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
        codegen_dir = os.path.join(project_dir, "prompt", ".claude", "codegen")
        sys.path.insert(0, codegen_dir)
        from infra_schema import WORKFLOW_STATUS_ENUM, TRANSLATION_STATUS_ENUM

        with open(file_path) as f:
            data = yaml.safe_load(f)

        wf = data.get("workflow", {}) if isinstance(data, dict) else {}
        warnings = []

        # W-1: status field
        status = wf.get("status", "")
        if status and status not in WORKFLOW_STATUS_ENUM:
            warnings.append(f"invalid status '{status}' — must be one of {sorted(WORKFLOW_STATUS_ENUM)}")

        # W-2: current_step range
        cs = wf.get("current_step")
        if cs is not None and (not isinstance(cs, int) or not 1 <= cs <= 12):
            warnings.append(f"current_step={cs} — must be int 1-12")

        # W-3: translation_tasks status values
        tt = wf.get("translation_tasks", {})
        if isinstance(tt, dict):
            for key, entry in tt.items():
                if isinstance(entry, dict):
                    ts = entry.get("status", "")
                    if ts and ts not in TRANSLATION_STATUS_ENUM:
                        warnings.append(f"translation_tasks.{key}.status='{ts}' invalid")
                    attempt = entry.get("attempt")
                    if attempt is not None and (not isinstance(attempt, int) or attempt < 0):
                        warnings.append(f"translation_tasks.{key}.attempt must be int >= 0")

        # W-4: outputs keys format (step-N-descriptor)
        outputs = wf.get("outputs", {})
        if isinstance(outputs, dict):
            for key in outputs:
                if not isinstance(key, str) or not re.match(r'^step-\d+-', key):
                    warnings.append(f"invalid output key '{key}'")

        if warnings:
            print(f"BLOCK: {'; '.join(warnings)}", file=sys.stderr)
            sys.exit(2)
        sys.exit(0)

    except ImportError:
        pass  # Fallback below
    except FileNotFoundError:
        sys.exit(0)  # state.yaml doesn't exist yet — allow creation
    except yaml.YAMLError as e:
        # Malformed YAML write — block so the model self-corrects (exit 2),
        # rather than crashing with an uncaught traceback (exit 1).
        # `yaml` is guaranteed bound here: ImportError is matched by the clause
        # above before this expression is evaluated.
        first_line = str(e).splitlines()[0] if str(e) else "parse error"
        print(f"BLOCK: malformed YAML in state.yaml — {first_line}", file=sys.stderr)
        sys.exit(2)

    # Fallback: stdlib-only minimal validation
    try:
        content = open(file_path).read()
    except Exception as e:
        print(f"BLOCK: cannot read state.yaml: {e}", file=sys.stderr)
        sys.exit(2)

    valid_statuses = {"not_started", "in_progress", "completed", "completed_degraded", "failed"}
    status_match = re.search(r'status:\s*["\']?(\w+)', content)
    if status_match and status_match.group(1) not in valid_statuses:
        print(f"BLOCK: invalid status '{status_match.group(1)}'", file=sys.stderr)
        sys.exit(2)

    step_match = re.search(r'current_step:\s*(\d+)', content)
    if step_match and not (1 <= int(step_match.group(1)) <= 12):
        print(f"BLOCK: current_step must be 1-12", file=sys.stderr)
        sys.exit(2)

    valid_tr_statuses = {"pending", "in_progress", "completed", "retry", "timeout", "degraded"}
    all_valid = valid_statuses | valid_tr_statuses
    for m in re.finditer(r'status:\s*["\']?(\w+)', content):
        val = m.group(1)
        if val not in all_valid:
            print(f"BLOCK: unrecognized status '{val}'", file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    validate()
