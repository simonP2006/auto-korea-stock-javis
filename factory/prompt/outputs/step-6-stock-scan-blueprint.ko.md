# Step 6 — stock-scan SKILL 블루프린트

> Generated: 2026-05-30
> Target deployment: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/`
> Step 9 `@scan-builder`가 본 블루프린트로부터 생성
> Skill 담당 범위: PG-1 (screener execution chains)
> Sources: workflow.md §6 (`@scan-designer` task), Step 2 research report, Step 4 architecture (paths, schema, OQ-3/ADR-011/ADR-012, 11 risks), Step 5 CLAUDE.md blueprint (§3 intent table, §5 error table), Step 1 error patterns + pipeline analysis, PRD FR-1/FR-2/FR-4/B-5/B-11/B-13/B-24

---

## §1. SKILL.md 헤더 및 트리거 조건

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

도구 선정 **근거(Rationale)**:
- `Bash` — `run_full_research_flow` / `run_prefetch` / `run_filters` / `Filter_condition_update` / `test -d` 사전 점검 (a)(c)에 필수.
- `Read` — `researchedCompany.md`, `stage*_passed.md`, `masterReference.log`, `prefetchManifest.json`, `screener_state.json`, `tuning-log.md`.
- `Glob` — WHY_REJECTED의 종목 폴더 탐색용 `reports/{date}/*{stock_name}*/` (B-5 §6.5).
- `Grep` — 스탬프 기반 masterReference.log 블록 추출, 파라미터 값 교차 검증.
- `Edit` — `masterReference.md` 누적 추가 (agent verification #9 — 사용자가 직접 편집한 라인을 보존하기 위해 반드시 Edit만 사용, 절대 Write 금지).
- `Write` — `screener_state.json` atomic write (`json.dump(tmp); mv tmp final`).
- `AskUserQuestion` — 분할 모드 프롬프트("필터를 실행할까요?"), 날짜 모호성 해소, prefetch 후 핸드오프 (PRD P4: 질문 최대 1개, 선택지 ≤ 3개).

`maxTurns: 80`은 SCAN_RANGE의 5일 루프 × 4-step 완료 처리(4-step completion handler) + 같은 세션 내의 종목별 WHY_REJECTED까지 수용할 수 있는 여유(headroom)를 제공.

**CLAUDE.md 의도 테이블(intent table)을 통한 트리거** (Step 5 블루프린트 §3 교차 참조 — 클러스터(cluster) 이름은 verbatim):

| CLAUDE.md cluster | → stock-scan action |
|---|---|
| `SCAN_TODAY` | Chain 1 — `scan_today(date?)` |
| `SCAN_SEPARATED` ("나눠서 해줘"/"단계별로 해줘"로 트리거) | Chain 2 — `scan_separated(date)` |
| `SCAN_RANGE` | Chain 3 — `scan_range(start, end)` |
| `SHOW_RESULTS` | Chain 4 — `show_results(date)` |
| `WHY_REJECTED` | Chain 5 — `why_rejected(stock_name, date)` |
| `COMPARE` | Chain 6 — `compare(date_a, date_b)` |
| `COMPARE_PARAMS` | Chain 7 — `compare_params(before_run, after_run)` |
| `RERUN_FILTERS` | Chain 8 — `rerun_filters(date)` |

혼합 의도(Mixed-intent)("필터 바꾸고 다시 돌려줘"): Step 5 §3의 혼합 의도 규칙(mixed-intent rule)에 따라 **filter-tune** Skill이 먼저 `CHANGE_PARAM`을 실행하고, 사용자가 확정한 뒤에야 stock-scan이 `RERUN_FILTERS`를 이어받는다. stock-scan은 파라미터 변경(mutation)을 절대 소유하지 않는다.

---

## §2. 경로 상수 참조

Step 4 architecture §1 + Step 5 블루프린트 §2를 그대로(verbatim) 상속한다. SKILL.md에서 **재정의하지 말 것** — 정본(canonical) 이름으로만 참조하라:

- `${KRT_ROOT}` = `/Users/tajun/spJavis/kiwoom-rest-trader`
- `${KRT_PYTHON}` = `${KRT_ROOT}/.venv/bin/python` (Python 3.12.7 검증 완료)
- `${KRT_REPORTS}` = `${KRT_ROOT}/reports`
- `${KRT_FILTERS}` = `${KRT_ROOT}/src/kiwoom/itemFilter`
- `${KRT_SCRIPTS}` = `${KRT_ROOT}/scripts`
- `EXEC_PATTERN` = `cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}`
- `run_full_research_flow` + `run_prefetch`에는 `RUN_IN_BACKGROUND = true` 필수 (ADR-012)

금지 형식 (D-7 / ADR-007): `source .venv/bin/activate && python …`. 항상 `.venv/bin/python` 직접 경로를 사용하라.

---

## §3. 8개 실행 체인

각 체인은 다음을 인코딩한다: **트리거 → 입력 → 사전 조건 검사 → 번호 매겨진 단계(Bash 명령 포함) → 체크포인트 → 출력(한국어) → 장애 복구 → 재시도 예산(Retry budget)**. 한국어 문자열은 PRD + Step 5 §6에서 verbatim 보존.

### Chain 1 — `SCAN_TODAY(date?)`

- **트리거 의도**: SCAN_TODAY (발화 예시: "오늘 종목 스캔해줘" / "오늘 결과 보여줘" / "오늘 돌려줘" / "{YYYYMMDD} 스캔")
- **기본 동작**: `run_full_research_flow` (D-2 / ADR-012, PRD FR-1.1)
- **입력**: `date` (기본값 = `$(date +%Y%m%d)` KST). 형식 가드: 8자리 숫자.
- **사전 조건 검사**: §4에 따른 세션 시작 (a)(b)(c). 세션의 첫 Bash 실행: 전체 실행 프로브(full execution probe) (R-11 / Step 4 §3 permission 주의사항(permission caveat)). 잠금(lock) 검사: `${KRT_REPORTS}/filter-tune.lock`이 존재하면 거부(R-9) → 한국어 메시지 `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`
- **백그라운드 실행 의무 (ADR-012)**: `Bash(run_in_background: true)` — **필수** (실제 런타임 10-15분 vs Bash 600초 캡).

**단계**:

1. `date` 형식 검증(`^[0-9]{8}$`). 무효 → 한국어 `"날짜 형식이 올바르지 않습니다 (YYYYMMDD). 예: 20260530"`.
2. 날짜가 미래가 아닌지 검증(`date_int <= today_int`). 미래 → 확인 프롬프트.
3. `${KRT_REPORTS}/screener_state.json` 읽기. `last_results_summary.scan_date == date && last_scan_date == date`이면 → "이미 스캔된 결과가 있습니다. 다시 실행할까요?" 질문 (캐시 히트 단축 옵션 = SHOW_RESULTS).
4. 예상 소요 시간 안내 (Step 4 §7 / ADR-012 verbatim):
   ```
   약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다.
   ```
5. 실행:
   ```
   Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_full_research_flow {date}
   ```
6. **30분 워치독(30-min watchdog)**: 30분 내 완료 알림이 없으면 → 한국어 폴백 `"실행이 예상보다 길어지고 있습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?"` + `scan_separated({date})` 제안.
7. **완료 알림 수신 시 — 4-step 완료 처리(4-step completion handler)** (PRD B-4 + Step 5 §5):
   - (1) **종목 수 추출** stdout에서: `save_researched_company`가 출력한 최종 단계 라인을 파싱 (전형적으로 `"researchedCompany.md: N종목 저장"`); 폴백 = `wc -l < researchedCompany.md`.
   - (2) **stderr 확인** — 트레이스백(traceback) / `Exception: …` 여부. stderr 비어있지 않고 exit ≠ 0이면 → 오류 경로로 분기.
   - (3) **오류 분류(error classification) 적용** (Step 5 §5 표 — `type(exc).__name__` STRING으로 디스패치(dispatch); OQ-3 / ADR-011에 따라 절대 `isinstance` 금지). §6 참조.
   - (4) **한국어 Stage-by-Stage 보고서 출력** (§5 템플릿).
8. **screener_state.json 기록**: `last_scan_date={date}`, `last_results_summary={scan_date, passed_count, by_stage}` 업데이트. atomic write (`json.dump(tmp); mv tmp final`).
9. 면책조항 추가 (세션의 첫 출력에는 전체, 이후에는 축약 — PRD B-23 / FR-8).

**체크포인트**:
- 종료 코드(Exit code) ≠ 0 → §6 오류 분류 (exit 1 = 도메인 입력 부재; exit 2 = 그 외 모든 경우).
- 실행 후 `${KRT_REPORTS}/{date}/researchedCompany.md` 부재 → "결과 파일이 생성되지 않았습니다 — 파이프라인이 중간 단계에서 종료되었을 수 있습니다. 기술 정보: stderr 마지막 줄 첨부."

**출력 포맷**: 한국어 Stage-by-Stage 표 + 최종 목록 + 면책조항 (§5 SHOW_RESULTS 템플릿 참조).

**장애 복구(Failure recovery)**:
- 백그라운드 워치독 타임아웃 → SCAN_SEPARATED 제안.
- `KiwoomAuthError` / `KiwoomApiError` → 사용자가 환경/네트워크 점검 후 재시도; 동일 체인 재호출 허용.
- `OrganizeError` / `PrefetchError` → 상류 스테이지 실행 안내; 확인 없이 자동 전환(auto-pivot)하지 말 것.

**재시도 예산(Retry budget)** (ADR-012 + agent verification #10):
- 동일 오류 유형이 연속 2회 관측 → 중단 + 한국어 설명: `"동일 오류가 2회 반복되었습니다. 추가 시도를 중단합니다. 원인: {cause}. 조치: {action}."` 무한 재시도 금지.

---

### Chain 2 — `SCAN_SEPARATED(date)`

- **트리거 의도**: B-11 분할 모드(split mode) ("나눠서 해줘" / "단계별로 해줘" / "분리해서 실행").
- **입력**: `date`. Chain 1과 동일한 날짜 검증.
- **사전 조건**: Chain 1과 동일 + filter-tune 잠금(lock) 검사.

**단계**:

1. 날짜 검증 (Chain 1 단계 1-2).
2. 안내: `"먼저 데이터 수집(prefetch)을 시작합니다. 약 10-15분 소요됩니다."`
3. 1단계 실행 — prefetch:
   ```
   Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_prefetch {date}
   ```
4. **30분 워치독** (Chain 1과 동일). 완료 시: 4-step 처리 — `prefetchManifest.json`에서 사전 수집된 종목 수 추출(`len(by_stock)`) + 오류 수 (값 ∉ {`"ok"`,`"empty"`,`"null"`,`null`,`""`}인 항목 수).
5. 한국어 prefetch 통계 보고서 출력 (B-11 verbatim 포맷, §5 참조).
6. AskUserQuestion (질문 1개, 선택지 2개): `"필터를 실행할까요?"` 옵션 = ["네, 지금 필터 실행", "잠시 후 직접 실행"].
7. 사용자가 확정하면 → 2단계 — **동기(synchronous)** 필터 실행:
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}
   ```
   (전형적으로 < 3분, Bash 600초 캡 내에 충분히 들어옴 — 백그라운드 불필요.)
8. exit 0이면 → Stage-by-Stage 보고서 (Chain 1 §5와 동일 템플릿). exit ≠ 0이면 → §6 디스패치.
9. screener_state.json 업데이트. 면책조항.

**체크포인트**: 단계 4 이후 `prefetchManifest.json` 부재 → 매니페스트 생성 실패; 보고 `"prefetchManifest.json 이 생성되지 않았습니다. Stage 0 prefetch 가 실패한 것으로 보입니다."` + stderr 말미.

**재시도 예산**: 동일 오류 2회 → 중단. prefetch는 성공했으나 필터가 실패한 경우 prefetch 산출물은 보존되므로 — 사용자는 Chain 8 (RERUN_FILTERS)을 통해 10-15분 비용을 다시 치르지 않고 필터만 재시도 가능.

---

### Chain 3 — `SCAN_RANGE(start, end)`

- **트리거 의도**: SCAN_RANGE ("이번 주 월~금 전부" / "{start}부터 {end}까지 스캔").
- **입력**: `start`, `end` YYYYMMDD. 제약: `start <= end`, 최대 31 캘린더 일(calendar day).

**단계**:

1. 영업일(business day) 목록 생성:
   - Bash: `start..end` 날짜 열거, `date +%u`(`6` / `7`)로 주말 `Sat`/`Sun` 제외.
   - **한국 공휴일 처리(KR holiday handling)**: 공휴일 데이터 하드코딩 없음 (PRD B-15, Step 5 §7). 경고 출력: `"⚠️ 주의: 한국 공휴일은 자동으로 제외되지 않습니다. 결과 폴더가 비어있다면 휴장일일 수 있습니다."`
2. 개수 확인: `"총 {N}영업일 스캔 예정 (예상 소요: ~{N*15}분). 진행할까요?"` AskUserQuestion 옵션: ["네, 전부 실행", "취소"].
3. 영업일 루프. 각 일자 `d_i`별로:
   - Chain 1 (SCAN_TODAY)을 `date=d_i`로 인라인 호출.
   - 완료 시 진행 상황 출력: `"{i}/{N}일 완료 — {d_i}: {count}종목 통과"`.
   - 오류 발생 시: 오류 로깅 후 사용자에게 질문 `"{d_i} 에서 오류 발생. 나머지 영업일을 계속할까요?"` (계속 / 중단).
4. 결과 집계 (B-24):
   - 일별 카운트 + 합집합(어느 날이든 통과) + 교집합(모든 날 통과) 계산.
   - 한국어 요약 표 출력 (§5 SCAN_RANGE 템플릿).
5. screener_state.json을 **마지막** 일자의 요약으로 업데이트 (Chain 1이 일별로 이미 수행).

**체크포인트**: 일자의 50%를 초과하여 오류가 발생하면, 2회 연속 실패 후 루프 중단 → 한국어 폴백 `"연속 오류로 범위 스캔을 중단했습니다."`

**재시도 예산**: 루프 내부 일별 재시도 없음 (사용자가 계속/중단 질문으로 결정). 동일 오류 2회 → 범위 스캔 전체 중단.

---

### Chain 4 — `SHOW_RESULTS(date)`

- **트리거 의도**: SHOW_RESULTS ("오늘 결과 보여줘" / "통과 종목 알려줘" / "최종 선별 목록").
- **입력**: `date` (기본값 = screener_state.json의 `last_scan_date`; 여전히 null이면 → AskUserQuestion).
- **사전 조건 (d)**: prefetchManifest.json 정상성 검사 (Step 4 §5). `${KRT_REPORTS}/{date}/` 부재 → `"{date} 결과가 없습니다. 스캔을 먼저 실행할까요?"` + SCAN_TODAY 제안.

**단계**:

1. `${KRT_REPORTS}/{date}/researchedCompany.md` 읽기 — **SHOW_RESULTS의 정본 파일(canonical SHOW_RESULTS file)** (Step 1 pipeline-analysis §(b) 라인 289-298: 5가지 근거, 그 중 `run_full_research_flow`와 `run_filters`가 모두 생성하는 유일한 파일이며; `Filter_condition_update`도 `_RESEARCHED_MD`를 통해 명시적으로 참조).
2. 각 스테이지 파일 읽기:
   - `stage1_chart60_120_passed.md`
   - `stage2_chart240_passed.md`
   - `stage2_1_chartDayPre_passed.md`
   - `stage3_chartDay_passed.md`
   - `stage4_investor_passed.md`
   - `stage5_finance_passed.md`
   각각에 대해 `wc -l`로 카운트 (각 파일은 줄당 stk_nm 1개, UTF-8 LF, 끝줄 개행, 비어있으면 0바이트 — Step 2 §5 C-6-2).
3. 스테이지별 탈락률(drop-off rate) 계산: `dropout_rate = 1 - (output / input)`. Stage 1 입력 ≈ `organizedCompany.md`의 크기 (정확한 분모를 위해 Read) — 부재 시 `"-"`로 폴백.
4. 한국어 표 출력 (§5 SHOW_RESULTS 템플릿):
   ```
   | Stage | 입력 | 통과 | 탈락률 |
   ```
5. 최종 통과 목록 출력 (종목명만, 줄당 1개). `>100`이면 → 처음 50개 표시 + `"... 외 {N}종목 (전체 목록: ${KRT_REPORTS}/{date}/researchedCompany.md)"`.

**사전 해결된 결정(Pre-Resolved Decision) — SHOW_RESULTS의 Type 패턴: Option (b)** (편차 금지).

- **결정**: SHOW_RESULTS 출력에서 Type A~E 패턴 정보 생략. 주석 추가: `"* Type 상세는 Stage 1 재평가로 확인 가능"`.
- **근거(Rationale)** (호출자 spec + Step 2 §3 + Step 1 pipeline-analysis §(b) 라인 179에서 verbatim):
  1. `stage1_chart60_120_passed.md`는 `r.candidate.stk_nm`만 저장 (줄당 이름의 플레인 텍스트). Type A~E 정보는 `r.extra["type_results"]`(프로세스 내부 전용) 또는 독립 실행의 stdout에 존재.
  2. `chart60_120Filter`로부터 Type을 재유도하려면 종목당 chart60.md + chart120.md 읽기와 패턴 매칭 재실행이 필요 — 경험적으로 종목당 ≥ 4 Read 호출 × 수백 종목 = agent verification 비용 예산을 훨씬 초과.
  3. 재유도(Re-derivation)는 취약(fragile): `_TYPE_*` 상수와 렌더링된 Markdown의 오래된 문자열 리터럴(stale string literals) 간의 어떠한 드리프트(ADR-010 — Type C `"2.0%"` / Type D `"60%"` 문서 드리프트)도 추론된 Type를 조용히 손상시킬 수 있음.
  4. 한국어 주석은 사용자에게 특정 종목에 대한 WHY_REJECTED로 Stage 1 재평가를 명시적으로 안내 — 이는 `masterReference.log`의 `r.extra` 텍스트에서 verbatim Type 매칭을 표면화함.

**체크포인트**: `researchedCompany.md`는 존재하지만 `stage*_passed.md`가 모두 부재 → "결과 파일이 부분적으로만 존재합니다 (researchedCompany.md 있음, 단계별 파일 부재). 필터 실행이 비정상 종료되었을 수 있습니다."

**출력**: §5 SHOW_RESULTS 한국어 템플릿 + 면책조항 (세션 첫 출력이 아니면 축약).

**재시도 예산**: 읽기 전용(read-only) 체인 — 실행 재시도 불필요. 파일시스템 오류 (`FileNotFoundError`, `PermissionError`)는 1회 보고, 자동 재시도 없음.

---

### Chain 5 — `WHY_REJECTED(stock_name, date)`

- **트리거 의도**: WHY_REJECTED ("OO전자 왜 빠졌어?" / "탈락 이유").
- **입력**: `stock_name` (한국어), `date` (기본값 = `last_scan_date`).
- **사전 조건**: `${KRT_REPORTS}/{date}/`가 반드시 존재; 그렇지 않으면 표준 `"결과가 없습니다"` 리디렉션.

**단계**:

1. **Glob 검사** — 종목이 수집 풀(collection pool)에 포함되었는지 확인:
   ```
   Glob: ${KRT_REPORTS}/{date}/*{stock_name}*/
   ```
   - **체크포인트**: 매칭 0건 → 한국어 출력 `"해당 종목은 수집 대상에 포함되지 않았습니다. 조건검색·상하한가 수집 단계에 들어오지 않은 종목입니다."` + `${KRT_REPORTS}/{date}/conditionResearch.md` 또는 `upperLowerPrice.md` 확인 제안. 체인 중지.
   - 다중 매칭 (부분 이름 중첩) → 최대 3개 후보로 AskUserQuestion.
2. **masterReference.md에 종목명 추가** — agent verification #9 (Edit only, 절대 Write 금지):
   ```
   Edit: ${KRT_REPORTS}/{date}/masterReference.md
   old_string: ""  (또는 마지막 줄)
   new_string: "{stock_name}\n"
   ```
   근거: Write는 사용자가 직접 편집한 항목을 덮어쓸 수 있음. Edit append는 안전하며 재실행 가능.
3. **Filter_condition_update를 동기 실행** (전형적으로 ~30초, 백그라운드 불필요):
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m src.kiwoom.itemFilter.Filter_condition_update {date}
   ```
4. **masterReference.log 읽기** — 가장 최근 블록 추출 (단계 3에서 출력된 것):
   - 헤더 라인 `[{stamp}] masterReference 분석 (date={date}, 대상 N종목)`을 Grep으로 검색하여 가장 최근의 스탬프(stamp) 선정 (마지막 출현).
   - 해당 헤더부터 다음 `<sep>` 또는 EOF까지 슬라이스.
   - 블록 내에서 `### {stock_name}` 하위 섹션 찾기.
5. **탈락 스테이지 + 조건 + 값 파싱** — ADR-009 하이브리드(hybrid) 정규식(regex)에 따른 자연어(natural-language) `reason` 텍스트 (Step 1 pipeline-analysis §(c) Gap 값(gap value) 포함: Partial). 블록 스키마는 verbatim:
   ```
   ### <stock_name>(<code>?)
   - Stage N — <stage_name> (<passed_file>): [<category>] <reason>
   ...
   (기록 YYYY-MM-DD HH:MM:SS)
   ```
   - 첫 `[제외]` 라인 식별 — 그것이 탈락 Stage.
   - 스테이지별 정규식 카탈로그(catalog) 적용 (filter-tune에 위임; stock-scan은 설명에 충분한 경량 버전 적용):
     - Stage 1: `Type ([A-E]):.*MA(\d+)\(([\d,]+(\.\d+)?)\)\s*[<>]\s*MA(\d+)×([\d.]+)\(([\d,]+(\.\d+)?)\)`
     - Stage 2: `MA60\(([\d,.]+)\)\s*<\s*MA306×([\d.]+)\(([\d,.]+)\)`
     - Stage 2-1: `금일 일봉\s*([+\-]\d+(\.\d+)?)%`
     - Stage 3: `종가\(([\d,]+)\)\s*vs\s*MA612\(([\d,.]+)\)\s*([+\-]\d+(\.\d+)?)%`
     - Stage 4: `(외국인|기관계|개인)\s*(\d+)회 연속 (매도|매수)\s*\(≥\s*(\d+)\)`
     - Stage 5: `당기순이익\s*([+\-]?\d+)억원\s*<\s*0`
   - 추출 가능 시 `gap = |actual - threshold|` 계산; regex 실패 시 → `"수치 추출 실패 — 원문 그대로 표시"` + raw `reason` 텍스트 출력.
6. **한국어 설명 출력** — FR-3.1 템플릿 (PRD §5.2 Pattern B):
   ```
   Stage N에서 탈락: {조건} = {실제값}. 기준 {기준값}. {gap} 미달.
   ```
   예 (Stage 3, MA612 밴드 초과): `"Stage 3에서 탈락: 종가가 MA612 대비 +53.41%. 기준 상한 +50.0%. 3.41%p 초과."`
   `(전 Stage 통과 — 기록 대상 없음)` 케이스: `"{stock_name}은(는) 5-Stage 전부 통과한 종목입니다 — 탈락 사유가 없습니다."`
7. **로그 회전 검사 (B-5 / PRD §6.5)**: `wc -l`로 `masterReference.log`의 줄 수 카운트. > 500이면 → 아카이브:
   ```
   mv ${KRT_REPORTS}/{date}/masterReference.log ${KRT_REPORTS}/{date}/masterReference.log.{YYYYMM}
   ```
   한국어 알림 출력: `"로그 회전: masterReference.log → masterReference.log.{YYYYMM} (500행 초과)"`. 다음 실행에서 새 로그가 비어있는 상태로 시작.

**체크포인트**:
- 단계 3 exit ≠ 0 → §6 오류 분류 (가장 가능성 높음: `ResearchError` / `FileNotFoundError` → 먼저 `{date}`에 대해 SCAN_TODAY 실행 제안).
- masterReference.log 블록에 `### {stock_name}` 하위 섹션 누락 (드묾 — 단계 2가 성공했다면 발생하지 않아야 함) → "block 파싱 실패. 기술 정보: ..."로 폴백.

**출력**: 한국어 탈락 설명 + 면책조항.

**재시도 예산**: 파싱 실패는 재시도 불가 (regex 실패 → raw 텍스트 출력). Bash 실행 실패는 동일 체인에서 1회 재시도; 동일 오류 2회 → 중단.

---

### Chain 6 — `COMPARE(date_a, date_b)`

- **트리거 의도**: COMPARE ("어제랑 오늘 비교해줘" / "{date_a}와 {date_b} 차이").
- **입력**: `date_a`, `date_b` YYYYMMDD.

**단계**:

1. `${KRT_REPORTS}/{date_a}/researchedCompany.md`와 `${KRT_REPORTS}/{date_b}/researchedCompany.md`가 모두 존재하는지 검증; 그렇지 않으면 `"{date_x} 결과 없음"` + 누락된 날짜에 대해 SCAN_TODAY 제안.
2. 두 파일을 집합 `S_a`, `S_b`로 읽기 (줄당 stk_nm 1개).
3. 계산:
   - `common = S_a ∩ S_b`
   - `only_a = S_a - S_b` (B에서 제거됨)
   - `only_b = S_b - S_a` (B에 추가됨)
4. **tuning-log.md 교차 참조** (FR-6.6): `${KRT_REPORTS}/tuning-log.md` 읽기 (PRD §9에 따른 세션 간 실험 이력의 정본 SOT). 일시(datetime)가 `date_a 00:00`과 `date_b 23:59` 사이인 행 필터링. 일치하는 행이 있으면 주석 추가:
   ```
   참고: {date_a}~{date_b} 기간 동안 파라미터 변경 {N}건 발견: {param_id_list}
   ```
   이는 FR-2.4 주의사항("날짜와 파라미터 설정이 동시에 다른 경우 이를 명시")을 표면화함.
5. 한국어 비교 표 출력 (§5 COMPARE 템플릿).

**체크포인트**: `tuning-log.md` 부재 → 주석 조용히 생략. `tuning-log.YYYYMM.md` 아카이브 (PRD §FR-6.6 200행 회전) — 일시가 아카이브 범위에 해당하면 함께 읽기.

**출력**: 3-버킷 표 + tuning 주석 + 면책조항.

**재시도 예산**: 읽기 전용 체인. 실행 재시도 없음.

---

### Chain 7 — `COMPARE_PARAMS(before_run, after_run)`

- **트리거 의도**: COMPARE_PARAMS ("변경 전후 비교", workflow.md §B-3에 따라 동일 날짜 / 다른 파라미터).
- **입력**: `before_run`과 `after_run` = tuning-log 행 ID 또는 일시. 사용자가 단순히 "변경 전후 비교"라고 말한 경우, `tuning-log.md`의 **마지막 2개 확정 행**으로 기본 설정.

**단계**:

1. `tuning-log.md`를 읽어 `before_run` / `after_run` 해석. **정본 8컬럼 스키마 (PRD FR-6.6, filter-tune §3 Step 7가 소유)**:
   ```
   | datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |
   ```
   stock-scan은 이 스키마를 READ; filter-tune이 유일한 writer. 추가 컬럼 불필요 (Review#1 수정: 스키마 정합).
2. `stocks_passed_before`와 `stocks_passed_after` 컬럼을 직접 추출 (각각 filter-tune §3 Step 7 spec에 따른 정수 카운트).
3. diff 계산 (Chain 6과 동일).
4. 한국어 표 출력 (§5 COMPARE_PARAMS 템플릿)으로 다음을 표시:
   - Param 변경: `{param_id}: {old} → {new}`
   - 통과 카운트 델타: `{before_count} → {after_count} ({delta:+d})`
   - 공통 / 추가 / 탈락 버킷.

**체크포인트**: tuning-log 행을 찾을 수 없음 → `"해당 변경 이력을 tuning-log.md에서 찾을 수 없습니다."` + 사용 가능한 행 확인을 위해 `cat tuning-log.md | tail -10` 제안.

**재시도 예산**: 읽기 전용. 재시도 없음.

---

### Chain 8 — `RERUN_FILTERS(date)`

- **트리거 의도**: RERUN_FILTERS ("필터만 다시 돌려줘" / "데이터는 그대로 두고 필터만").
- **입력**: `date` (기본값 = `last_scan_date`).
- **사전 조건 (d)**: `${KRT_REPORTS}/{date}/prefetchManifest.json`이 반드시 존재 + 오류 종목 0건 (§4 참조). 부재 → `"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."` 체인 중지.
- **잠금(Lock) 검사**: filter-tune.lock 존재 시 거부 (R-9).

**단계**:

1. 사전 점검 (d) 검사 (위).
2. 기존 `researchedCompany.md` 내용을 메모리에 스냅샷 저장 (`prev_passed` 집합), before/after 비교용.
3. **동기 실행(Synchronous execution)** (전형적으로 < 3분, 600초 Bash 캡 내):
   ```
   Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}
   ```
4. exit 0이면: 새 `researchedCompany.md`를 `new_passed` 집합으로 읽기.
5. 한국어 before/after 표 출력:
   ```
   변경 전: {len(prev_passed)}종목
   변경 후: {len(new_passed)}종목 ({delta:+d})
   추가: {sorted(new_passed - prev_passed)}
   탈락: {sorted(prev_passed - new_passed)}
   ```
6. `screener_state.last_results_summary` 업데이트.
7. 면책조항.

**체크포인트**:
- exit ≠ 0 → §6 디스패치 (가장 흔함: 단계 1과 단계 3 사이에 prefetchManifest.json이 삭제된 경우 `ResearchError`).
- `run_filters`는 `Filter_condition_update`를 **호출하지 않음** (Step 2 §7 + Step 1 pipeline-analysis 라인 124) — 따라서 `masterReference.log`는 이 체인에 의해 **업데이트되지 않음**. 사용자가 후속으로 WHY_REJECTED를 호출하면, Chain 5가 여전히 `Filter_condition_update`를 독립적으로 실행함.

**재시도 예산**: 동일 오류 2회 → 중단.

---

### 체인 요약 표

| # | Chain | 백그라운드? | 동기 런타임 | screener_state 쓰기? | masterReference.log 업데이트? |
|---|---|---|---|---|---|
| 1 | SCAN_TODAY | YES (ADR-012) | ~10-15분 | ✅ | ✅ (full flow 내부의 Filter_condition_update 통해) |
| 2 | SCAN_SEPARATED | prefetch는 YES, 필터는 NO | prefetch 10-15분, 필터 < 3분 | ✅ | ❌ (run_filters는 Filter_condition_update를 호출하지 않음) |
| 3 | SCAN_RANGE | YES (Chain 1 루프) | N × ~12분 | ✅ (일별) | ✅ (일별) |
| 4 | SHOW_RESULTS | NO | < 5초 | ❌ | ❌ |
| 5 | WHY_REJECTED | NO | ~30초 | ❌ | ✅ (append) |
| 6 | COMPARE | NO | < 5초 | ❌ | ❌ |
| 7 | COMPARE_PARAMS | NO | < 5초 | ❌ | ❌ |
| 8 | RERUN_FILTERS | NO | < 3분 | ✅ | ❌ |

---

## §4. 사전 점검 통합 (B-13)

Step 4 architecture §5 verbatim 참조. stock-scan은 다음을 지정된 시점에 실행한다:

**세션 시작 (경량, 1초 미만)** — 세션에서 stock-scan 체인의 첫 사용자 호출 시 실행:
- **(a)** `test -d ${KRT_ROOT}` — exit 0 기대; 실패 시 → AskUserQuestion (경로 재확인).
- **(c)** `test -w ${KRT_REPORTS}` — exit 0 기대; 실패 시 → `"reports/ 디렉터리에 쓰기 권한이 없습니다. chmod u+w 또는 디스크 여유 공간을 확인해주세요."`

**세션의 첫 Bash 실행 (OQ-3 / R-11 주의사항, Step 4 §3에 따라)** — 세션의 **첫** 백그라운드 또는 동기 Bash 호출 직전에 1회 실행:
- **(b)** 전체 실행 프로브: `[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version` — 끊긴 pyenv 심볼릭 링크(dangling pyenv symlinks)를 감지하기 위한 존재 + 역참조 체인 (R-10). 비-0 또는 버전 불일치 시: `"가상환경 Python 실행파일이 없습니다. cd ${KRT_ROOT} && python3.12 -m venv .venv && pip install -r requirements.txt 를 먼저 실행해주세요."` — 추가 실행 차단.
- Bash permission 프로브 (R-11): 첫 `cd ${KRT_ROOT} && .venv/bin/python --version`이 거부되면, `.claude/settings.local.json`에 `"Bash(cd /Users/tajun/spJavis/kiwoom-rest-trader && *)"`을 추가하거나 `/install`을 호출하라는 명확한 한국어 안내를 표면화.

**날짜 X에 대한 SHOW_RESULTS / WHY_REJECTED 사전 점검**:
- **(d)** `prefetchManifest.json` 정상성 검사 (Step 4 §5 명령 verbatim — Fix-Step10-A 방어적(defensive) non-ok 센티넬(sentinel)). 두 체인 모두 대상 날짜의 prefetch 산출물이 완전하다고 가정하므로 필수.

**Edit 전 사전 점검 (CHANGE_PARAM 전용 — 본 스킬 아님)**:
- **(e)** 파라미터 변수명 grep — **filter-tune** Skill이 처리, stock-scan 아님. 범위 경계 문서화를 위해서만 여기 언급.

stock-scan은 `Final` 상수를 절대 편집하지 않음; (e)는 범위 밖.

---

## §5. 결과 출력 포맷 템플릿

### 한국어 숫자 포맷 (PRD §7.3 verbatim)

- 가격: `4,805원` (천단위 콤마)
- 등락률: `-3.5%`
- 배수: `0.965배`
- 횟수: `5,234회`
- 금액: `1,234억원`
- 비율 표시: `15/350개`, `82개 → 45개`

Skill은 위 형식을 정확히 그대로 재현해야 함. 대체 단위(`￦`, `KRW`) 사용 금지, 과학적 표기법 금지, 영어 로케일(`4,805 KRW` 금지) 금지.

### SHOW_RESULTS 한국어 템플릿 (Chain 4 + Chain 1, 2, 8의 최종 출력)

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

(첫 출력이 아닌 경우 축약 면책조항: `(투자판단·책임은 본인에게 있습니다)`)

### Prefetch 통계 한국어 템플릿 (Chain 2 단계 5)

```
[데이터 수집 완료 — {date}]
- 대상 종목: {total}개
- 성공: {ok_count}개
- 빈 데이터: {empty_count}개
- 오류: {err_count}개

prefetchManifest.json 위치: ${KRT_REPORTS}/{date}/prefetchManifest.json
```

### WHY_REJECTED 한국어 템플릿 (Chain 5 단계 6)

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

### SCAN_RANGE 요약 한국어 템플릿 (Chain 3 단계 4)

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

### COMPARE 한국어 템플릿 (Chain 6)

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

### COMPARE_PARAMS 한국어 템플릿 (Chain 7)

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

### 오류 보고 한국어 템플릿 (§6 디스패치에서 사용)

```
[오류 발생]
{Korean summary 1 sentence}
원인: {cause}
조치: {user action}

기술 정보:
  {raw error excerpt — last 5 lines of stderr or exception type+message}
```

---

## §6. 체인별 오류 처리

**모든 체인은 `type(exc).__name__` STRING 매칭으로 오류를 디스패치한다** (OQ-3 / ADR-011 — 임포트된 `KiwoomApiError` 심볼에 대해 `isinstance`를 절대 사용하지 말 것; 해당 클래스는 kiwoom-rest-trader 모듈 전반에 걸쳐 **독립적으로 8회** 정의되어 있어 import 기반 catch는 그 중 7개를 조용히 놓침).

`Bash(run_in_background)` 체인의 경우, 오류는 완료 알림 후 stderr 라인으로 표면화된다. 디스패치 로직:

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

**Step 5 블루프린트 §5 오류 표 참조** (사용자 노출 클래스 9개, 한국어 메시지 verbatim). 핸드오프 편의를 위해 여기 반복:

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

**재시도 예산 (agent verification #10) — 체인별 반복**:
- 동일 체인 호출 내에서 동일 `type(exc).__name__`가 2회 연속 관측 → STOP. 한국어 중단 메시지 출력: `"동일 오류({exc_name})가 2회 반복되었습니다. 추가 시도를 중단합니다. 원인: {cause}. 조치: {action}."`
- 어디에서도 무한 재시도 루프 없음.
- Chain 3 SCAN_RANGE의 경우: 일별 동일 오류 2회 연속 실패는 범위 루프 전체를 중단함 (현재 일자뿐 아니라).

---

## §7. screener_state.json 읽기/쓰기 지점

Step 4 §4 스키마에 따름. atomic write: `json.dump(state, tmp); mv tmp final`. 잠금(locking) 없음 (Step 4 atomicity 비고에 따른 단일 스레드(single-threaded) 세션).

| Chain | Read | Write |
|---|---|---|
| 세션 시작 (어떤 체인이든 — 첫 호출) | ✅ `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files` 읽기 | — |
| Chain 1 SCAN_TODAY 종료 (성공) | — | ✅ `last_scan_date`, `last_results_summary={scan_date, passed_count, by_stage}` 업데이트 |
| Chain 2 SCAN_SEPARATED 종료 (성공 — 필터 단계 이후) | — | ✅ Chain 1과 동일 |
| Chain 3 SCAN_RANGE 일별 종료 | — | ✅ Chain 1을 따라 매일 업데이트 (이전 값 덮어씀) |
| Chain 4 SHOW_RESULTS | ✅ 캐시 히트 단축을 위해 `last_results_summary.scan_date == date` 검사 (스테이지 파일 재독 생략) | — |
| Chain 5 WHY_REJECTED | ✅ `date` 인자 생략 시 `last_scan_date` 읽기 | — |
| Chain 6 COMPARE | ✅ 기본값으로 `last_scan_date` 읽기 | — |
| Chain 7 COMPARE_PARAMS | ✅ 사용자가 모호한 경우 `before_run` / `after_run` 해석을 위해 `last_param_changes` 읽기 | — |
| Chain 8 RERUN_FILTERS 종료 (성공) | — | ✅ `last_results_summary` 업데이트 (last_scan_date 불변) |
| (filter-tune의 CHANGE_PARAM) | (cross-skill — `last_param_changes` 쓰기) | (filter-tune skill이 처리; stock-scan은 이 필드를 건드리지 않음) |

**JSON 손상 복구** (R-7 / Step 4 §10): `try: json.load() except json.JSONDecodeError: shutil.move(state_path, f"{state_path}.corrupt.{ts}")` → 신규 사용자로 취급 (파일 부재). 한국어 알림 출력: `"⚠️ screener_state.json 손상 감지. 손상 파일을 백업했습니다: {state_path}.corrupt.{ts}. 새로운 상태로 시작합니다."`

**Cross-skill 조정**: `last_param_changes`는 filter-tune이 소유. stock-scan은 이를 **읽기**만 함 (Chain 7 + Step 5 §10에 따른 세션 시작 시 드리프트 감지). stock-scan은 `last_param_changes`나 `current_backup_files`를 절대 변경하지 않음.

---

## §8. references/ 파일 계획

Step 9 `@scan-builder`가 `${KRT_ROOT}/.claude/skills/stock-scan/references/`에 다음 5개 reference 파일을 생성한다. 각 파일의 내용 요약:

### references/execution-chains.md (~250줄)

8개 체인 전체의 상세한 정본 정의: 체인별 입력, verbatim Bash 명령을 포함한 완전한 번호 매겨진 단계, 체크포인트 종료 코드 분기, 워치독 로직, 재시도 예산 강제 지점, before/after 상태 다이어그램. 각 체인 섹션 ≈ 30줄. 한국어 문자열은 `output-templates.md`로, ADR-012 세부사항은 `background-execution.md`로 교차 참조.

### references/pre-flight-checks.md (~80줄)

5개 사전 점검 (a)-(e)와 함께: 정확한 Bash 명령, 기대 종료 코드, 실패 시 한국어 오류 메시지, 복구 플로우차트(시각적 ASCII), 타이밍 다이어그램 (세션 시작 vs 첫 Bash vs 체인별). Step 4 architecture §5 verbatim 참조. R-10 끊긴 pyenv 심볼릭 링크 방어와 R-11 `Bash(python *)` permission 프로브 포함.

### references/output-templates.md (~150줄)

복사-붙여넣기 가능한 블록 형태의 모든 한국어 출력 템플릿: SHOW_RESULTS, prefetch 통계, WHY_REJECTED, SCAN_RANGE 요약, COMPARE, COMPARE_PARAMS, 오류 보고. PRD §7.3 숫자 포맷 예시 열거. 전체 면책조항 텍스트 + 축약 면책조항 + B-23 / FR-8에 따른 사용 시점 규칙. O/X 표현 정책 (FR-8.2/8.3) 예시 — 무엇을 말하고 무엇을 피할지.

### references/disclaimer.md (~30줄)

독립 면책조항 reference:
- 전체 버전 (세션의 첫 출력, PRD B-23 verbatim): `"⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다."`
- 축약 (후속 출력): `"(투자판단·책임은 본인에게 있습니다)"`
- PRD §7.3 / FR-8.2/8.3에 따른 O/X 정책: (O) `"기술적 완성도가 높은 종목"`, `"필터 조건을 충족한 종목"`, `"선별 결과"`, `"5-Stage 통과"`; (X) `"매수 추천"`, `"이 종목을 사세요"`, `"유망 종목"`, `"상승 예측"`, `"이익 보장"`
- 면책조항이 필요하지 **않은** 경우: 파라미터 조회, 오류 메시지, 시스템 상태 보고, 사전 점검 게이트.

### references/background-execution.md (~60줄)

ADR-012 강제 reference:
- 어떤 Bash 명령이 `run_in_background: true`를 **반드시** 사용해야 하는지 (`run_full_research_flow`와 `run_prefetch`만 — `run_filters` 명시적 제외, `Filter_condition_update` 명시적 제외).
- 30분 워치독 구현 패턴.
- 4-step 완료 처리 상세: (1) regex 폴백을 포함한 stdout 카운트 추출, (2) stderr 오류 스캔, (3) 오류 분류 디스패치 로직, (4) 한국어 보고서 출력.
- 10-15분 한국어 안내 문자열 verbatim.
- 타임아웃 폴백 한국어 메시지 verbatim.
- 알림 미수신 에스컬레이션 실패: 타임아웃 보고서 출력 + SCAN_SEPARATED 제안.

---

## §9. 안전 규칙 강제 지점 (TS-1~5)

stock-scan (PG-1, screener 실행 전용 — `Final` 상수를 쓰지 않음)에 대해:

| Rule | stock-scan에 적용? | 강제 |
|---|---|---|
| TS-1 | **N/A** — stock-scan은 `Final` 상수를 절대 쓰지 않음. 모든 파라미터 변경(mutation)은 filter-tune Skill에 존재. |
| TS-2 | **N/A** — 본 스킬은 `.bak.*` 파일 생성하지 않음. |
| TS-2a | **N/A** — 백업 라이프사이클(backup lifecycle) 관리 없음. |
| TS-3 | **N/A** — 값 범위 검사 없음 (어떤 값도 설정하지 않음). |
| TS-4 | **N/A** — 다중 파라미터 감지 없음 (변경되는 파라미터 없음). |
| TS-5 | **N/A** — TS-5 ("변경 후 재필터 실행 제안")는 filter-tune의 *제안*; stock-scan은 사용자가 나중에 RERUN_FILTERS를 호출하면 요청된 재실행을 수행. |

**면책조항 강제 (PRD §7.3 / FR-8 / B-23)** — stock-scan이 **실제로** 강제하는 단 하나의 안전 규칙:
- 결과를 출력하는 모든 체인(1, 2, 3, 4, 5, 6, 7, 8)은 면책조항을 반드시 추가해야 함.
- 포맷: 세션의 첫 출력에는 전체 버전, 이후에는 축약(1줄).
- 세션 범위 플래그로 추적 (초기 상태: 전체-미출력; 첫 출력 후 true로 토글).
- 면책조항이 필요하지 **않은** 경우: 오류 보고서, 사전 점검 메시지, AskUserQuestion 프롬프트, 진행 보고("3/5일 완료").

**암묵적 잠금 인식 (R-9)** — stock-scan은 filter-tune의 권고 잠금(advisory lock)에 따른다:
- Chain 1/2/3/8 Bash 실행 전에 `${KRT_REPORTS}/filter-tune.lock`을 확인. 존재 시 → `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`로 거부.
- stock-scan은 이 잠금을 생성하거나 해제하지 않음.

---

## §10. 길이 추정

| SKILL.md 섹션 | 추정 줄 수 |
|---|---|
| Frontmatter | 8 |
| §1 트리거 조건 | 6 |
| §2 경로 상수 참조 (단일 문장 — CLAUDE.md로 이연) | 2 |
| §3 8개 체인 (compact spec, 상세는 references/execution-chains.md로 이연) | 60 |
| §4 사전 점검 통합 | 8 |
| §5 출력 템플릿 참조 (references/output-templates.md로 이연) | 4 |
| §6 오류 처리 (pseudocode + 표 참조) | 8 |
| §7 screener_state.json I/O 표 | 8 |
| §8 references/ 파일 인덱스 | 6 |
| §9 안전 규칙 (TS-1~5 N/A + 면책조항 강제) | 6 |
| **SKILL.md 합계** | **~116** |

추가로 5개 reference 파일:
- `execution-chains.md` ≈ 250줄
- `pre-flight-checks.md` ≈ 80줄
- `output-templates.md` ≈ 150줄
- `disclaimer.md` ≈ 30줄
- `background-execution.md` ≈ 60줄

**전체 패키지**: SKILL.md (~116) + 5개 references (~570) = ~686줄의 skill 콘텐츠. workflow.md의 "포괄적·간결성 우선(comprehensive over terse)" 선호 범위 내 (절대 기준 1: 간결성보다 품질).

---

## §11. 검증 자체 점검

- [x] 모든 8개 체인을 다음 항목으로 명세: trigger / steps / checkpoint / output / failure / retry budget (§3 — Chain 1부터 Chain 8까지 각 섹션)
- [x] 사전 점검 (a)-(e) 통합 지점을 타이밍과 함께 명시 (§4 — 세션 시작 (a)(c) / 첫 Bash (b) / SHOW_RESULTS|WHY_REJECTED 전 (d) / 범위 외 (e))
- [x] 출력 포맷에 한국어 숫자 포맷이 **PRD §7.3에서 verbatim** 포함됨 (§5 — 가격/등락률/배수/횟수/금액 5개 형식)
- [x] references/ 목록 ≥ 5개 파일과 목적 (§8 — execution-chains, pre-flight-checks, output-templates, disclaimer, background-execution = 정확히 5개)
- [x] OQ-3 `type(exc).__name__` STRING 디스패치 명시적 기술 (§6 — pseudocode + 규칙 verbatim 인용)
- [x] ADR-012 백그라운드 의무가 체인 1 + 2(장시간 실행)에서 강제됨 — Chain 1 단계 5 `Bash(run_in_background: true)`; Chain 2 단계 3도 동일; 양쪽 모두 30분 워치독과 4-step 완료 처리 구비 (§3)
- [x] SHOW_RESULTS가 Option (b)를 사용 — Type 재유도 없음; 한국어 주석 `"* Type 상세는 Stage 1 재평가로 확인 가능"`이 verbatim 포함 (§3 Chain 4 + §5 SHOW_RESULTS 템플릿). 사전 해결된 결정 근거 문서화 (4가지 포인트).
- [x] 체인별 재시도 예산: 동일 `type(exc).__name__` 2회 → 중단 + 한국어 설명 (§3 각 체인 "재시도 예산" + §6 반복 참조)
- [x] masterReference.log / masterReference.md는 **Edit만** 사용 (절대 Write 금지) — Chain 5 단계 2 명시적 + agent verification #9 인용 (§3)
- [x] screener_state.json 읽기/쓰기 지점 표 완비 — 8개 체인 + 세션 시작을 모두 포함하는 9행 (§7)

---

*블루프린트 완성. Step 9 `@scan-builder`가 본 spec으로부터 최종 SKILL.md + 5개 references 파일을 `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/`에 작성한다.*
