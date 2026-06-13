#!/usr/bin/env python3
"""
PostToolUse hook: Informational monitoring of translation output quality.

Trigger: PostToolUse on Write where file path matches *.ko.md
Non-blocking: ALWAYS exits 0. Warnings printed to stderr for Orchestrator awareness.
Full P1 validation remains orchestrator-invoked validate_translation.py.
"""

import sys
import json
import os
import re


def monitor():
    tool_input = json.loads(os.environ.get("CLAUDE_TOOL_INPUT", "{}"))
    file_path = tool_input.get("file_path", "")

    if not file_path.endswith(".ko.md"):
        sys.exit(0)

    try:
        if not os.path.exists(file_path):
            sys.exit(0)

        content = open(file_path, encoding="utf-8").read()
        warnings = []

        # T-1: Minimum size check
        if len(content) < 100:
            warnings.append("WARN: Translation output < 100 bytes — may be incomplete")

        # T-2: Glossary spot-check (top 5 terms)
        glossary_path = os.path.join(
            os.environ.get("CLAUDE_PROJECT_DIR", "."), "translations", "glossary.yaml"
        )
        if os.path.exists(glossary_path):
            glossary_content = open(glossary_path, encoding="utf-8").read()
            ko_terms = re.findall(r':\s*"([^"]+)"', glossary_content)[:5]
            if ko_terms:
                missing = [t for t in ko_terms if t not in content]
                if len(missing) > 2:
                    warnings.append(f"WARN: {len(missing)}/5 top glossary terms missing in translation")

        # T-3: Untranslated block detection (5+ consecutive English-only lines)
        lines = content.split("\n")
        consecutive_en = 0
        in_code_block = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                consecutive_en = 0
                continue
            if in_code_block:
                continue
            if stripped and not stripped.startswith("#") and not stripped.startswith("|"):
                alpha_chars = [c for c in stripped if c.isalpha()]
                if alpha_chars and all(ord(c) < 128 for c in alpha_chars):
                    consecutive_en += 1
                else:
                    consecutive_en = 0
            else:
                consecutive_en = 0
            if consecutive_en >= 5:
                warnings.append("WARN: 5+ consecutive English-only lines — possible untranslated block")
                break

        if warnings:
            for w in warnings:
                print(w, file=sys.stderr)
    except Exception:
        pass  # Non-blocking — never fail

    sys.exit(0)


if __name__ == "__main__":
    monitor()
