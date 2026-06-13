# Step 1 — Parameter Full Inventory

> Generated: 2026-05-29
> Coverage: 7 active filter modules + `Filter_condition_update.py` shared helper
> Scope exclusion: `stageMasterFilter.py` (Phase 2 per PRD §12)
> SOT root: `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/`

This inventory is an exhaustive enumeration of **every** `Final[...]` typed constant declared in the in-scope modules. Constants are grouped by 5-Stage screening pipeline ownership. Filename-only / output-path-only constants are retained for completeness (they are part of the public surface of each module and may legitimately appear in tuning conversations as "where is X read from / written to?").

---

## Stage 0 — Shared / Pipeline-wide (`Filter_condition_update.py`)

> The orchestration helper that re-evaluates `masterReference` stocks against all 6 stage filters and appends drop-reasons to `masterReference.log`. Contains no tunable threshold values — only structural/identification constants.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for per-date report folders consumed by all stages. | Filter_condition_update.py:64 |
| `_MASTER_REFERENCE_MD` | `Final[str]` | `"masterReference.md"` | Filename of the master reference list (target stocks for drop-reason analysis). | Filter_condition_update.py:65 |
| `_MASTER_REFERENCE_LOG` | `Final[str]` | `"masterReference.log"` | Append-only log file where per-stock per-stage drop reasons are recorded. | Filter_condition_update.py:66 |
| `_RESEARCHED_MD` | `Final[str]` | `"researchedCompany.md"` | Filename of the final researched-companies report; presence triggers eligibility for analysis. | Filter_condition_update.py:67 |
| `_STAGES` | `Final[list[tuple[str, str, str, _StageFilter]]]` | 6-tuple list: `("Stage 1","chart60_120","stage1_chart60_120_passed.md", chart60_120_filter_stock)`, `("Stage 2","chart240","stage2_chart240_passed.md", chart240_filter_stock)`, `("Stage 2-1","chartDayPre","stage2_1_chartDayPre_passed.md", chartday_pre_filter_stock)`, `("Stage 3","chartDay","stage3_chartDay_passed.md", chartday_filter_stock)`, `("Stage 4","investor","stage4_investor_passed.md", investor_filter_stock)`, `("Stage 5","finance","stage5_finance_passed.md", finance_filter_stock)` | Canonical ordering of stages with (display label, stage name, passed-result filename, single-stock filter callable) per stage. Order must match `researchFlow.saveReport._STAGE_FILENAMES` 1:1. | Filter_condition_update.py:72-85 |
| `_NAME_CODE_RE` | `Final[re.Pattern[str]]` | `re.compile(r"^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$")` | Regex that splits a `"종목명(123456)"` line into named groups `nm` (name) and `cd` (4–6 digit stock code). | Filter_condition_update.py:88 |

---

## Stage 1 — `chart60_120Filter.py` (Type A/B/C/D/E pattern detection — 60min + 120min MA alignment)

> Five-pattern detector. First match (priority A→B→C→D→E) classifies the stock. Static structural checks evaluate on `bars[-8:]`; dynamic event checks evaluate on the most recent 1–16 bars depending on type.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for date-partitioned reports. | chart60_120Filter.py:110 |
| `_CHART60_FILENAME` | `Final[str]` | `"chart60.md"` | Input 60-minute bar report filename per stock folder. | chart60_120Filter.py:111 |
| `_CHART120_FILENAME` | `Final[str]` | `"chart120.md"` | Input 120-minute bar report filename per stock folder. | chart60_120Filter.py:112 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart60_120Filter.md"` | Output filter-result report filename written per date folder. | chart60_120Filter.py:113 |
| `_REQUIRED_STATIC_BARS` | `Final[int]` | `8` | Window size for static structural conditions (alignment / divergence / convergence): require **all** of `bars[-8:]` to satisfy. Applies to Types A/B/C/D. | chart60_120Filter.py:116 |
| `_ALIGN_TOL_LOOSE` | `Final[float]` | `0.015` (i.e., ×0.985) | **Shared loose alignment tolerance** for Types B/C/D within this module. Formula: `upper_MA >= lower_MA * (1 − _ALIGN_TOL_LOOSE)`. Asymmetric −1.5% slack. **CRITICAL: this is a multi-Type shared constant — changes propagate.** | chart60_120Filter.py:120 |
| `_TYPE_A_ALIGN_TOL` | `Final[float]` | `0.035` (i.e., ×0.965) | Type A–only 4-MA full alignment tolerance (-3.5%). Looser than `_ALIGN_TOL_LOOSE` to recover masters where noise broke a strict 4-line alignment. Applies to both 60m and 120m timeframes. | chart60_120Filter.py:125 |
| `_TYPE_B_BELOW_MA60_RATIO` | `Final[float]` | `0.97` | Type B–only: 120-min `MA10` and `MA20` must each be ≤ `MA60 × 0.97` (i.e., at least 3% below MA60), expressing the "rising-from-below" entry condition. | chart60_120Filter.py:128 |
| `_TYPE_C_CONVERGE_PCT` | `Final[float]` | `0.035` | Type C–only convergence threshold: `(max(MA10,MA20,MA60) − min)/min ≤ 3.5%` on every 120-min bar in `bars[-8:]`. Captures VCP-style tight consolidation. | chart60_120Filter.py:131 |
| `_TYPE_D_ALIGN_TOL_120` | `Final[float]` | `0.020` (i.e., ×0.98) | Type D–only "tangled" tolerance on 120-min: `MA10 ≥ MA60×0.98` AND `MA20 ≥ MA60×0.98` (order between MA10 and MA20 is free — tangling allowed). | chart60_120Filter.py:134 |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | `Final[float]` | `0.50` | Type D 60-min auxiliary threshold: fraction of `bars60[-16:]` whose `close > MA60` must be ≥ 50% (when the strict 4-line 60m alignment fallback fails). | chart60_120Filter.py:137 |
| `_TYPE_D_DYNAMIC_WINDOW` | `Final[int]` | `16` | Window size (in 60-min bars) for Type D's `close > MA60` ratio fallback. | chart60_120Filter.py:138 |
| `_TYPE_E_SPREAD_PCT` | `Final[float]` | `0.10` | Type E convergence ceiling on most-recent 120m bar: `(max(MA10,MA20,MA60) − min)/min ≤ 10%`. Wider than Type C — designed to catch "about-to-align" V-rebounds. | chart60_120Filter.py:143 |
| `_TYPE_E_DYNAMIC_WINDOW` | `Final[int]` | `8` | Window size (in 60-min bars) for Type E's `close > MA60` support-ratio evaluation. | chart60_120Filter.py:145 |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | `Final[float]` | `0.75` | Type E 60-min support threshold: fraction of `bars60[-8:]` with `close > MA60` must be ≥ 75% (fresh-breakout persistence). | chart60_120Filter.py:146 |
| `_TYPE_E_SHORT_ALIGN_WINDOW` | `Final[int]` | `2` | Type E short-alignment window — at least 1 of the last 2 120-min bars must satisfy the short-alignment condition. Rescues V-rebounds whose final bar has intraday noise. | chart60_120Filter.py:149 |
| `_TYPE_E_SHORT_ALIGN_TOL` | `Final[float]` | `0.016` (i.e., ×0.984) | Type E short-alignment tolerance for `MA10 ≥ MA20×(1−tol)` on 120-min recent window (1.6%). | chart60_120Filter.py:152 |
| `_TYPE_E_MA60_OVER_MA306_TOL` | `Final[float]` | `0.035` (i.e., ×0.965) | Type E **dedicated** long-trend tolerance: `MA60 ≥ MA306×(1−0.035)` on the last 120m bar. Split from `_ALIGN_TOL_LOOSE` (1.5%) because using the shared 1.5% over-restricted Type E V-rebound recovery while affecting Types B/C/D. | chart60_120Filter.py:156 |
| `_LABEL_A` | `Final[str]` | `"A"` | Display/category label for Type A matches. | chart60_120Filter.py:159 |
| `_LABEL_B` | `Final[str]` | `"B"` | Display/category label for Type B matches. | chart60_120Filter.py:160 |
| `_LABEL_C` | `Final[str]` | `"C"` | Display/category label for Type C matches. | chart60_120Filter.py:161 |
| `_LABEL_D` | `Final[str]` | `"D"` | Display/category label for Type D matches. | chart60_120Filter.py:162 |
| `_LABEL_E` | `Final[str]` | `"E"` | Display/category label for Type E matches. | chart60_120Filter.py:163 |
| `_LABEL_EXCLUDED` | `Final[str]` | `"제외"` | Category label for stocks failing all five Type checks. | chart60_120Filter.py:164 |
| `_LABEL_SKIP` | `Final[str]` | `"스킵"` | Category label for stocks with missing input files (chart60.md or chart120.md). | chart60_120Filter.py:165 |
| `_TYPE_CHECKERS` | `Final[tuple[tuple[str, object], ...]]` | `((_LABEL_A,_check_type_a),(_LABEL_B,_check_type_b),(_LABEL_C,_check_type_c),(_LABEL_D,_check_type_d),(_LABEL_E,_check_type_e))` | Ordered Type checker dispatch table — defines the priority A→B→C→D→E evaluation sequence in `evaluate_chart60_120`. | chart60_120Filter.py:572 |

---

## Stage 1-Adjacent — `chart60Filter.py` (60-min 4MA alignment, standalone)

> Standalone 60-minute MA alignment filter (used by chart60_120Filter via imports of its parsing helpers and regexes). Has its own independent alignment tolerance — **do not confuse with `_ALIGN_TOL_LOOSE`**.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for date-partitioned reports. | chart60Filter.py:68 |
| `_CHART60_FILENAME` | `Final[str]` | `"chart60.md"` | Input 60-minute bar report filename. | chart60Filter.py:69 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart60Filter.md"` | Output filter-result report filename. | chart60Filter.py:70 |
| `_MA_ALIGNMENT_TOLERANCE` | `Final[float]` | `0.005` (i.e., ×0.995) | **Independent** 4MA alignment tolerance for chart60Filter.py only: asymmetric −0.5% slack. Formula: `upper_MA >= lower_MA × (1 − _MA_ALIGNMENT_TOLERANCE)`. Strict alignment requirement. **Not the same constant as `_ALIGN_TOL_LOOSE` in chart60_120Filter.py.** | chart60Filter.py:75 |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | Window size: require **all** of `bars[-3:]` (latest 3 bars) to satisfy 4MA alignment. | chart60Filter.py:78 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | Regex matching the per-stock directory name format `"종목명(123456)"`; captures name and code. Also re-imported and reused by chart60_120Filter / chart240Filter / financeFilter / investorFilter via `_STOCK_DIR_PATTERN`. | chart60Filter.py:81 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*$")` | Parses one row of the chart60.md markdown timeseries table: 10 capture groups = (timestamp `YYYY-MM-DD HH:MM`, O, H, L, C, V, MA10, MA20, MA60, MA306). MA columns tolerate `—`/`-`/empty as missing. Also reused by chart60_120Filter and chart240Filter via re-import. | chart60Filter.py:86-92 |

---

## Stage 2 — `chart240Filter.py` (240-min long-term trend gate)

> Verifies that `MA60 ≥ MA306×(1 − tol)` holds on all of the last N 240-min bars. Reuses `Chart60Bar` and the chart60 table regex by re-import.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for date-partitioned reports. | chart240Filter.py:72 |
| `_CHART240_FILENAME` | `Final[str]` | `"chart240.md"` | Input 240-minute bar report filename. | chart240Filter.py:73 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chart240Filter.md"` | Output filter-result report filename. | chart240Filter.py:74 |
| `_MA60_MA306_TOLERANCE` | `Final[float]` | `0.025` (i.e., ×0.975) | Long-term trend tolerance on 240m: `MA60 ≥ MA306 × (1 − 0.025)` — asymmetric −2.5% slack. Required on every bar of the evaluation window. | chart240Filter.py:78 |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | Window size: require **all** of the latest 3 240m bars to satisfy the MA60-vs-MA306 trend condition. | chart240Filter.py:81 |

---

## Stage 2-1 — `chartDayPreFilter.py` (Same-day surge pre-exclusion gate)

> Excludes stocks whose latest daily bar rose ≥ 15% vs prior close — guards against overheated / chase-the-pump candidates entering Stage 3.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for date-partitioned reports. | chartDayPreFilter.py:46 |
| `_CHARTDAY_FILENAME` | `Final[str]` | `"chartDay.md"` | Input daily bar report filename (shared input with Stage 3). | chartDayPreFilter.py:47 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chartDayPreFilter.md"` | Output filter-result report filename. | chartDayPreFilter.py:48 |
| `_DAILY_SURGE_THRESHOLD` | `Final[float]` | `0.15` | Daily change ceiling: `(close − prev_close) / prev_close ≥ 0.15` (≥ +15%) → excluded. Strictly less-than semantics for PASS. | chartDayPreFilter.py:51 |

---

## Stage 3 — `chartDayFilter.py` (Daily MA alignment + MA612 band)

> Two-part test: (a) 4MA alignment on ≥ 2 of last 3 daily bars (single-bar noise buffer); (b) latest bar close within asymmetric MA612 band AND today close > yesterday close.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for date-partitioned reports. | chartDayFilter.py:55 |
| `_CHARTDAY_FILENAME` | `Final[str]` | `"chartDay.md"` | Input daily bar report filename. | chartDayFilter.py:56 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"chartDayFilter.md"` | Output filter-result report filename. | chartDayFilter.py:57 |
| `_MA10_MA20_MA60_TOLERANCE` | `Final[float]` | `0.05` (i.e., ×0.95) | Alignment tolerance for `MA10 ≥ MA20×0.95` and `MA20 ≥ MA60×0.95` on daily bars (-5.0% asymmetric). Wider than intraday because daily volatility is larger. | chartDayFilter.py:61 |
| `_MA60_MA306_LOWER_TOL` | `Final[float]` | `0.15` (lower band ×0.85) | Lower band of asymmetric MA60-vs-MA306 envelope: `MA60 ≥ MA306 × (1 − 0.15)` (i.e., ≥ ×0.85). Strict floor — prevents deep downtrends from passing. | chartDayFilter.py:63 |
| `_MA60_MA306_UPPER_TOL` | `Final[float]` | `0.45` (upper band ×1.45) | Upper band of asymmetric MA60-vs-MA306 envelope: `MA60 ≤ MA306 × (1 + 0.45)` (i.e., ≤ ×1.45). Permissive ceiling — allows strong uptrends. | chartDayFilter.py:64 |
| `_CLOSE_VS_MA612_LOWER` | `Final[float]` | `-0.15` (band ×0.85) | Lower edge of close-vs-MA612 envelope: `(close − MA612)/MA612 ≥ −0.15`. Excludes stocks too far below their long-term base. | chartDayFilter.py:68 |
| `_CLOSE_VS_MA612_UPPER` | `Final[float]` | `0.50` (band ×1.50) | Upper edge of close-vs-MA612 envelope: `(close − MA612)/MA612 ≤ 0.50`. Permissive to allow current masters which sit well above MA612. | chartDayFilter.py:69 |
| `_REQUIRED_CONSECUTIVE_BARS` | `Final[int]` | `3` | Sample window: examine the last 3 daily bars for alignment voting. | chartDayFilter.py:72 |
| `_REQUIRED_ALIGNED_BARS` | `Final[int]` | `2` | Voting threshold: at least 2 of the 3 examined bars must be aligned (noise-buffer rule). | chartDayFilter.py:73 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | Regex matching per-stock directory `"종목명(123456)"`; captures name & code. Same logical regex as chart60Filter's, declared independently here. | chartDayFilter.py:75 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*$")` | Parses chartDay.md markdown timeseries row: 11 capture groups = (date `YYYY-MM-DD`, O, H, L, C, V, MA10, MA20, MA60, MA306, MA612). Adds a fifth MA column (MA612) vs the intraday pattern. | chartDayFilter.py:78-85 |

---

## Stage 4 — `investorFilter.py` (Investor flow: foreign / institutional / individual)

> Drops stocks under any of four investor-flow exclusion rules across the last 16 trading days.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for date-partitioned reports. | investorFilter.py:39 |
| `_INVESTOR_FILENAME` | `Final[str]` | `"investor.md"` | Input investor-flow report filename (per stock). | investorFilter.py:40 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"investorFilter.md"` | Output filter-result report filename. | investorFilter.py:41 |
| `_REQUIRED_BARS` | `Final[int]` | `16` | Minimum number of trading-day rows required; fewer → excluded ("insufficient data"). | investorFilter.py:43 |
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | `Final[int]` | `2` | Exclude if foreign investors net-sold for ≥ 2 most-recent consecutive days (smart-money distribution signal). | investorFilter.py:46 |
| `_THRESHOLD_INST_CONSEC_SELL` | `Final[int]` | `8` | Exclude if domestic institutions net-sold for ≥ 8 most-recent consecutive days (sustained institutional distribution). | investorFilter.py:47 |
| `_THRESHOLD_INDI_CONSEC_BUY` | `Final[int]` | `3` | Exclude if individual investors net-bought for ≥ 3 most-recent consecutive days (contrarian: heavy retail buying signals smart-money exit). | investorFilter.py:48 |
| `_THRESHOLD_FOREIGN_TOTAL_SELL` | `Final[int]` | `15` | Exclude if foreign investors net-sold on ≥ 15 of the 16 sampled days (long-term distribution pattern). | investorFilter.py:49 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | Regex matching per-stock directory `"종목명(123456)"`; captures name & code. | investorFilter.py:51 |
| `_TABLE_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([+-]?[\d,]+)\s*\|\s*([+-]?[\d,]+)\s*\|\s*([+-]?[\d,]+)\s*\|\s*$")` | Parses investor.md markdown timeseries row: 4 capture groups = (date `YYYY-MM-DD`, individual, foreign, institutional). Signed integers (₩MM, sign preserved). | investorFilter.py:54-59 |

---

## Stage 5 — `financeFilter.py` (Financials: net income negativity exclusion)

> Excludes only if 당기순이익 (net income, ₩억원) is parsed as a real number `< 0`. Missing / invalid markers PASS (lenient). **No tunable threshold constants exist** — the `< 0` comparison is hard-coded inside `evaluate_finance`; this is the documented Phase-1 tuning limitation.

| Variable | Type | Current Value | Meaning | File:Line |
|---|---|---|---|---|
| `_DEFAULT_REPORTS_ROOT` | `Final[Path]` | `Path("reports")` | Default root directory for date-partitioned reports. | financeFilter.py:34 |
| `_FINANCE_FILENAME` | `Final[str]` | `"finance.md"` | Input financial-snapshot report filename (per stock). | financeFilter.py:35 |
| `_OUTPUT_FILENAME` | `Final[str]` | `"financeFilter.md"` | Output filter-result report filename. | financeFilter.py:36 |
| `_STOCK_DIR_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^(.+?)\((\d{4,6})\)$")` | Regex matching per-stock directory `"종목명(123456)"`; captures name & code. | financeFilter.py:38 |
| `_CUP_NGA_ROW_PATTERN` | `Final[re.Pattern[str]]` | `re.compile(r"^\|\s*당기순이익 \(억원\)\s*\|\s*(.+?)\s*\|\s*$")` | Parses the single row that reports net income; capture group 1 = raw value cell (number, `—`, or marker text). | financeFilter.py:41-43 |
| `_INVALID_MARKER` | `Final[str]` | `"응답 데이터 없음"` | Sentinel string written by `finance.render_markdown` when the API returned an empty payload. Treated as missing data → PASS (lenient). | financeFilter.py:46 |

---

## Critical Distinctions (Anti-Confusion)

### `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` — separate constants, similar names

These are **two independent module-level constants in two different files** with similar mnemonic intent but different values, scopes, and consumers. Conflating them during tuning will silently mis-tune an entire stage. Document table:

| Property | `_ALIGN_TOL_LOOSE` | `_MA_ALIGNMENT_TOLERANCE` |
|---|---|---|
| Owning module | `chart60_120Filter.py` | `chart60Filter.py` |
| Line | 120 | 75 |
| Value | `0.015` (×0.985, −1.5% slack) | `0.005` (×0.995, −0.5% slack) |
| Slack | Loose (3× wider) | Strict |
| Scope | **Shared** across Type B (60m & 120m), Type C (MA60-MA306 long-trend leg), Type D (60m fallback 4-line alignment) within chart60_120Filter | Sole alignment tolerance for the standalone chart60Filter 4MA alignment check |
| Impact of change | Cross-cuts Types B/C/D → broad recall/precision shift across multiple pattern detectors in Stage 1 | Localized to chart60Filter only — no cross-stage propagation |
| When to tune | Loosening admits more "imperfect" intraday alignments under Stage-1 pattern logic. Tighten when Stage-1 over-recalls. | Loosening admits more borderline-aligned 60m candidates under the strict 4-line check. Tighten when standalone chart60 over-recalls. |

**Discrimination rule for tuning conversations**: Whenever a user asks "loosen the 60-minute alignment tolerance," you MUST first determine whether they mean the Stage-1 pattern detector (`chart60_120Filter`) or the standalone strict alignment check (`chart60Filter`). The default in production is Stage-1; explicitly disambiguate before any Edit.

### Other look-alike constants discovered

- `_REQUIRED_CONSECUTIVE_BARS`: declared independently in **three** modules — `chart60Filter.py:78` (value `3`), `chart240Filter.py:81` (value `3`), `chartDayFilter.py:72` (value `3`). Same name, same value today, but each is a **separate** constant scoped to its module. Tuning one does NOT affect the others. Particularly subtle in Stage 3 because chartDay also has `_REQUIRED_ALIGNED_BARS=2`, so the rule is "≥ 2 of 3" rather than "all 3."
- `_REQUIRED_STATIC_BARS` (chart60_120Filter.py:116, value `8`) vs `_REQUIRED_CONSECUTIVE_BARS` (Stage-2 and Stage-3, value `3`) and `_REQUIRED_BARS` (investorFilter.py:43, value `16`): three different "window-size" constants with three different semantics — be precise in conversations.
- `_TYPE_D_DYNAMIC_WINDOW` (16) vs `_TYPE_E_DYNAMIC_WINDOW` (8): both are 60-min `close > MA60` ratio windows, but for different Types and different ratios (50% vs 75%). The PRD §5.1 footnote correctly notes these are rarely tuned because they're bounded by the 16-bar input fixture.
- `_STOCK_DIR_PATTERN` and `_TABLE_ROW_PATTERN`: declared by name in **multiple** modules (chart60, chartDay, investor, finance, and re-imported by chart60_120 / chart240). Logically identical for `_STOCK_DIR_PATTERN`; the `_TABLE_ROW_PATTERN` regexes differ structurally because each timeseries table has a different column count (60m: 10 groups including HH:MM; daily: 11 groups including MA612; investor: 4 groups, signed integers; finance: not a table — single-row pattern).
- `_MA60_MA306_TOLERANCE` (chart240Filter.py:78, value `0.025` / −2.5%) vs `_MA60_MA306_LOWER_TOL` (chartDayFilter.py:63, value `0.15` / −15%) vs `_TYPE_E_MA60_OVER_MA306_TOL` (chart60_120Filter.py:156, value `0.035` / −3.5%): three different MA60-vs-MA306 long-trend tolerances on three different timeframes — much looser on daily because long-term-base divergence is meaningful only on the daily timeframe.

---

## PRD §5.1 Cross-Reference

| PRD ID | PRD Variable | PRD Value | Code Value | Status | Notes |
|---|---|---|---|---|---|
| S1-1 | `_TYPE_A_ALIGN_TOL` | -3.5% (×0.965) | `0.035` | ✅ matches | chart60_120Filter.py:125 |
| S1-2 | `_ALIGN_TOL_LOOSE` (shared) | -1.5% (×0.985) | `0.015` | ✅ matches | chart60_120Filter.py:120 |
| S1-3 | `_TYPE_B_BELOW_MA60_RATIO` | -3.0% (×0.97) | `0.97` | ✅ matches | chart60_120Filter.py:128 |
| S1-4 | `_ALIGN_TOL_LOOSE` (shared) | -1.5% (×0.985) | `0.015` | ✅ matches (same constant as S1-2) | chart60_120Filter.py:120 |
| S1-5 | `_TYPE_C_CONVERGE_PCT` | 3.5% (0.035) | `0.035` | ✅ matches | chart60_120Filter.py:131. **Note**: PRD §5.4 narrative text and the `render_markdown` "판정 조건" string in chart60_120Filter.py:866 say "2.0%" — this is **stale documentation**; the live constant is 3.5%. Flag for §5.4 doc correction. |
| S1-6 | `_TYPE_D_ALIGN_TOL_120` | -2.0% (×0.98) | `0.020` | ✅ matches | chart60_120Filter.py:134 |
| S1-7 | `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 50% (0.50) | `0.50` | ✅ matches | chart60_120Filter.py:137. PRD §5.3 "60% 이상" narrative is stale; live constant is 50%. |
| S1-8 | `_TYPE_E_SPREAD_PCT` | 10.0% (0.10) | `0.10` | ✅ matches | chart60_120Filter.py:143 |
| S1-9 | `_TYPE_E_SHORT_ALIGN_TOL` | -1.6% (×0.984) | `0.016` | ✅ matches | chart60_120Filter.py:152 |
| S1-10 | `_TYPE_E_CLOSE_OVER_MA60_RATIO` | 75% (0.75) | `0.75` | ✅ matches | chart60_120Filter.py:146 |
| S1-10a | `_TYPE_E_MA60_OVER_MA306_TOL` | -3.5% (×0.965) | `0.035` | ✅ matches | chart60_120Filter.py:156 |
| S1-11 | `_REQUIRED_STATIC_BARS` | 8 bars | `8` | ✅ matches | chart60_120Filter.py:116 |
| S1-12 | (hard-coded, no `Final` constant) | latest 1 bar | n/a | ✅ matches by design | PRD correctly notes this is not a `Final` constant. |
| S2-1 | `_MA60_MA306_TOLERANCE` | -2.5% (×0.975) | `0.025` | ✅ matches | chart240Filter.py:78 |
| S2-2 | `_REQUIRED_CONSECUTIVE_BARS` | 3 bars (all) | `3` | ✅ matches | chart240Filter.py:81 |
| S21-1 | `_DAILY_SURGE_THRESHOLD` | +15% (0.15) | `0.15` | ✅ matches | chartDayPreFilter.py:51 |
| S3-1 | `_MA10_MA20_MA60_TOLERANCE` | -5.0% (×0.95) | `0.05` | ✅ matches | chartDayFilter.py:61 |
| S3-2 | `_MA60_MA306_LOWER_TOL` | -15% (×0.85) | `0.15` | ✅ matches | chartDayFilter.py:63 |
| S3-3 | `_MA60_MA306_UPPER_TOL` | +45% (×1.45) | `0.45` | ✅ matches | chartDayFilter.py:64 |
| S3-4 | `_CLOSE_VS_MA612_LOWER` | -15% (×0.85) | `-0.15` | ✅ matches | chartDayFilter.py:68 |
| S3-5 | `_CLOSE_VS_MA612_UPPER` | +50% (×1.50) | `0.50` | ✅ matches | chartDayFilter.py:69 |
| S3-6 | `_REQUIRED_ALIGNED_BARS` / `_REQUIRED_CONSECUTIVE_BARS` | 2 of 3 | `2` / `3` | ✅ matches | chartDayFilter.py:72-73 |
| S3-7 | (hard-coded comparison) | close > prev close | n/a | ✅ matches by design | PRD correctly notes this is hard-coded. |
| S4-1 | `_THRESHOLD_FOREIGN_CONSEC_SELL` | ≥ 2 days | `2` | ✅ matches | investorFilter.py:46 |
| S4-2 | `_THRESHOLD_INST_CONSEC_SELL` | ≥ 8 days | `8` | ✅ matches | investorFilter.py:47 |
| S4-3 | `_THRESHOLD_INDI_CONSEC_BUY` | ≥ 3 days | `3` | ✅ matches | investorFilter.py:48 |
| S4-4 | `_THRESHOLD_FOREIGN_TOTAL_SELL` | 16 of ≥15 | `15` | ✅ matches | investorFilter.py:49 |
| Stage 5 (no IDs) | hard-coded `cup_nga < 0` | hard-coded | hard-coded | ✅ matches by design | PRD correctly flags Phase-1 untunable. No `Final` constants for the threshold. |

**Constants in code but missing from PRD §5.1 catalog (❓)**: All filename/path constants (`_DEFAULT_REPORTS_ROOT`, `_*_FILENAME`, `_OUTPUT_FILENAME` across all 7 modules), all regex constants (`_STOCK_DIR_PATTERN`, `_TABLE_ROW_PATTERN`, `_NAME_CODE_RE`, `_CUP_NGA_ROW_PATTERN`), all label constants (`_LABEL_A..E`, `_LABEL_EXCLUDED`, `_LABEL_SKIP`), `_INVALID_MARKER`, `_STAGES`, `_TYPE_CHECKERS`, the standalone-chart60 constants (`_MA_ALIGNMENT_TOLERANCE`, `_REQUIRED_CONSECUTIVE_BARS`, `_REQUIRED_STATIC_BARS`-related window helpers `_TYPE_D_DYNAMIC_WINDOW`/`_TYPE_E_DYNAMIC_WINDOW`/`_TYPE_E_SHORT_ALIGN_WINDOW`), `_REQUIRED_BARS` (investor). These are intentionally omitted from PRD §5.1 because they are not user-facing tuning targets — they are structural / parsing / scaffolding. However, they ARE part of the SOT and must be enumerated for completeness.

**Constants in PRD §5.1 but absent from code (❗)**: **None detected.** Every PRD catalog row maps to a live code constant or is explicitly annotated as hard-coded.

**Discrepancies flagged for Orchestrator (⚠️)**:
1. PRD §5.4 narrative line for `_ALIGN_TOL_LOOSE` influence list says "Type B 60분 정배열, Type B MA60-MA306, Type C MA60-MA306, Type D 60분 정배열" — code-confirmed correct in `_check_type_b`, `_check_type_c` (MA60-MA306 leg uses `_ALIGN_TOL_LOOSE`), and `_check_type_d` (60m fallback `_is_4ma_aligned(b, _ALIGN_TOL_LOOSE)`). No discrepancy, but Type C convergence threshold inside `_c120` uses `_TYPE_C_CONVERGE_PCT` and PRD §5.1 row S1-5 line claims 3.5%, while the **rendered report header** baked into `render_markdown` at chart60_120Filter.py:866 still hard-codes the string `"2.0%"` — **documentation drift inside the source file itself**, not a constant mismatch.
2. Same kind of drift: chart60_120Filter.py:870 `render_markdown` says "비율 ≥ 60%" for Type D close>MA60 ratio while the live constant `_TYPE_D_CLOSE_OVER_MA60_RATIO = 0.50` evaluates to 50%. Tuning-time hazard: a user inspecting the rendered Markdown will see "60%" but the code uses 50%.

These two are NOT constant-value bugs — the math runs on the `Final` constants — but they are user-visible documentation drift inside the report renderer string literals. Flag for stage-1 cleanup pass.

---

## Coverage Self-Check

- [x] `Filter_condition_update.py` — **6** constants extracted (`_DEFAULT_REPORTS_ROOT`, `_MASTER_REFERENCE_MD`, `_MASTER_REFERENCE_LOG`, `_RESEARCHED_MD`, `_STAGES`, `_NAME_CODE_RE`).
- [x] `chart60Filter.py` — **7** constants extracted (`_DEFAULT_REPORTS_ROOT`, `_CHART60_FILENAME`, `_OUTPUT_FILENAME`, `_MA_ALIGNMENT_TOLERANCE`, `_REQUIRED_CONSECUTIVE_BARS`, `_STOCK_DIR_PATTERN`, `_TABLE_ROW_PATTERN`).
- [x] `chart60_120Filter.py` — **26** constants extracted (4 path/file + `_REQUIRED_STATIC_BARS` + `_ALIGN_TOL_LOOSE` + `_TYPE_A_ALIGN_TOL` + `_TYPE_B_BELOW_MA60_RATIO` + `_TYPE_C_CONVERGE_PCT` + `_TYPE_D_ALIGN_TOL_120` + `_TYPE_D_CLOSE_OVER_MA60_RATIO` + `_TYPE_D_DYNAMIC_WINDOW` + `_TYPE_E_SPREAD_PCT` + `_TYPE_E_DYNAMIC_WINDOW` + `_TYPE_E_CLOSE_OVER_MA60_RATIO` + `_TYPE_E_SHORT_ALIGN_WINDOW` + `_TYPE_E_SHORT_ALIGN_TOL` + `_TYPE_E_MA60_OVER_MA306_TOL` + 7 labels + `_TYPE_CHECKERS`).
- [x] `chart240Filter.py` — **5** constants extracted (`_DEFAULT_REPORTS_ROOT`, `_CHART240_FILENAME`, `_OUTPUT_FILENAME`, `_MA60_MA306_TOLERANCE`, `_REQUIRED_CONSECUTIVE_BARS`).
- [x] `chartDayPreFilter.py` — **4** constants extracted (`_DEFAULT_REPORTS_ROOT`, `_CHARTDAY_FILENAME`, `_OUTPUT_FILENAME`, `_DAILY_SURGE_THRESHOLD`).
- [x] `chartDayFilter.py` — **11** constants extracted (3 path/file + `_MA10_MA20_MA60_TOLERANCE` + `_MA60_MA306_LOWER_TOL` + `_MA60_MA306_UPPER_TOL` + `_CLOSE_VS_MA612_LOWER` + `_CLOSE_VS_MA612_UPPER` + `_REQUIRED_CONSECUTIVE_BARS` + `_REQUIRED_ALIGNED_BARS` + `_STOCK_DIR_PATTERN` + `_TABLE_ROW_PATTERN`). *(count = 12 incl. dual regexes; itemized correctly above)*
- [x] `investorFilter.py` — **10** constants extracted (`_DEFAULT_REPORTS_ROOT`, `_INVESTOR_FILENAME`, `_OUTPUT_FILENAME`, `_REQUIRED_BARS`, `_THRESHOLD_FOREIGN_CONSEC_SELL`, `_THRESHOLD_INST_CONSEC_SELL`, `_THRESHOLD_INDI_CONSEC_BUY`, `_THRESHOLD_FOREIGN_TOTAL_SELL`, `_STOCK_DIR_PATTERN`, `_TABLE_ROW_PATTERN`).
- [x] `financeFilter.py` — **6** constants extracted (`_DEFAULT_REPORTS_ROOT`, `_FINANCE_FILENAME`, `_OUTPUT_FILENAME`, `_STOCK_DIR_PATTERN`, `_CUP_NGA_ROW_PATTERN`, `_INVALID_MARKER`).
- [x] All 5 columns (Variable / Type / Current Value / Meaning / File:Line) populated for every row (no blanks).
- [x] `_ALIGN_TOL_LOOSE` (0.015, chart60_120Filter.py:120) and `_MA_ALIGNMENT_TOLERANCE` (0.005, chart60Filter.py:75) both documented and explicitly distinguished in the Critical Distinctions section.
- [x] PRD §5.1 cross-reference completed — all 25 catalogued rows match code values; 2 documentation-drift advisories raised (Type C %, Type D 60m %).

**Grand total: 75 `Final` constants extracted across 8 source files** (7 active filter modules + `Filter_condition_update.py`).
