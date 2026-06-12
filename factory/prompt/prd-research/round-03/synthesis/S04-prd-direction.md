---
round: 3
type: synthesis
topic: prd-direction
investigation_axis: coding-implementation
created: "2026-05-26T10:00:00+09:00"
title: "3차 조사 PRD 방향 조언 — 코딩·구현 축 반영"
input_files:
  - "synthesis/S01-spectral-positioning.md"
  - "synthesis/S02-implementation-scenarios.md"
  - "synthesis/S03-key-findings.md"
cross_cutting_axes:
  - "all 5 coding-implementation axes"
---

# S04: PRD 방향 조언 (3차 — 코딩·구현 축)

## PRD 섹션별 코딩·구현 축 반영 방향

### Section 3: 아키텍처 — 코드 수준 구체화

**반영 관점**: "왜 이 구현 패턴을 선택했는가"를 모든 결정에 포함.

**반영 내용**:

1. **Two-Engine 아키텍처 코드 수준 구체화**:
   - Engine 1 (Python): `main.py → collect.py → analyze.py → score.py → report.py` 순차. 결정론적. AI 미개입.
   - Engine 2 (Claude Code): `/scan` → `summary.md` 읽기 → 한국어 해석. 적응적. 선언적.
   - 인터페이스: `output/summary.md` (단일 핸드오프 파일)
   - Engine 2가 raw 데이터 직접 접근하지 않음 (summary-first 아키텍처적 필수)

2. **오케스트레이션 패턴 선언**:
   - "Claude Code 자체가 orchestrator. 별도 프레임워크 불필요."
   - 근거: T02 조사의 7-1-4 비교 결과
   - Phase 2+ 심층분석에서만 sub-agent fork 패턴

3. **파일 시스템 레이아웃**:
   ```
   stock-scanner/
   ├── config/
   │   ├── scoring_config.yaml     ← 스코어링 파라미터 SOT
   │   └── pipeline_config.yaml    ← 파이프라인 설정
   ├── src/
   │   ├── main.py                 ← 파이프라인 진입점
   │   ├── collect.py              ← pykrx → DuckDB
   │   ├── analyze.py              ← pandas-ta → DuckDB
   │   ├── score.py                ← DuckDB → DuckDB (scoring_config 참조)
   │   ├── report.py               ← DuckDB → summary.md
   │   └── gates/                  ← 검증 게이트 모듈
   │       ├── validate_collection.py
   │       ├── validate_indicators.py
   │       ├── validate_scores.py
   │       └── validate_report.py
   ├── data/
   │   └── stocks.duckdb           ← 분석 DB
   ├── output/
   │   └── summary.md              ← Engine 1→2 인터페이스
   ├── state/
   │   ├── pipeline_state.json     ← 파이프라인 상태
   │   └── pipeline_transitions.jsonl
   ├── logs/
   ├── .claude/
   │   ├── skills/stock-scanner/   ← 도메인 스킬
   │   ├── commands/               ← /scan, /analyze 등
   │   └── hooks/scripts/          ← 도메인 hook
   └── bootstrap.sh               ← 설치 스크립트
   ```

4. **workflow.md 구조 선언**:
   - Hybrid (절차+선언): Stage 1-3 절차적 (~210줄), Stage 4+해석 선언적 (~25줄)
   - workflow.md는 **명세(WHAT)**, Python은 **구현(HOW)**
   - 파라미터는 scoring_config.yaml 참조 (workflow.md에 직접 기술하지 않음)

### Section 2: 점수 산출 방법론 — scoring_config.yaml SOT

**반영 관점**: 구현 코드와 해석 스킬 모두 단일 설정 파일 참조.

**반영 내용**:
- `config/scoring_config.yaml`: 가중치, 임계값, 지표 파라미터의 단일 SOT
- `score.py`와 `stock-scanner/SKILL.md`가 동일 파일 참조
- "가설" 명시적 선언: `calibration_note` 필드
- 변경 프로토콜: yaml 수정 → score.py 자동 반영 + SKILL.md 자동 반영. workflow.md 수정 불필요

### Section 5 (신규 권고): 신뢰성·검증

**반영 관점**: 검증은 최적화가 아니라 전제조건. PRD에 독립 섹션 격상 필요.

**반영 내용**:
1. **4-Gate 검증 아키텍처**:
   ```
   collect ──Gate 1──→ analyze ──Gate 2──→ score ──Gate 3──→ report ──Gate 4──→ summary.md
     (엄격)              (선택적)           (엄격)            (선택적)
   ```
2. **실패 모드 대응 매트릭스**: FM-1~FM-6과 각 게이트 탐지 여부
3. **Circuit Breaker**: pykrx → FDR → 캐시 3-tier 폴백
4. **이상탐지**: 점수 분포 day-over-day drift > 15점 탐지
5. **첫 2주 dry-run 모드**: 경고만, 차단 없음 (임계값 교정 기간)

### Section 4: 사용자 경험 — 한국어 네이티브

**반영 관점**: 비기술 사용자를 위한 도메인 네이티브 인터페이스.

**반영 내용**:
- 6개 커맨드: /scan, /top, /analyze, /backtest, /regime, /anomalies (모든 설명 한국어)
- 에러 메시지 한국어화: "오늘 데이터 수집 실패. 어제 데이터로 분석합니다."
- SessionStart hook: 세션 시작 시 데이터 신선도 자동 보고
- stock-scanner SKILL.md에 한국어 금융 용어 사전 내장

### Section 7: 지속가능성·토큰 경제 — 구현 관점

**반영 관점**: 3차 조사에서 토큰 최적화 경로 구체화.

**반영 내용**:
- 특화 스킬 토큰 절약: 일일 ~1,250, 월 ~37,500
- Phase 2 모델 계층화: 루틴 스캔 = Sonnet, 심층 분석 = Opus
- 점진적 강화 로드맵:
  - Phase 1: 핵심 파이프라인 + Targeted Strict 검증 + 파일 기반 상태
  - Phase 2: 자동화 (claude -p + launchd) + 모델 계층화
  - Phase 3: 백테스팅 + VCP 전체 구현 + 월간 가중치 교정

### Section 8: 위험 등록부 — 3차 추가 항목

| ID | 위험 | 영향 | 확률 | 완화 |
|----|------|------|------|------|
| R-3-1 | scoring_config.yaml vs 코드 불일치 | HIGH | MED | CI 검증 스크립트: config→code 일관성 체크 |
| R-3-2 | workflow.md vs Python source SOT 경합 | MED | HIGH | 역할 분리 선언 (명세 vs 구현) |
| R-3-3 | Hook 누적 실행 시간 | LOW | MED | Hook별 timeout, 총 실행시간 모니터링 |
| R-3-4 | Agent Teams 실험적 상태 | MED | MED | Phase 2까지 성숙도 추적 |
| R-3-5 | 검증 게이트 오탐 (~3%) | LOW | HIGH | dry-run 2주 + 임계값 조정 |

---

## 조사 품질 검증 — 3층위 자기 점검

### 1층위: 사실 확인

| 코딩·구현 축 | 커버리지 | 출처 |
|------------|---------|------|
| workflow.md 설계 (선언/절차/혼합) | ✅ | T01 |
| 오케스트레이션 (중앙/분산) | ✅ | T02 |
| Skill/Hook/Command 전략 | ✅ | T03 |
| 검증·품질 게이트 | ✅ | T04 |
| 상태 관리·복구 | ✅ | T05 |
| 파일 시스템 레이아웃 | ✅ | T01-T05 교차 |
| scoring_config SOT | ✅ | T01+T03 독립 식별 |
| 구현량 추정 | ✅ | T01-T05 합산 |
| 로컬 실행 가능성 | ✅ | 전 항목 태깅 완료 |

**불일치**: 없음. 5팀 독립 조사 결론 수렴.

### 2층위: 구조 분석 — PRD 구현 섹션 구성 시 먼저 무너지는 지점

1. **scoring_config.yaml 4개 소비자 동기화**: 하나라도 구버전 읽으면 침묵적 불일치 → "변경 프로토콜" 명시 필요
2. **workflow.md vs Python SOT 경합**: 절차적 부분이 코드와 동기화 실패 가능 → 역할 분리 선언 또는 scoring_config 참조로 변경
3. **검증 임계값 초기 교정 부재**: Gate 3의 "mean 40-60, std 10-25" 가설 → 첫 2주 dry-run 모드 필수

### 3층위: 역방향 점검 — 다루지 않은 것

| 누락 항목 | PRD 영향도 | 조치 |
|-----------|-----------|------|
| 테스트 전략 (unit/integration/e2e) | HIGH | 별도 조사 또는 PRD에서 설계 |
| CI/CD 파이프라인 | MED | 간단한 pre-commit hook 수준 |
| bootstrap.sh 구체적 구현 | MED | 설치 스크립트 상세 단계 |
| DuckDB 스키마 마이그레이션 | MED | scoring_config 변경 시 테이블 변경 |
| 한국어 금융 용어 정확도 | LOW | 용어 사전으로 완화 |
| pykrx 데이터 가용 시점 실증 | HIGH | 2차 이관 항목, 실증 필요 |
| 에러 코드 표준화 | LOW | 게이트 에러 코드 체계 |
| 로깅 표준 | LOW | JSON structured logging |

---

## 1차 → 2차 → 3차 → PRD 흐름 요약

```
1차 조사 (일반 축)
  → Hybrid 아키텍처 확정, 비기술 사용자 확인
  → "기술적 완성도"에 표준 정의 없음

2차 조사 (기술·이론 축)
  → 6개 서브스코어 지표 매핑 확립
  → 4개 의존성 확정, Pragmatic 시나리오 선택
  → 침묵적 실패 = 단일 최대 위험

3차 조사 (코딩·구현 축)
  → Hybrid workflow.md (절차+선언, ~350-400줄)
  → 중앙 집중 오케스트레이션 (7-1-4 압승)
  → 특화 85% 스킬/훅 + scoring_config.yaml SOT
  → Targeted Strict 4-Gate 검증 (~780줄)
  → 파일 기반 상태 관리 + guard (~520줄)
  → Balanced 시나리오 선택 (~3,300줄 총 구현량)
  → 모든 선택지 [LOCAL-OK], [LOCAL-BLOCKED] 0개

→ PRD.md (다음 단계)
  → 1·2·3차 재료를 섹션별 반영
  → 미해결 15개 중 실증 테스트 6개는 구현 단계에서 해소
```
