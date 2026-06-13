"""src.kiwoom.etc.foreigner — 단일 파일 모듈 통합 테스트.

모델·클라이언트·파사드·리포터를 한 파일로 검증한다. 실제 네트워크는
:class:`httpx.MockTransport` 와 가짜 토큰 제공자로 격리한다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
import pytest

from src.kiwoom.etc.foreigner import (
    ForeignHoldingClient,
    ForeignHoldingRecord,
    KiwoomApiError,
    get_foreign_holding,
    render_markdown,
    save_foreigner_markdown,
)


# ─────────────────────────────────────────────────────────────────────────────
# 모델 검증
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+135300", 135300),
        ("-65000", 65000),
        ("135300", 135300),
        ("", 0),
        (None, 0),
        ("  +6663509  ", 6663509),
    ],
)
def test_record_strips_sign_for_absolute_fields(raw: object, expected: int) -> None:
    r = ForeignHoldingRecord.model_validate({"dt": "20241105", "close_pric": raw})
    assert r.close_pric == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+1000", 1000),
        ("-3441", -3441),
        ("0", 0),
        ("", 0),
        (None, 0),
        ("4627", 4627),
    ],
)
def test_record_keeps_sign_for_signed_fields(raw: object, expected: int) -> None:
    r = ForeignHoldingRecord.model_validate({"dt": "20241105", "chg_qty": raw})
    assert r.chg_qty == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+26.10", 26.10),
        ("-22.31", 22.31),
        ("0.00", 0.0),
        ("", 0.0),
        (None, 0.0),
    ],
)
def test_record_parses_percent_fields_as_float(raw: object, expected: float) -> None:
    r = ForeignHoldingRecord.model_validate({"dt": "20241105", "wght": raw})
    assert r.wght == pytest.approx(expected)


def test_record_full_payload_from_pdf_example() -> None:
    """PDF p.40 ka10008 예시 한 행 그대로 파싱."""
    r = ForeignHoldingRecord.model_validate(
        {
            "dt": "20241105",
            "close_pric": "135300",
            "pred_pre": "0",
            "trde_qty": "0",
            "chg_qty": "0",
            "poss_stkcnt": "6663509",
            "wght": "+26.10",
            "gain_pos_stkcnt": "18863197",
            "frgnr_limit": "25526706",
            "frgnr_limit_irds": "0",
            "limit_exh_rt": "+26.10",
        }
    )
    assert r.dt == "20241105"
    assert r.poss_stkcnt == 6663509
    assert r.wght == pytest.approx(26.10)
    assert r.frgnr_limit == 25526706
    assert r.limit_exh_rt == pytest.approx(26.10)


def test_kiwoom_api_error_message() -> None:
    err = KiwoomApiError(code=1700, msg="허용된 요청 개수 초과")
    assert err.code == 1700
    assert err.api_id == "ka10008"
    assert "ka10008" in str(err)


# ─────────────────────────────────────────────────────────────────────────────
# 클라이언트 (페이징 / 오류 자동처리)
# ─────────────────────────────────────────────────────────────────────────────


class _FakeAuth:
    def __init__(self) -> None:
        self.invalidated = 0
        self.fetch_count = 0

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        self.fetch_count += 1
        return f"token-{self.fetch_count}"

    def invalidate(self) -> None:
        self.invalidated += 1


class _FakeConfig:
    base_url = "https://mockapi.kiwoom.com"


def _make_client(handler) -> tuple[ForeignHoldingClient, _FakeAuth]:
    transport = httpx.MockTransport(handler)
    auth = _FakeAuth()
    client = ForeignHoldingClient(
        auth=auth, config=_FakeConfig(), transport=transport,
    )
    return client, auth


@pytest.mark.asyncio
async def test_client_uses_correct_path_and_api_id() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_id"] = request.headers.get("api-id")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_frgnr": []},
        )

    client, _ = _make_client(handler)
    await client.post({"stk_cd": "005930"})
    assert captured["url"].endswith("/api/dostk/frgnistt")
    assert captured["api_id"] == "ka10008"
    assert captured["body"] == {"stk_cd": "005930"}


@pytest.mark.asyncio
async def test_fetch_records_default_uses_sor_integrated() -> None:
    """fetch_records 기본 호출 시 stk_cd 에 _AL (SOR 통합) 자동 부여."""
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200, headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_frgnr": [{"dt": "20260509"}]},
        )

    client, _ = _make_client(handler)
    await client.fetch_records("005930", min_rows=1)
    assert captured[0]["stk_cd"] == "005930_AL"


@pytest.mark.asyncio
async def test_fetch_records_explicit_krx_keeps_plain() -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200, headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_frgnr": [{"dt": "20260509"}]},
        )

    client, _ = _make_client(handler)
    await client.fetch_records("005930", min_rows=1, exchange="krx")
    assert captured[0]["stk_cd"] == "005930"


@pytest.mark.asyncio
async def test_fetch_records_follows_cont_yn_paging() -> None:
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(
            {
                "cont_yn": request.headers.get("cont-yn"),
                "next_key": request.headers.get("next-key"),
            }
        )
        if request.headers.get("cont-yn") != "Y":
            return httpx.Response(
                200,
                headers={"cont-yn": "Y", "next-key": "KEY2"},
                json={
                    "return_code": 0,
                    "stk_frgnr": [
                        {"dt": "20260508", "poss_stkcnt": "1000"},
                        {"dt": "20260507", "poss_stkcnt": "999"},
                    ],
                },
            )
        return httpx.Response(
            200,
            headers={"cont-yn": "N", "next-key": ""},
            json={
                "return_code": 0,
                "stk_frgnr": [{"dt": "20260506", "poss_stkcnt": "998"}],
            },
        )

    client, _ = _make_client(handler)
    rows = await client.fetch_records("005930", min_rows=999)
    assert len(rows) == 3
    assert calls[0]["cont_yn"] is None
    assert calls[1]["cont_yn"] == "Y"
    assert calls[1]["next_key"] == "KEY2"


@pytest.mark.asyncio
async def test_fetch_records_stops_when_min_rows_reached() -> None:
    page = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page["n"] += 1
        return httpx.Response(
            200,
            headers={"cont-yn": "Y", "next-key": f"K{page['n']}"},
            json={
                "return_code": 0,
                "stk_frgnr": [
                    {"dt": f"2026050{page['n']}", "poss_stkcnt": "100"},
                ],
            },
        )

    client, _ = _make_client(handler)
    rows = await client.fetch_records("005930", min_rows=3)
    assert len(rows) == 3
    assert page["n"] == 3


@pytest.mark.asyncio
async def test_client_raises_on_business_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"return_code": 1902, "return_msg": "종목 정보가 없습니다"},
        )

    client, _ = _make_client(handler)
    with pytest.raises(KiwoomApiError) as exc:
        await client.post({"stk_cd": "INVALID"})
    assert exc.value.code == 1902
    assert exc.value.api_id == "ka10008"


@pytest.mark.asyncio
async def test_client_retries_on_rate_limit() -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(
                200,
                json={"return_code": 1700, "return_msg": "허용된 요청 개수 초과"},
            )
        return httpx.Response(
            200, headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_frgnr": []},
        )

    client, _ = _make_client(handler)
    data, _, _ = await client.post({"stk_cd": "005930"})
    assert state["calls"] == 2
    assert data["return_code"] == 0


@pytest.mark.asyncio
async def test_client_invalidates_token_on_8005() -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(
                200,
                json={"return_code": 8005, "return_msg": "Token이 유효하지 않습니다"},
            )
        return httpx.Response(
            200, headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_frgnr": []},
        )

    client, auth = _make_client(handler)
    await client.post({"stk_cd": "005930"})
    assert state["calls"] == 2
    assert auth.invalidated == 1


# ─────────────────────────────────────────────────────────────────────────────
# 파사드
# ─────────────────────────────────────────────────────────────────────────────


class _FakeFetchClient:
    """``fetch_records`` 만 호출되는 가짜 클라이언트."""

    def __init__(self, raw: list[dict]) -> None:
        self.raw = raw
        self.calls: list[dict] = []

    async def fetch_records(
        self, stk_cd, *, min_rows, exchange="sor", stop_when=None,
    ):
        self.calls.append(
            {"stk_cd": stk_cd, "min_rows": min_rows, "exchange": exchange}
        )
        return self.raw


@pytest.mark.asyncio
async def test_facade_returns_exact_n_bars_in_ascending_order() -> None:
    # API 는 최신→과거 순서로 반환 (실서버 동작과 동일).
    raw = [
        {"dt": f"2026050{8 - i}" if i < 8 else f"202604{30 - (i - 8):02d}", "poss_stkcnt": str(1000 - i)}
        for i in range(20)
    ]
    fake = _FakeFetchClient(raw)
    df = await get_foreign_holding("005930", bars=16, client=fake)

    assert len(df) == 16
    # 시간 오름차순 검증.
    assert list(df["dt"]) == sorted(df["dt"])
    # 마지막이 최신.
    assert df["dt"].iloc[-1] == "20260508"
    # min_rows = bars + 마진(4) = 20.
    assert fake.calls[0]["min_rows"] == 20


@pytest.mark.asyncio
async def test_facade_returns_empty_when_no_data() -> None:
    fake = _FakeFetchClient([])
    df = await get_foreign_holding("005930", bars=16, client=fake)
    assert df.empty


@pytest.mark.asyncio
async def test_facade_default_bars_16() -> None:
    raw = [{"dt": f"2026050{8 - i}" if i < 8 else f"202604{30 - (i - 8):02d}", "poss_stkcnt": "1"} for i in range(20)]
    fake = _FakeFetchClient(raw)
    df = await get_foreign_holding("005930", client=fake)
    assert len(df) == 16


@pytest.mark.asyncio
async def test_facade_default_exchange_is_sor() -> None:
    raw = [{"dt": f"2026050{8 - i}" if i < 8 else f"202604{30 - (i - 8):02d}", "poss_stkcnt": "1"} for i in range(20)]
    fake = _FakeFetchClient(raw)
    df = await get_foreign_holding("005930", client=fake)
    assert fake.calls[0]["exchange"] == "sor"
    assert df.attrs["exchange_label"] == "SOR(통합)"
    assert df.attrs["api_stk_cd"] == "005930_AL"


@pytest.mark.asyncio
async def test_facade_explicit_krx_exchange() -> None:
    raw = [{"dt": f"2026050{8 - i}" if i < 8 else f"202604{30 - (i - 8):02d}", "poss_stkcnt": "1"} for i in range(20)]
    fake = _FakeFetchClient(raw)
    df = await get_foreign_holding("005930", exchange="krx", client=fake)
    assert fake.calls[0]["exchange"] == "krx"
    assert df.attrs["exchange_label"] == "KRX"
    assert df.attrs["api_stk_cd"] == "005930"


# ─────────────────────────────────────────────────────────────────────────────
# 리포터
# ─────────────────────────────────────────────────────────────────────────────


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dt": "20260507",
                "close_pric": 271500,
                "trde_qty": 33651546,
                "chg_qty": -150000,
                "poss_stkcnt": 2888080689,
                "wght": 48.30,
                "gain_pos_stkcnt": 0,
                "frgnr_limit": 5969782550,
                "frgnr_limit_irds": 0,
                "limit_exh_rt": 48.30,
            },
            {
                "dt": "20260508",
                "close_pric": 268500,
                "trde_qty": 27875253,
                "chg_qty": 200000,
                "poss_stkcnt": 2876884902,
                "wght": 48.20,
                "gain_pos_stkcnt": 0,
                "frgnr_limit": 5969782550,
                "frgnr_limit_irds": 0,
                "limit_exh_rt": 48.20,
            },
        ]
    )


def test_render_markdown_contains_expected_sections() -> None:
    md = render_markdown(
        _make_df(),
        stk_cd="005930",
        stk_name="삼성전자",
        fetched_at="2026-05-09 22:00:00",
    )
    assert "# 삼성전자(005930) 외국인 보유 동향" in md
    assert "## 기본 정보" in md
    assert "## 최근 거래일 스냅샷" in md
    assert "## 일별 외국인 보유 내역" in md
    assert "ka10008" in md
    assert "2,876,884,902" in md  # 천단위 콤마
    assert "48.20" in md  # 비중 소수점 2자리
    assert "+200,000" in md  # 부호 보존된 chg_qty
    assert "-150,000" in md
    assert "2026-05-08" in md  # YYYYMMDD → YYYY-MM-DD


def test_render_markdown_handles_empty_df() -> None:
    md = render_markdown(pd.DataFrame(), stk_cd="005930", stk_name="삼성전자")
    assert "# 삼성전자(005930) 외국인 보유 동향" in md
    assert "응답 데이터 없음" in md


def test_save_uses_execution_date_for_directory(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 22, 0, 0)
    out = save_foreigner_markdown(
        df, stk_cd="005930", stk_name="삼성전자",
        output_root=tmp_path, now=fixed_now,
    )
    # <output_root>/<실행일>/<종목명(종목코드)>/foreigner.md
    assert out == tmp_path / "20260509" / "삼성전자(005930)" / "foreigner.md"
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "삼성전자" in body
    assert "2026-05-09 22:00:00" in body


def test_save_uses_stk_cd_only_when_no_name(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 22, 0, 0)
    out = save_foreigner_markdown(
        df, stk_cd="005930", output_root=tmp_path, now=fixed_now,
    )
    assert out == tmp_path / "20260509" / "005930" / "foreigner.md"


def test_save_filename_is_foreigner_md(tmp_path: Path) -> None:
    """chart60.md / chartDay.md 와 한 종목 디렉터리에 공존 가능."""
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 9, 0, 0)
    out = save_foreigner_markdown(
        df, stk_cd="005930", stk_name="삼성전자",
        output_root=tmp_path, now=fixed_now,
    )
    assert out.name == "foreigner.md"
