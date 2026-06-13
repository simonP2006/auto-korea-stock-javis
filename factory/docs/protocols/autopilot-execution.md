# Autopilot Execution Protocol

> Detailed checklist for executing workflows in Autopilot mode.
> Separated from CLAUDE.md — referenced only during workflow execution.

## Activation Patterns

| User Command | Behavior |
|-------------|----------|
| "autopilot mode", "run workflow automatically", "fully automated execution" | Set SOT `autopilot.enabled: true` then start workflow |
| "disable autopilot", "switch to manual mode" | Set SOT `autopilot.enabled: false` — applies from next `(human)` step |

## Checkpoint Behavior

| Checkpoint | Autopilot Behavior |
|-----------|-------------------|
| `(human)` + Slash Command | Generate complete output → auto-approve with quality-maximizing defaults → log decision |
| AskUserQuestion | Auto-select quality-maximizing option from choices → log decision |
| `(hook)` exit code 2 | **No change** — block as-is, relay feedback, rework |

## Decision Log

Auto-approved decisions are logged in `autopilot-logs/step-N-decision.md`: step, option, selection rationale (based on Absolute Criterion 1).
Decision Log standard template: `references/autopilot-decision-template.md`

## Runtime Enforcement Mechanisms

| Layer | Mechanism | Enforcement |
|-------|-----------|-------------|
| **Hook** (deterministic) | `restore_context.py` — SessionStart | When Autopilot active, inject 6 execution rules + previous step output verification results into context |
| **Hook** (deterministic) | `generate_snapshot_md()` — snapshot | Preserve Autopilot state + Agent Team state sections at IMMORTAL priority |
| **Hook** (deterministic) | `generate_context_summary.py` — Stop | Detect auto-approval patterns → generate missing Decision Log entries (safety net) |
| **Hook** (deterministic) | `update_work_log.py` — PostToolUse | Track step progression via `autopilot_step` field |
| **Prompt** (behavioral) | Execution Checklist (below) | Specify mandatory actions at start/during/after each step |

> Hook layer accesses SOT read-only (Absolute Criterion 2 compliance); writes only to `context-snapshots/` and `autopilot-logs/`.

---

## Execution Checklist (MANDATORY)

When executing a workflow in Autopilot mode, **must** perform this checklist for every step.

### Before Each Step
- [ ] Confirm SOT `current_step`
- [ ] Confirm previous step output file exists + is non-empty
- [ ] Confirm previous step output path is recorded in SOT `outputs`
- [ ] Read the step's `Verification` criteria — recognize the definition of "100% complete" first (AGENTS.md §5.3)

### During Step Execution
- [ ] Execute **all** tasks of the step **completely** (no abbreviation — Absolute Criterion 1)
- [ ] Generate output at **full quality**

### After Step Completion (Verification Gate — steps with `Verification` field only)
- [ ] Save output file to disk
- [ ] Self-verify output against each `Verification` criterion
- [ ] If any criterion fails:
  - [ ] Check + consume P1 retry budget: `python3 .claude/hooks/scripts/validate_retry_budget.py --step N --gate verification --project-dir . --check-and-increment`
  - [ ] `can_retry: true` → **Perform Abductive Diagnosis** (see diagnosis subsection below) → diagnosis-based re-execution
  - [ ] `can_retry: false` → user escalation (retry budget exhausted, counter not incremented)
- [ ] Confirm all criteria PASS
- [ ] Generate `verification-logs/step-N-verify.md`
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_verification.py --step N --project-dir .`
- [ ] Confirm P1 result `valid: true` (V1a-V1c all pass)

### After Step Completion (Cross-Step Traceability — steps with "cross-step traceability" in Verification only)
- [ ] Confirm output contains ≥ 3 `[trace:step-N:section-id]` markers
- [ ] All markers reference prior steps only (no forward references)
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_traceability.py --step N --project-dir .`
- [ ] Confirm P1 result `valid: true` (CT1-CT5 all pass)
- [ ] If CT3 WARNING (unresolved section ID), re-verify marker accuracy

### After Step Completion (Domain Knowledge Structure — DKS-pattern workflows only, optional)
- [ ] `domain-knowledge.yaml` build step: Run P1 validation: `python3 .claude/hooks/scripts/validate_domain_knowledge.py --project-dir .`
- [ ] Confirm P1 result `valid: true` (DK1-DK5 all pass)
- [ ] DKS reference step (output contains `[dks:xxx]` markers): Run P1 cross-validation: `python3 .claude/hooks/scripts/validate_domain_knowledge.py --project-dir . --check-output --step N`
- [ ] Confirm P1 cross-validation result `valid: true` (DK6-DK7 inclusive all pass)

### After Step Completion (pACS — performed after Verification Gate passes)
- [ ] Answer Pre-mortem Protocol 3 questions (AGENTS.md §5.4)
- [ ] Score F, C, L 3 dimensions → compute pACS = min(F, C, L)
- [ ] Generate `pacs-logs/step-N-pacs.md`
- [ ] Update SOT `pacs` field (current_step_score, dimensions, weak_dimension, history)
- [ ] If pACS RED (< 50):
  - [ ] Check + consume P1 retry budget: `python3 .claude/hooks/scripts/validate_retry_budget.py --step N --gate pacs --project-dir . --check-and-increment`
  - [ ] `can_retry: true` → **Perform Abductive Diagnosis** (see diagnosis subsection below) → diagnosis-based rework + re-score
  - [ ] `can_retry: false` → user escalation (retry budget exhausted, counter not incremented)
- [ ] If pACS YELLOW (50-69): Record weak dimension in Decision Log, proceed
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_pacs.py --step N --check-l0 --project-dir .`
- [ ] Confirm P1 result `valid: true` (PA1-PA7 + L0 all pass)
- [ ] Record output path in SOT `outputs`
- [ ] Increment SOT `current_step` +1
- [ ] `(human)` step: Generate `autopilot-logs/step-N-decision.md`
- [ ] `(human)` step: Add to SOT `auto_approved_steps`

### `(team)` Step Additional Checklist
- [ ] Immediately after `TeamCreate` → record in SOT `active_team` (name, status, tasks_pending)
- [ ] Each Teammate self-verifies against their Task's verification criteria before reporting (L1 — AGENTS.md §5.3)
- [ ] Each Teammate performs pACS self-scoring after L1 pass (L1.5 — session-internal, include score in report message)
- [ ] On each Teammate completion → Team Lead performs aggregate verification against step criteria (L2) + computes step pACS
- [ ] On L2 FAIL or Teammate pACS RED → SendMessage with specific feedback + re-execution instruction
- [ ] On each Teammate completion → update SOT `active_team.tasks_completed` + `completed_summaries`
- [ ] When all Tasks complete → record SOT `outputs`, increment `current_step` +1, set `active_team.status` → `all_completed`
- [ ] Immediately after `TeamDelete` → move SOT `active_team` → `completed_teams`
- [ ] Confirm Teammate outputs include Decision Rationale + Cross-Reference Cues

### After Step Completion (Adversarial Review — `Review: @reviewer|@fact-checker` steps only)
- [ ] Invoke agent specified in `Review:` field as Sub-agent (recommended: `isolation: "worktree"` — protects Orchestrator context, details: `reviewer.md § Context Isolation`)
- [ ] Save review report to `review-logs/step-N-review.md`
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_review.py --step N --project-dir . --check-pacs-arithmetic`
- [ ] Confirm P1 result `valid: true` (R1-R5 all pass)
- [ ] Check verdict:
  - [ ] PASS → proceed to next step (including Translation)
  - [ ] FAIL → Check + consume P1 retry budget: `python3 .claude/hooks/scripts/validate_retry_budget.py --step N --gate review --project-dir . --check-and-increment`
  - [ ] `can_retry: true` → **Perform Abductive Diagnosis** (see diagnosis subsection below) → diagnosis-based rework
  - [ ] `can_retry: false` → user escalation (retry budget exhausted, counter not incremented)
- [ ] If pACS Delta ≥ 15 → record in Decision Log + document recalibration rationale
- [ ] Translation execution prohibited while Review FAIL

### Quality Gate FAIL Diagnosis (Abductive Diagnosis — performed when retry is possible)
- [ ] Step A — P1 pre-evidence collection: `python3 .claude/hooks/scripts/diagnose_context.py --step N --gate {verification|pacs|review} --project-dir .`
- [ ] Check Fast-Path: `fast_path.eligible == true` → FP1/FP2 immediate re-execution, FP3 user escalation
- [ ] If Fast-Path not applicable → Step B — LLM diagnosis: root cause analysis based on evidence bundle + hypothesis priorities
- [ ] Generate diagnosis log: `diagnosis-logs/step-N-{gate}-{timestamp}.md`
- [ ] Step C — P1 post-validation: `python3 .claude/hooks/scripts/validate_diagnosis.py --step N --gate {verification|pacs|review} --project-dir .`
- [ ] Confirm P1 result `valid: true` (AD1-AD10 all pass)
- [ ] Execute rework based on selected hypothesis (H1/H2/H3/H4) from diagnosis

### After Step Completion (Translation — `Translation: @translator` steps only)
- [ ] Invoke `@translator` sub-agent (include `translations/glossary.yaml` reference)
- [ ] Confirm translation file (`*.ko.md`) exists on disk
- [ ] Confirm translation file is non-empty
- [ ] Record translation path in SOT `outputs.step-N-ko`
- [ ] Confirm `translations/glossary.yaml` updated
- [ ] Translation pACS scoring complete (Ft/Ct/Nt — `@translator` Step 4, AGENTS.md ��5.4)
- [ ] Translation pACS log generated (`pacs-logs/step-N-translation-pacs.md`)
- [ ] Run P1 validation: `python3 .claude/hooks/scripts/validate_translation.py --step N --project-dir . --check-pacs --check-sequence`
- [ ] Confirm P1 result `valid: true` (T1-T9 + sequence all pass)

---

## NEVER DO

- Increment `current_step` by 2+ at once — prohibited
- Advance to next step without output — prohibited
- "It's automatic so keep it brief" — prohibited — Absolute Criterion 1 violation
- Ignore `(hook)` exit code 2 blocks — prohibited
- Teammates directly modifying SOT in `(team)` steps — prohibited — Team Lead only updates SOT
- Initializing `active_team` to empty object on session restore — prohibited — preserve existing `completed_summaries` (conservative resume protocol)
- Advancing to next step with Verification criteria FAIL — prohibited — max 10 retries (15 when ULW active) then user escalation
- Falsely recording all Verification criteria as "PASS" — prohibited — specific Evidence required for each criterion
- Assigning pACS score without Pre-mortem Protocol — prohibited — weakness recognition is prerequisite to scoring
- Performing pACS without Verification Gate — prohibited — L1 pass is prerequisite to L1.5
- Assigning all pACS scores 90+ — prohibited — consistency between Pre-mortem identified weaknesses and scores required
- Executing Translation while Review FAIL — prohibited — Review PASS is prerequisite to Translation
- Processing Review with 0 issues as PASS — prohibited — P1 validation auto-rejects (R5 check)
- Scoring Reviewer pACS after referencing Generator pACS — prohibited — independent scoring mandatory
- Retrying quality gate FAIL without diagnosis using same approach — prohibited — Abductive Diagnosis or Fast-Path mandatory
- Recording only 1 hypothesis in diagnosis log — prohibited — minimum 2 hypothesis comparison (AD8)
- Selecting same hypothesis 3 consecutive times in diagnosis — prohibited — FP3 escalation (I-3 linkage)
