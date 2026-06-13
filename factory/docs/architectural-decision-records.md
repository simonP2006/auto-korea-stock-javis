# Architectural Decision Records — Stock Filter Orchestration

## Format
Each ADR: Context → Decision → Alternatives → Rationale → Source

## Pre-Resolved Decisions (from workflow.md)

### ADR-001: Deploy to kiwoom-rest-trader
- Context: Where should CLAUDE.md + skills live?
- Decision: /Users/tajun/spJavis/kiwoom-rest-trader/
- Alternatives: (a) same dir [chosen], (b) separate orchestration repo
- Rationale: User opens Claude Code there; shortest path constants; .claude/ exists
- Source: workflow.md D-1

### ADR-002: SCAN_TODAY = run_full_research_flow
- Context: Default execution command for "오늘 종목 스캔해줘"
- Decision: run_full_research_flow (combined prefetch+filter)
- Alternatives: (a) combined [chosen], (b) separated by default
- Rationale: PRD FR-1.1; user says "나눠서 해줘" for separated
- Source: workflow.md D-2

### ADR-003: 2-Skill architecture
- Context: How many skills?
- Decision: stock-scan + filter-tune (2 skills)
- Alternatives: (a) 2 skills [chosen], (b) single mega-skill, (c) 3+ skills
- Rationale: Different interaction patterns (fire-and-forget vs iterative)
- Source: workflow.md D-3

### ADR-004: Parameter SOT = Python Final constants
- Context: Where is the canonical parameter value?
- Decision: Always Read actual Python code; documentation is reference only
- Alternatives: (a) code as SOT [chosen], (b) separate config file
- Rationale: Avoids sync issues; code is always truth
- Source: workflow.md D-4

### ADR-005: Session continuity via screener_state.json
- Context: How to persist session state across Claude Code sessions?
- Decision: JSON file at reports/screener_state.json, CLAUDE.md rule (no Hook dependency)
- Alternatives: (a) JSON file [chosen], (b) Hook-based, (c) memory system
- Rationale: kiwoom-rest-trader lacks AgenticWorkflow Hook infrastructure
- Source: workflow.md D-5

### ADR-006: English execution + bilingual output pair
- Context: What language for agent execution?
- Decision: English for agent thinking; @translator produces Korean per step
- Alternatives: (a) English + translation [chosen], (b) All Korean, (c) English only
- Rationale: AI performance maximization + user accessibility via @translator
- Source: workflow.md D-6

### ADR-007: .venv/bin/python execution template
- Context: How to run Python in kiwoom-rest-trader?
- Decision: cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}
- Alternatives: (a) .venv/bin/python [chosen], (b) source activate
- Rationale: Shell-state independent; avoids activate issues
- Source: workflow.md D-7

### ADR-008: Phase 2 transition criteria
- Context: When does Phase 1 end and Phase 2 begin?
- Decision: ALL of: (a) SC-1.1~SC-2.7 achieved, (b) 5+ tuning sessions, (c) 4 weeks no critical bugs
- Alternatives: (a) measurable criteria [chosen], (b) time-based, (c) user request
- Rationale: Concrete criteria prevent indefinite Phase 1
- Source: PRD §12

## Runtime Decisions
[Orchestrator appends here after Steps 4, 5, 6, 8, 9 as needed]

### ADR-009: gap value extraction strategy (FR-5.2)
- Context: `masterReference.log` records gap values as natural-language text, not structured fields. FR-5.2(a) requires impact estimation.
- Decision: Phase 1 — regex extraction over 5 dominant reason formats; Phase 2 — patch `Filter_condition_update.py` to append `[gap: actual=…, threshold=…, gap=…, unit=…]` suffix.
- Alternatives: (a) Phase-1 regex + Phase-2 patch [chosen], (b) immediate patch in Phase 1, (c) skip impact estimation entirely.
- Rationale: PG safety — defer modification to working production code; estimated precision sufficient for FR-5.2(a); fallback message available when extraction fails.
- Source: Step 4 OQ-1

### ADR-010: chart60_120Filter doc-drift (Type C 2.0% / Type D 60% stale strings)
- Context: `render_markdown()` at lines 866-870 contains stale string literals (live constants are 3.5% / 50%).
- Decision: Phase 1 — Skill-layer Korean caveat; Phase 2 — trivial PR to update string literals.
- Alternatives: (a) defer + caveat [chosen], (b) immediate fix.
- Rationale: PG safety — cosmetic only, math runs on live constants. Skill annotation costs zero code change.
- Source: Step 4 OQ-2

### ADR-011: KiwoomApiError dispatch
- Context: 8 independent class declarations of `KiwoomApiError` across kiwoom-rest-trader.
- Decision: filter-tune Skill error layer dispatches on `type(exc).__name__ == "KiwoomApiError"` (never `isinstance` against any single import).
- Alternatives: (a) name-based [chosen], (b) catch-all + reflection, (c) structural typing on `code`/`msg` attributes.
- Rationale: Defensive and explicit; survives future class consolidation refactors; matches Step 1 research recommendation.
- Source: Step 4 OQ-3

### ADR-012: SCAN_TODAY = run_full_research_flow with background execution mandate
- Context: D-2 default mode + 10-15+ min runtime vs 10-min Bash cap.
- Decision: `run_full_research_flow` is default; all long-running scans (full flow, prefetch) MUST use `Bash(run_in_background: true)` with 30-min timeout safeguard.
- Alternatives: (a) background mandate [chosen], (b) hybrid first-time/thereafter routing, (c) split mode as default.
- Rationale: Preserves PRD FR-1.1 contract; background notification eliminates timeout pressure; explicit `"나눠서 해줘"` trigger gives user control over split mode.
- Source: Step 4 OQ-4 (re-affirms D-2 + adds background mandate)

## Post-Build Decisions (제품 사용 모드)

### ADR-013: Start Routing — 자연어 "시작" → 사용 모드 진입 + Infrastructure Build 노출 차단
- Context: 빌드 완료 후, 자연어 "시작"으로 제품 사용을 개시할 단일 진입점이 없었다. 동시에 이 제품을 *생성한* Infrastructure Build(12단계 빌드 워크플로우)가 사용 모드 선택지에 어떤 경로로도 노출되어서는 안 된다.
- Decision: 라우터를 **제품 도메인(이 CLAUDE.md)에만** 둔다 — 의미 기반 "시작" 인식(키워드 박제 금지) → 스마트 라우터(의도 해석·분기) → 프로젝트 초기화(Pre-flight (a)(b)(c) + screener_state.json 로드) → 제품 사용 모드 진입 → 사용자 안내 모드(모드↔결과 메뉴 = Onboarding Flow 첫 화면). 프레임워크 repo(AgenticWorkflow `workflow-executor`)에는 라우터 코드를 추가하지 않는다.
- Alternatives: (a) 제품 repo 배치 [chosen], (b) 프레임워크 repo 통합 라우터 — 기각(workflow-executor 트리거 "user invokes / session begins / always first action"가 "시작"과 충돌, state.yaml `completed_degraded`는 `completed`가 아니므로 early-exit 없이 step-12로 재진입 → Infrastructure Build 노출; 빌드 SOT↔제품 SOT 혼선).
- Rationale: 두 도메인이 **별개 저장소**라는 사실이 가장 강한 모드 경계. 제품 라우터는 제품 SOT(`screener_state.json`)만 읽고/쓰며 빌드 SOT(`state.yaml`)를 건드리지 않음 → 절대 기준 2 보존. Infrastructure Build는 별도 repo·별도 엔트리·별도 SOT라 어떤 분기·플래그·경로로도 도달 불가(필터/조건 은닉이 아닌 구조적 모드 분리). "사용자 안내 모드"는 단순 UI가 아니라 라우팅의 일부이므로 임의 신설이 아닌 본 CLAUDE.md 스펙 + `screener_state.json`(신규/재방문 분기)에 명시. "시작"과 구체 Intent(SCAN_TODAY 등) 경합은 우선순위 규칙(구체 Intent 식별 시 직접 라우팅)으로 해소.
- Source: 사용자 승인 2026-05-31 (구현 전 3층위 설계 보고 후). 제품 도메인 결정 — 루트 프레임워크 `DECISION-LOG.md`와 별도 네임스페이스(AW 루트 ADR-055 참조).

### ADR-014: Start Routing 거장 채점 → 개선 적용 → 적대적 재채점 → 회귀 수정
- Context: ADR-013으로 구현된 Start Routing/Onboarding을 거장 5인×15기준으로 채점(86/100)하고 도출된 개선 5건(P1×2 + P2×3)을 제품 CLAUDE.md에 적용했다. 적용 후 종합 점수를 "86→92~94"로 **추론 추정**했으나, 추정은 검증이 아니므로 영향받은 7개 기준을 독립 적대적 검증기로 재채점했다.
- Decision: **추정을 신뢰하지 않고 재채점으로 닫는다.** 재채점 결과 추정이 반증되고(7기준 확정: Cooper 목표언어 6·Pearl 온보딩 6·Nielsen 상태 7·Norman 예측 7·Nielsen 인식 7·Pearl 의미인식 7·Parnas 완전성 8 — 두 기준은 개선 전보다 **하락**), 단일 회귀가 4기준을 끌어내린 원인이 식별되어 즉시 수정했다.
- Root cause & fix (전부 사용자-표면 텍스트/제어흐름, 불변식 안전):
  - **회귀**: P1-b가 `SCAN_SEPARATED` 안내 메뉴 행(CLAUDE.md L124)을 추가하며 `(prefetch)`·`"필터 미실행"` 기계 토큰을 사용자 화면에 누수 — P1-a가 L127에서 제거한 바로 그 excise 클래스 재개봉. → L124를 목표언어로 재서술.
  - **P2-1 토큰 충돌**: COMPARE_PARAMS 자동 라우팅 마커 집합(`"실험"`/`"이 세션"`/`"이번 달 튜닝"`)이 모호 예시 `"이번 세션 비교해줘"`의 `"세션"`과 겹쳐, silent default 금지 보증이 샘. → 자동 라우팅 마커를 **명시적 실험 마커(`"실험"`/`"튜닝 실험"`)만**으로 축소 + 결과 마커 열거 + `"세션"` 단독 silent 라우팅 금지 명문화(CLAUDE.md L30). **`stock-scan/SKILL.md:25`가 이 목록을 "verbatim"으로 미러링하므로 동일 수정을 짝지어 적용** — 둘만 고치면 한 결함을 CLAUDE.md↔skill 드리프트로 맞바꾸므로 verbatim 불변식 보존이 필수.
  - **P2-2 정지 비대칭**: Pre-flight all-pass 상태줄 게이트 `"(a)(b)(c) 모두 통과 시"`인데 (b)만 `실행 차단`을 명시 → (a)/(c) 실패 시에도 `"준비됨"` 출력 가능. → (a)/(c)에 명시적 차단 추가 + 게이트를 "실패 경로에서 항상 거짓"으로 강화(CLAUDE.md L112·L114·L115).
- 14번째 클러스터 & flight-recorder: P1-b로 `SCAN_SEPARATED`가 CLAUDE.md 라우팅 표에 노출되어 라이브 제품은 **14 클러스터**(stock-scan skill 트리거 표에는 본래 존재, CLAUDE.md에서 누락이던 것 → 패리티 회복). 빌드 산출물 `prompt/outputs/step-10·step-11`(+`.ko`)은 빌드 시점 "13/13"을 기록한 비행기록장치이므로 **수치를 덮어쓰지 않고 사후 부록 주석만 추가**(미수행 검증 위조 방지). 14번째는 스모크 테스트로 **미재검증** = 미결 항목.
- Alternatives: (a) 추정치 92~94를 확정 점수로 채택 — 기각(적대적 검증 없이 인플레이션 박제). (b) flight-recorder를 14/14로 덮어쓰기 — 기각(하지 않은 검증을 했다고 기록 위조, 절대 기준 정직 위배). (c) L30만 수정 — 기각(skill verbatim 드리프트 신설).
- Rationale: "추정은 검증이 아니다"를 운영 규범으로 확립. SOT/RLM 보존(②) — 제품 SOT `screener_state.json`(05-30 14:18) 미접촉, 빌드 SOT `state.yaml`(프레임워크 repo) 무관, RLM 미접촉, Infrastructure Build 노출 0(L58 불변), 라우팅 집합 폐쇄성 불변(마커 *축소*는 클러스터 추가 아님).
- 해소 (2026-05-31 후속 승인·실행): (1) **14번째 클러스터 스모크 재검증 완료** — SCAN_SEPARATED가 CLAUDE.md 라우팅 표 + stock-scan skill §1(Chain 2) 양쪽에 존재 → **14/14 일치, 드리프트 0**(양방향 검사). 원본 스모크 "13/13"은 CLAUDE.md→skill 단방향이라 stock-scan이 줄곧 보유하던 SCAN_SEPARATED↔CLAUDE.md 누락 드리프트를 놓쳤고, P1-b가 그것을 닫음. step-11 산출물 부록에 재검증 결과 기록. (2) **CLAUDE.md L80** Error-Classification 사용자-행동 컬럼 `데이터 수집(prefetch)` → `데이터 수집`으로 jargon 제거 완료.
- 확정 15기준 재채점 (2026-05-31, 5거장×3, 전부 적대적·라인근거): Parnas[완전성8·정보은닉9·모듈분해6] Norman[예측6·발견성7·강제기능6] Nielsen[상태7·인식6·오류예방6] Cooper[목표언어7·엑사이즈7·페르소나8] Pearl[의미인식7·온보딩6·확인공개7] → **103/150 = 68.7/100**. **비교 단서(필수)**: 원본 86은 *라우터/온보딩 한정* 채점이었고, 이 재채점은 원본 15기준 축자 정의 부재로 **재구성**되어 *제품 CLAUDE.md 전역*(에러표·TS 안전규칙·cross-skill 경계)까지 넓게 잡음 → 68.7은 86의 직접 후속치가 아니라 더 엄격·광범위한 그물. 드롭의 큰 부분은 **이번 세션 무관 기존 체계 결함**: P3 tuning-log SOLE-writer 위반(stock-scan이 `stocks_passed_after` cross-write — 절대기준2 위반), N3 TS-1~5 advisory(forcing 아님), Ni3 에러표 원인 컬럼이 L97 jargon 금지 자체 위반(`return_code≠0` 등).
- 계층 A 수정 완료 (2026-05-31, 사용자 "5-Stage 제외" 승인): (3) CONFIRM 안내 메뉴행 추가 → **14/14 메뉴 매핑**(메뉴 8행); (4) 메뉴 jargon `chart60Filter`(L130 말예시→"이 필터는 무슨 역할이야?")·`diff`(L129→"나란히 비교") 제거, **`5-Stage`는 제품 고유 기능명이라 유지**; (5) skill:25 "verbatim" 태그를 "마커 목록은 CLAUDE.md와 동일; 상세 분기·AUQ는 CLAUDE.md 정본"으로 정정. 백업 `CLAUDE.md.bak.20260531_193809`.
- 계층 B 진위 판별 완료 (2026-05-31, "수정 아닌 진위부터" 지시) — 적대적 패스가 심각도를 과장한 것으로 판정: **B-1** tuning-log SOLE-writer는 실재 문구 부정확성이나 **절대기준2 위반 아님**(단일스레드·순차 호출 → 동시성 0; `pending`→정수 채움은 의도된 2단계 프로토콜, race 아님) → minor 문서 정정 대상. **B-2** TS-1~5 advisory는 **결함 아님**, CLAUDE.md 프롬프트 거버넌스 레이어의 아키텍처 트레이드오프(강제하려면 제품 repo 코드/훅 레이어 필요 = 별도 엔지니어링). **B-3** 원인 컬럼 jargon은 L97 위반이 아니라 L72 **under-specification**(원인 컬럼=에이전트용 분류 스펙, 실제 표시는 L96-97 치환 지배; L72에 치환 명시 한 줄 부재) → minor 스펙 명료성. 결론: 68.7의 체계적 드롭 18점 중 상당분이 심각도 과장 + 아키텍처 특성의 결함화; 진짜 잔여는 소규모 문서·스펙 명료성 2건(B-1 문구·B-3 한 줄), B-2는 수정 불요.
- 계층 B 수정 완료 (2026-05-31, 사용자 (가) 승인): **B-1** tuning-log "SOLE writer" 주장 3곳(stock-scan SKILL.md:92·output-templates.md:177·execution-chains.md:273)을 "행 생성 owner; `stocks_passed_after` 칸만 RERUN_FILTERS 완료 시 stock-scan이 순차 채움 — 비동시 2단계"로 정정(filter-tune L199를 정본으로 일관화, 동작 미변경). filter-tune L445의 `screener_state.json` "단일 writer"는 정확하므로 미수정. **B-3** L72에 원인-칼럼 기술 토큰=분류 기준·표시 시 L96-97 치환 명시 한 줄 추가.
- **다중 에이전트 영향분석으로 판명(2026-05-31, 49 에이전트·39 적대검증)**: stock-scan→tuning-log cross-write는 **유령(phantom)** — Chain 8 실행 스텝(execution-chains.md L301-318)이 tuning-log를 전혀 안 씀, "cross-write" 주장은 산문 4곳(filter-tune L199·stock-scan L92·execution-chains L273·output-templates L177)에만 존재, tuning-log.md는 헤더만(0행, 미실행). ⟹ filter-tune은 **이미 사실상 유일 writer**; "two-writer 위반"은 명목 + 미구현 유령. **진짜 결함**은 `stocks_passed_after`가 `'pending'`으로 쓰이고 정수로 바꾸는 구현 경로가 없음(orphaned-pending gap). 직전 B-1 문구 수정("행 생성 owner; stock-scan 순차 채움")도 유령 동작 서술이었음 → Option B가 정정. 분석이 이전 solo 분석 5개 오류 적발(after-count는 researchedCompany.md/stage5_finance_passed.md에도 존재; scan_date 귀속키 존재; B는 견고성↔순수성 교환 아님 — 오히려 완전성 증가; 위반은 명목; workflow.md L291은 읽기 금지 아님).
- **Option B 구현 완료 (2026-05-31, 사용자 "제대로 고치기" 승인, markdown only — 코드/테스트/스키마 0)**: 12개 편집/5파일. ① 유령 산문 제거(순차 채움·행 생성 owner·비동시 2단계 전부) → filter-tune이 8칼럼 전부의 sole writer. ② filter-tune backfill 배선 3곳(L199 스키마 정의 + CONFIRM Branch 3 + COMPARE_EXPERIMENTS Step 4 read-time), 게이트=scan_date가 행 datetime 이후 rerun 증명 + 더 최근 pending 없음 + B-12 drift 통과, 미충족 시 pending 유지(거짓 추정 금지), rotation 전 sweep+미측정 동결. ③ found-but-pending 가드 3 reader(stock-scan SKILL L96·execution-chains L285 checkpoint·output-templates L177)→"재실행 필요" 렌더·정수 파싱 금지. ④ Chain 8 Step 6에 tuning-log 미작성·cross-write 금지 명시. 검증: 유령 0, sole writer 5곳, screener_state.json 미접촉(05-30 14:18)·스키마 4키 불변(rerun_history 0), 펜스 전부 짝수. 백업 `.claude/skills.bak.20260531_210355.tgz`. 점수 8/10(A3·owned-store4·read-resolve5 압도). SOT 강화. **가드레일 테스트 추가 완료**: `tests/orchestration/test_tuning_log_single_writer.py` (22 테스트 PASS — 유령 표현 재발 금지·cross-write 단어 금지문맥 한정·filter-tune sole writer·backfill 3곳+scan_date 게이트·found-but-pending 가드 3 reader·Chain 8 미작성·screener_state 스키마 불팽창). 잔여(선택): B-2(TS advisory 트레이드오프) ADR 명문화.
- Source: 사용자 승인 2026-05-31 ("1,2,3 모두 승인 — 재채점·문서동기화·ADR기록; 지금 수정 후 ADR 기록 / 부록 주석만 추가" 결정). 백업 `CLAUDE.md.bak.20260531_183746`. 제품 도메인 결정 — 별도 네임스페이스.
