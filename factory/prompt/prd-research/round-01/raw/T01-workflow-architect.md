---
round: 1
type: raw
teammate: workflow-architect
axis: workflow-architecture
created: "2026-05-25T23:05:00+09:00"
question_summary: "KOSPI/KOSDAQ 2,500종목 기술적 완성도 분석 시스템의 파이프라인 실행 구조, 설정 아키텍처, 멀티에이전트 실행, 데이터 파이프라인 설계"
assumption_axis: "Claude Code standalone vs external tool integration"
branch_a: "Self-Contained (Claude Code 단독 완결)"
branch_b: "Integrated (외부 도구 연동 전제)"
web_search_count: 22
sources:
  - "Claude Code Hooks Guide (code.claude.com)"
  - "Claude Code Agent Teams documentation"
  - "Claude Code Scheduled Tasks / Desktop Scheduled Tasks"
  - "Claude Code Headless Mode documentation"
  - "Claude Code Sub-Agents Guide (aibuilderclub.com)"
  - "Claude Code Agent Teams Deep Dive (mindstudio.ai)"
  - "Addy Osmani: Claude Code Swarms"
  - "Claude Context Windows documentation"
  - "pykrx GitHub (sharebook-kr/pykrx)"
  - "FinanceDataReader GitHub"
  - "pykrx-mcp GitHub (sharebook-kr/pykrx-mcp)"
  - "PatternPy GitHub"
  - "DuckDB vs SQLite Comparison (analyticsvidhya.com)"
  - "Embedded Databases in 2026 (kestra.io)"
  - "macOS launchd scheduling guide"
  - "Claude Code Routines 2026"
  - "Claude Code Batch Processing Guide"
  - "Python Technical Analysis with TA-Lib (tradermade.com)"
  - "pandas-ta-classic GitHub"
  - "Flat Base Pattern (TraderLion)"
  - "Claude Code Schedule vs Loop vs Cron"
---

# Workflow Architect Investigation Report

## Executive Summary

This report investigates two opposing architectural branches for building a local stock screening system on Claude Code: **Branch A (Self-Contained)** assumes Claude Code alone is sufficient; **Branch B (Integrated)** assumes external tool integration is necessary. The investigation is grounded in evidence from current Claude Code documentation, Python financial library ecosystems, and local infrastructure capabilities on macOS.

---

## Branch A: Self-Contained (Claude Code Standalone)

### A1. Pipeline Execution Structure

**Basic Execution Unit**: In a self-contained architecture, the execution unit is a **Claude Code session** (interactive or headless). Each session can invoke sub-agents (isolated contexts), agent teams (parallel independent sessions), and hooks (deterministic shell scripts). The workflow.md file serves as the execution blueprint, with a state.yaml SOT tracking progress.

**How branching, iteration, and failure recovery work**:

- **Branching**: Implemented via Claude's conditional reasoning within the session. The Orchestrator reads SOT state, evaluates conditions, and routes to different sub-agents or workflow paths. Hook-based branching uses exit codes (0 = pass, 2 = block) for deterministic gates.

- **Iteration**: Claude Code has no native loop construct for workflow steps. Iteration must be implemented either: (a) via the Orchestrator re-invoking the same sub-agent with updated parameters, (b) via `/loop` for session-scoped polling (expires after 7 days, up to 3 days by default), or (c) via Python scripts called through the Bash tool that handle iteration internally.

- **Failure Recovery**: The existing AgenticWorkflow framework provides robust retry patterns: up to 3 attempts with feedback escalation, SOT records error state, and human escalation after max retries. Session recovery after crash/`/clear` uses the Context Preservation System (snapshots + SOT reading).

**State Storage**: Entirely file-based via the `.claude/` directory structure. The `state.yaml` SOT file tracks workflow progress, agent outputs, team states, and error conditions. Context snapshots in `.claude/context-snapshots/` preserve session continuity.

### A2. Configuration Architecture

**CLAUDE.md Strategy**: The existing project uses a hierarchical split approach:
- `CLAUDE.md` — lightweight TOC and top-level directives
- `AGENTS.md` — comprehensive methodology SOT
- `docs/protocols/` — detailed on-demand reference protocols
- `.claude/skills/workflow-generator/references/` — implementation patterns

**.claude/ Directory Design**:

| Directory | Purpose |
|-----------|---------|
| `.claude/agents/` | Sub-agent definitions (data-collector.md, technical-analyst.md, screener.md) |
| `.claude/skills/` | Reusable analysis skills (technical-indicators, pattern-recognition) |
| `.claude/commands/` | User interaction commands (/scan, /filter, /report) |
| `.claude/hooks/scripts/` | Validation and automation scripts |
| `.claude/context-snapshots/` | Runtime session persistence |
| `state.yaml` | Workflow SOT |

**Hooks Usage**:

| Hook Event | Automation |
|------------|-----------|
| `Setup --init` | Validate Python dependencies, check database file integrity |
| `PreToolUse (Bash)` | Block dangerous commands, validate script paths |
| `PostToolUse (Bash)` | Log data collection results, verify output file integrity |
| `Stop` | Save analysis progress snapshot |
| `TaskCompleted` | Validate stock screening output quality |

### A3. Multi-Agent Execution

**Context Isolation**: Claude Code sub-agents run in isolated context windows. Each sub-agent gets its own fresh 200K-1M token context, preventing pollution of the parent orchestrator's context.

**Preventing State Conflicts**: The SOT pattern (Absolute Rule 2) enforces single-writer discipline. Only the Orchestrator/Team Lead writes to `state.yaml`. Sub-agents and teammates produce output files and report back.

**Parallel Execution via Agent Teams**: Agent Teams (launched Feb 2026 with Opus 4.6) enable true parallel processing. A Team Lead could dispatch:
- `@data-collector-kospi` — collects KOSPI data
- `@data-collector-kosdaq` — collects KOSDAQ data simultaneously
- `@technical-analyzer` — processes completed data batches

Each teammate operates in a fully independent session with its own context window. Coordination happens via the shared task list and SendMessage.

### A4. Data Pipeline Within Claude Code

**Can Claude Code's Bash tool run Python scripts for data collection?** Yes. This is the primary mechanism. Claude Code's Bash tool can execute any shell command, including `python3 scripts/collect_data.py`.

**Can Claude Code manage cron-like scheduling natively?** Partially. Three options:
1. **Desktop Scheduled Tasks** (macOS): Run locally, persist across restarts, require the app to be open.
2. **`/loop` command**: Session-scoped polling, expires when terminal closes.
3. **Cloud Routines** (`/schedule`): Run on Anthropic's infrastructure. Cannot access local files or databases directly.

For daily stock data collection, **Desktop Scheduled Tasks** are the most viable native option, but they require the Claude Code Desktop app to remain open.

**How to handle 2,500+ stocks within context window limits?** Python scripts process data externally. Claude Code orchestrates but never loads raw data into its context. Instead:
1. Python scripts collect and store data to files/database
2. Python scripts compute technical indicators and scores
3. Python scripts produce a summary report (top 50 candidates with scores)
4. Claude Code reads only the summary report
5. Claude Code provides interpretive analysis on the filtered results

### A5. Branch A Conclusion

**What is achievable with Claude Code alone:**
- Full workflow orchestration (Research -> Planning -> Implementation)
- Sub-agent delegation for specialized tasks
- Agent Team parallel processing for KOSPI/KOSDAQ split
- Hook-based quality gates and validation
- Session persistence and recovery
- User interaction via slash commands
- Python script execution for all computational work

**Top 3 Strengths of Self-Contained Approach:**
1. **Unified orchestration surface**: All workflow logic, agent coordination, state management, and quality gates in one system
2. **Built-in context preservation**: Handles session crashes, compaction, and /clear events
3. **No external dependency management headache**: Only Python library dependencies need installation

**Where it hits walls:**
1. **Scheduling reliability**: Desktop Scheduled Tasks require the app to stay open. No native daemon-mode equivalent to launchd/cron.
2. **No native database management**: All database operations must go through Python scripts via Bash.
3. **No native data processing framework**: ALL numerical computation must be delegated to Python scripts.
4. **Rate limit and cost concerns**: Each Claude Code session consumes API credits.
5. **No file watching or event-driven triggers**: Scheduling is time-based only.

**Top 3 Must-Have Components:**
1. Python script suite for data collection, indicator calculation, and scoring
2. File-based data storage (CSV/Parquet minimum, database optional)
3. Summary report generation script that produces Claude-digestible output

---

## Branch B: Integrated (External Tool Integration)

### B1. Pipeline Execution Structure

**Composite Execution Units**: The pipeline combines Claude Code orchestration with external Python components:

```
[Claude Code Orchestrator]
    ├── [Python: Data Collector] → pykrx/FinanceDataReader → KRX API
    │       └── writes to → [DuckDB/SQLite: stock_data.db]
    ├── [Python: Technical Analyzer] → pandas-ta / ta-lib
    │       └── reads from DB → computes indicators → writes scores to DB
    ├── [Python: Stock Screener] → custom scoring logic
    │       └── reads from DB → applies filters → writes candidates to DB
    ├── [Python: Report Generator] → generates Markdown summary
    │       └── reads from DB → produces report.md
    └── [Claude Code: Interpreter] → reads report.md → provides analysis
```

**Fallback Strategy**:
- pykrx fails → Fall back to FinanceDataReader or direct KRX website scraping
- Database corrupted → Rebuild from raw CSV files
- Scheduled task fails → Retry mechanism + alert via file flag
- Claude Code session fails → Python pipeline runs independently

### B2. Integration Architecture

**Python Ecosystem:**

| Component | Primary Library | Backup | Purpose |
|-----------|----------------|--------|---------|
| Stock listing | pykrx `get_market_ticker_list()` | FinanceDataReader `StockListing('KRX')` | Get all ~2,500 tickers |
| OHLCV data | pykrx `get_market_ohlcv_by_date()` | FinanceDataReader `DataReader()` | Daily price data |
| Volume data | pykrx `get_market_trading_value_by_date()` | - | Trading value/volume |
| Technical indicators | pandas-ta (192+ indicators, pure Python) | ta-lib (faster, requires C library) | SMA, EMA, RSI, MACD, Bollinger, ADX |
| Pattern recognition | Custom Python + PatternPy | - | Base formation, breakout detection |
| Data manipulation | pandas + numpy | polars (faster) | DataFrame operations |

**pykrx vs FinanceDataReader Selection**:
- pykrx: Better for per-date market-wide queries. Actively maintained (v1.2.8). Scrapes KRX directly.
- FinanceDataReader: Better for per-ticker historical queries. Supports multiple exchanges. May have stability issues.
- **Recommendation**: Use pykrx as primary for daily batch collection, FinanceDataReader as fallback.

**Local Database: DuckDB vs SQLite**:
- DuckDB: Columnar storage (OLAP-optimized), 15-20x faster for analytical queries, vectorized batch processing, multi-threaded, 3x more compact.
- SQLite: Row-based storage (OLTP-optimized), single-threaded, mature ecosystem.
- **Recommendation: DuckDB** for this use case — workload is purely analytical.

**DuckDB Schema Design**:
```sql
CREATE TABLE stocks (
    ticker VARCHAR PRIMARY KEY, name VARCHAR,
    market VARCHAR, sector VARCHAR, listing_date DATE
);
CREATE TABLE daily_prices (
    ticker VARCHAR, date DATE,
    open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
    volume BIGINT, trading_value BIGINT,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE technical_indicators (
    ticker VARCHAR, date DATE,
    sma_20 DOUBLE, sma_50 DOUBLE, sma_200 DOUBLE,
    ema_20 DOUBLE, ema_50 DOUBLE,
    rsi_14 DOUBLE, macd DOUBLE, macd_signal DOUBLE,
    bollinger_upper DOUBLE, bollinger_lower DOUBLE,
    adx_14 DOUBLE, atr_14 DOUBLE, volume_sma_20 DOUBLE,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE completeness_scores (
    ticker VARCHAR, date DATE,
    ma_alignment_score DOUBLE, base_formation_score DOUBLE,
    volume_pattern_score DOUBLE, momentum_score DOUBLE,
    breakout_readiness DOUBLE, total_score DOUBLE,
    PRIMARY KEY (ticker, date)
);
```

**Scheduler: launchd (macOS native)**:
- Persists across reboots
- Handles sleep/wake: executes upon wake if missed
- Event-based triggers possible
- No dependency on Claude Code being open
- Runs at 18:30 daily (after KRX market close)

**Data Flow**:
```
[launchd 18:30 daily]
    └── python3 daily_collect.py
        ├── pykrx: fetch all OHLCV
        ├── DuckDB: INSERT INTO daily_prices
        ├── pandas-ta: compute indicators
        ├── DuckDB: INSERT INTO technical_indicators
        ├── custom scoring: compute completeness scores
        ├── DuckDB: INSERT INTO completeness_scores
        └── generate summary: top_candidates.md

[Claude Code session (on-demand)]
    └── Orchestrator reads top_candidates.md
        ├── Interprets scores and patterns
        ├── Generates actionable report
        └── Answers user questions
```

### B3. Complexity Management

**External Dependencies:**

| Dependency | Risk Level | Notes |
|-----------|------------|-------|
| Python 3.10+ | Low | Already present on most macOS |
| pykrx | Low | Pure Python, actively maintained |
| pandas | Low | Stable ecosystem |
| pandas-ta | Low | Pure Python, 192+ indicators |
| ta-lib | **Medium** | Requires C library compilation |
| DuckDB | Low | Embedded, no server process |

**Recommendation**: Use pandas-ta instead of ta-lib to avoid C dependency.

**Virtual Environment Strategy**: `python3 -m venv .venv` or `uv venv` with `requirements.txt` pinning.

**Configuration Portability**: All paths relative to project root, `requirements.txt` for dependencies, `setup.sh` for one-command installation.

### B4. Branch B Conclusion

**Workflow types that absolutely need external integration:**
1. Daily automated data collection — launchd required
2. Bulk numerical computation — Python/pandas/DuckDB handle this in seconds
3. Persistent structured data storage — database required for efficient querying

**Top 3 Strengths:**
1. **Separation of concerns**: Computation in Python (deterministic, fast), orchestration in Claude Code (intelligent, adaptive)
2. **Reliability through independence**: Data pipeline runs even when Claude Code is not active
3. **Scalability and performance**: DuckDB processes millions of rows in milliseconds

**Top 3 Risks:**
1. **Installation complexity**: Users must set up Python + venv + libraries + launchd
2. **Maintenance burden**: pykrx scrapes KRX website; interface changes break it
3. **Debugging difficulty**: Failures at multiple integration points

**Top 3 Must-Have Components:**
1. Python data pipeline scripts (collect, compute, score, report)
2. DuckDB database with well-designed schema
3. launchd configuration for daily automated execution

---

## Final Comparison: Branch A vs Branch B

### When Self-Contained is Right
1. Proof-of-concept / one-time analysis (not daily automated)
2. When simplicity is paramount (user types `/scan`, gets results)
3. When stock universe is small (20-50 stocks, not 2,500)

### When Integrated is Right
1. Daily automated screening of full KOSPI/KOSDAQ universe (the primary use case)
2. Historical backtesting and trend analysis
3. When reliability matters (pipeline must run independently of Claude Code)

### Capabilities Coverage Assessment

| Capability | Claude Code Native? | Coverage Level |
|-----------|---------------------|---------------|
| Workflow orchestration | Yes | 95% |
| Python script execution | Yes (Bash tool) | 90% |
| Data collection | Via Bash | 80% |
| Technical analysis computation | Via Bash | 80% |
| Database management | Via Bash | 70% |
| Scheduling (daily automation) | Partial | 40% |
| Large dataset handling | Via file delegation | 60% |
| Result presentation | Yes | 95% |

### What MUST Be Externally Integrated
1. **Python runtime and libraries** (pykrx, pandas, pandas-ta, DuckDB)
2. **Persistent scheduled execution** (launchd)
3. **Structured data storage** (DuckDB/SQLite)
4. **Technical indicator computation engine** (pandas-ta)

### Recommended Architecture: Hybrid (Branch B with Branch A Orchestration)

```
Layer 1: OS Scheduler (launchd)
Layer 2: Python Data Pipeline (scripts/)
Layer 3: Claude Code Orchestration (.claude/)
Layer 4: User Interface (Claude Code session)
```

---

## Parking Lot

| # | Discovery | Source | Follow-Up Category |
|---|-----------|--------|-------------------|
| P1 | pykrx has an official MCP server (`pykrx-mcp`) | Branch B | external-integration |
| P2 | Cloud Routines cannot access local files or databases | Branch A | structural-risk |
| P3 | Agent Teams require `EXPERIMENTAL_AGENT_TEAMS` flag — still experimental | Branch A | technical |
| P4 | Opus 4.6 and Sonnet 4.6 have 1M-token context windows | Branch A | technical |
| P5 | KRX website may implement rate limiting or CAPTCHA | Branch B | external-integration |
| P6 | "Technical completeness" has no standardized definition | Both | user-behavior |
| P7 | pandas-ta vs ta-lib performance gap for 2,500-stock computation | Branch B | technical |
| P8 | DuckDB's Parquet support could eliminate CSV intermediate files | Branch B | technical |
