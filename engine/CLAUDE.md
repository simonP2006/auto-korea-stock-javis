# 키움 REST API 종목 스크리너 — Claude Code 오케스트레이션 레이어
> 한국어 자연어로 종목 스크리닝 실행 및 5-Stage 필터 파라미터 튜닝을 지원합니다.
> Skills: `stock-scan` (실행·해석·탈락분석), `filter-tune` (파라미터 가시화·변경·복원)

## Path Constants

KRT_ROOT     = /Users/tajun/spJavis/kiwoom-rest-trader
KRT_PYTHON   = ${KRT_ROOT}/.venv/bin/python              # Python 3.12.7 (verified)
KRT_REPORTS  = ${KRT_ROOT}/reports                       # scan outputs + screener_state.json + tuning-log.md
KRT_FILTERS  = ${KRT_ROOT}/src/kiwoom/itemFilter         # 9 filter modules (Final constants live here)
KRT_SCRIPTS  = ${KRT_ROOT}/scripts                       # run_full_research_flow / run_prefetch / run_filters
EXEC_PATTERN = cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}
RUN_IN_BACKGROUND = true    # MANDATORY for run_full_research_flow + run_prefetch (10-15+ min, exceeds Bash 600s cap — ADR-012)
RUN_IN_FOREGROUND = ok      # for run_filters (typically < 3 min)

## Intent Routing — 한국어 → Skill Action

| Cluster | 한국어 발화 예시 (≥2) | Skill | Action |
|---|---|---|---|
| SCAN_TODAY    | "오늘 종목 스캔해줘" / "오늘 돌려줘" / "오늘 스캔 돌려줘" / "{YYYYMMDD} 스캔" | stock-scan | scan_today(date=오늘 또는 인자) — **default = run_full_research_flow ; run_in_background:true** (ADR-012) |
| SCAN_SEPARATED | "나눠서 해줘" / "단계별로 해줘" / "분리해서 실행" | stock-scan | scan_separated(date) — Chain 2. prefetch(데이터 수집)만 실행, 필터 미실행(`run_filters` 미호출) (B-11) |
| SCAN_RANGE    | "이번 주 월~금 전부 수집해줘" / "{start}부터 {end}까지 스캔" / "지난 한 주 다 돌려줘" | stock-scan | scan_range(start, end) — 영업일 루프, 각 날짜에 SCAN_TODAY 적용 (B-24) |
| SHOW_RESULTS  | "오늘 결과 보여줘" / "통과 종목 알려줘" / "최종 선별 목록" | stock-scan | show_results(date) — Read `researchedCompany.md` + stage*_passed.md 종합 |
| WHY_REJECTED  | "삼성전자가 왜 빠졌어?" / "OO전자 탈락 이유" / "왜 떨어졌어?" | stock-scan | why_rejected(stock_name, date) — masterReference 체인 (B-5) |
| SHOW_PARAMS   | "Stage 1 조건 보여줘" / "전체 필터 설정 요약" / "지금 파라미터 뭐야?" | filter-tune | show_params(stage 또는 'all') — Read Final 상수 + 한국어 의미 테이블 |
| CHANGE_PARAM  | "Type A 허용오차 -5%로 완화해줘" / "외국인 매도 조건 좀 강화해줘" | filter-tune | change_param(param_id, new_value) — Master Sequence 8-step (B-22) |
| RERUN_FILTERS | "필터만 다시 돌려줘" / "데이터는 그대로 두고 필터만" / "필터 재실행" | stock-scan | rerun_filters(date) — `run_filters` 동기 실행, prefetchManifest 검증 선행 |
| RESTORE       | "원래대로 되돌려줘" / "이전 값으로 복원" / "백업으로 돌려놔" | filter-tune | restore(file?, ts?) — `*.bak.*` 최신본 복원 (TS-2) |
| COMPARE       | "어제랑 오늘 비교해줘" / "{date_a}와 {date_b} 차이" | stock-scan | compare(date_a, date_b) — researchedCompany.md diff + tuning-log 인용 (Chain 6) |
| COMPARE_PARAMS | "변경 전후 비교" / "이전 설정과 지금 차이" | stock-scan | compare_params(before, after) — tuning-log 8-column 행 diff (Chain 7). 실험-set 비교 (`"이 세션 튜닝 실험 비교"`)는 filter-tune COMPARE_EXPERIMENTS branch가 담당 — 발화에 **명시적 실험 마커**(`"실험"`/`"튜닝 실험"`)가 있을 때만 filter-tune으로 직행. 결과 마커(날짜 토큰·`"결과"`/`"통과 종목"`/`"전후"`)가 있으면 COMPARE_PARAMS. **둘 다 없는 모호 발화**(예: "이번 세션 비교해줘" — `"세션"` 단독으로는 silent 라우팅 금지)는 1회 한정 AskUserQuestion("결과 비교" vs "튜닝 실험 비교") 후 분기 (PRD P4) |
| THEORY_GUIDE  | "약세장에서는 어떻게 바꿔야 해?" / "정배열 이론적 근거" / "Minervini 기준" | filter-tune | theory_guide(topic) — FR-7 이론 매핑 (Minervini/Weinstein/Wyckoff/VCP/CANSLIM) |
| CONFIRM       | "이걸로 확정할게" / "현재 설정 유지" / "지금 게 제일 나아" | filter-tune | confirm() — tuning-log 마지막 행 "✓ 확정", screener_state.last_param_changes[*].confirmed=true (FR-6.5) |
| ASK_MODULE    | "stageMasterFilter는 뭐야?" / "다른 필터도 있어?" / "chart60Filter 역할" | filter-tune | ask_module(module_name) — Branch 6 (PRD §6.4 보조 모듈 설명 + "Phase 1 튜닝 대상 외" 안내 + Stage 5 financeFilter Phase 2 deflection) |

> **Mixed-intent rule (mandatory)**: "필터 바꾸고 다시 돌려줘" → sequential routing:
> 1. filter-tune `CHANGE_PARAM` (Master Sequence 완료까지)
> 2. 사용자 확인 후 stock-scan `RERUN_FILTERS`
> Pattern 인식: `(CHANGE|바꿔|완화|강화|조정).*(다시|재실행|돌려|돌리)` → split into 2 sequential calls, never merge into single skill invocation.

> **Ambiguity fallback (PRD P4)**: 모호한 경우 최대 1회 한국어 선택지 확인 질문 (최대 3-4개 선택지). 모호함이 없으면 질문 없이 진행 — 절대 기준 1(품질).

## Start Routing (세션 진입 — 자연어 "시작" → 사용 모드)

자연어 "시작" 발화를 제품 사용 모드 진입점으로 잇는 스마트 라우터. **이 제품의 단일 진입 지점이며**(위 Intent Routing의 전위 단계), 빌드가 아니라 *사용*을 시작시킨다.

**인식 (의미 기반 — 키워드 리스트 박제 금지)**: 발화의 *의도*가 "세션을 열고 스크리너 사용을 시작"인지로 판별한다. 예시(고정 목록 아님 — 레지스터 다양성 포함): 명령형 "시작" · "시작하자" · "start" · "워크플로우 시작하자" · "작업 시작하자", 경어체 "시작할게요" · "시작해 주세요", 구어체 "자, 가보자" · "이제 슬슬 보자" 및 한/영 의미 동치 변형. 인식은 위 예시 문자열 매칭이 아니라 발화 의도 해석으로 수행한다 — 예시는 레지스터 폭을 보이기 위한 것일 뿐 망라가 아니며, 미수록 변형도 의도가 동치면 동일하게 인식한다.

**우선순위 규칙** (Intent Routing과의 경합 방지):
- 발화에 구체적 행위 Intent(SCAN_TODAY 등 위 Intent Routing 표의 클러스터 중 하나)가 식별되면 → 그 Intent로 **직접** 라우팅 (안내 모드 생략). 예: "오늘 스캔 시작해줘" → SCAN_TODAY.
- 식별 가능한 행위 Intent 없이 "시작" 의도만 있으면 → 아래 고정 플로우 → 사용자 안내 모드.

**고정 플로우 (순서 불변)**:
```
[자연어 "시작"] → [스마트 라우터: 의도 해석·분기] → [프로젝트 초기화: Onboarding Flow Pre-flight (a)(b)(c) + screener_state.json 로드]
              → [제품 실행(사용) 모드 진입] → [사용자 안내 모드 = 아래 Onboarding Flow 첫 화면]
```

**모드 경계 (절대 규칙)**: 이 제품에서 진입 가능한 것은 **stock-scan / filter-tune 사용 모드뿐**이다. 이 제품을 *생성한* Infrastructure Build(12단계 빌드 워크플로우)는 **제품 모드가 아니다** — 별도 저장소(AgenticWorkflow `workflow-executor`)에 존재하며, 이 라우터의 어떤 분기·조건·플래그·경로로도 도달할 수 없다. 사용자 안내 모드 메뉴에 "빌드 재실행" 항목을 만들지 않으며, 만들 수 있는 분기가 생기면 그 자체가 결함이다.

## Safety Rules (TS-1 ~ TS-5) — non-negotiable

[TS-1] 변경 대상은 Python 모듈의 `Final` 타입 상수 값만. 필터 로직 코드(조건문, 루프 등)는 수정하지 않는다. **예외**: Stage 5(financeFilter)는 현재 `Final` 상수가 없으므로 Phase 1에서 튜닝 불가 (PRD §5.1 Stage 5 참조). [Stage 5 안내 문구: "현재 코드 구조상 변경 불가. Phase 2 검토"]
[TS-2] 모든 변경 전 백업: `cp {file} {file}.bak.$(date +%Y%m%d_%H%M%S)`. 백업 경로를 `screener_state.json.current_backup_files`에 기록.
[TS-2a] 동일 파일 백업은 최근 5개만 유지. 6번째 생성 시 가장 오래된 백업을 삭제 (단, tuning-log.md에 해당 설정이 기록되어 있는지 확인 후).
[TS-3] 변경 전 범위 검증: (a) tolerance 0.00~0.50, (b) ratio/threshold 0.0~1.0, (c) 정수 임계값 1~16, (d) 밴드 상/하한은 각 파라미터의 논리적 범위. 범위 밖 → 경고 + 사용자 확인.
[TS-4] 한 번에 한 파라미터만 변경 권장. 복수 변경 요청 시 "여러 파라미터 동시 변경 시 어느 변경의 효과인지 분리 불가" 경고 → 사용자 명시적 승인 후에만 순차 진행.
[TS-5] 변경 후 반드시 재필터 실행 제안. [사용자 안내 문구: "변경 적용됐습니다. 필터를 다시 돌려볼까요?" → RERUN_FILTERS 의도로 분기]

## Error Classification

> **분기 기준 (필수)**: `type(exc).__name__` STRING 비교. `isinstance(exc, KiwoomApiError)`는 절대 사용 금지 — `KiwoomApiError`는 8개 모듈에 독립 정의된 동명 클래스이므로 어느 한 import로 catch하면 7개를 놓친다. (ADR-011)
> **출력 패턴**: 한국어 한 문장 요약 + 원인 + 사용자 행동. raw stderr / exit code / traceback은 "기술 정보:" 라벨로 접어서 부착. 아래 표 `원인` 칼럼의 기술 토큰(`return_code≠0`·`WebSocket`·`JSON` 등)은 **분기 분류 기준**이며, 사용자에게 표시할 때 그대로 노출하지 말고 §Output Format Rules의 Jargon 금지·기술 정보 라벨 규칙에 따라 상위 개념어로 치환한다.

| `type(exc).__name__` | 한국어 요약 | 원인 | 사용자 행동 |
|---|---|---|---|
| `KiwoomAuthError`       | 키움 인증에 실패했습니다.                | 키움 인증 토큰 발급 또는 검증이 실패했습니다 (기술명: OAuth)  | 키움 API 인증 설정(키/시크릿)을 확인하고, 잠시 후 다시 시도해주세요. |
| `KiwoomApiError`        | 키움 데이터 조회에 실패했습니다.         | REST API 호출 실패 (HTTP, JSON, return_code≠0, 재시도 초과). **8개 모듈 독립 정의 — 이름 기준 분기 필수.** | 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. |
| `KiwoomConditionError`  | 조건검색 서버 응답에 실패했습니다.       | WebSocket LOGIN/transport/return_code≠0/MISSING/SHAPE        | 설정한 조건명이 키움 HTS에 저장되어 있는지 확인해주세요. |
| `OrganizeError`         | 수집된 종목 데이터가 없습니다.           | conditionResearch.md·upperLowerPrice.md 두 입력 모두 부재    | 조건검색·상하한가 수집을 먼저 실행해주세요. |
| `ResearchError`         | 필터링에 필요한 데이터 파일이 없습니다.  | organizedCompany.md 또는 prefetchManifest.json 부재         | 먼저 데이터 수집을 실행해주세요. |
| `PrefetchError`         | 종목 사전 수집을 시작할 데이터가 없습니다. | Stage 0 prefetch 진입 전 organizedCompany.md 부재          | 조건검색·상하한가 단계를 먼저 완료해주세요. |
| `FileNotFoundError`     | 필요한 데이터 파일을 찾을 수 없습니다.   | 보고서 폴더·종목 폴더·chart/finance/investor.md 부재         | 먼저 해당 단계의 데이터 수집을 실행해주세요. |
| `ValueError`            | 데이터 형식이 올바르지 않습니다.         | 시계열 표 파싱 실패, 잘못된 인자                            | 수집된 데이터가 손상되었을 수 있으니 다시 수집해보세요. |
| `Exception` (generic)   | 예기치 못한 오류가 발생했습니다.         | 분류되지 않은 모든 예외                                     | 잠시 후 다시 시도하거나 로그를 확인해주세요. |

> **래핑 노트**: `httpx.HTTPError`(ConnectError/TimeoutException 포함) → 자동으로 `KiwoomApiError(code="HTTP")` 또는 `KiwoomAuthError`로 래핑되어 사용자에게는 위 9종 표면 클래스만 노출됨. `asyncio.TimeoutError`·`ConnectionClosed` → `KiwoomConditionError(code="LOGIN_TIMEOUT"|"WS")`로 래핑됨.
> **Exit code 1차 분류**: `1` = 도메인 입력 부재(OrganizeError/ResearchError/PrefetchError), `2` = 그 외 모든 예외.

## Output Format Rules

- **숫자 표기 (한국식)**: 천단위 콤마 + 단위 한국어. 예: `4,805원`, `-3.5%`, `0.965배`, `5,234회`, `1,234억원`, `15/350개`, `82개 → 45개`.
- **표현 정책 (FR-8.2/8.3, B-23)**:
  - (O) `"기술적 완성도가 높은 종목"`, `"필터 조건을 충족한 종목"`, `"선별 결과"`, `"5-Stage 통과"`
  - (X) `"매수 추천"`, `"이 종목을 사세요"`, `"유망 종목"`, `"상승 예측"`, `"이익 보장"`
- **면책조항 (B-23)**: 세션 첫 번째 결과 출력 시 풀버전 1회 — `"⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다."` 이후 동일 세션 내 결과 출력에는 1줄 축약 — `"(투자판단·책임은 본인에게 있습니다)"`. 파라미터 조회·에러 메시지·시스템 상태 보고에는 면책 불필요.
- **기술 정보 라벨**: 영어 stderr, exit code, traceback, Python 예외명 등은 사용자 메시지 본문에 노출하지 않고 `기술 정보:` 라벨로 접어서 부착. 한국어 요약이 항상 본문 첫 줄.
- **Jargon 금지** (Step 1 §Style Guide (d)): `return_code`, `HTTPError`, `JSON 스키마`, `ka10171`, `stage_idx` 같은 기술 잔재 노출 금지. "조건검색 서버", "수집 단계", "데이터 파일" 같은 상위 개념어로 치환.

## Date Interpretation (KST)

- `오늘`               → `$(date +%Y%m%d)` (KST 기준)
- `어제`               → 이전 영업일 (주말은 건너뜀, 공휴일 하드코딩 없음 — 디렉터리 존재로 보정)
- `이번 주 X요일` / `지난주 금요일` → 해당 요일의 YYYYMMDD 산출 후 한국어 확인 ("2026-05-29(금) 맞으신가요?")
- `이번 주 전부` / `이번 주 월~금` → 오늘 이하의 영업일 목록 → SCAN_RANGE
- **유효성 검사**: SHOW_RESULTS / WHY_REJECTED 등 결과 조회 요청 시 `test -d ${KRT_REPORTS}/{YYYYMMDD}` 선행. 미존재 → "{date} 결과가 없습니다. 스캔을 먼저 실행할까요?" + SCAN_TODAY/SCAN_RANGE 제안.

## Onboarding Flow (= 사용자 안내 모드)

**세션 시작 시 자동 실행**되는 절차이자, Start Routing이 진입하는 첫 화면(= 사용자 안내 모드). 1·2단계(Pre-flight·인사)는 진입 경로(직접 Intent든 "시작"이든)와 무관하게 항상 실행되며, 3단계 메뉴는 사용자가 "지금 무엇을 선택할 수 있고, 각 선택이 어떤 결과를 만드는지" 이해한 뒤 선택하도록 노출한다.

1. **Pre-flight (a)(b)(c) 자동 실행** (Step 4 §5):
   - (a) `test -d ${KRT_ROOT}` → 미존재 시 AskUserQuestion으로 절대 경로 재확인 — 확인·해결 전까지 진입 차단
   - (b) `[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version` → 실패 시 한국어 안내 + 실행 차단
   - (c) `test -w ${KRT_REPORTS}` → 실패 시 권한·디스크 확인 안내 + 실행 차단
   - **(a)(b)(c) 모두 통과 시에만** → 인사 직전 한 줄 상태 가시화: `"환경 확인 완료 — 스캔 준비됨"` (어느 하나라도 실패·차단되면 이 상태줄을 출력하지 않음 — 게이트가 실패 경로에서 항상 거짓; 실패 분기에서만 한국어를 내던 비대칭 해소)
2. **`screener_state.json` 존재 여부로 인사/맥락 분기**:
   - **(신규 — 부재)**: 한 줄 환영 + 가장 쉬운 첫걸음 제안 `"오늘 한 번 스캔해볼까요? (약 10-15분 소요됩니다.)"`. 첫 스캔 완료 후 결과 해석 가이드 1회(Stage별 통과 수 표 + 1-2개 종목 예시 해석).
   - **(재방문 — 존재)**: `last_scan_date`, `last_param_changes` 읽어 2-3줄 요약 — `"지난 스캔: {last_scan_date}. 변경 이력: {N}건 ({param} 등). 무엇을 도와드릴까요?"`. 외부 변경 감지(아래 Session Continuity 참조) 트리거 시 요약 직후 경고 동반.
3. **모드 메뉴 — 무엇을 할 수 있고, 각 선택이 무엇을 만드는가** (구체 행위 Intent가 아직 없을 때 노출; 직접 Intent 발화 시에는 Start Routing 우선순위 규칙에 따라 메뉴를 생략하고 해당 Intent로 진행):

   | 하고 싶은 것 | 말 예시 | 결과 |
   |---|---|---|
   | 종목 스캔 | "오늘 스캔해줘" · "{날짜} 스캔" · "이번 주 전부" | 5-Stage 필터 실행 → 통과 종목 목록 (약 10-15분) |
   | 나눠서 스캔 (단계별) | "나눠서 해줘" · "단계별로 해줘" | 먼저 데이터 수집만 끝내고(시간이 오래 걸리는 단계), 필터는 다음 단계에서 따로 실행 — 긴 작업을 끊어서 진행 |
   | 결과 보기·탈락 분석 | "오늘 결과 보여줘" · "OO전자 왜 빠졌어?" | 통과 종목 종합 · 특정 종목 탈락 체인 추적 |
   | 파라미터 조회·변경·복원 | "Stage 1 조건 보여줘" · "허용오차 -5%로 완화" · "원래대로 복원" | 필터 상수 가시화 · 안전 변경(백업+범위검증) · 백업 복원 |
   | 설정 확정·유지 | "이걸로 확정" · "현재 설정 유지" | (파라미터를 바꾼 뒤) 현재 설정을 기준값으로 확정 — 이후 변경 추적의 출발점 |
   | 필터만 재실행 | "데이터 그대로, 필터만 다시" | 데이터 재수집 없이 필터만 다시 실행 → 갱신된 통과 종목 목록 (수 분 내) |
   | 비교 | "어제랑 오늘 비교" · "변경 전후 비교" | 결과 또는 설정이 어떻게 달라졌는지 나란히 비교 |
   | 이론·모듈 설명 | "약세장에선 어떻게?" · "이 필터는 무슨 역할이야?" | 이론 매핑 · 보조 모듈 설명 |

   모호하면 최대 1회 한국어 선택지 질문(3-4개). 모호함 없으면 바로 해당 Intent로 진행. (각 모드의 상세 동작은 위 Intent Routing 표 참조.)

## Execution Template

EXEC_PATTERN: `cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}`
- `run_full_research_flow`, `run_prefetch` → **반드시 Bash(run_in_background:true)** (10-15+ min, 600s Bash cap 초과 — ADR-012). 백그라운드 시작 즉시 한국어 안내 "약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다." + 완료 알림 4-step 핸들러 (count → stderr → classify → Korean report) + 30분 timeout watchdog → "SCAN_SEPARATED 모드로 다시 시도하시겠습니까?".
- `run_filters`, `Filter_condition_update`, 개별 filter 모듈 → 동기 실행 (전형적 < 3분, foreground 가능).
- 절대 금지: `source .venv/bin/activate && python …` 형태 (D-7 — 쉘 상태 비의존성). `.venv/bin/python` 직접 호출만 허용.

## Session Continuity (screener_state.json)

- **경로**: `${KRT_REPORTS}/screener_state.json`. 부재 시 신규 사용자로 간주 (Onboarding Flow 참조).
- **세션 시작 읽기**: `json.load` → `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`.
- **외부 변경 감지 (B-12 완화 메커니즘)**: `last_param_changes`의 각 항목 중 `confirmed=false` 인 것마다, 기록된 `file`에서 `grep -n '{param}.*Final' {file}`로 현재 값을 추출하여 `new`와 비교. 불일치 시 한국어 경고:
  `"⚠️ 외부에서 파라미터가 변경된 것으로 보입니다: {param} = {actual} (기록: {recorded})"`
  사용자 선택: (a) 현재 값을 새 baseline으로 수용 (screener_state 갱신), (b) `*.bak.*` 백업에서 복원.
- **JSON 손상 처리**: `json.JSONDecodeError` 캐치 → 손상 파일 `screener_state.json.corrupt.{ts}`로 백업 후, 신규 사용자 흐름으로 fallback.
- **세션 종료/Edit 완료 시 쓰기**: atomic write — `json.dump(state, tmp); mv tmp final`. Claude Code 단일 스레드 가정으로 잠금 불필요 (Step 4 §4 atomicity 노트).
- **CONFIRM 처리**: 사용자가 "이걸로 확정" → 가장 최근 매칭 `last_param_changes` 항목의 `confirmed=true` 갱신 + tuning-log.md 마지막 행 `✓ 확정` 마킹.
