---
type: final-synthesis
created: "2026-05-26T22:00:00+09:00"
scope: "4개 라운드(일반·기술이론·코딩구현·외부연동) 전체 통합"
target: "PRD.md 제작의 최종 조사 입력"
source_file_count: 42
local_execution_constraint: true
---

# Final Research — KOSPI/KOSDAQ 종목 기술적 완성도 분석 및 선별 시스템

> 이 문서는 1~4차 심층조사(4개 축, 19명 teammate, 42개 파일)를 통합한 PRD 제작용 최종 조사 결과다.
> 모든 선택지에 LOCAL-* 태그를 유지하며, 상충 지점은 해결된 척하지 않고 명시한다.

---

## 0. 메타: 통합 범위 · 원본 파일 목록 · 작성 시점

### 0.1 작성 시점
- 통합 완료: 2026-05-26

### 0.2 원본 파일 목록 (42개)

| # | 경로 | 유형 | 반영 |
|---|------|------|------|
| 1 | `_index.yaml` | 마스터 인덱스 | ✅ |
| 2 | `README.md` | 확장 규칙·네이밍 규약 | ✅ |
| 3 | `round-01/_round-meta.yaml` | R1 메타 | ✅ |
| 4 | `round-01/raw/T01-workflow-architect.md` | R1 워크플로우 아키텍트 | ✅ |
| 5 | `round-01/raw/T02-scenario-explorer.md` | R1 시나리오 탐색 | ✅ |
| 6 | `round-01/raw/T03-operator-analyst.md` | R1 운영자 분석 | ✅ |
| 7 | `round-01/raw/T04-sustainability-strategist.md` | R1 지속가능성 전략 | ✅ |
| 8 | `round-01/synthesis/S01-convergence.md` | R1 수렴 분석 | ✅ |
| 9 | `round-01/synthesis/S02-risk-register.md` | R1 위험 등록부 | ✅ |
| 10 | `round-01/synthesis/S03-key-findings.md` | R1 핵심 발견 | ✅ |
| 11 | `round-01/synthesis/S04-prd-direction.md` | R1 PRD 방향 | ✅ |
| 12 | `round-02/_round-meta.yaml` | R2 메타 | ✅ |
| 13 | `round-02/raw/T01-platform-capability.md` | R2 플랫폼 역량 | ✅ |
| 14 | `round-02/raw/T02-configuration-architect.md` | R2 설정 아키텍처 | ✅ |
| 15 | `round-02/raw/T03-orchestration-engineer.md` | R2 오케스트레이션 | ✅ |
| 16 | `round-02/raw/T04-integration-specialist.md` | R2 통합 전문가 | ✅ |
| 17 | `round-02/raw/T05-theory-foundation.md` | R2 이론 기초 | ✅ |
| 18 | `round-02/raw/T06-orchestration-pattern-analysis.md` | R2 오케스트레이션 패턴 심층 | ✅ |
| 19 | `round-02/synthesis/S01-tech-discussion.md` | R2 기술 토론 | ✅ |
| 20 | `round-02/synthesis/S02-scenarios.md` | R2 시나리오 | ✅ |
| 21 | `round-02/synthesis/S03-key-findings.md` | R2 핵심 발견 | ✅ |
| 22 | `round-02/synthesis/S04-prd-direction.md` | R2 PRD 방향 | ✅ |
| 23 | `round-03/_round-meta.yaml` | R3 메타 | ✅ |
| 24 | `round-03/raw/T01-workflow-script-architect.md` | R3 워크플로우 스크립트 | ✅ |
| 25 | `round-03/raw/T02-agent-orchestration-coder.md` | R3 에이전트 오케스트레이션 | ✅ |
| 26 | `round-03/raw/T03-skills-hooks-developer.md` | R3 스킬/훅 개발 | ✅ |
| 27 | `round-03/raw/T04-verification-quality-coder.md` | R3 검증·품질 | ✅ |
| 28 | `round-03/raw/T05-state-recovery-coder.md` | R3 상태·복구 | ✅ |
| 29 | `round-03/synthesis/S01-spectral-positioning.md` | R3 스펙트럼 포지셔닝 | ✅ |
| 30 | `round-03/synthesis/S02-implementation-scenarios.md` | R3 구현 시나리오 | ✅ |
| 31 | `round-03/synthesis/S03-key-findings.md` | R3 핵심 발견 | ✅ |
| 32 | `round-03/synthesis/S04-prd-direction.md` | R3 PRD 방향 | ✅ |
| 33 | `round-04/_round-meta.yaml` | R4 메타 | ✅ |
| 34 | `round-04/raw/T01-mcp-server-specialist.md` | R4 MCP 서버 | ✅ |
| 35 | `round-04/raw/T02-local-tool-integration-expert.md` | R4 로컬 도구 | ✅ |
| 36 | `round-04/raw/T03-api-service-connector.md` | R4 API·서비스 | ✅ |
| 37 | `round-04/raw/T04-data-flow-architect.md` | R4 데이터 흐름 | ✅ |
| 38 | `round-04/raw/T05-reliability-fallback-engineer.md` | R4 신뢰성·폴백 | ✅ |
| 39 | `round-04/synthesis/S01-integration-spectrum.md` | R4 연동 스펙트럼 | ✅ |
| 40 | `round-04/synthesis/S02-discussion-scenarios.md` | R4 토론·시나리오 | ✅ |
| 41 | `round-04/synthesis/S03-key-findings.md` | R4 핵심 발견 | ✅ |
| 42 | `round-04/synthesis/S04-prd-direction.md` | R4 PRD 방향 | ✅ |

> 참고: `mandatory-decision-rules-sot.md` 파일은 존재하지 않아 반영하지 않음.

### 0.3 라운드별 개요

| 라운드 | 축 | 날짜 | Teammate 수 | WebSearch | 핵심 가정 축 |
|--------|-----|------|-----------|-----------|-------------|
| 1차 | 일반 (광범위) | 2026-05-25 | 4 | 103 | Claude Code standalone vs integrated |
| 2차 | 기술·이론 | 2026-05-25 | 5+1 | 80+ | Maximum Utilization vs Limitation-Aware |
| 3차 | 코딩·구현 | 2026-05-26 | 5 | N/A (코드 분석 중심) | 5개 구현 축별 상충 |
| 4차 | 외부 연동 | 2026-05-26 | 5 | 93+ | 5개 연동 축별 상충 |

---

## 1. 시스템 개요 (조사 기반)

### 1.1 제품 정체성

KOSPI/KOSDAQ 전 종목(~2,500개)을 대상으로 **"기술적 완성도"**라는 복합 점수를 일일 산출하고, 상위 종목을 한국어로 해석·보고하는 로컬 자동화 시스템.

**핵심 발견** [R1-S03-F1]: "기술적 완성도"는 표준 금융 용어가 아니다. 학술 논문이나 산업 합의가 없으므로 **PRD가 이 정의를 구축**해야 한다.

**"기술적 완성도" 개념 정의 — 4개 구성 요소** [R1-T02]:

| 한국어 개념 | 정의 | 서양 프레임워크 | 주요 제안자 |
|-----------|------|--------------|-----------|
| 바닥 다지기 (베이스 완성) | 하락 후 장기 횡보 압축. 바닥이 길고 타이트할수록 완성도 높음 | Weinstein Stage 1 + O'Neil 베이스 패턴 | Stan Weinstein |
| 매집 완성도 | 기관/세력의 지분 매집 증거. 하락일 거래량 고갈 + 상승일 점진적 증가 → VCP 수축 | Wyckoff Accumulation/Distribution | Richard Wyckoff |
| 이평선 정배열 | 현재가 > 단기 MA > 중기 MA > 장기 MA. 역배열→수렴→정배열 진행이 핵심 | SEPA Trend Template | Mark Minervini |
| 돌파 준비 | 명확한 저항 수준 근접 + 거래량 수축 + 가격 범위 축소 | VCP Breakout + Cup-with-Handle | Minervini, O'Neil |

**참조 문헌** [R1-T02, S2/S3 복원]:
- Mark Minervini, *Trade Like a Stock Market Wizard* / *Think and Trade Like a Champion*
- William O'Neil, *How to Make Money in Stocks* (CANSLIM)
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets*
- 한국 커뮤니티: 다음 카페 "부자아빠 주식학교", "상승하는 차트의 조건과 차트의 기본기" (고짹짹)

### 1.2 Two-Engine 아키텍처 (4개 라운드 연속 확인)

모든 19명의 teammate이 독립적으로 동일한 결론에 수렴:

```
Engine 1: Python Data Pipeline (결정론적, 토큰 소비 0)
  collect.py → analyze.py → score.py → report.py → summary.md

Engine 2: Claude Code Interpretation Layer (적응적, 토큰 소비)
  summary.md 읽기 → 한국어 해석 → 사용자 대화
```

- **출처**: R1-S03-F2(아키텍처 수렴), R2-S03-F1(summary-first 아키텍처적 필수), R3-S03-F1(코드 수준 구체화), R4-S03-F1(외부 연동에서도 분리 정당)
- **인터페이스**: `output/summary.md` (단일 핸드오프 파일, YAML 프론트매터 + Markdown 본문)
- **[LOCAL-OK]**: Engine 1 전부 로컬, Engine 2는 Anthropic API만 네트워크 의존

**summary.md 인터페이스 스키마** [R4-T04, Rev.3 통합 누락 보충]:

YAML 프론트매터 (9개 필드):
```yaml
---
report_date: "2026-05-26"        # 리포트 생성일
market_date: "2026-05-26"        # 시장 데이터 기준일
stock_count: 2487                # 분석 종목 수
kospi_count: 943
kosdaq_count: 1544
scoring_config_hash: "a1b2c3d4"  # 설정 변경 추적
gates_passed: [1, 2, 3, 4]      # 통과한 검증 게이트
degraded: false                  # 폴백 사용 여부
pipeline_version: "1.0.0"
---
```

Markdown 본문 구조: Market Overview 테이블 → Top 80 by Total Score (Rank/Ticker/Name/Total + 6개 서브스코어) → Anomaly Alerts → Sub-Score Distribution → Data Quality (게이트 통과/실패 상태). 크기: ~15-25KB (~5,000-8,000 토큰)

### 1.3 대상 사용자

**주 대상: 비기술 사용자** — "이 시스템을 어떻게 만들지 전혀 모른다"(사용자 원문). [R1-S03-F5]
- One-command setup (목표 15분 → R4 발견으로 1-2분으로 단축 가능)
- 일일 `/scan` 한 번으로 결과 확인
- 한국어 전용 인터페이스 (에러 메시지 포함)
- Graceful Degradation + 자동 재시도 (디버깅 불가능한 사용자 전제) [Rev.5 리프레이밍: "자가 복구"는 근본 원인 해결을 암시하나, 실제 메커니즘은 캐시 폴백 + 재시도 + 한국어 알림. 근본 원인 해결(예: pykrx 장기 다운)은 Phase 2 Telegram 알림 → 운영자 개입으로 위임]
- 설치 인내 한도: "3개 copy-paste 명령 OK, 5개 한계, 텍스트 수정 불가" [R1-T03]
- 이탈 트리거: Python 설치 실패(command not found), 영어 에러 메시지, 5분 초과 무피드백 대기, 구글링 필요한 상황 = 포기 [R1-T03, Rev.3 보충]
- 일일 사용 시간 예산: 3-5분 **= 결과 확인·해석 시간** [R1-T03, Rev.3 보충, Rev.5 명확화]. 파이프라인 실행(3-5분)은 launchd 백그라운드 자동 실행이 전제. 사용자는 완료된 summary.md만 확인
- 에러 복구 기대: "안 돼" → 자동 복구 기대 (디버깅 불가능한 사용자) [R1-T03, Rev.3 보충]

**부 대상: Power User** [R1-T03]:
- 배경: 개발자 또는 퀀트 트레이더, Claude Code Max 구독자, Python 환경 기보유
- 핵심 요구: 투명한 점수 알고리즘, YAML 설정 가능, raw 데이터 접근(DuckDB 쿼리/CSV 내보내기), 재현 가능한 결과
- 이탈 트리거: 불투명 점수, 부정확 데이터, 유연하지 않은 아키텍처, 10분 초과 스캔
- 최소 품질 기준: "Top 20 교차검증 시 70% 이상 합리적" [R1-T03]
- **설계 원칙**: 점진적 노출(Layer 0-4)로 두 사용자 모두 수용. 기본 사용자는 Layer 0-1, Power User는 Layer 2-4

### 1.4 법적 프레이밍 [R1-S03-F8]

한국 금융 규제상 무면허 투자 조언 불가.
- "기술적 완성도가 높은 종목" (O) / "이 종목을 사세요" (X)
- 모든 출력에 면책조항 내장: "투자 판단은 본인 책임", "매수·매도 추천이 아님"

---

## 2. 축별 종합

### 2.1 일반 축 (Round 1)

**출처**: `round-01/synthesis/S01~S04`, `round-01/raw/T01~T04`

#### Green Zone — 4/4 합의, 절대 필수

| # | 구성 요소 | 근거 | LOCAL |
|---|-----------|------|-------|
| 1 | Python 네이티브 데이터 파이프라인 | 2,500 × 250일 × 20+ 지표 = Python 영역. Claude 계산 = 토큰 파산 | [LOCAL-OK] |
| 2 | 로컬 데이터베이스 (DuckDB) | 캐시, 이력, 백테스팅 전제. DuckDB 분석 15-20x faster | [LOCAL-OK] |
| 3 | 데이터 소스 추상화 계층 | pykrx 불안정 대응. swap = 1 file change | [LOCAL-OK] |
| 4 | 기술적 완성도 점수 산출 엔진 | Minervini SEPA + Weinstein + Wyckoff. 결정론적·테스트 가능 | [LOCAL-OK] |
| 5 | 한국어 결과 프레젠테이션 | "RSI: 0.72"가 아닌 "모멘텀: 상승 중" | [LOCAL-OK] |
| 6 | 자동 설치·환경 구성 | uv + bootstrap.sh. pip을 모르는 사용자 | [LOCAL-OK] |
| 7 | 요약 우선 출력 패턴 | Python 전체 분석 → summary.md → Claude는 요약만 읽기 (40-60% 추가 절약) | [LOCAL-OK] |

#### Yellow Zone — 3/4 합의, 조건부

| # | 구성 요소 | 포함 조건 |
|---|-----------|----------|
| 1 | launchd 일일 자동 스케줄링 | Claude Code가 plist 자동 생성 |
| 2 | pykrx-mcp 통합 | MCP 안정성 확인 후 (→ R4에서 Phase 1 불필요 확정) |
| 3 | 점진적 노출 아키텍처 (Layer 0-4) | 현 사용자는 Layer 0-1만 |
| 4 | 에러 자동 복구 + 한국어 에러 메시지 | pykrx timeout auto-retry + 캐시 폴백 = 항상 포함 |

#### Red Zone — 후순위

백테스팅(3개월 후), 실시간 인트라데이 알림(별도 아키텍처), 커스텀 지표(사용자 요청 시), 자동 주문 집행(별도 프로젝트), 뉴스 감성 분석(별도 NLP).

#### 핵심 발견 8개

1. **"기술적 완성도" 정의 부재** → PRD가 구축 [R1-S03-F1]
2. **아키텍처 Hybrid 수렴** → Two-Engine [R1-S03-F2]
3. **토큰 경제 Branch B 필수** → 80-90% 절약 [R1-S03-F3]
4. **pykrx/KRX 최고 외부 위험** → 추상화 계층 필수 [R1-S03-F4]
5. **비기술 사용자** → 설치 UX 핵심 [R1-S03-F5]
6. **한국 주식 MCP 생태계 존재** → Phase 2 활용 가능 [R1-S03-F6]
7. **우선 시나리오 합의** → Phase 1(일일 스크리닝) → Phase 2(개별 분석) → Phase 3(알림) [R1-S03-F7]
8. **법규 프레이밍 필수** → 투자 조언이 아닌 분석 도구 [R1-S03-F8]

#### TOP 5 위험 가정 [R1-S02]

| # | 위험 | 영향 | 확률 |
|---|------|------|------|
| 1 | pykrx 기능 유지 | CRITICAL | HIGH |
| 2 | 점수 시스템 유용성 | CRITICAL | MEDIUM |
| 3 | 비기술 사용자 Python 설치 가능성 | HIGH | HIGH |
| 4 | Claude Code Max 구독 한도 충분 | HIGH | MEDIUM |
| 5 | 사용자 결과 적절 활용 | MEDIUM | MEDIUM |

---

### 2.2 기술·이론 축 (Round 2)

**출처**: `round-02/synthesis/S01~S04`, `round-02/raw/T01~T06`

#### 기술 선택 합의 (5/5)

| 기술 | 선택 이유 | LOCAL |
|------|----------|-------|
| summary-first 아키텍처 | 컨텍스트 보존, 결정론적 | [LOCAL-OK] |
| DuckDB 단일 파일 DB | 분석 특화, MVCC, pip 1줄 | [LOCAL-OK] |
| **pandas-ta-classic** (pandas-ta·TA-Lib 아님) | 순수 Python, Apple Silicon, 192+ 지표 + 62 캔들 패턴, Production/Stable | [LOCAL-OK] |

> ※ **pandas-ta → pandas-ta-classic 전환 확정** [Rev.3 심층조사]: 원본 pandas-ta(twopirllc) GitHub 리포지토리는 **이미 삭제됨(404)**. PyPI의 pandas-ta 0.4.71b0은 관리자가 변경되어 공급망 우려 존재. pandas-ta-classic(xgboosted, v0.6.20, 2026-05-20 릴리즈)은 Production/Stable, MIT, 월간 릴리즈, 192 지표 + 62 캔들 패턴. 시스템이 사용하는 6개 지표(SMA, RSI, MACD, ADX, BBands, OBV) 전부 API 호환 — 유일한 변경: `import pandas_ta` → `import pandas_ta_classic`. Python 3.10+, pandas 2.0+, NumPy 2.0+ 요구. **U6 해결, R-4-1 위험 사실상 제거**.
| uv 패키지 매니저 | Python 자동 설치, 80x 빠른 venv | [LOCAL-OK] |
| launchd StartCalendarInterval | macOS 네이티브, 수면/복귀 처리 | [LOCAL-OK] |
| 순차 파이프라인 | Prefect/Dagster 과잉, Claude 오케스트레이션 불필요 | [LOCAL-OK] |
| 멱등성 UPSERT | 0 비용으로 장애 복구 | [LOCAL-OK] |

#### 명시적 배제 (근거 포함)

- **MCP 서버** (0-1/5): 배치에 중복. Phase 2 대화형에서만 재검토.
- **멀티에이전트 토론** (0/5): Nature 2026 연구 — 다수 압력 순응. 단일 에이전트 동등 성능.
- **ToT**: 2,500종목 × N분기 = 토큰 폭발.
- **RAG**: 구조화 데이터에는 SQL > 벡터 검색.

#### 6개 서브스코어 매핑 [R2-S04, R2-T05]

| # | 서브스코어 | 기초 이론 | 지표 매핑 | 기본 가중치 |
|---|-----------|----------|----------|-----------|
| 1 | MA Alignment (이평선 정배열) | Minervini SEPA | 8기준 Boolean 합산 | 20% |
| 2 | Base Formation (바닥·매물대 정리) | Weinstein Stage | SMA 기울기 + 가격 위치 → 4단계 | 20% |
| 3 | Volume Behavior (거래량 수축·매집) | Wyckoff | OBV 추세 + 상승/하락 비율 + 수축도 | 20% |
| 4 | Momentum | 복합 | RSI(14) + MACD + ADX(14) | 15% |
| 5 | Breakout Readiness (돌파 임박도) | VCP 간소화 프록시 | BBand squeeze + volume decline | 15% |
| 6 | Relative Strength (상대 강도) | IBD RS Rating | 가중 수익률(40% 3mo + 20%×3) → 백분위 | 10% |

**가중치는 가설이며 백테스팅 필수** [R2-S03-F6]. 최소 3개월(66거래일) 데이터 후 교정.

#### 서브스코어 세부 포인트 할당 수식 [R2-T05]

**1. MA Alignment — Minervini SEPA 8개 기준**:

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

0-100 변환: 각 기준 충족 시 10-15점 배분. 완전 정배열 = 100점.

> **⚠️ CRITICAL — 수정주가(Adjusted Price) 전제조건** [Rev.3 심층조사]:
> MA Alignment의 8개 기준은 전부 SMA-50/150/200에 의존. 그러나 시스템의 배치 수집 API `get_market_ohlcv_by_ticker(date)`는 **adjusted 파라미터가 없으며 KRX 원본 가격만 반환**. 액면분할(연간 15-21건, 고모멘텀 대형주 집중) 시 SMA-200에 대규모 불연속 발생 → MA Alignment(20%) + Base Formation(20%) = **전체 점수의 40% 왜곡** 위험.
> - PL-5(실증 테스트)에서 **Phase 1 설계 요구사항으로 격상**.
> - 권장 대응: Hybrid Detection + Targeted Re-fetch (§5.2 Section 5 참조).
> - `get_market_ohlcv_by_date(ticker, adjusted=True)`는 Naver 소스 사용 — pykrx Issue #162에서 미작동 보고. FDR 교차검증 필요.

**2. Base Formation — Weinstein Stage 점수 매핑**:

| 단계 | 30주 SMA | 가격 | 점수 범위 |
|------|---------|------|----------|
| Stage 4 (하락) | 하락 | SMA 아래 이격 | 0-20 |
| Stage 1 초기 (매집) | 수평화 시작 | 횡보 | 20-40 |
| Stage 1 후기 | 수평 | 변동성 감소 | 40-60 |
| Stage 1→2 전환 | 상승 전환 | SMA 근접 | 60-80 |
| Stage 2 확인 (상승) | 상승 | SMA 위 이격 | 80-100 |

SMA 기울기 임계값: 0.02 (한국 시장 변동성에 대한 실증 검증 필요 — PL 항목).

**3. Volume Behavior — Wyckoff 3지표 조합**:
- OBV 추세 (20일 상승 여부): 0-30점
- 상승일/하락일 거래량 비율: >2.0=40점(강한 매집), >1.5=30점, <0.7=0점(분배): 0-40점
- 거래량 수축도 (최근 10일/과거 50일): <0.5=30점(강한 수축), <0.7=20점: 0-30점

**4. Momentum — RSI/MACD/ADX 복합**:
- RSI(14): 50-70=30점(강세), 40-50=15점(중립), >70=10점(과매수)
- MACD: 골든크로스+히스토그램 양수=40점, 크로스만=25점, 히스토그램 개선=15점
- ADX(14): >25=30점(강한 추세), >20=20점, >15=10점

**5. Breakout Readiness — VCP 수축 깊이**:
- 최종 수축 <5% = 90점, <10% = 70점, <15% = 50점
- Phase 1 간소화: 전체 스윙 포인트 탐지 대신 BBand 폭 수축 + 거래량 감소 프록시 (§2.2 VCP 간소화 프록시 참조)

**6. Relative Strength — IBD RS 공식**:
```
RS = 40% × 3개월 수익률 + 20% × 6개월 + 20% × 9개월 + 20% × 12개월
```
전 종목 대비 백분위 순위(0-99) → 직접 0-100 스케일 매핑.

#### 점수 해석 임계값

- 80+ = "완성 임박"
- 60-79 = "진행 중"
- 40-59 = "초기"
- <40 = "미성숙"

#### VCP 간소화 프록시 [R2-S03-F7]

Phase 1은 전체 VCP(스윙 포인트 탐지 + 수축 측정) 대신 **BBand 폭 수축 + 거래량 감소**를 대리 지표로 사용. 전체 VCP는 Phase 3에서 백테스팅 비교 후 전환 결정.

**Phase 1 초기 임계값 앵커** [Rev.4 적대적 성찰 반영]: Minervini (*Think and Trade Like a Champion*)의 일반적 VCP 수축 기준에서 도출한 초기값:
- BBand squeeze width: 최종 수축 ≤10% (BBand 상/하단 폭이 종가의 10% 이내)
- Volume decline: 최근 10일 평균 거래량이 50일 평균 대비 ≤60%
- **이 값은 가설적 초기값**이며, 66거래일(3개월) 운영 후 한국 시장 데이터로 교정 필요. 임계값 변경 시 scoring_config.yaml에 기록

> **상충**: 프록시와 전체 VCP 사이의 경계가 모호. 초기 앵커 제시되었으나 한국 시장 실증 검증 미완료. [R2-S01 충돌 #2, Rev.4 앵커 추가]

#### 시장 레짐 경고 오버레이 [R2-S01 충돌 #3]

KOSPI 200일 SMA 하회 시 별도 경고 표시. **합산 점수에 미포함** — 동일 90점이 시장 상황에 따라 다른 의미를 갖게 되므로 투명성을 위해 분리.

#### 핵심 발견 9개

1. Claude Code가 오케스트레이션 90%+ 네이티브 커버 → Prefect/Dagster 불필요 [R2-S03-F1]
2. **침묵적 실패(Silent Failure)가 단일 최대 위험** → 데이터 검증 게이트 필수 [R2-S03-F2]
3. ReAct/CoT 이미 Claude Code 내장 → 추가 프레임워크 불필요 [R2-S03-F3]
4. 기술 스택 4개 의존성만 (pykrx, DuckDB, **pandas-ta-classic**, uv) [R2-S03-F4, Rev.3 업데이트]
5. pykrx KRX 로그인 필수화 = 해결된 위험, 마찰점 잔존 [R2-S03-F5]
6. 점수 가중치 = 가설, 백테스팅 필수 [R2-S03-F6]
7. VCP Phase 1 간소화 프록시 [R2-S03-F7]
8. 검증된 소프트웨어 공학 원칙이 실제 신뢰성 기초 [R2-S03-F8]
9. 토큰 경제 장기 지속 가능 (~25K/일, ~$1.50/월) [R2-S03-F9]

#### 시나리오 선택: Pragmatic [R2-S02]

| 시나리오 | 특징 | 결정 |
|---------|------|------|
| **Experimental** | 멀티에이전트, MCP 3종, 전체 VCP | 배제 — Nature 2026, 토큰 2-3x |
| **Pragmatic** ← 선택 | 순차 + 검증 + 재시도 + VCP 간소화 | 침묵적 오류 방지, ~25K/일, 1-2주 구현 |
| **Established** | 최소, 검증 없음 | 배제 — FM-4,5 미탐지, 신뢰 파괴 |

---

### 2.3 코딩·구현 축 (Round 3)

**출처**: `round-03/synthesis/S01~S04`, `round-03/raw/T01~T05`

#### 5개 영역 스펙트럼 포지셔닝 [R3-S01]

```
Workflow Script:    75% 절차적 (Hybrid: Stage 1-3 절차적, Stage 4 선언적)
Orchestration:      90% 중앙집중 (Claude Code = orchestrator)
Skills & Hooks:     85% 특화 (도메인 지식 내장)
Verification:       70% 엄격 (Gate 1,3 전수 + Gate 2,4 샘플링)
State Management:   80% 파일 기반 (4단계 순차에 FSM 과설계)
```

수렴 패턴: 5개 영역 모두 **순수 극단 배제**, "절차적/엄격/특화" 편향, "과설계 경계" 의식.

#### workflow.md 이중 성격 [R3-S03-F1]

- Engine 1 (Python): `ta.bbands(close, length=20, std=2)` — 세부사항이 아닌 **제품 사양**
- Engine 2 (Claude Code): 선언적 의도 — 절차적 지정은 해석 품질 저하
- **권고**: Hybrid ~350-400줄 (절차적 Stage 1-3 + 선언적 Stage 4)

#### 오케스트레이션: 7-1-4 중앙 집중 [R3-S03-F2, R2-T06]

Claude Code 자체가 orchestrator. 7:1:4 비교 결과(Centralized 7승, Distributed 1승, Tie 4):
- 일일 파이프라인은 결정론적 Python 체인 → AI 판단 미개입
- Phase 2+ 심층분석에서만 sub-agent fork

#### scoring_config.yaml SOT [R3-S03-F6]

스코어링 파라미터 4곳 분산(workflow.md, score.py, SKILL.md, 검증 게이트) → 단일 SOT로 통합.

```yaml
version: "1.0"
last_calibrated: "2026-05-26"
weights:
  ma_alignment: 0.20
  base_formation: 0.20
  volume_behavior: 0.20
  momentum: 0.15
  breakout_readiness: 0.15
  relative_strength: 0.10
thresholds:
  strong_buy: 80
  buy: 60
  neutral: 40
  weak: 20
calibration_note: "가설적 가중치. 3개월 운영 후 교정 필요"
```

#### 4-Gate Targeted Strict 검증 [R3-S03-F4]

```
collect ──Gate 1──→ analyze ──Gate 2──→ score ──Gate 3──→ report ──Gate 4──→ summary.md
  (엄격)              (선택적)           (엄격)            (선택적)
```

| 실패 모드 | 엄격 탐지 | 선택적 탐지 | 영향 |
|-----------|---------|-----------|------|
| FM-1: pykrx 전수 0원 | ✅ | ✅ | CRITICAL |
| FM-2: 2500 중 1800만 반환 | ✅ | ✅ | HIGH |
| FM-3: 5일 전 캐시 데이터 | ✅ | ✅ | HIGH |
| FM-4: pandas-ta NaN 30% | ✅ | ❌ | MEDIUM |
| FM-5: 점수 분포 점진 이동 | ✅ | ❌ | MEDIUM |
| FM-6: DuckDB 손상 | ✅ | ✅ | HIGH |

Gate 1(수집) + Gate 3(스코어링) 엄격, Gate 2(지표) + Gate 4(리포트) 선택적. ~780줄.

#### 파일 기반 상태 관리 [R3-S03-F5]

- `pipeline_state.json`: 현재 단계, 마지막 성공, 에러 정보
- `initial_load_checkpoint.json`: 5년 초기 로드 중단 재개. **DuckDB가 정합성 SOT** [Rev.4]: checkpoint 파일 대신 `SELECT MAX(date) FROM ohlcv WHERE ticker = ?`로 실제 로드 진행률 판단. checkpoint.json은 보조 힌트. checkpoint 손상 시에도 DB 기준으로 안전 재개 가능
- `fcntl.flock()` lock file: 동시 실행 차단. **스테일 락 자동 해제** [Rev.4]: flock 획득 실패 시 (1) lock 파일 내 PID 확인, (2) 해당 PID 프로세스 미존재 시 lock 자동 해제 + 한국어 메시지 "이전 실행이 비정상 종료되었습니다. 자동 복구 중...", (3) PID 존재 시 "이미 실행 중입니다" 안내. 비기술 사용자의 "구글링 필요 = 포기"(§1.3) 방지
- 상태 머신에서 차용: guard 조건, JSONL 전이 로그, `VALID_TRANSITIONS` dict
- ~520줄

#### 구현 시나리오 선택: Balanced (B) [R3-S02]

| 시나리오 | 총 구현량 | FM 방어 | 결정 |
|---------|---------|---------|------|
| Full-Defensive (A) | ~4,200줄 | 6/6 | 배제 — FSM ~900줄 과설계 |
| **Balanced (B)** ← 선택 | **~3,280줄** | **6/6** (Gate 1,3 엄격) | 핵심 품질 + 현실적 구현 |
| Rapid-Prototype (C) | ~1,050줄 | 3/6 | 배제 — FM-4,5 미탐지, 금융 도구 부적합 |

#### 파일 시스템 레이아웃 [R3-S04]

```
stock-scanner/
├── config/
│   ├── scoring_config.yaml     ← SOT
│   └── pipeline_config.yaml
├── src/
│   ├── main.py
│   ├── collect.py
│   ├── analyze.py
│   ├── score.py
│   ├── report.py
│   └── gates/
├── data/stocks.duckdb
├── output/summary.md           ← Engine 1→2 인터페이스
├── state/pipeline_state.json
├── logs/
├── .claude/
│   ├── skills/stock-scanner/
│   ├── commands/
│   └── hooks/scripts/
└── bootstrap.sh
```

#### 핵심 발견 10개 요약

1. workflow.md 이중 성격 (명세+실행지침)
2. 오케스트레이션 = 이미 해결 (Claude Code)
3. 도메인 특화 스킬 일일 ~1,250 토큰 절약
4. 검증 = 신뢰의 전제조건 (최적화 아님)
5. 파일 기반 상태 관리 충분
6. scoring_config.yaml SOT 부상 (4 소비자)
7. 코딩 복잡도 예상보다 낮음
8. Claude Code 기능 경계 명확화
9. 전체 구현량 ~3,400-3,700줄 수렴
10. 대부분 선택지 [LOCAL-OK], [LOCAL-BLOCKED] 2개 (Naver Finance 스크래핑, API 키 기반 LLM — Phase 1 핵심에 해당 없음) [R4-T03]

---

### 2.4 외부 연동 축 (Round 4)

**출처**: `round-04/synthesis/S01~S04`, `round-04/raw/T01~T05`

#### 연동 스펙트럼 [R4-S01]

```
MCP Server:   Phase 1: 0개 (배치에 대화형 도구 무의미)
Local Tools:  brew 0개 (macOS 내장 + uv만)
API/Service:  Phase 1: 거의 로컬 (pykrx 유일한 네트워크 의존)
Data Flow:    100% 배치 (Phase 1)
Reliability:  Fail-fast 기본 + 선택적 degradation
```

#### 핵심 발견 10개

1. **Phase 1 외부 연동 = pykrx 하나** [R4-S03-F1]
2. **OpenAI/Gemini CLI 구독 인증 [LOCAL-OK]** — API 키 0개 [R4-S03-F2]
3. **한국 주식 MCP 생태계 존재** (pykrx-mcp, DuckDB MCP 등) [R4-S03-F3]
4. **Light 로컬 도구 승리** — uv + Python 3패키지, brew 0개, jq macOS Tahoe 내장 [R4-S03-F4]
5. **pandas-ta 아카이브 위험 → pandas-ta-classic 전환 확정** — 원본 리포 삭제(404), pandas-ta-classic v0.6.20 채택 [R4-S03-F5, Rev.3 해결]
6. **pykrx "치명적 3인조" (PK-3/4/5)** — 침묵적 0원/부분반환/날짜오인 [R4-S03-F6]
7. **배치 데이터 흐름 = Phase 1 유일한 정답** [R4-S03-F7]
8. **DuckDB 10년간 문제 없음** (~40-80MB/5년, 연간 ~50MB 증가) [R4-S03-F8]
9. **알림: osascript(Phase 1) + Telegram(Phase 2+)** [R4-S03-F9]
10. **LOCAL-BLOCKED = 2개** (Naver Finance 스크래핑, API 키 기반 LLM) — Phase 1 핵심 선택지에는 해당 없음 [R4-T03]. ※ R4-S03-F10의 "0개" 주장은 원본 T03의 2개 항목과 충돌하여 정정

#### 28개 장애 모드 카탈로그 [R4-T05]

| 도메인 | 수 | 침묵적? | 주요 방어 |
|--------|-----|---------|----------|
| pykrx | 9 (PK-1~9) | **PK-3/4/5 침묵적** | Gate 1 엄격 검증 |
| DuckDB | 6 (DB-1~6) | 없음 | Exception 처리 |
| Claude Code | 6 (CC-1~6) | 파괴적 없음 | Engine 2는 해석 전용 |
| Network | 4 (NW-1~4) | 없음 | Retry + timeout |
| macOS | 5 (OS-1~5) | OS-1/2 (스케줄 누락) | caffeinate + launchd coalescing |

**"치명적 3인조" (PK-3, PK-4, PK-5)** — Gate 1 엄격 검증이 **유일한** 방어선:

| ID | 장애 | 왜 침묵적인가 | 결과 |
|----|------|-------------|------|
| PK-3 | 전 종목 0원 반환 | pykrx가 0.0 값의 유효한 DataFrame 반환 | 전체 종목 쓰레기 점수 |
| PK-4 | 부분 데이터 (2,500 중 1,800만) | 더 짧은 유효 DataFrame 반환 | 700종목 누락, 편향 분석 |
| PK-5 | 어제 데이터를 오늘로 표시 | 날짜 불일치 예외 미발생 | 오래된 가격 기반 잘못된 신호 |

> 전체 28개 모드의 세부 설명·탐지 방법·폭발 반경·대응 전략은 canonical 문서(`research/reliability-fallback/branch-5-reliability-fallback-analysis.md`) 참조. [R4-T05]

#### 연속 실패 관리 [R4-S04, Rev.4 단순화]

- pybreaker 부적합: 인메모리 상태, 마이크로서비스 패턴 (일일 배치와 불일치)
- **단순 카운터 방식** [Rev.4]: `pipeline_state.json`의 `consecutive_failures` 필드. 3 이상이면 `degraded: true` + 캐시 폴백 실행 + 사용자 알림. 성공 시 카운터 리셋. ~20줄. 마이크로서비스 패턴(OPEN/HALF_OPEN/CLOSED 전이)은 일일 배치에 과잉 — ~~커스텀 파일 기반 ~230줄~~ 불필요
- 임계값: 3회 연속 일일 실패 → degraded 모드 (캐시 기반 분석) → 성공 시 자동 복귀

#### 연동 시나리오 선택: Selective Integration (B) [R4-S02]

Phase별 점진 확장: **Phase 1 = Self-Contained(C)에 가까움** → **Phase 2 = Selective(B)** → **Phase 3 = B+α**.

| 구성 | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|
| MCP | 0개 | DuckDB 읽기전용 | +pykrx-mcp |
| LLM | Claude만 | +Gemini CLI | +Codex CLI, Ollama |
| 데이터 | pykrx + FDR/캐시 | 동일 | +DART |
| 알림 | osascript | +Telegram | +Gmail MCP |
| 도구 | uv + pip 3패키지 | 동일 | +모델 계층화 |

#### 구현량 업데이트

```
기존 (3차): ~3,300-3,700줄
+ 신뢰성 레이어: ~850줄 (연속 실패 카운터, fallback chain, notification, health check) [Rev.4: CB 230줄→20줄 단순화]
= 총 ~4,150-4,550줄
```

---

## 3. 선택지 매트릭스 (LOCAL-* 태그 포함)

### 3.1 아키텍처 선택

| 결정 항목 | 선택 | 대안 (배제 이유) | LOCAL | 출처 |
|----------|------|----------------|-------|------|
| 전체 아키텍처 | Two-Engine Hybrid | 단일 Claude (토큰 파산) | [LOCAL-OK] | R1-S03-F2 |
| 오케스트레이션 | 중앙 집중 (Claude Code 자체) | Agent Swarm (4단계에 과잉), Prefect/Dagster (과잉) | [LOCAL-OK] | R3-S03-F2, R2-T06 |
| 워크플로우 설계 | Hybrid 절차+선언 (~350-400줄) | 순수 절차적 (해석 품질↓), 순수 선언적 (정밀성↓) | [LOCAL-OK] | R3-S03-F1 |
| 데이터베이스 | DuckDB 단일 파일 | SQLite (분석 15-50x 느림) | [LOCAL-OK] | R2-S04 |
| 지표 라이브러리 | **pandas-ta-classic** | pandas-ta (원본 삭제, 공급망 우려), TA-Lib (C 컴파일러, Apple Silicon) | [LOCAL-OK] | R2-S04, Rev.3 |
| 패키지 관리자 | uv | pip/conda (느림, 복잡) | [LOCAL-OK] | R2-S03-F4 |
| 스케줄러 | launchd | cron (macOS에서 비권장), Cloud Routines (로컬 파일 불가) | [LOCAL-OK] | R2-S01 |
| 파이프라인 패턴 | 순차 4단계 | DAG (과잉), 병렬 (불필요) | [LOCAL-OK] | R2-S01 |

### 3.2 스코어링 선택

| 결정 항목 | 선택 | 대안 (배제 이유) | LOCAL | 출처 |
|----------|------|----------------|-------|------|
| 점수 체계 | 6개 서브스코어 복합 (0-100) | 단순 지표 필터 (부가가치↓) | [LOCAL-OK] | R2-S04 |
| VCP 탐지 (Phase 1) | BBand squeeze 프록시 | 전체 VCP (복잡도↑, Phase 3) | [LOCAL-OK] | R2-S03-F7 |
| 가중치 관리 | scoring_config.yaml SOT | 코드 하드코딩 (유지보수↓) | [LOCAL-OK] | R3-S03-F6 |
| 시장 레짐 | 별도 경고 오버레이 | 합산 점수 포함 (해석 비직관적) | [LOCAL-OK] | R2-S01 |
| 시장별 가중치 | 단일 (3개월 후 차등화 검토) | 초기부터 분리 (데이터 부족) | [LOCAL-OK] | R2-S04 |

### 3.3 구현 선택

| 결정 항목 | 선택 | 대안 (배제 이유) | LOCAL | 출처 |
|----------|------|----------------|-------|------|
| 구현 시나리오 (R2) | Pragmatic | Experimental (토큰 2-3x), Established (FM-4,5 미탐지) | [LOCAL-OK] | R2-S02 |
| 구현 시나리오 (R3) | Balanced (~3,280줄) | Full-Defensive (과설계), Rapid-Prototype (신뢰 파괴) | [LOCAL-OK] | R3-S02 |
| 검증 전략 | Targeted Strict (~780줄) | 전수 엄격 (~950줄, 오탐 과다), 행 수만 체크 (FM-4,5 방치) | [LOCAL-OK] | R3-S03-F4 |
| 상태 관리 | 파일 기반 (~520줄) | FSM (~900줄, 4단계에 과설계) | [LOCAL-OK] | R3-S03-F5 |
| 스킬 특화도 | 85% 특화 / 15% 범용 | 100% 특화 (확장↓), 100% 범용 (토큰↑) | [LOCAL-OK] | R3-S03-F3 |

### 3.4 외부 연동 선택

| 결정 항목 | 선택 | 대안 (배제 이유) | LOCAL | 출처 |
|----------|------|----------------|-------|------|
| 연동 시나리오 | Selective Integration (B) | Full (설정 복잡↑), Self-Contained (폴백↓) | [LOCAL-OK] | R4-S02 |
| Phase 1 MCP | 0개 | DuckDB MCP 즉시 (배치에 불필요) | [LOCAL-OK] | R4-S03-F1 |
| 로컬 도구 전략 | Light (brew 0개) | Heavy (brew 2+개, 설치 마찰↑) | [LOCAL-OK] | R4-S03-F4 |
| 데이터 흐름 | 100% 배치 (Phase 1) | 실시간 스트리밍 (데이터 소스가 일일 배치) | [LOCAL-OK] | R4-S03-F7 |
| 연속 실패 관리 | 단순 카운터 (`pipeline_state.json`) [Rev.4] | ~~커스텀 FileCircuitBreaker (과잉)~~, pybreaker (인메모리, 배치 부적합) | [LOCAL-OK] | R4-S04, Rev.4 |
| 데이터 폴백 | 2-tier + FDR 보조 (pykrx→캐시, FDR Top-200 선택적) [Rev.4] | ~~3-tier (FDR 중간 계층 과대)~~, 4-tier (+DART+yfinance, 과잉) | [LOCAL-OK] | R4-S01, Rev.4 |
| 알림 (Phase 1) | osascript 네이티브 | Telegram (설정 마찰, Phase 2) | [LOCAL-OK] | R4-S03-F9 |
| 파일 쓰기 | Atomic write (tmp→rename) | 직접 쓰기 (중간 상태 노출) | [LOCAL-OK] | R4-S04 |

### 3.5 LOCAL-* 태그 전체 요약

- **[LOCAL-OK]**: 모든 핵심 선택지 (4라운드 연속)
- **[LOCAL-PARTIAL]**: 6개 (Agent Teams 실험적, pykrx 네트워크, Claude API 네트워크, Mermaid 렌더링, worktree git 필요, 알림 네트워크) — 모두 캐시/대안 폴백 존재
- **[LOCAL-BLOCKED]**: **2개** — (a) Naver Finance 스크래핑 (높은 유지보수, 법적 위험, 기술적 복잡도) [R4-T03], (b) API 키 기반 LLM 통합 (구독 CLI 인증과 충돌) [R4-T03]. Phase 1 핵심 선택지에는 해당 없음

---

## 4. 축 간 상충 · 미해결 지점

### 4.1 해결된 상충

| # | 상충 | 해결 | 출처 |
|---|------|------|------|
| C1 | 구조 vs 사용성 (WA: 깔끔한 모듈 / OA: 제로 설정) | auto-install 스크립트가 깔끔한 아키텍처를 설치. 사용자는 존재를 모름 | R1-S01 |
| C2 | 시나리오 범위 vs 토큰 (SE: 넓은 커버 / SS: 토큰 예산) | 모든 계산을 Python으로 (토큰 0). 넓은 커버리지 + 최소 토큰 | R1-S01 |
| C3 | 기능 깊이 vs 첫인상 (SE: 포괄 / OA: 즉시 결과) | Phase 1: 일일 스크리닝만 → 검증 → 확장 | R1-S01 |
| C4 | MCP 통합 vs 배치 파이프라인 자립성 | Phase 1 = MCP 없음. Phase 2에서 대화형 탐색 필요 시 DuckDB MCP만 | R2-S01 |
| C5 | VCP 전체 구현 vs Phase 1 실행 속도 | Phase 1은 BBand squeeze 프록시. Phase 3에서 전체 VCP 전환 결정 | R2-S01 |
| C6 | 시장 레짐 필터 vs 단순성 | 점수에 미포함, 별도 경고 오버레이 | R2-S01 |
| C7 | 속도 vs 품질 (Rapid-Prototype vs Balanced) | 절대 기준 1(품질)에 의해 속도 양보. FM-4,5 미탐지 불허 | R3-S01 |
| C8 | MCP 도입 시점 (T01 즉시 vs T02 불필요) | Phase 2에서 DuckDB MCP 도입, CLI 대안 유지 | R4-S01 |
| C9 | 폴백 깊이 (T03 4-tier vs T05 3-tier) | 2-tier + FDR 보조 [Rev.4 재정의]. FDR은 Top-200만 선택적 보조 | R4-S01, Rev.4 |
| C10 | LLM 연동 범위 (T03 4-LLM vs T04 복잡도 우려) | Phase별 점진: Phase 1=Claude, Phase 2=+Gemini, Phase 3=+Codex+Ollama | R4-S01 |

### 4.2 미해결 상충 (PRD에서 결정 필요)

| # | 상충 | 선택지 | 트레이드오프 | 출처 |
|---|------|--------|-----------|------|
| U1 | VCP 간소화 프록시 정확한 사양 | (a) BBand width ≤10%, volume decline ≤60% 초기 앵커 채택 [Rev.4] + 3개월 교정 / (b) 운영 데이터로만 결정 | **초기 앵커 제시됨** (§2.2 VCP 프록시 참조). 한국 시장 실증 미완료이므로 교정 필수 | R2-S04, R3-PL#7, Rev.4 |
| U2 | workflow.md vs Python source SOT 역할 분리 | (a) workflow.md = 명세(WHAT), Python = 구현(HOW) / (b) scoring_config 참조로 workflow.md 파라미터 제거 | 명세 중복 위험 vs 참조 간접 증가 | R3-S03-F1, R3-PL#7 |
| ~~U3~~ | ~~scoring_config.yaml 4개 소비자 동기화 프로토콜~~ **→ 해결 (Rev.4)**: (b) 단일 로딩 라이브러리 **채택**. `config.py` 모듈이 scoring_config.yaml 파싱 + 스키마 검증. 모든 소비자는 `from config import scoring_config` 사용. 별도 "동기화 프로토콜" 불필요 — 단일 로더가 SOT 접근점 | — | R3-PL#6, Rev.4 |
| U4 | Phase 1→2 전환 경계 | **(b) 조건 기반 채택** [Rev.4, Rev.5 순환 보완]: 세 조건 모두 충족 시 전환 — (1) 20 연속 거래일 정상 실행 (Gate 전체 통과), (2) Gate 통과율 95%+, (3) 사용자 교차검증에서 Top 20 중 14개(70%) 이상 '합리적' 평가. 시간 기반 하한: 최소 4주. **[Rev.5 순환 방지]**: 조건 (3)의 "합리적" 판정은 **가중치와 독립적인 정성 기준** — "해당 종목 차트를 열었을 때 기술적 상승 준비가 시각적으로 확인되는가"(방향성 체감). 가중치 교정은 전환 후 Phase 2에서 별도 수행. 가중치가 "가설"이더라도 방향성 감각은 평가 가능 | 객관적 기준 + 순환 논증 방지. 정량(조건 1,2) + 정성(조건 3) 분리로 가중치 의존 탈피 | R4-S04, Rev.4, Rev.5 |
| U5 | Gemini 무료 vs 구독 분기점 | (a) 무료 티어만 / (b) 초기 구독 | 일일 사용량 추정 없이 결정 불가 | R4-S04 |
| ~~U6~~ | ~~pandas-ta 아카이브 대응 시점~~ | **해결 (Rev.3)**: (a) 즉시 pandas-ta-classic 전환 **채택**. 원본 리포 이미 삭제, 전환 비용 = import 경로 변경 1줄, R-4-1 위험 제거 | — | R4-S03-F5, Rev.3 |
| U7 | **launchd 트리거 시점 불일치** — **기본값 18:00 KST 채택** [Rev.5] | (a) 16:30 KST [R4-T04] / **(b) 18:00 KST ← 기본값** [R4-T05, Rev.5] / (c) 18:30 [R1-T01]. **첫 2주 dry-run으로 PL-1 실증 후 보정**. 18:00 근거: KRX 장 마감(15:30) + 데이터 확정 지연(~1-2시간 추정) + 안전 마진. 너무 이르면(16:30) 미확정 위험, 너무 늦으면(18:30) 분석 지연. `scoring_config.yaml`의 `schedule_time` 필드로 사용자 변경 가능 | 기본값 선정 + 2주 보정으로 닭-달걀 교착 해소 [Rev.5] | R4-T04, R4-T05, R1-T01, Rev.5 |
| U8 | **수정주가(adjusted price) 처리 전략** [Rev.3 신설, Rev.5 조건부 분기 확정] | **(a) Hybrid Detection (pykrx adjusted 작동 시)** / **(d) FDR 선택적 재수집 (Plan B — adjusted 미작동 시)** [Rev.5]. 구현 초기 실증 게이트(§5.2 S5)에서 자동 판정. (b) 월간만 = 부적합, (c) FDR 전체 전환 = UX 파괴 | (a)↔(d) 자동 분기로 CRITICAL 위험 완화. 초기 5년 역사적 분할은 별도 1회성 스캔(§5.2 S5) | Rev.3, Rev.5 |

### 4.3 미해결 항목 통합 (Integrated Parking Lot — 25개 중 4개 해결, 2개 격상, 19개 활성)

#### 실증 테스트 필요 (6개)

| # | 항목 | 영향 | 출처 |
|---|------|------|------|
| PL-1 | pykrx 데이터 가용 시점 (장 마감 15:30 후 몇 분?) | launchd 스케줄 시각 결정 | R2-PL#1 |
| PL-2 | 5년 초기 데이터 로딩 소요시간 (~60-90분 추정) | 첫 설치 UX | R2-PL#2 |
| PL-3 | claude -p 구독 계정 호환 | Phase 2 자동화 실현 가능성 | R2-PL#3, GitHub #36324 |
| PL-4 | pandas-ta-classic numba JIT Apple Silicon 호환성 [Rev.4 명칭 정합] | 성능 (비호환 시 비활성화, 영향 미미) | R2-PL#4 |
| PL-5 | ~~pykrx 수정주가(adjusted) 파라미터 동작~~ **→ Phase 1 설계 요구사항으로 격상** [Rev.3] | `get_market_ohlcv_by_ticker()`에 adjusted 파라미터 없음 확인. MA Alignment(20%)+Base Formation(20%)=40% 왜곡 위험. §4.2 U8, §5.2 Section 5 참조 | R2-PL#5, Rev.3 |
| PL-6 | get_market_ohlcv_by_ticker(date) KOSPI+KOSDAQ 동시 반환 여부 | 수집 효율 | R2-PL#6 |

#### PRD 설계 결정 필요 (7개)

| # | 항목 | 영향 | 출처 |
|---|------|------|------|
| PL-7 | VCP 간소화 프록시 정확한 사양 (BBand squeeze/volume 임계값) | 구현 앵커 | R2-PL#7, U1 |
| PL-8 | 시장별 가중치 차등화 (KOSDAQ vs KOSPI) | 3개월 후 분리 검토 선언 | R2-PL#8 |
| PL-9 | 지표 간 충돌 플래깅 (MA 90 + Volume 30 괴리) | 사용자 경고 | R2-PL#9 |
| PL-10 | 한국어 금융 용어 사전 스킬 포함 여부 | 출력 품질 | R2-PL#10, R3-PL#12 |
| PL-11 | workflow.md vs Python source SOT 역할 분리 | 유지보수 | R3-PL#7, U2 |
| PL-12 | 검증 임계값 초기 교정 (dry-run 2주) | 오탐 관리 | R3-PL#8 |
| PL-13 | Phase 1→2 전환 진입 조건 — **조건 기반 확정** [Rev.4] | 로드맵 — U4에서 3가지 객관적 졸업 조건 정의 완료 | R4-S04, U4, Rev.4 |

#### 아키텍처·구현 결정 필요 (7개)

| # | 항목 | 영향 | 출처 |
|---|------|------|------|
| ~~PL-14~~ | ~~scoring_config.yaml 4개 소비자 동기화 프로토콜~~ **→ 해결 (Rev.4)**: `config.py` 단일 로더 패턴 채택. U3 해결 | ~~침묵적 불일치 방지~~ 해결됨 | R3-PL#6, Rev.4 |
| PL-15 | 테스트 전략 (unit/integration/e2e) — **Phase 1 필수로 격상** [Rev.4] | **품질 보장 핵심** — Gate 1/3 단위 테스트 커버리지 90%+ 필수 | R3-PL#9, Rev.4 |
| PL-16 | bootstrap.sh 구체적 구현 상세 | 설치 UX | R3-PL#10 |
| PL-17 | DuckDB 스키마 마이그레이션 | scoring_config 변경 시 | R3-PL#11 |
| PL-18 | Hook 누적 실행 시간 | 기존 15+ hook + 신규 4개 | R3-PL#13 |
| ~~PL-19~~ | ~~Circuit Breaker 상태 지속성~~ **→ 해결 (Rev.4)**: `pipeline_state.json`의 `consecutive_failures` 카운터로 단순화. 별도 CB 상태 불필요 | ~~프로세스 간 상태 유지~~ 해결됨 | R3-PL#14, Rev.4 |
| PL-20 | DNA 상속 긴장 (순수 Implementation이 3-phase에 유효한지) | 워크플로우 구조 | R3-PL#15 |

#### 외부 연동·신규 위험 (5개)

| # | 항목 | 영향 | 출처 |
|---|------|------|------|
| ~~PL-21~~ | ~~pandas-ta 아카이브~~ **→ 해결 (Rev.3)**: pandas-ta-classic v0.6.20 채택. import 경로 변경만. | ~~지표 계산~~ 해결됨 | R4-PL#16, Rev.3 |
| PL-22 | pykrx-mcp 안정성 미검증 (sharebook-kr, 2026 신규) | Phase 2 MCP 도입 | R4-PL#17 |
| PL-23 | 예약 작업 + MCP 초기화 버그 (GitHub #32000, #35899, #43397) | Phase 2 MCP | R4-PL#18 |
| PL-24 | macOS Tahoe Keychain 회귀 (`security -w` hang) | 인증 | R4-PL#20 |
| PL-25 | FDR 폴백 속도 (~42분, 2,500 ticker × 1 req/sec) | Top-200만 폴백 고려 | R4-PL#21 |

---

## 5. PRD 방향 조언 (골격 수준)

> 아래는 4개 라운드의 S04(PRD 방향) 문서를 통합한 섹션별 지침이다. **결론이 아니라 선택지와 근거를 유지한다.**

### 5.1 PRD 핵심 관점: "Two Engines, One Product"

- Engine 1 (Python): 결정론적, 테스트 가능, 토큰 0
- Engine 2 (Claude Code): 적응적, 한국어, 토큰 소비
- 경계: `output/summary.md` (Engine 1이 쓰고, Engine 2가 읽음)
- 경계 위반은 지속가능성 파괴 (Claude 계산 = 토큰 파산)

### 5.2 섹션별 방향

#### Section 1: 문제 정의
- 사용자 관점에서 작성 (물리적 불가능성: ~2,500종목 수동 검토)
- 기존 도구(Kiwoom HTS, Naver Finance, TradingView) 보완 관계 명시
- **16개 시나리오 매트릭스** [R1-T02]: A1-A4(일일 스크리닝), B1-B4(심층 분석), C1-C4(알림/모니터링), D1-D4(커스텀/고급). 빈도/복잡도/자동화 가능성/가치 평가 포함. Phase 1은 A2(장후 스크리닝) 집중, B1-B4/C1-C4/D1-D4는 Phase 2-3 로드맵
- 출처: R1-S04, R1-T02

#### Section 2: 점수 산출 방법론 — **PRD의 지적 핵심**
- 6개 서브스코어 정확한 수식 + pandas-ta 매핑
- 기본 가중치(20/20/20/15/15/10) + "가설" 선언
- scoring_config.yaml SOT + 변경 프로토콜
- VCP Phase 1 프록시 정의 + Phase 3 전환 기준
- 시장 레짐 경고 오버레이 (점수 미포함)
- 출처: R1-S04, R2-S04, R3-S04

#### Section 3: 아키텍처
- 4-Layer 아키텍처 다이어그램 (Scheduler → Python → Claude → User)
- Two-Engine 코드 수준 구체화 (R3 반영)
- 파일 시스템 레이아웃
- 기술 선택 근거 (DuckDB > SQLite, pandas-ta > TA-Lib 등 각각 트레이드오프)
- 오케스트레이션 패턴: "Claude Code 자체가 orchestrator" (7-1-4 근거)
- 연동 경계 선언 (Phase 1 외부 = pykrx 하나)
- MCP/LLM 로드맵 (Phase 2+)
- 출처: R1-S04, R2-S04, R3-S04, R4-S04

#### Section 4: 사용자 경험
- **설치 5단계 여정** [R2-T04, R2-S04, Rev.3 보충]:
  1. Terminal 열기
  2. `curl -LsSf https://astral.sh/uv/install.sh | sh` (uv 설치)
  3. `./bootstrap.sh` (Python 3.12 + 의존성)
  4. KRX Data Marketplace 등록 (https://data.krx.co.kr/ — 네이버/카카오 소셜 로그인, **무료**)
  5. KRX 자격증명 입력 — **대화형 프롬프트** [Rev.5: "텍스트 수정 불가" 사용자 대응]: bootstrap.sh가 `read -p "KRX ID: "` / `read -sp "KRX PW: "`로 대화형 입력 → 자동 `.env` 생성. 사용자는 텍스트 편집기를 열 필요 없음. Power User는 직접 `.env` 편집 가능(기존 파일 존재 시 스킵)
- **bootstrap.sh 구체적 구현** [R2-T04 lines 144-159, Rev.3 보충, Rev.5 대화형 프롬프트 추가]: 조건부 uv 설치 → `uv python install 3.12` → `uv venv` → `uv pip install pykrx duckdb pandas-ta-classic` → import 검증 → **KRX 자격증명 대화형 입력** (`.env` 미존재 시 `read -p`로 수집 → `.env` 자동 생성) → pykrx 로그인 검증. 약 15줄. DuckDB 초기화는 첫 실행 시 자동(bootstrap.sh 미포함). 목표: 1-2분. **[Rev.5 핵심]**: "텍스트 수정 불가"(§1.3) 사용자가 텍스트 편집 없이 설치를 완료할 수 있는 유일한 경로
- **KRX 등록 = 최대 마찰점** [R2-T04, Rev.3 보충]: 도구 설치보다 계정 등록이 더 큰 장벽. 소셜 로그인(Naver/Kakao)으로 마찰 최소화. 자격증명 저장: `.env` 파일 (plaintext 환경변수 — 설정 단순성 우선, Keychain 대비 보안 약함. macOS Tahoe Keychain 회귀 PL-24 회피). **자격증명 유효성 검증** [Rev.4]: pykrx 로그인 실패 시 exit code 11 + 한국어 메시지 출력. **자격증명 갱신 경로** [Rev.5: "텍스트 수정 불가" 대응]: 로그인 실패 감지 시 **대화형 재입력 프롬프트** 자동 실행 (`bootstrap.sh --reauth`) — 사용자가 직접 .env를 편집할 필요 없음. "⚠️ KRX 로그인 실패. 비밀번호를 다시 입력해주세요:" → 대화형 수집 → .env 덮어쓰기. Power User는 직접 .env 편집 가능
- **첫 실행 경험** [R2-S04 line 75, Rev.3 보충]: 5년 초기 데이터 로딩 60-90분 소요 → **진행률 표시 필수** + **당일 데이터로 즉시 첫 분석 제공**(백그라운드 로딩 전략). 무반응 60-90분 = 비기술 사용자 확정 이탈
- 일일 사용: `/scan` → **3-5분 대기** [R2-T05, Rev.3 보충] → summary.md 해석 → Naver/TradingView 링크
- 6개 커맨드: /scan, /top, /analyze, /backtest, /regime, /anomalies
- 에러 메시지 한국어화 — **ExitCode enum (0-79) + EXIT_MESSAGES_KO** [R4-T05]:

  | 범위 | 카테고리 | 예시 메시지 |
  |------|---------|-----------|
  | 0 | 성공 | "파이프라인 성공적으로 완료" |
  | 1-9 | 일반 오류 | "설정 파일 누락" |
  | 10-19 | 데이터 수집 | "KRX 서버 연결 실패" |
  | 20-29 | 분석 | "기술 지표 계산 실패" |
  | 30-39 | 스코어링 | "점수 계산 범위 이상" |
  | 40-49 | 리포트 | "요약 보고서 생성 실패" |
  | 50-59 | 데이터베이스 | "DuckDB 파일 손상" |
  | 60-69 | (예약) | — [Rev.3 주석: 원본 R4-T05에서 미정의. PRD에서 할당 결정] |
  | 70-79 | 시스템 | "디스크 공간 부족" |

- 점진적 노출: Layer 0 (기본) → Layer 1 (NL) → Layer 2 (flags) → Layer 3 (config) → Layer 4 (source)
- 출처: R1-S04, R2-S04, R3-S04, R4-S04

#### Section 5 (신규): 신뢰성·검증
- 4-Gate Targeted Strict 아키텍처
- 실패 모드 대응 매트릭스 (FM-1~FM-6)
- 28개 장애 모드 카탈로그 (§2.4 전체 목록 참조)
- 연속 실패 관리 (단순 카운터 ~20줄) [Rev.4 단순화]
- Fail-fast 기본 + 선택적 Degradation 구역
- 품질 배지 (summary.md 최상단)
- 첫 2주 dry-run 모드
- **5개 이상 탐지 규칙** [R3-T03]:
  1. Volume-Price Divergence: Volume > 80 + Trend < 30 → 조작 위험
  2. Perfect Score Syndrome: 6개 서브스코어 전부 5점 이내 차이 → 계산 오류 의심
  3. Micro-Cap Trap: 종합 > 80 + 시가총액 < 500억 원 → 유동성 위험
  4. Stale Data: 마지막 거래일 > 5영업일 전 → 거래 정지/상장 폐지 의심
  5. Single-Indicator Dominance: 1개 > 95, 나머지 전부 < 50 → 왜곡된 점수
- 출처: R3-S04, R4-S04, R3-T03

**수정주가(Adjusted Price) 처리 전략** [Rev.3 심층조사 — Phase 1 설계 요구사항]:

배치 API `get_market_ohlcv_by_ticker(date)`는 KRX 원본 가격만 반환 (adjusted 파라미터 없음). 한국 시장 연간 액면분할 15-21건, 주로 고모멘텀 대형주(삼성전자, 네이버, SK텔레콤 등). 분할 시 SMA-200 불연속 → MA Alignment(20%)+Base Formation(20%)=40% 왜곡.

| 전략 | 설명 | 장단점 |
|------|------|--------|
| **(a) Hybrid Detection + Targeted Re-fetch (권장)** | 일일 배치 수집 유지 + 전일 대비 종가 >30% 변동 탐지 → 플래깅 종목만 `get_market_ohlcv_by_date(ticker, adjusted=True)` 개별 재수집 + 주간 정합성 스캔 | 정확도 최고, 일일 추가 비용 ~수초(분할 발생 시만). pykrx Issue #162(adjusted 미작동) 위험 존재 → FDR 교차검증 |
| (b) 월간 전체 재수집만 (현행 §5.2 S6) | 월 1회 전체 재수집 시 수정주가 반영 | 분할 후 최대 30일간 오류 점수 생산 — **금융 도구로 부적합** |
| (c) FDR 기본 소스 전환 | FinanceDataReader 기본 수정주가 반환 | 일일 수집 속도 ~42분(2,500 ticker × 1 req/sec) — 배치 UX 파괴 |
| **(d) FDR Top-200 선택적 + 자체 비율 보정 (Plan B)** [Rev.5 신설] | 분할 탐지 시 FDR로 해당 종목만 수정주가 수집 (1 req/sec × 1종목 = 1초). `adjusted=True` 미작동 확인 시 자동 폴백 경로 | pykrx Issue #162 실작동 불가 시 **유일한 실행 가능 대안**. 속도 영향 무시 가능(분할 발생 종목만, 연 15-21건) |

**⚠️ 실증 게이트 (Implementation Gate)** [Rev.5 — P0-1 해결]:

PRD 구현 초기에 **반드시** 다음 분기를 실행:
1. `get_market_ohlcv_by_date(ticker, adjusted=True)` 실제 호출 테스트 (분할 이력 있는 종목: 삼성전자 2018-05-04)
2. **작동 시** → 전략 (a) 채택, FDR 교차검증은 주간 정합성 스캔에 한정
3. **미작동 시** (pykrx Issue #162 재현) → 전략 (d) 자동 채택: 분할 탐지 → FDR `DataReader(ticker, start, end)` 개별 수집 → 비율 계산 → DuckDB 역사 데이터 일괄 보정
4. 이 게이트는 **bootstrap.sh 첫 실행 시 자동 판정** — 결과를 `pipeline_config.yaml`의 `adjusted_price_strategy: "a" | "d"`에 기록

**역사적 분할 처리 전략 (Initial Load)** [Rev.5 — P0-1 해결]:

초기 5년 로드 시 `get_market_ohlcv_by_ticker(date)`는 원가격만 반환 → 5년간 75-105건 역사적 분할의 SMA 불연속이 **Hybrid Detection(일일 delta 탐지)으로는 포착 불가**:
- **해결**: 초기 로드 완료 후 1회성 **역사적 분할 스캔** 실행 — DuckDB에 적재된 전체 시계열에서 `close[t]/close[t-1]` > 1.5 또는 < 0.5인 모든 날짜·종목을 추출 → 해당 종목의 수정주가를 (a) 또는 (d) 전략으로 재수집 → 비율(분할 계수) 계산 → 분할 이전 전체 가격 일괄 보정
- **시점**: 초기 로드(60-90분) 직후, 첫 분석 실행 전. 추가 소요 ~5-10분(분할 이력 종목 75-105건 × FDR 1초/종목)
- **Gate 1 Day-1 제한** [Rev.5]: 첫 실행 시 t-1 데이터가 없으므로 분할 탐지 서브게이트는 **2일차부터 활성화**. Day 1은 역사적 분할 스캔이 대체

관련 Gate 확장: Gate 1에 **분할 탐지 서브게이트** 추가 — `close[t]/close[t-1]` > 1.5 또는 < 0.5 + 시장 전체 비연동 → corporate action 플래그. **2일차부터 활성** [Rev.5].

**시장 엣지 케이스 처리** [R3-T04 lines 157/1677/2102, Rev.3 보충]:

| 엣지 케이스 | Phase 1 처리 | Phase 2+ | 출처 |
|------------|-------------|----------|------|
| KRX 휴일 (추석/설날/대체공휴일) | 주말 휴리스틱만 (Gate 1 date freshness). 휴일에 실행 시 "어제 데이터로 분석" 폴백 | `pandas_market_calendars` XKRX 정밀 휴일 탐지 | R3-T04 line 157 |
| IPO (신규 상장) | Gate 1 종목 수 ±2% 허용 범위 (~50종목) | 신규 종목 자동 탐지 + 기본 데이터 부족 경고 | R3-T04 line 1677 |
| 상장폐지 | Stale Data 탐지 규칙 (마지막 거래일 > 5영업일) | DuckDB에서 종목 비활성 마킹 | R3-T03 rule #4 |
| 액면분할/병합 | **분할 탐지 Gate** (위 수정주가 전략 참조) | 기업행위 캘린더 연동 | R3-T04 line 2102 |
| 주식배당/무상증자 | 월간 재수집으로 반영 | targeted re-fetch 확장 | Rev.3 |

- 출처: R3-S04, R4-S04, R3-T03, R3-T04, Rev.3

#### Section 6: 데이터 전략
- pykrx 1.2.8 + KRX 로그인 필수화 반영
- **pykrx 속도 제한** [R2-T04, Rev.3 보충]: 비공식 스크래퍼 — KRX 과도 트래픽 IP 차단 명시, **"차단 해제 불가"** 정책. 최소 `time.sleep(1)` 권장. `get_market_ohlcv_by_ticker(date)`: 전 종목 1회 요청(2,500 개별 요청 불필요). IP 차단 시 pykrx-openapi(KRX 공식 API, 1 영업일 API 키 승인) 폴백 가능 [R2-T04]
- **2-tier 폴백 + FDR 보조** [Rev.4 단순화]: pykrx(기본) → DuckDB 캐시(폴백). FDR은 Top-200 종목 보조 수집원으로 선택적 활용 (~42분 소요, 전체 폴백으로 부적합). 실질 3-tier 표현은 FDR 제한(Top-200만, 속도)을 과대 포장
- 수집 전략: get_market_ohlcv_by_ticker(date) 배치 API
- **일일 증분 처리 시간: 3-5분** [R2-T05, Rev.3 보충]: 일일 당일 OHLCV 수집(2,500행) → DuckDB 추가 → 캐시된 과거 데이터로 지표 재계산 → 전 종목 재점수. 초기 5년 로딩(60-90분)과 구분
- ETL: 일일 증분 + 주간 정합성 + 월간 전체 재수집(수정주가) + **분할 탐지 시 즉시 targeted re-fetch** [Rev.3]
- **DuckDB 스키마 (3+3 테이블)** [R2-T04, R2-T02, Rev.3 보충]:

  핵심 3테이블 DDL [R2-T04, Rev.3 스키마-수식 정합성 보정]:
  ```sql
  CREATE TABLE ohlcv (
      ticker VARCHAR, date DATE,
      open INTEGER, high INTEGER, low INTEGER, close INTEGER,
      volume BIGINT, market_cap BIGINT,
      PRIMARY KEY (ticker, date)
  );
  CREATE TABLE indicators (
      ticker VARCHAR, date DATE,
      -- 한국 관례 기간 (일반 분석용)
      sma5 FLOAT, sma20 FLOAT, sma60 FLOAT, sma120 FLOAT,
      -- Minervini SEPA 기간 (MA Alignment 스코어링 필수)
      sma50 FLOAT, sma150 FLOAT, sma200 FLOAT,
      rsi14 FLOAT, macd FLOAT, macd_signal FLOAT,
      adx14 FLOAT, bbands_upper FLOAT, bbands_lower FLOAT, bbands_squeeze FLOAT,
      atr14 FLOAT, obv BIGINT, volume_sma20 FLOAT,
      PRIMARY KEY (ticker, date)
  );
  CREATE TABLE scores (
      ticker VARCHAR, date DATE,
      ma_alignment FLOAT, base_formation FLOAT, volume_behavior FLOAT,
      momentum FLOAT, breakout_readiness FLOAT, relative_strength FLOAT,
      total_score FLOAT,
      PRIMARY KEY (ticker, date)
  );
  ```

  > ※ 원본 R2-T04 DDL은 한국 관례 SMA 기간(5/20/60/120/200)만 정의. 그러나 §2.2 MA Alignment SEPA 8기준은 SMA(50)/SMA(150)/SMA(200)을 요구. Rev.3 정합성 검증에서 불일치 탐지 → sma50, sma150 컬럼 추가. sma60, sma120은 한국 시장 관례·Phase 2 확장용으로 보존.

  메타데이터 테이블 [R2-T02, Rev.4 Phase 구분]: Phase 1 필수 — `scan_history` (실행 메타). Phase 2 예약 — `user_watchlist` (사용자 관심 종목), `alerts` (알림 추적). Phase 1 DDL에서 watchlist/alerts 테이블 생성 지연

- 볼륨 예측: 5년 ~40-80MB, 연간 ~50MB
- **일일 자동 백업** [Rev.4]: 파이프라인 시작 전 `shutil.copy2(stocks.duckdb, stocks.duckdb.bak)`. DuckDB 단일 파일 손상 시 `.bak` 자동 복원. 추가 디스크: ~80MB(5년 기준). 5년치 데이터가 단일 파일에 집중되므로 백업 없이는 손상 = 60-90분 재수집(pykrx IP 차단 위험 결합 시 복구 불가능)
- Atomic write 패턴 (tmp→rename)
- summary.md 인터페이스: YAML 프론트매터 9필드 + Markdown 본문 (§1.2 스키마 상세 참조, ~15-25KB, ~5,000-8,000 토큰)
- 출처: R1-S04, R2-S04, R2-T04, R2-T05, R4-S04, Rev.3

#### Section 7: 지속가능성·토큰 경제
- 일일 ~23K-25K 토큰/세션
- Max 20x 대비 ~10% 사용 → 여유 충분
- Agent SDK Credit: $200/월, ~$1.50/월 소비
- 모델 계층화: 루틴=Sonnet, 심층=Opus (Phase 2)
- 총 월비용: ~$240 (기존 구독, 추가 비용 $0)
- 특화 스킬 절약: 일일 ~1,250, 월 ~37,500 토큰
- 출처: R1-S04, R2-S04, R3-S04, R4-S04

#### Section 8: 위험 등록부

전 라운드 위험 통합:

| ID | 위험 | 영향 | 확률 | 완화 | 출처 |
|----|------|------|------|------|------|
| R-1-1 | pykrx 기능 유지 | CRITICAL | HIGH | 2-tier 폴백 + FDR 보조 + 추상화 계층 [Rev.4] | R1-S02 |
| R-1-2 | 점수 시스템 유용성 | CRITICAL | MED | Minervini/Weinstein 기반 + 교정 | R1-S02 |
| R-1-3 | 비기술 사용자 설치 | HIGH | HIGH | bootstrap.sh + uv + **대화형 자격증명 프롬프트** [Rev.5: "텍스트 수정 불가" 사용자 대응] | R1-S02, Rev.5 |
| R-1-4 | 구독 한도 | HIGH | MED | Branch B (80-90% 절약) | R1-S02 |
| R-1-5 | 사용자 과신 | MED | MED | 면책조항 + 분석 프레이밍 | R1-S02 |
| R-2-1 | KRX 정책 재변경 | HIGH | LOW | 2-tier 폴백 + FDR 보조 [Rev.4] | R2-S04 |
| R-2-2 | VCP 프록시 정확도 | MED | MED | Phase 3 백테스팅 비교 | R2-S04 |
| R-2-3 | KOSDAQ/KOSPI 가중치 미분리 | MED | HIGH | 3개월 후 검토 | R2-S04 |
| R-2-4 | **수정주가 미처리 → CRITICAL 격상** [Rev.3] — 점수 왜곡 (데이터 품질 위험) | **CRITICAL** | **HIGH** | Hybrid Detection + Targeted Re-fetch (§5.2 S5). `get_market_ohlcv_by_ticker()`에 adjusted 없음 확인. 연간 15-21건 분할, 40% 점수 왜곡 | R2-S04, Rev.3 |
| R-2-5 | claude -p 호환 불확실 | MED | MED | GitHub #36324 추적 | R2-S04 |
| R-2-6 | 침묵적 실패 | CRITICAL | HIGH | 4-Gate 검증 | R2-S04 |
| R-3-1 | scoring_config vs 코드 불일치 | HIGH | MED | `config.py` 단일 로더 패턴 (U3 해결) [Rev.4] | R3-S04, Rev.4 |
| R-3-2 | workflow.md vs source SOT 경합 | MED | HIGH | 역할 분리 선언 | R3-S04 |
| R-3-3 | Hook 누적 실행 시간 | LOW | MED | timeout + 모니터링 | R3-S04 |
| R-3-4 | Agent Teams 실험적 | MED | MED | Phase 2까지 추적 | R3-S04 |
| R-3-5 | 검증 게이트 오탐 (~3%) | LOW | HIGH | dry-run 2주 | R3-S04 |
| ~~R-4-1~~ | ~~pandas-ta 아카이브~~ **→ 해결 (Rev.3)** | ~~HIGH~~ | ~~HIGH~~ | pandas-ta-classic v0.6.20 채택. 원본 리포 이미 삭제. import 변경 1줄 | R4-S04, Rev.3 |
| R-4-2 | pykrx-mcp 안정성 | MED | MED | Phase 2 전 실증 | R4-S04 |
| R-4-3 | MCP 초기화 버그 | MED | MED | GitHub #32000 추적 | R4-S04 |
| R-4-4 | Codex CLI git hang | LOW | MED | git repo 내 실행 | R4-S04 |
| R-4-5 | macOS Keychain 회귀 | MED | HIGH | Python keyring 대안 | R4-S04 |
| R-4-6 | FDR 폴백 속도 (~42분) | MED | LOW | Top-200만 폴백 | R4-S04 |
| R-5-1 | **수정주가 배치 API 기능 부재** [Rev.3 신규, Rev.5 완화 강화] — API 역량 공백. **실증 게이트 + 자동 분기로 완화** [Rev.5]: (1) 구현 초기에 `adjusted=True` 실증, (2) 작동 시 전략 (a), 미작동 시 전략 (d) 자동 채택, (3) 초기 로드 후 역사적 분할 1회성 스캔 필수. 잔존 위험: FDR마저 분할 종목 수정주가 미반환 시 수동 보정 필요 | CRITICAL | HIGH | 실증 게이트(§5.2 S5) + 전략 (a)↔(d) 자동 분기 + 역사적 분할 스캔 | Rev.3, Rev.5 |
| R-5-2 | **시장 엣지 케이스 미처리** (KRX 휴일, IPO, 상장폐지, 액면분할) [Rev.3 신규] | HIGH | HIGH | Phase 1: 휴리스틱 + Gate 허용 범위. Phase 2: 정밀 캘린더 | Rev.3 |
| R-6-1 | **스테일 flock 락 → 파이프라인 영구 차단** [Rev.4 신규] | HIGH | MED | PID 기반 스테일 락 자동 해제 + 한국어 메시지 (§2.3) | Rev.4 |
| R-6-2 | **DuckDB 단일 파일 손상 → 전체 데이터 소실** [Rev.4 신규] | HIGH | LOW | 일일 자동 백업 (`stocks.duckdb.bak`). ~80MB 추가 디스크 (§5.2 S6) | Rev.4 |
| R-6-3 | **검증 게이트 자체의 미검증 → 신뢰성 순환 논증** [Rev.4 신규] | CRITICAL | HIGH | Gate 1/3 단위 테스트 커버리지 90%+ 필수 (§6.1 G1 격상) | Rev.4 |

#### Section 9: 비목표 (명시적 배제)

| 항목 | 분류 | 이유 | 재검토 시점 |
|------|------|------|-----------|
| 실시간 인트라데이 | never (현재) | 완전히 다른 아키텍처 (WebSocket, HTS API) | 일일 스크리닝 안정화 후 |
| 자동 주문 집행 | never | 규제/위험/신뢰성 = 별도 도메인 | 별도 프로젝트 |
| 기본적 분석 | later | 별도 도메인, 기존 MCP 활용 가능 | Phase 3+ |
| 뉴스 감성 분석 | later | 별도 NLP 프로젝트 규모 | 기본 시스템 검증 후 |
| 차트 시각화 | never | TradingView 사용 | — |
| 멀티에이전트 토론 | never | Nature 2026: 다수 압력 순응, 단일 동등 성능 | — |
| MCP 서버 (Phase 1) | later | 배치에 중복 | Phase 2 |

---

## 6. 남은 공백 (추가 조사 필요 영역)

### 6.1 조사에서 다루지 않은 축 (역방향 점검)

| # | 미조사 영역 | PRD 영향도 | 근거 |
|---|-----------|-----------|------|
| G1 | 테스트 전략 (unit/integration/e2e 설계) — **Phase 1 필수 요구사항으로 격상** [Rev.4] | **CRITICAL** | R3-3층위에서 식별. Gate 1/3 단위 테스트 커버리지 90%+ 필수. FM-1~FM-6 각각에 대한 회귀 테스트 필수. 최소 전략: unit(gate 로직) + integration(pipeline e2e with fixture data). 검증 게이트가 검증되지 않으면 시스템 전체 신뢰성 주장이 순환 논증 [Rev.4 적대적 성찰] |
| G2 | CI/CD 파이프라인 | LOW | Phase 1 불필요 (로컬 실행). pre-commit hook 수준 |
| G3 | 사용자 투자 스타일·철학 | MED | R1-3층위에서 식별. 점수 가중치 초기값에 영향 |
| G4 | 장 종료 후 데이터 확정 시점 | HIGH | R1-3층위에서 식별. launchd 스케줄 결정에 필수 (PL-1과 동일) |
| ~~G5~~ | ~~수정주가 반영 방식~~ **→ Rev.3 심층조사 완료** | ~~HIGH~~ → §5.2 S5 반영 | `get_market_ohlcv_by_ticker()`에 adjusted 없음 확인. Hybrid Detection 전략 수립. §4.2 U8 참조 |
| G6 | 모니터링 대시보드 | LOW | Phase 1 파일 로그 충분 |
| G7 | 백업/클라우드 동기화 | LOW | Phase 2+ |
| G8 | AI Agent SDK (Anthropic) 연동 | MED | Phase 2+ 자동화 영향. R2에서 부분 조사 |
| G9 | 에러 코드 표준화 체계 | LOW | R3-3층위. 게이트 에러 코드 설계 |
| G10 | 로깅 표준 (JSON structured) | LOW | R3-3층위 |
| G11 | **macOS 버전 호환 매트릭스** [Rev.3 신규] | MED | Tahoe만 언급. Sonoma/Ventura 지원 범위, Apple Silicon/Intel 구분, 버전별 jq 내장 여부 미조사 |
| G12 | **시스템 요구사항 (RAM/CPU/디스크)** [Rev.3 신규] | MED | 전체 설치 크기, 최소 RAM/CPU, 파이프라인 메모리 피크 미조사 |
| G13 | **오프라인 모드 명시적 선언** [Rev.3 신규] | LOW | 2-tier 폴백(캐시) 존재하나 "네트워크 없이 캐시 분석 가능" 명시 없음 [Rev.4 용어 정합] |

### 6.2 조사했으나 결론 미도달

| # | 항목 | 상태 | 관련 상충 |
|---|------|------|---------|
| I1 | VCP 프록시 임계값 | 데이터 부재로 결정 불가 | U1 |
| I2 | KOSDAQ vs KOSPI 가중치 차등화 | 3개월 운영 데이터 필요 | — |
| ~~I3~~ | ~~pandas-ta 아카이브 대응 시점~~ **→ 해결 (Rev.3)** | pandas-ta-classic v0.6.20 채택. U6 해결 | ~~U6~~ |
| I4 | Gemini 무료 티어 충분성 | 일일 사용량 추정 미실시 | U5 |

---

## 통합 품질 검증 — 자기 점검

### 1층위 (사실 확인): 반영되지 않은 파일

| 파일 | 반영 상태 |
|------|---------|
| 42개 원본 파일 전체 | ✅ 반영 완료 (Rev.2 감사 보정 포함) |

누락 파일: **없음**. (Rev.1에서 "37개"로 기재되었으나 실제 42개 확인 후 정정.)

### 2층위 (구조 분석): PRD 제작 입력으로 사용 시 먼저 무너지는 지점

1. ~~**수정주가 처리 전략 (U8)**~~ [Rev.3 격상, **Rev.5 조건부 분기 해결**]: 실증 게이트(§5.2 S5)로 (a)↔(d) 자동 분기 + 역사적 분할 1회성 스캔 추가. 잔존 위험: FDR마저 수정주가 미반환 시 수동 보정 필요 (§5.2 S5 참조)
2. **VCP 프록시 사양 공백 (U1)**: Section 2(점수 방법론) 작성 시 BBand squeeze 임계값이 없으면 구현 앵커 부재. → 구현 단계에서 데이터 기반 교정 필요를 PRD에 명시해야.
3. ~~scoring_config.yaml 동기화 프로토콜 (U3)~~: **Rev.4에서 해결** — `config.py` 단일 로더 패턴 채택.
4. **workflow.md SOT 역할 미선언 (U2)**: workflow.md가 명세인지 실행 가이드인지 경계가 모호하면 코드와 문서 동기화 실패 → Section 3에서 선언 필요.
5. **테스트 전략 부재 (G1)** — **Phase 1 필수 요구사항으로 격상** [Rev.4]: Gate 1/3 단위 테스트 90%+ 커버리지 필수. 검증 게이트가 검증되지 않으면 시스템 전체 신뢰성이 순환 논증. PRD에서 별도 섹션 필수.
6. ~~pandas-ta 아카이브 타이밍 (U6)~~: **Rev.3에서 해결** — pandas-ta-classic v0.6.20 채택.
7. ~~**비기술 사용자 .env 편집 불가능**~~ [**Rev.5 해결**]: bootstrap.sh 대화형 프롬프트(`read -p`)로 자격증명 수집 → .env 자동 생성. "텍스트 수정 불가" 사용자가 텍스트 편집 없이 설치 완료 가능.

### 3층위 (역방향 점검): 다루지 않은 것

위 Section 6(남은 공백)에 포함. Rev.5 갱신된 우선순위:
- ~~**수정주가 처리** (U8)~~ — Rev.5 실증 게이트 + 자동 분기로 실행 경로 확보. 잔존: FDR 수정주가 미반환 시 수동 보정
- **시장 엣지 케이스** (R-5-2) — Phase 1 최소 처리 반영됨. 정밀 휴일 캘린더는 Phase 2
- **테스트 전략** (G1) — 품질 보장 핵심이나 4개 라운드 범위 밖
- **macOS 버전 호환 매트릭스** (G11) — PRD 지원 범위 선언 필요
- **사용자 투자 스타일** (G3) — 가중치 초기값 교정에 영향
- ~~**launchd 트리거 시점** (U7)~~ — Rev.5 기본값 18:00 KST 채택 + 2주 보정 선언으로 교착 해소
- ~~**시간 예산 모호성**~~ — Rev.5 명확화: "3-5분"은 결과 확인 시간, 파이프라인은 백그라운드 자동 실행

---
