"""src.kiwoom.upperLowerPrice.upperLowerPrice — 단일 파일 모듈 통합 테스트.

모델·필터·클라이언트·파사드·리포터를 한 파일로 검증한다. 실제 네트워크는
:class:`httpx.MockTransport` 와 가짜 토큰 제공자로 격리한다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
import pytest

from src.kiwoom.upperLowerPrice.upperLowerPrice import (
    KiwoomApiError,
    UpperLowerPriceClient,
    UpperLowerPriceFilters,
    UpperLowerPriceRow,
    filter_out_etf_etn_spac,
    get_upper_lower_price,
    is_etf,
    is_etn,
    is_spac,
    render_markdown,
    save_upper_lower_price_markdown,
)


# ─────────────────────────────────────────────────────────────────────────────
# 모델 — 값 변환 규칙
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+235500", 235500),
        ("-10060", 10060),
        ("13715", 13715),
        ("", 0),
        (None, 0),
        ("  +4970  ", 4970),
    ],
)
def test_row_strips_sign_for_price_fields(raw: object, expected: int) -> None:
    """cur_prc/sel_bid/buy_bid 는 ``+``/``-`` prefix 가 indicator 이므로 절댓값."""
    r = UpperLowerPriceRow.model_validate({"stk_cd": "005930", "cur_prc": raw})
    assert r.cur_prc == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+54200", 54200),
        ("-1790", -1790),
        ("0", 0),
        ("", 0),
        (None, 0),
    ],
)
def test_row_keeps_sign_for_pred_pre(raw: object, expected: int) -> None:
    """전일대비는 부호 보존 — 등락 방향이 의미."""
    r = UpperLowerPriceRow.model_validate({"stk_cd": "005930", "pred_pre": raw})
    assert r.pred_pre == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+29.90", 29.90),
        ("-15.11", -15.11),
        ("+30.00", 30.00),
        ("0.00", 0.0),
        ("", 0.0),
        (None, 0.0),
    ],
)
def test_row_keeps_sign_for_flu_rt(raw: object, expected: float) -> None:
    """등락률은 부호 보존 — 가격 변화 방향이 의미."""
    r = UpperLowerPriceRow.model_validate({"stk_cd": "005930", "flu_rt": raw})
    assert r.flu_rt == pytest.approx(expected)


def test_row_full_payload_from_pdf_example() -> None:
    """PDF p.62 ka10017 응답 예시 한 행 그대로 파싱."""
    r = UpperLowerPriceRow.model_validate(
        {
            "stk_cd": "005930",
            "stk_infr": "",
            "stk_nm": "삼성전자",
            "cur_prc": "+235500",
            "pred_pre_sig": "1",
            "pred_pre": "+54200",
            "flu_rt": "+29.90",
            "trde_qty": "0",
            "pred_trde_qty": "96197",
            "sel_req": "0",
            "sel_bid": "0",
            "buy_bid": "+235500",
            "buy_req": "4",
            "cnt": "1",
        }
    )
    assert r.stk_cd == "005930"
    assert r.stk_nm == "삼성전자"
    assert r.cur_prc == 235500
    assert r.pred_pre == 54200
    assert r.flu_rt == pytest.approx(29.90)
    assert r.pred_trde_qty == 96197
    assert r.buy_bid == 235500
    assert r.cnt == 1


def test_row_ignores_extra_fields() -> None:
    """API 가 미래에 새 필드를 추가해도 모델 검증은 깨지지 않는다."""
    r = UpperLowerPriceRow.model_validate(
        {"stk_cd": "005930", "future_field": "anything"},
    )
    assert r.stk_cd == "005930"


def test_kiwoom_api_error_uses_ka10017_id() -> None:
    err = KiwoomApiError(code=1700, msg="허용된 요청 개수 초과")
    assert err.code == 1700
    assert err.api_id == "ka10017"
    assert "ka10017" in str(err)


# ─────────────────────────────────────────────────────────────────────────────
# 필터
# ─────────────────────────────────────────────────────────────────────────────


def test_filters_default_matches_hts_screen() -> None:
    """기본값은 사용자 HTS [0162] 화면 그대로 (전체/상승/등락률순/...)."""
    body = UpperLowerPriceFilters().to_body()
    assert body == {
        "mrkt_tp": "000",
        "updown_tp": "2",
        "sort_tp": "3",
        "stk_cnd": "2",
        "trde_qty_tp": "00010",
        "crd_cnd": "0",
        "trde_gold_tp": "8",
        "stex_tp": "3",
    }


def test_filters_override_specific_fields() -> None:
    body = UpperLowerPriceFilters(updown_tp="1", mrkt_tp="101").to_body()
    assert body["updown_tp"] == "1"
    assert body["mrkt_tp"] == "101"
    # 나머지 기본값 유지
    assert body["sort_tp"] == "3"


def test_filters_reject_invalid_literal() -> None:
    with pytest.raises(Exception):
        UpperLowerPriceFilters(updown_tp="9")  # 7까지만 허용


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


def _make_client(handler) -> tuple[UpperLowerPriceClient, _FakeAuth]:
    transport = httpx.MockTransport(handler)
    auth = _FakeAuth()
    client = UpperLowerPriceClient(
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
            json={"return_code": 0, "updown_pric": []},
        )

    client, _ = _make_client(handler)
    body = UpperLowerPriceFilters().to_body()
    await client.post(body)
    assert captured["url"].endswith("/api/dostk/stkinfo")
    assert captured["api_id"] == "ka10017"
    assert captured["body"]["updown_tp"] == "2"
    assert captured["body"]["stk_cnd"] == "2"


@pytest.mark.asyncio
async def test_fetch_rows_follows_cont_yn_paging() -> None:
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
                    "updown_pric": [
                        {"stk_cd": "005930", "stk_nm": "삼성전자"},
                        {"stk_cd": "000660", "stk_nm": "SK하이닉스"},
                    ],
                },
            )
        return httpx.Response(
            200,
            headers={"cont-yn": "N", "next-key": ""},
            json={
                "return_code": 0,
                "updown_pric": [{"stk_cd": "035720", "stk_nm": "카카오"}],
            },
        )

    client, _ = _make_client(handler)
    body = UpperLowerPriceFilters().to_body()
    rows = await client.fetch_rows(body, max_rows=999)
    assert len(rows) == 3
    assert calls[0]["cont_yn"] is None
    assert calls[1]["cont_yn"] == "Y"
    assert calls[1]["next_key"] == "KEY2"


@pytest.mark.asyncio
async def test_fetch_rows_default_drains_until_cont_yn_n() -> None:
    """기본 max_rows=None 일 때 cont-yn=N 이 될 때까지 모든 페이지 누적."""
    page = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page["n"] += 1
        is_last = page["n"] == 7  # 7 페이지에서 종료
        return httpx.Response(
            200,
            headers={
                "cont-yn": "N" if is_last else "Y",
                "next-key": "" if is_last else f"K{page['n']}",
            },
            json={
                "return_code": 0,
                "updown_pric": [
                    {"stk_cd": f"P{page['n']}", "stk_nm": "T"},
                ],
            },
        )

    client, _ = _make_client(handler)
    body = UpperLowerPriceFilters().to_body()
    rows = await client.fetch_rows(body)  # max_rows 미지정 = None
    assert len(rows) == 7
    assert page["n"] == 7


@pytest.mark.asyncio
async def test_fetch_rows_stops_when_max_rows_reached() -> None:
    page = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page["n"] += 1
        return httpx.Response(
            200,
            headers={"cont-yn": "Y", "next-key": f"K{page['n']}"},
            json={
                "return_code": 0,
                "updown_pric": [
                    {"stk_cd": f"00000{page['n']}", "stk_nm": "T"},
                ],
            },
        )

    client, _ = _make_client(handler)
    body = UpperLowerPriceFilters().to_body()
    rows = await client.fetch_rows(body, max_rows=3)
    assert len(rows) == 3
    assert page["n"] == 3


@pytest.mark.asyncio
async def test_client_raises_on_business_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"return_code": 1902, "return_msg": "조건이 잘못되었습니다"},
        )

    client, _ = _make_client(handler)
    with pytest.raises(KiwoomApiError) as exc:
        await client.post({})
    assert exc.value.code == 1902
    assert exc.value.api_id == "ka10017"


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
            200,
            headers={"cont-yn": "N"},
            json={"return_code": 0, "updown_pric": []},
        )

    client, _ = _make_client(handler)
    data, _, _ = await client.post({})
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
            200,
            headers={"cont-yn": "N"},
            json={"return_code": 0, "updown_pric": []},
        )

    client, auth = _make_client(handler)
    await client.post({})
    assert state["calls"] == 2
    assert auth.invalidated == 1


# ─────────────────────────────────────────────────────────────────────────────
# 파사드
# ─────────────────────────────────────────────────────────────────────────────


class _FakeFetchClient:
    """``fetch_rows`` 만 호출되는 가짜 클라이언트."""

    def __init__(self, raw: list[dict]) -> None:
        self.raw = raw
        self.calls: list[dict] = []

    async def fetch_rows(self, body, *, max_rows=None):
        self.calls.append({"body": body, "max_rows": max_rows})
        return self.raw


@pytest.mark.asyncio
async def test_facade_default_filters_passed_to_client() -> None:
    fake = _FakeFetchClient([])
    df = await get_upper_lower_price(client=fake)
    assert df.empty
    assert fake.calls[0]["body"]["updown_tp"] == "2"
    assert fake.calls[0]["body"]["stk_cnd"] == "2"
    # 기본 max_rows 는 None (무제한 — cont-yn=N 까지 전체 수집)
    assert fake.calls[0]["max_rows"] is None


@pytest.mark.asyncio
async def test_facade_preserves_api_response_order() -> None:
    """sort_tp 결과를 그대로 보존 (시계열 아님 — 추가 정렬 없음)."""
    raw = [
        {"stk_cd": "A", "flu_rt": "+30.00"},
        {"stk_cd": "B", "flu_rt": "+25.10"},
        {"stk_cd": "C", "flu_rt": "+20.50"},
    ]
    fake = _FakeFetchClient(raw)
    df = await get_upper_lower_price(client=fake)
    assert list(df["stk_cd"]) == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_facade_attaches_filters_to_attrs() -> None:
    fake = _FakeFetchClient([{"stk_cd": "A"}])
    custom = UpperLowerPriceFilters(updown_tp="1", mrkt_tp="101")
    df = await get_upper_lower_price(filters=custom, client=fake)
    assert df.attrs["filters"]["updown_tp"] == "1"
    assert df.attrs["filters"]["mrkt_tp"] == "101"


@pytest.mark.asyncio
async def test_facade_attaches_filters_to_empty_df() -> None:
    fake = _FakeFetchClient([])
    df = await get_upper_lower_price(client=fake)
    assert df.empty
    assert "filters" in df.attrs


@pytest.mark.asyncio
async def test_facade_max_rows_forwarded() -> None:
    fake = _FakeFetchClient([])
    await get_upper_lower_price(max_rows=42, client=fake)
    assert fake.calls[0]["max_rows"] == 42


# ─────────────────────────────────────────────────────────────────────────────
# 리포터
# ─────────────────────────────────────────────────────────────────────────────


def _make_df() -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "stk_cd": "005930",
                "stk_nm": "삼성전자",
                "stk_infr": "",
                "cur_prc": 235500,
                "pred_pre_sig": "1",
                "pred_pre": 54200,
                "flu_rt": 29.90,
                "trde_qty": 1234567,
                "pred_trde_qty": 96197,
                "sel_req": 0,
                "sel_bid": 0,
                "buy_bid": 235500,
                "buy_req": 4,
                "cnt": 1,
            },
            {
                "stk_cd": "000660",
                "stk_nm": "SK하이닉스",
                "stk_infr": "",
                "cur_prc": 13715,
                "pred_pre_sig": "1",
                "pred_pre": 3165,
                "flu_rt": 30.00,
                "trde_qty": 555,
                "pred_trde_qty": 929670,
                "sel_req": 0,
                "sel_bid": 0,
                "buy_bid": 13715,
                "buy_req": 4,
                "cnt": 2,
            },
        ]
    )
    df.attrs["filters"] = UpperLowerPriceFilters().to_body()
    return df


def test_render_markdown_contains_filter_labels() -> None:
    md = render_markdown(_make_df(), fetched_at="2026-05-10 13:24:01")
    assert "# 상한가 종목 리포트 — 상승" not in md  # 상승 필터인데 상한이라고 적히면 안됨
    assert "상하한가 종목 리포트 — 상승" in md  # 기본필터 updown_tp=2 → 상승
    assert "전체(000)" in md  # 시장구분
    assert "상승(2)" in md
    assert "등락률순(3)" in md
    assert "ETF+ETN+스팩 제외(2)" in md
    assert "만주이상(00010)" in md
    assert "1천원이상(8)" in md
    assert "통합(3)" in md


def test_render_markdown_contains_table_rows() -> None:
    md = render_markdown(_make_df(), fetched_at="2026-05-10 13:24:01")
    assert "ka10017" in md
    assert "235,500" in md  # 천단위 콤마
    assert "+29.90" in md  # 등락률 부호 보존
    assert "+30.00" in md
    assert "+54,200" in md  # 전일대비 부호
    assert "+3,165" in md
    assert "삼성전자" in md
    assert "SK하이닉스" in md
    assert "수집 종목 수**: 2건" in md


def test_render_markdown_handles_empty_df() -> None:
    empty = pd.DataFrame()
    empty.attrs["filters"] = UpperLowerPriceFilters().to_body()
    md = render_markdown(empty)
    assert "응답 데이터 없음" in md
    assert "수집 종목 수**: 0건" in md


def test_render_markdown_with_filters_arg_overrides_attrs() -> None:
    df = _make_df()
    custom = UpperLowerPriceFilters(updown_tp="1")  # 상한
    md = render_markdown(df, filters=custom)
    assert "상한(1)" in md


def test_render_markdown_handles_signed_negative_pred_pre() -> None:
    df = _make_df()
    df.loc[0, "pred_pre"] = -54200
    df.loc[0, "flu_rt"] = -29.90
    md = render_markdown(df)
    assert "-54,200" in md
    assert "-29.90" in md


def test_save_writes_to_date_dir_root_without_stock_leaf(tmp_path: Path) -> None:
    """foreigner/chartDay 와 달리 종목 leaf 디렉터리 없이 날짜 디렉터리 직속."""
    df = _make_df()
    fixed_now = datetime(2026, 5, 10, 13, 24, 1)
    out = save_upper_lower_price_markdown(
        df, output_root=tmp_path, now=fixed_now,
    )
    assert out == tmp_path / "20260510" / "upperLowerPrice.md"
    assert out.exists()
    body = out.read_text(encoding="utf-8")
    assert "삼성전자" in body
    assert "2026-05-10 13:24:01" in body


def test_save_filename_is_upperLowerPrice_md(tmp_path: Path) -> None:
    df = _make_df()
    fixed_now = datetime(2026, 5, 10, 9, 0, 0)
    out = save_upper_lower_price_markdown(
        df, output_root=tmp_path, now=fixed_now,
    )
    assert out.name == "upperLowerPrice.md"


def test_save_uses_filters_arg_in_header(tmp_path: Path) -> None:
    df = _make_df()
    custom = UpperLowerPriceFilters(updown_tp="4")  # 하한
    fixed_now = datetime(2026, 5, 10, 9, 0, 0)
    out = save_upper_lower_price_markdown(
        df, filters=custom, output_root=tmp_path, now=fixed_now,
    )
    body = out.read_text(encoding="utf-8")
    assert "하한(4)" in body


# ─────────────────────────────────────────────────────────────────────────────
# ETF / ETN / SPAC 분류 함수
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    [
        # ── 브랜드 prefix 매칭 ──
        "KODEX 200",
        "KODEX 운송",
        "KODEX 미국AI소프트웨어TOP10",
        "TIGER 화장품",
        "TIGER 미국나스닥100",
        "PLUS 우주항공&UAM",
        "RISE 미국S&P500",
        "KBSTAR 골드선물(H)",
        "ACE MSCI인도네시아(합성)",
        "KINDEX 200",
        "SOL 화장품TOP3플러스",
        "HANARO 200",
        "KOSEF 200TR",
        "KIWOOM 코스피200",
        "KoAct 글로벌AI액티브",
        "TIMEFOLIO 글로벌AI인공지능액티브",
        "ARIRANG 고배당주",
        "BNK 고배당플러스",
        "FOCUS 코스피100",
        "TREX 펀더멘털200",
        "마이다스 글로벌리더",
        "파워 고배당저변동성",
        # ── 키워드 substring 매칭 (브랜드 prefix 없이도 캡쳐) ──
        "삼성 단기채권 펀드",         # 채권
        "어떤주식 혼합형",            # 혼합
        "신규운용사 글로벌액티브",      # 액티브
        "신규 ITF 코리아",            # ITF
        "삼성 미국고배당",             # 배당
        "한투 합성지수",              # 합성
        "신한 나스닥100",             # 나스닥
        "한투 다우존스30",            # 다우존스
    ],
)
def test_is_etf_positive(name: str) -> None:
    assert is_etf(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "삼성전자",
        "SK하이닉스",
        "카카오",
        "LG전자우",
        "현대차",
        "ACE침대",          # 공백 없음 → ETF 아님
        "ROBOT PLUS",        # PLUS 가 prefix 가 아님 (suffix)
        "KODEX",             # 브랜드만 단독 — 한국 ETF는 항상 설명 부분 있음
        "",
    ],
)
def test_is_etf_negative(name: str) -> None:
    assert is_etf(name) is False


@pytest.mark.parametrize(
    "name",
    [
        "미래에셋 레버리지 반도체 ETN",
        "신한 블룸버그 인버스2X WTI원유선물 ETN B",
        "메리츠 인버스 2X WTI원유 선물 ETN(H)",
        "미래에셋 레버리지 KRX 금현물 ETN",
        "삼성 KRX 금현물 ETN",
    ],
)
def test_is_etn_positive(name: str) -> None:
    assert is_etn(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "삼성전자",
        "미래에셋증권",        # 발행사명만으로는 미판정
        "신한지주",
        "메리츠금융지주",
        "",
    ],
)
def test_is_etn_negative(name: str) -> None:
    assert is_etn(name) is False


@pytest.mark.parametrize(
    "name",
    [
        "신한스팩7호",
        "하나금융스팩28호",
        "IBKS제15호스팩",
        "삼성머스트스팩5호",
        "엔에이치스팩30호",
    ],
)
def test_is_spac_positive(name: str) -> None:
    assert is_spac(name) is True


@pytest.mark.parametrize(
    "name",
    ["삼성전자", "스타벅스코리아", "스코프", "", "스파크플러스"],
)
def test_is_spac_negative(name: str) -> None:
    assert is_spac(name) is False


# ─────────────────────────────────────────────────────────────────────────────
# filter_out_etf_etn_spac
# ─────────────────────────────────────────────────────────────────────────────


def _mixed_df() -> pd.DataFrame:
    """ETF 3 / ETN 2 / SPAC 1 / 일반 4 = 총 10행."""
    df = pd.DataFrame(
        [
            {"stk_cd": "069500", "stk_nm": "KODEX 200", "flu_rt": 1.5},
            {"stk_cd": "102110", "stk_nm": "TIGER 200", "flu_rt": 1.4},
            {"stk_cd": "278530", "stk_nm": "ACE MSCI인도네시아(합성)", "flu_rt": 2.43},
            {"stk_cd": "610089", "stk_nm": "메리츠 인버스 2X WTI원유 선물 ETN(H)", "flu_rt": 2.56},
            {"stk_cd": "520087", "stk_nm": "미래에셋 레버리지 KRX 금현물 ETN", "flu_rt": 2.33},
            {"stk_cd": "457740", "stk_nm": "신한스팩7호", "flu_rt": 5.12},
            {"stk_cd": "005930", "stk_nm": "삼성전자", "flu_rt": 2.11},
            {"stk_cd": "000660", "stk_nm": "SK하이닉스", "flu_rt": 3.50},
            {"stk_cd": "035720", "stk_nm": "카카오", "flu_rt": 2.21},
            {"stk_cd": "066575", "stk_nm": "LG전자우", "flu_rt": 2.18},
        ]
    )
    df.attrs["filters"] = UpperLowerPriceFilters().to_body()
    return df


def test_filter_out_etf_etn_spac_counts() -> None:
    df = _mixed_df()
    out = filter_out_etf_etn_spac(df)
    stats = out.attrs["filter_stats"]
    assert stats["input_rows"] == 10
    assert stats["etf_excluded"] == 3
    assert stats["etn_excluded"] == 2
    assert stats["spac_excluded"] == 1
    assert stats["kept_rows"] == 4


def test_filter_out_etf_etn_spac_keeps_only_normal_stocks() -> None:
    df = _mixed_df()
    out = filter_out_etf_etn_spac(df)
    kept = list(out["stk_nm"])
    assert kept == ["삼성전자", "SK하이닉스", "카카오", "LG전자우"]


def test_filter_out_etf_etn_spac_preserves_order() -> None:
    """API 의 sort_tp 결과 순서가 보존되어야 한다."""
    df = _mixed_df()
    out = filter_out_etf_etn_spac(df)
    flu_rts = list(out["flu_rt"])
    # 일반 종목 4개의 원본 순서 (등락률은 정렬 기준이 아님 — 입력 순서가 핵심)
    assert flu_rts == [2.11, 3.50, 2.21, 2.18]


def test_filter_out_etf_etn_spac_preserves_filters_attr() -> None:
    df = _mixed_df()
    out = filter_out_etf_etn_spac(df)
    assert out.attrs["filters"]["updown_tp"] == "2"


def test_filter_out_etf_etn_spac_handles_empty() -> None:
    empty = pd.DataFrame()
    empty.attrs["filters"] = UpperLowerPriceFilters().to_body()
    out = filter_out_etf_etn_spac(empty)
    assert out.empty
    assert out.attrs["filter_stats"]["input_rows"] == 0
    assert out.attrs["filter_stats"]["kept_rows"] == 0
    assert out.attrs["filters"]["updown_tp"] == "2"


def test_filter_out_etf_etn_spac_handles_all_excluded() -> None:
    df = pd.DataFrame(
        [
            {"stk_cd": "A", "stk_nm": "KODEX 200"},
            {"stk_cd": "B", "stk_nm": "TIGER 200"},
        ]
    )
    out = filter_out_etf_etn_spac(df)
    assert len(out) == 0
    assert out.attrs["filter_stats"]["etf_excluded"] == 2
    assert out.attrs["filter_stats"]["kept_rows"] == 0


def test_filter_out_etf_etn_spac_handles_nan_stk_nm() -> None:
    """stk_nm 이 NaN/None 인 행은 안전하게 통과한다."""
    df = pd.DataFrame(
        [
            {"stk_cd": "A", "stk_nm": None},
            {"stk_cd": "B", "stk_nm": "삼성전자"},
        ]
    )
    out = filter_out_etf_etn_spac(df)
    assert len(out) == 2  # NaN 은 제외 마커에 매칭 안 됨


# ─────────────────────────────────────────────────────────────────────────────
# Facade — exclude_etf_etn_spac 플래그
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_facade_default_excludes_etf_etn_spac() -> None:
    raw = [
        {"stk_cd": "069500", "stk_nm": "KODEX 200"},
        {"stk_cd": "005930", "stk_nm": "삼성전자"},
        {"stk_cd": "610089", "stk_nm": "메리츠 인버스 2X WTI원유 선물 ETN(H)"},
        {"stk_cd": "457740", "stk_nm": "신한스팩7호"},
    ]
    fake = _FakeFetchClient(raw)
    df = await get_upper_lower_price(client=fake)
    assert list(df["stk_nm"]) == ["삼성전자"]
    stats = df.attrs["filter_stats"]
    assert stats["input_rows"] == 4
    assert stats["etf_excluded"] == 1
    assert stats["etn_excluded"] == 1
    assert stats["spac_excluded"] == 1
    assert stats["kept_rows"] == 1


@pytest.mark.asyncio
async def test_facade_disable_filter_keeps_etf_etn_spac() -> None:
    raw = [
        {"stk_cd": "069500", "stk_nm": "KODEX 200"},
        {"stk_cd": "005930", "stk_nm": "삼성전자"},
    ]
    fake = _FakeFetchClient(raw)
    df = await get_upper_lower_price(client=fake, exclude_etf_etn_spac=False)
    assert list(df["stk_nm"]) == ["KODEX 200", "삼성전자"]
    assert "filter_stats" not in df.attrs


@pytest.mark.asyncio
async def test_facade_filters_attr_preserved_after_exclusion() -> None:
    raw = [{"stk_cd": "069500", "stk_nm": "KODEX 200"}]
    fake = _FakeFetchClient(raw)
    custom = UpperLowerPriceFilters(updown_tp="1")
    df = await get_upper_lower_price(filters=custom, client=fake)
    assert df.empty
    assert df.attrs["filters"]["updown_tp"] == "1"


# ─────────────────────────────────────────────────────────────────────────────
# 리포트 — filter_stats 헤더 표시
# ─────────────────────────────────────────────────────────────────────────────


def test_render_markdown_shows_filter_stats_when_present() -> None:
    df = _make_df()
    df.attrs["filter_stats"] = {
        "input_rows": 500,
        "etf_excluded": 134,
        "etn_excluded": 18,
        "spac_excluded": 5,
        "kept_rows": 343,
    }
    md = render_markdown(df)
    assert "클라이언트 필터링" in md
    assert "원본 500건" in md
    assert "ETF 134" in md
    assert "ETN 18" in md
    assert "스팩 5" in md
    assert "최종 343건" in md


def test_render_markdown_omits_filter_stats_when_absent() -> None:
    df = _make_df()
    # filter_stats 미설정
    md = render_markdown(df)
    assert "클라이언트 필터링" not in md


def test_save_writes_filter_stats_in_file(tmp_path: Path) -> None:
    df = _make_df()
    df.attrs["filter_stats"] = {
        "input_rows": 100,
        "etf_excluded": 10,
        "etn_excluded": 5,
        "spac_excluded": 2,
        "kept_rows": 83,
    }
    fixed_now = datetime(2026, 5, 10, 14, 0, 0)
    out = save_upper_lower_price_markdown(
        df, output_root=tmp_path, now=fixed_now,
    )
    body = out.read_text(encoding="utf-8")
    assert "클라이언트 필터링" in body
    assert "최종 83건" in body
