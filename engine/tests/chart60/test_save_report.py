"""saveReport 모듈 — 디렉터리 명명 / 마크다운 렌더링 검증.

실행 시각을 ``now`` 인자로 주입해 결정적으로 검증한다.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.kiwoom.chart60.saveReport import (
    render_markdown,
    save_chart60_markdown,
)


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "cntr_tm": "20260508140000",
                "ts": pd.Timestamp("2026-05-08 14:00:00"),
                "date": "20260508",
                "open_pric": 266000,
                "high_pric": 270000,
                "low_pric": 265500,
                "cur_prc": 269000,
                "trde_qty": 2930231,
                "ma10": 237550.0,
                "ma20": 224425.0,
                "ma60": 200025.0,
                "ma306": 104184.64,
            },
            {
                "cntr_tm": "20260508150000",
                "ts": pd.Timestamp("2026-05-08 15:00:00"),
                "date": "20260508",
                "open_pric": 269000,
                "high_pric": 270000,
                "low_pric": 268500,
                "cur_prc": 268500,
                "trde_qty": 3176392,
                "ma10": 237550.0,
                "ma20": 224425.0,
                "ma60": 200025.0,
                "ma306": 104184.64,
            },
        ]
    )


def test_render_markdown_contains_expected_sections() -> None:
    md = render_markdown(
        _make_df(),
        stk_cd="005930",
        stk_name="삼성전자",
        fetched_at="2026-05-09 21:01:07",
    )
    assert "# 삼성전자(005930)" in md
    assert "## 기본 정보" in md
    assert "## 최근 봉 스냅샷" in md
    assert "## 60분봉 시계열" in md
    # 가격 천단위 콤마 + 부호 제거 검증.
    assert "268,500" in md
    # MA306 소수점 2자리.
    assert "104,184.64" in md
    # 시각 표기 변환.
    assert "2026-05-08 15:00" in md


def test_render_markdown_handles_empty_df() -> None:
    md = render_markdown(pd.DataFrame(), stk_cd="005930", stk_name="삼성전자")
    assert "# 삼성전자(005930)" in md
    assert "응답 데이터 없음" in md


def test_save_uses_execution_date_for_directory(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 21, 1, 7)
    out = save_chart60_markdown(
        df,
        stk_cd="005930",
        stk_name="삼성전자",
        output_root=tmp_path,
        now=fixed_now,
    )
    # 디렉터리: <output_root>/<실행일>/<종목명(종목코드)>/chart60.md
    assert out == tmp_path / "20260509" / "삼성전자(005930)" / "chart60.md"
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "삼성전자" in body
    assert "2026-05-09 21:01:07" in body


def test_save_uses_stk_cd_only_when_no_name(tmp_path: Path) -> None:
    """stk_name 미지정 시 디렉터리 leaf 는 stk_cd 단독."""
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 21, 1, 7)
    out = save_chart60_markdown(
        df, stk_cd="005930", output_root=tmp_path, now=fixed_now,
    )
    assert out == tmp_path / "20260509" / "005930" / "chart60.md"


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    df = _make_df()
    nested = tmp_path / "a" / "b" / "c"
    fixed_now = datetime(2026, 1, 2, 10, 0, 0)
    out = save_chart60_markdown(
        df,
        stk_cd="005930",
        stk_name="삼성전자",
        output_root=nested,
        now=fixed_now,
    )
    assert out == nested / "20260102" / "삼성전자(005930)" / "chart60.md"
    assert out.exists()


def test_save_overwrites_same_day_file(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 9, 0, 0)
    p1 = save_chart60_markdown(
        df, stk_cd="005930", stk_name="삼성전자",
        output_root=tmp_path, now=fixed_now,
    )
    first = p1.read_text(encoding="utf-8")

    later_now = datetime(2026, 5, 9, 15, 30, 0)
    p2 = save_chart60_markdown(
        df, stk_cd="005930", stk_name="삼성전자",
        output_root=tmp_path, now=later_now,
    )
    assert p1 == p2
    second = p2.read_text(encoding="utf-8")
    assert "09:00:00" in first
    assert "15:30:00" in second
    files = list((tmp_path / "20260509" / "삼성전자(005930)").iterdir())
    assert len(files) == 1
