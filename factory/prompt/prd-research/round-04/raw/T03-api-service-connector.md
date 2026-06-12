---
round: 4
type: raw
teammate: api-service-connector
axis: external-api-services
investigation_axis: external-integration
created: "2026-05-26T15:00:00+09:00"
question_summary: "External API and service integration for KOSPI/KOSDAQ stock pipeline — financial data sources, LLM provider CLI integration (OpenAI/Gemini subscription accounts), notification services, authentication, cost/rate limits, offline capability"
assumption_axis: "Cloud/External Services vs Fully Local/Offline"
branch_a: "Branch 3.1 — Cloud/External Services (maximize capabilities via external APIs)"
branch_b: "Branch 3.2 — Fully Local/Offline (network-independent operation)"
web_search_count: 32
cli_subscription_compliance:
  openai: "COMPLIANT — Codex CLI uses ChatGPT OAuth (browser login), charges to subscription. No API key."
  gemini: "COMPLIANT — Gemini CLI uses Google Account auth (browser login). Free tier: 60 RPM / 1,000 RPD."
  api_key_approach: "BLOCKED — violates ABSOLUTE ANCHOR ② constraint"
local_execution_tags:
  LOCAL_OK: ["OpenAI Codex CLI (ChatGPT OAuth)", "Gemini CLI (Google Account auth)", "Ollama (fully local)", "LM Studio (fully local)", "pykrx (web scraping)", "FinanceDataReader (web scraping)", "DuckDB (local DB)", "pandas-ta (local computation)", "Telegram Bot (Bot Token)", "osascript notification (macOS native)", "Python keyring (macOS Keychain access)", ".env file credential storage"]
  LOCAL_PARTIAL: ["pykrx (requires KRX network)", "Claude Code (requires Anthropic API)", "Gmail MCP (OAuth + network)", "Slack MCP (OAuth + network)", "DART API (requires API key registration + network)", "yfinance (unofficial, may throttle)", "KRX Open API (requires annual key renewal)", "LINE Notify (requires token)", "KakaoTalk kakaocli (Accessibility permissions)"]
  LOCAL_BLOCKED: ["Naver Finance scraping (high maintenance, legal risk, technical complexity)", "API-key-based LLM integration (violates subscription CLI constraint)"]
sources:
  - url: "https://google-gemini.github.io/gemini-cli/docs/get-started/authentication.html"
    desc: "Gemini CLI Authentication Setup — Google Account browser login"
  - url: "https://github.com/google-gemini/gemini-cli"
    desc: "Gemini CLI GitHub"
  - url: "https://developers.openai.com/codex/cli"
    desc: "OpenAI Codex CLI"
  - url: "https://developers.openai.com/codex/auth"
    desc: "Codex Authentication — ChatGPT OAuth"
  - url: "https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan"
    desc: "Using Codex with ChatGPT Subscription Plan"
  - url: "https://developers.openai.com/codex/noninteractive"
    desc: "Codex Non-Interactive Mode"
  - url: "https://github.com/openai/codex-plugin-cc"
    desc: "Official Codex Plugin for Claude Code"
  - url: "https://github.com/EvanZhouDev/openai-oauth"
    desc: "openai-oauth — localhost proxy with OAuth tokens"
  - url: "https://github.com/sharebook-kr/pykrx"
    desc: "pykrx GitHub"
  - url: "https://github.com/FinanceData/FinanceDataReader"
    desc: "FinanceDataReader GitHub"
  - url: "https://openapi.krx.co.kr/"
    desc: "KRX Open API"
  - url: "https://englishdart.fss.or.kr/"
    desc: "DART Repository (Financial Supervisory Service)"
  - url: "https://github.com/FinanceData/OpenDartReader"
    desc: "OpenDartReader"
  - url: "https://pypi.org/project/yfinance/"
    desc: "yfinance PyPI"
  - url: "https://github.com/slackapi/slack-mcp-plugin"
    desc: "Slack MCP Plugin (Official)"
  - url: "https://developers.google.com/workspace/gmail/api/guides/configure-mcp-server"
    desc: "Gmail MCP Server (Google Official)"
  - url: "https://github.com/silver-flight-group/kakaocli"
    desc: "kakaocli — KakaoTalk CLI for AI agents"
  - url: "https://github.com/Mrbaeksang/korea-stock-analyzer-mcp"
    desc: "Korea Stock Analyzer MCP — 6 investment strategies"
  - url: "https://dev.to/euda1mon1a/macos-tahoe-broke-keychain-cli-reads-novel-findings-from-an-ai-agent-deployment-2p3o"
    desc: "macOS Tahoe Keychain CLI Regression"
---

# T03: API & Service Connector — Cloud Services vs Fully Local

## Executive Summary

**OpenAI and Gemini subscription-based CLI integration is confirmed [LOCAL-OK]** — both authenticate via browser OAuth tied to subscription accounts, no API keys needed. Gemini CLI is the cleanest integration (Google Account auth, `gemini -p` headless mode, JSON output, 1,000 free requests/day). Total monthly cost: ~$240 (all existing subscriptions, zero additional API charges).

---

## Branch 3.1: Cloud/External Services

### 1. Financial Data APIs

| Source | Auth | Rate Limit | Cost | Korean Stocks | Tag |
|--------|------|-----------|------|--------------|-----|
| **pykrx** | None (scraping) | ~1 req/sec recommended | Free | KOSPI/KOSDAQ native | [LOCAL-PARTIAL] |
| **FinanceDataReader** | None | Similar to pykrx | Free | KRX + global markets | [LOCAL-PARTIAL] |
| **KRX Open API** | API key (free registration) | Annual renewal | Free | Official KRX source | [LOCAL-PARTIAL] |
| **DART API** | API key (free) | 10,000/day | Free | Corporate filings, XBRL | [LOCAL-PARTIAL] |
| **yfinance** | None | Unofficial, may throttle | Free | 005930.KS / 067160.KQ format | [LOCAL-PARTIAL] |
| **Naver Finance** | Scraping only | - | - | JS-rendered, CAPTCHA risk | **[LOCAL-BLOCKED]** |

### 2. LLM Provider Integration (★ KEY SECTION)

#### OpenAI (Codex CLI) — [LOCAL-OK] ✅ CLI-구독 준수

**How it works**:
1. Install: `npm install -g @openai/codex` or `brew install --cask codex`
2. First run: `codex` opens browser for ChatGPT OAuth login
3. Tokens cached at `~/.codex/auth.json`, auto-refreshed
4. Non-interactive: `codex exec "task"` — streams to stderr, result to stdout
5. Official Claude Code plugin: `codex-plugin-cc` (GitHub: openai/codex-plugin-cc)

**Integration patterns**:
- Pattern A: `Bash → codex exec "analyze code" 2>/dev/null`
- Pattern B: Official plugin via `/plugin marketplace add openai/codex-plugin-cc`
- Pattern C: `openai-oauth` localhost proxy for OpenAI-compatible endpoint

**Caveat**: `-q` (quiet) mode may hang at git warning in non-git directories.

#### Gemini CLI — [LOCAL-OK] ✅ CLI-구독 준수

**How it works**:
1. Install: `npm install -g @google/gemini-cli` (requires Node.js 20+)
2. First run: browser opens for Google Account sign-in
3. Credentials cached locally
4. Headless: `gemini -p "prompt"` — supports `--output-format json`

**Free tier (no subscription needed)**: 60 RPM / 1,000 RPD on Gemini 2.5 Pro — extremely generous.

**Integration patterns**:
- `echo "data" | gemini -p --output-format json` (Bash pipe)
- `.claude/agents/gemini-analyzer.md` (subagent wrapper)
- `.claude/commands/ask-gemini.md` (slash command)

#### API-key based — **[BLOCKED]** ❌

API-key approach violates ABSOLUTE ANCHOR ② constraint. User has subscription accounts for both OpenAI and Gemini. CLI tools authenticate via browser OAuth to these subscriptions. No API credit purchase needed.

#### Local LLMs (Ollama) — [LOCAL-OK]

- `brew install ollama` → `ollama serve` → localhost:11434
- Models: DeepSeek-R1 (reasoning), Qwen 3.5 (Korean multilingual)
- Claude Code offline: Set `ANTHROPIC_BASE_URL` to Ollama endpoint
- Quality: ~80% of cloud for coding, less for financial analysis

#### Multi-LLM Architecture Recommendation

| Role | Provider | Auth | Cost |
|------|----------|------|------|
| Primary orchestrator | Claude Code Max | Subscription | $200/mo |
| Code review / second opinion | Codex CLI | ChatGPT OAuth | $20/mo (included) |
| Batch analysis / large context | Gemini CLI | Google Account | Free tier sufficient |
| Offline fallback | Ollama (DeepSeek-R1) | None | Free |

### 3. Notification Services

| Service | Auth | Setup | Bidirectional | Best For | Tag |
|---------|------|-------|--------------|----------|-----|
| osascript | None | 0 (built-in) | No | Phase 1 | [LOCAL-OK] |
| **Telegram Bot** | Bot Token | Low | Yes | Phase 2+ alerts | [LOCAL-PARTIAL] |
| Gmail MCP | OAuth 2.0 | Medium | Yes | Email reports | [LOCAL-PARTIAL] |
| Slack MCP | OAuth | Medium | Yes | Team environment | [LOCAL-PARTIAL] |
| KakaoTalk | Accessibility API | High | Yes | Korean users | [LOCAL-PARTIAL] |

**Telegram recommended**: Lowest setup, official Claude Code Channel support, free API.

### 4. Authentication & Security

| Method | Security | Ease | Claude Code Compatible |
|--------|---------|------|----------------------|
| .env file | Low (plaintext) | Easy | Yes |
| macOS Keychain | High | Medium | **Regression on Tahoe** (`security -w` hangs) |
| Python keyring | High | Medium | Yes (recommended over `security` CLI) |
| Env variables | Medium | Easy | Yes |

**macOS Tahoe Keychain bug**: `security find-generic-password -w` may hang. Use Python `keyring` library instead.

### 5. Cost Structure

| Component | Monthly | Type |
|-----------|---------|------|
| Claude Code Max | $200 | Subscription (existing) |
| ChatGPT Plus | $20 | Subscription (existing) |
| Gemini Advanced | $20 | Subscription (existing) |
| pykrx/FDR/DuckDB/pandas-ta | $0 | Free |
| Telegram Bot | $0 | Free |
| **Total** | **$240** | **All existing subscriptions** |
| **API key charges** | **$0** | **None** |

---

## Branch 3.2: Fully Local/Offline

### Offline Capability Boundary

| Component | Works Offline? | Notes |
|-----------|---------------|-------|
| Python pipeline | YES (with cached data) | Full pipeline after initial fetch |
| DuckDB | YES | Fully local embedded DB |
| pandas-ta | YES | Local computation |
| Claude Code | NO (normally) | Requires Anthropic API |
| Claude Code + Ollama | YES | Quality degradation ~20-40% |
| pykrx fetch | NO | Needs KRX server |

### Offline Architecture: "Fetch Once, Analyze Many"

1. Data Layer: All OHLCV in DuckDB — permanently available offline after fetch
2. Indicator Layer: pandas-ta computes from cached DuckDB — zero network
3. Summary Layer: summary.md is pure text — readable offline
4. LLM: Ollama fallback for offline interpretation

---

## Comparison

| Dimension | Cloud (3.1) | Offline (3.2) | Recommended |
|-----------|------------|--------------|-------------|
| Data freshness | Daily (KRX) | Stale (last fetch) | Cloud |
| Analysis quality | Excellent (multi-LLM) | Good (Ollama) | Cloud |
| Notification | Multi-channel | osascript only | Cloud |
| Cost | ~$240/mo (subscriptions) | ~$0 | Cloud (already paid) |
| Reliability | Network-dependent | Self-contained | Hybrid |

**Recommendation**: Cloud for daily operation. Offline always available as fallback via DuckDB caching + Ollama.

---

## Parking Lot

1. **KRX Open API rate limits**: Registration needed to see docs
2. **Codex CLI -q mode bug**: May hang in non-git directories
3. **macOS Tahoe Keychain regression**: Severity unclear, keyring workaround needs verification
4. **Korea Stock Analyzer MCP vs custom pipeline**: Overlapping technical indicators
5. **Gemini free tier sufficiency**: 1,000/day vs actual daily request count
6. **Claude Code Channels stability**: Research preview (v2.1.80+), API may change
