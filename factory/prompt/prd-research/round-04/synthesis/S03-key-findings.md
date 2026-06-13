---
round: 4
type: synthesis
topic: key-findings
investigation_axis: external-integration
created: "2026-05-26T16:00:00+09:00"
title: "4차 조사 핵심 발견 — 외부 연동 기술 축 Cross-Cutting Discoveries"
input_agents:
  - "T01: MCP Server Specialist"
  - "T02: Local Tool Integration Expert"
  - "T03: API & Service Connector"
  - "T04: Data Flow Architect"
  - "T05: Reliability & Fallback Engineer"
cross_cutting_axes:
  - "all 5 external-integration axes"
---

# S03: 핵심 발견 (4차 조사 — 외부 연동 기술 축)

## Finding 1: Phase 1에서 외부 연동은 사실상 pykrx 하나뿐

**출처**: T01 (MCP), T02 (Local Tools), T03 (API), T04 (Data Flow)

Phase 1 배치 파이프라인의 외부 의존성 분석:
- **네트워크 필수**: pykrx (KRX 데이터 수집) — 유일한 외부 연동 지점
- **로컬 완결**: DuckDB, pandas-ta, uv, macOS 내장 도구 — 전부 로컬
- **MCP 불필요**: Phase 1은 launchd → python3 main.py 배치. 대화형 MCP 컨텍스트 없음
- **LLM 연동 불필요**: Engine 2 (Claude Code)는 Engine 1 산출물(summary.md) 해석만

**PRD 함의**: Phase 1 외부 연동 섹션은 pykrx + 3-tier 폴백(FDR→캐시)에 집중.
Phase 2+ 연동은 별도 로드맵 섹션으로 분리.

---

## Finding 2: OpenAI/Gemini 구독 계정 CLI 연동이 실제로 가능함 [LOCAL-OK]

**출처**: T03 (API & Service Connector)

**OpenAI Codex CLI**:
- `npm install -g @openai/codex` → 브라우저 OAuth → ChatGPT 구독으로 과금
- `codex exec "task"` 비대화형 모드로 Claude Code Bash에서 호출 가능
- 공식 `codex-plugin-cc` 플러그인으로 Claude Code 내 직접 통합
- [LOCAL-OK]

**Gemini CLI**:
- `npm install -g @google/gemini-cli` → 브라우저 Google 계정 로그인
- `gemini -p "prompt"` 헤드리스 모드, `--output-format json` 구조화 출력
- 무료 티어: 60 RPM / 1,000 RPD (Gemini 2.5 Pro) — 구독 없이도 충분할 수 있음
- [LOCAL-OK]

**핵심**: 둘 다 API 키 없이 구독 계정 인증으로 작동. ABSOLUTE ANCHOR ② 제약 완전 충족.

---

## Finding 3: 한국 주식 전용 MCP 서버 생태계가 이미 존재

**출처**: T01 (MCP), T03 (API)

| MCP 서버 | 출처 | 특징 | 상태 |
|----------|------|------|------|
| pykrx-mcp (sharebook-kr) | pykrx 공식 메인테이너 | KOSPI/KOSDAQ/KONEX, 재무제표, 투자자별 | [UNVERIFIED] 2026 신규 |
| kospi-kosdaq-stock-server | dragon1086 | OHLCV, 시가총액, PER/PBR | ★59, [LOCAL-OK] |
| korea-stock-mcp | jjlabsio | DART 공시 + KRX 가격 | DART/KRX API 키 필요 |
| Korea Stock Analyzer | Mrbaeksang | 6가지 투자 전략, RSI/MACD/볼린저 | [LOCAL-OK] |
| DuckDB MCP (ktanaka101) | ktanaka101 | SQL 쿼리, 읽기전용 모드 | ★141, [LOCAL-OK] |
| DuckDB MCP (MotherDuck) | MotherDuck 공식 | 로컬 DuckDB + 클라우드, 파일 잠금 없음 | [LOCAL-OK] |

**PRD 함의**: Phase 2 대화형 분석에서 DuckDB MCP(읽기전용) + pykrx-mcp 조합으로
Claude Code가 데이터베이스 직접 쿼리 + 실시간 시세 조회 가능.

---

## Finding 4: Light 로컬 도구 전략이 압도적 승리

**출처**: T02 (Local Tool Integration Expert)

**최소 설치**: uv 1개 (curl 설치) + Python 패키지 3개 (pykrx, duckdb, pandas-ta).
나머지 전부 macOS 내장:
- jq v1.7.1-apple (macOS Tahoe 내장 — 새 발견)
- osascript (네이티브 알림)
- caffeinate (파이프라인 중 절전 방지)
- launchd (스케줄링)
- plutil (plist 검증)

**DuckDB CLI 불필요**: Python API가 기능 완전. CLI는 개발자 편의 도구.
**fswatch 불필요**: launchd WatchPaths가 내장 대안.

**bootstrap.sh**: curl로 uv 설치 → `uv sync` → 완료. Homebrew 불필요. 목표 설치 시간: 1-2분.

---

## Finding 5: pandas-ta 아카이브 위험 — 2026년 7월 1일 마감

**출처**: T02 (Local Tool Integration Expert)

pandas-ta가 2026년 7월 1일까지 아카이브 예정 (지원 부족 시).
- **대안**: pandas-ta-classic (커뮤니티 포크, 200+ 지표, 활발히 유지)
- **호환성**: 드롭인 교체 가능 (API 호환)
- **조치**: pyproject.toml에 `pandas-ta>=0.3.14b1` 핀, 아카이브 후 classic으로 교체

**PRD 함의**: 위험 등록부에 R-4-1로 등록. 마이그레이션 경로 명시 필수.

---

## Finding 6: pykrx "치명적 3인조" — 침묵적 실패의 실체

**출처**: T05 (Reliability & Fallback Engineer)

28개 장애 모드 중 PK-3, PK-4, PK-5가 가장 위험:
| ID | 장애 | 침묵? | 결과 |
|----|------|-------|------|
| PK-3 | 전 종목 0원 반환 | **침묵** | 쓰레기 점수 전량 산출 |
| PK-4 | 2,500 중 1,800만 반환 | **침묵** | 700종목 누락, 편향 분석 |
| PK-5 | 어제 데이터를 오늘로 표시 | **침묵** | 날짜 오인, 잘못된 신호 |

**방어**: Gate 1 엄격 검증이 유일한 방어선. 없으면 쓰레기가 최종 보고서까지 관통.

---

## Finding 7: 배치 데이터 흐름이 Phase 1의 유일한 정답

**출처**: T04 (Data Flow Architect)

| 패턴 | Phase 1 가치 | 결론 |
|------|-------------|------|
| MCP 스트리밍 | 없음 | Skip |
| fswatch → claude -p | 없음 (일 1회 실행) | Phase 2+ |
| stdin/stdout 파이프 | 낮음 | 일회성 핸드오프 OK |
| SessionStart 훅 | **높음** | 데이터 신선도 보고 |
| launchd → python3 → 파일 | **최고** | 메인 패턴 |

**Atomic write**: 모든 파일 쓰기에 tmp→rename 패턴 필수 (~10줄 유틸리티).
**summary.md 포맷**: YAML 프론트매터(메타데이터) + Markdown 본문(LLM 해석용).

---

## Finding 8: DuckDB 저장량은 10년간 문제 없음

**출처**: T04 (Data Flow Architect)

- 5년 이력: ~3.37M rows/테이블 × 3 테이블
- DuckDB 압축 후: ~40-80MB
- 연간 증가: ~50MB
- 10년 후: ~90-150MB — macOS에서 무시 가능
- ACID + WAL + fsync: 단일 프로세스에서 매우 안정

---

## Finding 9: 알림은 osascript(Phase 1) + Telegram(Phase 2+)

**출처**: T03 (API), T05 (Reliability)

| 방법 | Phase | 설정 복잡도 | 결론 |
|------|-------|-----------|------|
| osascript 네이티브 알림 | Phase 1 | 0 (내장) | 즉시 사용 |
| Telegram 봇 | Phase 2+ | 낮음 (BotFather) | 양방향, Claude Code Channel 지원 |
| Slack MCP | Phase 2+ | 중간 (OAuth) | 팀 환경 |
| Gmail MCP | Phase 2+ | 중간 (OAuth) | 이미 프로젝트에 존재 |
| KakaoTalk | 미정 | 높음 (Accessibility) | 비공식 해킹적 접근 |

---

## Finding 10: LOCAL-BLOCKED 항목 = 0개 (4라운드 연속)

**출처**: T01-T05 전체

[LOCAL-BLOCKED]: **0개** (3차에 이어 4차에서도 확인)

[LOCAL-PARTIAL]: 3개 (모두 네트워크 의존, 캐시 폴백 존재)
1. pykrx — KRX 서버 의존, DuckDB 캐시 폴백
2. Claude Code API — Anthropic 서버 의존, Ollama 오프라인 폴백
3. 알림 서비스 — 네트워크 의존, osascript 로컬 폴백

---

## Cross-Round Continuity (1차 → 2차 → 3차 → 4차)

| 이전 발견 | 4차 검증·확장 |
|---------|-------------|
| Hybrid 아키텍처 (1차) | 외부 연동 관점에서도 Two-Engine 분리 정당: Engine 1 외부 의존 최소, Engine 2 순수 해석 |
| 4개 의존성 확정 (2차) | Light 전략으로 brew 0개 확인. pandas-ta 아카이브 위험 신규 발견 |
| MCP Phase 1 불필요 (2차) | Phase 1 = 0 MCP 확정. Phase 2 = DuckDB + pykrx MCP 로드맵 구체화 |
| 침묵적 실패 #1 위험 (2차) | 28개 장애 모드 카탈로그, PK-3/4/5 "치명적 3인조" 구체화 |
| 4-Gate 검증 (3차) | Fail-fast + 선택적 degradation 전략으로 Gate 위에 신뢰성 계층 구축 |
| 파일 기반 상태 (3차) | 커스텀 FileCircuitBreaker(파일 기반 상태 지속)로 확장 |
| Balanced 시나리오 ~3,300줄 (3차) | + 신뢰성 ~1,060줄 → 총 ~4,360-4,660줄 추정 |

---

## 미해결 항목 통합 (Integrated Parking Lot)

### 이전 라운드 이관 항목 (상태 업데이트)

1. **pykrx 데이터 가용 시점** (2차 PL#1): 여전히 미해결. 실증 필요.
2. **5년 초기 데이터 로딩** (2차 PL#2): ~60-90분 확인. checkpoint 재개 설계 완료.
3. **claude -p 구독 계정 호환** (2차 PL#3): GitHub #36324 추적 중.
4. **pandas-ta numba Apple Silicon** (2차 PL#4): 비호환 시 비활성화.
5. **pykrx 수정주가** (2차 PL#5): 여전히 미해결.
6-15. **3차 항목**: 상태 유지.

### 4차에서 새로 식별된 항목

16. **pandas-ta 아카이브 위험**: 2026.07.01 마감. pandas-ta-classic 마이그레이션 평가 필요.
17. **pykrx-mcp 안정성**: sharebook-kr의 MCP 서버가 매우 새로움. 실증 테스트 필요.
18. **예약 작업 + MCP 초기화 버그**: GitHub #32000, #35899, #43397. Phase 2 MCP 도입 전 추적.
19. **Codex CLI -q 모드 버그**: non-git 디렉터리에서 git warning으로 hang 가능.
20. **macOS Tahoe Keychain 회귀**: `security -w` hang. Python keyring 대안.
21. **FDR 폴백 속도**: ~42분 (2,500 ticker × 1 req/sec). Top-200만 폴백 고려.
22. **Korea Stock Analyzer MCP vs 커스텀 파이프라인**: 기술 지표 중복. 아키텍처 결정 필요.
23. **Gemini CLI 무료 티어 충분성**: 1,000 req/day. 일일 사용량 추정 필요.
24. **osascript 알림 macOS Sequoia 호환성**: Terminal.app에서 작동 여부 미확인.
25. **summary.md 품질 배지 위치**: 최상단 필수 (매몰 시 degradation 경고 놓침).
