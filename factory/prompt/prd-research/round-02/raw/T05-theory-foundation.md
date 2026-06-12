---
round: 2
type: raw
teammate: theory-foundation-expert
axis: theory-foundation
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
question_summary: "에이전틱 AI 이론(ReAct/CoT/ToT/Reflexion), 클래식 소프트웨어 공학 원칙, 기술적 분석 이론(Minervini/Weinstein/Wyckoff/IBD), 평가·벤치마킹 방법론을 분석하여 주식 분석 시스템의 이론적 기초 확립"
assumption_axis: "Modern Agentic Theory vs Established Automation Theory"
branch_a: "Modern Agentic Theory (최신 이론 — ReAct/CoT/ToT/Reflexion/Memory)"
branch_b: "Established Automation Theory (검증된 원칙 — Unix/ETL/FSM/Reliability/TA Theory)"
web_search_count: 19
local_execution_tags:
  LOCAL_OK: ["ReAct (built-in)", "CoT (built-in)", "Reflexion (monthly calibration)", "Memory via DuckDB", "Unix philosophy", "Separation of concerns", "Idempotency", "Fail-fast", "State machine", "ETL incremental", "Data quality gates", "Circuit breaker", "Graceful degradation", "Bulkhead", "Minervini SEPA/VCP", "Weinstein Stage Analysis", "Wyckoff Method", "IBD RS Rating", "Backtesting"]
  LOCAL_PARTIAL: ["Self-consistency (3x token cost)"]
  LOCAL_BLOCKED: ["ToT (token budget explosion)", "Multi-agent debate (impractical)", "RAG (unnecessary)", "Process Reward Models (training infra)"]
sources:
  - "Agentic Design Patterns 2026 (augmentcode.com)"
  - "Agentic AI Design Patterns: ReAct, Reflection & Tool Use (innovatrixinfotech.com)"
  - "AI Agentic Workflow Patterns 2026 (Medium)"
  - "Single-Agent vs Multi-Agent Systems (Medium)"
  - "Multi-Agent in Production 2026: What Actually Survived (Medium)"
  - "When Collaboration Fails: Adversarial Influence in Multi-Agent Debate (Nature 2026)"
  - "Chain of Thought Prompting Guide 2026 (orq.ai)"
  - "Tree of Thoughts: Deliberate Problem Solving (OpenReview)"
  - "Decreasing Value of Chain of Thought (Wharton)"
  - "Agent Self-Correction: From Reflexion to PRM (Zylos)"
  - "Externalization in LLM Agents: Memory Survey (arXiv 2604.08224)"
  - "MemMachine: Ground-Truth-Preserving Memory (arXiv 2604.04853)"
  - "Evaluation and Benchmarking of LLM Agents Survey (ACM)"
  - "Self-Consistency Prompting (Adaline)"
  - "Mark Minervini SEPA & VCP Complete Guide 2026 (finermarketpoints.com)"
  - "Minervini Trend Template Guide (ChartMill)"
  - "VCP Pattern Trading Guide 2026 (TradingSim)"
  - "Mastering VCP (TraderLion)"
  - "Stage Analysis Trading: Weinstein 4-Stage (AronGroups)"
  - "Complete Guide to Weinstein Stage Analysis (TraderLion)"
  - "Wyckoff Accumulation Pattern Guide (TrendSpider)"
  - "Wyckoff Method (Wyckoff Analytics)"
  - "IBD Style Relative Strength (GitHub/skyte)"
  - "Calculating IBD RS Rating with Python (Medium)"
  - "Circuit Breaker Pattern (System Design School)"
  - "Resilient Microservices Patterns (Design Gurus)"
  - "Scalable Pipelines Based on FSM (Medium)"
  - "ETL Best Practices 2026 (OneUptime)"
---

# T05: Theory Foundation Expert — Investigation Report

## Executive Summary

핵심 발견: 가장 가치 있는 현대적 에이전틱 패턴(ReAct, CoT)은 Claude Code에 이미 내장. 엔지니어링 가치는 추가 프레임워크가 아니라 Python ↔ Claude 간 인터페이스 설계에서 발생. 검증된 자동화 원칙(Unix 철학, 멱등성, Fail-Fast, 서킷 브레이커)이 시스템 신뢰성의 실제 기초. 기술적 분석 이론(Minervini/Weinstein/Wyckoff/IBD)은 6개 서브스코어의 지적 핵심.

---

## Branch 5.1: Modern Agentic Theory — Findings

### 1. ReAct (Reasoning + Acting) [LOCAL-OK]

**작동 원리** (Yao et al., 2023): 추론→행동→관찰 반복 루프. Claude Code의 도구 사용 루프가 **정확히 ReAct 패턴**.

**적용**: `/scan` 실행 시 Claude가 자연스럽게 (1) 데이터 신선도 추론 → (2) Python 실행 → (3) 결과 관찰 → (4) 해석 추론. 3-5 반복이면 충분.

**비용**: ReAct은 패턴당 가장 비쌈(각 추론 단계 = 1 LLM 호출). 일일 스캔 6단계 루프는 12K-28K 토큰 예산 내.

**판정**: 적용 가능하나 **이미 내장**. 별도 구현 불필요. 가치는 좋은 도구 인터페이스(summary.md 형식, DuckDB 쿼리 스크립트) 설계에서 발생.

### 2. CoT / ToT [LOCAL-OK / LOCAL-BLOCKED]

**CoT** (Wei 2022): 단계적 추론. Claude가 종목 해석 시 자연 발생. 2025-2026 Wharton 연구에 따르면 모델 능력 향상으로 명시적 CoT 가치 감소 중. **비용 0** (프롬프트 설계만).

**ToT** (Yao 2024): 분기 탐색 + 백트래킹. 2,500종목 × N개 분기 = **토큰 폭발**. 일일 배치에 **비실용적**.

**판정**: CoT는 출력 템플릿 설계로 활용. ToT는 스킵.

### 3. Multi-Agent Debate [LOCAL-BLOCKED]

**2025-2026 연구 결과 — 비판적**:
- Nature 2026 "에이전트가 진정으로 토론하는가?": 다수 압력에 순응할 뿐, 진정한 숙의 아님.
- Production 서베이(Medium, 2026.4): 1,600+ 실행 추적에서 14가지 실패 모드. "단일 에이전트 베이스라인이 동등 또는 우월."
- 실용적 팀 규모 상한: 3-4 에이전트.

**적용 평가**: 우리 점수 산출은 **결정론적 계산**(pandas-ta). LLM이 RSI를 계산하지 않음 — Python이 함. 멀티에이전트는 계산에 아무것도 추가하지 않음.

**판정**: 일일 배치에 **과잉**. 비용 2x, 가치 불비례. 예외: Phase 2에서 개별 종목 심층 분석 시 단일 에이전트 2-패스(강세/약세) 가능.

### 4. Reflexion [LOCAL-OK]

**작동 원리** (Shinn 2023): 과거 실패 반성 → 언어적 기억 저장 → 미래 성능 개선.

**적용 — 월간 교정 프로세스 (HIGH VALUE)**:
1. 80+ 점수 종목을 Day N에 기록
2. N+5, N+10, N+20일 가격 성과 추적
3. "80+ 점수 종목 중 20일 내 5%+ 상승 비율?" 분석
4. 가중치 조정 권고 생성

DuckDB에 성과 이력 저장. 월 1회 Python 스크립트 + Claude 해석.

**판정**: **고가치**. 실시간 에이전트 패턴이 아닌 주기적 교정 프로세스로 구현. 가중치가 "가설"이라는 인식(S03)에 직접 대응.

### 5. Memory Systems [LOCAL-OK]

**2026 분류** (arXiv 2604.08224): 단기(컨텍스트 윈도우), 장기 시맨틱(사실·일반화), 장기 에피소딕(시간 기록), 프로파일(사용자 선호).

**기존 아키텍처가 이미 충족**:
- 단기: Claude Code 컨텍스트 윈도우
- 시맨틱: DuckDB + CLAUDE.md
- 에피소딕: DuckDB daily_scores
- 프로파일: config.yaml
- 세션: `.claude/context-snapshots/`

**RAG 불필요**: 2,500종목 구조화된 데이터에 RAG 불필요. SQL 쿼리가 벡터 검색보다 빠르고 정확. RAG는 비구조화 지식 검색용 — 우리 시스템에 해당 없음.

### 6. Self-Consistency / Evaluation [LOCAL-PARTIAL / LOCAL-OK]

**자기 일관성**: N회 추론 → 다수결. 3x 토큰 비용. 일일 배치에 과잉, Phase 2 개별 종목 심층 분석에만 적용.

**백테스팅 (가장 중요한 평가)**: 과거 12개월 데이터로 전 종목 점수 산출 → 80+ 종목의 N+20일 수익률 추적 → 무작위 선택/KOSPI 지수/52주 신고가 스크리닝과 비교. **순수 계산, LLM 불필요**.

**판정**: 백테스팅은 **제품 신뢰성의 필수조건**. 출시 전 반드시 수행.

### Branch 5.1 결론

**실제 적용 (구현할 것)**:
1. ReAct: 이미 내장. 좋은 도구 인터페이스 설계.
2. CoT: 이미 내장. 구조화된 출력 템플릿 설계.
3. Reflexion (월간 교정): 높은 가치, 중간 복잡도.
4. Memory via DuckDB: 자연스러운 적합. 추가 프레임워크 불필요.
5. 백테스팅 평가: 출시 전 필수.

**학술적 흥미롭지만 비실용적**:
1. ToT: 배치에 토큰 비용 과다.
2. 멀티에이전트 토론: 단일 에이전트 동등 성능, 2x 비용.
3. 자기 일관성: Phase 2 심층 분석에만.
4. RAG: 구조화 데이터에 SQL이 우월.

---

## Branch 5.2: Established Automation Theory — Findings

### 1. Unix 철학 / 관심사 분리 [LOCAL-OK]

**직접 매핑**:

| Unix 도구 | 주식 시스템 대응 | 책임 |
|----------|---------------|------|
| `collect.py` | `cat` (데이터 소스) | pykrx → DuckDB OHLCV 수집 |
| `analyze.py` | `awk` (변환) | pandas-ta 지표 계산 |
| `score.py` | `sort`/`rank` (평가) | 6-컴포넌트 점수 공식 |
| `filter.py` | `grep` (필터) | 사용자 필터(시장, 섹터, 임계값) |
| `report.py` | `fmt` (포맷) | summary.md 생성 |

**3계층 아키텍처**: 데이터(DuckDB) / 로직(Python pandas-ta) / 프레젠테이션(Claude Code). **경계: summary.md**. "Claude가 계산하고, Python이 해석하는" 경계 침범 시 지속가능성 파괴.

**판정**: **필수** — 아키텍처 자체가 이 원칙.

### 2. 멱등성 (Idempotency) [LOCAL-OK]

같은 날 같은 시장 데이터로 파이프라인 재실행 → 동일 결과. DuckDB 쓰기를 UPSERT(INSERT OR REPLACE)로. collect 후 score 전 실패 시 → 재실행만으로 복구. 체크포인트/롤백/사가 패턴 불필요.

**판정**: **필수** — 가장 저렴한 신뢰성 패턴(UPSERT가 INSERT보다 구현 비용 사실상 동일).

### 3. Fail-Fast 원칙 [LOCAL-OK]

각 단계에서 출력 검증, 잘못된 데이터를 다음 단계로 전파하지 않음:

```
collect: pykrx 0종목 반환 → 즉시 FAIL
         1,800/2,500종목 반환 → WARN (부분 데이터)
         가격 날짜 불일치 → FAIL (데이터 손상)

analyze: 지표 계산 예외 → 해당 종목 로그·스킵, 나머지 계속
         10%+ 종목 실패 → FAIL (시스템적 문제)

score:   [0,100] 범위 초과 → BUG, FAIL
         평균 > 80 → 가중치 교정 오류, WARN
```

**판정**: **필수** — pykrx의 침묵적 오류에 대한 직접적 방어.

### 4. 상태 머신 (State Machine) [LOCAL-OK]

```
IDLE → COLLECTING → ANALYZING → SCORING → REPORTING → COMPLETE
  ↓        ↓           ↓          ↓          ↓
ERROR    ERROR       ERROR      ERROR      ERROR
```

**상태 전이 가드**: COLLECTING→ANALYZING은 2,000+ 종목 수집 시에만. ANALYZING→SCORING은 90%+ 지표 계산 완료 시에만.

**에이전트 루프 대비 장점**: 완전 결정론적, DuckDB 쿼리로 정확한 상태 확인, 토큰 비용 0. 파이프라인(Engine 1)은 상태 머신, 해석 층(Engine 2)은 에이전트 루프 — 각각의 장점 극대화.

**판정**: **권장** — 파이프라인의 결정론적 특성에 최적.

### 5. ETL 증분 처리 [LOCAL-OK]

**증분 처리 (권장)**: 일일 당일 OHLCV만 수집(2,500행) → DuckDB 추가 → 캐시된 과거 데이터로 지표 재계산 → 전 종목 재점수(공식 적용만이라 빠름). 예상 시간: **3-5분**.

**하이브리드 전략**: 일일 증분 + 주간(주말) 전체 정합성 검증 + 월간 전체 재수집(수정주가/기업 조치 반영).

**판정**: **필수** — KRX 요청 횟수 최소화 + 실행 시간 최적화.

### 6. 데이터 품질 게이트 [LOCAL-OK]

**Gate 1 — Post-Extract**: 행 수 2,000+? 날짜 일치? 가격 > 0? 거래량 ≠ 전부 0?
**Gate 2 — Post-Transform**: 지표 완전성? NaN < 5%? RSI ∈ [0,100]?
**Gate 3 — Post-Score**: 점수 ∈ [0,100]? 평균 30-60 사이? 90+ 점수 종목 수 합리적?

**판정**: **필수** — 각 게이트는 단순 Python assertion. 비용 밀리초. 쓰레기 데이터 차단.

### 7. 신뢰성 패턴 [LOCAL-OK]

**서킷 브레이커**: pykrx 3회 연속 실패 → OPEN(캐시 사용) → 1시간 후 HALF_OPEN(테스트 1회) → 성공 시 CLOSED.

**우아한 저하**: pykrx 다운 → 어제 캐시 사용 + "데이터: 어제 기준" 표시. 지표 1개 실패 → 나머지 5개로 비례 재계산. DuckDB 손상 → 백업 복원.

**벌크헤드**: 데이터 수집과 점수 산출 격리. collect 실패해도 어제 데이터로 score 가능. score 버그가 있어도 수집 데이터는 DuckDB에 안전.

**판정**: 서킷 브레이커 + 우아한 저하 **필수**. 벌크헤드 **권장**.

### Branch 5.2 결론

모든 원칙이 직접 구현 가능하고, 거의 0에 가까운 오버헤드를 가지며, 실제 실패 모드를 방어. Branch 5.1의 고급 패턴과 달리, "학술적이지만 비실용적"인 항목 없음 — 모두 엔지니어링 기초.

---

## Technical Analysis Theory — 점수 산출 방법론 기초

### 1. MA Alignment Score — Minervini SEPA Trend Template

**8개 기준 (정확한 임계값)**:

| # | 기준 | 수식 |
|---|------|------|
| 1 | 종가 > 50일 SMA | `close > SMA(close, 50)` |
| 2 | 종가 > 150일 SMA | `close > SMA(close, 150)` |
| 3 | 종가 > 200일 SMA | `close > SMA(close, 200)` |
| 4 | 50일 SMA > 150일 SMA | `SMA(50) > SMA(150)` |
| 5 | 50일 SMA > 200일 SMA | `SMA(50) > SMA(200)` |
| 6 | 150일 SMA > 200일 SMA | `SMA(150) > SMA(200)` |
| 7 | 200일 SMA 최소 1개월 상승 | `SMA(200, today) > SMA(200, 22일 전)` |
| 8a | 종가 ≥ 52주 저가 × 1.30 | 최소 30% 위 |
| 8b | 종가 ≥ 52주 고가 × 0.75 | 25% 이내 |

**0-100 점수 변환**: 각 기준 충족 시 10-15점 배분. 완전 정배열 = 100점.

### 2. Base Formation Score — Weinstein Stage Analysis

**30주 SMA(=150일 SMA)** 기울기와 가격 위치로 4단계 분류:

| Stage | 30주 SMA | 가격 | 거래량 | 의미 |
|-------|---------|------|--------|------|
| Stage 1: 매집 | 수평화 | 횡보 | 조용, 간헐적 급증 | 스마트머니 매집 |
| Stage 2: 상승 | 상승 | SMA 위에서 이격 | 상승일 강, 하락일 약 | **최적 매수 구간** |
| Stage 3: 분배 | 수평화 | 불규칙, 신고가 실패 | 하락일에 대량 | 스마트머니 분배 |
| Stage 4: 하락 | 하락 | SMA 아래로 이격 | 하락일에 대량 | **회피** |

**점수 매핑**: Stage 4→0-20, Stage 1 초기→20-40, Stage 1 후기→40-60, 1→2 전환→60-80, Stage 2 확인→80-100.

### 3. Volume Behavior Score — Wyckoff Method

**3가지 지표 조합**:
- **OBV 추세** (20일 상승 여부): 0-30점
- **상승일/하락일 거래량 비율**: >2.0=강한 매집(40점), >1.5=매집(30점), <0.7=분배(0점): 0-40점
- **거래량 수축도** (최근 10일/과거 50일): <0.5=강한 수축(30점), <0.7=보통(20점): 0-30점

### 4. Momentum Score — RSI/MACD/ADX 복합

- **RSI(14)**: 50-70=강세(30점), 40-50=중립(15점), >70=과매수(10점)
- **MACD**: 골든크로스+히스토그램 양수(40점), 크로스만(25점), 히스토그램 개선(15점)
- **ADX(14)**: >25=강한 추세(30점), >20=보통(20점), >15=약한(10점)

### 5. Breakout Readiness Score — Minervini VCP

**VCP(Volatility Contraction Pattern)** 탐지:
1. 스윙 고점/저점 식별 → 연속 풀백 깊이 계산
2. 각 풀백이 이전보다 작아지는지 확인 (예: 25%→15%→8%→3-4%)
3. 최종 수축기 거래량 감소 확인
4. 최종 수축 <5% = 90점, <10% = 70점, <15% = 50점

**VCP 성공률**: 주요 지수가 월간 10-EMA 위일 때 ~90.77%, 조정기에는 급락 → **시장 레짐 필터 필요**.

**Phase 1 간소화**: 전체 스윙 포인트 탐지 대신 Bollinger Band 폭 수축 + 거래량 감소를 프록시로.

### 6. Relative Strength Percentile — IBD RS Rating

**IBD 공식 재구성**:
```
RS = 40% × 3개월 수익률 + 20% × 6개월 + 20% × 9개월 + 20% × 12개월
```
전 종목 대비 백분위 순위(0-99) → 직접 0-100 스케일 매핑.

### 7. Composite Score

**6개 서브스코어 가중치 (기본값, 가설)**:

| 서브스코어 | 이론 기반 | 가중치 | 근거 |
|-----------|---------|--------|------|
| MA Alignment | Minervini | 20% | 상승 구조 확인의 기초 |
| Base Formation | Weinstein | 20% | 사이클 위치 식별 |
| Volume Behavior | Wyckoff | 20% | 가격 움직임의 거래량 검증 |
| Momentum | RSI/MACD/ADX | 15% | 현재 방향 강도 |
| Breakout Readiness | Minervini VCP | 15% | 실행 가능 진입점 근접도 |
| Relative Strength | IBD RS | 10% | 시장 대비 상대 성과 |

**점수 해석**: 80-100 "기술적 완성 임박", 60-79 "진행 중", 40-59 "초기 단계", 0-39 "미성숙".

**가중치는 가설**: 최소 3개월(66거래일) 백테스팅 데이터 후 Reflexion 교정. 초기 가중치는 Minervini(MA 필수 전제) + Wyckoff(거래량이 거짓말 탐지기) 이론에 기반.

---

## Branch 5.1 vs 5.2 Synthesis

### Theory-to-Practice 매핑

| 이론/원칙 | 적용 | 복잡도 | 가치 | 판정 |
|----------|------|--------|-----|------|
| ReAct | Claude Code 내장 | 0 | 높음 | USE (이미 존재) |
| CoT | 출력 템플릿 설계 | 0 | 높음 | USE |
| ToT | 배치에 비실용적 | 높음 | 낮음 | SKIP |
| 멀티에이전트 토론 | 단일 에이전트 동등 성능 | 높음 | 낮음 | SKIP (Phase 1) |
| Reflexion | 월간 가중치 교정 | 중간 | 매우 높음 | USE |
| Memory | DuckDB + context-snapshots | 낮음 | 높음 | USE (이미 존재) |
| RAG | SQL이 우월 | 중간 | 낮음 | SKIP |
| 백테스팅 | 점수 검증 | 중간 | 필수 | USE (출시 전) |
| Unix 철학 | 파이프라인 아키텍처 | 낮음 | 필수 | USE (필수) |
| 관심사 분리 | Python/Claude 경계 | 낮음 | 필수 | USE (필수) |
| 멱등성 | UPSERT 패턴 | 사소함 | 높음 | USE (필수) |
| Fail-Fast | 단계별 검증 | 낮음 | 높음 | USE (필수) |
| 상태 머신 | DuckDB 상태 테이블 | 낮음 | 높음 | USE |
| ETL 증분 | 일일 추가 + 주간 검증 | 낮음 | 높음 | USE (필수) |
| 데이터 품질 게이트 | 단계별 assertion | 낮음 | 높음 | USE (필수) |
| Minervini/Weinstein/Wyckoff/IBD | 점수 산출 핵심 | 중간 | 필수 | USE (필수) |
| 서킷 브레이커 | pykrx 장애 대응 | 낮음 | 높음 | USE (필수) |
| 우아한 저하 | 캐시 폴백 | 낮음 | 높음 | USE (필수) |

### 핵심 갭: 이론 vs 실제

**이론과 Claude Code가 완벽히 정렬되는 곳**:
1. ReAct이 네이티브. 도구 사용 루프가 곧 ReAct.
2. 메모리가 자연적. DuckDB + context-snapshots + CLAUDE.md.
3. 관심사 분리가 아키텍처. Engine 1(Python) / Engine 2(Claude), 인터페이스 = summary.md.

**이론과 실제가 다른 곳**:
1. 멀티에이전트: 이론은 전문화가 품질 향상이라 하지만, 우리의 결정론적 파이프라인에서 "전문 에이전트"는 Python 함수(pandas-ta).
2. RAG: 이론은 에피소딕+시맨틱+RAG 메모리라 하지만, 구조화된 데이터에는 SQL이 벡터 검색을 압도.
3. 계획 이론: Plan-and-Execute를 말하지만, 고정 파이프라인에 LLM 계획은 과잉. if/else가 더 빠르고 저렴.

### Parking Lot

1. 점수 가중치 교정: 초기 가중치는 가설. 최소 3개월 데이터 후 조정. 통계적 유의성 기준?
2. VCP 탐지 복잡도: Phase 1 간소화 프록시(BBand squeeze + volume) vs 전체 VCP. 전환 기준?
3. 시장 레짐 필터: KOSPI 200일 SMA 하회 시 전체 점수 신뢰도 하락. 별도 경고 vs 점수 반영?
4. 수정주가: 기업 분할/배당이 이동평균에 영향. pykrx adjusted 파라미터 동작 미확인.
5. Stage 1→2 전환 감지: SMA 기울기 임계값(0.02 사용)이 한국 시장 변동성에 적합한지 실증 필요.
6. 지표 간 충돌: MA 90점 + Volume 30점 = 이 괴리가 신호. 가중 평균이 정보를 소멸시킴.
7. KOSDAQ vs KOSPI: 소형주 행태 차이 → 시장별 가중치 차등화 검토.
