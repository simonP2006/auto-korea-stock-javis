---
round: 4
type: raw
teammate: mcp-server-specialist
axis: mcp-ecosystem
investigation_axis: external-integration
created: "2026-05-26T15:00:00+09:00"
question_summary: "MCP server ecosystem assessment for KOSPI/KOSDAQ stock analysis — rich ecosystem vs minimal+custom, server maturity, Claude Code compatibility, Phase 1 vs Phase 2+ roadmap"
assumption_axis: "Rich MCP Ecosystem vs Minimal MCP + Custom Servers"
branch_a: "Branch 1.1 — Rich MCP Ecosystem (maximize existing server ecosystem)"
branch_b: "Branch 1.2 — Minimal MCP + Custom Servers (minimum footprint, build only what's needed)"
web_search_count: 24
local_execution_tags:
  LOCAL_OK: ["mcp-server-duckdb (ktanaka101)", "mcp-server-motherduck", "pykrx-mcp (sharebook-kr)", "kospi-kosdaq-stock-server (dragon1086)", "Sequential Thinking MCP", "Memory MCP", "Playwright MCP (Microsoft)", "Slack Notification MCP", "Filesystem MCP", "Git MCP", "FastMCP custom server SDK", "MCP stdio transport"]
  LOCAL_PARTIAL: ["korea-stock-mcp (requires DART+KRX API key registration)", "Slack via Composio (self-notifications don't trigger)", "Scheduled tasks MCP initialization bug (GitHub #32000, #35899, #43397)"]
  LOCAL_BLOCKED: []
sources:
  - url: "https://github.com/modelcontextprotocol/servers"
    desc: "Official MCP Reference Servers (GitHub)"
  - url: "https://registry.modelcontextprotocol.io/"
    desc: "Official MCP Registry"
  - url: "https://github.com/ktanaka101/mcp-server-duckdb"
    desc: "mcp-server-duckdb by ktanaka101 — ★141, MIT license"
  - url: "https://github.com/motherduckdb/mcp-server-motherduck"
    desc: "mcp-server-motherduck by MotherDuck (official vendor)"
  - url: "https://github.com/sharebook-kr/pykrx-mcp"
    desc: "pykrx-mcp by sharebook-kr (pykrx maintainer org) — MIT, 2026"
  - url: "https://github.com/dragon1086/kospi-kosdaq-stock-server"
    desc: "kospi-kosdaq-stock-server — ★59, FastMCP-based"
  - url: "https://github.com/jjlabsio/korea-stock-mcp"
    desc: "korea-stock-mcp — DART + KRX data, ISC license"
  - url: "https://github.com/microsoft/playwright-mcp"
    desc: "Playwright MCP (Microsoft) — browser automation standard"
  - url: "https://code.claude.com/docs/en/mcp"
    desc: "Claude Code MCP Documentation"
  - url: "https://gofastmcp.com/tutorials/create-mcp-server"
    desc: "FastMCP Python SDK tutorial"
  - url: "https://github.com/jlowin/fastmcp"
    desc: "FastMCP GitHub"
---

# T01: MCP Server Specialist — Rich Ecosystem vs Minimal+Custom

## Executive Summary

Phase 1 needs **zero MCP servers** — the batch pipeline (launchd → python3 main.py) has no interactive Claude Code session to consume MCP tools. Phase 2+ interactive analysis benefits from **DuckDB MCP (read-only)** as the primary addition, with **pykrx-mcp** as a Phase 3 candidate pending stability verification. Three Korean stock-specific MCP servers were discovered during research.

---

## Branch 1.1: Rich MCP Ecosystem

### MCP Server Ecosystem Current State (2025-2026)

**Official Reference Servers** (Anthropic-maintained, 7 active):

| Server | Purpose | Relevance | Status |
|--------|---------|-----------|--------|
| Everything | Test server | Dev/testing only | [LOCAL-OK] |
| Fetch | HTTP requests | Could fetch financial APIs | [LOCAL-OK] |
| Filesystem | File read/write | Redundant — Claude Code has built-in tools | [LOCAL-OK] |
| Git | Git operations | Useful for version control | [LOCAL-OK] |
| Memory | Knowledge graph (JSONL) | Cross-session stock knowledge | [LOCAL-OK] |
| Sequential Thinking | Dynamic problem-solving | Complex multi-stock reasoning | [LOCAL-OK] |
| Time | Timezone conversion | Minimal value | [LOCAL-OK] |

13 servers archived to `github.com/modelcontextprotocol/servers-archived` in 2025 (Slack, Postgres, Puppeteer, etc. handed to vendor maintenance).

**Ecosystem scale**: 14,000+ servers on PulseMCP, 97M+ cumulative SDK downloads.

### Korean Stock Market MCP Servers

#### pykrx-mcp (sharebook-kr) — MOST RELEVANT
- From the pykrx maintainer team itself
- Wraps pykrx as MCP server — KOSPI/KOSDAQ/KONEX, prices, financials
- Maturity: **[UNVERIFIED]** — very new (2026), no adoption metrics found
- Value: Claude Code could query stock data interactively (vs batch-only pipeline)
- Config: `"command": "uvx", "args": ["pykrx-mcp"]`

#### kospi-kosdaq-stock-server (dragon1086) — ★59
- OHLCV, market cap, PER/PBR/Dividend, investor trading volume
- Install: `npx -y @smithery/cli install @dragon1086/kospi-kosdaq-stock-server --client claude`

#### korea-stock-mcp (jjlabsio)
- DART disclosure + KRX daily prices + XBRL financial statements
- **Requires**: DART API key + KRX API key (both free, registration needed)
- Unique: corporate filing data not available in other servers

### DuckDB MCP Servers

#### ktanaka101/mcp-server-duckdb — ★141
- SQL query tool, `--readonly` flag for safety, reusable connections
- Config: `claude mcp add duckdb uvx mcp-server-duckdb -- --db-path /path/to/stocks.duckdb --readonly`
- MIT license, well-documented

#### motherduckdb/mcp-server-motherduck — Vendor-backed
- Local DuckDB + MotherDuck cloud modes
- **Key advantage**: Won't hold file lock in read-only mode (coexists with write connections)
- JSON result limit: 1024 rows / 50,000 chars (configurable)

### MCP Configuration in Claude Code

```json
{
  "mcpServers": {
    "server-name": {
      "command": "executable",
      "args": ["arg1", "arg2"],
      "env": { "VAR": "value" },
      "type": "stdio"
    }
  }
}
```

**3 configuration scopes**: Project (`.claude/settings.json`), User (`~/.claude/settings.json`), Local (`~/.claude.json`).

**Performance**: Post-January 2026, MCP Tool Search defers loading — reduces overhead from ~77K to ~8.7K tokens (85% reduction). Productive setups: 2-5 servers. No hard limit.

### Rich Ecosystem Recommended Stack (Phase 2+, 4 servers)

1. **DuckDB MCP** (MotherDuck or ktanaka101) — Direct SQL queries
2. **pykrx-mcp** (sharebook-kr) — Live Korean market data
3. **Sequential Thinking** (official) — Complex multi-stock reasoning
4. **Slack Notification** — Alert delivery

---

## Branch 1.2: Minimal MCP + Custom Servers

### Minimum MCP footprint for Phase 1: ZERO

Phase 1 is a batch pipeline triggered by launchd. No interactive Claude Code session exists at pipeline runtime. MCP servers are inherently interactive (Claude calls tools during a conversation).

### When to add MCP

| Phase | MCP Addition | Trigger |
|-------|-------------|---------|
| Phase 1 | None | Batch pipeline has no conversation context |
| Phase 2 | DuckDB MCP (read-only) | Interactive `/scan` needs ad-hoc SQL |
| Phase 2+ | pykrx-mcp (if needed) | Live data beyond batch collection |
| Phase 3 | Custom unified server (maybe) | If multi-hop MCP calls become frequent |

### Bash + Hooks handle Phase 1 perfectly

- `python3 main.py` via Bash tool — full pipeline
- DuckDB CLI queries via Bash — ad-hoc debugging
- File I/O via Read/Write/Edit — native Claude Code
- Safety guardrails via Hooks — 14+ existing scripts

### Custom MCP Server Development

**FastMCP SDK** (Python): 30 minutes for minimal server, 2-4 hours for production.

```python
from fastmcp import FastMCP
mcp = FastMCP("Stock Analysis")

@mcp.tool
def get_stock_ohlcv(ticker: str, start_date: str, end_date: str) -> dict:
    from pykrx import stock
    df = stock.get_market_ohlcv(start_date, end_date, ticker)
    return df.to_dict()
```

**Custom server justified only when**: existing servers don't cover the need AND Bash+Hooks are insufficient. For this project: Phase 3 at earliest.

---

## Comparison: Branch 1.1 vs 1.2

| Dimension | Rich (1.1) | Minimal (1.2) | Winner |
|-----------|-----------|--------------|--------|
| Phase 1 servers | 0 | 0 | Tie |
| Phase 2 servers | 4 | 1 (DuckDB) | Depends on need |
| Setup complexity | Medium | Low | 1.2 |
| Token overhead | ~8.7K | ~2K | 1.2 |
| Interactive capability | Full | SQL only | 1.1 |
| Maintenance | 4 community servers | 1 mature server | 1.2 |
| **Recommendation** | Phase 2+ when interactive is primary | When batch results suffice | **1.2 for Phase 1** |

---

## Parking Lot

1. **pykrx-mcp stability** [UNVERIFIED]: Needs hands-on testing before Phase 2+ commitment
2. **Scheduled tasks + MCP bug**: GitHub #32000, #35899, #43397 — MCP connector init fails in scheduled/remote tasks
3. **MotherDuck vs ktanaka101 DuckDB**: Direct comparison test needed (file-lock, result format, error handling)
4. **korea-stock-mcp DART integration**: Worth investigating if disclosure data adds analytical value
5. **Memory MCP for cross-session knowledge**: Could persist stock patterns across sessions
6. **Custom unified MCP server**: Evaluate after Phase 2 usage patterns emerge
