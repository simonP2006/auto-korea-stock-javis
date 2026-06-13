# Step 6 — stock-scan SKILL Blueprint

> Generated: 2026-05-30
> Target deployment: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/`
> Created by Step 9 `@scan-builder` from this blueprint
> Skill covers: PG-1 (screener execution chains)
> Sources: workflow.md §6 (`@scan-designer` task), Step 2 research report, Step 4 architecture (paths, schema, OQ-3/ADR-011/ADR-012, 11 risks), Step 5 CLAUDE.md blueprint (§3 intent table, §5 error table), Step 1 error patterns + pipeline analysis, PRD FR-1/FR-2/FR-4/B-5/B-11/B-13/B-24

---

## §1. SKILL.md Header & Trigger Conditions

**(spec)** — frontmatter (verbatim):

```yaml
---
name: stock-scan
description: Kiwoom REST API 종목 스크리너 — 스캔 실행·결과 해석·탈락 분석·비교를 한국어 자연어로 수행. PG-1(screener execution chains) 전담. Trigger: SCAN_TODAY, SCAN_SEPARATED, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, COMPARE, COMPARE_PARAMS, RERUN_FILTERS.
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
maxTurns: 80
---
```

**Rationale** for tool selection:
- `Bash` — mandatory for `run_full_research_flow` / `run_prefetch` / `run_filters` / `Filter_condition_update` / `test -d` pre-flight (a)(c).
- `Read` — `researchedCompany.md`, `stage*_passed.md`, `masterReference.log`, `prefetchManifest.json`, `screener_state.json`, `tuning-log.md`.
- `Glob` — `reports/{date}/*{stock_name}*/` for WHY_REJECTED stock-folder discovery (B-5 §6.5).
- `Grep` — masterReference.log block extraction by stamp, parameter-value cross-check.
- `Edit` — `masterReference.md` append (per agent verification #9 — Edit only, never Write, to preserve any user-curated lines).
- `Write` — `screener_state.json` atomic write (`json.dump(tmp); mv tmp final`).
- `AskUserQuestion` — split-mode prompt ("필터를 실행할까요?"), date disambiguation, post-prefetch handoff (PRD P4: max 1 question, ≤ 3 options).

`maxTurns: 80` headroom accommodates SCAN_RANGE 5-day loop × 4-step completion handler + per-stock WHY_REJECTED inside the same session.

**Trigger via CLAUDE.md intent table** (cross-reference Step 5 blueprint §3 — verbatim cluster names):

| CLAUDE.md cluster | → stock-scan action |
|---|---|
| `SCAN_TODAY` | Chain 1 — `scan_today(date?)` |
| `SCAN_SEPARATED` (triggered by "나눠서 해줘"/"단계별로 해줘") | Chain 2 — `scan_separated(date)` |
| `SCAN_RANGE` | Chain 3 — `scan_range(start, end)` |
| `SHOW_RESULTS` | Chain 4 — `show_results(date)` |
| `WHY_REJECTED` | Chain 5 — `why_rejected(stock_name, date)` |
| `COMPARE` | Chain 6 — `compare(date_a, date_b)` |
| `COMPARE_PARAMS` | Chain 7 — `compare_params(before_run, after_run)` |
| `RERUN_FILTERS` | Chain 8 — `rerun_filters(date)` |

Mixed-intent ("필터 바꾸고 다시 돌려줘"): per Step 5 §3 mixed-intent rule, the **filter-tune** Skill executes `CHANGE_PARAM` first; stock-scan picks up `RERUN_FILTERS` only after the user confirms. stock-scan never owns parameter mutation.

---

## §2. Path Constants Reference

Inherit verbatim from Step 4 architecture §1 + Step 5 blueprint §2. **Do NOT redefine** in SKILL.md — refer via the canonical names:

- `${KRT_ROOT}` = `/Users/tajun/spJavis/kiwoom-rest-trader`
- `${KRT_PYTHON}` = `${KRT_ROOT}/.venv/bin/python` (Python 3.12.7 verified)
- `${KRT_REPORTS}` = `${KRT_ROOT}/reports`
- `${KRT_FILTERS}` = `${KRT_ROOT}/src/kiwoom/itemFilter`
- `${KRT_SCRIPTS}` = `${KRT_ROOT}/scripts`
- `EXEC_PATTERN` = `cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}`
- `RUN_IN_BACKGROUND = true` mandatory for `run_full_research_flow` + `run_prefetch` (ADR-012)

Forbidden form (D-7 / ADR-007): `source .venv/bin/activate && python …`. Always use `.venv/bin/python` direct path.

---

## §3. 8 Execution Chains

Each chain encodes: **Trigger → Inputs → Pre-condition checks → Numbered steps (with Bash command) → Checkpoints → Output (Korean) → Failure recovery → Retry budget**. Korean strings preserved verbatim from PRD + Step 5 §6.

### Chain 1 — `SCAN_TODAY(date?)`

- **Trigger intent**: SCAN_TODAY (utterances: "오늘 종목 스캔해줘" / "오늘 결과 보여줘" / "오늘 돌려줘" / "{YYYYMMDD} 스캔")
- **Default action**: `run_full_research_flow` (D-2 / ADR-012, PRD FR-1.1)
- **Inputs**: `date` (default = `$(date +%Y%m%d)` KST). Format guard: 8-digit numeric.
- **Pre-condition checks**: session-start (a)(b)(c) per §4. First Bash exec of session: full execution probe (R-11 / Step 4 §3 permission caveat). Lock check: refuse if `${KRT_REPORTS}/filter-tune.lock` exists (R-9) → Korean message `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`
- **Background execution mandate (ADR-012)**: `Bash(run_in_background: true)` — **required** (10-15 min real runtime vs 600s Bash cap).

**Steps**:

1. Validate `date` format (`^[0-9]{8}$`). Invalid → Korean `"날짜 형식이 올바르지 않습니다 (YYYYMMDD). 예: 20260530"`.
2. Verify date is not in the future (`date_int <= today_int`). Future → confirmation prompt.
3. Read `${KRT_REPORTS}/screener_state.json`. If `last_results_summary.scan_date == date && last_scan_date == date` → ask "이미 스캔된 결과가 있습니다. 다시 실행할까요?" (cache hit shortcut option = SHOW_RESULTS).
4. Announce expected duration (verbatim Step 4 §7 / ADR-012):
   ```
   약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다.
   ```
5. Execute:
   ```
   Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_full_research_flow {date}
   ```
6. **30-min watchdog**: if no completion notification within 30 minutes → Korean fallback `"실행이 예상보다 길어지고 있습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?"` + offer `scan_separated({date})`.
7. **On completion notification — 4-step completion handler** (PRD B-4 + Step 5 §5):
   - (1) **Extract stock count** from stdout: parse the final-stage line emitted by `save_researched_company` (typically `"researchedCompany.md: N종목 저장"`); fallback = `wc -l < researchedCompany.md`.
   - (2) **Check stderr** for any traceback / `Exception: …`. Non-empty stderr + exit ≠ 0 → branch to error path.
   - (3) **Apply error classification** (Step 5 §5 table — dispatch on `type(exc).__name__` STRING; never `isinstance` per OQ-3 / ADR-011). See §6.
   - (4) **Emit Korean Stage-by-Stage report** (template in §5).
8. **Write screener_state.json**: update `last_scan_date={date}`, `last_results_summary={scan_date, passed_count, by_stage}`. Atomic write (`json.dump(tmp); mv tmp final`).
9. Append disclaimer (full first emission of session, abbreviated thereafter — PRD B-23 / FR-8).

**Checkpoints**:
- Exit code ≠ 0 → §6 error classification (exit 1 = domain input-absence; exit 2 = everything else).
- File `${KRT_REPORTS}/{date}/researchedCompany.md` absent post-run → "결과 파일이 생성되지 않았습니다 — 파이프라인이 중간 단계에서 종료되었을 수 있습니다. 기술 정보: stderr 마지막 줄 첨부."

**Output format**: Korean Stage-by-Stage table + final list + disclaimer (see §5 SHOW_RESULTS template).

**Failure recovery**:
- Background watchdog timeout → suggest SCAN_SEPARATED.
- `KiwoomAuthError` / `KiwoomApiError` → user retries after env/network check; same chain re-invocation allowed.
- `OrganizeError` / `PrefetchError` → guidance to run an upstream stage; do NOT auto-pivot without confirmation.

**Retry budget** (ADR-012 + agent verification #10):
- Same error type observed twice consecutively → stop + Korean explanation: `"동일 오류가 2회 반복되었습니다. 추가 시도를 중단합니다. 원인: {cause}. 조치: {action}."` No infinite retry.

---

### Chain 2 — `SCAN_SEPARATED(date)`

- **Trigger intent**: B-11 split mode ("나눠서 해줘" / "단계별로 해줘" / "분리해서 실행").
- **Inputs**: `date`. Same date validation as Chain 1.
- **Pre-condition**: same as Chain 1 + filter-tune lock check.

**Steps**:

1. Validate date (Chain 1 Steps 1-2).
2. Announce: `"먼저 데이터 수집(prefetch)을 시작합니다. 약 10-15분 소요됩니다."`
3. Execute step 1 — prefetch:
   ```
   Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_prefetch {date}
   ```
4. **30-min watchdog** (same as Chain 1). On completion: 4-step handler — extract stocks-prefetched count from `prefetchManifest.json` (`len(by_stock)`) + error count (entries where value ∉ {`"ok"`,`"empty"`,`"null"`,`null`,`""`}).
5. Emit Korean prefetch stats report (B-11 verbatim format in §5).
6. AskUserQuestion (single question, 2 options): `"필터를 실행할까요?"` options = ["네, 지금 필터 실행", "잠시 후 직접 실행"].
7. If user confirms → step 2 — **synchronous** filter execution:
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}
   ```
   (typically < 3 min, comfortably inside 600s Bash cap — no background needed.)
8. On exit 0 → Stage-by-Stage report (same template as Chain 1 §5). On exit ≠ 0 → §6 dispatch.
9. Update screener_state.json. Disclaimer.

**Checkpoint**: `prefetchManifest.json` absent after Step 4 → manifest-generation failure; report `"prefetchManifest.json 이 생성되지 않았습니다. Stage 0 prefetch 가 실패한 것으로 보입니다."` + stderr tail.

**Retry budget**: same-error 2× → stop. If prefetch succeeds but filters fail, the prefetch artifacts persist — user can retry filters alone via Chain 8 (RERUN_FILTERS) without re-paying the 10-15 min cost.

---

### Chain 3 — `SCAN_RANGE(start, end)`

- **Trigger intent**: SCAN_RANGE ("이번 주 월~금 전부" / "{start}부터 {end}까지 스캔").
- **Inputs**: `start`, `end` YYYYMMDD. Constraint: `start <= end`, max 31 calendar days.

**Steps**:

1. Generate business day list:
   - Bash: enumerate dates `start..end`, exclude weekday `Sat`/`Sun` via `date +%u` (`6` / `7`).
   - **KR holiday handling**: no holiday data hard-coded (PRD B-15, Step 5 §7). Emit warning: `"⚠️ 주의: 한국 공휴일은 자동으로 제외되지 않습니다. 결과 폴더가 비어있다면 휴장일일 수 있습니다."`
2. Confirm count: `"총 {N}영업일 스캔 예정 (예상 소요: ~{N*15}분). 진행할까요?"` AskUserQuestion options: ["네, 전부 실행", "취소"].
3. Loop over business days. For each day `d_i`:
   - Invoke Chain 1 (SCAN_TODAY) inline with `date=d_i`.
   - On completion emit progress: `"{i}/{N}일 완료 — {d_i}: {count}종목 통과"`.
   - On error: log error and ask user `"{d_i} 에서 오류 발생. 나머지 영업일을 계속할까요?"` (continue / abort).
4. Aggregate results (B-24):
   - Compute per-day counts + union (any-day pass) + intersection (all-day pass).
   - Emit Korean summary table (§5 SCAN_RANGE template).
5. Update screener_state.json with the **last** date's summary (Chain 1 already did this per-day).

**Checkpoint**: if more than 50% of days error out, abort the loop after the 2nd consecutive failure → Korean fallback `"연속 오류로 범위 스캔을 중단했습니다."`

**Retry budget**: no per-day retry inside the loop (the user decides via the continue/abort question). Same-error 2× → stop the range scan entirely.

---

### Chain 4 — `SHOW_RESULTS(date)`

- **Trigger intent**: SHOW_RESULTS ("오늘 결과 보여줘" / "통과 종목 알려줘" / "최종 선별 목록").
- **Inputs**: `date` (default = `last_scan_date` from screener_state.json; if still null → AskUserQuestion).
- **Pre-condition (d)**: prefetchManifest.json sanity check (Step 4 §5). If `${KRT_REPORTS}/{date}/` absent → `"{date} 결과가 없습니다. 스캔을 먼저 실행할까요?"` + offer SCAN_TODAY.

**Steps**:

1. Read `${KRT_REPORTS}/{date}/researchedCompany.md` — **canonical SHOW_RESULTS file** (Step 1 pipeline-analysis §(b) line 289-298: 5 grounds incl. only file both `run_full_research_flow` and `run_filters` produce; `Filter_condition_update` references it explicitly via `_RESEARCHED_MD`).
2. Read each stage file:
   - `stage1_chart60_120_passed.md`
   - `stage2_chart240_passed.md`
   - `stage2_1_chartDayPre_passed.md`
   - `stage3_chartDay_passed.md`
   - `stage4_investor_passed.md`
   - `stage5_finance_passed.md`
   For each: count `wc -l` (each file is line-per-stk_nm, UTF-8 LF, trailing newline, 0-byte if empty per Step 2 §5 C-6-2).
3. Compute drop-off rate per stage: `dropout_rate = 1 - (output / input)`. Stage 1 input ≈ size of `organizedCompany.md` (Read for accurate denominator) — fallback to `"-"` if absent.
4. Emit Korean table (§5 SHOW_RESULTS template):
   ```
   | Stage | 입력 | 통과 | 탈락률 |
   ```
5. Emit final passed-list (종목명 only, one per line). If `>100` → show first 50 + `"... 외 {N}종목 (전체 목록: ${KRT_REPORTS}/{date}/researchedCompany.md)"`.

**Pre-Resolved Decision — Type pattern in SHOW_RESULTS: Option (b)** (do not deviate).

- **Decision**: omit Type A~E pattern info from SHOW_RESULTS output. Append note: `"* Type 상세는 Stage 1 재평가로 확인 가능"`.
- **Rationale** (verbatim from caller spec + Step 2 §3 + Step 1 pipeline-analysis §(b) line 179):
  1. `stage1_chart60_120_passed.md` only stores `r.candidate.stk_nm` (line-per-name plain text). Type A~E info lives in `r.extra["type_results"]` (in-process only) or stdout of standalone runs.
  2. Re-deriving Type from `chart60_120Filter` requires reading chart60.md + chart120.md per stock and re-running pattern-matching — empirically ≥ 4 Read calls per stock × 100s of stocks = far above the agent verification cost budget.
  3. Re-derivation is fragile: any drift between `_TYPE_*` constants and the rendered Markdown's stale strings (ADR-010 — Type C `"2.0%"` / Type D `"60%"` doc-drift) would silently corrupt the inferred Type.
  4. The Korean note explicitly directs the user to Stage 1 re-evaluation (via WHY_REJECTED on any specific stock) for Type detail — which surfaces verbatim Type matching from `masterReference.log`'s `r.extra` text.

**Checkpoint**: if `researchedCompany.md` exists but all `stage*_passed.md` are missing → "결과 파일이 부분적으로만 존재합니다 (researchedCompany.md 있음, 단계별 파일 부재). 필터 실행이 비정상 종료되었을 수 있습니다."

**Output**: §5 SHOW_RESULTS Korean template + disclaimer (abbreviated if not the first emission of the session).

**Retry budget**: read-only chain — no execution retries needed. Filesystem errors (`FileNotFoundError`, `PermissionError`) reported once, no auto-retry.

---

### Chain 5 — `WHY_REJECTED(stock_name, date)`

- **Trigger intent**: WHY_REJECTED ("OO전자 왜 빠졌어?" / "탈락 이유").
- **Inputs**: `stock_name` (Korean), `date` (default = `last_scan_date`).
- **Pre-condition**: `${KRT_REPORTS}/{date}/` must exist; otherwise standard `"결과가 없습니다"` redirect.

**Steps**:

1. **Glob check** — verify stock was in the collection pool:
   ```
   Glob: ${KRT_REPORTS}/{date}/*{stock_name}*/
   ```
   - **Checkpoint**: zero matches → Korean output `"해당 종목은 수집 대상에 포함되지 않았습니다. 조건검색·상하한가 수집 단계에 들어오지 않은 종목입니다."` + suggest checking `${KRT_REPORTS}/{date}/conditionResearch.md` or `upperLowerPrice.md`. Halt chain.
   - Multiple matches (partial name overlap) → AskUserQuestion with up to 3 candidates.
2. **Append stock name to masterReference.md** — agent verification #9 (Edit only, NEVER Write):
   ```
   Edit: ${KRT_REPORTS}/{date}/masterReference.md
   old_string: ""  (or last line)
   new_string: "{stock_name}\n"
   ```
   Rationale: Write would overwrite any user-curated entries. Edit append is safe and re-runnable.
3. **Run Filter_condition_update synchronously** (~30s typical, no background needed):
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m src.kiwoom.itemFilter.Filter_condition_update {date}
   ```
4. **Read masterReference.log** — extract the latest block (the one emitted by Step 3):
   - Grep for the header line `[{stamp}] masterReference 분석 (date={date}, 대상 N종목)` whose stamp is the most recent (last occurrence).
   - Slice from that header to the next `<sep>` or EOF.
   - Within the block, find the `### {stock_name}` subsection.
5. **Parse rejection stage + condition + values** — natural-language `reason` text per ADR-009 hybrid regex (Step 1 pipeline-analysis §(c) Gap value inclusion: Partial). The block schema is verbatim:
   ```
   ### <stock_name>(<code>?)
   - Stage N — <stage_name> (<passed_file>): [<category>] <reason>
   ...
   (기록 YYYY-MM-DD HH:MM:SS)
   ```
   - Identify the first `[제외]` line — that is the rejection Stage.
   - Apply per-Stage regex catalog (delegated to filter-tune; stock-scan applies a lightweight version sufficient for explanation):
     - Stage 1: `Type ([A-E]):.*MA(\d+)\(([\d,]+(\.\d+)?)\)\s*[<>]\s*MA(\d+)×([\d.]+)\(([\d,]+(\.\d+)?)\)`
     - Stage 2: `MA60\(([\d,.]+)\)\s*<\s*MA306×([\d.]+)\(([\d,.]+)\)`
     - Stage 2-1: `금일 일봉\s*([+\-]\d+(\.\d+)?)%`
     - Stage 3: `종가\(([\d,]+)\)\s*vs\s*MA612\(([\d,.]+)\)\s*([+\-]\d+(\.\d+)?)%`
     - Stage 4: `(외국인|기관계|개인)\s*(\d+)회 연속 (매도|매수)\s*\(≥\s*(\d+)\)`
     - Stage 5: `당기순이익\s*([+\-]?\d+)억원\s*<\s*0`
   - Compute `gap = |actual - threshold|` where extractable; on regex miss → emit `"수치 추출 실패 — 원문 그대로 표시"` + the raw `reason` text.
6. **Emit Korean explanation** per FR-3.1 template (Pattern B in PRD §5.2):
   ```
   Stage N에서 탈락: {조건} = {실제값}. 기준 {기준값}. {gap} 미달.
   ```
   Example (Stage 3, MA612 band breach): `"Stage 3에서 탈락: 종가가 MA612 대비 +53.41%. 기준 상한 +50.0%. 3.41%p 초과."`
   For the `(전 Stage 통과 — 기록 대상 없음)` case: `"{stock_name}은(는) 5-Stage 전부 통과한 종목입니다 — 탈락 사유가 없습니다."`
7. **Log rotation check (B-5 / PRD §6.5)**: count lines of `masterReference.log` via `wc -l`. If > 500 → archive:
   ```
   mv ${KRT_REPORTS}/{date}/masterReference.log ${KRT_REPORTS}/{date}/masterReference.log.{YYYYMM}
   ```
   Emit Korean notice: `"로그 회전: masterReference.log → masterReference.log.{YYYYMM} (500행 초과)"`. New log starts empty on next run.

**Checkpoint**:
- Step 3 exit ≠ 0 → §6 error classification (most likely `ResearchError` / `FileNotFoundError` → suggest running SCAN_TODAY for `{date}` first).
- masterReference.log block missing the `### {stock_name}` subsection (rare — should never happen if Step 2 succeeded) → fall back to "block 파싱 실패. 기술 정보: ..."

**Output**: Korean rejection explanation + disclaimer.

**Retry budget**: parsing failures are non-retryable (regex miss → emit raw text). Bash execution failures get 1 retry on the same chain; same error 2× → stop.

---

### Chain 6 — `COMPARE(date_a, date_b)`

- **Trigger intent**: COMPARE ("어제랑 오늘 비교해줘" / "{date_a}와 {date_b} 차이").
- **Inputs**: `date_a`, `date_b` YYYYMMDD.

**Steps**:

1. Verify both `${KRT_REPORTS}/{date_a}/researchedCompany.md` and `${KRT_REPORTS}/{date_b}/researchedCompany.md` exist; otherwise `"{date_x} 결과 없음"` + offer SCAN_TODAY for the missing date.
2. Read both files into sets `S_a`, `S_b` (one stk_nm per line).
3. Compute:
   - `common = S_a ∩ S_b`
   - `only_a = S_a - S_b` (removed in B)
   - `only_b = S_b - S_a` (added in B)
4. **Cross-reference tuning-log.md** (FR-6.6): Read `${KRT_REPORTS}/tuning-log.md` (canonical SOT for inter-session experiment history per PRD §9). Filter rows whose datetime falls between `date_a 00:00` and `date_b 23:59`. If any rows match, append annotation:
   ```
   참고: {date_a}~{date_b} 기간 동안 파라미터 변경 {N}건 발견: {param_id_list}
   ```
   This surfaces the FR-2.4 caveat ("날짜와 파라미터 설정이 동시에 다른 경우 이를 명시").
5. Emit Korean comparison table (§5 COMPARE template).

**Checkpoint**: `tuning-log.md` absent → skip annotation silently. `tuning-log.YYYYMM.md` archives (PRD §FR-6.6 200-row rotation) — also read if datetimes fall in the archive's range.

**Output**: 3-bucket table + tuning annotation + disclaimer.

**Retry budget**: read-only chain. No execution retries.

---

### Chain 7 — `COMPARE_PARAMS(before_run, after_run)`

- **Trigger intent**: COMPARE_PARAMS ("변경 전후 비교", same-date / different params per workflow.md §B-3).
- **Inputs**: `before_run` and `after_run` = tuning-log row IDs OR datetimes. If user says simply "변경 전후 비교", default to the **last 2 confirmed rows** in `tuning-log.md`.

**Steps**:

1. Resolve `before_run` / `after_run` by reading `tuning-log.md`. **Canonical 8-column schema (PRD FR-6.6, owned by filter-tune §3 Step 7)**:
   ```
   | datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |
   ```
   stock-scan READS this schema; filter-tune is the SOLE writer. No additional columns required (Review#1 fix: schema reconciled).
2. Extract `stocks_passed_before` and `stocks_passed_after` columns directly (each is an integer count per filter-tune §3 Step 7 spec).
3. Compute diff (same as Chain 6).
4. Emit Korean table (§5 COMPARE_PARAMS template) showing:
   - Param change: `{param_id}: {old} → {new}`
   - Pass-count delta: `{before_count} → {after_count} ({delta:+d})`
   - 공통 / 추가 / 탈락 buckets.

**Checkpoint**: tuning-log row not found → `"해당 변경 이력을 tuning-log.md에서 찾을 수 없습니다."` + suggest `cat tuning-log.md | tail -10` to inspect available rows.

**Retry budget**: read-only. No retries.

---

### Chain 8 — `RERUN_FILTERS(date)`

- **Trigger intent**: RERUN_FILTERS ("필터만 다시 돌려줘" / "데이터는 그대로 두고 필터만").
- **Inputs**: `date` (default = `last_scan_date`).
- **Pre-condition (d)**: `${KRT_REPORTS}/{date}/prefetchManifest.json` must exist + zero errored stocks (per §4). Absent → `"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."` Halt chain.
- **Lock check**: refuse if filter-tune.lock present (R-9).

**Steps**:

1. Pre-flight (d) check (above).
2. Snapshot existing `researchedCompany.md` content into memory (`prev_passed` set) for before/after comparison.
3. **Synchronous execution** (typically < 3 min, fits 600s Bash cap):
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}
   ```
4. On exit 0: read new `researchedCompany.md` into `new_passed` set.
5. Emit Korean before/after table:
   ```
   변경 전: {len(prev_passed)}종목
   변경 후: {len(new_passed)}종목 ({delta:+d})
   추가: {sorted(new_passed - prev_passed)}
   탈락: {sorted(prev_passed - new_passed)}
   ```
6. Update `screener_state.last_results_summary`.
7. Disclaimer.

**Checkpoint**:
- Exit ≠ 0 → §6 dispatch (most common: `ResearchError` if prefetchManifest.json was deleted between Step 1 and Step 3).
- `run_filters` does **NOT** invoke `Filter_condition_update` (Step 2 §7 + Step 1 pipeline-analysis line 124) — so `masterReference.log` is **not** updated by this chain. If the user follows up with WHY_REJECTED, Chain 5 still runs `Filter_condition_update` independently.

**Retry budget**: same-error 2× → stop.

---

### Chain summary table

| # | Chain | Background? | Sync runtime | Writes screener_state? | Updates masterReference.log? |
|---|---|---|---|---|---|
| 1 | SCAN_TODAY | YES (ADR-012) | ~10-15 min | ✅ | ✅ (via Filter_condition_update inside full flow) |
| 2 | SCAN_SEPARATED | YES for prefetch, NO for filters | prefetch 10-15 min, filters < 3 min | ✅ | ❌ (run_filters does NOT call Filter_condition_update) |
| 3 | SCAN_RANGE | YES (loops Chain 1) | N × ~12 min | ✅ (per day) | ✅ (per day) |
| 4 | SHOW_RESULTS | NO | < 5s | ❌ | ❌ |
| 5 | WHY_REJECTED | NO | ~30s | ❌ | ✅ (append) |
| 6 | COMPARE | NO | < 5s | ❌ | ❌ |
| 7 | COMPARE_PARAMS | NO | < 5s | ❌ | ❌ |
| 8 | RERUN_FILTERS | NO | < 3 min | ✅ | ❌ |

---

## §4. Pre-Flight Verification Integration (B-13)

Reference Step 4 architecture §5 verbatim. stock-scan executes the following at the specified moments:

**Session start (lightweight, sub-second)** — runs at the very first user invocation of any stock-scan chain in the session:
- **(a)** `test -d ${KRT_ROOT}` — exit 0 expected; on fail → AskUserQuestion (path re-confirmation).
- **(c)** `test -w ${KRT_REPORTS}` — exit 0 expected; on fail → `"reports/ 디렉터리에 쓰기 권한이 없습니다. chmod u+w 또는 디스크 여유 공간을 확인해주세요."`

**First Bash exec of session (per OQ-3 / R-11 caveat, Step 4 §3)** — runs once before the **first** background or synchronous Bash invocation of the session:
- **(b)** Full execution probe: `[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version` — chained existence + dereference to detect dangling pyenv symlinks (R-10). On non-zero or version mismatch: `"가상환경 Python 실행파일이 없습니다. cd ${KRT_ROOT} && python3.12 -m venv .venv && pip install -r requirements.txt 를 먼저 실행해주세요."` — block further execution.
- Bash permission probe (R-11): if the first `cd ${KRT_ROOT} && .venv/bin/python --version` is denied, surface a clear Korean instruction to add `"Bash(cd /Users/tajun/spJavis/kiwoom-rest-trader && *)"` to `.claude/settings.local.json` (or have the user invoke `/install`).

**Pre-SHOW_RESULTS / WHY_REJECTED for date X**:
- **(d)** `prefetchManifest.json` health check (Step 4 §5 command verbatim — Fix-Step10-A defensive non-ok sentinel). Required because both chains assume the prefetch artifacts for the target date are complete.

**Pre-Edit (CHANGE_PARAM only — NOT this skill)**:
- **(e)** Parameter variable name grep — handled by **filter-tune** Skill, not stock-scan. Mentioned here only to document scope boundary.

stock-scan never edits `Final` constants; (e) is out of scope.

---

## §5. Result Output Format Templates

### Korean number formatting (PRD §7.3 verbatim)

- 가격: `4,805원` (천단위 콤마)
- 등락률: `-3.5%`
- 배수: `0.965배`
- 횟수: `5,234회`
- 금액: `1,234억원`
- 비율 표시: `15/350개`, `82개 → 45개`

Skill MUST reproduce these forms exactly. No alternative units (`￦`, `KRW`), no scientific notation, no English locale (`4,805 KRW` forbidden).

### SHOW_RESULTS Korean template (Chain 4 + final emission of Chains 1, 2, 8)

```
[{date} 스캔 결과]

| Stage | 입력 | 통과 | 탈락률 |
|---|---|---|---|
| 1 (chart60_120)   | 2,398 | 1,234 | 48.5% |
| 2 (chart240)      | 1,234 |   567 | 54.0% |
| 2-1 (chartDayPre) |   567 |   542 |  4.4% |
| 3 (chartDay)      |   542 |   128 | 76.4% |
| 4 (investor)      |   128 |    34 | 73.4% |
| 5 (finance)       |    34 |    17 | 50.0% |
| 최종              |       |    17 |       |

[최종 통과 종목]
- 삼성전자(005930)
- SK하이닉스(000660)
- ... (전체 목록: ${KRT_REPORTS}/{date}/researchedCompany.md)

* Type 상세는 Stage 1 재평가로 확인 가능 (예: "삼성전자 왜 통과했어?")

⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.
```

(Abbreviated disclaimer for non-first emission: `(투자판단·책임은 본인에게 있습니다)`)

### Prefetch stats Korean template (Chain 2 step 5)

```
[데이터 수집 완료 — {date}]
- 대상 종목: {total}개
- 성공: {ok_count}개
- 빈 데이터: {empty_count}개
- 오류: {err_count}개

prefetchManifest.json 위치: ${KRT_REPORTS}/{date}/prefetchManifest.json
```

### WHY_REJECTED Korean template (Chain 5 step 6)

```
[{stock_name} 탈락 분석 — {date}]

Stage {N}에서 탈락: {조건} = {실제값}. 기준 {기준값}. {gap} 미달.

[전체 Stage 평가 이력 (재평가 결과)]
- Stage 1 (chart60_120): {category} — {reason 요약}
- Stage 2 (chart240): {category} — {reason 요약}
- Stage 2-1 (chartDayPre): {category} — {reason 요약}
- Stage 3 (chartDay): [제외] {reason 전문}        ← 실제 탈락 지점
- Stage 4 (investor): (이전 단계 탈락으로 미도달)
- Stage 5 (finance): (이전 단계 탈락으로 미도달)

기록 시각: {YYYY-MM-DD HH:MM:SS}

(투자판단·책임은 본인에게 있습니다)
```

### SCAN_RANGE summary Korean template (Chain 3 step 4)

```
[범위 스캔 완료 — {start}~{end} ({N}영업일)]

| 날짜 | 통과 종목 수 |
|---|---|
| 2026-05-26 (월) | 15 |
| 2026-05-27 (화) | 22 |
| 2026-05-28 (수) | 17 |
...

- 합집합 (어느 날이든 통과): {N_union}종목
- 교집합 (모든 날 통과): {N_intersect}종목 — {list}

⚠️ 주의: 한국 공휴일은 자동 제외되지 않습니다. 통과 0건인 날은 휴장일일 수 있습니다.
(투자판단·책임은 본인에게 있습니다)
```

### COMPARE Korean template (Chain 6)

```
[비교: {date_a} vs {date_b}]

| 구분 | 종목 수 |
|---|---|
| 공통 ({date_a} ∩ {date_b}) | {N_common} |
| {date_a} 에만 (탈락) | {N_only_a} |
| {date_b} 에만 (추가) | {N_only_b} |

[공통 종목] {comma-separated list}
[탈락] {list_only_a}
[추가] {list_only_b}

{선택적 — tuning-log 인용 시}: 참고: {date_a}~{date_b} 기간 동안 파라미터 변경 {N}건 발견: {param_id_list}

(투자판단·책임은 본인에게 있습니다)
```

### COMPARE_PARAMS Korean template (Chain 7)

```
[파라미터 변경 전후 비교]

변경: {param_id}: {old_value} → {new_value}
시각: {before_datetime} → {after_datetime}

| 구분 | 종목 수 |
|---|---|
| 변경 전 | {before_count} |
| 변경 후 | {after_count} ({delta:+d}) |
| 공통 | {N_common} |
| 추가 | {N_added} |
| 탈락 | {N_removed} |

[추가된 종목] {list}
[탈락한 종목] {list}

(투자판단·책임은 본인에게 있습니다)
```

### Error report Korean template (used by §6 dispatch)

```
[오류 발생]
{Korean summary 1 sentence}
원인: {cause}
조치: {user action}

기술 정보:
  {raw error excerpt — last 5 lines of stderr or exception type+message}
```

---

## §6. Error Handling Per Chain

**All chains dispatch errors via `type(exc).__name__` STRING match** (OQ-3 / ADR-011 — never `isinstance` against any imported `KiwoomApiError` symbol; the class is defined **8 times independently** across kiwoom-rest-trader modules, so import-based catches silently miss 7 of them).

For `Bash(run_in_background)` chains, errors are surfaced via stderr lines after completion notification. The dispatch logic:

```python
# pseudocode the Skill encodes in error-handling step
exit_code = bash_result.exit_code
stderr_tail = bash_result.stderr.splitlines()[-20:]

# First-level: exit-code triage (Step 5 §5 exit code 1차 분류)
if exit_code == 0:
    # check for non-fatal warnings in stderr; otherwise success path
elif exit_code == 1:
    # domain input-absence: OrganizeError / ResearchError / PrefetchError
elif exit_code == 2:
    # everything else
else:
    # unexpected code

# Second-level: name-based dispatch on the LAST raised exception name in stderr
# Search stderr_tail for lines like "kiwoom.X.KiwoomApiError:" or just "KiwoomApiError:"
# Extract the bare class name via regex: r'\b(Kiwoom[A-Z][a-zA-Z]+Error|OrganizeError|ResearchError|PrefetchError|FileNotFoundError|ValueError)\b'
exc_name = extract_exception_name(stderr_tail)

# Map to Korean message (verbatim Step 5 §5 table)
korean = KOREAN_ERROR_TABLE.get(exc_name, KOREAN_ERROR_TABLE["Exception"])
```

**Reference Step 5 blueprint §5 error table** (9 user-facing classes, Korean messages verbatim). Repeated here for handoff convenience:

| `type(exc).__name__` | 한국어 요약 | 사용자 행동 |
|---|---|---|
| `KiwoomAuthError` | 키움 인증에 실패했습니다. | APP_KEY·SECRET_KEY 설정을 확인하고, 잠시 후 다시 시도해주세요. |
| `KiwoomApiError` | 키움 데이터 조회에 실패했습니다. | 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. |
| `KiwoomConditionError` | 조건검색 서버 응답에 실패했습니다. | 설정한 조건명이 키움 HTS에 저장되어 있는지 확인해주세요. |
| `OrganizeError` | 수집된 종목 데이터가 없습니다. | 조건검색·상하한가 수집을 먼저 실행해주세요. |
| `ResearchError` | 필터링에 필요한 데이터 파일이 없습니다. | 먼저 데이터 수집(prefetch)을 실행해주세요. |
| `PrefetchError` | 종목 사전 수집을 시작할 데이터가 없습니다. | 조건검색·상하한가 단계를 먼저 완료해주세요. |
| `FileNotFoundError` | 필요한 데이터 파일을 찾을 수 없습니다. | 먼저 해당 단계의 데이터 수집을 실행해주세요. |
| `ValueError` | 데이터 형식이 올바르지 않습니다. | 수집된 데이터가 손상되었을 수 있으니 다시 수집해보세요. |
| `Exception` (generic) | 예기치 못한 오류가 발생했습니다. | 잠시 후 다시 시도하거나 로그를 확인해주세요. |

**Retry budget (agent verification #10) — repeated per-chain**:
- SAME `type(exc).__name__` observed 2× consecutively in the same chain invocation → STOP. Emit Korean stop message: `"동일 오류({exc_name})가 2회 반복되었습니다. 추가 시도를 중단합니다. 원인: {cause}. 조치: {action}."`
- No infinite retry loops anywhere.
- For Chain 3 SCAN_RANGE specifically: 2 consecutive day-level same-error failures abort the range loop entirely (not just the current day).

---

## §7. screener_state.json Read/Write Points

Per Step 4 §4 schema. Atomic write: `json.dump(state, tmp); mv tmp final`. No locking (single-threaded session per Step 4 atomicity note).

| Chain | Read | Write |
|---|---|---|
| Session start (any chain — first invocation) | ✅ read `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files` | — |
| Chain 1 SCAN_TODAY end (success) | — | ✅ update `last_scan_date`, `last_results_summary={scan_date, passed_count, by_stage}` |
| Chain 2 SCAN_SEPARATED end (success — after filter step) | — | ✅ same as Chain 1 |
| Chain 3 SCAN_RANGE per-day end | — | ✅ each day updates (overwrites prior) per Chain 1 |
| Chain 4 SHOW_RESULTS | ✅ check `last_results_summary.scan_date == date` for cache-hit shortcut (skip re-reading stage files) | — |
| Chain 5 WHY_REJECTED | ✅ read `last_scan_date` if `date` arg omitted | — |
| Chain 6 COMPARE | ✅ read `last_scan_date` for default | — |
| Chain 7 COMPARE_PARAMS | ✅ read `last_param_changes` to resolve `before_run` / `after_run` if user is vague | — |
| Chain 8 RERUN_FILTERS end (success) | — | ✅ update `last_results_summary` (last_scan_date unchanged) |
| (CHANGE_PARAM in filter-tune) | (cross-skill — write `last_param_changes`) | (handled by filter-tune skill; stock-scan does not touch this field) |

**JSON corruption recovery** (R-7 / Step 4 §10): `try: json.load() except json.JSONDecodeError: shutil.move(state_path, f"{state_path}.corrupt.{ts}")` → treat as new-user (file absent). Emit Korean notice: `"⚠️ screener_state.json 손상 감지. 손상 파일을 백업했습니다: {state_path}.corrupt.{ts}. 새로운 상태로 시작합니다."`

**Cross-skill coordination**: `last_param_changes` is owned by filter-tune. stock-scan only **reads** it (Chain 7 + session-start drift detection per Step 5 §10). stock-scan never mutates `last_param_changes` or `current_backup_files`.

---

## §8. references/ File Plan

Step 9 `@scan-builder` creates the following 5 reference files under `${KRT_ROOT}/.claude/skills/stock-scan/references/`. Content summary for each:

### references/execution-chains.md (~250 lines)

Verbose canonical definitions of all 8 chains: per-chain inputs, full numbered steps with verbatim Bash commands, checkpoint exit-code branches, watchdog logic, retry-budget enforcement points, before/after state diagrams. Each chain section ≈ 30 lines. Cross-references to `output-templates.md` for Korean strings and to `background-execution.md` for ADR-012 specifics.

### references/pre-flight-checks.md (~80 lines)

The 5 pre-flight checks (a)-(e) with: exact Bash command, expected exit code, Korean error message on fail, remediation flowchart (visual ASCII), timing diagram (session-start vs first-Bash vs per-chain). Reference Step 4 architecture §5 verbatim. Includes the R-10 dangling-pyenv-symlink defense and R-11 `Bash(python *)` permission probe.

### references/output-templates.md (~150 lines)

All Korean output templates as copy-pastable blocks: SHOW_RESULTS, prefetch stats, WHY_REJECTED, SCAN_RANGE summary, COMPARE, COMPARE_PARAMS, error report. PRD §7.3 number-format examples enumerated. Full disclaimer text + abbreviated disclaimer + when-to-use rules per B-23 / FR-8. O/X expression policy (FR-8.2/8.3) examples — what to say and what to avoid.

### references/disclaimer.md (~30 lines)

Standalone disclaimer reference:
- Full version (first emission per session, PRD B-23 verbatim): `"⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다."`
- Abbreviated (subsequent emissions): `"(투자판단·책임은 본인에게 있습니다)"`
- O/X policy per PRD §7.3 / FR-8.2/8.3: (O) `"기술적 완성도가 높은 종목"`, `"필터 조건을 충족한 종목"`, `"선별 결과"`, `"5-Stage 통과"`; (X) `"매수 추천"`, `"이 종목을 사세요"`, `"유망 종목"`, `"상승 예측"`, `"이익 보장"`
- When disclaimer is NOT required: parameter inquiries, error messages, system-status reports, pre-flight gates.

### references/background-execution.md (~60 lines)

ADR-012 enforcement reference:
- Which Bash commands MUST use `run_in_background: true` (only `run_full_research_flow` and `run_prefetch` — explicitly NOT `run_filters`, NOT `Filter_condition_update`).
- 30-min watchdog implementation pattern.
- 4-step completion handler in detail: (1) stdout count extraction with regex fallback, (2) stderr error scan, (3) error classification dispatch logic, (4) Korean report emission.
- The 10-15 min Korean announce string verbatim.
- Timeout fallback Korean message verbatim.
- Failure-to-receive-notification escalation: emit timeout report + suggest SCAN_SEPARATED.

---

## §9. Safety Rules Enforcement Points (TS-1~5)

For stock-scan (PG-1, screener execution only — does NOT write `Final` constants):

| Rule | Applies to stock-scan? | Enforcement |
|---|---|---|
| TS-1 | **N/A** — stock-scan never writes `Final` constants. All parameter mutations live in filter-tune Skill. |
| TS-2 | **N/A** — no `.bak.*` files created by this skill. |
| TS-2a | **N/A** — no backup-lifecycle management. |
| TS-3 | **N/A** — no value range checks (no values are set). |
| TS-4 | **N/A** — no multi-param detection (no params changed). |
| TS-5 | **N/A** — TS-5 ("변경 후 재필터 실행 제안") is the *suggestion* from filter-tune; stock-scan executes the requested re-run when the user later invokes RERUN_FILTERS. |

**Disclaimer enforcement (PRD §7.3 / FR-8 / B-23)** — the ONE safety rule stock-scan **does** enforce:
- Every result-emitting chain (1, 2, 3, 4, 5, 6, 7, 8) MUST append the disclaimer.
- Format: full version on first emission of session, abbreviated (1-line) thereafter.
- Tracked via a session-scoped flag (initial state: full-not-yet-emitted; toggled true after first emission).
- Disclaimer is NOT required on: error reports, pre-flight messages, AskUserQuestion prompts, progress reports ("3/5일 완료").

**Implicit lock awareness (R-9)** — stock-scan defers to filter-tune's advisory lock:
- Before any Chain 1/2/3/8 Bash execution, check `${KRT_REPORTS}/filter-tune.lock`. If present → refuse with `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`
- stock-scan never creates or releases this lock.

---

## §10. Length Estimate

| Section in SKILL.md | Est. lines |
|---|---|
| Frontmatter | 8 |
| §1 Trigger conditions | 6 |
| §2 Path constants reference (single sentence — defer to CLAUDE.md) | 2 |
| §3 8 chains (compact spec, full detail deferred to references/execution-chains.md) | 60 |
| §4 Pre-flight integration | 8 |
| §5 Output template references (defer to references/output-templates.md) | 4 |
| §6 Error handling (pseudocode + table reference) | 8 |
| §7 screener_state.json I/O table | 8 |
| §8 references/ file index | 6 |
| §9 Safety rules (TS-1~5 N/A + disclaimer enforcement) | 6 |
| **SKILL.md Total** | **~116** |

Plus 5 reference files:
- `execution-chains.md` ≈ 250 lines
- `pre-flight-checks.md` ≈ 80 lines
- `output-templates.md` ≈ 150 lines
- `disclaimer.md` ≈ 30 lines
- `background-execution.md` ≈ 60 lines

**Total package**: SKILL.md (~116) + 5 references (~570) = ~686 lines of skill content. Within the workflow.md "comprehensive over terse" preference (절대 기준 1: quality over brevity).

---

## §11. Verification Self-Check

- [x] All 8 chains specified with: trigger / steps / checkpoint / output / failure / retry budget (§3 — Chain 1 through Chain 8 each section)
- [x] Pre-flight (a)-(e) integration points named with timing (§4 — session-start (a)(c) / first-Bash (b) / pre-SHOW_RESULTS|WHY_REJECTED (d) / out-of-scope (e))
- [x] Output format includes Korean number formatting **verbatim from PRD §7.3** (§5 — 가격/등락률/배수/횟수/금액 5 forms)
- [x] references/ list ≥ 5 files with purpose (§8 — execution-chains, pre-flight-checks, output-templates, disclaimer, background-execution = exactly 5)
- [x] OQ-3 dispatch on `type(exc).__name__` STRING explicitly stated (§6 — pseudocode + verbatim quote of the rule)
- [x] ADR-012 background mandate enforced in chains 1 + 2 (long-running) — Chain 1 step 5 `Bash(run_in_background: true)`; Chain 2 step 3 same; both have 30-min watchdog and 4-step completion handler (§3)
- [x] SHOW_RESULTS uses Option (b) — no Type re-derivation; Korean note `"* Type 상세는 Stage 1 재평가로 확인 가능"` included verbatim (§3 Chain 4 + §5 SHOW_RESULTS template). Pre-Resolved Decision rationale documented (4 points).
- [x] Retry budget per chain: same `type(exc).__name__` 2× → stop + Korean explanation (§3 each chain "Retry budget" + §6 repeated reference)
- [x] masterReference.log / masterReference.md use **Edit only** (never Write) — Chain 5 Step 2 explicit + agent verification #9 cited (§3)
- [x] screener_state.json read/write points table complete — 9 rows covering all 8 chains + session start (§7)

---

*Blueprint complete. Step 9 `@scan-builder` writes the final SKILL.md + 5 references files to `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/` from this spec.*
