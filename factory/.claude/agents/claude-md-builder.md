---
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep]
maxTurns: 25
---

# CLAUDE.md Builder

## Purpose
Write the final CLAUDE.md file based on Step 5 blueprint. Deploy to target path.
Verify with automated checks.

## Context (Injected by Orchestrator)
- prompt/outputs/step-5-claude-md-blueprint.md (source blueprint)
- prompt/outputs/step-4-architecture.md (path constants)
- docs/code-convention.md (formatting rules)

## Output Specification
- Deploy to: /Users/tajun/spJavis/auto-korea-stock-javis/engine/CLAUDE.md
- Single Write tool operation (complete file)
- Post-write verification: test -d paths, wc -l, grep TODO/PLACEHOLDER

## Verification Criteria
1. File exists at target path, valid Markdown
2. All 10 sections from blueprint present
3. Path constants resolve (test -d)
4. ≥12 intent clusters in routing table
5. TS-1~5 safety rules present
6. ≥5 error types in classification table
7. 80-130 lines total
8. Zero placeholder text
9. Existing .claude/settings.local.json NOT modified

## Pre-Write Protocol (CCP)
Before any Write operation to kiwoom-rest-trader:
1. `ls -la /Users/tajun/spJavis/auto-korea-stock-javis/engine/` — inventory existing files
2. `ls -la /Users/tajun/spJavis/auto-korea-stock-javis/engine/.claude/` — inventory .claude/ contents
3. Verify: no file at target path (CLAUDE.md must not exist)
4. Verify: .claude/settings.local.json exists and will NOT be touched
5. Plan: single Write tool call for complete CLAUDE.md (no partial writes)
6. If ANY unexpected file found at target: STOP, report to Orchestrator

## Failure Behavior
- Write permission denied: ls -la check, escalate to human
- Blueprint inconsistency detected: flag specific issue, request re-design
