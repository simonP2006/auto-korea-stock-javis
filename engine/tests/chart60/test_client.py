"""KiwoomChartClient 페이징 / 오류 처리 검증.

httpx ``MockTransport`` 로 가짜 키움 응답을 주입한다. 실제 토큰 발급 호출을
피하기 위해 인증부는 :class:`_FakeAuth` 로 대체한다.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from src.kiwoom.chart60.getData.client import KiwoomChartClient
from src.kiwoom.chart60.getData.models import KiwoomApiError


class _FakeAuth:
    """``KiwoomAuth`` 인터페이스만 모방하는 토큰 스텁."""

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


def _make_client(handler) -> tuple[KiwoomChartClient, _FakeAuth]:
    transport = httpx.MockTransport(handler)
    auth = _FakeAuth()
    client = KiwoomChartClient(auth=auth, config=_FakeConfig(), transport=transport)
    return client, auth


@pytest.mark.asyncio
async def test_post_paged_follows_cont_yn_and_next_key() -> None:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(
            {
                "body": body,
                "cont_yn": request.headers.get("cont-yn"),
                "next_key": request.headers.get("next-key"),
                "api_id": request.headers.get("api-id"),
                "auth": request.headers.get("authorization"),
            }
        )
        if request.headers.get("cont-yn") != "Y":
            return httpx.Response(
                200,
                headers={"cont-yn": "Y", "next-key": "PAGE2KEY", "api-id": "ka10081"},
                json={
                    "return_code": 0,
                    "return_msg": "ok",
                    "stk_dt_pole_chart_qry": [
                        {"dt": "20260509", "cur_prc": "+1000"},
                        {"dt": "20260508", "cur_prc": "+999"},
                    ],
                },
            )
        return httpx.Response(
            200,
            headers={"cont-yn": "N", "next-key": "", "api-id": "ka10081"},
            json={
                "return_code": 0,
                "return_msg": "ok",
                "stk_dt_pole_chart_qry": [{"dt": "20260507", "cur_prc": "+998"}],
            },
        )

    client, _ = _make_client(handler)
    rows = await client.post_paged(
        "ka10081",
        {"stk_cd": "005930", "base_dt": "20260509", "upd_stkpc_tp": "1"},
        "stk_dt_pole_chart_qry",
    )
    assert len(rows) == 3
    assert len(calls) == 2
    assert calls[0]["cont_yn"] is None
    assert calls[0]["next_key"] is None
    assert calls[0]["api_id"] == "ka10081"
    assert calls[0]["auth"].startswith("Bearer token-")
    assert calls[1]["cont_yn"] == "Y"
    assert calls[1]["next_key"] == "PAGE2KEY"


@pytest.mark.asyncio
async def test_post_paged_stops_when_predicate_satisfied() -> None:
    page = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        page["n"] += 1
        return httpx.Response(
            200,
            headers={"cont-yn": "Y", "next-key": f"K{page['n']}"},
            json={
                "return_code": 0,
                "stk_min_pole_chart_qry": [
                    {"cntr_tm": f"2026050913{page['n']:02d}00", "cur_prc": "+100"},
                ],
            },
        )

    client, _ = _make_client(handler)
    rows = await client.post_paged(
        "ka10080",
        {"stk_cd": "005930", "tic_scope": "60"},
        "stk_min_pole_chart_qry",
        stop_when=lambda r: len(r) >= 3,
    )
    assert len(rows) == 3
    assert page["n"] == 3  # cont-yn=Y이지만 predicate가 먼저 종료시킴.


@pytest.mark.asyncio
async def test_post_raises_on_business_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"return_code": 1902, "return_msg": "종목 정보가 없습니다"},
        )

    client, _ = _make_client(handler)
    with pytest.raises(KiwoomApiError) as exc_info:
        await client.post("ka10080", {"stk_cd": "INVALID"})
    assert exc_info.value.code == 1902
    assert exc_info.value.api_id == "ka10080"


@pytest.mark.asyncio
async def test_post_retries_on_rate_limit_then_succeeds() -> None:
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
            json={"return_code": 0, "stk_dt_pole_chart_qry": [{"dt": "20260509", "cur_prc": "+1"}]},
        )

    client, _ = _make_client(handler)
    data, cont_yn, next_key = await client.post(
        "ka10081", {"stk_cd": "005930", "base_dt": "20260509", "upd_stkpc_tp": "1"}
    )
    assert state["calls"] == 2
    assert data["return_code"] == 0
    assert cont_yn == "N"


@pytest.mark.asyncio
async def test_post_invalidates_token_on_8005_then_retries() -> None:
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
            json={"return_code": 0, "stk_dt_pole_chart_qry": []},
        )

    client, auth = _make_client(handler)
    await client.post("ka10081", {"stk_cd": "005930", "base_dt": "20260509", "upd_stkpc_tp": "1"})
    assert state["calls"] == 2
    assert auth.invalidated == 1
    assert auth.fetch_count >= 2  # 재발급 1회 이상.
