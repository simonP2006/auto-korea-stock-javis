---
round: 2
type: synthesis
topic: prd-direction
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
title: "2차 조사 PRD 방향 조언 — 기술·이론 축 반영"
inputs:
  - "synthesis/S01-tech-discussion.md"
  - "synthesis/S02-scenarios.md"
  - "synthesis/S03-key-findings.md"
---

# S04: PRD 방향 조언 (2차 — 기술·이론 축)

## PRD 섹션별 기술·이론 축 반영 방향

### Section 2: 점수 산출 방법론 — **가장 중요**

**반영 관점**: 점수 산출 공식은 PRD의 지적 핵심. 2차 조사에서 확보한 구체적 지표 매핑과 임계값이 구현 앵커.

**반영 내용**:
- 6개 서브스코어의 **정확한 수식** (T5):
  - MA Alignment: Minervini SEPA 8기준 → Boolean 합산 × 가중치 → 0-100
  - Base Formation: Weinstein 4단계 분류(SMA 기울기 + 가격 위치) → 0-100 매핑
  - Volume Behavior: Wyckoff 3지표(OBV 추세 + 상승/하락 거래량 비율 + 수축도) → 0-100
  - Momentum: RSI(14) + MACD + ADX(14) 복합 → 0-100
  - Breakout Readiness: Phase 1은 간소화 프록시(BBand squeeze + volume decline)
  - Relative Strength: IBD RS Rating 가중 수익률(40% 3mo + 20% 6mo + 20% 9mo + 20% 12mo) → 백분위
- 기본 가중치(20/20/20/15/15/10)와 **"가설" 선언** — 3개월 운영 데이터 후 교정
- 점수 해석 임계값: 80+=완성 임박, 60-79=진행 중, 40-59=초기, <40=미성숙
- **VCP Phase 1 프록시 명시**: BBand 폭 수축 + 거래량 감소를 대리 지표로. 전체 VCP(스윙 포인트 탐지)는 Phase 3.
- 시장 레짐 경고 오버레이: KOSPI 200일 SMA 하회 시 경고(점수에 미포함, 별도 표시)

### Section 3: 아키텍처 — 기술 선택 근거

**반영 관점**: 모든 기술 선택에 "왜"를 포함. 2차 조사에서 각 선택지의 트레이드오프가 명확히 드러남.

**반영 내용**:
- **DuckDB > SQLite**: 분석 쿼리 15-50x 빠름, 컬럼형 압축, 2,500종목 × 5년 = 50-150MB (T4 검증)
- **pandas-ta > TA-Lib**: 순수 Python, Apple Silicon 호환, 설치 마찰 0, 130+ 지표 네이티브 (T4 검증)
- **pykrx (KRX 로그인 필수)**: v1.2.8, 무료 등록, `get_market_ohlcv_by_ticker` 배치 API (T4 검증)
- **uv > pip/conda**: Python 자동 설치, 80x 빠른 venv, 비기술 사용자 적합 (T4 검증)
- **MCP 불포함 이유**: 배치 파이프라인에 중복(T4), Phase 2에서 대화형 탐색 필요 시 재검토
- **순차 파이프라인 > 오케스트레이션 프레임워크**: 4단계에 Prefect/Dagster 과잉 (T3 검증)
- **멀티에이전트 불포함 이유**: Nature 2026 연구, 단일 에이전트 동등 성능, 토큰 2x (T5 검증)

**아키텍처 다이어그램 소재**:
```
launchd (StartCalendarInterval)
    ↓
Python Pipeline (main.py)
    ├─ collect.py → pykrx → DuckDB (ohlcv)    [서킷 브레이커]
    │   └─ Gate 1: 행 수, 가격 합리성
    ├─ analyze.py → pandas-ta → DuckDB (indicators)
    │   └─ Gate 2: NaN 비율, 지표 범위
    ├─ score.py → DuckDB (scores)
    │   └─ Gate 3: 점수 분포, 이상탐지
    └─ report.py → summary.md
                      ↓
Claude Code (해석 + 한국어 보고)
    ├─ SessionStart Hook → 데이터 신선도 확인
    ├─ /scan 명령어 → summary.md 읽기 + 분석
    └─ Skills (stock-scanner/SKILL.md → 점수 방법론)
```

### Section 4: 사용자 경험

**반영 관점**: 비기술 사용자의 설치·사용 여정을 기술 스택 현실과 정합.

**반영 내용**:
- **설치 여정 5단계** (T4 검증): Terminal 열기 → curl로 uv 설치 → bootstrap.sh 실행 → KRX 계정 등록(무료, 소셜 로그인) → .env에 KRX_ID/PW 설정. 목표: **15분**.
- **일일 사용**: `/scan` → summary.md 기반 한국어 분석 → Naver Finance/TradingView 링크 → 확인
- **에러 경험**: "오늘 데이터 수집 실패. 어제 데이터로 분석합니다." (서킷 브레이커 + 우아한 저하)
- **첫 실행 체험**: 5년 초기 데이터 로딩 60-90분 → 진행률 표시 필수. 부트스트랩 후 즉시 어제 데이터로 첫 분석 가능.

### Section 6: 데이터 전략

**반영 관점**: pykrx 현황 업데이트 + 폴백 전략 구체화.

**반영 내용**:
- **pykrx 1.2.8 필수 변경**: KRX Data Marketplace 로그인 필수화(2025.12) 반영
- **폴백 순서**: pykrx → FinanceDataReader → DuckDB 캐시. pykrx-openapi는 API 키 신청 마찰로 Phase 2.
- **수집 전략**: `get_market_ohlcv_by_ticker(date)` 배치 API → 전 종목 1회 요청
- **ETL 패턴**: 일일 증분 수집 + 주간 전체 정합성 검증 + 월간 전체 재수집(수정주가 반영)
- **DuckDB 스키마**: ohlcv + indicators + scores 3테이블 (T4 검증)

### Section 7: 지속가능성·토큰 경제

**반영 관점**: 구체적 토큰 소비량 확인.

**반영 내용**:
- 일일 스캔: CLAUDE.md ~5K + 파이프라인 실행 ~3K + summary.md 읽기 ~10K + 분석 출력 ~5K = **~23K 토큰/세션**
- Max 20x 5시간 윈도우 ~220K 대비 ~10% 사용 → 여유 충분
- Agent SDK 크레딧(2026.6.15 이후): $200/월, 일일 스캔 ~$1.50/월 → 장기 지속 가능
- claude -p 헤드리스 모드: 일일 자동 스캔에 적합, --max-turns/--max-budget-usd 가드레일 필수
- 모델 계층화 잠재력: 루틴 스캔 = Sonnet, 심층 분석 = Opus

### Section 8: 위험 등록부

**2차 조사에서 추가된 위험**:

| ID | 위험 | 영향 | 확률 | 완화 |
|----|------|------|------|------|
| R-2-1 | pykrx KRX Data Marketplace 정책 재변경 | HIGH | LOW | 폴백 3-tier(pykrx→FDR→캐시), pykrx-openapi 대기 |
| R-2-2 | VCP 간소화 프록시 정확도 불확실 | MEDIUM | MEDIUM | Phase 3에서 백테스팅 비교 후 전체 VCP 전환 결정 |
| R-2-3 | KOSDAQ/KOSPI 가중치 차등화 미적용 | MEDIUM | HIGH | 단일 가중치 시작, 3개월 후 시장별 분리 검토 |
| R-2-4 | 수정주가 미처리 시 이동평균 왜곡 | HIGH | MEDIUM | pykrx adjusted 파라미터 실증 테스트 후 파이프라인 반영 |
| R-2-5 | claude -p 구독 계정 호환 불확실 | MEDIUM | MEDIUM | GitHub issue #36324 추적, Phase 2 전 테스트 |
| R-2-6 | 침묵적 실패로 쓰레기 점수 산출 | CRITICAL | HIGH (검증 없이) | 데이터 검증 게이트 3단계 + 이상탐지 (Phase 1 필수) |

---

## 조사 품질 검증 — 3층위 자기 점검

### 1층위: 사실 확인

조사 범위 대 커버리지:

| 기술·이론 축 | 커버리지 |
|------------|---------|
| 에이전트 오케스트레이션 이론 | ✅ ReAct, CoT, ToT, 멀티에이전트 (T5) |
| 로컬 LLM·추론 스택 | ✅ Claude Code Max = 유일한 LLM, 로컬 LLM 불필요 확인 (T1) |
| 도구 호출·함수 호출 패러다임 | ✅ Built-in tools, MCP, Hooks (T1) |
| 플래닝·리플렉션 알고리즘 | ✅ Plan-and-Execute, Reflexion, Self-Consistency (T5) |
| 메모리·상태 관리 | ✅ DuckDB, config.yaml, context-snapshots (T2) |
| 자동화 트리거·스케줄링 | ✅ launchd, Hooks, Agent SDK (T1/T3) |
| 샌드박싱·권한 모델 | ✅ 3-tier permissions, settings.json (T1) |
| 실패 복구·관찰 가능성 | ✅ 서킷 브레이커, 우아한 저하, 벌크헤드, 데이터 검증 게이트 (T3/T5) |
| 평가·벤치마킹 방법론 | ✅ 백테스팅, A/B 비교, 교정 분석, 사용자 피드백 (T5) |

**불일치 항목**: 없음. 9개 축 전체 커버.

### 2층위: 구조 분석 — PRD 기술 섹션 구성 시 먼저 무너지는 지점

1. **VCP 간소화 프록시 경계 모호**: "Phase 1 프록시란 정확히 무엇인가" + "언제 전체 VCP로 전환하는가"를 PRD에 명시해야. BBand squeeze width 임계값, volume decline 비율의 구체적 수치 필요.

2. **시장별 가중치 차등화 미결정**: KOSDAQ 소형주는 거래량 패턴, 변동성, 기관 참여율이 상이. PRD는 "단일 가중치로 시작, 3개월 후 시장별 분리 검토"를 선언해야.

3. **수정주가 처리 미확인**: pykrx의 adjusted 파라미터 동작이 미검증. 기업 분할/배당이 모든 이동평균 계산에 영향. PRD에 "수정주가 검증 후 파이프라인 반영" 테스트 항목 필수.

### 3층위: 역방향 점검 — 다루지 않은 것

| 누락 항목 | PRD 영향도 | 조치 |
|-----------|-----------|------|
| pykrx 정확한 데이터 가용 시점 (장 마감 후 몇 분?) | launchd 스케줄 시각 결정 불가 | 실증: 15:35, 16:00, 17:00, 18:00에 pykrx 호출 비교 |
| 초기 역사 데이터 로딩 소요시간 | 첫 설치 시 사용자 대기 시간 | 5년치 배치 수집 예상 60-90분. 진행률 표시 필요 |
| claude -p 구독 계정 호환 | Phase 2 자동화 실현 가능성 | GitHub issue #36324 추적. 테스트 필요 |
| Kiwoom HTS 조건검색 결과 비교 | 제품 신뢰성 벤치마크 | 수동 비교만 가능(API 없음). "사용자 교차검증" 설계 |
| 한국어 금융 용어 Claude 정확도 | 출력 품질 | 스킬 참조 파일에 용어 사전 포함 결정 |
| Apple Silicon numba JIT 호환성 | pandas-ta 최적화 | 비호환 시 numba 비활성화 (영향 미미) |

---

## 1차 → 2차 → PRD 흐름 요약

```
1차 조사 (일반 축)
  → Hybrid 아키텍처 확정, Branch B(통합) 선택, 비기술 사용자 확인
  → "기술적 완성도"에 표준 정의 없음 → PRD가 구축해야

2차 조사 (기술·이론 축)
  → 6개 서브스코어의 구체적 지표 매핑 확립
  → 기술 스택 4개 의존성 확정 (pykrx, DuckDB, pandas-ta, uv)
  → Pragmatic 시나리오 선택 (검증 게이트 + 재시도 + 이상탐지)
  → 침묵적 실패가 단일 최대 위험 확인
  → 백테스팅 필수, 가중치는 "가설"

→ PRD.md (다음 단계)
  → 위 재료를 섹션별로 반영
  → 미해결 항목 10개 중 실증 테스트 6개는 구현 단계에서 해소
```
