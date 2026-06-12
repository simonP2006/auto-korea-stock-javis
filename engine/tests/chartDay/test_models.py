"""chartDay DailyCandle 부호 제거·결측 정규화 검증."""

from __future__ import annotations

import pytest

from src.kiwoom.chartDay.getData.models import DailyCandle, KiwoomApiError


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+78800", 78800),
        ("-78800", 78800),
        ("78800", 78800),
        ("", 0),
        (None, 0),
        (0, 0),
        ("  +69500  ", 69500),
        ("1.5", 1),
    ],
)
def test_daily_candle_strips_sign(raw: object, expected: int) -> None:
    c = DailyCandle.model_validate({"dt": "20250908", "cur_prc": raw})
    assert c.cur_prc == expected


def test_daily_candle_full_payload_from_pdf_example() -> None:
    c = DailyCandle.model_validate(
        {
            "cur_prc": "70100",
            "trde_qty": "9263135",
            "trde_prica": "648525",
            "dt": "20250908",
            "open_pric": "69800",
            "high_pric": "70500",
            "low_pric": "69600",
            "pred_pre": "+600",
            "pred_pre_sig": "2",
            "trde_tern_rt": "+0.16",
        }
    )
    assert c.dt == "20250908"
    assert c.cur_prc == 70100
    assert c.high_pric == 70500
    assert c.trde_qty == 9263135


def test_kiwoom_api_error_message_includes_context() -> None:
    err = KiwoomApiError(code=1700, msg="허용된 요청 개수 초과", api_id="ka10081")
    assert err.code == 1700
    assert err.api_id == "ka10081"
    assert "1700" in str(err)
    assert "ka10081" in str(err)
