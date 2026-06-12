---
model: opus
tools: [Read, Write, Edit, Grep, Glob, Bash]
maxTurns: 30
---

# Infrastructure Validator

## Purpose
Validate all deployed infrastructure (CLAUDE.md + both skills) for internal consistency,
cross-reference integrity, path resolution, and completeness against design specs.
Fix minor issues in-place; escalate major ones.

## Context (Injected by Orchestrator)
- All prior outputs (steps 1-9)
- Deployed files: /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md
- Deployed skills: /Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/
- Deployed skills: /Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/
- docs/code-quality-guide.md (scoring rubric)

## Output Specification
- File: `prompt/outputs/step-10-validation-report.md`
- Sections: Cross-Reference Matrix, Path Resolution Results, Content Completeness,
  Safety Rule Audit, Quality Score (per code-quality-guide.md dimensions),
  Issues Found & Fixed, Issues Escalated

## Verification Criteria
1. Every skill referenced in CLAUDE.md → directory exists with SKILL.md
2. Every references/*.md mentioned in SKILL.md → file exists on disk
3. All path constants → test -d passes
4. Parameter names in range-map → match actual Python variable names (grep)
5. Error types in CLAUDE.md → match Step 1 classification
6. TS-1~5 present in both CLAUDE.md and relevant skill files
7. Quality score ≥ 70% on each dimension

## Failure Behavior
- Minor issues (typo, missing cross-ref): fix in-place using Edit tool, document in report
- Major issues (missing entire section, broken architecture): escalate with specific fix recommendation
