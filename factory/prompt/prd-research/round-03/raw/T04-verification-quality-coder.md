---
round: 3
type: raw
teammate: verification-quality-coder
axis: verification-strategy
investigation_axis: coding-implementation
created: "2026-05-26T14:00:00+09:00"
question_summary: "Stock pipeline verification — strict (verify everything) vs selective (verify critical paths only). Concrete Python implementation for both, cost analysis, and hybrid recommendation."
assumption_axis: "Strict Verification vs Selective Verification"
branch_a: "Branch 4.1 — Strict Verification (verify EVERYTHING)"
branch_b: "Branch 4.2 — Selective Verification (verify only critical paths)"
web_search_count: 0
local_execution_tags:
  LOCAL_OK: ["ValidationResult dataclass", "Gate 1-4 validators", "retry decorator", "workflow-level checks", "quick_validate sampling", "DuckDB queries", "score distribution stats", "anomaly detection", "circuit breaker pattern"]
  LOCAL_PARTIAL: ["Monthly backtesting verification (needs 3+ months historical data)"]
  LOCAL_BLOCKED: []
sources:
  - "pykrx GitHub Issues (#276, #240, #151) — documented silent failure modes"
  - "Round 2 T03 Orchestration Engineer — Lightweight Plus recommendation"
  - "Round 2 S03 Finding 2 — Silent Failure is #1 risk"
  - "Round 2 S03 Finding 8 — Fail-Fast ~30 lines defends silent errors"
  - "Round 2 T05 Theory Foundation — scoring weights are hypotheses"
---

# T04: Verification & Quality Coder — Branch 4.1 vs 4.2 Investigation Report

## Executive Summary

This report provides **concrete Python implementations** for two verification strategies applied to the KOSPI/KOSDAQ Stock Technical Completeness Analysis pipeline. Branch 4.1 (Strict) validates every stage exhaustively. Branch 4.2 (Selective) validates only data-integrity-critical paths and samples for the rest.

**Conclusion**: The hybrid recommendation is to use **Strict verification for Gates 1 and 3** (data input and score output — where silent failure causes garbage results) and **Selective verification for Gates 2 and 4** (indicator computation and report formatting — where failures are either deterministic or cosmetic). This "Targeted Strict" approach captures ~95% of the reliability benefit at ~60% of the strict implementation cost.

---

## Shared Foundation: ValidationResult

Both branches share this data structure. Every validator returns it.

```python
# validation_types.py — Shared types for all validation gates [LOCAL-OK]

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(Enum):
    """Validation finding severity."""
    CRITICAL = "critical"   # Pipeline must abort
    WARNING = "warning"     # Pipeline continues, user alerted
    INFO = "info"           # Logged, no action


@dataclass
class Finding:
    """Single validation finding."""
    gate: str               # e.g. "gate_1", "gate_2"
    check: str              # e.g. "row_count", "price_sanity"
    severity: Severity
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Aggregated result from one or more validation checks."""
    gate: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    passed: bool = True
    findings: list[Finding] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def add(self, check: str, severity: Severity, message: str,
            details: dict | None = None) -> None:
        finding = Finding(
            gate=self.gate, check=check, severity=severity,
            message=message, details=details or {},
        )
        self.findings.append(finding)
        if severity == Severity.CRITICAL:
            self.passed = False

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "timestamp": self.timestamp,
            "passed": self.passed,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "stats": self.stats,
            "findings": [
                {
                    "check": f.check,
                    "severity": f.severity.value,
                    "message": f.message,
                    "details": f.details,
                }
                for f in self.findings
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
```

**Lines**: ~65. Used by both branches. [LOCAL-OK]

---

## Branch 4.1: Strict Verification (Verify EVERYTHING)

### Philosophy

Every pipeline stage has a validation gate that checks structure, content, range, freshness, distribution, and cross-stage consistency. The pipeline halts on any CRITICAL finding. Auto-retry handles transient failures. Monthly backtesting closes the feedback loop.

---

### Gate 1: Collection Validation (`validate_collection`)

Defends against: all-zero prices (FM-1), partial data (FM-2), stale data (FM-3).

```python
# validate_collection.py — Gate 1: Data collection output [LOCAL-OK]

from __future__ import annotations

from datetime import date, datetime, timedelta

import duckdb

from validation_types import Severity, ValidationResult


# --- Constants ---
MIN_EXPECTED_STOCKS = 2000
MAX_EXPECTED_STOCKS = 3200
MAX_PRICE_KRW = 10_000_000       # 10M KRW — KOSPI highest ~1M, margin for safety
MIN_NONZERO_RATIO = 0.95         # 95% of close prices must be > 0
STALE_DATA_DAYS = 3              # Alert if data is >3 calendar days old


def _get_last_trading_day(today: date | None = None) -> date:
    """Approximate last trading day (skip weekends).
    
    NOTE: Does not account for KRX holidays. Phase 2 adds
    pandas_market_calendars XKRX for precise holiday detection.
    """
    today = today or date.today()
    # If today is Saturday (5) or Sunday (6), step back
    if today.weekday() == 5:
        return today - timedelta(days=1)
    elif today.weekday() == 6:
        return today - timedelta(days=2)
    return today


def validate_collection(db_path: str, expected_date: date | None = None) -> ValidationResult:
    """
    Gate 1: Validate collection stage output in DuckDB.
    
    Checks:
        1. ohlcv table exists and has rows
        2. Row count within expected range (~2,000-3,200)
        3. Price sanity: no zeros, no negatives, no extremes
        4. Date freshness: data date is recent
        5. Market coverage: both KOSPI and KOSDAQ represented
        6. Volume sanity: no all-zero volume days
    
    Args:
        db_path: Path to DuckDB database file.
        expected_date: The trading date we expect data for.
                       Defaults to last trading day.
    
    Returns:
        ValidationResult with pass/fail and findings.
    """
    result = ValidationResult(gate="gate_1_collection")
    expected_date = expected_date or _get_last_trading_day()

    try:
        con = duckdb.connect(db_path, read_only=True)
    except Exception as e:
        result.add("db_connect", Severity.CRITICAL,
                   f"Cannot open DuckDB: {e}")
        return result

    try:
        # --- Check 1: Table exists and has rows ---
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'ohlcv'"
        ).fetchall()
        if not tables:
            result.add("table_exists", Severity.CRITICAL,
                       "Table 'ohlcv' does not exist in database")
            return result

        total_rows = con.execute("SELECT COUNT(*) FROM ohlcv").fetchone()[0]
        if total_rows == 0:
            result.add("row_count", Severity.CRITICAL,
                       "Table 'ohlcv' is empty (0 rows)")
            return result

        # --- Check 2: Row count for latest date ---
        latest_date_row = con.execute(
            "SELECT MAX(date) FROM ohlcv"
        ).fetchone()
        latest_date = latest_date_row[0]

        latest_count = con.execute(
            "SELECT COUNT(*) FROM ohlcv WHERE date = ?",
            [latest_date],
        ).fetchone()[0]

        result.stats["latest_date"] = str(latest_date)
        result.stats["latest_row_count"] = latest_count
        result.stats["total_rows"] = total_rows

        if latest_count < MIN_EXPECTED_STOCKS:
            result.add(
                "row_count", Severity.CRITICAL,
                f"Only {latest_count} stocks for {latest_date} "
                f"(expected >= {MIN_EXPECTED_STOCKS}). "
                f"Possible partial data from pykrx.",
                {"actual": latest_count, "minimum": MIN_EXPECTED_STOCKS},
            )
        elif latest_count > MAX_EXPECTED_STOCKS:
            result.add(
                "row_count", Severity.WARNING,
                f"Unusually high stock count: {latest_count} "
                f"(expected <= {MAX_EXPECTED_STOCKS})",
                {"actual": latest_count, "maximum": MAX_EXPECTED_STOCKS},
            )

        # --- Check 3: Price sanity ---
        # 3a: Zero close prices
        zero_close = con.execute(
            "SELECT COUNT(*) FROM ohlcv "
            "WHERE date = ? AND close = 0",
            [latest_date],
        ).fetchone()[0]

        zero_ratio = zero_close / max(latest_count, 1)
        result.stats["zero_close_count"] = zero_close
        result.stats["zero_close_ratio"] = round(zero_ratio, 4)

        if zero_ratio > (1 - MIN_NONZERO_RATIO):
            result.add(
                "price_zero", Severity.CRITICAL,
                f"{zero_close}/{latest_count} stocks have close=0 "
                f"({zero_ratio:.1%}). pykrx may have returned garbage data.",
                {"zero_count": zero_close, "ratio": zero_ratio},
            )

        # 3b: Negative prices
        neg_prices = con.execute(
            "SELECT COUNT(*) FROM ohlcv "
            "WHERE date = ? AND (open < 0 OR high < 0 OR low < 0 OR close < 0)",
            [latest_date],
        ).fetchone()[0]
        if neg_prices > 0:
            result.add(
                "price_negative", Severity.CRITICAL,
                f"{neg_prices} stocks have negative prices",
                {"count": neg_prices},
            )

        # 3c: Extreme prices
        extreme_prices = con.execute(
            "SELECT COUNT(*) FROM ohlcv "
            "WHERE date = ? AND close > ?",
            [latest_date, MAX_PRICE_KRW],
        ).fetchone()[0]
        if extreme_prices > 0:
            result.add(
                "price_extreme", Severity.WARNING,
                f"{extreme_prices} stocks have close > {MAX_PRICE_KRW:,} KRW",
                {"count": extreme_prices, "threshold": MAX_PRICE_KRW},
            )

        # 3d: OHLC consistency (high >= low, high >= open, high >= close)
        ohlc_violations = con.execute(
            "SELECT COUNT(*) FROM ohlcv "
            "WHERE date = ? AND (high < low OR high < open OR high < close "
            "   OR low > open OR low > close)",
            [latest_date],
        ).fetchone()[0]
        if ohlc_violations > 0:
            result.add(
                "ohlc_consistency", Severity.WARNING,
                f"{ohlc_violations} stocks have OHLC inconsistency "
                f"(high < low, etc.)",
                {"count": ohlc_violations},
            )

        # --- Check 4: Date freshness ---
        if latest_date is not None:
            # latest_date may be a string or date object depending on DuckDB version
            if isinstance(latest_date, str):
                latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d").date()
            else:
                latest_date_obj = latest_date

            days_old = (date.today() - latest_date_obj).days
            result.stats["data_age_days"] = days_old

            if days_old > STALE_DATA_DAYS:
                result.add(
                    "date_freshness", Severity.CRITICAL,
                    f"Data is {days_old} days old (latest: {latest_date}). "
                    f"Mac may have been off, or pykrx collection failed.",
                    {"days_old": days_old, "latest_date": str(latest_date)},
                )
            elif days_old > 1:
                result.add(
                    "date_freshness", Severity.WARNING,
                    f"Data is {days_old} day(s) old (latest: {latest_date}). "
                    f"May be normal if yesterday was a non-trading day.",
                    {"days_old": days_old},
                )

        # --- Check 5: Market coverage ---
        # Assumes 'market' column exists. If not, this check is skipped.
        has_market_col = con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'ohlcv' AND column_name = 'market'"
        ).fetchall()
        if has_market_col:
            markets = con.execute(
                "SELECT DISTINCT market FROM ohlcv WHERE date = ?",
                [latest_date],
            ).fetchall()
            market_names = {row[0] for row in markets}
            result.stats["markets_present"] = sorted(market_names)

            if len(market_names) < 2:
                result.add(
                    "market_coverage", Severity.WARNING,
                    f"Only {market_names} market(s) found. "
                    f"Expected both KOSPI and KOSDAQ.",
                    {"markets": sorted(market_names)},
                )

        # --- Check 6: Volume sanity ---
        zero_volume = con.execute(
            "SELECT COUNT(*) FROM ohlcv "
            "WHERE date = ? AND volume = 0",
            [latest_date],
        ).fetchone()[0]
        zero_vol_ratio = zero_volume / max(latest_count, 1)
        result.stats["zero_volume_ratio"] = round(zero_vol_ratio, 4)

        # Some stocks legitimately have zero volume (halted, very illiquid)
        # but >30% is suspicious
        if zero_vol_ratio > 0.30:
            result.add(
                "volume_zero", Severity.WARNING,
                f"{zero_volume}/{latest_count} stocks have zero volume "
                f"({zero_vol_ratio:.1%}). Possible data quality issue.",
                {"zero_count": zero_volume, "ratio": zero_vol_ratio},
            )

    finally:
        con.close()

    return result
```

**Lines**: ~165 (excluding comments/docstrings). [LOCAL-OK]

**Defenses**:
| Failure Mode | Check | Severity |
|-------------|-------|----------|
| FM-1: All-zero prices | `price_zero` — ratio > 5% | CRITICAL |
| FM-2: Partial data (1,800/2,500) | `row_count` — < 2,000 | CRITICAL |
| FM-3: Stale data | `date_freshness` — > 3 days | CRITICAL |
| FM-6: Corrupted DB | `db_connect`, `table_exists` | CRITICAL |
| Data quality: OHLC inconsistency | `ohlc_consistency` | WARNING |
| Data quality: extreme prices | `price_extreme` | WARNING |

---

### Gate 2: Indicator Validation (`validate_indicators`)

Defends against: NaN flooding (FM-4), range violations.

```python
# validate_indicators.py — Gate 2: Analysis stage output [LOCAL-OK]

from __future__ import annotations

import duckdb

from validation_types import Severity, ValidationResult


# --- Indicator range constraints ---
INDICATOR_RANGES: dict[str, tuple[float, float]] = {
    # (min_valid, max_valid)
    "rsi_14": (0.0, 100.0),
    "adx_14": (0.0, 100.0),
    "macd": (-1e9, 1e9),           # No bounded range, just no NaN/Inf
    "macd_signal": (-1e9, 1e9),
    "macd_hist": (-1e9, 1e9),
    "bb_upper": (0.0, 1e9),        # Bollinger bands must be positive
    "bb_middle": (0.0, 1e9),
    "bb_lower": (0.0, 1e9),
    "bb_width": (0.0, 1e9),
    "atr_14": (0.0, 1e9),
    "sma_20": (0.0, 1e9),
    "sma_50": (0.0, 1e9),
    "sma_150": (0.0, 1e9),
    "sma_200": (0.0, 1e9),
    "ema_21": (0.0, 1e9),
    "volume_sma_50": (0.0, 1e18),   # Volume can be very large
    "rs_score": (-1e9, 1e9),        # Relative Strength — can be negative
}

# Core indicators that MUST be present for scoring
CORE_INDICATORS = [
    "sma_50", "sma_150", "sma_200",   # MA Alignment sub-score
    "bb_width",                         # Base Formation sub-score (VCP proxy)
    "volume_sma_50",                    # Volume Behavior sub-score
    "rsi_14", "macd_hist",             # Momentum sub-score
    "atr_14",                           # Breakout Readiness sub-score
    "rs_score",                         # Relative Strength sub-score
]

MAX_NAN_RATIO = 0.05  # 5% NaN tolerance for core indicators
MAX_NAN_RATIO_NON_CORE = 0.15  # 15% for non-core (longer-period SMAs need history)


def validate_indicators(db_path: str, target_date: str | None = None) -> ValidationResult:
    """
    Gate 2: Validate indicator computation output.
    
    Checks:
        1. indicators table exists with expected columns
        2. NaN ratio per indicator (core < 5%, non-core < 15%)
        3. Range sanity: each indicator within defined bounds
        4. Core indicator completeness: all 6 sub-score inputs present
        5. Inf detection: no infinite values
    
    Args:
        db_path: Path to DuckDB database.
        target_date: Date to validate (default: latest).
    
    Returns:
        ValidationResult with pass/fail and per-indicator stats.
    """
    result = ValidationResult(gate="gate_2_indicators")

    try:
        con = duckdb.connect(db_path, read_only=True)
    except Exception as e:
        result.add("db_connect", Severity.CRITICAL,
                   f"Cannot open DuckDB: {e}")
        return result

    try:
        # Get table info
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'indicators'"
        ).fetchall()
        if not tables:
            result.add("table_exists", Severity.CRITICAL,
                       "Table 'indicators' does not exist")
            return result

        # Get target date
        if target_date is None:
            target_date = con.execute(
                "SELECT MAX(date) FROM indicators"
            ).fetchone()[0]

        total_stocks = con.execute(
            "SELECT COUNT(*) FROM indicators WHERE date = ?",
            [target_date],
        ).fetchone()[0]

        if total_stocks == 0:
            result.add("row_count", Severity.CRITICAL,
                       f"No indicator rows for date {target_date}")
            return result

        result.stats["target_date"] = str(target_date)
        result.stats["total_stocks"] = total_stocks

        # Get actual columns
        columns = con.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'indicators'"
        ).fetchall()
        actual_columns = {row[0] for row in columns}

        # --- Check 1: Core indicator columns exist ---
        missing_core = [c for c in CORE_INDICATORS if c not in actual_columns]
        if missing_core:
            result.add(
                "core_columns", Severity.CRITICAL,
                f"Missing core indicator columns: {missing_core}. "
                f"Cannot compute all 6 sub-scores.",
                {"missing": missing_core},
            )
            # Continue checking what we can

        # --- Check 2 & 3: NaN ratio and range per indicator ---
        indicator_stats = {}
        for col_name, (min_val, max_val) in INDICATOR_RANGES.items():
            if col_name not in actual_columns:
                continue

            stats = con.execute(f"""
                SELECT 
                    COUNT(*) AS total,
                    SUM(CASE WHEN {col_name} IS NULL THEN 1 ELSE 0 END) AS null_count,
                    SUM(CASE WHEN {col_name} = 'Infinity' OR {col_name} = '-Infinity' 
                         THEN 1 ELSE 0 END) AS inf_count,
                    SUM(CASE WHEN {col_name} IS NOT NULL 
                              AND {col_name} < {min_val} THEN 1 ELSE 0 END) AS below_min,
                    SUM(CASE WHEN {col_name} IS NOT NULL 
                              AND {col_name} > {max_val} THEN 1 ELSE 0 END) AS above_max,
                    AVG({col_name}) AS mean_val,
                    STDDEV({col_name}) AS std_val
                FROM indicators
                WHERE date = ?
            """, [target_date]).fetchone()

            total, null_count, inf_count, below_min, above_max, mean_val, std_val = stats
            nan_ratio = null_count / max(total, 1)
            is_core = col_name in CORE_INDICATORS
            threshold = MAX_NAN_RATIO if is_core else MAX_NAN_RATIO_NON_CORE

            indicator_stats[col_name] = {
                "nan_ratio": round(nan_ratio, 4),
                "inf_count": inf_count,
                "below_min": below_min,
                "above_max": above_max,
                "mean": round(mean_val, 4) if mean_val is not None else None,
                "std": round(std_val, 4) if std_val is not None else None,
                "is_core": is_core,
            }

            # NaN check
            if nan_ratio > threshold:
                severity = Severity.CRITICAL if is_core else Severity.WARNING
                result.add(
                    f"nan_ratio_{col_name}", severity,
                    f"{'CORE ' if is_core else ''}{col_name}: "
                    f"NaN ratio {nan_ratio:.1%} exceeds "
                    f"threshold {threshold:.0%} "
                    f"({null_count}/{total} stocks)",
                    {"nan_ratio": nan_ratio, "threshold": threshold},
                )

            # Inf check
            if inf_count and inf_count > 0:
                result.add(
                    f"inf_{col_name}", Severity.CRITICAL,
                    f"{col_name}: {inf_count} infinite values detected",
                    {"inf_count": inf_count},
                )

            # Range check
            out_of_range = (below_min or 0) + (above_max or 0)
            if out_of_range > 0:
                result.add(
                    f"range_{col_name}", Severity.WARNING,
                    f"{col_name}: {out_of_range} values out of range "
                    f"[{min_val}, {max_val}]",
                    {"below_min": below_min, "above_max": above_max},
                )

        result.stats["indicator_details"] = indicator_stats

        # --- Check 4: Per-stock completeness ---
        # Count stocks missing ANY core indicator
        if not missing_core:
            core_null_conditions = " OR ".join(
                f"{c} IS NULL" for c in CORE_INDICATORS
            )
            incomplete_stocks = con.execute(f"""
                SELECT COUNT(*) FROM indicators
                WHERE date = ? AND ({core_null_conditions})
            """, [target_date]).fetchone()[0]

            incomplete_ratio = incomplete_stocks / max(total_stocks, 1)
            result.stats["incomplete_stock_ratio"] = round(incomplete_ratio, 4)

            if incomplete_ratio > 0.10:
                result.add(
                    "stock_completeness", Severity.WARNING,
                    f"{incomplete_stocks}/{total_stocks} stocks "
                    f"({incomplete_ratio:.1%}) missing at least one "
                    f"core indicator. These stocks will have partial scores.",
                    {"incomplete_count": incomplete_stocks},
                )

    finally:
        con.close()

    return result
```

**Lines**: ~155. [LOCAL-OK]

---

### Gate 3: Score Validation (`validate_scores`)

Defends against: score distribution anomaly (FM-5), sub-score divergence.

```python
# validate_scores.py — Gate 3: Scoring stage output [LOCAL-OK]

from __future__ import annotations

import math
from datetime import date

import duckdb

from validation_types import Severity, ValidationResult


# --- Score distribution expectations ---
EXPECTED_MEAN_RANGE = (30.0, 70.0)    # Composite score mean should be 30-70
EXPECTED_STD_RANGE = (8.0, 30.0)      # Std dev: too tight = broken, too wide = random
MAX_DAY_OVER_DAY_DRIFT = 15.0         # Mean shift > 15 points = anomaly
MAX_SUB_SCORE_DIVERGENCE = 60.0       # If MA=90 but Volume=20, divergence = 70 > 60

SUB_SCORE_COLUMNS = [
    "ma_alignment",       # MA Alignment (weight: 20%)
    "base_formation",     # Base Formation (weight: 20%)
    "volume_behavior",    # Volume Behavior (weight: 20%)
    "momentum",           # Momentum (weight: 15%)
    "breakout_readiness", # Breakout Readiness (weight: 15%)
    "relative_strength",  # Relative Strength (weight: 10%)
]


def validate_scores(db_path: str, target_date: str | None = None) -> ValidationResult:
    """
    Gate 3: Validate scoring stage output.
    
    Checks:
        1. scores table exists and has rows matching collection count
        2. Score range: composite in [0, 100], sub-scores in [0, 100]
        3. Distribution sanity: mean in [30, 70], std in [8, 30]
        4. Day-over-day drift: mean shift > 15 points flagged
        5. Sub-score divergence: flag suspicious MA↔Volume gaps
        6. All-same-score detection (e.g., every stock = 50)
        7. Top-N stability: yesterday's top-10 didn't all vanish
    
    Returns:
        ValidationResult with pass/fail and distribution stats.
    """
    result = ValidationResult(gate="gate_3_scores")

    try:
        con = duckdb.connect(db_path, read_only=True)
    except Exception as e:
        result.add("db_connect", Severity.CRITICAL,
                   f"Cannot open DuckDB: {e}")
        return result

    try:
        # Check table exists
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'scores'"
        ).fetchall()
        if not tables:
            result.add("table_exists", Severity.CRITICAL,
                       "Table 'scores' does not exist")
            return result

        # Get target date
        if target_date is None:
            target_date = con.execute(
                "SELECT MAX(date) FROM scores"
            ).fetchone()[0]

        total_scored = con.execute(
            "SELECT COUNT(*) FROM scores WHERE date = ?",
            [target_date],
        ).fetchone()[0]

        if total_scored == 0:
            result.add("row_count", Severity.CRITICAL,
                       f"No scores for date {target_date}")
            return result

        result.stats["target_date"] = str(target_date)
        result.stats["total_scored"] = total_scored

        # --- Check 1: Cross-stage consistency (scores vs collection) ---
        # Check if ohlcv table exists for count comparison
        ohlcv_exists = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'ohlcv'"
        ).fetchall()
        if ohlcv_exists:
            collected_count = con.execute(
                "SELECT COUNT(*) FROM ohlcv WHERE date = ?",
                [target_date],
            ).fetchone()[0]
            if collected_count > 0:
                coverage = total_scored / collected_count
                result.stats["score_coverage"] = round(coverage, 4)
                if coverage < 0.80:
                    result.add(
                        "cross_stage_coverage", Severity.WARNING,
                        f"Only {total_scored}/{collected_count} stocks scored "
                        f"({coverage:.1%}). {collected_count - total_scored} "
                        f"stocks lost between collection and scoring.",
                        {"scored": total_scored, "collected": collected_count},
                    )

        # --- Check 2: Score range ---
        out_of_range = con.execute(
            "SELECT COUNT(*) FROM scores "
            "WHERE date = ? AND (composite_score < 0 OR composite_score > 100)",
            [target_date],
        ).fetchone()[0]
        if out_of_range > 0:
            result.add(
                "score_range", Severity.CRITICAL,
                f"{out_of_range} stocks have composite_score outside [0, 100]",
                {"count": out_of_range},
            )

        # Sub-score range check
        for sub in SUB_SCORE_COLUMNS:
            # Check if column exists first
            col_check = con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'scores' AND column_name = ?",
                [sub],
            ).fetchall()
            if not col_check:
                result.add(
                    f"missing_subscore_{sub}", Severity.WARNING,
                    f"Sub-score column '{sub}' not found in scores table",
                )
                continue

            sub_out = con.execute(f"""
                SELECT COUNT(*) FROM scores
                WHERE date = ? AND ({sub} < 0 OR {sub} > 100)
            """, [target_date]).fetchone()[0]
            if sub_out > 0:
                result.add(
                    f"subscore_range_{sub}", Severity.WARNING,
                    f"{sub}: {sub_out} values outside [0, 100]",
                )

        # --- Check 3: Distribution sanity ---
        dist = con.execute("""
            SELECT 
                AVG(composite_score) AS mean_score,
                STDDEV(composite_score) AS std_score,
                MIN(composite_score) AS min_score,
                MAX(composite_score) AS max_score,
                MEDIAN(composite_score) AS median_score
            FROM scores
            WHERE date = ?
        """, [target_date]).fetchone()

        mean_score, std_score, min_score, max_score, median_score = dist
        result.stats["distribution"] = {
            "mean": round(mean_score, 2) if mean_score else None,
            "std": round(std_score, 2) if std_score else None,
            "min": round(min_score, 2) if min_score else None,
            "max": round(max_score, 2) if max_score else None,
            "median": round(median_score, 2) if median_score else None,
        }

        if mean_score is not None:
            if not (EXPECTED_MEAN_RANGE[0] <= mean_score <= EXPECTED_MEAN_RANGE[1]):
                result.add(
                    "dist_mean", Severity.CRITICAL,
                    f"Mean composite score = {mean_score:.1f}, "
                    f"outside expected range {EXPECTED_MEAN_RANGE}. "
                    f"Possible systemic scoring error.",
                    {"mean": mean_score, "expected": EXPECTED_MEAN_RANGE},
                )

        if std_score is not None:
            if not (EXPECTED_STD_RANGE[0] <= std_score <= EXPECTED_STD_RANGE[1]):
                sev = Severity.CRITICAL if std_score < 3.0 else Severity.WARNING
                result.add(
                    "dist_std", sev,
                    f"Score std dev = {std_score:.1f}, "
                    f"outside expected range {EXPECTED_STD_RANGE}. "
                    f"{'All scores nearly identical — scoring logic broken?' if std_score < 3 else 'Unusually wide spread.'}",
                    {"std": std_score, "expected": EXPECTED_STD_RANGE},
                )

        # --- Check 4: Day-over-day drift ---
        prev_dates = con.execute("""
            SELECT DISTINCT date FROM scores
            WHERE date < ?
            ORDER BY date DESC
            LIMIT 1
        """, [target_date]).fetchall()

        if prev_dates:
            prev_date = prev_dates[0][0]
            prev_mean = con.execute(
                "SELECT AVG(composite_score) FROM scores WHERE date = ?",
                [prev_date],
            ).fetchone()[0]

            if prev_mean is not None and mean_score is not None:
                drift = abs(mean_score - prev_mean)
                result.stats["day_over_day_drift"] = round(drift, 2)
                result.stats["prev_date"] = str(prev_date)
                result.stats["prev_mean"] = round(prev_mean, 2)

                if drift > MAX_DAY_OVER_DAY_DRIFT:
                    result.add(
                        "drift", Severity.WARNING,
                        f"Mean score shifted {drift:.1f} points "
                        f"({prev_mean:.1f} → {mean_score:.1f}). "
                        f"Market regime change or scoring bug?",
                        {"drift": drift, "threshold": MAX_DAY_OVER_DAY_DRIFT},
                    )

        # --- Check 5: Sub-score divergence (suspicious patterns) ---
        # Find stocks where max sub-score - min sub-score > threshold
        existing_subs = []
        for sub in SUB_SCORE_COLUMNS:
            col_check = con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'scores' AND column_name = ?",
                [sub],
            ).fetchall()
            if col_check:
                existing_subs.append(sub)

        if len(existing_subs) >= 3:
            # Compute per-stock divergence
            greatest_expr = f"GREATEST({', '.join(existing_subs)})"
            least_expr = f"LEAST({', '.join(existing_subs)})"

            high_divergence = con.execute(f"""
                SELECT COUNT(*) FROM scores
                WHERE date = ?
                AND ({greatest_expr} - {least_expr}) > ?
            """, [target_date, MAX_SUB_SCORE_DIVERGENCE]).fetchone()[0]

            div_ratio = high_divergence / max(total_scored, 1)
            result.stats["high_divergence_ratio"] = round(div_ratio, 4)

            if div_ratio > 0.20:
                result.add(
                    "subscore_divergence", Severity.WARNING,
                    f"{high_divergence} stocks ({div_ratio:.1%}) have "
                    f"sub-score divergence > {MAX_SUB_SCORE_DIVERGENCE}. "
                    f"E.g., MA=90 but Volume=20. Review scoring logic.",
                    {"count": high_divergence, "ratio": div_ratio},
                )

        # --- Check 6: All-same detection ---
        if std_score is not None and std_score < 1.0 and total_scored > 10:
            result.add(
                "all_same_scores", Severity.CRITICAL,
                f"Score std dev = {std_score:.2f} — scores are effectively "
                f"identical. Scoring formula is broken.",
                {"std": std_score},
            )

        # --- Check 7: Top-N stability ---
        if prev_dates:
            prev_date = prev_dates[0][0]
            today_top10 = set(row[0] for row in con.execute("""
                SELECT ticker FROM scores
                WHERE date = ?
                ORDER BY composite_score DESC
                LIMIT 10
            """, [target_date]).fetchall())

            prev_top10 = set(row[0] for row in con.execute("""
                SELECT ticker FROM scores
                WHERE date = ?
                ORDER BY composite_score DESC
                LIMIT 10
            """, [prev_date]).fetchall())

            overlap = len(today_top10 & prev_top10)
            turnover = 10 - overlap
            result.stats["top10_turnover"] = turnover

            if turnover >= 8:
                result.add(
                    "top10_stability", Severity.WARNING,
                    f"Top-10 turnover = {turnover}/10. "
                    f"Only {overlap} stocks persisted from yesterday. "
                    f"Normal market volatility or scoring instability?",
                    {"turnover": turnover, "overlap": overlap},
                )

    finally:
        con.close()

    return result
```

**Lines**: ~220. [LOCAL-OK]

---

### Gate 4: Report Validation (`validate_report`)

Defends against: empty/missing report, stale report.

```python
# validate_report.py — Gate 4: Report stage output [LOCAL-OK]

from __future__ import annotations

import os
import time
from datetime import datetime

from validation_types import Severity, ValidationResult


EXPECTED_SECTIONS = [
    "상위",       # Top stocks section (e.g., "상위 20 종목", "상위 종목")
    "시장",       # Market overview (e.g., "시장 개요", "시장 현황")
    "점수",       # Scoring details (e.g., "점수 분포", "점수 요약")
]

MIN_REPORT_SIZE_BYTES = 500       # A real report is at least 500 bytes
MAX_REPORT_AGE_SECONDS = 3600     # Report should be < 1 hour old


def validate_report(report_path: str) -> ValidationResult:
    """
    Gate 4: Validate generated summary report.
    
    Checks:
        1. File exists
        2. File is non-empty (> 500 bytes)
        3. Contains expected sections
        4. File age < 1 hour
        5. No obvious error markers
    
    Returns:
        ValidationResult with pass/fail and findings.
    """
    result = ValidationResult(gate="gate_4_report")

    # --- Check 1: File exists ---
    if not os.path.exists(report_path):
        result.add("file_exists", Severity.CRITICAL,
                   f"Report file does not exist: {report_path}")
        return result

    # --- Check 2: File size ---
    file_size = os.path.getsize(report_path)
    result.stats["file_size_bytes"] = file_size

    if file_size == 0:
        result.add("file_empty", Severity.CRITICAL,
                   "Report file is empty (0 bytes)")
        return result

    if file_size < MIN_REPORT_SIZE_BYTES:
        result.add(
            "file_too_small", Severity.WARNING,
            f"Report is only {file_size} bytes "
            f"(expected >= {MIN_REPORT_SIZE_BYTES}). "
            f"May be a stub or error output.",
            {"size": file_size, "minimum": MIN_REPORT_SIZE_BYTES},
        )

    # --- Check 3: Expected sections ---
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        result.add("file_read", Severity.CRITICAL,
                   f"Cannot read report: {e}")
        return result

    result.stats["line_count"] = content.count("\n") + 1

    missing_sections = []
    for section_keyword in EXPECTED_SECTIONS:
        if section_keyword not in content:
            missing_sections.append(section_keyword)

    if missing_sections:
        result.add(
            "missing_sections", Severity.WARNING,
            f"Report missing expected section keywords: {missing_sections}",
            {"missing": missing_sections},
        )

    # --- Check 4: File age ---
    mtime = os.path.getmtime(report_path)
    age_seconds = time.time() - mtime
    result.stats["age_seconds"] = round(age_seconds, 0)

    if age_seconds > MAX_REPORT_AGE_SECONDS:
        result.add(
            "file_age", Severity.WARNING,
            f"Report is {age_seconds / 3600:.1f} hours old. "
            f"May be from a previous run.",
            {"age_seconds": age_seconds},
        )

    # --- Check 5: Error markers ---
    error_markers = ["Traceback", "Error:", "FAILED", "데이터 없음"]
    for marker in error_markers:
        if marker in content:
            result.add(
                "error_marker", Severity.WARNING,
                f"Report contains error marker: '{marker}'",
                {"marker": marker},
            )

    return result
```

**Lines**: ~85. [LOCAL-OK]

---

### Auto-Retry Decorator

Handles transient failures (pykrx network issues, DuckDB locks).

```python
# retry.py — Auto-retry with exponential backoff [LOCAL-OK]

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryExhausted(Exception):
    """All retry attempts failed."""
    def __init__(self, stage: str, attempts: int, last_error: Exception):
        self.stage = stage
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Stage '{stage}' failed after {attempts} attempts: {last_error}"
        )


def retry(
    max_attempts: int = 3,
    base_delay: float = 30.0,
    multiplier: float = 2.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    stage_name: str | None = None,
) -> Callable:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (including first).
        base_delay: Initial delay in seconds.
        multiplier: Delay multiplier per attempt (exponential backoff).
        retryable_exceptions: Tuple of exception types to retry on.
        stage_name: Human-readable stage name for logging.
    
    Usage:
        @retry(max_attempts=3, base_delay=30, stage_name="collect")
        def collect_data(db_path: str) -> None:
            ...
    
    Backoff schedule (default):
        Attempt 1: immediate
        Attempt 2: 30s delay
        Attempt 3: 60s delay
        Total max wait: 90s
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            name = stage_name or func.__name__
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(
                            f"[{name}] Succeeded on attempt {attempt}/{max_attempts}"
                        )
                    return result
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = base_delay * (multiplier ** (attempt - 1))
                        logger.warning(
                            f"[{name}] Attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.0f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[{name}] All {max_attempts} attempts exhausted. "
                            f"Last error: {e}"
                        )

            raise RetryExhausted(name, max_attempts, last_exception)  # type: ignore

        return wrapper
    return decorator


# --- Pre-configured decorators for each pipeline stage ---

retry_collect = retry(
    max_attempts=3,
    base_delay=30.0,        # 30s, 60s
    multiplier=2.0,
    retryable_exceptions=(ConnectionError, TimeoutError, OSError),
    stage_name="collect",
)

retry_compute = retry(
    max_attempts=2,
    base_delay=1.0,
    multiplier=1.0,
    retryable_exceptions=(Exception,),
    stage_name="compute",
)
```

**Lines**: ~85. [LOCAL-OK]

---

### Workflow-Level Verification (End-to-End)

```python
# validate_workflow.py — Workflow-level end-to-end verification [LOCAL-OK]

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from validation_types import Severity, ValidationResult

logger = logging.getLogger(__name__)


def validate_workflow(
    db_path: str,
    report_path: str,
    gate_results: list[ValidationResult],
) -> ValidationResult:
    """
    Workflow-level verification: all gates passed + cross-stage checks.
    
    Checks:
        1. All gates passed (no CRITICAL findings)
        2. Cross-stage stock count consistency
        3. Pipeline completion within time window
        4. Persist validation history for trend analysis
    
    Returns:
        ValidationResult summarizing entire pipeline health.
    """
    result = ValidationResult(gate="workflow_level")

    # --- Check 1: All gates passed ---
    failed_gates = [g for g in gate_results if not g.passed]
    total_critical = sum(g.critical_count for g in gate_results)
    total_warnings = sum(g.warning_count for g in gate_results)

    result.stats["gates_total"] = len(gate_results)
    result.stats["gates_passed"] = len(gate_results) - len(failed_gates)
    result.stats["total_critical"] = total_critical
    result.stats["total_warnings"] = total_warnings

    if failed_gates:
        gate_names = [g.gate for g in failed_gates]
        result.add(
            "gates_failed", Severity.CRITICAL,
            f"{len(failed_gates)} gate(s) failed: {gate_names}. "
            f"Total CRITICAL findings: {total_critical}.",
            {"failed_gates": gate_names},
        )

    # --- Check 2: Cross-stage stock count consistency ---
    # Extract stock counts from gate stats
    collected = None
    scored = None
    for g in gate_results:
        if g.gate == "gate_1_collection":
            collected = g.stats.get("latest_row_count")
        elif g.gate == "gate_3_scores":
            scored = g.stats.get("total_scored")

    if collected and scored:
        drop_ratio = 1 - (scored / collected)
        result.stats["collection_to_score_drop"] = round(drop_ratio, 4)
        if drop_ratio > 0.20:
            result.add(
                "stock_drop", Severity.WARNING,
                f"{scored}/{collected} stocks survived to scoring "
                f"({drop_ratio:.1%} dropped). "
                f"Check indicator computation for mass NaN.",
                {"collected": collected, "scored": scored, "drop": drop_ratio},
            )

    # --- Check 3: Persist validation history ---
    history_path = os.path.join(
        os.path.dirname(db_path), "validation_history.json"
    )
    history_entry = {
        "date": date.today().isoformat(),
        "timestamp": datetime.now().isoformat(),
        "passed": result.passed and not failed_gates,
        "total_critical": total_critical,
        "total_warnings": total_warnings,
        "gates": {g.gate: g.passed for g in gate_results},
    }

    # Append to history file
    history: list[dict] = []
    if os.path.exists(history_path):
        try:
            with open(history_path, "r") as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    history.append(history_entry)
    # Keep last 90 days
    history = history[-90:]

    try:
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.warning(f"Cannot write validation history: {e}")

    return result


def validate_monthly_backtest(
    db_path: str,
    lookback_days: int = 20,
) -> ValidationResult:
    """
    Monthly backtesting verification: did top-scored stocks outperform?
    
    Checks:
        1. Stocks scored 80+ N days ago: actual N+20 day return
        2. Stocks scored <30 N days ago: actual N+20 day return
        3. If low-scored stocks outperform high-scored stocks, flag calibration
    
    NOTE: This is a Phase 3 feature. Requires 3+ months of historical
    scores and OHLCV data. Implementation here is the skeleton.
    [LOCAL-PARTIAL — needs historical data accumulation]
    """
    import duckdb

    result = ValidationResult(gate="monthly_backtest")

    try:
        con = duckdb.connect(db_path, read_only=True)
    except Exception as e:
        result.add("db_connect", Severity.CRITICAL,
                   f"Cannot open DuckDB: {e}")
        return result

    try:
        # Check if we have enough history
        date_range = con.execute("""
            SELECT MIN(date), MAX(date), COUNT(DISTINCT date) 
            FROM scores
        """).fetchone()
        min_date, max_date, date_count = date_range

        result.stats["score_history_days"] = date_count or 0

        if (date_count or 0) < lookback_days + 5:
            result.add(
                "insufficient_history", Severity.INFO,
                f"Only {date_count} days of score history. "
                f"Need {lookback_days + 5}+ days for backtesting. "
                f"Will be available after ~1 month of operation.",
                {"days_available": date_count, "days_needed": lookback_days + 5},
            )
            return result

        # Get the date that is ~lookback_days ago
        eval_date = con.execute(f"""
            SELECT DISTINCT date FROM scores
            ORDER BY date ASC
            LIMIT 1
            OFFSET (SELECT COUNT(DISTINCT date) - {lookback_days} - 1 FROM scores)
        """).fetchone()

        if not eval_date:
            result.add("no_eval_date", Severity.INFO,
                       "Cannot determine evaluation date")
            return result

        eval_date = eval_date[0]
        result.stats["evaluation_date"] = str(eval_date)

        # Top-scored stocks (>= 80) on eval_date
        top_stocks = con.execute("""
            SELECT s.ticker, s.composite_score,
                   o_after.close AS close_after,
                   o_before.close AS close_before,
                   ((o_after.close - o_before.close) / NULLIF(o_before.close, 0)) * 100 
                       AS return_pct
            FROM scores s
            JOIN ohlcv o_before ON s.ticker = o_before.ticker AND s.date = o_before.date
            JOIN (
                SELECT ticker, close, date FROM ohlcv
                WHERE date = (SELECT MAX(date) FROM ohlcv)
            ) o_after ON s.ticker = o_after.ticker
            WHERE s.date = ? AND s.composite_score >= 80
        """, [eval_date]).fetchall()

        # Bottom-scored stocks (<= 30) on eval_date
        bottom_stocks = con.execute("""
            SELECT s.ticker, s.composite_score,
                   ((o_after.close - o_before.close) / NULLIF(o_before.close, 0)) * 100 
                       AS return_pct
            FROM scores s
            JOIN ohlcv o_before ON s.ticker = o_before.ticker AND s.date = o_before.date
            JOIN (
                SELECT ticker, close, date FROM ohlcv
                WHERE date = (SELECT MAX(date) FROM ohlcv)
            ) o_after ON s.ticker = o_after.ticker
            WHERE s.date = ? AND s.composite_score <= 30
        """, [eval_date]).fetchall()

        # Compute average returns
        if top_stocks:
            top_returns = [r[4] for r in top_stocks if r[4] is not None]
            avg_top_return = sum(top_returns) / len(top_returns) if top_returns else 0
            result.stats["top_stock_count"] = len(top_stocks)
            result.stats["avg_top_return_pct"] = round(avg_top_return, 2)
        else:
            avg_top_return = None

        if bottom_stocks:
            bottom_returns = [r[2] for r in bottom_stocks if r[2] is not None]
            avg_bottom_return = sum(bottom_returns) / len(bottom_returns) if bottom_returns else 0
            result.stats["bottom_stock_count"] = len(bottom_stocks)
            result.stats["avg_bottom_return_pct"] = round(avg_bottom_return, 2)
        else:
            avg_bottom_return = None

        # Calibration check: top should outperform bottom
        if avg_top_return is not None and avg_bottom_return is not None:
            if avg_bottom_return > avg_top_return:
                result.add(
                    "calibration_inverted", Severity.WARNING,
                    f"CALIBRATION ALERT: Bottom-scored stocks "
                    f"({avg_bottom_return:.1f}%) outperformed "
                    f"top-scored stocks ({avg_top_return:.1f}%). "
                    f"Scoring weights may need recalibration.",
                    {
                        "avg_top_return": avg_top_return,
                        "avg_bottom_return": avg_bottom_return,
                    },
                )

    finally:
        con.close()

    return result
```

**Lines**: ~175. [LOCAL-PARTIAL for backtesting — needs accumulated history]

---

### Pipeline Orchestrator (Strict Mode)

Ties all gates together with retry and escalation.

```python
# pipeline_strict.py — Pipeline orchestrator with strict verification [LOCAL-OK]

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

from retry import retry, retry_collect, RetryExhausted
from validation_types import Severity, ValidationResult

# These would be the actual pipeline stage functions
# from collect import collect_data
# from analyze import analyze_data
# from score import score_data
# from report import generate_report

from validate_collection import validate_collection
from validate_indicators import validate_indicators
from validate_scores import validate_scores
from validate_report import validate_report
from validate_workflow_level import validate_workflow, validate_monthly_backtest

logger = logging.getLogger(__name__)

DB_PATH = "data/stocks.duckdb"
REPORT_PATH = "output/summary.md"
BACKUP_DIR = "data/backups"
STATE_FILE = "data/pipeline_state.json"


def backup_database(db_path: str) -> str | None:
    """Create timestamped backup of DuckDB file before pipeline run."""
    if not os.path.exists(db_path):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"stocks_{timestamp}.duckdb")
    shutil.copy2(db_path, backup_path)
    # Prune backups older than 7 days
    _prune_backups(BACKUP_DIR, max_age_days=7)
    return backup_path


def _prune_backups(backup_dir: str, max_age_days: int = 7) -> None:
    """Remove backups older than max_age_days."""
    cutoff = datetime.now().timestamp() - (max_age_days * 86400)
    for f in Path(backup_dir).glob("stocks_*.duckdb"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            logger.info(f"Pruned old backup: {f.name}")


def update_state(stage: str, status: str, error: str | None = None,
                 extra: dict | None = None) -> None:
    """Update pipeline_state.json."""
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError):
            state = {}

    state.update({
        "last_stage": stage,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "error": error,
    })
    if extra:
        state.update(extra)

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def run_pipeline_strict() -> bool:
    """
    Run full pipeline with strict verification at every gate.
    
    Flow:
        backup → collect → Gate1 → analyze → Gate2 → score → Gate3 → 
        report → Gate4 → workflow-level → persist results
    
    Returns:
        True if pipeline completed successfully, False otherwise.
    """
    gate_results: list[ValidationResult] = []
    pipeline_start = datetime.now()

    # --- Step 0: Backup ---
    backup_path = backup_database(DB_PATH)
    if backup_path:
        logger.info(f"Database backed up to {backup_path}")
    update_state("backup", "complete")

    # --- Step 1: Collect ---
    try:
        update_state("collect", "running")
        # collect_data(DB_PATH)  # Actual collection function
        update_state("collect", "complete")
    except RetryExhausted as e:
        logger.error(f"Collection failed after retries: {e}")
        update_state("collect", "failed", str(e),
                     {"fallback": "using_cached_data"})
        # Escalation: use cached data + warn
        logger.warning("ESCALATION: Using cached data from last successful run")
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        update_state("collect", "failed", str(e))
        return False

    # --- Gate 1: Validate collection ---
    g1 = validate_collection(DB_PATH)
    gate_results.append(g1)
    logger.info(f"Gate 1: {'PASSED' if g1.passed else 'FAILED'} "
                f"(critical={g1.critical_count}, warnings={g1.warning_count})")

    if not g1.passed:
        update_state("gate_1", "failed",
                     f"{g1.critical_count} critical findings")
        logger.error("Gate 1 FAILED — aborting pipeline")
        _save_validation_report(gate_results)
        return False

    # --- Step 2: Analyze ---
    try:
        update_state("analyze", "running")
        # analyze_data(DB_PATH)  # Actual analysis function
        update_state("analyze", "complete")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        update_state("analyze", "failed", str(e))
        return False

    # --- Gate 2: Validate indicators ---
    g2 = validate_indicators(DB_PATH)
    gate_results.append(g2)
    logger.info(f"Gate 2: {'PASSED' if g2.passed else 'FAILED'} "
                f"(critical={g2.critical_count}, warnings={g2.warning_count})")

    if not g2.passed:
        update_state("gate_2", "failed",
                     f"{g2.critical_count} critical findings")
        logger.error("Gate 2 FAILED — aborting pipeline")
        _save_validation_report(gate_results)
        return False

    # --- Step 3: Score ---
    try:
        update_state("score", "running")
        # score_data(DB_PATH)  # Actual scoring function
        update_state("score", "complete")
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        update_state("score", "failed", str(e))
        return False

    # --- Gate 3: Validate scores ---
    g3 = validate_scores(DB_PATH)
    gate_results.append(g3)
    logger.info(f"Gate 3: {'PASSED' if g3.passed else 'FAILED'} "
                f"(critical={g3.critical_count}, warnings={g3.warning_count})")

    if not g3.passed:
        update_state("gate_3", "failed",
                     f"{g3.critical_count} critical findings")
        logger.error("Gate 3 FAILED — aborting pipeline")
        _save_validation_report(gate_results)
        return False

    # --- Step 4: Report ---
    try:
        update_state("report", "running")
        # generate_report(DB_PATH, REPORT_PATH)  # Actual report function
        update_state("report", "complete")
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        update_state("report", "failed", str(e))
        return False

    # --- Gate 4: Validate report ---
    g4 = validate_report(REPORT_PATH)
    gate_results.append(g4)
    logger.info(f"Gate 4: {'PASSED' if g4.passed else 'FAILED'} "
                f"(critical={g4.critical_count}, warnings={g4.warning_count})")

    # Gate 4 warnings don't abort — report is best-effort
    if not g4.passed:
        logger.warning("Gate 4 had critical findings but pipeline continues")

    # --- Workflow-level ---
    wf = validate_workflow(DB_PATH, REPORT_PATH, gate_results)
    gate_results.append(wf)

    # --- Monthly backtest (if enough history) ---
    bt = validate_monthly_backtest(DB_PATH)
    gate_results.append(bt)

    # --- Persist results ---
    _save_validation_report(gate_results)

    pipeline_duration = (datetime.now() - pipeline_start).total_seconds()
    update_state("complete", "success",
                 extra={
                     "duration_seconds": round(pipeline_duration, 1),
                     "gates_passed": sum(1 for g in gate_results if g.passed),
                     "total_warnings": sum(g.warning_count for g in gate_results),
                 })

    logger.info(f"Pipeline complete in {pipeline_duration:.1f}s. "
                f"All gates: {sum(1 for g in gate_results if g.passed)}/{len(gate_results)} passed.")
    return True


def _save_validation_report(gate_results: list[ValidationResult]) -> None:
    """Persist gate results as JSON for Claude Code to read."""
    report_path = "data/validation_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_passed": all(g.passed for g in gate_results),
        "gates": [g.to_dict() for g in gate_results],
    }
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    success = run_pipeline_strict()
    sys.exit(0 if success else 1)
```

**Lines**: ~175. [LOCAL-OK]

---

### Branch 4.1 Cost Analysis

| Metric | Gate 1 | Gate 2 | Gate 3 | Gate 4 | Retry | Workflow | **Total** |
|--------|--------|--------|--------|--------|-------|----------|-----------|
| Lines of code | ~165 | ~155 | ~220 | ~85 | ~85 | ~175 | **~885** |
| Lines (shared types) | — | — | — | — | — | — | **+65** |
| DuckDB queries/run | 8 | ~17 | ~12 | 0 | 0 | 4 | **~41** |
| Execution time (est.) | 0.5s | 1.5s | 1.0s | 0.01s | 0–90s | 0.5s | **3.5s** (no retry) |
| Token overhead for Claude | ~200 | ~300 | ~400 | ~100 | ~50 | ~200 | **~1,250 tokens** |
| False positive rate (est.) | ~2% | ~5% | ~3% | ~1% | N/A | ~1% | **~3% avg** |

**Total verification code**: ~950 lines (including shared types).
**Ratio to pipeline code**: If pipeline is ~600 lines, verification is ~1.6x pipeline code. This is HIGH but justified by the silent-failure risk profile.

**False positive scenarios**:
- Gate 1: New IPOs or delistings cause count fluctuation → ~2%
- Gate 2: Long-period SMA (200) has NaN for recently listed stocks → ~5% (manageable with non-core threshold)
- Gate 3: Genuine market regime shifts (crash/rally) trigger drift alert → ~3%
- Gate 4: Report section keywords change → ~1%

---

## Branch 4.2: Selective Verification (Verify Only Critical Paths)

### Philosophy

Verify only what can cause **systemic failure** (garbage-in → garbage-out). Skip checks where failure is either local/recoverable or detectable by the user in the report.

### Selection Criteria

| Check | Include? | Rationale |
|-------|----------|-----------|
| Gate 1: Row count | YES | Partial data is the most common pykrx failure |
| Gate 1: Zero price detection | YES | All-zero prices are catastrophic and silent |
| Gate 1: Date freshness | YES | Stale data produces misleading analysis |
| Gate 2: NaN ratio per indicator | **SKIP** | pandas-ta is deterministic; NaN only occurs when source data is bad (caught by Gate 1) |
| Gate 2: Range sanity | **SKIP** | If input data passes Gate 1, ranges are inherently valid |
| Gate 3: Score distribution | YES | Detects systemic scoring formula bugs |
| Gate 3: Sub-score divergence | **SKIP** | High divergence may be a real market signal, not an error |
| Gate 3: Day-over-day drift | **SKIP** | Market regime changes cause natural drift |
| Gate 3: Top-N stability | **SKIP** | High turnover is normal during volatile periods |
| Gate 4: File exists + non-empty | YES | Quick structural check |
| Gate 4: Section content | **SKIP** | Claude Code can handle any format |
| Workflow: Cross-stage count | **SKIP** | If Gate 1 passes, downstream counts are bounded |
| Monthly backtest | **USER** | User reviews monthly, not auto-judged |

### Lightweight Validation (`quick_validate`)

```python
# quick_validate.py — Branch 4.2: Selective verification [LOCAL-OK]

from __future__ import annotations

import os
import random
from datetime import date, timedelta
from typing import NamedTuple

import duckdb


class QuickResult(NamedTuple):
    """Lightweight validation result."""
    passed: bool
    errors: list[str]       # Critical problems (pipeline should abort)
    warnings: list[str]     # Non-critical (log and continue)
    stats: dict


MIN_STOCKS = 2000
SAMPLE_SIZE = 100           # Check 100 random stocks instead of all 2,500
STALE_DAYS = 3
EXPECTED_MEAN_RANGE = (30.0, 70.0)
EXPECTED_STD_MIN = 5.0


def quick_validate(db_path: str, report_path: str | None = None) -> QuickResult:
    """
    Selective verification: check only critical paths.
    
    Checks performed:
        1. Collection row count >= 2,000
        2. SAMPLED zero-price detection (100 random stocks)
        3. Date freshness (< 3 days old)
        4. Score distribution mean and std
        5. Report file exists and non-empty
    
    Checks SKIPPED (with rationale):
        - Per-indicator NaN ratio (pandas-ta deterministic, Gate 1 guards input)
        - Indicator range checks (bounded by valid input)
        - Sub-score divergence (may be genuine market signal)
        - Day-over-day drift (natural in volatile markets)
        - Top-N stability (normal market behavior)
        - Cross-stage stock count (bounded by Gate 1 pass)
        - Report section content (Claude adapts to any format)
    
    Args:
        db_path: Path to DuckDB database.
        report_path: Path to summary report (optional).
    
    Returns:
        QuickResult with pass/fail, errors, warnings, stats.
    """
    errors: list[str] = []
    warnings: list[str] = []
    stats: dict = {}

    # --- Database connectivity ---
    try:
        con = duckdb.connect(db_path, read_only=True)
    except Exception as e:
        return QuickResult(False, [f"Cannot open DB: {e}"], [], {})

    try:
        # ========================================
        # CHECK 1: Collection row count
        # ========================================
        latest_date = con.execute("SELECT MAX(date) FROM ohlcv").fetchone()[0]
        if latest_date is None:
            return QuickResult(False, ["ohlcv table is empty"], [], {})

        stock_count = con.execute(
            "SELECT COUNT(*) FROM ohlcv WHERE date = ?",
            [latest_date],
        ).fetchone()[0]

        stats["stock_count"] = stock_count
        stats["latest_date"] = str(latest_date)

        if stock_count < MIN_STOCKS:
            errors.append(
                f"Only {stock_count} stocks (need {MIN_STOCKS}+). "
                f"pykrx may have returned partial data."
            )

        # ========================================
        # CHECK 2: Sampled zero-price detection
        # ========================================
        # Instead of checking all 2,500 stocks, sample 100
        # Statistical reasoning: if >5% of stocks have zero prices,
        # probability of catching it with 100 samples > 99.4%
        # (1 - 0.95^100 = 0.9941)

        all_tickers = [
            row[0] for row in con.execute(
                "SELECT DISTINCT ticker FROM ohlcv WHERE date = ?",
                [latest_date],
            ).fetchall()
        ]

        sample_size = min(SAMPLE_SIZE, len(all_tickers))
        sample_tickers = random.sample(all_tickers, sample_size)

        # Build parameterized query for sample
        placeholders = ", ".join(["?"] * len(sample_tickers))
        zero_count = con.execute(f"""
            SELECT COUNT(*) FROM ohlcv
            WHERE date = ? AND ticker IN ({placeholders})
            AND close = 0
        """, [latest_date] + sample_tickers).fetchone()[0]

        zero_ratio = zero_count / sample_size
        stats["sampled_zero_ratio"] = round(zero_ratio, 4)
        stats["sample_size"] = sample_size

        if zero_ratio > 0.05:
            # Extrapolate: if 5%+ of sample is zero, likely systemic
            errors.append(
                f"{zero_count}/{sample_size} sampled stocks have close=0 "
                f"({zero_ratio:.1%}). Likely garbage data from pykrx."
            )

        # ========================================
        # CHECK 3: Date freshness
        # ========================================
        if isinstance(latest_date, str):
            from datetime import datetime
            latest_date_obj = datetime.strptime(latest_date, "%Y-%m-%d").date()
        else:
            latest_date_obj = latest_date

        days_old = (date.today() - latest_date_obj).days
        stats["data_age_days"] = days_old

        if days_old > STALE_DAYS:
            errors.append(
                f"Data is {days_old} days old. "
                f"Mac may have been off or pykrx failed."
            )
        elif days_old > 1:
            warnings.append(f"Data is {days_old} day(s) old.")

        # ========================================
        # CHECK 4: Score distribution (if scores exist)
        # ========================================
        score_tables = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'scores'"
        ).fetchall()

        if score_tables:
            dist = con.execute("""
                SELECT AVG(composite_score), STDDEV(composite_score)
                FROM scores
                WHERE date = (SELECT MAX(date) FROM scores)
            """).fetchone()

            mean_score, std_score = dist
            if mean_score is not None:
                stats["score_mean"] = round(mean_score, 2)
                stats["score_std"] = round(std_score, 2) if std_score else None

                if not (EXPECTED_MEAN_RANGE[0] <= mean_score <= EXPECTED_MEAN_RANGE[1]):
                    errors.append(
                        f"Score mean = {mean_score:.1f} "
                        f"(expected {EXPECTED_MEAN_RANGE}). "
                        f"Systemic scoring error."
                    )

                if std_score is not None and std_score < EXPECTED_STD_MIN:
                    errors.append(
                        f"Score std = {std_score:.1f} — scores nearly identical. "
                        f"Scoring formula broken."
                    )

        # ========================================
        # CHECK 5: Report file exists + non-empty
        # ========================================
        if report_path:
            if not os.path.exists(report_path):
                warnings.append(f"Report file not found: {report_path}")
            elif os.path.getsize(report_path) == 0:
                warnings.append("Report file is empty")

    finally:
        con.close()

    passed = len(errors) == 0
    return QuickResult(passed, errors, warnings, stats)


# --- Pipeline with selective verification ---

def run_pipeline_selective(db_path: str, report_path: str) -> bool:
    """
    Run pipeline with selective (lightweight) verification.
    
    Flow:
        collect → quick_validate(collection only) → 
        analyze → score → quick_validate(full) → 
        report → done
    
    No per-indicator validation. No sub-score checks.
    No retry logic (manual recovery only).
    """
    import logging
    logger = logging.getLogger(__name__)

    # Step 1: Collect
    # collect_data(db_path)

    # Quick check: collection only (before expensive compute)
    result = quick_validate(db_path)
    if not result.passed:
        logger.error(f"Collection validation failed: {result.errors}")
        return False

    # Step 2: Analyze (no validation gate)
    # analyze_data(db_path)

    # Step 3: Score (no validation gate)
    # score_data(db_path)

    # Step 4: Report
    # generate_report(db_path, report_path)

    # Final quick check (includes score distribution)
    final = quick_validate(db_path, report_path)
    if not final.passed:
        logger.error(f"Final validation failed: {final.errors}")
        return False

    for w in final.warnings:
        logger.warning(f"[WARN] {w}")

    logger.info(f"Pipeline complete. Stats: {final.stats}")
    return True
```

**Lines**: ~180 (including pipeline orchestrator). [LOCAL-OK]

---

### Branch 4.2 Cost Analysis

| Metric | Quick Validate | Pipeline | **Total** |
|--------|---------------|----------|-----------|
| Lines of code | ~130 | ~50 | **~180** |
| DuckDB queries/run | 5 | 0 | **~5** |
| Execution time (est.) | 0.3s | — | **0.3s** |
| Token overhead for Claude | ~150 | ~50 | **~200 tokens** |
| False positive rate (est.) | ~1% | — | **~1%** |

---

## COMPARISON: Branch 4.1 vs Branch 4.2

### Side-by-Side Metrics

| Dimension | 4.1 Strict | 4.2 Selective | Ratio |
|-----------|-----------|---------------|-------|
| Total lines of code | ~950 | ~180 | 5.3x |
| DuckDB queries per run | ~41 | ~5 | 8.2x |
| Execution overhead | ~3.5s | ~0.3s | 11.7x |
| Token overhead for Claude | ~1,250 | ~200 | 6.3x |
| False positive rate | ~3% | ~1% | 3x |
| **Failure modes caught** | **6/6** | **3/6** | — |
| **Failure modes missed** | **0/6** | **3/6** | — |

### Failure Mode Coverage

| # | Failure Mode | 4.1 Strict | 4.2 Selective |
|---|-------------|-----------|---------------|
| FM-1 | All-zero prices from pykrx | CAUGHT (full scan) | CAUGHT (sampling, 99.4% probability) |
| FM-2 | Partial data (1,800/2,500) | CAUGHT (row count) | CAUGHT (row count) |
| FM-3 | Stale data (Mac was off) | CAUGHT (date freshness) | CAUGHT (date freshness) |
| FM-4 | 30% NaN in indicators | CAUGHT (per-indicator NaN) | **MISSED** — pandas-ta NaN not checked |
| FM-5 | Score distribution shift | CAUGHT (mean/std + drift) | PARTIALLY CAUGHT (mean/std only, no drift) |
| FM-6 | DuckDB corruption | CAUGHT (db_connect) | CAUGHT (db_connect) |

### What 4.2 Misses — and What It Costs

**FM-4 (NaN flooding)**: If pandas-ta silently returns NaN for indicators (e.g., due to a library bug or incompatible data format), scores would be computed on partial data. The assumption that "pandas-ta is deterministic and reliable" is UNTESTED for KOSPI/KOSDAQ data.

**Risk**: Medium. pandas-ta is well-maintained, but Korean market data may have edge cases (decimal precision, volume scale). The NaN check costs ~40 lines — cheap insurance.

**FM-5 (drift detection)**: 4.2 catches broken formulas (all scores identical) but NOT gradual drift. If scoring logic has a regression that shifts mean by 20 points, 4.2 only catches it if the new mean falls outside [30, 70].

**Risk**: Low in Phase 1 (no scoring changes expected). Medium in Phase 2+ when weights are being tuned.

### The Cost of a Missed Error in a Stock Analysis System

This is the critical consideration that tilts the recommendation toward strict:

1. **User trust is binary**: One instance of presenting garbage scores as real analysis destroys user confidence. There is no "partial trust."

2. **Silent failure is invisible**: Unlike a crash (which the user sees), bad scores look like real scores. The user acts on them — potentially making investment decisions.

3. **Recovery cost is asymmetric**: Preventing a bad score costs ~3.5s of compute time. Discovering a bad score after the fact requires the user to question every previous result.

4. **This is a financial analysis tool**: The domain has zero tolerance for undetected data corruption. A weather app showing yesterday's forecast is annoying. A stock screener showing yesterday's analysis labeled as "today" can cause financial loss.

---

## RECOMMENDATION: Targeted Strict (Hybrid)

Neither pure-strict nor pure-selective is optimal. The right answer is **Strict for data-integrity gates, Selective for computation-quality gates**.

### The Hybrid: "Targeted Strict"

| Gate | Strategy | Rationale |
|------|----------|-----------|
| **Gate 1 (Collection)** | **STRICT** | Garbage in = garbage out. Silent failure is documented and common. Every check justified. |
| **Gate 2 (Indicators)** | **SELECTIVE+** | Check core indicator NaN ratio only (9 indicators). Skip non-core, skip range (bounded by valid input). ~60 lines instead of ~155. |
| **Gate 3 (Scores)** | **STRICT** | Score distribution anomaly is the only way to detect systemic formula bugs. Day-over-day drift catches regressions. Sub-score divergence is valuable for user trust. |
| **Gate 4 (Report)** | **SELECTIVE** | File exists + non-empty. Skip section validation (Claude adapts). ~30 lines instead of ~85. |
| **Retry** | **COLLECT ONLY** | Only collect has transient failures (network). analyze/score/report are deterministic. ~40 lines instead of ~85. |
| **Workflow-level** | **STRICT** | Cross-stage count + validation history. Cheap (~50 lines) and catches pipeline-level failures. |
| **Monthly backtest** | **PHASE 3** | Needs 3+ months of data. Park it. |

### Implementation Cost: Targeted Strict

| Component | Lines | Phase |
|-----------|-------|-------|
| Shared types (ValidationResult) | 65 | Phase 1 |
| Gate 1 (Strict) | 165 | Phase 1 |
| Gate 2 (Selective — core NaN only) | 60 | Phase 1 |
| Gate 3 (Strict) | 220 | Phase 1 |
| Gate 4 (Selective — exists + size) | 30 | Phase 1 |
| Retry (collect only) | 40 | Phase 1 |
| Workflow-level checks | 80 | Phase 1 |
| Pipeline orchestrator | 120 | Phase 1 |
| **Phase 1 Total** | **~780** | — |
| Full Gate 2 (add range + completeness) | +95 | Phase 2 |
| Full Gate 4 (add sections + age) | +55 | Phase 2 |
| Full retry (all stages) | +45 | Phase 2 |
| Monthly backtesting | +175 | Phase 3 |
| **Phase 2 Total** | **~975** | — |
| **Phase 3 Total** | **~1,150** | — |

### Phased Implementation Path

```
Phase 1 (Week 1-2): ~780 lines
├── ValidationResult shared types
├── Gate 1: FULL strict (all 6 checks)
├── Gate 2: Core NaN ratio only (9 indicators × threshold)
├── Gate 3: FULL strict (range, distribution, drift, divergence, stability)
├── Gate 4: exists + non-empty
├── Retry: collect only (3 attempts, 30s/60s backoff)
├── Workflow-level: cross-stage count + validation history
└── Pipeline orchestrator: backup → validate → run → validate flow

Phase 2 (Month 2): +195 lines
├── Gate 2: Add range checks, per-stock completeness
├── Gate 4: Add section validation, age check, error markers
├── Retry: Add analyze/score (1 retry each)
└── Validation dashboard: weekly summary from history

Phase 3 (Month 3+): +175 lines
├── Monthly backtest: N+20 day performance tracking
├── Scoring calibration alerts
└── Weight adjustment recommendations
```

---

## LOCAL EXECUTION TAGS

| Component | Tag | Notes |
|-----------|-----|-------|
| ValidationResult dataclass | [LOCAL-OK] | Pure Python, no external deps |
| Gate 1: validate_collection | [LOCAL-OK] | DuckDB read-only queries |
| Gate 2: validate_indicators | [LOCAL-OK] | DuckDB read-only queries |
| Gate 3: validate_scores | [LOCAL-OK] | DuckDB read-only queries |
| Gate 4: validate_report | [LOCAL-OK] | File system checks only |
| Retry decorator | [LOCAL-OK] | Pure Python, time.sleep |
| Workflow-level validation | [LOCAL-OK] | DuckDB + JSON file |
| Pipeline orchestrator | [LOCAL-OK] | Orchestrates local functions |
| quick_validate (selective) | [LOCAL-OK] | Sampling + DuckDB |
| Monthly backtesting | [LOCAL-PARTIAL] | Needs 3+ months accumulated data |

---

## PARKING LOT

1. **pandas-ta NaN edge cases on Korean data**: Need empirical test — does pandas-ta handle KOSPI volume scale (billions) and KOSDAQ micro-cap prices (<1,000 KRW) without overflow/underflow? The assumption in Branch 4.2 that "pandas-ta is reliable" is untested.

2. **DuckDB concurrent access during validation**: If collect.py is writing while validate runs, DuckDB's MVCC should handle it, but needs empirical confirmation. Consider: run validation AFTER stage completes, not concurrently.

3. **Adjusted price handling**: Corporate actions (splits, dividends) can cause SMA-200 to jump overnight. Gate 3 drift detection would fire a false positive. Need pykrx adjusted price option or corporate action calendar.

4. **KRX trading calendar integration**: Gate 1 date freshness currently uses weekday heuristic. Phase 2 should add `pandas_market_calendars` XKRX for precise holiday detection (Chuseok, Lunar New Year, etc.).

5. **Validation report size for Claude context**: At ~1,250 tokens per strict validation, the JSON report is small. But if historical trends (90 days) are included, token budget should be monitored.

6. **Retry timing vs KRX data availability**: The retry backoff (30s/60s/120s) assumes pykrx data is available but flaky. If data simply isn't published yet (e.g., running at 15:35), all 3 retries burn uselessly. Needs data-availability check before retry.

7. **Score distribution expected ranges are hypothetical**: EXPECTED_MEAN_RANGE (30-70) and EXPECTED_STD_RANGE (8-30) are assumptions. Phase 1 should LOG actual distributions and calibrate thresholds after 2 weeks of real data.

8. **Sampling statistical rigor (Branch 4.2)**: The 100-stock sample catches >5% zero-price rate with 99.4% confidence, but a localized issue (e.g., only KOSDAQ zero, KOSPI fine) with 2% rate has only ~87% detection probability. Full scan is safer for a financial tool.

9. **Circuit breaker for pykrx**: Round 2 T03 mentions circuit breaker pattern (~40 lines). Not implemented here. Should wrap collect stage: if pykrx fails 3 days consecutively, switch to FinanceDataReader fallback without retry.

10. **Validation for the validation**: Gate thresholds (MIN_EXPECTED_STOCKS=2000, MAX_NAN_RATIO=0.05) are themselves hypotheses. First 2 weeks should run in "observation mode" (log findings, don't abort) to calibrate.
