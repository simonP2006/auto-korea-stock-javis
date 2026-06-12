---
round: 1
type: raw
teammate: sustainability-strategist
axis: sustainability
created: "2026-05-25T23:06:00+09:00"
question_summary: "KOSPI/KOSDAQ 기술적 완성도 분석 시스템의 토큰 경제학, 구독 한도, 유지보수 부담, 확장 한계, 장기 지속 가능성"
assumption_axis: "Claude Code standalone vs external tool integration"
branch_a: "Self-Contained (Claude Code standalone)"
branch_b: "Integrated (external tool integration)"
web_search_count: 20
sources:
  - "Claude Code Pricing 2026 (verdent.ai)"
  - "Claude Code Pricing Every Plan Explained (ssdnodes.com)"
  - "Claude Code Rate Limits & Usage Quotas (truefoundry.com)"
  - "Max 20x plan hitting daily limit (GitHub issue #54714)"
  - "Why Claude Max Users Are Leaving (ofox.ai)"
  - "Claude Code Agents 2026 (cloudzero.com)"
  - "Claude's $200 Agent SDK Credit (claudefa.st)"
  - "Anthropic June 15 Billing Change (codersera.com)"
  - "1M context GA for Opus 4.6 and Sonnet 4.6 (claude.com)"
  - "pykrx GitHub Repository"
  - "pykrx PyPI"
  - "pykrx-openapi KRX OpenAPI documentation"
  - "DuckDB Benchmarks Over Time"
  - "Practical Limits of DuckDB on Commodity Hardware (dev.to)"
  - "My First Billion Rows in DuckDB (towardsdatascience.com)"
  - "Claude Code Hooks Complete Reference 2026 (thepromptshelf.dev)"
  - "Claude Code Changelog"
  - "Claude Code Batch Processing Guide (smartscope.blog)"
  - "Claude Code Headless Mode Guide (amux.io)"
  - "Python Virtual Environments Primer (realpython.com)"
---

# Sustainability Investigation Report

## Branch A: Self-Contained (Claude Code Standalone)

### 1. Token Consumption Analysis

**Per-Session Token Estimation:**

| Workflow Phase | Token Estimate |
|---|---|
| Orchestrator instructions + CLAUDE.md | 5,000-10,000 |
| Sub-agent spawning | 3,000-6,000 per agent |
| Script execution via Bash (2,500 stocks) | 15,000-40,000 |
| Raw data reading & parsing | 20,000-60,000 |
| Scoring/ranking interpretation | 5,000-15,000 |
| User interaction | 2,000-5,000 |

**Estimates by complexity:**

| Level | Tokens | Description |
|---|---|---|
| Simple scan | 30,000-50,000 | Run script, read top-20 summary |
| Full analysis | 80,000-150,000 | Full pipeline, Claude interprets |
| Deep-dive (1 stock) | 15,000-30,000 | Detailed single stock analysis |
| Full daily session | 125,000-240,000 | Scan + 3 deep-dives + follow-up |

**Monthly projection (22 trading days):**
- Conservative: 660K-1.1M tokens/month
- Realistic: 2.75M-5.28M tokens/month
- Heavy: 5M-10M tokens/month

### 2. Claude Code Max Subscription Limits

**Current state (May 2026, post-May 6 doubling):**

| Plan | Price | 5-Hour Window | Weekly Compute Hours |
|---|---|---|---|
| Pro | $20/month | ~10-45 prompts | ~40-80 Sonnet hours |
| Max 5x | $100/month | ~225 prompts | ~240 Sonnet / 24 Opus hours |
| Max 20x | $200/month | ~900 prompts | ~480 Sonnet / 40 Opus hours |

**Key constraints:**
1. Usage shared between Claude.ai chat AND Claude Code
2. March-April 2026: Max 20x users hit daily limits in 19 minutes (since doubled)
3. **June 15, 2026 billing change**: Agent SDK/headless usage moves to separate $200/month credit at API rates
4. No credit rollover

**Can daily screening be sustained on Max 20x?**
- Interactive: Possible but tight (2.75M-5.28M tokens/month within limits IF no other Claude usage)
- Headless (post-June 15): $200 credit at API rates → ~4-6M tokens/month total. Feasible for lean workflow.
- **Verdict**: Sustainable for lean workflow; fragile for rich workflow.

### 3. Token Optimization

| Strategy | Savings | Complexity |
|---|---|---|
| Push ALL computation to Python | 60-80% | Medium |
| Summary-first: only top-N results | 40-60% | Low |
| Avoid raw data in Claude context | 50-70% | Medium |
| Headless mode for automated runs | 15-25% | Low |
| Cache interpretive analysis | 20-30% on repeats | Medium |
| Use Sonnet instead of Opus for routine scans | 3-5x cheaper on API | Low |

**Fundamental insight**: Every Branch A optimization converges toward Branch B. Branch A "optimized" IS Branch B.

### 4. Maintenance Complexity

**Claude Code update impact:**
- Frequent updates (v2.1.141+ as of May 2026). Breaking changes occur.
- Sub-agent behaviors change across model versions (Opus 4.7 has API breaking changes vs 4.6).
- Hook API expanded from ~12 to 27+ events.
- No built-in regression testing framework.

**Configuration drift risk: HIGH** for Branch A. Natural language instructions accumulate ambiguity. No type system, no compiler, no linter.

**Debugging difficulty**: When Claude Code is orchestrator AND executor, debugging requires loading entire conversation context, which may exceed context window. No persistent logs.

### 5. Scaling Limits

| Dimension | Branch A Ceiling |
|---|---|
| Stock universe | ~5,000 before unmanageable |
| Scoring complexity | Limited to context window |
| Multiple screeners | 2-3 strategies before daily limits |
| Team collaboration | Not supported |
| Backtesting | Essentially impossible |

---

## Branch B: Integrated (External Tool Integration)

### 1. Token Consumption Analysis

| Workflow Phase | Tokens |
|---|---|
| Python pipeline (collect, compute, score) | **0** |
| Load summary report | 2,000-5,000 |
| Claude interprets/explains | 3,000-8,000 |
| User interaction | 2,000-5,000 |
| Deep-dive (1 stock) | 5,000-10,000 |
| **Total per session** | **12,000-28,000** |

**Monthly projection (22 trading days):**
- Conservative: 264K-440K tokens/month
- Realistic: 440K-880K tokens/month
- Heavy: 880K-1.32M tokens/month

**Comparison:**

| Metric | Branch A | Branch B | Savings |
|---|---|---|---|
| Daily tokens | 125K-240K | 12K-28K | **80-90%** |
| Monthly tokens | 2.75M-5.28M | 440K-880K | **80-85%** |
| Agent SDK credit | $40-80/month | $7-15/month | **80%+** |

### 2. Maintenance Complexity

**Python ecosystem:**

| Component | Update Freq | Breaking Risk | Mitigation |
|---|---|---|---|
| pykrx | Active | **HIGH** (KRX changed to require OpenAPI Key) | Abstract data layer, pin version |
| pandas | Quarterly | Medium | Pin in requirements.txt |
| pandas-ta | Infrequent | Low | Pin version |
| DuckDB | Quarterly | Low | Good backward compat, pin version |
| Python | Annual | Low for 3.10-3.13 | Use pyenv or uv |

**Critical finding**: KRX changed to require login/OpenAPI Key. `pykrx-openapi` is community alternative. Highest maintenance risk in entire system.

**Config locations: 5** (config.yaml, DuckDB schema, CLAUDE.md, launchd plist, requirements.txt) — more than Branch A but each well-scoped with standard tooling.

### 3. Debugging

**Advantages**: Each component has own logs (Python, DuckDB, launchd, Claude Code). Each testable in isolation.

**Disadvantages**: More integration points = more failure modes. "Scan didn't run" — was it launchd? Python? pykrx? DuckDB? network?

**Net assessment**: Easier than Branch A because failures are specific and inspectable.

### 4. Scaling Limits

**DuckDB storage growth:**

| Duration | Rows | Size | Performance |
|---|---|---|---|
| 1 year | 12.5M | 50-100 MB | Sub-second |
| 3 years | 37.5M | 150-300 MB | Sub-second |
| 5 years | 62.5M | 250-500 MB | < 1 second |

**Scaling pathways:**

| Dimension | Capability |
|---|---|
| Add KONEX (+1,500 stocks) | Change one config parameter |
| Add foreign stocks | Add new data source module |
| More indicators / ML scoring | Add Python functions only |
| Multiple strategies | Duplicate config files |
| Backtesting | Direct SQL on DuckDB, zero tokens |
| Team collaboration | Share DuckDB + config via Git |

### 5. Long-Term Assessment

**6-month projection:**

| Factor | Branch A | Branch B |
|---|---|---|
| Maintenance hours/month | 4-8 hrs | 2-4 hrs |
| Most likely failure | Token limit exhaustion | pykrx breaking change |
| Maintenance debt | High (prompt complexity) | Low (structured code) |

**1-year projection:**

| Factor | Branch A | Branch B |
|---|---|---|
| Survived Claude update? | HIGH RISK | LOW RISK (Claude is display only) |
| DB size? | N/A | < 200MB |
| Usage pattern | Degraded to weekly (token fatigue) | Expanded (daily auto + on-demand) |

---

## Final Comparison: Sustainability Ratings

| Timeframe | Branch A | Branch B |
|---|---|---|
| 6-month | **4/10** | **8/10** |
| 1-year | **2/10** | **7/10** |
| 2-year | **1/10** | **6/10** |

### Biggest Bottleneck

| Branch | Bottleneck |
|---|---|
| Branch A | **Token economics** — cost of Claude processing 2,500 stocks daily is unsustainable |
| Branch B | **Data source reliability** — pykrx dependency on KRX's interface |

---

## Must-Have Components for Sustainability

### Top 3 Essential

1. **Data Source Abstraction Layer**
   - KRX already changed API. Without abstraction, ~60% chance of breaking within 12 months.
   - Complexity: LOW-MEDIUM. Python interface with swappable implementations.

2. **Python-Native Computation Pipeline (External to Claude Code)**
   - 80-90% token savings. Difference between viable and not viable.
   - Complexity: MEDIUM. ~500-1,000 lines of Python.

3. **Automated Scheduling with Health Monitoring (launchd + watchdog)**
   - Without automation, behavioral decay: daily → weekly → monthly → abandoned in 3-6 months.
   - Complexity: LOW. One plist file + one health check script.

### Top 3 Anti-Patterns to Avoid

1. **Loading raw stock data into Claude's context window**
   - Can consume entire monthly token budget in days.
   - Correct: Python processes everything; Claude sees only summary.

2. **Using Claude as the scoring/calculation engine**
   - Wasteful, non-reproducible, untestable.
   - Correct: All scoring in Python with pytest coverage.

3. **Tight coupling between Claude Code hooks and business logic**
   - Hook APIs change. Business logic in hooks is untestable.
   - Correct: Hooks do infrastructure only; business logic in standalone Python.

---

## Parking Lot

| Discovery | Source | Follow-Up Category |
|---|---|---|
| KRX requires OpenAPI Key login; pykrx-openapi is alternative | Branch B | external-integration |
| June 15 Agent SDK billing: $200/month credit for headless | Branch A | structural-risk |
| KRX blocked access due to excessive pykrx traffic | Branch B | external-integration |
| Claude Code security vulnerabilities (CVE-2025-59536, CVE-2026-21852) | Both | technical |
| KRX extending trading hours to 12 hours by mid-2026 | Branch B | external-integration |
| Max 20x limits hit in 19 minutes during March 2026 | Branch A | structural-risk |
| pykrx-mcp exists as alternative integration path | Branch B | external-integration |
| DuckDB 1.4.0 adds encryption (AES-256-GCM) | Branch B | technical |
| `uv` replacing traditional venv/pip | Branch B | technical |
| Interactive and Agent SDK credits now separate post-June 15 | Both | user-behavior |
