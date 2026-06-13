---
round: 3
type: raw
teammate: agent-orchestration-coder
axis: orchestration-pattern
investigation_axis: coding-implementation
created: "2026-05-26T09:30:00+09:00"
question_summary: "Centralized vs Distributed orchestration patterns for the stock analysis pipeline — concrete pseudo-code, Claude Code native tooling, complexity analysis, and pragmatic recommendation"
assumption_axis: "Centralized Orchestrator vs Distributed Agent Swarm"
branch_a: "Branch 2.1 — Centralized Orchestration (Single orchestrator controls all flow)"
branch_b: "Branch 2.2 — Distributed Orchestration (Agent swarm with autonomous collaboration)"
web_search_count: 0
local_execution_tags:
  LOCAL_OK: ["Agent tool sub-agent spawning", "TaskCreate/TaskUpdate/TaskGet", "SendMessage inter-agent communication", "Hooks lifecycle automation", "Skills domain knowledge injection", "Commands user interface", "File-based state coordination", "DuckDB as pipeline SOT", "Sequential pipeline main.py", "launchd scheduling", "summary.md boundary", "pipeline_state.json", "config.yaml user settings"]
  LOCAL_PARTIAL: ["TeamCreate/TeamDelete (experimental, CLAUDE_AGENT_TEAMS=1 required)", "Worktree isolation (requires git repo)"]
  LOCAL_BLOCKED: []
sources:
  - "T01-platform-capability.md (Prior research — Claude Code capabilities)"
  - "T02-configuration-architect.md (Prior research — .claude/ structure)"
  - "T03-orchestration-engineer.md (Prior research — pipeline design)"
  - "T04-integration-specialist.md (Prior research — tech stack)"
  - "T05-theory-foundation.md (Prior research — agentic patterns)"
  - "S01-tech-discussion.md (Prior synthesis — tech consensus)"
  - "S03-key-findings.md (Prior synthesis — cross-cutting findings)"
  - "claude-code-patterns.md (Framework reference — Sub-agents, Agent Teams, Hooks, Tasks)"
---

# T02: Agent Orchestration Coder — Centralized vs Distributed

## Executive Summary

For a daily pipeline scanning ~2,500 KOSPI/KOSDAQ stocks with a deterministic `collect → analyze → score → report` flow, **Centralized Orchestration (Branch 2.1) is the pragmatic choice**. The pipeline is inherently sequential and deterministic — orchestration complexity adds no value. Distributed Orchestration (Branch 2.2) introduces coordination overhead disproportionate to a 4-stage pipeline with a single user. However, a **targeted hybrid** is viable: centralized for the daily pipeline, with ad-hoc distributed deep-dives on individual stocks.

---

## Branch 2.1: Centralized Orchestration

### 1. Orchestrator-SubAgent Pattern Design

#### 1.1 What the Orchestrator Does

The orchestrator is the single controller that:
1. **Reads the pipeline definition** (either from workflow.md or hardcoded pipeline stages)
2. **Parses task sequence** with dependency ordering
3. **Dispatches tasks** to sub-agents or executes directly
4. **Collects and validates results** (Anti-Skip Guard: file exists + >= 100 bytes)
5. **Manages state** in the SOT (pipeline_state.json or DuckDB `pipeline_runs` table)
6. **Makes quality judgments** (data validation gates, anomaly detection)
7. **Reports to user** in Korean via summary.md interpretation

#### 1.2 What Sub-Agents Do

Each sub-agent receives a single, well-scoped task with:
- Explicit input (file path or DuckDB query)
- Explicit expected output (file path)
- Verification criteria (row count, NaN ratio, score distribution)
- Maximum turns budget

Sub-agents return results to the orchestrator and terminate. They do NOT:
- Write to the SOT
- Communicate with other sub-agents
- Make workflow routing decisions

#### 1.3 Delegation Criteria [LOCAL-OK]

**Handled directly by orchestrator** (no sub-agent needed):
- Pipeline execution (`python3 main.py`) — deterministic, no LLM reasoning needed
- Data freshness checks — simple timestamp comparison
- SOT state updates — orchestrator-only write privilege
- User-facing summary interpretation — requires full context

**Delegated to sub-agents** (if needed at all):
- Deep analysis of individual stocks — specialist knowledge injection via Skills
- Multi-perspective interpretation — e.g., momentum view vs. value view
- Report generation for complex sector comparisons

**Critical insight from prior research (T03, S01)**: The pipeline itself (collect/analyze/score/report) is **pure Python computation**. Claude's role is **interpretation**, not computation. Therefore, most "sub-agent" work is actually `python3 script.py` via Bash tool, not LLM delegation.

#### 1.4 Concrete CLAUDE.md Snippet for the Orchestrator

```markdown
# Stock Technical Completeness Scanner — Orchestrator

## System Identity
You are the orchestrator for a KOSPI/KOSDAQ stock technical completeness analysis system.
Your role: execute the daily scan pipeline, interpret results, and communicate in Korean.

## Architecture Boundary
- **Python does ALL computation**: collect, analyze, score, report
- **You do ALL interpretation**: read summary.md, explain to user, answer questions
- **Boundary file**: output/summary.md (Python writes, you read)

## Pipeline Stages
```
launchd → python3 pipeline/main.py → output/summary.md → your interpretation
```

## Daily Scan Protocol
1. Check data freshness: `python3 pipeline/check_freshness.py`
   - If fresh (today's data exists): skip to step 4
   - If stale: proceed to step 2
2. Execute pipeline: `python3 pipeline/main.py`
   - Gate 1: stock_count >= 2300 (expect ~2500)
   - Gate 2: avg_score change < 20% vs yesterday
   - Gate 3: zero_price_count == 0
3. Verify completion: read pipeline/pipeline_state.json
   - status: "completed" → proceed
   - status: "failed" → report error in Korean, suggest retry
4. Read output/summary.md — interpret for user in Korean
5. If user asks about specific stock: `python3 pipeline/query_stock.py --code {CODE}`

## Error Communication (Korean)
- Collection failure: "오늘 데이터 수집에 실패했습니다. 어제 데이터로 분석합니다."
- Stale data: "최근 {N}일간 새 데이터가 없습니다. 결과의 신선도에 주의하세요."
- Anomaly detected: "점수 분포에 이상이 감지되었습니다: {details}"

## Constraints
- NEVER modify DuckDB directly — only Python scripts modify data
- NEVER skip data validation gates
- Token budget: ~25K per daily scan session
- Model: Sonnet for routine scans, Opus for deep analysis
```

#### 1.5 Concrete Agent Spawn Pattern Using the Agent Tool [LOCAL-OK]

```
# Scenario: User requests deep analysis of a specific stock after daily scan

## Orchestrator decides to delegate deep analysis:

Agent tool call:
  prompt: |
    Analyze stock code 005930 (Samsung Electronics) from multiple technical perspectives.
    
    Input data: Read data from DuckDB via:
      python3 pipeline/query_stock.py --code 005930 --format detailed
    
    Analysis framework (from stock-scanner skill):
    1. MA Alignment: Are moving averages in proper ascending order?
    2. Base Formation: Weinstein stage identification
    3. Volume Behavior: Wyckoff accumulation/distribution signs
    4. Momentum: RSI/MACD/ADX composite reading
    5. Breakout Readiness: BBand squeeze + volume contraction
    6. Relative Strength: Percentile rank vs all stocks
    
    Output: Write analysis to output/deep-analysis/005930.md
    Include: score breakdown, chart interpretation cues, risk factors
    Language: Korean
    
  tools: [Read, Write, Bash, Glob, Grep]
  model: opus
  maxTurns: 15
```

```
# Scenario: Parallel sector comparison (using fork pattern)

## Orchestrator spawns parallel sub-agents for independent sector views:

# Sub-agent 1: Technology sector
Agent tool call:
  prompt: |
    Analyze top-scoring stocks in the Technology sector.
    Run: python3 pipeline/query_sector.py --sector IT --top 10
    Write findings to output/sector-analysis/IT.md
  tools: [Read, Write, Bash]
  model: sonnet
  maxTurns: 10

# Sub-agent 2: Healthcare sector (can run in parallel)
Agent tool call:
  prompt: |
    Analyze top-scoring stocks in the Healthcare sector.
    Run: python3 pipeline/query_sector.py --sector Healthcare --top 10
    Write findings to output/sector-analysis/Healthcare.md
  tools: [Read, Write, Bash]
  model: sonnet
  maxTurns: 10

# Orchestrator merges after both complete:
# Read both files, synthesize cross-sector comparison
```

### 2. Task Management System Usage

#### 2.1 Task Queue Implementation [LOCAL-OK]

For the stock pipeline, the Claude Code Task system (TaskCreate/TaskUpdate/TaskGet) is **overkill for the daily pipeline** but **useful for ad-hoc deep analysis**:

**Daily pipeline** — no Task system needed:
```
# The pipeline IS the task queue. Sequential Python execution.
# pipeline_state.json tracks state. No Claude Task overhead.

python3 pipeline/main.py
# Internally: collect() → analyze() → score() → report()
# Each stage writes to DuckDB, checks gate, proceeds or fails
```

**Ad-hoc deep analysis** — Task system adds value:
```
# When user requests analysis of multiple stocks:
# "삼성전자, SK하이닉스, LG에너지솔루션 비교 분석해줘"

TaskCreate:
  subject: "Deep analysis: 005930 Samsung Electronics"
  description: "Run query_stock.py --code 005930, analyze 6 sub-scores, write to output/deep-analysis/005930.md"
  
TaskCreate:
  subject: "Deep analysis: 000660 SK Hynix"  
  description: "Run query_stock.py --code 000660, analyze 6 sub-scores, write to output/deep-analysis/000660.md"

TaskCreate:
  subject: "Deep analysis: 373220 LG Energy Solution"
  description: "Run query_stock.py --code 373220, analyze 6 sub-scores, write to output/deep-analysis/373220.md"

# Orchestrator monitors: TaskGet for each, then synthesizes comparison
```

#### 2.2 Task State Tracking [LOCAL-OK]

```python
# Pseudo-code: Orchestrator main loop for daily pipeline
# Note: This runs as Claude Code executing Bash commands,
# not as a standalone Python orchestrator.

def daily_scan_orchestration():
    """
    Orchestrator logic — executed by Claude Code's main session.
    NOT a Python daemon. Triggered by /scan command or SessionStart hook.
    """
    
    # Phase 1: Check preconditions
    freshness = bash("python3 pipeline/check_freshness.py")
    state = read_json("pipeline/pipeline_state.json")
    
    if freshness.today_data_exists and state.status == "completed":
        # Data already fresh — skip to interpretation
        summary = read_file("output/summary.md")
        return interpret_for_user(summary)  # Korean output
    
    # Phase 2: Execute pipeline with validation gates
    pipeline_stages = [
        PipelineStage(
            name="collect",
            command="python3 pipeline/collect.py",
            gate=lambda: validate_collection(),  # row_count >= 2300, zero_prices == 0
            retries=3,
            backoff=[30, 60, 120],  # seconds — pykrx network dependency
        ),
        PipelineStage(
            name="analyze", 
            command="python3 pipeline/analyze.py",
            gate=lambda: validate_analysis(),  # nan_ratio < 5%, indicator_ranges valid
            retries=1,
            backoff=[0],  # deterministic — failure = code bug
        ),
        PipelineStage(
            name="score",
            command="python3 pipeline/score.py",
            gate=lambda: validate_scores(),  # avg_score delta < 20%, distribution check
            retries=1,
            backoff=[0],
        ),
        PipelineStage(
            name="report",
            command="python3 pipeline/report.py",
            gate=lambda: file_exists_and_valid("output/summary.md"),
            retries=1,
            backoff=[0],
        ),
    ]
    
    for stage in pipeline_stages:
        for attempt in range(stage.retries):
            result = bash(stage.command)
            
            # Update pipeline_state.json
            update_state({
                "current_stage": stage.name,
                "status": "running",
                "attempt": attempt + 1,
                "last_run": now(),
            })
            
            if result.exit_code == 0 and stage.gate():
                update_state({
                    "status": "stage_completed",
                    f"{stage.name}_completed_at": now(),
                })
                break  # Gate passed — next stage
            
            if attempt < stage.retries - 1:
                sleep(stage.backoff[attempt])
                continue
            
            # All retries exhausted
            update_state({
                "status": "failed",
                "failed_stage": stage.name,
                "error": result.stderr,
            })
            
            # Graceful degradation
            if stage.name == "collect":
                # Use yesterday's data
                report_to_user("오늘 데이터 수집에 실패했습니다. 어제 데이터로 분석합니다.")
                update_state({"status": "stale_data"})
                # Continue with stale data
            else:
                report_to_user(f"파이프라인 {stage.name} 단계 실패: {result.stderr}")
                return  # Stop pipeline
    
    # Phase 3: Interpretation
    update_state({"status": "completed", "completed_at": now()})
    summary = read_file("output/summary.md")
    return interpret_for_user(summary)
```

#### 2.3 Task Dependency Resolution [LOCAL-OK]

For the daily pipeline, dependencies are trivially linear:

```
collect ──→ analyze ──→ score ──→ report
   │            │          │         │
   └ DuckDB ────┘──────────┘─────────┘
     (shared data store)
```

No complex dependency graph. Each stage reads the previous stage's DuckDB output. The orchestrator enforces ordering by sequential execution.

For ad-hoc multi-stock analysis, dependencies are also simple:
```
individual_stock_analyses (parallel, independent)
         │
         ├── 005930.md ──┐
         ├── 000660.md ──┼── comparison_synthesis (depends on all)
         └── 373220.md ──┘
```

**Pseudo-code: Task dependency tracking**
```python
def orchestrate_multi_stock_analysis(stock_codes):
    """Ad-hoc analysis with parallel sub-agents and dependency merge."""
    
    # Phase 1: Spawn independent analyses (no dependencies between them)
    tasks = {}
    for code in stock_codes:
        task_id = TaskCreate(
            subject=f"Deep analysis: {code}",
            description=f"Run query_stock.py --code {code}, write to output/deep-analysis/{code}.md",
        )
        tasks[code] = task_id
    
    # Phase 2: Poll for completion
    # (In practice, Claude Code's Agent tool handles this implicitly —
    #  each sub-agent runs to completion and returns)
    completed = {}
    for code, task_id in tasks.items():
        result = TaskGet(task_id)
        if result.status == "completed":
            completed[code] = f"output/deep-analysis/{code}.md"
    
    # Phase 3: Merge (orchestrator does this directly — no sub-agent needed)
    if len(completed) == len(stock_codes):
        synthesis = synthesize_comparison(completed)
        write_file("output/comparison.md", synthesis)
```

### 3. Fork and Agent-Teams Usage

#### 3.1 When to Use Fork (Parallel Exploration) [LOCAL-OK]

**Appropriate for this system**:
- Comparing different scoring weight configurations: "What if MA alignment gets 30% weight instead of 20%?"
- Running sector-by-sector analysis in parallel
- Generating alternative interpretations of the same data

```
# Fork example: Scoring weight sensitivity analysis
# Orchestrator spawns 3 parallel explorations

# Fork A: Default weights (20/20/20/15/15/10)
Agent tool call:
  prompt: |
    Run scoring with default weights:
    python3 pipeline/score.py --weights "20,20,20,15,15,10"
    Write top-20 list to output/sensitivity/default.md
  tools: [Bash, Write]
  model: sonnet
  maxTurns: 5

# Fork B: Momentum-heavy weights (15/15/15/25/20/10)
Agent tool call:
  prompt: |
    Run scoring with momentum-heavy weights:
    python3 pipeline/score.py --weights "15,15,15,25,20,10"
    Write top-20 list to output/sensitivity/momentum-heavy.md
  tools: [Bash, Write]
  model: sonnet
  maxTurns: 5

# Fork C: Base-heavy weights (15/25/20/15/15/10)
Agent tool call:
  prompt: |
    Run scoring with base-formation-heavy weights:
    python3 pipeline/score.py --weights "15,25,20,15,15,10"
    Write top-20 list to output/sensitivity/base-heavy.md
  tools: [Bash, Write]
  model: sonnet
  maxTurns: 5

# After all forks complete:
# Orchestrator reads all 3 files, compares overlap/divergence,
# identifies stocks that rank highly regardless of weighting (robust picks)
```

#### 3.2 When to Use Agent Teams [LOCAL-PARTIAL]

Agent Teams require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and are experimental. For this stock pipeline:

**Potentially useful** (but not for Phase 1):
- Multi-perspective stock evaluation: fundamental analyst + technical analyst + risk analyst
- Cross-validation of scoring methodology

**Not recommended for Phase 1**:
- Daily pipeline is deterministic — no need for team collaboration
- Single user — no concurrent access requirement
- Agent Teams add coordination complexity (SOT management, TeamCreate/Delete lifecycle)

```
# Agent Team example (Phase 2+): Multi-perspective deep analysis
# Only if user requests comprehensive evaluation

TeamCreate("stock-evaluation-005930")

# Teammate 1: Technical analyst
TaskCreate:
  subject: "Technical analysis: 005930"
  description: |
    As a technical analyst, evaluate Samsung Electronics:
    - Chart pattern identification (cup-and-handle, ascending triangle, etc.)
    - Support/resistance levels from DuckDB price data
    - Volume profile analysis
    Write to output/team-eval/005930-technical.md
  owner: "@technical-analyst"

# Teammate 2: Risk analyst
TaskCreate:
  subject: "Risk analysis: 005930"
  description: |
    As a risk analyst, evaluate Samsung Electronics:
    - Volatility metrics (ATR, Bollinger Band width)
    - Maximum drawdown from recent peak
    - Sector concentration risk
    Write to output/team-eval/005930-risk.md
  owner: "@risk-analyst"

# Team Lead merges after both complete:
# Read both files → synthesize balanced view → output/team-eval/005930-final.md
# SOT update: outputs.deep-analysis-005930 = "output/team-eval/005930-final.md"
TeamDelete("stock-evaluation-005930")
```

#### 3.3 How the Orchestrator Merges Results [LOCAL-OK]

Three merge patterns, selected by data type:

| Merge Pattern | When to Use | Implementation |
|--------------|-------------|----------------|
| **Concatenation** | Independent, non-overlapping analyses (sector reports) | Append markdown sections |
| **Comparison table** | Same entity, different perspectives (weight sensitivity) | Build comparison matrix |
| **Conflict resolution** | Contradicting conclusions (bull vs bear on same stock) | Present both with reasoning, let user decide |

```python
# Merge pseudo-code for weight sensitivity analysis
def merge_sensitivity_results(result_files):
    """Orchestrator merges parallel fork results."""
    
    all_top20 = {}
    for config_name, filepath in result_files.items():
        stocks = parse_top20(read_file(filepath))
        all_top20[config_name] = stocks
    
    # Find robust picks (appear in all configurations)
    robust = set(all_top20["default"]) & set(all_top20["momentum_heavy"]) & set(all_top20["base_heavy"])
    
    # Find configuration-sensitive picks (appear in only 1)
    sensitive = {}
    for config, stocks in all_top20.items():
        unique = set(stocks) - robust
        for other_config, other_stocks in all_top20.items():
            if other_config != config:
                unique -= set(other_stocks)
        sensitive[config] = unique
    
    report = f"""
    ## 가중치 민감도 분석 결과
    
    ### 강건한 종목 (모든 가중치에서 상위 20)
    {format_stock_list(robust)}
    
    ### 가중치 민감 종목
    - 모멘텀 중시: {format_stock_list(sensitive['momentum_heavy'])}
    - 기반 형성 중시: {format_stock_list(sensitive['base_heavy'])}
    
    ### 해석
    강건한 종목은 어떤 분석 관점에서도 높은 점수를 받으므로 신뢰도가 높습니다.
    """
    return report
```

### 4. Complexity Analysis

#### Orchestrator Setup Complexity: **LOW** [LOCAL-OK]

**Rationale**:
- The pipeline is already a sequential Python script (`main.py`)
- The orchestrator is Claude Code itself — no additional framework to install
- CLAUDE.md defines the orchestrator's behavior (~100 lines)
- `/scan` command triggers the entire flow
- State management is file-based (pipeline_state.json + DuckDB)

**Setup effort**: 
- CLAUDE.md: 1-2 hours
- `/scan` command: 30 minutes
- stock-scanner skill: 2-3 hours (scoring rubric documentation)
- SessionStart freshness hook: 1 hour
- Total: ~1 day

#### Scaling Burden as Sub-Agents Increase: **LOW-to-MED** [LOCAL-OK]

**LOW for Phase 1**: No sub-agents needed. Pipeline is pure Python.

**MED if deep analysis features grow**: Each new sub-agent type requires:
- Agent definition file (.claude/agents/specialist.md)
- Prompt engineering for the specialist's domain
- Orchestrator logic to route requests to the right specialist
- Output format standardization

**Scaling relief**: Claude Code's Agent tool handles sub-agent lifecycle. No custom scheduling or process management.

#### Single Point of Failure (Orchestrator Dies): **MEDIUM risk, LOW impact** [LOCAL-OK]

**Failure modes**:
1. **Claude session crashes mid-pipeline**: Pipeline writes intermediate results to DuckDB. Restart from last completed stage (pipeline_state.json tracks this).
2. **Context window exhaustion**: PreCompact hook saves state. Session recovery reads from context-snapshots/ + pipeline_state.json.
3. **Rate limit hit**: Token budget (~25K/session) is well within limits. Unlikely.

**Recovery protocol**:
```python
# SessionStart hook checks pipeline_state.json
def on_session_start():
    state = read_json("pipeline/pipeline_state.json")
    
    if state.status == "running":
        # Pipeline was interrupted
        last_completed = state.last_completed_stage
        report_to_user(f"이전 세션이 중단되었습니다. {last_completed} 이후부터 재개합니다.")
        # Resume from next stage
    
    elif state.status == "completed" and is_today(state.completed_at):
        report_to_user("오늘 스캔이 이미 완료되어 있습니다.")
    
    elif state.status == "failed":
        report_to_user(f"이전 스캔 실패: {state.error}. 재시도하시겠습니까?")
```

#### Context Window Pressure: **LOW** [LOCAL-OK]

**Critical design decision from prior research (T01, S01)**: **summary-first architecture**.

The orchestrator NEVER loads raw data (2,500 stocks × OHLCV = ~1.875M tokens). Instead:
- Python computes everything → DuckDB stores results → report.py generates summary.md (~5-10K tokens)
- Orchestrator reads only summary.md + pipeline_state.json
- Deep analysis sub-agents read targeted DuckDB queries (single stock = ~500 tokens)

**Token budget breakdown** (daily scan):
| Component | Tokens |
|-----------|--------|
| CLAUDE.md + system prompt | ~5,000 |
| Pipeline execution (Bash calls) | ~3,000 |
| summary.md reading | ~8,000 |
| Korean interpretation output | ~5,000 |
| User follow-up questions | ~4,000 |
| **Total** | **~25,000** |

This is ~11% of the Max 20x 5-hour window (~220K tokens). No pressure.

---

## Branch 2.2: Distributed Orchestration (Agent Swarm)

### 1. Agent Swarm Pattern Design

#### 1.1 Each Agent's Autonomy Scope [LOCAL-PARTIAL]

In a distributed pattern, each agent decides:
- **When to execute** its task (triggered by predecessor's output file appearing)
- **How to execute** (tool selection, retry strategy within its scope)
- **Quality judgment** on its own output (self-validation)
- **When to escalate** to the user (anomaly detection, repeated failures)

Each agent does NOT decide:
- Whether the overall pipeline should run (external trigger: launchd or user)
- Another agent's task parameters
- The final user-facing report content (that's the Report Agent's scope)

#### 1.2 Inter-Agent Communication [LOCAL-OK]

Three communication channels, from simplest to most complex:

**Channel 1: Shared Files (Primary)** — Agents read/write to agreed-upon file paths
```
Collector Agent writes → data/stocks.duckdb (ohlcv table)
                       → pipeline/gates/collection_gate.json

Analyzer Agent reads  ← data/stocks.duckdb (ohlcv table)
Analyzer Agent reads  ← pipeline/gates/collection_gate.json (validates precondition)
Analyzer Agent writes → data/stocks.duckdb (indicators table)
                      → pipeline/gates/analysis_gate.json

Scorer Agent reads    ← data/stocks.duckdb (ohlcv + indicators)
...and so on
```

**Channel 2: SendMessage (For real-time coordination)** [LOCAL-PARTIAL]
```
# Only available within Agent Teams (experimental feature)
# Collector Agent → sends completion notification → Analyzer Agent
SendMessage(
  to="@analyzer",
  content="Collection complete. 2,487 stocks loaded. Gate passed. Proceed."
)
```

**Channel 3: Task System (Structured handoff)** [LOCAL-PARTIAL]
```
# Task acts as a message queue between agents
TaskCreate(
  subject="Analysis ready",
  description="Collection stage complete. 2,487 stocks in DuckDB. Run analyze.py",
  blockedBy=[]  # No blockers — ready to proceed
)
```

#### 1.3 Consensus/Conflict Resolution [LOCAL-OK]

In a swarm, who makes the final call?

**Option A: Quality Agent as arbiter** (recommended if using swarm)
- A designated Quality Agent reads all other agents' outputs
- Runs cross-validation checks (do Analysis Agent's indicators match Scorer Agent's inputs?)
- Can veto and request re-execution
- Effectively becomes a de-facto orchestrator (see Complexity Analysis)

**Option B: File-based voting** (theoretical, not recommended)
- Each agent writes a confidence score to its gate file
- Downstream agents only proceed if upstream confidence > threshold
- No central arbiter — agents self-coordinate

**Option C: User as final arbiter** (simplest, most practical)
- Agents execute autonomously
- Quality checks are embedded in each agent
- User reviews final summary.md and asks questions
- Conflicts surface only in the report ("MA Alignment suggests strength, but Volume shows weakness")

#### 1.4 Concrete Multi-Agent Communication Pattern [LOCAL-OK]

```
# File-based coordination pattern (no experimental features required)

┌─────────────────────────────────────────────────────────┐
│                    SHARED STATE                          │
│  pipeline/coordination/                                  │
│  ├── pipeline_state.json       (overall progress)        │
│  ├── gates/                                              │
│  │   ├── collection_gate.json  (Collector → Analyzer)    │
│  │   ├── analysis_gate.json    (Analyzer → Scorer)       │
│  │   ├── scoring_gate.json     (Scorer → Reporter)       │
│  │   └── quality_gate.json     (Quality Agent's verdict) │
│  └── heartbeats/                                         │
│      ├── collector.json        (last_active timestamp)   │
│      ├── analyzer.json                                   │
│      ├── scorer.json                                     │
│      └── reporter.json                                   │
└─────────────────────────────────────────────────────────┘

# Gate file format:
{
  "stage": "collection",
  "status": "passed",           // "passed" | "failed" | "warning"
  "completed_at": "2026-05-26T16:05:00",
  "metrics": {
    "stocks_collected": 2487,
    "zero_prices": 0,
    "execution_time_sec": 45
  },
  "downstream_ready": true
}

# Agent checks precondition before executing:
def check_precondition(required_gate_file):
    """Each agent checks its upstream gate before starting."""
    if not file_exists(required_gate_file):
        return False  # Upstream not complete yet
    gate = read_json(required_gate_file)
    return gate["status"] == "passed" and gate["downstream_ready"]
```

### 2. Role-Based Agent Specialization

#### 2.1 Specialized Agent Types

| Agent | Responsibility | Input | Output | Autonomy |
|-------|---------------|-------|--------|----------|
| **Data Collector** | pykrx data retrieval + validation | launchd trigger, config.yaml | DuckDB ohlcv, collection_gate.json | Full (retries, circuit breaker) |
| **Analysis Agent** | Technical indicator computation | DuckDB ohlcv | DuckDB indicators, analysis_gate.json | Full (pandas-ta execution) |
| **Scoring Agent** | Composite score calculation | DuckDB ohlcv+indicators, config.yaml (weights) | DuckDB scores, scoring_gate.json | Full (score formula) |
| **Report Agent** | summary.md generation | DuckDB scores, config.yaml | output/summary.md | Full (formatting) |
| **Quality Agent** | Cross-validation, anomaly detection | All gate files, DuckDB | quality_gate.json, alerts.json | Full (can block pipeline) |

#### 2.2 Concrete .claude/agents/ Definitions

```markdown
# .claude/agents/data-collector.md
---
name: data-collector
description: Collects KOSPI/KOSDAQ OHLCV data from pykrx with circuit breaker and validation gates
model: sonnet
tools: Bash, Read, Write
maxTurns: 10
---

You are the Data Collector agent for the stock analysis pipeline.

## Responsibility
Execute data collection from KRX via pykrx, validate the results, and write gate status.

## Execution Protocol
1. Read config.yaml for collection parameters
2. Execute: `python3 pipeline/collect.py`
3. Validate results:
   - stock_count >= 2300 (expect ~2500 for KOSPI+KOSDAQ)
   - zero_price_count == 0
   - date matches today (or latest trading day)
4. Write gate file: pipeline/gates/collection_gate.json
5. On failure: retry up to 3 times with 30s/60s/120s backoff
6. On persistent failure: write gate with status "failed", 
   set fallback flag for stale data usage

## NEVER DO
- Never modify DuckDB schema
- Never skip validation gates
- Never proceed without writing the gate file
```

```markdown
# .claude/agents/scoring-agent.md
---
name: scoring-agent
description: Calculates 6 sub-scores and composite technical completeness score
model: sonnet
tools: Bash, Read, Write
maxTurns: 8
skills:
  - stock-scanner
---

You are the Scoring Agent for the stock analysis pipeline.

## Responsibility
Calculate MA Alignment, Base Formation, Volume Behavior, Momentum, 
Breakout Readiness, and Relative Strength scores for all stocks.

## Precondition
Read pipeline/gates/analysis_gate.json — proceed ONLY if status == "passed"

## Execution Protocol
1. Verify analysis gate passed
2. Read config.yaml for scoring weights (default: 20/20/20/15/15/10)
3. Execute: `python3 pipeline/score.py`
4. Validate results:
   - All stocks have scores (no NaN in total_score)
   - Score distribution: mean between 30-70, stddev between 10-25
   - Top-10 turnover vs yesterday < 70%
   - avg_score change vs yesterday < 20%
5. Write gate file: pipeline/gates/scoring_gate.json
6. On anomaly: write gate with status "warning" + anomaly details

## NEVER DO
- Never modify indicator data
- Never override scoring weights without config.yaml update
- Never suppress anomaly warnings
```

```markdown
# .claude/agents/quality-agent.md
---
name: quality-agent
description: Cross-validates pipeline outputs and detects anomalies across stages
model: opus
tools: Bash, Read, Write, Glob, Grep
maxTurns: 15
---

You are the Quality Agent — the final validation layer.

## Responsibility
Cross-validate all pipeline stages, detect inter-stage inconsistencies,
and produce the quality verdict that gates the final report.

## Execution Protocol
1. Read ALL gate files: collection_gate.json, analysis_gate.json, scoring_gate.json
2. Cross-validate:
   - stock_count consistent across stages (collection == analysis == scoring)
   - No data loss between stages (DuckDB row counts match)
   - Score distribution plausible given indicator distributions
   - Historical comparison: today's scores vs 7-day rolling average
3. Run anomaly detection:
   - avg_score sudden shift (> 2 stddev from 30-day mean)
   - top-10 complete turnover (entirely different stocks vs yesterday)
   - sector concentration (> 60% of top-20 from single sector)
4. Write quality_gate.json with verdict + findings
5. If critical anomaly detected: write alerts.json for user notification

## Arbiter Authority
If quality_gate reports a critical issue, the Report Agent MUST include
a prominent warning in summary.md. The pipeline does NOT stop — graceful
degradation with clear warnings.

## NEVER DO
- Never modify DuckDB data
- Never suppress warnings
- Never approve without actually running cross-validation
```

#### 2.3 Work Handoff Patterns Between Agents [LOCAL-OK]

```
# Sequential handoff via gate files:

Data Collector                    Analysis Agent
     │                                 │
     ├─ collect.py ──→ DuckDB          │
     ├─ validate ──→ gate passed       │
     ├─ Write collection_gate.json ────┤
     │                                 ├─ Read collection_gate.json
     │                                 ├─ Verify: status == "passed"
     │                                 ├─ analyze.py ──→ DuckDB
     │                                 ├─ Write analysis_gate.json ──→
     │                                 │
     
# Parallel handoff (Quality Agent reads everything):

Data Collector ──→ collection_gate.json ──┐
Analysis Agent ──→ analysis_gate.json  ───┤
Scoring Agent  ──→ scoring_gate.json   ───┼──→ Quality Agent
                                          │     (reads all gates)
                                          │     (cross-validates)
                                          └──→ quality_gate.json ──→ Report Agent
```

### 3. Swarm Control Mechanisms

#### 3.1 Divergence Prevention [LOCAL-OK]

**Problem**: Without a central orchestrator, agents might:
- Execute out of order (scorer runs before analyzer)
- Use stale data (collector rewrites DuckDB while analyzer reads)
- Enter infinite retry loops
- Produce inconsistent interpretations

**Prevention mechanisms**:

| Mechanism | Implementation | Cost |
|-----------|---------------|------|
| **Gate preconditions** | Each agent checks upstream gate file before starting | ~5 lines per agent |
| **DuckDB MVCC** | Read isolation during writes (built-in) | Zero |
| **Retry budget** | Max 3 retries per agent, then fail-with-alert | ~10 lines per agent |
| **Timestamp guards** | Agent rejects gate file older than 24 hours | ~3 lines per agent |
| **Quality Agent veto** | Quality Agent can flag the pipeline as compromised | ~20 lines |

#### 3.2 Progress Monitoring [LOCAL-OK]

```python
# pipeline/monitor.py — called by Quality Agent or user via /status command

def get_pipeline_status():
    """Read all gate files to determine overall pipeline progress."""
    stages = ["collection", "analysis", "scoring", "quality", "report"]
    status = {}
    
    for stage in stages:
        gate_file = f"pipeline/gates/{stage}_gate.json"
        if file_exists(gate_file):
            gate = read_json(gate_file)
            status[stage] = {
                "status": gate["status"],
                "completed_at": gate.get("completed_at"),
                "metrics": gate.get("metrics", {}),
            }
        else:
            status[stage] = {"status": "pending"}
    
    # Determine overall progress
    completed = sum(1 for s in status.values() if s["status"] in ["passed", "warning"])
    total = len(stages)
    
    return {
        "progress": f"{completed}/{total}",
        "stages": status,
        "overall_status": "completed" if completed == total else "in_progress",
    }
```

#### 3.3 User Intervention Points [LOCAL-OK]

| Intervention Point | Trigger | User Action |
|-------------------|---------|-------------|
| **Pipeline start** | User runs `/scan` or launchd triggers | None (automatic) |
| **Collection failure after 3 retries** | collection_gate.json status: "failed" | Decide: retry manually, use stale data, or investigate |
| **Anomaly detected** | quality_gate.json has warnings | Review warnings, decide if results are trustworthy |
| **Summary review** | Report Agent completes summary.md | Read, ask follow-up questions, request deep analysis |
| **Configuration change** | User modifies config.yaml weights | Re-run scoring stage only |

#### 3.4 Shared State File as Coordination Mechanism [LOCAL-OK]

```yaml
# pipeline/coordination/pipeline_state.json — Swarm coordination SOT

{
  "run_id": "2026-05-26-001",
  "triggered_by": "launchd",
  "triggered_at": "2026-05-26T16:00:00",
  "target_date": "2026-05-26",
  
  "stages": {
    "collection": {
      "agent": "data-collector",
      "status": "completed",
      "started_at": "2026-05-26T16:00:05",
      "completed_at": "2026-05-26T16:00:50",
      "gate": "passed",
      "retries": 0
    },
    "analysis": {
      "agent": "analysis-agent",  
      "status": "running",
      "started_at": "2026-05-26T16:00:52",
      "gate": "pending"
    },
    "scoring": {"status": "blocked_by_analysis"},
    "quality": {"status": "blocked_by_scoring"},
    "report": {"status": "blocked_by_quality"}
  },
  
  "anomalies": [],
  "alerts": [],
  
  "overall": {
    "status": "in_progress",
    "progress": "2/5",
    "estimated_completion": "2026-05-26T16:05:00"
  }
}
```

### 4. Complexity Analysis

#### Swarm Setup Complexity: **HIGH** [LOCAL-PARTIAL]

**Rationale**:
- **5 agent definition files** to write and maintain (.claude/agents/)
- **Gate file protocol** to design and implement (format, validation, error handling)
- **Coordination state** (pipeline_state.json) requires careful concurrent access design
- **DuckDB write locking**: only one writer at a time. Agents must serialize writes.
- **Agent Teams experimental**: `CLAUDE_AGENT_TEAMS=1` required, API potentially unstable
- **Testing complexity**: must verify all agent handoffs, gate transitions, error cascading

**Setup effort**:
- 5 agent definitions: 2-3 hours each = 10-15 hours
- Gate protocol design + implementation: 3-4 hours
- Coordination state management: 2-3 hours
- Integration testing: 4-5 hours
- Total: **~3-4 days** (vs ~1 day for centralized)

#### Communication Complexity as Agents Increase: **HIGH** [LOCAL-OK]

**Rationale**: Communication paths grow quadratically.

```
2 agents: 1 communication path
3 agents: 3 paths
5 agents: 10 paths
N agents: N*(N-1)/2 paths
```

For our 5 agents: 10 potential communication paths. Each requires:
- Gate file format agreement
- Error propagation protocol
- Timeout handling
- State consistency checks

With the centralized pattern: 4 paths (orchestrator ↔ each of 4 stages). Linear growth.

#### Unpredictable Behavior Risk: **MEDIUM** [LOCAL-OK]

**Risk factors**:
- Agents might misinterpret gate files (file format ambiguity)
- Race conditions if two agents read/write pipeline_state.json simultaneously
- Cascading failures: Analyzer fails → Scorer waits forever (no timeout)
- Quality Agent might approve a pipeline that a human would reject

**Mitigations**:
- Strict gate file schema with JSON Schema validation
- File-based locking (simple but effective for single-machine)
- Timeout per agent (maxTurns in agent definition)
- Quality Agent as last-resort safety net

---

## COMPARISON: Branch 2.1 (Centralized) vs Branch 2.2 (Distributed)

### Head-to-Head Comparison Matrix

| Dimension | Centralized (2.1) | Distributed (2.2) | Winner |
|-----------|-------------------|-------------------|--------|
| **Setup complexity** | LOW (~1 day) | HIGH (~3-4 days) | 2.1 |
| **Daily pipeline fit** | Excellent (sequential is natural) | Overkill (4 stages don't need autonomy) | 2.1 |
| **Deep analysis fit** | Good (sub-agents for ad-hoc) | Good (specialized agents) | Tie |
| **Context window pressure** | LOW (summary-first, ~25K tokens) | LOW (each agent has isolated context) | Tie |
| **Failure recovery** | Simple (pipeline_state.json resume) | Complex (gate files + coordination state) | 2.1 |
| **Scaling to new features** | MED (add sub-agent types) | MED (add specialized agents) | Tie |
| **Single point of failure** | Yes (orchestrator) | No (any agent can fail independently) | 2.2 |
| **Debugging difficulty** | LOW (single execution thread) | HIGH (distributed state across 5+ files) | 2.1 |
| **Token efficiency** | HIGH (one session) | LOWER (multiple agent sessions) | 2.1 |
| **Maintainability** | HIGH (1 CLAUDE.md + 1 command) | MED (5 agent files + gate protocol) | 2.1 |
| **Non-technical user** | Simple (/scan → done) | Same (/scan → done, complexity hidden) | Tie |
| **Platform maturity** | Stable (Agent tool, Bash, Hooks) | Experimental (Agent Teams) | 2.1 |

**Score: Centralized 7, Distributed 1, Tie 4**

### Can They Be Mixed?

**Yes — and this is the recommended approach for Phase 2+.**

```
# Hybrid Architecture:

## Daily Pipeline (Centralized — Phase 1)
/scan → Orchestrator → python3 pipeline/main.py → summary.md → interpretation
       (single session, ~25K tokens, deterministic)

## Deep Analysis (Distributed elements — Phase 2+)
/분석 삼성전자 → Orchestrator spawns sub-agents:
  ├── Technical analyst (sub-agent, sonnet)
  ├── Risk analyst (sub-agent, sonnet)  
  └── Orchestrator merges → output/deep-analysis/005930.md
      (still centralized merge, but parallel execution)

## Weight Sensitivity (Fork pattern — Phase 2+)
/민감도분석 → Orchestrator forks:
  ├── Default weights (parallel, sonnet)
  ├── Momentum-heavy (parallel, sonnet)
  └── Base-heavy (parallel, sonnet)
      → Orchestrator merges comparison
```

**Why this hybrid works**:
- Daily pipeline is sequential and deterministic → centralized is simpler
- Deep analysis benefits from parallel specialist perspectives → fork/sub-agent pattern
- No Agent Teams needed in Phase 1 → avoids experimental feature dependency
- Orchestrator remains the single point of control → easier debugging and recovery

### Context Window Implications

| Pattern | Context Consumption | Strategy |
|---------|-------------------|----------|
| **Centralized** | Orchestrator accumulates all results in one session | summary-first architecture caps at ~25K tokens. Sub-agent results return as text to orchestrator — each adds ~1-3K tokens. Safe up to ~10 sub-agents per session. |
| **Distributed** | Each agent has isolated context (no accumulation) | Each agent uses ~5-10K tokens independently. No single-session accumulation. However, total token cost is HIGHER because each agent loads CLAUDE.md + system prompt separately. |

**For this system**: Context window is not the bottleneck. summary-first architecture ensures the orchestrator never needs to ingest raw data. The ~25K token daily budget is well within limits for either pattern.

### Failure Modes: What Breaks First

**Centralized — First failure point**:
1. **Orchestrator session crashes mid-pipeline** → Recovery: read pipeline_state.json, resume from last completed stage. MEDIUM impact, LOW frequency.
2. **Sub-agent produces garbage output** → Recovery: orchestrator validates before accepting. LOW impact (caught by gates).
3. **Token rate limit during deep analysis** → Recovery: warn user, suggest retry later. LOW impact.

**Distributed — First failure point**:
1. **Agent misinterprets gate file format** → Entire downstream pipeline runs on wrong assumption. HIGH impact, MEDIUM frequency. Hard to debug across distributed state.
2. **DuckDB write conflict** → Two agents try to write simultaneously. DuckDB handles this (MVCC), but one agent waits. MEDIUM impact if timeouts are tight.
3. **Quality Agent false positive** → Flags a healthy pipeline as anomalous, user receives unnecessary warnings. LOW impact but degrades trust.
4. **Orphaned agent** → One agent crashes mid-execution, never writes gate file. Downstream agents wait forever. HIGH impact without timeout mechanism.

**Conclusion**: Centralized fails more gracefully. The single orchestrator can detect and report all failures. Distributed failures are harder to diagnose because state is scattered across multiple files and agent sessions.

### For THIS Specific System: The Pragmatic Choice

**Centralized Orchestration (Branch 2.1) is the clear winner.**

**Decisive factors**:

1. **Pipeline is deterministic**: `collect → analyze → score → report` is a fixed sequence of Python computations. There is no decision-making that requires autonomous agents. Claude's value is in **interpretation**, not in **orchestration**.

2. **Single user**: No concurrent access, no collaboration requirement. The distributed pattern's main advantage (fault isolation for multi-user systems) doesn't apply.

3. **4 stages**: The pipeline has exactly 4 stages. The overhead of 5 agent definitions, gate files, and coordination protocols is disproportionate to the problem size.

4. **Prior research consensus (S01)**: "순차 파이프라인 > 오케스트레이션 프레임워크" scored 5/5 consensus. "멀티에이전트 토론" scored 0/5. The research team unanimously favored simplicity.

5. **Platform maturity**: Agent Teams is experimental. The centralized pattern uses only stable Claude Code features (Agent tool, Bash, Hooks, Skills, Commands).

6. **Token economics**: A single orchestrator session costs ~25K tokens. Distributed agents would each need their own system prompt loading, increasing total cost by ~2-3x for no benefit.

7. **Non-technical user**: The user doesn't care about orchestration patterns. They care about `/scan` → clear results in Korean. Centralized delivers this with less that can go wrong.

**Recommended architecture**:

```
┌──────────────────────────────────────────────────────────┐
│                    Claude Code Session                     │
│                    (Orchestrator Role)                     │
│                                                           │
│  CLAUDE.md → defines orchestrator behavior                │
│  /scan     → triggers daily pipeline                      │
│  Skills    → stock-scanner/SKILL.md (scoring rubric)      │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  python3 pipeline/main.py                           │  │
│  │  (deterministic, no LLM needed)                     │  │
│  │                                                     │  │
│  │  collect() ──[Gate 1]──→ analyze() ──[Gate 2]──→   │  │
│  │  score() ──[Gate 3]──→ report() → summary.md       │  │
│  └─────────────────────────────────────────────────────┘  │
│                          │                                │
│  Orchestrator reads summary.md                            │
│  Interprets for user in Korean                            │
│                                                           │
│  ┌─── Ad-hoc (Phase 2+) ───────────────────────────────┐ │
│  │  Sub-agent: deep analysis (opus, when requested)    │ │
│  │  Fork: weight sensitivity (parallel sonnet agents)  │ │
│  └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
         │
    launchd (trigger)
```

---

## LOCAL EXECUTION TAGGING Summary

| Component | Tag | Notes |
|-----------|-----|-------|
| Centralized orchestrator (Claude Code session) | [LOCAL-OK] | Native Claude Code capabilities |
| Sequential Python pipeline (main.py) | [LOCAL-OK] | Pure Python, no external service |
| Sub-agent spawning (Agent tool) | [LOCAL-OK] | Stable Claude Code feature |
| Fork pattern (parallel sub-agents) | [LOCAL-OK] | Each sub-agent runs locally |
| Task management (TaskCreate/TaskGet) | [LOCAL-OK] | Built-in Claude Code feature |
| pipeline_state.json state tracking | [LOCAL-OK] | File-based, no external dependency |
| DuckDB storage | [LOCAL-OK] | Single-file, local database |
| launchd scheduling | [LOCAL-OK] | macOS native |
| summary-first architecture | [LOCAL-OK] | File-based boundary |
| SessionStart freshness hook | [LOCAL-OK] | Python script in .claude/hooks/ |
| Agent Teams (TeamCreate/TeamDelete) | [LOCAL-PARTIAL] | Experimental feature, requires CLAUDE_AGENT_TEAMS=1 |
| Worktree isolation for sub-agents | [LOCAL-PARTIAL] | Requires git repository initialization |
| SendMessage between agents | [LOCAL-PARTIAL] | Only within Agent Teams (experimental) |
| pykrx data collection | [LOCAL-PARTIAL] | Requires KRX network access + account |

**No [LOCAL-BLOCKED] items.** All orchestration patterns can be implemented locally on macOS.

---

## PARKING LOT

### Out-of-Scope Discoveries

1. **pykrx data availability timing**: The exact minute after market close (15:30 KST) when data becomes available affects launchd schedule configuration. Requires empirical testing at 15:35, 16:00, 17:00, 18:00. Identified in T03/T04 but not resolved.

2. **DuckDB concurrent read/write during pipeline**: When launchd-triggered Python writes to DuckDB while a Claude session reads, MVCC handles this but may cause momentary lock waits. Atomic file replacement pattern is a potential mitigation. Identified in T01 but not tested.

3. **claude -p headless mode for fully automated daily scans**: GitHub issue #36324 tracks subscription account compatibility. Phase 2 feature — daily scans could run without user interaction. Token guardrails (--max-turns, --max-budget-usd) required.

4. **Model tiering for cost optimization**: Routine daily scans use Sonnet (sufficient quality for deterministic pipeline + interpretation). Deep analysis uses Opus (quality-critical interpretation). Model selection protocol from claude-code-patterns.md applies.

5. **Context preservation across multi-day usage**: If user runs `/scan` daily, each session starts fresh. Historical context (yesterday's top picks, week-over-week trends) requires either DuckDB history tables or context-snapshot-based recovery. The existing AgenticWorkflow context preservation system handles this.

6. **Reflexion pattern for monthly weight calibration**: T05 identified this as the only high-value agentic pattern. Implementation involves backtesting top-scored stocks' N+20 day performance and adjusting weights. This is a separate workflow, not part of the daily pipeline orchestration.

7. **Korean financial terminology accuracy**: Stock-scanner skill should include a terminology reference mapping English technical terms to standard Korean financial vocabulary ("정배열" for aligned MAs, "눌림목" for pullback, "돌파" for breakout). Identified in T02/S04.

8. **VCP proxy vs full VCP transition criteria**: Phase 1 uses Bollinger Band squeeze + volume decline as proxy. The exact thresholds for BBand width and volume decline ratio need empirical calibration. The transition to full swing-point-based VCP detection is a Phase 3 decision. Identified in T05/S01.

9. **Multi-market weight differentiation**: KOSDAQ small-caps exhibit different volume patterns, volatility, and institutional participation than KOSPI large-caps. A single weight set may underperform on one market. Deferred to 3-month review. Identified in T05/S04.

10. **Bootstrap experience for initial 5-year data load**: First-time data loading takes ~60-90 minutes. Progress reporting and immediate analysis with partial data (yesterday only) are UX requirements not addressed by the orchestration pattern. Identified in T04/S04.
