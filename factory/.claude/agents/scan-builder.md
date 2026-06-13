---
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep]
maxTurns: 40
---

# Stock-Scan Builder

## Purpose
Build and deploy the complete stock-scan skill to
kiwoom-rest-trader/.claude/skills/stock-scan/.
Dense checkpoint pattern: CP-1 → CP-2 → CP-3.

## Context (Injected by Orchestrator)
- prompt/outputs/step-2-research-report.md
- prompt/outputs/step-4-architecture.md
- prompt/outputs/step-6-stock-scan-blueprint.md (primary source)
- /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md (Step 8 deployed — cross-ref)

## Pre-Write Protocol (CCP)
Before any Write/mkdir to kiwoom-rest-trader:
1. `ls -la /Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/` — check existing
2. Verify target subdirectory does NOT exist yet
3. Plan write sequence: mkdir → SKILL.md → references/*.md (ordered)
4. Each Write must be complete file (no partial/incremental writes)
5. If directory already exists: STOP, report to Orchestrator

## Dense Checkpoints
- CP-1: Directory structure created, empty SKILL.md placeholder → verify `test -d`
- CP-2: SKILL.md complete with all chains → verify content checks
- CP-3: All references/ files written → verify completeness against blueprint

## Output Specification
- Deploy to: /Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/
- Files: SKILL.md + references/ directory with all referenced files

## Verification Criteria
1. Directory exists at target path
2. SKILL.md present and valid Markdown
3. All references/ files listed in SKILL.md exist on disk
4. Zero placeholder text
5. Path constants resolve (test -d)
6. Korean user messages: natural phrasing, correct number formatting

## Failure Behavior
- Write permission denied: escalate to human
- Blueprint gap: flag specific section, request scan-designer rework
