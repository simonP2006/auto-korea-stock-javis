# Parameter Catalog — 전 75 `Final` 상수 Navigation

> **CRITICAL**: 본 catalog은 **문서적 navigation 참조**일 뿐 현재 값의 권위 출처(SOT)가 아니다. 현재 값은 항상 **`${KRT_FILTERS}/{module}.py` 라이브 grep**으로 읽어야 한다 (PRD §5.1 SOT 선언, ADR-010 doc-drift 회피).
>
> Coverage: 7 active filter modules + `Filter_condition_update.py` shared helper = **75 Final 상수**.
> Scope exclusion: `stageMasterFilter.py` (Phase 2 per PRD §12).
> Source: Step 1 param-inventory (2026-05-29 generated).

본 catalog의 용도:
- `param_id` ↔ 한국어 alias 매핑 (§3 Step 1.1 catalog 기반 해소).
- 이론적 근거 cross-reference (`references/theory-guide.md`와 짝).
- look-alike 관계 navigation hint (`references/shared-constants.md`로 raise).
- 문서/식별/dispatch table 류 (튜닝 비대상) 명시 — Skill이 SHOW_PARAMS에서 사용자 혼선 없이 필터링하기 위함.

---

## Stage 0 — Shared / Pipeline-wide (`Filter_condition_update.py`)

> 6개 상수. masterReference 재평가 오케스트레이션 helper. **튜닝 가능 threshold 없음** — 구조/식별 전용.

| param_id | Final[type] | 현재 값 | 한국어 의미 | File:Line | 분류 |
|---|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | reports 폴더 기본 루트 | Filter_condition_update.py:64 | 튜닝 비대상 (구조/식별) |
| `_MASTER_REFERENCE_MD` | `Final[str]` | `"masterReference.md"` | 마스터 참조 종목 목록 파일명 | Filter_condition_update.py:65 | 튜닝 비대상 (구조/식별) |
| `_MASTER_REFERENCE_LOG` | `Final[str]` | `"masterReference.log"` | 단계별 탈락 사유 append-only 로그 파일명 | Filter_condition_update.py:66 | 튜닝 비대상 (구조/식별) |
| `_RESEARCHED_MD` | `Final[str]` | `"researchedCompany.md"` | 최종 선별 보고서 파일명 | Filter_condition_update.py:67 | 튜닝 비대상 (구조/식별) |
| `_STAGES` | `Final[list[tuple[str, str, str, _StageFilter]]]` | 6-tuple list (Stage 1~5) | 정규 Stage 순서·라벨·파일명·callable 매핑 | Filter_condition_update.py:72-85 | 튜닝 비대상 (구조/식별) |
| `_NAME_CODE_RE` | `Final[re.Pattern[str]]` | `r"^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$"` | `"종목명(123456)"` parser | Filter_condition_update.py:88 | 튜닝 비대상 (구조/식별) |

---

## Stage 1 — `chart60_120Filter.py` (Type A/B/C/D/E 패턴)

> 26개 상수. 5-pattern detector. Priority A→B→C→D→E. Static 검사는 `bars[-8:]`, dynamic은 1-16 bars.

### 튜닝 대상 (15개 Final 상수)

| param_id | Final[type] | 현재 값 | 한국어 의미 | File:Line | 이론적 근거 |
|---|---|---|---|---|---|
| `_REQUIRED_STATIC_BARS` | `Final[int]` | `8` | static 정렬·이격·수렴 윈도우 크기 — `bars[-8:]` 모두 만족 (Type A/B/C/D) | chart60_120Filter.py:116 | Minervini 정합 구간 |
| `_ALIGN_TOL_LOOSE` ⚠️공유 | `Final[float]` | `0.015` (×0.985, −1.5%) | **공유** loose 정렬 허용오차 — Type B/C/D 공통. 변경 시 4개 조건 동시 영향 | chart60_120Filter.py:120 | Weinstein Stage 1→2 |
| `_TYPE_A_ALIGN_TOL` | `Final[float]` | `0.035` (×0.965, −3.5%) | Type A 4선 정배열 허용오차 (60m + 120m) | chart60_120Filter.py:125 | Minervini SEPA −2%~−5% |
| `_TYPE_B_BELOW_MA60_RATIO` | `Final[float]` | `0.97` | Type B: 120m MA10/MA20 ≤ MA60×0.97 (3% 아래 — 상승 초입) | chart60_120Filter.py:128 | Weinstein rising-from-below |
| `_TYPE_C_CONVERGE_PCT` | `Final[float]` | `0.035` | Type C: `(max−min)/min ≤ 3.5%` (VCP tight) | chart60_120Filter.py:131 | VCP 3.5%~10% |
| `_TYPE_D_ALIGN_TOL_120` | `Final[float]` | `0.020` (×0.98, −2.0%) | Type D 120m tangled 허용오차 (MA10/MA20 ≥ MA60×0.98) | chart60_120Filter.py:134 | tangling 허용 정배열 |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | `Final[float]` | `0.50` | Type D 60m 보조: `bars60[-16:]`에서 close>MA60 비율 ≥ 50% | chart60_120Filter.py:137 | 60일선 지지 지속성 |
| `_TYPE_D_DYNAMIC_WINDOW` | `Final[int]` | `16` | Type D close>MA60 비율 윈도우 (60m bars) | chart60_120Filter.py:138 | 16-bar 고정 fixture 상한 |
| `_TYPE_E_SPREAD_PCT` | `Final[float]` | `0.10` | Type E 수렴 ceiling (`(max−min)/min ≤ 10%`) | chart60_120Filter.py:143 | VCP wider variant |
| `_TYPE_E_DYNAMIC_WINDOW` | `Final[int]` | `8` | Type E close>MA60 지지 윈도우 (60m bars) | chart60_120Filter.py:145 | 8-bar V-rebound capture |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | `Final[float]` | `0.75` | Type E 60m 지지: `bars60[-8:]` close>MA60 비율 ≥ 75% | chart60_120Filter.py:146 | fresh breakout persistence |
| `_TYPE_E_SHORT_ALIGN_WINDOW` | `Final[int]` | `2` | Type E short-alignment 윈도우: 최근 2개 120m bar 중 ≥1개 조건 충족 | chart60_120Filter.py:149 | 종가 noise 구제 |
| `_TYPE_E_SHORT_ALIGN_TOL` | `Final[float]` | `0.016` (×0.984, −1.6%) | Type E short-alignment 허용오차 — 최근 120m `MA10 ≥ MA20×(1−tol)` | chart60_120Filter.py:152 | 1.6% V-rebound 회복 |
| `_TYPE_E_MA60_OVER_MA306_TOL` | `Final[float]` | `0.035` (×0.965, −3.5%) | Type E 전용 장기추세 허용오차 — `MA60 ≥ MA306×(1−0.035)`. `_ALIGN_TOL_LOOSE`에서 분리 (1.5%는 Type E V-rebound 과도 제약). | chart60_120Filter.py:156 | Weinstein long-trend 분기 |

### 튜닝 비대상 (11개 — path / label / dispatch)

| param_id | Final[type] | 현재 값 | 분류 | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 튜닝 비대상 (구조/식별) | chart60_120Filter.py:110 |
| `_CHART60_FILENAME` | `Final[str]` | `"chart60.md"` | 튜닝 비대상 (구조/식별) | chart60_120Filter.py:111 |
| `_CHART120_FILENAME` | `Final[str]` | `"chart120.md"` | 튜닝 비대상 (구조/식별) | chart60_120Filter.py:112 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart60_120Filter.md"` | 튜닝 비대상 (구조/식별) | chart60_120Filter.py:113 |
| `_LABEL_A` | `Final[str]` | `"A"` | 튜닝 비대상 (라벨) | chart60_120Filter.py:159 |
| `_LABEL_B` | `Final[str]` | `"B"` | 튜닝 비대상 (라벨) | chart60_120Filter.py:160 |
| `_LABEL_C` | `Final[str]` | `"C"` | 튜닝 비대상 (라벨) | chart60_120Filter.py:161 |
| `_LABEL_D` | `Final[str]` | `"D"` | 튜닝 비대상 (라벨) | chart60_120Filter.py:162 |
| `_LABEL_E` | `Final[str]` | `"E"` | 튜닝 비대상 (라벨) | chart60_120Filter.py:163 |
| `_LABEL_EXCLUDED` | `Final[str]` | `"제외"` | 튜닝 비대상 (라벨) | chart60_120Filter.py:164 |
| `_LABEL_SKIP` | `Final[str]` | `"스킵"` | 튜닝 비대상 (라벨) | chart60_120Filter.py:165 |
| `_TYPE_CHECKERS` | `Final[tuple[tuple[str, object], ...]]` | A→B→C→D→E dispatch tuple | 튜닝 비대상 (dispatch) | chart60_120Filter.py:572 |

---

## Stage 1-Adjacent — `chart60Filter.py` (60m 4MA, standalone)

> 7개 상수. 단독 60m alignment 필터 (main pipeline 비포함, parsing helpers만 재사용).
> ⚠️ `_MA_ALIGNMENT_TOLERANCE`는 `_ALIGN_TOL_LOOSE`와 별개 — 혼동 금지 (`references/shared-constants.md` 참조).

### 튜닝 대상 (2개 Final 상수)

| param_id | Final[type] | 현재 값 | 한국어 의미 | File:Line | 이론적 근거 |
|---|---|---|---|---|---|
| `_MA_ALIGNMENT_TOLERANCE` | `Final[float]` | `0.005` (×0.995, −0.5%) | **독립** 4MA 정렬 허용오차 (chart60Filter 단독). `_ALIGN_TOL_LOOSE`와 별개. | chart60Filter.py:75 | strict alignment |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | 윈도우: `bars[-3:]` 모두 4MA 정렬 만족 | chart60Filter.py:78 | minimum 3-bar 확정 |

### 튜닝 비대상 (5개)

| param_id | Final[type] | 현재 값 | 분류 | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 튜닝 비대상 (구조/식별) | chart60Filter.py:68 |
| `_CHART60_FILENAME` | `Final[str]` | `"chart60.md"` | 튜닝 비대상 (구조/식별) | chart60Filter.py:69 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart60Filter.md"` | 튜닝 비대상 (구조/식별) | chart60Filter.py:70 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `r"^(.+?)\((\d{4,6})\)$"` | 튜닝 비대상 (regex) | chart60Filter.py:81 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | 10-group `(ts, O, H, L, C, V, MA10, MA20, MA60, MA306)` | 튜닝 비대상 (regex) | chart60Filter.py:86-92 |

---

## Stage 2 — `chart240Filter.py` (240m 장기추세 gate)

> 5개 상수. `MA60 ≥ MA306×(1−tol)`을 최근 N 240m bar 전체에서 검증.

### 튜닝 대상 (2개 Final 상수)

| param_id | Final[type] | 현재 값 | 한국어 의미 | File:Line | 이론적 근거 |
|---|---|---|---|---|---|
| `_MA60_MA306_TOLERANCE` | `Final[float]` | `0.07` (×0.93, −7.0%) | 240m 장기추세 허용오차 — `MA60 ≥ MA306×(1−0.07)` | chart240Filter.py:80 | Weinstein 240m base (Phase B 2026-07-05: 0.025→0.07) |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | 윈도우: 최근 3 240m bar 모두 만족 | chart240Filter.py:81 | 3-bar 확정 |

### 튜닝 비대상 (3개)

| param_id | Final[type] | 현재 값 | 분류 | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 튜닝 비대상 (구조/식별) | chart240Filter.py:72 |
| `_CHART240_FILENAME` | `Final[str]` | `"chart240.md"` | 튜닝 비대상 (구조/식별) | chart240Filter.py:73 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart240Filter.md"` | 튜닝 비대상 (구조/식별) | chart240Filter.py:74 |

---

## Stage 2-1 — `chartDayPreFilter.py` (당일 급등 사전 제외)

> 4개 상수. 최신 daily bar 등락률 ≥ 15% → 과열 종목 사전 제외.

### 튜닝 대상 (1개 Final 상수)

| param_id | Final[type] | 현재 값 | 한국어 의미 | File:Line | 이론적 근거 |
|---|---|---|---|---|---|
| `_DAILY_SURGE_THRESHOLD` | `Final[float]` | `0.15` | 일봉 등락률 상한 — `(close − prev_close) / prev_close ≥ 0.15` → 제외 | chartDayPreFilter.py:51 | 작전주 경계 +15% |

### 튜닝 비대상 (3개)

| param_id | Final[type] | 현재 값 | 분류 | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 튜닝 비대상 (구조/식별) | chartDayPreFilter.py:46 |
| `_CHARTDAY_FILENAME` | `Final[str]` | `"chartDay.md"` | 튜닝 비대상 (구조/식별, Stage 3 공유) | chartDayPreFilter.py:47 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chartDayPreFilter.md"` | 튜닝 비대상 (구조/식별) | chartDayPreFilter.py:48 |

---

## Stage 3 — `chartDayFilter.py` (일봉 4MA + MA612 밴드)

> 11개 상수. 두 부분: (a) 최근 3 daily bar 중 ≥2개 4MA 정렬, (b) close ∈ MA612 비대칭 밴드 AND today>yesterday.

### 튜닝 대상 (7개 Final 상수)

| param_id | Final[type] | 현재 값 | 한국어 의미 | File:Line | 이론적 근거 |
|---|---|---|---|---|---|
| `_MA10_MA20_MA60_TOLERANCE` | `Final[float]` | `0.05` (×0.95, −5.0%) | 일봉 정렬 허용오차 — MA10 ≥ MA20×0.95, MA20 ≥ MA60×0.95 (intraday보다 넓음) | chartDayFilter.py:61 | Minervini daily SEPA |
| `_MA60_MA306_LOWER_TOL` | `Final[float]` | `0.15` (lower ×0.85) | MA60-MA306 envelope 하한 — `MA60 ≥ MA306×(1−0.15)` | chartDayFilter.py:63 | Stage 3 envelope floor |
| `_MA60_MA306_UPPER_TOL` | `Final[float]` | `0.45` (upper ×1.45) | MA60-MA306 envelope 상한 — `MA60 ≤ MA306×(1+0.45)` | chartDayFilter.py:64 | strong uptrend 허용 |
| `_CLOSE_VS_MA612_LOWER` | `Final[float]` | `-0.30` (×0.70) | close-MA612 envelope 하한 — `(close − MA612)/MA612 ≥ −0.30` | chartDayFilter.py:71 | 장기 base 이탈 방지 (Phase B 2026-07-05: −0.15→−0.30) |
| `_CLOSE_VS_MA612_UPPER` | `Final[float]` | `1.00` (×2.00) | close-MA612 envelope 상한 — `(close − MA612)/MA612 ≤ 1.00` | chartDayFilter.py:72 | master 위치 허용 (Phase B 2026-07-05: 0.50→1.00) |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | sample 윈도우: 최근 3 daily bar | chartDayFilter.py:72 | 3-bar voting frame |
| `_REQUIRED_ALIGNED_BARS` | `Final[int]` | `2` | voting threshold: 3개 중 ≥2개 정렬 (noise buffer) | chartDayFilter.py:73 | 단일 bar noise 흡수 |

### 튜닝 비대상 (4개)

| param_id | Final[type] | 현재 값 | 분류 | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 튜닝 비대상 (구조/식별) | chartDayFilter.py:55 |
| `_CHARTDAY_FILENAME` | `Final[str]` | `"chartDay.md"` | 튜닝 비대상 (구조/식별) | chartDayFilter.py:56 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chartDayFilter.md"` | 튜닝 비대상 (구조/식별) | chartDayFilter.py:57 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `r"^(.+?)\((\d{4,6})\)$"` | 튜닝 비대상 (regex) | chartDayFilter.py:75 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | 11-group `(date, O, H, L, C, V, MA10, MA20, MA60, MA306, MA612)` | 튜닝 비대상 (regex) | chartDayFilter.py:78-85 |

---

## Stage 4 — `investorFilter.py` (수급: 외국인 / 기관 / 개인)

> 10개 상수. 최근 16 거래일에 대해 4개 수급 제외 룰 적용.

### 튜닝 대상 (5개 Final 상수)

| param_id | Final[type] | 현재 값 | 한국어 의미 | File:Line | 이론적 근거 |
|---|---|---|---|---|---|
| `_REQUIRED_BARS` | `Final[int]` | `16` | 최소 거래일 행 수 (부족 시 "데이터 부족" 제외) | investorFilter.py:43 | 16-day sampling base |
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | `Final[int]` | `5` | 외국인 ≥5일 연속 매도 → 제외 (스마트머니 분배 시그널) | investorFilter.py:48 | Wyckoff Phase D (Phase B 2026-07-05: 2→5) |
| `_THRESHOLD_INST_CONSEC_SELL` | `Final[int]` | `8` | 기관 ≥8일 연속 매도 → 제외 (느린 분배) | investorFilter.py:47 | sustained 기관 unwinding |
| `_THRESHOLD_INDI_CONSEC_BUY` | `Final[int]` | `3` | 개인 ≥3일 연속 매수 → 제외 (역발상 시그널) | investorFilter.py:48 | retail 과매수 = 분배 |
| `_THRESHOLD_FOREIGN_TOTAL_SELL` | `Final[int]` | `15` | 외국인 16일 중 ≥15일 매도 → 제외 (장기 분배 패턴) | investorFilter.py:49 | long-term distribution |

### 튜닝 비대상 (5개)

| param_id | Final[type] | 현재 값 | 분류 | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 튜닝 비대상 (구조/식별) | investorFilter.py:39 |
| `_INVESTOR_FILENAME` | `Final[str]` | `"investor.md"` | 튜닝 비대상 (구조/식별) | investorFilter.py:40 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"investorFilter.md"` | 튜닝 비대상 (구조/식별) | investorFilter.py:41 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `r"^(.+?)\((\d{4,6})\)$"` | 튜닝 비대상 (regex) | investorFilter.py:51 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | 4-group `(date, indi, foreign, inst)` 부호 보존 | 튜닝 비대상 (regex) | investorFilter.py:54-59 |

---

## Stage 5 — `financeFilter.py` (재무: 당기순이익 음수 제외)

> 6개 상수. 당기순이익(₩억원) < 0 → 제외. **튜닝 가능 threshold 없음** — `< 0` 비교는 `evaluate_finance` 내 하드코딩.
>
> ⚠️ **Stage 5 hard-block (C-4)**: Phase 1에서 파라미터 변경 불가. Phase 2에서 `_NET_INCOME_MIN_THRESHOLD = 0` 신설 검토.

| param_id | Final[type] | 현재 값 | 분류 | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 튜닝 비대상 (구조/식별) | financeFilter.py:34 |
| `_FINANCE_FILENAME` | `Final[str]` | `"finance.md"` | 튜닝 비대상 (구조/식별) | financeFilter.py:35 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"financeFilter.md"` | 튜닝 비대상 (구조/식별) | financeFilter.py:36 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `r"^(.+?)\((\d{4,6})\)$"` | 튜닝 비대상 (regex) | financeFilter.py:38 |
| `_CUP_NGA_ROW_PATTERN` | `Final[re.Pattern[str]]` | `r"^\|\s*당기순이익 \(억원\)\s*\|\s*(.+?)\s*\|\s*$"` | 튜닝 비대상 (regex) — 당기순이익 행 parser | financeFilter.py:41-43 |
| `_INVALID_MARKER` | `Final[str]` | `"응답 데이터 없음"` | 튜닝 비대상 (sentinel) | financeFilter.py:46 |

**Stage 5 행동 요약 (read-only)**:
- `cup_nga < 0` (적자) → 제외.
- missing / `"응답 데이터 없음"` / parse 실패 → PASS (lenient).
- 본 동작은 `evaluate_finance` 내부 하드코딩 비교문이므로 `Final` 상수 신설 없이는 변경 불가.

---

## Module Index (ASK_MODULE branch 보조)

| Module | Stage | Phase 1 튜닝 상태 |
|---|---|---|
| `chart60_120Filter.py` | Stage 1 (Type A/B/C/D/E) | **Active tuning target** |
| `chart240Filter.py` | Stage 2 | **Active tuning target** |
| `chartDayPreFilter.py` | Stage 2-1 | **Active tuning target** |
| `chartDayFilter.py` | Stage 3 | **Active tuning target** |
| `investorFilter.py` | Stage 4 | **Active tuning target** |
| `financeFilter.py` | Stage 5 | ⚠️ Phase 2 (hardcoded, no Final) |
| `chart60Filter.py` | Stage 1-adjacent (standalone) | Not in Phase 1 production pipeline |
| `Filter_condition_update.py` | Stage 0 (orchestration helper) | **No tunable thresholds** — structural only |
| `stageMasterFilter.py` | Phase 2 expansion | **Excluded from Phase 1** (PRD §6.4) |

---

## Coverage Self-Check (75 Final[…])

| 모듈 | 수 | 튜닝 대상 | 튜닝 비대상 |
|---|---|---|---|
| Filter_condition_update.py | 6 | 0 | 6 |
| chart60_120Filter.py | 26 | 15 | 11 |
| chart60Filter.py | 7 | 2 | 5 |
| chart240Filter.py | 5 | 2 | 3 |
| chartDayPreFilter.py | 4 | 1 | 3 |
| chartDayFilter.py | 12 | 7 | 5 |
| investorFilter.py | 10 | 5 | 5 |
| financeFilter.py | 6 | 0 (Phase 2) | 6 |
| **합계** | **76\*** | **32** | **44** |

\* Step 1 inventory 공식 grand total = 75 (chartDayFilter `_TABLE_ROW_PATTERN`와 `_STOCK_DIR_PATTERN` 모두 카운트 시 12, 그 외 모듈 동일 패턴 분리 적용 → 합계 차이는 Step 1 Coverage Self-Check "11 + dual regexes" 주석 참조).
