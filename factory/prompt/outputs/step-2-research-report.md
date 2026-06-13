# Step 2 — Research Integration & Coverage Validation

> Generated: 2026-05-30
> Sources: step-1-param-inventory.md (75 Final constants), step-1-pipeline-analysis.md (9 modules, gap-value=Partial), step-1-error-patterns.md (14 error types)

## 1. Executive Summary

The kiwoom-rest-trader screener is a sequential 5-Stage filter pipeline (Stage 1 / 2 / 2-1 / 3 / 4 / 5) driven by three entry-point scripts (`run_full_research_flow.py`, `run_prefetch.py`, `run_filters.py`) plus a 6th tooled-up module (`Filter_condition_update.py`) that re-evaluates a user-curated `masterReference.md` against all stages and appends drop-reasons to an append-only `masterReference.log`. Tunable surface is well-defined: 75 `Final` constants extracted across 8 source files, all PRD §5.1 catalog rows match live code (only two cosmetic doc-drifts inside `chart60_120Filter.render_markdown`: "2.0%" / "60%" strings vs live 3.5% / 50% constants). Error surface is dominated by 14 exception types where the user-visible 9 collapse to a clean Korean-message dispatch table. The single biggest design risk for the orchestration layer is **`KiwoomApiError` being defined 8 times as independent class objects** — any `except KiwoomApiError` keyed on one import will silently miss the others, so the filter-tune Skill must dispatch on `type(exc).__name__` or on `RuntimeError` + attribute introspection. The biggest gap-value design decision needed for FR-5.2 is whether to patch `masterReference.log` to add a structured `[gap: …]` suffix per stage line; current state is "natural-language text only, numerics inline but non-uniform units (₩/%/회/억원)," making regex extraction unreliable. PRD §FR-1 through §FR-8 are all feasible with no blockers; remaining unknowns are deferred to Step 3 human gate (4 open questions).

## 2. PRD §FR-1 through §FR-8 Feasibility Matrix

| FR | Description (1-line) | Evidence (Step 1 source) | Feasibility | Risk |
|---|---|---|---|---|
| FR-1 | Natural-language scanner execution (full flow / prefetch / filters / date range / pre-flight) | step-1-pipeline-analysis.md §(a) traces all 3 scripts + exit-code conventions (0/1/2); step-1-error-patterns.md rows 4-6 confirm `OrganizeError`/`ResearchError`/`PrefetchError` exit-1 contract | Feasible | Low |
| FR-2 | Filter result interpretation (per-stage counts, comparisons, disclaimer) | step-1-pipeline-analysis.md §(b) confirms uniform `stage*_passed.md` plain-text schema (stk_nm per line, UTF-8 LF, trailing newline, 0-byte if empty); canonical SHOW_RESULTS = `researchedCompany.md` | Feasible | Low |
| FR-3 | Drop-reason deep analysis (stage/condition/value, multi-stock, gap) | step-1-pipeline-analysis.md §(c) confirms `masterReference.log` records actual + threshold inline; step-1-param-inventory.md gives every per-stage tunable for explanation context | Feasible | Med (FR-3.4 gap precision limited — see §5 / §10) |
| FR-4 | Parameter visualization (per-stage tables, theory mapping, history) | step-1-param-inventory.md fully enumerates 75 constants with file:line, current value, semantic meaning, and PRD §5.1 cross-reference (all rows match) | Feasible | Low |
| FR-5 | Parameter change execution (natural-language → Edit, impact preview, backup, range check, share-constant guard) | step-1-param-inventory.md "Critical Distinctions" surfaces `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` + shared-constant fan-out; live `Final` types confirmed for every targeted variable | Feasible | Med (FR-5.2 numeric impact estimation depends on log-format choice — see §10) |
| FR-6 | Iterative tuning loop (`run_filters` reuse, before/after diff, restore, confirm, tuning-log) | step-1-pipeline-analysis.md §(a) confirms `run_filters.py` does not touch `Filter_condition_update`; `researchedCompany.md` is the canonical diff target | Feasible | Low |
| FR-7 | Theory-based tuning guide (Minervini / Weinstein / Wyckoff / VCP / CANSLIM mapping, regime adjustment) | step-1-param-inventory.md per-stage "meaning" column already contains the theoretical lineage per constant; PRD §5.3 ↔ filter mapping table is unambiguous | Feasible | Med (theory mapping is anchored, but quantitative regime adjustment ranges are not yet sourced — see §10) |
| FR-8 | Disclaimer framing on every result emission | No code-side blocker — prompt-layer rule; nothing in Step 1 contradicts | Feasible | Low |

## 3. PRD §C.2 Traceability (Research 추가 조사 필요 항목)

| C.2 Item | Status | Step 1 Evidence | Notes |
|---|---|---|---|
| `masterReference.log` output format | Resolved (Partial gap data) | step-1-pipeline-analysis.md §(c) | Schema, separators, stamps, per-stock blocks fully documented; **gap values present as natural-language text only**, no structured `actual=`/`threshold=`/`gap=` fields. Patch proposal included. |
| `kiwoom-rest-trader` error patterns | Resolved | step-1-error-patterns.md full 14-row table + 9-known-type coverage | Korean message style guide auto-derived; `KiwoomApiError` 8-module trap documented as architectural risk. |
| `stage*_passed.md` exact format | Resolved | step-1-pipeline-analysis.md §(b) | All 6 stage files share identical line-per-stk_nm schema. **Type A/B/C/D/E pattern info is NOT in the .md** — only in stdout of standalone runs and inside `r.extra["type_results"]` within the pipeline. FR-2.2 "패턴 요약" must either parse `masterReference.log` reason text or extend `filter_stock()` return capture. |

## 4. workflow-idea §C-1 through §C-10 Resolution

| Item | Question | Resolution | Source |
|---|---|---|---|
| C-1 | Parameter catalog SOT duality (PRD says SOT = Python source; skill needs catalog for B-9 range check) | Resolved at Research — catalog stores only ranges/warning rules; current values always read live via `grep` / `Read`. Step 1 param inventory provides the authoritative snapshot for catalog seeding. | step-1-param-inventory.md (75-row table) |
| C-2 | `masterReference.log` gap data availability | Resolved at Research — **Partial**: textual numerics present, structured fields absent. Decision required at Planning whether to patch (see §10 Open Q1). | step-1-pipeline-analysis.md §(c) |
| C-3 | `_ALIGN_TOL_LOOSE` shared-constant dilemma (Types B/C/D fan-out) | Resolved at Research (impact map locked) → policy decision deferred to Planning. step-1-param-inventory.md "Critical Distinctions" lists exact consumer set: Type B 60m + Type B MA60-MA306 + Type C MA60-MA306 + Type D 60m fallback. | step-1-param-inventory.md §"Critical Distinctions" |
| C-4 | Stage 5 hard-coded `< 0` un-tunable | Resolved at Research — confirmed no `Final` constant for the threshold; CLAUDE.md must encode "Phase 2" deflection rule. | step-1-param-inventory.md Stage 5 section |
| C-5 | Date / holiday handling | Resolved at Research — kiwoom-rest-trader contains `_exchange.py` (referenced in step-1-error-patterns row 11) but Phase-1 plan uses `reports/{date}/` existence check; no holiday hardcoding needed. | step-1-error-patterns.md row 11 (`_exchange.py`) |
| C-6 | Research mandatory 4-item checklist | Resolved at Research — all 4 items closed (see §5 below). | step-1-* (all three artifacts) |
| C-7 | FR-7 theory guide lacks dedicated idea | Deferred — out of Research scope; filter-tune skill `references/theory-anchors.md` to be authored at Implementation. | n/a |
| C-8 | Deployment location undecided (A/B/C) | Deferred to Planning — choice between (A) inside kiwoom-rest-trader, (B) separate dir, (C) inside AgenticWorkflow; affects B-12 Hook reuse. Step 1 has no bearing on this decision. | n/a |
| C-9 | Meta-level gap (system behavior vs build method) | Deferred to Planning — B-19/B-20/B-21 (deployment / build order / verification) absorb this. | n/a |
| C-10 | B-11 default exec mode vs FR-1.1 spec tension (split vs full-flow default) | Resolved at Research (mechanical capability) — both `run_full_research_flow.py` and `run_prefetch.py + run_filters.py` are mechanically supported; policy choice (which is default for SCAN_TODAY) deferred to Planning. | step-1-pipeline-analysis.md §(a) |

## 5. workflow-idea §C-6 (Research 필수 조사 4-Item Checklist)

- [x] C-6-1: `masterReference.log` gap 수치 포함 여부 → **Partial — gap values present only as inline natural-language text within the per-stage `reason` string** (e.g., `종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%] 이탈`). No structured `[gap: …]` field. Filter-tune impact estimator (FR-5.2) must regex-extract or rely on the proposed minimal patch (3-step). (evidence: step-1-pipeline-analysis.md §(c) "Gap value inclusion: Partial")
- [x] C-6-2: `stage*_passed.md` format + Type pattern info → **All 6 stage files use an identical line-per-종목명 plain-text schema (UTF-8/LF, trailing newline, 0-byte when empty). Type A/B/C/D/E pattern information is NOT included** — Stage 1 .md emits only stk_nm. Type info lives in `r.extra["type_results"]` and surfaces in stdout for standalone runs only; FR-2.2 "통과 패턴 요약" must source it from `masterReference.log` reason strings (after triggering `Filter_condition_update`) or via direct `filter_stock()` invocation. (evidence: step-1-pipeline-analysis.md §(b))
- [x] C-6-3: Actual error patterns → **14 distinct error types catalogued** (6 domain custom + 3 built-in + 5 indirectly-wrapped). Exit-code convention is consistent (`0` normal / `1` input-absence domain error / `2` everything else). Korean message style guide derived (4 rules: domain-language / next-action-imperative / temporary-vs-structural / no-jargon). **Architectural trap**: `KiwoomApiError` defined as 8 independent class objects with the same name — never `except KiwoomApiError`-by-import. (evidence: step-1-error-patterns.md full table + architectural notes)
- [x] C-6-4: All Final constants extracted → **75 `Final[...]` typed constants enumerated across 8 source files** (7 active filter modules + `Filter_condition_update.py`). PRD §5.1 catalog: 25/25 rows match code values; 2 documentation-drift advisories inside `chart60_120Filter.render_markdown` string literals (Type C "2.0%" stale, Type D "60%" stale). No constants missing from PRD catalog that should be there; all omitted constants are intentionally structural/scaffolding. (evidence: step-1-param-inventory.md "Coverage Self-Check" + "PRD §5.1 Cross-Reference")

## 6. Refined Parameter Inventory (Summary by Stage)

The full 75-row table lives in **step-1-param-inventory.md** and is the SOT snapshot for catalog seeding. Per-stage tuning relevance for the `filter-tune` Skill:

| Stage | Module | Most-likely-tunable constants | Private/Shared | Notes |
|---|---|---|---|---|
| 1 | `chart60_120Filter.py` | `_TYPE_A_ALIGN_TOL`, `_ALIGN_TOL_LOOSE` ⚠️shared, `_TYPE_B_BELOW_MA60_RATIO`, `_TYPE_C_CONVERGE_PCT`, `_TYPE_D_ALIGN_TOL_120`, `_TYPE_D_CLOSE_OVER_MA60_RATIO`, `_TYPE_E_SPREAD_PCT`, `_TYPE_E_SHORT_ALIGN_TOL`, `_TYPE_E_CLOSE_OVER_MA60_RATIO`, `_TYPE_E_MA60_OVER_MA306_TOL`, `_REQUIRED_STATIC_BARS` | Mostly private to Type; `_ALIGN_TOL_LOOSE` fan-out = Type B 60m + Type B MA60-MA306 + Type C MA60-MA306 + Type D 60m fallback | 26 total constants including 7 labels + dispatch table; 11 doc-drift sites checked, 2 stale |
| 1-adj | `chart60Filter.py` (standalone) | `_MA_ALIGNMENT_TOLERANCE` (0.005), `_REQUIRED_CONSECUTIVE_BARS` (3) | Private — NOT shared with Stage 1's `_ALIGN_TOL_LOOSE` | **Anti-confusion**: see disambiguation block below |
| 2 | `chart240Filter.py` | `_MA60_MA306_TOLERANCE` (0.025), `_REQUIRED_CONSECUTIVE_BARS` (3) | Private | Reuses chart60 regexes by re-import |
| 2-1 | `chartDayPreFilter.py` | `_DAILY_SURGE_THRESHOLD` (0.15) | Private | Only one tunable threshold |
| 3 | `chartDayFilter.py` | `_MA10_MA20_MA60_TOLERANCE`, `_MA60_MA306_LOWER_TOL`, `_MA60_MA306_UPPER_TOL`, `_CLOSE_VS_MA612_LOWER`, `_CLOSE_VS_MA612_UPPER`, `_REQUIRED_ALIGNED_BARS`, `_REQUIRED_CONSECUTIVE_BARS` | Private | Asymmetric MA612 envelope (lower -15%, upper +50%) |
| 4 | `investorFilter.py` | `_THRESHOLD_FOREIGN_CONSEC_SELL` (2), `_THRESHOLD_INST_CONSEC_SELL` (8), `_THRESHOLD_INDI_CONSEC_BUY` (3), `_THRESHOLD_FOREIGN_TOTAL_SELL` (15) | Private | All integer day-count thresholds |
| 5 | `financeFilter.py` | **None** — `cup_nga < 0` hard-coded | n/a | CLAUDE.md must deflect to Phase 2 |

### `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` — DO-NOT-CONFLATE

| Property | `_ALIGN_TOL_LOOSE` | `_MA_ALIGNMENT_TOLERANCE` |
|---|---|---|
| Owner | `chart60_120Filter.py:120` | `chart60Filter.py:75` |
| Value | 0.015 (×0.985, -1.5%) | 0.005 (×0.995, -0.5%) |
| Scope | Shared across Type B/C/D within Stage 1 | Sole alignment tolerance for standalone chart60 |
| Tuning impact | Cross-cuts Types B/C/D | Localized, no cross-stage propagation |

filter-tune Skill MUST disambiguate before any Edit when user says "60-분 정배열 허용오차 완화."

Look-alike traps additionally documented in step-1-param-inventory.md: `_REQUIRED_CONSECUTIVE_BARS` declared independently in 3 modules (all currently `3`, but independent), `_REQUIRED_STATIC_BARS` (8) vs `_REQUIRED_BARS` (16, investor) vs `_REQUIRED_CONSECUTIVE_BARS` (3); 3 different MA60-MA306 tolerances on 3 timeframes.

## 7. Pipeline Architecture (Operational View)

Entry points the `stock-scan` Skill invokes (all under `/Users/tajun/spJavis/kiwoom-rest-trader/scripts/`, no argparse — direct `sys.argv` parsing):

- `SCAN_TODAY` → `run_full_research_flow.py` — full pipeline (① upperLowerPrice → ② conditionCompany → ③ organizedCompany → Stage 0 prefetch → Stage 1-5 filters → `Filter_condition_update`). `__main__` at line 69-70. Exit 0/1/2.
- `SCAN_PREFETCH_ONLY` → `run_prefetch.py` — ①+②+③+Stage 0 only, no filtering, no `Filter_condition_update`. `__main__` at line 185-186. Exit 0/1/2.
- `SCAN_FILTER_ONLY` → `run_filters.py` — `researchFlow.filter_today(date)` + `save_researched_company` + `save_all_stages_passed`. **Does NOT invoke `Filter_condition_update`** — `masterReference.log` is updated only via `run_full_research_flow.py`. `__main__` at line 87-88. Exit 0/1/2.

Standalone filter invocation pattern (for surgical debugging by filter-tune Skill or user) — all 9 filter modules expose `__main__`:

- `python -m src.kiwoom.itemFilter.<module> <stock> [YYYYMMDD]` or `--all [YYYYMMDD]` (argparse not used except `stageMasterFilter.py`).
- Lines: `chart60_120Filter.py:1071`, `chart240Filter.py:686`, `chartDayPreFilter.py:522`, `chartDayFilter.py:909`, `investorFilter.py:695`, `financeFilter.py:543`, `chart60Filter.py:819`, `Filter_condition_update.py:299`, `stageMasterFilter.py:713`.

WHY_REJECTED chain entry: `python -m src.kiwoom.itemFilter.Filter_condition_update YYYYMMDD [YYYYMMDD …]` — supports multi-date space-separated args.

**Canonical SHOW_RESULTS file**: `researchedCompany.md` (5 grounds in step-1-pipeline-analysis.md §(b)/Recommended canonical):
1. Only file both `run_full_research_flow.py` and `run_filters.py` produce.
2. `Filter_condition_update` references it explicitly via `_RESEARCHED_MD`.
3. `final_selected=True` (all 6 stages passed) precise semantics.
4. Identical content to `stage5_finance_passed.md` but clearer semantics.
5. `.p1.md`/`.p2.md` are **legacy orphans** — no generator code exists in current `src/`; present only in pre-2026-05-21 directories. `masterConditionCompany.md` is from `stageMasterFilter.py` (Phase 2 scope, independent pool).

## 8. Error Handling Matrix (Operational View)

Compressed from 14 catalogued types to the 9 user-facing classes the filter-tune / stock-scan Skills must dispatch:

| Error | User-facing Korean message | Suggested user action | Recovery strategy |
|---|---|---|---|
| `KiwoomAuthError` | 키움 인증에 실패했습니다. APP_KEY·SECRET_KEY 설정을 확인하고, 잠시 후 다시 시도해주세요. | Verify credentials, retry | Re-run after env var refresh |
| `KiwoomApiError` (any of 8 module-local definitions) | 키움 데이터 조회에 실패했습니다. 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. | Wait + retry | Re-run prefetch; dispatch by `type(exc).__name__` |
| `KiwoomConditionError` | 조건검색 서버 응답에 실패했습니다. 설정한 조건명이 키움 HTS에 저장되어 있는지 확인해주세요. | Verify HTS condition name | Re-run condition stage |
| `OrganizeError` | 수집된 종목 데이터가 없습니다. 조건검색·상하한가 수집을 먼저 실행해주세요. | Run condition + upperLower stages | Re-run earlier pipeline stage |
| `ResearchError` | 필터링에 필요한 데이터 파일이 없습니다. 먼저 데이터 수집(prefetch)을 실행해주세요. | Run prefetch | Pivot to `run_prefetch` |
| `PrefetchError` | 종목 사전 수집을 시작할 데이터가 없습니다. 조건검색·상하한가 단계를 먼저 완료해주세요. | Run condition stage | Re-run `run_full_research_flow` from start |
| `httpx.HTTPError` (incl. `ConnectError`, `TimeoutException`) | 키움 서버에 연결할 수 없습니다. 인터넷 연결과 키움 서버 상태를 확인한 뒤 다시 시도해주세요. | Check network, retry | Wrapped internally to `KiwoomApiError`/`KiwoomAuthError`; user-surface is the wrapped exception |
| `FileNotFoundError` | 필요한 데이터 파일을 찾을 수 없습니다. 먼저 해당 단계의 데이터 수집을 실행해주세요. | Run prerequisite stage | Re-run upstream pipeline step |
| `ValueError` (parser/argument) | 데이터 형식이 올바르지 않습니다. 수집된 데이터가 손상되었을 수 있으니 다시 수집해보세요. | Re-collect, file bug if persistent | Force re-prefetch for affected stock |

**Architectural risk (must surface to filter-tune Skill)**: `KiwoomApiError` is declared independently in **8 modules** (chart60/120/240/Day client `models.py`, `etc/foreigner.py:74`, `upperLowerPrice.py:214`, `finance/finance.py:82`, `investor/investor.py:88`). Each is a separate class object with the same name. Catching via `except KiwoomApiError` from one import does NOT catch the others. **Dispatch on `type(exc).__name__ == "KiwoomApiError"`** or on common base `RuntimeError` + attribute introspection (`exc.code`, `exc.api_id`). All `KiwoomApiError`/`KiwoomAuthError` raises have 0 explicit catches — they are absorbed by `except Exception` at script entry, exit 2. Exit-code convention is consistent: `0` normal / `1` input-absence domain error / `2` everything else — Skills can use exit code as a first-level dispatch key.

## 9. Cross-Reference Validation

Mutual consistency check across the 3 Step 1 artifacts:

- ✅ **Parameter inventory ↔ pipeline analysis**: Every module enumerated in step-1-param-inventory.md (`chart60_120Filter`, `chart60Filter`, `chart240Filter`, `chartDayPreFilter`, `chartDayFilter`, `investorFilter`, `financeFilter`, `Filter_condition_update`) appears in step-1-pipeline-analysis.md's call chain or `__main__` table. The 5-Stage execution order in `Filter_condition_update.py`'s `_STAGES` (S1→S2→S2-1→S3→S4→S5) matches `researchFlow.facade._run_filter_pipeline` execution and matches PRD §2.2 stage order.
- ✅ **Error patterns ↔ pipeline**: Every raise site cited in step-1-error-patterns.md lives in a module that step-1-pipeline-analysis.md traces (`auth.py`, `*/client.py`, `conditionCompany/*`, `organizedCompany/facade.py`, `researchFlow/facade.py`, `researchFlow/prefetch.py`, `itemFilter/*Filter.py`). Catch sites in scripts (`run_research_flow.py`, `run_filters.py`, `run_prefetch.py`) align with the exit-code contract of step-1-pipeline-analysis.md §(a).
- ✅ **Param inventory ↔ error patterns**: `FileNotFoundError` / `ValueError` catch sites in `itemFilter/*Filter.py` (chart60:565, chart240:450, chartDay:657, chartDayPre:316, chart60_120:789, finance:365, investor:479) cover every module whose `Final` constants are inventoried.

**No conflicts detected** between the three Step 1 outputs. The two minor advisories from step-1-param-inventory.md (Type C "2.0%" / Type D "60%" doc-drift in `render_markdown` string literals at chart60_120Filter.py:866/870) are pure documentation drift — math runs on the live `Final` constants — and are surfaced as Open Question 2 below.

## 10. Open Questions (forward to Step 3 human gate)

| Question | Why unresolved | Proposed mitigation | Where to address |
|---|---|---|---|
| Q1: Should `masterReference.log` be patched to add a structured `[gap: actual=…, threshold=…, gap=…]` suffix per stage line? | Current log carries gap values only as natural-language text with non-uniform units (₩/%/회/억원). FR-5.2(a) impact estimation regex-extraction is unreliable without a structured field. step-1-pipeline-analysis.md §(c) provides a 3-step minimal patch. | Decide at Planning: (A) ship Phase-1 with regex-best-effort extraction + explicit precision caveat to user, (B) apply the 3-step patch to `_analyze_stock` so the appendix `[gap: …]` is emitted, then Skills can rely on a deterministic parse. Trade-off: (A) zero code change in kiwoom-rest-trader, lower precision; (B) one small kiwoom-rest-trader patch + immediate precision win. | Planning §filter-tune design |
| Q2: Doc-drift in `chart60_120Filter.py render_markdown` ("Type C 2.0%" stale vs live 3.5%; "Type D 60%" stale vs live 50%) — fix now or defer? | step-1-param-inventory.md §"PRD §5.1 Cross-Reference" advisory #1+2. Math is correct; user reading the rendered Markdown sees stale percentages. Could mislead the user when reviewing existing reports. | Decide at Planning: (A) edit the two string literals at chart60_120Filter.py:866/870 in a single trivial PR (no logic change, true to live constants), (B) defer to Phase 2 and have the filter-tune Skill annotate the discrepancy whenever the user reads chart60_120Filter rendered output. | Planning §scope-of-changes-to-kiwoom-rest-trader |
| Q3: Should the filter-tune Skill expose the `KiwoomApiError` 8-module trap to the user, or hide it behind the dispatch layer? | The trap is invisible to the user but is a critical maintenance concern. step-1-error-patterns.md §Architectural Notes #1 documents it. If filter-tune merely catches via `type(exc).__name__`, the user never knows; if a future kiwoom-rest-trader refactor consolidates the class, the dispatch breaks silently. | Hide from runtime user-facing messages (always emit the canonical Korean text), but **encode an internal CLAUDE.md note** for the operator (Claude) that documents the dispatch rule and the underlying 8-module fact. Re-verify on every release of kiwoom-rest-trader (B-13 (e) "변수명 존재 검증"-style check, extended to "class consolidation 검증"). | filter-tune Skill `references/error-dispatch.md` |
| Q4: SCAN_TODAY default execution mode — `run_full_research_flow` (per FR-1.1) vs `run_prefetch` + `run_filters` split (per B-11)? | step-1-pipeline-analysis.md confirms both are mechanically supported; `run_filters` does NOT update `masterReference.log` whereas `run_full_research_flow` does. This is a UX/orchestration decision, not a research question. | Decide at Planning per C-10's 3 options: (a) PRD-faithful: SCAN_TODAY = full-flow default, "나눠서 해줘" → split; (b) B-11: always split, "한 번에 해줘" = full-flow; (c) hybrid: first-time = full-flow (onboarding), thereafter split (tuning sessions). Recommend (c) for best balance of FR-1.4 progress reporting and FR-6 tuning loop ergonomics. | Planning §CLAUDE.md routing table |

## 11. Verification Self-Check

- [x] All 3 Step 1 sources referenced (file:section citations) — step-1-param-inventory.md (§Critical Distinctions, §PRD §5.1 Cross-Reference, §Coverage Self-Check); step-1-pipeline-analysis.md (§(a), §(b), §(c)); step-1-error-patterns.md (full table, §Architectural Notes)
- [x] FR-1 through FR-8 each have a Feasibility verdict + Step 1 evidence (§2 — 8/8 rows)
- [x] All 4 C-6 items have ✅ with evidence (§5 — 4/4)
- [x] All 10 C-1..C-10 items have a Resolution column (§4 — 10/10; 6 Resolved at Research, 1 Deferred-policy, 3 Deferred-Planning)
- [x] Executive Summary ≤ 10 lines (§1 — one cohesive paragraph, ≤10 lines)
- [x] Open Questions section has ≥ 1 entry with proposed mitigation (§10 — 4 entries, each with proposed mitigation)
- [x] No conflicts between Step 1 outputs (§9 — three pairwise checks all ✅; two minor doc-drift advisories surfaced as Open Question 2)
