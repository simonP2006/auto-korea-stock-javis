---
round: 3
type: raw
teammate: skills-hooks-developer
axis: skills-hooks-commands
investigation_axis: coding-implementation
created: "2026-05-26T09:30:00+09:00"
question_summary: "General-purpose vs workflow-specific skills, hooks, and commands for the stock analysis system — concrete SKILL.md, hook scripts, command markdowns, token cost comparison, and hybrid recommendation"
assumption_axis: "General-Purpose Skills vs Workflow-Specific Skills"
branch_a: "Branch 3.1 — General-Purpose Skills Library (reusable across workflows)"
branch_b: "Branch 3.2 — Workflow-Specific Skills (optimized for stock analysis)"
web_search_count: 0
local_execution_tags:
  LOCAL_OK: ["data-validator skill", "score-interpreter skill", "pipeline-runner skill", "stock-scanner skill", "market-regime-detector skill", "anomaly-flagger skill", "check_data_freshness.py hook", "stock_session_init.py hook", "validate_pykrx_output.py hook", "/scan command", "/top command", "/analyze command", "/backtest command", "/regime command", "/anomalies command", "DuckDB queries", "pykrx validation"]
  LOCAL_PARTIAL: ["KRX API access (requires internet for data fetch, local execution)"]
  LOCAL_BLOCKED: ["Real-time price alerts (requires persistent background process — not in scope)"]
sources:
  - "Round 2 T01 — Platform Capability (Claude Code hooks, skills, commands)"
  - "Round 2 T02 — Configuration Architect (.claude/ structure)"
  - "Round 2 T05 — Theory Foundation (scoring methodology, Korean financial terms)"
  - "Existing project — .claude/hooks/scripts/ (hook implementation patterns)"
  - "Existing project — .claude/settings.json (hook configuration format)"
---

# T03: Skills & Hooks Developer — General-Purpose vs Workflow-Specific

## Executive Summary

For the KOSPI/KOSDAQ stock analysis system, a **hybrid approach (85% specific / 15% general)** is recommended. Domain-specific skills, hooks, and commands provide higher accuracy, ~1,250 tokens/day savings, and a Korean-native user experience. General-purpose reuse is a non-priority for this single-purpose product. Only the destructive command blocker and context preservation hooks remain general.

---

## Branch 3.1: General-Purpose Skills Library

### 1. Skill Design

#### Identified Skills

| Skill | Purpose | Reuse Potential |
|-------|---------|-----------------|
| `data-validator` | Validates any data pipeline output (DuckDB, CSV) | HIGH |
| `score-interpreter` | Interprets any composite scoring result | MED |
| `pipeline-runner` | Executes any Python pipeline with monitoring | HIGH |
| `report-generator` | Generates summary reports from structured data | HIGH |
| `data-freshness-checker` | Checks data staleness in time-series DB | MED |

#### Skill Composition Pattern

```
pipeline-runner → data-validator → score-interpreter → report-generator
```

File-mediated composition (not function-call): each skill reads previous skill's output file.

#### Concrete SKILL.md: data-validator

```markdown
---
name: data-validator
description: >
  Validates data pipeline output for completeness, schema conformance,
  and statistical anomalies.
---

# Data Validator

## Validation Protocol

### Step 1: Schema Validation
- [ ] All expected columns/fields present
- [ ] Data types match expected schema
- [ ] No unexpected null columns (>50% null = WARNING)

### Step 2: Completeness Check
- [ ] Row count within expected range
- [ ] Date range covers expected period
- [ ] No gaps in time-series data

### Step 3: Statistical Anomaly Detection
- [ ] No values exceed 3 std dev from mean (flag, don't block)
- [ ] Distribution consistent with historical runs

### Step 4: Cross-Reference Validation
- [ ] Spot-check 5 random records against source

## Input Interface
1. Data path (DuckDB file, CSV, etc.)
2. Schema definition (optional)
3. Expected row count range (optional)
4. Baseline path (optional)
```

[LOCAL-OK] — All validation runs locally.

#### Concrete SKILL.md: score-interpreter

```markdown
---
name: score-interpreter
description: >
  Interprets composite scoring results with weighted sub-scores.
---

# Score Interpreter

## Interpretation Protocol

### Step 1: Load Score Definition
- Sub-score names, weights, ranges
- Composite formula, threshold definitions

### Step 2: Contextual Interpretation
- Overall assessment (composite → qualitative category)
- Sub-score breakdown (strongest/weakest)
- Relative ranking (percentile)
- Delta analysis (vs previous period)

### Step 3: Pattern Detection
- Identify clusters of similar-scoring entities
- Flag unbalanced sub-scores
- Detect edge cases

## Limitations
- Cannot interpret without score definition provided by caller
- Domain-specific meaning must be injected each time
```

[LOCAL-OK]

**Key limitation**: score-interpreter deliberately avoids domain knowledge. "Volume score = 82" has no stock-specific meaning. Caller must inject all domain context → extra ~500 tokens per invocation.

### 2. Hook Design

#### General-Purpose Hooks

| Event | Hook Script | Purpose |
|-------|------------|---------|
| SessionStart | `check_data_freshness.py` | Check any DuckDB file staleness |
| PostToolUse(Bash) | `validate_pipeline_exit.py` | Check pipeline exit codes |
| Stop | `generate_execution_summary.py` | Summarize pipeline outcomes |
| PreToolUse(Bash) | `block_db_corruption.py` | Block commands corrupting any DB |

#### Concrete Hook: check_data_freshness.py

```python
#!/usr/bin/env python3
"""SessionStart Hook — Data Freshness Checker (General-Purpose)
Scans for *.duckdb files, compares mtime to threshold, warns if stale.
Exit: 0 always (informational only). [LOCAL-OK]"""

import json, os, sys, glob
from datetime import datetime, timedelta

DEFAULT_STALENESS_HOURS = 24
MAX_SCAN_DEPTH = 3

def find_duckdb_files(project_dir, max_depth=MAX_SCAN_DEPTH):
    results = []
    for depth in range(1, max_depth + 1):
        pattern = os.path.join(project_dir, *["*"] * depth)
        for f in glob.glob(pattern):
            if f.endswith(".duckdb") and os.path.isfile(f):
                results.append(f)
    return results

def check_freshness(db_path, threshold_hours):
    try:
        mtime = os.path.getmtime(db_path)
        modified = datetime.fromtimestamp(mtime)
        age = datetime.now() - modified
        return {
            "path": db_path,
            "modified": modified.strftime("%Y-%m-%d %H:%M"),
            "age_hours": round(age.total_seconds() / 3600, 1),
            "is_stale": age > timedelta(hours=threshold_hours),
        }
    except OSError:
        return {"path": db_path, "is_stale": True, "error": "cannot read metadata"}

def main():
    try:
        input_data = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", input_data.get("cwd", os.getcwd()))
        threshold = int(os.environ.get("DATA_FRESHNESS_HOURS", DEFAULT_STALENESS_HOURS))
        db_files = find_duckdb_files(project_dir)
        if not db_files:
            sys.exit(0)
        stale = [check_freshness(f, threshold) for f in db_files if check_freshness(f, threshold)["is_stale"]]
        if stale:
            rel = lambda p: os.path.relpath(p, project_dir)
            lines = ["[DATA FRESHNESS WARNING]"]
            for s in stale:
                lines.append(f"  - {rel(s['path'])}: {s['age_hours']}h old (threshold: {threshold}h)")
            lines.append("Consider running the data collection pipeline to refresh.")
            print("\n".join(lines))
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()
```

#### Hook → Skill Triggering

Hooks cannot directly invoke skills. Indirect pattern: hook outputs text → Claude reads → may suggest using a skill. Hook provides **information**, Claude decides **action**.

### 3. Command Design

| Command | Purpose | Relationship to Workflow |
|---------|---------|------------------------|
| `/scan` | Run daily pipeline | Triggers pipeline-runner |
| `/status` | Pipeline health check | Standalone diagnostic |
| `/history` | View past analyses | Reads output directory |
| `/validate` | Run data validation | Triggers data-validator |
| `/interpret` | Interpret latest scores | Triggers score-interpreter |

**Limitation**: Generic `/scan` says `pipeline/main.py` as placeholder — cannot assume domain structure. User must specify actual script path.

### 4. Complexity Analysis

| Metric | Estimate |
|--------|----------|
| Skills | 4-5 |
| Hooks | 3-4 new |
| Commands | 5 |
| Total new files | 12-14 |
| Reusability | **HIGH** |
| Maintenance | **LOW** |
| Token cost per invocation | **HIGHER** (domain context must be injected each time) |

---

## Branch 3.2: Workflow-Specific Skills

### 1. Skill Design

#### Identified Skills

| Skill | Purpose | Token Savings vs Generic |
|-------|---------|------------------------|
| `stock-scanner` | KOSPI/KOSDAQ technical completeness scoring | HIGH (~500 tokens/invocation) |
| `market-regime-detector` | KOSPI 200-day SMA analysis | MED |
| `anomaly-flagger` | Suspicious score pattern detection | MED |
| `korean-market-calendar` | KRX trading day awareness | LOW |

#### Concrete SKILL.md: stock-scanner (abbreviated — key structure)

```markdown
---
name: stock-scanner
description: >
  KOSPI/KOSDAQ 기술적 완전성 분석. 사용자가 "종목 스캔", "주식 분석",
  "stock scan", "오늘의 종목", "매수 후보" 등을 요청할 때 사용.
---

# Stock Scanner — KOSPI/KOSDAQ Technical Completeness Analysis

## Scoring Methodology

### 6 Sub-Scores (0-100)
| Sub-Score | Weight | Key Indicators |
|-----------|--------|----------------|
| MA Alignment (추세 정렬) | 0.20 | Minervini SEPA 8 criteria → boolean × 12.5 |
| Base Formation (베이스 형성) | 0.20 | Weinstein 4 stages (SMA slope + price) |
| Volume Behavior (거래량 행태) | 0.20 | Wyckoff: OBV + up/down ratio + contraction |
| Momentum (모멘텀) | 0.15 | RSI(14) + MACD + ADX(14) |
| Breakout Readiness (돌파 준비도) | 0.15 | BBand squeeze + volume decline proxy |
| Relative Strength (상대 강도) | 0.10 | IBD RS: 40% 3mo + 20% 6mo + 20% 9mo + 20% 12mo |

### Interpretation Thresholds
| Score | Category | Korean |
|-------|----------|--------|
| 80+ | 완성 임박 | 강력 매수 신호 |
| 60-79 | 진행 중 | 매수 신호 |
| 40-59 | 초기 | 중립 |
| <40 | 미성숙 | 약세 |

### Market Regime Context
| KOSPI vs 200-day SMA | Regime | Score Adjustment |
|----------------------|--------|-----------------|
| > 200-SMA + 5% | 강세장 (Bull) | Face-value |
| ±5% of 200-SMA | 박스권 (Neutral) | Raise buy threshold to 70 |
| < 200-SMA - 5% | 약세장 (Bear) | Raise buy threshold to 80 |

## Anomaly Detection Rules
1. Volume-Price Divergence: Volume > 80 + Trend < 30 → manipulation risk
2. Perfect Score Syndrome: All 6 sub-scores within 5 points → calculation error
3. Micro-Cap Trap: Composite > 80 + market cap < 50B KRW → liquidity risk
4. Stale Data: Last trading date > 5 business days → suspended/delisted
5. Single-Indicator Dominance: One > 95, all others < 50 → distorted

## Korean Financial Terminology Reference
| English | Korean | Abbreviation |
|---------|--------|-------------|
| Moving Average | 이동평균 | 이평 |
| Golden Cross | 골든크로스 | GC |
| Death Cross | 데드크로스 | DC |
| Support Level | 지지선 | — |
| Resistance Level | 저항선 | — |
| Trading Volume | 거래량 | — |
| Market Cap | 시가총액 | 시총 |
| Consolidation | 횡보/보합 | — |
| Breakout | 돌파 | — |
| Pullback | 눌림목 | — |
| Overbought | 과매수 | — |
| Oversold | 과매도 | — |

## Reference Files
- `references/scoring-weights.yaml` — weight SOT
- `references/indicator-formulas.md` — exact calculations
```

[LOCAL-OK] — All execution local.

### 2. Hook Design

#### Workflow-Specific Hooks

| Event | Hook Script | Purpose |
|-------|------------|---------|
| SessionStart | `stock_session_init.py` | DuckDB freshness + latest summary.md pointer |
| PreToolUse(Bash) | `block_duckdb_corruption.py` | Block commands corrupting stocks.duckdb |
| PostToolUse(Bash) | `validate_pykrx_output.py` | Validate pykrx/pipeline output specifically |
| Stop | `stock_context_snapshot.py` | Stock-analysis-aware context snapshot |

#### Concrete Hook: stock_session_init.py

```python
#!/usr/bin/env python3
"""SessionStart Hook — Stock Analysis Session Initializer
Checks DuckDB stock data freshness, reports latest analysis context.
Exit: 0 always (informational). [LOCAL-OK]"""

import json, os, sys
from datetime import datetime, timedelta

DUCKDB_PATH = "data/stocks.duckdb"
SUMMARY_PATH = "output/summary.md"
STALENESS_HOURS = 18

def main():
    try:
        input_data = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", input_data.get("cwd", os.getcwd()))
        db_path = os.path.join(project_dir, DUCKDB_PATH)
        summary_path = os.path.join(project_dir, SUMMARY_PATH)

        lines = ["[STOCK ANALYSIS SESSION]"]

        # DB freshness
        if not os.path.exists(db_path):
            lines.append(f"  Database: NOT FOUND. Run /scan to initialize.")
        else:
            age_h = round((datetime.now() - datetime.fromtimestamp(os.path.getmtime(db_path))).total_seconds() / 3600, 1)
            status = "STALE" if age_h > STALENESS_HOURS else "FRESH"
            lines.append(f"  Database: {status} ({age_h}h old)")
            if status == "STALE":
                lines.append("  Action: Run /scan to refresh")

        # Latest summary
        if os.path.exists(summary_path):
            with open(summary_path, "r") as f:
                header_lines = f.readlines()[:20]
            for line in header_lines:
                if any(k in line for k in ["KOSPI:", "분석일시", "분석 종목수"]):
                    lines.append(f"    {line.strip()}")

        lines.append("  Commands: /scan, /top N, /analyze TICKER")
        print("\n".join(lines))
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()
```

#### Concrete Hook: validate_pykrx_output.py

```python
#!/usr/bin/env python3
"""PostToolUse(Bash) Hook — Pipeline Output Validator
Only activates for pipeline commands (collect.py, analyze.py, score.py, main.py).
Exit: 0 always (warn via stdout). [LOCAL-OK]"""

import json, os, sys, re

PIPELINE_SCRIPTS = {"collect.py": "collection", "analyze.py": "analysis",
                    "score.py": "scoring", "main.py": "full_pipeline"}
MIN_STOCKS_TOTAL = 2000

def main():
    try:
        input_data = json.load(sys.stdin) if not sys.stdin.isatty() else {}
        command = input_data.get("tool_input", {}).get("command", "")
        stage = next((s for script, s in PIPELINE_SCRIPTS.items() if script in command), None)
        if not stage:
            sys.exit(0)

        tool_response = input_data.get("tool_response", {})
        exit_code = tool_response.get("exit_code", -1)
        stdout = tool_response.get("stdout", "")
        stderr = tool_response.get("stderr", "")
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        warnings = []

        if exit_code != 0:
            warnings.append(f"{stage} FAILED (exit code {exit_code})")
        if "HTTP Error" in stdout + stderr:
            warnings.append("KRX API error — data may be incomplete")
        if stage in ("collection", "full_pipeline"):
            numbers = [int(n) for n in re.findall(r'(\d{3,})', stdout) if 100 < int(n) < 5000]
            for num in numbers:
                if num < MIN_STOCKS_TOTAL:
                    warnings.append(f"Low stock count: {num} (expected >{MIN_STOCKS_TOTAL})")
        if stage in ("scoring", "full_pipeline"):
            summary = os.path.join(project_dir, "output", "summary.md")
            if not os.path.exists(summary):
                warnings.append("summary.md not generated")
            elif os.path.getsize(summary) < 500:
                warnings.append(f"summary.md suspiciously small ({os.path.getsize(summary)} bytes)")

        if warnings:
            print(f"[PIPELINE VALIDATION — {stage.upper()}]")
            for w in warnings:
                print(f"  WARNING: {w}")
    except Exception:
        pass
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### 3. Command Design

#### Concrete Command: /scan

```markdown
---
description: "KOSPI/KOSDAQ 전 종목 기술적 완전성 분석 파이프라인 실행"
---

## 종목 스캔 (Full Technical Completeness Scan)

### 실행 프로토콜:

**Step 1 — 사전 점검:**
1. `uv run python3 -c "import pykrx; import duckdb; import pandas_ta; print('OK')"`
2. DuckDB 파일 확인: `ls -la data/stocks.duckdb`
3. 장 마감 여부: 15:30 KST 이후인지 확인

**Step 2 — 데이터 수집:** `uv run python3 src/collect.py`
**Step 3 — 기술적 분석:** `uv run python3 src/analyze.py`
**Step 4 — 스코어링:** `uv run python3 src/score.py`

**Step 5 — 결과 해석:**
Read `output/summary.md` + stock-scanner 스킬 해석 기준:
1. 시장 환경 판단 (KOSPI 200일 이평)
2. 매수 임계값 적용 (시장 레짐별)
3. 상위 종목 해석 (Top 20 서브스코어 분석)
4. 이상 징후 검토 (5가지 규칙)
5. 한국어 리포트 생성
```

[LOCAL-OK]

#### Concrete Command: /analyze

```markdown
---
description: "개별 종목 심층 기술적 분석"
---

## 종목 심층 분석 (Single Stock Deep Dive)

$ARGUMENTS 종목에 대한 심층 분석.

### 입력: 6자리 코드(005930) 또는 종목명(삼성전자)

### 분석:
1. DuckDB에서 최근 30일 스코어 조회
2. 6개 서브스코어 심층 해석 (추세/모멘텀/거래량/변동성/지지저항/패턴)
3. 이상 징후 5규칙 적용
4. 30일 추이 분석
5. 한국어 리포트
```

[LOCAL-OK]

### 4. Complexity Analysis

| Metric | Estimate |
|--------|----------|
| Skills | 3-4 (stock-scanner, market-regime-detector, anomaly-flagger, korean-market-calendar) |
| Hooks | 4 new |
| Commands | 6 (/scan, /top, /analyze, /backtest, /regime, /anomalies) |
| Total new files | 13-16 |
| Reusability | **LOW** (stock-specific) |
| Maintenance | **MED** (scoring changes → skill updates) |
| Token cost per invocation | **LOWER** (domain context pre-loaded) |

---

## COMPARISON: Branch 3.1 vs 3.2

### Token Cost Comparison (per daily /scan)

**Branch 3.1 (General-Purpose)**:
- /scan command: ~200 tokens
- Score-interpreter context injection: ~500 tokens (6 sub-scores, weights, thresholds)
- Korean terms injection: ~300 tokens
- Anomaly rules injection: ~200 tokens
- Market regime injection: ~150 tokens
- Interpretation prompt: ~400 tokens
- **Total overhead: ~1,750 tokens/scan**

**Branch 3.2 (Workflow-Specific)**:
- /scan command: ~500 tokens (detailed, domain-aware)
- stock-scanner skill already loaded: 0 additional tokens
- **Total overhead: ~500 tokens/scan**

**Daily savings: ~1,250 tokens. Monthly: ~37,500 tokens.**

The real savings are in **accuracy**: "volume 90 + trend 20 = manipulation risk" cannot be expressed generically — must be injected every time in 3.1, or it gets missed.

### Component-Level Recommendation

| Component | Approach | Rationale |
|-----------|----------|-----------|
| Scoring skill | **SPECIFIC** | Domain knowledge is core value |
| Session start hook | **SPECIFIC** | Needs DuckDB schema, summary.md format, market hours |
| Pipeline validation hook | **SPECIFIC** | pykrx failure modes are domain-specific |
| Destructive command blocker | **GENERAL** (extend existing) | Just add DuckDB file patterns |
| Data freshness checking | **HYBRID** | Core logic general, threshold stock-specific |
| Commands | **SPECIFIC** | Non-technical Korean user needs domain-native commands |
| Execution summary | **GENERAL** (extend existing) | generate_context_summary.py already handles this |
| Report generation | **SPECIFIC** | Korean financial report structure |

### RECOMMENDATION: Hybrid (85% Specific / 15% General)

**Pure general (3.1) is wrong** because:
1. Non-technical user needs domain-native Korean commands
2. Scoring interpretation without embedded methodology = lower quality
3. Korean financial terminology injection on every invocation = wasteful + error-prone
4. Domain-specific anomaly detection cannot be expressed generically

**Pure specific (3.2) is nearly right** but:
1. Destructive command blocker doesn't need domain specificity
2. Context preservation system already general and excellent
3. Data freshness checker's core logic could serve other DuckDB projects

**Split**: 85% specific (stock-scanner, all commands, session init, pipeline validation, anomaly detection) + 15% general (extend existing hooks with DuckDB patterns).

---

## LOCAL EXECUTION TAGGING

| Component | Tag |
|-----------|-----|
| All hooks | [LOCAL-OK] |
| All skills | [LOCAL-OK] |
| All commands | [LOCAL-OK] |
| KRX API access | [LOCAL-PARTIAL] (internet required, local execution) |
| Real-time price alerts | [LOCAL-BLOCKED] (persistent background process — not in scope) |

---

## PARKING LOT

1. **Fundamental data integration**: PER/PBR/ROE from OpenDART API — separate workflow.
2. **Backtest framework**: `/backtest` command needs significant engineering (separate workflow).
3. **Multi-market expansion**: If US/crypto added, general-purpose skills become more relevant.
4. **Alert system**: `/watch TICKER` needs persistent background process (architecturally distinct).
5. **MCP server for DuckDB**: Direct DuckDB query access would change hook/command design.
6. **Sector rotation analysis**: Requires GICS sector classification data not in current pipeline.
7. **Hook performance budget**: 15+ existing + 2-4 new hooks. Cumulative latency needs monitoring.
8. **Score weight optimization**: 20/20/20/15/15/10 is design choice, not empirically optimized.
