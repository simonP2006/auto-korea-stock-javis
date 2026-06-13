"""src.kiwoom.investor.investor — 단일 파일 모듈 통합 테스트.

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

from src.kiwoom._exchange import normalize_stk_cd as _normalize_stk_cd
from src.kiwoom.investor.investor import (
    InvestorFlowClient,
    InvestorFlowRecord,
    KiwoomApiError,
    get_investor_flow,
    render_markdown,
    save_investor_markdown,
)


# ─────────────────────────────────────────────────────────────────────────────
# 모델 검증
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+1584", 1584),
        ("-61779", -61779),
        ("60195", 60195),
        ("0", 0),
        ("", 0),
        (None, 0),
        ("  +12345  ", 12345),
    ],
)
def test_record_keeps_sign_for_investor_fields(raw: object, expected: int) -> None:
    """순매수금액은 부호 자체가 의미를 가지므로 부호 보존."""
    r = InvestorFlowRecord.model_validate({"dt": "20241107", "frgnr_invsr": raw})
    assert r.frgnr_invsr == expected


def test_record_full_payload_from_pdf_example() -> None:
    """PDF p.157 ka10059 응답 예시 한 행 그대로 파싱."""
    r = InvestorFlowRecord.model_validate(
        {
            "dt": "20241107",
            "cur_prc": "+61300",
            "pre_sig": "2",
            "pred_pre": "+4000",
            "flu_rt": "+698",
            "acc_trde_qty": "1105968",
            "acc_trde_prica": "64215",
            "ind_invsr": "1584",
            "frgnr_invsr": "-61779",
            "orgn": "60195",
            "fnnc_invt": "25514",
            "insrnc": "0",
            "invtrt": "0",
            "etc_fnnc": "34619",
            "bank": "4",
            "penfnd_etc": "-1",
            "samo_fund": "58",
            "natn": "0",
            "etc_corp": "0",
            "natfor": "1",
        }
    )
    assert r.dt == "20241107"
    assert r.ind_invsr == 1584
    assert r.frgnr_invsr == -61779
    assert r.orgn == 60195


def test_record_ignores_extra_fields() -> None:
    """기관 세분류·시세 필드는 ``extra='ignore'`` 로 자동 폐기."""
    r = InvestorFlowRecord.model_validate(
        {
            "dt": "20241107",
            "ind_invsr": "100",
            "frgnr_invsr": "-200",
            "orgn": "300",
            "fnnc_invt": "999",
            "cur_prc": "+50000",
        }
    )
    assert not hasattr(r, "fnnc_invt")
    assert not hasattr(r, "cur_prc")


def test_kiwoom_api_error_message() -> None:
    err = KiwoomApiError(code=1700, msg="허용된 요청 개수 초과")
    assert err.code == 1700
    assert err.api_id == "ka10059"
    assert "ka10059" in str(err)


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


def _make_client(handler) -> tuple[InvestorFlowClient, _FakeAuth]:
    transport = httpx.MockTransport(handler)
    auth = _FakeAuth()
    client = InvestorFlowClient(
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
            json={"return_code": 0, "stk_invsr_orgn": []},
        )

    client, _ = _make_client(handler)
    await client.post(
        {
            "dt": "20260509",
            "stk_cd": "005930",
            "amt_qty_tp": "1",
            "trde_tp": "0",
            "unit_tp": "1000",
        }
    )
    assert captured["url"].endswith("/api/dostk/stkinfo")
    assert captured["api_id"] == "ka10059"
    assert captured["body"]["amt_qty_tp"] == "1"
    assert captured["body"]["trde_tp"] == "0"
    assert captured["body"]["unit_tp"] == "1000"


@pytest.mark.asyncio
async def test_fetch_records_default_uses_sor_integrated() -> None:
    """fetch_records 기본값은 SOR(통합) — HTS [0995] 통합 탭과 일치."""
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200,
            headers={"cont-yn": "N"},
            json={
                "return_code": 0,
                "stk_invsr_orgn": [{"dt": "20260509", "frgnr_invsr": "0"}],
            },
        )

    client, _ = _make_client(handler)
    await client.fetch_records("005930", base_dt="20260509", min_rows=1)
    assert captured[0] == {
        "dt": "20260509",
        "stk_cd": "005930_AL",
        "amt_qty_tp": "1",
        "trde_tp": "0",
        "unit_tp": "1000",
    }


@pytest.mark.asyncio
async def test_fetch_records_explicit_krx() -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200, headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_invsr_orgn": [{"dt": "20260509"}]},
        )

    client, _ = _make_client(handler)
    await client.fetch_records(
        "005930", base_dt="20260509", min_rows=1, exchange="krx",
    )
    assert captured[0]["stk_cd"] == "005930"


@pytest.mark.asyncio
async def test_fetch_records_explicit_nxt() -> None:
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200, headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_invsr_orgn": [{"dt": "20260509"}]},
        )

    client, _ = _make_client(handler)
    await client.fetch_records(
        "005930", base_dt="20260509", min_rows=1, exchange="nxt",
    )
    assert captured[0]["stk_cd"] == "005930_NX"


@pytest.mark.asyncio
async def test_fetch_records_explicit_suffix_overrides_exchange() -> None:
    """이미 접미사가 붙은 stk_cd 는 exchange 인자보다 우선."""
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content))
        return httpx.Response(
            200, headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_invsr_orgn": [{"dt": "20260509"}]},
        )

    client, _ = _make_client(handler)
    # exchange="krx" 지정해도 stk_cd 의 _NX 가 우선해야 함.
    await client.fetch_records(
        "005930_NX", base_dt="20260509", min_rows=1, exchange="krx",
    )
    assert captured[0]["stk_cd"] == "005930_NX"


def test_normalize_stk_cd_appends_al_for_sor_default() -> None:
    code, label = _normalize_stk_cd("005930", "sor")
    assert code == "005930_AL"
    assert label == "SOR(통합)"


def test_normalize_stk_cd_keeps_plain_for_krx() -> None:
    code, label = _normalize_stk_cd("005930", "krx")
    assert code == "005930"
    assert label == "KRX"


def test_normalize_stk_cd_appends_nx_for_nxt() -> None:
    code, label = _normalize_stk_cd("005930", "nxt")
    assert code == "005930_NX"
    assert label == "NXT"


def test_normalize_stk_cd_explicit_suffix_takes_precedence() -> None:
    code, label = _normalize_stk_cd("005930_AL", "krx")
    assert code == "005930_AL"
    assert label == "SOR(통합)"


def test_normalize_stk_cd_rejects_unknown_exchange() -> None:
    with pytest.raises(ValueError):
        _normalize_stk_cd("005930", "unknown")


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
                    "stk_invsr_orgn": [
                        {"dt": "20260508", "frgnr_invsr": "100"},
                        {"dt": "20260507", "frgnr_invsr": "200"},
                    ],
                },
            )
        return httpx.Response(
            200,
            headers={"cont-yn": "N", "next-key": ""},
            json={
                "return_code": 0,
                "stk_invsr_orgn": [{"dt": "20260506", "frgnr_invsr": "300"}],
            },
        )

    client, _ = _make_client(handler)
    rows = await client.fetch_records("005930", base_dt="20260509", min_rows=999)
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
                "stk_invsr_orgn": [
                    {"dt": f"2026050{page['n']}", "frgnr_invsr": "1"},
                ],
            },
        )

    client, _ = _make_client(handler)
    rows = await client.fetch_records("005930", base_dt="20260509", min_rows=3)
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
    assert exc.value.api_id == "ka10059"


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
            json={"return_code": 0, "stk_invsr_orgn": []},
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
            json={"return_code": 0, "stk_invsr_orgn": []},
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
        self, stk_cd, *, base_dt, min_rows, exchange="sor", stop_when=None,
    ):
        self.calls.append(
            {
                "stk_cd": stk_cd,
                "base_dt": base_dt,
                "min_rows": min_rows,
                "exchange": exchange,
            }
        )
        return self.raw


def _make_descending_raw(n: int) -> list[dict]:
    """API 는 최신→과거 순서로 반환 (실서버 동작과 동일)."""
    raw: list[dict] = []
    for i in range(n):
        if i < 8:
            dt = f"2026050{8 - i}"
        else:
            dt = f"202604{30 - (i - 8):02d}"
        raw.append(
            {
                "dt": dt,
                "ind_invsr": str(i),
                "frgnr_invsr": str(-i),
                "orgn": str(i * 2),
            }
        )
    return raw


@pytest.mark.asyncio
async def test_facade_returns_exact_n_bars_in_ascending_order() -> None:
    fake = _FakeFetchClient(_make_descending_raw(20))
    df = await get_investor_flow(
        "005930", bars=16, base_dt="20260509", client=fake,
    )

    assert len(df) == 16
    # 시간 오름차순 검증.
    assert list(df["dt"]) == sorted(df["dt"])
    # 마지막이 최신.
    assert df["dt"].iloc[-1] == "20260508"
    # min_rows = bars + 마진(4) = 20.
    assert fake.calls[0]["min_rows"] == 20
    assert fake.calls[0]["base_dt"] == "20260509"


@pytest.mark.asyncio
async def test_facade_returns_empty_when_no_data() -> None:
    fake = _FakeFetchClient([])
    df = await get_investor_flow(
        "005930", bars=16, base_dt="20260509", client=fake,
    )
    assert df.empty


@pytest.mark.asyncio
async def test_facade_default_bars_16() -> None:
    fake = _FakeFetchClient(_make_descending_raw(20))
    df = await get_investor_flow("005930", base_dt="20260509", client=fake)
    assert len(df) == 16


@pytest.mark.asyncio
async def test_facade_uses_today_when_base_dt_omitted() -> None:
    fake = _FakeFetchClient(_make_descending_raw(20))
    await get_investor_flow("005930", client=fake)
    today = datetime.now().strftime("%Y%m%d")
    assert fake.calls[0]["base_dt"] == today


@pytest.mark.asyncio
async def test_facade_default_exchange_is_sor() -> None:
    fake = _FakeFetchClient(_make_descending_raw(20))
    df = await get_investor_flow("005930", client=fake)
    assert fake.calls[0]["exchange"] == "sor"
    assert df.attrs["exchange_label"] == "SOR(통합)"
    assert df.attrs["api_stk_cd"] == "005930_AL"


@pytest.mark.asyncio
async def test_facade_exchange_krx_keeps_plain_code() -> None:
    fake = _FakeFetchClient(_make_descending_raw(20))
    df = await get_investor_flow("005930", exchange="krx", client=fake)
    assert df.attrs["exchange_label"] == "KRX"
    assert df.attrs["api_stk_cd"] == "005930"


@pytest.mark.asyncio
async def test_facade_preserves_signs_through_pipeline() -> None:
    raw = [
        {"dt": "20260509", "ind_invsr": "+1584", "frgnr_invsr": "-61779", "orgn": "+60195"},
        {"dt": "20260508", "ind_invsr": "-639", "frgnr_invsr": "-7", "orgn": "+646"},
    ]
    fake = _FakeFetchClient(raw)
    df = await get_investor_flow(
        "005930", bars=16, base_dt="20260509", client=fake,
    )
    last = df.iloc[-1]
    assert last["ind_invsr"] == 1584
    assert last["frgnr_invsr"] == -61779
    assert last["orgn"] == 60195


# ─────────────────────────────────────────────────────────────────────────────
# 리포터
# ─────────────────────────────────────────────────────────────────────────────


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dt": "20260508",
                "ind_invsr": -639,
                "frgnr_invsr": -7,
                "orgn": 646,
            },
            {
                "dt": "20260509",
                "ind_invsr": 1584,
                "frgnr_invsr": -61779,
                "orgn": 60195,
            },
        ]
    )


def test_render_markdown_contains_expected_sections() -> None:
    df = _make_df()
    df.attrs["exchange_label"] = "SOR(통합)"
    df.attrs["api_stk_cd"] = "005930_AL"
    md = render_markdown(
        df,
        stk_cd="005930",
        stk_name="삼성전자",
        fetched_at="2026-05-09 22:00:00",
    )
    assert "# 삼성전자(005930) 투자자·기관 순매수금액 추이" in md
    assert "## 기본 정보" in md
    assert "## 최근 거래일 스냅샷" in md
    assert "## 일별 순매수금액 추이" in md
    assert "ka10059" in md
    assert "amt_qty_tp=1" in md
    assert "trde_tp=0" in md
    assert "unit_tp=1000" in md
    assert "SOR(통합)" in md
    assert "005930_AL" in md
    assert "+1,584" in md
    assert "-61,779" in md
    assert "+60,195" in md
    assert "2026-05-09" in md  # YYYYMMDD → YYYY-MM-DD


def test_render_markdown_shows_krx_when_specified() -> None:
    df = _make_df()
    df.attrs["exchange_label"] = "KRX"
    df.attrs["api_stk_cd"] = "005930"
    md = render_markdown(df, stk_cd="005930", stk_name="삼성전자")
    assert "거래소**: KRX" in md
    assert "SOR(통합)" not in md


def test_render_markdown_table_has_only_4_columns() -> None:
    """표 헤더가 ``날짜·개인·외국인·기관계`` 4컬럼으로 고정."""
    md = render_markdown(
        _make_df(), stk_cd="005930", stk_name="삼성전자",
    )
    assert "| 날짜 | 개인 | 외국인 | 기관계 |" in md
    assert "| 종가" not in md
    assert "| 대비" not in md
    assert "| 등락" not in md


def test_render_markdown_handles_empty_df() -> None:
    md = render_markdown(pd.DataFrame(), stk_cd="005930", stk_name="삼성전자")
    assert "# 삼성전자(005930) 투자자·기관 순매수금액 추이" in md
    assert "응답 데이터 없음" in md


def test_save_uses_execution_date_for_directory(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 22, 0, 0)
    out = save_investor_markdown(
        df, stk_cd="005930", stk_name="삼성전자",
        output_root=tmp_path, now=fixed_now,
    )
    # <output_root>/<실행일>/<종목명(종목코드)>/investor.md
    assert out == tmp_path / "20260509" / "삼성전자(005930)" / "investor.md"
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "삼성전자" in body
    assert "2026-05-09 22:00:00" in body


def test_save_uses_stk_cd_only_when_no_name(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 22, 0, 0)
    out = save_investor_markdown(
        df, stk_cd="005930", output_root=tmp_path, now=fixed_now,
    )
    assert out == tmp_path / "20260509" / "005930" / "investor.md"


def test_save_filename_is_investor_md(tmp_path: Path) -> None:
    """foreigner.md / chart60.md / chartDay.md 와 한 종목 디렉터리에 공존 가능."""
    df = _make_df()
    fixed_now = datetime(2026, 5, 9, 9, 0, 0)
    out = save_investor_markdown(
        df, stk_cd="005930", stk_name="삼성전자",
        output_root=tmp_path, now=fixed_now,
    )
    assert out.name == "investor.md"
