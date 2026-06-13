"""거래소 코드 정규화 공용 유틸.

키움 REST API 의 ``stk_cd`` 필드는 거래소별 접미사를 포함한다 (PDF p.156 등):

    - **KRX** (한국거래소):     ``039490`` (평문)
    - **NXT** (NEXTRADE):       ``039490_NX``
    - **SOR** (Smart Order Routing, 통합): ``039490_AL``

HTS [0995] 종목별투자자 (통합) 탭, HTS 차트 (통합) 등 키움 HTS 의 기본 화면은
**SOR 통합값**을 표시한다. 한국시장은 2025년 NXT 개장 후 다중 거래소 체제로
들어섰고, KRX 단독 호출 시 NXT 거래분이 누락되어 HTS 통합값과 일치하지 않는다
(예: 005930 일봉 종가 KRX 268,500 vs SOR 276,500).

본 모듈은 ``stk_cd`` + ``exchange`` 두 인자를 키움 API 가 받는 코드로 정규화하는
:func:`normalize_stk_cd` 만 제공한다. 모든 도메인 모듈
(``chart60``, ``chartDay``, ``investor``, ``etc.foreigner`` 등) 이 동일하게
import 하여 사용한다.
"""

from __future__ import annotations

from typing import Final

_SUFFIX_SOR: Final[str] = "_AL"
_SUFFIX_NXT: Final[str] = "_NX"
_VALID_SUFFIXES: Final[tuple[str, ...]] = (_SUFFIX_SOR, _SUFFIX_NXT)

DEFAULT_EXCHANGE: Final[str] = "sor"


def normalize_stk_cd(stk_cd: str, exchange: str = DEFAULT_EXCHANGE) -> tuple[str, str]:
    """입력 종목코드 + 거래소 인자를 키움 API 가 받는 종목코드로 정규화.

    Args:
        stk_cd: 종목코드. 평문(``"005930"``) 또는 접미사 포함(``"005930_AL"``,
            ``"005930_NX"``) 모두 허용. 명시적 접미사가 있으면 그것을 우선한다.
        exchange: ``"sor"`` (통합, 기본) / ``"krx"`` / ``"nxt"``. 대소문자 무관.
            ``stk_cd`` 에 이미 접미사가 있으면 무시된다.

    Returns:
        ``(api_stk_cd, exchange_label)``. ``api_stk_cd`` 는 키움 API 에 보낼
        문자열, ``exchange_label`` 은 리포트 표시용 ("SOR(통합)" / "KRX" / "NXT").

    Raises:
        ValueError: 알 수 없는 ``exchange`` 값.

    예::

        >>> normalize_stk_cd("005930")
        ('005930_AL', 'SOR(통합)')
        >>> normalize_stk_cd("005930", "krx")
        ('005930', 'KRX')
        >>> normalize_stk_cd("005930", "nxt")
        ('005930_NX', 'NXT')
        >>> normalize_stk_cd("005930_AL", "krx")  # 명시적 접미사 우선
        ('005930_AL', 'SOR(통합)')
    """
    s = stk_cd.strip()
    for suffix in _VALID_SUFFIXES:
        if s.endswith(suffix):
            label = "SOR(통합)" if suffix == _SUFFIX_SOR else "NXT"
            return s, label
    ex = exchange.lower()
    if ex == "sor":
        return f"{s}{_SUFFIX_SOR}", "SOR(통합)"
    if ex == "krx":
        return s, "KRX"
    if ex == "nxt":
        return f"{s}{_SUFFIX_NXT}", "NXT"
    raise ValueError(f"알 수 없는 exchange: {exchange!r} (sor/krx/nxt 중 하나)")


__all__ = ["DEFAULT_EXCHANGE", "normalize_stk_cd"]
