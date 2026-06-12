---
round: 1
type: raw
teammate: operator-analyst
axis: user-experience
created: "2026-05-25T23:00:00+09:00"
question_summary: "KOSPI/KOSDAQ 기술적 완성도 분석 시스템의 사용자 유형별 경험, 설치 마찰, 에러 복구, 신뢰 구축 전략"
assumption_axis: "Power User vs General User"
branch_a: "Power User (파워 유저 — 복잡한 멀티에이전트 설계자)"
branch_b: "General User (일반 사용자 — 단순 자동화 사용자)"
web_search_count: 33
sources:
  - "How to Use Claude Code: Slash Commands, Agents, Skills (producttalk.org)"
  - "Claude Code Cheat Sheet 2026 (blakecrosley.com)"
  - "Claude Code 2026 Complete Beginner's Guide (godofprompt.ai)"
  - "Slash Commands in the SDK (Claude Code Docs)"
  - "Mac Automation Guide (timingapp.com)"
  - "Raycast Manual"
  - "pykrx GitHub Repository"
  - "AI Korean Stock Market DART & KRX MCP Server (skywork.ai)"
  - "Korean Stock Market MCP Server Features (fastmcp.me)"
  - "Claude Code Setup Hooks (claudefa.st)"
  - "Configure Claude Code with uv (pydevtools.com)"
  - "Claude Code Breaking Python Environment — UV fix (vibe-eval.com)"
  - "Hooks reference (Claude Code Docs)"
  - "What Is Claude Cowork (itech4mac.net)"
  - "Claude Cowork Overview (smartscope.blog)"
  - "Cowork product page (claude.com)"
  - "Get started with Claude Cowork (support.claude.com)"
  - "InvestSkill GitHub"
  - "Claude Trading Skills GitHub"
  - "Claude Equity Research GitHub"
  - "pykrx PyPI"
  - "pandas-ta PyPI"
  - "launchd scheduling on Mac (maketecheasier.com)"
  - "Scheduling Python Scripts On Mac (restack.io)"
  - "키움증권 영웅문 HTS 설치 가이드 (soomter.com)"
  - "TradingView Stock Screener (Korean)"
  - "Korea Investment Securities Open API GitHub"
---

# Operator Analyst Investigation Report

## Executive Summary

This report investigates user experience from two perspectives: a technically skilled Power User (Branch A) and a non-technical General User (Branch B). The investigation reveals a fundamental tension between these audiences, but identifies a viable "progressive disclosure" architecture. The General User is the primary design target, matching the actual user profile.

---

## Branch A: Power User Investigation

### 1. Persona Detail

**Background**: Developer or quantitative trader, Claude Code Max subscriber, Python environment already configured.
**Current workflow**: TradingView + manual chart review of 50-200 stocks, misses ~2,300 stocks.
**Core frustration**: Coverage gap — good stocks exist outside their watchlist.
**Expectation**: Tool that extends their eyeballs across the entire market, not one that replaces judgment.

### 2. Must-Have Components

1. **Transparent scoring algorithm** — see exactly how scores are computed, validate against own analysis
2. **Configurable parameters** — weights, thresholds, lookback periods in YAML/JSON
3. **Raw data access** — query underlying database, export to CSV
4. **Reproducible results** — identical results on same date

### 3. Acceptable Complexity

| Dimension | Tolerance |
|-----------|-----------|
| Initial setup time | 2-4 hours |
| CLAUDE.md editing | Comfortable |
| Terminal fluency | Expert |
| Debugging willingness | High |
| Config complexity tolerance | High |

### 4. User Journey

- **Installation (30 min)**: `git clone` → `uv sync` → edit config.yaml → `python setup --verify`
- **First use (2 hours)**: Full scan, examine top 20, cross-validate on TradingView, adjust weights
- **Daily use (10-15 min)**: `/scan`, review top 10, `/scan --diff`
- **Customization**: Add indicators, modify algorithms, create sector profiles
- **Advanced**: Write custom screeners, backtest, schedule via launchd

### 5. Abandonment Triggers

1. **Opaque scoring** — can't understand/modify how score is computed
2. **Stale/incorrect data** — pykrx returns wrong data, trust destroyed
3. **Inflexible architecture** — adding indicators requires modifying core code
4. **Performance** — scanning 2,500 stocks takes > 10 minutes

**Minimum quality threshold**: Cross-validating top 20, at least 70% should feel "reasonable."

---

## Branch B: General User Investigation

### 1. Persona Detail

**Background**: Individual stock trader (30s-50s), uses Kiwoom HTS, NOT a programmer. **This matches the actual user.**
**Current workflow**: Manual chart review on Naver Finance/HTS, reads stock community posts, 30-50 stock watchlist.
**Core frustration**: "I know there are good stocks I'm missing because I can only look at so many charts."
**Expectation**: "Give me a list of 10-20 stocks ready to move. I'll check charts myself."

### 2. Must-Have Components

1. **One-command setup that actually works** — detect missing Python, install everything, verify
2. **Single slash command for daily use** — `/scan` produces human-readable Korean list
3. **Korean-language output** — all results, explanations, errors in Korean
4. **Interpreted results** — "이동평균선 정배열 완성도: 높음" not "MA_ALIGN: 0.85"
5. **Reliability over features** — 95% uptime > amazing features at 80%

### 3. Acceptable Complexity

| Dimension | Tolerance |
|-----------|-----------|
| Initial setup time | 15-30 minutes MAX |
| CLAUDE.md editing | Will NOT do this |
| Terminal commands | Copy-paste only |
| Python understanding | None |
| Debugging willingness | Zero |
| Config file editing | Will NOT edit YAML/JSON |

### 4. User Journey

**Ideal Installation (15 min)**:
1. Open Claude Code in project directory
2. Setup hook auto-runs: Python check, install deps, verify connectivity
3. `/설치확인` — system reports health
4. `/scan` — first results

**Realistic Installation** (what will probably happen):
1. Clone repo (needs step-by-step instructions)
2. Python may not be installed (macOS 12.3+ removed Python 2.7)
3. Xcode Command Line Tools prompt appears
4. pip may fail due to permissions
5. They ask Claude "왜 안 돼?"

**Daily use (3-5 min)**: Open Claude Code → `/scan` → read results → open on Naver/HTS → done.

### 5. Immediate Abandonment Triggers

1. **Python installation failure** — "command not found: python3" with no auto-recovery
2. **English error messages** — stack traces, pip errors cause disengagement
3. **Empty or obviously wrong results** — stocks in downtrend ranked high
4. **Waiting > 5 minutes without feedback** — assume frozen, close terminal
5. **Any step requiring Googling** — friction exceeds patience

**Setup patience boundary**: 3 copy-paste commands acceptable; 5 marginal; any requiring text modification unacceptable.

---

## Critical Analysis: The Gap

### The Installation Problem

| Step | Power User | General User |
|------|-----------|-------------|
| Check Python | `python3 --version` | Doesn't know what Python is |
| Install Python | `brew install python` | Has never opened Terminal |
| Create venv | `uv venv` | Does not understand concept |
| Install deps | `uv pip install -r requirements.txt` | Will copy-paste if instructed |
| Verify pykrx | Runs test script | Cannot interpret success/failure |
| Configure | Edits YAML with satisfaction | Will not touch config files |
| **Total time** | **15-30 minutes** | **Hours or never complete** |

**The bootstrap problem**: Setup hooks are Python-based, but user may not have Python installed. Chicken-and-egg.

**Proposed solution**: Shell-based bootstrap (`bootstrap.sh`):
1. Check for Python 3.10+
2. If missing, check for Homebrew
3. If Homebrew missing, install it (requires user Enter + password)
4. Install Python via Homebrew
5. Python-based setup hook takes over

### The Daily Operation Gap

| Aspect | Power User | General User |
|--------|-----------|-------------|
| Invocation | `/scan --kosdaq --min-volume=1M` | "오늘 종목 뭐가 좋아?" |
| Output | JSON/CSV with full breakdown | Formatted Korean list |
| Error handling | Reads traceback | "안 돼" — expects auto-fix |
| Customization | config.yaml | Natural language requests |

**Solution**: Dual-interface design with progressive disclosure.

### The Error Recovery Gap

| Failure | Auto-Recovery Strategy |
|---------|----------------------|
| pykrx timeout | Auto-retry 3x with exponential backoff |
| KRX structure change | Detect via validation, alert, use cache |
| Missing package | Auto-install on next run |
| Network offline | Use cached data with warning |
| Config corrupted | Validate on load, restore from backup |

### The Trust Problem

**Power User**: Trust through transparency — show the math, allow cross-validation.
**General User**: Trust through alignment — if first scan matches their intuition, trust is established. Frame as "candidates" not "buy signals."

**Legal risk**: Korean financial regulation on investment advice. System must frame output as analysis tool, not recommendations. Include disclaimers.

---

## Recommended Design Direction: General User Primary

**Rationale**:
1. Actual user is a general user (stated: "이 시스템을 어떻게 만들지 전혀 모른다")
2. Easier to add power-user features (expose configs) to simple system than to simplify complex system
3. Day-1 experience determines adoption

**Progressive Disclosure Architecture**:
- **Layer 0** (Default): `/scan` → Korean results with sensible defaults
- **Layer 1** (Natural language): "코스닥만 보여줘" — Claude parses and applies filters
- **Layer 2** (Structured flags): `/scan --market=kosdaq --format=json`
- **Layer 3** (Configuration file): Edit `config.yaml` for persistent custom weights
- **Layer 4** (Source code): Modify analysis scripts, add indicators

---

## Top 5 Must-Have Components

### 1. Automated Bootstrap & Environment Setup
- Shell + Python setup handling entire installation
- **Critical for**: General User (blocks all usage without it)
- **Complexity**: Medium-High

### 2. Data Collection Pipeline with Resilience
- pykrx + rate limiting + exponential backoff retry + progress reporting + data validation + caching
- **Critical for**: Both equally
- **Complexity**: Medium

### 3. Technical Completeness Scoring Engine
- pandas-ta indicators + composite scoring + configurable weights
- **Critical for**: Both equally (different interfaces)
- **Complexity**: Medium-High

### 4. Korean-Language Result Presentation
- Score-to-narrative templates + Korean TA terminology + Markdown + Naver Finance links
- **Critical for**: General User (this IS their product)
- **Complexity**: Medium

### 5. Error Handling & Self-Recovery System
- Korean error translation + auto-retry + cache fallback + dependency auto-repair + diagnostic logging
- **Critical for**: General User (prevents abandonment)
- **Complexity**: Medium

---

## Parking Lot

| # | Discovery | Source | Follow-up Category |
|---|-----------|--------|-------------------|
| 1 | pykrx scraping fragility — KRX 2026 login policy changes caused issues | Branch B | technical |
| 2 | Claude Cowork compatibility — GUI access for non-technical users | Branch B | external-integration |
| 3 | Korean financial regulation risk — investment advice licensing | Branch B | structural-risk |
| 4 | Historical performance validation needed | Branch A | technical |
| 5 | launchd scheduling for daily automation | Branch B | technical |
| 6 | Korea Investment Securities Open API as pykrx alternative | Both | external-integration |
| 7 | Existing Claude Code trading skills ecosystem (InvestSkill, etc.) | Both | technical |
| 8 | "2,500 stocks in 10 minutes" performance budget — pykrx may take 15-30 min | Branch B | technical |
| 9 | Python bootstrap chicken-and-egg problem | Branch B | structural-risk |
| 10 | User behavior after receiving results — last mile workflow | Branch B | user-behavior |
