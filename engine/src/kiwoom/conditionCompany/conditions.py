"""ka10171: 조건검색 목록조회.

서버에 저장된 조건검색식 목록을 조회하여 ``{name: seq}`` 매핑으로 반환한다.
응답의 ``data`` 는 ``[[seq, name], ...]`` 형식의 2차원 리스트(문서 p.244)지만,
계정에 따라 dict 리스트로 응답하는 경우도 있어 양쪽 모두를 허용한다.
"""

from __future__ import annotations

from typing import Final

from loguru import logger

from src.kiwoom.conditionCompany.models import ConditionItem, KiwoomConditionError
from src.kiwoom.conditionCompany.ws_client import KiwoomConditionWebSocket

_API_ID: Final[str] = "ka10171"
_TRNM: Final[str] = "CNSRLST"


def _parse_data(data: object) -> list[ConditionItem]:
    """응답 ``data`` 를 ``ConditionItem`` 리스트로 정규화."""
    if not isinstance(data, list):
        return []
    items: list[ConditionItem] = []
    for row in data:
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            items.append(ConditionItem(seq=str(row[0]), name=str(row[1])))
        elif isinstance(row, dict):
            items.append(
                ConditionItem(
                    seq=str(row.get("seq", "")),
                    name=str(row.get("name", "")),
                )
            )
    return items


async def fetch_condition_list(
    ws: KiwoomConditionWebSocket,
) -> list[ConditionItem]:
    """ka10171 호출 → 서버 저장 조건검색식 전체 목록.

    Args:
        ws: 이미 LOGIN 완료된 :class:`KiwoomConditionWebSocket` 세션.

    Returns:
        ``ConditionItem`` 리스트 (응답 순서 보존).

    Raises:
        KiwoomConditionError: API 오류 응답.
    """
    msg = await ws.request({"trnm": _TRNM}, expected_trnm=_TRNM)
    items = _parse_data(msg.get("data"))
    logger.info("ka10171 조건식 목록 {n}건 수신", n=len(items))
    return items


async def build_name_to_seq(
    ws: KiwoomConditionWebSocket,
    *,
    required_names: list[str] | None = None,
) -> dict[str, str]:
    """``{조건명: seq}`` 매핑을 만들어 반환한다.

    ``required_names`` 가 주어지면 모두 발견되었는지 사전 검증한다.
    누락이 있으면 :class:`KiwoomConditionError` 로 raise.

    Args:
        ws: 활성 WebSocket 세션.
        required_names: 반드시 존재해야 하는 조건명 리스트(이름 매칭).

    Returns:
        조건명 → seq 매핑 dict.

    Raises:
        KiwoomConditionError: 동명 조건이 둘 이상 존재하거나 ``required_names``
            중 일부가 서버 목록에 없는 경우.
    """
    items = await fetch_condition_list(ws)

    name_to_seq: dict[str, str] = {}
    duplicates: list[str] = []
    for item in items:
        if item.name in name_to_seq:
            duplicates.append(item.name)
            continue  # 첫 등장만 채택, 중복은 따로 모아 경고
        name_to_seq[item.name] = item.seq

    if duplicates:
        logger.warning(
            "ka10171 동명 조건식 중복 발견(첫 항목만 사용): {d}",
            d=sorted(set(duplicates)),
        )

    if required_names:
        missing = [n for n in required_names if n not in name_to_seq]
        if missing:
            raise KiwoomConditionError(
                code="MISSING",
                msg=f"서버에 저장되지 않은 조건명: {missing}",
                api_id=_API_ID,
            )

    return name_to_seq
