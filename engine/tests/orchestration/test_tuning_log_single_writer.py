"""tuning-log single-writer 가드레일 — Option B 스펙 불변식 잠금.

이 제품은 CLAUDE.md/skill 마크다운 기반 오케스트레이션 레이어이므로,
`stocks_passed_after` 흐름의 정합성은 Python 동작이 아니라 **skill 스펙**에 산다.
본 테스트는 Option B(2026-05-31, ADR-014)에서 확립한 불변식을 박제하여
향후 편집이 유령(phantom) cross-write를 재도입하거나 안전장치를 누락하지
못하도록 한다.

불변식:
1. 유령 cross-write 표현(순차 채움/행 생성 owner/비동시 2단계) 재발 금지.
2. `cross-write`라는 단어는 오직 *금지* 문맥에서만 등장.
3. filter-tune이 tuning-log 8칼럼 전부의 sole writer로 선언.
4. filter-tune backfill이 3곳(스키마 정의·CONFIRM·COMPARE_EXPERIMENTS)에 배선,
   scan_date 게이트 명시.
5. found-but-pending 가드가 3개 reader 전부에 존재.
6. Chain 8이 tuning-log를 쓰지 않음을 명시.
7. screener_state 스키마 불팽창(`rerun_history` 등 신규 키 없음).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# tests/orchestration/test_*.py → parents[2] == repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / ".claude" / "skills"

FILTER_TUNE_SKILL = SKILLS / "filter-tune" / "SKILL.md"
FILTER_TUNE_SEQ = SKILLS / "filter-tune" / "references" / "tuning-sequence.md"
STOCK_SCAN_SKILL = SKILLS / "stock-scan" / "SKILL.md"
EXEC_CHAINS = SKILLS / "stock-scan" / "references" / "execution-chains.md"
OUTPUT_TEMPLATES = SKILLS / "stock-scan" / "references" / "output-templates.md"

ALL_SKILL_FILES = [
    FILTER_TUNE_SKILL,
    FILTER_TUNE_SEQ,
    STOCK_SCAN_SKILL,
    EXEC_CHAINS,
    OUTPUT_TEMPLATES,
]

# 유령 cross-write를 묘사하던 표현들 — 어느 skill 파일에도 다시 나타나면 안 된다.
PHANTOM_PHRASES = ["순차 채움", "행 생성 owner", "비동시 2단계"]

# Option B 이전에 cross-write를 떠받치던 readers (found-but-pending 가드 필수).
PENDING_GUARD_READERS = [STOCK_SCAN_SKILL, EXEC_CHAINS, OUTPUT_TEMPLATES]


def _read(path: Path) -> str:
    assert path.exists(), f"skill 파일 부재: {path}"
    return path.read_text(encoding="utf-8")


def test_skill_files_exist() -> None:
    for path in ALL_SKILL_FILES:
        assert path.is_file(), f"가드레일 대상 파일 부재: {path}"


@pytest.mark.parametrize("path", ALL_SKILL_FILES, ids=lambda p: p.name)
def test_no_phantom_cross_write_phrasing(path: Path) -> None:
    """유령 cross-write 묘사가 어느 skill 파일에도 재발하지 않는다."""
    text = _read(path)
    for phrase in PHANTOM_PHRASES:
        assert phrase not in text, (
            f"{path.name}: 유령 cross-write 표현 '{phrase}' 재발 — "
            f"Option B는 stock-scan→tuning-log cross-write를 제거했다."
        )


@pytest.mark.parametrize("path", ALL_SKILL_FILES, ids=lambda p: p.name)
def test_cross_write_word_only_in_prohibition(path: Path) -> None:
    """`cross-write` 단어는 오직 금지 문맥에서만 등장한다."""
    for i, line in enumerate(_read(path).splitlines(), start=1):
        if "cross-write" in line:
            assert "금지" in line, (
                f"{path.name}:{i}: 'cross-write'가 금지 문맥 밖에서 등장 — "
                f"행: {line.strip()!r}"
            )


def test_filter_tune_declared_sole_writer() -> None:
    """filter-tune이 단독 writer로 선언되고, 읽는 쪽은 sole writer로 인지한다."""
    ft = _read(FILTER_TUNE_SKILL)
    assert "단독 writer" in ft, "filter-tune 스키마 정의에 '단독 writer' 선언 부재."
    for path in (STOCK_SCAN_SKILL, EXEC_CHAINS, OUTPUT_TEMPLATES):
        assert "sole writer" in _read(path), (
            f"{path.name}: filter-tune을 'sole writer'로 명시하지 않음."
        )


def test_backfill_wired_three_sites_with_gate() -> None:
    """filter-tune backfill이 충분히 배선되고 scan_date 게이트가 명시된다."""
    ft = _read(FILTER_TUNE_SKILL)
    assert ft.count("backfill") >= 3, (
        "filter-tune SKILL.md backfill 배선 부족 — "
        "스키마 정의·CONFIRM·COMPARE_EXPERIMENTS 3곳 기대."
    )
    assert "scan_date" in ft, "backfill 게이트(scan_date) 명시 부재."
    assert "backfill" in _read(FILTER_TUNE_SEQ), (
        "tuning-sequence.md가 backfill 미러를 누락."
    )


@pytest.mark.parametrize("path", PENDING_GUARD_READERS, ids=lambda p: p.name)
def test_found_but_pending_guard_present(path: Path) -> None:
    """모든 reader가 pending 셀을 정수로 파싱하지 않고 '재실행 필요'로 처리한다."""
    text = _read(path)
    assert "재실행 필요" in text, (
        f"{path.name}: found-but-pending 가드('재실행 필요') 부재 — "
        f"pending 셀에 정수 연산이 새어 깨진 출력 위험."
    )


def test_chain8_does_not_write_tuning_log() -> None:
    """Chain 8(RERUN_FILTERS)이 tuning-log를 쓰지 않음을 명시한다."""
    text = _read(EXEC_CHAINS)
    assert "쓰지 않는다" in text and "cross-write 금지" in text, (
        "execution-chains.md: Chain 8의 tuning-log 미작성/ cross-write 금지 명시 부재."
    )


@pytest.mark.parametrize("path", ALL_SKILL_FILES, ids=lambda p: p.name)
def test_no_screener_state_schema_bloat(path: Path) -> None:
    """Option B는 신규 screener_state 키를 도입하지 않는다(owned-store 설계 기각)."""
    assert "rerun_history" not in _read(path), (
        f"{path.name}: 'rerun_history' 등장 — Option B는 스키마 불팽창이 전제."
    )
