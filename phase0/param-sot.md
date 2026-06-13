# Phase 0 — 과업 0-5: 파라미터 SOT 재기준선 (engine 단독)

> 작성: 2026-06-13 / 작성자: Phase 0 워커
> 대상: `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/` 전 모듈
> 방법: Python `ast` 모듈 기반 전수 추출(독립 스크립트) + factory 동결 도구 `param_ast.py` 교차 실행 — 두 방법 결과 **완전 일치**
> 엔진 git 기준선: kiwoom-rest-trader HEAD `359fb57`, itemFilter 최종 커밋 `fa9f340` (2026-06-12), `git status --porcelain -- src/kiwoom/itemFilter` 출력 없음(클린)

---

## 0. 결론 요약 (3줄)

1. **엔진 실측 전수 = `Final` 선언 87개** (10개 `.py` 파일, 수치 선언 32개 / distinct 수치명 30개). factory README의 87은 **정확**하다.
2. **step-1 인벤토리의 75는 "76의 산술 착오"**다: 스코프에서 stageMasterFilter(11개)를 명시 제외한 것은 의도된 설계이고, 추가로 chartDayFilter를 자기 표에는 12행 적고 합산에는 11로 넣은 −1 슬립이 있다. `75 + 1(chartDayFilter 슬립) + 11(stageMasterFilter 스코프 제외) = 87`로 **완전 정합**.
3. canonical 제안: **"SOT = 코드이며, 그 집계는 `param_ast.extract_dir(${KRT_FILTERS})` 출력으로 정의된다"** — 전수(인벤토리) 스코프 87 / Phase-1 튜닝 스코프 76(= 87 − stageMasterFilter 11). 숫자 "75"는 신규 산출물에서 인용 금지.

---

## 1. 모듈별 `Final` 선언 전수 집계 (AST 실측, 2026-06-13)

추출 기준: 모듈 레벨 `ast.AnnAssign` + annotation이 `Final`/`Final[...]`/`typing.Final`. 백업 파일 `chartDayFilter.py.bak.20260601_211732`는 `.py` 확장자가 아니므로 양쪽 도구 모두 자동 제외(내용은 라이브 파일과 `diff` 결과 동일 — 카운트 영향 0).

### 1.1 모듈별 합계

| 모듈 | Final 전체 | 수치(임계) | 수치(윈도우/표본) | 수치(구조ε) | 경로/파일명 | 정규식 | 라벨/마커 | 구조(튜플/디스패치/상태경로) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `Filter_condition_update.py` | 6 | 0 | 0 | 0 | 4 | 1 | 0 | 1 |
| `__init__.py` | 0 | — | — | — | — | — | — | — |
| `chart240Filter.py` | 5 | 1 | 1 | 0 | 3 | 0 | 0 | 0 |
| `chart60Filter.py` | 7 | 1 | 1 | 0 | 3 | 2 | 0 | 0 |
| `chart60_120Filter.py` | 26 | 10 | 4 | 0 | 4 | 0 | 7 | 1 |
| `chartDayFilter.py` | 12 | 5 | 2 | 0 | 3 | 2 | 0 | 0 |
| `chartDayPreFilter.py` | 4 | 1 | 0 | 0 | 3 | 0 | 0 | 0 |
| `financeFilter.py` | 6 | 0 | 0 | 0 | 3 | 2 | 1 | 0 |
| `investorFilter.py` | 10 | 4 | 1 | 0 | 3 | 2 | 0 | 0 |
| `stageMasterFilter.py` | 11 | 0 | 0 | 1 | 7 | 0 | 0 | 3 |
| **합계** | **87** | **22** | **9** | **1** | **33** | **9** | **8** | **5** |

- 수치 선언 합계 = 22 + 9 + 1 = **32** (factory `param_ast.py` CLI 출력 "87 Final constants (**32 numeric**)"과 일치).
- distinct 수치명 = **30** (`_REQUIRED_CONSECUTIVE_BARS`가 3개 모듈에 동명 독립 선언 → 32 − 2). 배포본 `validate_param_values.py` 출력 "87 Final constants (**30 distinct numeric**)"과 일치.
- 비수치 = 87 − 32 = **55**.

### 1.2 상수 단위 전수 표 (87개)

분류 약어: **임계** = 수치 임계(튜닝 가능) · **윈도우** = 수치 윈도우/표본 크기(튜닝 가능하나 입력 fixture 16-bar에 상한) · **경로** = 경로/파일명 · **정규식** · **라벨/마커** · **구조** = 튜플/디스패치/상태경로/ε.

#### Filter_condition_update.py (6)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 64 | 경로 |
| `_MASTER_REFERENCE_MD` | `'masterReference.md'` | 65 | 경로 |
| `_MASTER_REFERENCE_LOG` | `'masterReference.log'` | 66 | 경로 |
| `_RESEARCHED_MD` | `'researchedCompany.md'` | 67 | 경로 |
| `_STAGES` | Stage 1~5 6-튜플 리스트 | 72 | 구조 |
| `_NAME_CODE_RE` | `^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$` | 88 | 정규식 |

#### chart240Filter.py (5)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 72 | 경로 |
| `_CHART240_FILENAME` | `'chart240.md'` | 73 | 경로 |
| `_OUTPUT_FILENAME` | `'chart240Filter.md'` | 74 | 경로 |
| `_MA60_MA306_TOLERANCE` | `0.025` | 78 | 임계 |
| `_REQUIRED_CONSECUTIVE_BARS` | `3` | 81 | 윈도우 |

#### chart60Filter.py (7)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 68 | 경로 |
| `_CHART60_FILENAME` | `'chart60.md'` | 69 | 경로 |
| `_OUTPUT_FILENAME` | `'chart60Filter.md'` | 70 | 경로 |
| `_MA_ALIGNMENT_TOLERANCE` | `0.005` | 75 | 임계 |
| `_REQUIRED_CONSECUTIVE_BARS` | `3` | 78 | 윈도우 |
| `_STOCK_DIR_PATTERN` | `^(.+?)\((\d{4,6})\)$` | 81 | 정규식 |
| `_TABLE_ROW_PATTERN` | 60분봉 표 행 파서(10 capture) | 86 | 정규식 |

#### chart60_120Filter.py (26)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 110 | 경로 |
| `_CHART60_FILENAME` | `'chart60.md'` | 111 | 경로 |
| `_CHART120_FILENAME` | `'chart120.md'` | 112 | 경로 |
| `_OUTPUT_FILENAME` | `'chart60_120Filter.md'` | 113 | 경로 |
| `_REQUIRED_STATIC_BARS` | `8` | 116 | 윈도우 |
| `_ALIGN_TOL_LOOSE` | `0.015` | 120 | 임계 (B/C/D 공유 — 주의) |
| `_TYPE_A_ALIGN_TOL` | `0.035` | 125 | 임계 |
| `_TYPE_B_BELOW_MA60_RATIO` | `0.97` | 128 | 임계 |
| `_TYPE_C_CONVERGE_PCT` | `0.035` | 131 | 임계 |
| `_TYPE_D_ALIGN_TOL_120` | `0.02` | 134 | 임계 |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | `0.5` | 137 | 임계 |
| `_TYPE_D_DYNAMIC_WINDOW` | `16` | 138 | 윈도우 |
| `_TYPE_E_SPREAD_PCT` | `0.1` | 143 | 임계 |
| `_TYPE_E_DYNAMIC_WINDOW` | `8` | 145 | 윈도우 |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | `0.75` | 146 | 임계 |
| `_TYPE_E_SHORT_ALIGN_WINDOW` | `2` | 149 | 윈도우 |
| `_TYPE_E_SHORT_ALIGN_TOL` | `0.016` | 152 | 임계 |
| `_TYPE_E_MA60_OVER_MA306_TOL` | `0.035` | 156 | 임계 |
| `_LABEL_A` | `'A'` | 159 | 라벨/마커 |
| `_LABEL_B` | `'B'` | 160 | 라벨/마커 |
| `_LABEL_C` | `'C'` | 161 | 라벨/마커 |
| `_LABEL_D` | `'D'` | 162 | 라벨/마커 |
| `_LABEL_E` | `'E'` | 163 | 라벨/마커 |
| `_LABEL_EXCLUDED` | `'제외'` | 164 | 라벨/마커 |
| `_LABEL_SKIP` | `'스킵'` | 165 | 라벨/마커 |
| `_TYPE_CHECKERS` | A→B→C→D→E 디스패치 튜플 | 572 | 구조 |

#### chartDayFilter.py (12)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 55 | 경로 |
| `_CHARTDAY_FILENAME` | `'chartDay.md'` | 56 | 경로 |
| `_OUTPUT_FILENAME` | `'chartDayFilter.md'` | 57 | 경로 |
| `_MA10_MA20_MA60_TOLERANCE` | `0.05` | 61 | 임계 |
| `_MA60_MA306_LOWER_TOL` | `0.15` | 63 | 임계 |
| `_MA60_MA306_UPPER_TOL` | `0.45` | 64 | 임계 |
| `_CLOSE_VS_MA612_LOWER` | `-0.15` | 68 | 임계 |
| `_CLOSE_VS_MA612_UPPER` | `0.5` | 69 | 임계 |
| `_REQUIRED_CONSECUTIVE_BARS` | `3` | 72 | 윈도우 |
| `_REQUIRED_ALIGNED_BARS` | `2` | 73 | 윈도우 |
| `_STOCK_DIR_PATTERN` | `^(.+?)\((\d{4,6})\)$` | 75 | 정규식 |
| `_TABLE_ROW_PATTERN` | 일봉 표 행 파서(11 capture, MA612 포함) | 78 | 정규식 |

#### chartDayPreFilter.py (4)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 46 | 경로 |
| `_CHARTDAY_FILENAME` | `'chartDay.md'` | 47 | 경로 |
| `_OUTPUT_FILENAME` | `'chartDayPreFilter.md'` | 48 | 경로 |
| `_DAILY_SURGE_THRESHOLD` | `0.15` | 51 | 임계 |

#### financeFilter.py (6)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 34 | 경로 |
| `_FINANCE_FILENAME` | `'finance.md'` | 35 | 경로 |
| `_OUTPUT_FILENAME` | `'financeFilter.md'` | 36 | 경로 |
| `_STOCK_DIR_PATTERN` | `^(.+?)\((\d{4,6})\)$` | 38 | 정규식 |
| `_CUP_NGA_ROW_PATTERN` | 당기순이익 행 파서 | 41 | 정규식 |
| `_INVALID_MARKER` | `'응답 데이터 없음'` | 46 | 라벨/마커 |

※ Stage 5 판정식 `cup_nga < 0`은 하드코딩(Final 상수 없음) — Phase 1 튜닝 불가가 설계상 한계(step-1:147, TS-1 예외와 일치).

#### investorFilter.py (10)

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 39 | 경로 |
| `_INVESTOR_FILENAME` | `'investor.md'` | 40 | 경로 |
| `_OUTPUT_FILENAME` | `'investorFilter.md'` | 41 | 경로 |
| `_REQUIRED_BARS` | `16` | 43 | 윈도우 |
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | `2` | 46 | 임계 |
| `_THRESHOLD_INST_CONSEC_SELL` | `8` | 47 | 임계 |
| `_THRESHOLD_INDI_CONSEC_BUY` | `3` | 48 | 임계 |
| `_THRESHOLD_FOREIGN_TOTAL_SELL` | `15` | 49 | 임계 |
| `_STOCK_DIR_PATTERN` | `^(.+?)\((\d{4,6})\)$` | 51 | 정규식 |
| `_TABLE_ROW_PATTERN` | 투자자 표 행 파서(4 capture, 부호 보존) | 54 | 정규식 |

#### stageMasterFilter.py (11) — Phase-1 튜닝 스코프 외

| 상수 | 값 | 라인 | 분류 |
|---|---|---:|---|
| `_DEFAULT_REPORTS_ROOT` | `Path('reports')` | 57 | 경로 |
| `_CHARTDAY_FILENAME` | `'chartDay.md'` | 58 | 경로 |
| `_ORG_FILENAME` | `'organizedCompany.md'` | 59 | 경로 |
| `_MASTER_FILENAME` | `'masterReference.md'` | 60 | 경로 |
| `_OUTPUT_FILENAME` | `'masterConditionCompany.md'` | 61 | 경로 |
| `_STATE_PATH` | `Path(__file__)...parent / 'stageMasterFilter_state.json'` | 63 | 경로 |
| `_STATE_BACKUP_PATH` | `_STATE_PATH + '.bak'` | 64 | 경로 |
| `_DEFAULT_BOOTSTRAP_DATES` | `('20260518'~'20260522')` 5일 튜플 | 68 | 구조 |
| `_FEATURES` | 4-feature 튜플(close_over_ma20 등) | 73 | 구조 |
| `_OPTIONAL_FEATURES` | `frozenset({'close_over_ma306'})` | 80 | 구조 |
| `_EPS` | `1e-06` | 83 | 구조ε (수치이나 비교 epsilon — 튜닝 비대상) |

#### __init__.py (0)

`Final` 선언 없음 (AST 실측 0건).

---

## 2. 기존 집계와의 대조 — 75 vs 87 차이의 모듈 단위 해명

### 2.1 두 숫자의 출처

| 숫자 | 출처 | 정의된 스코프 |
|---|---|---|
| **75** | `AgenticWorkflow-main-stock-filtering-collector/prompt/outputs/step-1-param-inventory.md:247` ("Grand total: 75 Final constants ... across 8 source files") | "7 active filter modules + Filter_condition_update.py" — **stageMasterFilter.py 명시 제외** (같은 문서 :5 "Scope exclusion: stageMasterFilter.py (Phase 2 per PRD §12)") |
| **87** | `AgenticWorkflow-main-stock-filtering-collector/README.md:233` ("`param_ast`/`validate_param_values`로 87개 Final 상수 무할루시네이션 검증") | `param_ast.extract_dir`가 `filters_dir.glob("*.py")` **전체**를 순회 (`prompt/.claude/codegen/param_ast.py:106`) — 즉 stageMasterFilter.py·__init__.py 포함 디렉터리 전수 |

### 2.2 모듈 단위 차이 분해 (완전 정합)

| 모듈 | step-1 자기검증 카운트 | step-1 본문 표 실제 행수 | 엔진 AST 실측(오늘) | 차이 원인 |
|---|---:|---:|---:|---|
| Filter_condition_update.py | 6 (step-1:235) | 6 | 6 | **양쪽 모두 포함** — 차이 요인 아님 |
| chart60Filter.py | 7 (step-1:236) | 7 | 7 | 일치 |
| chart60_120Filter.py | 26 (step-1:237) | 26 | 26 | 일치 |
| chart240Filter.py | 5 (step-1:238) | 5 | 5 | 일치 |
| chartDayPreFilter.py | 4 (step-1:239) | 4 | 4 | 일치 |
| **chartDayFilter.py** | **11** (step-1:240) | **12** (step-1:111–122, 12행) | **12** | **−1 산술 슬립**: 자기검증 줄이 11로 합산하면서 같은 줄 괄호에 "*(count = 12 incl. dual regexes; itemized correctly above)*"라고 스스로 12임을 적어둠. 본문 표는 12행으로 정확 |
| investorFilter.py | 10 (step-1:241) | 10 | 10 | 일치 |
| financeFilter.py | 6 (step-1:242) | 6 | 6 | 일치 |
| **stageMasterFilter.py** | — (스코프 제외, step-1:5) | — | **11** | **의도된 스코프 제외** (Phase 2, PRD §12) — 87에는 포함 |
| __init__.py | — | — | 0 | 양쪽 모두 0 — 차이 요인 아님 |
| `chartDayFilter.py.bak.*` | — | — | 미집계 | `.py` glob 비매치로 양쪽 자동 제외. 내용도 라이브 파일과 동일(diff 검증) |
| **합계** | **75** | **76** | **87** | `75 = 76 − 1(슬립)` / `87 = 76 + 11(stageMaster)` |

**산식: 75 (step-1 공식 합계) + 1 (chartDayFilter 11→12 산술 착오) + 11 (stageMasterFilter 스코프 제외분) = 87 (엔진 실측·README 일치).** 그 외 어떤 모듈에서도 불일치 없음.

### 2.3 교차 검증 (도구 2종 + 동결 게이트 1종)

1. **독립 AST 스크립트** (본 과업에서 작성, /tmp): 87개, 모듈별 분포 §1.1과 동일.
2. **factory 동결 도구 직접 실행**: `python3 prompt/.claude/codegen/param_ast.py ${KRT_FILTERS}` → `Extracted 87 Final constants (32 numeric)` — 본 실측과 동일.
3. **배포본 값-동등성 오라클**: `kiwoom-rest-trader/.claude/skills/filter-tune/scripts/validate_param_values.py` 실행(읽기 전용) → `Code: 87 Final constants (30 distinct numeric)` / `HARD value-equality checks passed: 42` / **exit 0 (PASSED)** / 경고 1건(`_EPS`가 catalog 미수록 — stageMaster 스코프 외이므로 정상). 배포 스크립트는 factory 원본과 **byte-identical** (diff 검증).
4. **라인 정합**: step-1(2026-05-29 생성)의 모든 File:Line 인용이 오늘 AST 실측 라인과 1:1 일치 → step-1 생성 이후 itemFilter의 Final 블록에 추가·삭제·이동 없음.

### 2.4 부수 발견 — 배포 카탈로그의 추가 내부 불일치 (참고)

배포본 `kiwoom-rest-trader/.claude/skills/filter-tune/references/parameter-catalog.md`는 75를 표제로 쓰면서(:1, :5) 자기검증 표에서는 합계 **76\***을 적고 각주로 75와의 긴장을 인정한다(:243, :245). 추가로 Stage 1 섹션 소제목이 "튜닝 대상 (**15개**)"(:35)·"튜닝 비대상 (**11개**)"(:57)인데 실제 표 행수는 **14 / 12**다(합 26은 맞음 — 소제목만 각각 ±1 오류). 같은 뿌리(75 산술 슬립)에서 파생된 표기 흔들림으로 판단된다. `filter-tune/SKILL.md:244`의 "(74/75 params ...)"도 75 계열 숫자를 승계한 문장이다. **본 과업 범위상 파일은 수정하지 않았다.**

---

## 3. Canonical 정의 제안 (filter-tune이 신뢰할 단일 기준)

> **제안 (1개): 파라미터 SOT의 모집단은 문서의 어떤 숫자도 아니고, `param_ast.extract_dir(${KRT_FILTERS})`의 실행 결과 그 자체다.**
> (`${KRT_FILTERS}` = `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter`, 도구 = `kiwoom-rest-trader/.claude/skills/filter-tune/scripts/param_ast.py` — factory `prompt/.claude/codegen/param_ast.py`와 byte-identical)

스코프 명문화:

| 계층 | 정의 | 현재 값 (2026-06-13, HEAD 359fb57) |
|---|---|---|
| **L0 — 전수 인벤토리 스코프** | `${KRT_FILTERS}/*.py` 전체의 모듈레벨 `Final` 선언. `.bak.*`는 glob상 자동 제외. 파일 추가·상수 추가 시 자동 반영 | **87개** (수치 선언 32 / distinct 수치명 30) |
| **L1 — Phase-1 튜닝 스코프** | L0 − `stageMasterFilter.py` (PRD §12/§6.4 Phase 2 유보) | **76개** (active 8개 모듈; 수치 31 선언 / 29 distinct) |
| **L2 — 실질 튜닝 후보** | L1 중 수치 상수(임계 22 + 윈도우 9). financeFilter는 수치 상수 0으로 TS-1 예외(하드코딩 `< 0`) 유지 | **31개** |

운영 규칙(제안):
1. **고정 숫자 인용 금지** — 신규 산출물·대화에서 "Final 상수 N개"를 말할 때는 반드시 `param_ast.py` 실행 결과를 인용하고 스코프(L0=87/L1=76)를 병기한다. 숫자 **"75"는 산술 착오 유래이므로 어떤 신규 문서에서도 재인용 금지**.
2. **게이트 일원화** — filter-tune §11 게이트(`validate_param_values.py`)가 이미 L0 전수를 추출해 배포 문서의 주장 값과 대조한다(오늘 실행: 42건 HARD 통과, exit 0). 이 게이트 통과가 곧 "canonical과 문서의 값 동기화" 증명이다.
3. **카탈로그의 지위** — `references/parameter-catalog.md`는 navigation 참조일 뿐 SOT가 아니라는 자기 선언(:3)을 유지한다. 카운트 표제도 차후(별도 승인 시) 75→76으로 정정 권고. **동결된 factory 문서(step-1, README)는 수정하지 않는다** — 75는 동결 산출물의 역사적 기록으로 두고, 본 문서가 재기준선 해석을 제공한다.

---

## 4. 수정/미수정 선언

- 본 과업에서 **수정한 파일 없음** (엔진·factory·skill 모두 읽기 전용으로만 접근; `validate_param_values.py`는 read-only 도구로 설계 명시 — 해당 스크립트 docstring "Read-only: reads product .py + deployed .md; writes nothing").
- 산출물은 본 파일 1개: `/Users/tajun/spJavis/auto-korea-stock-javis/phase0/param-sot.md`.

## 5. 근거 인덱스 (파일:라인)

| 주장 | 근거 |
|---|---|
| 엔진 전수 87 (32 numeric) | AST 실측(§1.2 전 행에 파일:라인 기재) + `prompt/.claude/codegen/param_ast.py` CLI 실행 출력 |
| README 87 주장 | `AgenticWorkflow-main-stock-filtering-collector/README.md:233` |
| 87의 스코프 = 디렉터리 전수 | `prompt/.claude/codegen/param_ast.py:106` (`filters_dir.glob("*.py")`) |
| step-1 75 주장 | `prompt/outputs/step-1-param-inventory.md:247` |
| step-1 stageMaster 제외 | `prompt/outputs/step-1-param-inventory.md:5` |
| chartDayFilter 11/12 슬립 | `prompt/outputs/step-1-param-inventory.md:240` (자기검증 11 + 괄호 주석 "count = 12") vs 같은 문서 :111–122 (12행) |
| 배포 카탈로그 76* 각주 | `kiwoom-rest-trader/.claude/skills/filter-tune/references/parameter-catalog.md:243,245` |
| 카탈로그 소제목 15/11 vs 실제 14/12 | `parameter-catalog.md:35,57` vs 해당 표 행수 |
| SKILL.md 75 승계 | `kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md:244` |
| 오라클 PASS·_EPS 경고 | `validate_param_values.py` 실행 출력 (exit 0, HARD 42, 경고 `_EPS`) |
| 배포·factory 스크립트 동일 | `diff -q` 결과 SAME (filter-tune/scripts/param_ast.py vs prompt/.claude/codegen/param_ast.py) |
| .bak 파일 무영향 | `diff -q chartDayFilter.py chartDayFilter.py.bak.20260601_211732` → IDENTICAL; glob `*.py` 비매치 |
| git 기준선 | `git rev-parse --short HEAD` = 359fb57; `git log -1 -- src/kiwoom/itemFilter` = fa9f340 (2026-06-12) |

---
## [정정 추기 — 검증관 + 마스터, 2026-06-13]
본 문서의 L0=87은 **기준 커밋 359fb57 시점** 수치다. 직후 0-4 커밋(a9a8f51)이 `_NAME_CODE_RE: Final`(비수치, 정규식 상수)을 추가해 **현재 HEAD 기준 L0=88**이다. 수치 튜닝 스코프(L1=76, L2=31 수치선언/29 distinct)는 영향 없음. canonical 정의는 "param_ast.extract_dir 실행 결과 그 자체"이므로 자동 추종된다.
