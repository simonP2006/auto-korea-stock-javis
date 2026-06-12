---
round: 3
type: raw
teammate: workflow-script-architect
axis: workflow-script-design
investigation_axis: coding-implementation
created: "2026-05-26T09:30:00+09:00"
question_summary: "Declarative vs Procedural workflow.md design for the stock analysis pipeline — concrete 4-task samples, orchestrator role analysis, complexity comparison, and hybrid recommendation"
assumption_axis: "Declarative Workflow vs Procedural Workflow"
branch_a: "Branch 1.1 — Declarative Workflow (specify WHAT, orchestrator decides HOW)"
branch_b: "Branch 1.2 — Procedural Workflow (specify WHAT + HOW + WHO + ORDER)"
web_search_count: 0
local_execution_tags:
  LOCAL_OK: ["pykrx data collection", "DuckDB storage", "pandas-ta computation", "Scoring computation", "Report generation", "Claude Code /scan", "launchd scheduling", "SOT state.yaml", "Validation gates", "FDR fallback", "Circuit breaker"]
  LOCAL_PARTIAL: []
  LOCAL_BLOCKED: []
sources:
  - "Round 1 S04 — Two Engines architecture (Engine 1: Python, Engine 2: Claude Code)"
  - "Round 2 T04 — Integration Specialist (pykrx API, DuckDB schema)"
  - "Round 2 T05 — Theory Foundation (scoring methodology, 6 sub-scores)"
  - "Round 2 S03 — Key Findings (silent failure, summary-first architecture)"
  - "AgenticWorkflow CLAUDE.md — SOT pattern, Inherited DNA"
---

# T01: Workflow Script Architect — Declarative vs Procedural

## Executive Summary

For the KOSPI/KOSDAQ stock analysis pipeline, a **hybrid approach** is recommended: procedural for pipeline stages 1-3 (collection, analysis, scoring) where every parameter IS the product specification, and declarative for stage 4 (report) and Claude Code interpretation where flexibility is an asset. Estimated workflow.md: ~350-400 lines (hybrid) vs ~150-200 (pure declarative) vs ~450-550 (pure procedural).

---

## Branch 1.1: Declarative Workflow

### 1. workflow.md Structure

The declarative approach specifies **intent, goals, and exit criteria** for each task. The orchestrator determines execution order, agent assignment, and implementation details at runtime.

#### Concrete 4-Task workflow.md Sample

```markdown
# KOSPI/KOSDAQ Technical Completeness Analysis Pipeline

## Overview
- **Input**: KRX market data (KOSPI + KOSDAQ, ~2,500 stocks)
- **Output**: `outputs/summary.md` — ranked stock list with composite scores
- **Frequency**: Daily (post-market, triggered by launchd)

## Implementation

### 1. Data Collection
- **Goal**: Obtain today's OHLCV data for all KOSPI and KOSDAQ stocks
- **Exit Criteria**:
  - [ ] DuckDB `ohlcv` table contains rows for today's date
  - [ ] Row count >= 2,000 (minimum viable stock count)
  - [ ] No stock has all-zero prices (pykrx silent failure guard)
  - [ ] Price sanity: no stock price < 0 or > 100,000,000 KRW
- **Input**: KRX market data via pykrx
- **Output**: DuckDB `ohlcv` table updated with today's data
- **On Failure**: Use most recent cached data; flag staleness in report

### 2. Technical Indicator Computation
- **Goal**: Compute all required technical indicators from OHLCV history
- **Exit Criteria**:
  - [ ] DuckDB `indicators` table populated for all stocks in `ohlcv`
  - [ ] NaN ratio < 5% for any single indicator column
  - [ ] All 6 sub-score input indicators present
- **Input**: DuckDB `ohlcv` table (historical + today)
- **Output**: DuckDB `indicators` table
- **Depends On**: Task 1 exit criteria satisfied

### 3. Composite Scoring
- **Goal**: Score each stock on 6-dimension technical completeness (0-100)
- **Exit Criteria**:
  - [ ] DuckDB `scores` table contains composite + 6 sub-scores per stock
  - [ ] Score distribution is non-degenerate (std_dev > 5)
  - [ ] No score < 0 or > 100
  - [ ] Top-80 list extractable for report
- **Input**: DuckDB `indicators` table
- **Output**: DuckDB `scores` table
- **Depends On**: Task 2 exit criteria satisfied

### 4. Report Generation
- **Goal**: Produce human-readable summary of top-scoring stocks
- **Exit Criteria**:
  - [ ] `outputs/summary.md` exists and >= 500 bytes
  - [ ] Contains top-N stock table with composite + 6 sub-scores
  - [ ] Contains data freshness timestamp
  - [ ] Contains market regime indicator
- **Input**: DuckDB `scores` table
- **Output**: `outputs/summary.md`
- **Depends On**: Task 3 exit criteria satisfied
```

[LOCAL-OK] — All execution is local Python + DuckDB.

#### Dependency Expression

Dependencies are implicit through `Depends On` field — only which task's exit criteria must be satisfied. The orchestrator infers execution order from dependency declarations.

#### Completion Criteria Expression

Each task has an `Exit Criteria` checklist with specific, measurable, machine-verifiable boolean predicates.

### 2. Orchestrator Agent Role

**What the orchestrator figures out on its own:**
- Execution order from dependency graph (trivially linear: 1→2→3→4)
- Agent assignment (all 4 tasks are Python scripts, not AI agents)
- Failure recovery interpretation (which fallback to apply)
- Gate validation (running checks against exit criteria)

**What goes into CLAUDE.md:**
- This is a deterministic Python pipeline (Engine 1), not AI agent tasks
- Scoring methodology reference (skill: stock-scanner/SKILL.md)
- Data freshness protocol (SessionStart hook)
- Interpretation role: Claude reads summary.md, produces Korean analysis

**Autonomy level**: HIGH — full discretion on HOW, constrained only on WHAT must be true.

### 3. Implementation Complexity Analysis

| Dimension | Rating | Rationale |
|-----------|--------|-----------|
| Writing difficulty | **LOW** | 4 tasks with clear exit criteria |
| Orchestrator setup | **HIGH** | Must parse goals, map to scripts, implement all validation logic |
| Unexpected behavior risk | **MED** | Orchestrator might interpret exit criteria differently than intended |
| Debugging difficulty | **HIGH** | Must reconstruct orchestrator's decision chain from logs |

---

## Branch 1.2: Procedural Workflow

### 1. workflow.md Structure

The procedural approach specifies **WHAT + HOW + WHO + ORDER** — a complete execution recipe.

#### Concrete 4-Task workflow.md Sample (abbreviated — key structure)

```markdown
# KOSPI/KOSDAQ Technical Completeness Analysis Pipeline

## Implementation

### 1. Data Collection
- **Executor**: `python3 src/collect.py --date $(date +%Y%m%d)`
- **Verification**:
  - [ ] Gate 1a: `SELECT COUNT(*) FROM ohlcv WHERE date = today()` >= 2000
  - [ ] Gate 1b: `SELECT COUNT(*) FROM ohlcv WHERE date = today() AND close = 0` == 0
  - [ ] Gate 1c: `SELECT MAX(close) FROM ohlcv WHERE date = today()` < 100000000
  - [ ] Gate 1d: `SELECT MIN(close) FROM ohlcv WHERE date = today() WHERE close > 0` > 0
- **Task**: Execute `collect.py` which:
  1. Calls `pykrx.stock.get_market_ohlcv_by_ticker(today)` for KOSPI
  2. Calls `pykrx.stock.get_market_ohlcv_by_ticker(today)` for KOSDAQ
  3. Merges DataFrames, validates dtypes
  4. `INSERT OR REPLACE INTO ohlcv` via DuckDB
  5. Runs Gate 1a-1d; raises `CollectionError` on failure
- **Post-processing**: `python3 src/validate_collection.py`
- **On Failure (Circuit Breaker)**:
  ```
  IF pykrx raises ConnectionError OR Timeout:
    attempt += 1
    IF attempt <= 3: sleep(30 * attempt), RETRY
    ELSE:
      SET circuit_breaker = OPEN
      FALLBACK: use most recent cached date
      FLAG: "STALE DATA WARNING"
  IF Gate 1a fails (< 2000 rows):
    FALLBACK to FinanceDataReader
    Re-run Gates; IF still fails: use cache
  ```
- **SOT Update**:
  ```yaml
  state.yaml:
    current_step: 1 → 2
    outputs.step-1: "data/stocks.duckdb:ohlcv"
    pipeline.collection_date: "2026-05-26"
    pipeline.row_count: 2487
    pipeline.data_source: "pykrx"
  ```

### 2. Technical Indicator Computation
- **Executor**: `python3 src/analyze.py`
- **Depends On**: Task 1 (current_step >= 2 in SOT)
- **Pre-processing**: `python3 src/prepare_history.py`
  - Ensures 200+ trading days per stock for SMA-200
  - Stocks with < 200 days → excluded, logged
- **Task**: Execute `analyze.py` which:
  1. Reads eligible tickers
  2. For each: queries DuckDB for 200-day OHLCV
  3. Computes via pandas-ta:
     - `ta.sma(close, length=20)`, `ta.sma(close, length=50)`,
       `ta.sma(close, length=150)`, `ta.sma(close, length=200)`
     - `ta.ema(close, length=21)`
     - `ta.bbands(close, length=20, std=2)` → upper, lower, width
     - `ta.obv(close, volume)`, `ta.rsi(close, length=14)`
     - `ta.macd(close, fast=12, slow=26, signal=9)`
     - `ta.adx(high, low, close, length=14)`
     - `ta.sma(volume, length=50)`
  4. Stores in DuckDB `indicators` table (UPSERT)
- **Verification**: Gate 2a-2d (row match, NaN ratio, range sanity, column completeness)

### 3. Composite Scoring
- **Executor**: `python3 src/score.py`
- **Task**: Execute `score.py` which:
  1. Reads `indicators` from DuckDB
  2. Computes 6 sub-scores:
     - MA Alignment (0.20): Minervini SEPA 8 criteria → boolean sum × 12.5
     - Base Formation (0.20): Weinstein 4 stages via SMA slope + price position
     - Volume Behavior (0.20): Wyckoff 3 indicators (OBV + volume ratio + contraction)
     - Momentum (0.15): RSI(14) + MACD + ADX(14) composite
     - Breakout Readiness (0.15): BBand squeeze + volume decline proxy
     - Relative Strength (0.10): IBD RS Rating weighted returns
  3. `composite = 0.20*ma + 0.20*base + 0.20*vol + 0.15*mom + 0.15*brk + 0.10*rs`
  4. Stores in DuckDB `scores` (UPSERT)
- **Verification**: Gate 3a-3e (row match, distribution stats, range, anomaly count, sub-score presence)
- **Post-processing**: `python3 src/detect_anomalies.py`
  - Day-over-day mean shift > 10 → flag market regime change

### 4. Report Generation
- **Executor**: `python3 src/report.py`
- **Task**: Generate Markdown with sections:
  - Data Freshness, Market Regime, Top Stocks (top 20 detailed, top 80 compact),
    Score Distribution, Sub-Score Leaders
- **Verification**: Gate 4a-4e (file exists, >=500 bytes, required sections, ticker validity)
```

[LOCAL-OK] — Every component runs locally.

### 2. Execution Control Precision

- **No fork points** in this sequential pipeline (collect→analyze→score→report)
- Conditional branches encoded in `On Failure` blocks with exact IF/ELSE logic
- **Agent teams not used**: all 4 tasks are deterministic Python (Engine 1). Claude Code role begins only at `/scan` time.

### 3. Implementation Complexity Analysis

| Dimension | Rating | Rationale |
|-----------|--------|-----------|
| Writing difficulty | **HIGH** | Requires complete knowledge of pykrx API, DuckDB SQL, pandas-ta signatures, scoring formulas |
| Maintenance burden | **HIGH** | workflow.md becomes second source of truth alongside Python source |
| Execution predictability | **HIGH** (positive) | Orchestrator executes exactly what is written |
| Debugging difficulty | **LOW** (easy) | Every step, gate, and failure branch is specified |

---

## COMPARISON: Branch 1.1 vs 1.2

### Per-Stage Suitability

| Pipeline Stage | Better Approach | Rationale |
|---------------|----------------|-----------|
| **Data Collection** | **Procedural** | 5+ distinct failure modes, each requires different response (retry/fallback/cache). Declarative collapses them into one generic statement. |
| **Indicator Computation** | **Procedural** | `ta.bbands(close, length=20, std=2)` is not a detail — it IS the specification. |
| **Composite Scoring** | **Procedural** | Weights (20/20/20/15/15/10), Minervini 8 criteria, VCP proxy — these are product requirements, not implementation details. |
| **Report Generation** | **Declarative** | Report structure can be adequately specified by exit criteria. Formatting flexibility is an asset. |

### Hybrid Recommendation

**Proposed hybrid structure:**
- Stages 1-3: PROCEDURAL (exact scripts, params, gates, failure branches)
- Stage 4 + Claude Code interpretation: DECLARATIVE (exit criteria + flexible execution)

This aligns with "Two Engines, One Product": Engine 1 (Python) needs procedural precision; Engine 2 (Claude Code) needs declarative flexibility.

### Estimated workflow.md Lines

| Approach | Lines | Breakdown |
|----------|-------|-----------|
| Declarative | ~150-200 | 4 tasks × ~20 lines + config (~50) + DNA (~30) + error (~20) |
| Procedural | ~450-550 | 4 tasks × ~80 lines + config (~80) + DNA (~30) + error (~40) |
| **Hybrid** | **~350-400** | Tasks 1-3 procedural (~70 ea = 210) + Task 4 declarative (~25) + config (~80) + DNA (~30) + error (~40) |

### Can They Be Mixed?

**Yes — this is the recommended approach.** The stock pipeline has a clear boundary: stages 1-3 are Engine 1 (deterministic Python, every parameter matters); stage 4 and Claude Code interpretation are Engine 2 (intelligent, adaptive, flexibility is an asset).

### Decision Matrix

| Criterion | Declarative | Procedural | Hybrid |
|-----------|------------|------------|--------|
| Writing effort | LOW | HIGH | MED |
| Orchestrator setup | HIGH | LOW | MED |
| Execution predictability | MED | HIGH | HIGH |
| Debugging | HARD | EASY | EASY (1-3), MED (4) |
| Maintenance burden | LOW | HIGH | MED |
| **For this system** | NO | YES (over-constrains reporting) | **BEST** |

---

## LOCAL EXECUTION TAGGING

All components: [LOCAL-OK]. No [LOCAL-PARTIAL] or [LOCAL-BLOCKED] items.

| Component | Tag |
|-----------|-----|
| pykrx data collection | [LOCAL-OK] |
| DuckDB storage | [LOCAL-OK] |
| pandas-ta computation | [LOCAL-OK] |
| Scoring computation | [LOCAL-OK] |
| Report generation | [LOCAL-OK] |
| Claude Code /scan | [LOCAL-OK] |
| launchd scheduling | [LOCAL-OK] |
| SOT state.yaml | [LOCAL-OK] |
| Validation gates | [LOCAL-OK] |
| FDR fallback | [LOCAL-OK] |
| Circuit breaker | [LOCAL-OK] |

---

## PARKING LOT

1. **SOT Schema for Pipeline Metadata**: Procedural workflow introduces `pipeline` section in `state.yaml` not in standard AgenticWorkflow template. Configuration Architect team to decide: extend standard schema or separate file?

2. **Validation Gate Scripts as Shared Library**: Both approaches require validation scripts sharing common patterns (DuckDB connection, threshold checking, JSON logging). `src/gates/` shared module recommended.

3. **workflow.md as Specification vs Documentation**: If both workflow.md and Python source exist, which is authoritative? CCP needs ruling: is changing `score.py` without updating workflow.md a CCP violation?

4. **pykrx Data Availability Timing**: launchd schedule uses 18:00 KST. Actual earliest pykrx data availability is unverified (round-02 parking lot item #1).

5. **Scoring Formula Version Control**: Parameters embedded in workflow.md AND score.py. A `scoring_config.yaml` referencing both would be the SOT for scoring parameters.

6. **Circuit Breaker State Persistence**: Circuit breaker needs state across pipeline runs. Options: extend `state.yaml` or separate `circuit_state.json`.

7. **DNA Inheritance Tension**: Stock pipeline is a single-phase Implementation workflow, not 3-phase (Research→Planning→Implementation). Clarification needed on whether pure-Implementation workflows are valid in AgenticWorkflow genome.

8. **Korean Localization Boundary**: report.py generates English summary.md, Claude provides Korean interpretation. Alternative: report.py could produce Korean directly via templates.
