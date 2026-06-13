"""chartDay KiwoomChartClient 페이징 / 오류 처리 검증.

chart60 클라이언트와 동일 구현이지만 chartDay 패키지에 위치한 사본을
독립적으로 검증한다.
"""

from __future__ import annotations

import json

import httpx
import pytest

from src.kiwoom.chartDay.getData.client import KiwoomChartClient
from src.kiwoom.chartDay.getData.models import KiwoomApiError


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


def _make_client(handler) -> tuple[KiwoomChartClient, _FakeAuth]:
    transport = httpx.MockTransport(handler)
    auth = _FakeAuth()
    client = KiwoomChartClient(auth=auth, config=_FakeConfig(), transport=transport)
    return client, auth


@pytest.mark.asyncio
async def test_post_paged_follows_cont_yn_and_next_key() -> None:
    calls: list[dict] = []

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
                headers={"cont-yn": "Y", "next-key": "PAGE2KEY"},
                json={
                    "return_code": 0,
                    "stk_dt_pole_chart_qry": [
                        {"dt": "20260509", "cur_prc": "+1000"},
                        {"dt": "20260508", "cur_prc": "+999"},
                    ],
                },
            )
        return httpx.Response(
            200,
            headers={"cont-yn": "N", "next-key": ""},
            json={
                "return_code": 0,
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
    assert calls[0]["api_id"] == "ka10081"
    assert calls[0]["auth"].startswith("Bearer token-")
    assert calls[1]["cont_yn"] == "Y"
    assert calls[1]["next_key"] == "PAGE2KEY"


@pytest.mark.asyncio
async def test_post_raises_on_business_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"return_code": 1902, "return_msg": "종목 정보가 없습니다"},
        )

    client, _ = _make_client(handler)
    with pytest.raises(KiwoomApiError) as exc:
        await client.post("ka10081", {"stk_cd": "INVALID"})
    assert exc.value.code == 1902
    assert exc.value.api_id == "ka10081"


@pytest.mark.asyncio
async def test_post_retries_on_rate_limit_then_succeeds() -> None:
    state = {"calls": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["calls"] == 1:
            return httpx.Response(
                200, json={"return_code": 1700, "return_msg": "허용된 요청 개수 초과"}
            )
        return httpx.Response(
            200,
            headers={"cont-yn": "N"},
            json={"return_code": 0, "stk_dt_pole_chart_qry": [{"dt": "20260509", "cur_prc": "+1"}]},
        )

    client, _ = _make_client(handler)
    data, cont_yn, _ = await client.post(
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
                200, json={"return_code": 8005, "return_msg": "Token이 유효하지 않습니다"}
            )
        return httpx.Response(
            200, headers={"cont-yn": "N"}, json={"return_code": 0, "stk_dt_pole_chart_qry": []}
        )

    client, auth = _make_client(handler)
    await client.post("ka10081", {"stk_cd": "005930", "base_dt": "20260509", "upd_stkpc_tp": "1"})
    assert state["calls"] == 2
    assert auth.invalidated == 1
    assert auth.fetch_count >= 2
