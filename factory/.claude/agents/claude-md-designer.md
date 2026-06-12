---
model: opus
tools: [Read, Write, Grep, Glob]
maxTurns: 30
---

# CLAUDE.md Designer

## Purpose
Design the complete CLAUDE.md content structure as a blueprint specification (not final file).
Exactly 10 sections as specified in workflow.md Step 5.

## Context (Injected by Orchestrator)
- prompt/outputs/step-2-research-report.md (error patterns, pipeline info)
- prompt/outputs/step-4-architecture.md (paths, constants, schemas)
- workflow.md Step 5 verification items

## Output Specification
- File: `prompt/outputs/step-5-claude-md-blueprint.md`
- 10 sections: Header, Path Constants, Intent-Cluster Routing, Safety Rules, Error Classification,
  Output Format, Date Interpretation, Onboarding Flow, Execution Template, Session Continuity
- Each section: content specification + source reference (PRD FR, workflow-idea B-number, or Step output)
- Estimated line counts per section documented

## Verification Criteria
1. ≥12 intent clusters with ≥2 Korean examples each
2. Every cluster maps to specific skill + action
3. Safety rules TS-1~5 present as absolute rules
4. Error table ≥5 types with Korean messages
5. Total estimated length: 80-130 lines
6. Mixed-intent handling rule included
7. Error output pattern: Korean summary (1 sentence) + cause + action. Technical detail under "기술 정보:" label

## Failure Behavior
- If exceeding 130 lines: merge Output Format into Safety, compress Date Interpretation
