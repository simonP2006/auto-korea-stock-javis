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
  - "risk-assessment"
  - "parking-lot-integration"
---

# S02: Risk Register + Parking Lot Integration

## TOP 5 Risk Assumptions

### 1. pykrx Will Remain Functional for Data Collection
- **Impact**: CRITICAL (no data = entire system worthless)
- **Probability**: HIGH (KRX already changed to require OpenAPI Key login)
- **Verification**: Test pykrx-openapi + direct KRX API + FinanceDataReader as alternatives
- **Mitigation**: Data source abstraction layer (mandatory Green Zone component)
- **Risk Owner**: Workflow Architect + Sustainability Strategist
- **Source**: WA-P5, SE-P3, OA-P1, SS (KRX OpenAPI Key change)

### 2. Scoring System Will Produce Useful Stock Selections
- **Impact**: CRITICAL (useless results = user abandonment)
- **Probability**: MEDIUM (no validation data exists yet)
- **Verification**: 6-month historical backtest + user cross-validation
- **Mitigation**: Initial weights from Minervini/Weinstein (proven frameworks); iterative calibration
- **Risk Owner**: Scenario Explorer
- **Source**: SE-P5, SE-P9, OA (trust problem)

### 3. Non-Technical User Can Install Python Environment
- **Impact**: HIGH (installation failure = can't start)
- **Probability**: HIGH (macOS has no user-installable Python since 12.3)
- **Verification**: Test on stock macOS with no developer tools
- **Mitigation**: Shell bootstrap script + uv-based auto-installation
- **Risk Owner**: Operator Analyst
- **Source**: OA-P9 (bootstrap chicken-and-egg), OA (Branch B installation analysis)

### 4. Claude Code Max Subscription Limits Remain Sufficient
- **Impact**: HIGH (limit exceeded = service interruption)
- **Probability**: MEDIUM (Branch B is comfortable; March 2026 tightening precedent)
- **Verification**: Prototype execution + actual token consumption measurement
- **Mitigation**: Python-native computation (80-90% savings); use Sonnet for routine, Opus for deep-dive
- **Risk Owner**: Sustainability Strategist
- **Source**: SS (token consumption analysis), SS (subscription limits)

### 5. User Will Use Results Appropriately (Not Over-Trust)
- **Impact**: MEDIUM (legal/ethical risk under Korean financial regulation)
- **Probability**: MEDIUM
- **Verification**: N/A (behavioral assumption)
- **Mitigation**: Frame as "analysis candidates" not "buy recommendations"; mandatory disclaimers; 한국 금융 규제 준수
- **Risk Owner**: Operator Analyst
- **Source**: OA-P3 (financial regulation risk)

---

## Integrated Parking Lot

All parking lot items from 4 teammates, merged and deduplicated, categorized for follow-up.

### Technical Verification Required

| # | Item | Source | PRD Decision at Risk |
|---|------|--------|---------------------|
| T1 | pandas-ta vs ta-lib performance benchmark (2,500 stocks x 250 days x 20 indicators) | WA-P7 | Installation complexity vs processing speed |
| T2 | VCP pattern detection algorithm complexity (successive contraction detection) | SE-P11 | Scoring engine implementation difficulty estimate |
| T3 | Agent Teams experimental flag stability | WA-P3 | Parallel processing architecture reliability |
| T4 | DuckDB Parquet support → eliminate CSV intermediates | WA-P8 | Pipeline simplification |
| T5 | Historical performance validation / backtesting infrastructure | OA-P4 | Scoring system credibility |
| T6 | "2,500 stocks in 10 minutes" performance budget — pykrx may take 15-30 min | OA-P8 | User patience threshold; incremental/cached scanning needed |
| T7 | Claude Code security vulnerabilities (CVE-2025-59536, CVE-2026-21852) | SS | Security review for financial data hooks |
| T8 | `uv` as dependency management replacement for pip/venv | SS | Long-term maintenance strategy |

### External Integration Verification Required

| # | Item | Source | PRD Decision at Risk |
|---|------|--------|---------------------|
| E1 | pykrx-openapi feature completeness and stability | SS | Data source fallback strategy |
| E2 | KRX request rate limits (per-minute/hour exact numbers) | WA-P1, SS | Data collection schedule design |
| E3 | Korea Investment Securities REST API for real-time data | SE-P4 | Future real-time feature expansion |
| E4 | KRX trading hours extension to 12 hours (mid-2026) | SS | launchd scheduling time adjustment |
| E5 | pykrx-mcp batch processing capability | WA-P1 | MCP vs Bash script integration decision |
| E6 | korea-stock-analyzer-mcp as complement | SE-P2 | Leveraging existing MCP infrastructure |
| E7 | Claude Cowork compatibility for non-technical UX | OA-P2 | General user interface strategy |

### User Behavior Verification Required

| # | Item | Source | PRD Decision at Risk |
|---|------|--------|---------------------|
| U1 | User behavior after receiving results (Naver? HTS? code search?) | OA-P10 | Output format optimization |
| U2 | Scoring methodology co-design (user domain knowledge) | SE-P9 | Weight/threshold initial values |
| U3 | User's actual investment style/philosophy | Unaddressed | Score weight calibration |
| U4 | TradingView Pine Screener as validation benchmark | SE-P10 | Cross-validation strategy |

### Structural Risk Exploration Required

| # | Item | Source | PRD Decision at Risk |
|---|------|--------|---------------------|
| R1 | Korean financial regulation — investment advice licensing | OA-P3 | Disclaimer and framing strategy |
| R2 | Cloud Routines cannot access local files | WA-P2 | Scheduling architecture confirmation |
| R3 | June 15, 2026 Agent SDK billing separation: $200/month credit | SS | Headless mode viability |
| R4 | Max 20x limits hit in 19 minutes (March 2026 precedent) | SS | Token budget planning uncertainty |
| R5 | Python bootstrap chicken-and-egg (setup hooks need Python) | OA-P9 | Installation architecture |
| R6 | Adjusted price (수정주가) handling in pykrx | Unaddressed | Technical indicator calculation accuracy |
| R7 | KRX data settlement timing (market close → data available) | Unaddressed | launchd schedule time |
| R8 | macOS sleep/wake behavior with launchd | Unaddressed | Daily automation reliability |
