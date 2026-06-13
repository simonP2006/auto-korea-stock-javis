---
name: filter-tune
description: Kiwoom filter parameter tuning — interactive Korean-language fine-tuning with safety rails (TS-1~5 enforced). Handles SHOW_PARAMS, CHANGE_PARAM, CONFIRM, RESTORE, COMPARE_EXPERIMENTS, THEORY_GUIDE, ASK_MODULE.
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
maxTurns: 40
---

# filter-tune SKILL

PG-2(파라미터 튜닝 — paramount goal) 전담 Skill. 5-Stage 필터 파이프라인의 `Final` 상수 가시화·변경·복원·이론 해설을 한국어 자연어로 수행한다. 스캔 실행(SCAN_TODAY/SHOW_RESULTS/WHY_REJECTED/COMPARE 등)은 **stock-scan Skill** 소관이며 본 Skill은 절대 다루지 않는다. 본 Skill은 PG-1과 직교(orthogonal)하며, `Final` 상수 값 외 어떠한 코드 로직(조건문/루프/타입 시그니처)도 수정하지 않는다.

## §1. 트리거 조건

CLAUDE.md `Intent Routing` 테이블의 다음 7개 클러스터가 본 Skill로 라우팅된다:

| Cluster | → Branch / Master Action |
|---|---|
| `SHOW_PARAMS` | §4 SHOW_PARAMS branch |
| `CHANGE_PARAM` | §3 PARAM_CHANGE master sequence (8 steps) |
| `CONFIRM` | §4 CONFIRM branch |
| `RESTORE` | §4 RESTORE branch (primary + tuning-log fallback) |
| `COMPARE` (params 스코프) | §4 COMPARE_EXPERIMENTS branch |
| `THEORY_GUIDE` | §4 THEORY_GUIDE branch |
| `ASK_MODULE` | §4 ASK_MODULE branch (inline answer w/ Phase 2 deflection) |

**Mixed-intent 규칙** (CLAUDE.md §Intent Routing 하단 verbatim): `"필터 바꾸고 다시 돌려줘"` → 본 Skill `CHANGE_PARAM` 완료 → 사용자 확인 → stock-scan `RERUN_FILTERS`. §3 Step 8이 그 seam이다.

## §2. 경로 상수

CLAUDE.md `Path Constants` 섹션의 값을 그대로 사용한다 (재정의 금지):
- `${KRT_ROOT}`, `${KRT_PYTHON}`, `${KRT_REPORTS}`, `${KRT_FILTERS}`, `${KRT_SCRIPTS}`

본 Skill 특정 경로:
- `${KRT_REPORTS}/tuning-log.md` — Step 7 append target / COMPARE_EXPERIMENTS / RESTORE fallback 소스.
- `${KRT_REPORTS}/tuning-log.YYYYMM.md` — 200행 초과 시 회전 아카이브 (B-16).
- `${KRT_REPORTS}/screener_state.json` — `last_param_changes` / `current_backup_files` 단일 writer (cross-skill 경계: stock-scan은 READ-only).
- `${KRT_REPORTS}/filter-tune.lock` — **디렉터리** 형태의 R-9 advisory lock (Step 5 acquire / Step 7 release).
- `${KRT_REPORTS}/{YYYYMMDD}/masterReference.log` — Read-only; Step 3 gap-impact 추정 (ADR-009).
- **Edit 단일 쓰기 대상**: `${KRT_FILTERS}/*.py` 내 `Final` 상수 값만 (TS-1).
- **Python 호출 범위**: 본 Skill은 `${KRT_PYTHON}`을 **읽기 전용 결정론 가드**(`.claude/skills/filter-tune/scripts/` — §11)에 한해 직접 호출한다. 가드는 파일을 수정하지 않는다. 필터 재실행은 직접 하지 않고 Step 8에서 stock-scan에 위임한다.
- `.claude/skills/filter-tune/scripts/` — 결정론 가드 스크립트 디렉터리 (`validate_param_values.py` / `unit_conversion.py` / `param_ast.py`, read-only, §11).

## §3. Master Tuning Sequence — `PARAM_CHANGE(param_id, new_value)` (8-step + SHORTCUT)

전체 상세 (regex 카탈로그·worked example·Korean string library)는 `references/tuning-sequence.md` 참조. 여기서는 spec verbatim 요약만.

### Step 0 [TS-4] — Multi-param 감지

**Trigger**: 한 turn에서 ≥2개의 distinct `param_id`(한국어 alias 또는 `_VARIABLE_NAME`)가 `"그리고/또/도/와/,"` 등 연접 절로 등장 시.

**Verbatim Korean warning** (PRD TS-4 + B-22 line 274):
> `"한 번에 하나씩 변경을 권장합니다. 동시에 여러 파라미터를 바꾸면 어느 변경이 결과에 어떤 영향을 줬는지 분리하기 어렵습니다. 어떻게 진행하시겠습니까?"`

**AskUserQuestion (3 옵션, P4 ≤4)**:
1. `"하나씩 차례대로 변경하기"` → 각 `param_id`마다 Steps 1-8 직렬 loop. 각 완료 후 `"{param_id}_N 변경이 완료됐습니다. 다음 파라미터({param_id}_N+1)를 계속 진행할까요?"`
2. `"한 번에 모두 변경하기 (영향 추적 불가)"` → 각 param Steps 1-7 (중간 확인 없음). Step 8은 마지막에 1회만.
3. `"취소"` → 전체 PARAM_CHANGE abort.

동일 turn-cluster 내 옵션 2 명시 승인 후 재경고 없음 (idempotent).

### Step 1 [B-9, TS-3] — Range Map 조회 + Stage 5 hard-block

**Step 1.−1 — [자동 검증] 값 무결성 게이트 (§11)**: PARAM_CHANGE turn 시작 시 1회 실행:
```
cd ${KRT_ROOT} && ${KRT_PYTHON} .claude/skills/filter-tune/scripts/validate_param_values.py
```
- exit 0 → catalog/range-map/unit-conversion의 모든 문서 값이 라이브 코드와 일치. 진행.
- exit 1 → 문서 드리프트. 출력된 불일치 항목을 한국어로 사용자에게 경고하고, 이후 모든 현재값은 **라이브 grep만 권위 출처로 사용**한다 (catalog 표기값 인용 금지).

**Step 1.0 — Keyword pre-check (Review#3 fix, catalog 조회 BEFORE 발화)**:
사용자 발화 원본에서 Stage-5 / financeFilter / 당기순이익 keyword를 먼저 스캔. 트리거 (어느 하나라도 일치):
- 부분문자열 `cup_nga` (대소문자 무시)
- 부분문자열 `당기순이익`
- 부분문자열 `financeFilter` / `finance_filter` / `finance Filter` (대소문자 무시)
- 부분문자열 `Stage 5` / `stage5` / `재무 단계` / `5단계`
- 부분문자열 `순이익` AND 변경의도 동사 (`바꿔` / `변경` / `수정` / `튜닝` / `올려` / `내려` / `늘려` / `줄여`) 공존

일치 시 → 아래 Step 1.2 verbatim C-4 메시지로 즉시 REJECT, 본 turn 종료. **근거**: workflow.md §6 L286 + PRD §5.1 Stage 5 admonition — financeFilter는 `Final` 상수 zero이므로 catalog lookup이 비-Stage5 후보를 fuzzy fallback으로 반환해 hard-block을 우회할 수 있다. 본 keyword pre-check가 **primary guard**, Step 1.2 catalog 기반은 **secondary guard**.

**Step 1.1 — Catalog 기반 `param_id` 해소**:
`references/parameter-catalog.md`로 한국어 alias → `param_id` 해소. 실패 시 §5 anti-conflation 표 우선 적용 → 그래도 모호하면 AskUserQuestion으로 disambiguate.

**Step 1.2 — Stage 5 hard-block (C-4, secondary guard)**:
해소된 `param_id`가 `financeFilter.py` 소유면 REJECT verbatim:
> `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. 당기순이익 판정(cup_nga < 0)이 하드코딩 비교문이고 Final 상수가 존재하지 않습니다. Phase 2에서 상수화를 검토합니다."`

본 turn 종료, Step 2 진입 금지.

**Step 1.3 — Range check** (`references/range-map.md`):
- `new_value ∈ physical range AND ∉ danger zone` → Step 2.
- `new_value ∈ danger zone` (예: tolerance ≥ 0.30 → 사실상 무력화) → Korean warning + AskUserQuestion (3옵션):
  > `"허용오차 -{X}%면 사실상 필터가 무력화됩니다. 정말 이 값으로 진행할까요?"`
  옵션: (a) 그대로 진행 (b) 안전 범위 권장값({suggested})으로 변경 (c) 취소.
- `new_value ∉ physical range` → REJECT (override 불가):
  > `"{param_korean_name}의 물리적 범위는 {range_min} ~ {range_max}입니다. 입력하신 {new_value}는 범위를 벗어났습니다. (이론적 근거: {basis})"`

### Step 2 [B-17] — 공유 상수 영향 공개

`references/shared-constants.md` 조회. **공유**(현재 유일: `_ALIGN_TOL_LOOSE` — chart60_120Filter.py:120) 일 경우 verbatim 영향 목록 표출:
> `"⚠️ 이 상수는 공유 상수입니다. 변경 시 다음 조건들이 동시에 영향을 받습니다:`
> ` • Type B — 120분 MA10-MA20 근접 판정`
> ` • Type B — MA60-MA306 근접 판정`
> ` • Type C — MA60-MA306 장기추세 leg`
> ` • Type D — 60분 4선 정배열 fallback`
> `특정 Type만 조정하려면 해당 Type 전용 상수 신설이 필요합니다 (TS-1 로직 변경 — 사용자 명시적 승인 필요)."`

**Private**(나머지 74개): 메시지 skip → Step 3.

### Step 3 [B-10] — masterReference.log gap 추정 (ADR-009)

1. `latest_date = screener_state.json.last_scan_date` → `${KRT_REPORTS}/{latest_date}/masterReference.log`. fallback: `reports/*/masterReference.log` glob의 최신 mtime.
2. 부재/비어있음 → `"추정 데이터 없음 — masterReference.log이 비어있거나 부재합니다. 정확한 영향은 변경 후 run_filters 재실행으로 확인하세요."` Step 4로 advisory 전달.
3. 존재 → `references/tuning-sequence.md §D` regex 카탈로그(MA_ALIGNMENT / MA_BAND_PCT / DAILY_SURGE / INVESTOR_CONSEC / FINANCE_CUP_NGA 5종)로 `(actual, threshold, unit)` 추출 → 새 값으로 row-별 `would_pass` 재계산.
4. 집계 Korean line: `"masterReference.log {M}개 행 중 {N}개에서 gap 추출. {delta} {direction} (추정 정확도 {N/M*100:.0f}%)."` (direction: `"개 추가 통과 예상"` / `"개 추가 탈락 예상"` / `"개 변화 없음"`).
5. `N/M < 0.5` → "추정 데이터 부족" advisory만, 수치 delta 미제공.

### Step 4 [B-7] — 확인 테이블

**Verbatim Korean 표** (B-7 + FR-5.6):

```
| 파라미터 | 현재 값 | 변경 후 |
|---|---|---|
| {var_name} ({Korean meaning}) | {current_value_display} | {new_value_display} |
```

**Display rule** (`references/unit-conversion.md`): tolerance → raw + `-X.X% (×Y.YYY)` 동시 / ratio → raw + `Z%` 동시 / integer → bare (`2일`).

**Appendix**: 공유 상수 경고(Step 2) collapsed re-emit / Step 3 delta `"예상 영향: 약 {delta}개 종목 추가 통과 (추정 정확도 {N/M*100:.0f}%)"` 또는 `"예상 영향: 추정 데이터 없음 (run_filters 재실행으로 정확한 결과 확인)"`.

**AskUserQuestion (3옵션)**: (1) `"적용 (Edit 진행)"` → Step 5 / (2) `"다른 값으로 시도"` → 새 값 입력 → Steps 1-4 loop / (3) `"취소"` → `"변경을 취소했습니다."`로 abort.

### Step 5 [B-8, TS-2, TS-2a, R-9] — 백업 + lock 획득 (mkdir 원자성 — Review#2 fix)

1. **R-9 advisory lock acquire — atomic mkdir (TOCTOU-safe)**:
   ```bash
   if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then
     # lock acquired — proceed
     true
   else
     # contention — another instance owns the lock; refuse
     echo "BLOCKED" >&2; exit 2
   fi
   ```
   `mkdir`는 POSIX에서 atomic — 한 프로세스만 성공, 나머지는 `EEXIST`. 락은 **디렉터리**이지 파일이 아니다 — Step 7에서 `rmdir`로 해제. BLOCKED 시 Korean:
   > `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."`
   abort, exit 2 (CLAUDE.md exit code 분류 — 그 외 예외).

2. **Backup (TS-2)**:
   ```bash
   cp ${KRT_FILTERS}/{file_basename} ${KRT_FILTERS}/{file_basename}.bak.$(date +%Y%m%d_%H%M%S)
   ```
   생성된 `.bak` 경로를 `screener_state.json.current_backup_files`에 append.

3. **Rotation (TS-2a, ≤ 5 보존)**:
   ```bash
   ls -t ${KRT_FILTERS}/{file_basename}.bak.* 2>/dev/null
   ```
   count ≤ 5 → no rotation. count = 6+ → 가장 오래된 1개만:
   - `grep -l "{oldest_timestamp}" ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.*.md` → 매치 있음 → `rm {oldest_backup}`.
   - 매치 없음 → KEEP + Korean warning `"백업 {N}개 한도를 초과했지만 가장 오래된 백업이 튜닝 로그에 기록되지 않아 보존합니다. 수동 정리를 권장합니다."` (PRD line 442 gate).

4. **State sync**: `screener_state.json` Read → `current_backup_files` append + 삭제 path 제거. 원자적 `tmp + mv` write.

### Step 6 — Edit `Final` 상수 값

**Pre-Edit (R-2, B-13e — §5 canonical)**:
- `grep -n '\b{variable_name}\b' ${KRT_FILTERS}/{file_path}` (word boundary).
- 0 hits → fuzzy fallback + AskUserQuestion (§5). 미해결 시 abort.
- ≥1 hits AND 해당 line이 `Final[` 포함 → 진행. 미포함 → REJECT:
  > `"이 변수는 Final 타입이 아닙니다. TS-1에 따라 변경할 수 없습니다."`

**Edit 연산**:
- `old_string`: `: Final[type] = {current_literal}` 전체 context 포함.
- `new_string`: 동일 line, literal만 `references/unit-conversion.md` 변환 후 교체.
- **[자동 검증] 변환 round-trip (§11)** — 퍼센트→literal 변환이 일어나는 tolerance 계열에 한해, Edit 직전 `new_string`의 literal을 검증:
  ```
  cd ${KRT_ROOT} && ${KRT_PYTHON} .claude/skills/filter-tune/scripts/unit_conversion.py --verify {new_literal} {부호포함_user_pct}
  ```
  exit 0 → Edit 진행. exit 1 → **Edit 중단**(예: 사용자가 "-5%"라 했는데 0.95를 기입하려는 경우). `--pct {부호포함_user_pct}`로 올바른 literal 재확인 후 재시도. (ratio/정수 파라미터는 변환이 항등이므로 본 검증 생략.)

**Comment auto-update (workflow.md agent verification #9)**: 직전 line이 `# 이전: {old_value}` 또는 `# 마지막 변경: …` 형식이면 2차 Edit으로 `# 이전: {prior_old_value} (변경: YYYY-MM-DD)` 갱신/추가 (idempotent — 중복 누적 금지).

### Step 7 [B-16] — tuning-log append + rotation + state + lock release

**Tuning-log 8-column 스키마 (PRD FR-6.6 verbatim, Review#1 canonical)**:

```
| datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |
```

**Column 규격**:
- `datetime` — ISO 8601 KST: `YYYY-MM-DDTHH:mm:ss+09:00`.
- `param_id` — full Python 변수명 (예: `_TYPE_A_ALIGN_TOL`).
- `param_name` — `references/parameter-catalog.md`의 한국어 의미 (예: `Type A 4선 정배열 허용오차`).
- `old_value` / `new_value` — raw value (예: `0.035`). **NOT** user-percent. (downstream regex 안정성; user-facing 렌더링은 read 시점에 수행.)
- `stocks_passed_before` — write 순간 `screener_state.json.last_results_summary.passed_count` (FR-6.6 baseline). 정수 또는 prior scan 부재 시 `null`.
- `stocks_passed_after` — write 시점 placeholder `pending`. **filter-tune이 단독 writer**: 가장 최근 `pending` 행을 `screener_state.json.last_results_summary.passed_count`로 backfill (게이트: `last_results_summary.scan_date`가 해당 행 `datetime` 이후 rerun 증명 + 더 최근 `pending` 행 없음 + B-12 외부변경 검사 통과). 미충족 시 `pending` 유지(거짓 추정 금지). backfill 발동 지점: CONFIRM · 다음 CHANGE_PARAM Step 7 · COMPARE_EXPERIMENTS read-time. stock-scan은 이 칸을 쓰지 않는다(전 칼럼 READ-only).
- `notes` — minimum: `(motivation) | (decision_status)`. 예시:
  - `Stage 1 통과율 77% 탈락에 따른 허용오차 완화 시도 | 미확정`
  - `과도한 통과 — 백업 복원 | ✓ 복원`
  - `세션 최종 결과 — 확정 | ✓ 확정` (CONFIRM branch가 설정)

**Atomic append**: Bash `>>`로 leading `|` + trailing `|\n` 전체 row. 헤더 부재 시(첫 호출) 헤더 선재 작성 (Step 10 `@infra-validator`가 시드, 본 동작은 방어용).

**Rotation (200행)**:
- `wc -l ${KRT_REPORTS}/tuning-log.md` − 헤더행 ≥ 200 →
  - **회전 전 backfill sweep**: 라이브 파일의 해소 가능한 최신 `pending` 행을 위 게이트로 채운 뒤, 남은 미해소 `pending` 셀은 `미측정`(terminal)으로 동결 — 아카이브가 영구 `pending`을 들고 가지 않도록.
  ```bash
  mv ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.$(date +%Y%m).md
  # then write fresh header + new row to ${KRT_REPORTS}/tuning-log.md
  ```
- 후속 COMPARE_EXPERIMENTS / RESTORE fallback은 `tuning-log.md` + `tuning-log.*.md` 모두 glob (B-16 archive search).

**state.json update**: `last_param_changes`에 append:
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
원자적 `tmp + mv` (Step 4 §4 atomicity).

**Lock release (R-9)**: `rmdir ${KRT_REPORTS}/filter-tune.lock` (락이 디렉터리이므로 rmdir로 매칭 — Step 5 mkdir과 대칭). try/finally 의미: Step 7 어느 substep이 실패해도 락 해제는 시도 (stuck lock 방지).

### Step 8 [TS-5] — 재실행 제안

**Verbatim** (PRD TS-5 + B-22):
> `"변경 적용됐습니다. 필터를 다시 돌려볼까요? (run_filters 동기 실행 — 보통 1-3분 소요)"`

본 Skill은 질문만 emit하고 메인 thread로 제어 반환. CLAUDE.md routing이 `"네/응/해줘"` → stock-scan `RERUN_FILTERS`로 라우팅. 거부(`"아니"/"나중에"`) 시 `"알겠습니다. 필요할 때 \"필터 재실행\"이라고 말씀하시면 됩니다."`로 종료.

### SHORTCUT (B-22)

**Predicate evaluation ordering (Review Step10-W3 fix)** — SHORTCUT은 다음 두 술어가 **모두** 결정된 *후*에만 활성화된다:
1. **In-range 판정**: Step 1.3 (Range check) 완료 후 — `new_value ∈ physical range AND ∉ danger zone` 일 때만 true. Step 1.0 keyword pre-check / Step 1.2 Stage 5 hard-block에 걸리면 즉시 REJECT이므로 SHORTCUT 평가 자체에 도달 못한다.
2. **Not-shared 판정**: Step 2 (공유 상수 영향 공개)의 `references/shared-constants.md` 조회 완료 후 — 현재 유일한 공유 상수는 `_ALIGN_TOL_LOOSE` 1개이므로 이 변수면 false, 나머지 74개는 true.

두 술어 모두 true → Steps 2-3 user-facing 출력 생략 (Step 2는 silent skip / Step 3는 silent 계산 후 Step 4 appendix에만 반영). 시퀀스: 0 → 1 (1.0→1.1→1.2→1.3 full) → [SHORTCUT 술어 evaluate] → 4 → 5 → 6 → 7 → 8. (74/75 params가 private + in-range이므로 default path.)

> **명시적 ordering 보장**: Step 1.0 keyword pre-check + Step 1.2 Stage 5 secondary guard는 SHORTCUT보다 항상 *선행*한다 (Stage 5는 in-range 판정 자체가 N/A이므로 SHORTCUT으로 우회 불가).

## §4. 6 Branch 정의

전체 step 차트·error handler·Korean string library는 `references/tuning-sequence.md §B` 참조.

### Branch 1: `SHOW_PARAMS(stage?)`

**Step 1 — Stage 해소**: `"Stage 1|2|2-1|3|4|5"` / 모듈명(`chart60_120` 등) / 테마구(`수급` → S4, `재무` → S5) 파싱. 부재/`"전체"` → 전 5 Stage.

**Step 1.5 — Stage 5 hard-block (C-4)**: 사용자가 Stage 5 파라미터 detail을 변경 의도와 함께 요청 시 (`"Stage 5 조건 어떻게 바꿔?"`):
> `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. Phase 2에서 상수화를 검토합니다."` (workflow.md L286 verbatim)

이후 read-only 요약: `cup_nga < 0 → 제외`, missing → PASS (hardcoded) + `references/parameter-catalog.md` Stage 5 섹션 cross-reference.

**Step 2 — 라이브 상수 Read**: 먼저 **[자동 검증] 값 무결성 게이트**(§11)를 1회 실행 — `cd ${KRT_ROOT} && ${KRT_PYTHON} .claude/skills/filter-tune/scripts/validate_param_values.py`; exit 1이면 불일치 항목을 한국어로 경고하고 라이브 grep을 우선한다. 이후 각 in-scope Stage의 `${KRT_FILTERS}/{module}.py`에 대해 `grep -n 'Final\[' ${KRT_FILTERS}/{module}.py` + 각 변수의 현재 literal grep. **`references/parameter-catalog.md`의 값을 권위 출처로 인용 금지** — code가 SOT (PRD §5.1).

**Step 3 — Korean 테이블 (FR-4.1)**:

```
## Stage 1 — chart60_120Filter.py (60분/120분봉 MA 정배열)

| ID | 변수명 | 현재 값 | 한국어 의미 | 이론적 근거 |
|---|---|---|---|---|
| S1-1 | _TYPE_A_ALIGN_TOL | -3.5% (×0.965, raw=0.035) | Type A 4선 정배열 허용오차 | Minervini SEPA |
| S1-2 | _ALIGN_TOL_LOOSE ⚠️공유 | -1.5% (×0.985, raw=0.015) | (공유) Type B/C/D 4개 조건 | 상승 초입 + 장기 추세 |
| ... | | | | |
```

⚠️공유 marker는 단일 공유 상수 행에만. `"전체"` 모드: 5 Stage 표 순차 (Stage 5는 read-only 요약).

**Step 4 — Footer**: `references/parameter-catalog.md` cross-reference + `"파라미터 변경은 \"{변수명}를 {새값}으로 바꿔줘\" 같이 말씀해주세요."`

### Branch 2: `CHANGE_PARAM(param_id, new_value)`

§3 master sequence. 별도 branch 로직 없음 — 완전성을 위해 명시만.

### Branch 3: `CONFIRM` (FR-6.5)

1. `screener_state.json.last_param_changes`에서 최신 `confirmed == false` 식별. 없으면 `"확정할 미확정 변경 이력이 없습니다."` 종료.
2. `tuning-log.md`에서 일치 `datetime` 행 찾아 `notes`에 `| ✓ 확정` suffix Edit (회전된 `tuning-log.YYYYMM.md`에 있으면 archive에 Edit). **이때 해당 행 `stocks_passed_after`가 `pending`이고 `last_results_summary.scan_date`가 행 `datetime` 이후 rerun을 증명하면 정수로 backfill(같은 Edit). 증명 못 하면 `pending` 유지 — rerun 미수행 시 after==before 거짓 기입 금지.**
3. state.json `confirmed = true`로 갱신 (원자적 write).
4. Korean ack verbatim (workflow.md L287): `"현재 설정이 확정되었습니다."`

### Branch 4: `RESTORE` (FR-6.4 + B-8 fallback)

**Step 1 — target 파일 해소**: 메시지에 hint → 단일 `{file_basename}`. 모호 시 AskUserQuestion으로 top-3 최근 `last_param_changes` 제시.

**Step 2a — Primary (백업 glob)**:
```bash
ls -t ${KRT_FILTERS}/{file_basename}.bak.* 2>/dev/null | head -1
```
non-empty → `"가장 최근 백업({backup_path})에서 복원합니다. 진행할까요?"` (예/아니) → 예 시 R-9 lock 획득(Step 5 mkdir 동일) → **try { `cp {backup_path} ${KRT_FILTERS}/{file_basename}` → `tuning-log.md`에 RESTORE 행 append(notes `"복원 (from {backup_filename}) | ✓ 복원"`) → state.json `last_param_changes`에 `confirmed=true`로 append } finally { `rmdir ${KRT_REPORTS}/filter-tune.lock` 항상 시도 — stuck lock 방지 (Step10-W4 fix) }**. ack: `"{file_basename}을 {backup_timestamp} 시점 백업으로 복원했습니다."`

**Step 2b — Fallback (tuning-log → Edit; B-8 KEY FEATURE)**:
`*.bak.*` 부재 시(회전 / 수동 삭제 / 미생성) 활성화. 알고리즘:
1. `tuning-log.md` + 전 `tuning-log.YYYYMM.md` 아카이브 Read (oldest-first).
2. `param_id` 일치 행 필터.
3. 현재 값 직전 마지막 행의 `old_value`가 복원 target.
4. §5 B-13e variable-name check.
5. AskUserQuestion: `"⚠️ 백업 파일이 없어 튜닝 로그에서 이전 값을 찾았습니다: {old_value_in_log}. Edit으로 직접 복원할까요? (.bak 파일이 없으므로 다시 변경하면 이 단계 이전 값으로는 돌아갈 수 없습니다.)"` 옵션: (a) 진행 (b) 다른 행 선택 (c) 취소.
6. 진행 시 R-9 lock 획득 → **try { Edit (`Final` 상수 값 교체) → RESTORE 행 append → state.json 갱신 } finally { `rmdir ${KRT_REPORTS}/filter-tune.lock` 항상 시도 — Edit 실패 시에도 stuck lock 방지 (Step10-W4 fix) }**.
7. Korean ack verbatim (workflow.md L288):
   > `"백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다. ({param_id}: {current_was} → {restored_to})"`
8. RESTORE 행 append (notes `"로그 기반 복원 (백업 부재) | ✓ 복원"`).

**Step 2c — Both fail**: `"{param_id}의 백업도, 변경 이력도 찾을 수 없습니다. 현재 값이 최초 설정값으로 보입니다. 참조용 PRD §5.1 카탈로그 값({prd_catalog_value})으로 강제 복원하시겠습니까?"` 수락 시 PRD catalog value를 `new_value`로 §3 master sequence (Steps 0-8) 진행.

### Branch 5: `THEORY_GUIDE(stage?, context?)` (FR-7)

**Step 1 — context**: theory name (`Minervini` / `Weinstein` / `Wyckoff` / `VCP` / `CANSLIM`) / stage / market regime (`강세` / `약세` / `횡보`).

**Step 2 — theory-guide.md verbatim render**: PRD §5.3 매핑 (Minervini SEPA → S1 Type A, S3 / Weinstein → S2, S1 Type B / Wyckoff → S4 / VCP → S1 Type C·E + S2-1 / CANSLIM-N → S5 Phase 2).

**Step 3 — Market regime (FR-7.2)**:
- `약세`: PRD §5.2 패턴 C verbatim — defensive(수급 강화) vs opportunistic(정배열 완화 + 장기추세 강화) two-track, `"어느 방향으로 가시겠습니까?"`로 종료.
- `강세`: 과열 필터 강화(Stage 2-1 surge → +10%) + 정배열 완화(돌파 포착).
- `횡보`: VCP 강조 — `_TYPE_C_CONVERGE_PCT`를 2.5%로 좁힘.

**Step 4 — Param ↔ theory (FR-7.3)**: 구체적 param에 대한 권장 범위 요청 시 `references/theory-guide.md`의 per-param 표 인용.

### Branch 6: `ASK_MODULE(module_name)` (§6.4 + workflow.md L290)

**Step 1**: 9 active 모듈 + `Filter_condition_update.py` 대조.

**Step 2 — 한국어 역할 표** (verbatim from `references/parameter-catalog.md`의 Module Index):
- `chart60_120Filter.py` — Stage 1 Type A/B/C/D/E (**Active tuning target**)
- `chart240Filter.py` — Stage 2 240m long-term (Active)
- `chartDayPreFilter.py` — Stage 2-1 surge exclusion (Active)
- `chartDayFilter.py` — Stage 3 daily MA + MA612 band (Active)
- `investorFilter.py` — Stage 4 (Active)
- `financeFilter.py` — Stage 5 ⚠️ Phase 2 (hardcoded, no Final)
- `chart60Filter.py` — standalone strict 60m alignment (not in main pipeline)
- `Filter_condition_update.py` — masterReference.log writer (no tunables)
- `stageMasterFilter.py` — Phase 2 (Excluded from Phase 1)

**Step 3 — Phase 2 deflection** (stageMasterFilter):
> `"stageMasterFilter.py는 별도 누적-확장 풀(positive coverage) 산출용 모듈입니다. 현재 5-Stage 파이프라인과 독립적으로 동작하며, Phase 1에서는 파라미터 튜닝 대상에서 제외됩니다. Phase 2 안정화 이후 검토 예정입니다."`

### Branch 7: `COMPARE_EXPERIMENTS` (B-16 combination view)

**Step 1**: `tuning-log.md` Read. 스코프 `"이번 달"` / `"지난 달"` 시 `tuning-log.YYYYMM.md` 아카이브도 Read.

**Step 2 — filter**: `"이 세션"` default → `datetime ≥ session_start_time` / `"오늘"` → KST today / `"이번 달"` → current YYYYMM.

**Step 3 — Korean 비교 표**:

```
## 이 세션 튜닝 실험 비교

| # | 변경 시각 | 파라미터 | 변경 전 → 후 | 통과 변화 | 비고 |
|---|---|---|---|---|---|
| 1 | 2026-05-30 14:23 | _TYPE_A_ALIGN_TOL (Type A 정배열 허용오차) | 0.035 → 0.05 | 17 → 22 (+5) | Stage 1 완화 | 미확정 |
| 2 | 2026-05-30 14:41 | _TYPE_E_SPREAD_PCT (Type E 수렴 폭) | 0.10 → 0.08 | 22 → 19 (-3) | E 과잉 조정 | 미확정 |
| 3 | 2026-05-30 15:02 | _THRESHOLD_FOREIGN_CONSEC_SELL | 2 → 3 | 19 → 24 (+5) | 약세장 수급 완화 | ✓ 확정 |
```

**Step 4 — narrative (FR-6.3)**: **render 직전 read-time backfill** — 가장 최근 `pending` 행을 위 게이트로 해소(turn당 ≤1행). 이후 max `stocks_passed_after`는 **해소된 행에 한해** 계산 → `"가장 통과 종목 많았던 설정"` (FR-8 — 투자 추천 아님 명시). `✓ 확정` 행 highlight. 잔여 `pending`/`미측정` 행 → advisory; 해소된 행이 0이면 `"아직 통과 수가 측정된 실험이 없습니다"` 명시.

**Step 5 — 면책** (FR-8.1 축약): `"(투자판단·책임은 본인에게 있습니다)"` (CLAUDE.md §Output Format 1줄 축약 규칙).

## §5. 변수명 검증 (B-13e / R-2)

EVERY Edit 직전 (§3 Step 6 / RESTORE primary Step 2 / RESTORE fallback Step 6-equiv):

```bash
grep -n '\b{variable_name}\b' ${KRT_FILTERS}/{file_path}
```

**Decision tree**:
1. ≥1 hit AND line contains `Final[` → Edit 진행.
2. ≥1 hit BUT no `Final[` → REJECT `"이 변수는 Final 타입이 아닙니다. TS-1에 따라 변경할 수 없습니다."`
3. 0 hits → fuzzy fallback (`grep -in '{trimmed_partial}' …` 대소문자 무시) → top-3 후보 Korean 렌더:
   > `"⚠️ '{variable_name}' 변수를 찾지 못했습니다. 변수명이 변경된 것 같습니다. 다음 후보들이 있습니다: • {c1} (line {N1}) • {c2} (line {N2}) • {c3} (line {N3}) 어떤 변수를 변경할까요?"`
   AskUserQuestion (4옵션: top-3 + `"취소"`).

**Anti-conflation table** (Step 1 §Critical Distinctions, full version in `references/shared-constants.md`):

| 모호 한국어 | 후보 | 디스앰비귀에이션 질문 |
|---|---|---|
| `"60분 정배열 허용오차"` | `_ALIGN_TOL_LOOSE` (chart60_120:120) vs `_MA_ALIGNMENT_TOLERANCE` (chart60:75) | `"두 가지 다른 변수가 있습니다: (1) chart60_120Filter의 Type B/C/D 공유 허용오차 (-1.5%) vs (2) chart60Filter 단독 모듈 4선 정배열 (-0.5%). 어느 쪽을 변경할까요?"` |
| `"평가 봉 수"` | `_REQUIRED_CONSECUTIVE_BARS` (chart60 / chart240 / chartDay 3-way 독립) | `"세 개 모듈에서 독립적으로 선언되어 있습니다: chart60 / chart240 / chartDay. 어느 Stage의 윈도우 크기를 바꿀까요?"` |
| `"MA60-MA306 허용오차"` | `_MA60_MA306_TOLERANCE` (chart240, 0.025) vs `_MA60_MA306_LOWER_TOL` (chartDay, 0.15) vs `_TYPE_E_MA60_OVER_MA306_TOL` (chart60_120 Type E, 0.035) | `"세 가지 다른 시간프레임에 있습니다: (1) Stage 2 240분 (-2.5%) (2) Stage 3 일봉 하한 (-15%) (3) Stage 1 Type E 전용 (-3.5%). 어느 쪽인가요?"` |
| `"창 크기"` / `"윈도우"` | `_REQUIRED_STATIC_BARS` (8) vs `_REQUIRED_CONSECUTIVE_BARS` (3, 3-way) vs `_REQUIRED_BARS` (16) vs `_TYPE_D_DYNAMIC_WINDOW` (16) | 4-row 표 렌더 → 사용자 선택. |

## §6. Backup / Restore 프로토콜 (TS-2 / TS-2a)

| Action | Command | Naming | Notes |
|---|---|---|---|
| **Create** | `cp ${KRT_FILTERS}/{file} ${KRT_FILTERS}/{file}.bak.$(date +%Y%m%d_%H%M%S)` | `{file}.bak.20260530_142345` | Step 5. `ls -t` 정렬 + tuning-log timestamp join 위해 형식 mandatory. |
| **List** | `ls -t ${KRT_FILTERS}/{file}.bak.*` | newest first | RESTORE primary + Step 5 회전 count. |
| **Rotate** | count > 5 → `grep -l '{oldest_ts}' tuning-log.md tuning-log.*.md` → 매치: `rm {oldest}` / 미매치: KEEP + warn | tuning-log gate 이후 | TS-2a (PRD line 442). |
| **Restore (primary)** | `cp ${KRT_FILTERS}/{file}.bak.{newest_ts} ${KRT_FILTERS}/{file}` | newest .bak | RESTORE Step 2a. |
| **Restore (fallback)** | `tuning-log.md` + 아카이브 Read → 마지막 `param_id` 행 → `old_value`로 Edit | .bak 부재 시 | B-8 KEY FEATURE (workflow.md L288). |

**Lock semantics (R-9)**: 백업 생성·Edit·tuning-log append는 Step 5(mkdir) → Step 7(rmdir) 사이 `filter-tune.lock` 디렉터리 sentinel 하에 atomic. stock-scan은 Bash 실행 전 `filter-tune.lock` 디렉터리 존재 확인 후 거부: `"⚠️ 파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`

## §7. references/ 파일 목록

- `references/parameter-catalog.md` — 전 75 `Final` 상수 navigation catalog (Stage별 그룹 + 한국어 의미 + 이론적 근거). **현재 값의 권위 출처 아님 — 라이브 code grep이 SOT.**
- `references/range-map.md` — TS-3 range/danger zone/Korean warning/이론적 근거 (75 constants 전수 coverage).
- `references/unit-conversion.md` — tolerance ↔ multiplier ↔ user-percent SOT 공식 + worked examples.
- `references/shared-constants.md` — `_ALIGN_TOL_LOOSE` shared registry + anti-conflation 표 (look-alike 5종).
- `references/theory-guide.md` — FR-7 Stage별 이론 매핑 (Minervini / Weinstein / Wyckoff / VCP / CANSLIM-N) + 시장 regime 가이드.
- `references/tuning-sequence.md` — §3 8-step verbose + 6 branch 차트 + TS-1~5 enforcement matrix + ADR-009 regex catalogue + Korean string library.

## §8. 안전 규칙 enforcement matrix (TS-1 ~ TS-5 + R-9 + Stage 5)

| Rule | Where enforced | SKILL anchor |
|---|---|---|
| **TS-1** (`Final` 값만 변경) | §3 Step 6 — Edit gated on `Final[` substring presence. Stage 5 hard-block at §3 Step 1.0 + Step 1.2. | §3 Step 1, Step 6 |
| **TS-2** (변경 전 백업) | §3 Step 5 — `cp` before Edit + `current_backup_files` append. | §3 Step 5 |
| **TS-2a** (백업 5개 한도 + tuning-log gate) | §3 Step 5 — `grep -l` against `tuning-log.md` + 아카이브. | §3 Step 5 rotation block |
| **TS-3** (범위 검증) | §3 Step 1.3 — Range Map REJECT (out-of-range) / warn + AskUserQuestion (danger zone). | §3 Step 1 |
| **TS-4** (한 번에 하나) | §3 Step 0 — multi-param 감지 + 3옵션 AskUserQuestion. | §3 Step 0 |
| **TS-5** (재실행 제안) | §3 Step 8 — Korean prompt + RERUN_FILTERS handoff. | §3 Step 8 |
| **R-9** (advisory lock — mkdir/rmdir 디렉터리) | §3 Step 5 acquire (atomic mkdir) / §3 Step 7 release (rmdir). | §3 Step 5, Step 7 |

**Stage 5 hard-block triple defence** (C-4 + workflow.md L286):
1. §3 Step 1.0 (PARAM_CHANGE keyword pre-check — **primary**)
2. §3 Step 1.2 (PARAM_CHANGE catalog 기반 — secondary)
3. §4 Branch 1 SHOW_PARAMS Step 1.5 (변경 의도 + Stage 5 단어 동반 시 안내)
4. §4 Branch 6 ASK_MODULE `financeFilter.py` 행 (`⚠️ Phase 2 (hardcoded, no Final constant)`)

## §9. screener_state.json I/O

Step 4 §4 schema. 원자적 write (`json.dump(state, tmp); mv tmp final`). JSON 손상 → `screener_state.json.corrupt.{ts}` 백업 후 기본 empty array로 진행 (R-7 — CLAUDE.md가 사용자 표면 처리).

| Operation | Read | Write | Notes |
|---|---|---|---|
| 세션 시작 (CLAUDE.md 핸드오프) | ✅ `last_param_changes[*]`의 `confirmed=false` vs 현재 Final 값 grep 비교 | — | 외부변경 경고 (B-12). 본 Skill은 경고 state만 소비. |
| Step 5 (백업 생성) | ✅ | ✅ `current_backup_files` append | `cp` 완료 후. |
| Step 6 (Edit) | — | — | Edit 자체는 state 미쓰기. |
| Step 7 (Edit 완료 후) | — | ✅ `last_param_changes` append (`confirmed=false`) | Step 4 §4 schema. |
| Step 5 rotation | — | ✅ `current_backup_files`에서 회전된 `.bak` path 제거 | 회전 발생 시. |
| CONFIRM branch | ✅ 최신 `confirmed=false` 식별 | ✅ `confirmed=true`로 set | tuning-log `✓ 확정` 마크와 pair. |
| RESTORE branch (any path) | ✅ | ✅ restoration 엔트리 append (`confirmed=true`) | RESTORE는 사용자 의도 = 묵시 confirm. |
| All paths | — | atomic `tmp + mv` | Step 4 §4 atomicity. |
| R-7 (corrupt state) | ✅ `json.JSONDecodeError` catch | ✅ `.corrupt.{ts}` backup | CLAUDE.md가 사용자 표면, Skill은 default empty로 진행. |

**Cross-skill 경계**: `last_param_changes`와 `current_backup_files`의 **단일 writer는 본 filter-tune**. stock-scan은 READ-only.

## §10. Skill-level Verification Self-Check

- [x] §3 master sequence: 8 numbered steps (Step 0~Step 8) — 각 TS rule citation + Korean message.
- [x] §3 Step 1.0 keyword pre-check (Review#3 fix) — Stage 5 primary guard 명시.
- [x] §3 Step 5 mkdir 원자성 lock (Review#2 fix) + §3 Step 7 rmdir 해제 — 디렉터리 형태.
- [x] §3 Step 7 tuning-log 8-column 스키마 (Review#1 verbatim) — `datetime / param_id / param_name / old_value / new_value / stocks_passed_before / stocks_passed_after / notes`.
- [x] §4 6 branches (SHOW_PARAMS / CONFIRM / RESTORE / THEORY_GUIDE / ASK_MODULE / COMPARE_EXPERIMENTS) — CHANGE_PARAM은 §3에 defer.
- [x] §5 anti-conflation 4-row 표 — `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` 등.
- [x] §6 backup `*.bak.YYYYMMDD_HHmmss` 명명 + TS-2a 회전 gate.
- [x] §7 references = 6 files (parameter-catalog / range-map / unit-conversion / shared-constants / theory-guide / tuning-sequence).
- [x] §8 enforcement matrix — TS-1~5 + R-9 모두 채워짐.
- [x] **Stage 5 hard-block 4 위치** (§3 Step 1.0 / §3 Step 1.2 / §4 SHOW_PARAMS Step 1.5 / §4 ASK_MODULE financeFilter 행).
- [x] ADR-011 `type(exc).__name__` STRING 분기 — 본 Skill은 CLAUDE.md `§Error Classification` 표를 단일 SOT로 참조하며 중복 보관 금지.
- [x] §9 state.json 9-row I/O 표 + cross-skill 경계 (단일 writer 명시).
- [x] §11 결정론 가드 2종 (`validate_param_values.py` 값 무결성 / `unit_conversion.py --verify` 변환 round-trip) — §3 Step 1.−1·Step 6, §4 SHOW_PARAMS Step 2에 배선.

## §11. Deterministic Guards (자동 검증 — 할루시네이션 차단)

LLM 추론 대신 결정론적 Python이 값 정확성을 강제한다. 모두 **read-only**(파일 수정 없음), stdlib만 사용. 위치: `.claude/skills/filter-tune/scripts/`.

| 스크립트 | 언제 (배선 위치) | 통과 (exit 0) | 실패 (exit 1) 시 |
|---|---|---|---|
| `validate_param_values.py` | §3 Step 1.−1 (PARAM_CHANGE 시작) · §4 SHOW_PARAMS Step 2 | catalog/range-map/unit-conversion 문서값 ↔ 라이브 코드 전부 일치 | 불일치 항목 한국어 경고 + 이후 **라이브 grep만 신뢰** |
| `unit_conversion.py --verify {literal} {±%}` | §3 Step 6 (Edit 직전, tolerance 계열) | literal이 사용자 의도 % 와 일치 | **Edit 중단** + `--pct {±%}`로 올바른 literal 재계산 |

- 실행 패턴: `cd ${KRT_ROOT} && ${KRT_PYTHON} .claude/skills/filter-tune/scripts/{script}`.
- 근거: 문서(catalog/range-map)는 navigation hint일 뿐 권위 출처는 라이브 코드(D-4, §7). 이 가드가 둘의 일치를 결정론적으로 보장한다 — `validate_param_values.py`는 product의 모든 numeric `Final` 값(29/30)을 catalog와 정확 대조, `unit_conversion.py`는 `0.05↔0.95` 류 변환 오류를 차단.
- 회귀 검증: AgenticWorkflow `prompt/.claude/tests/test_param_values.py`가 동일 스크립트(배포본)를 차단 게이트로 검증하며, 배포본 ↔ 소스 byte-identity(`filecmp`)도 확인한다.
