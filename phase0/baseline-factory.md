# Phase 0-2b: factory 테스트 베이스라인

- 측정일: 2026-06-13
- 대상 repo: `/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector` (기존 실repo, 수정·커밋 없음)
- 실행 환경: Python 3.12.7, pytest 9.0.3, pyyaml 6.0.3 (모두 기설치 — 추가 pip 설치 불필요)
- 실행 위치: repo 루트에서 실행 (`cd` 후 `python3 -m pytest ...`)

## 1) 루트 스위트: `python3 -m pytest tests/ -q`

| 항목 | 값 |
|---|---|
| 수집 | 64 tests collected |
| 결과 | **64 passed** in 0.56s (재실행 0.51s, 재현 확인) |
| 실패 | 0 |

테스트 파일 (3개, `tests/` 디렉토리):
- `tests/test_codegen_pipeline.py`
- `tests/test_sot_schema_enforcement.py`
- `tests/test_state_machine_invariants.py`

## 2) factory 스위트: `python3 -m pytest prompt/.claude/tests/ -q`

| 항목 | 값 |
|---|---|
| 수집 | 55 tests collected |
| 결과 | **1 failed, 54 passed** in 0.15s |
| 실패 | 1 (아래 상세) |

테스트 파일 (11개 + conftest.py + run_tests.py, `prompt/.claude/tests/`):
`test_param_values.py`, `test_step_01_research.py`, `test_step_02_integration.py`, `test_step_04_architecture.py`, `test_step_05_blueprint.py`, `test_step_06_skill_design.py`, `test_step_08_claude_md.py`, `test_step_09_skills.py`, `test_step_10_infra.py`, `test_step_11_smoke.py`

### 실패 상세 (1건)

- 테스트: `prompt/.claude/tests/test_step_08_claude_md.py::test_line_count` (assert 위치: 같은 파일 line 17)
- 단언: `assert 80 <= len(lines) <= 130` — "CLAUDE.md is 150 lines (expected 80-130)"
- 검사 대상 파일: `KRT_ROOT / "CLAUDE.md"` (`test_step_08_claude_md.py:8`)
  - `KRT_ROOT` 정의: `prompt/.claude/tests/conftest.py:9` — `Path(os.environ.get("KRT_ROOT", "/Users/tajun/spJavis/kiwoom-rest-trader"))`
  - 즉 실제 검사 파일 = `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md`
- 실측: `wc -l` = **150 lines** (파일 mtime 5월 31 19:53, 20,308 bytes) → 상한 130 초과 20줄
- 성격: 코드 결함이 아닌 **베이스라인 드리프트** — 배포된 kiwoom-rest-trader/CLAUDE.md가 테스트 작성 시점 기대 범위(80–130줄)보다 커진 상태. 같은 파일의 `test_file_exists`, `test_no_placeholders` 등 나머지 검증은 통과.
- 본 과업 규칙(파일 수정 금지)에 따라 수정하지 않고 기록만 함.

## 3) 의존성 기록

- 부족 모듈 없음 — 두 스위트 모두 수집·실행 완료 (ModuleNotFoundError 0건).
- `pip3 install --user` 추가 설치 수행하지 않음.

## 4) 베이스라인 요약

| 스위트 | 수집 | passed | failed | 비고 |
|---|---|---|---|---|
| `tests/` (루트) | 64 | 64 | 0 | 그린 |
| `prompt/.claude/tests/` (factory) | 55 | 54 | 1 | `test_step_08_claude_md.py::test_line_count` — 외부 파일(kiwoom-rest-trader/CLAUDE.md) 150줄 > 상한 130 |

합계: 119 수집 / 118 passed / 1 failed.
