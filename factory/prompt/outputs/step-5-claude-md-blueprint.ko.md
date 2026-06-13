# Step 5 — CLAUDE.md 블루프린트

> 생성일: 2026-05-30
> 대상 파일: `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md`
> 목표 크기: 80-130 줄 (간결하면서도 완전한)
> 본 블루프린트로부터 Step 8 `@claude-md-builder`가 생성
> 출처: PRD §FR-1..FR-8 + §TS-1..TS-5 + §7.3 + workflow-idea §B-3/§B-12/§B-15/§B-23/§B-25 + Step 1 error-patterns + Step 4 아키텍처 (경로 상수, 스키마, OQ-1..OQ-4 / ADR-009..012)

## 블루프린트 규약

- **(spec)** = Step 8 `@claude-md-builder`가 최종 CLAUDE.md에 그대로(verbatim) 기록하는 텍스트/구조
- **(source)** = 추적성 앵커 (PRD FR-N / TS-N / §X.Y, workflow-idea B-N, Step 산출물 §N, ADR-N)
- **(estimate)** = 최종 80-130줄 목표에 기여하는 대략적 줄 수

블루프린트 자체는 근거, 대안, 검증 항목을 포함하므로 300줄을 초과할 수 있다 — 이 중 어느 것도 최종 파일에는 상속되지 않는다.

---

## §1. 헤더 (estimate: 3 줄, source: PRD §1 한 줄 정의 + §1 구현 형태 + workflow-idea B-1 2-skill 구조)

**(spec)** — CLAUDE.md 상단의 verbatim 블록:

```
# 키움 REST API 종목 스크리너 — Claude Code 오케스트레이션 레이어
> 한국어 자연어로 종목 스크리닝 실행 및 5-Stage 필터 파라미터 튜닝을 지원합니다.
> Skills: `stock-scan` (실행·해석·탈락분석), `filter-tune` (파라미터 가시화·변경·복원)
```

**근거**: 첫 세 줄에서 (a) 시스템 정체성, (b) 한국어 전용 페르소나, (c) 두 스킬 분리(B-1)를 확립한다. 스킬을 이름으로 참조하므로 §3의 라우팅 테이블이 정본(canonical) 목적지를 갖는다.

---

## §2. 경로 상수 (estimate: 8 줄, source: Step 4 §1 + workflow.md Constants line 44 + ADR-007 venv 잠금 + ADR-012 백그라운드 의무)

**(spec)** — "## Path Constants" 헤딩 아래의 verbatim 블록:

```
KRT_ROOT     = /Users/tajun/spJavis/kiwoom-rest-trader
KRT_PYTHON   = ${KRT_ROOT}/.venv/bin/python              # Python 3.12.7 (verified)
KRT_REPORTS  = ${KRT_ROOT}/reports                       # scan outputs + screener_state.json + tuning-log.md
KRT_FILTERS  = ${KRT_ROOT}/src/kiwoom/itemFilter         # 9 filter modules (Final constants live here)
KRT_SCRIPTS  = ${KRT_ROOT}/scripts                       # run_full_research_flow / run_prefetch / run_filters
EXEC_PATTERN = cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}
RUN_IN_BACKGROUND = true    # MANDATORY for run_full_research_flow + run_prefetch (10-15+ min, exceeds Bash 600s cap — ADR-012)
RUN_IN_FOREGROUND = ok      # for run_filters (typically < 3 min)
```

**근거**: Step 4 §1 검증에 따라 5개 디렉터리 상수 모두 `PASS`. ADR-007 / D-7에 따라 `.venv/bin/python` 사용 (`source .venv/bin/activate`는 절대 사용 금지). ADR-012 백그라운드 의무는 풀-플로우 스캔에서 Bash 도구의 10분 타임아웃 실패를 방지한다.

---

## §3. 의도 클러스터 라우팅 테이블 (estimate: 30 줄, source: workflow-idea B-3 + Step 4 §7 + PRD §3 대화 패턴 + ADR-012)

**(spec)** — Markdown 테이블 포맷, B-3에 명시된 12개 필수 클러스터 + 혼합 의도 규칙(workflow.md 검증 line 198, line 207) 그대로:

```
## Intent Routing — 한국어 → Skill Action

| Cluster | 한국어 발화 예시 (≥2) | Skill | Action |
|---|---|---|---|
| SCAN_TODAY    | "오늘 종목 스캔해줘" / "오늘 결과 보여줘" / "오늘 돌려줘" / "{YYYYMMDD} 스캔" | stock-scan | scan_today(date=오늘 또는 인자) — **default = run_full_research_flow ; run_in_background:true** (ADR-012) |
| SCAN_RANGE    | "이번 주 월~금 전부 수집해줘" / "{start}부터 {end}까지 스캔" / "지난 한 주 다 돌려줘" | stock-scan | scan_range(start, end) — 영업일 루프, 각 날짜에 SCAN_TODAY 적용 (B-24) |
| SHOW_RESULTS  | "오늘 결과 보여줘" / "통과 종목 알려줘" / "최종 선별 목록" | stock-scan | show_results(date) — Read `researchedCompany.md` + stage*_passed.md 종합 |
| WHY_REJECTED  | "삼성전자가 왜 빠졌어?" / "OO전자 탈락 이유" / "왜 떨어졌어?" | stock-scan | why_rejected(stock_name, date) — masterReference 체인 (B-5) |
| SHOW_PARAMS   | "Stage 1 조건 보여줘" / "전체 필터 설정 요약" / "지금 파라미터 뭐야?" | filter-tune | show_params(stage 또는 'all') — Read Final 상수 + 한국어 의미 테이블 |
| CHANGE_PARAM  | "Type A 허용오차 -5%로 완화해줘" / "외국인 매도 조건 좀 강화해줘" | filter-tune | change_param(param_id, new_value) — Master Sequence 8-step (B-22) |
| RERUN_FILTERS | "필터만 다시 돌려줘" / "데이터는 그대로 두고 필터만" / "필터 재실행" | stock-scan | rerun_filters(date) — `run_filters` 동기 실행, prefetchManifest 검증 선행 |
| RESTORE       | "원래대로 되돌려줘" / "이전 값으로 복원" / "백업으로 돌려놔" | filter-tune | restore(file?, ts?) — `*.bak.*` 최신본 복원 (TS-2) |
| COMPARE       | "어제랑 오늘 비교해줘" / "변경 전후 비교" / "{date_a}와 {date_b} 차이" | stock-scan | compare(date_a, date_b) 또는 compare_params(before, after) — researchedCompany.md diff + tuning-log 인용 |
| THEORY_GUIDE  | "약세장에서는 어떻게 바꿔야 해?" / "정배열 이론적 근거" / "Minervini 기준" | filter-tune | theory_guide(topic) — FR-7 이론 매핑 (Minervini/Weinstein/Wyckoff/VCP/CANSLIM) |
| CONFIRM       | "이걸로 확정할게" / "현재 설정 유지" / "지금 게 제일 나아" | filter-tune | confirm() — tuning-log 마지막 행 "✓ 확정", screener_state.last_param_changes[*].confirmed=true (FR-6.5) |
| ASK_MODULE    | "stageMasterFilter는 뭐야?" / "다른 필터도 있어?" / "chart60Filter 역할" | (no skill) | inline_answer — PRD §6.4 보조 모듈 설명 + "Phase 1 튜닝 대상 외" 안내 |

> **Mixed-intent rule (mandatory)**: "필터 바꾸고 다시 돌려줘" → sequential routing:
> 1. filter-tune `CHANGE_PARAM` (Master Sequence 완료까지)
> 2. 사용자 확인 후 stock-scan `RERUN_FILTERS`
> Pattern 인식: `(CHANGE|바꿔|완화|강화|조정).*(다시|재실행|돌려|돌리)` → split into 2 sequential calls, never merge into single skill invocation.

> **Ambiguity fallback (PRD P4)**: 모호한 경우 최대 1회 한국어 선택지 확인 질문 (최대 3-4개 선택지). 모호함이 없으면 질문 없이 진행 — 절대 기준 1(품질).
```

**근거**: B-3의 12개 클러스터 모두 verbatim. workflow.md line 207에 따라 혼합 의도 규칙을 명시. 각 클러스터는 대응되는 Skill의 SKILL.md가 구현할(Step 9) 단일 구체 액션 이름으로 매핑된다. `ASK_MODULE`은 PRD §6.4가 `stageMasterFilter`를 Phase 1 튜닝에서 명시적으로 제외하므로 Skill로 라우팅하지 않는 유일한 클러스터다 — 직접 인라인 응답.

---

## §4. 안전 규칙 — TS-1 ~ TS-5 (estimate: 12 줄, source: PRD §5.5 / TS-1..TS-5 + TS-2a 백업 라이프사이클)

**(spec)** — "## Safety Rules (TS-1 ~ TS-5)" 아래의 verbatim 블록 — 순서는 PRD §5.5와 일치:

```
## Safety Rules (TS-1 ~ TS-5) — non-negotiable

[TS-1] 변경 대상은 Python 모듈의 `Final` 타입 상수 값만. 필터 로직 코드(조건문, 루프 등)는 수정하지 않는다. **예외**: Stage 5(financeFilter)는 현재 `Final` 상수가 없으므로 Phase 1에서 튜닝 불가 (§5.1 Stage 5 참조). [Stage 5 안내 문구: "현재 코드 구조상 변경 불가. Phase 2 검토"]
[TS-2] 모든 변경 전 백업: `cp {file} {file}.bak.$(date +%Y%m%d_%H%M%S)`. 백업 경로를 `screener_state.json.current_backup_files`에 기록.
[TS-2a] 동일 파일 백업은 최근 5개만 유지. 6번째 생성 시 가장 오래된 백업을 삭제 (단, tuning-log.md에 해당 설정이 기록되어 있는지 확인 후).
[TS-3] 변경 전 범위 검증: (a) tolerance 0.00~0.50, (b) ratio/threshold 0.0~1.0, (c) 정수 임계값 1~16, (d) 밴드 상/하한은 각 파라미터의 논리적 범위. 범위 밖 → 경고 + 사용자 확인.
[TS-4] 한 번에 한 파라미터만 변경 권장. 복수 변경 요청 시 "여러 파라미터 동시 변경 시 어느 변경의 효과인지 분리 불가" 경고 → 사용자 명시적 승인 후에만 순차 진행.
[TS-5] 변경 후 반드시 재필터 실행 제안. [사용자 안내 문구: "변경 적용됐습니다. 필터를 다시 돌려볼까요?" → RERUN_FILTERS 의도로 분기]
```

**근거**: PRD §5.5에서 verbatim. TS-2 단독으로는 무제한 디스크 증가가 발생하므로(R-13) TS-2a를 포함. 오류 처리와 Skill 파일이 정확한 규칙을 인용할 수 있도록 모든 규칙에 `[TS-N]` 접두를 부착.

---

## §5. 오류 분류 테이블 (estimate: 15 줄, source: Step 1 error-patterns.md §Full Error Inventory + Step 4 OQ-3 / ADR-011 + PRD §B-4)

**(spec)** — verbatim 블록. 디스패치 아키텍처에 대한 필수 코멘트와 PRD 검증 §7에 따른 "기술 정보:" 라벨에 유의:

```
## Error Classification

> **분기 기준 (필수)**: `type(exc).__name__` STRING 비교. `isinstance(exc, KiwoomApiError)`는 절대 사용 금지 — `KiwoomApiError`는 8개 모듈에 독립 정의된 동명 클래스이므로 어느 한 import로 catch하면 7개를 놓친다. (ADR-011)
> **출력 패턴**: 한국어 한 문장 요약 + 원인 + 사용자 행동. raw stderr / exit code / traceback은 "기술 정보:" 라벨로 접어서 부착.

| `type(exc).__name__` | 한국어 요약 | 원인 | 사용자 행동 |
|---|---|---|---|
| `KiwoomAuthError`       | 키움 인증에 실패했습니다.                | OAuth 토큰 발급/검증 실패                                   | APP_KEY·SECRET_KEY 설정을 확인하고, 잠시 후 다시 시도해주세요. |
| `KiwoomApiError`        | 키움 데이터 조회에 실패했습니다.         | REST API 호출 실패 (HTTP, JSON, return_code≠0, 재시도 초과). **8개 모듈 독립 정의 — 이름 기준 분기 필수.** | 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. |
| `KiwoomConditionError`  | 조건검색 서버 응답에 실패했습니다.       | WebSocket LOGIN/transport/return_code≠0/MISSING/SHAPE        | 설정한 조건명이 키움 HTS에 저장되어 있는지 확인해주세요. |
| `OrganizeError`         | 수집된 종목 데이터가 없습니다.           | conditionResearch.md·upperLowerPrice.md 두 입력 모두 부재    | 조건검색·상하한가 수집을 먼저 실행해주세요. |
| `ResearchError`         | 필터링에 필요한 데이터 파일이 없습니다.  | organizedCompany.md 또는 prefetchManifest.json 부재         | 먼저 데이터 수집(prefetch)을 실행해주세요. |
| `PrefetchError`         | 종목 사전 수집을 시작할 데이터가 없습니다. | Stage 0 prefetch 진입 전 organizedCompany.md 부재          | 조건검색·상하한가 단계를 먼저 완료해주세요. |
| `FileNotFoundError`     | 필요한 데이터 파일을 찾을 수 없습니다.   | 보고서 폴더·종목 폴더·chart/finance/investor.md 부재         | 먼저 해당 단계의 데이터 수집을 실행해주세요. |
| `ValueError`            | 데이터 형식이 올바르지 않습니다.         | 시계열 표 파싱 실패, 잘못된 인자                            | 수집된 데이터가 손상되었을 수 있으니 다시 수집해보세요. |
| `Exception` (generic)   | 예기치 못한 오류가 발생했습니다.         | 분류되지 않은 모든 예외                                     | 잠시 후 다시 시도하거나 로그를 확인해주세요. |

> **래핑 노트**: `httpx.HTTPError`(ConnectError/TimeoutException 포함) → 자동으로 `KiwoomApiError(code="HTTP")` 또는 `KiwoomAuthError`로 래핑되어 사용자에게는 위 9종 표면 클래스만 노출됨. `asyncio.TimeoutError`·`ConnectionClosed` → `KiwoomConditionError(code="LOGIN_TIMEOUT"|"WS")`로 래핑됨.
> **Exit code 1차 분류**: `1` = 도메인 입력 부재(OrganizeError/ResearchError/PrefetchError), `2` = 그 외 모든 예외.
```

**근거**: Step 1 §Architectural Notes #4에 따르면 9개 행이 사용자 노출 오류 표면의 99% 이상을 커버한다. 한국어 메시지는 Step 1 오류 인벤토리에서 verbatim. ADR-011 / OQ-3에 따라 이름 기반 디스패치를 아키텍처 규칙으로 강제. PRD §B-4 "접힌 상세" 패턴은 "기술 정보:" 라벨로 구현.

---

## §6. 출력 포맷 규칙 (estimate: 10 줄, source: PRD §7.3 + FR-8.2/8.3 + B-23 + Step 1 §Korean Message Style Guide)

**(spec)** — "## Output Format Rules" 아래의 verbatim 블록:

```
## Output Format Rules

- **숫자 표기 (한국식)**: 천단위 콤마 + 단위 한국어. 예: `4,805원`, `-3.5%`, `0.965배`, `5,234회`, `1,234억원`, `15/350개`, `82개 → 45개`.
- **표현 정책 (FR-8.2/8.3, B-23)**:
  - (O) `"기술적 완성도가 높은 종목"`, `"필터 조건을 충족한 종목"`, `"선별 결과"`, `"5-Stage 통과"`
  - (X) `"매수 추천"`, `"이 종목을 사세요"`, `"유망 종목"`, `"상승 예측"`, `"이익 보장"`
- **면책조항 (B-23)**: 세션 첫 번째 결과 출력 시 풀버전 1회 — `"⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다."` 이후 동일 세션 내 결과 출력에는 1줄 축약 — `"(투자판단·책임은 본인에게 있습니다)"`. 파라미터 조회·에러 메시지·시스템 상태 보고에는 면책 불필요.
- **기술 정보 라벨**: 영어 stderr, exit code, traceback, Python 예외명 등은 사용자 메시지 본문에 노출하지 않고 `기술 정보:` 라벨로 접어서 부착. 한국어 요약이 항상 본문 첫 줄.
- **Jargon 금지** (Step 1 §Style Guide (d)): `return_code`, `HTTPError`, `JSON 스키마`, `ka10171`, `stage_idx` 같은 기술 잔재 노출 금지. "조건검색 서버", "수집 단계", "데이터 파일" 같은 상위 개념어로 치환.
```

**근거**: 4개 예시가 PRD §7.3가 강제하는 3가지 숫자 표기 형식을 커버. O/X 표현 정책은 FR-8.2/8.3에서 verbatim. B-23에 따라 2-상태 면책조항(풀버전 vs 축약). "기술 정보:" 라벨은 한국어 전용 규칙을 위반하지 않고 raw 에러 출력을 위한 깔끔한 구조적 탈출구를 제공한다.

---

## §7. 날짜 해석 (estimate: 5 줄, source: workflow-idea B-15 + PRD FR-1.2)

**(spec)** — "## Date Interpretation" 아래의 verbatim 블록:

```
## Date Interpretation (KST)

- `오늘`               → `$(date +%Y%m%d)` (KST 기준)
- `어제`               → 이전 영업일 (주말은 건너뜀, 공휴일 하드코딩 없음 — 디렉터리 존재로 보정)
- `이번 주 X요일` / `지난주 금요일` → 해당 요일의 YYYYMMDD 산출 후 한국어 확인 ("2026-05-29(금) 맞으신가요?")
- `이번 주 전부` / `이번 주 월~금` → 오늘 이하의 영업일 목록 → SCAN_RANGE
- **유효성 검사**: SHOW_RESULTS / WHY_REJECTED 등 결과 조회 요청 시 `test -d ${KRT_REPORTS}/{YYYYMMDD}` 선행. 미존재 → "{date} 결과가 없습니다. 스캔을 먼저 실행할까요?" + SCAN_TODAY/SCAN_RANGE 제안.
```

**근거**: 디렉터리 존재 검사로 한국 공휴일 하드코딩 필요성을 제거(B-15 트레이드오프 명시). "이번 주 금요일" 같은 요일명은 PRD P4 한 번 확인 원칙에 따라 한국어 확인 한 번으로 모호함을 제거.

---

## §8. 온보딩 플로우 (estimate: 10 줄, source: workflow-idea B-25 + B-12 완화책 + Step 4 §5 사전 점검 (a)-(c))

**(spec)** — "## Onboarding Flow" 아래의 verbatim 블록:

```
## Onboarding Flow

세션 시작 시:
1. **Pre-flight (a)(b)(c) 자동 실행** (Step 4 §5):
   - (a) `test -d ${KRT_ROOT}` → 미존재 시 AskUserQuestion으로 절대 경로 재확인
   - (b) `[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version` → 실패 시 한국어 안내 + 실행 차단
   - (c) `test -w ${KRT_REPORTS}` → 실패 시 권한·디스크 확인 안내
2. **`screener_state.json` 존재 여부로 분기**:

**(신규 사용자 — screener_state.json 부재)**:
- 기능 소개 3줄 (Korean): (i) "오늘 종목 스캔해줘"로 5-Stage 필터링 실행, (ii) "Stage 1 조건 보여줘"로 파라미터 조회, (iii) "OO전자 왜 빠졌어?"로 탈락 분석.
- 안내된 첫 실행 제안: `"오늘 한 번 스캔해볼까요? (약 10-15분 소요됩니다.)"`
- 첫 스캔 완료 후 결과 해석 가이드 1회 출력 (Stage별 통과 수 표 + 1-2개 종목 예시 해석).

**(재방문 사용자 — screener_state.json 존재)**:
- `last_scan_date`, `last_param_changes` 읽어 2-3줄 한국어 세션 요약:
  `"지난 스캔: {last_scan_date}. 변경 이력: {N}건 ({param} 등). 무엇을 도와드릴까요?"`
- 외부 변경 감지(아래 §10 참조)가 트리거되면 세션 요약 직후 경고를 함께 표시.
```

**근거**: B-25 신규/재방문 분기 명시. 사전 점검 (a)-(c)는 모든 세션 시작 시 실행되므로 인라인 처리. (d)(e)는 Skill 수준 호출 시점으로 이월(Step 4 §5 타이밍 다이어그램). 기능 소개는 workflow-idea B-25 핵심에 따라 3줄로 유지.

---

## §9. 실행 템플릿 (estimate: 4 줄, source: Step 4 §6 + ADR-007 + ADR-012)

**(spec)** — "## Execution Template" 아래의 verbatim 블록:

```
## Execution Template

EXEC_PATTERN: `cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}`
- `run_full_research_flow`, `run_prefetch` → **반드시 Bash(run_in_background:true)** (10-15+ min, 600s Bash cap 초과 — ADR-012). 백그라운드 시작 즉시 한국어 안내 "약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다." + 완료 알림 4-step 핸들러 (count → stderr → classify → Korean report) + 30분 timeout watchdog → "SCAN_SEPARATED 모드로 다시 시도하시겠습니까?".
- `run_filters`, `Filter_condition_update`, 개별 filter 모듈 → 동기 실행 (전형적 < 3분, foreground 가능).
- 절대 금지: `source .venv/bin/activate && python …` 형태 (D-7 — 쉘 상태 비의존성). `.venv/bin/python` 직접 호출만 허용.
```

**근거**: ADR-012 백그라운드 의무는 운영상 가장 결정적인 단일 라인이다 — 이것이 없으면 풀-플로우 스캔이 10분 후 조용히 실패한다. D-7 venv 직접 경로 규칙은 미묘한 PATH/활성화 버그를 방지한다.

---

## §10. 세션 연속성 (estimate: 7 줄, source: workflow-idea B-12 + Step 4 §4 스키마 + ADR-007)

**(spec)** — "## Session Continuity" 아래의 verbatim 블록:

```
## Session Continuity (screener_state.json)

- **경로**: `${KRT_REPORTS}/screener_state.json`. 부재 시 신규 사용자로 간주 (§8).
- **세션 시작 읽기**: `json.load` → `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`.
- **외부 변경 감지 (B-12 완화 메커니즘)**: `last_param_changes`의 각 항목 중 `confirmed=false` 인 것마다, 기록된 `file`에서 `grep -n '{param}.*Final' {file}`로 현재 값을 추출하여 `new`와 비교. 불일치 시 한국어 경고:
  `"⚠️ 외부에서 파라미터가 변경된 것으로 보입니다: {param} = {actual} (기록: {recorded})"`
  사용자 선택: (a) 현재 값을 새 baseline으로 수용 (screener_state 갱신), (b) `*.bak.*` 백업에서 복원.
- **JSON 손상 처리**: `json.JSONDecodeError` 캐치 → 손상 파일 `screener_state.json.corrupt.{ts}`로 백업 후, 신규 사용자 흐름으로 fallback.
- **세션 종료/Edit 완료 시 쓰기**: atomic write — `json.dump(state, tmp); mv tmp final`. Claude Code 단일 스레드 가정으로 잠금 불필요 (Step 4 §4 atomicity 노트).
- **CONFIRM 처리**: 사용자가 "이걸로 확정" → 가장 최근 매칭 `last_param_changes` 항목의 `confirmed=true` 갱신 + tuning-log.md 마지막 행 `✓ 확정` 마킹.
```

**근거**: B-12 외부 변경 감지 알람 문자열은 verbatim (workflow.md line 219). Step 4 §4에 따라 tmp+mv를 통한 atomic write. R-7(Step 4 §10)에 따라 손상 상태 폴백 처리.

---

## §11. 길이 추정 요약

| § | 섹션 | 추정 줄 수 |
|---|---|---|
| 1 | 헤더 | 3 |
| 2 | 경로 상수 | 8 |
| 3 | 의도 클러스터 라우팅 테이블 | 30 |
| 4 | 안전 규칙 TS-1..TS-5 | 12 |
| 5 | 오류 분류 테이블 | 15 |
| 6 | 출력 포맷 규칙 | 10 |
| 7 | 날짜 해석 | 5 |
| 8 | 온보딩 플로우 | 10 |
| 9 | 실행 템플릿 | 4 |
| 10 | 세션 연속성 | 7 |
|   | **총 추정** | **104** |

목표 범위: **80-130 줄**. 추정 **104** — 범위 내. **압축 불필요.**

**수정된 추정이 130을 초과할 경우** (예: Step 8 빌더가 한국어 표현으로 행 수가 부풀어 오르는 경우): workflow.md §5 Failure Recovery line 227의 압축 정책 적용:
- **§6 출력 포맷 규칙**을 **§4 안전 규칙**에 병합 (둘 다 출력 가드)
- **§7 날짜 해석**을 §3의 SCAN_TODAY/SCAN_RANGE 행에 인라인으로 압축

이 두 가지 병합으로 약 10-12줄을 절약하면서 모든 spec 콘텐츠를 보존한다.

---

## §12. 검증 자체 점검

- [x] **(spec)** + **(source)** + **(estimate)** + 근거를 모두 갖춘 10개 필수 섹션 존재
- [x] §3 의도 테이블에 **12개 클러스터** 존재 (SCAN_TODAY, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, SHOW_PARAMS, CHANGE_PARAM, RERUN_FILTERS, RESTORE, COMPARE, THEORY_GUIDE, CONFIRM, ASK_MODULE) — B-3 verbatim 목록과 일치 (workflow.md line 198)
- [x] 각 클러스터마다 **≥2개 한국어 발화 예시** 존재 (대부분 3-4개)
- [x] 모든 클러스터가 특정 Skill(`stock-scan` / `filter-tune` / 인라인) + 액션 이름에 매핑됨
- [x] 혼합 의도 규칙이 §3에 명시됨 ("필터 바꾸고 다시 돌려줘" → 순차 CHANGE_PARAM → RERUN_FILTERS)
- [x] PRD 안전 규칙 5개 **TS-1..TS-5** 모두 §4에 verbatim 존재 (추가로 TS-2a 백업 라이프사이클)
- [x] §5 오류 테이블이 Step 1 §Full Error Inventory와 일치하는 한국어 메시지로 **사용자 노출 오류 클래스 9종**을 커버
- [x] §5에서 **OQ-3 / ADR-011**을 명시적으로 강제: `type(exc).__name__` STRING 디스패치, `isinstance` 절대 사용 금지 — 아키텍처 규칙 코멘트로 등장
- [x] §5에서 `KiwoomApiError` 8개 모듈 독립성을 아키텍처적 사실로 문서화
- [x] §6의 숫자 포맷 예시 (`4,805원`, `-3.5%`, `0.965배`)가 PRD §7.3과 verbatim 일치
- [x] §6에 FR-8.2/8.3에 따른 O/X 표현 정책 포함
- [x] §6에 B-23에 따른 면책조항 축약 로직 (첫 번째는 풀버전, 이후는 1줄)
- [x] §8 온보딩이 B-25에 따라 **신규**(`screener_state.json` 부재) vs **재방문** 사용자를 구분
- [x] §7 날짜 해석이 B-15에 따라 `오늘` / `어제` / 요일명 / `이번 주`를 커버
- [x] §7 디렉터리 존재 유효성 검사로 한국 공휴일 하드코딩 필요성 제거
- [x] §10이 Step 4 §4에 따라 `screener_state.json` 스키마의 4개 필드 모두를 읽고 씀 (`last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`)
- [x] §10 외부 변경 경고 문자열은 workflow.md line 219에서 **verbatim**
- [x] §9가 ADR-012에 따라 풀-플로우 + prefetch에 대해 `run_in_background:true`를 의무화
- [x] §9가 D-7 / ADR-007에 따라 `source .venv/bin/activate`를 금지
- [x] 총 추정 최종 파일 줄 수: **104** — 80-130 범위 내
- [x] 블루프린트에 추정이 130을 초과할 경우의 장애 복구 압축 계획 포함

---

## §13. 출처 추적성 매트릭스

| 최종 파일 섹션 | PRD 앵커 | workflow-idea 앵커 | Step 산출물 앵커 |
|---|---|---|---|
| §1 헤더 | §1, §3 (사용자 페르소나) | B-1 (2-skill 구조) | — |
| §2 경로 상수 | §6.1 (경로) | B-6 (실행 템플릿) | Step 4 §1, §6; ADR-007 |
| §3 의도 라우팅 | FR-1..FR-7 (대화 패턴 §3) | B-3 (12 클러스터) | Step 4 §7 (SCAN_TODAY 트리); ADR-012 |
| §4 안전 규칙 | §5.5 TS-1..TS-5, TS-2a | B-7 (확정), B-8 (백업), B-9 (범위), B-17 (공유 상수) | — |
| §5 오류 테이블 | §B-4 (오류 래핑), §3 (영어 = 이탈) | B-4 (오류 테이블) | Step 1 §Full Error Inventory; Step 4 OQ-3 / ADR-011 |
| §6 출력 포맷 | §7.3, FR-8.2/8.3 | B-23 (면책 + 표현 정책) | Step 1 §Korean Message Style Guide |
| §7 날짜 해석 | FR-1.2, FR-1.3 | B-15 | — |
| §8 온보딩 | §3 (사용자 페르소나) | B-25 (온보딩), B-12 (상태) | Step 4 §5 (사전 점검 a-c) |
| §9 실행 템플릿 | §6.2 | B-6, B-11 (분할 모드) | Step 4 §6, §7; ADR-007, ADR-012 |
| §10 세션 연속성 | §3 (재방문 사용자) | B-12 | Step 4 §4 (스키마); R-7 손상 완화책 |

10개 섹션 모두 최소 1개의 PRD 앵커와 1개의 workflow-idea 앵커로 추적된다. §2, §5, §8, §9, §10은 추가로 Step 4 아키텍처(경로 검증, 스키마, ADR)를 인용한다.

---

## §14. Step 8 `@claude-md-builder` 핸드오프 지침

Step 8이 본 블루프린트를 읽을 때, 빌더는 반드시:

1. **순서**: 정확히 §1 → §2 → §3 → §4 → §5 → §6 → §7 → §8 → §9 → §10 순서로 섹션 출력. 재배열 금지.
2. **Verbatim 복사**: 모든 **(spec)** 블록을 — 이모지 경고(`⚠️`), 체크마크(`✓`), 인라인 코드 스팬, 한국어 표현 포함하여 — verbatim 복사. 의역 금지.
3. **경로 치환**: `${KRT_ROOT}` 등은 리터럴 shell-style 변수로 그대로 둠(사전 치환 금지). CLAUDE.md는 Claude Code가 읽어 Bash 호출 시 치환한다.
4. **줄 예산**: 출력 후 파일에 `wc -l` 실행. > 130이면 §11 압축 정책 적용(§6 → §4 병합, §7 인라인). < 80이면 어떤 **(spec)** 블록도 실수로 요약되지 않았는지 재확인.
5. **한국어 정확성**: 한국어 문장의 모든 공백 보존 (예: `한국어자연어로`가 아닌 `한국어 자연어로`). 모든 한글-로마자 경계 공백 보존.
6. **추가 섹션 금지**: 본 블루프린트가 명시하지 않은 섹션은 추가하지 말 것 ("Examples" 없음, "Glossary" 없음, "Troubleshooting" 없음). 블루프린트는 설계상 완전(exhaustive)하다.
7. **헤더 1행은 반드시**: `# 키움 REST API 종목 스크리너 — Claude Code 오케스트레이션 레이어`. 하이픈이 아닌 em-dash (`—`).

---

*블루프린트 완료. 구현은 Step 8(`@claude-md-builder`가 본 spec으로부터 `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md`를 작성)에서 수행한다.*
