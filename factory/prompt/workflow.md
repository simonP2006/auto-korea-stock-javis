# KOSPI/KOSDAQ Stock Technical Analysis Filter Orchestration System — Build Workflow

Build a Claude Code orchestration layer (CLAUDE.md + 2 Skills) for the existing kiwoom-rest-trader stock screener, enabling a non-technical Korean-speaking user to (1) run stock screening via natural language commands and (2) fine-tune filter parameters through guided conversational interaction.

## Overview

- **Input**: PRD (`prompt/prd.md` v0.3.0-draft), Workflow Ideas (`prompt/workflow-idea/workflow-idea.md` v0.5.0), kiwoom-rest-trader source code (`/Users/tajun/spJavis/kiwoom-rest-trader/`)
- **Output**: Deployed `CLAUDE.md` + `stock-scan` skill + `filter-tune` skill in kiwoom-rest-trader
- **Frequency**: One-time build (with iterative refinement)
- **Autopilot**: enabled
- **pACS**: enabled

### Core Purpose Anchor

> **Primary Goal 1 (PG-1)**: Enable the user to command the stock screener to collect data for a specific date (YYYYMMDD) and run 5-Stage filters via Korean natural language.
> **Primary Goal 2 (PG-2)**: Help the user fine-tune filter parameters through intuitive Korean-language interaction — **this is the paramount objective**.
>
> Every step in this workflow MUST serve at least one of these goals. The connection is explicitly stated per step.

### Target Deployment

| Item | Target Path |
|------|-------------|
| CLAUDE.md | `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md` |
| stock-scan skill | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/` |
| filter-tune skill | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/` |
| screener_state.json | `/Users/tajun/spJavis/kiwoom-rest-trader/reports/screener_state.json` |
| tuning-log.md | `/Users/tajun/spJavis/kiwoom-rest-trader/reports/tuning-log.md` |
| Working outputs | `/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector/prompt/outputs/` |
| SOT | `/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector/prompt/.claude/state.yaml` |

### Key Design Decisions (Pre-Resolved)

| ID | Decision | Rationale | Source |
|----|----------|-----------|--------|
| D-1 | Deploy to kiwoom-rest-trader (Option A from C-8) | User opens Claude Code there; shortest path constants; `.claude/` already exists (only `settings.local.json` — no conflict) | C-8 |
| D-2 | SCAN_TODAY defaults to `run_full_research_flow` | PRD FR-1.1 compliance; user says "나눠서 해줘" to trigger separated mode (C-10 resolution). **Timeout note**: `run_full_research_flow` and `run_prefetch` take 10-15+ min — MUST use `Bash(run_in_background: true)` to avoid Claude Code's 10-min Bash timeout (600,000ms max). See SCAN_TODAY chain in Step 6 for details. | C-10, FR-1.1 |
| D-3 | 2-Skill architecture: `stock-scan` + `filter-tune` | Different interaction patterns (fire-and-forget vs iterative dialog); context efficiency | B-1 |
| D-4 | Parameter catalog = documentation only; SOT = Python `Final` constants | Always `Read` actual code before any parameter operation; avoids sync issues | C-1 |
| D-5 | Session continuity via `screener_state.json` (CLAUDE.md rule, no Hook dependency) | kiwoom-rest-trader lacks AgenticWorkflow Hook infrastructure | B-12, C-8 |
| D-6 | English for agent execution; Korean for all user-facing output | AI performance maximization (절대 기준 1) | AGENTS.md §5.2 |
| D-7 | Execution template: `.venv/bin/python` (not `source activate`) | Shell-state independent; avoids activate-related issues | B-6 |

### Constants

```
KRT_ROOT    = /Users/tajun/spJavis/kiwoom-rest-trader
KRT_PYTHON  = ${KRT_ROOT}/.venv/bin/python
KRT_REPORTS = ${KRT_ROOT}/reports
KRT_FILTERS = ${KRT_ROOT}/src/kiwoom/itemFilter
KRT_SCRIPTS = ${KRT_ROOT}/scripts
EXEC_PATTERN = cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}
```

---

## Inherited DNA (Parent Genome)

> This workflow inherits the complete genome of AgenticWorkflow.
> It builds a stock screening orchestration system; the genome is identical. See `soul.md §0`.

**Constitutional Principles** (adapted to this workflow's domain):

1. **Quality Absolutism** — The final CLAUDE.md and skill files must enable a non-technical user to operate the screener and tune filters entirely through Korean natural language. Every chain, checkpoint, and error message must be production-ready. Speed and token cost are irrelevant.
2. **Single-File SOT** — `prompt/.claude/state.yaml` tracks workflow build state. Only the orchestrator writes. Research findings and blueprints are stored as step output files, not in SOT.
3. **Code Change Protocol** — Implementation steps that write files to kiwoom-rest-trader follow intent→impact→design protocol. Critical: must not break existing kiwoom-rest-trader functionality or overwrite existing `.claude/settings.local.json`.

**Inherited Patterns**:

| DNA Component | Inherited Form |
|--------------|---------------|
| 3-Phase Structure | Research → Planning → Implementation |
| SOT Pattern | `prompt/.claude/state.yaml` — single writer (Orchestrator/Team Lead) |
| 4-Layer QA | L0 Anti-Skip → L1 Verification → L1.5 pACS → L2 Adversarial Review |
| P1 Hallucination Prevention | Research phase extracts structured data from Python code via grep/Read before analysis |
| P2 Expert Delegation | Specialized agents: code analysis (3), skill design (2), skill build (2) |
| Safety | TS-1~5 safety rules inherited into filter-tune skill output |
| Adversarial Review | `@reviewer` for implementation, `@fact-checker` for research |
| Context Preservation | Snapshot + RLM for long-running workflow |

**Domain-Specific Gene Expression**:
- **P1 (Data Refinement)** strongly expressed: Research phase uses `grep -n 'Final'` to extract structured parameter data from raw Python before analysis. This prevents hallucinated parameter values.
- **P2 (Expert Delegation)** strongly expressed: 3 research specialists (param extraction, pipeline mapping, error classification), 2 skill designers, 2 skill builders — each with deep focus on their domain.
- **CCP** moderately expressed: Implementation modifies only prompt files (CLAUDE.md, SKILL.md), not Python logic. Risk is lower, but cross-reference accuracy between CLAUDE.md ↔ skill files ↔ actual code is critical.

---

## Research

### 1. (team) Kiwoom-rest-trader Deep Code Analysis

> **PG Connection**: PG-1 + PG-2 — Without accurate code-level understanding of filter parameters (PG-2), execution commands (PG-1), and error patterns (PG-1), the orchestration layer will produce wrong results.

- **Team**: `code-analysis-team`
- **Checkpoint Pattern**: standard
- **Pre-processing**: `grep -rn 'Final\[' /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/*.py` — pre-extract all Final constant declarations for Teammate A context injection
- **Tasks**:
  - `@param-extractor` (opus): **Parameter Full Inventory**
    Read every `.py` file in `${KRT_FILTERS}/`. For each `Final` constant, extract: (1) variable name, (2) type (`int`/`float`), (3) current value, (4) meaning (from comments/context), (5) file:line location. Map shared constants — identify `_ALIGN_TOL_LOOSE` usages across all filter conditions (note: shared within `chart60_120Filter.py` across Types B/C/D/E, not cross-file). **Attention**: `chart60Filter.py` has its own independent constant `_MA_ALIGNMENT_TOLERANCE` (0.005) which is distinct from `chart60_120Filter.py`'s `_ALIGN_TOL_LOOSE` (0.015) — document both clearly to prevent tuning confusion. Cross-reference against PRD §5.1 catalog; flag any discrepancies between PRD snapshot and actual code. Format as structured Markdown table grouped by Stage.
    Output: `prompt/outputs/step-1-param-inventory.md`

  - `@pipeline-analyzer` (opus): **Pipeline Dependency Graph & Output Schema**
    Three sub-tasks:
    (a) **Execution pipeline trace**: Read `${KRT_SCRIPTS}/run_full_research_flow.py`, `run_prefetch.py`, `run_filters.py`. Map the call chain: which functions call which filter modules, in what order. Determine if each filter can run independently. Document module entry points (`__main__` blocks).
    (b) **Output format verification**: Search `${KRT_REPORTS}/` for any existing `stage*_passed.md` files. If found, document exact format (line-by-line structure, headers, separators). If none exist, analyze the Python code that generates these files (`write` or `open` calls in filter modules) to determine output format. Also document `researchedCompany.md` format. Specifically check: does `stage1_chart60_120_passed.md` include Type pattern info (A/B/C/D/E)? **Additionally**: investigate variant output files observed in existing reports — `researchedCompany.p1.md`, `researchedCompany.p2.md`, `masterConditionCompany.md`. Determine: (i) what generates them, (ii) their relationship to `researchedCompany.md`, (iii) which file the SHOW_RESULTS chain should read as the canonical result.
    (c) **masterReference.log format**: Analyze `${KRT_FILTERS}/Filter_condition_update.py` in depth. Determine the exact log output format — especially whether it includes numeric gap values between actual values and threshold values (critical for FR-5.2 impact estimation, B-10). Document field names, separators, and example output lines.
    Output: `prompt/outputs/step-1-pipeline-analysis.md`

  - `@error-analyzer` (sonnet): **Error Pattern Classification**
    Grep for exception handling patterns (`except`, `raise`, `sys.exit`, `exit(`) across `${KRT_SCRIPTS}/` and `src/kiwoom/`. Additionally, grep for `class.*Error\|class.*Exception` to discover ALL custom exception class definitions. For each error type found, record: (1) exception class name, (2) trigger condition, (3) exit code, (4) stderr message pattern, (5) source file:line. Known types to map: `KiwoomAuthError`, `KiwoomApiError` (appears in 6+ modules), `KiwoomConditionError`, `ResearchError`, `OrganizeError`, `PrefetchError`, `httpx.ConnectError`, `httpx.TimeoutException`, `FileNotFoundError`. **Include ALL additional error types discovered beyond this list.** Produce a Korean message mapping table for each error type (B-4).
    Output: `prompt/outputs/step-1-error-patterns.md`

- **Join**: All 3 teammates complete → Orchestrator proceeds to Step 2
- **SOT Write**: Team Lead records completion status and output paths in `state.yaml`
- **Review**: `@fact-checker` — verify extracted parameter values match actual code; verify pipeline trace matches `user_command_manual.md`
- **Translation**: none
- **Failure Recovery**: If any teammate fails after 3 retries, the orchestrator reads the target files directly and produces a minimal report for that area. The remaining teammates' outputs are still used.

---

### 2. Research Integration & Coverage Validation

> **PG Connection**: PG-1 + PG-2 — Ensures no critical unknowns remain. Missing information at this stage cascades into flawed design, which means broken execution (PG-1) or incorrect tuning guidance (PG-2).

- **Agent**: `@research-integrator` (opus)
- **Verification**:
  - [ ] All 3 items from PRD C.2 (추가 조사 필요 항목: masterReference.log format, error patterns, stage*_passed.md format) are resolved with concrete findings
  - [ ] All 4 items from workflow-idea C-6 (Research 필수 조사 목록) are answered:
    - C-6-1: masterReference.log gap 수치 포함 여부 → answered
    - C-6-2: stage*_passed.md format + Type pattern info → answered
    - C-6-3: actual error patterns → answered
    - C-6-4: all Final constants extracted → answered
  - [ ] Parameter inventory covers all 7 filter modules (chart60_120, chart240, chartDayPre, chartDay, investor, finance, chart60). **Note**: `stageMasterFilter.py` (+ `stageMasterFilter_state.json`) is explicitly excluded — Phase 2 scope per PRD §12. `chart60Filter.py` is a sub-component of `chart60_120Filter` but has its own independent constant `_MA_ALIGNMENT_TOLERANCE` (0.005) distinct from `_ALIGN_TOL_LOOSE` (0.015).
  - [ ] Pipeline dependency graph is complete: every filter → input file(s) → output file(s)
  - [ ] Error classification has ≥5 distinct error types with Korean message mappings
  - [ ] Any remaining unknowns are explicitly listed with mitigation strategies
  - [ ] PRD FR-1 through FR-8 feasibility confirmed or risk flagged (source: Steps 1 teammate outputs)
- **Task**: Merge Step 1 teammate outputs (`step-1-param-inventory.md`, `step-1-pipeline-analysis.md`, `step-1-error-patterns.md`) into a single unified reference document. For each PRD requirement (FR-1 through FR-8), cite the specific research finding that confirms implementation feasibility. For workflow-idea items C-1 through C-10, document the resolution based on research findings or confirm they remain deferred to Planning. List any remaining unknowns with proposed mitigation strategies.
- **Output**: `prompt/outputs/step-2-research-report.md`
- **Post-processing**: Checklist verification — every PRD C.2 item and workflow-idea C-6 item has a ✅ or ⚠️ mark with evidence
- **Review**: `@fact-checker` — verify cross-references between research report and source teammate outputs are accurate
- **Translation**: none
- **Failure Recovery**: If research-integrator fails, orchestrator manually merges teammate outputs into a simplified table.

---

### 3. (human) Research Findings Review

> **PG Connection**: PG-1 + PG-2 — User validates system understanding before design begins. Incorrect assumptions caught here prevent cascading design errors.

- **Action**: Review the research integration report (`prompt/outputs/step-2-research-report.md`). Confirm:
  1. Parameter values match your understanding of the filter system
  2. Filter execution pipeline is correctly traced
  3. Error classifications make sense for your experience with the system
  4. Any flagged unknowns are acceptable or need additional investigation
- **Command**: `/review-research`
- **Autopilot Default**: Approve if `@fact-checker` passed with no corrections AND no RED pACS flags in Step 2. Log decision rationale.
- **Rejection Path**: If user rejects with specific concerns → re-run affected Step 1 teammate(s) with user feedback as additional context → re-run Step 2 integration → return to Step 3. If user rejects entirely → escalate to workflow redesign.

---

## Planning

### 4. Architecture & Deployment Design

> **PG Connection**: PG-1 + PG-2 — Resolves deployment location (D-1), execution template (D-7), and session continuity (D-5). These are the foundation of every execution command (PG-1) and every parameter operation (PG-2). Wrong architecture = systemic failure.

- **Agent**: `@architect` (opus)
- **Verification**:
  - [ ] Deployment file table lists every output file with its exact target path
  - [ ] Path constants (KRT_ROOT, KRT_PYTHON, KRT_REPORTS, KRT_FILTERS) verified against actual filesystem via `test -d` commands
  - [ ] Execution template specified and tested: `cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}` — confirmed `.venv/bin/python` exists and is executable
  - [ ] SCAN_TODAY default = `run_full_research_flow` (D-2) confirmed with routing logic for separated mode
  - [ ] screener_state.json location = `${KRT_REPORTS}/screener_state.json` with JSON schema defined (fields: `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`)
  - [ ] Existing `kiwoom-rest-trader/.claude/settings.local.json` preserved — no overwrites
  - [ ] Pre-flight verification checklist items (a)-(e) from B-13 defined with concrete Bash check commands:
    - (a) `test -d ${KRT_ROOT}`
    - (b) `test -x ${KRT_PYTHON}`
    - (c) `test -w ${KRT_REPORTS}`
    - (d) prefetch completeness check: parse `prefetchManifest.json` for ok/error/empty counts
    - (e) parameter variable name grep before Edit
  - [ ] `.gitignore` update plan for `*.bak.*` pattern documented
  - [ ] No file in deployment target will overwrite existing content (source: `ls` of existing `.claude/`)
- **Task**: Finalize the deployment architecture based on pre-resolved decisions D-1 through D-7. Produce a complete deployment manifest with every file path. Verify all path constants against the actual filesystem. Design the screener_state.json schema with all fields from B-12. Define the pre-flight verification checklist with executable commands. Inventory existing files in `kiwoom-rest-trader/.claude/` to ensure no conflicts. Plan `.gitignore` updates.
- **Output**: `prompt/outputs/step-4-architecture.md`
- **Review**: `@reviewer` — verify no conflicts with existing kiwoom-rest-trader structure
- **Translation**: none
- **Failure Recovery**: Path constant verification failure → prompt user with AskUserQuestion to confirm correct kiwoom-rest-trader location.

---

### 5. CLAUDE.md Blueprint Design

> **PG Connection**: PG-1 + PG-2 — CLAUDE.md is the sole routing hub. The intent-cluster table maps Korean input to the correct skill (PG-1: stock-scan, PG-2: filter-tune). Safety rules protect against destructive parameter changes (PG-2). Error wrapping prevents English error exposure (PG-1).

- **Agent**: `@claude-md-designer` (opus)
- **Verification**:
  - [ ] Intent-cluster routing table has ≥12 clusters with ≥2 Korean example phrases each (B-3 full cluster list: SCAN_TODAY, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, SHOW_PARAMS, CHANGE_PARAM, RERUN_FILTERS, RESTORE, COMPARE, THEORY_GUIDE, CONFIRM, ASK_MODULE)
  - [ ] Every cluster maps to a specific skill invocation (`stock-scan` or `filter-tune`) with the action name
  - [ ] Path constants section uses exact values from Step 4 architecture (source: Step 4)
  - [ ] Safety rules section encodes TS-1 through TS-5 as non-negotiable rules
  - [ ] Error classification table includes all error types from Step 1 research (source: Step 1 Teammate C)
  - [ ] Output format rules encode: 한국식 숫자 표기 ("4,805원", "-3.5%", "0.965배"), 면책조항 template, 표현 정책 (O: "기술적 완성도가 높은 종목" / X: "매수 추천") — from PRD §7.3, FR-8
  - [ ] Onboarding flow distinguishes new user (no screener_state.json) vs returning user (B-25)
  - [ ] Date interpretation rules encode B-15: "오늘" = `date +%Y%m%d`, "어제" = previous business day, weekday check
  - [ ] Estimated total length: 80–120 lines (compact but complete)
  - [ ] Mixed-intent handling rule: "필터 바꾸고 다시 돌려줘" → sequential routing (filter-tune → stock-scan)
- **Task**: Design the complete CLAUDE.md content structure. This is a blueprint specification (not the final file). Include exactly these 10 sections:

  1. **Header** (~3 lines): System name, purpose statement, skill references
  2. **Path Constants** (~8 lines): KRT_ROOT through EXEC_PATTERN from Step 4
  3. **Intent-Cluster Routing Table** (~30 lines): 12 clusters from B-3 with Korean patterns and skill+action mappings. Include mixed-intent rule.
  4. **Safety Rules** (~12 lines): TS-1 (Final constants only), TS-2 (backup before change), TS-3 (range validation), TS-4 (one-at-a-time recommendation), TS-5 (rerun suggestion after change)
  5. **Error Classification Table** (~15 lines): Error type → Korean message → Claude action. From Step 1 error analysis.
  6. **Output Format Rules** (~10 lines): Number formatting, disclaimer template, expression policy (FR-8.2/8.3). Disclaimer behavior: full disclaimer on first result output per session; abbreviated 1-line on subsequent outputs (B-23).
  7. **Date Interpretation** (~5 lines): B-15 rules. Directory existence = validity check.
  8. **Onboarding Flow** (~10 lines): New user (pre-flight + capabilities intro + first-execution interpretation guide after initial scan) vs returning user (session summary from screener_state.json). Source: B-25.
  9. **Execution Template** (~4 lines): EXEC_PATTERN with `.venv/bin/python`
  10. **Session Continuity** (~7 lines): Read screener_state.json at session start. If `last_param_changes` is non-empty, grep current `Final` value for each recorded param and compare with recorded `new_value`. Mismatch → Korean warning: "⚠️ 외부에서 파라미터가 변경된 것으로 보입니다: {param} = {actual} (기록: {recorded})". Write updated state at session end. Source: B-12 mitigation.

  Each section must reference its source (PRD FR, workflow-idea B-number, or Step output).

- **Output**: `prompt/outputs/step-5-claude-md-blueprint.md`
- **Post-processing**: Count estimated lines per section. Flag if total exceeds 130 lines — trim lower-priority content to maintain context efficiency.
- **Review**: `@reviewer` — verify routing table covers all PRD FR requirements; verify safety rules match TS-1~5 exactly
- **Translation**: none
- **Failure Recovery**: If blueprint exceeds line target, merge Output Format Rules into Safety Rules section and compress Date Interpretation inline.

---

### 6. (team) Skill Blueprint Design

> **PG Connection**: PG-1 → stock-scan skill (screener execution chains). PG-2 → filter-tune skill (parameter tuning master sequence). These are the two pillars of the entire system.

- **Team**: `skill-design-team`
- **Checkpoint Pattern**: standard
- **Pre-processing**: Provide each teammate with:
  - `prompt/outputs/step-2-research-report.md` (full research context)
  - `prompt/outputs/step-4-architecture.md` (deployment paths, constants)
  - `prompt/outputs/step-5-claude-md-blueprint.md` (routing table, safety rules)
- **Tasks**:

  - `@scan-designer` (opus): **stock-scan Skill Blueprint**
    Design the stock-scan SKILL.md structure and `references/` contents plan. The skill handles all PG-1 interactions. Include:

    1. **SKILL.md Structure**: Purpose statement, trigger conditions (which intent-clusters route here), cross-references to CLAUDE.md and kiwoom-rest-trader.

    2. **Execution Chains** (encode as numbered step sequences with checkpoints):
       - `SCAN_TODAY(date?)`: Default `run_full_research_flow`. Steps: validate date → announce expected time ("약 10-15분 소요됩니다") → execute with **`Bash(run_in_background: true)`** (mandatory — command exceeds 10-min Bash timeout) → on background completion notification, apply **4-step completion handling** (same as SCAN_SEPARATED): (1) extract stock count from stdout, (2) check stderr for errors, (3) apply error classification table from CLAUDE.md (B-4), (4) Korean result/error report → report Stage-by-stage results + final list + disclaimer. Checkpoint: exit code ≠ 0 → error classification table lookup. **Timeout safeguard**: if no completion notification within 30 min, report timeout and suggest retrying with SCAN_SEPARATED.
       - `SCAN_SEPARATED(date)`: `run_prefetch` with **`Bash(run_in_background: true)`** → on completion notification, report prefetch stats → prompt "필터를 실행할까요?" → `run_filters` (synchronous — typically <2 min) → report. Background completion handling: (1) extract stock count from stdout, (2) check stderr, (3) apply error classification, (4) Korean report (B-11).
       - `SCAN_RANGE(start, end)`: Generate business day list → loop SCAN_TODAY per day → progress report "3/5일 완료" → aggregate results (B-24).
       - `SHOW_RESULTS(date)`: Read `researchedCompany.md` → Korean summary table with Stage-by-stage stats from `stage*_passed.md` files. Format: `| Stage | 입력 | 통과 | 탈락률 |`.
       - `WHY_REJECTED(stock_name, date)`: Step 1: glob `reports/{date}/*{stock_name}*/` → checkpoint: not found → "해당 종목은 수집 대상에 포함되지 않았습니다". Step 2: Write stock name to `masterReference.md`. Step 3: Run `Filter_condition_update {date}`. Step 4: Read `masterReference.log` → extract latest block. Step 5: Parse rejection stage + condition + values → Korean explanation: "Stage N에서 탈락: {조건} = {실제값}. 기준 {기준값}. {gap} 미달." Step 6: Check log rotation (>500 lines → archive) (B-5, §6.5).
       - `COMPARE(date_a, date_b)`: Read both `researchedCompany.md` → compute diff (common/added/removed) → if tuning-log has changes between dates, note it → Korean comparison table (B-3 COMPARE chain).
       - `COMPARE_PARAMS(before_run, after_run)`: Same-date, different params comparison from tuning-log + current results (B-3 COMPARE_PARAMS chain).
       - `RERUN_FILTERS(date)`: Execute `run_filters` only → report before/after comparison (B-11).

    3. **Pre-flight Verification** (B-13): Session-start lightweight checks (a-c) + first-run full checks (d-e). Integration with onboarding flow.

    4. **Result Output Format**: Stage-by-stage summary → final list → disclaimer. Korean number formatting. **Type pattern handling**: Research confirmed `stage1_chart60_120_passed.md` contains stock names only (no Type A~E info). Two alternatives: (a) Re-derive Type by reading each passed stock's chart60/120.md and re-running pattern matching logic from `chart60_120Filter.py` — accurate but expensive; (b) Omit Type info from SHOW_RESULTS and note "Type 상세는 Stage 1 재평가로 확인 가능" — simple. **The `@scan-designer` decides between (a) and (b) based on Step 2 research findings — specifically: whether re-deriving Type info requires ≤3 additional Read calls per stock. Document the chosen approach and rationale in the blueprint.**

    5. **references/ File Plan**:
       - `references/execution-chains.md`: All chain definitions with checkpoint details
       - `references/pre-flight-checks.md`: Check commands and Korean error messages

    - **Deliverable**: `prompt/outputs/step-6-stock-scan-blueprint.md`

  - `@tune-designer` (opus): **filter-tune Skill Blueprint**
    Design the filter-tune SKILL.md structure and `references/` contents plan. The skill handles all PG-2 interactions. Include:

    1. **SKILL.md Structure**: Purpose statement, trigger conditions, master sequence overview.

    2. **Master Tuning Sequence** — `PARAM_CHANGE(param_id, new_value)` (B-22 full integration):
       - Step 0 `[TS-4]`: Multi-param detection → "한 번에 하나씩 변경을 권장합니다" warning. User override allowed; then apply Steps 1-8 per param.
       - Step 1 `[B-9]`: Range Map lookup → out-of-bounds = REJECT with Korean reason + theoretical basis.
       - Step 2 `[B-17]`: Shared constant check → if `_ALIGN_TOL_LOOSE`, list all affected Types/conditions with Korean explanation.
       - Step 3 `[B-10]`: masterReference.log gap analysis → "약 N개 추가 통과 예상". FALLBACK: no log available → skip, announce "추정 데이터 없음" at Step 4.
       - Step 4 `[B-7]`: Confirmation table: `| 파라미터 | 현재 값 | 변경 후 |` + Step 2-3 warnings + "적용할까요?"
       - Step 5 `[B-8]`: Backup: `cp {file} {file}.bak.{YYYYMMDD_HHmmss}`. Rotate: keep ≤5, oldest deleted only after tuning-log check (TS-2a).
       - Step 6: `Edit` the `Final` constant value. Unit conversion: user % → tolerance → multiplier (references/unit-conversion.md).
       - Step 7 `[B-16]`: Append row to `reports/tuning-log.md`: `| datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |`. **Log rotation**: if tuning-log.md exceeds 200 rows, archive to `tuning-log.YYYYMM.md` and start fresh (B-16 archiving rule). Claude must search archives when querying past tuning history.
       - Step 8: "필터를 다시 돌려볼까요?" suggestion.
       - SHORTCUT: In-range + non-shared constant → skip Steps 2, 3.

    3. **Branch Definitions**:
       - `SHOW_PARAMS(stage?)`: Read `Final` constants from specified filter module → format as Korean table with current value + meaning + theoretical basis. **Stage 5 limitation (C-4)**: `financeFilter.py` has no `Final` constants (hardcoded `cup_nga < 0`). If user requests Stage 5 parameter change → "Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. Phase 2에서 상수화를 검토합니다" response. Encode this as explicit branch in SHOW_PARAMS and PARAM_CHANGE Step 1 pre-check.
       - `CONFIRM`: Mark tuning-log last row notes = "✓ 확정" → update screener_state.json → "현재 설정이 확정되었습니다" (FR-6.5).
       - `RESTORE`: (1) Check `*.bak.*` existence via glob. (2a) If found → restore newest `.bak` → log restoration. (2b) If not found → extract `old_value` from tuning-log → Edit to restore → "백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다" (B-8 fallback).
       - `THEORY_GUIDE(stage?, context?)`: Serve FR-7 theory mapping from references/theory-guide.md. Market regime guidance (강세/약세/횡보 adjustments).
       - `ASK_MODULE(module_name)`: Explain auxiliary module existence/role + Phase 2 referral (PRD §6.4).
       - `COMPARE_EXPERIMENTS`: When user asks "이 세션 실험 결과 정리해줘" or similar — read `tuning-log.md` `stocks_passed_before`/`stocks_passed_after` columns chronologically → generate Korean comparison table showing each parameter change and its effect on pass count. No separate storage needed; tuning-log is the sole data source (B-16 combination view).

    4. **Parameter Variable Name Verification** (B-13e, PRD R-2): Before any Edit, `grep -n '{variable_name}' {file_path}`. If not found → "변수명이 변경된 것 같습니다" → fuzzy search → user alert.

    5. **references/ File Plan**:
       - `references/parameter-catalog.md`: All parameters grouped by Stage — documentation only, current values always from code
       - `references/range-map.md`: Physical range, danger zone, warning message, basis (theoretical/empirical) per parameter
       - `references/unit-conversion.md`: SOT for conversion: `tolerance = 1 - multiplier`, `user_pct = tolerance × 100`, `multiplier = 1 - (user_pct / 100)`
       - `references/shared-constants.md`: `_ALIGN_TOL_LOOSE` → affected Types/conditions map
       - `references/theory-guide.md`: Minervini SEPA, Weinstein Stage, Wyckoff, VCP, CANSLIM mapping per filter Stage
       - `references/tuning-sequence.md`: Master sequence + all branches (detailed encoding)

    - **Deliverable**: `prompt/outputs/step-6-filter-tune-blueprint.md`

- **Join**: Both teammates complete → Orchestrator proceeds to Step 7
- **SOT Write**: Team Lead records completion status and output paths
- **Review**: `@reviewer` — verify blueprints collectively cover all PRD FR-1 through FR-8; verify master tuning sequence encodes all 6 sub-ideas (B-7/8/9/10/16/17)
- **Translation**: none
- **Failure Recovery**: If one teammate fails, orchestrator assigns the failed skill design to a new agent with the other teammate's completed output as context reference.

---

### 7. (human) Design Approval

> **PG Connection**: PG-1 + PG-2 — Last checkpoint before file creation. User validates that the architecture and skill designs match their actual usage patterns and expectations.

- **Action**: Review all planning outputs:
  1. Architecture decision (`step-4-architecture.md`): Do the deployment paths make sense? Is the execution template correct?
  2. CLAUDE.md blueprint (`step-5-claude-md-blueprint.md`): Does the routing table capture how you'd actually speak in Korean? Are the safety rules appropriate?
  3. stock-scan blueprint (`step-6-stock-scan-blueprint.md`): Do the execution chains match your daily workflow?
  4. filter-tune blueprint (`step-6-filter-tune-blueprint.md`): Does the tuning flow feel safe and intuitive? Is the confirmation step acceptable?
  5. Any missing features or incorrect assumptions?
- **Command**: `/review-design`
- **Autopilot Default**: Approve if `@reviewer` passed on all blueprints AND no RED pACS flags. Record the decision rationale in the SOT (`state.yaml` `autopilot.decisions[]`); an optional `autopilot-logs/step-7-decision.md` projection may also be written (see Autopilot Logs — SOT is canonical).
- **Rejection Path**: If user rejects specific blueprint(s) → re-run affected Step (4/5/6) with user feedback → return to Step 7. If user rejects architecture (Step 4) → cascade re-run Steps 5-6 as they depend on architecture decisions.

---

## Implementation

### 8. CLAUDE.md Construction

> **PG Connection**: PG-1 + PG-2 — CLAUDE.md is the single entry point. It routes user intent to skills (PG-1: stock-scan, PG-2: filter-tune) and enforces safety rules (PG-2) and error wrapping (PG-1).

- **Agent**: `@claude-md-builder` (opus)
- **Verification**:
  - [ ] File exists at `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md` and is valid Markdown
  - [ ] All 10 sections from Step 5 blueprint are present in the file
  - [ ] All path constants resolve to existing directories (verified via `test -d` commands executed in Bash)
  - [ ] Intent-cluster routing table has ≥12 clusters matching Step 5 blueprint
  - [ ] Safety rules TS-1~5 present as absolute rules
  - [ ] Error classification table has ≥5 error types with Korean messages
  - [ ] File length is 80–130 lines (measured via `wc -l`)
  - [ ] Skill directory references (`stock-scan`, `filter-tune`) are syntactically correct (directories created in Step 9)
  - [ ] No placeholder text — every value is concrete
  - [ ] Existing `kiwoom-rest-trader/.claude/settings.local.json` is NOT modified
- **Pre-processing**: `ls -la /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md 2>/dev/null` — confirm no existing file (already verified: none exists)
- **Task**: Write the final CLAUDE.md file based on Step 5 blueprint. Deploy to target path. After writing:
  1. Verify all path constants with `test -d` commands
  2. Verify file length with `wc -l`
  3. Verify no placeholder text with `grep -c 'TODO\|PLACEHOLDER\|TBD\|XXX'`

  **CCP Compliance**:
  - Intent: Create orchestration routing document for stock screening system
  - Impact: New file in kiwoom-rest-trader — changes Claude Code behavior in that directory. No overwrites.
  - Design: Write complete file via Write tool in single operation.

- **Output**: `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md`
- **Post-processing**: `wc -l /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md && grep -c 'TODO\|PLACEHOLDER\|TBD' /Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md || true`
- **Review**: `@reviewer` — verify completeness against Step 5 blueprint; confirm no existing functionality broken
- **Translation**: none
- **Failure Recovery**: Write failure → check permissions with `ls -la`. Permission denied → prompt user with AskUserQuestion.

---

### 9. (team) Skill File Construction

> **PG Connection**: PG-1 → stock-scan skill files directly enable screener execution. PG-2 → filter-tune skill files directly enable parameter tuning. These are the core system deliverables.

- **Team**: `skill-build-team`
- **Checkpoint Pattern**: dense
- **Pre-processing**: Provide both teammates with:
  - `prompt/outputs/step-2-research-report.md` (code analysis reference for accurate parameter/chain encoding)
  - `prompt/outputs/step-4-architecture.md` (path constants)
  - Step 6 respective blueprints
  - Step 8 CLAUDE.md (for cross-reference consistency)
- **Tasks**:

  - `@scan-builder` (opus): **stock-scan Skill Construction**
    Build the complete stock-scan skill based on Step 6 blueprint.
    - **Checkpoints**:
      - CP-1: Directory structure created (`mkdir -p .claude/skills/stock-scan/references/`) + SKILL.md skeleton with purpose, triggers, chain overview
      - CP-2: All execution chains fully encoded in SKILL.md with checkpoints, error branches, Korean messages
      - CP-3: `references/execution-chains.md` and `references/pre-flight-checks.md` complete. All cross-references to CLAUDE.md verified.
    - **Post-processing per checkpoint**: `wc -l` on each file; `grep -c 'TODO\|PLACEHOLDER'` verification
    - **Deliverable**: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/` (SKILL.md + references/)

  - `@tune-builder` (opus): **filter-tune Skill Construction**
    Build the complete filter-tune skill based on Step 6 blueprint.
    - **Checkpoints**:
      - CP-1: Directory structure created (`mkdir -p .claude/skills/filter-tune/references/`) + SKILL.md skeleton with purpose, triggers, master sequence overview
      - CP-2: Master tuning sequence fully encoded with all 8 steps + SHORTCUT + branches (CONFIRM, RESTORE, SHOW_PARAMS, THEORY_GUIDE, ASK_MODULE). Range Map integration and unit conversion logic verified.
      - CP-3: All 6 references/ files complete:
        - `parameter-catalog.md`: All parameters from Step 1 research, grouped by Stage
        - `range-map.md`: Physical range, danger zone, warning, basis for each parameter
        - `unit-conversion.md`: Conversion formulas as SOT
        - `shared-constants.md`: `_ALIGN_TOL_LOOSE` dependency map
        - `theory-guide.md`: 5 theory frameworks mapped to Stages
        - `tuning-sequence.md`: Full master sequence with branch definitions
    - **Post-processing per checkpoint**: `wc -l` on each file; cross-reference check between SKILL.md and references/
    - **Deliverable**: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/` (SKILL.md + references/)

- **Join**: Both teammates complete → Orchestrator proceeds to Step 10
- **SOT Write**: Team Lead records deployment paths and completion status
- **Review**: `@reviewer` — verify both skills are internally consistent; verify all references/ files exist; verify SKILL.md cross-references to CLAUDE.md are correct
- **Translation**: none
- **Failure Recovery**: If a teammate fails at CP-1 or CP-2, retry with increased maxTurns. If CP-3 fails (references/ files), orchestrator writes the references/ files directly using the Step 6 blueprint as source material (절대 기준 1 — no TODO stubs or incomplete deliverables permitted). If orchestrator also fails → human escalation with specific file list and blueprint reference.

---

### 10. Supporting Infrastructure & Cross-Reference Validation

> **PG Connection**: PG-2 — screener_state.json enables session continuity for tuning workflows. tuning-log.md enables experiment tracking. .gitignore prevents backup file pollution. Cross-reference validation ensures the system is internally coherent.

- **Agent**: `@infra-validator` (opus)
- **Verification**:
  - [ ] `reports/screener_state.json` created with valid JSON schema matching B-12 spec:
    ```json
    {"last_scan_date": null, "last_param_changes": [], "last_results_summary": null, "current_backup_files": []}
    ```
  - [ ] `reports/tuning-log.md` created with header row: `| datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |` (English schema — canonical, matches the Step 7 append target in filter-tune `tuning-sequence.md` and the SOLE-writer schema in stock-scan SKILL.md; runtime parsers read these column keys)
  - [ ] `.gitignore` in kiwoom-rest-trader contains `*.bak.*` (appended, not overwritten)
  - [ ] Cross-reference: every skill name in CLAUDE.md routing table → corresponding `.claude/skills/{name}/SKILL.md` exists
  - [ ] Cross-reference: every `references/*.md` mentioned in SKILL.md files → file exists on disk
  - [ ] Cross-reference: path constants in CLAUDE.md → all directories exist (`test -d`)
  - [ ] Cross-reference: parameter names in `range-map.md` → match actual Python variable names from Step 1 inventory
  - [ ] Cross-reference: error types in CLAUDE.md error table → match Step 1 error classification
  - [ ] No orphan files: every created file is referenced by at least one other file in the system
- **Task**:
  1. Create `${KRT_REPORTS}/screener_state.json` with default empty schema
  2. Create `${KRT_REPORTS}/tuning-log.md` with Markdown table header
  3. Append `*.bak.*` to kiwoom-rest-trader `.gitignore` (create if not exists; append to existing)
  4. Create slash command files in `.claude/commands/` (project-level — these are workflow orchestration commands, NOT deployed to kiwoom-rest-trader; matches the `file:` paths in the Slash Commands section below):
     - `review-research.md` (Step 3 trigger)
     - `review-design.md` (Step 7 trigger)
     - `accept-system.md` (Step 12 trigger)
     Content as specified in Slash Commands section of this workflow.
  5. Run comprehensive cross-reference validation:
     - Read CLAUDE.md → extract skill references → verify each exists as directory
     - Read each SKILL.md → extract references/ file mentions → verify each exists
     - Read CLAUDE.md path constants → `test -d` each
     - Read range-map.md parameter names → grep against actual Python code for existence
     - Read CLAUDE.md error table → cross-reference with step-1-error-patterns.md
  6. Fix any broken references found (Edit/Write to correct paths or create missing files)
  7. Generate validation report with pass/fail per check

- **Output**: Supporting files created + `prompt/outputs/step-10-validation-report.md`
- **Post-processing**: Count total cross-reference checks run and pass rate. Target: 100% pass.
- **Review**: `@reviewer` — verify no broken references remain; verify .gitignore append didn't corrupt existing entries
- **Translation**: none
- **Failure Recovery**: Cross-reference failures → fix in-place. If fix requires structural change, log and escalate to human (Step 12).

---

### 11. Smoke Test Verification

> **PG Connection**: PG-1 + PG-2 — Prompt-engineering artifacts can only be verified by testing in real Claude Code context (B-21). Without testing, quality cannot be claimed (절대 기준 1). This step tests the *structure and content* of the files, not actual API execution.

- **Agent**: `@smoke-tester` (opus)
- **Verification**:
  - [ ] ≥7 test scenarios executed with documented results
  - [ ] ≥5 golden path tests: all PASS
  - [ ] ≥1 safety rule test: TS-1 rejection confirmed in skill content
  - [ ] ≥1 error path test: Korean error message confirmed in error table
  - [ ] Each test includes: test ID, scenario, input simulation, expected behavior, actual finding, PASS/FAIL
  - [ ] All FAIL results have remediation actions completed or escalated
- **Task**: Verify the deployed system by examining file contents and simulating interactions. Execute these test scenarios:

  **Golden Path Tests** (file content verification):
  1. `GP-1`: Read CLAUDE.md → verify routing table parses: each cluster has ≥2 Korean patterns + skill+action mapping
  2. `GP-2`: Read stock-scan SKILL.md → verify SCAN_TODAY chain has all steps: date validation → execution → parsing → reporting
  3. `GP-3`: Read filter-tune SKILL.md → verify PARAM_CHANGE master sequence has all 8 steps in correct order
  4. `GP-4`: Simulate "Stage 1 조건 보여줘": Read CLAUDE.md routing → confirms route to filter-tune SHOW_PARAMS → Read SKILL.md chain → confirm it references parameter-catalog.md → Read parameter-catalog.md → confirm Stage 1 parameters are listed
  5. `GP-5`: Verify pre-flight checks: Read pre-flight-checks.md → execute each Bash check command → all pass on current filesystem
  6. `GP-6`: Verify tuning-log.md header format matches B-16 specification
  7. `GP-7`: Verify screener_state.json is valid JSON with all required fields

  **Safety Tests**:
  8. `ST-1`: Read CLAUDE.md → confirm TS-1 rule explicitly forbids filter logic code modification
  9. `ST-2`: Read range-map.md → confirm at least 3 parameters have danger zone definitions with warning messages

  **Error Path Tests**:
  10. `EP-1`: Read CLAUDE.md error table → confirm ≥5 error types each have Korean message + Claude action
  11. `EP-2`: Verify error table references match actual exception class names from Step 1 research

  **Note**: Full system tests requiring Kiwoom API access (actual scan execution, live filter runs) are deferred to Step 12 user acceptance testing. This step verifies structural correctness and content completeness only.

- **Output**: `prompt/outputs/step-11-smoke-test.md`
- **Review**: none (smoke test is itself the verification mechanism)
- **Translation**: none
- **Failure Recovery**: FAIL results → fix in-place with Edit tool → re-test. If 3+ FAILs, escalate to human review before Step 12.

---

### 12. (human) Final Acceptance Testing

> **PG Connection**: PG-1 + PG-2 — The actual non-technical Korean-speaking user tests the system with real interactions. This is the ultimate quality gate.

- **Action**: Open a new Claude Code session in `/Users/tajun/spJavis/kiwoom-rest-trader/`. Test the following scenarios:

  **PG-1 Tests (Screener Execution)**:
  1. Does Claude greet you in Korean and explain what it can do? (Onboarding)
  2. "오늘 종목 스캔해줘" → Does it execute `run_full_research_flow` correctly? (FR-1.1)
  3. "결과 보여줘" → Does it show Korean summary with Stage stats + disclaimer? (FR-2)
  4. "삼성전자 왜 빠졌어?" → Does it trace through masterReference and explain in Korean? (FR-3)

  **PG-2 Tests (Filter Tuning)**:
  5. "Stage 1 조건 보여줘" → Does it show formatted parameter table with Korean meanings? (FR-4)
  6. "Type A 허용오차를 -5%로 바꿔줘" → Does it show confirmation table before changing? (FR-5, B-7)
  7. "원래대로 되돌려줘" → Does it restore from backup? (FR-6.4, B-8)
  8. "필터만 다시 돌려줘" → Does it run `run_filters` only? (FR-6.1)

  **Edge Cases**:
  9. Try requesting filter logic change → Does it reject per TS-1?
  10. Try an out-of-range parameter value → Does it warn per TS-3?

- **Command**: `/accept-system`
- **Autopilot Default**: N/A — this step MUST be human-verified. The system is designed for a non-technical user; only that user can confirm it works as intended.
- **Rejection Path**: If ≤2 scenarios fail → fix in-place (Edit tool on deployed files) → re-test failed scenarios only. If ≥3 scenarios fail → root-cause analysis → determine if design (Steps 5-6) or implementation (Steps 8-9) is the source → re-run from identified source step. **Partial acceptance**: user may accept PG-1 (scan) while requesting PG-2 (tuning) rework, or vice versa.

---

## Claude Code Configuration

### Sub-agents

```yaml
# === Research Phase ===

param-extractor:
  description: "Extract all Final constants from kiwoom-rest-trader filter modules"
  model: opus
  tools: [Read, Grep, Glob]
  permissionMode: default
  maxTurns: 30
  memory: local

pipeline-analyzer:
  description: "Analyze filter execution pipeline, output schemas, and masterReference.log format"
  model: opus
  tools: [Read, Grep, Glob, Bash]
  permissionMode: default
  maxTurns: 40
  memory: local

error-analyzer:
  description: "Classify error patterns in kiwoom-rest-trader"
  model: sonnet
  tools: [Read, Grep, Glob]
  permissionMode: default
  maxTurns: 20
  memory: local

research-integrator:
  description: "Merge research findings and validate coverage against PRD"
  model: opus
  tools: [Read, Grep]
  permissionMode: default
  maxTurns: 25
  memory: local

# === Planning Phase ===

architect:
  description: "Design deployment architecture and resolve technical decisions"
  model: opus
  tools: [Read, Grep, Glob, Bash]
  permissionMode: default
  maxTurns: 25
  memory: project

claude-md-designer:
  description: "Design CLAUDE.md blueprint with routing table and safety rules"
  model: opus
  tools: [Read]
  permissionMode: default
  maxTurns: 30
  memory: project

scan-designer:
  description: "Design stock-scan skill blueprint with execution chains"
  model: opus
  tools: [Read]
  permissionMode: default
  maxTurns: 35
  memory: project

tune-designer:
  description: "Design filter-tune skill blueprint with tuning sequence and range map"
  model: opus
  tools: [Read]
  permissionMode: default
  maxTurns: 40
  memory: project

# === Implementation Phase ===

claude-md-builder:
  description: "Build and deploy CLAUDE.md to kiwoom-rest-trader"
  model: opus
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  permissionMode: default
  maxTurns: 25
  memory: project

scan-builder:
  description: "Build stock-scan skill files (SKILL.md + references/)"
  model: opus
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  permissionMode: default
  maxTurns: 40
  memory: project

tune-builder:
  description: "Build filter-tune skill files (SKILL.md + references/)"
  model: opus
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  permissionMode: default
  maxTurns: 50
  memory: project

infra-validator:
  description: "Create supporting infrastructure and validate all cross-references"
  model: opus
  tools: [Read, Write, Edit, Bash, Glob, Grep]
  permissionMode: default
  maxTurns: 30
  memory: project

smoke-tester:
  description: "Execute structural smoke tests on deployed files"
  model: opus
  tools: [Read, Grep, Glob, Bash]
  permissionMode: default
  maxTurns: 25
  memory: project
```

### Checkpoint Patterns

```yaml
checkpoint_patterns:
  execution_note: "Checkpoints are executed by the Orchestrator at the specified frequency. Each action translates to a tool call: 'Verify files exist' = Bash(ls/test -f), 'Run verification' = Read + compare against checklist, 'Log pACS' = record score inline in state.yaml (canonical; build-step pACS) or Write to pacs-logs/ for the translation track, 'Submit review' = Agent(@reviewer or @fact-checker)."

  standard:
    description: "Default verification at step completion"
    actions:
      - Verify all output files exist and are non-empty
      - Run verification checklist items
      - Log pACS self-assessment
      - Submit to adversarial review if specified
    frequency: "Once, at step completion"

  dense:
    description: "Multi-checkpoint verification within a single step"
    actions:
      - All standard actions, executed at each named checkpoint (CP-1, CP-2, CP-3...)
      - Per-checkpoint post-processing (wc -l, placeholder grep)
      - Each checkpoint must pass before proceeding to next
      - Failure at any checkpoint triggers step-level failure recovery
    frequency: "At each named checkpoint within the step"
```

### Agent Teams

```yaml
teams:
  code-analysis-team:    # Step 1
    purpose: "Parallel deep analysis of kiwoom-rest-trader source code"
    teammates: [param-extractor, pipeline-analyzer, error-analyzer]
    join_condition: "All 3 teammates complete"
    sot_writer: "Orchestrator (Team Lead)"
    lifecycle: step-scoped

  skill-design-team:     # Step 6
    purpose: "Parallel design of stock-scan and filter-tune skill blueprints"
    teammates: [scan-designer, tune-designer]
    join_condition: "Both teammates complete"
    sot_writer: "Orchestrator (Team Lead)"
    lifecycle: step-scoped

  skill-build-team:      # Step 9
    purpose: "Parallel construction of stock-scan and filter-tune skill files"
    teammates: [scan-builder, tune-builder]
    join_condition: "Both teammates complete"
    sot_writer: "Orchestrator (Team Lead)"
    lifecycle: step-scoped
```

### SOT (State Management)

- **SOT File**: `prompt/.claude/state.yaml`
- **Write Authority**: Orchestrator only (Team Lead during team steps)
- **Agent Access**: Read-only — agents produce output files; orchestrator records paths in SOT
- **Quality Override**: Standard SOT pattern; no exceptions needed

```yaml
# state.yaml schema
workflow:
  name: "stock-filtering-collector"
  version: "1.0.0"
  current_step: 1
  status: "not_started"    # not_started | in_progress | completed | completed_degraded | failed
  degradation_notes: []    # e.g. ["step-1: error-analyzer failed, orchestrator produced minimal report"]
  parent_genome:
    version: "2026-05-26"
    source: "AgenticWorkflow"
  outputs:
    step-1-param-inventory: null
    step-1-pipeline-analysis: null
    step-1-error-patterns: null
    step-2-research-report: null
    step-4-architecture: null
    step-5-claude-md-blueprint: null
    step-6-stock-scan-blueprint: null
    step-6-filter-tune-blueprint: null
    step-8-claude-md: null
    step-9-stock-scan-skill: null
    step-9-filter-tune-skill: null
    step-10-validation-report: null
    step-11-smoke-test: null
  autopilot:
    mode: "enabled"
    decisions: []
  active_team: null
  completed_teams: []
```

### Slash Commands

```yaml
commands:
  /review-research:
    description: "Step 3 — Research 결과 검토 및 승인"
    file: ".claude/commands/review-research.md"
    content: |
      Read the research integration report at prompt/outputs/step-2-research-report.md.
      Present a Korean summary of key findings to the user.
      Ask for approval to proceed to Planning phase.

  /review-design:
    description: "Step 7 — 설계 검토 및 승인"
    file: ".claude/commands/review-design.md"
    content: |
      Read architecture (step-4), CLAUDE.md blueprint (step-5), and skill blueprints (step-6) from prompt/outputs/.
      Present a Korean summary of design decisions to the user.
      Ask for approval to proceed to Implementation phase.

  /accept-system:
    description: "Step 12 — 최종 시스템 수락 테스트"
    file: ".claude/commands/accept-system.md"
    content: |
      Guide the user through acceptance testing of the deployed system.
      Present the 10 test scenarios from Step 12 in Korean.
      Record pass/fail for each scenario.
```

### Runtime Directories

```yaml
runtime_directories:
  prompt/outputs/:           # Step output files (research reports, blueprints, test results) — populated
  prompt/.claude/:           # SOT directory (state.yaml) — canonical record of all build decisions
  verification-logs/:        # L1 verification results — ADVISORY file layer; canonical record is state.yaml inline (see note)
  pacs-logs/:                # pACS self-assessment results — holds TRANSLATION pACS files (step-{N}-translation-pacs.md); build-step pACS lives inline in state.yaml
  review-logs/:              # Adversarial review results — ADVISORY file layer; canonical record is state.yaml autopilot.decisions notes
  autopilot-logs/:           # Autopilot decision logs — ADVISORY file layer; canonical record is state.yaml autopilot.decisions
```

> **SOT precedence (절대 기준 2)**: The single source of truth for every build-step decision, adversarial review outcome, and L1 verification is the **inline record in `prompt/.claude/state.yaml`** (`autopilot.decisions[]` with step/gate/decision/note/date; `translation_tasks.*.pacs_score`). The `autopilot-logs/`, `review-logs/`, and `verification-logs/` directories are an **optional/advisory** per-file projection of that same data — they may be empty when the data is fully captured inline, which is the normal, compliant state (no separate writer competes with the single SOT writer). Only `pacs-logs/` is independently materialized, and only for the **translation** track.

### Error Handling

```yaml
error_handling:
  precedence: "Step-level 'Failure Recovery' overrides these defaults when defined."

  on_agent_failure:
    action: retry_with_feedback
    max_attempts: 3
    escalation: human

  on_validation_failure:
    action: retry_or_rollback
    retry_with_feedback: true
    rollback_after: 3

  on_review_failure:
    severity_low:    # Minor issues (typo, formatting, non-structural)
      action: fix_in_place_and_re_review
      max_attempts: 2
    severity_high:   # Structural issues (wrong routing, missing safety rule, broken cross-reference)
      action: re_run_step_with_feedback
      max_attempts: 1
      escalation: human
    reviewer_timeout:
      action: log_and_proceed_with_warning
      note: "Review bypassed — flag for Step 12 human validation"

  on_hook_failure:
    action: log_and_continue

  on_context_overflow:
    action: save_and_recover

  on_teammate_failure:
    attempt_1: retry_same_agent
    attempt_2: replace_with_upgrade
    attempt_3: human_escalation

  on_deployment_conflict:
    action: backup_existing_then_write
    backup_pattern: "{filename}.pre-orchestration.bak"
    note: "Already verified no CLAUDE.md exists; .claude/settings.local.json is preserved"

  on_path_not_found:
    action: ask_user
    message: "kiwoom-rest-trader 경로를 찾을 수 없습니다. 정확한 경로를 알려주세요."
```

### Autopilot Logs

```yaml
autopilot_logging:
  primary_record: "state.yaml autopilot.decisions[]"   # CANONICAL — single SOT writer; all required_fields captured here
  log_directory: "autopilot-logs/"                     # OPTIONAL advisory projection of primary_record
  log_format: "step-{N}-decision.md"                   # optional; only materialized if a per-file copy is needed
  required_fields:                                     # recorded inline as {step, gate, decision, note, date}
    - step_number        # -> step
    - checkpoint_type    # -> gate
    - decision           # -> decision
    - rationale          # -> note
    - timestamp          # -> date
```

### pACS Logs

```yaml
pacs_logging:
  # Two tracks, by design:
  build_step_pacs:                          # CANONICAL inline in state.yaml
    primary_record: "state.yaml autopilot.decisions[].note (pACS=NN) + translation_tasks.*.pacs_score"
    dimensions: [F, C, L]                   # Fidelity / Completeness / Lucidity
    scoring: "min-score"
    triggers:
      GREEN: "≥ 70 → auto-proceed"
      YELLOW: "50-69 → proceed with flag"
      RED: "< 50 → rework or escalate"
  translation_pacs:                         # materialized as files
    log_directory: "pacs-logs/"
    log_format: "step-{N}-translation-pacs.md"
    dimensions: [Ft, Ct, Nt]               # Fidelity / Completeness / Naturalness (translation-specific)
    scoring: "min-score"
    triggers: { GREEN: "≥ 70", YELLOW: "50-69", RED: "< 50" }
```
