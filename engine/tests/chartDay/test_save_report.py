"""chartDay saveReport — 디렉터리 명명/마크다운 렌더링 검증."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.kiwoom.chartDay.saveReport import (
    render_markdown,
    save_chartday_markdown,
)


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dt": "20260507",
                "open_pric": 272000,
                "high_pric": 277000,
                "low_pric": 260500,
                "cur_prc": 263500,
                "trde_qty": 33651546,
                "ma10": 232450.0,
                "ma20": 221525.0,
                "ma60": 198205.0,
                "ma306": 103480.07,
                "ma612": 95012.34,
            },
            {
                "dt": "20260508",
                "open_pric": 260000,
                "high_pric": 270000,
                "low_pric": 260000,
                "cur_prc": 268500,
                "trde_qty": 27875253,
                "ma10": 237550.0,
                "ma20": 224425.0,
                "ma60": 200025.0,
                "ma306": 104184.64,
                "ma612": 95800.50,
            },
        ]
    )


def test_render_markdown_contains_expected_sections() -> None:
    md = render_markdown(
        _make_df(),
        stk_cd="005930",
        stk_name="삼성전자",
        fetched_at="2026-05-09 21:30:00",
    )
    assert "# 삼성전자(005930) 일봉 차트 + MA 분석" in md
    assert "## 기본 정보" in md
    assert "## 최근 봉 스냅샷" in md
    assert "## 일봉 시계열" in md
    assert "MA612" in md
    # 가격 천단위 콤마.
    assert "268,500" in md
    # 날짜 변환 (YYYYMMDD → YYYY-MM-DD).
    assert "2026-05-08" in md
    # 데이터 출처가 ka10081 단일.
    assert "ka10081" in md


def test_render_markdown_handles_empty_df() -> None:
    md = render_markdown(pd.DataFrame(), stk_cd="005930", stk_name="삼성전자")
    assert "# 삼성전자(005930)" in md
    assert "응답 데이터 없음" in md


def test_save_uses_execution_date_for_directory(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 21, 30, 0)
    out = save_chartday_markdown(
        df,
        stk_cd="005930",
        stk_name="삼성전자",
        output_root=tmp_path,
        now=fixed_now,
    )
    # <output_root>/<실행일>/<종목명(종목코드)>/chartDay.md
    assert out == tmp_path / "20260509" / "삼성전자(005930)" / "chartDay.md"
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "삼성전자" in body
    assert "2026-05-09 21:30:00" in body


def test_save_uses_stk_cd_only_when_no_name(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 21, 30, 0)
    out = save_chartday_markdown(
        df, stk_cd="005930", output_root=tmp_path, now=fixed_now,
    )
    assert out == tmp_path / "20260509" / "005930" / "chartDay.md"


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    df = _make_df()
    nested = tmp_path / "a" / "b" / "c"
    fixed_now = datetime(2026, 1, 2, 10, 0, 0)
    out = save_chartday_markdown(
        df,
        stk_cd="005930",
        stk_name="삼성전자",
        output_root=nested,
        now=fixed_now,
    )
    assert out == nested / "20260102" / "삼성전자(005930)" / "chartDay.md"
    assert out.exists()


def test_save_filename_is_chartday_md(tmp_path: Path) -> None:
    """chart60.md 와 한 종목 디렉터리에 공존할 수 있도록 파일명이 다른지 확인."""
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 9, 0, 0)
    out = save_chartday_markdown(
        df, stk_cd="005930", stk_name="삼성전자",
        output_root=tmp_path, now=fixed_now,
    )
    assert out.name == "chartDay.md"
