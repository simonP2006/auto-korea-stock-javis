"""조건검색 통합 결과를 마크다운으로 저장.

저장 경로: ``reports/<실행일자 YYYYMMDD>/conditionResearch.md`` (단일 파일).

리포트 구성:
    1. 헤더(실행시각, 모드, 실행순서, 누락)
    2. 통합 요약 테이블 — 조건별 raw / 누적후 / 제외 카운트
    3. 조건별 상세 섹션 — 검색식 정의 + 매칭 종목 표(전략 A 적용 후)
    4. 부록 — 공통 대상변경(jpg) 메모

전략 A(순차 누적 제외) 표기 규약:
    - 각 조건 섹션의 표는 "이 조건이 처음으로 잡은 종목"만 보여준다.
    - 표 위 메타라인에 ``RAW: M건 / 누적후: N건 (앞 X건 제외)`` 표기.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.conditionCompany.formulas import (
    COMMON_UNIVERSE_NOTE,
    FORMULA_DEFINITIONS,
)
from src.kiwoom.conditionCompany.models import (
    CompositeResult,
    FilteredConditionResult,
    MatchedStock,
)
from src.kiwoom.config import config

_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports")
_FILENAME: Final[str] = "conditionResearch.md"


def _fmt_int(v: int) -> str:
    return f"{v:,}"


def _fmt_pct(v: float) -> str:
    return f"{v:+.2f}%"


def _fmt_won(v: int) -> str:
    return f"{v:,}"


def _fmt_signed_won(v: int) -> str:
    if v > 0:
        return f"+{v:,}"
    return f"{v:,}"


def _stock_table(stocks: list[MatchedStock]) -> list[str]:
    """매칭 종목 리스트를 마크다운 표 라인들로 변환."""
    if not stocks:
        return ["_(매칭 종목 없음)_"]
    lines = [
        "| # | 종목코드 | 종목명 | 현재가 | 전일대비 | 등락율 | 시가 | 고가 | 저가 | 거래량 |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, s in enumerate(stocks, 1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    s.stk_cd,
                    s.stk_nm,
                    _fmt_won(s.cur_prc),
                    _fmt_signed_won(s.pred_pre),
                    _fmt_pct(s.flu_rt),
                    _fmt_won(s.open_pric),
                    _fmt_won(s.high_pric),
                    _fmt_won(s.low_pric),
                    _fmt_int(s.trde_qty),
                ]
            )
            + " |"
        )
    return lines


def _formula_block(name: str) -> list[str]:
    """``FORMULA_DEFINITIONS`` 의 식 본문을 들여쓰기 마크다운으로."""
    spec = FORMULA_DEFINITIONS.get(name)
    if spec is None:
        return ["_(식 정의 미등록)_"]
    combine, conds = spec
    out = [f"**결합식**: `{combine}`", ""]
    for code, body in conds:
        out.append(f"- **{code}**: {body}")
    return out


def _summary_table(result: CompositeResult) -> list[str]:
    lines = [
        "| # | 조건명 | seq | RAW 매칭 | 누적 후 | 제외 |",
        "|---:|---|---|---:|---:|---:|",
    ]
    raw_total = 0
    kept_total = 0
    for i, r in enumerate(result.results, 1):
        lines.append(
            f"| {i} | {r.name} | {r.seq} | {_fmt_int(r.raw_count)} | "
            f"{_fmt_int(r.kept_count)} | {_fmt_int(r.excluded_count)} |"
        )
        raw_total += r.raw_count
        kept_total += r.kept_count
    lines.append(
        f"| | **합계** |  | **{_fmt_int(raw_total)}** | "
        f"**{_fmt_int(kept_total)}** | **{_fmt_int(raw_total - kept_total)}** |"
    )
    return lines


def render_markdown(result: CompositeResult) -> str:
    """``CompositeResult`` 를 마크다운 문자열로 렌더링."""
    fetched = result.fetched_at.strftime("%Y-%m-%d %H:%M:%S")
    today = result.fetched_at.strftime("%Y-%m-%d")

    lines: list[str] = [
        f"# 조건검색 결과 — {today}",
        "",
        "## 실행 정보",
        f"- 조회 시각: {fetched}",
        f"- 실행 모드: `{config.mode}` ({config.base_url})",
        "- 거래소: KRX",
        f"- 실행 조건식 수: {len(result.results)} / {len(result.execution_order)}",
        f"- 실행 순서: {' → '.join(result.execution_order)}",
        "- 중복 처리: **전략 A (순차 누적 제외)** — 먼저 잡힌 자가 임자",
        f"- 고유 누적 종목 수: **{_fmt_int(result.total_unique)}**",
    ]
    if result.missing:
        lines.append(f"- ⚠️ 누락(서버 미등록): {', '.join(result.missing)}")
    lines.append("")

    lines += [
        "## 통합 요약",
        "",
        *_summary_table(result),
        "",
    ]

    lines.append("---")
    lines.append("")
    lines.append("## 조건별 상세")
    lines.append("")

    for i, fr in enumerate(result.results, 1):
        lines += _section_for_condition(i, fr)

    lines += [
        "---",
        "",
        "## 부록: 공통 대상변경 설정 (영웅문4 기준)",
        "",
        COMMON_UNIVERSE_NOTE,
        "",
        "## 비고",
        "- 가격 단위: 원, 거래량 단위: 주",
        "- 등락율은 ka10172 응답 필드 12를 1/100로 보정한 % 값",
        "- 표의 매칭 종목은 **전략 A 적용 후**(중복 제거된 새 종목만)임",
        "- 검색식 텍스트는 ``docs/conditionResearch/*.xls`` 추출본 기준",
        "- 데이터 출처: 키움 OpenAPI ka10171 / ka10172 (WebSocket)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]

    return "\n".join(lines)


def _section_for_condition(idx: int, fr: FilteredConditionResult) -> list[str]:
    lines = [
        f"### {idx}. {fr.name} (seq=`{fr.seq}`)",
        "",
        *_formula_block(fr.name),
        "",
        f"- RAW 매칭: **{_fmt_int(fr.raw_count)}건**",
        f"- 누적 후 매칭: **{_fmt_int(fr.kept_count)}건** "
        f"(앞 조건들에서 이미 잡힌 {_fmt_int(fr.excluded_count)}건 제외)",
        "",
        *_stock_table(fr.stocks),
        "",
    ]
    return lines


def save_condition_research(
    result: CompositeResult,
    *,
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
) -> Path:
    """``reports/<YYYYMMDD>/conditionResearch.md`` 로 저장하고 경로를 반환.

    Args:
        result: ``run_all_conditions()`` 반환값.
        output_root: 리포트 루트(기본 ``reports``).

    Returns:
        저장된 파일 경로.
    """
    today_dir = result.fetched_at.strftime("%Y%m%d")
    out_dir = output_root / today_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _FILENAME

    md = render_markdown(result)
    out_path.write_text(md, encoding="utf-8")
    logger.info("conditionResearch.md 저장: {p}", p=out_path)
    return out_path
