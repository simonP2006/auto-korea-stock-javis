# Step 6 — filter-tune SKILL Blueprint

> Generated: 2026-05-30
> Target deployment: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/`
> Created by Step 9 `@tune-builder` from this blueprint
> Skill covers: PG-2 — parameter tuning (paramount goal)
> Sources: PRD FR-4..FR-8 / TS-1..TS-5 / §5 / §6.4 / §7.3, workflow.md §6 (lines 268-303), workflow-idea B-7/B-8/B-9/B-10/B-16/B-17/B-22, Step 1 param-inventory (75 Final constants), Step 1 pipeline-analysis §(c) (gap-value ADR-009), Step 2 research §6/§8, Step 4 architecture (path constants, ADR-009/010/011/012, R-9 lock semantics, schema), Step 5 CLAUDE.md blueprint (§3 routing, §4 TS verbatim, §5 error table)

## Blueprint Conventions

- **(spec)** = literal text/structure that Step 9 `@tune-builder` writes verbatim into the final SKILL.md
- **(source)** = traceability anchor (PRD / workflow-idea / Step output / ADR)
- **(estimate)** = approximate line count contributed to the final SKILL.md

The blueprint itself can exceed 700 lines because it carries rationale, sequence detail, branch fallbacks, and reference-file plans — none of which the final SKILL.md inherits. The final SKILL.md is estimated at ~134 lines (see §10); reference files account for ~980 additional lines distributed across 6 files.

---

## §1. SKILL.md Header & Trigger Conditions

### Frontmatter — **(spec)**

```yaml
---
name: filter-tune
description: Kiwoom filter parameter tuning — interactive Korean-language fine-tuning with safety rails (TS-1~5 enforced). Handles SHOW_PARAMS, CHANGE_PARAM, CONFIRM, RESTORE, COMPARE_EXPERIMENTS, THEORY_GUIDE, ASK_MODULE.
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
maxTurns: 40
---
```

**Rationale**:
- `model: opus` — PRD §3 user persona is a senior Korean trader with deep theory knowledge; tuning conversations involve Minervini/Weinstein/VCP/CANSLIM reasoning + gap-numeric extraction from `masterReference.log` per ADR-009. Sonnet may degrade theory mapping accuracy.
- `tools` list explicitly omits `Task` (no sub-agent dispatch within skill — Skill runs serially within main session) and explicitly includes `AskUserQuestion` for TS-3 range-violation + TS-4 multi-param + B-7 confirmation gates.
- `maxTurns: 40` accommodates the 8-step master sequence (1 user prompt → up to 6 internal turns) executed up to ~6 times per tuning session before user revisits stock-scan.

### Trigger via CLAUDE.md Intent Table — **(source: Step 5 §3)**

CLAUDE.md routes the following 7 intent clusters to this skill:

| Cluster | Master action (SKILL §3/§4) |
|---|---|
| `SHOW_PARAMS` | §4 SHOW_PARAMS branch |
| `CHANGE_PARAM` | §3 PARAM_CHANGE master sequence (8 steps) |
| `CONFIRM` | §4 CONFIRM branch |
| `RESTORE` | §4 RESTORE branch (primary + tuning-log fallback) |
| `COMPARE` (when scoped to params) | §4 COMPARE_EXPERIMENTS branch |
| `THEORY_GUIDE` | §4 THEORY_GUIDE branch |
| `ASK_MODULE` | §4 ASK_MODULE branch (inline answer w/ Phase 2 deflection) |

> The mixed-intent rule from Step 5 §3 ("필터 바꾸고 다시 돌려줘") triggers sequential `CHANGE_PARAM` → user confirm → stock-scan `RERUN_FILTERS`. The handoff at Step 8 of the master sequence is the seam.

---

## §2. Path Constants Reference

Inherit verbatim from Step 4 §1 (also documented in CLAUDE.md §2 per Step 5 blueprint). Skill references — never re-defines — these shell-style variables. All path interpolation happens at Bash invocation time.

| Variable | Value | Usage in this skill |
|---|---|---|
| `${KRT_ROOT}` | `/Users/tajun/spJavis/kiwoom-rest-trader` | Sole prefix for all `cd` invocations (per ADR-007 venv direct call). |
| `${KRT_PYTHON}` | `${KRT_ROOT}/.venv/bin/python` | **NOT invoked from this skill** — filter-tune never runs Python scripts; it edits constants and reads files. (Re-run after edit is delegated to stock-scan via the Step 8 handoff.) |
| `${KRT_REPORTS}` | `${KRT_ROOT}/reports` | Source for `masterReference.log`, target for `screener_state.json`, `tuning-log.md`, and the R-9 advisory lock `filter-tune.lock`. |
| `${KRT_FILTERS}` | `${KRT_ROOT}/src/kiwoom/itemFilter` | **Sole write target for Edit.** Per TS-1 + Step 4 §2 "Files explicitly NOT modified" — Edit is restricted to `Final` constant values inside `*.py` files under this directory. Never any other path. |
| `${KRT_SCRIPTS}` | `${KRT_ROOT}/scripts` | Read-only; referenced only when explaining the SCAN_TODAY/RERUN_FILTERS chain to the user. Never invoked from this skill. |

**Critical absolute-path constants used inside this skill**:

| Path | Purpose |
|---|---|
| `${KRT_REPORTS}/tuning-log.md` | Append target (Step 7 of master sequence). Read by `COMPARE_EXPERIMENTS` and `RESTORE` fallback. |
| `${KRT_REPORTS}/tuning-log.YYYYMM.md` | Archive target when active log exceeds 200 rows (FR-6.6 / B-16 rotation). Read by `RESTORE` fallback if active log misses the entry. |
| `${KRT_REPORTS}/screener_state.json` | Atomic read/write — `last_param_changes` array maintained. (Schema per Step 4 §4.) |
| `${KRT_REPORTS}/filter-tune.lock` | R-9 advisory sentinel file. Created at Step 5, removed at Step 7. stock-scan refuses to launch background scans while this exists. |
| `${KRT_REPORTS}/{YYYYMMDD}/masterReference.log` | Read-only — Step 3 gap-impact estimation per ADR-009 regex extraction. |

---

## §3. Master Tuning Sequence — `PARAM_CHANGE(param_id, new_value)` (B-22 full integration)

### Sequence Diagram (informative)

```
User: "Type A 허용오차 -5%로 완화해줘"
  │
  ▼
Step 0 [TS-4]  multi-param detection                        ──┐ if multi → warn + AskUserQuestion
  │                                                            │ if proceed → loop Steps 1-8 per param
  ▼                                                            │
Step 1 [B-9, TS-3]  Range Map lookup + Stage 5 hard-block      │
  │  ├ out-of-range → REJECT (Korean + theoretical basis)      │
  │  └ Stage 5 → REJECT (C-4: "현재 코드 구조상 변경 불가...")  │
  ▼                                                            │
Step 2 [B-17]  Shared constant impact                          │ (SHORTCUT skips Steps 2-3
  │  ├ shared → list affected Types/conditions                 │  if in-range AND not shared)
  │  └ private → skip                                          │
  ▼                                                            │
Step 3 [B-10]  masterReference.log gap analysis                │
  │  └ "약 N개 추가 통과 예상" (or "추정 데이터 없음")          │
  ▼                                                            │
Step 4 [B-7]  Confirmation table + AskUserQuestion             │
  │  ├ user 취소 → abort                                       │
  │  ├ user 다른 값 → loop Steps 1-4 with new_value            │
  │  └ user 적용 → proceed                                     │
  ▼                                                            │
Step 5 [B-8, TS-2, TS-2a, R-9]  Backup + lock acquire          │
  │  ├ acquire ${KRT_REPORTS}/filter-tune.lock                 │
  │  ├ cp {file} {file}.bak.$(date +%Y%m%d_%H%M%S)             │
  │  └ rotation: if >5 .bak files, gate on tuning-log presence │
  ▼                                                            │
Step 6  Edit Final constant value                              │
  │  ├ B-13e variable-name presence check (R-2/§5)             │
  │  ├ unit conversion (refs/unit-conversion.md)               │
  │  └ adjacent comment auto-update                            │
  ▼                                                            │
Step 7 [B-16]  tuning-log.md append + rotation + lock release  │
  │  ├ row format (FR-6.6)                                     │
  │  ├ rotate if >200 rows → tuning-log.YYYYMM.md              │
  │  ├ update screener_state.json.last_param_changes           │
  │  └ rm ${KRT_REPORTS}/filter-tune.lock                      │
  ▼                                                            │
Step 8 [TS-5]  Rerun suggestion                                │
  │  └ "필터를 다시 돌려볼까요?" → route to stock-scan RERUN_FILTERS
  ▼
END
```

### Step 0 [TS-4] — Multi-param detection — **(spec)**

**Trigger**: user message references > 1 distinct `param_id` (by Korean name or variable name) in a single turn.

**Detection heuristic** (pseudocode for SKILL.md):
- Tokenize user message; count occurrences of any known parameter Korean alias or `_VARIABLE_NAME` against `references/parameter-catalog.md`.
- If `count >= 2` AND clauses are conjoined ("그리고", "또", "도", "와", comma-list): proceed to multi-param branch.

**Korean warning (verbatim, source PRD TS-4 + workflow-idea B-22 line 274)**:
> `"한 번에 하나씩 변경을 권장합니다. 동시에 여러 파라미터를 바꾸면 어느 변경이 결과에 어떤 영향을 줬는지 분리하기 어렵습니다. 어떻게 진행하시겠습니까?"`

**AskUserQuestion options (3 choices, PRD P4 ≤4)**:
1. `"하나씩 차례대로 변경하기"` → loop Steps 1-8 per `param_id` serially. After each completion, prompt: `"{param_id}_N 변경이 완료됐습니다. 다음 파라미터({param_id}_N+1)를 계속 진행할까요?"` Skip to next on confirm; abort remaining on decline.
2. `"한 번에 모두 변경하기 (영향 추적 불가)"` → user accepts loss of causal attribution; loop Steps 1-7 per param without intermediate confirmation; Step 8 emitted only once at the end.
3. `"취소"` → abort the entire PARAM_CHANGE.

**Idempotence**: if Step 0 already ran for this session and user explicitly affirmed option 2, do not re-warn within the same turn-cluster.

### Step 1 [B-9, TS-3] — Range Map lookup + Stage 5 hard-block — **(spec)**

**Operations**:

**Step 1.0 — Keyword pre-check (Review#3 fix, fires BEFORE catalog lookup)**:
Before any resolution attempt, scan the raw user utterance for Stage-5 / financeFilter / 당기순이익 keywords. Trigger conditions (any of):
- Substring `cup_nga` (case-insensitive)
- Substring `당기순이익` (Korean for "net income")
- Substring `financeFilter` or `finance_filter` or `finance Filter` (case-insensitive)
- Substring `Stage 5` or `stage5` or `재무 단계` or `5단계`
- Substring `순이익` AND change-intent verb (`바꿔`, `변경`, `수정`, `튜닝`, `올려`, `내려`, `늘려`, `줄여`)
On any hit → REJECT with verbatim C-4 message (same as Step 1.2 below) and terminate this turn. **Rationale**: per workflow.md §6 line 286 and PRD §5.1 Stage 5 admonition, financeFilter has zero `Final` constants — catalog lookup would either fail or return non-Stage-5 candidates via the §5 fuzzy fallback, silently bypassing the hard-block. The keyword pre-check is the **primary** Stage 5 guard; catalog-based Step 1.2 below is the **secondary** guard for cases where the catalog mistakenly lists a Stage 5 param.

1. Resolve `param_id` from natural-language alias via `references/parameter-catalog.md`. Failure → AskUserQuestion to disambiguate (e.g., "60-분 정배열 허용오차" → `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` — see §5 Anti-Conflation Disambiguation).
2. **Stage 5 (financeFilter) hard-block (C-4, secondary guard)**: if resolved `param_id` is owned by `financeFilter.py` (catalog lookup somehow returned a Stage 5 row despite Step 1.0 pre-check), REJECT with:
   > `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. 당기순이익 판정(cup_nga < 0)이 하드코딩 비교문이고 Final 상수가 존재하지 않습니다. Phase 2에서 상수화를 검토합니다."` (verbatim from CLAUDE.md TS-1 exception clause and PRD §5.1 Stage 5 admonition.)
   Skill terminates this turn without entering Step 2.
3. **Range lookup**: `references/range-map.md` keyed by `param_id` → (physical range, danger zone, theoretical basis).
4. **Range check**:
   - if `new_value` ∈ physical range AND ∉ danger zone → proceed to Step 2.
   - if `new_value` ∈ danger zone (subset of physical range producing degenerate filter behaviour, e.g., tolerance ≥ 0.30 → "사실상 필터 무력화") → emit Korean warning + AskUserQuestion. PRD FR-5.5 verbatim style: `"허용오차 -{X}%면 사실상 필터가 무력화됩니다. 정말 이 값으로 진행할까요?"` Options: (a) 그대로 진행 (b) 안전 범위 권장값으로 변경 ({suggested}) (c) 취소.
   - if `new_value` ∉ physical range → REJECT (no override path). Korean message format: `"{param_korean_name}의 물리적 범위는 {range_min} ~ {range_max}입니다. 입력하신 {new_value}는 범위를 벗어났습니다. (이론적 근거: {basis})"`.

**Out-of-range rejection examples** (illustrative for SKILL implementer; reference-file holds all 75):
- `_TYPE_A_ALIGN_TOL = -0.50` → REJECT `"허용오차의 물리적 범위는 0.00 ~ 0.50입니다. 입력하신 -0.50은 범위를 벗어났습니다. (이론적 근거: tolerance는 비대칭 슬랙 폭이므로 부호는 양수, 50% 초과 시 정배열 개념 자체가 무의미)"`
- `_THRESHOLD_FOREIGN_CONSEC_SELL = 0` → REJECT `"정수 임계값의 물리적 범위는 1 ~ 16입니다. (16봉 데이터 한계). 0은 조건 자체를 끄는 의미이므로 임계값으로 부적합."`

### Step 2 [B-17] — Shared constant impact — **(spec)**

**Operations**:
1. Check `references/shared-constants.md` whether `param_id` appears in the "shared constants" registry.
2. If **shared** (currently exactly **one** entry: `_ALIGN_TOL_LOOSE` in `chart60_120Filter.py:120`): emit Korean impact disclosure listing every affected (Type, condition) tuple. Verbatim format:
   > `"⚠️ 이 상수는 공유 상수입니다. 변경 시 다음 조건들이 동시에 영향을 받습니다:`
   > ` • Type B — 120분 MA10-MA20 근접 판정`
   > ` • Type B — MA60-MA306 근접 판정`
   > ` • Type C — MA60-MA306 장기추세 leg`
   > ` • Type D — 60분 4선 정배열 fallback`
   > `특정 Type만 조정하려면 해당 Type 전용 상수 신설이 필요합니다 (TS-1 로직 변경 — 사용자 명시적 승인 필요)."`
3. If **private** (any other param_id): skip — proceed directly to Step 3.

**Source**: PRD §5.4 verbatim influence-list + Step 1 param-inventory "Critical Distinctions" + Step 2 §6 disambiguation table.

### Step 3 [B-10] — Impact preview from `masterReference.log` (ADR-009 hybrid) — **(spec)**

**Operations**:
1. Resolve latest available `masterReference.log`: `${KRT_REPORTS}/{latest_date}/masterReference.log` where `latest_date` = `screener_state.json.last_scan_date` (fallback: glob newest `reports/*/masterReference.log` modification time).
2. If absent / empty: ANNOUNCE `"추정 데이터 없음 — masterReference.log이 비어있거나 부재합니다. 정확한 영향은 변경 후 run_filters 재실행으로 확인하세요."` Skip to Step 4 carrying this advisory.
3. If present: invoke ADR-009 regex catalogue (`references/gap-extractor.md` — co-located with `tuning-sequence.md`) to extract `(actual, threshold, unit)` from every line whose `param_id` corresponds to the parameter being changed. Apply the new_value to recompute `would_pass` per row.
4. Aggregate:
   - `parsed_total = N parsed / M total rows` (transparency per Step 4 OQ-1).
   - `delta = count(would_pass | new) - count(would_pass | current)`
   - Korean line: `"masterReference.log {M}개 행 중 {N}개에서 gap 추출. {delta} {direction} (추정 정확도 {N/M*100:.0f}%)."` where `direction` = `"개 추가 통과 예상"` if delta > 0, `"개 추가 탈락 예상"` if delta < 0, `"개 변화 없음"` if delta = 0.
5. If `N/M < 0.5` (Step 4 R-4 fallback threshold): treat as "추정 데이터 부족" — emit advisory and proceed without numeric delta.

**Regex catalogue** (held in `references/tuning-sequence.md` §gap-extractor — top 5 dominant reason formats):
| Pattern key | Example reason text | Named groups extracted |
|---|---|---|
| `MA_ALIGNMENT` | `"MA60(7,195) < MA306×0.965(7,198)"` | `actual=7195`, `threshold=7198`, `unit=원` |
| `MA_BAND_PCT` | `"종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%]"` | `actual_pct=53.41`, `lower=-15.0`, `upper=50.0` |
| `DAILY_SURGE` | `"금일 일봉 +16.44% — 15% 이상 급상승"` | `actual_pct=16.44`, `threshold_pct=15.0` |
| `INVESTOR_CONSEC` | `"외국인 3회 연속 매도 (≥ 2)"` | `actual_days=3`, `threshold_days=2` |
| `FINANCE_CUP_NGA` | `"당기순이익 -70억원 < 0 (적자)"` | `actual_won=-70`, `threshold_won=0` |

### Step 4 [B-7] — Confirmation — **(spec)**

**Korean table format** (verbatim layout, per workflow-idea B-7 + PRD FR-5.6):

```
| 파라미터 | 현재 값 | 변경 후 |
|---|---|---|
| {var_name} ({Korean meaning}) | {current_value_display} | {new_value_display} |
```

**Display conventions** (per PRD §7.3 / CLAUDE.md §6):
- Tolerance: render both raw (`0.035`) and percent-form (`-3.5% (×0.965)`).
- Ratio: render both raw (`0.50`) and percent-form (`50%`).
- Integer: render bare (`2일`).

**Appendices when warnings exist**:
- If Step 2 emitted shared-constant warning → re-emit the affected list (collapsed: "공유 상수 — Type B/C/D 4개 조건 영향").
- If Step 3 computed delta → append: `"예상 영향: 약 {delta}개 종목 추가 통과 (추정 정확도 {N/M*100:.0f}%)"`.
- If Step 3 announced "추정 데이터 없음" → append: `"예상 영향: 추정 데이터 없음 (run_filters 재실행으로 정확한 결과 확인)"`.

**AskUserQuestion** (3 options per PRD P4):
1. `"적용 (Edit 진행)"` → proceed to Step 5.
2. `"다른 값으로 시도"` → AskUserQuestion follow-up asking `"새로운 값을 입력해주세요"`; on receipt, loop Steps 1-4 with new_value.
3. `"취소"` → abort the master sequence; emit `"변경을 취소했습니다."`

### Step 5 [B-8, TS-2, TS-2a, R-9] — Backup with rotation + lock acquire — **(spec)**

**Operations** (strictly ordered):

1. **R-9 advisory lock acquire (atomic — TOCTOU-safe, Review#2 fix)**:
   ```bash
   if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then
     # lock acquired — proceed
     true
   else
     # contention — another instance owns the lock; refuse
     echo "BLOCKED" >&2; exit 2
   fi
   ```
   `mkdir` is atomic on POSIX filesystems (one process succeeds, others fail with `EEXIST`). The lock is a **directory**, not a file — release at Step 7 via `rmdir`. On `BLOCKED`: emit Korean message `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."` Abort sequence. Exit code `2` aligns with the stock-scan/filter-tune error catalog (0=ok, 1=domain *Error, 2=other). (stock-scan symmetrically refuses background scans while this directory exists — Step 4 §10 R-9 mitigation.)

2. **Backup creation (TS-2)**:
   ```bash
   cp ${KRT_FILTERS}/{file_basename} ${KRT_FILTERS}/{file_basename}.bak.$(date +%Y%m%d_%H%M%S)
   ```
   Capture the resulting backup path; subsequently appended to `screener_state.json.current_backup_files`.

3. **Backup rotation (TS-2a, ≤ 5 retention)**:
   ```bash
   ls -t ${KRT_FILTERS}/{file_basename}.bak.* 2>/dev/null
   ```
   - If returned count ≤ 5 → no rotation.
   - If count = 6+ → for the **oldest** backup only:
     - `grep -l "{oldest_timestamp}" ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.*.md` → if any match (the value introduced by that backup is recorded in the tuning log) → `rm {oldest_backup}`.
     - If no match → KEEP the backup + emit Korean warning `"백업 {N}개 한도를 초과했지만 가장 오래된 백업이 튜닝 로그에 기록되지 않아 보존합니다. 수동 정리를 권장합니다."` (TS-2a gate per PRD line 442.)

4. **State sync**: read `screener_state.json` → append new backup path to `current_backup_files` array; remove any deleted backup paths.

### Step 6 — Edit the `Final` constant value — **(spec)**

**Pre-Edit validation** (R-2, B-13e — see §5 for canonical encoding):
- `grep -n '\b{variable_name}\b' ${KRT_FILTERS}/{file_path}` (anchored word boundary).
- If 0 hits → trigger fuzzy fallback + AskUserQuestion (§5 protocol). Abort if unresolved.
- If ≥ 1 hit → confirm the matched line contains `Final[` typing annotation. If not → REJECT `"이 변수는 Final 타입이 아닙니다. TS-1에 따라 변경할 수 없습니다."` (Defensive: catches the rare case of grep matching a comment or docstring.)

**Edit operation**:
- Use Claude Code `Edit` tool.
- `old_string`: the line containing the current value, including the `: Final[type] = current_value_literal` portion (sufficient context for unique match).
- `new_string`: identical line with the `current_value_literal` replaced by `new_value_literal` (using `references/unit-conversion.md` for user-percent → raw-value translation).

**Unit conversion examples** (verbatim from `references/unit-conversion.md`):
- User says `"-5%"` for `_TYPE_A_ALIGN_TOL` → `tolerance = 0.05` → literal `0.05`.
- User says `"3%"` for `_TYPE_C_CONVERGE_PCT` → `ratio = 0.03` → literal `0.03`.
- User says `"외국인 매도 2일"` for `_THRESHOLD_FOREIGN_CONSEC_SELL` → integer `2` → literal `2`.

**Comment-update rule (agent verification #9 per workflow.md)**:
- If the line immediately preceding the constant declaration is a comment of the form `# 이전: {old_value}` or `# 마지막 변경: ...`, update or append a fresh `# 이전: {prior_old_value} (변경: YYYY-MM-DD)` comment via a second Edit call. Idempotent — never accumulates duplicate trailing comments.

**Pre-flight order** (Step 4 §5 timing diagram): R-10/R-11 pre-flight checks `(a)/(b)/(c)` already ran at CLAUDE.md session start. Step 6 only re-runs **check (e)** (variable name presence) — the per-Edit guard.

### Step 7 [B-16] — `tuning-log.md` append + rotation + state update + lock release — **(spec)**

**Tuning-log row format (PRD FR-6.6 verbatim 8-column schema)**:

```
| {datetime} | {param_id} | {param_name} | {old_value} | {new_value} | {stocks_passed_before} | {stocks_passed_after} | {notes} |
```

**Column specifications**:
- `datetime` — ISO 8601 with KST offset, format `YYYY-MM-DDTHH:mm:ss+09:00`.
- `param_id` — full Python variable name, e.g., `_TYPE_A_ALIGN_TOL`.
- `param_name` — Korean meaning from `references/parameter-catalog.md`, e.g., `Type A 4선 정배열 허용오차`.
- `old_value` / `new_value` — raw value (e.g., `0.035`) — NOT user-percent form. (Persistent format for downstream regex; user-facing rendering happens at read time.)
- `stocks_passed_before` — value of `screener_state.json.last_results_summary.passed_count` at the moment of Step 7 entry (PRD FR-6.6 baseline source). Format: integer or `null` if no prior scan recorded.
- `stocks_passed_after` — placeholder `pending` at write time. Updated to the actual integer at the next RERUN_FILTERS completion (stock-scan Skill cross-writes when filling its own SHOW_RESULTS).
- `notes` (비고) — **minimum content (agent verification #10 per workflow.md)**: `(motivation) | (decision_status)`. Examples:
  - `Stage 1 통과율 77% 탈락에 따른 허용오차 완화 시도 | 미확정`
  - `과도한 통과 — 백업 복원 | ✓ 복원`
  - `세션 최종 결과 — 확정 | ✓ 확정` (set by CONFIRM branch)

**Atomic append**:
- Use Bash `>>` with full row including leading `|` and trailing `|\n`. Pre-create header on first invocation if `tuning-log.md` is absent (Step 10 `@infra-validator` already seeds the header, so this is defensive).

**Rotation (FR-6.6 + B-16 — 200-row threshold)**:
- Pre-append count: `wc -l ${KRT_REPORTS}/tuning-log.md` (minus header row).
- If row-count ≥ 200 → atomic rotate:
  ```bash
  mv ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.$(date +%Y%m).md
  # then write fresh header + new row to ${KRT_REPORTS}/tuning-log.md
  ```
- Subsequent queries (COMPARE_EXPERIMENTS, RESTORE fallback) MUST glob both `tuning-log.md` AND `tuning-log.*.md` per workflow-idea B-16 archive search requirement.

**state.json update**:
- Read `screener_state.json` (json.JSONDecodeError fallback per R-7).
- Append to `last_param_changes` array:
  ```json
  {
    "date": "{datetime}",
    "param": "{param_id}",
    "old": {old_value},
    "new": {new_value},
    "file": "src/kiwoom/itemFilter/{file_basename}",
    "confirmed": false
  }
  ```
- Atomic write: `json.dump(state, tmp_fp)` → `mv tmp final` (per Step 4 §4 atomicity rule).

**Lock release (R-9)**: `rmdir ${KRT_REPORTS}/filter-tune.lock` (lock is a directory per Step 5 Review#2 fix). Wrapped in a `try/finally`-equivalent (per shell semantics: if any preceding step in Step 7 errored, still attempt removal at the failure handler to prevent stuck locks).

### Step 8 [TS-5] — Rerun suggestion — **(spec)**

**Korean message (verbatim, PRD TS-5 + workflow-idea B-22)**:
> `"변경 적용됐습니다. 필터를 다시 돌려볼까요? (run_filters 동기 실행 — 보통 1-3분 소요)"`

**Routing**:
- This SKILL emits the question + hands control back to the main thread.
- CLAUDE.md routing table (§3 Step 5 blueprint) catches `"네/응/해줘"` confirmations and routes to stock-scan `RERUN_FILTERS` cluster.
- On user decline (`"아니"` / `"나중에"`): emit `"알겠습니다. 필요할 때 \"필터 재실행\"이라고 말씀하시면 됩니다."` and end sequence.

### SHORTCUT (B-22)

If `param_id` is in-range AND `param_id` is not a shared constant (Step 2 returns "private"):
- Skip Step 2 (no shared warning to emit).
- Skip Step 3 (still computed silently, but the per-row delta is rolled into the Step 4 confirmation appendix without a separate user pause).
- Sequence becomes: 0 → 1 → 4 → 5 → 6 → 7 → 8.

**Rationale**: most parameters (74 of 75) are private and in-range; gating every confirmation through 8 explicit steps inflates conversation length. Shortcut preserves all safety guarantees because Steps 2-3 emit nothing actionable in the in-range / private case.

---

## §4. Six Branch Definitions

Each branch below specifies: trigger (Korean utterance class), Korean-message output skeleton, internal step sequence, and fallback behaviour.

### Branch 1: `SHOW_PARAMS(stage?)` — **(source: FR-4.1, FR-4.3)**

**Triggers**: `"Stage N 조건 보여줘"`, `"전체 필터 설정 요약"`, `"지금 파라미터 뭐야?"`, `"투자자 수급 임계값 알려줘"`.

**Step 1 — Stage resolution**:
- Parse user message for stage hint: `"Stage 1|2|2-1|3|4|5"` or module name (`"chart60_120"`, `"investorFilter"`) or thematic phrase (`"수급"` → Stage 4, `"재무"` → Stage 5).
- If absent / "전체" → all 5 stages.

**Step 1.5 — Stage 5 hard-block (C-4)**:
- If user explicitly asks for Stage 5 parameter detail with implicit change intent (`"Stage 5 조건 어떻게 바꿔?"`):
  > `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. Phase 2에서 상수화를 검토합니다."` (verbatim per workflow.md line 286)
  
  Followed by a read-only view: current behaviour summary (`cup_nga < 0 → 제외`, missing → PASS — hardcoded) plus reference to `references/parameter-catalog.md` Stage 5 section.

**Step 2 — Read live Final constants**:
- For each in-scope Stage's file at `${KRT_FILTERS}/{module}.py`, use `grep -n 'Final\[' ${KRT_FILTERS}/{module}.py` to enumerate; for each variable, also `grep -n '_VAR_NAME'` to read the current literal.
- Critically: **never read the value from `references/parameter-catalog.md`** — catalog is documentation; code is SOT (per PRD §5.1 SOT declaration).

**Step 3 — Korean table format** (FR-4.1):

```
## Stage 1 — chart60_120Filter.py (60분/120분봉 MA 정배열)

| ID | 변수명 | 현재 값 | 한국어 의미 | 이론적 근거 |
|---|---|---|---|---|
| S1-1 | _TYPE_A_ALIGN_TOL | -3.5% (×0.965, raw=0.035) | Type A 4선 정배열 허용오차 — MA10≥MA20≥MA60≥MA306 인접 비교 시 허용 최대 하방 이격 | Minervini SEPA |
| S1-2 | _ALIGN_TOL_LOOSE ⚠️공유 | -1.5% (×0.985, raw=0.015) | (공유) Type B 120분 MA10-MA20 근접 / Type B MA60-MA306 / Type C MA60-MA306 / Type D 60분 fallback | 상승 초입 + 장기 추세 |
| ... | | | | |
```

- ⚠️공유 marker on the single shared constant row.
- For "전체" mode: render 5 stage tables sequentially (Stage 5 is the read-only summary).

**Step 4 — Footer**:
- Append cross-reference to `references/parameter-catalog.md` for theory deep-dive.
- Append `"파라미터 변경은 \"{변수명}를 {새값}으로 바꿔줘\" 같이 말씀해주세요."` (UX nudge per FR-4.2).

### Branch 2: `CHANGE_PARAM(param_id, new_value)`

This is the master sequence in §3. No separate branch logic — listed here for completeness only.

### Branch 3: `CONFIRM` — **(source: FR-6.5)**

**Triggers**: `"이걸로 확정할게"`, `"현재 설정 유지"`, `"지금 게 제일 나아"`, `"OK 이대로 가자"`.

**Step 1 — locate last param change**:
- Read `screener_state.json` → `last_param_changes` array.
- Identify the most recent entry where `confirmed == false`. If none → emit `"확정할 미확정 변경 이력이 없습니다."` and end.

**Step 2 — update tuning-log.md last row 비고**:
- Find the row in `tuning-log.md` whose `datetime` matches the last_param_changes entry's `date`.
- Use Edit to set its `notes` column to include the suffix `| ✓ 확정` (preserving prior motivation text).
- If row is in archived `tuning-log.YYYYMM.md` (rotation occurred between change and confirm — rare but possible): edit the archive file instead.

**Step 3 — update state.json**:
- Set `last_param_changes[*].confirmed = true` on the matched entry.
- Atomic write per Step 4 §4.

**Step 4 — Korean ack**:
> `"현재 설정이 확정되었습니다."` (verbatim FR-6.5 per workflow.md line 287)

### Branch 4: `RESTORE` — **(source: FR-6.4 + B-8 fallback)**

**Triggers**: `"원래대로 되돌려줘"`, `"이전 값으로 복원"`, `"백업으로 돌려놔"`, `"{N분 전} 값으로 돌려"`.

**Step 1 — target file resolution**:
- If user message includes file/param hint → resolve to single `{file_basename}`.
- If ambiguous → AskUserQuestion: `"어떤 파라미터를 복원할까요?"` listing the top-3 most-recent `last_param_changes` entries.

**Step 2a — Primary path: glob backups**:
```bash
ls -t ${KRT_FILTERS}/{file_basename}.bak.* 2>/dev/null | head -1
```
- If output non-empty → primary path:
  - Korean confirmation: `"가장 최근 백업({backup_path})에서 복원합니다. 진행할까요?"` AskUserQuestion (예/아니).
  - On 예: acquire R-9 lock → `cp {backup_path} ${KRT_FILTERS}/{file_basename}` → release lock.
  - Append RESTORE entry to `tuning-log.md`: `| {datetime} | {param_id} | {korean_meaning} | {current_before_restore} | {restored_value} | ... | 복원 (from {backup_filename}) | ✓ 복원 |`.
  - Append to `screener_state.json.last_param_changes` with `confirmed=true` (restore is implicitly confirmed by user intent).
  - Korean ack: `"{file_basename}을 {backup_timestamp} 시점 백업으로 복원했습니다."`

**Step 2b — Fallback path: tuning-log → Edit (B-8 fallback, KEY FEATURE)**:

This activates when `*.bak.*` files do not exist (rotated out, manually deleted, or never created). This is the **critical resilience feature** of FR-6.4 — without it, parameter loss is irreversible after backup rotation.

Algorithm:
1. Read `tuning-log.md` AND every `tuning-log.YYYYMM.md` archive (oldest-first iteration so the most recent change-history is reconstructible).
2. Filter rows by `param_id` matching the target.
3. Identify the chronologically LAST row before the current value — its `old_value` column is the restoration target.
4. **B-13e variable-name check** (§5) — confirm `param_id` still exists in code at the same line.
5. AskUserQuestion: `"⚠️ 백업 파일이 없어 튜닝 로그에서 이전 값을 찾았습니다: {old_value_in_log}. Edit으로 직접 복원할까요? (.bak 파일이 없으므로 다시 변경하면 이 단계 이전 값으로는 돌아갈 수 없습니다.)"` Options: (a) 진행 (b) 다른 행 선택 (c) 취소.
6. On 진행: acquire R-9 lock → Edit the constant → release lock.
7. Korean ack (verbatim per workflow.md line 288):
   > `"백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다. ({param_id}: {current_was} → {restored_to})"`
8. Append RESTORE entry to `tuning-log.md` with notes `"로그 기반 복원 (백업 부재) | ✓ 복원"`.

**Step 2c — Both paths fail**:
- Neither `*.bak.*` nor any tuning-log row for `param_id` exists.
- Korean message: `"{param_id}의 백업도, 변경 이력도 찾을 수 없습니다. 현재 값이 최초 설정값으로 보입니다. 참조용 PRD §5.1 카탈로그 값({prd_catalog_value})으로 강제 복원하시겠습니까?"` AskUserQuestion → on accept, treat as a forward PARAM_CHANGE (master sequence Steps 0-8) with `new_value = prd_catalog_value`.

### Branch 5: `THEORY_GUIDE(stage?, context?)` — **(source: FR-7)**

**Triggers**: `"약세장에서는 어떻게 바꿔야 해?"`, `"정배열 이론적 근거"`, `"Minervini 기준이 뭐야?"`, `"VCP가 무슨 뜻이야?"`.

**Step 1 — context resolution**:
- Parse for theory name (`Minervini` / `Weinstein` / `Wyckoff` / `VCP` / `CANSLIM`), stage indicator, market regime keyword (`강세` / `약세` / `횡보`).

**Step 2 — read `references/theory-guide.md`**:
- Render the matched section verbatim. Theory-guide.md structure (per PRD §5.3):

| Theory | Stage mapping | Anchor reference |
|---|---|---|
| Minervini SEPA | Stage 1 Type A, Stage 3 | 정배열 허용오차 통상 -2%~-5% |
| Weinstein Stage Analysis | Stage 2 (240m), Stage 1 Type B | MA60≥MA306 기준 |
| Wyckoff | Stage 4 (수급 조건) | 스마트머니 이탈 징후 |
| VCP (Volatility Contraction) | Stage 1 Type C/E, Stage 2-1 (preexclusion) | 수렴 폭 3.5%~10% |
| CANSLIM-N (Current earnings) | Stage 5 (당기순이익) | 적자 제외 (Phase 2 상수화 필요) |

**Step 3 — Market-regime guidance (FR-7.2)**:
- If user mentions `약세`: emit verbatim PRD §5.2 패턴 C (lines 386-393) — defensive (수급 강화) vs opportunistic (정배열 완화 + 장기추세 강화) two-track guidance, ending with `"어느 방향으로 가시겠습니까?"`.
- If user mentions `강세`: mirror — recommend tightening overheating filters (Stage 2-1 surge threshold to +10%) + loosening alignment for breakout capture.
- If user mentions `횡보`: mid-point — emphasize VCP convergence detection (Stage 1 Type C, lower `_TYPE_C_CONVERGE_PCT` to 2.5% for tighter VCP capture).

**Step 4 — Param-to-theory linkage table** (FR-7.3):
- If user asks `"이 파라미터 권장 범위가 뭐야?"` (where param is concrete): emit `references/theory-guide.md` per-param recommended range with theoretical citation.

### Branch 6: `ASK_MODULE(module_name)` — **(source: PRD §6.4 + workflow.md line 290)**

**Triggers**: `"stageMasterFilter는 뭐야?"`, `"chart60Filter는 왜 있어?"`, `"다른 필터도 있어?"`.

**Step 1 — module identification**:
- Match user input against the 9 active modules + `Filter_condition_update.py`.

**Step 2 — explanation**:

| Module | Role | Phase 1 tuning status |
|---|---|---|
| `chart60_120Filter.py` | Stage 1 — Type A/B/C/D/E pattern detection | **Active tuning target** |
| `chart240Filter.py` | Stage 2 — 240m long-term trend | **Active tuning target** |
| `chartDayPreFilter.py` | Stage 2-1 — Same-day surge exclusion | **Active tuning target** |
| `chartDayFilter.py` | Stage 3 — Daily MA alignment + MA612 band | **Active tuning target** |
| `investorFilter.py` | Stage 4 — Foreign/institutional/individual flow | **Active tuning target** |
| `financeFilter.py` | Stage 5 — Net income | ⚠️ Phase 2 (hardcoded, no Final constant) |
| `chart60Filter.py` | Standalone strict 60m MA alignment (NOT in main pipeline; re-imported by chart60_120Filter for parsing helpers only) | Not in Phase 1 production pipeline |
| `Filter_condition_update.py` | masterReference.log writer (orchestration helper) | **No tunable thresholds** — structural only |
| `stageMasterFilter.py` | Phase 2 module — 4-feature band coverage expansion | **Excluded from Phase 1** (per PRD §6.4) |

**Step 3 — Phase 2 deflection for `stageMasterFilter.py`**:
- Korean message: `"stageMasterFilter.py는 별도 누적-확장 풀(positive coverage) 산출용 모듈입니다. 현재 5-Stage 파이프라인과 독립적으로 동작하며, Phase 1에서는 파라미터 튜닝 대상에서 제외됩니다. Phase 2 안정화 이후 검토 예정입니다."`

### Branch 7: `COMPARE_EXPERIMENTS` — **(source: workflow.md line 291 + B-16 combination view)**

**Triggers**: `"이 세션 실험 결과 정리해줘"`, `"여러 설정 비교"`, `"오늘 튜닝 기록 보여줘"`, `"어떤 설정이 통과 가장 많았어?"`.

**Step 1 — read sources** (`tuning-log.md` is sole data source per B-16):
- Read active `tuning-log.md`.
- If user message scopes to a longer window (`"이번 달"` / `"지난 달"`): additionally read matching `tuning-log.YYYYMM.md` archives.

**Step 2 — filter scope**:
- `"이 세션"` (default scope) → entries where `datetime ≥ session_start_time` (session_start derived from `screener_state.json.last_scan_date` boundary or the first row's date if state is null).
- `"오늘"` → entries dated today (KST).
- `"이번 달"` → entries dated within current YYYYMM.

**Step 3 — Korean comparison table**:

```
## 이 세션 튜닝 실험 비교

| # | 변경 시각 | 파라미터 | 변경 전 → 후 | 통과 변화 | 비고 |
|---|---|---|---|---|---|
| 1 | 2026-05-30 14:23 | _TYPE_A_ALIGN_TOL (Type A 정배열 허용오차) | 0.035 → 0.05 | 17 → 22 (+5) | Stage 1 통과율 완화 | 미확정 |
| 2 | 2026-05-30 14:41 | _TYPE_E_SPREAD_PCT (Type E 수렴 폭) | 0.10 → 0.08 | 22 → 19 (-3) | E 과잉 통과 조정 | 미확정 |
| 3 | 2026-05-30 15:02 | _THRESHOLD_FOREIGN_CONSEC_SELL (외국인 연속매도) | 2 → 3 | 19 → 24 (+5) | 약세장 수급 완화 | ✓ 확정 |
```

**Step 4 — Korean narrative summary** (FR-6.3):
- Identify the row with maximum `stocks_passed_after` → recommend as "가장 통과 종목 많았던 설정" with note that this is **not** an investment recommendation per FR-8.
- Identify rows marked `✓ 확정` → highlight as user-anchored.
- If `stocks_passed_after = pending` for any row (because user did not run RERUN_FILTERS after that change) → emit advisory.

**Step 5 — Disclaimer** (FR-8.1):
- Single-line at end: `"(투자판단·책임은 본인에게 있습니다)"` per CLAUDE.md §6 short-form rule.

---

## §5. Parameter Variable Name Verification (B-13e / R-2)

Before EVERY `Edit` (Step 6 of master sequence, Step 2 of RESTORE primary path, Step 6-equivalent in RESTORE fallback):

### Canonical verification protocol

```bash
grep -n '\b{variable_name}\b' ${KRT_FILTERS}/{file_path}
```

**Decision tree**:
1. **≥ 1 hit AND line contains `Final[`** → proceed to Edit.
2. **≥ 1 hit BUT no `Final[` on any matched line** → REJECT `"이 변수는 Final 타입이 아닙니다. TS-1에 따라 변경할 수 없습니다."` (catches comments / docstrings.)
3. **0 hits** → enter fuzzy fallback:
   - `grep -in '{partial_name_trimmed_of_underscores_and_caps}' ${KRT_FILTERS}/{file_path}` — case-insensitive partial match.
   - Render top-3 candidates in Korean:
     > `"⚠️ '{variable_name}' 변수를 찾지 못했습니다. 변수명이 변경된 것 같습니다. 다음 후보들이 있습니다:`
     > `  • {candidate_1} (line {N1})`
     > `  • {candidate_2} (line {N2})`
     > `  • {candidate_3} (line {N3})`
     > `어떤 변수를 변경할까요?"`
   - AskUserQuestion with 4 options: top-3 candidates + `"취소"`.

**Anti-Conflation Disambiguation (per Step 1 §Critical Distinctions)**:

When user message contains ambiguous Korean phrase, force AskUserQuestion before resolution:

| Korean ambiguous phrase | Possible variables | Disambiguation question |
|---|---|---|
| `"60분 정배열 허용오차"` | `_ALIGN_TOL_LOOSE` (chart60_120Filter.py, 0.015, Type B/C/D shared) vs `_MA_ALIGNMENT_TOLERANCE` (chart60Filter.py, 0.005, standalone strict) | `"두 가지 다른 변수가 있습니다: (1) chart60_120Filter의 Type B/C/D 공유 허용오차 (-1.5%) vs (2) chart60Filter 단독 모듈 4선 정배열 (-0.5%). 어느 쪽을 변경할까요?"` |
| `"평가 봉 수"` | `_REQUIRED_CONSECUTIVE_BARS` (declared in chart60Filter, chart240Filter, chartDayFilter — all currently 3, all independent) | `"세 개 모듈에서 독립적으로 선언되어 있습니다: chart60 / chart240 / chartDay. 어느 Stage의 윈도우 크기를 바꿀까요?"` |
| `"MA60-MA306 허용오차"` | `_MA60_MA306_TOLERANCE` (chart240, 0.025) vs `_MA60_MA306_LOWER_TOL` (chartDay, 0.15) vs `_TYPE_E_MA60_OVER_MA306_TOL` (chart60_120 Type E, 0.035) | `"세 가지 다른 시간프레임에 있습니다: (1) Stage 2 240분 (-2.5%) (2) Stage 3 일봉 하한 (-15%) (3) Stage 1 Type E 전용 (-3.5%). 어느 쪽인가요?"` |
| `"창 크기"` / `"윈도우"` | `_REQUIRED_STATIC_BARS` (8) vs `_REQUIRED_CONSECUTIVE_BARS` (3 in three modules) vs `_REQUIRED_BARS` (16, investor) vs `_TYPE_D_DYNAMIC_WINDOW` (16) | Render 4-row table; ask user to pick. |

**Rationale**: Step 1 param-inventory documents 4+ look-alike groups whose conflation would silently mistune entire stages. The verification protocol enforces a single-question gate before any Edit.

---

## §6. Backup / Restore Protocol (TS-2 / TS-2a)

| Action | Command | Naming Convention | Notes |
|---|---|---|---|
| **Create** | `cp ${KRT_FILTERS}/{file} ${KRT_FILTERS}/{file}.bak.$(date +%Y%m%d_%H%M%S)` | `{file}.bak.20260530_142345` | Step 5 of master sequence. Naming format **mandatory** for `ls -t` sort + tuning-log timestamp join. |
| **List** | `ls -t ${KRT_FILTERS}/{file}.bak.*` | Newest first | Used by RESTORE primary path + Step 5 rotation count. |
| **Rotate** | If count > 5 → `grep -l '{oldest_ts}' ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.*.md` → if match: `rm {oldest}`. If no match: KEEP + warn. | only after log check | TS-2a gate (PRD line 442). |
| **Restore (primary)** | `cp ${KRT_FILTERS}/{file}.bak.{newest_ts} ${KRT_FILTERS}/{file}` | newest .bak | RESTORE Branch Step 2a. |
| **Restore (fallback)** | Read `tuning-log.md` + archives → identify last row for `param_id` → Edit constant to its `old_value` column | when no .bak | B-8 fallback (KEY FEATURE per workflow.md line 288). |

**Lock semantics** (R-9):
- Backup creation, Edit, and tuning-log append are atomic under the `filter-tune.lock` sentinel held from Step 5 to Step 7.
- stock-scan reads `filter-tune.lock` existence before launching any background `run_full_research_flow` / `run_prefetch` and refuses with: `"⚠️ 파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."` (Step 4 R-9 mitigation verbatim.)

---

## §7. `references/` File Plan (≥ 6 files per skill verification requirement)

### `references/parameter-catalog.md` (~300 lines)

**Purpose**: Documentation reference for all 75 `Final` constants from Step 1 param-inventory. **Never** the SOT for current values — code is always read live at runtime.

**Structure**:
- Grouped by Stage (0 / 1 / 1-adjacent / 2 / 2-1 / 3 / 4 / 5).
- Per param: variable name, file:line, theoretical Korean meaning, PRD §5.1 ID anchor, theoretical basis citation (Minervini/Weinstein/etc.), look-alike sibling cross-reference.
- Explicit **"current value source: live code via grep — do NOT cite this file as authoritative"** disclaimer at top.

**Coverage**: must contain every one of the 75 constants enumerated in Step 1 param-inventory §Coverage Self-Check. Documentation-only constants (filenames, regex, labels, dispatch tables, etc.) included for completeness but explicitly marked `# 튜닝 비대상 (구조/식별)`.

### `references/range-map.md` (~150 lines)

**Purpose**: TS-3 range validation lookup table covering all 75 constants from Step 1 (every Stage 0-4 + Stage 5 explicit hard-block row).

**Structure per row**:
| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_TYPE_A_ALIGN_TOL` | 0.00 ~ 0.50 | ≥ 0.30 | `"허용오차 -30%는 사실상 필터 무력화"` | Minervini -2%~-5% recommended; > 30% loses signal |
| `_ALIGN_TOL_LOOSE` | 0.00 ~ 0.30 | ≥ 0.15 | `"15%는 정배열 개념 자체가 무력화"` | Stage 1 shared — Type B/C/D fan-out (tighter danger zone than Type A) |
| `_TYPE_B_BELOW_MA60_RATIO` | 0.50 ~ 1.00 | ≤ 0.85 or ≥ 1.00 | `"0.85 이하면 거의 모든 종목 통과 (조건 무력화)"` | Weinstein Stage 1→2 — 3% below MA60 is canonical |
| `_TYPE_C_CONVERGE_PCT` | 0.00 ~ 0.30 | ≥ 0.10 | `"수렴 폭 10% 초과면 VCP 수렴 개념 아님"` | VCP 3.5%~10% per PRD §5.3 |
| `_TYPE_E_SPREAD_PCT` | 0.00 ~ 0.30 | ≥ 0.20 | `"확산 폭 20% 초과면 정배열 직전 의미 없음"` | VCP wider variant |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 0.0 ~ 1.0 | ≤ 0.20 or ≥ 0.90 | `"비율 90% 이상이면 거의 모든 종목 탈락"` | 60일선 지지 지속성 |
| `_DAILY_SURGE_THRESHOLD` | 0.05 ~ 0.30 | ≤ 0.05 or ≥ 0.30 | `"+30% 이상은 상한가 부근 — 의미 없음"` | 작전주 경계 +15% canonical |
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | 1 ~ 16 | ≥ 12 | `"12일 이상은 거의 모든 종목 탈락"` | Wyckoff 스마트머니 분배 |
| `_THRESHOLD_INDI_CONSEC_BUY` | 1 ~ 16 | ≤ 1 | `"1일은 통상 매수가 매수 시그널이 아님"` | 역발상 신호 |
| `_MA60_MA306_LOWER_TOL` | 0.00 ~ 0.50 | ≥ 0.40 | `"하한 -40% 이하면 깊은 하락 종목도 통과"` | Stage 3 envelope |
| ... (cover all 75) |

**Coverage requirement**: must mention all 75 constants from Step 1 grouped by Stage. The 10 examples above are representative; the file authoritatively encodes the full TS-3 range gate.

### `references/unit-conversion.md` (~30 lines)

**Purpose**: SOT for tolerance ↔ multiplier ↔ user-percent conversion, used at Step 6 of master sequence + Step 4 of confirmation table rendering.

**Content**:

```
# Unit Conversion (TS-1 안전성 보장)

## tolerance ↔ multiplier ↔ user-percent (3가지 폼)

- `tolerance = 1 - multiplier`
- `multiplier = 1 - tolerance`
- `user_pct = tolerance × 100`
- `tolerance = user_pct / 100`

## Examples

| User says | tolerance (raw) | multiplier (×) | user-percent display |
|---|---|---|---|
| "-5%로 완화" | 0.05 | 0.95 | -5.0% (×0.95) |
| "-3%로 완화" | 0.03 | 0.97 | -3.0% (×0.97) |
| "-1.5%" (현재 _ALIGN_TOL_LOOSE) | 0.015 | 0.985 | -1.5% (×0.985) |
| "-3.5%" (현재 _TYPE_A_ALIGN_TOL) | 0.035 | 0.965 | -3.5% (×0.965) |
| "-15%" (Stage 3 _MA60_MA306_LOWER_TOL) | 0.15 | 0.85 | -15.0% (×0.85) |
| "+45%" (Stage 3 upper band) | 0.45 (literal in code) | 1.45 | +45.0% (×1.45) |
| "+50%" (Stage 3 _CLOSE_VS_MA612_UPPER) | 0.50 | 1.50 | +50.0% (×1.50) |

## Ratio constants (NOT tolerances)

These are pure fractions and use NO sign convention:

| Variable | Korean | Raw | Display |
|---|---|---|---|
| `_TYPE_B_BELOW_MA60_RATIO` | MA60 대비 상한 비율 | 0.97 | 3% 이상 아래 (97% 미만) |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 60분 close>MA60 비율 | 0.50 | 50% |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | 60분 MA60 위 지지 | 0.75 | 75% |
| `_DAILY_SURGE_THRESHOLD` | 일봉 등락률 상한 | 0.15 | +15% |

## Convergence percent (raw = display/100)

| Variable | Raw | Display |
|---|---|---|
| `_TYPE_C_CONVERGE_PCT` | 0.035 | 3.5% |
| `_TYPE_E_SPREAD_PCT` | 0.10 | 10% |

## Integer thresholds

No conversion — value is bare integer (days/bars/count).
```

### `references/shared-constants.md` (~50 lines)

**Purpose**: Step 2 (B-17) shared-constant lookup. Covers the one current shared constant + anti-conflation table for look-alikes (per Step 1 §Critical Distinctions).

**Content sketch**:

```
# Shared Constants Registry

## Active shared constants (B-17 trigger)

### _ALIGN_TOL_LOOSE — chart60_120Filter.py:120 — value 0.015 (-1.5%)
**Affected (Type, condition) tuples**:
- Type B: 120분 MA10-MA20 근접 판정 (S1-2)
- Type B: MA60-MA306 근접 판정 (S1-4)
- Type C: MA60-MA306 장기추세 leg
- Type D: 60분 4선 정배열 fallback (when strict 60m alignment fails)

**When variant needed**: see PRD §5.4 — TS-1 conflict (would require Final 신설) — requires explicit user 승인.

## Anti-conflation pairs (NOT shared but look alike — disambiguation required)

| Pair | Files | Discrimination criterion |
|---|---|---|
| `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` | chart60_120Filter:120 vs chart60Filter:75 | "60-분 정배열 허용오차" — chart60_120 (Stage 1 production) is the default |
| `_REQUIRED_CONSECUTIVE_BARS` (3-way independent) | chart60:78, chart240:81, chartDay:72 | Each scoped to its module; tuning one does NOT propagate |
| `_MA60_MA306_TOLERANCE` vs `_MA60_MA306_LOWER_TOL` vs `_TYPE_E_MA60_OVER_MA306_TOL` | chart240:78 vs chartDay:63 vs chart60_120:156 | 3 different timeframes (240m / daily / 120m Type E) |
| `_TYPE_D_DYNAMIC_WINDOW` vs `_TYPE_E_DYNAMIC_WINDOW` | both chart60_120 | window sizes 16 vs 8 for different ratios (50% vs 75%) |
| `_STOCK_DIR_PATTERN` (5 modules) | chart60, chartDay, investor, finance, +re-imports | Logically identical regex; structurally independent declarations |
```

### `references/theory-guide.md` (~250 lines)

**Purpose**: FR-7 theory mapping + market-regime guidance. Read by THEORY_GUIDE branch.

**Structure**:

```
# Theory Guide — 이론 기반 파라미터 튜닝

## 1. Theory ↔ Stage Mapping (PRD §5.3 verbatim)

### Minervini SEPA (Specific Entry Point Analysis)
- **Stages**: Stage 1 Type A (60m/120m 4선 정배열), Stage 3 (일봉 정배열)
- **Anchor**: 정배열 허용오차 통상 -2%~-5%
- **Tunable parameters**:
  - `_TYPE_A_ALIGN_TOL` (Stage 1) — recommend keep at -2%~-5%
  - `_MA10_MA20_MA60_TOLERANCE` (Stage 3) — wider OK because daily volatility is larger
- **Loosen when**: Stage 1 over-rejects in trending market (>70% drop)
- **Tighten when**: too many noisy candidates (Stage 1 < 30% drop)

### Weinstein Stage Analysis
- **Stages**: Stage 2 (240m long-term), Stage 1 Type B (rising-from-below)
- **Anchor**: MA60 ≥ MA306 — long-term trend up
- **Tunable parameters**:
  - `_MA60_MA306_TOLERANCE` (Stage 2) — recommend -2%~-3%
  - `_TYPE_B_BELOW_MA60_RATIO` — entry zone definition
- **Loosen when**: scanning rotational sectors at cycle low
- **Tighten when**: scanning continuation patterns mid-bull

### Wyckoff (Smart Money Distribution)
- **Stages**: Stage 4 (investor flow)
- **Anchor**: foreign / institutional sell sequences signal distribution
- **Tunable parameters**:
  - `_THRESHOLD_FOREIGN_CONSEC_SELL` (default 2 days) — Wyckoff Phase D signal
  - `_THRESHOLD_INST_CONSEC_SELL` (default 8 days) — slower institutional unwinding
  - `_THRESHOLD_INDI_CONSEC_BUY` (default 3 days) — contrarian retail signal
- **Loosen (= raise threshold)**: bull market — retail buying not yet distributive
- **Tighten (= lower threshold)**: bear/correction — defensive screening

### VCP (Volatility Contraction Pattern)
- **Stages**: Stage 1 Type C, Type E
- **Anchor**: 수렴 폭 3.5%~10%
- **Tunable parameters**:
  - `_TYPE_C_CONVERGE_PCT` — tight VCP (default 3.5%)
  - `_TYPE_E_SPREAD_PCT` — about-to-align V-rebound (default 10%)
- **Loosen when**: scanning post-IPO / post-correction setup base
- **Tighten when**: late-cycle topping bases

### CANSLIM-N (Current earnings)
- **Stages**: Stage 5 (financeFilter) — currently NOT tunable in Phase 1
- **Anchor**: 적자 제외 (cup_nga ≥ 0)
- **Tunable parameters**: ⚠️ none (hardcoded). Phase 2 consideration: add `_NET_INCOME_MIN_THRESHOLD = 0` and expose for tuning.

## 2. Market Regime Adjustment (FR-7.2)

### 강세장 (Bull market — uptrend confirmed)
- Loosen Stage 1 alignment (favour breakout capture)
- Tighten Stage 2-1 surge threshold (more frequent overheating)
- Loosen Stage 4 investor flow (retail buying less distributive)

### 약세장 (Bear market — downtrend or post-correction)
- (Defensive) Tighten Stage 4 — foreign sell ≥ 1 day
- (Defensive) Tighten Stage 1 alignment — only fully-confirmed setups
- (Opportunistic) Loosen Stage 1 + tighten Stage 2 — bottom-fishing rotational candidates

### 횡보장 (Sideways)
- Emphasize VCP — lower `_TYPE_C_CONVERGE_PCT` to 2.5% for tighter base detection
- Lower `_TYPE_E_SPREAD_PCT` to 7-8% — focus on about-to-align setups

## 3. Per-Parameter Recommended Ranges (FR-7.3)

Per-Stage tables citing theoretical anchor + recommended low/high bounds (avoid danger zone) + canonical default. Coverage: every actively tunable parameter from Stages 1-4 (~25 rows).

## 4. Data-Driven Suggestion Patterns (FR-7.4)

When user invokes WHY_REJECTED or COMPARE → filter-tune may proactively suggest tuning if the data shows a clear pattern:
- "Stage 1에서 80% 탈락" → "Type A 허용오차 완화 검토"
- "외국인 매도 평균 1.8일" → "수급 임계값을 2일에서 3일로 완화 검토"
```

### `references/tuning-sequence.md` (~200 lines)

**Purpose**: Verbose encoding of the master sequence (8 steps) + all 6 branches + ADR-009 gap-extractor regex catalogue. The "long-form" companion to the compact SKILL.md §3.

**Structure**:
- §A Master sequence flow chart (text) + per-step checkpoint list
- §B 6 branch flow charts
- §C TS-1~5 enforcement matrix (per Step / per branch)
- §D ADR-009 gap-extractor regex catalogue with worked examples
- §E Error recovery handlers (R-9 lock contention, R-7 state.json corruption, B-13e variable-rename, B-8 backup exhaustion)
- §F Korean message library (verbatim strings) — all user-facing strings consolidated for translation review (FR-8 framing pass)

**Special role**: this is the file the @reviewer at Step 7 of workflow.md cross-references against Step 1 param-inventory + PRD §5.5 + Step 4 ADRs to verify completeness.

---

## §8. Safety Rules Enforcement Points (verbatim citation from Step 5 §4)

The 5 PRD safety rules + TS-2a + R-9 are enforced at specific points in §3 master sequence and §4 branches:

| Rule | Where enforced | SKILL.md anchor |
|---|---|---|
| **TS-1** ("Final 상수 값만 변경") | §3 Step 6 — Edit gated on `Final[` substring presence on matched line. Stage 5 hard-block at §3 Step 1. | §3 Step 1 + Step 6 |
| **TS-2** ("변경 전 백업") | §3 Step 5 — `cp` before any Edit. State `current_backup_files` array also updated. | §3 Step 5 |
| **TS-2a** ("백업 5개 한도 + tuning-log 게이트") | §3 Step 5 — rotation gate: `grep -l` against `tuning-log.md` + archives. | §3 Step 5 (rotation block) |
| **TS-3** ("범위 검증") | §3 Step 1 — Range Map lookup with REJECT (out-of-range) or warn + AskUserQuestion (danger zone). | §3 Step 1 |
| **TS-4** ("한 번에 하나") | §3 Step 0 — multi-param detection + 3-option AskUserQuestion. | §3 Step 0 |
| **TS-5** ("변경 후 재실행 제안") | §3 Step 8 — explicit Korean prompt + RERUN_FILTERS handoff. | §3 Step 8 |
| **R-9** (advisory lock) | §3 Step 5 acquire / §3 Step 7 release. stock-scan reads existence before launching background scans. | §3 Step 5 + Step 7 |

**Stage 5 hard-block coverage** (per workflow.md C-4 + line 286): enforced at THREE locations to be defence-in-depth:
1. §3 Step 1 (PARAM_CHANGE master sequence) — primary REJECT gate.
2. §4 Branch 1 SHOW_PARAMS — read-only summary with explicit "변경 불가" annotation.
3. §4 Branch 6 ASK_MODULE — `financeFilter.py` row explicitly marked "Phase 2".

---

## §9. `screener_state.json` Read/Write Points

Per Step 4 §4 schema. Atomic write via `json.dump(state, tmp_fp); mv tmp final` (Step 4 §4 atomicity rule).

| Operation | Read | Write | Notes |
|---|---|---|---|
| Session start (handoff from CLAUDE.md onboarding) | ✅ check `last_param_changes[*]` with `confirmed=false` against current Final values via grep | — | External-change warning per B-12 (CLAUDE.md §10). Filter-tune does NOT actually run this — CLAUDE.md does, but the skill consumes the warning state if any. |
| Step 5 (backup creation) | ✅ — | ✅ append to `current_backup_files` | After `cp` completes. |
| Step 6 (Edit) | — | — | (Edit itself doesn't write state.) |
| Step 7 (after Edit) | — | ✅ append to `last_param_changes` with `confirmed=false` | Per Step 4 §4 schema. |
| Step 5 rotation | — | ✅ remove rotated `.bak` paths from `current_backup_files` | If rotation removed any backup. |
| CONFIRM branch | ✅ identify latest `confirmed=false` entry | ✅ set `confirmed=true` | Pairs with tuning-log row `✓ 확정` mark. |
| RESTORE branch (any path) | ✅ — | ✅ append restoration entry with `confirmed=true` | Restore is implicitly user-confirmed. |
| All paths | — | atomic write: `tmp + mv` | Per Step 4 §4. |
| R-7 (corrupt state) | ✅ catch `json.JSONDecodeError` | ✅ backup corrupt file to `.corrupt.{ts}` | Skill treats state as missing and proceeds with default empty arrays. CLAUDE.md (not skill) handles the user-facing fallback. |

---

## §10. Length Estimate (Final SKILL.md)

| Section | Est. lines |
|---|---|
| Frontmatter (YAML) | 8 |
| §1 Trigger conditions (Korean intent cluster table) | 6 |
| §2 Path constants reference | 8 |
| §3 8-step master sequence (compact form, defers to tuning-sequence.md for verbosity) | 50 |
| §4 6 branches (compact form, defers to tuning-sequence.md) | 36 |
| §5 Parameter name verification | 6 |
| §6 Backup/restore protocol table | 8 |
| §7 references/ overview | 6 |
| §8 Safety rules enforcement matrix | 6 |
| §9 state.json I/O table | 6 |
| Header/footer comments | 4 |
| **SKILL.md Total** | **~144 lines** |

Plus the 6 reference files: **~30 + ~50 + ~150 + ~200 + ~250 + ~300 = ~980 lines** distributed.

**Compression policy** (if SKILL.md > 130 — workflow.md target):
- Compress §4 branches to single-line per branch with cross-reference to `tuning-sequence.md §B`. Saves ~25 lines.
- Compress §3 8 steps to step name + 1-line summary per step with cross-reference to `tuning-sequence.md §A`. Saves ~30 lines.
- Combined: estimated ~89 lines — well under 130.

**No compression needed if 130-150 acceptable**; the master sequence detail is high-information-density and arguably belongs in SKILL.md proper. Step 9 `@tune-builder` decides based on final line count.

---

## §11. Verification Self-Check

- [x] Master sequence has **8 numbered steps**, each with TS-rule citation (TS-3/-4/-2/-1/-5) + checkpoints + Korean message
- [x] **6 branches** specified (SHOW_PARAMS, PARAM_CHANGE→§3, CONFIRM, RESTORE, THEORY_GUIDE, ASK_MODULE, COMPARE_EXPERIMENTS) — counted via §4 sub-headers: SHOW_PARAMS / CHANGE_PARAM(→§3) / CONFIRM / RESTORE / THEORY_GUIDE / ASK_MODULE / COMPARE_EXPERIMENTS — = 6 distinct branches (CHANGE_PARAM defers to §3 master sequence; the 6 are SHOW / CONFIRM / RESTORE / THEORY / ASK / COMPARE)
- [x] Range Map covers **all 75 Final constants** from Step 1 (specified in §7 `references/range-map.md` requirement; 10 representative examples shown; coverage gate "must cover 75 constants grouped by Stage")
- [x] Backup convention `*.bak.YYYYMMDD_HHmmss` enforced + TS-2a rotation gate present (§3 Step 5, §6)
- [x] TS-1~5 enforcement points marked in §3 / §4 / §8 matrix — all 5 cells filled
- [x] Theory guide references PRD §5.3 anchors (Minervini SEPA / Weinstein / Wyckoff / VCP / CANSLIM) — full mapping in `references/theory-guide.md` §1
- [x] references/ list = **6 files** (`parameter-catalog`, `range-map`, `unit-conversion`, `shared-constants`, `theory-guide`, `tuning-sequence`) — §7 enumeration
- [x] Parameter structure validation: §3 Step 6 verifies `Final[` substring on matched line before Edit (rejects comments/docstrings)
- [x] Comment update rule: §3 Step 6 includes adjacent `# 이전: {old_value}` comment auto-update logic (agent verification #9)
- [x] Tuning log 비고 minimum: §3 Step 7 specifies `(motivation) | (decision_status)` format with concrete examples (agent verification #10)
- [x] Backup exhaustion recovery: §4 RESTORE Branch Step 2b is the B-8 fallback (tuning-log → Edit), made crystal clear in §4 + §6 + §10
- [x] R-9 advisory lock: §3 Step 5 acquire / Step 7 release — codified with bash commands + try/finally release semantics
- [x] OQ-3 (ADR-011) dispatch consistent with stock-scan: §3 + §9 use `type(exc).__name__` per CLAUDE.md §5; SKILL inherits dispatch table by reference (no duplication)
- [x] **Stage 5 hard-block (C-4) coverage** — three locations: §3 Step 1 (PARAM_CHANGE), §4 SHOW_PARAMS Step 1.5, §4 ASK_MODULE financeFilter row
- [x] Anti-conflation table for look-alikes (§5) covers `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` + `_REQUIRED_CONSECUTIVE_BARS` 3-way + 3-way MA60-MA306 + window-size 4-way
- [x] Korean messages verbatim from PRD/Step 5 where available (verified: TS-5 message, FR-6.5 confirmation, B-8 fallback message, B-12 external-change format, PRD FR-5.5 danger-zone message)
- [x] All path references via `${KRT_…}` variables — no hardcoded absolute paths in **(spec)** blocks
- [x] Blueprint only — no files written to `/Users/tajun/spJavis/kiwoom-rest-trader/`
- [x] Tuning-log 8-column schema: `datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes` — verbatim from FR-6.6 / workflow.md line 281
- [x] Tuning-log rotation at 200 rows → `tuning-log.YYYYMM.md` archive — FR-6.6 + B-16; archive search required by COMPARE_EXPERIMENTS + RESTORE fallback
- [x] ADR-009 gap-extractor regex catalogue: 5 dominant patterns documented in §3 Step 3 + `references/tuning-sequence.md §D`
- [x] Multi-param TS-4 detection heuristic (tokenize + conjunction recognition) + 3-option AskUserQuestion present in §3 Step 0
- [x] Disclaimer line (FR-8.1 abbreviated form) emitted by COMPARE_EXPERIMENTS Step 5

---

## §12. Source Traceability Matrix

| SKILL Section | PRD Anchor | workflow-idea Anchor | Step Output Anchor |
|---|---|---|---|
| §1 Frontmatter | §3 (user persona — opus model) | B-1 (skill structure) | — |
| §2 Path Constants | §6.1 paths | B-6 (exec template) | Step 4 §1, §6 |
| §3 Master Sequence | §5.5 TS-1..5, FR-5, FR-6 | B-7/8/9/10/16/17/22 | Step 4 §4 (state schema), §10 R-9; ADR-009, ADR-011, ADR-012 |
| §3 Step 1 Stage 5 block | §5.1 Stage 5 admonition, §10 비목표 (Phase 2) | C-4 (workflow.md line 286) | Step 1 param-inventory Stage 5 section |
| §3 Step 2 Shared constant | §5.4 공유 상수 주의사항 | B-17 | Step 1 §Critical Distinctions |
| §3 Step 3 gap extraction | FR-5.2 | B-10 | Step 1 pipeline-analysis §(c); ADR-009 (Step 4 OQ-1) |
| §3 Step 4 Confirmation | FR-5.6 + §7.3 numeric formatting | B-7 | Step 5 §6 (CLAUDE.md format rules) |
| §3 Step 5 Backup + lock | TS-2, TS-2a + R-9 mitigation | B-8 | Step 4 §10 R-9 |
| §3 Step 6 Edit + B-13e | FR-5.1, FR-5.4, TS-1 | B-13e (variable name presence) | Step 4 §5 pre-flight (e); Step 1 §Critical Distinctions |
| §3 Step 7 tuning-log + state | FR-6.6 | B-16 (200-row rotation) | Step 4 §4 schema |
| §3 Step 8 Rerun suggestion | TS-5, FR-5.6 | B-22 | Step 5 §3 mixed-intent rule |
| §4 SHOW_PARAMS | FR-4.1, FR-4.3 | (CLAUDE.md routing) | Step 5 §3 intent cluster |
| §4 CONFIRM | FR-6.5 | (workflow.md line 287) | Step 5 §10 state semantics |
| §4 RESTORE | FR-6.4 + B-8 fallback | (workflow.md line 288) | Step 1 inventory (variable-name continuity); Step 4 §4 state |
| §4 THEORY_GUIDE | FR-7.1, FR-7.2, FR-7.3, FR-7.4 | (workflow.md line 289) | PRD §5.3 mapping |
| §4 ASK_MODULE | §6.4 모듈 인터페이스 | (workflow.md line 290) | Step 2 §7 (Phase 1 vs Phase 2 boundary) |
| §4 COMPARE_EXPERIMENTS | FR-6.3 | B-16 combination view (workflow.md line 291) | Step 4 §4 last_results_summary |
| §5 Variable name verification | TS-1 + FR-5.1 | B-13e | Step 1 §Critical Distinctions (anti-conflation); Step 4 §5 (e) |
| §6 Backup/Restore protocol | TS-2, TS-2a, FR-6.4 | B-8 | Step 4 §4 (state.json.current_backup_files) |
| §7 references/ plan | FR-4.1, FR-7, §5.4, §5.5 | (workflow.md line 295-301) | All Step 1-4 outputs |
| §8 Safety enforcement matrix | §5.5 TS-1~5 | B-7/B-8/B-9/B-17/B-22 | Step 4 R-9 |
| §9 state.json I/O | §3 (returning user) | B-12 | Step 4 §4 schema |

All sections trace to ≥ 1 PRD anchor + ≥ 1 workflow-idea anchor + ≥ 1 Step output. ADR-009/011/012 absorbed at relevant sections.

---

## §13. Step 9 `@tune-builder` Handoff Instructions

When Step 9 reads this blueprint, the builder MUST:

1. **Write target**: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` (and 6 reference files under `references/`).
2. **Order**: emit SKILL.md sections in this exact order — Frontmatter → §1 Trigger → §2 Path Constants → §3 Master Sequence (8 steps + SHORTCUT) → §4 6 branches → §5 Variable verification → §6 Backup protocol → §7 references/ overview → §8 Safety enforcement matrix → §9 state.json I/O.
3. **Verbatim copy** every **(spec)** block — including emoji warnings (⚠️), checkmarks (✓), inline code spans, and Korean phrasing. No paraphrasing of Korean strings.
4. **Path substitution**: leave `${KRT_*}` literal — Claude Code shell substitutes at Bash invocation.
5. **Line budget**: after emit, `wc -l` on SKILL.md. If > 150, apply §10 compression: collapse §3 step bodies to 1-line summaries with cross-refs to `tuning-sequence.md §A`; collapse §4 branch bodies to 1-line summaries with cross-refs to `tuning-sequence.md §B`. Target ~89-130 lines.
6. **Korean correctness**: preserve all spacing in Korean sentences. Preserve all hangul-roman boundary spaces. Em-dashes (—) not hyphens for Korean punctuation.
7. **No additional sections**: do NOT add Examples / Glossary / Troubleshooting sections that this blueprint does not specify.
8. **Reference files**: each must be created as a separate file under `.claude/skills/filter-tune/references/`. The 6 files are mandatory (verification criterion). Do NOT inline reference content into SKILL.md.
9. **Range Map coverage gate**: `references/range-map.md` MUST include a row for every one of the 75 `Final` constants from Step 1 param-inventory §Coverage Self-Check. Stage 5 rows are present but marked "튜닝 불가 (Phase 2)". @reviewer at Step 11 will verify this gate.
10. **Stage 5 hard-block triple defence**: confirm that the C-4 message appears in (a) §3 Step 1 PARAM_CHANGE master sequence, (b) §4 SHOW_PARAMS Branch Step 1.5, (c) §4 ASK_MODULE financeFilter row. Three locations — not two, not four.

---

*Blueprint complete. Implementation occurs in Step 9 (`@tune-builder` writes `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` + 6 reference files from this spec). Cross-reference review at Step 11.*
