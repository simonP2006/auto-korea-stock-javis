---
model: opus
tools: [Read, Write, Grep, Glob, Bash]
maxTurns: 40
---

# Pipeline Analyzer

## Purpose
Three sub-tasks: (a) trace execution pipeline call chain, (b) verify output file formats,
(c) analyze masterReference.log format in depth.

## Context (Injected by Orchestrator)
- KRT_SCRIPTS = /Users/tajun/spJavis/kiwoom-rest-trader/scripts
- KRT_REPORTS = /Users/tajun/spJavis/kiwoom-rest-trader/reports
- KRT_FILTERS = /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter

## Output Specification
- File: `prompt/outputs/step-1-pipeline-analysis.md`
- Sections: (a) Call Chain Diagram, (b) Output Format Catalog, (c) masterReference.log Schema
- Sub-task (b) must investigate: researchedCompany.p1.md, researchedCompany.p2.md, masterConditionCompany.md
- Sub-task (c) must determine: does log include numeric gap values (critical for FR-5.2)

## Verification Criteria
1. Call chain: run_full_research_flow → run_prefetch → run_filters traced
2. Each filter module's input/output files documented
3. stage*_passed.md format documented (or code-derived format if files don't exist)
4. masterReference.log field names and separators documented
5. Variant output files (p1.md, p2.md, masterConditionCompany.md) explained

## Failure Behavior
- Bash commands timeout: use Read tool as fallback for file inspection
- Missing reports directory: document assumption, proceed with code analysis only
