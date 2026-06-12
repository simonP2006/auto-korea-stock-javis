---
round: 3
type: synthesis
topic: implementation-scenarios
investigation_axis: coding-implementation
created: "2026-05-26T10:00:00+09:00"
title: "3차 조사 — 3가지 구현 시나리오 비교 (Full-Defensive / Balanced / Rapid-Prototype)"
input_files:
  - "raw/T01-workflow-script-architect.md"
  - "raw/T02-agent-orchestration-coder.md"
  - "raw/T03-skills-hooks-developer.md"
  - "raw/T04-verification-quality-coder.md"
  - "raw/T05-state-recovery-coder.md"
  - "synthesis/S01-spectral-positioning.md"
cross_cutting_axes:
  - "defense-level"
  - "implementation-effort"
  - "reliability-vs-speed"
---

# S02: 3가지 구현 시나리오 비교

## Scenario A: Full-Defensive (모든 엣지 케이스 처리)

**철학**: "모든 실패 가능성에 대비한다."

| 영역 | 구성 | 코드량 (줄) |
|------|------|-----------|
| workflow.md | 절차적, 모든 분기·예외 명시 | ~550 |
| 오케스트레이션 | 중앙 집중, 모든 전환점에 상태 검사 | ~200 |
| Skills/Hooks | 특화 100%, 모든 이벤트에 hook | ~600 |
| 검증 | 전수 엄격 (Gate 1-4 모두) | ~950 |
| 상태 관리 | 구조화 상태 머신 | ~900 |
| 파이프라인 코드 | Python collect/analyze/score/report | ~1000 |
| **총계** | | **~4,200** |

**장점**:
1. 6/6 핵심 실패 모드 완전 방어
2. 풍부한 로그로 디버깅 용이
3. 상태 머신으로 정밀한 전이 제어

**위험**:
1. **과설계**: 4단계 순차 파이프라인에 ~900줄 FSM은 불필요한 복잡도
2. **유지보수 부담**: 변경 시 workflow.md + Python + FSM + 검증 게이트 동시 수정
3. **오탐 과다**: Gate 2,4의 엄격 검증이 3%+ 오탐 → 사용자 경고 피로

**선택 조건**: 오류 제로 톨러런스, 규제 환경, 무한 구현 시간.

---

## Scenario B: Balanced (핵심만 방어) ← **권고**

**철학**: "핵심 경로만 방어하고 나머지는 실용적으로."

| 영역 | 구성 | 코드량 (줄) |
|------|------|-----------|
| workflow.md | Hybrid 절차+선언 | ~380 |
| 오케스트레이션 | 중앙 집중, 핵심 전환점만 검사 | ~100 |
| Skills/Hooks | 특화 85% + 범용 확장 15% | ~500 |
| 검증 | Targeted Strict (Gate 1,3 엄격 + Gate 2,4 선택적) | ~780 |
| 상태 관리 | 파일 기반 + guard/JSONL 차용 | ~520 |
| 파이프라인 코드 | Python collect/analyze/score/report | ~1000 |
| **총계** | | **~3,280** |

**장점**:
1. 6/6 핵심 실패 모드 방어 (Gate 1,3 엄격 → 가장 위험한 FM-1~3 커버)
2. 합리적 구현량 (~3,300줄 vs Full-Defensive ~4,200줄)
3. scoring_config.yaml SOT로 유지보수 부담 최소화
4. 파일 기반 상태 → 투명한 디버깅

**위험**:
1. Gate 2 선택적 검증으로 FM-4 (NaN flooding) 일부 미탐지 (확률 LOW — pandas-ta 결정론적)
2. Gate 4 선택적 검증으로 리포트 형식 이상 미탐지 (영향 LOW — Claude 해석 가능)
3. 검증 임계값이 가설적 → 첫 2주 오탐 가능 (dry-run 모드로 완화)

**선택 조건**: **이 시스템에 최적** — 금융 도구 수준 품질 + 현실적 구현량. 품질 절대기준(절대 기준 1) 충족.

---

## Scenario C: Rapid-Prototype (최소 구현, 빠른 검증)

**철학**: "먼저 돌아가는 것을 확인하고, 점진적으로 견고하게."

| 영역 | 구성 | 코드량 (줄) |
|------|------|-----------|
| workflow.md | 선언적 최소 | ~150 |
| 오케스트레이션 | `main.py` 직접 실행, 오케스트레이터 없음 | ~0 |
| Skills/Hooks | 최소 (/scan만, hook 없음) | ~100 |
| 검증 | 행 수만 체크 | ~100 |
| 상태 관리 | 없음 (재실행이 복구) | ~0 |
| 파이프라인 코드 | Python collect/analyze/score/report (최소) | ~700 |
| **총계** | | **~1,050** |

**장점**:
1. 빠른 PoC — 작동 확인 후 점진적 강화
2. 최소 코드 → 최소 버그
3. 학습 곡선 없음

**위험**:
1. **FM-4, FM-5 미탐지**: NaN flooding과 점진적 분포 이동 → 쓰레기 점수 무경고 제시
2. **5년 초기 로드 중단 시 처음부터**: 체크포인트 없음 → 60-90분 재실행
3. **사용자 신뢰 파괴**: 금융 도구에서 한 번의 쓰레기 점수 = 비가역적 신뢰 상실
4. **점진적 강화의 비현실성**: 나중에 검증·상태 추가하면 파이프라인 전체 리팩터링 필요

**선택 조건**: PoC/학습 목적. **금융 분석 도구로는 부적합**.

### 점진적 강화 로드맵 (C → B 경로)

```
Phase 1 (즉시): Scenario C — 최소 구현, 작동 확인
Phase 2 (1주 후): Gate 1,3 추가 (+~400줄) → 핵심 실패 모드 방어
Phase 3 (2주 후): 상태 관리 추가 (+~520줄) → 복구 가능
Phase 4 (3주 후): 특화 스킬/hook 추가 (+~500줄) → 완전한 Scenario B
```

문제: Phase 2-4가 기존 코드에 검증·상태를 끼워 넣는 리팩터링이므로, Scenario B를 처음부터 구축하는 것과 총 작업량이 유사하거나 더 많을 수 있음.

---

## 3개 시나리오 비교 매트릭스

| 기준 | Full-Defensive (A) | Balanced (B) | Rapid-Prototype (C) |
|------|-------------------|--------------|---------------------|
| **총 구현량** | ~4,200줄 | **~3,280줄** | ~1,050줄 |
| **안정성** | 매우 높음 | 높음 | 낮음 |
| **핵심 FM 방어** | 6/6 | 6/6 (Gate 1,3 엄격) | 3/6 |
| **구현 기간** | 길음 | 중간 | 짧음 |
| **토큰 소비 (검증 포함)** | 높음 | 중간 | 낮음 |
| **디버깅 용이성** | 높음 (로그 풍부) | 중간 | 낮음 |
| **확장 비용** | 낮음 (기반 탄탄) | 중간 | 높음 (나중에 추가) |
| **유지보수 부담** | 높음 (4곳 동시 수정) | 중간 | 낮음 (코드 적음) |
| **사용자 신뢰** | 매우 높음 | 높음 | 낮음 (위험) |
| **로컬 실행** | [LOCAL-OK] | [LOCAL-OK] | [LOCAL-OK] |

### 선택 로직

```
IF 오류 제로 톨러런스 AND 구현 시간 무제한:
  → Full-Defensive (A)
ELIF 핵심 품질 보장 AND 현실적 구현량:
  → Balanced (B) ← 이 시스템에 최적
ELIF PoC 목적 AND 금융 도구 아님:
  → Rapid-Prototype (C)
```

### 권고: Scenario B (Balanced)

- 절대 기준 1(품질)에 의해 C는 배제 — 금융 도구에서 FM-4,5 미탐지 불허
- A는 과설계 — FSM ~900줄이 4단계 순차 파이프라인에 불필요
- B가 6/6 핵심 실패 모드 방어 + ~3,300줄 합리적 구현량
- scoring_config.yaml SOT로 유지보수 부담 관리
