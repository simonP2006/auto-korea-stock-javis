# Step 5 — CLAUDE.md Blueprint

> Generated: 2026-05-30
> Target file: `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md`
> Target size: 80-130 lines (compact but complete)
> Created by Step 8 `@claude-md-builder` from this blueprint
> Sources: PRD §FR-1..FR-8 + §TS-1..TS-5 + §7.3 + workflow-idea §B-3/§B-12/§B-15/§B-23/§B-25 + Step 1 error-patterns + Step 4 architecture (path constants, schema, OQ-1..OQ-4 / ADR-009..012)

## Blueprint Conventions

- **(spec)** = literal text/structure that Step 8 `@claude-md-builder` writes verbatim into the final CLAUDE.md
- **(source)** = traceability anchor (PRD FR-N / TS-N / §X.Y, workflow-idea B-N, Step output §N, ADR-N)
- **(estimate)** = approximate line count contributed to the final 80-130 line target

The blueprint itself can exceed 300 lines because it carries rationale, alternatives, and verification — none of which the final file inherits.

---

## §1. Header (estimate: 3 lines, source: PRD §1 한 줄 정의 + §1 구현 형태 + workflow-idea B-1 2-skill structure)

**(spec)** — verbatim block at the top of CLAUDE.md:

```
# 키움 REST API 종목 스크리너 — Claude Code 오케스트레이션 레이어
> 한국어 자연어로 종목 스크리닝 실행 및 5-Stage 필터 파라미터 튜닝을 지원합니다.
> Skills: `stock-scan` (실행·해석·탈락분석), `filter-tune` (파라미터 가시화·변경·복원)
```

**Rationale**: First three lines establish (a) system identity, (b) Korean-only persona, (c) the two-skill split (B-1). Skills referenced by name so that the routing table in §3 has a canonical destination.

---

## §2. Path Constants (estimate: 8 lines, source: Step 4 §1 + workflow.md Constants line 44 + ADR-007 venv lock + ADR-012 background mandate)

**(spec)** — verbatim block under "## Path Constants" heading:

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

**Rationale**: All 5 directory constants `PASS` per Step 4 §1 verification. `.venv/bin/python` (never `source .venv/bin/activate`) per ADR-007 / D-7. Background mandate per ADR-012 prevents Bash-tool 10-min timeout failure on full-flow scans.

---

## §3. Intent-Cluster Routing Table (estimate: 30 lines, source: workflow-idea B-3 + Step 4 §7 + PRD §3 대화 패턴 + ADR-012)

**(spec)** — Markdown table format, exactly 12 mandatory clusters from B-3 plus the mixed-intent rule (workflow.md verification line 198, line 207):

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

**Rationale**: All 12 clusters from B-3 verbatim. Mixed-intent rule explicit per workflow.md line 207. Each cluster maps to a single concrete action name that the corresponding Skill SKILL.md will implement (Step 9). `ASK_MODULE` is the only cluster that does NOT route to a Skill — it's a direct inline answer because PRD §6.4 explicitly excludes `stageMasterFilter` from Phase 1 tuning.

---

## §4. Safety Rules — TS-1 through TS-5 (estimate: 12 lines, source: PRD §5.5 / TS-1..TS-5 + TS-2a backup lifecycle)

**(spec)** — verbatim block under "## Safety Rules (TS-1 ~ TS-5)" — order matches PRD §5.5:

```
## Safety Rules (TS-1 ~ TS-5) — non-negotiable

[TS-1] 변경 대상은 Python 모듈의 `Final` 타입 상수 값만. 필터 로직 코드(조건문, 루프 등)는 수정하지 않는다. **예외**: Stage 5(financeFilter)는 현재 `Final` 상수가 없으므로 Phase 1에서 튜닝 불가 (§5.1 Stage 5 참조). [Stage 5 안내 문구: "현재 코드 구조상 변경 불가. Phase 2 검토"]
[TS-2] 모든 변경 전 백업: `cp {file} {file}.bak.$(date +%Y%m%d_%H%M%S)`. 백업 경로를 `screener_state.json.current_backup_files`에 기록.
[TS-2a] 동일 파일 백업은 최근 5개만 유지. 6번째 생성 시 가장 오래된 백업을 삭제 (단, tuning-log.md에 해당 설정이 기록되어 있는지 확인 후).
[TS-3] 변경 전 범위 검증: (a) tolerance 0.00~0.50, (b) ratio/threshold 0.0~1.0, (c) 정수 임계값 1~16, (d) 밴드 상/하한은 각 파라미터의 논리적 범위. 범위 밖 → 경고 + 사용자 확인.
[TS-4] 한 번에 한 파라미터만 변경 권장. 복수 변경 요청 시 "여러 파라미터 동시 변경 시 어느 변경의 효과인지 분리 불가" 경고 → 사용자 명시적 승인 후에만 순차 진행.
[TS-5] 변경 후 반드시 재필터 실행 제안. [사용자 안내 문구: "변경 적용됐습니다. 필터를 다시 돌려볼까요?" → RERUN_FILTERS 의도로 분기]
```

**Rationale**: Verbatim from PRD §5.5. TS-2a included because TS-2 alone causes unbounded disk growth (R-13). Every rule prefixed `[TS-N]` so error-handling and Skill files can cite the exact rule.

---

## §5. Error Classification Table (estimate: 15 lines, source: Step 1 error-patterns.md §Full Error Inventory + Step 4 OQ-3 / ADR-011 + PRD §B-4)

**(spec)** — verbatim block. Note the mandatory comment on dispatch architecture and the "기술 정보:" label per PRD verification §7:

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

**Rationale**: 9 rows covers > 99% of user-facing error surface per Step 1 §Architectural Notes #4. Korean messages are verbatim from Step 1 error inventory. Name-based dispatch enforced as architectural rule per ADR-011 / OQ-3. PRD §B-4 "접힌 상세" pattern realised via "기술 정보:" label.

---

## §6. Output Format Rules (estimate: 10 lines, source: PRD §7.3 + FR-8.2/8.3 + B-23 + Step 1 §Korean Message Style Guide)

**(spec)** — verbatim block under "## Output Format Rules":

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

**Rationale**: 4 examples cover the 3 number forms PRD §7.3 mandates. O/X 표현 정책 verbatim from FR-8.2/8.3. Two-state disclaimer (full vs abbreviated) per B-23. "기술 정보:" label provides clean structural escape for raw error output without violating Korean-only rule.

---

## §7. Date Interpretation (estimate: 5 lines, source: workflow-idea B-15 + PRD FR-1.2)

**(spec)** — verbatim block under "## Date Interpretation":

```
## Date Interpretation (KST)

- `오늘`               → `$(date +%Y%m%d)` (KST 기준)
- `어제`               → 이전 영업일 (주말은 건너뜀, 공휴일 하드코딩 없음 — 디렉터리 존재로 보정)
- `이번 주 X요일` / `지난주 금요일` → 해당 요일의 YYYYMMDD 산출 후 한국어 확인 ("2026-05-29(금) 맞으신가요?")
- `이번 주 전부` / `이번 주 월~금` → 오늘 이하의 영업일 목록 → SCAN_RANGE
- **유효성 검사**: SHOW_RESULTS / WHY_REJECTED 등 결과 조회 요청 시 `test -d ${KRT_REPORTS}/{YYYYMMDD}` 선행. 미존재 → "{date} 결과가 없습니다. 스캔을 먼저 실행할까요?" + SCAN_TODAY/SCAN_RANGE 제안.
```

**Rationale**: Directory-existence check obviates need for KR holiday hardcoding (B-15 트레이드오프 명시). "이번 주 금요일" 같은 weekday name은 한국어 확인 한 번으로 모호함 제거 (PRD P4 한 번 확인 원칙).

---

## §8. Onboarding Flow (estimate: 10 lines, source: workflow-idea B-25 + B-12 mitigation + Step 4 §5 pre-flight (a)-(c))

**(spec)** — verbatim block under "## Onboarding Flow":

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

**Rationale**: B-25 신규/재방문 분기 명시. Pre-flight (a)-(c) inline since they run every session start. (d)(e) deferred to Skill-level invocation (Step 4 §5 timing diagram). Capabilities intro stays to 3 lines per workflow-idea B-25 핵심.

---

## §9. Execution Template (estimate: 4 lines, source: Step 4 §6 + ADR-007 + ADR-012)

**(spec)** — verbatim block under "## Execution Template":

```
## Execution Template

EXEC_PATTERN: `cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}`
- `run_full_research_flow`, `run_prefetch` → **반드시 Bash(run_in_background:true)** (10-15+ min, 600s Bash cap 초과 — ADR-012). 백그라운드 시작 즉시 한국어 안내 "약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다." + 완료 알림 4-step 핸들러 (count → stderr → classify → Korean report) + 30분 timeout watchdog → "SCAN_SEPARATED 모드로 다시 시도하시겠습니까?".
- `run_filters`, `Filter_condition_update`, 개별 filter 모듈 → 동기 실행 (전형적 < 3분, foreground 가능).
- 절대 금지: `source .venv/bin/activate && python …` 형태 (D-7 — 쉘 상태 비의존성). `.venv/bin/python` 직접 호출만 허용.
```

**Rationale**: ADR-012 background mandate is the single most operationally critical line — without it the full-flow scan silently fails after 10 minutes. D-7 venv direct-path rule prevents subtle PATH/activation bugs.

---

## §10. Session Continuity (estimate: 7 lines, source: workflow-idea B-12 + Step 4 §4 schema + ADR-007)

**(spec)** — verbatim block under "## Session Continuity":

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

**Rationale**: B-12 외부 변경 감지 alarm string verbatim (workflow.md line 219). Atomic write via tmp+mv per Step 4 §4. Corrupt-state fallback per R-7 (Step 4 §10).

---

## §11. Length Estimate Summary

| § | Section | Est. lines |
|---|---|---|
| 1 | Header | 3 |
| 2 | Path Constants | 8 |
| 3 | Intent-Cluster Routing Table | 30 |
| 4 | Safety Rules TS-1..TS-5 | 12 |
| 5 | Error Classification Table | 15 |
| 6 | Output Format Rules | 10 |
| 7 | Date Interpretation | 5 |
| 8 | Onboarding Flow | 10 |
| 9 | Execution Template | 4 |
| 10 | Session Continuity | 7 |
|   | **Total estimate** | **104** |

Target band: **80-130 lines**. Estimate **104** — within range. **No compression required.**

**If revised estimate > 130** (e.g., Step 8 builder finds Korean phrasing inflates row count): apply compression policy from workflow.md §5 Failure Recovery line 227:
- merge **§6 Output Format Rules** into **§4 Safety Rules** (both are 출력 가드)
- compress **§7 Date Interpretation** inline into the SCAN_TODAY/SCAN_RANGE rows of §3

These two collapses save ~10-12 lines and preserve all spec content.

---

## §12. Verification Self-Check

- [x] All 10 mandatory sections present with **(spec)** + **(source)** + **(estimate)** + rationale
- [x] §3 Intent table has **12 clusters** (SCAN_TODAY, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, SHOW_PARAMS, CHANGE_PARAM, RERUN_FILTERS, RESTORE, COMPARE, THEORY_GUIDE, CONFIRM, ASK_MODULE) — matches B-3 verbatim list (workflow.md line 198)
- [x] Each cluster has **≥2 Korean utterance examples** (most have 3-4)
- [x] Every cluster maps to a specific Skill (`stock-scan` / `filter-tune` / inline) + action name
- [x] Mixed-intent rule explicit in §3 ("필터 바꾸고 다시 돌려줘" → sequential CHANGE_PARAM → RERUN_FILTERS)
- [x] All 5 PRD safety rules **TS-1..TS-5** present verbatim in §4 (plus TS-2a backup lifecycle)
- [x] §5 Error table covers **9 user-facing error classes** with Korean messages matching Step 1 §Full Error Inventory
- [x] §5 explicitly enforces **OQ-3 / ADR-011**: `type(exc).__name__` STRING dispatch, never `isinstance` — note appears as architectural rule comment
- [x] §5 documents `KiwoomApiError` 8-module independence as architectural fact
- [x] §6 number format examples (`4,805원`, `-3.5%`, `0.965배`) match PRD §7.3 verbatim
- [x] §6 includes O/X expression policy per FR-8.2/8.3
- [x] §6 disclaimer abbreviation logic per B-23 (full first time, 1-line thereafter)
- [x] §8 onboarding distinguishes **new** (no `screener_state.json`) vs **returning** user per B-25
- [x] §7 date interpretation covers `오늘` / `어제` / weekday names / `이번 주` per B-15
- [x] §7 directory-existence validity check obviates KR holiday hardcoding
- [x] §10 reads/writes all 4 fields of `screener_state.json` schema per Step 4 §4 (`last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`)
- [x] §10 external-change warning string is **verbatim** from workflow.md line 219
- [x] §9 mandates `run_in_background:true` for full-flow + prefetch per ADR-012
- [x] §9 forbids `source .venv/bin/activate` per D-7 / ADR-007
- [x] Total estimated final-file lines: **104** — within 80-130 band
- [x] Blueprint includes failure-recovery compression plan if estimate breaches 130

---

## §13. Source Traceability Matrix

| Final-file Section | PRD Anchor | workflow-idea Anchor | Step Output Anchor |
|---|---|---|---|
| §1 Header | §1, §3 (user persona) | B-1 (2-skill structure) | — |
| §2 Path Constants | §6.1 (paths) | B-6 (exec template) | Step 4 §1, §6; ADR-007 |
| §3 Intent Routing | FR-1..FR-7 (대화 패턴 §3) | B-3 (12 clusters) | Step 4 §7 (SCAN_TODAY tree); ADR-012 |
| §4 Safety Rules | §5.5 TS-1..TS-5, TS-2a | B-7 (confirm), B-8 (backup), B-9 (range), B-17 (shared const) | — |
| §5 Error Table | §B-4 (error wrapping), §3 (영어 = 이탈) | B-4 (error table) | Step 1 §Full Error Inventory; Step 4 OQ-3 / ADR-011 |
| §6 Output Format | §7.3, FR-8.2/8.3 | B-23 (disclaimer + expression policy) | Step 1 §Korean Message Style Guide |
| §7 Date Interp | FR-1.2, FR-1.3 | B-15 | — |
| §8 Onboarding | §3 (user persona) | B-25 (onboarding), B-12 (state) | Step 4 §5 (pre-flight a-c) |
| §9 Execution Template | §6.2 | B-6, B-11 (split mode) | Step 4 §6, §7; ADR-007, ADR-012 |
| §10 Session Continuity | §3 (returning user) | B-12 | Step 4 §4 (schema); R-7 corruption mitigation |

All 10 sections trace to at least one PRD anchor and one workflow-idea anchor. §2, §5, §8, §9, §10 additionally cite Step 4 architecture (path verification, schema, ADRs).

---

## §14. Step 8 `@claude-md-builder` Handoff Instructions

When Step 8 reads this blueprint, the builder MUST:

1. **Order**: emit sections §1 → §2 → §3 → §4 → §5 → §6 → §7 → §8 → §9 → §10 in that exact order. No re-ordering.
2. **Verbatim copy** every **(spec)** block — including emoji warnings (`⚠️`), checkmarks (`✓`), inline code spans, and Korean phrasing. No paraphrasing.
3. **Path substitution**: leave `${KRT_ROOT}` etc. as literal shell-style variables (not pre-substituted). CLAUDE.md is read by Claude Code which substitutes on Bash invocation.
4. **Line budget**: after emit, run `wc -l` on the file. If > 130, apply §11 compression policy (merge §6 → §4, inline §7). If < 80, double-check that no **(spec)** block was accidentally summarised.
5. **Korean correctness**: preserve all spacing in Korean sentences (e.g., `한국어 자연어로` not `한국어자연어로`). Preserve all hangul-roman boundary spaces.
6. **No additional sections**: do NOT add sections that this blueprint does not specify (no "Examples", no "Glossary", no "Troubleshooting"). The blueprint is exhaustive by design.
7. **Header line 1 must be**: `# 키움 REST API 종목 스크리너 — Claude Code 오케스트레이션 레이어`. Em-dash (`—`), not hyphen.

---

*Blueprint complete. Implementation occurs in Step 8 (`@claude-md-builder` writes `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md` from this spec).*
