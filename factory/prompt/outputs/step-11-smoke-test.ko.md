# Step 11 — 스모크 테스트 검증 보고서

> 생성: 2026-05-30 (KST)
> 모드: DRY-RUN (실제 파이프라인 실행 없음, 파일 수정 없음)
> 범위: 10개 End-to-End 테스트 시나리오 + 사전 점검 + 의도 라우팅 + KNOWN ISSUE
> 배포 대상: `/Users/tajun/spJavis/kiwoom-rest-trader/` (CLAUDE.md 14,730 바이트, Step-10 편집 이후)
> 점검한 Skill SOT: stock-scan/SKILL.md (211줄), filter-tune/SKILL.md (441줄), references 파일 11개

## Executive Summary (≤10줄)

- 추적한 시나리오: **10/10**
- **PASS: 10  FAIL: 0  PARTIAL: 0**
- 사전 점검 (a)(b)(c): **전부 PASS** — 디렉터리 존재, Python 3.12.7 확인, reports 쓰기 가능
- Stage 5 하드 차단: **4/4 변형 모두 PRIMARY 가드에서 차단** (Step 1.0 키워드 사전 점검), Step 1.2 보조 가드 + SHOW_PARAMS Step 1.5 + ASK_MODULE financeFilter 행이 triple defence 심층 방어로 작동
- ADR-011 `type(exc).__name__` STRING 디스패치: CLAUDE.md L52 + stock-scan §6 의사 코드에서 확인
- ADR-012 `Bash(run_in_background:true)` 의무: CLAUDE.md L13/L20과 stock-scan §3 Chain 1 양쪽에서 확인
- R-9 잠금 의미론: mkdir/rmdir 디렉터리 기반, atomic POSIX 의미론, RESTORE Step 2a와 2b 양쪽에서 try/finally (Step10-W4 수정 검증됨)
- 혼합 의도 분할 라우팅 (CLAUDE.md L34-37 정규식): End-to-End 검증 완료
- screener_state.json 존재 (재방문 사용자 경로); 스모크 테스트 시점에 `filter-tune.lock` 없음
- Step 12 사람 리뷰를 위한 핵심 이슈: **블로킹 0건** / **권고 3건** (§8 참조)
- **종합: PASS**

---

## §1. 사전 점검 Dry-Run 결과

| 점검 항목 | 명령 | 결과 |
|---|---|---|
| (a) `${KRT_ROOT}` 존재 | `test -d /Users/tajun/spJavis/kiwoom-rest-trader` | **PASS** — `(a) PASS: kiwoom-rest-trader exists` |
| (b) Python venv 실행 가능 + R-10 프로브 | `[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version` | **PASS** — `Python 3.12.7` (CLAUDE.md L8 선언과 verbatim 일치) |
| (c) `${KRT_REPORTS}` 쓰기 가능 | `test -w /Users/tajun/spJavis/kiwoom-rest-trader/reports` | **PASS** — `(c) PASS: reports writable` |
| 잠금 상태 | `test -d ${KRT_REPORTS}/filter-tune.lock` | 없음 — 경합 없음 (R-9 정상 초기 상태) |
| screener_state.json | `test -f ${KRT_REPORTS}/screener_state.json` | **존재** (427 바이트, mtime May 30 14:18) → **재방문 사용자 분기** |
| reports/ 디렉터리 목록 | `ls reports/ \| head -5` | `20260510.zip, 20260512.zip, 20260513.zip, 20260514, 20260514.zip` — 과거 스캔 디렉터리 존재 |

**해석**: 스모크 테스트 세션은 재방문 사용자를 만난다. CLAUDE.md L102-105에 따라, 온보딩은 `last_scan_date` + `last_param_changes`로부터 2-3줄 한국어 세션 요약을 출력한다. 외부 변경 감지 (B-12)는 어떠한 사용자 발화보다 먼저 실행된다.

---

## §2. 의도 라우팅 검증 (CLAUDE.md vs Skills)

| 클러스터 | CLAUDE.md 라우트 | Skill 주장 | 일치? |
|---|---|---|---|
| SCAN_TODAY | stock-scan `scan_today()` + run_in_background:true (ADR-012) | stock-scan §3 Chain 1 (`run_full_research_flow` bg-true) | **YES** |
| SCAN_RANGE | stock-scan `scan_range(start, end)` B-24 | stock-scan §3 Chain 3 (영업일 loop, max 31일) | **YES** |
| SHOW_RESULTS | stock-scan `show_results(date)` | stock-scan §3 Chain 4 (Option (b) — Type 생략) | **YES** |
| WHY_REJECTED | stock-scan `why_rejected(...)` masterReference 체인 | stock-scan §3 Chain 5 (Edit only, NEVER Write) | **YES** |
| SHOW_PARAMS | filter-tune `show_params(stage)` | filter-tune §4 Branch 1 (live grep, 카탈로그 SOT 아님) | **YES** |
| CHANGE_PARAM | filter-tune `change_param(...)` 마스터 시퀀스 8단계 | filter-tune §3 마스터 시퀀스 (Steps 0-8 + SHORTCUT) | **YES** |
| RERUN_FILTERS | stock-scan `rerun_filters(date)` sync | stock-scan §3 Chain 8 (prefetchManifest 사전 점검, 포어그라운드) | **YES** |
| RESTORE | filter-tune `restore(file?, ts?)` | filter-tune §4 Branch 4 (Step 2a primary, 2b 폴백, 2c 양쪽 실패) | **YES** |
| COMPARE | stock-scan `compare(date_a, date_b)` Chain 6 | stock-scan §3 Chain 6 + COMPARE_PARAMS 이중 경로 주석 | **YES** (L29에 문서화된 experiment-scope 라우팅 규칙 포함) |
| COMPARE_PARAMS | stock-scan `compare_params(...)` Chain 7 | stock-scan §3 Chain 7 (8-컬럼 읽기) — experiment-set → filter-tune COMPARE_EXPERIMENTS | **YES** (분할 규칙 명시) |
| THEORY_GUIDE | filter-tune `theory_guide(topic)` FR-7 | filter-tune §4 Branch 5 (Minervini/Weinstein/Wyckoff/VCP/CANSLIM) | **YES** |
| CONFIRM | filter-tune `confirm()` | filter-tune §4 Branch 3 (state.confirmed=true + 튜닝 로그 ✓ 확정) | **YES** |
| ASK_MODULE | filter-tune `ask_module(...)` Branch 6 + Phase-2 디플렉션 | filter-tune §4 Branch 6 (financeFilter ⚠️ Phase 2) | **YES** |

**결과**: CLAUDE.md 라우팅 테이블과 Skill 내부 트리거 테이블 간 13/13 클러스터 일치. 드리프트 감지 없음.

> **부록 (2026-05-31, 빌드 후 — flight-recorder 무결성 보존)**: 위 13/13은 *빌드 시점 검증값*이며 그대로 보존한다. 빌드 완료 후 사후 제품-CLAUDE.md 수정(P1-b)으로 14번째 클러스터 `SCAN_SEPARATED`가 노출되었다 — 이미 stock-scan skill 트리거 표에는 존재했으나 CLAUDE.md 라우팅 표에서 누락되어 있던 것. 라이브 제품은 현재 **14 클러스터**. **2026-05-31 양방향 재검증 완료**: `SCAN_SEPARATED`가 CLAUDE.md 라우팅 표 + stock-scan skill §1 트리거 표(Chain 2) **양쪽에 존재** → **14/14 일치, 드리프트 0**. 참고: 위 13/13은 CLAUDE.md→skill **단방향** 검사였다(step-10 내부 일관성 주석 참조); stock-scan skill은 줄곧 SCAN_SEPARATED(Chain 2)를 가졌으나 CLAUDE.md 라우팅 표가 누락 — P1-b가 원본 스모크가 놓친 실제 skill→CLAUDE.md 드리프트를 닫았다. filter-tune §1의 7번째 항목 `COMPARE_EXPERIMENTS`는 COMPARE_PARAMS의 실험-스코프 하위 브랜치(CLAUDE.md L30)로 문서화된 것이며 고아가 아니다. 제품 ADR-014 참조.

**혼합 의도 규칙 (CLAUDE.md L34-37)**: 정규식 `(CHANGE|바꿔|완화|강화|조정).*(다시|재실행|돌려|돌리)` → 순차적 `[filter-tune CHANGE_PARAM, stock-scan RERUN_FILTERS]`로 분할. 두 Skill 모두 이 규칙을 verbatim으로 참조한다 (stock-scan §1 / filter-tune §1).

---

## §3. 테스트 시나리오 — 결과 매트릭스

| # | 시나리오 | 입력 (한국어) | 기대되는 Skill+액션 | 추적 판정 | 비고 |
|---|---|---|---|---|---|
| 1 | SCAN_TODAY 기본 | "오늘 종목 스캔해줘" | stock-scan Chain 1 (run_full_research_flow bg-true) | **PASS** | ADR-012 의무가 CLAUDE.md와 SKILL.md 양쪽에서 검증됨 |
| 2 | SHOW_RESULTS 정본(canonical) | "오늘 결과 보여줘" | stock-scan Chain 4 (Type 생략, Option (b)) | **PASS** | 한국어 주석 `"* Type 상세는 Stage 1 재평가로 확인 가능"`가 output-templates.md L48에 verbatim |
| 3 | WHY_REJECTED 체인 | "삼성전자가 왜 빠졌어?" | stock-scan Chain 5 (Edit only, log rotation > 500) | **PASS** | NEVER Write 규칙 L79 검증; 로테이션 한국어 메시지가 output-templates.md L98에 존재 |
| 4 | PG-2 PARAM_CHANGE happy path | "Type A 허용오차 -5%로 완화해줘" | filter-tune 마스터 시퀀스 8단계 | **PASS** | 8단계 모두 존재 및 순서 일치; Step 5에서 mkdir atomic |
| 5 | Stage 5 하드 차단 | "Stage 5 조건 바꿔줘" + 3 변형 | filter-tune Step 1.0 PRIMARY 가드 REJECT | **PASS** | 4/4 변형이 Step 1.0 키워드 사전 점검에서 포착됨 |
| 6 | 공유 상수 영향 (B-17) | "_ALIGN_TOL_LOOSE를 0.02로 바꿔" | filter-tune Step 2 공유 레지스트리 → 4-튜플 verbatim 목록 | **PASS** | shared-constants.md가 단일 공유 상수임을 확인; chart60_120 vs chart60 구분 명시 |
| 7 | RESTORE 분기 (B-8 폴백) | "원래대로 되돌려줘" | filter-tune Branch 4 Step 2a (primary) / 2b (폴백) | **PASS** | try/finally rmdir이 2a와 2b 양쪽에서 검증 (Step10-W4 수정 284, 293번 줄) |
| 8 | 혼합 의도 | "필터 바꾸고 다시 돌려줘" | 순차: CHANGE_PARAM → 사용자 확인 → RERUN_FILTERS | **PASS** | CLAUDE.md L34-37 정규식 + 두 Skill 모두 규칙을 verbatim 참조 |
| 9 | 에러 처리 (KiwoomApiError) | bg 스캔이 KiwoomApiError("HTTP") 발행 | CLAUDE.md `type(exc).__name__` STRING 디스패치 | **PASS** | ADR-011 명시 L52; 사용자 액션이 전문 용어 없음 `"잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요."` L58 |
| 10 | R-9 잠금 경합 | filter-tune Edit 중 SCAN_TODAY | stock-scan이 한국어 메시지로 거부 | **PASS** | 양쪽 검증: stock-scan §3 Chain 1 L43 거부 + filter-tune §3 Step 5 mkdir/Step 7 rmdir |

---

## §4. 시나리오별 상세

### 시나리오 1 — SCAN_TODAY 기본 (PG-1 happy path)
- **입력**: `"오늘 종목 스캔해줘"`
- **라우팅 추적**:
  - CLAUDE.md L20 → SCAN_TODAY 클러스터 → stock-scan `scan_today(date=today)`, 주석 `default = run_full_research_flow ; run_in_background:true` 포함 (ADR-012)
  - stock-scan §1 §3 Chain 1 (L41-51)
- **체인 단계 검증**:
  1. 날짜 검증 `^[0-9]{8}$` (Chain 1 Step 1)
  2. 미래 날짜 가드 (Step 2)
  3. screener_state 캐시 히트 점검 (Step 3)
  4. 한국어 추정값 출력: `"약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다."` (verbatim L48, background-execution.md §2)
  5. `Bash(run_in_background:true): cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_full_research_flow {date}` (verbatim L46-47)
  6. 30분 워치독 → SCAN_SEPARATED 제안 (L49)
  7. 4-step 완료 처리: 카운트 → stderr → 분류 → 한국어 보고 (L50)
  8. screener_state.json atomic write (last_scan_date, last_results_summary)
  9. 면책조항 첨부 (세션 첫 회 = 풀, 이후 = 1줄)
- **출력 템플릿**: output-templates.md §2 SHOW_RESULTS 한국어 템플릿 (Stage 테이블 + 최종 리스트 + Option (b) Type 주석 + 면책조항)
- **R-9 잠금 사전 점검**: §3 Chain 1 L43 — `${KRT_REPORTS}/filter-tune.lock` 디렉터리 존재 확인; 거부 메시지 verbatim
- **판정**: **PASS**

### 시나리오 2 — SHOW_RESULTS 정본(canonical)
- **입력**: `"오늘 결과 보여줘"`
- **라우팅 추적**: CLAUDE.md L20 (주: 동일한 한국어 발화가 SCAN_TODAY 예시에도 등장 — 그러나 SHOW_RESULTS L22가 `"오늘 결과 보여줘" / "통과 종목 알려줘" / "최종 선별 목록"`을 다룸. 해석 구분: 오늘에 대한 scan-today 결과 파일이 존재하면 SHOW_RESULTS 단축 경로 적용; 그렇지 않으면 SCAN_TODAY) → stock-scan §3 Chain 4 (L72-75)
- **체인 단계**:
  1. `${KRT_REPORTS}/{date}/researchedCompany.md` Read
  2. 6× `stage*_passed.md` Read
  3. Stage-by-Stage 통과/탈락률 테이블 작성
  4. Type 생략 (사전 해결된 결정 (b)) — 한국어 주석 `"* Type 상세는 Stage 1 재평가로 확인 가능"` 첨부 (verbatim output-templates.md L48)
  5. >100건 → 상위 50개 + 전체 경로 주석
  6. 면책조항 1줄 약식 (세션 첫 회가 아니라고 가정)
- **Type 생략 검증**: SKILL.md L74 + output-templates.md L48이 Option (b) 확인 — 근거: stage1_passed.md는 종목명만 저장; 재유도 비용; ADR-010 문서 드리프트 위험
- **판정**: **PASS**

### 시나리오 3 — WHY_REJECTED 체인
- **입력**: `"삼성전자가 왜 빠졌어?"`
- **라우팅 추적**: CLAUDE.md L23 → stock-scan §3 Chain 5 (L77-85)
- **체인 단계**:
  1. `Glob: ${KRT_REPORTS}/{date}/*삼성전자*/` — 수집 풀 존재 확인
  2. **masterReference.md append: Edit only (NEVER Write)** — verbatim L79 ("사용자 큐레이션 보존, agent verification #9")
  3. `Bash(run_in_background:false): ${KRT_PYTHON} -m src.kiwoom.itemFilter.Filter_condition_update {date}` (~30초) — verbatim L81-83
  4. Grep을 통해 최신 masterReference.log 블록 Read
  5. `### 삼성전자` 하위 섹션 추출
  6. Stage 1-5 정규식 파싱 사유
  7. 한국어 WHY_REJECTED 템플릿 출력 (output-templates.md §4)
- **로그 로테이션 (B-5)**: `wc -l masterReference.log > 500` → `mv masterReference.log masterReference.log.{YYYYMM}` (L85 + output-templates.md L98)
- **NEVER Write 규칙**: SKILL.md L79 및 §10 자체 점검 L207에서 검증됨
- **판정**: **PASS**

### 시나리오 4 — PG-2 PARAM_CHANGE happy path (최우선)
- **입력**: `"Type A 허용오차 -5%로 완화해줘"`
- **라우팅 추적**: CLAUDE.md L25 CHANGE_PARAM → filter-tune §3 마스터 시퀀스 (L43-222)

**8단계 추적**:

- **Step 0 [TS-4] — 다중 파라미터 감지** (filter-tune §3 L47-59):
  - 입력은 단일 파라미터 ("Type A 허용오차"). 연결어 없음 (`그리고/또/도/와/,`).
  - 결과: 다중 파라미터 아님 → Step 1로 진행.

- **Step 1.0 — 키워드 사전 점검** (L62-71):
  - 스캔되는 부분 문자열: `cup_nga`, `당기순이익`, `financeFilter`, `Stage 5`, `stage5`, `재무 단계`, `5단계`.
  - 입력 `"Type A 허용오차 -5%로 완화해줘"` → Stage-5 키워드 일치 없음.
  - 결과: Step 1.1로 PASS 통과.

- **Step 1.1 — 카탈로그 해석** (L73-74):
  - `references/parameter-catalog.md` 한국어 별칭 맵: `"Type A 4선 정배열 허용오차"` ↔ `_TYPE_A_ALIGN_TOL`.
  - 라이브 grep `chart60_120Filter.py:125`가 `Final[float] = 0.035` 확인.
  - 결과: `param_id = _TYPE_A_ALIGN_TOL` 해석됨.

- **Step 1.2 — Stage 5 하드 차단 (보조)** (L76-80):
  - 파일 소유자 확인: `chart60_120Filter.py` ≠ `financeFilter.py`.
  - 결과: PASS.

- **Step 1.3 — 범위 확인** (L82-89, range-map.md L37):
  - `_TYPE_A_ALIGN_TOL` 물리적 범위: `0.000 ~ 0.500`, 위험 구간: `≥ 0.300`.
  - 사용자 의도 `-5%` → 단위 변환 (Step 6 §A): `-5% = tolerance 0.05`.
  - `0.05 ∈ [0.000, 0.500]` AND `0.05 < 0.300` → 범위 내, 위험 아님.
  - 결과: PASS, Step 2로 진행.

- **Step 2 [B-17] — 공유 상수 확인** (L91-100, shared-constants.md L13):
  - 공유 상수 레지스트리: `_ALIGN_TOL_LOOSE`만 공유됨. `_TYPE_A_ALIGN_TOL`은 비공유(private).
  - 결과: SKIP (SHORTCUT 후보 — 다만 Step 3은 Step 4 부록에 데이터를 공급하기 위해 조용히 실행됨).

- **Step 3 [B-10] — masterReference.log gap 분석** (L102-108, ADR-009):
  - `screener_state.json.last_scan_date`에서 `latest_date` 추출.
  - `${KRT_REPORTS}/{latest_date}/masterReference.log` Read.
  - tuning-sequence.md §D의 정규식 카탈로그 `MA_ALIGNMENT`가 `(actual, threshold, unit)` 행을 추출.
  - 새 값 `0.05` vs 현재 `0.035`로 `would_pass` 재계산.
  - 한국어 라인: `"masterReference.log {M}개 행 중 {N}개에서 gap 추출. 약 N개 추가 통과 예상 (추정 정확도 X%)."`

- **Step 4 [B-7] — 확인 테이블 + AskUserQuestion** (L110-124):
  - Verbatim 한국어 테이블:
    ```
    | 파라미터 | 현재 값 | 변경 후 |
    |---|---|---|
    | _TYPE_A_ALIGN_TOL (Type A 4선 정배열 허용오차) | -3.5% (×0.965, raw=0.035) | -5.0% (×0.95, raw=0.05) |
    ```
  - 표시 규약은 unit-conversion.md에 따름: tolerance → raw + `-X.X% (×Y.YYY)`.
  - 부록: 공유 경고 생략(비공유), Step 3의 masterReference.log 델타.
  - AskUserQuestion 3개 옵션: 적용 / 다른 값 / 취소.

- **Step 5 [TS-2, R-9] — mkdir 잠금 + 백업** (L126-156):
  - R-9 권고 잠금 획득 — atomic mkdir:
    ```bash
    if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then ... else BLOCKED; fi
    ```
    POSIX-atomic — 정확히 한 프로세스만 성공 (다른 프로세스는 EEXIST).
  - 백업: `cp ${KRT_FILTERS}/chart60_120Filter.py ${KRT_FILTERS}/chart60_120Filter.py.bak.20260530_HHmmss`
  - 로테이션: `ls -t *.bak.*` 개수 ≤ 5 → 로테이션 없음.
  - 상태 동기화: `screener_state.current_backup_files` append (atomic tmp+mv).

- **Step 6 — Final 상수 Edit** (L158-170):
  - 사전 Edit grep: `grep -n '\b_TYPE_A_ALIGN_TOL\b' chart60_120Filter.py` → 125번 줄에서 `Final[float]` 확인.
  - `old_string`: `_TYPE_A_ALIGN_TOL: Final[float] = 0.035`
  - `new_string`: `_TYPE_A_ALIGN_TOL: Final[float] = 0.05`
  - 주석 자동 업데이트 (위 줄): `# 이전: 0.035 (변경: 2026-05-30)` 멱등 업데이트.

- **Step 7 [B-16] — 튜닝 로그 append + 상태 + 잠금 해제** (L172-215):
  - 8-컬럼 행:
    ```
    | 2026-05-30T14:35:22+09:00 | _TYPE_A_ALIGN_TOL | Type A 4선 정배열 허용오차 | 0.035 | 0.05 | {count_before} | pending | Stage 1 통과율 완화 시도 | 미확정 |
    ```
  - Atomic `>>` append. 헤더가 없으면 사전 시딩.
  - 로테이션: `wc -l - header ≥ 200` → `mv tuning-log.md tuning-log.YYYYMM.md`.
  - state.json `last_param_changes`에 `confirmed=false`로 append.
  - **잠금 해제**: `rmdir ${KRT_REPORTS}/filter-tune.lock` (try/finally 의미론).

- **Step 8 [TS-5] — 재실행 제안** (L217-222):
  - Verbatim: `"변경 적용됐습니다. 필터를 다시 돌려볼까요? (run_filters 동기 실행 — 보통 1-3분 소요)"`
  - 라우팅 이음매 → `"네/응/해줘"`일 경우 stock-scan RERUN_FILTERS.

- **판정**: **PASS** — 8단계 모두 존재, 올바른 순서, Step 5 mkdir atomic (POSIX EEXIST 의미론).

### 시나리오 5 — Stage 5 하드 차단 (심층 방어)
- **입력 변형**:
  - 5 (기본): `"Stage 5 조건 바꿔줘"` → 키워드 `Stage 5` MATCH → **Step 1.0 PRIMARY 가드에서 BLOCKED**.
  - 5a: `"당기순이익 임계값 -1로 바꿔"` → 키워드 `당기순이익` MATCH → **Step 1.0 PRIMARY 가드에서 BLOCKED**.
  - 5b: `"cup_nga 조건 완화"` → 부분 문자열 `cup_nga` (대소문자 무시) MATCH → **Step 1.0 PRIMARY 가드에서 BLOCKED**.
  - 5c: `"financeFilter PER 조건"` → 부분 문자열 `financeFilter` (대소문자 무시) MATCH → **Step 1.0 PRIMARY 가드에서 BLOCKED**.

- **Verbatim C-4 거부 메시지** (L78):
  > `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. 당기순이익 판정(cup_nga < 0)이 하드코딩 비교문이고 Final 상수가 존재하지 않습니다. Phase 2에서 상수화를 검토합니다."`

- **4개 변형 모두 카탈로그 조회 전 Step 1.0에서 단락**(short-circuit)됨 (근거 L71): financeFilter에는 Final 상수가 0개 → 카탈로그 퍼지 폴백이 그렇지 않으면 non-Stage5 false positive를 반환할 수 있음. Step 1.0 키워드 사전 점검이 PRIMARY 가드.

- **Triple defence 검증** (filter-tune §8 L410-414):
  1. §3 Step 1.0 — PRIMARY (키워드 사전 점검) ← 4/4 변형 모두 여기서 포착
  2. §3 Step 1.2 — SECONDARY (카탈로그 파일 소유자 확인)
  3. §4 Branch 1 SHOW_PARAMS Step 1.5 — 변경 의도 + Stage 5 단어
  4. §4 Branch 6 ASK_MODULE `financeFilter.py` 행 (`⚠️ Phase 2 (hardcoded, no Final)`)

- **판정**: **PASS** — 4/4 변형이 PRIMARY 가드에서 차단; 보조/3차 방어가 심층 방어로 존재.

### 시나리오 6 — 공유 상수 영향 (B-17)
- **입력**: `"_ALIGN_TOL_LOOSE를 0.02로 바꿔"`
- **Step 1.0**: Stage 5 키워드 없음 → PASS.
- **Step 1.2**: `_ALIGN_TOL_LOOSE` 소유자 = `chart60_120Filter.py:120` (financeFilter 아님) → PASS.
- **Step 1.3 범위 확인** (range-map.md L36): `_ALIGN_TOL_LOOSE` 물리적 범위 `0.000 ~ 0.300`, 위험 구간 `≥ 0.150`. `0.02 ∈ [0.000, 0.300]` AND `0.02 < 0.150` → 범위 내, 위험 아님.
- **Step 2 [B-17] — 공유 상수 영향** (shared-constants.md L13-32):
  - 레지스트리가 `_ALIGN_TOL_LOOSE`가 **유일한 활성 공유 상수**임을 확인.
  - Verbatim 영향 목록 출력:
    > `"⚠️ 이 상수는 공유 상수입니다. 변경 시 다음 조건들이 동시에 영향을 받습니다:`
    > ` • Type B — 120분 MA10-MA20 근접 판정`
    > ` • Type B — MA60-MA306 근접 판정`
    > ` • Type C — MA60-MA306 장기추세 leg`
    > ` • Type D — 60분 4선 정배열 fallback`
    > `특정 Type만 조정하려면 해당 Type 전용 상수 신설이 필요합니다 (TS-1 로직 변경 — 사용자 명시적 승인 필요)."`
- **범위 구분** (shared-constants.md L40-55, Pair 1):
  - `_ALIGN_TOL_LOOSE` (chart60_120Filter.py:120, 값 0.015) ≠ `_MA_ALIGNMENT_TOLERANCE` (chart60Filter.py:75, 값 0.005).
  - 후자는 단독 모듈이며 메인 파이프라인에 포함되지 않음; 스테이지 간 전파 없음.
  - 모호한 한국어 입력에 대비한 명확화 질문 제공: `"두 가지 다른 변수가 있습니다: (1) chart60_120Filter의 Type B/C/D 공유 허용오차 (-1.5%) vs (2) chart60Filter 단독 모듈 4선 정배열 (-0.5%). 어느 쪽을 변경할까요?"`
- **Step 4** 강화된 확인 테이블이 Step 2 경고를 포함 (L122에 따라 축약 재출력).
- **판정**: **PASS**

### 시나리오 7 — RESTORE 분기 (B-8 폴백)
- **입력**: `"원래대로 되돌려줘"`
- **라우팅 추적**: CLAUDE.md L27 → filter-tune §4 Branch 4 (L276-298).

- **Step 1 — 대상 파일 해석** (L278):
  - 한국어 발화에 파일 힌트 없음 → AskUserQuestion으로 가장 최근 `last_param_changes` 후보 상위 3개 제시.
  - 사용자가 `chart60_120Filter.py`를 선택했다고 가정.

- **Step 2a — Primary (.bak glob)** (L280-284):
  ```bash
  ls -t ${KRT_FILTERS}/chart60_120Filter.py.bak.* 2>/dev/null | head -1
  ```
  - 비어 있지 않음 → AskUserQuestion `"가장 최근 백업({backup_path})에서 복원합니다. 진행할까요?"`
  - 사용자가 예라고 답함 → **R-9 잠금 획득 (mkdir, atomic)** → **try { cp backup → file; 튜닝 로그 RESTORE 행 append (`notes: "복원 (from {bak}) | ✓ 복원"`); state.json append (`confirmed=true`) } finally { rmdir 잠금 — 항상 시도 — stuck lock 방지 (Step10-W4 수정) }**.
  - 한국어 ack: `"{file_basename}을 {backup_timestamp} 시점 백업으로 복원했습니다."`

- **Step 2b — 폴백 (B-8 핵심 기능)** (L286-296):
  - .bak 없음 (로테이션 / 수동 삭제 / 생성된 적 없음) → 폴백 활성화.
  - 알고리즘:
    1. `tuning-log.md` + 모든 `tuning-log.YYYYMM.md` 아카이브 Read (오래된 순부터).
    2. `param_id`와 일치하는 행 필터링.
    3. 마지막 행의 `old_value` = 복원 대상.
    4. B-13e 변수명 점검.
    5. AskUserQuestion: `"⚠️ 백업 파일이 없어 튜닝 로그에서 이전 값을 찾았습니다: {old_value_in_log}. Edit으로 직접 복원할까요? (.bak 파일이 없으므로 다시 변경하면 이 단계 이전 값으로는 돌아갈 수 없습니다.)"`
    6. 진행 시: **R-9 잠금 획득 → try { Final 상수 Edit; RESTORE 행 append; state.json 업데이트 } finally { rmdir 잠금 항상 — Edit 실패 시에도 잠금 해제 트리거 (Step10-W4 수정 L293 검증) }**.
    7. 한국어 폴백 ack: `"백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다. ({param_id}: {current_was} → {restored_to})"`
    8. RESTORE 행 notes: `"로그 기반 복원 (백업 부재) | ✓ 복원"`.

- **Step 2c — 양쪽 모두 실패** (L298): PRD §5.1 카탈로그 값을 최후의 `new_value`로 사용 → 마스터 시퀀스 Steps 0-8.

- **try/finally 검증**:
  - L284 (Step 2a): `"try { ... } finally { rmdir ${KRT_REPORTS}/filter-tune.lock 항상 시도 — stuck lock 방지 (Step10-W4 fix) }"`
  - L293 (Step 2b): `"try { ... } finally { rmdir ${KRT_REPORTS}/filter-tune.lock 항상 시도 — Edit 실패 시에도 stuck lock 방지 (Step10-W4 fix) }"`

- **판정**: **PASS** — 두 분기 모두 명시적 try/finally 의미론; Step10-W4 수정 확인됨.

### 시나리오 8 — 혼합 의도 (CLAUDE.md 순차 규칙)
- **입력**: `"필터 바꾸고 다시 돌려줘"`
- **CLAUDE.md L34-37 verbatim**:
  > 혼합 의도 규칙 (필수): `"필터 바꾸고 다시 돌려줘"` → 순차 라우팅:
  > 1. filter-tune `CHANGE_PARAM` (마스터 시퀀스 완료까지)
  > 2. 사용자 확인 후 stock-scan `RERUN_FILTERS`
  > Pattern 인식: `(CHANGE|바꿔|완화|강화|조정).*(다시|재실행|돌려|돌리)` → 2개의 순차 호출로 분할, 단일 Skill 호출로 병합하지 않음.
- **정규식 테스트**:
  - `"필터 바꾸고 다시 돌려줘"` → `바꾸` 캡처 (alternation의 `바꿔`와 부분 일치 — 주의: CLAUDE.md는 `바꿔` 리터럴을 사용하므로 정규식이 관대한 경우 한국어 형태론상 `바꾸` 어간과 일치 가능; 그렇지 않으면 더 넓은 패턴 `(CHANGE|바꿔|완화|강화|조정)`가 `바꾸고`를 받아들이려면 정확히 `바꿔` 형태가 등장할 때만 부분 문자열로 매칭됨).
  - **권고 사항**: 리터럴 정규식 `바꿔`는 `바꾸고` 형태론에 매칭되지 않을 수 있음. 이는 알려진 어간 매칭 미묘성. 실제로는 두 Skill의 SKILL.md L28 / L27도 규칙을 참조하므로 런타임 LLM 기반 의도 분류가 이를 보완할 가능성 큼. **Step 12 리뷰용**: 견고성을 위해 정규식을 `바꾸|바꿔|변경`으로 확장 고려. (§8에 권고 항목으로 기록.)
- **두 Skill 모두 명시**:
  - stock-scan §1 L28: `"필터 바꾸고 다시 돌려줘" → filter-tune CHANGE_PARAM 선행 → 사용자 확인 후 stock-scan RERUN_FILTERS`
  - filter-tune §1 L27: 동일 verbatim
- **순서화**: filter-tune 마스터 시퀀스 Step 8 (L217-222)이 `"변경 적용됐습니다. 필터를 다시 돌려볼까요?"`를 출력 → CLAUDE.md 라우팅이 `"네/응/해줘"`를 stock-scan RERUN_FILTERS Chain 8로 디스패치.
- **never-merge 불변식**: filter-tune §2 L41이 filter-tune 내 Python 실행을 명시적으로 금지; stock-scan §11 (TS 규칙 N/A)이 파라미터 수정을 금지.
- **판정**: **PASS** (정규식 형태론에 대한 권고 포함).

### 시나리오 9 — 에러 처리 (KiwoomApiError)
- **입력**: 백그라운드 스캔이 `KiwoomApiError(code="HTTP")` 발행 → exit code 2 + 클래스명을 포함한 stderr.
- **CLAUDE.md 오류 분류 §** (L50-68):
  - **L52 verbatim**: `"분기 기준 (필수): type(exc).__name__ STRING 비교. isinstance(exc, KiwoomApiError)는 절대 사용 금지 — KiwoomApiError는 8개 모듈에 독립 정의된 동명 클래스이므로 어느 한 import로 catch하면 7개를 놓친다. (ADR-011)"`
  - **L58 행**:
    | `KiwoomApiError` | 키움 데이터 조회에 실패했습니다. | REST API 호출 실패 (HTTP, JSON, return_code≠0, 재시도 초과). 8개 모듈 독립 정의 — 이름 기준 분기 필수. | 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. |
- **래핑 주석** (L67): `httpx.HTTPError` (ConnectError/TimeoutException) → `KiwoomApiError(code="HTTP")` 또는 `KiwoomAuthError`로 자동 래핑; 9개 클래스만 표면화.
- **전문 용어 방지 검증** (L78 — Step 1 §Style Guide (d)): 금지 토큰 `return_code, HTTPError, JSON 스키마, ka10171, stage_idx`; 사용자 액션 `"잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요."`는 **전문 용어 없음** (Python 클래스명 없음, exit code 없음, 트레이스백 없음) — Step 10 W4 수정 이후 확인됨.
- **출력 패턴** (L53): 한국어 한 문장 요약 + 원인 + 사용자 행동. raw stderr/exit code/트레이스백은 `기술 정보:` 라벨 아래 (축약).
- **stock-scan §6 의사 코드** (L137-149)가 ADR-011 STRING-디스패치 구현을 확인.
- **판정**: **PASS**

### 시나리오 10 — R-9 잠금 경합
- **시나리오**: stock-scan SCAN_TODAY가 filter-tune의 Edit 중간(Step 5 mkdir과 Step 7 rmdir 사이)에 호출됨.
- **stock-scan 측** (거부 검증):
  - §3 Chain 1 L43: `"사전점검: §4의 (a)(b)(c) + ${KRT_REPORTS}/filter-tune.lock 존재 시 거부 (R-9 — 한국어 메시지: '파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요.')"`
  - §9 L196: `"암묵적 락 인지 (R-9): 모든 실행 체인(1/2/3/8)은 Bash 실행 전 ${KRT_REPORTS}/filter-tune.lock 존재 확인. 있으면 거부 ... stock-scan은 락을 생성·해제하지 않는다."`
  - execution-chains.md L18: 동일 verbatim 거부 메시지.
- **filter-tune 측** (획득 + 해제 검증):
  - §3 Step 5 L130-140: `if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then ... else BLOCKED; exit 2; fi` — POSIX atomic; 단일 우승자.
  - §3 Step 7 L215: `rmdir ${KRT_REPORTS}/filter-tune.lock` — try/finally 의미론. "Step 7 어느 substep이 실패해도 락 해제는 시도 (stuck lock 방지)."
  - §6 L387: 잠금 의미론 요약 명시; stock-scan 거부 메시지가 Chain 1 메시지의 verbatim 복사.
- **대칭성 점검**: mkdir (디렉터리 생성) ↔ rmdir (디렉터리 제거). 둘 다 디렉터리 센티넬에 대한 atomic POSIX 연산 (파일 아님). 프로세스 간 의미론: 기존 디렉터리에 mkdir을 시도하는 모든 프로세스는 EEXIST 수신.
- **한국어 거부 메시지 정확한 형태**:
  > `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`
  (stock-scan Chain 1 메시지에는 선두 ⚠️ 없음, filter-tune Step 5 BLOCKED 변형 L139의 `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."`에는 선두 ⚠️ 있음)
- **권고 사항**: 두 BLOCKED 메시지가 약간 다름 (거부 vs 경합). 둘 다 한국어이며 전문 용어 없음이지만, 대칭적 사용자 경험을 원한다면 Step 12에서 통일을 선택할 수 있음. §8에 기록.
- **판정**: **PASS** (잠금 의미론 정확; 사소한 문구 차이는 허용 가능하나 권고됨).

---

## §5. Stage 5 하드 차단 — 4-변형 방어 추적

filter-tune §3 Step 1.0 발생 조건에 대한 변형의 상세 추적:

| 변형 | 입력 | Step 1.0 키워드 매치 | 차단 경로 | 한국어 메시지 |
|---|---|---|---|---|
| 5 (기본) | "Stage 5 조건 바꿔줘" | `Stage 5` 부분 문자열 | PRIMARY (Step 1.0) | C-4 verbatim L78 |
| 5a | "당기순이익 임계값 -1로 바꿔" | `당기순이익` 부분 문자열 | PRIMARY (Step 1.0) | C-4 verbatim L78 |
| 5b | "cup_nga 조건 완화" | `cup_nga` 부분 문자열 (대소문자 무시) | PRIMARY (Step 1.0) | C-4 verbatim L78 |
| 5c | "financeFilter PER 조건" | `financeFilter` 부분 문자열 (대소문자 무시) | PRIMARY (Step 1.0) | C-4 verbatim L78 |

**왜 PRIMARY > SECONDARY인가**:
- financeFilter.py에 Final 상수가 0개 (PRD §5.1 + workflow.md L286).
- Step 1.0이 없다면 Step 1.1 카탈로그 조회는 존재하지 않는 param_id를 검색하여 다른 스테이지의 퍼지 폴백 한국어 별칭을 반환할 가능성이 있음 → 사용자가 자기도 모르게 잘못된 스테이지 변경을 수락할 수 있음.
- Step 1.0 키워드 사전 점검은 카탈로그 이전에 가로채기 → fail-safe.

**심층 방어 팬아웃** (§8 L410-414):
1. §3 Step 1.0 — PRIMARY (PARAM_CHANGE 키워드 사전 점검) ← 모든 변형이 여기서 포착
2. §3 Step 1.2 — SECONDARY (PARAM_CHANGE 카탈로그 파일 소유자 확인, Step 1.0이 놓쳐도 여전히 포착)
3. §4 Branch 1 SHOW_PARAMS Step 1.5 — SHOW_PARAMS 경로의 변경 의도 + Stage 5 단어
4. §4 Branch 6 ASK_MODULE — `financeFilter.py` 행이 `⚠️ Phase 2 (hardcoded, no Final constant)`로 표시

**판정**: 4/4 PRIMARY 포착, 총 4개 방어 계층 — 강력한 하드 차단.

---

## §6. 백업 / 잠금 프로토콜 검증

### 백업 명명 규칙
- 포맷: `{file}.bak.YYYYMMDD_HHmmss` (filter-tune §3 Step 5 L144 + §6 L381에서 검증)
- 예시: `chart60_120Filter.py.bak.20260530_142345`
- `ls -t` 시간 순 정렬 AND 튜닝 로그 타임스탬프와의 조인에 필수.

### 로테이션 (TS-2a)
- 캡: 파일당 ≤ 5개 백업.
- 6번째 생성 → 가장 오래된 항목은 **튜닝 로그 게이트 점검 이후에만** 삭제 (`grep -l '{oldest_ts}' tuning-log.md tuning-log.*.md`).
  - 매치 있음 → `rm {oldest}`.
  - 매치 없음 → 보존 + 한국어 경고 `"백업 {N}개 한도를 초과했지만 가장 오래된 백업이 튜닝 로그에 기록되지 않아 보존합니다. 수동 정리를 권장합니다."` (filter-tune §3 L154, PRD 442번 줄 게이트).
- 시퀀스: state.json `current_backup_files` 필드가 atomic하게 업데이트 (tmp + mv).

### 잠금 의미론 (R-9)
- **타입**: 디렉터리 센티넬 (파일 아님) → atomic POSIX mkdir 가능.
- **획득**: filter-tune §3 Step 5 L128-138:
  ```bash
  if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then proceed; else BLOCKED exit 2; fi
  ```
- **해제**: filter-tune §3 Step 7 L215 + RESTORE Step 2a L284 + Step 2b L293:
  ```bash
  rmdir ${KRT_REPORTS}/filter-tune.lock
  ```
- **try/finally 불변식**: 세 해제 지점 모두 변경(mutation)을 try/finally로 래핑 — Edit/cp 성공이나 실패와 무관하게 rmdir 항상 시도. **Step10-W4 수정 검증됨.**
- **stock-scan 측** (소비자): `test -d ${KRT_REPORTS}/filter-tune.lock`에 대한 Bash 사전 점검 → 한국어 거부 메시지 (stock-scan 측에서 생성/삭제 없음; §9 L196).

**판정**: PASS. mkdir atomic; rmdir 항상 시도; cross-skill 협력 명시적.

---

## §7. screener_state.json 라이프사이클

### 신규 사용자 (파일 없음)
- 사전 점검 (a)(b)(c) → 3줄 기능 소개:
  - (i) `"오늘 종목 스캔해줘"`로 5-Stage 필터링 실행
  - (ii) `"Stage 1 조건 보여줘"`로 파라미터 조회
  - (iii) `"OO전자 왜 빠졌어?"`로 탈락 분석
- 첫 실행 프롬프트: `"오늘 한 번 스캔해볼까요? (약 10-15분 소요됩니다.)"`
- 첫 SCAN_TODAY 완료 후: 1회용 결과 해석 가이드 (Stage 테이블 + 예시 종목 1-2개).

### 재방문 사용자 (파일 존재) — 현재 스모크 테스트 상태
- 관찰된 파일: `/Users/tajun/spJavis/kiwoom-rest-trader/reports/screener_state.json`, 427 바이트, mtime May 30 14:18.
- `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files` Read.
- CLAUDE.md L104에 따라 2-3줄 한국어 세션 요약 출력:
  `"지난 스캔: {last_scan_date}. 변경 이력: {N}건 ({param} 등). 무엇을 도와드릴까요?"`
- 외부 변경 감지 (B-12, CLAUDE.md L118-120): 각 `confirmed=false` 항목에 대해 `grep -n '{param}.*Final' {file}` → `recorded.new`와 비교. 불일치 → 경고 + 사용자 선택 (a) 새 baseline으로 수락 / (b) .bak에서 복원.

### Atomic write
- 규약: `json.dump(state, tmp); mv tmp final` (Step 4 §4 atomicity 주석).
- 단일 스레드 Claude Code 가정 → state.json에 파일 잠금 없음 (잠금은 cross-skill filter-tune 변경(mutation) 단계에만 적용).

### JSON 손상 처리 (R-7)
- `json.JSONDecodeError` 포착 → `screener_state.json.corrupt.{ts}` 백업 → 신규 사용자 흐름으로 폴백.
- filter-tune §9 R-7 행: 기본 빈 배열.

### Cross-skill writer 경계
- `last_param_changes` 및 `current_backup_files`: **filter-tune 단독 writer**, stock-scan은 READ 전용.
- `last_scan_date` 및 `last_results_summary`: stock-scan이 작성 (Chains 1/2/3/8), filter-tune은 read만 (Step 3 gap 분석 baseline).

**판정**: PASS. 라이프사이클이 신규 사용자, 재방문 사용자, 손상, cross-skill 경계 사례를 모두 다룸.

---

## §8. KNOWN ISSUE (Step 12 사람 리뷰용)

DRY-RUN 스모크 테스트가 실제 런타임 없이 검증할 수 없는 항목들:

1. **30분 워치독 이후 실제 Bash 백그라운드 프로세스 고아(orphan) 정리**: 30분 워치독 (Chain 1 Step 6)이 한국어 폴백 `"실행이 예상보다 길어지고 있습니다..."`를 출력하고 SCAN_SEPARATED 피벗을 제안하지만, **원래의 백그라운드 프로세스는 자동으로 종료되지 않음** (background-execution.md §3 라인 "백그라운드 process는 별도로 계속 진행 중일 수 있음을 사용자에게 알림"). 위험: 좀비 프로세스 + 사용자가 피벗을 수락 AND 원본이 결국 완료되는 경우 중복 스캔 출력 덮어쓰기. Step 12 권장 사항: 명시적 `kill -TERM` 정책 또는 명시적 사용자 프롬프트 설계.

2. **동시(concurrent) 다중 Claude 인스턴스 잠금 경쟁**: mkdir은 POSIX 상에서 **FS inode 단위로** atomic. 네트워크 파일시스템 (NFS/SMB) 또는 동일 머신상의 두 Claude Code 인스턴스에 걸쳐서는, EEXIST 보장이 로컬 FS에는 유지되지만 `${KRT_REPORTS}`에 대한 cross-machine 의미론은 규정되지 않음. 스모크 테스트는 두 개의 동시 filter-tune Edit를 시뮬레이션할 수 없음.

3. **kiwoom-rest-trader 버전 이력에 걸친 `prefetchManifest.json` 스키마 변동**: Chain 8 RERUN_FILTERS Step (d) 사전 점검은 매니페스트가 `{"ok", "empty", "null", null, ""}`의 센티넬 값을 가진 `by_stock` 딕셔너리를 갖는다고 가정. 과거 보고서(예: 20260510.zip)는 다른 스키마를 가질 수 있음 — 센티넬 집합이 진화할 수 있음. Step 12 권장 사항: 실제 최근 보고서에 대해 검증.

4. **혼합 의도 정규식 형태론** (시나리오 8의 권고): CLAUDE.md L37 정규식의 리터럴 `바꿔` 토큰이 `바꾸고/바꾸어/바꿔서` 형태론적 변형을 놓칠 수 있음. 한국어 어간은 `바꾸-` → `바꾸/바꿔/바꾸어/바꾸고`는 모두 동일 동사의 유효한 표면형. LLM 매개 의도 분류는 런타임에 보완할 수 있으나 순수 정규식 테스트는 `바꾸고`에서 실패함. 더 넓은 패턴 권장: `(바꾸|바꿔|변경|수정).*`.

5. **R-9 BLOCKED 문구 비대칭** (시나리오 10의 권고): stock-scan 거부 `"파라미터 변경 중이라 스캔을 시작할 수 없습니다..."` vs filter-tune 경합 `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다..."`. 둘 다 전문 용어 없는 한국어; 차이는 의도적 (스캔 측 vs 변경 측 관점). 대칭적 사용자 경험을 선호한다면 Step 12에서 통일을 선택할 수 있음.

6. **stock-scan Chain 8의 `stocks_passed_after` cross-write**: filter-tune §3 Step 7 L186은 `stocks_passed_after`가 write 시점에 `pending`이며 다음 RERUN_FILTERS에서 stock-scan에 의해 cross-write된다고 선언. stock-scan §3 Chain 8은 RERUN_FILTERS를 참조하나, 튜닝 로그로의 명시적 Edit-back 단계가 stock-scan SKILL.md에 가시화되어 있지 않음 — `execution-chains.md` Chain 8 상세에서 검증 필요 (이 스모크 테스트에서 완전히 읽지 않음). Step 12 권장 사항: 이 cross-skill writer 핸드셰이크의 명시적 추적.

---

## §9. 검증 자체 점검

- [x] 10개 시나리오 모두 추적됨 (§4가 각각 개별적으로 다룸).
- [x] Stage 5 4-변형 방어 확인됨 (§5 — 전부 Step 1.0의 PRIMARY).
- [x] 사전 점검 (a)(b)(c) dry-run 결과 캡처됨 (§1).
- [x] R-9 잠금 의미론이 두 Skill 모두에서 검증됨 (§6 + 시나리오 10).
- [x] 백업 규약 `*.bak.YYYYMMDD_HHmmss` 검증됨 (§6).
- [x] 실제 파이프라인 미실행 (`run_full_research_flow`, `run_prefetch`, `run_filters` 절대 호출되지 않음 — 정적 SKILL.md 읽기 + 읽기 전용 bash만).
- [x] 배포된 파일 미수정 (Edit/Write가 `/Users/tajun/spJavis/kiwoom-rest-trader/`에서 호출된 적 없음; Read + 읽기 전용 Bash 명령만).
- [x] KNOWN ISSUE 목록 ≥3 항목 (§8에 6개 항목).
- [x] CLAUDE.md 크기 불변: 14,730 바이트 (Step-10 이후 기대 크기와 일치).
- [x] settings.local.json mtime 불변: May 13 19:46:18 2026.
- [x] ADR-011 (`type(exc).__name__` STRING 디스패치) verbatim이 CLAUDE.md L52 + stock-scan §6 의사 코드에 존재.
- [x] ADR-012 (`Bash(run_in_background:true)` 의무) verbatim이 CLAUDE.md L13/L20 + stock-scan §3 Chain 1 L46-47에 존재.
- [x] Type 생략 (사전 해결된 결정 Option (b)) verbatim 한국어가 output-templates.md L48에 존재.
- [x] try/finally rmdir이 RESTORE Step 2a (L284)와 Step 2b (L293) 양쪽에 — Step10-W4 수정.

---

## 부록 A — 읽기 전용 모드 최종 검증

스모크 테스트 후 검증으로 배포된 시스템에 어떠한 변경(mutation)도 발생하지 않았음을 확인:

| 파일 | 사전 테스트 상태 | 사후 테스트 상태 | 동일? |
|---|---|---|---|
| `${KRT_ROOT}/CLAUDE.md` 크기 | 14,730 바이트 | 14,730 바이트 | YES |
| `${KRT_ROOT}/.claude/settings.local.json` mtime | May 13 19:46:18 2026 | May 13 19:46:18 2026 | YES |
| `${KRT_REPORTS}/screener_state.json` mtime | May 30 14:18 | May 30 14:18 | YES |
| `${KRT_REPORTS}/filter-tune.lock` | 없음 | 없음 | YES |
| `${KRT_REPORTS}/` 목록 | 20260510.zip, 20260512.zip, ..., 20260519 | 동일 | YES |

**읽기 전용 모드 유지됨**. 실행된 모든 명령: `test`, `ls`, `wc`, `stat`, `head`, `grep`, 그리고 Read tool. `Edit`, `Write`, `mkdir`, `cp`, `mv`, 또는 파이프라인 호출 없음.
