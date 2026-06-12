---
round: 2
type: synthesis
topic: key-findings
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
title: "2차 조사 핵심 발견 — 기술·이론 축 Cross-Cutting Discoveries"
inputs:
  - "raw/T01-platform-capability.md"
  - "raw/T02-configuration-architect.md"
  - "raw/T03-orchestration-engineer.md"
  - "raw/T04-integration-specialist.md"
  - "raw/T05-theory-foundation.md"
  - "synthesis/S01-tech-discussion.md"
  - "synthesis/S02-scenarios.md"
---

# S03: 핵심 발견 (2차 조사 — 기술·이론 축)

## Finding 1: Claude Code 플랫폼이 오케스트레이션의 90%+를 네이티브 커버

**출처**: T1 (Platform Capability)

Claude Code의 9개 생명주기 Hook, Skills, Commands가 주식 분석 시스템의 대부분을 커버. **3가지 핵심 갭만 외부 의존**:
1. 자체 스케줄링 불가 → launchd plist ~20줄로 해결 (LOW 비용)
2. 원시 데이터 컨텍스트 수용 불가 → summary-first 아키텍처가 **아키텍처적 필수** (비용 ZERO)
3. 컴팩션 시 분석 맥락 소실 → 기존 context preservation hooks로 해결 (LOW 비용)

**PRD 함의**: 별도 오케스트레이션 프레임워크(Prefect/Dagster/Luigi) 불필요. Claude Code + Python + launchd로 충분.

---

## Finding 2: 침묵적 실패(Silent Failure)가 시스템의 단일 최대 위험

**출처**: T3 (Orchestration Engineer), T5 (Theory Foundation)

pykrx의 문서화된 실패 모드가 검증 없는 파이프라인의 치명적 약점을 드러냄:
- pykrx가 모든 종가를 0으로 반환 → 에러 없음, 쓰레기 점수 산출
- 2,500 중 1,800종목만 반환 → 700종목 누락, 사용자 모름
- Mac 1주 꺼짐 → 5일 전 캐시 데이터로 분석, 신선도 경고 부재

**결론**: 데이터 검증 게이트(~30줄)와 점수 이상탐지(~15줄)는 "최적화"가 아니라 **사용자 신뢰의 전제조건**. Established 시나리오를 배제하고 Pragmatic을 선택한 핵심 근거.

---

## Finding 3: 가장 가치 있는 에이전틱 패턴은 이미 Claude Code에 내장

**출처**: T5 (Theory Foundation)

ReAct(추론→행동→관찰)과 CoT(단계적 추론)이 Claude Code의 도구 사용 루프에 네이티브 구현. 추가 프레임워크 불필요.

**비실용적 패턴**:
- ToT: 2,500종목 × N분기 = 토큰 폭발
- 멀티에이전트 토론: Nature 2026 연구에서 "다수 압력 순응" 확인. 1,600+ 실행 추적에서 단일 에이전트가 동등 이상.
- RAG: 구조화된 데이터(점수, 가격)에는 SQL이 벡터 검색보다 우월.

**유일한 고가치 에이전틱 패턴**: Reflexion — 월간 교정 프로세스로 구현(실시간 패턴 아님). 80+ 종목의 N+20일 성과 추적 → 가중치 조정.

---

## Finding 4: 기술 스택 4개 의존성만으로 전체 파이프라인 구축 가능

**출처**: T4 (Integration Specialist)

| 의존성 | 용도 | 설치 복잡도 | 위험 |
|--------|------|-----------|------|
| pykrx 1.2.8 | KRX OHLCV 수집 | pip install | 중간 (KRX 의존) |
| DuckDB 1.5.2 | 분석 DB | pip install | 낮음 |
| pandas-ta | 지표 계산 | pip install | 낮음 |
| uv | Python 환경 관리 | curl 1줄 | 낮음 |

**불필요한 것**: TA-Lib(C 컴파일러 필요, Apple Silicon 문제), MCP 서버(배치에 중복), Prefect/Dagster(4단계에 과잉), RAG/벡터 DB(SQL 충분).

---

## Finding 5: pykrx KRX 로그인 필수화는 해결된 위험이지만 마찰점은 잔존

**출처**: T4 (Integration Specialist)

2025.12 KRX Data Marketplace 로그인 필수화 이후 pykrx v1.2.x가 적응 완료(마일스톤 #2, 2026.1.31 완료). 등록 무료(네이버/카카오 소셜 로그인). 그러나:
- 비기술 사용자에게 환경변수 설정(KRX_ID/KRX_PW)은 마찰점
- 설치 가이드에 스크린샷 필수
- `get_market_ohlcv_by_ticker(date)` 배치 API로 전 종목 1회 요청 가능 → 속도 제한 위험 최소화

---

## Finding 6: 점수 가중치는 "가설"이며 백테스팅이 필수

**출처**: T5 (Theory Foundation)

기본 가중치(MA 20% + Base 20% + Volume 20% + Momentum 15% + Breakout 15% + RS 10%)는 Minervini/Weinstein/Wyckoff/IBD 이론에서 추론했으나 **실증적 근거 없음**.

- 최소 3개월(66거래일) 백테스팅 데이터 후 교정 필요
- Reflexion 패턴으로 월간 자동 교정 프로세스 구축 가능
- KOSDAQ vs KOSPI 행태 차이 → 시장별 가중치 차등화 검토 필요
- 백테스팅 없이 출시하면 제품은 "블랙 박스"

---

## Finding 7: VCP 탐지는 Phase 1에서 간소화 프록시로 시작해야

**출처**: T5 (Theory Foundation), S01 (Tech Discussion)

전체 VCP(스윙 포인트 탐지 + 수축 측정)는:
- 구현 복잡도 높음 (오류 가능성)
- Phase 1 실행 속도 저하
- 프록시와 전체 VCP 사이의 경계가 모호

**Phase 1 프록시**: Bollinger Band 폭 수축 + 거래량 감소. 성공률 ~90.77%는 시장 레짐 의존적이므로 별도 경고 오버레이로 구현.

**전환 기준**: Phase 3(Month 2+)에서 백테스팅 데이터로 프록시 vs 전체 VCP 정확도 비교 후 결정.

---

## Finding 8: 검증된 소프트웨어 공학 원칙이 시스템 신뢰성의 실제 기초

**출처**: T5 (Theory Foundation)

현대적 에이전틱 이론보다 검증된 자동화 원칙이 실용적 가치 높음:

| 원칙 | 비용 | 방어하는 실패 모드 |
|------|------|-------------------|
| 멱등성 (UPSERT) | 사실상 0 | 재실행으로 장애 복구 |
| Fail-Fast | ~30줄 | 침묵적 오류 전파 |
| 서킷 브레이커 | ~40줄 | pykrx 장애 시 캐시 폴백 |
| 우아한 저하 | 아키텍처 설계 | 부분 장애에도 서비스 유지 |
| ETL 증분 처리 | 파이프라인 설계 | KRX 과도 요청, 실행 시간 |
| 데이터 품질 게이트 | ~30줄 | 쓰레기 데이터 차단 |

**핵심 통찰**: 이 패턴들은 거의 0에 가까운 구현 비용으로 실제 실패 모드를 방어. 멀티에이전트나 ToT 같은 고비용 패턴과 대조적.

---

## Finding 9: 토큰 경제는 장기 지속 가능

**출처**: T1 (Platform Capability), T4 (Integration Specialist)

- 일일 스캔: ~23K-25K 토큰/세션 (CLAUDE.md ~5K + 파이프라인 ~3K + summary.md ~10K + 분석 ~5K)
- Max 20x 5시간 윈도우 ~220K 대비 ~10% → 충분한 여유
- Agent SDK Credit(2026.6.15 이후): $200/월, 일일 스캔 ~$1.50/월
- claude -p 헤드리스: 일일 자동 스캔에 적합, 가드레일 필수(--max-turns/--max-budget-usd)

---

## Cross-Round Continuity (1차 → 2차)

| 1차 발견 | 2차 검증·확장 |
|---------|-------------|
| "기술적 완성도"는 표준 정의 없음 (1차 S03 F1) | 6개 서브스코어 구체적 지표 매핑 확립 (2차 T5) |
| Hybrid 아키텍처 유일한 경로 (1차 S03 F2) | summary-first가 "아키텍처적 필수" 확인 (2차 T1) |
| pykrx가 최고 위험 (1차 S03 F4) | KRX 로그인 적응 완료, 배치 API 확인, 폴백 전략 구체화 (2차 T4) |
| 비기술 사용자 (1차 S03 F5) | 설치 5단계 15분 목표, uv + bootstrap.sh 설계 (2차 T4) |
| 토큰 경제 Branch B 80-90% 절약 (1차 S03 F3) | 일일 ~25K 토큰, $1.50/월 구체 수치 확인 (2차 T1/T4) |

---

## 미해결 항목 통합 (Integrated Parking Lot)

### 실증 테스트 필요

1. **pykrx 데이터 가용 시점**: 장 마감 15:30 후 15:35/16:00/17:00/18:00 테스트 → launchd 스케줄 시각 결정
2. **5년 초기 역사 데이터 로딩**: 배치 수집 예상 60-90분 → bootstrap 진행률 표시 필요
3. **claude -p 구독 계정 호환**: GitHub issue #36324, Max 구독 + API 키 없는 환경 테스트
4. **pandas-ta numba JIT Apple Silicon**: 비호환 시 numba 비활성화(성능 영향 미미)
5. **pykrx 수정주가(adjusted)**: 기업 분할/배당이 이동평균 전체에 영향
6. **get_market_ohlcv_by_ticker(date) 범위**: KOSPI+KOSDAQ 동시 반환 여부

### PRD 설계 결정 필요

7. **VCP 간소화 프록시 정확한 사양**: BBand squeeze + volume decline의 구체적 임계값
8. **시장별 가중치 차등화**: 단일 가중치로 시작, 3개월 후 분리 검토 선언
9. **지표 간 충돌 플래깅**: MA 90 + Volume 30 같은 괴리를 명시적 경고로 표시할지
10. **한국어 금융 용어 정확도**: 스킬 참조 파일에 용어 사전 포함 여부 ("정배열", "눌림목", "돌파")
