# execution-chains.md

8개 실행 체인의 canonical 정의. SKILL.md §3의 verbose 확장. 각 체인은 다음 구조로 기술된다: **Trigger → Inputs → Pre-condition checks → 번호 매겨진 Steps (Bash 명령어 verbatim) → Checkpoints → Output (한국어, `output-templates.md` 참조) → Failure recovery → Retry budget**.

한국어 출력 문자열은 모두 `output-templates.md`의 verbatim 사본을 참조한다. 백그라운드 실행 세부는 `background-execution.md`를 본다.

---

## Chain 1 — `SCAN_TODAY(date?)`

**Trigger intent**: SCAN_TODAY. 한국어 발화 예: `"오늘 종목 스캔해줘"`, `"오늘 결과 보여줘"`, `"오늘 돌려줘"`, `"{YYYYMMDD} 스캔"`.

**Inputs**: `date` (default = `$(date +%Y%m%d)` KST). 8-digit numeric format guard.

**Pre-condition checks**:
- 세션 시작 시 (a)(c) — `references/pre-flight-checks.md` 참조.
- 세션 첫 Bash 호출 직전 (b) + 권한 probe (R-11) — 동.
- `${KRT_REPORTS}/filter-tune.lock` 존재 시 거부 (R-9) → 한국어: `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`

**Background execution mandate (ADR-012)**: `Bash(run_in_background: true)` — **필수** (10-15분 실 runtime vs 600s Bash cap).

**Steps**:

1. Validate `date` 형식 `^[0-9]{8}$`. 실패 → 한국어: `"날짜 형식이 올바르지 않습니다 (YYYYMMDD). 예: 20260530"`.
2. `date_int <= today_int` 확인. 미래 날짜 → 사용자 확인 prompt.
3. `${KRT_REPORTS}/screener_state.json` Read. `last_results_summary.scan_date == date && last_scan_date == date` 이면 cache-hit 단축: `"이미 스캔된 결과가 있습니다. 다시 실행할까요?"` (선택지: 재실행 / SHOW_RESULTS로 단축).
4. 예상 소요 안내 (verbatim Step 4 §7 / ADR-012):
   ```
   약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다.
   ```
5. 실행:
   ```
   Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_full_research_flow {date}
   ```
6. **30분 watchdog**: 완료 알림이 30분 안에 없으면 → `"실행이 예상보다 길어지고 있습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?"` + `scan_separated({date})` 옵션 제공.
7. **완료 알림 수신 — 4-step 완료 핸들러** (PRD B-4 + Step 5 §5, `background-execution.md` 상세):
   - (1) **stock count 추출** — stdout의 최종 단계 라인 (`save_researched_company`가 emit하는 `"researchedCompany.md: N종목 저장"` 형식); fallback = `wc -l < researchedCompany.md`.
   - (2) **stderr 스캔** — traceback / `Exception: …` 존재 시 + exit ≠ 0 → 에러 분기.
   - (3) **에러 분류 적용** (SKILL.md §6 — `type(exc).__name__` STRING 분기, `isinstance` 금지 OQ-3 / ADR-011).
   - (4) **한국어 Stage-by-Stage 보고서 emit** — `output-templates.md` SHOW_RESULTS 템플릿.
8. **screener_state.json Write**: `last_scan_date={date}`, `last_results_summary={scan_date, passed_count, by_stage}` 갱신. atomic write.
9. 면책 부착 (세션 첫 출력 풀버전, 이후 축약 — `disclaimer.md` 참조).

**Checkpoints**:
- Exit code ≠ 0 → SKILL.md §6 분류 (exit 1 = 도메인 입력 부재 OrganizeError/ResearchError/PrefetchError; exit 2 = 그 외).
- `${KRT_REPORTS}/{date}/researchedCompany.md` 미존재 → `"결과 파일이 생성되지 않았습니다 — 파이프라인이 중간 단계에서 종료되었을 수 있습니다. 기술 정보: stderr 마지막 줄 첨부."`

**Output**: `output-templates.md` SHOW_RESULTS Korean template.

**Failure recovery**:
- watchdog timeout → SCAN_SEPARATED 제안.
- `KiwoomAuthError` / `KiwoomApiError` → env·네트워크 확인 후 동일 체인 재호출 허용.
- `OrganizeError` / `PrefetchError` → 상위 단계 실행 안내; 자동 pivot 금지.

**Retry budget**: 동일 `type(exc).__name__` 2회 연속 → 중단 + 한국어 stop 메시지. 무한 retry loop 금지.

---

## Chain 2 — `SCAN_SEPARATED(date)`

**Trigger intent**: B-11 split mode — `"나눠서 해줘"` / `"단계별로 해줘"` / `"분리해서 실행"`.

**Inputs**: `date`. Chain 1과 동일 검증.

**Pre-condition**: Chain 1과 동일 + filter-tune lock 체크.

**Steps**:

1. date 검증 (Chain 1 Step 1-2).
2. 안내: `"먼저 데이터 수집(prefetch)을 시작합니다. 약 10-15분 소요됩니다."`
3. Step 1 — prefetch 실행 (ADR-012 mandate):
   ```
   Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_prefetch {date}
   ```
4. 30분 watchdog (Chain 1과 동일). 완료 시 4-step 핸들러 — `prefetchManifest.json` (`len(by_stock)`)에서 수집 종목 수 + 비-ok sentinel 카운트 (value ∉ {`"ok"`,`"empty"`,`"null"`,`null`,`""`}) 추출.
5. 한국어 prefetch 통계 보고 emit — `output-templates.md` 프리페치 stats 템플릿 (B-11 verbatim).
6. AskUserQuestion (단일 질문, 2 옵션, PRD P4): `"필터를 실행할까요?"` 옵션 = ["네, 지금 필터 실행", "잠시 후 직접 실행"].
7. 사용자 확인 시 → Step 2 — filter 동기 실행:
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}
   ```
   (typically < 3분, 600s Bash cap 내 — background 불필요.)
8. exit 0 → SHOW_RESULTS 템플릿 (Chain 1과 동일). exit ≠ 0 → SKILL.md §6 분기.
9. screener_state.json 갱신. 면책.

**Checkpoint**: Step 4 후 `prefetchManifest.json` 미존재 → manifest 생성 실패; `"prefetchManifest.json 이 생성되지 않았습니다. Stage 0 prefetch 가 실패한 것으로 보입니다."` + stderr tail.

**Retry budget**: 동일 오류 2회 → 중단. prefetch 성공 + filters 실패 시 prefetch artifact 보존되므로 사용자가 Chain 8(RERUN_FILTERS)로 10-15분 비용 없이 재시도 가능.

---

## Chain 3 — `SCAN_RANGE(start, end)`

**Trigger intent**: SCAN_RANGE — `"이번 주 월~금 전부"` / `"{start}부터 {end}까지 스캔"`.

**Inputs**: `start`, `end` YYYYMMDD. 제약: `start <= end`, 최대 31 calendar days.

**Steps**:

1. 영업일 목록 생성:
   - Bash: `start..end` 열거, `date +%u`로 `6`(Sat)/`7`(Sun) 제외.
   - **한국 공휴일 처리**: hard-coded 없음 (PRD B-15, Step 5 §7). 경고 emit: `"⚠️ 주의: 한국 공휴일은 자동으로 제외되지 않습니다. 결과 폴더가 비어있다면 휴장일일 수 있습니다."`
2. 횟수 확인: `"총 {N}영업일 스캔 예정 (예상 소요: ~{N*15}분). 진행할까요?"` AskUserQuestion 옵션: ["네, 전부 실행", "취소"].
3. 영업일 loop. 각 `d_i`:
   - Chain 1(SCAN_TODAY) inline 호출 with `date=d_i`.
   - 완료 시 진행률 emit: `"{i}/{N}일 완료 — {d_i}: {count}종목 통과"`.
   - 오류 시: 로그 + `"{d_i} 에서 오류 발생. 나머지 영업일을 계속할까요?"` (continue/abort).
4. 결과 집계 (B-24):
   - per-day count + 합집합 (어느 날이든 통과) + 교집합 (모든 날 통과).
   - `output-templates.md` SCAN_RANGE 템플릿 emit.
5. screener_state.json 갱신은 **마지막** 일자의 summary로 (Chain 1이 per-day 이미 수행).

**Checkpoint**: 일자의 50% 초과가 오류 + 2회 연속 실패 → 루프 중단 → `"연속 오류로 범위 스캔을 중단했습니다."`

**Retry budget**: per-day 자동 재시도 없음 (사용자가 continue/abort 결정). 동일 오류 2회 연속 → 범위 스캔 전체 중단.

---

## Chain 4 — `SHOW_RESULTS(date)`

**Trigger intent**: SHOW_RESULTS — `"오늘 결과 보여줘"` / `"통과 종목 알려줘"` / `"최종 선별 목록"`.

**Inputs**: `date` (default = `last_scan_date` from screener_state.json; null이면 AskUserQuestion).

**Pre-condition (d)**: `prefetchManifest.json` 무결성 체크 (Step 4 §5). `${KRT_REPORTS}/{date}/` 미존재 → `"{date} 결과가 없습니다. 스캔을 먼저 실행할까요?"` + SCAN_TODAY 옵션.

**Steps**:

1. `${KRT_REPORTS}/{date}/researchedCompany.md` Read — **canonical SHOW_RESULTS 파일** (Step 1 pipeline-analysis §(b) 5 grounds: `run_full_research_flow`와 `run_filters` 양쪽 모두 생성; `Filter_condition_update`가 `_RESEARCHED_MD`로 참조).
2. 각 stage 파일 Read:
   - `stage1_chart60_120_passed.md`
   - `stage2_chart240_passed.md`
   - `stage2_1_chartDayPre_passed.md`
   - `stage3_chartDay_passed.md`
   - `stage4_investor_passed.md`
   - `stage5_finance_passed.md`
   각 파일은 line-per-stk_nm UTF-8 LF + trailing newline + 빈 경우 0-byte (Step 2 §5 C-6-2). `wc -l`로 count.
3. 단계별 dropout 계산: `dropout_rate = 1 - (output / input)`. Stage 1 input ≈ `organizedCompany.md` size (Read 정확 denominator) — 미존재 시 `"-"` fallback.
4. 한국어 표 emit (`output-templates.md` SHOW_RESULTS):
   ```
   | Stage | 입력 | 통과 | 탈락률 |
   ```
5. 최종 통과 목록 emit (종목명, 1줄당 1개). `>100` 이면 상위 50개 + `"... 외 {N}종목 (전체 목록: ${KRT_REPORTS}/{date}/researchedCompany.md)"`.

**Pre-Resolved Decision — Type 패턴 표시 Option (b) 확정** (deviation 금지):
- SHOW_RESULTS 출력에서 Type A~E 정보 생략. 안내 부착: `"* Type 상세는 Stage 1 재평가로 확인 가능"`.
- 근거 4점:
  1. `stage1_chart60_120_passed.md`는 `r.candidate.stk_nm`만 저장 (line-per-name 평문). Type A~E 정보는 `r.extra["type_results"]` (in-process only) 또는 standalone 실행의 stdout에만 존재.
  2. `chart60_120Filter`로 Type 재유도 시 stock당 chart60.md + chart120.md Read + 패턴매칭 재실행 필요 — 100s of stocks × ≥4 Read = 비용 예산 초과.
  3. 재유도는 fragile — `_TYPE_*` 상수와 렌더링된 Markdown의 stale string 간 drift (ADR-010 — Type C `"2.0%"` / Type D `"60%"`) 시 silently 오염.
  4. 한국어 안내가 사용자를 Stage 1 재평가(WHY_REJECTED)로 명시적으로 유도 — `masterReference.log`의 `r.extra` 텍스트에서 verbatim Type 매칭을 얻을 수 있음.

**Checkpoint**: `researchedCompany.md` 존재하지만 모든 `stage*_passed.md` 부재 → `"결과 파일이 부분적으로만 존재합니다 (researchedCompany.md 있음, 단계별 파일 부재). 필터 실행이 비정상 종료되었을 수 있습니다."`

**Output**: `output-templates.md` SHOW_RESULTS Korean template + 면책 (세션 첫 출력 아니면 축약).

**Retry budget**: read-only 체인 — 실행 retry 불필요. `FileNotFoundError` / `PermissionError`는 1회 보고 후 종료.

---

## Chain 5 — `WHY_REJECTED(stock_name, date)`

**Trigger intent**: WHY_REJECTED — `"OO전자 왜 빠졌어?"` / `"탈락 이유"`.

**Inputs**: `stock_name` (Korean), `date` (default = `last_scan_date`).

**Pre-condition**: `${KRT_REPORTS}/{date}/` 존재 필수; 미존재 시 표준 `"결과가 없습니다"` redirect.

**Steps**:

1. **Glob 체크** — 종목이 수집 pool에 있었는지 확인:
   ```
   Glob: ${KRT_REPORTS}/{date}/*{stock_name}*/
   ```
   - Checkpoint: zero match → `"해당 종목은 수집 대상에 포함되지 않았습니다. 조건검색·상하한가 수집 단계에 들어오지 않은 종목입니다."` + `${KRT_REPORTS}/{date}/conditionResearch.md` 또는 `upperLowerPrice.md` 확인 안내. 체인 halt.
   - 다중 match (부분명 중복) → AskUserQuestion 최대 3 후보.

2. **masterReference.md에 종목명 append** — agent verification #9 (`Edit` only, NEVER `Write`):
   ```
   Edit: ${KRT_REPORTS}/{date}/masterReference.md
   old_string: ""  (or last line)
   new_string: "{stock_name}\n"
   ```
   근거: `Write`는 사용자 큐레이션 entry를 덮어쓴다. `Edit` append만 safe + 재실행 가능.

3. **Filter_condition_update 동기 실행** (~30s, background 불필요):
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m src.kiwoom.itemFilter.Filter_condition_update {date}
   ```

4. **masterReference.log Read** — Step 3가 emit한 최신 블록 추출:
   - 헤더 라인 `[{stamp}] masterReference 분석 (date={date}, 대상 N종목)` Grep, 가장 최근 stamp (마지막 출현) 선택.
   - 해당 헤더부터 다음 `<sep>` 또는 EOF까지 slice.
   - 블록 내 `### {stock_name}` 서브섹션 검색.

5. **Rejection stage + 조건 + 값 파싱** — ADR-009 hybrid regex (Step 1 pipeline-analysis §(c) Gap value inclusion: Partial). 블록 스키마 verbatim:
   ```
   ### <stock_name>(<code>?)
   - Stage N — <stage_name> (<passed_file>): [<category>] <reason>
   ...
   (기록 YYYY-MM-DD HH:MM:SS)
   ```
   - 첫 `[제외]` 라인 — 탈락 Stage.
   - per-Stage regex catalog (filter-tune에 위임; stock-scan은 설명용 lightweight 버전만):
     - Stage 1: `Type ([A-E]):.*MA(\d+)\(([\d,]+(\.\d+)?)\)\s*[<>]\s*MA(\d+)×([\d.]+)\(([\d,]+(\.\d+)?)\)`
     - Stage 2: `MA60\(([\d,.]+)\)\s*<\s*MA306×([\d.]+)\(([\d,.]+)\)`
     - Stage 2-1: `금일 일봉\s*([+\-]\d+(\.\d+)?)%`
     - Stage 3: `종가\(([\d,]+)\)\s*vs\s*MA612\(([\d,.]+)\)\s*([+\-]\d+(\.\d+)?)%`
     - Stage 4: `(외국인|기관계|개인)\s*(\d+)회 연속 (매도|매수)\s*\(≥\s*(\d+)\)`
     - Stage 5: `당기순이익\s*([+\-]?\d+)억원\s*<\s*0`
   - `gap = |actual - threshold|` 추출 가능 시 계산; regex miss 시 → `"수치 추출 실패 — 원문 그대로 표시"` + raw `reason`.

6. **한국어 설명 emit** — FR-3.1 Pattern B template (`output-templates.md` WHY_REJECTED):
   ```
   Stage N에서 탈락: {조건} = {실제값}. 기준 {기준값}. {gap} 미달.
   ```
   예 (Stage 3 MA612 band breach): `"Stage 3에서 탈락: 종가가 MA612 대비 +53.41%. 기준 상한 +50.0%. 3.41%p 초과."`
   `(전 Stage 통과 — 기록 대상 없음)` 케이스: `"{stock_name}은(는) 5-Stage 전부 통과한 종목입니다 — 탈락 사유가 없습니다."`

7. **로그 회전 체크 (B-5 / PRD §6.5)**: `wc -l masterReference.log` > 500 → archive:
   ```
   mv ${KRT_REPORTS}/{date}/masterReference.log ${KRT_REPORTS}/{date}/masterReference.log.{YYYYMM}
   ```
   한국어 알림: `"로그 회전: masterReference.log → masterReference.log.{YYYYMM} (500행 초과)"`. 새 로그는 다음 실행 시 빈 채로 시작.

**Checkpoint**:
- Step 3 exit ≠ 0 → SKILL.md §6 분류 (`ResearchError` / `FileNotFoundError` 가능성 높음 → `{date}` SCAN_TODAY 선행 안내).
- Step 2가 성공했는데도 `### {stock_name}` 서브섹션 누락 (드묾) → `"block 파싱 실패. 기술 정보: ..."` fallback.

**Output**: 한국어 탈락 설명 + 면책.

**Retry budget**: parsing 실패는 non-retryable (regex miss → raw 텍스트). Bash 실행 실패는 1회 retry; 동일 오류 2회 → 중단.

---

## Chain 6 — `COMPARE(date_a, date_b)`

**Trigger intent**: COMPARE — `"어제랑 오늘 비교해줘"` / `"{date_a}와 {date_b} 차이"`.

**Inputs**: `date_a`, `date_b` YYYYMMDD.

**Steps**:

1. 양쪽 `${KRT_REPORTS}/{date_a}/researchedCompany.md` 와 `${KRT_REPORTS}/{date_b}/researchedCompany.md` 존재 확인; 없으면 `"{date_x} 결과 없음"` + 해당 날짜 SCAN_TODAY 제안.
2. 두 파일을 set `S_a`, `S_b`로 Read (1줄당 1 stk_nm).
3. 계산:
   - `common = S_a ∩ S_b`
   - `only_a = S_a - S_b` (B에서 탈락)
   - `only_b = S_b - S_a` (B에서 추가)
4. **tuning-log.md 교차 참조** (FR-6.6): `${KRT_REPORTS}/tuning-log.md` Read (canonical SOT for 세션간 실험 이력 — PRD §9). datetime이 `date_a 00:00` ~ `date_b 23:59` 사이인 행 필터. 매칭 행 있으면 주석 부착:
   ```
   참고: {date_a}~{date_b} 기간 동안 파라미터 변경 {N}건 발견: {param_id_list}
   ```
   FR-2.4 caveat (`"날짜와 파라미터 설정이 동시에 다른 경우 이를 명시"`) 표면화.
5. `output-templates.md` COMPARE Korean 표 emit.

**Checkpoint**: `tuning-log.md` 미존재 → 주석 silently skip. `tuning-log.YYYYMM.md` archive (PRD §FR-6.6 200-row rotation) — datetime이 archive 범위에 있으면 이것도 Read.

**Output**: 3-bucket 표 + tuning 주석 + 면책.

**Retry budget**: read-only — 실행 retry 없음.

---

## Chain 7 — `COMPARE_PARAMS(before_run, after_run)`

**Trigger intent**: COMPARE_PARAMS — `"변경 전후 비교"` (workflow.md §B-3 same-date / different params).

**Inputs**: `before_run` / `after_run` = tuning-log row ID 또는 datetime. 사용자가 그냥 "변경 전후 비교"만 말하면 `tuning-log.md` 마지막 2 확정 행을 default로.

**Steps**:

1. `tuning-log.md` Read → `before_run` / `after_run` 해소. **canonical 8-column 스키마 (PRD FR-6.6, filter-tune §3 Step 7이 8개 칼럼 전부의 sole writer; stock-scan은 READ-only)**:
   ```
   | datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |
   ```
   stock-scan은 이 스키마를 READS만; 추가 칼럼 불필요 (Review#1 fix — 스키마 reconciled).
2. `stocks_passed_before` / `stocks_passed_after` 칼럼에서 직접 integer count 추출 (filter-tune §3 Step 7 spec 기준).
3. diff 계산 (Chain 6과 동일 — 공통/추가/탈락 set).
4. `output-templates.md` COMPARE_PARAMS Korean 표 emit:
   - Param change: `{param_id}: {old} → {new}`
   - Pass-count delta: `{before_count} → {after_count} ({delta:+d})`
   - 공통 / 추가 / 탈락 buckets.

**Checkpoint**: (a) tuning-log 행 not found → `"해당 변경 이력을 tuning-log.md에서 찾을 수 없습니다."` + `cat tuning-log.md | tail -10` 안내. (b) **found-but-pending** (`stocks_passed_after`가 `pending`/`미측정`) → `"재실행 필요 (재필터 미완료로 변경 후 통과 수 미측정)"` 렌더, delta 생략 — 문자열에 정수 연산 금지.

**Retry budget**: read-only. 재시도 없음.

---

## Chain 8 — `RERUN_FILTERS(date)`

**Trigger intent**: RERUN_FILTERS — `"필터만 다시 돌려줘"` / `"데이터는 그대로 두고 필터만"`.

**Inputs**: `date` (default = `last_scan_date`).

**Pre-condition (d)**: `${KRT_REPORTS}/{date}/prefetchManifest.json` 존재 + 오류 0건 (`pre-flight-checks.md` (d) 참조). 미존재 → `"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."` halt.

**Lock check**: filter-tune.lock 있으면 거부 (R-9).

**Steps**:

1. Pre-flight (d) 체크.
2. 기존 `researchedCompany.md` snapshot → `prev_passed` set (before/after 비교용).
3. **동기 실행** (typically < 3분, 600s Bash cap 내):
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}
   ```
4. exit 0 → 새 `researchedCompany.md` Read → `new_passed` set.
5. before/after 한국어 표 emit:
   ```
   변경 전: {len(prev_passed)}종목
   변경 후: {len(new_passed)}종목 ({delta:+d})
   추가: {sorted(new_passed - prev_passed)}
   탈락: {sorted(prev_passed - new_passed)}
   ```
6. `screener_state.last_results_summary` 갱신. **(Chain 8은 `tuning-log.md`를 쓰지 않는다 — `stocks_passed_after` 해소는 filter-tune의 backfill 책임이며 여기서 cross-write 금지.)**
7. 면책.

**Checkpoint**:
- exit ≠ 0 → SKILL.md §6 분기 (가장 흔한 케이스: Step 1과 Step 3 사이에 prefetchManifest.json이 삭제된 경우 `ResearchError`).
- `run_filters`는 `Filter_condition_update`를 **호출하지 않음** (Step 2 §7 + Step 1 pipeline-analysis line 124) → `masterReference.log`는 본 체인이 갱신하지 않음. 사용자가 후속으로 WHY_REJECTED 호출 시 Chain 5가 `Filter_condition_update`를 독립적으로 실행.

**Retry budget**: 동일 오류 2회 → 중단.

---

## 체인간 cross-reference 요약

- Chain 1, 2, 3 → `output-templates.md` SHOW_RESULTS + `background-execution.md` ADR-012.
- Chain 4 → `output-templates.md` SHOW_RESULTS (Option (b) Type 정책).
- Chain 5 → `output-templates.md` WHY_REJECTED.
- Chain 6 → `output-templates.md` COMPARE.
- Chain 7 → `output-templates.md` COMPARE_PARAMS + 8-column tuning-log 스키마 (`stocks_passed_before`, `stocks_passed_after`).
- Chain 8 → `pre-flight-checks.md` (d) prefetchManifest 무결성.
- 모든 체인 → `disclaimer.md` 면책 enforcement.
