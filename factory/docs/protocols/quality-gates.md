# Quality Gates & P1 Validation

> Detailed specification for the 4-layer quality assurance architecture and P1 hallucination prevention.
> Separated from CLAUDE.md — referenced for quality gate design, debugging, and extension.

## 4-Layer Quality Assurance Architecture (L0 → L1 → L1.5 → L2)

Orchestrator increments `current_step` sequentially only. Each step must pass up to 4 verification layers before advancing:

1. **L0 Anti-Skip Guard** (deterministic) — Output file existence + minimum size (100 bytes). Performed by `validate_step_output()` in the Hook layer.
2. **L1 Verification Gate** (semantic) — Agent self-verifies that output meets `Verification` criteria 100%. On failure, re-execute only the failed portion (max 10 attempts). Logged in `verification-logs/step-N-verify.md`.
3. **L1.5 pACS Self-Rating** (confidence) — Pre-mortem Protocol execution followed by F/C/L 3-dimension scoring. Logged in `pacs-logs/step-N-pacs.md`. RED (< 50) triggers rework.
4. **[L2 Calibration]** (optional) — Separate `@verifier` agent cross-validates pACS scores. High-risk steps only.

> Steps without a `Verification` field proceed with Anti-Skip Guard only (backward compatible). Details: `AGENTS.md §5.3`, `§5.4`

---

## P1 Hallucination Prevention

Tasks requiring 100% accuracy repeatedly are enforced via Python code.

### (1) KI Schema Validation
`_validate_session_facts()` guarantees presence of 11 mandatory RLM keys (session_id, tags, final_status, diagnosis_patterns, etc.) before knowledge-index writes — fills safe defaults on missing.

### (2) Partial Failure Isolation
In `archive_and_index_session()`, archive file write failures do not block knowledge-index updates — protects RLM core assets.

### (3) SOT Write Pattern Validation
`setup_init.py`'s `_check_sot_write_safety()` detects SOT filename + write pattern co-occurrence in Hook scripts using AST function boundary analysis (Tier 1: blocks non-SOT scripts referencing SOT, Tier 2: per-function write pattern inspection for SOT-aware scripts).

### (4) SOT Schema Validation
`validate_sot_schema()` verifies workflow state.yaml structural integrity across 8 items:
- **S1-S6**: current_step type/range, outputs type/key format, future step output detection, workflow_status valid values, auto_approved_steps consistency
- **S7**: pacs 5-field validation (S7a dimensions F/C/L 0-100, S7b current_step_score 0-100, S7c weak_dimension F/C/L, S7d history dict→{score, weak}, S7e pre_mortem_flag string)
- **S8**: active_team 5-field validation (S8a name string, S8b status partial|all_completed, S8c tasks_completed list, S8d tasks_pending list, S8e completed_summaries dict→dict)

Runs at both SessionStart and Stop hooks.

### (5) Adversarial Review P1 Validation
`validate_review_output()` verifies review report structural integrity:
- R1: File exists
- R2: Minimum size
- R3: 4 required sections present
- R4: Explicit PASS/FAIL extraction
- R5: Issue table ≥ 1 row

`parse_review_verdict()` — regex-extracts issue severity counts.
`calculate_pacs_delta()` — Generator-Reviewer pACS difference (Delta ≥ 15 → recalibration).
`validate_review_sequence()` — Enforces Review PASS → Translation order via file timestamps.
Standalone script: `validate_review.py`.

### (6) Translation P1 Validation
`validate_translation_output()` verifies translation outputs across 7 items:
- T1: File exists, T2: Minimum size, T3: English source exists, T4: .ko.md extension, T5: Non-whitespace, T6: Heading count ±20%, T7: Code block count matches

`check_glossary_freshness()` — glossary timestamp freshness (T8).
`verify_pacs_arithmetic()` — All pACS log min() arithmetic accuracy (T9 — universal).
`validate_verification_log()` — Verification log V1a-V1c.
`validate_translation.py` mandates Review verdict=PASS check.
Standalone script: `validate_translation.py`.

### (7) pACS P1 Validation
`validate_pacs_output()` verifies pACS logs across 6 items:
- PA1: File exists, PA2: Minimum size 50 bytes, PA3: Dimension scores ≥ 3 (0-100 range), PA4: Pre-mortem section exists, PA5: min() arithmetic accuracy, PA7: RED block (pACS < 50 → FAIL)
- PA6 (optional): Score-color zone consistency

Standalone script: `validate_pacs.py`.

### (8) L0 Anti-Skip Guard Implementation
`validate_step_output()` — L0 validation 3 items:
- L0a: File exists at SOT outputs.step-N path
- L0b: File size ≥ MIN_OUTPUT_SIZE (100 bytes)
- L0c: Non-whitespace confirmed

Combined validation via `validate_pacs.py --check-l0`.

### (9) Predictive Debugging P1 Validation
`validate_risk_scores()` — risk-scores.json 6 items:
- RS1: Required keys, RS2: data_sessions integer, RS3: risk_score range, RS4: error_count arithmetic consistency, RS5: resolution_rate range, RS6: top_risk_files sorted + exist

### (10) Retry Budget P1 Validation
`validate_retry_budget.py` — Deterministic retry budget judgment:
- RB1: Counter file read, RB2: ULW active detection, RB3: Budget comparison (`retries_used < max_retries`)
- `max_retries`: 3 when ULW active, 2 when inactive
- `--increment` mode for atomic counter write increment

### (11) Abductive Diagnosis P1 Validation
`validate_diagnosis_log()` — Diagnosis log 10 items:
- AD1: File exists, AD2: Minimum size 100 bytes, AD3: Gate field match, AD4: Selected hypothesis exists, AD5: Evidence ≥ 1, AD6: Action Plan exists, AD7: No forward references, AD8: Hypotheses ≥ 2, AD9: Selected hypothesis consistency, AD10: Prior diagnosis reference (retry > 0)

`diagnose_failure_context()` — Pre-evidence collection (retry_history, upstream_evidence, hypothesis_priority, fast_path, raw_evidence). Fast-Path (FP1-FP3) for deterministic shortcuts.
Standalone scripts: `diagnose_context.py` (pre-analysis), `validate_diagnosis.py` (post-validation).

### (12) Cross-Step Traceability P1 Validation
`validate_cross_step_traceability()` — 5 items:
- CT1: Trace marker exists, CT2: Referenced step output exists, CT3: Section ID resolution (Warning), CT4: Minimum density ≥ 3, CT5: No forward references

Standalone script: `validate_traceability.py`.

### (13) Domain Knowledge Structure P1 Validation
`validate_domain_knowledge()` — domain-knowledge.yaml 7 items:
- DK1: File exists + YAML valid, DK2: metadata required keys, DK3: entities structure, DK4: relations referential integrity, DK5: constraints structure, DK6: output DKS reference resolution, DK7: constraint non-violation

Standalone script: `validate_domain_knowledge.py`. Optional — not all workflows require it.

### (14) Workflow.md DNA Inheritance P1 Validation
`validate_workflow_md()` — 8 items:
- W1: File exists, W2: Minimum size 500 bytes, W3: `## Inherited DNA` header, W4: Inherited Patterns table ≥ 3 rows, W5: Constitutional Principles section, W6: CAP reference, W7: CT Verification-Validator consistency, W8: DKS Verification-Validator consistency

Standalone script: `validate_workflow.py`. Manual invocation after workflow-generator completion.
