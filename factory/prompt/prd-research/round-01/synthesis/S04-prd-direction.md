---
round: 1
type: synthesis
created: "2026-05-25T23:10:00+09:00"
input_files:
  - "synthesis/S01-convergence.md"
  - "synthesis/S02-risk-register.md"
  - "synthesis/S03-key-findings.md"
cross_cutting_axes:
  - "prd-section-design"
  - "quality-criteria"
---

# S04: PRD.md Section-by-Section Direction Advice

> This file advises HOW to write each PRD section. It does NOT contain PRD content itself.

## Core Perspective: "Two Engines, One Product"

The system is two independent engines:
- **Engine 1**: Python data pipeline (collect → analyze → score → filter) — deterministic, testable, zero tokens
- **Engine 2**: Claude Code interpretation layer (interpret → explain → interact) — intelligent, adaptive, token-consuming

PRD must define the boundary between these two engines clearly. Blurred boundaries (Claude computing, Python interpreting) destroy sustainability.

---

## Section 1: Problem Statement

**Approach**: Write from user's perspective. Why does this system need to exist?
**Must include**:
- Physical impossibility of manually reviewing ~2,500 KOSPI/KOSDAQ stocks daily
- Existing tools (Kiwoom HTS 조건검색, Naver Finance, TradingView) cannot compute custom composite "technical completeness" scores
- The gap: no tool provides AI-interpreted, Korean-language technical completeness screening for the full Korean stock universe
**Caution**: Acknowledge this system COMPLEMENTS (not replaces) existing tools. Kiwoom for execution, TradingView for charting, our system for scoring/discovery.

## Section 2: Product Definition — Scoring Methodology (MOST CRITICAL SECTION)

**Approach**: This IS the intellectual core. No standard exists — PRD must construct the definition.
**Must include**:
- 6 sub-score definitions with exact formulas (mapping to pandas-ta indicators)
- Default weights and their rationale (Minervini/Weinstein/Wyckoff references)
- Score interpretation thresholds (80+ = "완성 임박", 60-80 = "진행 중", <40 = "미성숙")
- Openness declaration: weights are hypotheses, calibrated through 3-month operational data
**Caution**: This section's quality determines entire product value. Under-specifying here means implementation has no anchor.

## Section 3: Architecture

**Approach**: 4-Layer hybrid architecture with clear responsibility separation.
**Must include**:
- Architecture diagram (Scheduler → Python Pipeline → Claude Code → User)
- Technology stack choices with trade-off rationale (DuckDB vs SQLite, pandas-ta vs ta-lib, pykrx vs alternatives)
- Data flow diagram (pykrx → DuckDB → summary.md → Claude → Korean results)
- Data source abstraction layer design (pykrx instability response)
- DuckDB schema design (stocks, daily_prices, technical_indicators, completeness_scores)
**Caution**: Don't skip the "why" for each technology choice. Future maintainers need trade-off context.

## Section 4: User Experience

**Approach**: General user as primary design target. Progressive disclosure.
**Must include**:
- Installation journey: shell bootstrap → Python auto-install → deps → verify (target: 15 min)
- Daily use journey: `/scan` → Korean results → Naver/HTS confirmation (target: 5 min)
- Error scenarios: Korean error messages + auto-retry + cache fallback
- Progressive disclosure layers: Layer 0 (default) → Layer 1 (NL) → Layer 2 (flags) → Layer 3 (config) → Layer 4 (source)
- Trust building strategy: alignment with user intuition + "candidates not recommendations" framing
**Caution**: Every feature must pass: "Will a non-technical user actually do this?"

## Section 5: Priority Scenarios (Phased Delivery)

**Approach**: 3-phase incremental delivery.
**Must include**:
- Phase 1 (MVP): After-market daily screening → top stock list + Korean interpretation
- Phase 2: Individual stock deep-dive (`/종목분석 삼성전자`)
- Phase 3: Score threshold alerts (launchd + macOS notification)
- Explicit non-goals: real-time signals, auto-trading, fundamental analysis, charting
**Caution**: Each phase must be independently valuable. Phase 2 shouldn't require Phase 3.

## Section 6: Data Strategy

**Approach**: Data source instability is the #1 external risk. Treat as first-class concern.
**Must include**:
- Primary source: pykrx (KRX direct scraping)
- Secondary: pykrx-openapi (KRX OpenAPI Key-based)
- Tertiary: FinanceDataReader (Naver Finance-based)
- Abstraction layer design (swap = 1 file change)
- KRX rate limit mitigation (rate limiting, IP blocking avoidance)
- DuckDB storage projections: ~50-100MB/year, 5-year ~500MB
- Data freshness strategy: daily incremental update, not full re-fetch
**Caution**: Don't treat data source abstraction as "nice to have." It's survival infrastructure.

## Section 7: Sustainability & Token Economics

**Approach**: Quantified sustainability analysis. Numbers, not adjectives.
**Must include**:
- Per-session token budget: 12K-28K (Branch B architecture)
- Monthly projection: 264K-880K tokens (22 trading days)
- Max subscription fitness analysis
- June 15, 2026 Agent SDK billing change impact
- Maintenance time estimate: 2-4 hours/month
- 6-month sustainability rating: 8/10 (Branch B)
- Anti-patterns to avoid: raw data in context, Claude as calculator, business logic in hooks
**Caution**: Token sustainability is NOT an optimization goal — it's a survival condition.

## Section 8: Risk Register

**Approach**: TOP 5 risks with verification plans.
**Must include**:
- Each risk: impact, probability, verification method, mitigation, owner
- Legal/regulatory framing (Korean financial regulation)
- Parking lot items assigned to follow-up investigation categories
**Caution**: Don't bury the pykrx/KRX risk. It's #1 and already partially manifesting.

## Section 9: Non-Goals (Explicit Exclusions)

**Approach**: What this system will NOT do, and why.
**Must include**:
- Real-time intraday signals (different architecture class)
- Automated order execution (regulatory/risk domain)
- Fundamental analysis scoring (separate domain, existing MCP servers handle it)
- News sentiment analysis (separate NLP project)
- Interactive charting (use TradingView for this)
- Each item: "never" vs "later" classification with revisit trigger
**Caution**: Non-goals prevent scope creep. Explicit exclusions are as important as inclusions.

---

## Quality Criteria for PRD

A "탁월한 PRD" (excellent PRD) from this research must satisfy:

1. **Scoring methodology is fully specified** — someone could implement it from the PRD alone
2. **Architecture boundary is crystal clear** — which engine does what, no ambiguity
3. **User journey is realistic** — tested against "non-technical user" constraint
4. **Token budget is quantified** — not "efficient" but "12K-28K per session"
5. **Risk #1 (data source) has concrete mitigation** — abstraction layer design specified
6. **Legal framing is embedded** — not an afterthought disclaimer but design-level constraint
7. **Non-goals are explicit** — prevents future scope creep

---

## Gaps Requiring Follow-Up Before PRD Finalization

| Gap | Impact on PRD | Suggested Resolution |
|-----|---------------|---------------------|
| Scoring weights/thresholds have no empirical basis | Section 2 incomplete | Declare as "initial hypothesis"; define calibration protocol |
| KRX data settlement timing unknown | Section 6 (launchd schedule) | Test pykrx data availability at various post-close times |
| Adjusted price (수정주가) handling unclear | Section 2 (indicator accuracy) | Verify pykrx `adjusted` parameter behavior |
| User's investment style not confirmed | Section 2 (weight calibration) | Ask user before PRD finalization |
| pykrx-openapi not tested | Section 6 (fallback viability) | Prototype test in follow-up investigation |
| macOS sleep/wake + launchd reliability | Section 5 Phase 3 | Test on actual macOS hardware |
