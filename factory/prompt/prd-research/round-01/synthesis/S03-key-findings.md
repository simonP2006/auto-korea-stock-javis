---
round: 1
type: synthesis
created: "2026-05-25T23:10:00+09:00"
input_files:
  - "raw/T01-workflow-architect.md"
  - "raw/T02-scenario-explorer.md"
  - "raw/T03-operator-analyst.md"
  - "raw/T04-sustainability-strategist.md"
cross_cutting_axes:
  - "definition-problem"
  - "architecture-convergence"
  - "token-economics"
  - "data-source-risk"
  - "user-profile"
  - "mcp-ecosystem"
---

# S03: Key Findings — Cross-Cutting Discoveries

## Finding 1: "기술적 완성도" Has No Standard Definition

**Importance**: CRITICAL — this is the product's intellectual core.

"기술적 완성도" is NOT a standardized financial term. No published scoring rubric, no academic paper, no industry consensus. It's a composite concept from Korean retail trading communities.

**Closest Western mapping**:
- Minervini SEPA Trend Template + VCP → overall readiness
- Weinstein Stage Analysis → base formation
- Wyckoff Accumulation/Distribution → volume patterns
- IBD Relative Strength Rating → momentum ranking

**Proposed 6-component score** (0-100 composite):
1. MA Alignment Score (이평선 정배열)
2. Base Formation Score (바닥/매물대 정리)
3. Volume Behavior Score (거래량 수축/매집)
4. Momentum Score (RSI/MACD/ADX)
5. Breakout Readiness Score (돌파 임박도)
6. Relative Strength Percentile (상대 강도)

**PRD Implication**: PRD must DEFINE this score system. No reference implementation to copy. Weights are hypotheses requiring iterative calibration.

---

## Finding 2: Architecture Converges to Hybrid (All 4 Teammates Agree)

**The architecture that all 4 perspectives independently arrived at**:

```
Layer 1: OS Scheduler (launchd)
  └── Daily 18:30 auto-trigger (post-market close)

Layer 2: Python Data Pipeline (scripts/)
  ├── collect.py   → pykrx → DuckDB
  ├── analyze.py   → pandas-ta → DuckDB
  ├── score.py     → custom scoring → DuckDB
  └── report.py    → DuckDB → summary.md (top 20-50)

Layer 3: Claude Code Orchestration (.claude/)
  ├── agents/      → data interpreter, technical analyst
  ├── commands/    → /scan, /종목분석, /설정
  ├── hooks/       → installation verification, error handling
  └── skills/      → technical analysis knowledge

Layer 4: User Interface (Claude Code session)
  └── Korean NL input → interpreted results → Naver Finance links
```

**Why convergence**: Each perspective independently reached the same conclusion:
- **WA**: Python handles computation; Claude orchestrates
- **SE**: All priority scenarios need database + scheduler + Python
- **OA**: Separation lets each layer be debuggable independently
- **SS**: Only sustainable path (80-90% token savings)

**Key insight**: Branch A (standalone) "optimized for tokens" IS Branch B (integrated). Optimization converges to the same architecture.

---

## Finding 3: Token Economics Make Branch B Non-Negotiable

| Metric | Branch A | Branch B | Savings |
|---|---|---|---|
| Daily session tokens | 125K-240K | 12K-28K | **80-90%** |
| Monthly (22 days) | 2.75M-5.28M | 264K-880K | **80-85%** |
| Max 20x fitness | Tight to exceeded | Comfortable | Substantial headroom |
| Agent SDK credit ($200/mo) | $40-80/mo consumed | $7-15/mo consumed | **80%+** |
| 6-month sustainability | 4/10 | 8/10 | — |

Branch A's token consumption exceeds comfortable subscription limits for daily usage. Branch B is the survival condition, not an optimization.

**June 15, 2026 billing change**: Agent SDK credit separated ($200/month at API rates). This makes headless automated scans viable within Branch B's lean token profile.

---

## Finding 4: pykrx/KRX Data Source Is the Highest External Risk

**Events already occurred**:
- KRX changed to require OpenAPI Key login
- pykrx-openapi emerged as community alternative
- KRX blocked excessive automated requests (IP-based blocking)

**Current state**: pykrx (v1.2.8) scrapes KRX website directly. Any KRX website structure change breaks it.

**Mitigation architecture** (Data Source Abstraction Layer):
```python
class DataCollector(Protocol):
    def get_daily_prices(self, date: str, market: str) -> DataFrame: ...
    def get_stock_list(self, market: str) -> list[str]: ...

# Implementations (swappable):
class PykrxCollector(DataCollector): ...
class PykrxOpenApiCollector(DataCollector): ...
class KrxDirectApiCollector(DataCollector): ...
class FinanceDataReaderCollector(DataCollector): ...
```

**Priority order**: pykrx (easiest) → pykrx-openapi (KRX official) → direct KRX API → FinanceDataReader (backup)

---

## Finding 5: Target User Is Non-Technical — Installation UX Is Critical

**User's own statement**: "이 시스템을 어떻게 만들지 전혀 모른다" (doesn't know how to build this at all).

**Critical UX requirements** (from Operator Analyst):
- One-command setup (15 min max)
- Single slash command daily operation (`/scan`)
- Korean-language everything (results, errors, explanations)
- Zero debugging capability — system must self-heal

**The bootstrap problem**: Setup hooks are Python-based, but user may not have Python. Shell bootstrap script needed first.

**Progressive disclosure design**: Layer 0 (default `/scan`) → Layer 1 (NL filters "코스닥만") → Layer 2 (flags `--market=kosdaq`) → Layer 3 (config.yaml) → Layer 4 (source code).

---

## Finding 6: Existing Korean Stock MCP Server Ecosystem

| MCP Server | Provider | Capabilities | Relevance |
|---|---|---|---|
| pykrx-mcp | sharebook-kr | KRX data via MCP protocol | Direct Claude Code integration for stock data |
| korea-stock-mcp | jjlabsio | DART + KRX, financial statements | Fundamental data supplement |
| korea-stock-analyzer-mcp | Mrbaeksang | 6 guru strategies + MA/RSI/MACD | Basic technical indicators — foundation to build on |

**Implication**: Don't build from scratch where existing MCP servers can be leveraged. But none implement the full "technical completeness" scoring methodology.

---

## Finding 7: Priority Scenarios

All 4 teammates converged on the same priority ordering:

1. **Phase 1 (MVP)**: After-market close daily screening (A2) — core value proposition
2. **Phase 2**: Individual stock technical deep-dive (B1) — natural "next step" after screening
3. **Phase 3**: Score threshold alerts (C1) — transforms pull-based to push-based

**What NOT to build**: Real-time trading, automated orders, fundamental analysis, charting, news sentiment.

---

## Finding 8: Legal/Regulatory Framing Required

Korean financial regulation restricts unlicensed investment advice. The system must:
- Frame output as "technical analysis screening tool" NOT "investment recommendations"
- Include disclaimers: "투자 판단은 본인 책임", "매수·매도 추천이 아님"
- Use language: "기술적 완성도가 높은 종목" NOT "이 종목을 사세요"
- Design-level embedding of appropriate humility in all outputs
