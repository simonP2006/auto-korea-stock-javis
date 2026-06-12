# Step 2 — 리서치 통합 및 커버리지 검증

> 생성일: 2026-05-30
> 출처: step-1-param-inventory.md (Final 상수 75개), step-1-pipeline-analysis.md (모듈 9개, gap-value=Partial), step-1-error-patterns.md (오류 유형 14종)

## 1. Executive Summary

kiwoom-rest-trader 스크리너는 3개의 진입점 스크립트(`run_full_research_flow.py`, `run_prefetch.py`, `run_filters.py`)와 사용자 큐레이션 `masterReference.md`를 모든 스테이지에 대해 재평가하여 drop-reason을 누적-확장(append-only) `masterReference.log`에 추가하는 6번째 도구 모듈(`Filter_condition_update.py`)이 구동하는, 순차적인 5-Stage 필터 파이프라인(Stage 1 / 2 / 2-1 / 3 / 4 / 5)이다. 튜닝 표면은 잘 정의되어 있다: 8개 소스 파일에 걸쳐 75개의 `Final` 상수가 추출되었으며, PRD §5.1 카탈로그 행은 모두 실제 코드와 일치한다(단, `chart60_120Filter.render_markdown` 내부에 두 개의 사소한 문서 드리프트만 존재: "2.0%" / "60%" 문자열 vs 실제 3.5% / 50% 상수). 오류 표면은 14개 예외 유형이 지배하며, 사용자 노출 9개는 깔끔한 한국어 메시지 디스패치 테이블로 압축된다. Orchestration 계층에 대한 가장 큰 단일 설계 리스크는 **`KiwoomApiError`가 독립된 클래스 객체로 8번 정의되어 있다는 점**이다 — 어느 한 임포트를 키로 사용하는 `except KiwoomApiError`는 나머지를 조용히 놓치게 되므로, filter-tune Skill은 `type(exc).__name__` 또는 `RuntimeError` + 속성 인트로스펙션을 기반으로 디스패치해야 한다. FR-5.2에 필요한 가장 큰 격차값 설계 결정은 `masterReference.log`를 패치하여 스테이지 라인마다 구조화된 `[gap: …]` 접미사를 추가할 것인지 여부다; 현재 상태는 "자연어 텍스트만 존재, 수치는 인라인이지만 단위가 비균일(₩/%/회/억원)"하여 정규식 추출의 신뢰성이 떨어진다. PRD §FR-1부터 §FR-8까지 모두 차단 요소 없이 실현 가능하며, 남은 미해결 사항은 Step 3 휴먼 게이트로 이월된다(미해결 질문 4건).

## 2. PRD §FR-1부터 §FR-8까지 실현 가능성 매트릭스

| FR | 설명 (1줄) | 증거 (Step 1 출처) | 실현 가능성 | 리스크 |
|---|---|---|---|---|
| FR-1 | 자연어 기반 스캐너 실행 (full flow / prefetch / filters / 날짜 범위 / 사전 점검) | step-1-pipeline-analysis.md §(a)가 3개 스크립트 + 종료 코드 규약(0/1/2)을 모두 추적; step-1-error-patterns.md 4-6행이 `OrganizeError`/`ResearchError`/`PrefetchError`의 exit-1 계약 확인 | 실현 가능 | Low |
| FR-2 | 필터 결과 해석 (스테이지별 카운트, 비교, 면책 고지) | step-1-pipeline-analysis.md §(b)가 균일한 `stage*_passed.md` 평문 스키마 확인(라인당 stk_nm, UTF-8 LF, 끝 개행, 비어있을 경우 0바이트); 정본(canonical) SHOW_RESULTS = `researchedCompany.md` | 실현 가능 | Low |
| FR-3 | Drop-reason 심층 분석 (스테이지/조건/값, 다종목, 격차) | step-1-pipeline-analysis.md §(c)가 `masterReference.log`가 실제값 + 임계값을 인라인으로 기록함을 확인; step-1-param-inventory.md가 모든 스테이지별 튜닝 가능 항목을 설명 맥락과 함께 제공 | 실현 가능 | Med (FR-3.4 격차 정밀도 제한 — §5 / §10 참조) |
| FR-4 | 파라미터 시각화 (스테이지별 표, 이론 매핑, 이력) | step-1-param-inventory.md가 file:line, 현재값, 의미론적 의미, PRD §5.1 상호참조와 함께 75개 상수를 모두 열거(모든 행 일치) | 실현 가능 | Low |
| FR-5 | 파라미터 변경 실행 (자연어 → Edit, 영향 미리보기, 백업, 범위 점검, 공유 상수 가드) | step-1-param-inventory.md "Critical Distinctions"가 `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` + 공유 상수 팬아웃을 부각; 대상 변수마다 실제 `Final` 타입 확인 완료 | 실현 가능 | Med (FR-5.2 수치 영향 추정은 로그 포맷 선택에 의존 — §10 참조) |
| FR-6 | 반복 튜닝 루프 (`run_filters` 재사용, before/after diff, 복원, 확인, 튜닝 로그) | step-1-pipeline-analysis.md §(a)가 `run_filters.py`는 `Filter_condition_update`를 건드리지 않음을 확인; `researchedCompany.md`가 정본(canonical) diff 대상 | 실현 가능 | Low |
| FR-7 | 이론 기반 튜닝 가이드 (Minervini / Weinstein / Wyckoff / VCP / CANSLIM 매핑, 시장 국면 조정) | step-1-param-inventory.md의 스테이지별 "meaning" 컬럼이 이미 상수별 이론적 계보를 포함; PRD §5.3 ↔ 필터 매핑 테이블이 명확함 | 실현 가능 | Med (이론 매핑은 정착되었으나 정량적 시장 국면 조정 범위는 아직 출처 미확정 — §10 참조) |
| FR-8 | 모든 결과 출력 시 면책 고지 프레이밍 | 코드 측 차단 요소 없음 — 프롬프트 계층 규칙; Step 1에서 모순되는 내용 없음 | 실현 가능 | Low |

## 3. PRD §C.2 추적성 (Research 추가 조사 필요 항목)

| C.2 항목 | 상태 | Step 1 증거 | 비고 |
|---|---|---|---|
| `masterReference.log` 출력 포맷 | Resolved (Partial gap 데이터) | step-1-pipeline-analysis.md §(c) | 스키마, 구분자, 타임스탬프, 종목별 블록이 완전히 문서화됨; **격차값은 자연어 텍스트로만 존재**하며, 구조화된 `actual=`/`threshold=`/`gap=` 필드는 없음. 패치 제안 포함. |
| `kiwoom-rest-trader` 오류 패턴 | Resolved | step-1-error-patterns.md의 14행 전체 테이블 + 9개 알려진 유형 커버리지 | 한국어 메시지 스타일 가이드 자동 도출; `KiwoomApiError` 8 모듈 트랩이 아키텍처 리스크로 문서화됨. |
| `stage*_passed.md` 정확한 포맷 | Resolved | step-1-pipeline-analysis.md §(b) | 6개 스테이지 파일 모두 stk_nm 단위 동일한 라인 스키마 공유. **Type A/B/C/D/E 패턴 정보는 .md에 포함되지 않음** — 단독 실행 시 stdout과 파이프라인 내부 `r.extra["type_results"]`에만 존재. FR-2.2 "패턴 요약"은 `masterReference.log` reason 텍스트를 파싱하거나 `filter_stock()` 반환을 확장 캡처해야 함. |

## 4. workflow-idea §C-1부터 §C-10까지 해소

| 항목 | 질문 | 해소 | 출처 |
|---|---|---|---|
| C-1 | 파라미터 카탈로그 SOT 이중성 (PRD는 SOT = Python 소스로 명시; skill은 B-9 범위 점검을 위해 카탈로그 필요) | Research 단계에서 해소 — 카탈로그는 범위/경고 규칙만 저장하며, 현재값은 항상 `grep` / `Read`를 통해 실시간으로 읽음. Step 1 param inventory가 카탈로그 시드용 권위 있는 스냅샷을 제공. | step-1-param-inventory.md (75행 테이블) |
| C-2 | `masterReference.log` 격차 데이터 가용성 | Research 단계에서 해소 — **Partial**: 텍스트 수치는 존재, 구조화된 필드는 부재. 패치 여부 결정은 Planning으로 이월(§10 Open Q1 참조). | step-1-pipeline-analysis.md §(c) |
| C-3 | `_ALIGN_TOL_LOOSE` 공유 상수 딜레마 (Type B/C/D 팬아웃) | Research에서 해소(영향 맵 확정) → 정책 결정은 Planning으로 이월. step-1-param-inventory.md "Critical Distinctions"가 정확한 소비자 집합을 열거: Type B 60m + Type B MA60-MA306 + Type C MA60-MA306 + Type D 60m 폴백. | step-1-param-inventory.md §"Critical Distinctions" |
| C-4 | Stage 5의 하드코딩 `< 0` 비튜닝 가능 | Research에서 해소 — 임계값을 위한 `Final` 상수가 없음을 확인; CLAUDE.md가 "Phase 2" 회피 규칙을 인코딩해야 함. | step-1-param-inventory.md Stage 5 섹션 |
| C-5 | 날짜 / 휴일 처리 | Research에서 해소 — kiwoom-rest-trader가 `_exchange.py`(step-1-error-patterns 11행에서 참조됨)를 포함하나, Phase-1 계획은 `reports/{date}/` 존재 점검을 사용; 휴일 하드코딩 불필요. | step-1-error-patterns.md 11행 (`_exchange.py`) |
| C-6 | Research 필수 4항목 체크리스트 | Research에서 해소 — 4개 항목 모두 종료(아래 §5 참조). | step-1-* (3개 아티팩트 전체) |
| C-7 | FR-7 이론 가이드 전용 아이디어 부재 | 이월 — Research 범위 외; filter-tune skill `references/theory-anchors.md`는 Implementation 단계에서 작성 예정. | n/a |
| C-8 | 배포 위치 미정 (A/B/C) | Planning으로 이월 — (A) kiwoom-rest-trader 내부, (B) 별도 디렉터리, (C) AgenticWorkflow 내부 중 선택; B-12 Hook 재사용에 영향. Step 1은 이 결정에 영향이 없음. | n/a |
| C-9 | 메타 수준 격차 (시스템 행동 vs 빌드 방법) | Planning으로 이월 — B-19/B-20/B-21 (배포 / 빌드 순서 / 검증)이 이를 흡수. | n/a |
| C-10 | B-11 기본 실행 모드 vs FR-1.1 명세 긴장 (분할 vs full-flow 기본값) | Research에서 해소(기계적 능력) — `run_full_research_flow.py`와 `run_prefetch.py + run_filters.py` 모두 기계적으로 지원됨; 정책 선택(SCAN_TODAY의 기본값)은 Planning으로 이월. | step-1-pipeline-analysis.md §(a) |

## 5. workflow-idea §C-6 (Research 필수 조사 4-Item Checklist)

- [x] C-6-1: `masterReference.log` gap 수치 포함 여부 → **Partial — 격차값은 스테이지별 `reason` 문자열 내부의 인라인 자연어 텍스트로만 존재**(예: `종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%] 이탈`). 구조화된 `[gap: …]` 필드 없음. Filter-tune 영향 추정기(FR-5.2)는 정규식 추출에 의존하거나 제안된 최소 패치(3단계)에 의존해야 함. (증거: step-1-pipeline-analysis.md §(c) "Gap value inclusion: Partial")
- [x] C-6-2: `stage*_passed.md` 포맷 + Type 패턴 정보 → **6개 스테이지 파일 모두 종목명 단위 동일한 평문 스키마(UTF-8/LF, 끝 개행, 비어있을 경우 0바이트)를 사용. Type A/B/C/D/E 패턴 정보는 포함되지 않음** — Stage 1 .md는 stk_nm만 출력. Type 정보는 `r.extra["type_results"]`에 존재하며 단독 실행 시에만 stdout에 표면화됨; FR-2.2 "통과 패턴 요약"은 `masterReference.log` reason 문자열에서 가져오거나(`Filter_condition_update` 트리거 이후) 직접 `filter_stock()` 호출을 통해 가져와야 함. (증거: step-1-pipeline-analysis.md §(b))
- [x] C-6-3: 실제 오류 패턴 → **14개의 서로 다른 오류 유형 카탈로깅됨**(도메인 커스텀 6개 + 빌트인 3개 + 간접 래핑 5개). 종료 코드 규약은 일관됨(`0` 정상 / `1` 입력 부재 도메인 오류 / `2` 그 외 전부). 한국어 메시지 스타일 가이드 도출(4 규칙: 도메인 언어 / 다음 행동 명령형 / 일시적 vs 구조적 / 전문 용어 배제). **아키텍처 트랩**: `KiwoomApiError`가 동일 이름의 독립 클래스 객체로 8회 정의됨 — 임포트 기반의 `except KiwoomApiError`를 절대 사용하지 말 것. (증거: step-1-error-patterns.md 전체 테이블 + 아키텍처 비고)
- [x] C-6-4: 모든 Final 상수 추출 → **8개 소스 파일에 걸쳐 75개의 `Final[...]` 타입 상수 열거됨**(활성 필터 모듈 7개 + `Filter_condition_update.py`). PRD §5.1 카탈로그: 25/25 행이 코드 값과 일치; `chart60_120Filter.render_markdown` 문자열 리터럴 내부에 2개의 문서 드리프트 권고(Type C "2.0%" 구식, Type D "60%" 구식). PRD 카탈로그에서 누락되어야 할 상수는 없음; 누락된 모든 상수는 의도적으로 구조/스캐폴딩성. (증거: step-1-param-inventory.md "Coverage Self-Check" + "PRD §5.1 Cross-Reference")

## 6. 정제된 파라미터 인벤토리 (스테이지별 요약)

전체 75행 테이블은 **step-1-param-inventory.md**에 존재하며 카탈로그 시드를 위한 SOT 스냅샷이다. `filter-tune` Skill을 위한 스테이지별 튜닝 관련성:

| 스테이지 | 모듈 | 튜닝 가능성 높은 상수 | 비공개/공유 | 비고 |
|---|---|---|---|---|
| 1 | `chart60_120Filter.py` | `_TYPE_A_ALIGN_TOL`, `_ALIGN_TOL_LOOSE` ⚠️공유, `_TYPE_B_BELOW_MA60_RATIO`, `_TYPE_C_CONVERGE_PCT`, `_TYPE_D_ALIGN_TOL_120`, `_TYPE_D_CLOSE_OVER_MA60_RATIO`, `_TYPE_E_SPREAD_PCT`, `_TYPE_E_SHORT_ALIGN_TOL`, `_TYPE_E_CLOSE_OVER_MA60_RATIO`, `_TYPE_E_MA60_OVER_MA306_TOL`, `_REQUIRED_STATIC_BARS` | 대부분 Type별 비공개; `_ALIGN_TOL_LOOSE` 팬아웃 = Type B 60m + Type B MA60-MA306 + Type C MA60-MA306 + Type D 60m 폴백 | 라벨 7개 + 디스패치 테이블 포함 총 26개 상수; 문서 드리프트 점검 사이트 11곳 중 2곳 구식 |
| 1-adj | `chart60Filter.py` (단독) | `_MA_ALIGNMENT_TOLERANCE` (0.005), `_REQUIRED_CONSECUTIVE_BARS` (3) | 비공개 — Stage 1의 `_ALIGN_TOL_LOOSE`와 공유되지 않음 | **혼동 방지**: 아래 구분 블록 참조 |
| 2 | `chart240Filter.py` | `_MA60_MA306_TOLERANCE` (0.025), `_REQUIRED_CONSECUTIVE_BARS` (3) | 비공개 | chart60 정규식을 재임포트하여 재사용 |
| 2-1 | `chartDayPreFilter.py` | `_DAILY_SURGE_THRESHOLD` (0.15) | 비공개 | 튜닝 가능한 임계값 1개만 존재 |
| 3 | `chartDayFilter.py` | `_MA10_MA20_MA60_TOLERANCE`, `_MA60_MA306_LOWER_TOL`, `_MA60_MA306_UPPER_TOL`, `_CLOSE_VS_MA612_LOWER`, `_CLOSE_VS_MA612_UPPER`, `_REQUIRED_ALIGNED_BARS`, `_REQUIRED_CONSECUTIVE_BARS` | 비공개 | 비대칭 MA612 엔벨로프 (하단 -15%, 상단 +50%) |
| 4 | `investorFilter.py` | `_THRESHOLD_FOREIGN_CONSEC_SELL` (2), `_THRESHOLD_INST_CONSEC_SELL` (8), `_THRESHOLD_INDI_CONSEC_BUY` (3), `_THRESHOLD_FOREIGN_TOTAL_SELL` (15) | 비공개 | 모두 정수형 일수 임계값 |
| 5 | `financeFilter.py` | **없음** — `cup_nga < 0` 하드코딩 | n/a | CLAUDE.md가 Phase 2로 회피해야 함 |

### `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` — 혼동 금지

| 속성 | `_ALIGN_TOL_LOOSE` | `_MA_ALIGNMENT_TOLERANCE` |
|---|---|---|
| 소유자 | `chart60_120Filter.py:120` | `chart60Filter.py:75` |
| 값 | 0.015 (×0.985, -1.5%) | 0.005 (×0.995, -0.5%) |
| 범위 | Stage 1 내부 Type B/C/D 간 공유 | 단독 chart60의 유일한 정렬 허용 오차 |
| 튜닝 영향 | Type B/C/D를 가로질러 영향 | 국지적, 스테이지 간 전파 없음 |

filter-tune Skill은 사용자가 "60-분 정배열 허용오차 완화"라고 말할 때 어떠한 Edit 이전에 반드시 구분해야 한다.

step-1-param-inventory.md에 추가로 문서화된 유사 명칭 트랩: `_REQUIRED_CONSECUTIVE_BARS`는 3개 모듈에서 독립적으로 선언됨(현재 모두 `3`이나 독립적), `_REQUIRED_STATIC_BARS` (8) vs `_REQUIRED_BARS` (16, investor) vs `_REQUIRED_CONSECUTIVE_BARS` (3); 3개 시간프레임에 걸쳐 3개의 서로 다른 MA60-MA306 허용 오차.

## 7. 파이프라인 아키텍처 (운영 관점)

`stock-scan` Skill이 호출하는 진입점(모두 `/Users/tajun/spJavis/kiwoom-rest-trader/scripts/` 아래, argparse 없음 — 직접 `sys.argv` 파싱):

- `SCAN_TODAY` → `run_full_research_flow.py` — 전체 파이프라인 (① upperLowerPrice → ② conditionCompany → ③ organizedCompany → Stage 0 prefetch → Stage 1-5 필터 → `Filter_condition_update`). `__main__`은 69-70행. Exit 0/1/2.
- `SCAN_PREFETCH_ONLY` → `run_prefetch.py` — ①+②+③+Stage 0만 수행, 필터링 없음, `Filter_condition_update` 호출 없음. `__main__`은 185-186행. Exit 0/1/2.
- `SCAN_FILTER_ONLY` → `run_filters.py` — `researchFlow.filter_today(date)` + `save_researched_company` + `save_all_stages_passed`. **`Filter_condition_update`를 호출하지 않음** — `masterReference.log`는 `run_full_research_flow.py`를 통해서만 갱신됨. `__main__`은 87-88행. Exit 0/1/2.

단독 필터 호출 패턴 (filter-tune Skill 또는 사용자에 의한 외과적 디버깅용) — 9개 필터 모듈 모두 `__main__`을 노출:

- `python -m src.kiwoom.itemFilter.<module> <stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` (`stageMasterFilter.py`를 제외하고 argparse 미사용).
- 라인: `chart60_120Filter.py:1071`, `chart240Filter.py:686`, `chartDayPreFilter.py:522`, `chartDayFilter.py:909`, `investorFilter.py:695`, `financeFilter.py:543`, `chart60Filter.py:819`, `Filter_condition_update.py:299`, `stageMasterFilter.py:713`.

WHY_REJECTED 체인 진입점: `python -m src.kiwoom.itemFilter.Filter_condition_update YYYYMMDD [YYYYMMDD …]` — 공백 구분 다중 날짜 인자 지원.

**정본(canonical) SHOW_RESULTS 파일**: `researchedCompany.md` (step-1-pipeline-analysis.md §(b)/Recommended canonical의 5가지 근거):
1. `run_full_research_flow.py`와 `run_filters.py` 양쪽이 모두 생성하는 유일한 파일.
2. `Filter_condition_update`가 `_RESEARCHED_MD`를 통해 명시적으로 참조함.
3. `final_selected=True` (6개 스테이지 모두 통과)의 정확한 의미론.
4. `stage5_finance_passed.md`와 동일 내용이지만 의미론이 더 명확함.
5. `.p1.md`/`.p2.md`는 **레거시(legacy) 고아(orphan) 파일** — 현재 `src/`에는 생성 코드가 존재하지 않음; 2026-05-21 이전 디렉터리에만 존재. `masterConditionCompany.md`는 `stageMasterFilter.py`에서 생성됨(Phase 2 범위, 독립 풀).

## 8. 오류 처리 매트릭스 (운영 관점)

카탈로깅된 14개 유형을 filter-tune / stock-scan Skill이 디스패치해야 하는 9개 사용자 노출 클래스로 압축:

| 오류 | 사용자 노출 한국어 메시지 | 권장 사용자 행동 | 복구 전략 |
|---|---|---|---|
| `KiwoomAuthError` | 키움 인증에 실패했습니다. APP_KEY·SECRET_KEY 설정을 확인하고, 잠시 후 다시 시도해주세요. | 자격 증명 확인 후 재시도 | 환경 변수 갱신 후 재실행 |
| `KiwoomApiError` (8개 모듈 로컬 정의 중 하나) | 키움 데이터 조회에 실패했습니다. 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. | 대기 후 재시도 | prefetch 재실행; `type(exc).__name__` 기반 디스패치 |
| `KiwoomConditionError` | 조건검색 서버 응답에 실패했습니다. 설정한 조건명이 키움 HTS에 저장되어 있는지 확인해주세요. | HTS 조건명 확인 | condition 스테이지 재실행 |
| `OrganizeError` | 수집된 종목 데이터가 없습니다. 조건검색·상하한가 수집을 먼저 실행해주세요. | condition + upperLower 스테이지 실행 | 이전 파이프라인 스테이지 재실행 |
| `ResearchError` | 필터링에 필요한 데이터 파일이 없습니다. 먼저 데이터 수집(prefetch)을 실행해주세요. | prefetch 실행 | `run_prefetch`로 전환 |
| `PrefetchError` | 종목 사전 수집을 시작할 데이터가 없습니다. 조건검색·상하한가 단계를 먼저 완료해주세요. | condition 스테이지 실행 | `run_full_research_flow`를 처음부터 재실행 |
| `httpx.HTTPError` (`ConnectError`, `TimeoutException` 포함) | 키움 서버에 연결할 수 없습니다. 인터넷 연결과 키움 서버 상태를 확인한 뒤 다시 시도해주세요. | 네트워크 확인 후 재시도 | 내부적으로 `KiwoomApiError`/`KiwoomAuthError`로 래핑; 사용자 노출은 래핑된 예외 |
| `FileNotFoundError` | 필요한 데이터 파일을 찾을 수 없습니다. 먼저 해당 단계의 데이터 수집을 실행해주세요. | 선행 스테이지 실행 | 상위 파이프라인 단계 재실행 |
| `ValueError` (파서/인자) | 데이터 형식이 올바르지 않습니다. 수집된 데이터가 손상되었을 수 있으니 다시 수집해보세요. | 재수집, 지속될 경우 버그 제출 | 해당 종목에 대해 prefetch 강제 재실행 |

**아키텍처 리스크 (filter-tune Skill에 반드시 표면화)**: `KiwoomApiError`가 **8개 모듈**에서 독립적으로 선언됨(chart60/120/240/Day 클라이언트의 `models.py`, `etc/foreigner.py:74`, `upperLowerPrice.py:214`, `finance/finance.py:82`, `investor/investor.py:88`). 각각 동일 이름의 별개 클래스 객체. 한 임포트의 `except KiwoomApiError`로는 다른 것을 잡지 못한다. **`type(exc).__name__ == "KiwoomApiError"` 기반 디스패치** 또는 공통 베이스 `RuntimeError` + 속성 인트로스펙션(`exc.code`, `exc.api_id`) 사용. 모든 `KiwoomApiError`/`KiwoomAuthError` raise에는 명시적 catch가 0개 — 스크립트 진입점의 `except Exception`에 흡수되어 exit 2로 종료. 종료 코드 규약은 일관됨: `0` 정상 / `1` 입력 부재 도메인 오류 / `2` 그 외 전부 — Skill은 종료 코드를 1차 디스패치 키로 활용 가능.

## 9. 상호참조 검증

3개의 Step 1 아티팩트 간 상호 일관성 점검:

- ✅ **파라미터 인벤토리 ↔ 파이프라인 분석**: step-1-param-inventory.md에 열거된 모든 모듈(`chart60_120Filter`, `chart60Filter`, `chart240Filter`, `chartDayPreFilter`, `chartDayFilter`, `investorFilter`, `financeFilter`, `Filter_condition_update`)이 step-1-pipeline-analysis.md의 호출 체인 또는 `__main__` 테이블에 등장. `Filter_condition_update.py`의 `_STAGES`에 정의된 5-Stage 실행 순서(S1→S2→S2-1→S3→S4→S5)가 `researchFlow.facade._run_filter_pipeline` 실행과 일치하며 PRD §2.2 스테이지 순서와도 일치.
- ✅ **오류 패턴 ↔ 파이프라인**: step-1-error-patterns.md에 인용된 모든 raise 위치가 step-1-pipeline-analysis.md가 추적하는 모듈(`auth.py`, `*/client.py`, `conditionCompany/*`, `organizedCompany/facade.py`, `researchFlow/facade.py`, `researchFlow/prefetch.py`, `itemFilter/*Filter.py`)에 존재. 스크립트의 catch 위치(`run_research_flow.py`, `run_filters.py`, `run_prefetch.py`)가 step-1-pipeline-analysis.md §(a)의 종료 코드 계약과 일치.
- ✅ **파라미터 인벤토리 ↔ 오류 패턴**: `itemFilter/*Filter.py`(chart60:565, chart240:450, chartDay:657, chartDayPre:316, chart60_120:789, finance:365, investor:479)의 `FileNotFoundError` / `ValueError` catch 위치는 `Final` 상수가 인벤토리된 모든 모듈을 커버.

3개 Step 1 출력물 간 **충돌 미탐지**. step-1-param-inventory.md의 두 가지 사소한 권고(`render_markdown` 문자열 리터럴 내 Type C "2.0%" / Type D "60%" 문서 드리프트, chart60_120Filter.py:866/870)는 순수 문서 드리프트이며 — 계산은 실제 `Final` 상수로 실행됨 — 아래 Open Question 2로 표면화됨.

## 10. 미해결 질문 (Step 3 휴먼 게이트로 이월)

| 질문 | 미해결 이유 | 제안된 완화책 | 처리 위치 |
|---|---|---|---|
| Q1: `masterReference.log`를 패치하여 스테이지 라인마다 구조화된 `[gap: actual=…, threshold=…, gap=…]` 접미사를 추가해야 하는가? | 현재 로그는 격차값을 비균일 단위(₩/%/회/억원)의 자연어 텍스트로만 전달. FR-5.2(a) 영향 추정의 정규식 추출은 구조화된 필드 없이는 신뢰할 수 없음. step-1-pipeline-analysis.md §(c)가 3단계 최소 패치를 제공. | Planning에서 결정: (A) 정규식 최선 노력 추출 + 사용자에 대한 명시적 정밀도 단서와 함께 Phase-1 출시, (B) `_analyze_stock`에 3단계 패치를 적용하여 부록 `[gap: …]`이 출력되도록 하고 Skill이 결정론적 파싱에 의존하게 함. 트레이드오프: (A) kiwoom-rest-trader 코드 변경 0건, 낮은 정밀도; (B) kiwoom-rest-trader 소규모 패치 1건 + 즉각적인 정밀도 향상. | Planning §filter-tune design |
| Q2: `chart60_120Filter.py render_markdown`의 문서 드리프트("Type C 2.0%"가 실제 3.5%와 상이; "Type D 60%"가 실제 50%와 상이) — 지금 수정할 것인가, 이월할 것인가? | step-1-param-inventory.md §"PRD §5.1 Cross-Reference" 권고 #1+2. 계산은 정확; 렌더링된 Markdown을 읽는 사용자는 구식 백분율을 보게 됨. 기존 보고서를 검토할 때 사용자를 오도할 수 있음. | Planning에서 결정: (A) chart60_120Filter.py:866/870의 두 문자열 리터럴을 단일 trivial PR에서 수정(로직 변경 없음, 실제 상수에 충실), (B) Phase 2로 이월하고 filter-tune Skill이 사용자가 chart60_120Filter 렌더링 출력을 읽을 때마다 불일치를 주석으로 표시. | Planning §kiwoom-rest-trader 변경 범위 |
| Q3: filter-tune Skill은 `KiwoomApiError` 8 모듈 트랩을 사용자에게 노출해야 하는가, 디스패치 계층 뒤에 숨겨야 하는가? | 트랩은 사용자에게 보이지 않지만 중요한 유지보수 관심사임. step-1-error-patterns.md §아키텍처 비고 #1이 이를 문서화. filter-tune이 단지 `type(exc).__name__`을 통해 잡기만 하면 사용자는 알 수 없으며; 향후 kiwoom-rest-trader 리팩토링이 클래스를 통합할 경우 디스패치가 조용히 깨질 수 있음. | 런타임 사용자 노출 메시지에서는 숨김(항상 정본 한국어 텍스트 출력), 그러나 **운영자(Claude)를 위한 내부 CLAUDE.md 노트를 인코딩**하여 디스패치 규칙과 그 기저의 8 모듈 사실을 문서화. kiwoom-rest-trader의 매 릴리스마다 재검증(B-13 (e) "변수명 존재 검증" 방식의 점검을 "class 통합 검증"으로 확장). | filter-tune Skill `references/error-dispatch.md` |
| Q4: SCAN_TODAY 기본 실행 모드 — `run_full_research_flow` (FR-1.1 기준) vs `run_prefetch` + `run_filters` 분할 (B-11 기준)? | step-1-pipeline-analysis.md가 양쪽 모두 기계적으로 지원됨을 확인; `run_filters`는 `masterReference.log`를 갱신하지 않는 반면 `run_full_research_flow`는 갱신함. 이는 UX/orchestration 결정이지 리서치 질문이 아님. | C-10의 3개 옵션에 따라 Planning에서 결정: (a) PRD 충실: SCAN_TODAY = full-flow 기본, "나눠서 해줘" → 분할; (b) B-11: 항상 분할, "한 번에 해줘" = full-flow; (c) 하이브리드: 최초 실행 = full-flow(온보딩), 이후 분할(튜닝 세션). FR-1.4 진행 보고와 FR-6 튜닝 루프 사용성의 최적 균형을 위해 (c) 권장. | Planning §CLAUDE.md 라우팅 테이블 |

## 11. 검증 자체 점검

- [x] 3개 Step 1 출처가 모두 참조됨 (file:section 인용) — step-1-param-inventory.md (§Critical Distinctions, §PRD §5.1 Cross-Reference, §Coverage Self-Check); step-1-pipeline-analysis.md (§(a), §(b), §(c)); step-1-error-patterns.md (전체 테이블, §Architectural Notes)
- [x] FR-1부터 FR-8까지 각각 실현 가능성 판정 + Step 1 증거 보유 (§2 — 8/8 행)
- [x] 4개 C-6 항목 모두 ✅ 및 증거 보유 (§5 — 4/4)
- [x] C-1부터 C-10까지 10개 항목 모두 Resolution 컬럼 보유 (§4 — 10/10; Resolved at Research 6건, Deferred-policy 1건, Deferred-Planning 3건)
- [x] Executive Summary ≤ 10줄 (§1 — 응집된 단일 문단, ≤10줄)
- [x] Open Questions 섹션에 제안된 완화책을 포함한 항목 ≥ 1건 (§10 — 4건, 각각 제안된 완화책 포함)
- [x] Step 1 출력물 간 충돌 없음 (§9 — 3개 쌍별 점검 모두 ✅; 두 개의 사소한 문서 드리프트 권고는 Open Question 2로 표면화)
