---
round: 4
type: raw
teammate: reliability-fallback-engineer
axis: reliability-strategy
investigation_axis: external-integration
created: "2026-05-26T15:00:00+09:00"
question_summary: "Fail-fast vs graceful degradation reliability strategies for KOSPI/KOSDAQ stock pipeline — circuit breaker, monitoring, recovery, user notification, 28 failure modes"
assumption_axis: "Fail-Fast vs Graceful Degradation"
branch_a: "Branch 5.1 — Fail-Fast (stop immediately, preserve state, notify)"
branch_b: "Branch 5.2 — Graceful Degradation (continue with reduced quality, mark degradation)"
web_search_count: 11
canonical_location: "../../research/reliability-fallback/branch-5-reliability-fallback-analysis.md"
local_execution_tags:
  LOCAL_OK: ["circuit breaker (custom FileCircuitBreaker)", "osascript notification", "structured logging (JSON)", "checkpoint-based recovery", "DuckDB ACID/WAL", "pipeline_state.json", "exit codes with Korean messages", "health check", "fcntl.flock", "quality markers/badges", "fallback chain (pykrx→FDR→cache)", "anomaly detection"]
  LOCAL_PARTIAL: ["launchd missed schedule (coalesced on wake)", "Claude API (network dependent)", "pykrx (KRX server dependent)"]
  LOCAL_BLOCKED: []
sources:
  - desc: "Round 2 S03 Finding 2 — Silent Failure is #1 risk"
  - desc: "Round 3 T04 — 4-Gate Targeted Strict verification (~780 lines)"
  - desc: "Round 3 T05 — File-based state management (pipeline_state.json)"
  - desc: "pybreaker v1.3.0 — Python circuit breaker library"
  - desc: "DuckDB ACID documentation — MVCC + WAL + fsync"
  - desc: "macOS launchd documentation — StartCalendarInterval sleep behavior"
  - desc: "pykrx GitHub issues — silent failure modes documented"
  - desc: "Anthropic status page — 99.32% 30-day uptime (2025-2026)"
---

# T05: Reliability & Fallback Engineer — Fail-Fast vs Graceful Degradation

> **Canonical document**: The full 2,127-line research report is located at:
> `research/reliability-fallback/branch-5-reliability-fallback-analysis.md`
>
> This file is the round-04/raw/ reference entry per extension rules.
> The canonical document contains the complete analysis including all 28 failure modes,
> circuit breaker implementation, exit code design, and cost estimates.

## Executive Summary

**Fail-fast as default + selective narrow degradation** is the recommended strategy. 28 failure modes were cataloged across 5 domains (pykrx 9, DuckDB 6, Claude Code 6, Network 4, macOS 5). The "lethal trio" (PK-3/4/5) — silent pykrx failures that produce garbage scores — is the primary threat. A custom `FileCircuitBreaker` (~230 lines, JSON file persistence) is recommended over pybreaker for daily batch context.

---

## Key Findings Summary

### 28 Failure Mode Catalog

| Domain | Count | Silent? | Primary Defense |
|--------|-------|---------|----------------|
| pykrx | 9 | PK-3/4/5 are **SILENT** | Gate 1 strict validation |
| DuckDB | 6 | None silent | Exception handling |
| Claude Code | 6 | None destructive | Engine 2 is interpretation-only |
| Network | 4 | None silent | Retry + timeout |
| macOS | 5 | OS-1/2 (missed schedule) | caffeinate + launchd coalescing |

### The "Lethal Trio" (PK-3, PK-4, PK-5)

| ID | Failure | Why Silent | Consequence |
|----|---------|-----------|-------------|
| PK-3 | All-zero prices returned | pykrx returns valid DataFrame with 0.0 values | Garbage scores for ALL stocks |
| PK-4 | Partial data (1,800/2,500 stocks) | pykrx returns valid DataFrame, just shorter | 700 stocks missing, biased analysis |
| PK-5 | Stale data (yesterday labeled as today) | No date mismatch exception | Wrong signals from outdated prices |

**Defense**: Gate 1 validation is the ONLY defense. Without it, garbage propagates to summary.md undetected.

### Circuit Breaker: Custom FileCircuitBreaker

- **Why not pybreaker**: In-memory state doesn't survive between daily launchd invocations
- **Design**: JSON file persistence at `data/circuit_breaker_state.json`
- **States**: CLOSED → OPEN (after 3 consecutive daily failures) → HALF_OPEN (after 24h cooldown)
- **Implementation**: ~230 lines Python, no external dependencies
- **Target**: pykrx only (sole external data dependency in Phase 1)

### Fail-Fast vs Degradation Zones

| Zone | Strategy | Examples |
|------|----------|---------|
| **Fail-fast** | Stop, preserve state, notify | Gate 1 CRITICAL failure, DB corruption, disk full |
| **Degrade** | Continue with reduced quality + badge | Data source fallback (pykrx→FDR→cache), partial data with warning |
| **Retry** | Retry with backoff, then fail-fast | Network timeout, pykrx rate limit |
| **Ignore** | Log and continue | DuckDB WAL auto-recovery, launchd coalescing |

### Exit Code System

Standard exit codes (0-79) with Korean messages:

| Range | Category | Example |
|-------|----------|---------|
| 0 | Success | "파이프라인 성공적으로 완료" |
| 1-9 | General errors | "설정 파일 누락" |
| 10-19 | Data collection | "KRX 서버 연결 실패" |
| 20-29 | Analysis | "기술 지표 계산 실패" |
| 30-39 | Scoring | "점수 계산 범위 이상" |
| 40-49 | Reporting | "요약 보고서 생성 실패" |
| 50-59 | Database | "DuckDB 파일 손상" |
| 70-79 | System | "디스크 공간 부족" |

### Implementation Cost

| Component | Lines | Purpose |
|-----------|-------|---------|
| FileCircuitBreaker | ~230 | pykrx circuit breaker |
| FallbackChain | ~180 | pykrx→FDR→cache data source fallback |
| NotificationManager | ~150 | osascript + Phase 2 Telegram |
| ExitCode enum + messages | ~120 | Structured exit codes + Korean messages |
| HealthCheck | ~150 | Pre-flight checks (disk, DB, network) |
| Quality badges | ~100 | summary.md degradation markers |
| Anomaly detection | ~130 | Score distribution anomaly detection |
| **Total** | **~1,060** | |

Combined with Round 3 estimates (~3,300 lines), total system: **~4,360-4,660 lines**.

---

## Full Document Reference

The complete analysis (2,127 lines) at the canonical location includes:

1. **Section 1**: Full 28-failure-mode catalog with detection methods, frequency, blast radius
2. **Section 2**: Detailed Branch 5.1 (Fail-Fast) analysis with implementation code
3. **Section 3**: Detailed Branch 5.2 (Graceful Degradation) with fallback chain code
4. **Section 4**: FileCircuitBreaker complete implementation (~230 lines)
5. **Section 5**: Exit code system with full ExitCode enum and Korean message mapping
6. **Section 6**: Comparison matrix (Fail-Fast vs Degradation across 12 dimensions)
7. **Section 7**: Notification architecture (osascript → Telegram → Slack progression)
8. **Section 8**: Health check and pre-flight validation
9. **Section 9**: Cost estimation and implementation sizing

---

## Parking Lot

1. **pybreaker vs custom benchmark**: Verify FileCircuitBreaker JSON I/O overhead is <1ms
2. **FDR fallback Top-200 strategy**: Which 200 stocks? By market cap? By recent volume?
3. **Anomaly detection baseline**: Need 30+ days of score distribution data before reliable detection
4. **Telegram notification rate limit**: Telegram Bot API allows 30 msg/sec — more than sufficient
5. **launchd coalescing behavior**: Exact behavior when Mac wakes after multiple missed intervals
