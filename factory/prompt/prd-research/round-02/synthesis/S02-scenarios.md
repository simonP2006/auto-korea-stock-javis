---
round: 2
type: synthesis
topic: scenarios
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
title: "PHASE 3 — 3가지 기술 구현 시나리오 비교 분석"
inputs:
  - "synthesis/S01-tech-discussion.md"
  - "raw/T01-platform-capability.md"
  - "raw/T02-configuration-architect.md"
  - "raw/T03-orchestration-engineer.md"
  - "raw/T04-integration-specialist.md"
  - "raw/T05-theory-foundation.md"
---

# S02: 3가지 기술 구현 시나리오 (PHASE 3)

## 시나리오 비교 매트릭스

| 기준 | Experimental | Pragmatic | Established |
|------|-------------|-----------|-------------|
| **파이프라인** | 멀티에이전트 병렬 분석 + MCP 통합 | 순차 파이프라인 + 데이터 검증 + 재시도 | 최소 순차 파이프라인 |
| **점수 산출** | 전체 VCP + 시장 레짐 필터 + 자기일관성 검증 | 간소화 VCP 프록시 + 시장 경고 오버레이 | 기본 지표만 (MA, RSI, MACD) |
| **Claude 역할** | 분석 + 토론 + 반성 + 교정 | 해석 + 한국어 보고 + 주간 요약 | 결과 읽기 + 한국어 변환만 |
| **설정** | 20개 파일, 5개 Hook, 2개 에이전트 | 7-10개 파일, 3개 Hook, 1개 스킬 | 5개 파일, 2개 Hook |
| **연동** | pykrx + pykrx-openapi + FDR + MCP 3종 | pykrx + FDR 폴백 + osascript 알림 | pykrx만 |
| **구현 복잡도** | 높음 (3-4주) | 중간 (1-2주) | 낮음 (3-5일) |
| **학습곡선** | 높음 | 중간 | 낮음 |
| **안정성** | 중간 (실험적 기능 의존) | 높음 | 매우 높음 |
| **기능 범위** | 최대 | 핵심 + 핵심 확장 | 최소 기능 |
| **토큰 효율** | 낮음 (멀티에이전트 = 2-3x) | 높음 (일일 ~25K 토큰) | 최고 (일일 ~15K 토큰) |
| **6개월 지속가능성** | 5/10 | 8/10 | 9/10 |

---

## 시나리오별 상세 분석

### Experimental 시나리오

**포함 기술**: 멀티에이전트 토론(강세/약세), ToT 분석, MCP 3종(pykrx-mcp, korea-stock-mcp, korea-stock-analyzer-mcp), 전체 VCP 스윙 포인트 탐지, 시장 레짐 필터 점수 포함, Agent Teams.

**장점**: 기능적으로 가장 풍부. 대화형 탐색 UX 우수. 심층 분석 품질 최고.

**약점**:
- Nature 2026 연구: 멀티에이전트 토론이 실제로는 다수 압력에 순응
- Agent Teams 실험적(CLAUDE_AGENT_TEAMS=1 필요), 안정성 미검증
- 토큰 예산 2-3x (일일 ~60K+ vs 220K 윈도우 = 여유 감소)
- MCP 서버 3종이 배치 파이프라인과 중복 → 불일치 위험
- 3-4주 개발, 높은 학습곡선

**사용자 대상**: 기술적 사용자, 시스템 아키텍처에 관심, 실험 의향.

### Pragmatic 시나리오 (권장)

**포함 기술**: 순차 파이프라인 + 데이터 검증 게이트(~30줄) + 수집 재시도(~20줄) + 점수 이상탐지(~15줄). 간소화 VCP 프록시(BBand squeeze + volume). 시장 레짐 경고 오버레이. pykrx + FDR 폴백. osascript 알림. 1개 스킬(stock-scanner). claude -p 헤드리스(Phase 2).

**장점**:
- 침묵적 오류 방지 (T3에서 식별된 핵심 위험 해결)
- 총 오케스트레이션 코드 ~150줄 (T3 검증)
- 일일 스캔 ~25K 토큰 (220K 윈도우의 ~10%)
- 1-2주 구현 가능
- Phase 1→2→3 점진적 확장 경로 명확

**약점**:
- 간소화 VCP 프록시의 정확도 불확실 (전체 VCP 대비)
- Reflexion 교정이 3개월 운영 데이터 축적 후에야 가능

**사용자 대상**: 비기술 사용자, 신뢰할 수 있는 일일 자동 시스템 원함.

### Established 시나리오

**포함 기술**: 최소 순차 파이프라인(검증 없음), 기본 지표만(SMA, RSI, MACD — VCP/Wyckoff 제외), pykrx만(폴백 없음), 결과 읽기 + 한국어 변환만.

**장점**: 3-5일 개발, 최소 유지보수, 최고 안정성, 최저 토큰 소비.

**약점**:
- **치명적**: 침묵적 오류 감지 불가 (T3에서 식별된 핵심 위험)
  - pykrx가 0 가격 반환 → 에러 없이 쓰레기 점수 산출
  - 1,800/2,500 종목만 반환 → 700종목 누락, 사용자 모름
- 6개 서브스코어 중 3개(Base Formation, Volume Behavior, Breakout Readiness) 누락
- pykrx 장애 시 대안 없음

**사용자 대상**: 빠른 프로토타입, 개념 검증용.

---

## 시나리오 선택 로직

```
Established를 택할 조건:
  ✅ 우선 작동하는 것 확인 → ✅ 사용자가 비기술자 → ✅ 유지보수 최소화
  ❌ 침묵적 오류 방지 불가 — 사용자 신뢰 파괴 위험

Pragmatic을 택할 조건:
  ✅ 침묵적 실패 방지 필수 → ✅ 일일 자동화 신뢰성 필요 → ✅ 점진적 확장 계획
  ✅ 비기술 사용자 대상 → ✅ 1-2주 구현 가능

Experimental을 택할 조건:
  ❌ 높은 학습곡선 수용 → ❌ 실험적 기능 리스크 감수
  ❌ Nature 2026 연구가 멀티에이전트 효과에 회의적
```

---

## 종합 판단: Pragmatic 시나리오 권장

**결정 근거**:

1. **데이터 검증 게이트 없이는 침묵적 오류가 사용자 신뢰를 파괴** (Established 배제 — T3 Silent Failure 분석이 결정적)
2. **멀티에이전트/MCP 통합은 현 단계에서 비용 대비 가치 낮음** (Experimental 배제 — T5 Nature 2026 연구, T4 MCP 중복성 분석이 근거)
3. **비기술 사용자 대상이므로 1-2주 구현 + 높은 안정성이 적합** (Round 1 S03 Finding 5 "비기술 사용자" 연속)

**Phase 전략**:

| Phase | 시점 | 범위 | Pragmatic 구성 요소 |
|-------|------|------|-------------------|
| Phase 1 | Week 1-2 | MVP | 순차 파이프라인 + 검증 게이트 + 재시도 + 이상탐지 + 6개 서브스코어(VCP 간소화) |
| Phase 2 | Week 3-4 | 자동화 | launchd 스케줄링 + claude -p 한국어 요약 + osascript 알림 |
| Phase 3 | Month 2+ | 교정 | Reflexion 월간 교정 + 시장별 가중치 분리 검토 + 전체 VCP 전환 검토 |
