---
type: audit-report
created: "2026-05-26T23:30:00+09:00"
target: "final-research.md"
scope: "원본 42개 파일 ↔ final-research.md 반영 완결성 감사"
verdict: "부분 반영 — 구조적 완결, 세부 누락 다수"
---

# 감사 보고서: final-research.md 반영 완결성

> 감사 대상: `/prompt/prd-research/final-research.md`
> 감사 기준: `/prompt/prd-research/` 내 42개 원본 파일 전체
> 감사 방법: 5개 병렬 에이전트가 42개 원본 파일을 전수 읽기 후, final-research.md와 항목별 대조

---

## A. 원본 ↔ final-research.md 반영 매핑 표

### A-0. 메타 파일

| # | 원본 파일 | 반영 여부 | 반영 위치 | 유형 |
|---|----------|----------|----------|------|
| 1 | `_index.yaml` | 부분 반영 | §0.2 표, §0.3 표 | **부분 반영** — key_outcomes 33개 항목 미반영, per-team branch 구조 미반영 |
| 2 | `README.md` | 부분 반영 | §0.2 표 "확장 규칙·네이밍 규약" 1줄 | **부분 반영** — append-only 정책, 수정 시 `_corrections/` 규칙, YAML frontmatter 필수 스키마, "later rounds override earlier rounds" 원칙 미반영 |

### A-1. Round 1 (일반 축)

| # | 원본 파일 | 반영 여부 | 반영 위치 | 유형 |
|---|----------|----------|----------|------|
| 3 | `round-01/_round-meta.yaml` | 부분 반영 | §0.3 표 | **부분 반영** — quality_verification 3층위(layer_1/2/3) 내용, execution method, total_duration_minutes(~27), assumption_axis rationale 미반영 |
| 4 | `T01-workflow-architect.md` | 부분 반영 | §2.1 Green Zone, §1.2 | **부분 반영** — DuckDB 4-table DDL 스키마, Capabilities Coverage 8항목 표(95%/90%/80%/80%/70%/40%/60%/95%), Hook 사용 테이블(5개 이벤트), Desktop Scheduled Tasks 상세, pykrx vs FDR 비교(per-date vs per-ticker) 누락 |
| 5 | `T02-scenario-explorer.md` | 부분 반영 | §1.1, §2.1 F1, §2.1 F7 | **부분 반영** — 16개 시나리오 전체 매트릭스(A1-A4, B1-B4, C1-C4, D1-D4) 누락. "기술적 완성도" 4개 구성 개념(바닥 다지기/매집 완성도/이평선 정배열/돌파 준비) 한국어 금융 정의 누락. Minervini/O'Neil/Weinstein 서적 참조 누락. Kiwoom HTS 영웅검색 상세 누락. Branch A/B 서비스 가능 시나리오 목록 누락 |
| 6 | `T03-operator-analyst.md` | 부분 반영 | §1.3, §5.2 Section 4 | **부분 반영** — Power User 페르소나 전체 누락. Power User must-haves(투명한 점수, YAML 설정, raw 데이터 접근, 재현 가능) 누락. 설치 인내 한도("3개 복붙 OK, 5개 한계, 텍스트 수정 불가") 누락. 최소 품질 기준("Top 20 중 70% 합리적") 누락. 일반 사용자 즉각 이탈 트리거 5개 중 일부 누락. 설치 현실 시나리오(Xcode 프롬프트, pip 권한 실패, "왜 안 돼?") 누락. Claude Code 기존 트레이딩 스킬(InvestSkill 등) 누락 |
| 7 | `T04-sustainability-strategist.md` | 부분 반영 | §2.1 F3, §5.2 Section 7 | **부분 반영** — Branch A/B 단계별 토큰 소비 상세(6단계/4단계 각 범위) 누락. 구독 플랜 비교 표(Pro/Max5x/Max20x 가격·프롬프트 수) 누락. 6개 토큰 최적화 전략(개별 절약률 포함) 누락. pykrx 12개월 내 60% 파손 확률 누락. 3개 Anti-Pattern 누락. Branch A 스케일링 한계 5항목 누락. Branch B 스케일링 경로 6항목 누락. CVE-2025-59536, CVE-2026-21852 보안 취약점 누락. DuckDB 1.4.0 AES-256-GCM 암호화 누락. KRX 2026 중반 거래 시간 12시간 연장 누락. Max 20x 19분 한도 도달 전례 누락. Config drift 위험 분석 누락 |
| 8 | `R1-S01-convergence.md` | 완전 반영 | §2.1 Green/Yellow/Red Zone | **완전 반영** — 7 Green, 4 Yellow, 5 Red 항목 + 4개 상충 해결 모두 반영 |
| 9 | `R1-S02-risk-register.md` | 부분 반영 | §2.1 TOP 5 위험, §5.2 Section 8 | **부분 반영** — TOP 5 위험은 반영. 그러나 S02의 통합 Parking Lot 30개 항목(T1-T8, E1-E7, U1-U4, R1-R8)은 대부분 누락. 특히 "PRD Decision at Risk" 칼럼(각 PL 항목이 어떤 PRD 결정을 위험에 빠뜨리는지) 완전 소실 |
| 10 | `R1-S03-key-findings.md` | 완전 반영 | §2.1 핵심 발견 8개 | **완전 반영** — F1-F8 모두 반영, 출처 태그 유지 |
| 11 | `R1-S04-prd-direction.md` | 부분 반영 | §5.2 전반 | **부분 반영** — "Two Engines, One Product" 프레이밍, 9개 PRD 섹션 구조, 7개 "탁월한 PRD" 품질 기준, 6개 후속 조사 필요 갭 → 이 중 품질 기준 7개와 섹션별 "Must include"/"Caution" 지침 상세 누락 |

### A-2. Round 2 (기술·이론 축)

| # | 원본 파일 | 반영 여부 | 반영 위치 | 유형 |
|---|----------|----------|----------|------|
| 12 | `round-02/_round-meta.yaml` | 부분 반영 | §0.3 표 | **부분 반영** — per-team 10개 branch 구조, total_tool_uses(98), total_duration(~40min), quality_verification 3층위 미반영 |
| 13 | `T01-platform-capability.md` | 부분 반영 | §2.2 F1, §5.2 Section 3 | **부분 반영** — Hook 이벤트 테이블(9개, cadence/matchers), 4 handler types(timeout 포함), Agent Teams 2026.2부터 실험적, worktree 지원 상세, Hook 미지원 이벤트 5개(OnTimer/OnSchedule/OnFileChange/OnError/OnNetworkRequest), Hook 런타임 패키지 설치 불가, Platform utilization ~85% 수치 누락 |
| 14 | `T02-configuration-architect.md` | 부분 반영 | §2.2 | **부분 반영** — "Precise Minimal" 접근법(7 files/3 Hooks), DuckDB 6-table 스키마, Hook 성능(~300ms Python startup × 20 Bash calls = 12s overhead), Phase 1/2/3 확장 로드맵 누락 |
| 15 | `T03-orchestration-engineer.md` | 부분 반영 | §2.2 F2, §4.1 | **부분 반영** — 4개 Silent Failure 시나리오 구체적 서술(0원 가격/1800개만 반환/5일 전 캐시/평균 30% 변화) 누락. "Category error" 프레이밍(결정론적 파이프라인에 에이전트 패턴 적용은 범주 오류) 누락. Lightweight Plus 접근법 ~150줄 상세 누락. pipeline_metrics/pipeline_runs DuckDB 테이블 스키마 누락. pykrx GitHub issues #276/#240/#151 누락 |
| 16 | `T04-integration-specialist.md` | 부분 반영 | §2.2 F4, §3.1 | **부분 반영** — 완전한 bootstrap.sh 스크립트 누락. FallbackProvider Python 클래스 누락. External validation link 형식(Naver Finance/TradingView URL 패턴) 누락. pykrx-openapi 12개월 API 키 유효기간 누락. FinanceDataReader 1,438 stars + JSONDecodeError 보고 누락. claude -p 불안정 보고 누락 |
| 17 | `T05-theory-foundation.md` | 부분 반영 | §2.2 서브스코어, §3.2 | **부분 반영** — 서브스코어 매핑 표는 반영. 그러나 각 서브스코어의 **세부 포인트 할당**(OBV 0-30pt, 상승/하락 비율 0-40pt, 수축 0-30pt 등) 누락. Minervini 8개 기준 정확한 수식 누락. Weinstein 단계별 점수 매핑(Stage 4→0-20, Stage 1 early→20-40 등) 누락. VCP 수축 깊이 예시(25%→15%→8%→3-4%) 누락. SMA 기울기 임계값(0.02) 누락. Unix philosophy 매핑 표 누락. Memory 분류(arXiv 2604.08224) 누락 |
| 18 | `T06-orchestration-pattern-analysis.md` | 부분 반영 | §2.3 오케스트레이션 7-1-4 | **부분 반영** — 7-1-4 결론과 중앙 집중 선택은 반영. 그러나 T06 자체가 `_round-meta.yaml`에 누락(메타데이터 갭). Agent spawn 의사코드 3개 시나리오, daily_scan_orchestration() ~80줄 의사코드, Distributed Agent 정의 3개(.claude/agents/), Gate 파일 JSON 사양, 통신 경로 공식(N*(N-1)/2), 머지 패턴 3개, 대안 가중치 구성 3개 누락 |
| 19 | `R2-S01-tech-discussion.md` | 부분 반영 | §2.2 기술 선택 합의, 명시적 배제 | **부분 반영** — 12개 기술의 합의 점수(0/5~5/5)가 final-research에서는 "5/5" 중심으로 축약. 3-4/5(Yellow: validation gates, circuit breaker, Reflexion)의 조건부 합의 상세 누락 |
| 20 | `R2-S02-scenarios.md` | 완전 반영 | §2.2 시나리오 선택 | **완전 반영** — Experimental/Pragmatic/Established 3개 시나리오 비교, Phase 전략 포함 |
| 21 | `R2-S03-key-findings.md` | 완전 반영 | §2.2 핵심 발견 9개 | **완전 반영** — F1-F9 모두 반영, Cross-Round Continuity 포함 |
| 22 | `R2-S04-prd-direction.md` | 부분 반영 | §5.2 전반 | **부분 반영** — 8개 PRD 섹션 방향은 반영. 아키텍처 다이어그램(ASCII) 누락. 비용 상세 표(Experimental/Pragmatic/Established 간 dependency/failure point/setup time 비교) 일부 누락 |

### A-3. Round 3 (코딩·구현 축)

| # | 원본 파일 | 반영 여부 | 반영 위치 | 유형 |
|---|----------|----------|----------|------|
| 23 | `round-03/_round-meta.yaml` | 부분 반영 | §0.3 표 | **부분 반영** — LOCAL-PARTIAL 3개 항목 구체 명시 반영, quality_verification 3층위 미반영 |
| 24 | `T01-workflow-script-architect.md` | 부분 반영 | §2.3 workflow.md 이중 성격 | **부분 반영** — 구체적 workflow.md 샘플(선언적/절차적 양쪽 전문) 누락. pandas-ta 함수 시그니처 11개(`ta.sma`, `ta.bbands`, `ta.obv` 등) 누락. Per-stage 적합성 분석(3:1 절차:선언) 상세 누락. 복잡도 분석 표(Writing difficulty/Orchestrator setup/Debugging difficulty) 누락. Circuit breaker 로직(3 retry, sleep(30*attempt), FDR 폴백) 누락 |
| 25 | `T02-agent-orchestration-coder.md` | 부분 반영 | §2.3 오케스트레이션 7-1-4 | **부분 반영** — 토큰 예산 분해(CLAUDE.md 5K + Pipeline 3K + summary 8K + Korean 5K + follow-up 4K = 25K) 누락. 통신 복잡도 공식(N*(N-1)/2) 누락. Agent Teams TeamCreate 예제 누락. 3개 머지 패턴 누락. 한국어 에러 메시지 예제 누락. daily_scan_orchestration() 의사코드 누락. Parking Lot 10개 중 상당수 미반영 |
| 26 | `T03-skills-hooks-developer.md` | 부분 반영 | §2.3 F3, §5.2 Section 4 | **부분 반영** — 토큰 비용 비교(General 1,750 vs Specific 500 tokens/scan) 누락. 4개 Specific 스킬 이름(stock-scanner, market-regime-detector, anomaly-flagger, korean-market-calendar) 누락. 5개 General 스킬 목록 + 배제 사유 누락. Anomaly 탐지 5개 규칙 상세(Volume-Price Divergence, Perfect Score Syndrome 등) 누락. 한국어 금융 용어 참조 12개 쌍 누락. 구체적 Hook Python 코드(check_data_freshness.py ~55줄, stock_session_init.py ~45줄, validate_pykrx_output.py ~55줄) 누락 |
| 27 | `T04-verification-quality-coder.md` | 부분 반영 | §2.3 4-Gate 검증 | **부분 반영** — Gate 구조와 FM-1~6 매트릭스는 반영. 그러나 INDICATOR_RANGES dict(17개 지표 min/max) 누락. 통계적 샘플링 근거(100 샘플, 99.4% 탐지 확률) 누락. Per-gate 비용 분석 표(줄 수/DuckDB 쿼리/실행 시간/토큰/오탐률) 누락. 구체적 검증 상수(MIN_NONZERO_RATIO=0.95, MAX_PRICE_KRW=10,000,000, MAX_DAY_OVER_DAY_DRIFT=15.0 등) 누락. pykrx GitHub issues #276/#240/#151 누락 |
| 28 | `T05-state-recovery-coder.md` | 부분 반영 | §2.3 파일 기반 상태 관리 | **부분 반영** — pipeline_state.json 필드와 PipelineLock은 반영. 그러나 FSM 11 States/18 Triggers 완전 열거 누락. 금지 전이 10쌍 누락. 이벤트 로그 스키마(sequence_id, duration_ms, guard_evaluated) 누락. 접근 패턴 표(6 actors × read/write) 누락. 5.1→5.2 마이그레이션 경로 누락. xxhash64 선택 근거(10GB/s, DuckDB 내장) 누락. SessionStart 훅 통합(get_pipeline_context()) 누락 |
| 29 | `R3-S01-spectral-positioning.md` | 완전 반영 | §2.3 5개 영역 스펙트럼 | **완전 반영** — 5개 %수치, 수렴 패턴, 4-관점 토론 결과 반영 |
| 30 | `R3-S02-implementation-scenarios.md` | 완전 반영 | §2.3 구현 시나리오 | **완전 반영** — A/B/C 시나리오 비교, 줄 수, FM 방어 범위 반영 |
| 31 | `R3-S03-key-findings.md` | 완전 반영 | §2.3 핵심 발견 10개 | **완전 반영** — F1-F10 모두 반영 |
| 32 | `R3-S04-prd-direction.md` | 완전 반영 | §5.2 전반 | **완전 반영** — PRD 섹션 매핑, 위험 등록부 5항목, 3층위 자기 검증 반영 |

### A-4. Round 4 (외부 연동 축)

| # | 원본 파일 | 반영 여부 | 반영 위치 | 유형 |
|---|----------|----------|----------|------|
| 33 | `round-04/_round-meta.yaml` | 부분 반영 | §0.3 표 | **부분 반영** — key_outcomes 12개 항목 중 상위 수준만, quality_verification 미반영 |
| 34 | `T01-mcp-server-specialist.md` | 부분 반영 | §2.4 F3, §3.4 | **부분 반영** — 4개 한국 주식 MCP 서버 이름은 반영. MCP 설정 JSON 3개 scope(Project/User/Local) 누락. FastMCP SDK 코드 예제 누락. 13개 아카이브 서버 상세 누락. Branch 1.1 vs 1.2 토큰 오버헤드(~8.7K vs ~2K) 비교 누락. Memory MCP 스톡 패턴 지속성 PL 항목 누락 |
| 35 | `T02-local-tool-integration-expert.md` | 부분 반영 | §2.4 F4 | **부분 반영** — Light 전략 승리는 반영. Apple Silicon 호환성 매트릭스(7 컴포넌트) 누락. 도구별 버전(Python 3.12.7, jq 1.7.1-apple, uv 0.10.12, ruff 0.15.14, sqlite3 3.51.0, curl 8.7.1, git 2.50.1) 누락. rsync/mktemp/diff/watchdog LOCAL-OK 항목 누락. DuckDB CLI ~30MB/fswatch ~1MB 설치 크기 누락 |
| 36 | `T03-api-service-connector.md` | 부분 반영 | §2.4 F2, §3.4 | **부분 반영** — LLM CLI 인증 개요는 반영. Codex CLI 3개 통합 패턴(Bash exec/plugin/openai-oauth proxy) 누락. Gemini CLI 통합 패턴(pipe/subagent wrapper/slash command) 누락. LM Studio LOCAL-OK 누락. LINE Notify/KakaoTalk kakaocli LOCAL-PARTIAL 누락. Claude Code Channels(research preview v2.1.80+) 누락. 구독 비용 상세 표(Claude $200 + ChatGPT $20 + Gemini $20 = $240) 누락 |
| 37 | `T04-data-flow-architect.md` | 부분 반영 | §2.4 F7, F8, §5.2 Section 6 | **부분 반영** — 배치 흐름 및 DuckDB 크기는 반영. 완전한 summary.md 예제(YAML frontmatter 11개 필드) 누락. 데이터 직렬화 표준 표(7개 데이터 타입) 누락. Phase 2+ 출력 디렉터리 구조(detail/{ticker}.md, archive/) 누락. Streaming 패턴 평가 표(5개 패턴) 누락. launchd 16:30 KST 트리거 시점 누락(T05의 18:00과 불일치 미해결) |
| 38 | `T05-reliability-fallback-engineer.md` | 부분 반영 | §2.4 전반 | **부분 반영** — 28개 장애 모드 총 수와 카테고리 합계는 반영. 그러나 28개 개별 모드(PK-1~9, DB-1~6, CC-1~6, NW-1~4, OS-1~5)의 전체 목록과 Silent 여부 누락. ExitCode enum 22개 코드+한국어 메시지 누락. fail_fast() 구현 ~120줄 누락. 알림 결정 매트릭스(5개 이벤트별 sound/urgency) 누락. DegradationLevel IntEnum(FULL~OFFLINE 6단계) 부분만 반영. collect_with_fallback() 구현 누락. 이중 형식 로깅(human .log + JSON .jsonl) 누락. DuckDB 건강 점검 + 복구 구현 누락. 복구 결정 매트릭스(12개 실패 유형) 누락. 체크포인트 기반 복구 시나리오 7개 누락. 27개 구체적 출처 URL 누락. **launchd 18:00 KST vs T04 16:30 KST 불일치 미해결** |
| 39 | `R4-S01-integration-spectrum.md` | 완전 반영 | §2.4 연동 스펙트럼 | **완전 반영** — 5개 축 포지셔닝, 합의/배제 항목 반영 |
| 40 | `R4-S02-discussion-scenarios.md` | 완전 반영 | §2.4 연동 시나리오 | **완전 반영** — Phase별 점진 확장, 4-관점 토론, Selective(B) 선택 반영 |
| 41 | `R4-S03-key-findings.md` | **왜곡** | §2.4 핵심 발견 10개 | **왜곡** — F10 "LOCAL-BLOCKED = 0" 주장이 원본 T03의 2개 LOCAL-BLOCKED(Naver Finance scraping, API-key LLM)와 충돌. 원본 합성(S03) 자체의 오류가 final-research에 전파 |
| 42 | `R4-S04-prd-direction.md` | 부분 반영 | §5.2 전반 | **부분 반영** — 대부분 반영. "What was not covered" 표(6항목: CI/CD, 모니터링 대시보드, 백업, 멀티유저, AI Agent SDK, 한국어 STT/TTS) 일부 final-research §6에 흡수 |

### A-5. 반영 유형 집계

| 유형 | 파일 수 | 비율 |
|------|--------|------|
| 완전 반영 | 10 | 23.8% |
| 부분 반영 | 31 | 73.8% |
| 왜곡 | 1 | 2.4% |
| 누락 | 0 | 0% |
| 출처 소실 | — | 아래 §B 참조 |

---

## B. 누락·왜곡·출처 소실 목록

### B-1. 사실 오류 / 왜곡 (CRITICAL)

| # | 항목 | 근거 | final-research.md 위치 |
|---|------|------|---------------------|
| **W1** | **LOCAL-BLOCKED 개수 왜곡** | final-research §3.5: "LOCAL-BLOCKED: **0개** (4라운드 연속)". 그러나 R4-T03-api-service-connector.md는 명시적으로 2개 LOCAL-BLOCKED 항목을 열거: (a) Naver Finance scraping (높은 유지보수, 법적 위험, 기술적 복잡도), (b) API-key-based LLM integration (구독 CLI 제약 위반). 이 오류는 R4-S03-F10 자체에 존재하며 final-research가 검증 없이 전파. | §3.5, §2.4 F10 |
| **W2** | **source_file_count 불일치** | frontmatter: `source_file_count: 37`. §0 서두: "37개 파일". 그러나 §0.2 표는 42개 항목을 나열하며 모두 ✅ 반영 표시. 실제 디렉터리 내 파일 수(final-research.md 제외)도 42개. 37은 어디에서도 일관된 계산이 안 됨. | frontmatter, §0 |
| **W3** | **pandas-ta 지표 수 불일치 미해결** | R1-T01: "192+ indicators". R2-T04: "130+ indicators". final-research §2.2: "130+ 지표". 두 원본의 수치 차이가 언급 없이 한쪽 수치만 채택. | §2.2 기술 선택 합의 표 |
| **W4** | **launchd 트리거 시점 불일치 미해결** | R4-T04: "16:30 KST". R4-T05 canonical: "18:00 KST". R1-T01: "18:30 daily". final-research는 어느 시점도 명시하지 않아 상충이 은폐됨. | §5.2 Section 4 |

### B-2. 구조적 누락 (HIGH — PRD 작성에 직접 영향)

| # | 누락 항목 | 원본 위치 | PRD 영향 | 비고 |
|---|----------|----------|---------|------|
| **M1** | **서브스코어 세부 포인트 할당 수식** — OBV 0-30pt, 상승/하락 비율 0-40pt 등 각 구성요소의 정확한 점수 변환 규칙 | R2-T05 §Breakout Readiness, Volume Behavior, Momentum | CRITICAL — §5.2 Section 2 "정확한 수식" 작성 불가 | 점수 방법론이 PRD의 지적 핵심이라 선언하면서 수식 상세를 누락 |
| **M2** | **Minervini SEPA 8개 기준 정확한 수식** — `close > SMA(50)`, `SMA(50) > SMA(150)`, 52주 저점×1.30, 52주 고점×0.75 등 | R2-T05 | CRITICAL — MA Alignment 서브스코어 구현 사양 | §2.2에 "8기준 Boolean 합산"만 기재, 수식 자체 없음 |
| **M3** | **Weinstein 4단계 점수 매핑** — Stage 4→0-20, Stage 1 early→20-40, Stage 1 late→40-60, 1→2 transition→60-80, Stage 2→80-100 | R2-T05 | HIGH — Base Formation 서브스코어 구현 사양 | |
| **M4** | **16개 시나리오 전체 매트릭스** — A1-A4(일일), B1-B4(심층), C1-C4(알림), D1-D4(고급). 빈도/복잡도/자동화/가치 평가 포함 | R1-T02 | HIGH — §5.2 Section 1 "문제 정의"에서 사용자 워크플로우 범위 설정 필요 | 상위 3개+비목표만 반영, 나머지 13개 소실 |
| **M5** | **R1-S02 Parking Lot 30개 항목** — "PRD Decision at Risk" 칼럼 포함. 각 PL 항목이 어떤 PRD 설계 결정에 위험을 주는지 명시 | R1-S02 | HIGH — PL 항목 간 우선순위 판단 근거 소실 | §4.3에 25개로 재편되며 상당수 "PRD 결정 위험" 연결 소실 |
| **M6** | **Power User 페르소나 및 요구사항** — 투명한 점수, YAML 설정, raw 데이터 접근, 재현 가능성, 이탈 트리거 4개 | R1-T03 | HIGH — 비기술 사용자만 타겟으로 설계하면 Power User 확장성 누락 | General User만 반영, Power User 완전 소실 |
| **M7** | **"기술적 완성도" 한국어 금융 개념 정의** — 바닥 다지기(베이스 완성), 매집 완성도(거래량 패턴), 이평선 정배열(가격 위치), 돌파 준비(VCP 패턴) | R1-T02 | HIGH — §1.1 "기술적 완성도는 표준 금융 용어가 아니다" 선언 후 정의를 구축하지 않음 | PRD에서 정의를 구축해야 한다고 선언했으나 원본의 정의 초안이 final-research에 없음 |
| **M8** | **28개 장애 모드 개별 목록** — PK-1~9, DB-1~6, CC-1~6, NW-1~4, OS-1~5 각각의 설명, Silent 여부, 대응 전략 | R4-T05 canonical | HIGH — §5.2 Section 5 "28개 장애 모드 카탈로그" 언급하면서 내용 없음 | 총 수와 카테고리 합계만 기재 |
| **M9** | **ExitCode enum 22개 + 한국어 에러 메시지** — SUCCESS=0부터 INTERNAL_ERROR=79까지 전체 코드와 한국어 메시지 | R4-T05 canonical | MEDIUM — §5.2 Section 4 에러 메시지 한국어화 구현 근거 | "ExitCode enum + EXIT_MESSAGES_KO" 언급만 |
| **M10** | **Anomaly 탐지 5개 규칙** — Volume-Price Divergence, Perfect Score Syndrome, Micro-Cap Trap, Stale Data, Single-Indicator Dominance | R3-T03 | MEDIUM — §5.2 Section 5 이상 탐지 구현 사양 | |

### B-3. 세부 누락 (MEDIUM — 유용하나 PRD 골격에는 비필수)

| # | 누락 항목 | 원본 위치 |
|---|----------|----------|
| M11 | 6개 토큰 최적화 전략 (개별 절약률 포함) | R1-T04 |
| M12 | pykrx 12개월 내 ~60% 파손 확률 | R1-T04 |
| M13 | 3개 Anti-Pattern (raw 데이터 로딩, Claude 계산기, Hook 비즈니스 로직) | R1-T04 |
| M14 | CVE-2025-59536, CVE-2026-21852 보안 취약점 | R1-T04 |
| M15 | 설치 인내 한도 ("3개 복붙 OK, 5개 한계, 텍스트 수정 불가") | R1-T03 |
| M16 | 최소 품질 기준 ("Top 20 중 70% 합리적") | R1-T03 |
| M17 | Hook 성능 오버헤드 (~300ms × 20 = 12s) | R2-T02 |
| M18 | 12개 한국어 금융 용어 쌍 | R3-T03 |
| M19 | DuckDB 6-table 스키마 vs 3-table 불일치 | R2-T02 vs R2-T04 |
| M20 | 구독 플랜 비교 표 (Pro/Max5x/Max20x 가격·프롬프트) | R1-T04 |
| M21 | Apple Silicon 호환성 매트릭스 (7 컴포넌트) | R4-T02 |
| M22 | FDR Top-200 선정 기준 미지정 (시가총액? 거래량?) | R4-T05 PL#2 |
| M23 | DuckDB 1.4.0 AES-256-GCM 암호화 | R1-T04 |
| M24 | KRX 거래 시간 12시간 연장 (2026 중반) | R1-T04 |
| M25 | Max 20x 19분 한도 도달 전례 (2026.3) | R1-T04 |
| M26 | Claude Code 기존 트레이딩 스킬 (InvestSkill 등) | R1-T03 |
| M27 | R1-S04 "탁월한 PRD" 7개 품질 기준 | R1-S04 |
| M28 | T06이 `_round-meta.yaml`에 미등재 (메타데이터 갭) | R2 meta |
| M29 | LM Studio LOCAL-OK | R4-T03 |
| M30 | 복구 결정 매트릭스 (12개 실패 유형별 전략·자동화·사용자 행동) | R4-T05 |

### B-4. 출처 소실

| # | 항목 | 설명 |
|---|------|------|
| **S1** | R1-S02 Parking Lot "PRD Decision at Risk" 칼럼 | 각 PL 항목이 어떤 PRD 결정을 위험에 빠뜨리는지의 매핑이 소실. final-research §4.3은 PL 항목만 나열하고 위험 연결 없음 |
| **S2** | R1-T02 서적 참조 | Minervini "Trade Like a Stock Market Wizard", O'Neil "How to Make Money in Stocks", Weinstein "Secrets for Profiting" — 점수 방법론의 학술적·실무적 근거 출처 |
| **S3** | R1-T02 한국 커뮤니티 출처 | 다음 카페 "부자아빠 주식학교", "상승하는 차트의 조건과 차트의 기본기" by 고짹짹 — "기술적 완성도" 개념의 한국 소매 투자 커뮤니티 기원 근거 |
| **S4** | R2-T03/T04/T05 pykrx GitHub issues | #276, #240, #151 — 침묵적 실패의 구체적 증거 문서 |
| **S5** | R4-T05 27개 출처 URL | 28개 장애 모드 카탈로그의 근거가 되는 공식 문서, GitHub 이슈, 기술 문서 링크 |
| **S6** | R2-T05 arXiv 논문 | 2604.08224 (Memory 분류), 2604.04853 (MemMachine) — 메모리 아키텍처 이론적 근거 |

---

## C. 감사 총평

### 판정: "구조적 완결, 세부 부정확" — **"완벽 반영" 아님**

#### 근거 요약

**1. 구조적 달성 (긍정적)**:
- 42개 원본 파일 중 완전 누락 = 0개. 모든 파일이 최소 1회 이상 참조됨.
- 4개 라운드의 Synthesis 문서(S01~S04, 총 16개)는 대부분 완전 반영(10/16 완전, 6/16 부분).
- 핵심 발견(F-번호 항목) 37개 중 36개 정확 반영, 1개 왜곡(R4-S03-F10 LOCAL-BLOCKED).
- 선택지 매트릭스(§3)는 모든 결정 항목에 LOCAL-* 태그와 출처를 유지.
- 상충 해결/미해결 분리(§4)가 정직하게 수행됨.

**2. 세부 실패 (부정적)**:
- **4개 사실 오류**(W1~W4): LOCAL-BLOCKED 개수, 파일 수, 지표 수, launchd 시점.
- **10개 구조적 누락**(M1~M10): PRD 작성에 직접 필요한 사양 수준 정보(서브스코어 수식, 장애 모드 전체 목록, 시나리오 매트릭스 등).
- **20개 세부 누락**(M11~M30): 유용하나 PRD 골격에는 비필수.
- **6개 출처 소실**(S1~S6): 서적 참조, GitHub 이슈, arXiv 논문 등 추적 가능한 근거 자료.
- Raw 파일의 Parking Lot 항목 대규모 유실: R1 ~40개→5개, R3 46개→15개, R4 ~35개→25개. 총 ~120개 원본 PL 항목 중 최종 25개만 잔존.

**3. "완벽 반영" 주장 자체에 대한 판정**:

final-research.md §통합 품질 검증에서 "37개 원본 파일 전체 ✅ 반영 완료, 누락 파일: 없음"이라 선언했으나, 이는 **"파일이 참조되었는지"만 확인한 것이지 "파일의 내용이 무손실 반영되었는지"를 확인한 것이 아님**. 31/42 파일이 "부분 반영"이며, 사실 오류 4건, 출처 소실 6건이 존재. "무손실 통합"이라는 §0 서두의 선언은 사실과 불일치.

#### PRD 작성 전 반드시 보정해야 할 항목 (우선순위순)

1. **W1 수정**: LOCAL-BLOCKED 2개 항목 명시 (Naver Finance, API-key LLM)
2. **W2 수정**: source_file_count를 42로 정정 또는 37의 계산 근거 명시
3. **M1+M2+M3 보충**: 6개 서브스코어 세부 포인트 할당 수식 (PRD Section 2의 핵심)
4. **M8 보충**: 28개 장애 모드 개별 목록 (PRD Section 5의 핵심)
5. **W3 해결**: pandas-ta 지표 수 192+ vs 130+ 불일치 해결
6. **W4 해결**: launchd 트리거 시점 16:30 vs 18:00 vs 18:30 불일치 해결
7. **M7 보충**: "기술적 완성도" 한국어 금융 개념 정의 (PRD Section 1-2의 전제)
8. **M6 보충**: Power User 페르소나 최소 요약 (확장성 근거)

---

## 📋 STEP COMPLETION REPORT

### 1. INSTRUCTIONS RECEIVED
- /prompt/prd-research/ 내 원본 파일 전수 식별
- 각 원본 항목의 final-research.md 내 반영 매핑
- 반영 유형 분류 (완전 반영 / 부분 반영 / 누락 / 왜곡 / 출처 소실)
- 3층위 품질 검증 (사실 확인 / 구조 분석 / 역방향 점검)
- 감사 보고서만 산출, final-research.md 수정 금지, PRD.md 작성 금지

### 2. FEATURES / TOOLS USED
- agent-teams / teammate: ✗ not used
- Agent Swarm / orchestrator: ✗ not used
- Sub-agents: ✓ 5 sub-agents spawned (4 round auditors + 1 meta auditor, parallel)
- Task Management System: ✗ not used
- fork: ✗ not used
- hooks: ✗ not used
- commands: ✗ not used
- skills: ✗ not used
- Task verification / TDD: ✗ not applicable
- Web search / fetch: ✗ not needed
- Source of Truth (SOT): ✗ not applicable (audit output)

### 3. DELIVERABLES PRODUCED
CREATED:
- `/prompt/prd-research/audit-report.md` (이 파일)
MODIFIED:
- (없음)
DELETED:
- (없음)

### 4. OBJECTIVE COMPLETION ASSESSMENT
- 원본 파일 전수 식별: ✅ DONE (42개 파일 식별, 5개 에이전트 전수 읽기)
- 반영 매핑: ✅ DONE (42개 파일 각각 매핑 완료)
- 반영 유형 분류: ✅ DONE (완전 10, 부분 31, 왜곡 1, 누락 0)
- 누락·왜곡·출처 소실 목록: ✅ DONE (W4 + M30 + S6 = 총 40개 항목)
- 3층위 품질 검증: ✅ DONE
- ABSOLUTE ANCHOR 준수: ✅ DONE (final-research.md 미수정, PRD.md 미생성)

Rate the overall completion: **95%** complete

Explain what was NOT completed:
- Round 1/2의 persisted output에서 일부 raw 파일(T01-T04) 내 모든 개별 Parking Lot 항목의 1:1 매핑까지는 시도했으나, ~120개 원본 PL 중 일부 항목의 정확한 흡수/배제 경로를 100% 추적하지 못함 (추적 가능 ~85%)

### 5. HONESTY FLAGS
- Did you skip any instruction because it was too complex? **NO**
- Did you make assumptions without explicit confirmation? **NO** — 5개 에이전트가 42개 파일을 직접 읽어 검증
- Did you produce placeholder/stub code instead of real implementation? **NO** — 감사 보고서 문서
- Did you hallucinate file contents you did not actually verify? **NO** — 모든 내용은 에이전트의 Read tool 결과 기반
- Did you run out of turns before completing the task? **NO**
- Is there anything the next step needs to know about the current state? **YES** — W1(LOCAL-BLOCKED 왜곡)과 M1-M3(서브스코어 수식 누락)은 PRD 작성 전 반드시 final-research.md에 보정 필요

### 6. NEXT STEP RISK
- W1(LOCAL-BLOCKED 개수 왜곡)을 보정하지 않으면 PRD가 "모든 선택지 로컬 실행 가능"이라는 잘못된 전제 위에 구축됨
- M1-M3(서브스코어 수식)을 보정하지 않으면 PRD Section 2(점수 방법론)를 "정확한 수식"으로 작성할 수 없어 PRD의 지적 핵심이 공백
- M8(28개 장애 모드)을 보정하지 않으면 PRD Section 5(신뢰성·검증)가 총 수만 언급하는 빈 섹션이 됨
- ~95개 Parking Lot 항목이 유실되었으므로, PRD 작성 시 원본 raw 파일의 PL 항목을 직접 참조해야 함
