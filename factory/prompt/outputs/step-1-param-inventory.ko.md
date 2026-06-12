# Step 1 — 파라미터 전체 인벤토리

> 생성일: 2026-05-29
> 범위: 활성 필터 모듈 7개 + `Filter_condition_update.py` 공유 헬퍼
> 범위 제외: `stageMasterFilter.py` (PRD §12에 따라 Phase 2)
> SOT 루트: `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/`

본 인벤토리는 범위 내 모듈에서 선언된 **모든** `Final[...]` 타입 상수를 빠짐없이 열거한 자료다. 상수는 5단계 스크리닝 파이프라인의 소유권에 따라 분류되어 있다. 파일명 전용 / 출력 경로 전용 상수도 완전성을 위해 보존한다(각 모듈의 공개 표면(public surface)의 일부이며, "X가 어디서 읽혀 어디로 쓰이는가?"라는 튜닝 대화에서 정당하게 등장할 수 있다).

---

## Stage 0 — 공유 / 파이프라인 전역 (`Filter_condition_update.py`)

> `masterReference` 종목을 6개 스테이지 필터 전체에 대해 재평가하고 탈락 사유를 `masterReference.log`에 누적 기록하는 오케스트레이션 헬퍼. 튜닝 가능한 임계값(threshold)은 포함하지 않으며, 구조적·식별용 상수만 보유한다.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 모든 스테이지가 소비하는 일자별 리포트 폴더의 기본 루트 디렉터리. | Filter_condition_update.py:64 |
| `_MASTER_REFERENCE_MD` | `Final[str]` | `"masterReference.md"` | 마스터 레퍼런스 목록(탈락 사유 분석 대상 종목) 파일명. | Filter_condition_update.py:65 |
| `_MASTER_REFERENCE_LOG` | `Final[str]` | `"masterReference.log"` | 종목별·스테이지별 탈락 사유가 누적 기록되는 append-only 로그 파일. | Filter_condition_update.py:66 |
| `_RESEARCHED_MD` | `Final[str]` | `"researchedCompany.md"` | 최종 리서치 종목 리포트 파일명. 이 파일의 존재가 분석 자격 트리거로 사용된다. | Filter_condition_update.py:67 |
| `_STAGES` | `Final[list[tuple[str, str, str, _StageFilter]]]` | 6-튜플 리스트: `("Stage 1","chart60_120","stage1_chart60_120_passed.md", chart60_120_filter_stock)`, `("Stage 2","chart240","stage2_chart240_passed.md", chart240_filter_stock)`, `("Stage 2-1","chartDayPre","stage2_1_chartDayPre_passed.md", chartday_pre_filter_stock)`, `("Stage 3","chartDay","stage3_chartDay_passed.md", chartday_filter_stock)`, `("Stage 4","investor","stage4_investor_passed.md", investor_filter_stock)`, `("Stage 5","finance","stage5_finance_passed.md", finance_filter_stock)` | 각 스테이지별 (표시 라벨, 스테이지명, 통과 결과 파일명, 단일 종목 필터 호출 가능 객체)로 구성된 표준 스테이지 순서. 순서는 `researchFlow.saveReport._STAGE_FILENAMES`와 1:1로 일치해야 한다. | Filter_condition_update.py:72-85 |
| `_NAME_CODE_RE` | `Final[re.Pattern[str]]` | `re.compile(r"^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$")` | `"종목명(123456)"` 형태의 라인을 명명 그룹 `nm`(이름)과 `cd`(4–6자리 종목 코드)로 분리하는 정규식. | Filter_condition_update.py:88 |

---

## Stage 1 — `chart60_120Filter.py` (Type A/B/C/D/E 패턴 감지 — 60분 + 120분 MA 정렬)

> 5가지 패턴 감지기. 첫 매칭(우선순위 A→B→C→D→E)이 종목을 분류한다. 정적 구조 검사는 `bars[-8:]`에서 평가하고, 동적 이벤트 검사는 Type에 따라 최근 1–16개 봉에서 평가한다.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 일자별 파티션 리포트의 기본 루트 디렉터리. | chart60_120Filter.py:110 |
| `_CHART60_FILENAME` | `Final[str]` | `"chart60.md"` | 종목 폴더별 입력 60분봉 리포트 파일명. | chart60_120Filter.py:111 |
| `_CHART120_FILENAME` | `Final[str]` | `"chart120.md"` | 종목 폴더별 입력 120분봉 리포트 파일명. | chart60_120Filter.py:112 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart60_120Filter.md"` | 일자 폴더별로 기록되는 출력 필터 결과 리포트 파일명. | chart60_120Filter.py:113 |
| `_REQUIRED_STATIC_BARS` | `Final[int]` | `8` | 정적 구조 조건(정렬 / 발산 / 수렴)의 윈도우 크기: `bars[-8:]`의 **전부**가 조건을 충족해야 한다. Type A/B/C/D에 적용된다. | chart60_120Filter.py:116 |
| `_ALIGN_TOL_LOOSE` | `Final[float]` | `0.015` (즉, ×0.985) | 본 모듈 내 Type B/C/D가 **공유**하는 느슨한(loose) 정렬 허용 오차. 공식: `upper_MA >= lower_MA * (1 − _ALIGN_TOL_LOOSE)`. 비대칭 −1.5% 여유. **중요: 이는 다수의 Type이 공유하는 상수이므로 변경 시 영향이 전파된다.** | chart60_120Filter.py:120 |
| `_TYPE_A_ALIGN_TOL` | `Final[float]` | `0.035` (즉, ×0.965) | Type A 전용 4-MA 완전 정렬 허용 오차(-3.5%). 노이즈로 인해 엄격한 4선 정렬이 깨진 주도주를 복구하기 위해 `_ALIGN_TOL_LOOSE`보다 느슨하게 설정. 60분·120분 두 시간프레임 모두에 적용된다. | chart60_120Filter.py:125 |
| `_TYPE_B_BELOW_MA60_RATIO` | `Final[float]` | `0.97` | Type B 전용: 120분 `MA10`과 `MA20`이 각각 `MA60 × 0.97` 이하여야 한다(즉, MA60보다 최소 3% 아래). "아래로부터 상승" 진입 조건을 표현한다. | chart60_120Filter.py:128 |
| `_TYPE_C_CONVERGE_PCT` | `Final[float]` | `0.035` | Type C 전용 수렴 임계값: `bars[-8:]`의 모든 120분봉에서 `(max(MA10,MA20,MA60) − min)/min ≤ 3.5%`. VCP 스타일의 타이트한 통합 구간을 포착한다. | chart60_120Filter.py:131 |
| `_TYPE_D_ALIGN_TOL_120` | `Final[float]` | `0.020` (즉, ×0.98) | Type D 전용 120분 "엉킴(tangled)" 허용 오차: `MA10 ≥ MA60×0.98` AND `MA20 ≥ MA60×0.98` (MA10과 MA20 사이의 순서는 자유 — 엉킴 허용). | chart60_120Filter.py:134 |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | `Final[float]` | `0.50` | Type D 60분 보조 임계값: 엄격한 4선 60분 정렬 폴백이 실패한 경우, `bars60[-16:]` 중 `close > MA60`인 비율이 50% 이상이어야 한다. | chart60_120Filter.py:137 |
| `_TYPE_D_DYNAMIC_WINDOW` | `Final[int]` | `16` | Type D의 `close > MA60` 비율 폴백을 위한 윈도우 크기(60분봉 단위). | chart60_120Filter.py:138 |
| `_TYPE_E_SPREAD_PCT` | `Final[float]` | `0.10` | 가장 최근 120분봉에 대한 Type E 수렴 상한: `(max(MA10,MA20,MA60) − min)/min ≤ 10%`. Type C보다 넓게 설정 — "곧 정렬될" V자 반등을 포착하도록 설계됨. | chart60_120Filter.py:143 |
| `_TYPE_E_DYNAMIC_WINDOW` | `Final[int]` | `8` | Type E의 `close > MA60` 지지 비율 평가를 위한 윈도우 크기(60분봉 단위). | chart60_120Filter.py:145 |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | `Final[float]` | `0.75` | Type E 60분 지지 임계값: `bars60[-8:]` 중 `close > MA60`인 비율이 75% 이상이어야 한다(신선한 돌파의 지속성). | chart60_120Filter.py:146 |
| `_TYPE_E_SHORT_ALIGN_WINDOW` | `Final[int]` | `2` | Type E 단기 정렬 윈도우 — 최근 2개 120분봉 중 최소 1개가 단기 정렬 조건을 충족해야 한다. 마지막 봉에 장중 노이즈가 있는 V자 반등을 구제한다. | chart60_120Filter.py:149 |
| `_TYPE_E_SHORT_ALIGN_TOL` | `Final[float]` | `0.016` (즉, ×0.984) | 120분 최근 윈도우에서 `MA10 ≥ MA20×(1−tol)`에 대한 Type E 단기 정렬 허용 오차(1.6%). | chart60_120Filter.py:152 |
| `_TYPE_E_MA60_OVER_MA306_TOL` | `Final[float]` | `0.035` (즉, ×0.965) | Type E **전용** 장기 추세 허용 오차: 마지막 120분봉에서 `MA60 ≥ MA306×(1−0.035)`. 공유 `_ALIGN_TOL_LOOSE`(1.5%)를 사용하면 Type E V자 반등 복구를 과도하게 제한하면서 Type B/C/D에 영향을 주었기 때문에 분리되었다. | chart60_120Filter.py:156 |
| `_LABEL_A` | `Final[str]` | `"A"` | Type A 매칭의 표시/카테고리 라벨. | chart60_120Filter.py:159 |
| `_LABEL_B` | `Final[str]` | `"B"` | Type B 매칭의 표시/카테고리 라벨. | chart60_120Filter.py:160 |
| `_LABEL_C` | `Final[str]` | `"C"` | Type C 매칭의 표시/카테고리 라벨. | chart60_120Filter.py:161 |
| `_LABEL_D` | `Final[str]` | `"D"` | Type D 매칭의 표시/카테고리 라벨. | chart60_120Filter.py:162 |
| `_LABEL_E` | `Final[str]` | `"E"` | Type E 매칭의 표시/카테고리 라벨. | chart60_120Filter.py:163 |
| `_LABEL_EXCLUDED` | `Final[str]` | `"제외"` | 5개 Type 검사 전부에 실패한 종목의 카테고리 라벨. | chart60_120Filter.py:164 |
| `_LABEL_SKIP` | `Final[str]` | `"스킵"` | 입력 파일(chart60.md 또는 chart120.md)이 누락된 종목의 카테고리 라벨. | chart60_120Filter.py:165 |
| `_TYPE_CHECKERS` | `Final[tuple[tuple[str, object], ...]]` | `((_LABEL_A,_check_type_a),(_LABEL_B,_check_type_b),(_LABEL_C,_check_type_c),(_LABEL_D,_check_type_d),(_LABEL_E,_check_type_e))` | 순서가 부여된 Type 검사기 디스패치 테이블 — `evaluate_chart60_120`에서 A→B→C→D→E 우선순위 평가 순서를 정의한다. | chart60_120Filter.py:572 |

---

## Stage 1 인접 — `chart60Filter.py` (60분 4MA 정렬, 독립형)

> 독립형 60분 MA 정렬 필터(chart60_120Filter가 파싱 헬퍼와 정규식을 import하여 사용). 자체적으로 독립된 정렬 허용 오차를 가짐 — **`_ALIGN_TOL_LOOSE`와 혼동하지 말 것**.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 일자별 파티션 리포트의 기본 루트 디렉터리. | chart60Filter.py:68 |
| `_CHART60_FILENAME` | `Final[str]` | `"chart60.md"` | 입력 60분봉 리포트 파일명. | chart60Filter.py:69 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart60Filter.md"` | 출력 필터 결과 리포트 파일명. | chart60Filter.py:70 |
| `_MA_ALIGNMENT_TOLERANCE` | `Final[float]` | `0.005` (즉, ×0.995) | chart60Filter.py **전용**의 **독립된** 4MA 정렬 허용 오차: 비대칭 −0.5% 여유. 공식: `upper_MA >= lower_MA × (1 − _MA_ALIGNMENT_TOLERANCE)`. 엄격한 정렬 요건. **chart60_120Filter.py의 `_ALIGN_TOL_LOOSE`와는 동일한 상수가 아니다.** | chart60Filter.py:75 |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | 윈도우 크기: `bars[-3:]`(최근 3개 봉)의 **전부**가 4MA 정렬을 충족해야 한다. | chart60Filter.py:78 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | 종목별 디렉터리 이름 형식 `"종목명(123456)"`에 일치하는 정규식. 이름과 코드를 캡처한다. chart60_120Filter / chart240Filter / financeFilter / investorFilter도 `_STOCK_DIR_PATTERN`를 통해 재-import하여 재사용한다. | chart60Filter.py:81 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*$")` | chart60.md 마크다운 시계열 테이블의 한 행을 파싱한다: 10개 캡처 그룹 = (타임스탬프 `YYYY-MM-DD HH:MM`, O, H, L, C, V, MA10, MA20, MA60, MA306). MA 컬럼은 `—`/`-`/공백을 누락값으로 허용한다. chart60_120Filter와 chart240Filter도 재-import를 통해 재사용한다. | chart60Filter.py:86-92 |

---

## Stage 2 — `chart240Filter.py` (240분 장기 추세 게이트)

> 최근 N개 240분봉 전부에 대해 `MA60 ≥ MA306×(1 − tol)`이 성립하는지 검증. `Chart60Bar`와 chart60 테이블 정규식을 재-import하여 재사용한다.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 일자별 파티션 리포트의 기본 루트 디렉터리. | chart240Filter.py:72 |
| `_CHART240_FILENAME` | `Final[str]` | `"chart240.md"` | 입력 240분봉 리포트 파일명. | chart240Filter.py:73 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart240Filter.md"` | 출력 필터 결과 리포트 파일명. | chart240Filter.py:74 |
| `_MA60_MA306_TOLERANCE` | `Final[float]` | `0.025` (즉, ×0.975) | 240분 장기 추세 허용 오차: `MA60 ≥ MA306 × (1 − 0.025)` — 비대칭 −2.5% 여유. 평가 윈도우의 모든 봉에서 요구된다. | chart240Filter.py:78 |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | 윈도우 크기: 최근 240분봉 3개 **전부**가 MA60-vs-MA306 추세 조건을 충족해야 한다. | chart240Filter.py:81 |

---

## Stage 2-1 — `chartDayPreFilter.py` (당일 급등 사전 제외 게이트)

> 직전 종가 대비 최신 일봉이 15% 이상 상승한 종목을 제외 — 과열된 / 추격 매수성 후보가 Stage 3에 진입하는 것을 방지한다.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 일자별 파티션 리포트의 기본 루트 디렉터리. | chartDayPreFilter.py:46 |
| `_CHARTDAY_FILENAME` | `Final[str]` | `"chartDay.md"` | 입력 일봉 리포트 파일명(Stage 3과 입력을 공유). | chartDayPreFilter.py:47 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chartDayPreFilter.md"` | 출력 필터 결과 리포트 파일명. | chartDayPreFilter.py:48 |
| `_DAILY_SURGE_THRESHOLD` | `Final[float]` | `0.15` | 일간 변동률 상한: `(close − prev_close) / prev_close ≥ 0.15`(≥ +15%) → 제외. PASS는 엄격히 미만(less-than) 의미론을 따른다. | chartDayPreFilter.py:51 |

---

## Stage 3 — `chartDayFilter.py` (일봉 MA 정렬 + MA612 밴드)

> 두 부분 검사: (a) 최근 3개 일봉 중 ≥ 2개에서 4MA 정렬(단일 봉 노이즈 버퍼); (b) 최신 봉의 종가가 비대칭 MA612 밴드 내에 있으며 AND 금일 종가 > 전일 종가.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 일자별 파티션 리포트의 기본 루트 디렉터리. | chartDayFilter.py:55 |
| `_CHARTDAY_FILENAME` | `Final[str]` | `"chartDay.md"` | 입력 일봉 리포트 파일명. | chartDayFilter.py:56 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chartDayFilter.md"` | 출력 필터 결과 리포트 파일명. | chartDayFilter.py:57 |
| `_MA10_MA20_MA60_TOLERANCE` | `Final[float]` | `0.05` (즉, ×0.95) | 일봉에서 `MA10 ≥ MA20×0.95`와 `MA20 ≥ MA60×0.95`에 대한 정렬 허용 오차(비대칭 -5.0%). 일간 변동성이 더 크기 때문에 장중보다 넓다. | chartDayFilter.py:61 |
| `_MA60_MA306_LOWER_TOL` | `Final[float]` | `0.15` (하한 밴드 ×0.85) | 비대칭 MA60-vs-MA306 엔벨로프의 하한 밴드: `MA60 ≥ MA306 × (1 − 0.15)`(즉, ≥ ×0.85). 엄격한 하한 — 깊은 하락 추세가 통과하는 것을 막는다. | chartDayFilter.py:63 |
| `_MA60_MA306_UPPER_TOL` | `Final[float]` | `0.45` (상한 밴드 ×1.45) | 비대칭 MA60-vs-MA306 엔벨로프의 상한 밴드: `MA60 ≤ MA306 × (1 + 0.45)`(즉, ≤ ×1.45). 관대한 상한 — 강한 상승 추세를 허용한다. | chartDayFilter.py:64 |
| `_CLOSE_VS_MA612_LOWER` | `Final[float]` | `-0.15` (밴드 ×0.85) | 종가-vs-MA612 엔벨로프의 하단 경계: `(close − MA612)/MA612 ≥ −0.15`. 장기 베이스로부터 너무 멀리 하락한 종목을 제외한다. | chartDayFilter.py:68 |
| `_CLOSE_VS_MA612_UPPER` | `Final[float]` | `0.50` (밴드 ×1.50) | 종가-vs-MA612 엔벨로프의 상단 경계: `(close − MA612)/MA612 ≤ 0.50`. 현재 주도주가 MA612보다 충분히 위에 위치하는 것을 허용하는 관대한 설정. | chartDayFilter.py:69 |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | 샘플 윈도우: 정렬 투표를 위해 최근 3개 일봉을 검사. | chartDayFilter.py:72 |
| `_REQUIRED_ALIGNED_BARS` | `Final[int]` | `2` | 투표 임계값: 검사된 3개 봉 중 최소 2개가 정렬 상태여야 함(노이즈 버퍼 규칙). | chartDayFilter.py:73 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | 종목별 디렉터리 `"종목명(123456)"`에 일치하는 정규식. 이름과 코드를 캡처. chart60Filter의 것과 논리적으로 동일하나 여기서는 독립적으로 선언되어 있다. | chartDayFilter.py:75 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*$")` | chartDay.md 마크다운 시계열 행을 파싱한다: 11개 캡처 그룹 = (날짜 `YYYY-MM-DD`, O, H, L, C, V, MA10, MA20, MA60, MA306, MA612). 장중 패턴에 비해 다섯 번째 MA 컬럼(MA612)이 추가되어 있다. | chartDayFilter.py:78-85 |

---

## Stage 4 — `investorFilter.py` (수급: 외국인 / 기관 / 개인)

> 최근 16거래일에 걸쳐 4가지 수급 제외 규칙 중 하나라도 해당하는 종목을 탈락시킨다.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 일자별 파티션 리포트의 기본 루트 디렉터리. | investorFilter.py:39 |
| `_INVESTOR_FILENAME` | `Final[str]` | `"investor.md"` | 입력 수급 리포트 파일명(종목별). | investorFilter.py:40 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"investorFilter.md"` | 출력 필터 결과 리포트 파일명. | investorFilter.py:41 |
| `_REQUIRED_BARS` | `Final[int]` | `16` | 요구되는 최소 거래일 행 수. 미만 시 → 제외("데이터 부족"). | investorFilter.py:43 |
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | `Final[int]` | `2` | 외국인 투자자가 최근 연속 ≥ 2일 순매도한 경우 제외(스마트 머니 분산 매도 신호). | investorFilter.py:46 |
| `_THRESHOLD_INST_CONSEC_SELL` | `Final[int]` | `8` | 국내 기관이 최근 연속 ≥ 8일 순매도한 경우 제외(지속적 기관 분산 매도). | investorFilter.py:47 |
| `_THRESHOLD_INDI_CONSEC_BUY` | `Final[int]` | `3` | 개인 투자자가 최근 연속 ≥ 3일 순매수한 경우 제외(역지표: 강한 개인 매수는 스마트 머니의 이탈을 시사). | investorFilter.py:48 |
| `_THRESHOLD_FOREIGN_TOTAL_SELL` | `Final[int]` | `15` | 외국인 투자자가 16개 샘플 거래일 중 ≥ 15일 순매도한 경우 제외(장기 분산 매도 패턴). | investorFilter.py:49 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | 종목별 디렉터리 `"종목명(123456)"`에 일치하는 정규식. 이름과 코드를 캡처한다. | investorFilter.py:51 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([+-]?[\d,]+)\s*\|\s*([+-]?[\d,]+)\s*\|\s*([+-]?[\d,]+)\s*\|\s*$")` | investor.md 마크다운 시계열 행을 파싱한다: 4개 캡처 그룹 = (날짜 `YYYY-MM-DD`, 개인, 외국인, 기관). 부호 있는 정수(₩백만, 부호 보존). | investorFilter.py:54-59 |

---

## Stage 5 — `financeFilter.py` (재무: 당기순이익 음수 제외)

> 당기순이익(₩억원)이 실수로 파싱되어 `< 0`인 경우에만 제외한다. 누락 / 무효 마커는 PASS(관대). **튜닝 가능한 임계값 상수는 존재하지 않는다** — `< 0` 비교는 `evaluate_finance` 내부에 하드코딩되어 있다. 이것이 Phase-1의 문서화된 튜닝 한계이다.

| 변수 | 타입 | 현재 값 | 의미 | 파일:행 |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | 일자별 파티션 리포트의 기본 루트 디렉터리. | financeFilter.py:34 |
| `_FINANCE_FILENAME` | `Final[str]` | `"finance.md"` | 입력 재무 스냅샷 리포트 파일명(종목별). | financeFilter.py:35 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"financeFilter.md"` | 출력 필터 결과 리포트 파일명. | financeFilter.py:36 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | 종목별 디렉터리 `"종목명(123456)"`에 일치하는 정규식. 이름과 코드를 캡처한다. | financeFilter.py:38 |
| `_CUP_NGA_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*당기순이익 \(억원\)\s*\|\s*(.+?)\s*\|\s*$")` | 당기순이익을 보고하는 단일 행을 파싱한다. 캡처 그룹 1 = 원본 값 셀(숫자, `—`, 또는 마커 문자열). | financeFilter.py:41-43 |
| `_INVALID_MARKER` | `Final[str]` | `"응답 데이터 없음"` | API가 비어 있는 페이로드를 반환했을 때 `finance.render_markdown`이 기록하는 센티넬 문자열. 데이터 누락으로 취급 → PASS(관대). | financeFilter.py:46 |

---

## 결정적 구분 (혼동 방지)

### `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` — 별개의 상수이며 이름만 유사함

이 둘은 **서로 다른 두 파일에 정의된 독립적인 모듈 레벨 상수**이며, 니모닉(mnemonic) 의도는 유사하지만 값·범위·소비자가 다르다. 튜닝 중 둘을 혼동하면 한 스테이지 전체가 조용히 잘못 튜닝된다. 비교표:

| 속성 | `_ALIGN_TOL_LOOSE` | `_MA_ALIGNMENT_TOLERANCE` |
|---|---|---|
| 소속 모듈 | `chart60_120Filter.py` | `chart60Filter.py` |
| 행 번호 | 120 | 75 |
| 값 | `0.015` (×0.985, −1.5% 여유) | `0.005` (×0.995, −0.5% 여유) |
| 여유 | 느슨함 (3배 더 넓음) | 엄격함 |
| 범위 | chart60_120Filter 내에서 Type B(60분 및 120분), Type C(MA60-MA306 장기 추세 분기), Type D(60분 폴백 4선 정렬) 전반에 걸쳐 **공유됨** | 독립형 chart60Filter의 4MA 정렬 검사에만 적용되는 단독 정렬 허용 오차 |
| 변경 영향 | Type B/C/D를 횡단함 → Stage 1의 복수 패턴 감지기에 걸쳐 광범위한 재현율/정밀도 변화 발생 | chart60Filter에 국한 — 스테이지 간 전파 없음 |
| 튜닝 시점 | 완화 시 Stage-1 패턴 로직 하에서 더 많은 "불완전한" 장중 정렬이 수용된다. Stage-1이 과도하게 재현될 때 엄격화한다. | 완화 시 엄격한 4선 검사 하에서 경계선상의 60분 정렬 후보가 더 많이 수용된다. 독립형 chart60이 과도하게 재현될 때 엄격화한다. |

**튜닝 대화에서의 판별 규칙**: 사용자가 "60분 정렬 허용 오차를 완화하라"고 요청할 때마다, 그 의미가 Stage-1 패턴 감지기(`chart60_120Filter`)인지 독립형 엄격 정렬 검사(`chart60Filter`)인지를 **반드시** 먼저 판별해야 한다. 프로덕션의 기본값은 Stage-1이며, Edit 이전에 명시적으로 모호성을 해소하라.

### 발견된 기타 유사 외형 상수

- `_REQUIRED_CONSECUTIVE_BARS`: **세 개** 모듈에서 독립적으로 선언됨 — `chart60Filter.py:78`(값 `3`), `chart240Filter.py:81`(값 `3`), `chartDayFilter.py:72`(값 `3`). 이름과 현재 값은 동일하지만, 각각은 자기 모듈에 한정된 **별개의** 상수이다. 하나를 튜닝해도 다른 것에 영향을 주지 않는다. Stage 3에서 특히 미묘한 이유는 chartDay에 `_REQUIRED_ALIGNED_BARS=2`가 함께 있어 규칙이 "3 중 ≥ 2"이지 "3 전부"가 아니기 때문이다.
- `_REQUIRED_STATIC_BARS`(chart60_120Filter.py:116, 값 `8`) vs `_REQUIRED_CONSECUTIVE_BARS`(Stage-2 및 Stage-3, 값 `3`) 및 `_REQUIRED_BARS`(investorFilter.py:43, 값 `16`): 세 가지 의미가 서로 다른 세 개의 "윈도우 크기" 상수 — 대화에서 정확하게 표현해야 한다.
- `_TYPE_D_DYNAMIC_WINDOW`(16) vs `_TYPE_E_DYNAMIC_WINDOW`(8): 둘 다 60분 `close > MA60` 비율 윈도우이지만, 서로 다른 Type과 서로 다른 비율(50% vs 75%)에 해당한다. PRD §5.1 각주가 정확히 지적하듯, 이들은 16-bar 입력 픽스처에 의해 경계가 정해지므로 거의 튜닝되지 않는다.
- `_STOCK_DIR_PATTERN`과 `_TABLE_ROW_PATTERN`: **여러** 모듈(chart60, chartDay, investor, finance에서 직접 선언되고 chart60_120 / chart240에서 재-import됨)에서 같은 이름으로 선언된다. `_STOCK_DIR_PATTERN`은 논리적으로 동일하지만, `_TABLE_ROW_PATTERN`은 각 시계열 테이블의 컬럼 수가 다르기 때문에 구조적으로 다르다(60분: HH:MM 포함 10개 그룹; 일봉: MA612 포함 11개 그룹; 수급: 4개 그룹, 부호 있는 정수; 재무: 테이블이 아닌 단일 행 패턴).
- `_MA60_MA306_TOLERANCE`(chart240Filter.py:78, 값 `0.025` / −2.5%) vs `_MA60_MA306_LOWER_TOL`(chartDayFilter.py:63, 값 `0.15` / −15%) vs `_TYPE_E_MA60_OVER_MA306_TOL`(chart60_120Filter.py:156, 값 `0.035` / −3.5%): 세 가지 서로 다른 시간프레임에 대한 세 가지 MA60-vs-MA306 장기 추세 허용 오차 — 일봉에서 훨씬 느슨한 이유는 장기 베이스로부터의 발산이 일봉 시간프레임에서만 의미가 있기 때문이다.

---

## PRD §5.1 상호 참조

| PRD ID | PRD 변수 | PRD 값 | 코드 값 | 상태 | 비고 |
|---|---|---|---|---|---|
| S1-1 | `_TYPE_A_ALIGN_TOL` | -3.5% (×0.965) | `0.035` | ✅ 일치 | chart60_120Filter.py:125 |
| S1-2 | `_ALIGN_TOL_LOOSE` (공유) | -1.5% (×0.985) | `0.015` | ✅ 일치 | chart60_120Filter.py:120 |
| S1-3 | `_TYPE_B_BELOW_MA60_RATIO` | -3.0% (×0.97) | `0.97` | ✅ 일치 | chart60_120Filter.py:128 |
| S1-4 | `_ALIGN_TOL_LOOSE` (공유) | -1.5% (×0.985) | `0.015` | ✅ 일치 (S1-2와 동일 상수) | chart60_120Filter.py:120 |
| S1-5 | `_TYPE_C_CONVERGE_PCT` | 3.5% (0.035) | `0.035` | ✅ 일치 | chart60_120Filter.py:131. **주의**: PRD §5.4 본문과 chart60_120Filter.py:866의 `render_markdown` "판정 조건" 문자열은 "2.0%"라고 기재 — 이는 **오래된 문서**이며 실제 상수는 3.5%. §5.4 문서 수정 대상으로 표기. |
| S1-6 | `_TYPE_D_ALIGN_TOL_120` | -2.0% (×0.98) | `0.020` | ✅ 일치 | chart60_120Filter.py:134 |
| S1-7 | `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 50% (0.50) | `0.50` | ✅ 일치 | chart60_120Filter.py:137. PRD §5.3의 "60% 이상" 서술은 오래된 내용이며, 실제 상수는 50%. |
| S1-8 | `_TYPE_E_SPREAD_PCT` | 10.0% (0.10) | `0.10` | ✅ 일치 | chart60_120Filter.py:143 |
| S1-9 | `_TYPE_E_SHORT_ALIGN_TOL` | -1.6% (×0.984) | `0.016` | ✅ 일치 | chart60_120Filter.py:152 |
| S1-10 | `_TYPE_E_CLOSE_OVER_MA60_RATIO` | 75% (0.75) | `0.75` | ✅ 일치 | chart60_120Filter.py:146 |
| S1-10a | `_TYPE_E_MA60_OVER_MA306_TOL` | -3.5% (×0.965) | `0.035` | ✅ 일치 | chart60_120Filter.py:156 |
| S1-11 | `_REQUIRED_STATIC_BARS` | 8 봉 | `8` | ✅ 일치 | chart60_120Filter.py:116 |
| S1-12 | (하드코딩, `Final` 상수 없음) | 최근 1 봉 | 해당 없음 | ✅ 설계상 일치 | PRD는 이것이 `Final` 상수가 아님을 정확히 명시. |
| S2-1 | `_MA60_MA306_TOLERANCE` | -2.5% (×0.975) | `0.025` | ✅ 일치 | chart240Filter.py:78 |
| S2-2 | `_REQUIRED_CONSECUTIVE_BARS` | 3 봉 (전부) | `3` | ✅ 일치 | chart240Filter.py:81 |
| S21-1 | `_DAILY_SURGE_THRESHOLD` | +15% (0.15) | `0.15` | ✅ 일치 | chartDayPreFilter.py:51 |
| S3-1 | `_MA10_MA20_MA60_TOLERANCE` | -5.0% (×0.95) | `0.05` | ✅ 일치 | chartDayFilter.py:61 |
| S3-2 | `_MA60_MA306_LOWER_TOL` | -15% (×0.85) | `0.15` | ✅ 일치 | chartDayFilter.py:63 |
| S3-3 | `_MA60_MA306_UPPER_TOL` | +45% (×1.45) | `0.45` | ✅ 일치 | chartDayFilter.py:64 |
| S3-4 | `_CLOSE_VS_MA612_LOWER` | -15% (×0.85) | `-0.15` | ✅ 일치 | chartDayFilter.py:68 |
| S3-5 | `_CLOSE_VS_MA612_UPPER` | +50% (×1.50) | `0.50` | ✅ 일치 | chartDayFilter.py:69 |
| S3-6 | `_REQUIRED_ALIGNED_BARS` / `_REQUIRED_CONSECUTIVE_BARS` | 3 중 2 | `2` / `3` | ✅ 일치 | chartDayFilter.py:72-73 |
| S3-7 | (하드코딩 비교) | close > prev close | 해당 없음 | ✅ 설계상 일치 | PRD는 이것이 하드코딩되어 있음을 정확히 명시. |
| S4-1 | `_THRESHOLD_FOREIGN_CONSEC_SELL` | ≥ 2일 | `2` | ✅ 일치 | investorFilter.py:46 |
| S4-2 | `_THRESHOLD_INST_CONSEC_SELL` | ≥ 8일 | `8` | ✅ 일치 | investorFilter.py:47 |
| S4-3 | `_THRESHOLD_INDI_CONSEC_BUY` | ≥ 3일 | `3` | ✅ 일치 | investorFilter.py:48 |
| S4-4 | `_THRESHOLD_FOREIGN_TOTAL_SELL` | 16 중 ≥15 | `15` | ✅ 일치 | investorFilter.py:49 |
| Stage 5 (ID 없음) | 하드코딩 `cup_nga < 0` | 하드코딩 | 하드코딩 | ✅ 설계상 일치 | PRD는 Phase-1 튜닝 불가를 정확히 명시. 임계값에 대한 `Final` 상수 없음. |

**코드에는 존재하나 PRD §5.1 카탈로그에는 없는 상수(❓)**: 7개 모듈 전반의 모든 파일명/경로 상수(`_DEFAULT_REPORTS_ROOT`, `_*_FILENAME`, `_OUTPUT_FILENAME`), 모든 정규식 상수(`_STOCK_DIR_PATTERN`, `_TABLE_ROW_PATTERN`, `_NAME_CODE_RE`, `_CUP_NGA_ROW_PATTERN`), 모든 라벨 상수(`_LABEL_A..E`, `_LABEL_EXCLUDED`, `_LABEL_SKIP`), `_INVALID_MARKER`, `_STAGES`, `_TYPE_CHECKERS`, 독립형 chart60 상수(`_MA_ALIGNMENT_TOLERANCE`, `_REQUIRED_CONSECUTIVE_BARS`, `_REQUIRED_STATIC_BARS` 관련 윈도우 헬퍼 `_TYPE_D_DYNAMIC_WINDOW`/`_TYPE_E_DYNAMIC_WINDOW`/`_TYPE_E_SHORT_ALIGN_WINDOW`), `_REQUIRED_BARS`(investor). 이들은 사용자 대상 튜닝 타깃이 아니라 구조 / 파싱 / 스캐폴딩이기 때문에 PRD §5.1에서 의도적으로 누락되었다. 그러나 이들도 SOT의 일부이므로 완전성을 위해 열거되어야 한다.

**PRD §5.1에 존재하나 코드에 부재한 상수(❗)**: **검출되지 않음.** 모든 PRD 카탈로그 행이 실제 코드 상수에 매핑되거나 명시적으로 하드코딩으로 주석되어 있다.

**Orchestrator에 보고할 불일치(⚠️)**:
1. `_ALIGN_TOL_LOOSE`의 영향 목록에 대한 PRD §5.4 본문 라인은 "Type B 60분 정배열, Type B MA60-MA306, Type C MA60-MA306, Type D 60분 정배열"이라 명시 — 코드상으로 `_check_type_b`, `_check_type_c`(MA60-MA306 분기가 `_ALIGN_TOL_LOOSE`를 사용), `_check_type_d`(60분 폴백 `_is_4ma_aligned(b, _ALIGN_TOL_LOOSE)`)에서 옳음이 확인됨. 불일치 없음. 다만 `_c120` 내부의 Type C 수렴 임계값은 `_TYPE_C_CONVERGE_PCT`를 사용하며 PRD §5.1 행 S1-5는 3.5%를 주장하는데, **렌더링된 리포트 헤더**가 chart60_120Filter.py:866의 `render_markdown` 안에서 여전히 `"2.0%"` 문자열을 하드코딩 — 상수 불일치가 아니라 **소스 파일 내부의 문서 드리프트**이다.
2. 동일한 종류의 드리프트: chart60_120Filter.py:870 `render_markdown`은 Type D close>MA60 비율에 대해 "비율 ≥ 60%"라고 기재하지만, 실제 상수 `_TYPE_D_CLOSE_OVER_MA60_RATIO = 0.50`은 50%로 평가된다. 튜닝 시점 리스크: 렌더링된 마크다운을 검토하는 사용자는 "60%"를 보지만 코드는 50%를 사용한다.

이 두 가지는 상수 값 버그가 **아니다** — 수학 연산은 `Final` 상수를 기준으로 실행된다 — 그러나 리포트 렌더러의 문자열 리터럴 내부에 존재하는 사용자 가시(user-visible) 문서 드리프트이다. Stage-1 정리 패스 대상으로 표기.

---

## 커버리지 자체 검증

- [x] `Filter_condition_update.py` — **6개** 상수 추출(`_DEFAULT_REPORTS_ROOT`, `_MASTER_REFERENCE_MD`, `_MASTER_REFERENCE_LOG`, `_RESEARCHED_MD`, `_STAGES`, `_NAME_CODE_RE`).
- [x] `chart60Filter.py` — **7개** 상수 추출(`_DEFAULT_REPORTS_ROOT`, `_CHART60_FILENAME`, `_OUTPUT_FILENAME`, `_MA_ALIGNMENT_TOLERANCE`, `_REQUIRED_CONSECUTIVE_BARS`, `_STOCK_DIR_PATTERN`, `_TABLE_ROW_PATTERN`).
- [x] `chart60_120Filter.py` — **26개** 상수 추출(경로/파일 4개 + `_REQUIRED_STATIC_BARS` + `_ALIGN_TOL_LOOSE` + `_TYPE_A_ALIGN_TOL` + `_TYPE_B_BELOW_MA60_RATIO` + `_TYPE_C_CONVERGE_PCT` + `_TYPE_D_ALIGN_TOL_120` + `_TYPE_D_CLOSE_OVER_MA60_RATIO` + `_TYPE_D_DYNAMIC_WINDOW` + `_TYPE_E_SPREAD_PCT` + `_TYPE_E_DYNAMIC_WINDOW` + `_TYPE_E_CLOSE_OVER_MA60_RATIO` + `_TYPE_E_SHORT_ALIGN_WINDOW` + `_TYPE_E_SHORT_ALIGN_TOL` + `_TYPE_E_MA60_OVER_MA306_TOL` + 라벨 7개 + `_TYPE_CHECKERS`).
- [x] `chart240Filter.py` — **5개** 상수 추출(`_DEFAULT_REPORTS_ROOT`, `_CHART240_FILENAME`, `_OUTPUT_FILENAME`, `_MA60_MA306_TOLERANCE`, `_REQUIRED_CONSECUTIVE_BARS`).
- [x] `chartDayPreFilter.py` — **4개** 상수 추출(`_DEFAULT_REPORTS_ROOT`, `_CHARTDAY_FILENAME`, `_OUTPUT_FILENAME`, `_DAILY_SURGE_THRESHOLD`).
- [x] `chartDayFilter.py` — **11개** 상수 추출(경로/파일 3개 + `_MA10_MA20_MA60_TOLERANCE` + `_MA60_MA306_LOWER_TOL` + `_MA60_MA306_UPPER_TOL` + `_CLOSE_VS_MA612_LOWER` + `_CLOSE_VS_MA612_UPPER` + `_REQUIRED_CONSECUTIVE_BARS` + `_REQUIRED_ALIGNED_BARS` + `_STOCK_DIR_PATTERN` + `_TABLE_ROW_PATTERN`). *(이중 정규식 포함 시 총 12개; 위에 항목별로 정확히 열거됨)*
- [x] `investorFilter.py` — **10개** 상수 추출(`_DEFAULT_REPORTS_ROOT`, `_INVESTOR_FILENAME`, `_OUTPUT_FILENAME`, `_REQUIRED_BARS`, `_THRESHOLD_FOREIGN_CONSEC_SELL`, `_THRESHOLD_INST_CONSEC_SELL`, `_THRESHOLD_INDI_CONSEC_BUY`, `_THRESHOLD_FOREIGN_TOTAL_SELL`, `_STOCK_DIR_PATTERN`, `_TABLE_ROW_PATTERN`).
- [x] `financeFilter.py` — **6개** 상수 추출(`_DEFAULT_REPORTS_ROOT`, `_FINANCE_FILENAME`, `_OUTPUT_FILENAME`, `_STOCK_DIR_PATTERN`, `_CUP_NGA_ROW_PATTERN`, `_INVALID_MARKER`).
- [x] 5개 컬럼(변수 / 타입 / 현재 값 / 의미 / 파일:행) 전부가 모든 행에 채워짐(공백 없음).
- [x] `_ALIGN_TOL_LOOSE`(0.015, chart60_120Filter.py:120)와 `_MA_ALIGNMENT_TOLERANCE`(0.005, chart60Filter.py:75) 둘 다 문서화되었으며 결정적 구분 섹션에서 명시적으로 구별됨.
- [x] PRD §5.1 상호 참조 완료 — 카탈로그된 25개 행 전부가 코드 값과 일치; 문서 드리프트 권고 2건 제기됨(Type C %, Type D 60분 %).

**총합: 8개 소스 파일 전반에 걸쳐 추출된 `Final` 상수 75개**(활성 필터 모듈 7개 + `Filter_condition_update.py`).
