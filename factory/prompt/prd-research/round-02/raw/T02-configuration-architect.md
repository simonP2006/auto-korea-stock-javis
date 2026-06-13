---
round: 2
type: raw
teammate: configuration-architect
axis: configuration-architecture
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
question_summary: "CLAUDE.md 전략, .claude/ 디렉토리 구조, Hooks 설계, DuckDB 스키마, 메모리·상태 관리를 분석하여 주식 분석 시스템의 최적 설정 아키텍처 도출"
assumption_axis: "Minimal Configuration vs Precision Configuration"
branch_a: "Minimal Configuration (단순 설정 — 유지보수 최소화)"
branch_b: "Precision Configuration (정밀 설정 — 에러 자동 감지)"
web_search_count: 16
local_execution_tags:
  LOCAL_OK: ["CLAUDE.md", ".claude/ directory", "settings.json", "Hooks", "DuckDB schema", "config.yaml", "summary.md", "Skills", "Commands"]
  LOCAL_PARTIAL: ["Hook performance optimization (Bash wrapper)"]
  LOCAL_BLOCKED: []
sources:
  - "Best practices for Claude Code (code.claude.com/docs/en/best-practices)"
  - "Writing a good CLAUDE.md (humanlayer.dev)"
  - "Designing CLAUDE.md correctly: 2026 architecture (obviousworks.ch)"
  - "Best Practices for CLAUDE.md: Ultimate Guide 2026 (amitray.com)"
  - "DuckDB vs SQLite Complete Comparison (datacamp.com)"
  - "DuckDB vs SQLite (motherduck.com)"
  - "Hooks reference — Claude Code Docs"
  - "Claude Code Hooks Tutorial: 5 Production Hooks (blakecrosley.com)"
  - "Manage costs effectively — Claude Code Docs"
  - "Claude Code 1M Context Window (claudecodecamp.com)"
  - "23 Tips for Claude Code Token Saving (analyticsvidhya.com)"
  - "The .claude Directory Explained 2026 (claudedirectory.org)"
  - "Anatomy of the .claude/ Folder (dailydoseofds.com)"
  - "Using CLAUDE.MD files (claude.com/blog)"
  - "CLAUDE.md Examples and Best Practices 2026 (morphllm.com)"
  - "MCP + DuckDB (motherduck.com/blog)"
---

# T02: Configuration Architect — Investigation Report

## Executive Summary

단일 목적 주식 분석 시스템에 최적인 설정은 "Precise Minimal" — 7개 파일·3개 Hook으로 시작하되, SessionStart 데이터 신선도 검증과 PreToolUse DuckDB 보호라는 2개 핵심 안전장치를 포함. 운영 피드백에 따라 단계적 증설.

---

## Branch 2.1: Minimal Configuration — Findings

### 1. CLAUDE.md Minimal Strategy

**포함해야 할 것** (필수):
- 프로젝트 목적 1줄, 스택 선언, 핵심 명령어, 디렉토리 맵 (5-7줄), 핵심 규칙 5-6개

**포함하지 말아야 할 것**:
- 점수 루브릭 상세 (docs/scoring-rubric.md로 분리)
- 파이프라인 구현 상세 (코드 자체에 존재)
- 기술 지표 정의 (참조 자료)
- 사용자 설정 기본값 (config.yaml 또는 DuckDB)

**토큰 비용**: 100줄 CLAUDE.md ≈ 1,500-2,000 토큰. 1M 윈도우 대비 무시 가능하나, 짧을수록 지시 이행률 높음.

**권장 크기**: 80-100줄. 점수 방법론은 `@docs/scoring-rubric.md`로 on-demand 로딩. [LOCAL-OK]

### 2. Memory & State — Minimal

**필수 파일 3개**:

| File | Purpose |
|------|---------|
| data/stocks.duckdb | 모든 OHLCV, 지표, 점수 |
| config.yaml | 사용자 설정 (5-10개 항목) |
| output/summary.md | 최신 스캔 결과 (Claude 읽기용) |

**DuckDB로 ALL state 처리 가능?** — 가능. 단, 사용자 설정은 config.yaml이 적합 (사람이 편집 가능, git diff 가시적). [LOCAL-OK]

### 3. .claude/ Minimal Layout

```
.claude/
├── settings.json       # 권한 + 최소 hooks
├── commands/
│   └── scan.md         # /scan
└── skills/
    └── stock-scanner/
        └── SKILL.md    # 점수 방법론
```

3개 파일. 에이전트 없음 (단일 목적 시스템에 서브에이전트 위임 불필요). [LOCAL-OK]

### 4. Hooks Minimal Design

필수 Hook: SessionStart (데이터 신선도) + PreToolUse(Bash) (DuckDB 보호) = **2개 신규 + 3개 상속** (Stop, PreCompact, SessionEnd). [LOCAL-OK]

### Branch 2.1 Conclusion

7개 파일, 3개 Hook. 일일 스캔 작동. 위험: 침묵적 실패 감지 불가.

---

## Branch 2.2: Precision Configuration — Findings

### 1. CLAUDE.md Hierarchical Strategy

계층 구조: `~/.claude/CLAUDE.md` (글로벌) → `project/CLAUDE.md` (프로젝트) → 워크스페이스별. `@import`로 외부 참조.

**점수 가중치 위치 결정**:
- docs/scoring-rubric.md (@import 참조) — 상세 루브릭
- config.yaml — 가중치 숫자값 (사용자 조정 가능)

권장: 프로젝트 CLAUDE.md ~120줄 + @import 참조. [LOCAL-OK]

### 2. Memory & State — Structured

**DuckDB Schema**:

```sql
-- 핵심 데이터
CREATE TABLE raw_ohlcv (code, name, date, open, high, low, close, volume, market, sector);
CREATE TABLE indicators (code, date, sma_5..sma_120, rsi_14, macd, bbands_*, obv, atr_14, adx_14, volume_sma_20);
CREATE TABLE scores (code, date, ma_alignment, base_formation, volume_behavior, momentum, breakout_readiness, relative_strength, total_score, rank);

-- 상태
CREATE TABLE scan_history (scan_date, stocks_scanned, top_10_codes, execution_time_sec, errors, status);
CREATE TABLE user_watchlist (code, name, added_date, notes);
CREATE TABLE alerts (id, code, alert_type, triggered_date, message, acknowledged);
```

**파일 기반 상태**: config.yaml, output/summary.md, output/alerts.json, output/sector-report.md, data/scan-status.json. [LOCAL-OK]

### 3. .claude/ Comprehensive Layout

```
.claude/
├── settings.json
├── agents/
│   ├── stock-analyst.md
│   └── reporter.md
├── commands/
│   ├── scan.md, analyze.md, sector.md, config.md
├── skills/
│   └── stock-scanner/
│       ├── SKILL.md
│       └── references/
│           ├── indicators.md, scoring-rubric.md, examples/
└── hooks/scripts/
    ├── check_data_freshness.py, verify_dependencies.py
    ├── block_duckdb_danger.py, log_pipeline_run.py
    └── archive_analysis.py
```

10개 파일. [LOCAL-OK]

### 4. Hooks Comprehensive Design

5개 Hook: Setup(init), SessionStart, PreToolUse(Bash), PostToolUse(Bash), Stop.

**성능 우려**: PreToolUse/PostToolUse가 Bash 호출마다 Python 기동(~300ms). 스캔 중 20회 Bash → 12초 오버헤드. **완화**: Bash 래퍼로 early-exit. [LOCAL-PARTIAL]

### Branch 2.2 Conclusion

20개 파일, 5개 Hook. 에러 자동 감지·기록·경고. 개발 4-5일. Hook 성능 최적화 필요.

---

## Branch 2.1 vs 2.2 Synthesis

### Recommended: "Precise Minimal" (Phase-based)

**Phase 1 — Ship It (Week 1)**:

```
CLAUDE.md (~100줄)
config.yaml
data/stocks.duckdb
output/summary.md

.claude/
├── settings.json (권한 + 3 hooks)
├── commands/scan.md
└── skills/stock-scanner/
    ├── SKILL.md
    └── references/scoring-rubric.md
```

Hooks: SessionStart(check_data_freshness.py) + PreToolUse(block_duckdb_danger.py) + 상속 3개.

**Total: 7 파일, 3 신규 Hook.** [LOCAL-OK]

**Phase 2 — Harden (Week 3-4)**: /analyze 명령어, PostToolUse 로깅, alerts.json (운영 피드백 기반).

**Phase 3 — Optimize (Month 2+)**: 서브에이전트, 섹터별 워크스페이스, scan_history 테이블.

### Parking Lot

1. pykrx rate limiting → DuckDB 스키마에 last_updated 컬럼 필요 여부
2. launchd + Claude Code 상호작용: 순수 Python 스캔 vs Claude 세션 생성 → Hook 설계 영향
3. DuckDB 5년 용량: ~50-100MB, 백업 전략 필요
4. 상속 hooks 호환성: AgenticWorkflow → stock system fork 시 어떤 Hook 유지/제거
5. config.yaml 스키마: watchlist, sectors_of_interest, min_score_threshold, alert_types
