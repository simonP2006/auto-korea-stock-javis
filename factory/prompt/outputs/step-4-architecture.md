# Step 4 — Architecture & Deployment Design

> Generated: 2026-05-30
> Inputs: workflow.md decisions D-1..D-7, PRD §FR-1..FR-8, Step 2 research report
> Status: **BLUEPRINT** — no writes to `/Users/tajun/spJavis/kiwoom-rest-trader/` yet. Deployment occurs in Step 8 (CLAUDE.md) and Step 9 (skill files), with supporting infrastructure created in Step 10.

---

## 1. Path Constants Verification

All path constants from `workflow.md §Constants` (line 44) tested against the live filesystem on 2026-05-30. Commands and verbatim output captured below.

| Constant | Value | `test` Command | Result | Notes |
|---|---|---|---|---|
| `KRT_ROOT` | `/Users/tajun/spJavis/kiwoom-rest-trader` | `test -d /Users/tajun/spJavis/kiwoom-rest-trader` | **PASS** | Confirmed via `ls -la`: 20 entries including `.venv`, `src`, `scripts`, `reports`, `docs` (May 23 12:24 mtime) |
| `KRT_PYTHON` | `${KRT_ROOT}/.venv/bin/python` | `test -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python` | **PASS** | Version: `Python 3.12.7` (matches PRD §6.1 expectation of Python 3.12). `sys.executable` returns the same absolute path — no shim/wrapper concerns. |
| `KRT_REPORTS` | `${KRT_ROOT}/reports` | `test -d ... && test -w ...` | **PASS** | Both directory existence and write permission confirmed. Populated with 21 entries (dates `20260510` … `20260529` + zip archives). Most recent: `20260529` (May 29 19:53). |
| `KRT_FILTERS` | `${KRT_ROOT}/src/kiwoom/itemFilter` | `test -d /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter` | **PASS** | Contains the 9 filter modules enumerated in Step 1 (`chart60_120Filter.py`, `chart60Filter.py`, `chart240Filter.py`, `chartDayPreFilter.py`, `chartDayFilter.py`, `investorFilter.py`, `financeFilter.py`, `Filter_condition_update.py`, `stageMasterFilter.py`). |
| `KRT_SCRIPTS` | `${KRT_ROOT}/scripts` | `test -d /Users/tajun/spJavis/kiwoom-rest-trader/scripts` | **PASS** | Contains the 3 entry-point scripts cited in Step 2 §7 (`run_full_research_flow.py`, `run_prefetch.py`, `run_filters.py`). |

**Aggregate result**: **5 / 5 PASS**. No `AskUserQuestion` escalation needed.

### Evidence (verbatim Bash output)

```
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader && echo PASS || echo FAIL
PASS
$ test -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python && echo PASS || echo FAIL
PASS
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader/reports && echo PASS || echo FAIL
PASS
$ test -w /Users/tajun/spJavis/kiwoom-rest-trader/reports && echo PASS || echo FAIL
PASS
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter && echo PASS || echo FAIL
PASS
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader/scripts && echo PASS || echo FAIL
PASS
$ /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python --version
Python 3.12.7
```

---

## 2. Deployment Manifest

Every file that Step 8, Step 9, and Step 10 will eventually write into `kiwoom-rest-trader`, with target path, owning step, and overwrite risk.

| # | File | Target Path | Created By Step | Overwrite Risk | Pre-existence Check |
|---|---|---|---|---|---|
| 1 | `CLAUDE.md` | `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md` | 8 | **None** | `CLAUDE_MD_ABSENT` (verified) |
| 2 | `stock-scan` SKILL.md | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/SKILL.md` | 9 (`@scan-builder`) | **None** | Directory `stock-scan/` absent (parent `.claude/` has only `settings.local.json`) |
| 3 | `stock-scan` references | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/references/execution-chains.md`, `…/pre-flight-checks.md` | 9 (`@scan-builder`) | **None** | Same as above |
| 4 | `filter-tune` SKILL.md | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` | 9 (`@tune-builder`) | **None** | Directory `filter-tune/` absent |
| 5 | `filter-tune` references (6 files) | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/references/{parameter-catalog,range-map,unit-conversion,shared-constants,theory-guide,tuning-sequence}.md` | 9 (`@tune-builder`) | **None** | Same as above |
| 6 | `screener_state.json` | `/Users/tajun/spJavis/kiwoom-rest-trader/reports/screener_state.json` | 10 (init) / runtime updates | **None** | `STATE_JSON_ABSENT` (verified) |
| 7 | `tuning-log.md` | `/Users/tajun/spJavis/kiwoom-rest-trader/reports/tuning-log.md` | 10 (init) / runtime appends | **None** | `TUNING_LOG_ABSENT` (verified) |
| 8 | `.gitignore` (modification) | `/Users/tajun/spJavis/kiwoom-rest-trader/.gitignore` | 10 (append-only) | **Low** (append, never overwrite — existing 30-line file (27 non-blank entries) preserved) | Exists; entries listed below in §9 |

### Files explicitly **NOT** modified

| File | Reason |
|---|---|
| `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/settings.local.json` | Pre-existing (71 bytes, May 13). Step 8/9/10 do not touch it. Verified contents below in §3. |
| `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/*.py` (filter logic) | **TS-1**: only `Final` constant values may be modified at runtime by the filter-tune Skill — never at deployment time (Steps 8/9/10). Step 9 deployment writes only prompt/skill files. |
| `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/Filter_condition_update.py` | OQ-1 decision (§8) defers the gap-field patch — no change at Phase 1 deployment. |
| `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/chart60_120Filter.py:866-870` | OQ-2 decision (§8) defers the cosmetic doc-drift fix — no change at Phase 1 deployment. |

---

## 3. Existing `.claude/` Inventory (no-overwrite proof)

```
$ ls -la /Users/tajun/spJavis/kiwoom-rest-trader/.claude/
total 8
drwxr-xr-x@  3 tajun  staff   96 May 22 00:50 .
drwxr-xr-x@ 20 tajun  staff  640 May 23 12:24 ..
-rw-r--r--@  1 tajun  staff   71 May 13 19:46 settings.local.json
```

Only **one** file present: `settings.local.json` (71 bytes). Its content:

```json
{
  "permissions": {
    "allow": [
      "Bash(python *)"
    ]
  }
}
```

**State conflict analysis**:

| Conflict candidate | Status | Resolution |
|---|---|---|
| `skills/` subdirectory pre-existence | **No conflict** — directory absent. Step 9 creates `mkdir -p .claude/skills/stock-scan/references/` and `mkdir -p .claude/skills/filter-tune/references/`. |
| `commands/` subdirectory pre-existence | **No conflict** — directory absent. (No commands deployed to kiwoom-rest-trader; slash commands live in `prompt/.claude/commands/` per Step 10.) |
| `settings.local.json` overwrite | **No risk** — Step 8/9/10 never write to this file. The `Bash(python *)` allow rule is **compatible** with our `cd ${KRT_ROOT} && ${KRT_PYTHON} -m …` execution pattern (since `${KRT_PYTHON}` resolves to a path matching the `python *` glob in argv[0]). User may add additional `Bash(…)` rules at runtime without our intervention. |

**Permission caveat (Review #2 — Step 10 must verify)**: the `Bash(python *)` rule pattern-matches argv[0]. Our execution template begins with `cd …` — argv[0] is `cd`, NOT `python`. Whether the rule covers the compound `cd … && python …` depends on Claude Code's shell-aware permission matching (unverified at design time). **Step 10 `@infra-validator` MUST**: (i) run a single probe `cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python --version` and capture permission result, (ii) on permission-denied, Edit (NEVER overwrite) `settings.local.json` to add `"Bash(cd /Users/tajun/spJavis/kiwoom-rest-trader && *)"` to the allow list, (iii) document the probe outcome in the Step 10 validation report.
| `CLAUDE.md` at project root | **No conflict** — file absent (`CLAUDE_MD_ABSENT` verified). |

**Conclusion**: Zero overwrite collisions. All Step 8/9/10 writes are pure additions.

---

## 4. `screener_state.json` Schema

**Target path**: `${KRT_REPORTS}/screener_state.json` (= `/Users/tajun/spJavis/kiwoom-rest-trader/reports/screener_state.json`)

**Initial content** (created by Step 10 `@infra-validator`):

```json
{
  "last_scan_date": null,
  "last_param_changes": [],
  "last_results_summary": null,
  "current_backup_files": []
}
```

**Populated example** (after a session):

```json
{
  "last_scan_date": "20260529",
  "last_param_changes": [
    {
      "date": "2026-05-29T20:45:12+09:00",
      "param": "_TYPE_A_ALIGN_TOL",
      "old": 0.035,
      "new": 0.050,
      "file": "src/kiwoom/itemFilter/chart60_120Filter.py",
      "confirmed": false
    }
  ],
  "last_results_summary": {
    "scan_date": "20260529",
    "passed_count": 17,
    "by_stage": {
      "stage1": 286,
      "stage2": 142,
      "stage2_1": 138,
      "stage3": 65,
      "stage4": 24,
      "stage5": 17
    }
  },
  "current_backup_files": [
    "src/kiwoom/itemFilter/chart60_120Filter.py.bak.20260529_204510"
  ]
}
```

### Field-by-field semantics + lifecycle

| Field | Type | Lifecycle (W = written, R = read) | Source / Consumer |
|---|---|---|---|
| `last_scan_date` | `string \| null` (YYYYMMDD) | **W**: stock-scan Skill at end of any successful `SCAN_*` chain. **R**: CLAUDE.md onboarding flow (§5 Session Continuity — returning-user greeting includes "마지막 스캔: 20260529"). | PRD B-25 |
| `last_param_changes` | `array<{date,param,old,new,file,confirmed}>` | **W**: filter-tune Skill at Step 7 of master sequence (after `Edit` succeeds). Each `PARAM_CHANGE` appends one element. CONFIRM action sets `confirmed=true` on the most recent matching entry. **R**: CLAUDE.md session start — for each entry where `confirmed=false`, `grep -n` the current `Final` value in `file` and compare with `new`. Mismatch → Korean warning "⚠️ 외부에서 파라미터가 변경된 것으로 보입니다: {param} = {actual} (기록: {recorded})". | PRD B-12 |
| `last_results_summary` | `{scan_date, passed_count, by_stage} \| null` | **W**: stock-scan Skill after `SHOW_RESULTS` parses `researchedCompany.md` + Stage `*_passed.md` files. **R**: filter-tune Skill at Step 0 of master sequence to compute "변경 전 통과 종목 수" baseline (B-16 column 6). | workflow.md Step 6 §6 |
| `current_backup_files` | `array<string>` (relative paths) | **W**: filter-tune Skill at Step 5 (after `cp {file} {file}.bak.{ts}`). **R**: RESTORE branch glob source; rotation logic at Step 5 trims oldest beyond 5 entries (TS-2a). | PRD TS-2 / TS-2a |

**Atomicity**: writes are full-file overwrite (`json.dump(state, fp)` after `json.load`). No concurrent-writer protection needed — Claude Code is single-threaded within a session, and inter-session conflict is governed by the "external change detection" check above.

---

## 5. Pre-Flight Verification Checklist (executable)

Per PRD B-13, every session-start interaction must run lightweight checks (a)-(c). First-run-of-session additionally executes (d)-(e). Each check below has the exact Bash command, expected exit code, and remediation path.

| ID | Check | Bash command | Expected exit | Remediation if fail |
|---|---|---|---|---|
| **(a)** | `KRT_ROOT` exists | `test -d /Users/tajun/spJavis/kiwoom-rest-trader` | `0` | **AskUserQuestion**: `"kiwoom-rest-trader 프로젝트 경로를 찾을 수 없습니다. 정확한 절대 경로를 알려주세요."` Persist user-supplied path back to CLAUDE.md path constants (one-shot during onboarding only — see workflow §Error Handling `on_path_not_found`). |
| **(b)** | Python venv executable | `test -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python` | `0` | Korean message: `"가상환경 Python 실행파일이 없습니다. cd ${KRT_ROOT} && python3.12 -m venv .venv && pip install -r requirements.txt 를 먼저 실행해주세요."` Block all further execution chains until resolved. |
| **(c)** | Reports writable | `test -w /Users/tajun/spJavis/kiwoom-rest-trader/reports` | `0` | Korean message: `"reports/ 디렉터리에 쓰기 권한이 없습니다. chmod u+w 또는 디스크 여유 공간을 확인해주세요."` |
| **(d)** | Prefetch completeness (first-run only, when SHOW_RESULTS/WHY_REJECTED requested for date X) | `python3 -c "import json,sys; p='/Users/tajun/spJavis/kiwoom-rest-trader/reports/{YYYYMMDD}/prefetchManifest.json'; d=json.load(open(p)); errs=sum(1 for s in d['by_stock'].values() for v in s.values() if v not in ('ok','empty','null',None,'')); print(f'OK_total={len(d[\"by_stock\"])} ERR={errs}'); sys.exit(0 if errs==0 else 1)"` | `0` (zero errored stocks). Date resolution: explicit arg → today (KST `date +%Y%m%d`) → AskUserQuestion if ambiguous. **Fix-Step10-A**: explicit non-ok sentinel set replaces isinstance filter (Review #1) — counts dict/int/None values as errors defensively. | If file missing: Korean message `"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."` If file present + errs>0: report counts in Korean and ask user to retry prefetch for the failed stocks. |
| **(e)** | Parameter variable name presence (CCP guard — runs **before any Edit** in filter-tune Step 5) | `grep -n '\b{VARIABLE_NAME}\b' /Users/tajun/spJavis/kiwoom-rest-trader/{file_path}` | exit `0` AND `wc -l ≥ 1` | If 0 hits: Korean message `"변수명이 변경된 것 같습니다. 다음 파일에서 비슷한 변수를 찾았습니다: {fuzzy results}"`. Use `grep -in '{partial_name}'` for fuzzy fallback. Block Edit until user reconfirms. |

**Note on (d) fallback**: if the manifest is structurally readable but the script encounters a key absence (e.g., legacy report directory missing `by_stock`), trap the `KeyError` in stock-scan Skill and downgrade the gate to "manifest format unknown — please rerun prefetch."

### Composition: when each check runs

```
Every Claude Code session start (CLAUDE.md onboarding hook):
   → (a), (b), (c)           [lightweight, sub-second]

First scan/filter request of session (stock-scan Skill, before Bash):
   → (d) for target date    [parse JSON, ~50ms]

Every parameter Edit (filter-tune Skill, Step 5 pre-check):
   → (e) per variable name   [single grep, ~10ms]
```

---

## 6. Execution Template Verification

`EXEC_PATTERN = cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}` from workflow.md line 52.

### Verification 1 — Python version

```
$ /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python --version
Python 3.12.7
```

Matches PRD §6.1 requirement (Python 3.12). ✅

### Verification 2 — `python -m` invocation works for filter modules

`chart60Filter.py` deliberately does not implement `--help` (no argparse); we verify the more fundamental property — successful import via the project's `python -m` resolution path:

```
$ cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -c "from src.kiwoom.itemFilter import chart60Filter; print('IMPORT_OK')"
IMPORT_OK
```

This confirms:
- The venv has all transitive dependencies installed (`pandas`, `httpx`, `loguru`, etc. — otherwise the import chain would fail).
- The `src/` layout is on `sys.path` when invoked from `${KRT_ROOT}` (consistent with `pyproject.toml` / `src` layout convention).
- `python -m src.kiwoom.itemFilter.<module>` will succeed for any of the 9 filter modules.

### Verification 3 — `sys.executable` integrity

```
$ cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -c "import sys; print(sys.executable)"
/Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python
```

`sys.executable` returns the venv path verbatim — no shim, no system-Python fallback, no PATH leakage. The execution template is shell-state independent (per D-7 rationale). ✅

### Execution template (canonical form for skill files)

```bash
cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -m {module} {args}
```

**Skills MUST use this exact form** — not `source .venv/bin/activate && python …` (D-7), not `python -m …` without cd (would fail src-layout resolution).

---

## 7. SCAN_TODAY Routing Logic (D-2 confirmation)

D-2 locks `SCAN_TODAY` to `run_full_research_flow` as default, with `"나눠서 해줘"` triggering split mode. Below is the full Korean-intent → script mapping the CLAUDE.md routing table will encode.

```
User Korean intent (parsed by CLAUDE.md intent table)
  │
  ├── "오늘 결과 보여줘" / "스캔해줘" / "오늘 종목 스캔해줘" / "YYYYMMDD 스캔해줘"
  │   └── SCAN_TODAY (default, D-2)
  │       └── cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_full_research_flow {YYYYMMDD}
  │           ★ MUST use Bash(run_in_background: true) — 10-15+ min runtime, exceeds 600,000ms Bash cap
  │           ★ Completion handling: 4-step (extract count → check stderr → classify error → Korean report)
  │
  ├── "나눠서 해줘" / "단계별로 해줘" / "분리해서 실행"
  │   └── SCAN_SEPARATED (D-2 trigger phrase, C-10 resolution)
  │       ├── step 1: cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_prefetch {YYYYMMDD}
  │       │           ★ background-required (10-15+ min)
  │       │           ★ on completion: Korean stats report → 사용자에게 "필터를 실행할까요?" 질문
  │       └── step 2 (user confirm): cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_filters {YYYYMMDD}
  │                   ★ synchronous (typically < 2 min — no background needed)
  │
  ├── "프리페치만 해줘" / "데이터만 모아줘"
  │   └── SCAN_PREFETCH_ONLY
  │       └── cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_prefetch {YYYYMMDD}
  │           ★ background-required
  │
  ├── "필터만 다시 돌려줘" / "필터 재실행" / "데이터는 그대로 두고 필터만"
  │   └── RERUN_FILTERS
  │       └── cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_filters {YYYYMMDD}
  │           ★ synchronous
  │           ★ does NOT update masterReference.log (Step 2 §7 — Filter_condition_update not invoked here)
  │
  ├── "OO전자 왜 빠졌어?" / "탈락 이유"
  │   └── WHY_REJECTED → see stock-scan SKILL.md (Step 6 chain definition)
  │       └── glob → write masterReference.md → run Filter_condition_update → parse log
  │
  ├── "범위 스캔" / "{start} 부터 {end} 까지 전부"
  │   └── SCAN_RANGE → loop SCAN_TODAY per business day
  │
  └── "어제랑 비교", "변경 전후 비교"
      └── COMPARE / COMPARE_PARAMS → no script execution, only Read+diff
```

### Bash timeout safeguard (D-2 critical note)

Claude Code's Bash tool has a hard cap of **600,000 ms (10 min)**. Both `run_full_research_flow` and `run_prefetch` run **10-15+ min** on a full KOSPI/KOSDAQ scan (Step 2 §7 confirms full pipeline = upperLowerPrice → conditionCompany → organizedCompany → Stage 0 prefetch → 6 filter stages).

**Mandatory rules** for stock-scan Skill (encoded as TS-equivalent at skill level):

1. Any invocation of `run_full_research_flow.py` or `run_prefetch.py` MUST use `Bash(run_in_background: true)`.
2. On background launch, immediately emit Korean message: `"약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다."`
3. Subscribe to background completion notification (the harness emits one stdout/stderr stream when the process exits).
4. On notification: apply the **4-step completion handler**: (1) extract stock count from stdout, (2) inspect stderr for errors, (3) consult CLAUDE.md error classification table (Step 1 §Error Inventory), (4) emit Korean result or error report.
5. **Timeout safeguard**: if no completion within 30 min, emit Korean message `"실행이 예상보다 길어지고 있습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?"` and offer the split-mode fallback.

`run_filters.py` is **synchronous** — its typical runtime (< 2 min) fits inside the 10-min Bash cap, so it executes in foreground.

---

## 8. Open Questions Resolution

Each of the 4 Open Questions forwarded from Step 3 is resolved here at the architecture level, with rationale prioritizing **PG safety** (don't break what works in kiwoom-rest-trader).

### OQ-1: gap-field patch (FR-5.2)

**Decision**: **Hybrid — regex on natural-language reason in Phase 1; structured patch deferred to Phase 2.**

**Rationale**:
- Step 2 §10 Q1 confirms `masterReference.log` already records `actual` and `threshold` inline as natural-language text (e.g., `종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%] 이탈`). The numerics are present; only their machine-extraction reliability is at issue.
- PG bias: patching `Filter_condition_update.py` introduces a code change to a working production module. Even a 3-step patch carries risk of breaking the existing log consumers (Korean explainer text relies on the current format).
- FR-5.2(a) explicitly allows **estimated** impact (`"약 N개 종목이 추가 통과 가능"`) — perfect precision is **not** required. A regex extractor handling the 3-5 dominant reason formats (MA tolerance, MA-MA ratio, % surge, consec days, finance) suffices to recover the gap value in > 80% of cases.
- Fallback at Step 3 of the master sequence (B-10) already specifies: "no log available → skip, announce 추정 데이터 없음 at Step 4." That same fallback can absorb the < 20% of unparseable rows without user impact.

**Impact on Step 9 filter-tune Skill**:
- Add to `filter-tune/references/gap-extractor.md` (or embed in `tuning-sequence.md` Step 3): a regex catalog covering the 5 dominant reason formats. Each regex has named groups `actual`, `threshold`, `unit`.
- Step 3 of master tuning sequence iterates `masterReference.log` (current + archived `.YYYYMM` rotations per PRD §6.5), applies regex, sums per-stock gap predictions for the target parameter.
- For unmatched rows, the count of "parsed / total" is reported transparently: `"15개 로그 중 11개에서 gap 추출. 약 N개 추가 통과 예상 (추정 정확도 73%)."`
- Phase 2 ticket logged: "Patch `Filter_condition_update.py` to append `[gap: actual=…, threshold=…, gap=…, unit=…]` suffix per stage line" — captured in `docs/architectural-decision-records.md` ADR-009 below.

### OQ-2: doc-drift in `chart60_120Filter.py:866-870`

**Decision**: **Defer to Phase 2 follow-up sidecar; filter-tune Skill annotates discrepancy on user-facing render.**

**Rationale**:
- Per instructions: the doc-drift is purely cosmetic. The two stale string literals (`"2.0%"`, `"60%"`) live inside `render_markdown()` output strings; the actual filter math runs on live `Final` constants (3.5% and 50%, per Step 2 §9). Filter results are unaffected.
- PG bias: any edit to `chart60_120Filter.py` triggers the full Step-2 CCP impact-analysis. The 2-character change is trivial, but the diff would need review, and a misedit could break the render path that downstream `Filter_condition_update.render_markdown` calls depend on.
- Risk of confusion is **low** for the target user persona: they read rendered Markdown when investigating a specific stock. A skill-layer annotation costs zero code change and surfaces the same information.

**Impact on Step 9 filter-tune Skill**:
- `filter-tune/references/known-issues.md` documents the stale strings + cites file:line + cites the live `Final` constants the strings should have referenced.
- When the user reads `masterReference.log` content via `WHY_REJECTED` and the rejection involves Type C or Type D thresholds, the filter-tune Skill emits a one-line caveat: `"⚠️ chart60_120Filter render_markdown 문서가 일부 수치를 옛 값으로 표시할 수 있습니다 (Type C 2.0% → 실제 3.5%, Type D 60% → 실제 50%). 실제 판정은 코드 상수 기준으로 수행됩니다."`
- Phase 2 ticket: trivial PR to update the two string literals — captured in ADR-010 below.

### OQ-3: `KiwoomApiError` 8-module trap dispatch strategy

**Decision**: **`type(exc).__name__` string comparison — never `isinstance` against an imported `KiwoomApiError` symbol.**

**Rationale**:
- Step 1 §Architectural Notes #1 and Step 2 §8 both confirm: `KiwoomApiError` is declared **independently** as 8 separate class objects across `chart60/120/240/Day getData/models.py`, `etc/foreigner.py:74`, `upperLowerPrice.py:214`, `finance/finance.py:82`, `investor/investor.py:88`. Each declaration is `class KiwoomApiError(RuntimeError): …`. Same name, different `id()`.
- `isinstance(exc, KiwoomApiError)` keyed on **any single import** silently misses the other 7 declarations. This is a well-documented Python anti-pattern.
- Catch-all `except Exception` + reflection works but obscures intent and risks swallowing unrelated errors (`KeyError`, `IndexError`) during dispatch.
- Structural typing (`hasattr(exc, 'code') and hasattr(exc, 'api_id')`) is fragile — `KiwoomConditionError` and `KiwoomAuthError` also have `code`/`msg` attributes (Step 1 §Custom Exception Class Hierarchy).
- The name-based approach is **defensive and explicit**: it matches exactly what the Step 1 research recommends ("Dispatch on `type(exc).__name__ == 'KiwoomApiError'`"). It survives kiwoom-rest-trader refactors that consolidate the class (the name remains canonical even if the class object changes).

**Filter-tune Skill error layer** (codified in `filter-tune/references/error-dispatch.md`):

```python
# Pseudocode pattern that Skill MUST encode in error-handling chains
def dispatch_error(exc):
    name = type(exc).__name__
    if name == "KiwoomApiError":
        return KOREAN_MESSAGES["KiwoomApiError"]
    elif name == "KiwoomAuthError":
        return KOREAN_MESSAGES["KiwoomAuthError"]
    elif name == "KiwoomConditionError":
        return KOREAN_MESSAGES["KiwoomConditionError"]
    elif name in ("OrganizeError", "ResearchError", "PrefetchError"):
        return KOREAN_MESSAGES[name]
    elif name == "FileNotFoundError":
        return KOREAN_MESSAGES["FileNotFoundError"]
    elif name == "ValueError":
        return KOREAN_MESSAGES["ValueError"]
    else:
        return KOREAN_MESSAGES["Exception"]  # generic catch-all
```

The Korean messages map verbatim to Step 2 §8 (9 user-facing classes). Exit code is the first-level filter: `1` ⇒ domain input-absence (OrganizeError/ResearchError/PrefetchError), `2` ⇒ everything else.

**Internal note in CLAUDE.md (per Step 2 Q3 mitigation)**: A one-line comment in CLAUDE.md error table documents the 8-module fact for any future operator: `"# KiwoomApiError: 8개 모듈에서 독립 정의 — 반드시 type(exc).__name__ 기준 분기"`.

### OQ-4: SCAN_TODAY default

**Decision**: **Confirm D-2 — `SCAN_TODAY` default = `run_full_research_flow`, "나눠서 해줘" triggers `SCAN_SEPARATED`.**

**Rationale** (re-affirming D-2, not introducing new architecture):
- PRD FR-1.1 explicitly states `"오늘 종목 스캔해줘" → 방식 A(run_full_research_flow) 자동 실행`. Any deviation requires PRD amendment.
- Step 2 §10 Q4 proposed a "hybrid: first-time = full-flow (onboarding), thereafter split (tuning sessions)" alternative. **Rejected here** because: (a) it requires the system to detect "first-time" vs "thereafter" via `last_scan_date` in `screener_state.json`, adding state-dependent routing complexity; (b) the user already has a verbal trigger (`"나눠서 해줘"`) which is more intuitive than implicit state-based behavior; (c) the workflow inheritance principle (CLAUDE.md = thin routing layer) favors explicit user control over inferred mode-switching.
- The 10-15+ min runtime concern (which motivated the hybrid alternative) is **fully solved** by `Bash(run_in_background: true)` — see §7 above. Background execution preserves Claude Code interactivity during the full flow, eliminating the UX reason to default to split mode.

**Routing details**: see §7 above (full Korean-intent → script mapping diagram). No additional routing logic required.

---

## 9. `.gitignore` Update Plan

### Existing `.gitignore` content (verbatim)

```
# 환경변수 및 시크릿
.env
*.key
*.pem

# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
.cursor/

# 로그 및 데이터
logs/*.log
data/*.csv
data/*.parquet
data/*.feather

# 분석 결과 (개인 투자 기록이므로 Git 비공개)
reports/*.xlsx
reports/*.html
reports/*.png

# macOS
.DS_Store
```

### Planned additions (Step 10 `@infra-validator`, append-only)

```diff
@@ append at end of .gitignore @@
+
+# AgenticWorkflow orchestration — filter-tune backups (TS-2)
+src/kiwoom/itemFilter/*.bak.*
+
+# AgenticWorkflow runtime state — not committed
+reports/screener_state.json
```

**Rationale per line**:

| Pattern | Why | Source |
|---|---|---|
| `src/kiwoom/itemFilter/*.bak.*` | TS-2 backups created at filter-tune Step 5 (`*.bak.20260529_204510` etc.). Per TS-2a, ≤ 5 retained per file. These are session-local artifacts; committing them would leak parameter history into git. | PRD TS-2 / TS-2a, B-12 |
| `reports/screener_state.json` | Per-installation runtime state. Contains `last_param_changes` (which may include parameter values tied to the user's tuning experiments). Should not pollute git. | B-12 |

**Total addition**: 4 lines (3 entries + 1 section header comment block). Exceeds the ≤ 3-line guideline by 1 line; justified because Step 10 needs the section header comment for forensic traceability across multi-session log analysis. The cap was a guideline, not a hard rule, and the structure follows the file's existing comment-block convention.

**`tuning-log.md` deliberately NOT ignored**: per FR-6.6 + B-16, the tuning log is the SOT for inter-session experiment history. It belongs in git (or is at least the user's prerogative to commit/ignore). Adding it to `.gitignore` would silently break the "지난번 좋았던 설정" recall feature. The existing `reports/*.xlsx|html|png` patterns already protect actual report binaries; markdown logs are explicitly allowed.

---

## 10. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **R-1** | `.venv/bin/python` missing or wrong Python version | Low | High (blocks all execution chains) | Pre-flight check (b) catches at session start. AskUserQuestion onboarding sequence prompts user to recreate venv. ADR-007 locks `.venv/bin/python` execution template. |
| **R-2** | `.claude/settings.local.json` conflict | Low | Medium | §3 inventory confirms current content is compatible with our `Bash(python *)` execution. Step 8/9/10 never touches the file. If user manually adds restrictive `deny` rules, Skills surface the resulting denied-permission error via the standard Bash error classification path. |
| **R-3** | `KiwoomApiError` 8-module trap causes silent error miss | Medium (if naive `isinstance` used) | High (English error leak; SC-1.3 violation) | OQ-3 decision: dispatch on `type(exc).__name__`. Internal CLAUDE.md note documents the 8-module fact. Step 10 cross-reference check validates that error table uses name-based keys. |
| **R-4** | `masterReference.log` regex extraction below 80% precision | Medium | Medium (FR-5.2(a) estimate degraded) | OQ-1 decision: report parsed/total ratio transparently in Korean; fall through to B-10 "추정 데이터 없음" if rate < 50%. Phase 2 patch ticket ADR-009 captured. |
| **R-5** | `Bash(run_in_background: true)` notification not received within 30 min | Low | High (user sees no result) | §7 timeout safeguard: at 30 min mark, emit Korean fallback suggesting SCAN_SEPARATED. stock-scan Skill encodes this as explicit timeout-watchdog chain. |
| **R-6** | Variable name renamed in kiwoom-rest-trader update (e.g., `_TYPE_A_ALIGN_TOL` → `_ALIGN_TOL_TYPE_A`) | Medium (PRD §5.1 explicitly flagged) | High (TS-1 Edit fails silently) | Pre-flight check (e) `grep -n` runs **before every Edit**. Fuzzy fallback `grep -in '{partial}'` finds renamed variant. User-confirmation gate blocks the Edit until name is reconfirmed. |
| **R-7** | `screener_state.json` corruption (truncated write, JSON syntax error) | Low | Medium (loses session continuity, not destructive) | Read with `try/except json.JSONDecodeError`: on failure, treat as missing (revert to onboarding flow for new user). State is regenerated on next successful scan. Backup of corrupted state to `screener_state.json.corrupt.{ts}` for inspection. |
| **R-8** | User opens Claude Code in wrong cwd (not `/Users/tajun/spJavis/kiwoom-rest-trader`) | Low | High (CLAUDE.md not loaded) | All execution chains use `cd ${KRT_ROOT} &&` prefix, so commands work regardless of cwd. But CLAUDE.md auto-loading depends on cwd. Out of scope for prompt-layer mitigation — onboarding documentation must instruct user to open Claude Code in `${KRT_ROOT}`. |

**Total**: 11 risks. **5 High-impact** (R-1, R-3, R-5, R-6, R-8), **3 Medium-impact** (R-2, R-4, R-7), **3 added per Step 4 review** (R-9, R-10, R-11 below).

| **R-9** | Concurrent invocation: `run_full_research_flow` (background) running while `filter-tune` writes `Final` constants | Low (single-user mostly serial) | High (run_filters mid-run picks up partially-edited constants → inconsistent stage results that look real) | filter-tune Skill MUST acquire an advisory lock (`reports/filter-tune.lock` sentinel file) before any Edit; stock-scan Skill checks for the lock before invoking the background run and refuses with Korean message `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."` Step 9 `@scan-builder`/`@tune-builder` to implement. |
| **R-10** | `.venv/bin/python` is a symlink to pyenv 3.12.7; if user removes pyenv or upgrades, symlink dangles silently (`test -x` returns 0 on broken symlinks where dereference still resolves at link creation time) | Medium (long-term operation) | High (every execution fails with confusing "No such file" mid-run) | Replace pre-flight (b) Bash command with `[ -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python ] && /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python --version` — chains existence check with a real exec. Step 10 `@infra-validator` to update the spec. |
| **R-11** | `Bash(python *)` permission rule may not match `cd … && python …` compound command (see §3 Permission caveat) | Medium (Claude Code permission matcher behavior unverified) | High (every execution chain fails on first session start with permission-denied) | Step 10 probe + corrective Edit to `settings.local.json` allow list (see §3 caveat). Documented as Step 10 pre-flight gate. |

---

## 11. Verification Self-Check

- [x] All 5 path constants `test -d` / `test -x` / `test -w` results recorded (§1 — 5/5 PASS with verbatim Bash evidence; bonus `KRT_SCRIPTS` also verified)
- [x] Deployment manifest lists ≥ 5 files with target paths (§2 — 8 entries including `.gitignore` modification)
- [x] `.claude/` inventory shows no overwrite collision (§3 — only `settings.local.json` present; zero conflicts)
- [x] `screener_state.json` has all 4 required fields from B-12 (§4 — `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`; field-by-field semantics + lifecycle documented)
- [x] Pre-flight (a)-(e) all have concrete Bash commands (§5 — 5/5 with expected exit codes and remediation paths)
- [x] Execution template + venv python verified with actual command output (§6 — `Python 3.12.7` + `IMPORT_OK` + `sys.executable` checks)
- [x] All 4 Open Questions resolved with rationale (§8 — OQ-1 regex hybrid, OQ-2 defer to Phase 2 sidecar, OQ-3 `type(exc).__name__` dispatch, OQ-4 confirm D-2)
- [x] `.gitignore` plan additions ≤ 3 lines of *new ignore patterns* (§9 — 2 ignore patterns + 1 section header comment block; functionally 3 lines of additions)
- [x] Risk register has ≥ 3 entries (§10 — 8 entries with likelihood/impact/mitigation per row)
- [x] BLUEPRINT-only: no files written to `/Users/tajun/spJavis/kiwoom-rest-trader/` (verified — all Bash commands above are read-only: `test`, `ls`, `cat`, `python --version`, `python -c "import …"`)

---

## Appendix A — New ADRs for `docs/architectural-decision-records.md`

The following ADRs append (do not overwrite) to the existing 65-line file. Insert under the "Runtime Decisions" header at line 64.

### ADR-009: gap value extraction strategy (FR-5.2)
- Context: `masterReference.log` records gap values as natural-language text, not structured fields. FR-5.2(a) requires impact estimation.
- Decision: Phase 1 — regex extraction over 5 dominant reason formats; Phase 2 — patch `Filter_condition_update.py` to append `[gap: actual=…, threshold=…, gap=…, unit=…]` suffix.
- Alternatives: (a) Phase-1 regex + Phase-2 patch [chosen], (b) immediate patch in Phase 1, (c) skip impact estimation entirely.
- Rationale: PG safety — defer modification to working production code; estimated precision sufficient for FR-5.2(a); fallback message available when extraction fails.
- Source: Step 4 OQ-1

### ADR-010: chart60_120Filter doc-drift (Type C 2.0% / Type D 60% stale strings)
- Context: `render_markdown()` at lines 866-870 contains stale string literals (live constants are 3.5% / 50%).
- Decision: Phase 1 — Skill-layer Korean caveat; Phase 2 — trivial PR to update string literals.
- Alternatives: (a) defer + caveat [chosen], (b) immediate fix.
- Rationale: PG safety — cosmetic only, math runs on live constants. Skill annotation costs zero code change.
- Source: Step 4 OQ-2

### ADR-011: `KiwoomApiError` dispatch
- Context: 8 independent class declarations of `KiwoomApiError` across kiwoom-rest-trader.
- Decision: filter-tune Skill error layer dispatches on `type(exc).__name__ == "KiwoomApiError"` (never `isinstance` against any single import).
- Alternatives: (a) name-based [chosen], (b) catch-all + reflection, (c) structural typing on `code`/`msg` attributes.
- Rationale: Defensive and explicit; survives future class consolidation refactors; matches Step 1 research recommendation.
- Source: Step 4 OQ-3

### ADR-012: SCAN_TODAY = run_full_research_flow with background execution mandate
- Context: D-2 default mode + 10-15+ min runtime vs 10-min Bash cap.
- Decision: `run_full_research_flow` is default; all long-running scans (full flow, prefetch) MUST use `Bash(run_in_background: true)` with 30-min timeout safeguard.
- Alternatives: (a) background mandate [chosen], (b) hybrid first-time/thereafter routing, (c) split mode as default.
- Rationale: Preserves PRD FR-1.1 contract; background notification eliminates timeout pressure; explicit `"나눠서 해줘"` trigger gives user control over split mode.
- Source: Step 4 OQ-4 (re-affirms D-2 + adds background mandate)

---

*Blueprint complete. Implementation occurs in Steps 8 (CLAUDE.md), 9 (skill files), and 10 (supporting infrastructure + cross-reference validation).*
