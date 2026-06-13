"""DailyCandle / MinuteCandle 의 부호 제거·결측 정규화 검증."""

from __future__ import annotations

import pytest

from src.kiwoom.chart60.getData.models import (
    DailyCandle,
    KiwoomApiError,
    MinuteCandle,
)


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
        ("1.5", 1),  # 소수점 폴백
    ],
)
def test_daily_candle_strips_sign(raw: object, expected: int) -> None:
    c = DailyCandle.model_validate({"dt": "20250908", "cur_prc": raw})
    assert c.cur_prc == expected


def test_daily_candle_full_payload_from_pdf_example() -> None:
    # PDF p.202 ka10081 응답 예시의 한 행.
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


def test_minute_candle_full_payload_from_pdf_example() -> None:
    # PDF p.200 ka10080 응답 예시의 한 행 (음수 부호 표기 포함).
    c = MinuteCandle.model_validate(
        {
            "cur_prc": "-78800",
            "trde_qty": "7913",
            "cntr_tm": "20250917132000",
            "open_pric": "-78850",
            "high_pric": "-78900",
            "low_pric": "-78800",
            "acc_trde_qty": "14947571",
            "pred_pre": "-600",
            "pred_pre_sig": "5",
        }
    )
    assert c.cntr_tm == "20250917132000"
    assert c.cur_prc == 78800
    assert c.open_pric == 78850
    assert c.high_pric == 78900
    assert c.low_pric == 78800
    assert c.trde_qty == 7913


def test_kiwoom_api_error_message_includes_context() -> None:
    err = KiwoomApiError(code=1700, msg="허용된 요청 개수 초과", api_id="ka10080")
    assert err.code == 1700
    assert err.api_id == "ka10080"
    assert "1700" in str(err)
    assert "ka10080" in str(err)
