---
round: 4
type: raw
teammate: reliability-fallback-engineer
axis: reliability-strategy
investigation_axis: deep-dive-research
created: "2026-05-26T15:00:00+09:00"
question_summary: "Fail-fast vs graceful degradation reliability strategies for KOSPI/KOSDAQ stock pipeline — circuit breaker, monitoring, recovery, user notification"
assumption_axis: "Fail-Fast vs Graceful Degradation"
branch_a: "Branch 5.1 — Fail-Fast (stop immediately, preserve state, notify)"
branch_b: "Branch 5.2 — Graceful Degradation (continue with reduced quality, mark degradation)"
web_search_count: 11
local_execution_tags:
  LOCAL_OK: ["circuit breaker (pybreaker/custom)", "osascript notification", "terminal-notifier", "structured logging (structlog/JSON)", "checkpoint-based recovery", "DuckDB ACID/WAL", "pipeline_state.json", "exit codes", "health check", "fcntl.flock", "quality markers", "fallback chain", "anomaly detection"]
  LOCAL_PARTIAL: ["launchd missed schedule (coalesced on wake)", "Claude API (network dependent)", "pykrx (KRX server dependent)"]
  LOCAL_BLOCKED: []
sources:
  - "Round 2 S03 Finding 2 — Silent Failure is #1 risk"
  - "Round 3 T04 — 4-Gate Targeted Strict verification (~780 lines)"
  - "Round 3 T05 — File-based state management (pipeline_state.json)"
  - "Round 3 S03 Finding 4 — Verification is trust prerequisite"
  - "pybreaker v1.3.0 — Python circuit breaker library"
  - "DuckDB ACID documentation — MVCC + WAL + fsync"
  - "macOS launchd documentation — StartCalendarInterval sleep behavior"
  - "pykrx GitHub issues — silent failure modes documented"
  - "Anthropic status page — 99.32% 30-day uptime (2025-2026)"
---

# Branch 5: Reliability & Fallback Strategies — Deep Research Report

> **System**: KOSPI/KOSDAQ Stock Technical Completeness Analysis & Selection System
> **Architecture**: launchd -> Python Pipeline (collect -> analyze -> score -> report) -> Claude Code interpretation
> **Critical Constraint**: Silent failure is the #1 risk (Round 2 Finding)
> **User Profile**: Non-technical, Korean-speaking
> **Date**: 2026-05-26

---

## 1. External Integration Failure Mode Catalog

### 1.1 pykrx Failures

| ID | Failure Mode | Detection Method | Frequency Est. | Blast Radius | Silent? |
|----|-------------|-----------------|----------------|--------------|---------|
| PK-1 | **KRX server down** (maintenance, outage) | `ConnectionError` / `TimeoutError` from requests | ~2-5 days/year (KRX scheduled maintenance + rare outages) | Total: no data collected | NO — exception raised |
| PK-2 | **Rate limited / IP blocked** | HTTP 403/429 or empty response after N rapid requests | Rare if using `get_market_ohlcv_by_ticker(date)` batch API (1 call) | Total: all tickers fail | PARTIALLY — may return empty DataFrame silently |
| PK-3 | **Returns all-zero prices** (FM-1) | Gate 1: `zero_close_ratio > 5%` | Documented in pykrx issues; estimated ~1-2/month | **CATASTROPHIC**: garbage scores for ALL stocks | **YES — SILENT** |
| PK-4 | **Partial data** (FM-2: 1,800/2,500) | Gate 1: `row_count < MIN_EXPECTED_STOCKS` | ~1-3/month (KRX data publication delay, KOSDAQ lag) | HIGH: 700 stocks missing, biased analysis | **YES — SILENT** |
| PK-5 | **Stale data** (FM-3: Mac was off) | Gate 1: `date_freshness > STALE_DATA_DAYS` | Depends on user behavior (laptop sleep/travel) | HIGH: yesterday's data labeled as today | **YES — SILENT** |
| PK-6 | **KRX website structure change** | `KeyError` / `IndexError` in pykrx parsing | ~1-2/year (KRX redesigns) — requires pykrx library update | Total: library broken until update | NO — exception |
| PK-7 | **KRX login expired/invalid** | Authentication error from KRX Data Marketplace | ~1/year (password expiry, TOS change) | Total: all queries fail | NO — exception |
| PK-8 | **Timeout (slow response)** | `requests.Timeout` after 30-60s | ~5-10/month (KRX peak hours, network issues) | Transient: retry succeeds | NO — exception |
| PK-9 | **Data format change** (new columns, type changes) | `TypeError` / `ValueError` in data processing | ~1/year with KRX updates | HIGH: parsing breaks | NO — exception |

**Key Insight**: PK-3, PK-4, PK-5 are the **lethal trio** — they are SILENT. The 4-Gate system (Gate 1) is the primary defense. Without it, these produce trash scores that look real.

### 1.2 DuckDB Failures

| ID | Failure Mode | Detection Method | Frequency Est. | Blast Radius | Silent? |
|----|-------------|-----------------|----------------|--------------|---------|
| DB-1 | **File corruption** (FM-6) | `duckdb.IOException` on connect, or data inconsistency | Very rare (<1/year) — DuckDB ACID with WAL + fsync | Total: all historical data at risk | NO — exception on access |
| DB-2 | **Disk full** | `OSError: No space left on device` during write; DuckDB GitHub #9667 confirms corruption risk | Rare on modern Macs with 256GB+; risk during initial 5-year load | **CRITICAL**: low disk space CAN corrupt the database file | NO — exception |
| DB-3 | **Concurrent write access** | `duckdb.IOException: Could not set lock` | Should never occur with `fcntl.flock()` PipelineLock; risk if user opens DB in DBeaver while pipeline runs | Blocked: second writer fails | NO — exception |
| DB-4 | **Schema mismatch** (after code update) | `duckdb.CatalogException: Column X not found` | ~1-2/year during updates | HIGH: pipeline stage fails | NO — exception |
| DB-5 | **WAL file left from crash** | DuckDB auto-recovers on next connect (re-applies WAL) | After any crash during write | None: auto-recovery | NO — transparent |
| DB-6 | **Large WAL accumulation** | WAL file grows unbounded during long writes (GitHub #9150) | During initial 5-year load | Performance degradation | NO — but slow |

**Key Insight**: DuckDB is remarkably reliable for this use case. Single-process + ACID + WAL = very low corruption risk. The main threat is **disk full during write** (DB-2). Pre-flight disk space check is cheap insurance.

### 1.3 Claude Code / Anthropic API Failures

| ID | Failure Mode | Detection Method | Frequency Est. | Blast Radius | Silent? |
|----|-------------|-----------------|----------------|--------------|---------|
| CC-1 | **API timeout** | HTTP timeout, no response within 60s | ~2-5/month (per Anthropic status history) | Interpretation delayed, not lost | NO |
| CC-2 | **Context window exceeded** | Token count error from API | Unlikely with summary-first (~10K tokens) | Interpretation fails | NO |
| CC-3 | **Model unavailable** (503 errors) | HTTP 503, "service unavailable" | Notable incident April 2026; overall 99.32% 30-day uptime | Interpretation delayed | NO |
| CC-4 | **Hook script failure** | Non-zero exit code from hook, stderr output | Depends on code quality | Specific hook skipped | NO — Claude Code logs it |
| CC-5 | **Compaction loses analysis context** | Context window compacted mid-interpretation | ~1-2/session for long analyses | Partial context loss | PARTIALLY — may repeat work |
| CC-6 | **claude -p headless mode failure** | Process exit code != 0 | Unknown (experimental feature) | Phase 2 automation fails | NO — exit code |

**Key Insight**: Claude Code failures are non-silent and non-destructive. Engine 2 interprets data that Engine 1 already validated and stored. If interpretation fails, the pipeline data is safe — just re-interpret.

### 1.4 Network Failures

| ID | Failure Mode | Detection Method | Frequency Est. | Blast Radius |
|----|-------------|-----------------|----------------|--------------|
| NW-1 | **DNS resolution failure** | `socket.gaierror` | Rare on stable home/office Wi-Fi | Total: pykrx and API both fail |
| NW-2 | **Connection timeout** | `requests.ConnectionError` | ~5-10/month | Transient: retry usually succeeds |
| NW-3 | **Partial response** (TCP reset mid-transfer) | Truncated data, JSON parse error | Rare (<1/month) | pykrx may return partial ticker list |
| NW-4 | **VPN/proxy interference** | Connection rejected, SSL errors | User-specific | Total: all network calls fail |

### 1.5 macOS System Failures

| ID | Failure Mode | Detection Method | Frequency Est. | Blast Radius |
|----|-------------|-----------------|----------------|--------------|
| OS-1 | **Mac sleeping during scheduled run** | launchd `StartCalendarInterval` coalesces missed runs on wake | Common (daily laptop sleep) | Pipeline runs on wake instead of scheduled time |
| OS-2 | **Mac powered off at scheduled time** | Job does NOT run until next scheduled interval | Travel, weekends | Pipeline misses 1+ days |
| OS-3 | **Disk space exhausted** | `OSError`, `IOError` | Rare | DuckDB corruption risk (DB-2) |
| OS-4 | **Memory pressure** (large initial load) | `MemoryError`, system slowdown | Only during 5-year load with many tickers | Process killed by OS |
| OS-5 | **launchd schedule drift** (sleep/wake coalescing) | Multiple missed intervals → single run on wake | Regular | Some daily runs skipped |

**Critical launchd Behavior**:
- `StartCalendarInterval`: If Mac is **asleep** when the job should run, it runs **on wake**. If Mac is **off**, it does **NOT** run until the next scheduled time.
- `StartInterval`: Multiple missed intervals are **coalesced into one** event on wake.
- **Implication for this system**: A user who closes their laptop Friday evening and opens it Monday morning will get ONE run on Monday, missing Friday's scheduled run. This is acceptable for daily analysis (Monday catches up), but the system must detect and report the gap.

---

## 2. Branch 5.1: Fail-Fast Strategy

### 2.1 Philosophy

> "Stop the pipeline at the first sign of trouble. Preserve state so you can resume. Tell the user exactly what happened in language they understand."

**When to use**: When data integrity is paramount and partial results are worse than no results. This is the DEFAULT for a financial analysis tool.

### 2.2 Standardized Exit Code Scheme

```python
# exit_codes.py — Standardized pipeline exit codes [LOCAL-OK]

from enum import IntEnum


class ExitCode(IntEnum):
    """Pipeline exit codes — BSD sysexits convention extended for stock pipeline."""
    
    # === Success ===
    SUCCESS = 0                  # Pipeline completed successfully
    
    # === Data failures (10-19) ===
    COLLECTION_FAILED = 10       # pykrx data collection failed
    COLLECTION_GARBAGE = 11      # Gate 1: all-zero prices or critical data quality
    COLLECTION_PARTIAL = 12      # Gate 1: partial data (< MIN_EXPECTED_STOCKS)
    COLLECTION_STALE = 13        # Gate 1: data older than STALE_DATA_DAYS
    
    # === Computation failures (20-29) ===
    ANALYSIS_FAILED = 20         # Indicator computation crashed
    ANALYSIS_NAN_FLOOD = 21      # Gate 2: core indicator NaN > threshold
    SCORING_FAILED = 22          # Scoring computation crashed
    SCORING_ANOMALY = 23         # Gate 3: distribution anomaly detected
    
    # === Output failures (30-39) ===
    REPORT_FAILED = 30           # Report generation crashed
    REPORT_EMPTY = 31            # Gate 4: report file empty/missing
    
    # === Infrastructure failures (40-49) ===
    DB_CONNECT_FAILED = 40       # DuckDB cannot open
    DB_CORRUPTION = 41           # DuckDB integrity check failed
    DISK_FULL = 42               # Insufficient disk space
    LOCK_HELD = 43               # Another pipeline instance is running
    
    # === External service failures (50-59) ===
    KRX_UNAVAILABLE = 50         # KRX/pykrx server unreachable
    KRX_AUTH_FAILED = 51         # KRX login expired
    CLAUDE_API_TIMEOUT = 52      # Claude Code API timeout
    NETWORK_ERROR = 53           # General network failure
    
    # === Recovery actions (60-69) ===
    RETRY_EXHAUSTED = 60         # All retry attempts failed
    DEGRADED_COMPLETE = 61       # Pipeline completed with degraded data
    CHECKPOINT_RESUME = 62       # Resumed from checkpoint (informational)
    
    # === Internal errors (70-79) ===
    CONFIG_ERROR = 70            # scoring_config.yaml missing/invalid
    INTERNAL_ERROR = 79          # Unexpected error


# Korean user-friendly error messages
EXIT_MESSAGES_KO: dict[int, str] = {
    ExitCode.SUCCESS: "분석이 정상적으로 완료되었습니다.",
    ExitCode.COLLECTION_FAILED: "KRX 데이터를 가져오지 못했습니다. 인터넷 연결을 확인해주세요.",
    ExitCode.COLLECTION_GARBAGE: "KRX에서 비정상 데이터를 받았습니다 (가격이 모두 0원). 잠시 후 다시 시도합니다.",
    ExitCode.COLLECTION_PARTIAL: "일부 종목 데이터만 수집되었습니다. KRX 서버가 불안정한 것 같습니다.",
    ExitCode.COLLECTION_STALE: "최신 데이터를 가져올 수 없어 이전 데이터를 사용합니다.",
    ExitCode.ANALYSIS_FAILED: "기술 지표 계산 중 오류가 발생했습니다.",
    ExitCode.ANALYSIS_NAN_FLOOD: "기술 지표 계산 결과가 비정상입니다. 데이터 품질 문제일 수 있습니다.",
    ExitCode.SCORING_FAILED: "종목 점수 계산 중 오류가 발생했습니다.",
    ExitCode.SCORING_ANOMALY: "점수 분포가 비정상입니다. 점수 계산 로직에 문제가 있을 수 있습니다.",
    ExitCode.REPORT_FAILED: "분석 보고서 생성 중 오류가 발생했습니다.",
    ExitCode.REPORT_EMPTY: "분석 보고서가 비어있습니다.",
    ExitCode.DB_CONNECT_FAILED: "데이터베이스를 열 수 없습니다. 파일이 손상되었을 수 있습니다.",
    ExitCode.DB_CORRUPTION: "데이터베이스가 손상되었습니다. 백업에서 복구가 필요합니다.",
    ExitCode.DISK_FULL: "디스크 공간이 부족합니다. 불필요한 파일을 삭제해주세요.",
    ExitCode.LOCK_HELD: "이미 분석이 실행 중입니다. 잠시 기다려주세요.",
    ExitCode.KRX_UNAVAILABLE: "한국거래소(KRX) 서버에 연결할 수 없습니다. 점검 시간일 수 있습니다.",
    ExitCode.KRX_AUTH_FAILED: "KRX 로그인이 만료되었습니다. KRX_ID/KRX_PW를 확인해주세요.",
    ExitCode.CLAUDE_API_TIMEOUT: "AI 분석 서버 응답이 없습니다. 잠시 후 다시 시도합니다.",
    ExitCode.NETWORK_ERROR: "인터넷 연결에 문제가 있습니다.",
    ExitCode.RETRY_EXHAUSTED: "여러 번 재시도했지만 실패했습니다. 나중에 다시 실행해주세요.",
    ExitCode.DEGRADED_COMPLETE: "일부 제한된 데이터로 분석을 완료했습니다. 결과에 주의가 필요합니다.",
    ExitCode.CONFIG_ERROR: "설정 파일에 문제가 있습니다.",
    ExitCode.INTERNAL_ERROR: "예상치 못한 오류가 발생했습니다.",
}
```

**Lines**: ~75. [LOCAL-OK]

### 2.3 State Preservation at Failure Point

Leverages the `pipeline_state.json` design from Round 3 T05 (File-Based State Management). On failure, the orchestrator:

1. Writes `pipeline_state.json` with `status: "failed"`, error details, and `last_successful_stage`
2. Writes the stage's `*_result.json` with partial output metadata
3. Writes the Gate's `ValidationResult` to `data/validation_report.json`
4. Sends macOS notification (see 2.4)
5. Exits with specific exit code

```python
# fail_fast.py — Fail-fast orchestration pattern [LOCAL-OK]

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

logger = logging.getLogger("pipeline.failfast")


def fail_fast(
    stage: str,
    exit_code: int,
    error_message: str,
    state_dir: str,
    validation_result: Optional[dict] = None,
    notify_user: bool = True,
) -> None:
    """
    Fail-fast handler: preserve state, notify user, exit.
    
    Called when a Gate check fails or a stage throws an unrecoverable error.
    
    Args:
        stage: Pipeline stage that failed ("collect", "analyze", "score", "report")
        exit_code: Standardized exit code from ExitCode enum
        error_message: Technical error message (for logs)
        state_dir: Path to state/ directory
        validation_result: Gate validation result dict (if available)
        notify_user: Whether to send macOS notification
    """
    from exit_codes import EXIT_MESSAGES_KO
    
    now = datetime.now().astimezone().isoformat()
    
    # 1. Update pipeline_state.json
    state_path = os.path.join(state_dir, "pipeline_state.json")
    state = _read_json(state_path) or {}
    state.update({
        "stage": stage,
        "status": "failed",
        "error": {
            "stage": stage,
            "exit_code": exit_code,
            "message": error_message,
            "timestamp": now,
        },
        "updated_at": now,
        "lock_pid": None,
        "lock_acquired_at": None,
    })
    _write_json_atomic(state_path, state)
    
    # 2. Save validation report (if Gate failure)
    if validation_result:
        report_path = os.path.join(state_dir, "..", "data", "validation_report.json")
        _write_json_atomic(report_path, {
            "timestamp": now,
            "failed_stage": stage,
            "exit_code": exit_code,
            "validation": validation_result,
        })
    
    # 3. Log the failure
    logger.error(
        f"FAIL-FAST: stage={stage} exit_code={exit_code} "
        f"error={error_message}"
    )
    
    # 4. Notify user
    if notify_user:
        user_message = EXIT_MESSAGES_KO.get(exit_code, error_message)
        _notify_macos(
            title="주식 분석 오류",
            message=user_message,
            subtitle=f"단계: {_stage_name_ko(stage)}",
        )
    
    # 5. Exit with code
    sys.exit(exit_code)


def _stage_name_ko(stage: str) -> str:
    """Translate stage name to Korean."""
    return {
        "collect": "데이터 수집",
        "analyze": "기술 지표 계산",
        "score": "종목 점수 산출",
        "report": "보고서 생성",
        "interpret": "AI 해석",
    }.get(stage, stage)


def _notify_macos(title: str, message: str, subtitle: str = "") -> None:
    """Send macOS native notification via osascript."""
    script = f'display notification "{message}" with title "{title}"'
    if subtitle:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
    try:
        subprocess.run(
            ["osascript", "-e", script],
            timeout=5,
            capture_output=True,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        logger.warning(f"macOS notification failed: {e}")
        # Fallback: terminal-notifier (if installed)
        try:
            cmd = ["terminal-notifier", "-title", title, "-message", message]
            if subtitle:
                cmd.extend(["-subtitle", subtitle])
            subprocess.run(cmd, timeout=5, capture_output=True)
        except (FileNotFoundError, OSError):
            pass  # No notification — log is the fallback


def _read_json(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json_atomic(path: str, data: dict) -> None:
    import tempfile
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            f.write("\n")
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
```

**Lines**: ~120. [LOCAL-OK]

### 2.4 User Notification Patterns

#### Strategy 1: macOS Native Notification (PRIMARY — Phase 1)

```python
# notification.py — macOS notification strategies [LOCAL-OK]

import subprocess
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger("pipeline.notify")


def notify_success(stock_count: int, top_stock: str, score: float) -> None:
    """Notify user of successful pipeline completion."""
    _notify_macos(
        title="주식 분석 완료",
        message=f"{stock_count}개 종목 분석 완료. 최고 점수: {top_stock} ({score:.0f}점)",
        sound="default",
    )


def notify_degraded(reason: str, data_age_days: int) -> None:
    """Notify user of degraded (but usable) results."""
    _notify_macos(
        title="주식 분석 완료 (제한적)",
        message=f"⚠️ {reason}. {data_age_days}일 전 데이터로 분석했습니다.",
        sound="default",
    )


def notify_failure(stage_ko: str, user_message: str) -> None:
    """Notify user of pipeline failure."""
    _notify_macos(
        title="주식 분석 오류",
        message=user_message,
        subtitle=f"단계: {stage_ko}",
        sound="Basso",  # Error sound
    )


def _notify_macos(
    title: str,
    message: str,
    subtitle: str = "",
    sound: str = "",
) -> bool:
    """
    Send macOS notification. Returns True if successful.
    
    Priority chain:
    1. osascript (built-in, no install)
    2. terminal-notifier (brew install, more features)
    3. Log file (always works)
    
    NOTE: On macOS Sequoia (15.x), osascript notifications may not work
    from Terminal.app. terminal-notifier is more reliable.
    """
    # Escape quotes for AppleScript
    message = message.replace('"', '\\"')
    title = title.replace('"', '\\"')
    subtitle = subtitle.replace('"', '\\"')
    
    # Strategy 1: osascript
    script_parts = [f'display notification "{message}" with title "{title}"']
    if subtitle:
        script_parts[0] = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
    if sound:
        script_parts[0] += f' sound name "{sound}"'
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script_parts[0]],
            timeout=5,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True
        logger.debug(f"osascript failed: {result.stderr}")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    
    # Strategy 2: terminal-notifier
    try:
        cmd = [
            "terminal-notifier",
            "-title", title,
            "-message", message,
            "-group", "stock-pipeline",
        ]
        if subtitle:
            cmd.extend(["-subtitle", subtitle])
        if sound:
            cmd.extend(["-sound", sound])
        
        result = subprocess.run(cmd, timeout=5, capture_output=True)
        if result.returncode == 0:
            return True
    except (FileNotFoundError, OSError):
        pass
    
    # Strategy 3: Log only (always works)
    logger.info(f"NOTIFICATION: [{title}] {subtitle} — {message}")
    return False
```

**Lines**: ~95. [LOCAL-OK]

**Notification Decision Matrix**:

| Event | Notification | Sound | Urgency |
|-------|-------------|-------|---------|
| Pipeline success | "분석 완료" + top stock | Default | Low |
| Degraded completion | "제한적 분석" + reason | Default | Medium |
| Gate failure (abort) | Error message in Korean | Basso (error) | High |
| Retry in progress | No notification (avoid spam) | None | None |
| 3 consecutive failures | "수동 확인 필요" | Basso | Critical |

### 2.5 Checkpoint-Based Recovery

The checkpoint/recovery design from Round 3 T05 already covers this. Key integration points for fail-fast:

```python
# recovery.py — Resume from last successful gate [LOCAL-OK]

def resume_from_failure(state_dir: str, project_dir: str) -> int:
    """
    Resume pipeline from the last failure point.
    
    Logic:
    1. Read pipeline_state.json
    2. If last_successful_stage exists, skip to next stage
    3. If no successful stage, start from beginning
    4. If retry count >= MAX_RETRIES, offer degraded mode or abort
    
    Returns exit code.
    """
    from resume_logic import resume_pipeline, Action
    
    decision = resume_pipeline(state_dir)
    
    if decision.action == Action.SKIP_COMPLETE:
        return ExitCode.SUCCESS
    
    if decision.action == Action.WAIT_RUNNING:
        return ExitCode.LOCK_HELD
    
    if decision.action == Action.RUN_FULL:
        return _run_pipeline_from(project_dir, "collect", attempt=1)
    
    if decision.action == Action.RESUME_STAGE:
        return _run_pipeline_from(
            project_dir,
            decision.stage,
            attempt=decision.attempt,
        )
    
    return ExitCode.INTERNAL_ERROR
```

**Key Recovery Scenarios**:

| Scenario | State After Failure | Recovery Action |
|----------|-------------------|-----------------|
| pykrx timeout during collect | `stage=collect, status=failed, attempt=1` | Retry collect (up to 3x) |
| Gate 1 fails (garbage data) | `stage=collect, status=failed, exit_code=11` | Wait 1 hour, retry collect |
| Gate 2 fails (NaN flood) | `stage=analyze, status=failed` | Re-collect then re-analyze |
| Gate 3 fails (score anomaly) | `stage=score, status=failed` | Investigate — may need config fix |
| Mac was off for 3 days | `stage=collect, run_id=3_days_ago` | Start fresh daily run |
| 5-year load interrupted at 60% | `initial_load_checkpoint.json: 3/5 years` | Resume from year 4 |
| DuckDB corrupted | `DB_CONNECT_FAILED` | Restore from `data/backups/` |

---

## 3. Branch 5.2: Graceful Degradation Strategy

### 3.1 Philosophy

> "It's better to tell the user 'here's what I could find, with caveats' than 'sorry, the whole thing failed.' But NEVER present degraded data as if it were complete."

**When to use**: When some result is better than no result, AND the degradation is clearly communicated.

### 3.2 Degradation Levels

```python
# degradation.py — Quality degradation levels and markers [LOCAL-OK]

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class DegradationLevel(IntEnum):
    """Pipeline quality levels — higher = worse degradation."""
    FULL = 0       # All data fresh, all gates passed
    LEVEL_1 = 1    # Yesterday's data (stale but valid)
    LEVEL_2 = 2    # Cached indicators (skip new calculation)
    LEVEL_3 = 3    # Previously scored stocks only (no new scores)
    LEVEL_4 = 4    # Data freshness warning only (no analysis)
    OFFLINE = 5    # Complete failure — no output


@dataclass
class QualityContext:
    """Tracks current quality state through the pipeline."""
    level: DegradationLevel = DegradationLevel.FULL
    reasons: list[str] = field(default_factory=list)
    data_date: Optional[str] = None          # Actual date of data used
    expected_date: Optional[str] = None      # Date data should be
    stale_days: int = 0
    missing_stocks: int = 0
    skipped_stages: list[str] = field(default_factory=list)
    degraded_indicators: list[str] = field(default_factory=list)
    
    def degrade(self, level: DegradationLevel, reason: str) -> None:
        """Downgrade quality level (can only go down, never up)."""
        if level > self.level:
            self.level = level
            self.reasons.append(reason)
    
    def get_quality_badge(self) -> str:
        """Korean quality badge for report header."""
        badges = {
            DegradationLevel.FULL: "✅ 전체 분석 완료",
            DegradationLevel.LEVEL_1: "⚠️ 어제 데이터로 분석",
            DegradationLevel.LEVEL_2: "⚠️ 캐시된 지표 사용 (새 계산 건너뜀)",
            DegradationLevel.LEVEL_3: "⚠️ 이전 점수만 표시 (신규 점수 없음)",
            DegradationLevel.LEVEL_4: "❌ 데이터 신선도 경고만 표시",
            DegradationLevel.OFFLINE: "❌ 분석 불가 — 데이터 없음",
        }
        badge = badges.get(self.level, "❓ 알 수 없는 상태")
        if self.stale_days > 0:
            badge += f" ({self.stale_days}일 전 데이터)"
        return badge
    
    def get_report_header(self) -> str:
        """Generate quality header for summary.md report."""
        if self.level == DegradationLevel.FULL:
            return f"## 데이터 품질: {self.get_quality_badge()}\n"
        
        lines = [
            f"## 데이터 품질: {self.get_quality_badge()}",
            "",
            "### 제한 사항",
        ]
        for reason in self.reasons:
            lines.append(f"- {reason}")
        
        if self.missing_stocks > 0:
            lines.append(f"- {self.missing_stocks}개 종목 데이터 누락")
        
        if self.skipped_stages:
            stage_names = {
                "analyze": "기술 지표 계산",
                "score": "종목 점수 산출",
            }
            skipped_ko = [stage_names.get(s, s) for s in self.skipped_stages]
            lines.append(f"- 건너뛴 단계: {', '.join(skipped_ko)}")
        
        lines.append("")
        lines.append("> 이 분석 결과는 제한된 데이터를 기반으로 합니다. "
                     "투자 결정 전에 최신 데이터로 재분석하시기 바랍니다.")
        lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        return {
            "level": self.level.name,
            "level_value": int(self.level),
            "reasons": self.reasons,
            "data_date": self.data_date,
            "expected_date": self.expected_date,
            "stale_days": self.stale_days,
            "missing_stocks": self.missing_stocks,
            "skipped_stages": self.skipped_stages,
            "badge": self.get_quality_badge(),
        }
```

**Lines**: ~100. [LOCAL-OK]

### 3.3 Fallback Chain Implementation

```python
# fallback_chain.py — Data source fallback: pykrx -> FDR -> cache [LOCAL-OK]

from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Optional

import duckdb

logger = logging.getLogger("pipeline.fallback")


class DataSourceResult:
    """Result from a data source attempt."""
    def __init__(
        self,
        success: bool,
        source: str,
        row_count: int = 0,
        data_date: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.source = source
        self.row_count = row_count
        self.data_date = data_date
        self.error = error


def collect_with_fallback(
    db_path: str,
    target_date: date,
    quality: "QualityContext",
) -> DataSourceResult:
    """
    3-tier data collection fallback chain.
    
    Tier 1: pykrx (primary, freshest data)
    Tier 2: FinanceDataReader (secondary, alternative source)
    Tier 3: DuckDB cache (yesterday's data, stale but valid)
    
    Each tier is tried in order. On success, return immediately.
    On failure, log and try next tier.
    """
    
    # === Tier 1: pykrx ===
    try:
        logger.info(f"[Tier 1/3] Attempting pykrx collection for {target_date}")
        result = _collect_pykrx(db_path, target_date)
        if result.success and result.row_count > 0:
            logger.info(f"[Tier 1/3] pykrx: {result.row_count} rows collected")
            return result
        else:
            logger.warning(f"[Tier 1/3] pykrx returned {result.row_count} rows")
    except Exception as e:
        logger.warning(f"[Tier 1/3] pykrx failed: {e}")
    
    # === Tier 2: FinanceDataReader ===
    try:
        logger.info(f"[Tier 2/3] Attempting FinanceDataReader for {target_date}")
        result = _collect_fdr(db_path, target_date)
        if result.success and result.row_count > 0:
            logger.info(f"[Tier 2/3] FDR: {result.row_count} rows collected")
            quality.degrade(
                DegradationLevel.LEVEL_1,
                "보조 데이터 소스(FinanceDataReader)에서 수집"
            )
            return result
        else:
            logger.warning(f"[Tier 2/3] FDR returned {result.row_count} rows")
    except Exception as e:
        logger.warning(f"[Tier 2/3] FinanceDataReader failed: {e}")
    
    # === Tier 3: DuckDB Cache ===
    logger.info("[Tier 3/3] Falling back to cached data")
    result = _get_cached_data(db_path, target_date)
    if result.success:
        stale_days = (target_date - date.fromisoformat(result.data_date)).days
        quality.degrade(
            DegradationLevel.LEVEL_1,
            f"KRX 데이터 수집 실패. {stale_days}일 전 캐시 데이터 사용"
        )
        quality.stale_days = stale_days
        logger.info(
            f"[Tier 3/3] Cache hit: {result.row_count} rows "
            f"from {result.data_date} ({stale_days} days old)"
        )
        return result
    
    # === All tiers failed ===
    logger.error("All 3 data source tiers failed")
    quality.degrade(DegradationLevel.OFFLINE, "모든 데이터 소스 실패")
    return DataSourceResult(
        success=False,
        source="none",
        error="All data sources failed: pykrx, FDR, cache",
    )


def _collect_pykrx(db_path: str, target_date: date) -> DataSourceResult:
    """Collect from pykrx. Raises on failure."""
    # Actual implementation would use:
    # from pykrx import stock
    # df = stock.get_market_ohlcv_by_ticker(target_date.strftime("%Y%m%d"))
    # then UPSERT into DuckDB
    raise NotImplementedError("Actual pykrx collection — to be implemented")


def _collect_fdr(db_path: str, target_date: date) -> DataSourceResult:
    """Collect from FinanceDataReader. Raises on failure."""
    # Actual implementation would use:
    # import FinanceDataReader as fdr
    # df = fdr.DataReader(ticker, start, end)
    # NOTE: FDR requires per-ticker calls, much slower than pykrx batch
    raise NotImplementedError("Actual FDR collection — to be implemented")


def _get_cached_data(db_path: str, target_date: date) -> DataSourceResult:
    """Get most recent data from DuckDB cache."""
    try:
        con = duckdb.connect(db_path, read_only=True)
        try:
            row = con.execute(
                "SELECT MAX(date), COUNT(*) FROM ohlcv"
            ).fetchone()
            
            if row and row[0] is not None:
                latest_date = str(row[0])
                row_count = row[1]
                return DataSourceResult(
                    success=True,
                    source="duckdb_cache",
                    row_count=row_count,
                    data_date=latest_date,
                )
        finally:
            con.close()
    except Exception as e:
        logger.error(f"Cache read failed: {e}")
    
    return DataSourceResult(
        success=False,
        source="duckdb_cache",
        error="No cached data available",
    )
```

**Lines**: ~130. [LOCAL-OK]

### 3.4 Degraded Pipeline Orchestration

```python
# pipeline_degraded.py — Graceful degradation orchestrator [LOCAL-OK]

def run_pipeline_graceful(project_dir: str) -> tuple[int, QualityContext]:
    """
    Run pipeline with graceful degradation.
    
    Flow:
    1. collect (with 3-tier fallback)
    2. Gate 1 → if CRITICAL but data exists, degrade to Level 1-2
    3. analyze → if fails, skip and degrade to Level 2
    4. Gate 2 (selective) → warnings only
    5. score → if fails, use previous scores (Level 3)
    6. Gate 3 → if CRITICAL, still output with heavy warnings
    7. report → always attempt
    8. Inject quality header into report
    
    Returns:
        (exit_code, quality_context)
    """
    quality = QualityContext()
    quality.expected_date = date.today().isoformat()
    
    db_path = os.path.join(project_dir, "data", "stock_analysis.duckdb")
    report_path = os.path.join(project_dir, "output", date.today().isoformat(), "summary.md")
    
    # --- Stage 1: Collect (with fallback) ---
    collect_result = collect_with_fallback(db_path, date.today(), quality)
    
    if not collect_result.success:
        # Total failure — nothing to work with
        notify_failure("데이터 수집", "데이터를 가져올 수 없습니다.")
        return (ExitCode.COLLECTION_FAILED, quality)
    
    quality.data_date = collect_result.data_date
    
    # --- Gate 1 (always run, but may not abort) ---
    g1 = validate_collection(db_path)
    if not g1.passed:
        if collect_result.source == "duckdb_cache":
            # Using cache — relax freshness check
            logger.warning("Gate 1 failed but using cached data — continuing degraded")
            quality.degrade(DegradationLevel.LEVEL_1, "데이터 검증 경고 있음")
        else:
            # Fresh data failed validation — this is serious
            if g1.stats.get("zero_close_ratio", 0) > 0.50:
                # More than half the data is zeros — abort
                notify_failure("데이터 수집", "수집된 데이터가 비정상입니다.")
                return (ExitCode.COLLECTION_GARBAGE, quality)
            # Partial issues — continue with warnings
            quality.degrade(DegradationLevel.LEVEL_1, "데이터 품질 경고 있음")
    
    # --- Stage 2: Analyze ---
    try:
        # analyze_data(db_path)
        pass
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        quality.degrade(DegradationLevel.LEVEL_2, f"기술 지표 계산 실패: {e}")
        quality.skipped_stages.append("analyze")
        # Check if previous indicators exist in DB
        # If yes, continue with stale indicators
        # If no, skip to Level 3
    
    # --- Stage 3: Score ---
    if "analyze" not in quality.skipped_stages:
        try:
            # score_data(db_path)
            pass
        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            quality.degrade(DegradationLevel.LEVEL_3, f"종목 점수 계산 실패: {e}")
            quality.skipped_stages.append("score")
    else:
        quality.degrade(DegradationLevel.LEVEL_3, "지표 누락으로 점수 계산 불가")
        quality.skipped_stages.append("score")
    
    # --- Gate 3 (if scores exist) ---
    if "score" not in quality.skipped_stages:
        g3 = validate_scores(db_path)
        if not g3.passed:
            quality.degrade(DegradationLevel.LEVEL_2, "점수 분포 이상 감지")
            # Continue but mark heavily
    
    # --- Stage 4: Report (always attempt) ---
    try:
        # generate_report(db_path, report_path, quality_header=quality.get_report_header())
        pass
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        quality.degrade(DegradationLevel.LEVEL_4, f"보고서 생성 실패: {e}")
    
    # --- Notify based on quality ---
    if quality.level == DegradationLevel.FULL:
        notify_success(stock_count=2400, top_stock="005930", score=87.5)
        return (ExitCode.SUCCESS, quality)
    elif quality.level <= DegradationLevel.LEVEL_3:
        notify_degraded(quality.reasons[0], quality.stale_days)
        return (ExitCode.DEGRADED_COMPLETE, quality)
    else:
        notify_failure("분석", "분석을 완료할 수 없습니다.")
        return (ExitCode.RETRY_EXHAUSTED, quality)
```

### 3.5 Auto-Recovery: Quality Upgrade on Integration Recovery

```python
# auto_recovery.py — Detect when integration recovers [LOCAL-OK]

def check_and_upgrade_quality(
    db_path: str,
    quality: QualityContext,
    target_date: date,
) -> bool:
    """
    After degraded run, check if the primary source has recovered.
    Called at the start of the NEXT pipeline run.
    
    If yesterday was degraded but today's pykrx works, automatically
    re-run yesterday's analysis with fresh data.
    
    Returns True if upgrade was performed.
    """
    if quality.level == DegradationLevel.FULL:
        return False  # Nothing to upgrade
    
    # Try primary source
    try:
        result = _collect_pykrx(db_path, target_date)
        if result.success and result.row_count >= MIN_EXPECTED_STOCKS:
            logger.info(
                "Primary source recovered. Running full pipeline."
            )
            # Reset quality
            quality.level = DegradationLevel.FULL
            quality.reasons.clear()
            quality.stale_days = 0
            quality.skipped_stages.clear()
            return True
    except Exception:
        pass
    
    return False
```

---

## 4. Circuit Breaker Pattern — Detailed Design

### 4.1 Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Pipeline       │     │  Circuit Breaker  │     │  Data Source      │
│   Orchestrator   │────>│  (per source)     │────>│  (pykrx/FDR)     │
│                  │     │                   │     │                  │
│                  │<────│  state: CLOSED    │<────│  response/error  │
│                  │     │        OPEN       │     │                  │
│                  │     │        HALF_OPEN  │     │                  │
└─────────────────┘     └──────────────────┘     └──────────────────┘
                              │
                              ▼
                        ┌──────────────────┐
                        │  breaker_state/   │
                        │  pykrx.json       │ ← Persistent state
                        │  fdr.json         │    between runs
                        └──────────────────┘
```

### 4.2 State Transitions

```
CLOSED (normal operation)
  │
  ├── Success → stay CLOSED (reset failure count)
  │
  └── Failure → increment failure_count
        │
        └── failure_count >= FAIL_MAX (3) → OPEN
              │
              ▼
OPEN (all calls immediately fail, use fallback)
  │
  └── After RESET_TIMEOUT (next day's run / 24h) → HALF_OPEN
        │
        ▼
HALF_OPEN (try ONE request to test recovery)
  │
  ├── Success → CLOSED (reset everything)
  │
  └── Failure → OPEN (restart timeout)
```

### 4.3 Custom File-Based Circuit Breaker

```python
# circuit_breaker.py — File-persistent circuit breaker for stock pipeline [LOCAL-OK]

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger("pipeline.breaker")

T = TypeVar("T")


class BreakerState(str, Enum):
    CLOSED = "closed"         # Normal operation
    OPEN = "open"             # All calls fail immediately
    HALF_OPEN = "half_open"   # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit is OPEN and call is rejected."""
    def __init__(self, source: str, opened_at: str, next_attempt: str):
        self.source = source
        self.opened_at = opened_at
        self.next_attempt = next_attempt
        super().__init__(
            f"Circuit breaker OPEN for '{source}' since {opened_at}. "
            f"Next attempt: {next_attempt}"
        )


class FileCircuitBreaker:
    """
    Circuit breaker with file-based state persistence.
    
    Designed for the stock pipeline where:
    - Runs are daily (not per-second like microservices)
    - State must persist between runs (launchd -> python3 -> exit)
    - Recovery check = "try again next day"
    
    Design decisions:
    - File-based storage (not Redis/pybreaker) — no external dependency
    - Atomic JSON writes (temp -> rename) for crash safety
    - FAIL_MAX=3 for daily pipeline: 3 consecutive daily failures
    - RESET_TIMEOUT=24h: try again next scheduled run
    - State file per data source: breaker_state/pykrx.json, breaker_state/fdr.json
    
    Usage:
        breaker = FileCircuitBreaker("pykrx", state_dir="state/breaker_state")
        try:
            result = breaker.call(lambda: pykrx_collect(date))
        except CircuitBreakerError:
            # Use fallback (FDR or cache)
            result = fallback_collect(date)
    """
    
    def __init__(
        self,
        name: str,
        state_dir: str = "state/breaker_state",
        fail_max: int = 3,
        reset_timeout_hours: float = 24.0,
        success_threshold: int = 1,
    ):
        self.name = name
        self.state_dir = state_dir
        self.state_file = os.path.join(state_dir, f"{name}.json")
        self.fail_max = fail_max
        self.reset_timeout = timedelta(hours=reset_timeout_hours)
        self.success_threshold = success_threshold
        
        os.makedirs(state_dir, exist_ok=True)
        self._state = self._load_state()
    
    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute func through the circuit breaker.
        
        - CLOSED: execute normally
        - OPEN: raise CircuitBreakerError immediately (fast fail)
        - HALF_OPEN: execute once to test recovery
        
        Raises:
            CircuitBreakerError: if circuit is OPEN
            Exception: if func raises and circuit trips
        """
        state = self._state
        current_state = BreakerState(state.get("state", "closed"))
        
        # === OPEN: check if timeout expired ===
        if current_state == BreakerState.OPEN:
            opened_at = state.get("opened_at", "")
            if opened_at:
                opened_time = datetime.fromisoformat(opened_at)
                elapsed = datetime.now().astimezone() - opened_time
                if elapsed >= self.reset_timeout:
                    # Transition to HALF_OPEN
                    logger.info(
                        f"[{self.name}] OPEN -> HALF_OPEN "
                        f"(timeout expired after {elapsed})"
                    )
                    self._update_state(BreakerState.HALF_OPEN)
                    current_state = BreakerState.HALF_OPEN
                else:
                    remaining = self.reset_timeout - elapsed
                    next_attempt = (
                        datetime.now().astimezone() + remaining
                    ).isoformat()
                    raise CircuitBreakerError(
                        self.name, opened_at, next_attempt
                    )
        
        # === CLOSED or HALF_OPEN: execute func ===
        try:
            result = func(*args, **kwargs)
            self._on_success(current_state)
            return result
        except Exception as e:
            self._on_failure(current_state, str(e))
            raise
    
    def _on_success(self, current_state: BreakerState) -> None:
        """Handle successful call."""
        if current_state == BreakerState.HALF_OPEN:
            # Recovery confirmed — close circuit
            logger.info(f"[{self.name}] HALF_OPEN -> CLOSED (recovery confirmed)")
            self._update_state(BreakerState.CLOSED, reset_counters=True)
        else:
            # Reset failure count on success
            self._state["consecutive_failures"] = 0
            self._save_state()
    
    def _on_failure(self, current_state: BreakerState, error: str) -> None:
        """Handle failed call."""
        failures = self._state.get("consecutive_failures", 0) + 1
        self._state["consecutive_failures"] = failures
        self._state["last_failure"] = {
            "error": error,
            "timestamp": datetime.now().astimezone().isoformat(),
        }
        
        if current_state == BreakerState.HALF_OPEN:
            # Recovery attempt failed — reopen
            logger.warning(
                f"[{self.name}] HALF_OPEN -> OPEN "
                f"(recovery attempt failed: {error})"
            )
            self._update_state(BreakerState.OPEN)
        elif failures >= self.fail_max:
            # Threshold reached — open circuit
            logger.error(
                f"[{self.name}] CLOSED -> OPEN "
                f"({failures} consecutive failures >= {self.fail_max})"
            )
            self._update_state(BreakerState.OPEN)
        else:
            logger.warning(
                f"[{self.name}] failure {failures}/{self.fail_max}: {error}"
            )
            self._save_state()
    
    def _update_state(
        self,
        new_state: BreakerState,
        reset_counters: bool = False,
    ) -> None:
        """Transition to new state and persist."""
        now = datetime.now().astimezone().isoformat()
        self._state["state"] = new_state.value
        self._state["state_changed_at"] = now
        
        if new_state == BreakerState.OPEN:
            self._state["opened_at"] = now
        
        if reset_counters:
            self._state["consecutive_failures"] = 0
            self._state.pop("opened_at", None)
        
        # Append to history (keep last 30 entries)
        history = self._state.get("history", [])
        history.append({
            "state": new_state.value,
            "timestamp": now,
            "failures": self._state.get("consecutive_failures", 0),
        })
        self._state["history"] = history[-30:]
        
        self._save_state()
    
    def _load_state(self) -> dict:
        """Load breaker state from file."""
        if not os.path.exists(self.state_file):
            return {
                "name": self.name,
                "state": BreakerState.CLOSED.value,
                "consecutive_failures": 0,
                "state_changed_at": datetime.now().astimezone().isoformat(),
                "history": [],
            }
        try:
            with open(self.state_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.warning(f"Corrupt breaker state for {self.name} — resetting")
            return {
                "name": self.name,
                "state": BreakerState.CLOSED.value,
                "consecutive_failures": 0,
                "state_changed_at": datetime.now().astimezone().isoformat(),
                "history": [],
            }
    
    def _save_state(self) -> None:
        """Persist state atomically."""
        import tempfile
        fd, tmp = tempfile.mkstemp(
            dir=self.state_dir, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
                f.write("\n")
            os.rename(tmp, self.state_file)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    
    # --- Inspection API ---
    
    @property
    def current_state(self) -> BreakerState:
        return BreakerState(self._state.get("state", "closed"))
    
    @property
    def failure_count(self) -> int:
        return self._state.get("consecutive_failures", 0)
    
    def get_status_ko(self) -> str:
        """Korean status message for user display."""
        state = self.current_state
        if state == BreakerState.CLOSED:
            return f"{self.name}: 정상"
        elif state == BreakerState.OPEN:
            failures = self.failure_count
            return (
                f"{self.name}: 비활성 (연속 {failures}회 실패). "
                f"다음 시도: 내일 자동 실행"
            )
        else:
            return f"{self.name}: 복구 시도 중"
    
    def force_close(self) -> None:
        """Manual override: force circuit to CLOSED state."""
        logger.info(f"[{self.name}] FORCED CLOSE by user")
        self._update_state(BreakerState.CLOSED, reset_counters=True)


# === Pre-configured breakers for each data source ===

def create_pykrx_breaker(state_dir: str) -> FileCircuitBreaker:
    """
    pykrx circuit breaker.
    
    Config rationale:
    - fail_max=3: If pykrx fails 3 consecutive daily runs, it's likely
      a systemic issue (KRX maintenance, pykrx library broken).
    - reset_timeout=24h: Try again on the next daily run.
    - This means: Mon fail, Tue fail, Wed fail -> OPEN.
      Thu: HALF_OPEN (try once). If success -> CLOSED.
    """
    return FileCircuitBreaker(
        name="pykrx",
        state_dir=state_dir,
        fail_max=3,
        reset_timeout_hours=24.0,
    )


def create_fdr_breaker(state_dir: str) -> FileCircuitBreaker:
    """
    FinanceDataReader circuit breaker.
    
    Config: Same as pykrx but independent state.
    Both breakers can be OPEN simultaneously — then cache is used.
    """
    return FileCircuitBreaker(
        name="fdr",
        state_dir=state_dir,
        fail_max=3,
        reset_timeout_hours=24.0,
    )
```

**Lines**: ~230. [LOCAL-OK]

**Why custom instead of pybreaker**: 
1. pybreaker is designed for per-request circuit breaking in web services (in-memory state, sub-second resets). This pipeline runs once daily — state MUST persist between runs.
2. pybreaker's `CircuitRedisStorage` requires Redis. The custom `FileCircuitBreaker` uses JSON files — no external dependency.
3. pybreaker adds a pip dependency for ~50 lines of actual logic.
4. Custom implementation is transparent and debuggable (`cat state/breaker_state/pykrx.json`).

### 4.4 Circuit Breaker Integration with Fallback Chain

```python
# collect_orchestrator.py — Integrates breakers with fallback [LOCAL-OK]

def collect_data(
    db_path: str,
    target_date: date,
    state_dir: str,
    quality: QualityContext,
) -> DataSourceResult:
    """
    Collection with circuit breakers + fallback chain.
    
    Decision tree:
    1. Is pykrx breaker CLOSED/HALF_OPEN?
       → YES: try pykrx
       → NO: skip pykrx (fast!)
    2. pykrx failed?
       → Try FDR (if its breaker allows)
    3. FDR failed?
       → Use DuckDB cache
    """
    pykrx_breaker = create_pykrx_breaker(os.path.join(state_dir, "breaker_state"))
    fdr_breaker = create_fdr_breaker(os.path.join(state_dir, "breaker_state"))
    
    # Tier 1: pykrx
    if pykrx_breaker.current_state != BreakerState.OPEN:
        try:
            result = pykrx_breaker.call(_collect_pykrx, db_path, target_date)
            if result.success and result.row_count > 0:
                return result
        except CircuitBreakerError as e:
            logger.info(f"pykrx breaker OPEN: {e}")
        except Exception as e:
            logger.warning(f"pykrx failed (breaker recorded): {e}")
    else:
        logger.info(f"pykrx breaker OPEN — skipping. {pykrx_breaker.get_status_ko()}")
    
    # Tier 2: FDR
    if fdr_breaker.current_state != BreakerState.OPEN:
        try:
            result = fdr_breaker.call(_collect_fdr, db_path, target_date)
            if result.success and result.row_count > 0:
                quality.degrade(DegradationLevel.LEVEL_1, "보조 데이터 소스 사용")
                return result
        except CircuitBreakerError:
            logger.info("FDR breaker OPEN — skipping")
        except Exception as e:
            logger.warning(f"FDR failed: {e}")
    
    # Tier 3: Cache
    result = _get_cached_data(db_path, target_date)
    if result.success:
        quality.degrade(DegradationLevel.LEVEL_1, "캐시 데이터 사용")
        return result
    
    quality.degrade(DegradationLevel.OFFLINE, "모든 데이터 소스 실패")
    return DataSourceResult(success=False, source="none", error="All sources failed")
```

---

## 5. Monitoring & Observability for Non-Technical Users

### 5.1 Dual-Format Logging

```python
# logging_config.py — Pipeline logging setup [LOCAL-OK]

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime


def setup_pipeline_logging(log_dir: str, run_id: str) -> None:
    """
    Configure dual-format logging:
    1. Human-readable log file (for user / manual debugging)
    2. JSON structured log (for programmatic analysis / health dashboard)
    
    Both files written simultaneously.
    """
    os.makedirs(log_dir, exist_ok=True)
    
    root = logging.getLogger("pipeline")
    root.setLevel(logging.DEBUG)
    
    # --- Human-readable file handler ---
    human_path = os.path.join(log_dir, f"pipeline_{run_id}.log")
    human_handler = logging.FileHandler(human_path, encoding="utf-8")
    human_handler.setLevel(logging.INFO)
    human_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(human_handler)
    
    # --- JSON structured file handler ---
    json_path = os.path.join(log_dir, f"pipeline_{run_id}.jsonl")
    json_handler = logging.FileHandler(json_path, encoding="utf-8")
    json_handler.setLevel(logging.DEBUG)
    json_handler.setFormatter(JsonFormatter())
    root.addHandler(json_handler)
    
    # --- Console handler (minimal, for launchd stdout capture) ---
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s"
    ))
    root.addHandler(console)


class JsonFormatter(logging.Formatter):
    """Format log records as JSON lines."""
    
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            entry["error"] = str(record.exc_info[1])
            entry["traceback"] = self.formatException(record.exc_info)
        
        # Include extra fields (if passed via logger.info("msg", extra={...}))
        for key in ("stage", "gate", "breaker", "source", "row_count",
                     "quality_level", "duration_ms"):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        
        return json.dumps(entry, ensure_ascii=False, default=str)
```

### 5.2 Health Dashboard (Run History Summary)

```python
# health_dashboard.py — Pipeline health for non-technical users [LOCAL-OK]

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Optional


def generate_health_summary(
    state_dir: str,
    log_dir: str,
    breaker_dir: str,
    last_n_days: int = 7,
) -> str:
    """
    Generate Korean-language health summary for the user.
    
    Output format: plain text suitable for terminal display or
    injection into Claude Code context.
    
    Sections:
    1. Current status (running? last result?)
    2. Last N days: success/failure history
    3. Data source health (circuit breaker states)
    4. Anomaly alerts (score drift, stale data)
    """
    lines: list[str] = []
    lines.append("=" * 50)
    lines.append("  주식 분석 파이프라인 상태 요약")
    lines.append("=" * 50)
    lines.append("")
    
    # --- Section 1: Current Status ---
    state_path = os.path.join(state_dir, "pipeline_state.json")
    if os.path.exists(state_path):
        with open(state_path, "r") as f:
            state = json.load(f)
        
        status = state.get("status", "?")
        stage = state.get("stage", "?")
        run_id = state.get("run_id", "?")
        updated = state.get("updated_at", "?")
        
        status_ko = {
            "running": "실행 중",
            "success": "정상 완료",
            "failed": "오류 발생",
            "degraded": "제한적 완료",
        }.get(status, status)
        
        lines.append(f"현재 상태: {status_ko}")
        lines.append(f"마지막 실행: {run_id} ({updated})")
        
        if status == "failed":
            error = state.get("error", {})
            lines.append(f"오류: {error.get('message', '알 수 없음')}")
            attempt = state.get("attempt", 1)
            lines.append(f"재시도 횟수: {attempt}/3")
    else:
        lines.append("현재 상태: 아직 실행된 적 없음")
    
    lines.append("")
    
    # --- Section 2: Run History ---
    lines.append("--- 최근 7일 실행 기록 ---")
    validation_path = os.path.join(
        os.path.dirname(state_dir), "data", "validation_history.json"
    )
    if os.path.exists(validation_path):
        with open(validation_path, "r") as f:
            history = json.load(f)
        
        recent = history[-last_n_days:]
        success_count = sum(1 for h in recent if h.get("passed", False))
        total = len(recent)
        
        lines.append(f"성공: {success_count}/{total}일")
        for h in reversed(recent):
            d = h.get("date", "?")
            passed = "O" if h.get("passed") else "X"
            warnings = h.get("total_warnings", 0)
            extra = f" (경고 {warnings}건)" if warnings > 0 else ""
            lines.append(f"  {d}: [{passed}]{extra}")
    else:
        lines.append("  실행 기록 없음")
    
    lines.append("")
    
    # --- Section 3: Data Source Health ---
    lines.append("--- 데이터 소스 상태 ---")
    for source_name in ["pykrx", "fdr"]:
        breaker_path = os.path.join(breaker_dir, f"{source_name}.json")
        if os.path.exists(breaker_path):
            with open(breaker_path, "r") as f:
                breaker = json.load(f)
            state_str = breaker.get("state", "closed")
            failures = breaker.get("consecutive_failures", 0)
            
            if state_str == "closed":
                lines.append(f"  {source_name}: 정상")
            elif state_str == "open":
                lines.append(f"  {source_name}: 비활성 (연속 {failures}회 실패)")
            else:
                lines.append(f"  {source_name}: 복구 시도 중")
        else:
            lines.append(f"  {source_name}: 상태 정보 없음")
    
    lines.append("")
    
    # --- Section 4: Anomaly Alerts ---
    lines.append("--- 이상 징후 ---")
    anomalies = _detect_anomalies(state_dir)
    if anomalies:
        for a in anomalies:
            lines.append(f"  ⚠️ {a}")
    else:
        lines.append("  이상 징후 없음")
    
    lines.append("")
    lines.append("=" * 50)
    
    return "\n".join(lines)


def _detect_anomalies(state_dir: str) -> list[str]:
    """Detect anomalies from recent pipeline runs."""
    anomalies = []
    
    validation_path = os.path.join(
        os.path.dirname(state_dir), "data", "validation_history.json"
    )
    if not os.path.exists(validation_path):
        return anomalies
    
    with open(validation_path, "r") as f:
        history = json.load(f)
    
    if len(history) < 2:
        return anomalies
    
    # Check for consecutive failures
    recent_3 = history[-3:]
    if all(not h.get("passed", True) for h in recent_3):
        anomalies.append("최근 3일 연속 실패 — 시스템 점검 필요")
    
    # Check for score drift (from validation stats if available)
    # This would read from the gate 3 stats in validation reports
    
    return anomalies
```

### 5.3 Error Message Translation (Technical -> Korean Non-Technical)

| Technical Error | Korean User Message | Action Hint |
|----------------|--------------------:|-------------|
| `ConnectionError: pykrx` | "KRX 데이터를 가져올 수 없습니다" | "인터넷 연결을 확인해주세요" |
| `Gate 1: zero_close_ratio > 5%` | "수집된 데이터가 비정상입니다" | "자동으로 재시도합니다" |
| `Gate 1: row_count < 2000` | "일부 종목만 수집되었습니다" | "KRX 서버 상태를 확인 중입니다" |
| `Gate 3: mean outside [30,70]` | "점수 분포가 비정상입니다" | "점수 계산에 문제가 있을 수 있습니다" |
| `duckdb.IOException` | "데이터베이스를 열 수 없습니다" | "백업에서 복구가 필요합니다" |
| `OSError: No space left` | "디스크 공간이 부족합니다" | "불필요한 파일을 삭제해주세요" |
| `BlockingIOError (lock)` | "이미 분석이 실행 중입니다" | "잠시 기다려주세요" |
| `RetryExhausted (3 attempts)` | "여러 번 시도했지만 실패했습니다" | "나중에 다시 실행해주세요" |
| `CircuitBreakerError` | "데이터 소스가 일시적으로 비활성입니다" | "내일 자동으로 재시도합니다" |
| `score drift > 15 points` | "점수가 평소보다 크게 변동했습니다" | "시장 변동 또는 시스템 이상일 수 있습니다" |

---

## 6. Recovery Strategies

### 6.1 Recovery Decision Matrix

| Failure Type | Recovery Strategy | Automated? | User Action |
|-------------|-------------------|-----------|-------------|
| **Transient network** (PK-8, NW-2) | Retry with backoff (30s/60s/120s) | YES | None |
| **pykrx garbage data** (PK-3) | Re-collect after 1 hour | YES (next run) | Check notification |
| **pykrx partial data** (PK-4) | Use available data + quality marker | YES (degraded) | Review warning |
| **Stale data** (PK-5, OS-1) | Use cache + quality marker | YES (degraded) | Open laptop earlier |
| **pykrx library broken** (PK-6) | Circuit breaker -> FDR fallback | YES | Wait for pykrx update |
| **KRX auth expired** (PK-7) | Fail-fast + clear notification | NO | Re-enter KRX_ID/KRX_PW |
| **DuckDB corruption** (DB-1) | Restore from backup (data/backups/) | SEMI-AUTO | Run `/repair` command |
| **Disk full** (DB-2, OS-3) | Fail-fast + notification | NO | Free disk space |
| **Gate 3 score anomaly** (FM-5) | Log + continue with warning | YES (degraded) | Review scores |
| **5-year load interrupted** | Resume from checkpoint | YES | Re-run pipeline |
| **Pipeline crash mid-stage** | Resume from last successful stage | YES | Re-run pipeline |
| **3+ consecutive failures** | Escalate notification | YES | Manual investigation |

### 6.2 Checkpoint-Based Recovery

```
Pipeline Run:
  collect ──[checkpoint]──> analyze ──[checkpoint]──> score ──[checkpoint]──> report
     │                         │                        │                       │
     ▼                         ▼                        ▼                       ▼
  collect_result.json    analyze_result.json      score_result.json      report_result.json
     │
     └──> initial_load_checkpoint.json (for 5-year load)

On Restart:
  1. Read pipeline_state.json → find last_successful_stage
  2. Skip completed stages (data already in DuckDB via UPSERT)
  3. Resume from next stage
  4. DuckDB UPSERT = idempotent → safe to re-run any stage
```

### 6.3 DuckDB Integrity Check & Repair

```python
# db_health.py — DuckDB health check and repair [LOCAL-OK]

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path

import duckdb

logger = logging.getLogger("pipeline.db_health")


def check_database_health(db_path: str) -> dict:
    """
    Pre-flight database health check.
    
    Checks:
    1. File exists and is readable
    2. DuckDB can open it
    3. Expected tables exist
    4. Basic query succeeds
    5. Disk space sufficient (>500MB free)
    
    Returns dict with health status.
    """
    health = {"healthy": True, "checks": {}, "warnings": []}
    
    # 1. File exists
    if not os.path.exists(db_path):
        health["checks"]["file_exists"] = False
        health["healthy"] = False
        health["warnings"].append("데이터베이스 파일이 없습니다 (첫 실행?)")
        return health
    health["checks"]["file_exists"] = True
    
    # 2. File size
    file_size = os.path.getsize(db_path)
    health["checks"]["file_size_mb"] = round(file_size / 1_048_576, 2)
    
    # 3. Can open
    try:
        con = duckdb.connect(db_path, read_only=True)
    except Exception as e:
        health["checks"]["can_open"] = False
        health["healthy"] = False
        health["warnings"].append(f"데이터베이스를 열 수 없습니다: {e}")
        return health
    health["checks"]["can_open"] = True
    
    try:
        # 4. Expected tables
        tables = {
            row[0] for row in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        expected = {"ohlcv"}  # Minimum required
        missing = expected - tables
        health["checks"]["tables_present"] = list(tables)
        if missing:
            health["warnings"].append(f"테이블 누락: {missing}")
        
        # 5. Basic query
        try:
            row_count = con.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0]
            health["checks"]["ohlcv_rows"] = row_count
        except Exception:
            health["checks"]["ohlcv_rows"] = 0
    finally:
        con.close()
    
    # 6. Disk space
    stat = os.statvfs(os.path.dirname(db_path))
    free_mb = (stat.f_bavail * stat.f_frsize) / 1_048_576
    health["checks"]["disk_free_mb"] = round(free_mb, 0)
    if free_mb < 500:
        health["healthy"] = False
        health["warnings"].append(
            f"디스크 공간 부족: {free_mb:.0f}MB 남음 (최소 500MB 필요)"
        )
    
    return health


def repair_database(db_path: str, backup_dir: str) -> bool:
    """
    Repair corrupted DuckDB by restoring from latest backup.
    
    Strategy:
    1. Find latest backup in backup_dir
    2. Verify backup integrity (can open + has tables)
    3. Replace corrupted file with backup
    4. Log the repair action
    
    Returns True if repair succeeded.
    """
    # Find latest backup
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        logger.error("No backup directory found")
        return False
    
    backups = sorted(
        backup_path.glob("stocks_*.duckdb"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    
    if not backups:
        logger.error("No backup files found")
        return False
    
    latest_backup = backups[0]
    logger.info(f"Latest backup: {latest_backup.name}")
    
    # Verify backup
    try:
        con = duckdb.connect(str(latest_backup), read_only=True)
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables"
        ).fetchall()
        con.close()
        if not tables:
            logger.error("Backup is empty")
            return False
    except Exception as e:
        logger.error(f"Backup is also corrupted: {e}")
        return False
    
    # Replace corrupted file
    try:
        # Archive corrupted file
        corrupt_archive = db_path + f".corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(db_path):
            os.rename(db_path, corrupt_archive)
            logger.info(f"Corrupted file archived: {corrupt_archive}")
        
        # Also move WAL file if it exists
        wal_path = db_path + ".wal"
        if os.path.exists(wal_path):
            os.rename(wal_path, corrupt_archive + ".wal")
        
        # Copy backup
        shutil.copy2(str(latest_backup), db_path)
        logger.info(f"Database restored from {latest_backup.name}")
        return True
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        return False
```

**Lines**: ~130. [LOCAL-OK]

### 6.4 Initial Load Recovery (5-Year Load Interrupted)

Covered by Round 3 T05 `initial_load_checkpoint.json` design. Key addition for reliability:

```python
# initial_load_recovery.py — 5-year load with per-month checkpointing [LOCAL-OK]

def resume_initial_load(
    db_path: str,
    checkpoint_path: str,
    quality: QualityContext,
) -> bool:
    """
    Resume interrupted 5-year initial load.
    
    Granularity: per-month (not per-year from T05 design).
    Rationale: 5-year load takes ~60-90 min. Per-year checkpoint means
    losing up to ~18 min of work on crash. Per-month = max ~1.5 min lost.
    
    Each month is loaded via:
    1. pykrx.get_market_ohlcv_by_ticker(date) for each trading day
    2. DuckDB INSERT OR REPLACE (idempotent)
    3. Update checkpoint after each month completes
    
    Mac sleep handling:
    - On sleep: process pauses (SIGSTOP equivalent)
    - On wake: process resumes from exact point
    - Checkpoint is already saved for completed months
    - Worst case: current month re-fetches ~20 trading days
    """
    pass  # Implementation follows T05 pattern with month granularity
```

---

## 7. Integration-Specific Reliability Assessment

### 7.1 pykrx Reliability Profile

| Metric | Assessment | Source |
|--------|-----------|--------|
| **Underlying mechanism** | Web scraping (KRX website + Naver Finance) | pykrx GitHub README |
| **Single point of failure** | KRX website structure change → library breaks | GitHub issues |
| **Rate limiting** | KRX blocks rapid requests; 1-second delay recommended | pykrx docs |
| **Batch API** | `get_market_ohlcv_by_ticker(date)` — single call for all tickers | Round 2 T04 |
| **Data freshness** | Available ~15:35 KST (after market close 15:30) — needs empirical test | Parking lot |
| **Auth requirement** | KRX Data Marketplace login (free, social auth) since 2025.12 | pykrx v1.2.x |
| **Maintenance status** | Active (last commit 2025); responsive to issues | GitHub |
| **Historical reliability** | Periodic breakages when KRX changes site structure | GitHub issues #276, #240 |
| **Silent failure rate** | UNDOCUMENTED — estimated 1-3/month for partial data | Inferred from issues |

**Risk Rating**: MEDIUM-HIGH. pykrx is the system's most fragile dependency. Mitigation: 3-tier fallback + circuit breaker + Gate 1 validation.

### 7.2 DuckDB Reliability Profile

| Metric | Assessment | Source |
|--------|-----------|--------|
| **ACID compliance** | Full ACID with MVCC + WAL + fsync | DuckDB docs |
| **Corruption risk** | Very low. Known risk: disk full during write (GitHub #9667) | DuckDB GitHub |
| **Concurrent access** | Single writer process; multiple readers OK | DuckDB concurrency docs |
| **WAL recovery** | Automatic on next connect — re-applies uncommitted WAL entries | DuckDB docs |
| **File size** | Efficient columnar compression; 5 years OHLCV ~50-100MB estimated | Inference |
| **Schema migration** | No built-in migration tool; ALTER TABLE supported | DuckDB docs |
| **Backup strategy** | File copy (single-file DB); `EXPORT DATABASE` for SQL dump | DuckDB docs |

**Risk Rating**: LOW. DuckDB is the most reliable component. Pre-flight disk space check is the main safeguard.

### 7.3 launchd Reliability Profile

| Metric | Assessment | Source |
|--------|-----------|--------|
| **Missed schedule (sleep)** | `StartCalendarInterval`: runs on wake. `StartInterval`: coalesced. | Apple docs |
| **Missed schedule (off)** | Does NOT run until next scheduled interval | Apple docs |
| **Multiple missed intervals** | Coalesced into single run on wake | Apple developer forums |
| **RunAtLoad** | Runs immediately when plist is loaded (login/boot) | Apple docs |
| **Error handling** | Logs to system log; `StandardOutPath`/`StandardErrorPath` for capture | Apple docs |
| **Recommended config** | `StartCalendarInterval` with Hour=18, Minute=0 (6 PM KST) | System design |

**Recommended launchd plist**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" 
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stock-scanner.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/pipeline_runner.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>18</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/path/to/logs/launchd_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/path/to/logs/launchd_stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
```

**Risk Rating**: LOW. launchd is macOS-native and extremely reliable. The only risk is the user's laptop being off/sleeping — documented and handled.

### 7.4 Claude Code / Anthropic API Reliability

| Metric | Assessment | Source |
|--------|-----------|--------|
| **SLA** | 99.9% uptime commitment | Anthropic docs |
| **Actual uptime (30-day)** | ~99.32% (up to ~5h downtime/month) | Anthropic status page |
| **Notable incidents** | April 2026: API 503 errors across Claude 4 endpoints | News reports |
| **Impact on this system** | Engine 2 (interpretation) only — does NOT affect Engine 1 (data pipeline) | Architecture |
| **Fallback** | If interpretation fails, pipeline data is safe; user can re-interpret later | Design |

**Risk Rating**: LOW for this system. Claude Code failures only affect interpretation, not data integrity.

---

## 8. COMPARISON: Fail-Fast (5.1) vs Graceful Degradation (5.2)

### 8.1 Decision Matrix

| Criterion | 5.1 Fail-Fast | 5.2 Graceful Degradation | Winner |
|-----------|--------------|--------------------------|--------|
| **Prevents garbage scores** | YES — stops immediately | DEPENDS — quality markers must be visible | **5.1** (safer) |
| **User experience on bad day** | "분석 실패" notification, no output | "제한적 분석 완료" with caveats | **5.2** (more useful) |
| **Implementation complexity** | LOWER (~200 lines for fail-fast) | HIGHER (~400 lines for degradation levels + quality tracking) | **5.1** (simpler) |
| **Silent failure risk** | ZERO — any anomaly = abort | LOW but non-zero — degradation markers could be missed | **5.1** (safer) |
| **Daily usefulness** | Binary: full result or nothing | Gradient: some result most days | **5.2** (practical) |
| **Trust building** | High — "if it shows, it's correct" | Medium — user must read quality badge | **5.1** (trust) |
| **Non-technical user clarity** | Simple: "worked" or "didn't work" | Complex: understand degradation levels | **5.1** (clarity) |
| **Recovery automation** | Waits for next run / manual retry | Auto-upgrades when source recovers | **5.2** (automated) |
| **Financial risk** | ZERO — no bad data acted upon | LOW but non-zero — stale data could mislead | **5.1** (safer) |

### 8.2 RECOMMENDATION: Fail-Fast Default + Selective Degradation

**Neither pure fail-fast nor pure degradation is correct. The right answer is fail-fast as the DEFAULT with explicit, narrow degradation paths.**

```
                      ┌─── Gate Fails (CRITICAL) ───> ABORT (fail-fast)
                      │
Pipeline Stage ───>  Gate ─── Gate Passes ───────────> CONTINUE
                      │
                      └─── Gate Warns (WARNING) ──────> CONTINUE + MARK
                      
Exception in:
  collect ────> Tier 2/3 fallback (degraded) OR abort if all fail
  analyze ────> ABORT (no safe degradation — stale indicators mislead)
  score   ────> ABORT (no safe degradation — stale scores mislead)
  report  ────> RETRY once, then degrade to "raw data available" 
```

**Fail-Fast Zones** (no degradation allowed):
- Gate 1 CRITICAL (all-zero prices, < 50% expected stocks)
- Gate 2 CRITICAL (core indicator NaN > threshold)
- Gate 3 CRITICAL (score distribution mean outside [30, 70], std < 3)

**Degradation Zones** (continue with quality markers):
- Gate 1 WARNING (partial data 80-95% of expected, stale by 1-2 days)
- Data source fallback (pykrx -> FDR -> cache)
- Gate 3 WARNING (day-over-day drift, sub-score divergence, top-N turnover)
- Gate 4 (report format issues — non-critical)

**Rationale**: 
1. Round 2 finding: "Silent failure is the single biggest risk — trash scores without detection = irreversible trust loss." Fail-fast is the primary defense.
2. BUT a system that fails 20% of days due to transient pykrx issues will also lose user trust. Degradation for the collection tier only (with clear markers) is pragmatic.
3. The non-technical user understands "분석 완료" vs "분석 오류" (binary). Adding "제한적 분석" as a THIRD state is manageable IF the quality badge is prominent in the report.

---

## 9. Integrated Architecture

```
launchd (18:00 KST or on-wake)
  │
  ▼
pipeline_runner.py
  │
  ├── Pre-flight checks
  │   ├── Disk space > 500MB?
  │   ├── DuckDB health check
  │   └── PipelineLock acquired?
  │
  ├── Circuit Breaker Check
  │   ├── pykrx breaker state
  │   └── FDR breaker state
  │
  ├── Collect (with 3-tier fallback)
  │   ├── Tier 1: pykrx (via breaker)
  │   ├── Tier 2: FDR (via breaker)
  │   └── Tier 3: DuckDB cache
  │
  ├── Gate 1 (STRICT)
  │   ├── CRITICAL → ABORT + notify
  │   └── WARNING → degrade + continue
  │
  ├── Analyze
  │   └── Exception → ABORT (no safe degradation)
  │
  ├── Gate 2 (SELECTIVE: core NaN only)
  │   └── CRITICAL → ABORT
  │
  ├── Score
  │   └── Exception → ABORT
  │
  ├── Gate 3 (STRICT)
  │   ├── CRITICAL → ABORT + notify
  │   └── WARNING → mark + continue
  │
  ├── Report (inject quality header)
  │
  ├── Gate 4 (SELECTIVE: exists + non-empty)
  │
  ├── Save pipeline_state.json (success/degraded)
  │
  ├── Notify user (success/degraded/failure)
  │
  └── Exit with standardized code
```

---

## 10. Implementation Estimate

| Component | Lines | Phase | Priority |
|-----------|-------|-------|----------|
| Exit codes + Korean messages | ~75 | Phase 1 | P0 |
| Fail-fast handler | ~120 | Phase 1 | P0 |
| macOS notification | ~95 | Phase 1 | P0 |
| QualityContext (degradation levels) | ~100 | Phase 1 | P0 |
| FileCircuitBreaker | ~230 | Phase 1 | P1 |
| Fallback chain (3-tier) | ~130 | Phase 1 | P1 |
| Dual-format logging | ~60 | Phase 1 | P1 |
| Health dashboard | ~120 | Phase 1 | P2 |
| DuckDB health check + repair | ~130 | Phase 1 | P2 |
| **Phase 1 Total** | **~1,060** | — | — |

Note: This is ON TOP OF the 4-Gate validation (~780 lines from T04) and state management (~520 lines from T05).

**Combined reliability layer**: ~2,360 lines
- State management: ~520
- Validation gates: ~780
- Reliability/fallback: ~1,060

**Ratio to core pipeline**: If pipeline stages are ~800-1,000 lines, reliability is ~2.4-3x pipeline code. This ratio is HIGH but justified: this is a financial analysis tool where silent failure is catastrophic.

---

## 11. Parking Lot

### From This Research

1. **osascript notification compatibility on macOS Sequoia**: Some users report osascript notifications not working from Terminal.app on Sequoia. `terminal-notifier` (brew install) is more reliable. Need to test on user's actual macOS version.

2. **FinanceDataReader per-ticker API**: Unlike pykrx's batch API, FDR requires per-ticker calls. For 2,500 tickers with 1-second delay = ~42 minutes. This makes FDR a SLOW fallback. Consider: FDR for top-200 tickers only (from previous day's scores) as a practical compromise.

3. **Circuit breaker FAIL_MAX calibration**: FAIL_MAX=3 means 3 consecutive DAILY failures before opening. Is this too aggressive (opens after Mon/Tue/Wed fail even if it's just a KRX maintenance window)? Or too lenient (user sees 3 days of failures before fallback activates)? Needs empirical calibration.

4. **Quality badge prominence in report**: The "⚠️ 어제 데이터로 분석" badge MUST be at the very top of summary.md. If it's buried, the user may miss it — defeating the purpose. Claude Code interpretation should also mention it.

5. **Anomaly detection threshold calibration**: Score drift > 15 points and other thresholds are hypothetical. First 2 weeks should run in observation mode.

6. **Pre-flight disk space check threshold**: 500MB is conservative. DuckDB file for 5 years of OHLCV data is estimated ~50-100MB. But WAL during writes can grow (DuckDB #9150). Need empirical sizing.

7. **Log retention policy**: `logs/` directory needs rotation. Suggested: 14 days of human-readable, 30 days of JSON structured logs, 90 days of validation history.

8. **Email/Slack notification (Phase 2)**: macOS notification only works when user is at the Mac. For travel scenarios, email or Slack webhook would be more reliable. Requires integration work.

### Inherited from Previous Rounds

9. **pykrx data availability timing** (R2 PL#1): Still needs empirical test — when exactly is data available after 15:30 close?
10. **Trading day calendar** (R3 PL#3): `is_trading_day()` needs KRX holiday calendar
11. **Circuit breaker state persistence format** (R3 PL#14): Resolved — JSON file per source in `state/breaker_state/`
12. **Notification on failure** (R3 T05 PL#5): Resolved — macOS notification + log

---

## Sources

- [PyBreaker GitHub — Python Circuit Breaker](https://github.com/danielfm/pybreaker)
- [PyBreaker on PyPI](https://pypi.org/project/pybreaker/)
- [circuitbreaker on PyPI](https://pypi.org/project/circuitbreaker/)
- [How to Implement Circuit Breakers in Python (OneUptime, 2026)](https://oneuptime.com/blog/post/2026-01-23-python-circuit-breakers/view)
- [Implementing Circuit Breaker Pattern with PyBreaker](https://thebackenddevelopers.substack.com/p/implementing-the-circuit-breaker)
- [macOS terminal-notifier GitHub](https://github.com/julienXX/terminal-notifier)
- [macOS Notifications from Terminal Scripts](https://swissmacuser.ch/native-macos-notifications-from-terminal-scripts/)
- [DuckDB ACID Transactions](https://duckdb.org/2024/09/25/changing-data-with-confidence-and-acid)
- [DuckDB Concurrency Documentation](https://duckdb.org/docs/current/connect/concurrency)
- [DuckDB Low Disk Space Corruption — Issue #9667](https://github.com/duckdb/duckdb/issues/9667)
- [DuckDB WAL Size Issue — Issue #9150](https://github.com/duckdb/duckdb/issues/9150)
- [DuckDB Concurrent Writes Discussion — #4899](https://github.com/duckdb/duckdb/discussions/4899)
- [launchd StartCalendarInterval Sleep Behavior — Apple Forums](https://developer.apple.com/forums/thread/52369)
- [pykrx GitHub Repository](https://github.com/sharebook-kr/pykrx)
- [pykrx Empty DataFrame Issue — #30](https://github.com/sharebook-kr/pykrx/issues/30)
- [FinanceDataReader GitHub](https://github.com/FinanceData/FinanceDataReader)
- [Anthropic Claude Status — Uptime History](https://status.anthropic.com/uptime)
- [Claude Q1 2026 Uptime Discussion — Hacker News](https://news.ycombinator.com/item?id=47543189)
- [March 2026 Claude Outage & Failover Tips](https://deployflow.co/blog/claude-anthropic-outage-protect-claude-infrastructure/)
- [Python Exit Code Conventions](https://henryleach.com/2025/02/controlling-python-exit-codes-and-shell-scripts/)
- [Python Structured Logging Guide](https://www.hrekov.com/blog/python-structured-logging)
- [Graceful Degradation Patterns (2026)](https://dev.to/young_gao/graceful-degradation-4b5p)
- [Pipeline Recovery: Resume from Failures](https://fastercapital.com/content/Pipeline-Recovery--How-to-Recover-and-Resume-Your-Pipeline-from-Failures-and-Interruptions.html)
- [python-checkpointing GitHub](https://github.com/a-rahimi/python-checkpointing)
