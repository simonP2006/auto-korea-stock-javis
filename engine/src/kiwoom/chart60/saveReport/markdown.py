"""60분봉 + 일봉 MA 결과를 마크다운 리포트로 저장.

저장 경로 규칙: ``reports/<실행일자 YYYYMMDD>/chart60.md``.
"실행일자"는 함수가 호출되는 시점의 시스템 현재일(``datetime.now()``)이며,
DataFrame 안의 봉 날짜와는 별개다(스크립트 실행 단위로 묶기 위함).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

import pandas as pd
from loguru import logger

from src.kiwoom.config import config

_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports")
_FILENAME: Final[str] = "chart60.md"


def _fmt_int(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(v):,}"


def _fmt_float(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v):,.2f}"


def _fmt_ts(s: str) -> str:
    """``YYYYMMDDHHMMSS`` → ``YYYY-MM-DD HH:MM``."""
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"


def render_markdown(
    df: pd.DataFrame,
    *,
    stk_cd: str,
    stk_name: str = "",
    fetched_at: str = "",
) -> str:
    """DataFrame을 마크다운 문자열로 렌더링한다.

    Args:
        df: ``get_60min_with_daily_ma()`` 가 반환한 DataFrame.
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
        return f"# {title_name} 60분봉 분석\n\n응답 데이터 없음.\n"

    last = df.iloc[-1]
    first = df.iloc[0]

    lines: list[str] = [
        f"# {title_name} 60분 차트 + 60분봉 MA 분석",
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
        f"- **분봉 행 수**: {len(df)}봉",
        f"- **시간 범위**: {_fmt_ts(first['cntr_tm'])} ~ {_fmt_ts(last['cntr_tm'])}",
        "- **MA 산출 기준**: 60분봉 종가 기준 단순이동평균(SMA) — HTS [0600] 60분봉 MA 와 일치",
        "",
        "## 최근 봉 스냅샷",
        f"- **최근 봉 시각**: {_fmt_ts(last['cntr_tm'])}",
        f"- **최근 종가**: {_fmt_int(last['cur_prc'])} 원",
    ]
    for col in ("ma10", "ma20", "ma60", "ma306"):
        if col in df.columns:
            label = col.upper()  # MA10, MA20, ...
            lines.append(f"- **{label}**: {_fmt_float(last[col])}")
    lines += [
        "",
        "## 60분봉 시계열 (시간 오름차순)",
        "",
        "| 시각 | 시가 | 고가 | 저가 | 종가 | 거래량 | MA10 | MA20 | MA60 | MA306 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in df.iterrows():
        lines.append(
            "| {ts} | {o} | {h} | {l} | {c} | {v} | {m10} | {m20} | {m60} | {m306} |".format(
                ts=_fmt_ts(r["cntr_tm"]),
                o=_fmt_int(r["open_pric"]),
                h=_fmt_int(r["high_pric"]),
                l=_fmt_int(r["low_pric"]),
                c=_fmt_int(r["cur_prc"]),
                v=_fmt_int(r["trde_qty"]),
                m10=_fmt_float(r.get("ma10")),
                m20=_fmt_float(r.get("ma20")),
                m60=_fmt_float(r.get("ma60")),
                m306=_fmt_float(r.get("ma306")),
            )
        )
    lines += [
        "",
        "## 비고",
        "- 가격 단위: 원, 거래량 단위: 주(60분봉별 체결량)",
        "- MA 값은 60분봉 종가의 N 기간 단순이동평균(SMA) — HTS [0600] 60분봉 차트의 MA 와 동일한 의미",
        "- 데이터 출처: 키움 OpenAPI ka10080(주식분봉차트조회)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_chart60_markdown(
    df: pd.DataFrame,
    *,
    stk_cd: str,
    stk_name: str = "",
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Path:
    """마크다운 렌더 후 ``<output_root>/<오늘 YYYYMMDD>/chart60.md`` 에 저장.

    Args:
        df: facade 반환 DataFrame.
        stk_cd: 종목코드.
        stk_name: 종목명(표시용).
        output_root: 리포트 루트 디렉터리(기본 ``reports``).
        now: 실행 시각. ``None`` 이면 ``datetime.now()`` 사용. 테스트에서는
            결정적 검증을 위해 고정값을 주입한다.

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
