---
round: 3
type: synthesis
topic: key-findings
investigation_axis: coding-implementation
created: "2026-05-26T10:00:00+09:00"
title: "3차 조사 핵심 발견 — 코딩·구현 축 Cross-Cutting Discoveries"
input_files:
  - "raw/T01-workflow-script-architect.md"
  - "raw/T02-agent-orchestration-coder.md"
  - "raw/T03-skills-hooks-developer.md"
  - "raw/T04-verification-quality-coder.md"
  - "raw/T05-state-recovery-coder.md"
  - "synthesis/S01-spectral-positioning.md"
  - "synthesis/S02-implementation-scenarios.md"
cross_cutting_axes:
  - "all 5 coding-implementation axes"
---

# S03: 핵심 발견 (3차 조사 — 코딩·구현 축)

## Finding 1: workflow.md의 이중 성격 — "명세서이자 실행 지침"

**출처**: T01 (Workflow Script Architect)

workflow.md는 이 시스템에서 두 역할을 동시 수행:
- **Engine 1 (Python)**: 절차적 명세 — `ta.bbands(close, length=20, std=2)` 같은 구체적 호출이 "세부사항"이 아니라 **제품 사양** 그 자체.
- **Engine 2 (Claude Code)**: 선언적 의도 — summary.md 읽고 한국어 해석. 절차적 지정은 해석 품질 저하.

**PRD 함의**: Hybrid workflow.md (~350-400줄). 절차적(Stage 1-3) + 선언적(Stage 4+해석).

**위험**: workflow.md vs Python source SOT 경합. → `scoring_config.yaml`로 분리 필요.

---

## Finding 2: 오케스트레이션은 이미 해결된 문제

**출처**: T02 (Agent Orchestration Coder)

Claude Code 자체가 orchestrator. 별도 레이어 불필요. 7-1-4 비교 결과 중앙 집중 압승:
- 일일 파이프라인은 **결정론적 Python 스크립트 체인** — AI 판단 미개입
- `launchd → python3 main.py` → 순차 실행 → Claude Code가 summary.md 해석
- Agent Swarm: 설정 복잡도 HIGH, Agent Teams가 실험적 기능으로 플랫폼 리스크

**Phase 2+ 확장**: 개별 종목 심층분석(`/analyze TICKER`)에서만 sub-agent fork. 자율 swarm 아님.

---

## Finding 3: 도메인 특화 스킬이 범용보다 ~1,250 토큰/일 절약 + 정확도 우위

**출처**: T03 (Skills & Hooks Developer)

stock-scanner 스킬에 6개 서브스코어·해석 임계값·한국어 용어·이상탐지 규칙 **미리 내장**:
- 매 /scan 호출 시 ~1,250 토큰 절약 (월 ~37,500)
- 핵심: "거래량 90 + 추세 20 = 조작 위험" — 범용 스킬로 전달 불가

**권고**: Hybrid 85% 특화 / 15% 범용 확장.

---

## Finding 4: 검증은 "최적화"가 아니라 "신뢰의 전제조건"

**출처**: T04 (Verification & Quality Coder)

금융 분석 도구에서 사용자 신뢰는 이진적 — 한 번의 쓰레기 점수 = 비가역적 신뢰 상실.

| 실패 모드 | 엄격(4.1) | 선택적(4.2) | 영향 |
|-----------|----------|-----------|------|
| FM-1: pykrx 전수 0원 반환 | ✅ | ✅ | CRITICAL |
| FM-2: 2500중 1800만 반환 | ✅ | ✅ | HIGH |
| FM-3: 5일 전 캐시 데이터 | ✅ | ✅ | HIGH |
| FM-4: pandas-ta NaN 30% | ✅ | ❌ | MEDIUM |
| FM-5: 점수 분포 점진 이동 | ✅ | ❌ | MEDIUM |
| FM-6: DuckDB 손상 | ✅ | ✅ | HIGH |

**Targeted Strict 권고**: Gate 1(수집) + Gate 3(스코어링) 엄격, Gate 2(지표) + Gate 4(리포트) 선택적. Phase 1에 ~780줄.

---

## Finding 5: 상태 관리는 파일 기반이면 충분

**출처**: T05 (State & Recovery Coder)

4단계 순차 파이프라인에 정형 FSM은 ~380줄 불필요 의례. 파일 기반(~520줄)으로 7개 장애 시나리오 모두 처리:
- `pipeline_state.json`: 현재 단계, 마지막 성공, 에러 정보
- `initial_load_checkpoint.json`: 5년 초기 로드 중단 재개
- `fcntl.flock()` lock file: 동시 실행 차단

**상태 머신에서 차용**: guard 조건 (인라인), JSONL 전이 로그, `VALID_TRANSITIONS` dict.

---

## Finding 6: scoring_config.yaml이 SOT 후보로 부상

**출처**: T01, T03 독립 식별 → 통합 발견

스코어링 파라미터가 4곳에 분산: workflow.md, score.py, SKILL.md, 검증 게이트.

**해결**: `config/scoring_config.yaml`을 SOT로 선언. 모든 소비자가 이 파일 참조.

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

---

## Finding 7: 코딩 복잡도는 "예상보다 낮다"

**출처**: T01-T05 교차 검증

| 예상보다 쉬운 것 | 이유 |
|----------------|------|
| 오케스트레이션 | Claude Code가 90%+ 커버. `launchd → python3 main.py` |
| 상태 관리 | 4단계 순차 → 단순 JSON 충분 |
| Hook 통합 | 기존 인프라 확장 |
| 스케줄링 | launchd plist ~20줄 |

| 예상보다 어려운 것 | 이유 |
|------------------|------|
| scoring_config SOT 동기화 | 4개 소비자 일관성 |
| pykrx 장애 모드 다양성 | 5가지 이상, 각 다른 복구 |
| VCP 간소화 프록시 경계 | 임계값 미확정 |
| workflow.md vs source SOT 경합 | 역할 분리 미선언 |

---

## Finding 8: Claude Code의 기능 경계 명확화

**출처**: T02 (오케스트레이션), T03 (스킬/훅)

| 가능 (Phase 1) | 유의 (Phase 2+) | 불가능 |
|---------------|------------------|--------|
| Hook (9 이벤트, 안정) | Agent Teams (실험적) | 자체 스케줄링 |
| Skills/Commands (안정) | claude -p 헤드리스 (미확인) | 실시간 모니터링 |
| Agent tool (안정) | SendMessage (Teams 내) | 지속적 백그라운드 |
| Task management (안정) | worktree (git 필요) | 외부 API 키 관리 |
| Read/Write/Edit/Bash (안정) | Model tiering | MCP (Phase 1 불필요) |

---

## Finding 9: 전체 구현량 추정치 수렴

**출처**: T01-T05 합산

| 구성 요소 | 코드량 (줄) |
|-----------|-----------|
| Python 파이프라인 | ~800-1,000 |
| 검증 게이트 | ~780 |
| 상태 관리 + 복구 | ~520 |
| workflow.md | ~350-400 |
| Hook 스크립트 (2개 신규) | ~300 |
| SKILL.md (stock-scanner) | ~200 |
| Commands (6개) | ~400 |
| Config (yaml + plist) | ~80 |
| **총계** | **~3,400-3,700** |

---

## Finding 10: 모든 선택지가 LOCAL-OK

**출처**: T01-T05 전체

[LOCAL-BLOCKED]: **0개**

[LOCAL-PARTIAL]: 3개 (모두 회피 가능)
1. Agent Teams — 실험적 → Phase 1 미사용
2. pykrx 네트워크 — 캐시 폴백으로 오프라인 대응
3. Mermaid 렌더링 — 텍스트 대체 가능

---

## Cross-Round Continuity (1차 → 2차 → 3차)

| 이전 발견 | 3차 검증·확장 |
|---------|-------------|
| Hybrid 아키텍처 (1차 S03 F2) | Two-Engine 코드 수준 구체화: Engine 1=절차적 Python, Engine 2=선언적 Claude Code (3차 T01) |
| Claude Code 90%+ 커버 (2차 S03 F1) | 오케스트레이션 패턴 비교 7-1-4 중앙 집중 확정 (3차 T02) |
| 침묵적 실패 #1 위험 (2차 S03 F2) | 4-Gate Targeted Strict 검증 ~780줄 구체 구현 (3차 T04) |
| 4개 의존성 (2차 S03 F4) | 파일 시스템 레이아웃, skill/hook/command 구체 설계 (3차 T03) |
| 점수 가중치 "가설" (2차 S03 F6) | scoring_config.yaml SOT 패턴 도출 (3차 T01+T03) |

---

## 미해결 항목 통합 (Integrated Parking Lot)

### 이전 라운드에서 이관된 항목

1. **pykrx 데이터 가용 시점** (2차 PL#1): 장 마감 후 실증 테스트 필요 → launchd 시각 결정
2. **5년 초기 데이터 로딩** (2차 PL#2): ~60-90분, 진행률 표시 필요
3. **claude -p 구독 계정 호환** (2차 PL#3): GitHub #36324 추적
4. **pandas-ta numba Apple Silicon** (2차 PL#4): 비호환 시 비활성화
5. **pykrx 수정주가** (2차 PL#5): adjusted 파라미터 실증 테스트

### 3차에서 새로 식별된 항목

6. **scoring_config.yaml 4개 소비자 동기화 프로토콜**: 하나라도 불일치 시 침묵적 오류
7. **workflow.md vs Python source SOT 역할 분리 선언**: PRD에서 결정 필요
8. **검증 임계값 초기 교정**: 첫 2주 dry-run 모드 필요
9. **테스트 전략 (unit/integration/e2e)**: 조사 범위 밖, 별도 설계 필요
10. **bootstrap.sh 구체적 구현**: 설치 스크립트 상세 단계
11. **DuckDB 스키마 마이그레이션**: scoring_config 변경 시 테이블 변경 가능
12. **한국어 금융 용어 Claude 정확도**: 용어 사전으로 완화
13. **Hook 누적 실행 시간**: 기존 15+ hook + 신규 4개, 총 실행시간 모니터링
14. **Circuit Breaker 상태 지속성**: 파이프라인 간 실패 상태 유지
15. **DNA 상속 긴장**: 순수 Implementation 워크플로우가 3-phase 구조에 유효한지
