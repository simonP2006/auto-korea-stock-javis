---
round: 4
type: synthesis
topic: discussion-scenarios
investigation_axis: external-integration
created: "2026-05-26T16:30:00+09:00"
title: "4차 조사 토론 결과 + 시나리오 비교"
---

# S02: 연동 토론 결과 + 3가지 시나리오 비교

## Phase 2 토론: 4가지 관점 교차 분석

### 기능 극대화 관점
- 4개 MCP 서버 + 4개 LLM + Telegram + DART
- 외부 의존 ~15, 실패 지점 ~12
- 장점: 최대 분석 역량, 다양한 데이터 소스
- 약점: 설정 복잡도 HIGH, 유지보수 부담 HIGH

### 안정성 우선 관점
- 검증된 연동만: pykrx + DuckDB + Claude Code
- 외부 의존 ~3, 실패 지점 ~2
- 장점: 안정적 일일 운영, 장애 최소
- 약점: 기능 제한, 확장성 낮음

### 설정 단순성 관점
- brew 0개, uv + Python 패키지만
- 설치 1-2분, 설정 파일 2개 (scoring_config.yaml + pipeline_config.yaml)
- 장점: 비기술 사용자 친화, 재설치 용이
- 약점: 고급 기능 포기

### 자립성/독립성 관점
- 오프라인 가능 범위 극대화
- Engine 1 완전 오프라인 (캐시 데이터), Engine 2 Ollama 폴백
- 장점: 네트워크 없어도 작동
- 약점: 데이터 신선도 문제, LLM 품질 저하

### 4가지 관점 합의표

| 연동 구성 | 기능 극대화 | 안정성 | 단순성 | 자립성 | 합의도 |
|----------|----------|-------|-------|-------|--------|
| pykrx 데이터 수집 | ✓ | ✓ | ✓ | ✓ | 4/4 ✅ |
| DuckDB 로컬 DB | ✓ | ✓ | ✓ | ✓ | 4/4 ✅ |
| pandas-ta 지표 | ✓ | ✓ | ✓ | ✓ | 4/4 ✅ |
| 3-tier 데이터 폴백 | ✓ | ✓ | ✓ | ✓ | 4/4 ✅ |
| Gate 1-4 검증 | ✓ | ✓ | ✓ | ✓ | 4/4 ✅ |
| osascript 알림 | ✓ | ✓ | ✓ | ✓ | 4/4 ✅ |
| Atomic write 패턴 | ✓ | ✓ | ✓ | ✓ | 4/4 ✅ |
| DuckDB MCP (Phase 2) | ✓ | ✓ | ✗ | ✗ | 2/4 |
| Gemini CLI (Phase 2) | ✓ | ✗ | ✗ | ✗ | 1/4 |
| Telegram 봇 (Phase 2) | ✓ | ✓ | ✗ | ✗ | 2/4 |
| DART API | ✓ | ✗ | ✗ | ✗ | 1/4 |
| Ollama 오프라인 | ✓ | ✗ | ✗ | ✓ | 2/4 |

**의사결정 포인트**:
1. DuckDB MCP: 기능과 단순성 충돌 → Phase 2에서 도입, 단순성이 안정성 검증 후 양보
2. Gemini CLI: 기능과 안정성/단순성/자립성 3중 충돌 → Phase 2 후반, 사용량 측정 후 결정
3. Telegram: 기능/안정성과 단순성/자립성 충돌 → Phase 2, 사용자가 Telegram 사용자인 경우만

---

## Phase 3 시나리오: 3가지 연동 수준

### Scenario A: Full Integration

**철학**: 가능한 모든 외부 연동을 활용하여 최대 역량 확보.

| 구성 요소 | 구체적 연동 |
|----------|----------|
| MCP | DuckDB + pykrx-mcp + Sequential Thinking + Slack |
| LLM | Claude + Codex CLI + Gemini CLI + Ollama |
| 데이터 | pykrx + FDR + DART + yfinance |
| 알림 | Telegram + Slack + Gmail + osascript |
| 도구 | brew(duckdb, fswatch) + uv + Python |

- 외부 의존: ~15, 설정 시간: ~30분, 실패 지점: ~12
- 장점: 최대 분석 역량, 다중 데이터 소스 교차검증, 멀티 LLM 세컨드 오피니언
- 위험: 설정 복잡도, 유지보수 부담, 알 수 없는 상호작용 버그

### Scenario B: Selective Integration (★ 권장)

**철학**: 핵심 연동만 포함, 나머지는 내장 기능으로 대체.

| 구성 요소 | 구체적 연동 |
|----------|----------|
| MCP | DuckDB (읽기전용, Phase 2) |
| LLM | Claude + Gemini CLI (Phase 2) |
| 데이터 | pykrx + FDR 폴백 + DuckDB 캐시 |
| 알림 | osascript (Phase 1) + Telegram (Phase 2) |
| 도구 | uv + Python 패키지만 (brew 0개) |

- 외부 의존: ~6, 설정 시간: ~5분, 실패 지점: ~5
- 장점: 핵심 기능 확보, 관리 가능한 복잡도, 점진 확장 가능
- 위험: 일부 고급 기능 포기 (DART 재무데이터, 코드 리뷰)

### Scenario C: Self-Contained

**철학**: 외부 의존 극도 최소화, 자립적 운영.

| 구성 요소 | 구체적 연동 |
|----------|----------|
| MCP | 없음 |
| LLM | Claude만 (Ollama 오프라인 폴백) |
| 데이터 | pykrx + DuckDB 캐시 (FDR도 미사용) |
| 알림 | osascript만 |
| 도구 | uv + Python 패키지만 |

- 외부 의존: ~2, 설정 시간: ~2분, 실패 지점: ~2
- 장점: 극도로 단순, 높은 이식성, 오프라인 대부분 가능
- 위험: 데이터 소스 단일 의존, LLM 폴백 품질 저하, 확장 어려움
- 향후 확장: Scenario B로 마이그레이션 경로 열림

---

## 시나리오 선택: Selective Integration (B)

**이유**:
1. Phase 1은 사실상 Self-Contained(C)와 동일 — pykrx 하나만 외부 연동
2. Phase 2에서 B로 자연스럽게 확장 — DuckDB MCP + Gemini CLI + Telegram
3. A는 설정 복잡도가 비기술 사용자에게 부적합
4. C는 확장성이 부족하고 데이터 폴백이 약함

**핵심**: Phase 1 = C, Phase 2 = B, Phase 3 = B+α (A의 선택 요소 추가)
