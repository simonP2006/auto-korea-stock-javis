---
round: 1
type: raw
teammate: scenario-explorer
axis: scenario-landscape
created: "2026-05-25T22:57:00+09:00"
question_summary: "KOSPI/KOSDAQ 종목 기술적 완성도 분석 시스템의 사용 시나리오 전체 지형도, '기술적 완성도' 정의, 대안 도구 조사, 시나리오 우선순위"
assumption_axis: "Claude Code standalone vs external tool integration"
branch_a: "Self-Contained scenarios"
branch_b: "Integrated scenarios"
web_search_count: 28
sources:
  - "pykrx GitHub (sharebook-kr/pykrx)"
  - "pykrx-mcp GitHub (sharebook-kr/pykrx-mcp)"
  - "korea-stock-mcp (jjlabsio/korea-stock-mcp)"
  - "korea-stock-analyzer-mcp (Mrbaeksang)"
  - "FinanceDataReader GitHub"
  - "Korean Quant Investment Cookbook (WikiDocs)"
  - "Korean Quant Investment with Python (GitHub)"
  - "Kiwoom Securities Condition Search documentation"
  - "Kiwoom Condition Search Signal Service"
  - "Korean Brokerage API Comparison (QuantyLab Blog)"
  - "Korea Investment Securities Open Trading API (GitHub)"
  - "TradingView Stock Screener (Korean)"
  - "KRX Open API (Official)"
  - "KRX Data Marketplace"
  - "Mark Minervini Trend Template (Deepvue)"
  - "Mark Minervini SEPA Strategy (FinerMarketPoints)"
  - "VCP Pattern Trading Guide (TradingSim)"
  - "Stan Weinstein Stage Analysis (TraderLion)"
  - "William O'Neil CANSLIM (Wikipedia)"
  - "IBD Relative Strength Rating (GitHub)"
  - "IBD Stock Ratings Explained"
  - "TA-Lib Documentation (WikiDocs Korean)"
  - "pandas-ta (PyPI)"
  - "Korean Stock Data in SQLite (WikiDocs)"
  - "Korean Technical Analysis PDF (Naver)"
  - "Chart Conditions for Rising Stocks (고짹짹, Naver)"
  - "Alpha Vantage MCP"
  - "Technical Analysis Namu Wiki (Korean)"
---

# Scenario Explorer Investigation Report

## 1. Defining "Technical Completeness" (기술적 완성도)

### 1.1 What the Term Means

"Technical completeness" (기술적 완성도) is **not a formally standardized term** in Korean financial literature. There is no single canonical definition, no published scoring rubric, and no widely-cited academic paper defining it as a discrete metric. It is a **composite concept** used by Korean retail traders to describe **how "ready" a stock's chart is for a major breakout move**.

### 1.2 Component Concepts

**A. Base Formation Quality (바닥 다지기 / 베이스 완성)**
- Prolonged sideways consolidation after a decline
- The longer and tighter the base, the higher the "completeness"
- Equivalent to Stan Weinstein's Stage 1 (Basing) and William O'Neil's base patterns

**B. Accumulation Phase Completion (매집 완성도)**
- Evidence that institutional or "force" (세력) players have accumulated shares
- Signals: gradually increasing volume on up-days, decreasing on down-days
- The "매집 완성" signal: volume dries up completely on pullbacks (supply exhaustion), then sudden volume surge
- Price volatility narrows progressively (VCP concept)

**C. Moving Average Alignment (이평선 정배열)**
- "정배열" means: current price > short-term MA > mid-term MA > long-term MA
- Key MAs in Korean markets: 5-day, 20-day, 60-day, 120-day, 200-day (or 240-day)
- Transition from 역배열 through convergence to 정배열 is a key progression

**D. Breakout Readiness (돌파 준비)**
- Stock at or near a clearly defined resistance level (pivot point)
- Volume contracting (calm before the storm)
- Price range tightening (Volatility Contraction Pattern / VCP)

### 1.3 Closest Western Equivalents

| Korean Concept | Western Framework | Key Proponent |
|---|---|---|
| 기술적 완성도 (overall) | SEPA Trend Template + VCP | Mark Minervini |
| 바닥 다지기 | Stage 1 Basing | Stan Weinstein |
| 매집 완성도 | Accumulation/Distribution | Wyckoff Method |
| 이평선 정배열 | Moving Average Alignment | General TA |
| 돌파 준비 | Cup-with-Handle pivot, VCP breakout | William O'Neil, Minervini |
| 상대 강도 | Relative Strength Rating | IBD |

### 1.4 Proposed Scoring Methodology

Since no standard scoring exists, the system must **construct** one:

1. **Minervini Trend Template (8-point checklist)**: Binary pass/fail
2. **Base Pattern Quality Score**: Depth of correction, duration, VCP contractions, volume behavior
3. **Moving Average Alignment Score**: Degree of 정배열, slope of key MAs, price distance from MAs
4. **Relative Strength Percentile**: IBD-style RS rating (weighted 12-month performance)
5. **Volume Behavior Score**: Accumulation/distribution ratio, volume trend, dry-up quality
6. **Breakout Proximity**: Distance to pivot point / resistance level

**Composite Score** = weighted sum, normalized to 0-100.

### 1.5 Key References
- Mark Minervini, "Trade Like a Stock Market Wizard" and "Think and Trade Like a Champion"
- William O'Neil, "How to Make Money in Stocks" (CANSLIM)
- Stan Weinstein, "Secrets for Profiting in Bull and Bear Markets"
- Korean community: Daum Cafe "부자아빠 주식학교," Naver stock communities
- "상승하는 차트의 조건과 차트의 기본기" by 고짹짹

---

## 2. Scenario Landscape Map

### Category A: Daily Screening Workflows

| Scenario | Frequency | Complexity | Automation Potential | Value |
|---|---|---|---|---|
| A1: Morning Pre-Market Scan | Daily | Medium | High | Saves 30-60 min |
| A2: After-Market Close Screening | Daily | Medium | High | **Primary use case** |
| A3: Weekly Summary & Sector Rotation | Weekly | Medium-High | High | Saves 2-3 hours |
| A4: Monthly Portfolio Rebalancing | Monthly | High | Partial | Systematic review |

### Category B: Deep Analysis Workflows

| Scenario | Frequency | Complexity | Automation Potential | Value |
|---|---|---|---|---|
| B1: Individual Stock Deep-Dive | On-demand | High | Partial | Replaces manual chart reading |
| B2: Sector Comparative Analysis | Weekly-Monthly | High | High | Identifies strongest in strongest |
| B3: Market Breadth & Health | Daily-Weekly | Medium | High | Market timing context |
| B4: Historical Backtesting | Ad-hoc | Very High | Medium | Validates scoring system |

### Category C: Alert/Monitoring Workflows

| Scenario | Frequency | Complexity | Automation Potential | Value |
|---|---|---|---|---|
| C1: Score Threshold Alert | Daily | Medium | High | Push-based notification |
| C2: Volume Spike Detection | Daily | Low-Medium | High | Early 세력 activity warning |
| C3: MA Crossover Alerts | Daily | Low | High | Classic signal detection |
| C4: RS Ranking Changes | Weekly | Medium | High | Momentum shift detection |

### Category D: Custom/Advanced Workflows

| Scenario | Frequency | Complexity | Automation Potential | Value |
|---|---|---|---|---|
| D1: Custom Indicator Development | Ad-hoc | Very High | Low | Power user extension |
| D2: Multi-Timeframe Analysis | Daily-Weekly | High | High | Reduces false signals |
| D3: Correlation/Pair Analysis | Ad-hoc | High | Medium | Portfolio diversification |
| D4: Export to External Tools | On-demand | Low-Medium | High | Bridges to brokerage tools |

---

## 3. Alternative Tools & Methods Investigation

### Category A: Korean Brokerage Screeners

**Kiwoom Securities HeroesWorld (키움증권 영웅문 조건검색)**
- Strengths: Real-time data, direct order execution, up to 20 combinable indicators, "영웅검색" AI-powered
- Weaknesses: Windows-only, capacity limits during volatile markets, cannot implement custom composite scoring, no export API
- Cost: Free with brokerage account
- Relationship to our system: **COMPLEMENT** — Kiwoom for execution, our system for scoring/analysis

**Korea Investment Securities**: Only Korean brokerage with a public REST API

### Category B: Korean Financial Data Platforms

**Naver Finance (네이버 증권)**
- Strengths: Free, comprehensive, real-time quotes
- Weaknesses: No custom scoring, no API, no automation
- Relationship: **Our system REPLACES Naver's basic screening**

**KRX Data Marketplace**: Official exchange data, KRX Open API (10,000 calls/day limit)

### Category C: Python-Based Open Source

**pykrx**: KRX + Naver scraping, OHLCV + financial + investor data. ~4 hours for 3 years of all-stock data.
**pykrx-mcp**: MCP server wrapping pykrx for Claude Desktop/Code integration.
**FinanceDataReader**: Multi-source (Yahoo, Naver, KRX), global coverage.
**pandas-ta**: 130+ indicators, pure Python.

**Existing MCP Servers**:
- korea-stock-mcp (jjlabsio): DART + KRX, financial statements
- korea-stock-analyzer-mcp (Mrbaeksang): 6 guru strategies + MA/RSI/MACD — basic but not full completeness scoring

### Category D: Commercial Tools

**TradingView**: Best charting, Pine Script, built-in Korean stock screener. Custom screener needs paid plan ($14.95+/month).
- Relationship: **Our system REPLACES TradingView screening** for "technical completeness"

---

## 4. Scenario Requirements Matrix

### Priority Scenario A2: After-Market Close Daily Screening

| Requirement | Detail |
|---|---|
| Technical Components | Data collector, indicator calculator, scoring engine, results formatter, local storage |
| Data Sources | pykrx for OHLCV + volume (all KOSPI/KOSDAQ) |
| Computation | MAs, RSI, MACD, ATR, volume averages, RS percentile, VCP detection, base pattern recognition |
| Output Format | Ranked table in Markdown (top 20-50 stocks) |
| Claude Code Integration | Python scripts via Bash; results interpreted by Claude |

### Priority Scenario B1: Individual Stock Deep-Dive

| Requirement | Detail |
|---|---|
| Technical Components | Multi-timeframe retrieval, comprehensive indicators, pattern recognition, Claude interpretation |
| Output Format | Detailed report with stage classification, key levels, MA status, accumulation assessment |

---

## 5. Branch A vs B Comparison

**Branch A (Standalone) fully services**: A2, A3, B1, B2, B3, C3, C4, D4
**Branch A limitations**: No persistent database, no real scheduler, slow data collection, no real-time, no charts

**Branch B (Integrated) additionally services**: A1, A4, B4, C1, C2, D1, D2, D3
**Branch B required components**: SQLite/DuckDB, launchd/cron, pykrx + scripts, notification system

**Verdict**: Branch B is necessary for any scenario beyond basic on-demand analysis.

---

## 6. Final Conclusions

### Top 3 Priority Scenarios

1. **After-Market Close Daily Screening (A2)**: Core value proposition. All components exist. Foundation for everything else.
2. **Individual Stock Deep-Dive (B1)**: Natural "second step." Claude's NL capabilities add unique value.
3. **Score Threshold Alert (C1)**: Transforms pull-based to push-based. Where automation provides most time savings.

### Core Components Required by All Priority Scenarios
1. Data Collection Layer (pykrx-based Python scripts)
2. Local Database (SQLite/DuckDB)
3. Technical Indicator Engine (pandas-ta)
4. Scoring Engine (custom Python — Technical Completeness Score)
5. Relative Strength Calculator (IBD-style RS percentile)
6. Output Formatter (Markdown for Claude)
7. MCP Integration (pykrx-mcp or custom)

### Scenarios This System Should NOT Attempt
1. Real-time intraday trading signals
2. Automated order execution
3. Fundamental analysis scoring
4. News sentiment analysis
5. Interactive charting

---

## Parking Lot

| # | Discovery | Source | Follow-up Category |
|---|-----------|--------|-------------------|
| P1 | pykrx-mcp could be extended rather than built from scratch | Alternative Tools | technical |
| P2 | korea-stock-analyzer-mcp has basic technical indicators | Alternative Tools | external-integration |
| P3 | KRX Open API has 10,000 calls/day limit; pykrx not rate-limited but slow | Data Requirements | technical |
| P4 | Korea Investment Securities is the ONLY brokerage with REST API | Alternative Tools | external-integration |
| P5 | No existing tool implements "technical completeness" composite score | Definition | structural-risk |
| P6 | pandas-ta recommended over TA-Lib for macOS | Technical Stack | technical |
| P7 | SQLite is zero-config, adequate for ~3M rows | Architecture | technical |
| P8 | macOS launchd preferred over cron (cron deprecated) | Architecture | technical |
| P9 | Scoring methodology is a creative/domain design task, not engineering | Definition | user-behavior |
| P10 | TradingView Pine Screener as validation benchmark | Alternative Tools | external-integration |
| P11 | VCP detection is algorithmically complex | Scoring Methodology | technical |
| P12 | IBD RS Rating formula is well-documented and implementable | Scoring Methodology | technical |
