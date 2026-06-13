# Workflow Coding — Infrastructure Build Specification

> Implementation blueprint for `workflow.md` (v1.0). This document specifies every file,
> agent, hook, command, and test required to execute the 12-step stock-filter orchestration workflow.
>
> **Language rule**: All infrastructure code, agent definitions, and technical content in English.
> Korean only in user-facing strings within final deployed skill files.

---

## 0. Invariants (Pre-Implementation Checks)

Before writing any file, the implementer MUST verify:

```bash
# Local execution premise
test -d /Users/tajun/spJavis/kiwoom-rest-trader          # Target project exists
test -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python  # Python executable
test -d /Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector/prompt  # Working dir

# SOT preservation
test ! -f prompt/.claude/state.yaml  # SOT not yet created (fresh start)

# No overwrites
test ! -f /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md  # No existing CLAUDE.md
ls /Users/tajun/spJavis/kiwoom-rest-trader/.claude/  # Only settings.local.json expected
```

**PG Connection**: All invariants protect PG-1 (execution) and PG-2 (tuning) by ensuring the target environment is intact before any modification.

---

## 1. Architecture Overview

### Execution Model

```
Main Session (Orchestrator)
├── Reads state.yaml → determines current_step
├── Dispatches work via:
│   ├── Agent tool (single-agent steps: 2, 4, 5, 8, 10, 11)
│   ├── Parallel Agent calls (team steps: 1, 6, 9)
│   └── AskUserQuestion (human steps: 3, 7, 12)
├── Receives output → validates via TDD tests
├── Writes SOT (state.yaml) — SOLE WRITER
└── Proceeds to next step or triggers fallback
```

### Component Responsibility Matrix

| Component | Responsibility | Write Targets |
|-----------|---------------|---------------|
| Orchestrator | Sequencing, SOT writes, human gates, review dispatch, translation tracking | `state.yaml` only |
| Sub-agents (13) | Step execution — research, design, build, validate | `prompt/outputs/step-N-*.md` |
| Skills (1) | Workflow executor entry point | None (read-only orchestration) |
| Hooks (2 new) | SOT schema validation + translation output monitoring | None (exit code enforcement / informational) |
| Commands (4) | Human checkpoint triggers + translation observability | None (read + present) |
| Tests (9) | Step verification (incl. glossary consistency) | `verification-logs/` |
| Reviewer/Fact-checker | Adversarial quality gates | `review-logs/` |

### Data Flow

```
workflow.md (spec) ──┐
                     ├──▶ Orchestrator ──▶ state.yaml (SOT)
state.yaml (state) ──┘        │
                              ├──▶ Agent → prompt/outputs/step-N-*.md
                              ├──▶ Tests → verification-logs/
                              ├──▶ pACS → pacs-logs/
                              └──▶ Review → review-logs/
```

**SOT Preservation**: Only orchestrator writes `state.yaml`. All agents produce output to distinct paths. No concurrent writes possible.

**Local Execution**: All paths are absolute local paths. No network dependencies in orchestration layer.

---

## 2. Teammate Configuration

### 2.1 Agent Definitions to Create

Each file in `.claude/agents/` follows this template:

```markdown
---
model: {opus|sonnet}
tools: [{tool_list}]
maxTurns: {N}
---

# {Agent Name}

## Purpose
{One paragraph describing the agent's role and what it produces}

## Context (Injected by Orchestrator)
{List of files/data the orchestrator must provide in the prompt}

## Output Specification
{Exact output file path and format requirements}

## Verification Criteria
{Numbered list matching workflow.md verification items for this agent's step}

## Failure Behavior
{What to do on error — retry strategy, degradation output}

## Pre-Write Protocol (CCP — Implementation agents only)
Before any Write/Edit operation to the target project (kiwoom-rest-trader):
1. Read existing directory: `ls -la {target_dir}` — identify conflicts
2. Verify no overwrite of existing files unless explicitly designed
3. Plan write sequence: mkdir → file writes → post-verification
4. If unexpected file found: report to Orchestrator, do NOT overwrite
```

### 2.2 Complete Agent Roster

| # | Agent File | Model | maxTurns | Phase | Step |
|---|-----------|-------|----------|-------|------|
| 1 | `param-extractor.md` | opus | 30 | Research | 1 |
| 2 | `pipeline-analyzer.md` | opus | 40 | Research | 1 |
| 3 | `error-analyzer.md` | sonnet | 20 | Research | 1 |
| 4 | `research-integrator.md` | opus | 25 | Research | 2 |
| 5 | `architect.md` | opus | 25 | Planning | 4 |
| 6 | `claude-md-designer.md` | opus | 30 | Planning | 5 |
| 7 | `scan-designer.md` | opus | 35 | Planning | 6 |
| 8 | `tune-designer.md` | opus | 40 | Planning | 6 |
| 9 | `claude-md-builder.md` | opus | 25 | Implementation | 8 |
| 10 | `scan-builder.md` | opus | 40 | Implementation | 9 |
| 11 | `tune-builder.md` | opus | 50 | Implementation | 9 |
| 12 | `infra-validator.md` | opus | 30 | Implementation | 10 |
| 13 | `smoke-tester.md` | opus | 25 | Implementation | 11 |

> **Codegen (§17)**: Agent roster metadata (model, tools, maxTurns, step, output_key) is the authoritative source in `infra_schema.AGENT_ROSTER`. Agent definition file frontmatter is auto-generated by `generate_infra.py`. Manual edits to frontmatter will be overwritten on regeneration.

**Existing agents reused (no modification)**:
- `.claude/agents/reviewer.md` — Steps 4, 5, 6, 8, 9, 10
- `.claude/agents/fact-checker.md` — Steps 1, 2
- `.claude/agents/translator.md` — Steps 1, 2, 4, 5, 6, 10, 11 (post-Review translation)

### 2.3 Team Compositions

```yaml
# Step 1: code-analysis-team
teammates: [param-extractor, pipeline-analyzer, error-analyzer]
parallelism: "3 concurrent Agent calls"
join: "All 3 must complete. Partial: use available outputs."
timeout_proxy: "maxTurns 30/40/20 — approximately 15-30 min per agent"
context_injection_shared:
  - "grep -rn 'Final\\[' KRT_FILTERS/*.py output"
  - "KRT_ROOT path constants"

# Step 6: skill-design-team
teammates: [scan-designer, tune-designer]
parallelism: "2 concurrent Agent calls"
join: "Both must complete."
timeout_proxy: "maxTurns 35/40 — approximately 20-35 min per agent"
context_injection_shared:
  - "prompt/outputs/step-2-research-report.md"
  - "prompt/outputs/step-4-architecture.md"
  - "prompt/outputs/step-5-claude-md-blueprint.md"

# Step 9: skill-build-team (Design Fix C-4: sequential, no worktree)
teammates: [scan-builder, tune-builder]
parallelism: "SEQUENTIAL — scan-builder first, tune-builder second (§9.2)"
join: "Both complete sequentially → orchestrator verifies both directories"
timeout_proxy: "maxTurns 40/50 — approximately 30-50 min per agent"
context_injection_shared:
  - "prompt/outputs/step-2-research-report.md"
  - "prompt/outputs/step-4-architecture.md"
  - "Step 6 respective blueprints"
  - "Step 8 deployed CLAUDE.md (for cross-reference consistency)"
```

> **Design Fix H-1 — Timeout Enforcement**: Claude Code Agent tool has no wall-clock timeout parameter. `maxTurns` is the sole enforcement mechanism. The `timeout_proxy` field documents the estimated wall-clock equivalent. If an agent exhausts maxTurns without producing output, the Orchestrator receives an empty/error result and triggers Fallback F-1.

**Quality Rationale for Team vs Single-Agent** (AGENTS.md §5 five-factor assessment):

| Step | Structure | Dominant Quality Factors | Decision |
|------|-----------|------------------------|----------|
| 1 | Team (3) | Cross-validation ✓ Error isolation ✓ Independent expertise ✓ | 3 independent domains → team |
| 6 | Team (2) | Independent expertise ✓ Error isolation ✓ Disjoint outputs ✓ | PG-1/PG-2 fully independent → team |
| 9 | Team (2) | Error isolation ✓ Disjoint paths ✓ Independent expertise ✓ | stock-scan/filter-tune share no state → team |
| 2 | Single | Context depth ✓✓ Information loss risk ✓ | Must synthesize 3 prior outputs → single |
| 4,5 | Single | Context depth ✓✓ Output consistency ✓ | Sequential refinement chain → single |
| 8 | Single | Context depth ✓✓ Output consistency ✓ | Blueprint→deployment requires full context → single |
| 10 | Single | Context depth ✓✓ Cross-reference ✓ | Must validate ALL prior outputs coherently → single |
| 11 | Single | Context depth ✓ Sequential verification ✓ | End-to-end smoke test requires unified view → single |

**PG Connection**: Team structure mirrors workflow.md exactly. Research team (PG-1+PG-2 foundation), Design team (PG-1: stock-scan, PG-2: filter-tune), Build team (final deliverables).

---

## 3. Orchestrator Design

### 3.1 Orchestrator Implementation: `workflow-executor` Skill

**Location**: `.claude/skills/workflow-executor/`

```
.claude/skills/workflow-executor/
├── SKILL.md              # Main orchestration logic
└── references/
    ├── step-dispatch.md  # Per-step dispatch table (agent, context, verification)
    └── fallback-paths.md # Complete fallback decision tree
```

### 3.2 SKILL.md Core Logic (Pseudocode)

```
ON INVOCATION (including re-entry after context compaction):
  0. [RE-ENTRY PROTOCOL — Design Fix C-5]
     Read state.yaml → get current_step, status, last_completed_substep
     This skill is ALWAYS the first action after session start/resume.
     Context Preservation ensures state.yaml persists across compactions.
     After PreCompact/clear/resume: model re-reads state.yaml and continues
     from exact point of interruption (step + substep level).
  
  1. Read state.yaml → get current_step, status
  2. If status == "completed" → report final state, exit
  3. If status == "failed" → present recovery options to user
  4. Dispatch current_step:
     - Look up step-dispatch.md for: agent(s), context files, verification tests
     - Spawn agent(s) via Agent tool (parallel if team step, sequential for Step 9)
     - On completion: run verification test (pytest step-N)
     - On PASS: update state.yaml (current_step += 1, record output path)
     - On FAIL: trigger fallback (see fallback-paths.md)
  5. If next step is (human): invoke slash command, await user
     - Step 12 ALWAYS requires human (never auto-approve — Design Fix M-3)
  6. Loop until completed or human-blocked

CONTEXT OVERFLOW HANDLING:
  - Each step completion writes state.yaml — serves as durable checkpoint
  - If PreCompact fires mid-step: substep progress tracked in state.yaml
    (e.g., translation_tasks tracks which translations completed)
  - On session resume: model reads SKILL.md instructions + state.yaml
    → determines exact resume point → continues without user re-invocation
  - SessionStart hook's restore_context.py provides RLM pointers to this skill

AUTOPILOT CONTINUITY:
  - After compaction, autopilot.mode remains in state.yaml (persistent)
  - Orchestrator re-reads it and continues auto-approving per protocol
  - Exception: Step 12 — hard block regardless of autopilot state
```

### 3.3 Step Dispatch Table (references/step-dispatch.md)

| Step | Type | Agent(s) | Context Injection | Verification | Review | Translation | File Writer |
|------|------|----------|-------------------|--------------|--------|-------------|-------------|
| 1 | team | param-extractor, pipeline-analyzer, error-analyzer | grep output, KRT paths | test_step_01 | @fact-checker | @translator (×3) | agent (Write tool) |
| 2 | single | research-integrator | step-1 outputs (3 files) | test_step_02 | @fact-checker | @translator | agent (Write tool) |
| 3 | human | — | step-2 output (Korean ver.) | — | — | — | — |
| 4 | single | architect | KRT filesystem, PRD | test_step_04 | @reviewer | @translator | agent (Write tool) |
| 5 | single | claude-md-designer | step-4 output | test_step_05 | @reviewer | @translator | agent (Write tool) |
| 6 | team | scan-designer, tune-designer | steps 2,4,5 outputs | test_step_06 | @reviewer | @translator (×2) | agent (Write tool) |
| 7 | human | — | steps 4,5,6 outputs (Korean ver.) | — | — | — | — |
| 8 | single | claude-md-builder | step-5 blueprint | test_step_08 | @reviewer | none (Korean authored directly) | agent (Write tool) |
| 9 | sequential | scan-builder, tune-builder | steps 2,4,6 + step-8 | test_step_09 | @reviewer | none (code-like deliverables) | agent (Write tool) |
| 10 | single | infra-validator | all prior outputs | test_step_10 | @reviewer | @translator | agent (Write+Edit) |
| 11 | single | smoke-tester | deployed files | test_step_11 | — | @translator | — (read-only) |
| 12 | human | — | all deployed files | — | — | — | — |

> **Codegen (§17)**: This dispatch table is auto-generated from `infra_schema.STEP_DISPATCH` by `generate_infra.py`. The generated `references/step-dispatch.md` is the authoritative runtime copy; this table is the human-readable design reference.

> **Design Fix H-5 — File Writer Column**: All agents producing output files have the Write tool (C-1 fix) and write their own output to disk. The Orchestrator does NOT mediate file writes — it only verifies file existence post-completion via TDD tests.

> **Design Fix H-2 — Translation for Steps 10/11**: workflow.md originally specified "Translation: none" for Steps 10/11. This implementation spec intentionally ADDS translation for these steps because: (a) Step 10 validation report helps user understand system health at Step 12 review, (b) Step 11 smoke test results are presented to user. This is a conscious quality enhancement (절대 기준 1) documented as deviation from workflow.md. STEP_DISPATCH and AGENT_ROSTER reflect this decision.

### 3.4 Translation Dispatch Protocol

After Review PASS (or L1.5 if Review is unspecified), the Orchestrator triggers `@translator` for steps marked with Translation in the dispatch table.

**Execution Sequence** (per AGENTS.md §5.2):

```
Step N agent completes → Review PASS
  → Orchestrator updates SOT: translation_tasks[step-N-{descriptor}].status = "in_progress"
  → Orchestrator records start_time for timeout tracking
  → Orchestrator invokes @translator (Agent tool, subagent_type: "translator")
    Prompt includes:
      - Source file path: prompt/outputs/step-N-{descriptor}.md
      - Instruction: "Translate the above file following your 7-step protocol"
    @translator executes:
      ① Read translations/glossary.yaml
      ② Read English source (complete)
      ③ Translate with glossary consistency
      ④ Self-review + Translation pACS (Ft/Ct/Nt)
      ⑤ Update glossary.yaml (new terms only)
      ⑥ Write prompt/outputs/step-N-{descriptor}.ko.md
      ⑦ Write pacs-logs/step-N-translation-pacs.md
  → Orchestrator calculates duration_sec = now - start_time
  → Orchestrator updates SOT:
      translation_tasks[step-N-{descriptor}] = {
        status: "completed", attempt: K, pacs_score: Ft, duration_sec: D
      }
      outputs.step-N-{descriptor}-ko = path
  → P1 validation: python3 .claude/hooks/scripts/validate_translation.py --step N
  → IF pACS RED (< 50): status → "retry", re-invoke @translator (§3.4 retry semantics)
  → Proceed to next step
```

**Team Step Translation** (Steps 1, 6):

```
Step 1: 3 SOT-recorded outputs → @translator called 3× sequentially:
  1. step-1-param-inventory.md → step-1-param-inventory.ko.md
  2. step-1-pipeline-analysis.md → step-1-pipeline-analysis.ko.md
  3. step-1-error-patterns.md → step-1-error-patterns.ko.md

Step 6: 2 SOT-recorded outputs → @translator called 2× sequentially:
  1. step-6-stock-scan-blueprint.md → step-6-stock-scan-blueprint.ko.md
  2. step-6-filter-tune-blueprint.md → step-6-filter-tune-blueprint.ko.md
```

**Sequential guarantee**: `@translator` modifies `glossary.yaml` on each call. Sequential invocation prevents concurrent write conflicts (절대 기준 2).

**Partial failure recovery (glossary state)**: If translation N of K fails (pACS RED), `glossary.yaml` retains terms added by successful prior translations. Rollback is unnecessary — glossary is append-only. Retranslation reuses existing terms, improving consistency. Retry semantics: `@translator` retranslates weak sections within the failed file (not the entire file from scratch). After 3 failed retranslation attempts on the same file → proceed with best-effort translation and flag in `degradation_notes` (consistent with §12.2). The Orchestrator retries only the failed file, not the entire sequence.

**Translation Timeout Budget** (C-5 — Critical Reflection):

Per-file translation budget: 15 minutes. Aggregate budget per step:
- Single-output steps (2, 4, 5, 10, 11): 15 min max
- Step 1 (3 files sequential): 45 min max
- Step 6 (2 files sequential): 30 min max

Timeout enforcement:
```
IF @translator exceeds per-file budget (15 min):
  → Kill agent, record partial output (if any)
  → Mark SOT: translation_tasks[step-N-file] = {status: "timeout", attempt: K}
  → IF attempt < 3: retry with reduced scope (translate only untranslated sections)
  → IF attempt >= 3: flag in degradation_notes, proceed to next file/step
  → Step 12 human gate presents incomplete translation list for manual decision

IF aggregate budget exceeded:
  → Skip remaining translations for this step
  → Record all skipped files in degradation_notes
  → Proceed to next step (English output is authoritative — Korean is supplementary)
```

Context Preservation interaction: precompact triggers at ~80% context budget. If translation sequence is interrupted by precompact, Orchestrator resumes from last successful translation (tracked in SOT `translation_tasks`).

**Why none for Steps 8-9**: Step 8 produces CLAUDE.md with Korean user messages authored directly (not translated). Step 9 produces SKILL.md + references/ — these are agent-consumed prompt engineering artifacts that remain in English for AI performance (D-6).

### 3.5 SOT Write Protocol

```python
# Orchestrator-only write sequence (conceptual)
def update_sot(step_num, status, output_path=None, degradation=None):
    sot_path = "prompt/.claude/state.yaml"
    current = read_yaml(sot_path)
    
    # Design Fix H-4: Backup before every write (rotation: keep last 3)
    backup_path = f"{sot_path}.bak"
    copy_file(sot_path, backup_path)  # Simple single-file backup
    
    current["workflow"]["current_step"] = step_num
    current["workflow"]["status"] = status
    if output_path:
        current["workflow"]["outputs"][f"step-{step_num}-*"] = output_path
    if degradation:
        current["workflow"]["degradation_notes"].append(degradation)
    write_yaml(sot_path, current)
    # PostToolUse hook validates schema automatically
```

**SOT Backup Protocol (Design Fix H-4)**:
- Before every `state.yaml` write, Orchestrator copies current file to `state.yaml.bak`
- On SOT corruption (Fallback F-6): restore from `.bak`, verify schema, resume
- Single backup file (no rotation needed — only latest pre-write state matters)
- Backup is a simple `cp` in Bash — no complex logic

**Local Execution**: Orchestrator runs entirely in the main Claude Code session on local macOS. No remote calls except tool invocations.

---

## 4. Sub-agent Detailed Specifications

### 4.1 Research Phase Agents

#### param-extractor.md

```markdown
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
```

#### pipeline-analyzer.md

```markdown
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
```

#### error-analyzer.md

```markdown
---
model: sonnet
tools: [Read, Write, Grep, Glob]
maxTurns: 20
---

# Error Analyzer

## Purpose
Classify all error/exception patterns in kiwoom-rest-trader. Produce Korean message
mapping table for each error type.

## Context (Injected by Orchestrator)
- Search paths: /Users/tajun/spJavis/kiwoom-rest-trader/scripts/, /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/
- Known types (minimum): KiwoomAuthError, KiwoomApiError, KiwoomConditionError, ResearchError,
  OrganizeError, PrefetchError, httpx.ConnectError, httpx.TimeoutException, FileNotFoundError

## Output Specification
- File: `prompt/outputs/step-1-error-patterns.md`
- Format: Table with columns: | Error Class | Trigger Condition | Exit Code | Stderr Pattern | Source File:Line | Korean Message |
- Must discover ALL custom exception classes beyond the known list
- Korean messages: natural phrasing for non-technical user

## Verification Criteria
1. ≥5 distinct error types documented
2. All 9 known types addressed (found or confirmed absent)
3. Each entry has Korean message mapping
4. Custom exception class definitions (class...Error) discovered via grep

## Failure Behavior
- If fewer than 5 types found: document search patterns used, flag for human review
```

### 4.2 Planning Phase Agents

#### architect.md

```markdown
---
model: opus
tools: [Read, Write, Grep, Glob, Bash]
maxTurns: 25
---

# Architect

## Purpose
Finalize deployment architecture. Verify all path constants against actual filesystem.
Design screener_state.json schema. Define pre-flight verification checklist.

## Context (Injected by Orchestrator)
- Decisions D-1 through D-7 from workflow.md
- KRT_ROOT = /Users/tajun/spJavis/kiwoom-rest-trader
- Step 1 outputs (for error patterns integration)

## Output Specification
- File: `prompt/outputs/step-4-architecture.md`
- Must include: deployment manifest, path verification results, screener_state.json schema,
  pre-flight checklist (a-e), .gitignore update plan, existing .claude/ inventory
- Additionally produces: `docs/code-convention.md`, `docs/architectural-decision-records.md`,
  `docs/code-quality-guide.md` (evaluation criteria files)

## Verification Criteria
1. All path constants verified via `test -d` (results included)
2. screener_state.json schema: last_scan_date, last_param_changes, last_results_summary, current_backup_files
3. Pre-flight checks (a-e) have concrete Bash commands
4. Existing .claude/settings.local.json preservation confirmed
5. No deployment target overwrites existing content

## Failure Behavior
- Path not found: AskUserQuestion to confirm correct kiwoom-rest-trader location
- Permission denied: document and escalate to human
```

#### claude-md-designer.md

```markdown
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
7. Error output pattern specified: Korean summary (1 sentence) + cause + action. Technical detail (file path, stack trace) under "기술 정보:" label — preserves debugging info without triggering user exit (PRD §3 이탈 트리거) — PRD adversarial reflection A-5

## Failure Behavior
- If exceeding 130 lines: merge Output Format into Safety, compress Date Interpretation
```

#### scan-designer.md

```markdown
---
model: opus
tools: [Read, Write, Grep, Glob]
maxTurns: 35
---

# Stock-Scan Skill Designer

## Purpose
Design the complete stock-scan SKILL.md blueprint: 8 execution chains (SCAN_TODAY,
SCAN_SEPARATED, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, COMPARE, COMPARE_PARAMS,
RERUN_FILTERS), pre-flight checks, output formatting, and all references/ file specs.

## Context (Injected by Orchestrator)
- prompt/outputs/step-2-research-report.md (pipeline & param inventory)
- prompt/outputs/step-4-architecture.md (paths, screener_state.json schema)
- prompt/outputs/step-5-claude-md-blueprint.md (intent clusters → chain mapping)

## Pre-Resolved Decision (Design Fix H-8)
- **Type pattern in SHOW_RESULTS**: Use option (b) — omit Type A~E info from
  SHOW_RESULTS output. Add note: "Type 상세는 Stage 1 재평가로 확인 가능".
  Rationale: Re-deriving Type requires reading each passed stock's chart data
  and re-running pattern matching — expensive and fragile. Option (b) is
  deterministic, testable, and sufficient for user needs.
  This decision is PRE-RESOLVED to prevent downstream test ambiguity (GP-4).

## Output Specification
- File: `prompt/outputs/step-6-stock-scan-blueprint.md`
- Must include: 8 chain specifications with input/output/error for each,
  pre-flight check sequence (a-e), output format template with Korean formatting,
  references/ file list with content summaries, safety rule enforcement points

## Verification Criteria
1. All 8 execution chains specified with concrete steps
2. Pre-flight checks (a-e) map to Bash commands
3. Output format includes Korean number formatting rules
4. references/ file list ≥5 files with purpose descriptions
5. Safety rules TS-1~5 enforcement points marked per chain
6. screener_state.json read/write points documented
7. SHOW_RESULTS uses option (b): no Type re-derivation, Korean note instead
8. Execution chains specify Bash timeout value (600000ms for run_prefetch/run_full_research_flow) — PRD adversarial reflection A-1
9. Log file manipulation rules: masterReference.log/masterReference.md use Edit (append) only, never Write (overwrite) — PRD adversarial reflection A-2
10. KRT execution error retry budget specified: same error type 2× consecutive → stop + Korean explanation of manual action required. AI-unresolvable error list included (API auth, network, disk) — PRD adversarial reflection A-3

## Failure Behavior
- Missing pipeline data from Step 2: use code analysis as fallback
- Chain specification ambiguity: flag for Step 7 human review
```

#### tune-designer.md

```markdown
---
model: opus
tools: [Read, Write, Grep, Glob]
maxTurns: 40
---

# Filter-Tune Skill Designer

## Purpose
Design the complete filter-tune SKILL.md blueprint: master tuning sequence (8 steps),
6 branch flows (SHOW_PARAMS, CONFIRM, RESTORE, THEORY_GUIDE, ASK_MODULE,
COMPARE_EXPERIMENTS), parameter range-map, backup/restore protocol, and all
references/ file specs.

## Context (Injected by Orchestrator)
- prompt/outputs/step-2-research-report.md (param inventory with ranges)
- prompt/outputs/step-4-architecture.md (paths, backup protocol design)
- prompt/outputs/step-5-claude-md-blueprint.md (intent clusters → branch mapping)

## Output Specification
- File: `prompt/outputs/step-6-filter-tune-blueprint.md`
- Must include: 8-step master sequence with decision points, 6 branch flow
  specifications, range-map.md content (parameter bounds + Korean warnings),
  backup/restore protocol with file naming convention, theory-guide.md content
  outline, references/ file list with content summaries

## Verification Criteria
1. Master sequence has 8 numbered steps with clear entry/exit criteria
2. All 6 branches specified with trigger conditions
3. range-map covers all Final constants from Step 1 inventory
4. Backup protocol: *.bak.YYYYMMDD_HHmmss naming enforced
5. TS-1~5 enforcement points marked in tuning sequence
6. Theory guide references PRD §5 parameter relationships
7. references/ file list ≥6 files with purpose descriptions
8. Parameter structure validation before modification: verify target variable is `Final[...]` typed Python constant (not YAML/JSON/other format). If not Final → report "구조 변경 감지" + halt modification — PRD adversarial reflection C-2
9. Comment update rule: when modifying a constant value, update any comment on the same or adjacent line that references the old value. Unrelated comments untouched — PRD adversarial reflection C-3
10. Tuning log '비고' field content specification: minimum = (a) 변경 동기 (user's stated reason or summary), (b) 확정 여부 (확정/실험 중). Example: "약세장 대응, 수급 강화 — 실험 중" — PRD adversarial reflection C-4
11. Backup exhaustion recovery procedure documented: when all 5 backups consumed and user wants earlier value → read tuning-log.md for historical values → Edit re-application — PRD adversarial reflection A-4/O-1

## Failure Behavior
- Missing parameter ranges from Step 2: use code-derived defaults, flag uncertainty
- Theory guide gaps: mark sections as "[NEEDS_DOMAIN_EXPERT]" for Step 7 review
```

### 4.3 Implementation Phase Agents

#### claude-md-builder.md

```markdown
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
- Deploy to: /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md
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

## Pre-Write Protocol (CCP — 절대 기준 3)
Before any Write operation to kiwoom-rest-trader:
1. `ls -la /Users/tajun/spJavis/kiwoom-rest-trader/` — inventory existing files
2. `ls -la /Users/tajun/spJavis/kiwoom-rest-trader/.claude/` — inventory .claude/ contents
3. Verify: no file at target path (CLAUDE.md must not exist — §0 Invariants)
4. Verify: .claude/settings.local.json exists and will NOT be touched
5. Plan: single Write tool call for complete CLAUDE.md (no partial writes)
6. If ANY unexpected file found at target: STOP, report to Orchestrator

## Failure Behavior
- Write permission denied: ls -la check, escalate to human
- Blueprint inconsistency detected: flag specific issue, request re-design
```

#### scan-builder.md / tune-builder.md

```markdown
---
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep]
maxTurns: 40  # scan-builder: 40, tune-builder: 50
---

# {Stock-Scan | Filter-Tune} Builder

## Purpose
Build and deploy the complete {stock-scan | filter-tune} skill to
kiwoom-rest-trader/.claude/skills/{stock-scan | filter-tune}/.
Dense checkpoint pattern: CP-1 → CP-2 → CP-3.

## Context (Injected by Orchestrator)
- prompt/outputs/step-2-research-report.md
- prompt/outputs/step-4-architecture.md
- prompt/outputs/step-6-{stock-scan|filter-tune}-blueprint.md (primary source)
- /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md (Step 8 deployed — cross-ref)

## Pre-Write Protocol (CCP — 절대 기준 3)
Before any Write/mkdir to kiwoom-rest-trader:
1. `ls -la /Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/` — check existing
2. Verify target subdirectory does NOT exist yet
3. Plan write sequence: mkdir → SKILL.md → references/*.md (ordered)
4. Each Write must be complete file (no partial/incremental writes)
5. If directory already exists: STOP, report to Orchestrator

## Dense Checkpoints
- CP-1: Directory structure created, empty SKILL.md placeholder → verify `test -d`
- CP-2: SKILL.md complete with all chains/sequences → verify content checks
- CP-3: All references/ files written → verify completeness against blueprint

## Output Specification
- Deploy to: /Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/{stock-scan|filter-tune}/
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
- Blueprint gap: flag specific section, request scan-designer/tune-designer rework
```

---

## 5. Skills

### 5.1 workflow-executor Skill

**Location**: `.claude/skills/workflow-executor/`

#### SKILL.md Structure

```markdown
# Workflow Executor — Stock Filter Orchestration Build

## Purpose
Orchestrate the 12-step build workflow defined in prompt/workflow.md.
This skill is the single entry point for executing the infrastructure build.

## Trigger
- User invokes directly or orchestrator session begins
- Session start: read state.yaml to determine resume point

## Core Loop
1. Read prompt/.claude/state.yaml
2. Determine current_step
3. Consult references/step-dispatch.md for dispatch parameters
4. Execute step (Agent/Team/Human gate)
5. Run verification (pytest)
6. Update SOT
7. Proceed or fallback

## Constraints
- SOLE SOT WRITER — no agent writes state.yaml
- Team steps 1, 6: parallel Agent calls. Step 9: SEQUENTIAL (C-4 fix)
- Human steps: present in Korean, await approval
- Step 12: ALWAYS human-verified — never auto-approve regardless of autopilot (M-3)
- Every agent spawn includes full context injection (no assumptions)
- All agents that produce output files have Write tool — they write their own output
- Before every state.yaml write: backup to state.yaml.bak (H-4)
- KRT long-running commands (run_prefetch, run_full_research_flow): Bash timeout=600000ms (10 min). PRD adversarial A-1
- Log files (masterReference.log, tuning-log.md): Edit append-only, never Write overwrite. PRD adversarial A-2
- KRT error retry budget: same error type 2× → halt + escalate to user with Korean guide (F-13). PRD adversarial A-3

## Cross-References
- Workflow spec: prompt/workflow.md
- SOT: prompt/.claude/state.yaml
- Tests: prompt/.claude/tests/
- Fallback: references/fallback-paths.md
```

### 5.2 Skill Files NOT Created Here

The `stock-scan` and `filter-tune` skills are **products of the workflow** (Steps 8-9), not infrastructure. They are deployed to kiwoom-rest-trader, not to this project.

---

## 6. Hooks

### 6.1 New Hook: `validate_state_yaml.py`

**Purpose**: Enforce SOT schema integrity on every write to state.yaml.

**Trigger**: PostToolUse on `Write|Edit` where file path matches `**/state.yaml`

**Design Constraint (Design Fix C-3)**: This hook does NOT delegate to `_context_lib.validate_sot_schema()` — that existing function validates the Context Preservation system's autopilot state (different schema with statuses `{running, completed, error, paused}`). Instead, this hook imports enums directly from `infra_schema.py` to validate the workflow-specific `state.yaml` schema. This prevents cross-schema contamination while maintaining single-source enum definition (R-10).

**Schema coverage**: Must validate all top-level fields including `translation_tasks` (C-1). Each entry in `translation_tasks` must have: `status` ∈ {pending, in_progress, completed, retry, timeout, degraded}, `attempt` ∈ int≥0, `pacs_score` ∈ null|float[0-100], `duration_sec` ∈ null|int≥0.

> **Codegen (§17)**: Status enum values are defined once in `infra_schema.WORKFLOW_STATUS_ENUM` and `infra_schema.TRANSLATION_STATUS_ENUM`. Both `validate_state_yaml.py` and `generate_infra.py` import from this single source — eliminates enum duplication (R-10 resolution).

**Path resolution (Design Fix H-3)**: `infra_schema.py` lives at `prompt/.claude/codegen/infra_schema.py`. The hook resolves it via `CLAUDE_PROJECT_DIR` environment variable:
```python
codegen_dir = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), "prompt", ".claude", "codegen")
sys.path.insert(0, codegen_dir)
from infra_schema import WORKFLOW_STATUS_ENUM, TRANSLATION_STATUS_ENUM
```

**Scope restriction (Design Fix M-5)**: Hook only triggers for the workflow SOT at `prompt/.claude/state.yaml`, not arbitrary state.yaml files elsewhere.

**PyYAML requirement (Design Fix H-7)**: Phase 0.1 installs PyYAML (`pip install pyyaml`) as infrastructure prerequisite. Primary path always uses PyYAML; fallback regex path handles only edge cases where installation failed.

**Logic**:
```python
import sys, json, os, re

# Exact SOT path — prevents false triggers on unrelated state.yaml files (M-5)
WORKFLOW_SOT_SUFFIX = os.path.join("prompt", ".claude", "state.yaml")

def validate():
    tool_input = json.loads(os.environ.get("CLAUDE_TOOL_INPUT", "{}"))
    file_path = tool_input.get("file_path", "")
    
    if not file_path.endswith(WORKFLOW_SOT_SUFFIX):
        sys.exit(0)
    
    # Primary: import enums from infra_schema (NOT _context_lib — different schema)
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
            warnings.append(f"invalid status '{status}' — must be one of {WORKFLOW_STATUS_ENUM}")
        
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
        pass  # Fallback below (infra_schema or PyYAML unavailable)
    except FileNotFoundError:
        sys.exit(0)  # state.yaml doesn't exist yet — allow creation
    
    # Fallback: stdlib-only minimal validation
    try:
        content = open(file_path).read()
    except Exception as e:
        print(f"BLOCK: cannot read state.yaml: {e}", file=sys.stderr)
        sys.exit(2)
    
    valid_statuses = {"not_started", "in_progress", "completed", "completed_degraded", "failed"}
    status_match = re.search(r'status:\s*["\']?(\w+)', content)
    if not status_match or status_match.group(1) not in valid_statuses:
        print(f"BLOCK: invalid status", file=sys.stderr)
        sys.exit(2)
    
    step_match = re.search(r'current_step:\s*(\d+)', content)
    if not step_match or not (1 <= int(step_match.group(1)) <= 12):
        print(f"BLOCK: current_step must be 1-12", file=sys.stderr)
        sys.exit(2)
    
    # Fallback: validate translation_tasks statuses via regex
    valid_tr_statuses = {"pending", "in_progress", "completed", "retry", "timeout", "degraded"}
    for m in re.finditer(r'status:\s*["\']?(\w+)', content):
        val = m.group(1)
        if val not in valid_statuses and val not in valid_tr_statuses:
            print(f"BLOCK: unrecognized status '{val}'", file=sys.stderr)
            sys.exit(2)
    
    sys.exit(0)

if __name__ == "__main__":
    validate()
```

**Registration** (append to `.claude/settings.json` PostToolUse):
```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/scripts/validate_state_yaml.py",
      "timeout": 10
    }
  ]
}
```

### 6.2 New Hook: `monitor_translation_output.py`

**Purpose**: Informational monitoring of translation output quality upon write. Non-blocking (exit 0 always).

**Trigger**: PostToolUse on `Write` where file path matches `**/outputs/**-ko.md` OR `**/*.ko.md`

**Design Rationale** (C-2 — Critical Reflection): `validate_translation.py` exists as a standalone P1 script but lacks automatic invocation. This hook provides an early-warning layer — it does NOT block (exit 0), only prints warnings to stderr for Orchestrator awareness. Full P1 validation remains orchestrator-invoked after each translation.

**Logic**:
```python
import sys, json, os

def monitor():
    tool_input = json.loads(os.environ.get("CLAUDE_TOOL_INPUT", "{}"))
    file_path = tool_input.get("file_path", "")
    
    # Only trigger for Korean translation output files
    if not file_path.endswith(".ko.md"):
        sys.exit(0)
    
    # Quick sanity checks (non-blocking — informational only)
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
            import re
            glossary_content = open(glossary_path, encoding="utf-8").read()
            # Extract Korean terms (values after colon in YAML)
            ko_terms = re.findall(r':\s*"([^"]+)"', glossary_content)[:5]
            missing = [t for t in ko_terms if t not in content]
            if len(missing) > 2:
                warnings.append(f"WARN: {len(missing)}/5 top glossary terms missing in translation")
        
        # T-3: Untranslated block detection (3+ consecutive English-only lines)
        lines = content.split("\n")
        consecutive_en = 0
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("```") and not stripped.startswith("#"):
                if all(ord(c) < 128 for c in stripped if c.isalpha()):
                    consecutive_en += 1
                else:
                    consecutive_en = 0
            else:
                consecutive_en = 0
            if consecutive_en >= 5:
                warnings.append("WARN: 5+ consecutive English-only lines detected — possible untranslated block")
                break
        
        if warnings:
            for w in warnings:
                print(w, file=sys.stderr)
    except Exception:
        pass  # Non-blocking — never fail
    
    sys.exit(0)

if __name__ == "__main__":
    monitor()
```

**Registration** (append to `.claude/settings.json` PostToolUse):
```json
{
  "matcher": "Write",
  "hooks": [
    {
      "type": "command",
      "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/scripts/monitor_translation_output.py",
      "timeout": 8
    }
  ]
}
```

**Non-blocking guarantee**: Always exits 0. Warnings printed to stderr appear in Claude Code output but do not block the Write operation. Orchestrator uses these as early signals; definitive validation remains P1 `validate_translation.py`.

### 6.3 Existing Hooks (No Modification)

All existing hooks in `.claude/settings.json` remain intact. New hooks are APPENDED to the PostToolUse array (not replacing existing entries).

**Hook Execution Order for `Write|Edit` on state.yaml** (Critical Reflection C-3a):

When state.yaml is written, PostToolUse hooks fire in array order:
1. `context_guard.py` (matcher: `Edit|Write|Bash|Task|...`) — work log update
2. `security_sensitive_file_guard.py` (matcher: `Edit|Write`) — warns if sensitive file
3. `validate_state_yaml.py` (matcher: `Write|Edit`) — **schema validation, exit 2 on failure**
4. `monitor_translation_output.py` (matcher: `Write`) — informational only, exit 0 always (fires for *.ko.md writes; no-ops for state.yaml)

Claude Code executes all matching hooks regardless of prior exit codes. Exit code 2 from any hook blocks the tool result from being accepted by the model — the write physically completes on disk but the model receives an error signal and must correct it. This means `validate_state_yaml.py` always runs even if prior hooks warn, and its exit code 2 triggers model self-correction for invalid SOT writes.

**SOT Preservation**: Hook only validates; never writes. Exit code 2 blocks invalid writes.

**Local Execution**: Python script, no network. Primary path uses `_context_lib` + PyYAML (installed in project env); fallback path is stdlib-only regex validation (no external dependencies).

---

## 7. Commands

### 7.1 Command Files to Create

| File | Step | Content Summary |
|------|------|-----------------|
| `.claude/commands/review-research.md` | 3 | Read step-2 report, present Korean summary, ask approval |
| `.claude/commands/review-design.md` | 7 | Read steps 4-6, present Korean summary, ask approval |
| `.claude/commands/accept-system.md` | 12 | Guide 10 test scenarios in Korean, record pass/fail |
| `.claude/commands/review-translation.md` | any | Translation progress dashboard + quality summary |

### 7.2 Command Template

```markdown
# /review-research — Research 결과 검토

Read the research integration report.
- Primary (user-facing): `prompt/outputs/step-2-research-report.ko.md` (한국어 번역)
- Reference (detail): `prompt/outputs/step-2-research-report.md` (영어 원본)

## Instructions
1. Read the Korean translation file (primary presentation to user)
2. Summarize key findings in Korean (3-5 bullet points)
3. Present verification status (all PRD C.2 items, workflow-idea C-6 items)
4. Note: "영어 원본: prompt/outputs/step-2-research-report.md 에서 확인 가능합니다."
5. Ask the user: "Research 결과를 승인하시겠습니까? Planning 단계로 진행합니다."
6. On approval: update state.yaml current_step to 4
7. On rejection: ask for specific concerns, prepare re-run of affected Step 1 teammates
```

```markdown
# /review-design — 설계 검토

Read all planning outputs (Korean versions as primary).
- Architecture: `prompt/outputs/step-4-architecture.ko.md` / English: `step-4-architecture.md`
- CLAUDE.md blueprint: `prompt/outputs/step-5-claude-md-blueprint.ko.md` / English: `step-5-claude-md-blueprint.md`
- stock-scan blueprint: `prompt/outputs/step-6-stock-scan-blueprint.ko.md` / English: `step-6-stock-scan-blueprint.md`
- filter-tune blueprint: `prompt/outputs/step-6-filter-tune-blueprint.ko.md` / English: `step-6-filter-tune-blueprint.md`

## Instructions
1. Read all Korean translation files
2. Present concise design summary in Korean per file
3. Note English originals available for technical detail
4. Ask: "설계를 승인하시겠습니까? Implementation 단계로 진행합니다."
5. On approval: update state.yaml current_step to 8
6. On rejection: identify specific blueprint(s) for rework
```

(accept-system adapted per workflow.md Step 12 — no translation involved since it's live testing.)

### 7.3 `/review-translation` Command (C-3 — Critical Reflection)

```markdown
# /review-translation — 번역 현황 대시보드

Read the SOT and all translation outputs to present a comprehensive translation status.

## Instructions
1. Read `prompt/.claude/state.yaml` → extract `translation_tasks` and `outputs.*-ko` keys
2. For each translation-eligible step (1, 2, 4, 5, 6, 10, 11):
   a. Check if English source exists
   b. Check if `.ko.md` translation exists
   c. Read pACS score from `pacs-logs/step-N-translation-pacs.md` (if exists)
   d. Check glossary.yaml change count since last translation
3. Present summary table in Korean:
   | 단계 | 영어 원본 | 한국어 번역 | pACS 점수 | 상태 |
   |------|----------|-----------|----------|------|
4. Highlight:
   - ❌ 미완료 번역 (missing .ko.md files)
   - ⚠️ 저품질 번역 (pACS < 70)
   - ✅ 완료 + 양호 번역
5. Report glossary.yaml statistics:
   - Total terms: N
   - Terms added this workflow: M
6. If any translations are missing or low-quality:
   - Ask: "재번역을 실행하시겠습니까?" with step selection
   - On approval: trigger @translator for selected steps
7. Note: "이 명령은 Human Gate (Step 3, 7, 12) 전에 사용하면 번역 품질을 사전 확인할 수 있습니다."
```

**PG Connection**: Ensures PG-1/PG-2 Korean user-facing outputs meet quality bar before human gates.

---

## 8. Task Verification (TDD)

### 8.1 Test Infrastructure Location

```
prompt/.claude/tests/
├── conftest.py              # Shared constants, path fixtures, helper functions
├── test_step_01_research.py
├── test_step_02_integration.py
├── test_step_04_architecture.py
├── test_step_05_blueprint.py
├── test_step_06_skill_design.py
├── test_step_08_claude_md.py
├── test_step_09_skills.py
├── test_step_10_infra.py
├── test_step_11_smoke.py
└── run_tests.py             # CLI runner: python run_tests.py --step N
```

### 8.2 conftest.py (Shared Fixtures)

> **Codegen (§17)**: Path constants (KRT_ROOT, AW_ROOT, etc.) and domain constants (FILTER_MODULES) are defined in `infra_schema.py` and injected by `generate_infra.py` into the `[CODEGEN]`-delimited section of conftest.py. Manual path or module edits should be made in `infra_schema.py`, not conftest.py directly.

```python
import os
import re
import pytest
from pathlib import Path

# Environment-variable overridable paths (Critical Reflection C-2b: reduces shotgun surgery risk)
KRT_ROOT = Path(os.environ.get("KRT_ROOT", "/Users/tajun/spJavis/kiwoom-rest-trader"))
AW_ROOT = Path(os.environ.get("AW_ROOT", "/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector"))
OUTPUTS = AW_ROOT / "prompt" / "outputs"
GLOSSARY = AW_ROOT / "translations" / "glossary.yaml"
KRT_PYTHON = KRT_ROOT / ".venv" / "bin" / "python"
KRT_FILTERS = KRT_ROOT / "src" / "kiwoom" / "itemFilter"
KRT_REPORTS = KRT_ROOT / "reports"
KRT_SCRIPTS = KRT_ROOT / "scripts"

@pytest.fixture
def outputs_dir():
    return OUTPUTS

@pytest.fixture
def krt_root():
    return KRT_ROOT

@pytest.fixture
def glossary_terms():
    """Load Korean terms from glossary.yaml for consistency verification."""
    if not GLOSSARY.exists():
        return {}
    content = GLOSSARY.read_text(encoding="utf-8")
    # Parse YAML-like "key": "value" pairs (lightweight — no PyYAML dependency in tests)
    terms = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', content))
    return terms  # {English: Korean}
```

### 8.3 Test Examples

#### test_step_01_research.py

```python
"""Step 1: Research output verification."""
from conftest import OUTPUTS

def test_param_inventory_exists():
    f = OUTPUTS / "step-1-param-inventory.md"
    assert f.exists(), "param-inventory output missing"
    assert f.stat().st_size > 100, "param-inventory suspiciously small"

def test_param_inventory_covers_all_modules():
    content = (OUTPUTS / "step-1-param-inventory.md").read_text()
    modules = ["chart60_120", "chart240", "chartDayPre", "chartDay", "investor", "finance", "chart60"]
    for mod in modules:
        assert mod.lower() in content.lower(), f"Module {mod} not found in inventory"

def test_pipeline_analysis_exists():
    f = OUTPUTS / "step-1-pipeline-analysis.md"
    assert f.exists()
    assert f.stat().st_size > 200

def test_error_patterns_exists():
    f = OUTPUTS / "step-1-error-patterns.md"
    assert f.exists()
    content = f.read_text()
    assert content.count("|") > 20, "Error table seems too small (few pipe chars)"

def test_error_patterns_minimum_types():
    content = (OUTPUTS / "step-1-error-patterns.md").read_text()
    error_keywords = ["KiwoomAuthError", "KiwoomApiError", "httpx"]
    found = sum(1 for kw in error_keywords if kw in content)
    assert found >= 3, f"Only {found}/3 known error types found"
```

#### test_step_08_claude_md.py

```python
"""Step 8: Deployed CLAUDE.md verification."""
import subprocess
from conftest import KRT_ROOT

CLAUDE_MD = KRT_ROOT / "CLAUDE.md"

def test_file_exists():
    assert CLAUDE_MD.exists()

def test_line_count():
    lines = CLAUDE_MD.read_text().splitlines()
    assert 80 <= len(lines) <= 130, f"CLAUDE.md is {len(lines)} lines (expected 80-130)"

def test_no_placeholders():
    content = CLAUDE_MD.read_text()
    for placeholder in ["TODO", "PLACEHOLDER", "TBD", "XXX"]:
        assert placeholder not in content, f"Placeholder '{placeholder}' found"

def test_routing_table_clusters():
    content = CLAUDE_MD.read_text()
    # Count intent cluster markers (expect ≥12)
    clusters = content.count("stock-scan") + content.count("filter-tune")
    assert clusters >= 12, f"Only {clusters} skill references found (expect ≥12)"

def test_safety_rules():
    content = CLAUDE_MD.read_text()
    for ts in ["TS-1", "TS-2", "TS-3", "TS-4", "TS-5"]:
        assert ts in content, f"Safety rule {ts} missing"

def test_path_constants_resolve():
    content = CLAUDE_MD.read_text()
    # Extract KRT_ROOT value and verify
    assert str(KRT_ROOT) in content
    assert (KRT_ROOT / ".venv" / "bin" / "python").exists()

def test_settings_local_preserved():
    settings = KRT_ROOT / ".claude" / "settings.local.json"
    # File should still exist if it existed before
    # (orchestrator verifies this pre-step)
    pass  # Existence verified by pre-flight, not post-build
```

### 8.4 Translation Verification Tests

Added to each test file for translation-eligible steps (1, 2, 4, 5, 6, 10, 11):

```python
"""Translation output verification — shared pattern."""
import re
from pathlib import Path
from conftest import OUTPUTS, GLOSSARY

def _verify_translation(english_filename: str):
    """Verify Korean translation exists and meets minimum criteria."""
    en_file = OUTPUTS / english_filename
    ko_file = OUTPUTS / english_filename.replace(".md", ".ko.md")
    
    assert en_file.exists(), f"English source missing: {english_filename}"
    assert ko_file.exists(), f"Korean translation missing: {ko_file.name}"
    assert ko_file.stat().st_size >= 100, f"Translation too small: {ko_file.name}"
    
    en_headings = en_file.read_text().count("\n#")
    ko_headings = ko_file.read_text().count("\n#")
    tolerance = max(1, int(en_headings * 0.2))
    assert abs(en_headings - ko_headings) <= tolerance, \
        f"Heading count mismatch: EN={en_headings}, KO={ko_headings}"

def _verify_glossary_consistency(english_filename: str, min_hit_ratio: float = 0.5):
    """Verify Korean translation uses glossary terms consistently (C-4)."""
    ko_file = OUTPUTS / english_filename.replace(".md", ".ko.md")
    if not ko_file.exists() or not GLOSSARY.exists():
        return  # Skip if prerequisites missing
    
    ko_content = ko_file.read_text(encoding="utf-8")
    glossary_content = GLOSSARY.read_text(encoding="utf-8")
    
    # Extract Korean terms from glossary
    ko_terms = re.findall(r':\s*"([^"]+)"', glossary_content)
    if not ko_terms:
        return
    
    # Check how many glossary Korean terms appear in the translation
    found = sum(1 for term in ko_terms if term in ko_content)
    ratio = found / len(ko_terms)
    assert ratio >= min_hit_ratio, \
        f"Glossary consistency low: {found}/{len(ko_terms)} terms found ({ratio:.0%} < {min_hit_ratio:.0%})"

def _verify_no_untranslated_blocks(english_filename: str, max_consecutive: int = 5):
    """Verify no large untranslated English blocks remain (C-4)."""
    ko_file = OUTPUTS / english_filename.replace(".md", ".ko.md")
    if not ko_file.exists():
        return
    
    content = ko_file.read_text(encoding="utf-8")
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
            # Check if line is purely ASCII (likely untranslated English)
            alpha_chars = [c for c in stripped if c.isalpha()]
            if alpha_chars and all(ord(c) < 128 for c in alpha_chars):
                consecutive_en += 1
            else:
                consecutive_en = 0
        else:
            consecutive_en = 0
        
        assert consecutive_en < max_consecutive, \
            f"Untranslated block detected: {max_consecutive}+ consecutive English lines in {ko_file.name}"

# Example in test_step_01_research.py:
def test_step_1_translations():
    for f in ["step-1-param-inventory.md", "step-1-pipeline-analysis.md", "step-1-error-patterns.md"]:
        _verify_translation(f)

def test_step_1_glossary_consistency():
    for f in ["step-1-param-inventory.md", "step-1-pipeline-analysis.md", "step-1-error-patterns.md"]:
        _verify_glossary_consistency(f)

def test_step_1_no_untranslated_blocks():
    for f in ["step-1-param-inventory.md", "step-1-pipeline-analysis.md", "step-1-error-patterns.md"]:
        _verify_no_untranslated_blocks(f)

# Example in test_step_02_integration.py:
def test_step_2_translation():
    _verify_translation("step-2-research-report.md")

def test_step_2_glossary_consistency():
    _verify_glossary_consistency("step-2-research-report.md")

def test_step_2_no_untranslated_blocks():
    _verify_no_untranslated_blocks("step-2-research-report.md")
```

P1 enforcement: `validate_translation.py` (T1-T9) runs independently per the orchestrator protocol in §3.4 — these pytest tests provide the TDD verification layer. The new `_verify_glossary_consistency` and `_verify_no_untranslated_blocks` helpers (C-4) catch glossary drift and untranslated blocks that the basic size/heading check would miss.

### 8.5 TDD Execution Protocol

```
BEFORE step execution:
  - Orchestrator reads test file → understands acceptance criteria
  - Orchestrator includes criteria in agent prompt context

AFTER step execution:
  - Orchestrator runs: cd prompt/.claude/tests && python -m pytest test_step_{N}*.py -v
  - ALL PASS → proceed
  - ANY FAIL:
    - Retry 1: re-run agent with failure details as feedback
    - Retry 2: re-run with model upgrade (sonnet → opus) if applicable
    - Retry 3: human escalation

OUTPUT: verification-logs/step-{N}-test-results.txt
```

**PG Connection**: Tests encode the verification items from workflow.md — ensuring PG-1 (execution chains work) and PG-2 (tuning sequence complete).

**Local Execution**: pytest runs locally, no network.

---

## 9. Build Isolation (Sequential Execution)

> **Design Fix C-4**: Worktree isolation removed. This project is not a git repository, making `isolation: "worktree"` impossible. Additionally, builders write to an EXTERNAL directory (kiwoom-rest-trader), which worktree cannot isolate regardless. Sequential execution is the sole strategy — functionally equivalent since build targets are disjoint paths.

### 9.1 Isolation Analysis

| Step | Parallel? | Strategy | Rationale |
|------|-----------|----------|-----------|
| 1 (Research) | **Yes** | Parallel Agent calls (no isolation needed) | Read-only operations + disjoint output paths |
| 6 (Design) | **Yes** | Parallel Agent calls (no isolation needed) | Disjoint output paths (`step-6-stock-scan-*` vs `step-6-filter-tune-*`) |
| 9 (Build) | **No** | Sequential: scan-builder → tune-builder | Write to external dir `kiwoom-rest-trader/.claude/skills/` — sequential prevents mkdir race on parent |
| 11 (Smoke) | N/A | Single agent | Read-only verification |

### 9.2 Step 9 Sequential Build Protocol

```
1. Orchestrator spawns scan-builder (NO isolation parameter)
   → Builder creates: kiwoom-rest-trader/.claude/skills/stock-scan/ (SKILL.md + references/)
   → On completion: Orchestrator verifies directory exists + all files present
   → CP-1/CP-2/CP-3 checkpoints validated

2. AFTER scan-builder completes:
   Orchestrator spawns tune-builder (NO isolation parameter)
   → Builder creates: kiwoom-rest-trader/.claude/skills/filter-tune/ (SKILL.md + references/)
   → On completion: Orchestrator verifies directory exists + all files present
   → CP-1/CP-2/CP-3 checkpoints validated

3. Post-build verification:
   → Both skill directories exist with all expected files
   → Cross-reference: SKILL.md references/*.md all resolve
   → No merge step needed (sequential writes to disjoint paths)
```

**Quality trade-off**: Sequential is ~10 min slower than parallel but eliminates all race conditions. Per 절대 기준 1, quality (correctness) dominates speed.

---

## 10. Fallback Design

### 10.1 Hierarchical Fallback Table

| Level | Trigger | Action | SOT Update |
|-------|---------|--------|------------|
| F-1 | Agent fails (timeout/error) | Retry same agent with error feedback (max 3) | status: "in_progress" |
| F-2 | Agent fails 3× | Orchestrator executes directly using agent's prompt as guide | degradation_notes: append |
| F-3 | Team member unresponsive | Kill + replace. If 2nd fails → orchestrator takes over that role | degradation_notes: append |
| F-4 | Team coordination breaks | Terminate team. Re-execute sequentially with prior outputs as context | active_team: null |
| F-5 | ~~Worktree merge conflict~~ | ~~Apply changes sequentially~~ **(Removed — C-4: no worktree, sequential by design)** | — |
| F-6 | SOT corrupted | Restore from `state.yaml.bak` (H-4). If .bak also corrupt: reconstruct from existing output files on disk | Rebuilt from outputs |
| F-7 | @reviewer timeout | Log warning, proceed. Flag for Step 12 human validation | decisions: append "review_bypassed" |
| F-8 | Path not found | AskUserQuestion: confirm kiwoom-rest-trader location | Block until resolved |
| F-9 | 3+ consecutive step failures | Present diagnostic to human with options: retry/intervene/abort | status: "failed" |
| F-10 | @translator timeout (>15 min per file) | Kill agent, record partial. Retry up to 3×. After 3×: proceed with English-only, flag in degradation_notes | translation_tasks[file].status: "timeout" |
| F-11 | Translation aggregate budget exceeded (step total) | Skip remaining translations for this step. English is authoritative; Korean is supplementary | degradation_notes: append |
| F-12 | Target file already exists (prior partial run) | Verify content completeness. If incomplete/corrupt → delete and rewrite. If complete and valid → skip step, record in SOT. Applies to: CLAUDE.md (Step 8), skill dirs (Step 9), support files (Step 10) | outputs: record existing path |
| F-13 | KRT execution error (API auth expired, network, disk) — AI-unresolvable | Same error 2× consecutive → halt retry. Present Korean explanation: error type + what user must do manually. AI-unresolvable types: Kiwoom API 인증 만료, 네트워크 단절, 디스크 공간 부족. Resume only after user confirms fix — PRD adversarial reflection A-3 | status remains "in_progress", degradation_notes: append "krt_error_escalated" |

### 10.2 Degraded Completion

If any step completes with degradation (F-2, F-3 outcomes):
- SOT records `status: "completed_degraded"`
- `degradation_notes` lists affected steps
- Step 12 human review receives degradation report as additional context
- System is still usable but may have gaps flagged for human attention

---

## 11. SOT (Source of Truth) Specification

### 11.1 File: `prompt/.claude/state.yaml`

> **Codegen (§17)**: This YAML template is auto-generated by `generate_infra.py` from `infra_schema.py`. The `outputs` keys (22) and `translation_tasks` entries (10) are derived from `AGENT_ROSTER[*].output_key` — no manual enumeration. Schema changes propagate to `validate_state_yaml.py` automatically via shared enum imports.

```yaml
workflow:
  name: "stock-filtering-collector"
  version: "1.0.0"
  current_step: 1
  status: "not_started"
  degradation_notes: []
  parent_genome:
    version: "2026-05-26"
    source: "AgenticWorkflow"
  outputs:
    step-1-param-inventory: null
    step-1-param-inventory-ko: null
    step-1-pipeline-analysis: null
    step-1-pipeline-analysis-ko: null
    step-1-error-patterns: null
    step-1-error-patterns-ko: null
    step-2-research-report: null
    step-2-research-report-ko: null
    step-4-architecture: null
    step-4-architecture-ko: null
    step-5-claude-md-blueprint: null
    step-5-claude-md-blueprint-ko: null
    step-6-stock-scan-blueprint: null
    step-6-stock-scan-blueprint-ko: null
    step-6-filter-tune-blueprint: null
    step-6-filter-tune-blueprint-ko: null
    step-8-claude-md: null
    step-9-stock-scan-skill: null
    step-9-filter-tune-skill: null
    step-10-validation-report: null
    step-10-validation-report-ko: null
    step-11-smoke-test: null
    step-11-smoke-test-ko: null
  translation_tasks:
    step-1-param-inventory: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-1-pipeline-analysis: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-1-error-patterns: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-2-research-report: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-4-architecture: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-5-claude-md-blueprint: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-6-stock-scan-blueprint: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-6-filter-tune-blueprint: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-10-validation-report: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
    step-11-smoke-test: {status: "pending", attempt: 0, pacs_score: null, duration_sec: null}
  # translation_tasks.status: pending | in_progress | completed | retry | timeout | degraded
  # Orchestrator updates after each @translator invocation — sole writer (절대 기준 2)
  autopilot:
    mode: "enabled"
    decisions: []
  active_team: null
  completed_teams: []
```

**`-ko` key convention**: Anti-Skip Guard's `.isdigit()` guard automatically skips `-ko` suffixed keys. Translation verification is handled by Orchestrator checklist + P1 `validate_translation.py`, not Anti-Skip Guard.

### 11.2 Write Rules

1. **SOLE WRITER**: Orchestrator (main session) only
2. **Atomic writes**: Single Write tool call per update (no partial YAML)
3. **Validation**: PostToolUse hook (`validate_state_yaml.py`) enforces schema
4. **Read access**: All agents may read via Read tool (injected in prompt context)
5. **No agent writes**: Agents produce to `prompt/outputs/` — orchestrator records paths in SOT

### 11.3 State Transitions

```
not_started → in_progress     (first step begins)
in_progress → in_progress     (step advances: current_step incremented)
in_progress → completed       (step 12 passes)
in_progress → completed_degraded  (step 12 passes with degradation_notes non-empty)
in_progress → failed          (3+ consecutive failures, human opts to abort)
failed → in_progress          (human restarts from specific step)
```

---

## 12. English Execution Rules

### 12.1 Language Assignment Table

| Artifact | Language | Justification |
|----------|----------|---------------|
| Agent definition files (.claude/agents/*.md) | English | AI execution quality (D-6) |
| Agent prompts (dispatch text) | English | Thinking/reasoning quality |
| Skill SKILL.md files (workflow-executor) | English | Agent-consumed |
| Test files (prompt/.claude/tests/) | English | Code |
| Hook scripts | English | Code |
| SOT (state.yaml) | English | Machine-readable |
| Step output files (prompt/outputs/) | English | Agent-consumed intermediate artifacts |
| Deployed CLAUDE.md (kiwoom-rest-trader) | **Mixed** | Routing structure English, user messages Korean |
| Deployed skill files (stock-scan, filter-tune) | **Mixed** | Chain logic English, Korean user messages embedded |
| Slash command descriptions | Korean | User-facing |
| Error messages in final skills | Korean | End-user consumption |
| Orchestrator↔User communication | Korean | User interaction |
| docs/ evaluation criteria files | English | Technical reference for agents |

### 12.2 Translation Protocol Integration

**Principle**: All agent execution produces English outputs. `@translator` sub-agent converts text content to Korean after each step's Review pass.

**Bilingual Output Pair Rule** (AGENTS.md §5.2 activation):
```
prompt/outputs/step-N-{descriptor}.md      # English original (agent-produced)
prompt/outputs/step-N-{descriptor}.ko.md   # Korean translation (@translator-produced)
```

**Orchestrator Sequence** (full pipeline per step):
```
Agent work (English) → L0 → L1 → L1.5 → L2 Review → PASS
  → @translator invocation (sequential, one file at a time)
  → SOT -ko path recording
  → P1 validate_translation.py
  → Next step
```

**Translation-eligible steps**: 1, 2, 4, 5, 6, 10, 11 (7 steps producing text content)
**Translation-exempt steps**: 8 (Korean authored directly), 9 (code-like deliverables)

**glossary.yaml**: `@translator`'s persistent external memory (RLM pattern). Updated by translator only — Orchestrator never touches it. No concurrent write risk since translation runs sequentially per step.

**Failure handling**: Translation pACS RED (< 50) → automatic retranslation of weak sections. After 3 failed retranslation attempts → proceed with best-effort translation and flag in degradation_notes.

### 12.3 Korean Quality Rule

Korean text in final deployed files must be:
- Natural phrasing (not literal translation from English)
- Verified by reading aloud (no awkward constructs)
- Following number formatting: "4,805원", "-3.5%", "0.965배"
- Following expression policy: "기술적 완성도가 높은 종목" (O) / "매수 추천" (X)

---

## 13. Evaluation Criteria Files

### 13.1 `docs/code-convention.md`

**Creation**: Step 4 (architect agent output)
**Used by**: All implementation agents (Steps 8, 9, 10) as context injection

```markdown
# Code Convention — Stock Filter Orchestration

## Naming
- Skill directories: kebab-case (stock-scan/, filter-tune/)
- Output files: step-{N}-{descriptor}.md
- Reference files: kebab-case.md
- Agent files: kebab-case.md matching agent role name

## Markdown Structure
- CLAUDE.md: max 130 lines, 10 sections, no headers beyond H3
- SKILL.md: numbered chains with [checkpoint] markers
- references/: flat directory, no subdirectories

## Content Rules
- Zero placeholder text (TODO, TBD, PLACEHOLDER, XXX — grep-enforced)
- All path constants: verified absolute paths resolving to real filesystem
- Korean text: natural phrasing, Korean number formatting
- Parameter names: exact match to Python variable names (grep-verified)
- Cross-references: every mentioned file must exist on disk
- Log file manipulation: append-only files (masterReference.log, tuning-log.md) use Edit tool (append) — never Write (full overwrite). PRD adversarial A-2
- Comment hygiene: when modifying a Python constant value, update same-line/adjacent-line comments that reference the old value. Leave unrelated comments untouched. PRD adversarial C-3
- Tuning log '비고': minimum content = change motivation (user's words) + decision status (확정/실험 중). PRD adversarial C-4

## Verification Commands
- Placeholder check: grep -c 'TODO\|PLACEHOLDER\|TBD\|XXX' {file} → must return 0
- Line count: wc -l {file} → must be within documented range
- Path check: test -d {path} → must succeed for all referenced directories
```

### 13.2 `docs/architectural-decision-records.md`

**Creation**: Step 4 (initialized with D-1~D-7). Updated after each step with new decisions.
**Used by**: Orchestrator for decision consistency, @reviewer for design coherence

```markdown
# Architectural Decision Records — Stock Filter Orchestration

## Format
Each ADR: Context → Decision → Alternatives → Rationale → Source

## Pre-Resolved (from workflow.md)

### ADR-001: Deploy to kiwoom-rest-trader
- Context: Where should CLAUDE.md + skills live?
- Decision: /Users/tajun/spJavis/kiwoom-rest-trader/
- Alternatives: (a) same dir [chosen], (b) separate orchestration repo
- Rationale: User opens Claude Code there; shortest path constants; .claude/ exists
- Source: workflow.md D-1, workflow-idea C-8

### ADR-002: SCAN_TODAY = run_full_research_flow
- Context: Default execution command for "오늘 종목 스캔해줘"
- Decision: run_full_research_flow (combined prefetch+filter)
- Alternatives: (a) combined [chosen], (b) separated by default
- Rationale: PRD FR-1.1; user says "나눠서 해줘" for separated
- Source: workflow.md D-2, workflow-idea C-10

### ADR-003: 2-Skill architecture
- Context: How many skills?
- Decision: stock-scan + filter-tune (2 skills)
- Alternatives: (a) 2 skills [chosen], (b) single mega-skill, (c) 3+ skills
- Rationale: Different interaction patterns (fire-and-forget vs iterative)
- Source: workflow.md D-3, workflow-idea B-1

### ADR-004: Parameter SOT = Python Final constants
- Context: Where is the canonical parameter value?
- Decision: Always Read actual Python code; documentation is reference only
- Alternatives: (a) code as SOT [chosen], (b) separate config file
- Rationale: Avoids sync issues; code is always truth
- Source: workflow.md D-4, workflow-idea C-1

### ADR-005: Session continuity via screener_state.json
- Context: How to persist session state across Claude Code sessions?
- Decision: JSON file at reports/screener_state.json, CLAUDE.md rule (no Hook dependency)
- Alternatives: (a) JSON file [chosen], (b) Hook-based, (c) memory system
- Rationale: kiwoom-rest-trader lacks AgenticWorkflow Hook infrastructure
- Source: workflow.md D-5, workflow-idea B-12

### ADR-006: English execution + bilingual output pair
- Context: What language for agent execution? How to serve Korean-speaking user?
- Decision: English for agent thinking/execution; @translator produces Korean translation per step; results stored as English+Korean pair; Korean version presented to user at human gates
- Alternatives: (a) English execution + per-step translation [chosen], (b) All Korean, (c) English only with manual user translation
- Rationale: AI performance maximization (절대 기준 1) + user accessibility via @translator (AGENTS.md §5.2). Translation adds quality-cost (time), which is explicitly acceptable under 절대 기준 1 ("속도 완전 무시").
- Source: workflow.md D-6, AGENTS.md §5.2, 추가 절대 원칙 1-2

### ADR-007: .venv/bin/python execution template
- Context: How to run Python in kiwoom-rest-trader?
- Decision: cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}
- Alternatives: (a) .venv/bin/python [chosen], (b) source activate
- Rationale: Shell-state independent; avoids activate issues
- Source: workflow.md D-7, workflow-idea B-6

### ADR-008: Phase 2 transition criteria (PRD adversarial reflection C-1)
- Context: When does Phase 1 end and Phase 2 begin?
- Decision: Phase 2 begins when ALL of: (a) SC-1.1~SC-2.7 all achieved, (b) user completes 5+ independent tuning sessions, (c) 4 weeks operation without critical bugs
- Alternatives: (a) measurable criteria [chosen], (b) time-based only, (c) user request
- Rationale: Adversarial reflection identified "Phase 1 안정화 후" as unmeasurable — concrete criteria prevent indefinite Phase 1 stagnation
- Source: PRD §12, adversarial reflection C-1

## Runtime Decisions (appended during execution)
[Orchestrator appends here after Steps 4, 5, 6, 8, 9 as needed]
```

### 13.3 `docs/code-quality-guide.md`

**Creation**: Step 4 (architect agent output)
**Used by**: @reviewer (scoring rubric), @smoke-tester (test design reference)

```markdown
# Code Quality Guide — Stock Filter Orchestration

## Quality Dimensions & Weights

| Dimension | Weight | PASS Criteria |
|-----------|--------|---------------|
| Functional Completeness | 30% | All 12 clusters routable, all chains encoded |
| Internal Consistency | 25% | Zero broken cross-references |
| User Experience | 20% | Natural Korean, correct formatting, clear flow |
| Structural Compliance | 15% | Line counts within bounds, all sections present |
| Safety & Robustness | 10% | TS-1~5 present, range validation, backup protocol |

## Functional Completeness Checklist
- [ ] 12 intent clusters in CLAUDE.md routing table
- [ ] 8 execution chains in stock-scan SKILL.md (SCAN_TODAY, SCAN_SEPARATED, SCAN_RANGE,
      SHOW_RESULTS, WHY_REJECTED, COMPARE, COMPARE_PARAMS, RERUN_FILTERS)
- [ ] 8 tuning sequence steps in filter-tune master sequence
- [ ] 6 branches in filter-tune (SHOW_PARAMS, CONFIRM, RESTORE, THEORY_GUIDE,
      ASK_MODULE, COMPARE_EXPERIMENTS)
- [ ] Pre-flight checks (a-e) executable

## Internal Consistency Rules
- Every skill name in CLAUDE.md → SKILL.md directory exists
- Every references/*.md in SKILL.md → file exists on disk
- Path constants in CLAUDE.md → directories exist (test -d)
- Parameter names in range-map.md → match Python variable names (grep)
- Error types in CLAUDE.md → match Step 1 classification

## UX Quality Standards
- Korean number format: "4,805원", "-3.5%", "0.965배"
- Disclaimer: full on first output per session, abbreviated 1-line on subsequent
- Expression policy: "기술적 완성도가 높은 종목" (O) / "매수 추천" (X)
- Safety warnings in Korean: clear, non-technical language
- Error output pattern: Korean summary (1문장) + 원인 + 조치방법. Technical detail (path, traceback) under "기술 정보:" label — user reads summary, AI retains debug data. PRD adversarial A-5
- Retry budget: same KRT error 2× → stop retrying, present user-actionable Korean guide. AI-unresolvable: API 인증, 네트워크, 디스크. PRD adversarial A-3

## Structural Bounds
- CLAUDE.md: 80-130 lines
- SKILL.md: organized with numbered chains
- references/: flat, complete, no stubs
- state.yaml: valid schema (hook-enforced)

## Safety Requirements
- TS-1: Only Final constants modifiable (no filter logic changes)
- TS-2: Backup before any parameter change (*.bak.YYYYMMDD_HHmmss)
- TS-3: Range validation with Korean warning for out-of-bounds
- TS-4: One-at-a-time recommendation (multi-param warning)
- TS-5: Rerun suggestion after parameter change
```

---

## 14. Implementation Order

### 14.1 Build Sequence (Dependencies)

```
Phase 0-pre: Codegen Bootstrap (§17 — hallucination prevention)
  ├── 0-pre.1: Create infra_schema.py (build-time SOT — all structured data)
  ├── 0-pre.2: Create generate_infra.py (deterministic file generator)
  └── 0-pre.3: Create validate_infra.py (cross-reference integrity checker)

Phase 0: Infrastructure Bootstrap (this document's scope)
  ├── 0.0: Prerequisites — pip install pyyaml (H-7); verify KRT_ROOT exists
  ├── 0.1: Create runtime directories
  ├── 0.2: generate_infra.py → state.yaml (SOT initialization — auto-generated from schema)
  ├── 0.3: generate_infra.py → validate_state_yaml.py enum imports + register in settings.json
  ├── 0.3b: Create monitor_translation_output.py hook + register in settings.json
  ├── 0.4: generate_infra.py → conftest.py [CODEGEN] constants; LLM authors test logic
  ├── 0.5: generate_infra.py → 13 agent frontmatter; LLM authors agent body content
  ├── 0.6: generate_infra.py → step-dispatch.md; LLM authors SKILL.md + fallback-paths.md
  ├── 0.7: generate_infra.py → command file path refs; LLM authors command instructions
  ├── 0.8: Create 3 evaluation criteria files (docs/) — LLM authored
  └── 0.9: validate_infra.py → cross-reference integrity check (GATE — must pass before Phase 1)

Phase 1: Workflow Execution (post-infrastructure)
  Steps 1-12 as defined in workflow.md
```

### 14.2 Critical Path

```
infra_schema.py → generate_infra.py → {state.yaml, agent frontmatter, step-dispatch.md, conftest constants, enum imports}
  → validate_infra.py (cross-reference gate — MUST PASS)
  → hook (validates writes) → agents (consume state) → skill (dispatches agents) → tests (verify outputs)
```

If any of these are malformed, downstream steps fail. Build order matters.

---

## 15. File Manifest (Complete)

### New Files (39 total)

```
# Agent definitions (13)
.claude/agents/param-extractor.md
.claude/agents/pipeline-analyzer.md
.claude/agents/error-analyzer.md
.claude/agents/research-integrator.md
.claude/agents/architect.md
.claude/agents/claude-md-designer.md
.claude/agents/scan-designer.md
.claude/agents/tune-designer.md
.claude/agents/claude-md-builder.md
.claude/agents/scan-builder.md
.claude/agents/tune-builder.md
.claude/agents/infra-validator.md
.claude/agents/smoke-tester.md

# Skill (3 files)
.claude/skills/workflow-executor/SKILL.md
.claude/skills/workflow-executor/references/step-dispatch.md
.claude/skills/workflow-executor/references/fallback-paths.md

# Commands (4)
.claude/commands/review-research.md
.claude/commands/review-design.md
.claude/commands/accept-system.md
.claude/commands/review-translation.md

# Hooks (2)
.claude/hooks/scripts/validate_state_yaml.py
.claude/hooks/scripts/monitor_translation_output.py

# SOT (1)
prompt/.claude/state.yaml

# Tests (11)
prompt/.claude/tests/conftest.py
prompt/.claude/tests/test_step_01_research.py
prompt/.claude/tests/test_step_02_integration.py
prompt/.claude/tests/test_step_04_architecture.py
prompt/.claude/tests/test_step_05_blueprint.py
prompt/.claude/tests/test_step_06_skill_design.py
prompt/.claude/tests/test_step_08_claude_md.py
prompt/.claude/tests/test_step_09_skills.py
prompt/.claude/tests/test_step_10_infra.py
prompt/.claude/tests/test_step_11_smoke.py
prompt/.claude/tests/run_tests.py

# Evaluation criteria (3)
docs/code-convention.md
docs/architectural-decision-records.md
docs/code-quality-guide.md

# Codegen layer (3 — §17, Phase 0-pre)
prompt/.claude/codegen/infra_schema.py
prompt/.claude/codegen/generate_infra.py
prompt/.claude/codegen/validate_infra.py

# Runtime directories (5 — created empty)
prompt/outputs/          # English originals + Korean translations (*.ko.md)
verification-logs/
pacs-logs/               # Includes step-N-translation-pacs.md from @translator
review-logs/
autopilot-logs/
```

### Modified Files (1)

```
.claude/settings.json  — append validate_state_yaml.py + monitor_translation_output.py to PostToolUse hooks
```

### Deleted Files (0)

---

## 16. Risk Register

| # | Risk | Impact | Mitigation | Owner |
|---|------|--------|-----------|-------|
| R-1 | Agent definitions too vague → poor output quality | High (cascades through all steps) | Each agent has explicit Verification Criteria + Output Specification | Implementer |
| R-2 | TeamCreate experimental feature unavailable | Medium (slower execution) | Fallback F-4: parallel Agent calls | Orchestrator |
| R-3 | ~~Worktree isolation not supported~~ | ~~Low~~ **(RESOLVED C-4: worktree removed, sequential-only by design)** | §9 redesigned — no git repo needed | N/A |
| R-4 | Test files have false negatives | Medium (bad output passes) | @reviewer L2 provides second opinion | Review cycle |
| R-5 | Context overflow during long workflow | Medium (loss of state) | Existing Context Preservation + state.yaml as recovery point | Hooks |
| R-6 | settings.json hook registration breaks existing hooks | High (system destabilized) | APPEND only, test after modification | Implementer |
| R-7 | @translator maxTurns (20) insufficient for large outputs | Low (largest output ~step-2) | Monitor; increase to 30 if step-2 translation truncates | Orchestrator |
| R-8 | glossary.yaml concurrent write (team step parallel calls) | Medium (term inconsistency) | Sequential @translator invocation guaranteed by §3.4 protocol | Orchestrator |
| R-9 | Translation quality drift across 12 invocations | Low (glossary anchors terms) | Translation pACS per step; glossary.yaml accumulates; memory: project stores style patterns | @translator |
| R-10 | Schema validation duplication (hook vs _context_lib) | Medium (schema drift) | **Mitigated (C-3 fix)**: hook imports enums from `infra_schema.py` directly — does NOT use `_context_lib.validate_sot_schema()` (different schema). Single enum source via codegen (§6.1, §17) | Implementer |
| R-11 | Implementation agents overwrite existing files in target | Medium (data loss) | **Mitigated**: CCP Pre-Write Protocol in agent template + builder specs (§2.1, §4.3) | Builder agents |
| R-12 | Path constant change requires multi-file edit | Low→Medium (maintenance) | **Mitigated**: conftest.py uses env vars; agent paths injected via context (§8.2) | Implementer |
| R-13 | Translation timeout cascade (Step 1: 3 sequential × 15min = 45min) | Medium (context pressure) | **Mitigated**: §3.4 timeout budget + F-10/F-11 fallback + SOT `translation_tasks` tracking for resume after precompact | Orchestrator |
| R-14 | monitor_translation_output.py false positives (glossary check too strict) | Low (informational only) | Non-blocking hook (exit 0 always); top-5 term check with 2-term tolerance; full validation remains P1 script | Implementer |
| R-15 | infra_schema.py itself contains errors (wrong agent names, missing steps) | High (cascades to all generated files) | **Mitigated**: validate_infra.py runs V-1~V-10 meta-validation on schema; schema is compact (~100 lines) and human-reviewable | Implementer |
| R-16 | Codegen vs LLM boundary unclear → partial file edit conflicts | Medium (merge difficulties) | **Mitigated**: §17.5 Boundary Rule + `[CODEGEN:START/END]` markers in mixed files; LLM must not edit marker-delimited sections | Implementer |
| R-17 | infra_schema.py SOT diverges from workflow-coding.md design reference | Medium (authoritative source confusion) | **Mitigated**: §17.6 establishes infra_schema.py as authoritative for structured data; workflow-coding.md tables are design reference only | Implementer |
| R-18 | Over-engineering: codegen layer adds complexity without proportional benefit | Low | **Mitigated**: codegen scope strictly limited to 7 confirmed generation targets (§17.3 G-1~G-7); creative content stays LLM-authored (§17.5) | Implementer |
| R-19 | KRT architecture change: Final constants → YAML/JSON config migration | Medium (deployed skills fail silently) | **Mitigated**: tune-designer spec requires Final type verification before modification (adversarial C-2). Deployed skill pre-modifies: grep variable name → verify `Final[` annotation → if absent, halt + report "구조 변경 감지" to user | Deployed skills |
| R-20 | Bash timeout for KRT prefetch (2500 stocks × ~2.3s = ~96min) | High (command killed mid-execution) | **Mitigated**: scan-designer spec requires 600000ms timeout for long commands (adversarial A-1). Note: 10min may still be insufficient for full 2500-stock prefetch — skill should check partial output + inform user of progress at each available opportunity | Deployed skills |
| R-21 | masterReference.log corruption via Write overwrite | Medium (historical analysis data loss) | **Mitigated**: code-convention rule + scan-designer spec: log files use Edit append-only (adversarial A-2). scan-builder embeds this as absolute rule in SKILL.md | Deployed skills |

---

## 17. Hallucination Prevention — Python Codegen Layer

### 17.1 Design Rationale

The Infrastructure Build requires 39 files containing cross-referenced structured data: agent names, step numbers, file paths, status enums, and output keys appear in state.yaml, agent definitions, step-dispatch.md, test files, commands, and hooks. When an LLM generates these files sequentially, referential integrity failures (typos, missing entries, enum drift) are the dominant hallucination mode.

**Core principle**: Structured data that must be 100% accurate across multiple files is defined once in Python (`infra_schema.py`) and mechanically propagated. Creative content (agent Purpose, Failure Behavior, command instructions) remains LLM-authored.

**Philosophical alignment**:
- **절대 기준 1 (Quality)**: Deterministic generation eliminates the most frequent quality defect class (cross-reference inconsistency)
- **절대 기준 2 (SOT)**: Extends SOT principle from runtime (state.yaml) to build-time (infra_schema.py)
- **P1 (Data refinement)**: "AI 전달 전 Python 등으로 노이즈 제거" — codegen is P1 applied to infrastructure build itself

**Origin**: Confirmed via 57-item full audit (3-axis evaluation: rigor × repeatability × hallucination risk). 18 items scored HIGH on all 3 axes → consolidated into 7 generation targets (G-1~G-7).

### 17.2 Build-Time SOT: `infra_schema.py`

**Location**: `prompt/.claude/codegen/infra_schema.py`

**Data structures** (authoritative single source for all structured data):

```python
# === Status Enums (single definition — imported by validate_state_yaml.py) ===
WORKFLOW_STATUS_ENUM = {"not_started", "in_progress", "completed", "completed_degraded", "failed"}
TRANSLATION_STATUS_ENUM = {"pending", "in_progress", "completed", "retry", "timeout", "degraded"}

# === Path Constants ===
KRT_ROOT = "/Users/tajun/spJavis/kiwoom-rest-trader"
AW_ROOT  = "/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector"

# === Agent Roster (13 agents — authoritative for §2.2 table) ===
# Design fix C-1: All agents that produce output files have Write tool.
# Design fix C-2: infra-validator has Write+Edit (creates/fixes files in Step 10).
AGENT_ROSTER = [
    {"name": "param-extractor",     "model": "opus",   "tools": ["Read","Write","Grep","Glob"],                       "maxTurns": 30, "phase": "Research",       "step": 1,  "output_key": "step-1-param-inventory",      "translate": True},
    {"name": "pipeline-analyzer",   "model": "opus",   "tools": ["Read","Write","Grep","Glob","Bash"],                "maxTurns": 40, "phase": "Research",       "step": 1,  "output_key": "step-1-pipeline-analysis",    "translate": True},
    {"name": "error-analyzer",      "model": "sonnet", "tools": ["Read","Write","Grep","Glob"],                       "maxTurns": 20, "phase": "Research",       "step": 1,  "output_key": "step-1-error-patterns",       "translate": True},
    {"name": "research-integrator", "model": "opus",   "tools": ["Read","Write","Grep","Glob","Bash"],                "maxTurns": 25, "phase": "Research",       "step": 2,  "output_key": "step-2-research-report",      "translate": True},
    {"name": "architect",           "model": "opus",   "tools": ["Read","Write","Grep","Glob","Bash"],                "maxTurns": 25, "phase": "Planning",       "step": 4,  "output_key": "step-4-architecture",         "translate": True},
    {"name": "claude-md-designer",  "model": "opus",   "tools": ["Read","Write","Grep","Glob"],                       "maxTurns": 30, "phase": "Planning",       "step": 5,  "output_key": "step-5-claude-md-blueprint",  "translate": True},
    {"name": "scan-designer",       "model": "opus",   "tools": ["Read","Write","Grep","Glob"],                       "maxTurns": 35, "phase": "Planning",       "step": 6,  "output_key": "step-6-stock-scan-blueprint", "translate": True},
    {"name": "tune-designer",       "model": "opus",   "tools": ["Read","Write","Grep","Glob"],                       "maxTurns": 40, "phase": "Planning",       "step": 6,  "output_key": "step-6-filter-tune-blueprint","translate": True},
    {"name": "claude-md-builder",   "model": "opus",   "tools": ["Read","Write","Edit","Bash","Glob","Grep"], "maxTurns": 25, "phase": "Implementation", "step": 8,  "output_key": "step-8-claude-md",            "translate": False},
    {"name": "scan-builder",        "model": "opus",   "tools": ["Read","Write","Edit","Bash","Glob","Grep"], "maxTurns": 40, "phase": "Implementation", "step": 9,  "output_key": "step-9-stock-scan-skill",     "translate": False},
    {"name": "tune-builder",        "model": "opus",   "tools": ["Read","Write","Edit","Bash","Glob","Grep"], "maxTurns": 50, "phase": "Implementation", "step": 9,  "output_key": "step-9-filter-tune-skill",    "translate": False},
    {"name": "infra-validator",     "model": "opus",   "tools": ["Read","Write","Edit","Grep","Glob","Bash"], "maxTurns": 30, "phase": "Implementation", "step": 10, "output_key": "step-10-validation-report",   "translate": True},
    {"name": "smoke-tester",        "model": "opus",   "tools": ["Read","Grep","Glob","Bash"],                "maxTurns": 25, "phase": "Implementation", "step": 11, "output_key": "step-11-smoke-test",          "translate": True},
]

# === Step Dispatch (12 steps — authoritative for §3.3 table) ===
STEP_DISPATCH = [
    {"step": 1,  "type": "team",   "agents": ["param-extractor","pipeline-analyzer","error-analyzer"], "review": "fact-checker", "translate": True},
    {"step": 2,  "type": "single", "agents": ["research-integrator"],                                  "review": "fact-checker", "translate": True},
    {"step": 3,  "type": "human",  "agents": [],                                                       "review": None,           "translate": False},
    {"step": 4,  "type": "single", "agents": ["architect"],                                            "review": "reviewer",     "translate": True},
    {"step": 5,  "type": "single", "agents": ["claude-md-designer"],                                   "review": "reviewer",     "translate": True},
    {"step": 6,  "type": "team",   "agents": ["scan-designer","tune-designer"],                        "review": "reviewer",     "translate": True},
    {"step": 7,  "type": "human",  "agents": [],                                                       "review": None,           "translate": False},
    {"step": 8,  "type": "single", "agents": ["claude-md-builder"],                                    "review": "reviewer",     "translate": False},
    {"step": 9,  "type": "sequential", "agents": ["scan-builder","tune-builder"],                      "review": "reviewer",     "translate": False},
    {"step": 10, "type": "single", "agents": ["infra-validator"],                                      "review": "reviewer",     "translate": True},
    {"step": 11, "type": "single", "agents": ["smoke-tester"],                                         "review": None,           "translate": True},
    {"step": 12, "type": "human",  "agents": [],                                                       "review": None,           "translate": False},
]

# === Filter Modules (kiwoom-rest-trader — verified against actual code) ===
FILTER_MODULES = [
    "chart60_120Filter", "chart240Filter", "chartDayPreFilter",
    "chartDayFilter", "investorFilter", "financeFilter", "chart60Filter",
]
```

**Invariant**: Every structured data value that appears in 2+ generated files MUST exist in `infra_schema.py`. If a new cross-referenced value is needed, add it to the schema first, then regenerate.

### 17.3 Generation Targets (7 Confirmed Candidates)

| # | Target | Source in Schema | Generated Artifact | Replaces Manual Work |
|---|--------|------------------|--------------------|---------------------|
| G-1 | state.yaml output keys + translation_tasks | `AGENT_ROSTER[*].output_key` + `-ko` suffix for translate=True | `prompt/.claude/state.yaml` | Manual 22-key + 10-entry enumeration (§11.1) |
| G-2 | Agent definition frontmatter | `AGENT_ROSTER[*].{model,tools,maxTurns}` | `.claude/agents/*.md` YAML header | Manual 13 × 3-field transcription (§2.2) |
| G-3 | Step dispatch table | `STEP_DISPATCH` joined with `AGENT_ROSTER` | `references/step-dispatch.md` | Manual 12×7 table (§3.3) |
| G-4 | conftest.py constants | Path constants + `FILTER_MODULES` | `prompt/.claude/tests/conftest.py` `[CODEGEN]` section | Manual path/module listing (§8.2) |
| G-5 | Enum imports in validation hook | `WORKFLOW_STATUS_ENUM`, `TRANSLATION_STATUS_ENUM` | `validate_state_yaml.py` `[CODEGEN]` section | Duplicated enum sets (§6.1, R-10) |
| G-6 | File manifest validator | All file paths derived from schema | `validate_infra.py` manifest check | Manual 39-file list verification (§15) |
| G-7 | Command file path refs | `AGENT_ROSTER[*].output_key` | `.claude/commands/*.md` path strings in `[CODEGEN]` sections | Manual path transcription (§7) |

**Not generated** (LLM-authored — §17.5 governs): Agent body content (Purpose, Context, Output Specification, Verification Criteria, Failure Behavior), SKILL.md orchestration logic, fallback-paths.md strategy descriptions, evaluation criteria prose, command instruction flows, monitor_translation_output.py logic.

### 17.4 Cross-Validation Protocol: `validate_infra.py`

**Location**: `prompt/.claude/codegen/validate_infra.py`

**Execution**: Phase 0.9 — GATE. Must pass with zero errors before Phase 1.

**Validation rules**:

```python
def validate_all():
    errors = []
    
    # V-1: Every STEP_DISPATCH agent exists in AGENT_ROSTER
    roster_names = {a["name"] for a in AGENT_ROSTER}
    for step in STEP_DISPATCH:
        for agent in step["agents"]:
            if agent not in roster_names:
                errors.append(f"V-1: Step {step['step']} references unknown agent '{agent}'")
    
    # V-2: Every AGENT_ROSTER agent appears in at least one STEP_DISPATCH
    dispatched = {a for s in STEP_DISPATCH for a in s["agents"]}
    for name in roster_names:
        if name not in dispatched:
            errors.append(f"V-2: Agent '{name}' in roster but never dispatched")
    
    # V-3: Output keys are unique across entire roster
    keys = [a["output_key"] for a in AGENT_ROSTER]
    if len(keys) != len(set(keys)):
        dupes = [k for k in keys if keys.count(k) > 1]
        errors.append(f"V-3: Duplicate output_key: {dupes}")
    
    # V-4: Generated state.yaml output keys match AGENT_ROSTER
    # (Reads generated state.yaml, parses keys, compares against schema)
    
    # V-5: Agent definition files exist and frontmatter matches schema
    # (For each agent in AGENT_ROSTER: file exists, model/tools/maxTurns match)
    
    # V-6: step-dispatch.md table matches STEP_DISPATCH
    # (Parses generated Markdown table, compares row-by-row)
    
    # V-7: conftest.py [CODEGEN] constants match schema
    # (Reads conftest.py, extracts CODEGEN section, verifies paths + FILTER_MODULES)
    
    # V-8: validate_state_yaml.py imports enums from infra_schema
    # (Grep for import statement — no hardcoded enum sets)
    
    # V-9: File manifest completeness (all 39 expected files exist on disk)
    
    # V-10: Translation eligibility consistency
    for agent in AGENT_ROSTER:
        step_entry = next((s for s in STEP_DISPATCH if s["step"] == agent["step"]), None)
        if step_entry and agent["translate"] != step_entry["translate"]:
            errors.append(f"V-10: Agent '{agent['name']}' translate={agent['translate']} "
                          f"but Step {agent['step']} translate={step_entry['translate']}")
    
    return errors  # empty list = PASS
```

### 17.5 Boundary Rule: Codegen vs LLM

| Aspect | Codegen (Deterministic) | LLM (Creative) |
|--------|------------------------|-----------------|
| Agent frontmatter | model, tools, maxTurns | — |
| Agent body | — | Purpose, Context, Output Spec, Verification, Failure |
| state.yaml | All fields, keys, defaults, structure | — |
| step-dispatch.md | Complete table structure + cell values | — |
| conftest.py | Path constants, FILTER_MODULES | Test functions, fixtures beyond paths |
| validate_state_yaml.py | Enum imports from infra_schema | Fallback regex logic, error messages |
| Commands (*.md) | File path references | Instruction flows, presentation logic |
| Evaluation criteria | — | All content (prose) |
| SKILL.md | — | All content (orchestration logic) |
| fallback-paths.md | Status values in SOT Update column | Fallback strategy descriptions |

**Marker convention**: Generated sections in mixed files are delimited by:

```
# === [CODEGEN:START — from infra_schema.py] ===
# ... generated content — DO NOT EDIT ...
# === [CODEGEN:END] ===
```

LLM MUST NOT edit content between these markers. `generate_infra.py` overwrites marker-delimited sections only, preserving all content outside markers.

### 17.6 Build-Time vs Runtime SOT Relationship

```
Build-time SOT (infra_schema.py)
  │  Lifecycle: Phase 0-pre only. Not imported at runtime.
  │
  ├── generates → state.yaml template     (Runtime SOT — initial state)
  ├── generates → agent frontmatter        (consumed by Orchestrator at dispatch)
  ├── generates → step-dispatch.md         (consumed by Orchestrator at dispatch)
  ├── generates → conftest.py constants    (consumed by pytest)
  ├── generates → enum imports             (consumed by validate_state_yaml.py)
  └── validates → cross-reference integrity (V-1~V-10)

Runtime SOT (state.yaml)
  │  Lifecycle: Phase 1 (workflow execution). Written only by Orchestrator.
  │
  ├── written by  → Orchestrator (sole writer — 절대 기준 2)
  ├── validated by → validate_state_yaml.py (imports enums from infra_schema.py)
  ├── read by     → All agents, commands, tests
  └── persists    → workflow execution state (current_step, outputs, translation_tasks)
```

**Lifecycle separation**: `infra_schema.py` is consumed during Phase 0 (infrastructure build) AND at runtime by `validate_state_yaml.py` hook. This is the sole runtime dependency — the hook imports `WORKFLOW_STATUS_ENUM` and `TRANSLATION_STATUS_ENUM` from `infra_schema.py` via `CLAUDE_PROJECT_DIR`-based path resolution (§6.1 Design Fix C-3/H-3). Justification: R-10 mitigation (single enum source prevents schema drift between hook and codegen). Note: the hook does NOT import from `_context_lib.validate_sot_schema()` — that function validates a DIFFERENT schema (Context Preservation system's autopilot state).

**SOT hierarchy**: `infra_schema.py` (build-time, structured data) → generates → `state.yaml` (runtime, execution state). No circular dependency. `workflow-coding.md` tables (§2.2, §3.3, §11.1) are the human-readable design reference; `infra_schema.py` is the machine-readable authoritative source.

**RLM pattern preserved**: Codegen does not touch runtime RLM artifacts (`glossary.yaml`, `context-snapshots/`, `screener_state.json`). These remain agent-managed during Phase 1 execution. Build-time and runtime memory systems are fully orthogonal.
