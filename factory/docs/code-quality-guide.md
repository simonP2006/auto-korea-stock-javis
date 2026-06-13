# Code Quality Guide — Stock Filter Orchestration

## Quality Dimensions & Weights

| Dimension | Weight | PASS Criteria |
|-----------|--------|---------------|
| Functional Completeness | 30% | All 12 clusters routable, all chains encoded |
| Internal Consistency | 25% | Zero broken cross-references |
| User Experience | 20% | Natural Korean, correct formatting, clear flow |
| Structural Compliance | 15% | Line counts within bounds, all sections present |
| Safety & Robustness | 10% | TS-1~5 present, range validation, backup protocol |

## Functional Completeness Checklist
- [ ] 12 intent clusters in CLAUDE.md routing table
- [ ] 8 execution chains in stock-scan SKILL.md (SCAN_TODAY, SCAN_SEPARATED, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, COMPARE, COMPARE_PARAMS, RERUN_FILTERS)
- [ ] 8 tuning sequence steps in filter-tune master sequence
- [ ] 6 branches in filter-tune (SHOW_PARAMS, CONFIRM, RESTORE, THEORY_GUIDE, ASK_MODULE, COMPARE_EXPERIMENTS)
- [ ] Pre-flight checks (a-e) executable

## Internal Consistency Rules
- Every skill name in CLAUDE.md → SKILL.md directory exists
- Every references/*.md in SKILL.md → file exists on disk
- Path constants in CLAUDE.md → directories exist (test -d)
- Parameter names in range-map.md → match Python variable names (grep)
- Error types in CLAUDE.md → match Step 1 classification

## UX Quality Standards
- Korean number format: "4,805원", "-3.5%", "0.965배"
- Disclaimer: full on first output per session, abbreviated 1-line on subsequent
- Expression policy: "기술적 완성도가 높은 종목" (O) / "매수 추천" (X)
- Safety warnings in Korean: clear, non-technical language
- Error output pattern: Korean summary (1문장) + 원인 + 조치방법. Technical detail under "기술 정보:" label
- Retry budget: same KRT error 2× → stop, present Korean guide. AI-unresolvable: API 인증, 네트워크, 디스크

## Structural Bounds
- CLAUDE.md: 80-130 lines
- SKILL.md: organized with numbered chains
- references/: flat, complete, no stubs
- state.yaml: valid schema (hook-enforced)

## Safety Requirements
- TS-1: Only Final constants modifiable (no filter logic changes)
- TS-2: Backup before any parameter change (*.bak.YYYYMMDD_HHmmss)
- TS-3: Range validation with Korean warning for out-of-bounds
- TS-4: One-at-a-time recommendation (multi-param warning)
- TS-5: Rerun suggestion after parameter change
