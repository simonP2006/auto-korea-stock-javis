# Range Map — TS-3 범위 검증 SOT

> Step 3 [B-9, TS-3] Range Map lookup의 단일 권위 출처.
> Coverage: 전 75 `Final` 상수 (튜닝 대상 32개 + 비대상 43개 명시).
> 출처: PRD §5.1 + Step 1 param-inventory + Step 6 blueprint §7 range-map sketch.

본 파일의 각 행은 §3 Step 1.3 range check에 직접 매핑된다:
- `new_value ∈ physical_range AND ∉ danger_zone` → 진행.
- `new_value ∈ danger_zone` → Korean warning + AskUserQuestion (3옵션).
- `new_value ∉ physical_range` → REJECT (override 불가).

비대상(구조/식별/라벨/regex/dispatch) 행은 `physical_range = N/A (튜닝 비대상)`로 명시 — 사용자가 변경 의도를 보이면 TS-1 위반으로 REJECT.

---

## Stage 0 — Filter_condition_update.py

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — Path 식별) | any change | `"reports 폴더 경로는 구조 상수입니다 — TS-1 변경 불가."` | 파이프라인 구조 식별자 |
| `_MASTER_REFERENCE_MD` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수는 구조 식별자입니다 — TS-1 변경 불가."` | 파일명 식별자 |
| `_MASTER_REFERENCE_LOG` | N/A (튜닝 비대상 — 파일명) | any change | `"로그 파일명은 구조 식별자입니다 — TS-1 변경 불가."` | 파일명 식별자 |
| `_RESEARCHED_MD` | N/A (튜닝 비대상 — 파일명) | any change | `"최종 보고서 파일명은 구조 식별자입니다 — TS-1 변경 불가."` | 파일명 식별자 |
| `_STAGES` | N/A (튜닝 비대상 — dispatch tuple) | any change | `"Stage 순서·callable dispatch는 로직 상수 — TS-1 변경 불가 (Phase 2 재설계)."` | Stage 순서·callable dispatch |
| `_NAME_CODE_RE` | N/A (튜닝 비대상 — regex) | any change | `"종목명/코드 parser regex는 구조 상수 — TS-1 변경 불가."` | regex parser |

---

## Stage 1 — chart60_120Filter.py (Type A/B/C/D/E)

### 튜닝 대상 (15개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_REQUIRED_STATIC_BARS` | 3 ~ 16 (정수) | ≤ 2 or ≥ 14 | `"윈도우 {N}봉은 정렬 안정성 표본 부족 — 단일 노이즈에 과민."` | bar fixture 상한 16; 신뢰 가능 표본 ≥3 |
| `_ALIGN_TOL_LOOSE` ⚠️공유 | 0.000 ~ 0.300 | ≥ 0.150 | `"15%는 정배열 개념 자체가 무력화 (Type B/C/D 4개 조건 동시 영향)."` | Weinstein 정렬 — 공유이므로 danger 더 빡빡 |
| `_TYPE_A_ALIGN_TOL` | 0.000 ~ 0.500 | ≥ 0.300 | `"허용오차 30% 이상은 사실상 정배열 필터 무력화."` | Minervini −2%~−5%; 30% 초과 시 의미 상실 |
| `_TYPE_B_BELOW_MA60_RATIO` | 0.50 ~ 1.00 | ≤ 0.85 or ≥ 1.00 | `"비율 0.85 이하면 거의 모든 종목 통과 (조건 무력화). 1.00 이상은 'rising-from-below' 의미 상실."` | Weinstein rising-from-below |
| `_TYPE_C_CONVERGE_PCT` | 0.000 ~ 0.300 | ≥ 0.100 | `"수렴 폭 10% 초과면 VCP 수렴 개념 아님."` | VCP 3.5%~10% (PRD §5.3) |
| `_TYPE_D_ALIGN_TOL_120` | 0.000 ~ 0.300 | ≥ 0.150 | `"15% 초과면 tangled 정렬 의미 상실."` | tangling 허용 정배열 — Type A보다 빡빡 |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 0.00 ~ 1.00 | ≤ 0.20 or ≥ 0.90 | `"비율 90% 이상이면 거의 모든 종목 탈락. 20% 이하면 사실상 통과."` | 60일선 지지 지속성 (50% canonical) |
| `_TYPE_D_DYNAMIC_WINDOW` | 4 ~ 16 (정수) | ≤ 3 or ≥ 17 | `"16봉 초과는 fixture 한계, 3봉 이하는 표본 부족."` | fixture 상한 16 |
| `_TYPE_E_SPREAD_PCT` | 0.000 ~ 0.300 | ≥ 0.200 | `"확산 폭 20% 초과면 정배열 직전 의미 없음."` | VCP wider variant |
| `_TYPE_E_DYNAMIC_WINDOW` | 4 ~ 16 (정수) | ≤ 3 or ≥ 17 | `"16봉 초과는 fixture 한계, 3봉 이하는 표본 부족."` | 8 canonical |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | 0.00 ~ 1.00 | ≤ 0.30 or ≥ 0.95 | `"95% 이상은 거의 모든 종목 탈락. 30% 이하는 fresh-breakout 의미 상실."` | breakout persistence |
| `_TYPE_E_SHORT_ALIGN_WINDOW` | 1 ~ 8 (정수) | ≥ 8 | `"short-align 윈도우 8 이상이면 'recent' 의미 상실."` | recent V-rebound 구제 |
| `_TYPE_E_SHORT_ALIGN_TOL` | 0.000 ~ 0.200 | ≥ 0.100 | `"10% 초과면 short-alignment 개념 무력."` | 1.6% canonical |
| `_TYPE_E_MA60_OVER_MA306_TOL` | 0.000 ~ 0.300 | ≥ 0.150 | `"Type E 장기추세 허용오차 15% 초과는 'long-trend up' 의미 상실."` | Weinstein long-trend |

### 튜닝 비대상 (11개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — Path) | any change | `"reports 폴더 경로는 구조 상수입니다 — TS-1 변경 불가."` | 구조 식별자 |
| `_CHART60_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 입력 파일명 |
| `_CHART120_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 입력 파일명 |
| `_OUTPUT_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 출력 파일명 |
| `_LABEL_A` | N/A (튜닝 비대상 — 라벨) | any change | `"Type 라벨은 식별 상수 — TS-1 변경 불가."` | 카테고리 라벨 |
| `_LABEL_B` | N/A (튜닝 비대상 — 라벨) | any change | `"Type 라벨은 식별 상수 — TS-1 변경 불가."` | 카테고리 라벨 |
| `_LABEL_C` | N/A (튜닝 비대상 — 라벨) | any change | `"Type 라벨은 식별 상수 — TS-1 변경 불가."` | 카테고리 라벨 |
| `_LABEL_D` | N/A (튜닝 비대상 — 라벨) | any change | `"Type 라벨은 식별 상수 — TS-1 변경 불가."` | 카테고리 라벨 |
| `_LABEL_E` | N/A (튜닝 비대상 — 라벨) | any change | `"Type 라벨은 식별 상수 — TS-1 변경 불가."` | 카테고리 라벨 |
| `_LABEL_EXCLUDED` | N/A (튜닝 비대상 — 라벨) | any change | `"제외 라벨은 식별 상수 — TS-1 변경 불가."` | 카테고리 라벨 |
| `_LABEL_SKIP` | N/A (튜닝 비대상 — 라벨) | any change | `"스킵 라벨은 식별 상수 — TS-1 변경 불가."` | 카테고리 라벨 |
| `_TYPE_CHECKERS` | N/A (튜닝 비대상 — dispatch) | any change | `"Type checker dispatch는 로직 상수 — TS-1 변경 불가."` | A→B→C→D→E priority dispatch |

---

## Stage 1-adjacent — chart60Filter.py (standalone)

### 튜닝 대상 (2개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_MA_ALIGNMENT_TOLERANCE` | 0.000 ~ 0.100 | ≥ 0.050 | `"5% 이상은 strict 4MA 정렬의 의미 무력 — Stage 1 chart60_120과 혼동 주의 (\"60분 정배열 허용오차\")."` | strict alignment — Stage 1 production은 `_ALIGN_TOL_LOOSE` 사용 |
| `_REQUIRED_CONSECUTIVE_BARS` | 1 ~ 16 (정수) | ≤ 1 or ≥ 8 | `"1봉은 단일 노이즈에 과민. 8봉 이상은 stale 데이터에 표본 끌림."` | 3-bar canonical |

### 튜닝 비대상 (5개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — Path) | any change | `"reports 폴더 경로는 구조 상수 — TS-1 변경 불가."` | 구조 식별자 |
| `_CHART60_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 입력 파일명 |
| `_OUTPUT_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 출력 파일명 |
| `_STOCK_DIR_PATTERN` | N/A (튜닝 비대상 — regex) | any change | `"종목 폴더 regex는 구조 상수 — TS-1 변경 불가."` | regex parser |
| `_TABLE_ROW_PATTERN` | N/A (튜닝 비대상 — regex) | any change | `"timeseries table regex는 구조 상수 — TS-1 변경 불가."` | regex parser |

---

## Stage 2 — chart240Filter.py

### 튜닝 대상 (2개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_MA60_MA306_TOLERANCE` | 0.000 ~ 0.200 | ≥ 0.080 | `"8% 이상은 240m 장기추세 'up' 의미 상실 (Weinstein)."` | Weinstein 240m base −2.5% canonical · 현행 0.07 (Phase B 2026-07-05) |
| `_REQUIRED_CONSECUTIVE_BARS` | 1 ~ 8 (정수) | ≤ 1 or ≥ 6 | `"1봉은 단일 240m 노이즈에 과민. 6봉 이상은 ~6일치 trend 시간 지연."` | 3-bar canonical |

### 튜닝 비대상 (3개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — Path) | any change | `"reports 폴더 경로는 구조 상수 — TS-1 변경 불가."` | 구조 식별자 |
| `_CHART240_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 입력 파일명 |
| `_OUTPUT_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 출력 파일명 |

---

## Stage 2-1 — chartDayPreFilter.py

### 튜닝 대상 (1개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DAILY_SURGE_THRESHOLD` | 0.05 ~ 0.30 | ≤ 0.05 or ≥ 0.30 | `"+30% 이상은 상한가 부근 — 의미 없음. 5% 이하는 거의 모든 종목 제외."` | 작전주 경계 +15% canonical |

### 튜닝 비대상 (3개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — Path) | any change | `"reports 폴더 경로는 구조 상수 — TS-1 변경 불가."` | 구조 식별자 |
| `_CHARTDAY_FILENAME` | N/A (튜닝 비대상 — 파일명 / Stage 3 공유 입력) | any change | `"파일명 상수 — TS-1 변경 불가 (Stage 3과 공유 입력)."` | 입력 파일명 |
| `_OUTPUT_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 출력 파일명 |

---

## Stage 3 — chartDayFilter.py

### 튜닝 대상 (7개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_MA10_MA20_MA60_TOLERANCE` | 0.000 ~ 0.200 | ≥ 0.150 | `"15% 초과면 일봉 정렬 의미 상실."` | Minervini daily SEPA −5% canonical |
| `_MA60_MA306_LOWER_TOL` | 0.000 ~ 0.500 | ≥ 0.400 | `"하한 −40% 이하면 깊은 하락 종목도 통과."` | Stage 3 envelope floor |
| `_MA60_MA306_UPPER_TOL` | 0.00 ~ 2.00 | ≤ 0.20 or ≥ 1.50 | `"+150% 이상은 모든 강세 종목 무제한 통과. 20% 이하는 강세 마스터 종목까지 탈락."` | strong uptrend ceiling |
| `_CLOSE_VS_MA612_LOWER` | -0.50 ~ 0.00 | ≤ -0.40 | `"-40% 이하면 장기 base에서 깊이 이탈한 종목도 통과."` | 장기 base 이탈 방지 |
| `_CLOSE_VS_MA612_UPPER` | 0.00 ~ 2.00 | ≤ 0.10 or ≥ 1.50 | `"+150% 이상은 모든 강세 종목 무제한. 10% 이하는 현재 마스터 종목까지 탈락."` | master 위치 허용 ceiling |
| `_REQUIRED_CONSECUTIVE_BARS` | 2 ~ 10 (정수) | ≤ 1 or ≥ 8 | `"1봉은 voting frame 불가. 8봉 이상은 stale."` | 3-bar voting canonical |
| `_REQUIRED_ALIGNED_BARS` | 1 ~ `_REQUIRED_CONSECUTIVE_BARS` (정수) | == `_REQUIRED_CONSECUTIVE_BARS` (strict 'all') | `"voting threshold가 윈도우 크기와 같으면 noise buffer 효과 사라짐 (단일 bar 노이즈 → 탈락)."` | "≥ 2 of 3" buffer rule |

### 튜닝 비대상 (5개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — Path) | any change | `"reports 폴더 경로는 구조 상수 — TS-1 변경 불가."` | 구조 식별자 |
| `_CHARTDAY_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 입력 파일명 |
| `_OUTPUT_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 출력 파일명 |
| `_STOCK_DIR_PATTERN` | N/A (튜닝 비대상 — regex) | any change | `"종목 폴더 regex는 구조 상수 — TS-1 변경 불가."` | regex parser |
| `_TABLE_ROW_PATTERN` | N/A (튜닝 비대상 — regex, 11-group MA612 포함) | any change | `"daily timeseries regex는 구조 상수 — TS-1 변경 불가."` | regex parser |

---

## Stage 4 — investorFilter.py

### 튜닝 대상 (5개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_REQUIRED_BARS` | 8 ~ 16 (정수) | ≤ 7 or ≥ 17 | `"8 미만은 sampling base 부족. 17 이상은 fixture 한계 초과."` | 16-day fixture |
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | 1 ~ 16 (정수) | ≤ 1 or ≥ 12 | `"1일은 통상 매도가 시그널이 아님 — 거의 모든 종목 탈락. 12일 이상은 거의 모든 종목 통과."` | Wyckoff Phase D — 2일 canonical · 현행 5 (Phase B 2026-07-05) |
| `_THRESHOLD_INST_CONSEC_SELL` | 1 ~ 16 (정수) | ≤ 2 or ≥ 14 | `"2일 이하는 모든 종목 탈락. 14일 이상은 8일 분배 검출 의미 상실."` | 기관 unwinding 8일 canonical |
| `_THRESHOLD_INDI_CONSEC_BUY` | 1 ~ 16 (정수) | ≤ 1 or ≥ 12 | `"1일은 통상 매수가 매수 시그널이 아님 — 거의 모든 종목 탈락. 12일 이상은 거의 모든 종목 통과."` | 역발상 시그널 — 3일 canonical |
| `_THRESHOLD_FOREIGN_TOTAL_SELL` | 1 ~ `_REQUIRED_BARS` (정수) | ≤ 8 or ≥ 16 | `"8 이하면 절반 미만 매도도 탈락 = 과도. 16 (전체)는 사실상 통과만 허용 = 조건 무력화."` | long-term distribution 15/16 canonical |

### 튜닝 비대상 (5개)

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — Path) | any change | `"reports 폴더 경로는 구조 상수 — TS-1 변경 불가."` | 구조 식별자 |
| `_INVESTOR_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 입력 파일명 |
| `_OUTPUT_FILENAME` | N/A (튜닝 비대상 — 파일명) | any change | `"파일명 상수 — TS-1 변경 불가."` | 출력 파일명 |
| `_STOCK_DIR_PATTERN` | N/A (튜닝 비대상 — regex) | any change | `"종목 폴더 regex는 구조 상수 — TS-1 변경 불가."` | regex parser |
| `_TABLE_ROW_PATTERN` | N/A (튜닝 비대상 — regex, 부호 보존 4-group) | any change | `"investor timeseries regex는 구조 상수 — TS-1 변경 불가."` | regex parser |

---

## Stage 5 — financeFilter.py (⚠️ Phase 2 hard-block)

> **모든 행이 튜닝 비대상**. PARAM_CHANGE 진입 시 §3 Step 1.0(keyword pre-check) 또는 Step 1.2(catalog)에서 C-4 verbatim 메시지로 REJECT.

| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | N/A (튜닝 비대상 — reports/ 디렉터리 경로 상수) | any change | `"Stage 5 financeFilter는 Phase 2 상수화 대상입니다. _DEFAULT_REPORTS_ROOT는 reports/ 디렉터리 경로(Path)로 사용자 튜닝 대상이 아닙니다. 당기순이익 판정(cup_nga < 0)은 하드코딩 비교문이며 Final 상수가 없으므로 변경 자체가 불가합니다."` | C-4 |
| `_FINANCE_FILENAME` | N/A (튜닝 비대상 — `finance.md` 파일명) | any change | `"Stage 5 financeFilter는 Phase 2 상수화 대상입니다. _FINANCE_FILENAME은 종목별 finance.md 파일명을 가리키는 문자열 상수로 튜닝 대상이 아닙니다. 당기순이익 판정(cup_nga < 0)은 하드코딩 비교문이며 Final 상수가 없으므로 변경 자체가 불가합니다."` | C-4 |
| `_OUTPUT_FILENAME` | N/A (튜닝 비대상 — 출력 파일명 `researchedCompany.md`) | any change | `"Stage 5 financeFilter는 Phase 2 상수화 대상입니다. _OUTPUT_FILENAME은 산출 보고서 파일명(researchedCompany.md)을 가리키는 문자열 상수로 튜닝 대상이 아닙니다. 당기순이익 판정(cup_nga < 0)은 하드코딩 비교문이며 Final 상수가 없으므로 변경 자체가 불가합니다."` | C-4 |
| `_STOCK_DIR_PATTERN` | N/A (튜닝 비대상 — 종목 디렉터리명 regex) | any change | `"Stage 5 financeFilter는 Phase 2 상수화 대상입니다. _STOCK_DIR_PATTERN은 종목 디렉터리명을 매칭하는 정규식 패턴으로 튜닝 대상이 아닙니다. 당기순이익 판정(cup_nga < 0)은 하드코딩 비교문이며 Final 상수가 없으므로 변경 자체가 불가합니다."` | C-4 |
| `_CUP_NGA_ROW_PATTERN` | N/A (튜닝 비대상 — `당기순이익` 행 parser regex) | any change | `"Stage 5 financeFilter는 Phase 2 상수화 대상입니다. _CUP_NGA_ROW_PATTERN은 당기순이익 행을 파싱하는 정규식으로, 임계값이 아닙니다. 임계값 자체(cup_nga < 0)는 하드코딩되어 Final 상수가 없으므로 변경 자체가 불가합니다. Phase 2에서 `_NET_INCOME_MIN_THRESHOLD` 상수화 시 본 행 옆에 임계값 행이 추가될 예정입니다."` | C-4 |
| `_INVALID_MARKER` | N/A (튜닝 비대상 — sentinel `"응답 데이터 없음"`) | any change | `"Stage 5 financeFilter는 Phase 2 상수화 대상입니다. _INVALID_MARKER는 `\"응답 데이터 없음\"` sentinel 문자열로 튜닝 대상이 아닙니다. 당기순이익 판정(cup_nga < 0)은 하드코딩 비교문이며 Final 상수가 없으므로 변경 자체가 불가합니다."` | C-4 |

**Implicit threshold (Final 상수 없음)**: `cup_nga < 0` 비교는 `evaluate_finance` 내 하드코딩 — Final 상수 부재이므로 TS-1 + TS-3 모두 적용 불가. Phase 2 `_NET_INCOME_MIN_THRESHOLD = 0` 신설 시 본 표에 추가 예정.

---

## Coverage Self-Check

| 모듈 | 행 수 | 튜닝 대상 행 | 튜닝 비대상 행 |
|---|---|---|---|
| Filter_condition_update.py | 6 | 0 | 6 |
| chart60_120Filter.py | 27 | 15 | 12 |
| chart60Filter.py | 7 | 2 | 5 |
| chart240Filter.py | 5 | 2 | 3 |
| chartDayPreFilter.py | 4 | 1 | 3 |
| chartDayFilter.py | 12 | 7 | 5 |
| investorFilter.py | 10 | 5 | 5 |
| financeFilter.py | 6 | 0 (Phase 2) | 6 |
| **합계** | **77** | **32** | **45** |

(파일별 `_TABLE_ROW_PATTERN` / `_STOCK_DIR_PATTERN` 모두 별도 행으로 카운트 — Step 1 inventory의 grand total 75 + Stage 5 implicit threshold 0 + chart60_120 `_TYPE_CHECKERS` 1)

**Verification**: 본 파일은 Step 1 param-inventory §Coverage Self-Check의 모든 변수(75)에 대응되는 row를 보유한다. Phase 2 검토 대상(Stage 5 implicit threshold)은 Final 상수 부재로 row 추가 보류.
