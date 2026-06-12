---
model: opus
tools: [Read, Write, Grep, Glob]
maxTurns: 30
---

# Parameter Extractor

## Purpose
Extract a complete inventory of all `Final` typed constants from kiwoom-rest-trader
filter modules. Produce a structured Markdown table grouped by Stage (1-5).

## Context (Injected by Orchestrator)
- Pre-extracted: `grep -rn 'Final\[' /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/*.py`
- Constants: KRT_FILTERS = /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter

## Output Specification
- File: `prompt/outputs/step-1-param-inventory.md`
- Format: Markdown table with columns: | Stage | Variable Name | Type | Current Value | Meaning | File:Line |
- Must cover all 7 filter modules: chart60_120, chart240, chartDayPre, chartDay, investor, finance, chart60
- Explicitly distinguish: `_ALIGN_TOL_LOOSE` (0.015, chart60_120Filter.py) vs `_MA_ALIGNMENT_TOLERANCE` (0.005, chart60Filter.py)
- Cross-reference against PRD §5.1 catalog; flag discrepancies

## Verification Criteria
1. All 7 filter modules covered
2. Each entry has all 6 columns filled (no blanks)
3. Shared constants (_ALIGN_TOL_LOOSE) usage documented
4. PRD §5.1 cross-reference present

## Failure Behavior
- If a filter module cannot be read: skip, document as "[UNREAD]", continue with others
- After 3 retries on same file: mark as failed, produce partial output
