---
name: stock-scan
description: Kiwoom REST API 종목 스크리너 — 스캔 실행·결과 해석·탈락 분석·비교를 한국어 자연어로 수행. PG-1(screener execution chains) 전담. Trigger: SCAN_TODAY, SCAN_SEPARATED, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, COMPARE, COMPARE_PARAMS, RERUN_FILTERS.
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
maxTurns: 80
---

# stock-scan SKILL

PG-1(screener execution chains) 전담 Skill. 5-Stage 필터 파이프라인 실행 + 결과 해석 + 탈락 분석 + 비교를 모두 한국어 자연어로 수행한다. 파라미터 변경(CHANGE_PARAM)·복원(RESTORE)·이론 해설(THEORY_GUIDE)·확정(CONFIRM)은 **filter-tune Skill** 소관이며 본 Skill은 절대 다루지 않는다.

## §1. 트리거 조건

CLAUDE.md `Intent Routing` 테이블의 다음 8개 클러스터가 본 Skill로 라우팅된다:

| Cluster | → Chain |
|---|---|
| `SCAN_TODAY` | Chain 1 — `scan_today(date?)` |
| `SCAN_SEPARATED` (트리거: "나눠서 해줘"/"단계별로 해줘") | Chain 2 — `scan_separated(date)` |
| `SCAN_RANGE` | Chain 3 — `scan_range(start, end)` |
| `SHOW_RESULTS` | Chain 4 — `show_results(date)` |
| `WHY_REJECTED` | Chain 5 — `why_rejected(stock_name, date)` |
| `COMPARE` | Chain 6 — `compare(date_a, date_b)` |
| `COMPARE_PARAMS` | Chain 7 — `compare_params(before_run, after_run)`. 단, 발화에 **명시적 실험 마커**(`"실험"`/`"튜닝 실험"`) 포함 시 실험-set 비교이므로 본 Skill 범위 밖 → filter-tune `COMPARE_EXPERIMENTS` 소관. `"세션"` 단독으로는 silent 라우팅 금지 — 모호 시 CLAUDE.md §Intent Routing의 1회 AUQ 분기 (마커 목록은 CLAUDE.md §Intent Routing과 동일; 상세 분기·AUQ 규칙은 CLAUDE.md가 정본) |
| `RERUN_FILTERS` | Chain 8 — `rerun_filters(date)` |

**Mixed-intent 규칙** (CLAUDE.md §Intent Routing 하단 verbatim): `"필터 바꾸고 다시 돌려줘"` → filter-tune `CHANGE_PARAM` 선행 → 사용자 확인 후 stock-scan `RERUN_FILTERS`. 본 Skill은 파라미터 변경을 절대 시도하지 않는다.

## §2. 경로 상수

CLAUDE.md `Path Constants` 섹션의 값을 그대로 사용한다 (재정의 금지):
- `${KRT_ROOT}`, `${KRT_PYTHON}`, `${KRT_REPORTS}`, `${KRT_FILTERS}`, `${KRT_SCRIPTS}`
- `EXEC_PATTERN = cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}`
- 금지 형태(D-7 / ADR-007): `source .venv/bin/activate && python …`

## §3. 8개 실행 체인 (요약)

각 체인의 전체 단계·체크포인트·재시도 예산은 `references/execution-chains.md` 참조. 여기서는 요약만.

### Chain 1 — SCAN_TODAY(date?)
- **기본 동작**: `run_full_research_flow` 백그라운드 실행 (D-2 / ADR-012, PRD FR-1.1).
- **사전점검**: §4의 (a)(b)(c) + `${KRT_REPORTS}/filter-tune.lock` 존재 시 거부 (R-9 — 한국어 메시지: `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`).
- **실행 명령 (ADR-012 mandate)**:
  ```
  Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_full_research_flow {date}
  ```
- **백그라운드 안내**: `"실측 기준 80분~6시간 소요됩니다(데이터량·시간대에 따라 변동). 완료되면 자동으로 결과를 보고합니다."`
- **7시간 watchdog** (실측 최대 6시간 + 여유 1시간): 7시간 무완료 시 이상으로 판정 → `"실행이 실측 범위(80분~6시간)를 넘겼습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?"`
- **완료 처리 4-step**: (1) stdout 종목 수 추출 → (2) stderr 오류 스캔 → (3) §6 에러 분류 → (4) §5 SHOW_RESULTS 한국어 보고서 + screener_state 갱신.
- **재시도 예산**: 동일 `type(exc).__name__` 2회 연속 시 중단.

### Chain 2 — SCAN_SEPARATED(date)
- **트리거**: "나눠서 해줘" / "단계별로 해줘" / "분리해서 실행" (B-11).
- **Step 1 — prefetch (ADR-012 mandate)**:
  ```
  Bash(run_in_background: true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_prefetch {date}
  ```
  완료 시 한국어 통계 보고 → AskUserQuestion `"필터를 실행할까요?"` (옵션 2개: "네, 지금 필터 실행", "잠시 후 직접 실행").
- **Step 2 — filters (synchronous, < 3분)**:
  ```
  Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}
  ```
- prefetch 성공 후 필터만 실패한 경우 → Chain 8(RERUN_FILTERS)로 재시도 가능 (수집 비용 보존).

### Chain 3 — SCAN_RANGE(start, end)
- 영업일 목록 생성(주말 제외), 최대 31일 제약.
- 한국 공휴일 하드코딩 없음 → 경고: `"⚠️ 주의: 한국 공휴일은 자동으로 제외되지 않습니다. 결과 폴더가 비어있다면 휴장일일 수 있습니다."`
- 각 영업일에 Chain 1 inline 호출, 진행률 보고, 2회 연속 동일 오류 시 범위 전체 중단.
- 마지막에 합집합/교집합 집계 (B-24).

### Chain 4 — SHOW_RESULTS(date)
- `${KRT_REPORTS}/{date}/researchedCompany.md` + 6개 `stage*_passed.md` Read → 단계별 통과/탈락률 표.
- **Type 패턴 표시 정책 — Option (b) 확정**: SHOW_RESULTS에서 Type A~E 정보 생략. 안내 문구 부착: `"* Type 상세는 Stage 1 재평가로 확인 가능"`. (이유: stage1_passed.md는 종목명만 저장, 재유도 비용 과다, ADR-010 doc-drift 위험.)
- 100개 초과 시 상위 50개 + 전체 경로 안내.

### Chain 5 — WHY_REJECTED(stock_name, date)
- Glob: `${KRT_REPORTS}/{date}/*{stock_name}*/` — 종목 수집 여부 확인. 미존재 시 한국어 안내 후 종료.
- **masterReference.md append**: `Edit` only (NEVER `Write` — 사용자 큐레이션 보존, agent verification #9).
- `Filter_condition_update` 동기 실행 (~30s):
  ```
  Bash(run_in_background: false): cd ${KRT_ROOT} && ${KRT_PYTHON} -m src.kiwoom.itemFilter.Filter_condition_update {date}
  ```
- masterReference.log 최신 블록 Grep → `### {stock_name}` 서브섹션 추출 → Stage별 regex로 reason 파싱 (Stage 1~5) → §5 WHY_REJECTED 템플릿으로 한국어 출력.
- **로그 회전 (B-5)**: `wc -l masterReference.log > 500` 시 `masterReference.log.{YYYYMM}`으로 mv.

### Chain 6 — COMPARE(date_a, date_b)
- 두 날짜의 `researchedCompany.md`를 set으로 Read → 공통/탈락/추가 3-bucket.
- `${KRT_REPORTS}/tuning-log.md` 교차 참조 (FR-6.6): `date_a 00:00 ~ date_b 23:59` 사이 행이 있으면 `"참고: {date_a}~{date_b} 기간 동안 파라미터 변경 {N}건 발견: {param_id_list}"` 부착.

### Chain 7 — COMPARE_PARAMS(before_run, after_run)
- `tuning-log.md` 읽기. **canonical 8-column 스키마 (PRD FR-6.6, filter-tune §3 Step 7이 8개 칼럼 전부의 sole writer; stock-scan은 전 칼럼 READ-only)**:
  ```
  | datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |
  ```
- stock-scan은 READS만; 추가 칼럼 불필요 (Review#1 fix). `stocks_passed_before`/`stocks_passed_after` 칼럼에서 직접 카운트 추출 — 단 `stocks_passed_after`가 `pending`/`미측정`이면 정수 파싱 금지(found-but-pending: `"재실행 필요"`로 처리).
- 사용자가 "변경 전후 비교"만 말하면 마지막 2개 확정 행을 default로 사용.

### Chain 8 — RERUN_FILTERS(date)
- **사전점검 (d)**: `${KRT_REPORTS}/{date}/prefetchManifest.json` 존재 + 오류 0건 (Fix-Step10-A 방어적 sentinel). 미존재 시: `"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."` 후 중단.
- 락 체크 (R-9) 동일.
- 기존 `researchedCompany.md` 스냅샷 → `run_filters` 동기 실행 → 새 결과와 set diff → 변경 전/후 표.
- ⚠️ `run_filters`는 `Filter_condition_update`를 호출하지 않음 → masterReference.log 미갱신. 후속 WHY_REJECTED는 Chain 5에서 독립적으로 갱신.

### 체인 요약표

| # | Chain | Background? | screener_state 쓰기 | masterReference.log 갱신 |
|---|---|---|---|---|
| 1 | SCAN_TODAY | YES (ADR-012) | ✅ | ✅ (full flow 내부 Filter_condition_update) |
| 2 | SCAN_SEPARATED | prefetch YES, filters NO | ✅ | ❌ (run_filters는 미호출) |
| 3 | SCAN_RANGE | YES (Chain 1 loop) | ✅ (per day) | ✅ (per day) |
| 4 | SHOW_RESULTS | NO | ❌ | ❌ |
| 5 | WHY_REJECTED | NO | ❌ | ✅ (append) |
| 6 | COMPARE | NO | ❌ | ❌ |
| 7 | COMPARE_PARAMS | NO | ❌ | ❌ |
| 8 | RERUN_FILTERS | NO | ✅ | ❌ |

## §4. 사전 검증 통합 (B-13)

| 시점 | 체크 | 상세 |
|---|---|---|
| 세션 시작 (최초 stock-scan 호출 시) | (a) `test -d ${KRT_ROOT}` / (c) `test -w ${KRT_REPORTS}` | `references/pre-flight-checks.md` 참조 |
| 세션 첫 Bash 실행 직전 (R-11 / OQ-3 caveat) | (b) `[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version` (R-10 dangling symlink 방어) + 권한 probe | 동일 |
| SHOW_RESULTS / WHY_REJECTED 직전 (date X) | (d) `prefetchManifest.json` 무결성 (Fix-Step10-A 비-ok sentinel) | 동일 |
| Edit pre-check (e) | 본 Skill 범위 외 — filter-tune 전용 | 언급만 |

## §5. 출력 형식

모든 한국어 템플릿 verbatim 보관: `references/output-templates.md`. 숫자 형식 (PRD §7.3 verbatim): 가격 `4,805원` / 등락률 `-3.5%` / 배수 `0.965배` / 횟수 `5,234회` / 금액 `1,234억원` / 비율 `15/350개`, `82개 → 45개`. `KRW`, `￦`, 과학적 표기 금지.

결과 출력 체인(1, 2, 3, 4, 5, 6, 7, 8) 모두 면책조항 부착 — 세션 첫 출력은 풀버전, 이후는 1줄 축약. 상세 정책: `references/disclaimer.md`.

## §6. 에러 처리 — `type(exc).__name__` STRING 분기 (ADR-011)

**필수**: 모든 체인은 `type(exc).__name__` STRING 매칭으로 분기한다. `isinstance(exc, KiwoomApiError)`는 절대 금지 — `KiwoomApiError`는 kiwoom-rest-trader 8개 모듈에 독립 정의되어 있으므로 어느 한 import로 catch하면 7개를 놓친다 (OQ-3 / ADR-011).

```python
# Skill이 에러 처리 단계에서 인코딩하는 pseudocode (verbatim from Step 4 ADR-011)
exit_code = bash_result.exit_code
stderr_tail = bash_result.stderr.splitlines()[-20:]

# 1차: exit-code triage — 1=도메인 입력 부재, 2=그 외, 0=성공 (Step 4 §8 / CLAUDE.md Exit code 1차 분류)
# 2차: stderr_tail에서 정규식으로 마지막 예외명 추출
#   r'\b(Kiwoom[A-Z][a-zA-Z]+Error|OrganizeError|ResearchError|PrefetchError|FileNotFoundError|ValueError)\b'
exc_name = extract_exception_name(stderr_tail)  # type(exc).__name__ equivalent

# 3차: 한국어 메시지 매핑 (CLAUDE.md §Error Classification 9-row 표)
korean = KOREAN_ERROR_TABLE.get(exc_name, KOREAN_ERROR_TABLE["Exception"])
```

한국어 메시지 9-row 표는 CLAUDE.md `§Error Classification` 참조 (verbatim 동일). 본 Skill은 SOT 중복 보관 금지 — CLAUDE.md 표가 단일 출처.

**재시도 예산 (agent verification #10)**: 동일 `type(exc).__name__` 2회 연속 → 중단 + 한국어 안내 `"동일 오류({exc_name})가 2회 반복되었습니다. 추가 시도를 중단합니다. 원인: {cause}. 조치: {action}."` 무한 재시도 금지.

## §7. screener_state.json I/O

원자적 쓰기 (`json.dump(state, tmp); mv tmp final`). 단일 세션 가정 → 잠금 없음 (Step 4 §4 atomicity 노트). JSON 손상 시 `screener_state.json.corrupt.{ts}`로 백업 → 신규 사용자 흐름 (R-7).

| Chain | Read | Write |
|---|---|---|
| 세션 시작 (임의 체인 최초 호출) | ✅ `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files` | — |
| Chain 1 SCAN_TODAY (성공) | — | ✅ `last_scan_date`, `last_results_summary={scan_date, passed_count, by_stage}` |
| Chain 2 SCAN_SEPARATED (필터 단계 성공) | — | ✅ Chain 1과 동일 |
| Chain 3 SCAN_RANGE (per-day) | — | ✅ 각 일자가 직전 값을 덮어씀 |
| Chain 4 SHOW_RESULTS | ✅ `last_results_summary.scan_date == date` 캐시 hit 단축 | — |
| Chain 5 WHY_REJECTED | ✅ `date` 인자 누락 시 `last_scan_date` 사용 | — |
| Chain 6 COMPARE | ✅ default 결정용 `last_scan_date` | — |
| Chain 7 COMPARE_PARAMS | ✅ `last_param_changes` 모호 해소 | — |
| Chain 8 RERUN_FILTERS (성공) | — | ✅ `last_results_summary` 갱신 (`last_scan_date` 불변) |

**Cross-skill 경계**: `last_param_changes`와 `current_backup_files`는 filter-tune SOLE-writer. stock-scan은 READ-only. CHANGE_PARAM 쓰기 분기 없음.

## §8. references/ 파일 목록

- `references/execution-chains.md` — 8 체인 전체 상세 (steps, checkpoints, 한국어 출력, retry budget)
- `references/pre-flight-checks.md` — (a)~(e) 5개 체크 + 한국어 오류 메시지 + 복구 안내
- `references/output-templates.md` — 모든 한국어 출력 템플릿 verbatim (SHOW_RESULTS, prefetch stats, WHY_REJECTED, SCAN_RANGE, COMPARE, COMPARE_PARAMS, error report) + 숫자 형식 5종
- `references/disclaimer.md` — 면책조항 풀/축약 + O/X 표현 정책 + 부착 면제 조건
- `references/background-execution.md` — ADR-012 mandate + 7시간 watchdog + 4-step 완료 핸들러

## §9. 안전 규칙 (TS-1 ~ TS-5)

stock-scan은 PG-1(스크리너 실행) 전담이며 `Final` 상수를 절대 쓰지 않으므로 TS-1~5 직접 적용 대상이 **N/A**:

| Rule | stock-scan 적용? | 사유 |
|---|---|---|
| TS-1 | N/A | `Final` 상수 미수정 (filter-tune 전담). |
| TS-2 | N/A | `*.bak.*` 미생성. |
| TS-2a | N/A | 백업 수명주기 관리 없음. |
| TS-3 | N/A | 값 범위 검증 없음 (값 설정 자체 없음). |
| TS-4 | N/A | 복수 파라미터 감지 없음. |
| TS-5 | N/A | "변경 후 재필터 실행 제안"은 filter-tune 측 *제안*; 사용자가 RERUN_FILTERS로 호출하면 stock-scan이 실행. |

**stock-scan이 enforce하는 유일한 안전 규칙 — 면책조항** (PRD §7.3 / FR-8 / B-23): 결과 출력 체인 8개 전부 면책 부착. 세션 1회 풀버전, 이후 1줄 축약. 부착 면제: 에러 리포트, 사전점검 메시지, AskUserQuestion 프롬프트, 진행률 보고("3/5일 완료").

**암묵적 락 인지 (R-9)**: 모든 실행 체인(1/2/3/8)은 Bash 실행 전 `${KRT_REPORTS}/filter-tune.lock` 존재 확인. 있으면 거부 (위 §3 Chain 1 한국어 메시지 동일). stock-scan은 락을 생성·해제하지 않는다.

## §10. Skill-level Verification Self-Check

- [x] 8개 체인 모두 §3에 요약 + `references/execution-chains.md`에 전체 상세 — Chain 1~8.
- [x] 사전점검 (a)~(e) §4에 시점별로 명시 — session-start/first-Bash/per-chain/out-of-scope 분류.
- [x] §5에서 PRD §7.3 한국어 숫자 형식 verbatim — 가격/등락률/배수/횟수/금액/비율.
- [x] §6에서 ADR-011 `type(exc).__name__` STRING 분기 명시 + pseudocode + isinstance 금지 사유.
- [x] §3 Chain 1, Chain 2에 ADR-012 `Bash(run_in_background: true)` mandate + 7시간 watchdog (실측 80분~6시간 기반).
- [x] §3 Chain 4에 Pre-Resolved Decision Option (b) 명시 + 한국어 안내 `"* Type 상세는 Stage 1 재평가로 확인 가능"`.
- [x] §6 + 각 체인에 재시도 예산 — 동일 `type(exc).__name__` 2회 → 중단.
- [x] Chain 5에 masterReference.md `Edit` only (NEVER `Write`) 명시.
- [x] §7 screener_state.json 9-row I/O 테이블 (세션 시작 + 8 체인).
- [x] Chain 7에 8-column tuning-log 스키마 verbatim (Review#1 fix — `stocks_passed_before`, `stocks_passed_after` 포함).
- [x] references/ 5개 파일 목록 명시 (§8).
- [x] TS-1~5 N/A 명시 + 면책 enforcement (§9).
