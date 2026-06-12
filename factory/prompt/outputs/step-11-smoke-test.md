# Step 11 — Smoke Test Verification Report

> Generated: 2026-05-30 (KST)
> Mode: DRY-RUN (no real pipeline execution, no file modifications)
> Scope: 10 end-to-end test scenarios + pre-flight + intent routing + known limitations
> Deployed target: `/Users/tajun/spJavis/kiwoom-rest-trader/` (CLAUDE.md 14,730 bytes, post Step-10 edits)
> Skill SOTs inspected: stock-scan/SKILL.md (211 lines), filter-tune/SKILL.md (441 lines), 11 references files

## Executive Summary (≤10 lines)

- Scenarios traced: **10/10**
- **PASS: 10  FAIL: 0  PARTIAL: 0**
- Pre-flight (a)(b)(c): **ALL PASS** — directory present, Python 3.12.7 verified, reports writable
- Stage 5 hard-block: **4/4 variants blocked at PRIMARY guard** (Step 1.0 keyword pre-check), with Step 1.2 secondary guard + SHOW_PARAMS Step 1.5 + ASK_MODULE financeFilter row as triple defence-in-depth
- ADR-011 `type(exc).__name__` STRING dispatch: confirmed in CLAUDE.md L52 + stock-scan §6 pseudocode
- ADR-012 `Bash(run_in_background:true)` mandate: confirmed both in CLAUDE.md L13/L20 and stock-scan §3 Chain 1
- R-9 lock semantics: mkdir/rmdir directory-based, atomic POSIX semantics, try/finally in BOTH RESTORE Step 2a and 2b (Step10-W4 fix verified)
- Mixed-intent split routing (CLAUDE.md L34-37 regex): verified end-to-end
- screener_state.json present (returning-user path); no `filter-tune.lock` present at smoke-test time
- Critical issues for Step 12 human review: **0 blocking** / **3 advisory** (see §8)
- **Overall: PASS**

---

## §1. Pre-flight Dry-Run Results

| Check | Command | Result |
|---|---|---|
| (a) `${KRT_ROOT}` exists | `test -d /Users/tajun/spJavis/kiwoom-rest-trader` | **PASS** — `(a) PASS: kiwoom-rest-trader exists` |
| (b) Python venv executable + R-10 probe | `[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version` | **PASS** — `Python 3.12.7` (matches CLAUDE.md L8 declaration verbatim) |
| (c) `${KRT_REPORTS}` writable | `test -w /Users/tajun/spJavis/kiwoom-rest-trader/reports` | **PASS** — `(c) PASS: reports writable` |
| Lock-state | `test -d ${KRT_REPORTS}/filter-tune.lock` | absent — no contention (R-9 healthy initial state) |
| screener_state.json | `test -f ${KRT_REPORTS}/screener_state.json` | **PRESENT** (427 bytes, mtime May 30 14:18) → **returning-user branch** |
| reports/ directory listing | `ls reports/ \| head -5` | `20260510.zip, 20260512.zip, 20260513.zip, 20260514, 20260514.zip` — historical scan directories present |

**Interpretation**: The smoke-test session encounters a returning user. Per CLAUDE.md L102-105, onboarding emits 2-3 line Korean session summary from `last_scan_date` + `last_param_changes`. External-change detection (B-12) runs before any user utterance.

---

## §2. Intent Routing Verification (CLAUDE.md vs Skills)

| Cluster | CLAUDE.md route | Skill claim | Match? |
|---|---|---|---|
| SCAN_TODAY | stock-scan `scan_today()` + run_in_background:true (ADR-012) | stock-scan §3 Chain 1 (`run_full_research_flow` bg-true) | **YES** |
| SCAN_RANGE | stock-scan `scan_range(start, end)` B-24 | stock-scan §3 Chain 3 (영업일 loop, max 31일) | **YES** |
| SHOW_RESULTS | stock-scan `show_results(date)` | stock-scan §3 Chain 4 (Option (b) — Type omitted) | **YES** |
| WHY_REJECTED | stock-scan `why_rejected(...)` masterReference 체인 | stock-scan §3 Chain 5 (Edit only, NEVER Write) | **YES** |
| SHOW_PARAMS | filter-tune `show_params(stage)` | filter-tune §4 Branch 1 (live grep, not catalog SOT) | **YES** |
| CHANGE_PARAM | filter-tune `change_param(...)` Master Sequence 8-step | filter-tune §3 Master Sequence (Steps 0-8 + SHORTCUT) | **YES** |
| RERUN_FILTERS | stock-scan `rerun_filters(date)` sync | stock-scan §3 Chain 8 (prefetchManifest pre-check, foreground) | **YES** |
| RESTORE | filter-tune `restore(file?, ts?)` | filter-tune §4 Branch 4 (Step 2a primary, 2b fallback, 2c both-fail) | **YES** |
| COMPARE | stock-scan `compare(date_a, date_b)` Chain 6 | stock-scan §3 Chain 6 + COMPARE_PARAMS dual route note | **YES** (with experiment-scope routing rule documented L29) |
| COMPARE_PARAMS | stock-scan `compare_params(...)` Chain 7 | stock-scan §3 Chain 7 (8-column read) — experiment-set → filter-tune COMPARE_EXPERIMENTS | **YES** (split rule explicit) |
| THEORY_GUIDE | filter-tune `theory_guide(topic)` FR-7 | filter-tune §4 Branch 5 (Minervini/Weinstein/Wyckoff/VCP/CANSLIM) | **YES** |
| CONFIRM | filter-tune `confirm()` | filter-tune §4 Branch 3 (state.confirmed=true + tuning-log ✓ 확정) | **YES** |
| ASK_MODULE | filter-tune `ask_module(...)` Branch 6 + Phase-2 deflection | filter-tune §4 Branch 6 (financeFilter ⚠️ Phase 2) | **YES** |

**Result**: 13/13 clusters match between CLAUDE.md routing table and skill internal trigger tables. No drift detected.

> **Addendum (2026-05-31, post-build — flight-recorder integrity preserved)**: The 13/13 above is the *as-verified-at-build* value and is retained unchanged. After build completion, a post-hoc product-CLAUDE.md fix (P1-b) exposed a 14th cluster `SCAN_SEPARATED` — it already existed in the stock-scan skill trigger table but was missing from the CLAUDE.md routing table. Live product is now **14 clusters**. **Re-verified 2026-05-31 (bidirectional)**: `SCAN_SEPARATED` is present in BOTH the CLAUDE.md routing table AND the stock-scan skill §1 trigger table (Chain 2) → **14/14 clusters match, zero drift**. Note: the original 13/13 above was a one-directional CLAUDE.md→skill check (cf. step-10 Internal-Consistency note); the stock-scan skill always carried SCAN_SEPARATED (Chain 2) but the CLAUDE.md routing table omitted it — P1-b closed that real skill→CLAUDE.md drift the original smoke test missed. filter-tune §1's 7th entry `COMPARE_EXPERIMENTS` is the documented experiment-scope sub-branch of COMPARE_PARAMS (CLAUDE.md L30), not an orphan. See product ADR-014.

**Mixed-intent rule (CLAUDE.md L34-37)**: regex `(CHANGE|바꿔|완화|강화|조정).*(다시|재실행|돌려|돌리)` → split into sequential `[filter-tune CHANGE_PARAM, stock-scan RERUN_FILTERS]`. Both skills reference this rule verbatim (stock-scan §1 / filter-tune §1).

---

## §3. Test Scenarios — Results Matrix

| # | Scenario | Input (Korean) | Expected Skill+Action | Trace verdict | Notes |
|---|---|---|---|---|---|
| 1 | SCAN_TODAY default | "오늘 종목 스캔해줘" | stock-scan Chain 1 (run_full_research_flow bg-true) | **PASS** | ADR-012 mandate verified in both CLAUDE.md and SKILL.md |
| 2 | SHOW_RESULTS canonical | "오늘 결과 보여줘" | stock-scan Chain 4 (Type omitted, Option (b)) | **PASS** | Korean note `"* Type 상세는 Stage 1 재평가로 확인 가능"` verbatim in output-templates.md L48 |
| 3 | WHY_REJECTED chain | "삼성전자가 왜 빠졌어?" | stock-scan Chain 5 (Edit only, log rotation > 500) | **PASS** | NEVER Write rule verified L79; rotation Korean message in output-templates.md L98 |
| 4 | PG-2 PARAM_CHANGE happy path | "Type A 허용오차 -5%로 완화해줘" | filter-tune Master Sequence 8 steps | **PASS** | All 8 steps present and ordered; mkdir atomic in Step 5 |
| 5 | Stage 5 hard-block | "Stage 5 조건 바꿔줘" + 3 variants | filter-tune Step 1.0 PRIMARY guard REJECT | **PASS** | 4/4 variants caught at Step 1.0 keyword pre-check |
| 6 | Shared constant impact (B-17) | "_ALIGN_TOL_LOOSE를 0.02로 바꿔" | filter-tune Step 2 shared registry → 4-tuple verbatim list | **PASS** | shared-constants.md confirms single shared constant; chart60_120 vs chart60 distinction explicit |
| 7 | RESTORE branch (B-8 fallback) | "원래대로 되돌려줘" | filter-tune Branch 4 Step 2a (primary) / 2b (fallback) | **PASS** | try/finally rmdir verified in BOTH 2a and 2b (Step10-W4 fix lines 284, 293) |
| 8 | Mixed intent | "필터 바꾸고 다시 돌려줘" | sequential: CHANGE_PARAM → user confirm → RERUN_FILTERS | **PASS** | CLAUDE.md L34-37 regex + both skills reference rule verbatim |
| 9 | Error handling (KiwoomApiError) | bg scan emits KiwoomApiError("HTTP") | CLAUDE.md `type(exc).__name__` STRING dispatch | **PASS** | ADR-011 explicit L52; user action jargon-free `"잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요."` L58 |
| 10 | R-9 lock contention | SCAN_TODAY during filter-tune Edit | stock-scan refuses with Korean message | **PASS** | Both sides verified: stock-scan §3 Chain 1 L43 refusal + filter-tune §3 Step 5 mkdir/Step 7 rmdir |

---

## §4. Per-Scenario Detail

### Scenario 1 — SCAN_TODAY default (PG-1 happy path)
- **Input**: `"오늘 종목 스캔해줘"`
- **Routing trace**:
  - CLAUDE.md L20 → SCAN_TODAY cluster → stock-scan `scan_today(date=today)` with annotation `default = run_full_research_flow ; run_in_background:true` (ADR-012)
  - stock-scan §1 §3 Chain 1 (L41-51)
- **Chain steps verified**:
  1. date validation `^[0-9]{8}$` (Chain 1 Step 1)
  2. future-date guard (Step 2)
  3. screener_state cache-hit check (Step 3)
  4. Korean estimate emit: `"약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다."` (verbatim L48, background-execution.md §2)
  5. `Bash(run_in_background:true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_full_research_flow {date}` (verbatim L46-47)
  6. 30-min watchdog → SCAN_SEPARATED suggestion (L49)
  7. 4-step completion handler: count → stderr → classify → Korean report (L50)
  8. screener_state.json atomic write (last_scan_date, last_results_summary)
  9. Disclaimer attached (session-first = full, subsequent = 1-line)
- **Output template**: output-templates.md §2 SHOW_RESULTS Korean template (Stage table + final list + Option (b) Type note + disclaimer)
- **R-9 lock pre-check**: §3 Chain 1 L43 — `${KRT_REPORTS}/filter-tune.lock` directory existence checked; refusal message verbatim
- **Verdict**: **PASS**

### Scenario 2 — SHOW_RESULTS canonical
- **Input**: `"오늘 결과 보여줘"`
- **Routing trace**: CLAUDE.md L20 (note: same Korean utterance also lives in SCAN_TODAY examples — but SHOW_RESULTS L22 covers `"오늘 결과 보여줘" / "통과 종목 알려줘" / "최종 선별 목록"`. Disambiguation: if scan-today result file exists for today, SHOW_RESULTS short-path applies; otherwise SCAN_TODAY) → stock-scan §3 Chain 4 (L72-75)
- **Chain steps**:
  1. Read `${KRT_REPORTS}/{date}/researchedCompany.md`
  2. Read 6× `stage*_passed.md`
  3. Compose Stage-by-Stage 통과/탈락률 table
  4. Type omission (Pre-Resolved Decision (b)) — attach Korean note `"* Type 상세는 Stage 1 재평가로 확인 가능"` (verbatim output-templates.md L48)
  5. >100 items → top 50 + full path note
  6. Disclaimer 1-line abbreviated (assuming not session-first)
- **Type omission verification**: SKILL.md L74 + output-templates.md L48 confirm Option (b) — rationale: stage1_passed.md stores stock-name only; re-derivation cost; ADR-010 doc-drift risk
- **Verdict**: **PASS**

### Scenario 3 — WHY_REJECTED chain
- **Input**: `"삼성전자가 왜 빠졌어?"`
- **Routing trace**: CLAUDE.md L23 → stock-scan §3 Chain 5 (L77-85)
- **Chain steps**:
  1. `Glob: ${KRT_REPORTS}/{date}/*삼성전자*/` — collection presence check
  2. **masterReference.md append: Edit only (NEVER Write)** — verbatim L79 ("사용자 큐레이션 보존, agent verification #9")
  3. `Bash(run_in_background:false): ${KRT_PYTHON} -m src.kiwoom.itemFilter.Filter_condition_update {date}` (~30s) — verbatim L81-83
  4. Read latest masterReference.log block via Grep
  5. Extract `### 삼성전자` subsection
  6. Stage 1-5 regex parse reason
  7. Emit Korean WHY_REJECTED template (output-templates.md §4)
- **Log rotation (B-5)**: `wc -l masterReference.log > 500` → `mv masterReference.log masterReference.log.{YYYYMM}` (L85 + output-templates.md L98)
- **NEVER Write rule**: verified at SKILL.md L79 and §10 self-check L207
- **Verdict**: **PASS**

### Scenario 4 — PG-2 PARAM_CHANGE happy path (paramount)
- **Input**: `"Type A 허용오차 -5%로 완화해줘"`
- **Routing trace**: CLAUDE.md L25 CHANGE_PARAM → filter-tune §3 Master Sequence (L43-222)

**8-step trace**:

- **Step 0 [TS-4] — Multi-param detection** (filter-tune §3 L47-59):
  - Input is single-param ("Type A 허용오차"). No conjunctions (`그리고/또/도/와/,`).
  - Result: NO multi-param → continue to Step 1.

- **Step 1.0 — Keyword pre-check** (L62-71):
  - Substrings scanned: `cup_nga`, `당기순이익`, `financeFilter`, `Stage 5`, `stage5`, `재무 단계`, `5단계`.
  - Input `"Type A 허용오차 -5%로 완화해줘"` → no Stage-5 keyword match.
  - Result: PASS through to Step 1.1.

- **Step 1.1 — Catalog resolution** (L73-74):
  - `references/parameter-catalog.md` Korean alias map: `"Type A 4선 정배열 허용오차"` ↔ `_TYPE_A_ALIGN_TOL`.
  - Live grep `chart60_120Filter.py:125` confirms `Final[float] = 0.035`.
  - Result: `param_id = _TYPE_A_ALIGN_TOL` resolved.

- **Step 1.2 — Stage 5 hard-block (secondary)** (L76-80):
  - File ownership check: `chart60_120Filter.py` ≠ `financeFilter.py`.
  - Result: PASS.

- **Step 1.3 — Range check** (L82-89, range-map.md L37):
  - `_TYPE_A_ALIGN_TOL` physical range: `0.000 ~ 0.500`, danger zone: `≥ 0.300`.
  - User intent `-5%` → unit-conversion (Step 6 §A): `-5% = tolerance 0.05`.
  - `0.05 ∈ [0.000, 0.500]` AND `0.05 < 0.300` → in-range, not danger.
  - Result: PASS, proceed to Step 2.

- **Step 2 [B-17] — Shared constant check** (L91-100, shared-constants.md L13):
  - shared-constants registry: only `_ALIGN_TOL_LOOSE` is shared. `_TYPE_A_ALIGN_TOL` is private.
  - Result: SKIP (SHORTCUT eligibility candidate — but Step 3 still runs silently to feed Step 4 appendix).

- **Step 3 [B-10] — masterReference.log gap analysis** (L102-108, ADR-009):
  - Pull `latest_date` from `screener_state.json.last_scan_date`.
  - `${KRT_REPORTS}/{latest_date}/masterReference.log` Read.
  - Regex catalogue `MA_ALIGNMENT` from tuning-sequence.md §D extracts `(actual, threshold, unit)` rows.
  - Recompute `would_pass` with new value `0.05` vs current `0.035`.
  - Korean line: `"masterReference.log {M}개 행 중 {N}개에서 gap 추출. 약 N개 추가 통과 예상 (추정 정확도 X%)."`

- **Step 4 [B-7] — Confirmation table + AskUserQuestion** (L110-124):
  - Verbatim Korean table:
    ```
    | 파라미터 | 현재 값 | 변경 후 |
    |---|---|---|
    | _TYPE_A_ALIGN_TOL (Type A 4선 정배열 허용오차) | -3.5% (×0.965, raw=0.035) | -5.0% (×0.95, raw=0.05) |
    ```
  - Display rule per unit-conversion.md: tolerance → raw + `-X.X% (×Y.YYY)`.
  - Appendix: shared warning skipped (private), Step 3 delta from masterReference.log.
  - AskUserQuestion 3 options: 적용 / 다른 값 / 취소.

- **Step 5 [TS-2, R-9] — mkdir lock + backup** (L126-156):
  - R-9 advisory lock acquire — atomic mkdir:
    ```bash
    if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then ... else BLOCKED; fi
    ```
    POSIX-atomic — exactly one process succeeds (EEXIST elsewhere).
  - Backup: `cp ${KRT_FILTERS}/chart60_120Filter.py ${KRT_FILTERS}/chart60_120Filter.py.bak.20260530_HHmmss`
  - Rotation: `ls -t *.bak.*` count ≤ 5 → no rotation.
  - State sync: `screener_state.current_backup_files` append (atomic tmp+mv).

- **Step 6 — Edit Final constant** (L158-170):
  - Pre-Edit grep: `grep -n '\b_TYPE_A_ALIGN_TOL\b' chart60_120Filter.py` → line 125 confirms `Final[float]`.
  - `old_string`: `_TYPE_A_ALIGN_TOL: Final[float] = 0.035`
  - `new_string`: `_TYPE_A_ALIGN_TOL: Final[float] = 0.05`
  - Comment auto-update (line above): `# 이전: 0.035 (변경: 2026-05-30)` idempotent update.

- **Step 7 [B-16] — tuning-log append + state + lock release** (L172-215):
  - 8-column row:
    ```
    | 2026-05-30T14:35:22+09:00 | _TYPE_A_ALIGN_TOL | Type A 4선 정배열 허용오차 | 0.035 | 0.05 | {count_before} | pending | Stage 1 통과율 완화 시도 | 미확정 |
    ```
  - Atomic `>>` append. Header pre-seeded if missing.
  - Rotation: `wc -l - header ≥ 200` → `mv tuning-log.md tuning-log.YYYYMM.md`.
  - state.json `last_param_changes` append with `confirmed=false`.
  - **Lock release**: `rmdir ${KRT_REPORTS}/filter-tune.lock` (try/finally semantic).

- **Step 8 [TS-5] — Rerun suggestion** (L217-222):
  - Verbatim: `"변경 적용됐습니다. 필터를 다시 돌려볼까요? (run_filters 동기 실행 — 보통 1-3분 소요)"`
  - Routing seam → stock-scan RERUN_FILTERS on `"네/응/해줘"`.

- **Verdict**: **PASS** — all 8 steps present, ordered correctly, mkdir Step 5 atomic (POSIX EEXIST semantics).

### Scenario 5 — Stage 5 hard-block (defence-in-depth)
- **Input variants**:
  - 5 (base): `"Stage 5 조건 바꿔줘"` → keyword `Stage 5` MATCH → **BLOCKED at Step 1.0 PRIMARY guard**.
  - 5a: `"당기순이익 임계값 -1로 바꿔"` → keyword `당기순이익` MATCH → **BLOCKED at Step 1.0 PRIMARY guard**.
  - 5b: `"cup_nga 조건 완화"` → substring `cup_nga` (case-insensitive) MATCH → **BLOCKED at Step 1.0 PRIMARY guard**.
  - 5c: `"financeFilter PER 조건"` → substring `financeFilter` (case-insensitive) MATCH → **BLOCKED at Step 1.0 PRIMARY guard**.

- **Verbatim C-4 rejection message** (L78):
  > `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. 당기순이익 판정(cup_nga < 0)이 하드코딩 비교문이고 Final 상수가 존재하지 않습니다. Phase 2에서 상수화를 검토합니다."`

- **All 4 variants short-circuit at Step 1.0 before catalog lookup** (rationale L71): financeFilter has zero Final constants → catalog fuzzy fallback could otherwise return a non-Stage5 false positive. Step 1.0 keyword pre-check is the PRIMARY guard.

- **Triple defence verification** (filter-tune §8 L410-414):
  1. §3 Step 1.0 — PRIMARY (keyword pre-check) ← 4/4 variants caught HERE
  2. §3 Step 1.2 — SECONDARY (catalog file-ownership check)
  3. §4 Branch 1 SHOW_PARAMS Step 1.5 — change-intent + Stage 5 word
  4. §4 Branch 6 ASK_MODULE `financeFilter.py` row (`⚠️ Phase 2 (hardcoded, no Final)`)

- **Verdict**: **PASS** — 4/4 variants blocked at PRIMARY guard; secondary/tertiary defences exist as defence-in-depth.

### Scenario 6 — Shared constant impact (B-17)
- **Input**: `"_ALIGN_TOL_LOOSE를 0.02로 바꿔"`
- **Step 1.0**: no Stage 5 keyword → PASS.
- **Step 1.2**: `_ALIGN_TOL_LOOSE` owner = `chart60_120Filter.py:120` (NOT financeFilter) → PASS.
- **Step 1.3 Range check** (range-map.md L36): `_ALIGN_TOL_LOOSE` physical range `0.000 ~ 0.300`, danger zone `≥ 0.150`. `0.02 ∈ [0.000, 0.300]` AND `0.02 < 0.150` → in-range, not danger.
- **Step 2 [B-17] — Shared constant impact** (shared-constants.md L13-32):
  - Registry confirms `_ALIGN_TOL_LOOSE` is the **single active shared constant**.
  - Verbatim influence list emitted:
    > `"⚠️ 이 상수는 공유 상수입니다. 변경 시 다음 조건들이 동시에 영향을 받습니다:`
    > ` • Type B — 120분 MA10-MA20 근접 판정`
    > ` • Type B — MA60-MA306 근접 판정`
    > ` • Type C — MA60-MA306 장기추세 leg`
    > ` • Type D — 60분 4선 정배열 fallback`
    > `특정 Type만 조정하려면 해당 Type 전용 상수 신설이 필요합니다 (TS-1 로직 변경 — 사용자 명시적 승인 필요)."`
- **Scope distinction** (shared-constants.md L40-55, Pair 1):
  - `_ALIGN_TOL_LOOSE` (chart60_120Filter.py:120, value 0.015) ≠ `_MA_ALIGNMENT_TOLERANCE` (chart60Filter.py:75, value 0.005).
  - The latter is standalone module, NOT in main pipeline; no cross-stage propagation.
  - Disambiguation question available for ambiguous Korean: `"두 가지 다른 변수가 있습니다: (1) chart60_120Filter의 Type B/C/D 공유 허용오차 (-1.5%) vs (2) chart60Filter 단독 모듈 4선 정배열 (-0.5%). 어느 쪽을 변경할까요?"`
- **Step 4** enhanced confirmation table embeds the Step 2 warning (collapsed re-emit per L122).
- **Verdict**: **PASS**

### Scenario 7 — RESTORE branch (B-8 fallback)
- **Input**: `"원래대로 되돌려줘"`
- **Routing trace**: CLAUDE.md L27 → filter-tune §4 Branch 4 (L276-298).

- **Step 1 — Target file resolution** (L278):
  - Korean utterance has no file hint → AskUserQuestion top-3 most recent `last_param_changes` candidates.
  - Assume user picks `chart60_120Filter.py`.

- **Step 2a — Primary (.bak glob)** (L280-284):
  ```bash
  ls -t ${KRT_FILTERS}/chart60_120Filter.py.bak.* 2>/dev/null | head -1
  ```
  - non-empty → AskUserQuestion `"가장 최근 백업({backup_path})에서 복원합니다. 진행할까요?"`
  - User says 예 → **R-9 lock acquire (mkdir, atomic)** → **try { cp backup → file; tuning-log RESTORE row append (`notes: "복원 (from {bak}) | ✓ 복원"`); state.json append (`confirmed=true`) } finally { rmdir lock — ALWAYS attempt — stuck lock prevention (Step10-W4 fix) }**.
  - Korean ack: `"{file_basename}을 {backup_timestamp} 시점 백업으로 복원했습니다."`

- **Step 2b — Fallback (B-8 KEY FEATURE)** (L286-296):
  - .bak absent (rotation / manual delete / never created) → activate fallback.
  - Algorithm:
    1. Read `tuning-log.md` + all `tuning-log.YYYYMM.md` archives (oldest-first).
    2. Filter rows matching `param_id`.
    3. Last row's `old_value` = restore target.
    4. B-13e variable-name check.
    5. AskUserQuestion: `"⚠️ 백업 파일이 없어 튜닝 로그에서 이전 값을 찾았습니다: {old_value_in_log}. Edit으로 직접 복원할까요? (.bak 파일이 없으므로 다시 변경하면 이 단계 이전 값으로는 돌아갈 수 없습니다.)"`
    6. On proceed: **R-9 lock acquire → try { Edit Final constant; RESTORE row append; state.json update } finally { rmdir lock ALWAYS — Edit failure also triggers lock release (Step10-W4 fix verified L293) }**.
    7. Korean fallback ack: `"백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다. ({param_id}: {current_was} → {restored_to})"`
    8. RESTORE row notes: `"로그 기반 복원 (백업 부재) | ✓ 복원"`.

- **Step 2c — Both fail** (L298): PRD §5.1 catalog value as last-resort `new_value` → Master Sequence Steps 0-8.

- **try/finally verification**:
  - L284 (Step 2a): `"try { ... } finally { rmdir ${KRT_REPORTS}/filter-tune.lock 항상 시도 — stuck lock 방지 (Step10-W4 fix) }"`
  - L293 (Step 2b): `"try { ... } finally { rmdir ${KRT_REPORTS}/filter-tune.lock 항상 시도 — Edit 실패 시에도 stuck lock 방지 (Step10-W4 fix) }"`

- **Verdict**: **PASS** — both branches have explicit try/finally semantic; Step10-W4 fix confirmed.

### Scenario 8 — Mixed intent (CLAUDE.md sequential rule)
- **Input**: `"필터 바꾸고 다시 돌려줘"`
- **CLAUDE.md L34-37 verbatim**:
  > Mixed-intent rule (mandatory): `"필터 바꾸고 다시 돌려줘"` → sequential routing:
  > 1. filter-tune `CHANGE_PARAM` (Master Sequence 완료까지)
  > 2. 사용자 확인 후 stock-scan `RERUN_FILTERS`
  > Pattern 인식: `(CHANGE|바꿔|완화|강화|조정).*(다시|재실행|돌려|돌리)` → split into 2 sequential calls, never merge into single skill invocation.
- **Regex test**:
  - `"필터 바꾸고 다시 돌려줘"` → captures `바꾸` (alternation `바꿔` partial-match — note CLAUDE.md uses `바꿔` literal which matches `바꾸` stem in Korean morphology if regex tolerant; otherwise the broader pattern `(CHANGE|바꿔|완화|강화|조정)` should accept `바꾸고` because regex matches substring `바꿔` only if exactly that form occurs).
  - **Advisory finding**: the literal regex `바꿔` may fail to match `바꾸고` morphology. This is a known stem-matching nuance. In practice, both skills' SKILL.md L28 / L27 also reference the rule, and runtime LLM-based intent classification likely tolerates this. **For Step 12 review**: consider broadening regex to `바꾸|바꿔|변경` for robustness. (Logged in §8 as advisory item.)
- **Both skills explicitly state**:
  - stock-scan §1 L28: `"필터 바꾸고 다시 돌려줘" → filter-tune CHANGE_PARAM 선행 → 사용자 확인 후 stock-scan RERUN_FILTERS`
  - filter-tune §1 L27: same verbatim
- **Sequencing**: Step 8 of filter-tune Master Sequence (L217-222) emits `"변경 적용됐습니다. 필터를 다시 돌려볼까요?"` → CLAUDE.md routing dispatches `"네/응/해줘"` to stock-scan RERUN_FILTERS Chain 8.
- **Never-merge invariant**: filter-tune §2 L41 explicitly forbids Python execution within filter-tune; stock-scan §11 (TS rules N/A) forbids parameter modification.
- **Verdict**: **PASS** (with advisory on regex morphology).

### Scenario 9 — Error handling (KiwoomApiError)
- **Input**: background scan emits `KiwoomApiError(code="HTTP")` → exit code 2 + stderr containing class name.
- **CLAUDE.md Error Classification §** (L50-68):
  - **L52 verbatim**: `"분기 기준 (필수): type(exc).__name__ STRING 비교. isinstance(exc, KiwoomApiError)는 절대 사용 금지 — KiwoomApiError는 8개 모듈에 독립 정의된 동명 클래스이므로 어느 한 import로 catch하면 7개를 놓친다. (ADR-011)"`
  - **L58 row**:
    | `KiwoomApiError` | 키움 데이터 조회에 실패했습니다. | REST API 호출 실패 (HTTP, JSON, return_code≠0, 재시도 초과). 8개 모듈 독립 정의 — 이름 기준 분기 필수. | 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. |
- **Wrapping note** (L67): `httpx.HTTPError` (ConnectError/TimeoutException) → auto-wrapped to `KiwoomApiError(code="HTTP")` or `KiwoomAuthError`; surface 9 classes only.
- **Jargon-free verification** (L78 — Step 1 §Style Guide (d)): forbidden tokens `return_code, HTTPError, JSON 스키마, ka10171, stage_idx`; user action `"잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요."` is **jargon-free** (no Python class name, no exit code, no traceback) — post Step 10 W4 fix confirmed.
- **Output pattern** (L53): Korean 한 문장 요약 + 원인 + 사용자 행동. raw stderr/exit code/traceback under `기술 정보:` label (collapsed).
- **stock-scan §6 pseudocode** (L137-149) confirms ADR-011 STRING-dispatch implementation.
- **Verdict**: **PASS**

### Scenario 10 — R-9 lock contention
- **Scenario**: stock-scan SCAN_TODAY invoked while filter-tune is mid-Edit (between Step 5 mkdir and Step 7 rmdir).
- **stock-scan side** (refusal verification):
  - §3 Chain 1 L43: `"사전점검: §4의 (a)(b)(c) + ${KRT_REPORTS}/filter-tune.lock 존재 시 거부 (R-9 — 한국어 메시지: '파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요.')"`
  - §9 L196: `"암묵적 락 인지 (R-9): 모든 실행 체인(1/2/3/8)은 Bash 실행 전 ${KRT_REPORTS}/filter-tune.lock 존재 확인. 있으면 거부 ... stock-scan은 락을 생성·해제하지 않는다."`
  - execution-chains.md L18: same verbatim refusal message.
- **filter-tune side** (acquire + release verification):
  - §3 Step 5 L130-140: `if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then ... else BLOCKED; exit 2; fi` — POSIX atomic; one winner.
  - §3 Step 7 L215: `rmdir ${KRT_REPORTS}/filter-tune.lock` — try/finally semantic. "Step 7 어느 substep이 실패해도 락 해제는 시도 (stuck lock 방지)."
  - §6 L387: lock semantics summary explicit; stock-scan refusal message verbatim copy of Chain 1 message.
- **Symmetry check**: mkdir (directory creation) ↔ rmdir (directory removal). Both are atomic POSIX ops on a directory sentinel (NOT a file). Cross-process semantics: any process attempting mkdir on existing dir gets EEXIST.
- **Korean refusal message exact form**:
  > `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`
  (without leading ⚠️ in stock-scan Chain 1 message, with leading ⚠️ in filter-tune Step 5 BLOCKED variant L139 `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."`)
- **Advisory finding**: The two BLOCKED messages are slightly different (refusal vs contention). Both Korean, jargon-free, but if symmetric UX is desired Step 12 may choose to unify. Logged in §8.
- **Verdict**: **PASS** (lock semantics correct; small wording divergence is acceptable but advisory).

---

## §5. Stage 5 Hard-Block — 4-Variant Defence Trace

Detailed trace of variants against filter-tune §3 Step 1.0 trigger conditions:

| Variant | Input | Step 1.0 keyword match | Block path | Korean message |
|---|---|---|---|---|
| 5 (base) | "Stage 5 조건 바꿔줘" | `Stage 5` substring | PRIMARY (Step 1.0) | C-4 verbatim L78 |
| 5a | "당기순이익 임계값 -1로 바꿔" | `당기순이익` substring | PRIMARY (Step 1.0) | C-4 verbatim L78 |
| 5b | "cup_nga 조건 완화" | `cup_nga` substring (case-insensitive) | PRIMARY (Step 1.0) | C-4 verbatim L78 |
| 5c | "financeFilter PER 조건" | `financeFilter` substring (case-insensitive) | PRIMARY (Step 1.0) | C-4 verbatim L78 |

**Why PRIMARY > SECONDARY**:
- financeFilter.py has zero Final constants (PRD §5.1 + workflow.md L286).
- If Step 1.0 were absent, Step 1.1 catalog lookup would search for non-existent param_ids, possibly returning a fuzzy fallback Korean alias from another stage → user could unwittingly accept a wrong-stage change.
- Step 1.0 keyword pre-check intercepts BEFORE catalog → fail-safe.

**Defence-in-depth fan-out** (§8 L410-414):
1. §3 Step 1.0 — PRIMARY (PARAM_CHANGE keyword pre-check) ← all variants caught here
2. §3 Step 1.2 — SECONDARY (PARAM_CHANGE catalog file-ownership check, would still catch if Step 1.0 missed)
3. §4 Branch 1 SHOW_PARAMS Step 1.5 — change-intent + Stage 5 word in SHOW_PARAMS path
4. §4 Branch 6 ASK_MODULE — `financeFilter.py` row marked `⚠️ Phase 2 (hardcoded, no Final constant)`

**Verdict**: 4/4 PRIMARY catches, 4 defence layers total — strong hard-block.

---

## §6. Backup / Lock Protocol Verification

### Backup naming convention
- Format: `{file}.bak.YYYYMMDD_HHmmss` (verified in filter-tune §3 Step 5 L144 + §6 L381)
- Example: `chart60_120Filter.py.bak.20260530_142345`
- Mandatory for `ls -t` chronological ordering AND join with tuning-log timestamps.

### Rotation (TS-2a)
- Cap: ≤ 5 backups per file.
- 6th creation → oldest deleted **only after** tuning-log gate check (`grep -l '{oldest_ts}' tuning-log.md tuning-log.*.md`).
  - Match found → `rm {oldest}`.
  - Match absent → KEEP + Korean warning `"백업 {N}개 한도를 초과했지만 가장 오래된 백업이 튜닝 로그에 기록되지 않아 보존합니다. 수동 정리를 권장합니다."` (filter-tune §3 L154, PRD line 442 gate).
- Sequence: state.json `current_backup_files` field updated atomically (tmp + mv).

### Lock semantics (R-9)
- **Type**: directory sentinel (NOT file) → enables atomic POSIX mkdir.
- **Acquire**: filter-tune §3 Step 5 L128-138:
  ```bash
  if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then proceed; else BLOCKED exit 2; fi
  ```
- **Release**: filter-tune §3 Step 7 L215 + RESTORE Step 2a L284 + Step 2b L293:
  ```bash
  rmdir ${KRT_REPORTS}/filter-tune.lock
  ```
- **try/finally invariant**: All three release sites wrap mutations in try/finally — rmdir always attempted regardless of Edit/cp success or failure. **Step10-W4 fix verified.**
- **stock-scan side** (consumer): Bash pre-check on `test -d ${KRT_REPORTS}/filter-tune.lock` → refusal Korean message (no create/delete from stock-scan side; §9 L196).

**Verdict**: PASS. mkdir atomic; rmdir always attempted; cross-skill cooperation explicit.

---

## §7. screener_state.json Lifecycle

### New user (file absent)
- Pre-flight (a)(b)(c) → capabilities intro 3 lines:
  - (i) `"오늘 종목 스캔해줘"`로 5-Stage 필터링 실행
  - (ii) `"Stage 1 조건 보여줘"`로 파라미터 조회
  - (iii) `"OO전자 왜 빠졌어?"`로 탈락 분석
- First-execution prompt: `"오늘 한 번 스캔해볼까요? (약 10-15분 소요됩니다.)"`
- After first SCAN_TODAY completion: 1-time results-interpretation guide (Stage table + 1-2 example stocks).

### Returning user (file present) — current smoke-test state
- File observed: `/Users/tajun/spJavis/kiwoom-rest-trader/reports/screener_state.json`, 427 bytes, mtime May 30 14:18.
- Read `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`.
- Emit 2-3 line Korean session summary per CLAUDE.md L104:
  `"지난 스캔: {last_scan_date}. 변경 이력: {N}건 ({param} 등). 무엇을 도와드릴까요?"`
- External-change detection (B-12, CLAUDE.md L118-120): for each `confirmed=false` entry, `grep -n '{param}.*Final' {file}` → compare to `recorded.new`. Mismatch → warning + user choice (a) accept as new baseline / (b) restore from .bak.

### Atomic write
- Convention: `json.dump(state, tmp); mv tmp final` (Step 4 §4 atomicity note).
- Single-threaded Claude Code assumption → no file lock for state.json (lock only for cross-skill filter-tune mutation phase).

### JSON corruption handling (R-7)
- `json.JSONDecodeError` caught → `screener_state.json.corrupt.{ts}` backup → fallback to new-user flow.
- filter-tune §9 R-7 row: default empty array.

### Cross-skill writer boundary
- `last_param_changes` and `current_backup_files`: **filter-tune SOLE writer**, stock-scan READ-only.
- `last_scan_date` and `last_results_summary`: stock-scan writes (Chains 1/2/3/8), filter-tune reads only (Step 3 gap analysis baseline).

**Verdict**: PASS. Lifecycle covers new-user, returning-user, corruption, and cross-skill boundary cases.

---

## §8. Known Limitations (for Step 12 human review)

Items the DRY-RUN smoke test cannot verify without actual runtime:

1. **Real Bash background process orphan cleanup after 30-min watchdog**: The 30-min watchdog (Chain 1 Step 6) emits Korean fallback `"실행이 예상보다 길어지고 있습니다..."` and offers SCAN_SEPARATED pivot, but **the original background process is NOT killed automatically** (background-execution.md §3 line "백그라운드 process는 별도로 계속 진행 중일 수 있음을 사용자에게 알림"). Risk: zombie process + duplicate scan output overwrite if user accepts pivot AND original eventually completes. Recommend Step 12: design explicit `kill -TERM` policy or explicit user prompt.

2. **Concurrent multi-Claude-instance lock race**: mkdir is atomic **per-FS inode** on POSIX. On networked filesystems (NFS/SMB) or across two Claude Code instances on the same machine, the EEXIST guarantee holds for local FS but cross-machine semantics for `${KRT_REPORTS}` are not specified. Smoke-test cannot simulate two simultaneous filter-tune Edits.

3. **`prefetchManifest.json` schema variations across kiwoom-rest-trader version history**: Chain 8 RERUN_FILTERS Step (d) pre-check assumes the manifest has `by_stock` dict with sentinel values in `{"ok", "empty", "null", null, ""}`. Historical reports (e.g. 20260510.zip) may have different schemas — sentinel set may evolve. Recommend Step 12: verify against actual recent report.

4. **Mixed-intent regex morphology** (advisory from Scenario 8): the literal `바꿔` token in CLAUDE.md L37 regex may miss `바꾸고/바꾸어/바꿔서` morphological variants. Korean stem is `바꾸-` → `바꾸/바꿔/바꾸어/바꾸고` are all valid surface forms of the same verb. The LLM-mediated intent classification may compensate at runtime, but pure regex test would fail on `바꾸고`. Recommend broader pattern: `(바꾸|바꿔|변경|수정).*`.

5. **R-9 BLOCKED wording asymmetry** (advisory from Scenario 10): stock-scan refusal `"파라미터 변경 중이라 스캔을 시작할 수 없습니다..."` vs filter-tune contention `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다..."`. Both are jargon-free Korean; difference is intentional (scan-side vs change-side perspectives). Step 12 may choose to unify if symmetric UX is preferred.

6. **stock-scan Chain 8 cross-write of `stocks_passed_after`**: filter-tune §3 Step 7 L186 declares `stocks_passed_after` is `pending` at write-time and to be cross-written by stock-scan on next RERUN_FILTERS. stock-scan §3 Chain 8 references RERUN_FILTERS but the explicit Edit-back-into-tuning-log step is not visible in stock-scan SKILL.md — needs verification in `execution-chains.md` Chain 8 detail (not fully read in this smoke-test). Recommend Step 12: explicit trace of this cross-skill writer handshake.

---

## §9. Verification Self-Check

- [x] 10 scenarios all traced (§4 covers each individually).
- [x] Stage 5 4-variant defence confirmed (§5 — all PRIMARY at Step 1.0).
- [x] Pre-flight (a)(b)(c) dry-run results captured (§1).
- [x] R-9 lock semantics verified in both Skills (§6 + Scenario 10).
- [x] Backup convention `*.bak.YYYYMMDD_HHmmss` verified (§6).
- [x] No actual pipeline executed (`run_full_research_flow`, `run_prefetch`, `run_filters` never invoked — only static SKILL.md reading + read-only bash).
- [x] No deployed file modified (Edit/Write never invoked on `/Users/tajun/spJavis/kiwoom-rest-trader/`; only Read + Bash read-only commands).
- [x] Known limitations list ≥3 items (§8 has 6 items).
- [x] CLAUDE.md size unchanged: 14,730 bytes (matches post-Step-10 expected size).
- [x] settings.local.json mtime unchanged: May 13 19:46:18 2026.
- [x] ADR-011 (`type(exc).__name__` STRING dispatch) verbatim in CLAUDE.md L52 + stock-scan §6 pseudocode.
- [x] ADR-012 (`Bash(run_in_background:true)` mandate) verbatim in CLAUDE.md L13/L20 + stock-scan §3 Chain 1 L46-47.
- [x] Type omission (Pre-Resolved Decision Option (b)) verbatim Korean in output-templates.md L48.
- [x] try/finally rmdir in BOTH RESTORE Step 2a (L284) and Step 2b (L293) — Step10-W4 fix.

---

## Appendix A — Read-Only Mode Final Verification

Post-smoke-test verification confirming no mutation occurred on the deployed system:

| File | Pre-test state | Post-test state | Same? |
|---|---|---|---|
| `${KRT_ROOT}/CLAUDE.md` size | 14,730 bytes | 14,730 bytes | YES |
| `${KRT_ROOT}/.claude/settings.local.json` mtime | May 13 19:46:18 2026 | May 13 19:46:18 2026 | YES |
| `${KRT_REPORTS}/screener_state.json` mtime | May 30 14:18 | May 30 14:18 | YES |
| `${KRT_REPORTS}/filter-tune.lock` | absent | absent | YES |
| `${KRT_REPORTS}/` listing | 20260510.zip, 20260512.zip, ..., 20260519 | same | YES |

**READ-ONLY mode preserved**. All commands executed: `test`, `ls`, `wc`, `stat`, `head`, `grep`, plus Read tool. No `Edit`, `Write`, `mkdir`, `cp`, `mv`, or pipeline invocations.
