---
round: 4
type: raw
teammate: data-flow-architect
axis: data-flow
investigation_axis: external-integration
created: "2026-05-26T15:00:00+09:00"
question_summary: "Data flow architecture for KOSPI/KOSDAQ stock pipeline — real-time streaming vs batch file exchange, Engine 1→2 interface design, atomic write patterns, DuckDB volume, data serialization"
assumption_axis: "Real-Time Streaming vs Batch File Exchange"
branch_a: "Branch 4.1 — Real-Time Streaming (event-driven data flow between components)"
branch_b: "Branch 4.2 — Batch File Exchange (file-based handoff between pipeline stages)"
web_search_count: 26
local_execution_tags:
  LOCAL_OK: ["DuckDB (local embedded DB)", "summary.md file handoff", "YAML frontmatter + Markdown body", "atomic write (tmp→os.replace())", "fcntl.flock() file locking", "pipeline_state.json", "launchd batch trigger", "SessionStart hook data freshness", "Python tempfile + os.replace()", "pandas DataFrame → Markdown table"]
  LOCAL_PARTIAL: ["pykrx fetch (requires KRX network)", "claude -p headless mode (experimental, GitHub #36324)"]
  LOCAL_BLOCKED: []
sources:
  - url: "https://duckdb.org/docs/current/guides/performance/schema"
    desc: "DuckDB Schema Design — columnar compression ratios"
  - url: "https://duckdb.org/docs/current/sql/concurrency"
    desc: "DuckDB Concurrency — single-writer, multiple-reader"
  - url: "https://docs.python.org/3/library/os.html#os.replace"
    desc: "Python os.replace() — atomic file rename"
  - url: "https://docs.python.org/3/library/fcntl.html"
    desc: "Python fcntl — file locking"
  - url: "https://docs.python.org/3/library/tempfile.html"
    desc: "Python tempfile — secure temporary files"
  - url: "https://yaml.org/spec/1.2.2/"
    desc: "YAML 1.2.2 Specification"
  - url: "https://github.com/sharebook-kr/pykrx"
    desc: "pykrx — DataFrame output format"
  - url: "https://duckdb.org/docs/current/guides/import/csv_import"
    desc: "DuckDB CSV/Parquet Import"
---

# T04: Data Flow Architect — Real-Time Streaming vs Batch File Exchange

## Executive Summary

**Phase 1 is 100% batch** — the data source (KRX) publishes daily, the pipeline runs once daily via launchd, and the consumer (Claude Code) reads a finished summary.md. Real-time streaming adds complexity with zero Phase 1 value. The critical design decision is the **Engine 1→2 interface**: summary.md with YAML frontmatter (machine-parseable metadata) + Markdown body (LLM-readable analysis). Atomic writes (tmp→os.replace()) are mandatory for all file handoffs.

---

## Branch 4.1: Real-Time Streaming

### Streaming Patterns Evaluated

| Pattern | Mechanism | Phase 1 Value | Verdict |
|---------|-----------|---------------|---------|
| MCP streaming | MCP server pushes tools to Claude | None — no interactive session at pipeline runtime | Skip |
| fswatch → claude -p | File change triggers headless Claude | None — daily batch, not continuous | Phase 2+ |
| stdin/stdout pipe | Python → Claude via pipe | Low — one-shot handoff sufficient | Optional |
| WebSocket / SSE | Real-time event stream | None — data source is daily batch | Skip |
| Pub/Sub (Redis, NATS) | Message queue | Overkill for single-process daily pipeline | Skip |

### When Streaming Makes Sense (Phase 2+)

1. **launchd WatchPaths**: File change triggers pipeline re-run (e.g., user edits scoring_config.yaml)
2. **SessionStart hook**: Claude Code session opens → hook reports data freshness → Claude decides whether to re-scan
3. **claude -p headless**: Automated interpretation triggered by pipeline completion
4. **Multi-stock drill-down**: User requests `/analyze TICKER` → real-time pykrx fetch + Claude interpretation

### Streaming Architecture Cost

- Event infrastructure: message broker or file watcher
- Error handling: retry, backpressure, dead letter queue
- State management: event ordering, idempotency, deduplication
- Monitoring: event lag, throughput, error rate

**Verdict**: All overhead, zero Phase 1 benefit. Data source is daily close-of-market.

---

## Branch 4.2: Batch File Exchange (★ Recommended)

### Phase 1 Data Flow: Linear Pipeline

```
launchd (16:30 KST trigger)
  └─ caffeinate -i python3 main.py
       ├─ Stage 1: Collect (pykrx → DuckDB)
       │    └─ Gate 1: zero_close_ratio, row_count, date_freshness
       ├─ Stage 2: Analyze (DuckDB → pandas-ta → DuckDB)
       │    └─ Gate 2: indicator_null_ratio, value_range checks
       ├─ Stage 3: Score (DuckDB → scoring_config.yaml → DuckDB)
       │    └─ Gate 3: score_range, distribution checks
       └─ Stage 4: Report (DuckDB → summary.md)
            └─ Gate 4: file size, section count, YAML parse
```

### Engine 1→2 Interface: summary.md Design

**Format**: YAML frontmatter (machine metadata) + Markdown body (LLM content)

```yaml
---
report_date: "2026-05-26"
market_date: "2026-05-26"
stock_count: 2487
kospi_count: 943
kosdaq_count: 1544
scoring_config_hash: "a1b2c3d4"
gates_passed: [1, 2, 3, 4]
degraded: false
degradation_reason: null
pipeline_version: "1.0.0"
generated_at: "2026-05-26T16:45:23+09:00"
---

# KOSPI/KOSDAQ Technical Completeness Report — 2026-05-26

## Market Overview
| Metric | KOSPI | KOSDAQ | Combined |
|--------|-------|--------|----------|
| Stocks Analyzed | 943 | 1,544 | 2,487 |
| Avg Total Score | 62.3 | 58.7 | 60.1 |
| Scores ≥ 80 | 47 | 31 | 78 |
...

## Top 80 by Total Score
| Rank | Ticker | Name | Total | Trend | Volume | Momentum | Volatility | Pattern | Relative |
...

## Anomaly Alerts
- ⚠️ 005930 (삼성전자): Volume spike 3.2σ above 20-day mean
...

## Sub-Score Distribution
...

## Data Quality
- Gate 1: PASS (zero_close=0.0%, stocks=2487, freshness=0d)
- Gate 2: PASS (null_ratio=0.3%)
- Gate 3: PASS (score_range=[12.5, 94.2])
- Gate 4: PASS (size=18.2KB, sections=5)
```

**Size estimate**: ~15-25KB (~5,000-8,000 tokens) — <1% of Claude's 1M context window.

### Atomic Write Pattern

All file outputs must use atomic write to prevent partial reads:

```python
import os
import tempfile

def atomic_write(path: str, content: str) -> None:
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        os.replace(tmp_path, path)  # atomic on POSIX
    except:
        os.unlink(tmp_path)
        raise
```

**Applied to**: summary.md, pipeline_state.json, circuit_breaker_state.json, all JSON state files.

**Why mandatory**: launchd may trigger next run or Claude Code may read summary.md while Engine 1 is writing. Without atomic write, reader sees truncated/corrupt data.

### DuckDB File Locking

```python
import fcntl

class PipelineLock:
    def __init__(self, lock_path: str):
        self.lock_path = lock_path
    
    def __enter__(self):
        self.fd = open(self.lock_path, 'w')
        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self
    
    def __exit__(self, *args):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        self.fd.close()
```

DuckDB is single-writer by design. `fcntl.flock()` prevents concurrent pipeline instances (e.g., launchd coalesced runs after wake).

### DuckDB Volume Projections

| Metric | Value |
|--------|-------|
| Daily new rows | ~2,500 (KOSPI+KOSDAQ) |
| Row size (OHLCV) | ~64 bytes uncompressed |
| Tables | 3 (ohlcv, indicators, scores) |
| 1 year raw | ~2.7M rows |
| 5 years raw | ~13.5M rows |
| 5 years compressed (DuckDB) | **~40-80MB** |
| Annual growth | ~50MB |
| 10 years | ~90-150MB |
| Cleanup needed? | **No** — negligible on modern Mac |

DuckDB columnar compression achieves 5-10x on OHLCV float data. ACID + WAL + fsync ensures durability.

### Data Serialization Standards

| Data Type | Format | Transport | Consumer |
|-----------|--------|-----------|----------|
| Raw OHLCV | DuckDB table (columnar) | DuckDB SQL | analyze.py |
| Technical indicators | DuckDB table (columnar) | DuckDB SQL | score.py |
| Scores + rankings | DuckDB table (columnar) | DuckDB SQL | report.py |
| Pipeline output | summary.md (YAML+MD) | File read | Claude Code |
| Pipeline state | pipeline_state.json | File read | Hooks, Claude |
| Scoring config | scoring_config.yaml | File read | 4 consumers |
| Circuit breaker | circuit_breaker_state.json | File read | Pipeline |

### Phase 2+ Data Flow Extensions

```
output/
├── summary.md              ← Phase 1 (always present, Engine 1→2 interface)
├── detail/{ticker}.md      ← Phase 2 (/analyze TICKER — per-stock deep dive)
├── archive/                ← Phase 2 (daily archival, YYYY-MM-DD/ structure)
│   └── 2026-05-26/
│       ├── summary.md
│       └── pipeline_state.json
└── market/                 ← Phase 3 (market-level segmentation)
    ├── kospi/
    └── kosdaq/
```

---

## Comparison

| Dimension | Streaming (4.1) | Batch (4.2) | Winner |
|-----------|----------------|------------|--------|
| Phase 1 fit | None | Perfect | Batch |
| Complexity | High | Low | Batch |
| Debugging | Hard (async events) | Easy (files on disk) | Batch |
| Data source match | Mismatch (daily data) | Match (daily pipeline) | Batch |
| Phase 2 extensibility | Natural for real-time | Requires add-on | Streaming |
| Reliability | Complex (backpressure) | Simple (atomic write) | Batch |

**Recommendation**: 100% batch for Phase 1. Phase 2 adds targeted streaming (WatchPaths, SessionStart hook) as thin overlay on batch foundation.

---

## Parking Lot

1. **summary.md quality badge placement**: Top of frontmatter vs top of body — affects Claude Code's first-read parsing
2. **DuckDB WAL accumulation during initial 5-year load**: May need periodic checkpoint
3. **archive/ retention policy**: Indefinite or 30/90/365 days? Disk impact minimal.
4. **detail/{ticker}.md generation latency**: Per-stock deep dive may take 5-10s with pykrx re-fetch
5. **claude -p headless data freshness**: How to pass summary.md content to headless Claude Code
6. **Multi-LLM data flow**: Gemini/Codex CLI output format standardization needed for Phase 2+
