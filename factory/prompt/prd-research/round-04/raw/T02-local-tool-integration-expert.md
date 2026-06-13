---
round: 4
type: raw
teammate: local-tool-integration-expert
axis: local-tooling
investigation_axis: external-integration
created: "2026-05-26T15:00:00+09:00"
question_summary: "Local CLI tool integration for KOSPI/KOSDAQ stock pipeline on macOS — heavy tooling (brew ecosystem) vs light tooling (macOS built-ins + uv only), Apple Silicon compatibility, installation friction for non-technical user"
assumption_axis: "Heavy Local Tooling vs Light Local Tooling"
branch_a: "Branch 2.1 — Heavy Local Tooling (aggressive use of brew, CLI tools, system utilities)"
branch_b: "Branch 2.2 — Light Local Tooling (minimal dependency, Claude Code built-ins + macOS native)"
web_search_count: 49
local_execution_tags:
  LOCAL_OK: ["uv (already installed)", "ruff (already installed)", "brew (already installed)", "python3 (pyenv 3.12.7)", "jq (macOS Tahoe built-in /usr/bin/jq v1.7.1-apple)", "sqlite3 (built-in)", "curl (built-in)", "git (built-in)", "osascript (built-in)", "caffeinate (built-in)", "plutil (built-in)", "launchd (built-in)", "rsync (built-in)", "mktemp (built-in)", "diff (built-in)", "DuckDB CLI (brew)", "fswatch (brew)", "pykrx (pip)", "duckdb-python (pip)", "pandas-ta (pip)", "watchdog (pip)"]
  LOCAL_PARTIAL: ["pandas-ta archival risk (July 2026 deadline — pandas-ta-classic fallback exists)"]
  LOCAL_BLOCKED: []
sources:
  - url: "https://duckdb.org/docs/current/dev/building/macos"
    desc: "DuckDB macOS Installation"
  - url: "https://formulae.brew.sh/formula/duckdb"
    desc: "DuckDB Homebrew Formula"
  - url: "https://docs.astral.sh/uv/"
    desc: "uv Official Docs"
  - url: "https://docs.astral.sh/ruff/"
    desc: "Ruff Docs"
  - url: "https://github.com/emcrisostomo/fswatch"
    desc: "fswatch GitHub — cross-platform file change monitoring"
  - url: "https://pypi.org/project/pandas-ta/"
    desc: "pandas-ta PyPI"
  - url: "https://pypi.org/project/pandas-ta-classic/"
    desc: "pandas-ta-classic PyPI — community fork, 200+ indicators"
  - url: "https://github.com/xgboosted/pandas-ta-classic"
    desc: "pandas-ta-classic GitHub"
  - url: "https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html"
    desc: "Apple Scheduling Timed Jobs (launchd)"
  - url: "https://developer.apple.com/documentation/macos-release-notes/macos-26-release-notes"
    desc: "macOS Tahoe Release Notes"
---

# T02: Local Tool Integration Expert — Heavy vs Light Tooling

## Executive Summary

**Light tooling wins decisively**: `uv` + 3 Python packages + macOS built-ins = complete system with **zero Homebrew packages**. Installation time drops from 5-15 minutes (with Homebrew) to **1-2 minutes**. Key discovery: `jq` is now built-in on macOS Tahoe. Critical risk: pandas-ta archival by July 2026 — pandas-ta-classic is the drop-in replacement.

---

## Environment Baseline (Verified on This Machine)

**System**: macOS Tahoe 26.5, Apple Silicon (arm64), Homebrew installed at `/opt/homebrew/bin/brew`

### macOS Built-in Tools (Zero Installation)

| Tool | Path | Version | Purpose | Tag |
|------|------|---------|---------|-----|
| python3 | pyenv 3.12.7 | 3.12.7 | Pipeline execution | [LOCAL-OK] |
| **jq** | **/usr/bin/jq** | **1.7.1-apple** | JSON processing — **NOW BUILT-IN** | [LOCAL-OK] |
| sqlite3 | /usr/bin/sqlite3 | 3.51.0 | Fallback DB | [LOCAL-OK] |
| curl | /usr/bin/curl | 8.7.1 | Network requests | [LOCAL-OK] |
| git | /usr/bin/git | 2.50.1 | Version control | [LOCAL-OK] |
| osascript | built-in | - | macOS native notifications | [LOCAL-OK] |
| caffeinate | built-in | - | Prevent sleep during pipeline | [LOCAL-OK] |
| plutil | built-in | - | launchd plist validation | [LOCAL-OK] |
| launchd | built-in | - | Task scheduling | [LOCAL-OK] |

### Already Installed (User Environment)

| Tool | Path | Version |
|------|------|---------|
| uv | ~/.local/bin/uv | 0.10.12 |
| ruff | pyenv 3.12.7 | 0.15.14 |
| brew | /opt/homebrew/bin/brew | installed |

---

## Branch 2.1: Heavy Local Tooling

### Additional Tools Considered

| Tool | Install | Size | Purpose | Required? |
|------|---------|------|---------|-----------|
| DuckDB CLI | `brew install duckdb` | ~30MB | Ad-hoc SQL, markdown export | Optional (Python API sufficient) |
| fswatch | `brew install fswatch` | ~1MB | File change detection | Optional (launchd WatchPaths alternative) |

### Heavy Tooling Patterns

**Pipeline with monitoring**:
```bash
caffeinate -i python3 main.py 2>&1 | tee -a pipeline.log
STATUS=$(jq -r '.status' pipeline_state.json)
if [ "$STATUS" = "success" ]; then
    osascript -e 'display notification "스캔 완료" with title "주식 분석기"'
else
    osascript -e 'display notification "스캔 실패" with title "주식 분석기" sound name "Basso"'
fi
```

**DuckDB CLI debugging**:
```bash
duckdb data/stocks.duckdb -markdown -c "
  SELECT ticker, total_score, rank FROM scores
  WHERE date = current_date ORDER BY total_score DESC LIMIT 50
"
```

---

## Branch 2.2: Light Local Tooling (★ Recommended)

### Minimum Viable Tool Set

**Total external installations: 1 (uv) + 3 Python packages. Zero brew packages.**

| Layer | Tool | Install Method |
|-------|------|---------------|
| Python env | uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python packages | pykrx, duckdb, pandas-ta | `uv add pykrx duckdb pandas-ta` |
| Scheduling | launchd | Already on macOS |
| Everything else | macOS built-ins | Already on macOS |

### Claude Code Built-in Capabilities Replace External Tools

| Need | Claude Code Tool | Sufficient? |
|------|-----------------|-------------|
| Run pipeline | Bash → `python3 main.py` | Yes |
| Read results | Read tool | Yes |
| Edit config | Edit tool | Yes |
| Search patterns | Grep (ripgrep) | Yes |
| Process JSON | Bash → jq (built-in!) | Yes |
| Validate plist | Bash → plutil (built-in) | Yes |
| Notifications | Bash → osascript (built-in) | Yes |
| Prevent sleep | Bash → caffeinate (built-in) | Yes |

### DuckDB Python API Replaces CLI

```python
import duckdb
conn = duckdb.connect('data/stocks.duckdb')
results = conn.execute("SELECT ... FROM scores ...").fetchdf()
with open('output/summary.md', 'w') as f:
    f.write(results.to_markdown(index=False))
```

### launchd WatchPaths Replaces fswatch

```xml
<key>WatchPaths</key>
<array>
    <string>/path/to/project/output/summary.md</string>
</array>
```

---

## Apple Silicon Compatibility Matrix

| Component | Native arm64? | Notes |
|-----------|---------------|-------|
| uv | Yes | Rust binary, fastest on arm64 |
| Python 3.12 | Yes | Universal2 framework build |
| pykrx | Yes | Pure Python (no C extensions) |
| DuckDB Python | Yes | Native arm64 wheels on PyPI |
| pandas-ta | Yes | Pure Python |
| jq | Yes | Apple-shipped universal binary |
| All macOS built-ins | Yes | Part of OS |

**ZERO Apple Silicon compatibility issues.**

---

## Comparison: Heavy vs Light

| Dimension | Heavy (2.1) | Light (2.2) | Winner |
|-----------|------------|------------|--------|
| External installs | uv + 2 brew | uv only | Light |
| Install time | 5-15 min (Homebrew) | 1-2 min | Light |
| User friction | Medium | Low | Light |
| Debugging | DuckDB CLI | Python REPL + Claude | Heavy (marginal) |
| Disk footprint | ~80MB extra | ~0 extra | Light |
| Maintenance | brew update + uv sync | uv sync only | Light |

---

## Critical Findings

### pandas-ta Archival Risk (R-4-1)
pandas-ta will be **archived by July 1, 2026** (~5 weeks). Mitigation: **pandas-ta-classic** (community fork, 200+ indicators, actively maintained, API-compatible drop-in).

### jq Now Built-in on macOS Tahoe
`/usr/bin/jq` v1.7.1-apple — genuine Apple-shipped universal binary. Eliminates brew dependency for JSON processing. **Caveat**: Older macOS versions (Sequoia, Sonoma) may need `brew install jq`.

### caffeinate is Critical
`caffeinate -i python3 main.py` prevents sleep during the 2-5 minute pykrx collection window. If Mac sleeps mid-collection, data is incomplete. launchd plist should wrap pipeline call with caffeinate.

### KRX Credential Setup is Biggest Friction
Not tool installation but KRX Data Marketplace registration (free, social login) + `.env` setup for KRX_ID/KRX_PW is the single biggest onboarding friction point.

---

## Parking Lot

1. **pandas-ta-classic migration**: API compatibility validation needed before July 2026
2. **KRX registration UX**: Dedicated bootstrap step for non-technical users
3. **macOS Tahoe jq availability**: Verified on 26.5, needs check on older versions
4. **Log rotation**: `pipeline.log` at ~1KB/day, `find -mtime +30 -delete` suffices
5. **ruff integration**: Already installed, add to pyproject.toml dev dependencies
