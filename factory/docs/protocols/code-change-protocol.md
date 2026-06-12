# Code Change Protocol (CCP) — Detailed Specification

> Detailed procedure for Absolute Criterion 3 (Code Change Protocol).
> Separated from CLAUDE.md — referenced when making code changes.

## 3-Step Protocol

Before writing, modifying, adding, or deleting code, you must internally perform these 3 steps.
Skipping this protocol is an absolute criterion violation.
Always perform the protocol, but scale analysis depth proportional to the change's impact scope.

### Step 1 — Intent Identification
- Define the change purpose (bug fix / feature addition / refactoring / performance) and constraints (compatibility, tech stack) in 1-2 sentences
- For minor changes (typos, comments, formatting): confirm "no ripple effect" then execute immediately

### Step 2 — Ripple Effect Analysis
- Direct dependencies + call relationships (caller/callee)
- Structural relationships (inheritance, composition, references)
- Data model / schema / type cascading changes
- Tests, configuration, documentation, API specs
- If tight coupling or shotgun surgery risk exists: **must** notify user and discuss before proceeding

### Step 3 — Change Design (Change Plan)
- Step-by-step change order (which file/function first → dependency propagation → test/doc alignment)
- If coupling reduction / cohesion increase opportunities appear, propose them (execute only after user approval)

## Proportionality Rule

| Change Scale | Analysis Depth |
|-------------|---------------|
| Minor (typos, comments) | Step 1 only — confirm no ripple effect |
| Standard (function/logic changes) | Full 3 steps |
| Large-scale (architecture, API) | Full 3 steps + prior user approval mandatory |

## Communication Rules
- Avoid unnecessarily verbose theoretical explanations; focus on concrete code and specific steps.
- Add brief rationale for important design choices.
- Even when ambiguity exists, do not avoid the work — state "reasonable assumptions" explicitly, then propose the best design.

## Coding Anchor Points (CAP)

All CCP steps are performed with these 4 attitudes internalized:

- **CAP-1**: Think before coding — no modifications before reading code. Surface tradeoffs. Ask when unclear.
- **CAP-2**: Simplicity first — minimal code. No speculative features, premature abstractions, or unnecessary helpers.
- **CAP-3**: Goal-based execution — define success criteria first, then verify after implementation.
- **CAP-4**: Surgical changes — only the requested change. No unrelated "improvements".

> CAP is subordinate to CCP; when conflicting with Absolute Criterion 1 (quality), quality wins. Details: AGENTS.md §2 Absolute Criterion 3.
