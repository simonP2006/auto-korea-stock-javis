# Code Convention — Stock Filter Orchestration

## Naming
- Skill directories: kebab-case (stock-scan/, filter-tune/)
- Output files: step-{N}-{descriptor}.md
- Reference files: kebab-case.md
- Agent files: kebab-case.md matching agent role name

## Markdown Structure
- CLAUDE.md: max 130 lines, 10 sections, no headers beyond H3
- SKILL.md: numbered chains with [checkpoint] markers
- references/: flat directory, no subdirectories

## Content Rules
- Zero placeholder text (TODO, TBD, PLACEHOLDER, XXX — grep-enforced)
- All path constants: verified absolute paths resolving to real filesystem
- Korean text: natural phrasing, Korean number formatting
- Parameter names: exact match to Python variable names (grep-verified)
- Cross-references: every mentioned file must exist on disk
- Log file manipulation: append-only files (masterReference.log, tuning-log.md) use Edit tool (append) — never Write (full overwrite)
- Comment hygiene: when modifying a Python constant value, update same-line/adjacent-line comments that reference the old value. Leave unrelated comments untouched
- Tuning log '비고': minimum content = change motivation (user's words) + decision status (확정/실험 중)

## Verification Commands
- Placeholder check: `grep -c 'TODO\|PLACEHOLDER\|TBD\|XXX' {file}` → must return 0
- Line count: `wc -l {file}` → must be within documented range
- Path check: `test -d {path}` → must succeed for all referenced directories
