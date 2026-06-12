---
round: 4
type: synthesis
topic: integration-spectrum
investigation_axis: external-integration
created: "2026-05-26T16:30:00+09:00"
title: "4차 조사 연동 스펙트럼 포지셔닝"
---

# S01: 5개 영역별 연동 접근 스펙트럼

## 스펙트럼 포지셔닝

```
MCP Server:    풍부한 생태계 ←──────────→ 최소+커스텀   [Phase 1: 최소(0개), Phase 2: 선택적(1-2개)]
Local Tools:   적극 활용 ←──────────→ 최소 의존         [결정: 최소 의존 (brew 0개)]
API & Service: 클라우드 연동 ←──────────→ 완전 로컬      [Phase 1: 거의 로컬, Phase 2: 선택적 클라우드]
Data Flow:     실시간 ←──────────→ 배치                  [결정: 100% 배치 (Phase 1)]
Reliability:   Fail-fast ←──────────→ Graceful degradation [결정: Fail-fast 기본 + 선택적 degradation]
```

## 모든 영역이 동의하는 연동 구성

### 전원 추천
- DuckDB 로컬 DB (모든 영역에서 안정성·성능·로컬 완결성 확인)
- pykrx → FDR → 캐시 3-tier 폴백 (T01, T03, T05 동의)
- 파일 기반 배치 교환 (T04: 단순, 안정, 디버깅 용이)
- macOS 내장 도구 활용 (T02: jq, osascript, caffeinate, launchd)

### 전원 필수
- Gate 1 엄격 검증 (PK-3/4/5 침묵적 실패 방어)
- Atomic write (tmp→rename) 모든 파일 교환에
- 한국어 에러 메시지 (비기술 사용자)

### 전원 배제
- Naver Finance 스크래핑 [LOCAL-BLOCKED — 높은 유지보수, 법적 리스크]
- API 키 기반 LLM 연동 [BLOCKED — 구독 계정 CLI 연동 제약]
- Phase 1 MCP 서버 [불필요 — 배치 파이프라인에 대화형 도구 무의미]
- Phase 1 실시간 스트리밍 [불필요 — 데이터 소스가 일일 배치]

## 영역 간 최대 불일치

### 불일치 #1: MCP 도입 시점
- T01 (MCP Specialist): Phase 2 초기에 DuckDB MCP 즉시 도입 권장
- T02 (Local Tools): DuckDB CLI로 충분, MCP는 부가 복잡도
- **해결**: Phase 2에서 DuckDB MCP 도입하되, CLI 대안 유지

### 불일치 #2: 폴백 깊이
- T03 (API): 4-tier 폴백 (pykrx→FDR→DART→yfinance→캐시) 권장
- T05 (Reliability): FDR 폴백이 ~42분으로 느림, 3-tier(pykrx→FDR→캐시) 충분
- **해결**: 3-tier 유지. FDR은 Top-200 종목만 폴백하여 시간 단축

### 불일치 #3: LLM 연동 범위
- T03 (API): Claude+Gemini+Codex+Ollama 4-LLM 아키텍처 권장
- T04 (Data Flow): 데이터 흐름 복잡도 증가 우려
- **해결**: Phase별 점진 도입. Phase 1=Claude만, Phase 2=+Gemini, Phase 3=+Codex+Ollama
