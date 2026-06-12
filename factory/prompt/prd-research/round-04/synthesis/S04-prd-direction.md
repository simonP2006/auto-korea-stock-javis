---
round: 4
type: synthesis
topic: prd-direction
investigation_axis: external-integration
created: "2026-05-26T16:30:00+09:00"
title: "4차 조사 PRD 방향 조언 — 외부 연동 기술 축 반영"
inputs:
  - "synthesis/S01-integration-spectrum.md"
  - "synthesis/S02-discussion-scenarios.md"
  - "synthesis/S03-key-findings.md"
---

# S04: PRD 방향 조언 (4차 — 외부 연동 기술 축)

## 연동 시나리오 비교 (Phase 2 토론 + Phase 3 시나리오 통합)

### 3가지 연동 수준 비교

| 기준 | Full Integration | Selective Integration | Self-Contained |
|------|-----------------|---------------------|----------------|
| MCP 서버 | 4개 (DuckDB+pykrx+Thinking+Slack) | 1개 (DuckDB 읽기전용) | 0개 |
| LLM 제공자 | Claude+Codex+Gemini+Ollama | Claude+Gemini | Claude만 |
| 로컬 도구 (brew) | 2개 (duckdb-cli, fswatch) | 0개 | 0개 |
| 알림 | Telegram+Slack+osascript | Telegram+osascript | osascript만 |
| 데이터 소스 | pykrx+FDR+DART+yfinance | pykrx+FDR | pykrx+캐시 |
| 외부 의존 수 | ~15 | ~6 | ~2 |
| 설정 복잡도 | 높음 | 중간 | 낮음 |
| 실패 지점 수 | ~12 | ~5 | ~2 |
| 오프라인 작동 | 제한적 | 부분 가능 | 대부분 가능 |
| 이식성 | 낮음 | 중간 | 높음 |
| 기능 범위 | 최대 | 핵심+α | 핵심만 |

### 권장: Selective Integration (Phase별 점진 확장)

**Phase 1 = Self-Contained에 가까움**:
- 외부 연동: pykrx 1개 + FDR/캐시 폴백
- MCP: 0개
- LLM: Claude Code Max 1개
- 알림: osascript (내장)
- 데이터 흐름: 100% 배치
- 설치: uv + Python 패키지 3개

**Phase 2 = Selective Integration**:
- +DuckDB MCP (읽기전용, 대화형 쿼리)
- +Gemini CLI (대량 분석, 무료 티어)
- +Telegram 봇 (양방향 알림)
- +claude -p 헤드리스 자동화
- +launchd WatchPaths (파일 변경 감지)

**Phase 3 = Full Integration 선택 요소**:
- +Codex CLI (코드 리뷰, 세컨드 오피니언)
- +pykrx-mcp (실시간 시세 조회)
- +DART API (기업 재무제표)
- +모델 계층화 (루틴=Sonnet, 심층=Opus)
- +Ollama 오프라인 폴백

---

## PRD 섹션별 외부 연동 축 반영 방향

### Section 3: 아키텍처 — 외부 연동 레이어 추가

**반영 관점**: Two-Engine 아키텍처에 연동 레이어를 명시적으로 추가.

**반영 내용**:

1. **연동 경계 선언**:
   ```
   Engine 1 (Python Pipeline):
     외부 연동: pykrx (KRX 네트워크) — 유일한 네트워크 의존
     폴백: pykrx → FDR → DuckDB 캐시 (3-tier)
     나머지: 전부 로컬 (DuckDB, pandas-ta, 파일 시스템)

   Engine 2 (Claude Code):
     외부 연동: Anthropic API (LLM 호출)
     로컬 자원: summary.md 읽기, Hook 실행, Skill 참조
     Phase 2+ 연동: DuckDB MCP, Gemini CLI, Telegram
   ```

2. **MCP 로드맵 (Phase 2+)**:
   - Phase 2: `mcp-server-duckdb --readonly` (Claude가 DB 직접 쿼리)
   - Phase 2: DuckDB MCP는 MotherDuck 또는 ktanaka101 중 파일 잠금 동작 비교 후 결정
   - Phase 3: pykrx-mcp (대화형 실시간 시세), 안정성 검증 후

3. **LLM 연동 아키텍처 (Phase 2+)**:
   ```
   Claude Code Max (주 오케스트레이터)
     ├─ Bash → gemini -p (배치 분석, Google Account OAuth)
     ├─ Bash → codex exec (코드 리뷰, ChatGPT OAuth)
     └─ Fallback: Ollama (DeepSeek-R1, 오프라인)
   ```
   - **중요**: 모든 LLM 연동은 CLI → 구독 계정 인증. API 키 0개.
   - Gemini 무료 티어(1,000 req/day)만으로 Phase 2 충분할 수 있음

4. **알림 아키텍처**:
   - Phase 1: `osascript -e 'display notification "..." with title "주식 분석기"'`
   - Phase 2: Telegram 봇 (BotFather → TELEGRAM_BOT_TOKEN + CHAT_ID)
   - Phase 2+: Gmail MCP (이미 프로젝트에 존재)

### Section 5: 신뢰성·검증 — 외부 연동 실패 대응

**반영 관점**: 외부 연동 지점마다 실패 모드와 대응 전략 명시.

**반영 내용**:

1. **장애 모드 카탈로그**: 28개 장애 모드 (pykrx 9, DuckDB 6, Claude 6, Network 4, macOS 5)
   - "치명적 3인조" (PK-3/4/5): 침묵적 실패 → Gate 1 엄격 검증이 유일한 방어선

2. **Circuit Breaker 설계**:
   - 대상: pykrx (유일한 외부 데이터 소스)
   - 패턴: 커스텀 FileCircuitBreaker (~230줄) — 프로세스 간 상태 지속
   - 임계값: 3회 연속 일일 실패 → OPEN → 24시간 후 HALF_OPEN
   - pybreaker 부적합 이유: 인메모리 상태, 마이크로서비스 패턴 (일일 배치와 불일치)

3. **Fail-fast 기본 + 선택적 Degradation**:
   - **Fail-fast 구역**: Gate 1 CRITICAL, Gate 3 CRITICAL, DB 손상
   - **Degradation 구역**: 데이터 소스 폴백 (pykrx→FDR→캐시), 부분 데이터 경고
   - **품질 배지**: summary.md 최상단에 "⚠️ 어제 데이터로 분석" 스타일 경고

4. **표준 종료 코드 체계**: ExitCode enum (0-79), 각 코드에 한국어 메시지 매핑

5. **구현량 추정 업데이트**:
   ```
   기존 (3차): ~3,300-3,700줄
   + 신뢰성 레이어: ~1,060줄 (circuit breaker, fallback chain, notification, health check)
   = 총 ~4,360-4,760줄
   ```

### Section 4: 사용자 경험 — 설치와 알림

**반영 관점**: 비기술 사용자의 설치 마찰 최소화 + 이해 가능한 에러 메시지.

**반영 내용**:

1. **bootstrap.sh 최종 설계**:
   ```bash
   curl로 uv 설치 → uv sync → DuckDB 초기화 → launchd 설정 (선택)
   ```
   - Homebrew 불필요 (macOS 내장 + uv만으로 충분)
   - 목표 설치 시간: **1-2분** (Homebrew 경유 시 5-15분이었음)
   - 가장 큰 마찰점: KRX 계정 등록 (도구 설치가 아님)

2. **에러 메시지 한국어화**:
   - "pykrx connection refused" → "한국거래소(KRX) 서버에 연결할 수 없습니다. 점검 시간일 수 있습니다."
   - ExitCode enum + EXIT_MESSAGES_KO 딕셔너리 (~30개 메시지)

3. **알림 UX**:
   - Phase 1: macOS 네이티브 알림 (소리 포함: 성공 시 기본, 실패 시 "Basso")
   - `caffeinate -i` 파이프라인 래핑: Mac 절전 방지

### Section 6: 데이터 전략 — 데이터 흐름 구체화

**반영 관점**: 파일 기반 배치 교환의 안전한 구현.

**반영 내용**:

1. **Atomic write 패턴**: tmp 파일 → os.replace() 원자적 이름 변경 (~10줄 유틸리티)
   - summary.md, pipeline_state.json, 모든 JSON 상태 파일에 적용

2. **summary.md 인터페이스 설계**:
   - 포맷: YAML 프론트매터(report_date, stock_count, scoring_config_hash, gates_passed, degraded) + Markdown 본문
   - 크기: ~15-25KB (~5,000-8,000 토큰) — 1M 컨텍스트의 <1%
   - 콘텐츠: Market Overview 테이블 + Top 80 순위 + Anomaly Alerts + Sub-Score Distribution + Data Quality

3. **DuckDB 볼륨 예측**:
   - 5년 이력: ~3.37M rows × 3 테이블 → 압축 후 ~40-80MB
   - 연간 증가: ~50MB
   - 정리 불필요 기간: ~10년

4. **Phase 2+ 파일 확장**:
   ```
   output/
   ├── summary.md              ← Phase 1 (항상 존재)
   ├── detail/{ticker}.md      ← Phase 2 (/analyze TICKER 용)
   ├── archive/                ← Phase 2 (일일 보관)
   └── market/                 ← Phase 3 (시장별 분리)
   ```

### Section 7: 지속가능성 — 비용 구조

**반영 관점**: 구독 기반 비용 모델 확인.

**반영 내용**:
- Claude Code Max: $200/월 (이미 구독)
- ChatGPT Plus: $20/월 (이미 구독) — Codex CLI 포함
- Gemini Advanced: $20/월 (이미 구독) — 무료 티어만으로 충분할 수 있음
- pykrx/FDR/DuckDB/pandas-ta: 무료
- Telegram 봇: 무료
- **API 키 기반 비용: $0** (모든 LLM이 구독 계정 인증)
- 총 월비용: ~$240 (전부 기존 구독, 추가 비용 0)

### Section 8: 위험 등록부 — 4차 추가 항목

| ID | 위험 | 영향 | 확률 | 완화 |
|----|------|------|------|------|
| R-4-1 | pandas-ta 2026.07.01 아카이브 | HIGH | HIGH | pandas-ta-classic 마이그레이션 준비 |
| R-4-2 | pykrx-mcp 안정성 미검증 | MED | MED | Phase 2 도입 전 실증 테스트 |
| R-4-3 | 예약 작업 MCP 초기화 버그 | MED | MED | GitHub #32000 추적, Phase 2 전 확인 |
| R-4-4 | Codex CLI -q 모드 git hang | LOW | MED | git repo 내에서만 실행 또는 플러그인 사용 |
| R-4-5 | macOS Tahoe Keychain 회귀 | MED | HIGH | Python keyring 라이브러리 대안 |
| R-4-6 | FDR 폴백 속도 (~42분) | MED | LOW | Top-200 종목만 폴백 또는 병렬화 |

---

## 조사 품질 검증 — 3층위 자기 점검

### 1층위: 사실 확인

| 외부 연동 축 | 커버리지 | 출처 |
|------------|---------|------|
| MCP 서버 생태계 (공식+커뮤니티) | ✅ | T01 (WebSearch 24회) |
| 로컬 도구 (macOS 내장 + brew) | ✅ | T02 (실환경 검증) |
| 금융 데이터 API (pykrx/FDR/DART/yfinance) | ✅ | T03 (WebSearch 32회) |
| LLM 연동 (OpenAI/Gemini/Ollama) | ✅ | T03 (CLI 인증 방식 검증) |
| 알림 서비스 (Telegram/Slack/Gmail/Kakao/LINE) | ✅ | T03 |
| 데이터 흐름 (배치/실시간/직렬화) | ✅ | T04 (WebSearch 26회) |
| 신뢰성 (장애 모드/회로차단기/폴백) | ✅ | T05 (WebSearch 11회, 28 FM) |
| 인증·보안 (OAuth/API키/Keychain) | ✅ | T03 |
| 비용·제한 | ✅ | T03 |
| 로컬 실행 태그 | ✅ | 전 항목 태깅 |

**불일치**: 없음. 5개 도메인 전체 커버.

### 2층위: 구조 분석 — PRD 연동 섹션 구성 시 먼저 무너지는 지점

1. **Phase 1→2 전환 경계 모호**: "언제 MCP를 추가하는가"의 기준 부재 → PRD에 Phase 2 진입 조건 명시 필요
2. **Gemini 무료 vs 구독 분기점**: 일일 사용량 추정 없이는 결정 불가 → Phase 2 초기 사용량 측정 후 결정
3. **pandas-ta 아카이브와 기존 설계 영향**: scoring_config.yaml의 4개 소비자 중 analyze.py가 pandas-ta 의존 → 교체 시 Gate 2 임계값 재교정 필요

### 3층위: 역방향 점검 — 다루지 않은 것

| 누락 항목 | PRD 영향도 | 조치 |
|-----------|-----------|------|
| CI/CD 연동 (GitHub Actions 등) | LOW | Phase 1 불필요, 로컬 실행 |
| 모니터링 대시보드 (Grafana 등) | LOW | Phase 1 파일 로그 충분 |
| 백업 클라우드 동기화 (iCloud/S3) | LOW | Phase 2+ 고려 |
| 다중 사용자/팀 연동 | LOW | 단일 사용자 시스템 |
| AI Agent SDK (Anthropic) | MED | Phase 2+ 자동화에 영향 — 2차에서 부분 조사됨 |
| 한국어 STT/TTS 연동 | LOW | 음성 인터페이스 미계획 |

---

## 1차 → 2차 → 3차 → 4차 → PRD 흐름 요약

```
1차 조사 (일반 축)
  → Hybrid 아키텍처, 비기술 사용자, Branch B 통합

2차 조사 (기술·이론 축)
  → 6개 서브스코어, 4개 의존성, Pragmatic 시나리오
  → 침묵적 실패 = #1 위험

3차 조사 (코딩·구현 축)
  → Hybrid workflow.md, 중앙 오케스트레이션
  → 4-Gate 검증, 파일 기반 상태, ~3,300줄
  → scoring_config.yaml SOT

4차 조사 (외부 연동 축) ← 이번
  → Phase 1 외부 연동 = pykrx 하나 + 폴백
  → OpenAI/Gemini CLI 구독 인증 [LOCAL-OK] 확인
  → Light 도구 전략 (brew 0개)
  → 배치 100%, Atomic write 필수
  → 28개 장애 모드, 커스텀 회로차단기
  → pandas-ta 아카이브 위험 신규 발견
  → LOCAL-BLOCKED: 0개 (4라운드 연속)

→ PRD.md (다음 단계)
  → 1·2·3·4차 재료를 섹션별 반영
  → 미해결 25개 중 실증 테스트 6개 + 아키텍처 결정 3개는 구현 단계에서 해소
```
