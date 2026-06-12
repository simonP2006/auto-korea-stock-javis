"""일봉 + MA 결과를 마크다운 리포트로 저장.

저장 경로 규칙: ``reports/<실행일자 YYYYMMDD>/chartDay.md``.
"실행일자"는 함수가 호출되는 시점의 시스템 현재일(``datetime.now()``)이며,
DataFrame 안의 봉 날짜와는 별개다.

본 단계 구현은 chart60과 동일하게 시간 오름차순(과거→최신)으로 표를 그린다.
표시 정렬을 내림차순으로 바꾸는 후속 작업은 별도 단계에서 처리한다.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

import pandas as pd
from loguru import logger

from src.kiwoom.config import config

_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports")
_FILENAME: Final[str] = "chartDay.md"
_MA_COLUMNS_DEFAULT: Final[tuple[str, ...]] = ("ma10", "ma20", "ma60", "ma306", "ma612")


def _fmt_int(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(v):,}"


def _fmt_float(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v):,.2f}"


def _fmt_dt(s: str) -> str:
    """``YYYYMMDD`` → ``YYYY-MM-DD``."""
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def render_markdown(
    df: pd.DataFrame,
    *,
    stk_cd: str,
    stk_name: str = "",
    fetched_at: str = "",
) -> str:
    """일봉 DataFrame을 마크다운 문자열로 렌더링한다.

    Args:
        df: ``get_daily_with_ma()`` 가 반환한 DataFrame.
        stk_cd: 종목코드.
        stk_name: 종목명(표시용, 미지정 시 빈 문자열).
        fetched_at: 취득 시각 표기(미지정 시 빈 문자열).

    Returns:
        마크다운 본문 문자열. ``df`` 가 비었으면 그 사실을 표기하는 짧은 문서.
    """
    title_name = f"{stk_name}({stk_cd})" if stk_name else stk_cd
    exchange_label = df.attrs.get("exchange_label", "SOR(통합)")
    api_stk_cd = df.attrs.get("api_stk_cd", stk_cd)
    if df.empty:
        return f"# {title_name} 일봉 분석\n\n응답 데이터 없음.\n"

    last = df.iloc[-1]
    first = df.iloc[0]
    ma_cols_present = [c for c in _MA_COLUMNS_DEFAULT if c in df.columns]

    lines: list[str] = [
        f"# {title_name} 일봉 차트 + MA 분석",
        "",
        "## 기본 정보",
        f"- **종목코드**: {stk_cd} (API 호출 코드: `{api_stk_cd}`)",
    ]
    if stk_name:
        lines.append(f"- **종목명**: {stk_name}")
    lines += [
        f"- **거래소**: {exchange_label}",
        f"- **데이터 모드**: {config.mode} ({config.base_url})",
        f"- **취득 시각**: {fetched_at}" if fetched_at else "- **취득 시각**: —",
        f"- **일봉 행 수**: {len(df)}봉",
        f"- **날짜 범위**: {_fmt_dt(first['dt'])} ~ {_fmt_dt(last['dt'])}",
        "- **MA 산출 기준**: 일봉 종가 기준 단순이동평균(SMA)",
        "",
        "## 최근 봉 스냅샷",
        f"- **최근 봉 일자**: {_fmt_dt(last['dt'])}",
        f"- **최근 종가**: {_fmt_int(last['cur_prc'])} 원",
    ]
    for col in ma_cols_present:
        label = col.upper()
        lines.append(f"- **{label}(일)**: {_fmt_float(last[col])}")

    ma_header = " | ".join(c.upper() for c in ma_cols_present)
    ma_align = "|".join(["---:"] * len(ma_cols_present))
    lines += [
        "",
        "## 일봉 시계열 (날짜 오름차순)",
        "",
        f"| 날짜 | 시가 | 고가 | 저가 | 종가 | 거래량 | {ma_header} |",
        f"|---|---:|---:|---:|---:|---:|{ma_align}|",
    ]
    for _, r in df.iterrows():
        cells = [
            _fmt_dt(r["dt"]),
            _fmt_int(r["open_pric"]),
            _fmt_int(r["high_pric"]),
            _fmt_int(r["low_pric"]),
            _fmt_int(r["cur_prc"]),
            _fmt_int(r["trde_qty"]),
        ]
        cells.extend(_fmt_float(r.get(c)) for c in ma_cols_present)
        lines.append("| " + " | ".join(cells) + " |")

    lines += [
        "",
        "## 비고",
        "- 가격 단위: 원, 거래량 단위: 주",
        "- MA 값은 일봉 종가 기준 단순이동평균(SMA). 윈도우 미충족 구간은 NaN(``—``)으로 표기",
        "- 데이터 출처: 키움 OpenAPI ka10081(주식일봉차트조회)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_chartday_markdown(
    df: pd.DataFrame,
    *,
    stk_cd: str,
    stk_name: str = "",
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Path:
    """마크다운 렌더 후 ``<output_root>/<오늘 YYYYMMDD>/chartDay.md`` 에 저장.

    Args:
        df: ``get_daily_with_ma()`` 반환 DataFrame.
        stk_cd: 종목코드.
        stk_name: 종목명(표시용).
        output_root: 리포트 루트 디렉터리(기본 ``reports``).
        now: 실행 시각. ``None`` 이면 ``datetime.now()`` 사용.

    Returns:
        저장된 파일의 ``Path``.
    """
    current = now or datetime.now()
    today_dir = current.strftime("%Y%m%d")
    fetched_at = current.strftime("%Y-%m-%d %H:%M:%S")

    md = render_markdown(df, stk_cd=stk_cd, stk_name=stk_name, fetched_at=fetched_at)

    stock_leaf = f"{stk_name}({stk_cd})" if stk_name else stk_cd
    out_dir = output_root / today_dir / stock_leaf
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _FILENAME
    out_path.write_text(md, encoding="utf-8")
    logger.info("리포트 저장: {p}", p=out_path)
    return out_path
