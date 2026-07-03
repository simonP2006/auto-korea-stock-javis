"""run_backfill CLI 헬퍼 단위 검증 — 주말 거부 · 종목 목록 파싱.

CLI 프로세스가 아니라 순수 헬퍼(``_is_weekend`` / ``_parse_stocks_file``)를
직접 검증한다(네트워크·프로세스 없음).
"""

from __future__ import annotations

import pytest

from scripts.run_backfill import _is_weekend, _parse_stocks_file
from src.kiwoom.researchFlow.backfill import BackfillError


def test_is_weekend_saturday_sunday_true() -> None:
    assert _is_weekend("20260620") is True   # 토
    assert _is_weekend("20260621") is True   # 일


def test_is_weekend_weekday_false() -> None:
    assert _is_weekend("20260618") is False  # 목
    assert _is_weekend("20260619") is False  # 금


def test_parse_stocks_file_code_and_name(tmp_path) -> None:
    p = tmp_path / "stocks.txt"
    p.write_text(
        "# 주석 줄\n"
        "005930,삼성전자\n"
        "\n"
        "000660\n",  # NAME 생략 → CODE 를 종목명으로
        encoding="utf-8",
    )
    candidates, code_map = _parse_stocks_file(p)

    assert [(c.stk_cd, c.stk_nm) for c in candidates] == [
        ("005930", "삼성전자"),
        ("000660", "000660"),
    ]
    assert code_map == {"삼성전자": "005930", "000660": "000660"}


def test_parse_stocks_file_missing_raises(tmp_path) -> None:
    with pytest.raises(BackfillError, match="없음"):
        _parse_stocks_file(tmp_path / "nope.txt")


def test_parse_stocks_file_empty_raises(tmp_path) -> None:
    p = tmp_path / "empty.txt"
    p.write_text("# 주석만\n\n", encoding="utf-8")
    with pytest.raises(BackfillError, match="유효한 종목이 없습니다"):
        _parse_stocks_file(p)
