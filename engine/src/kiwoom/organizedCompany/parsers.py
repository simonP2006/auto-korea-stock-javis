"""마크다운 표에서 종목 데이터를 추출한다.

대상 입력 파일은 두 가지지만, 두 파일 모두 다음 공통 구조를 갖는 표를 가진다:

    | # | 종목코드 | 종목명 | ... | 등락률(또는 등락율) | ... |

공통 처리:
    - 마크다운을 줄 단위로 스캔
    - ``|`` 로 시작하는 헤더 라인을 만나면, 다음 줄이 분리자(``|---|---:|...``)
      인지 확인
    - 헤더에 ``종목명`` + (``등락률`` 또는 ``등락율``) 컬럼이 있는 표만 채택
    - 데이터 행을 끝까지 읽고 ``OrganizedStock`` 으로 변환

이 방식은 표 헤더가 파일별로 달라도(컬럼 개수·순서 차이) 안전하게 동작한다.
``conditionResearch.md`` 의 통합 요약 표(``조건명, seq, RAW...``)는 ``종목명``
컬럼이 없으므로 자동으로 무시된다.
"""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from src.kiwoom.organizedCompany.models import OrganizedStock, SourceLabel

_NAME_HEADERS: tuple[str, ...] = ("종목명",)
_RATE_HEADERS: tuple[str, ...] = ("등락률", "등락율")
_CODE_HEADERS: tuple[str, ...] = ("종목코드",)


def _split_row(line: str) -> list[str]:
    """``"| a | b | c |"`` → ``["a", "b", "c"]`` (앞뒤 파이프 제거 + 셀 strip)."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [cell.strip() for cell in s.split("|")]


def _is_separator(line: str) -> bool:
    """``"|---|---:|:---:|"`` 같은 표 분리자 라인 여부."""
    s = line.strip()
    if not s.startswith("|"):
        return False
    cells = _split_row(s)
    if not cells:
        return False
    return all(c and all(ch in "-:" for ch in c) for c in cells)


def _find_col(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    """헤더 셀 중 ``candidates`` 와 일치하는 첫 인덱스. 없으면 ``None``."""
    for i, h in enumerate(headers):
        if h in candidates:
            return i
    return None


def _parse_rate(s: str) -> float:
    """``"+24.11"`` / ``"-1.30%"`` / ``"0.00"`` / 빈값 → ``float`` (% 단위, 부호 보존)."""
    if not s:
        return 0.0
    cleaned = s.strip().replace("%", "").replace(",", "").replace("+", "")
    if not cleaned or cleaned == "-":
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_from_text(text: str, *, source: SourceLabel) -> list[OrganizedStock]:
    """주어진 마크다운 본문에서 모든 종목 표를 누적 파싱."""
    lines = text.splitlines()
    out: list[OrganizedStock] = []
    n = len(lines)
    i = 0
    table_count = 0

    while i < n:
        line = lines[i]
        if not line.lstrip().startswith("|"):
            i += 1
            continue

        if i + 1 >= n or not _is_separator(lines[i + 1]):
            i += 1
            continue

        # 헤더 + 분리자 확인됨 → 표 시작
        headers = _split_row(line)
        name_idx = _find_col(headers, _NAME_HEADERS)
        rate_idx = _find_col(headers, _RATE_HEADERS)
        if name_idx is None or rate_idx is None:
            # 종목 표가 아님(예: 통합 요약 표). 분리자 다음 라인부터 다시 스캔
            i += 2
            continue

        code_idx = _find_col(headers, _CODE_HEADERS)
        table_count += 1
        i += 2  # 분리자 다음으로 이동

        # 데이터 행 누적
        while i < n and lines[i].lstrip().startswith("|"):
            cells = _split_row(lines[i])
            i += 1
            if len(cells) <= max(name_idx, rate_idx):
                continue
            stk_nm = cells[name_idx].strip()
            if not stk_nm:
                continue
            stk_cd = cells[code_idx].strip() if (code_idx is not None and len(cells) > code_idx) else ""
            flu_rt = _parse_rate(cells[rate_idx])
            out.append(
                OrganizedStock(
                    stk_cd=stk_cd,
                    stk_nm=stk_nm,
                    flu_rt=flu_rt,
                    source=source,
                )
            )

    logger.debug(
        "parsed source={s} tables={t} rows={r}",
        s=source, t=table_count, r=len(out),
    )
    return out


def parse_condition_research(path: Path | str) -> list[OrganizedStock]:
    """``reports/.../conditionResearch.md`` 파싱.

    9개 조건별 표를 모두 누적해 반환한다(중복 제거 전).
    파일이 없으면 빈 리스트.
    """
    p = Path(path)
    if not p.exists():
        logger.warning("conditionResearch.md 없음: {p}", p=p)
        return []
    text = p.read_text(encoding="utf-8")
    rows = _extract_from_text(text, source="conditionRes")
    logger.info("conditionResearch.md: {r}건 추출", r=len(rows))
    return rows


def parse_upper_lower_price(path: Path | str) -> list[OrganizedStock]:
    """``reports/.../upperLowerPrice.md`` 파싱."""
    p = Path(path)
    if not p.exists():
        logger.warning("upperLowerPrice.md 없음: {p}", p=p)
        return []
    text = p.read_text(encoding="utf-8")
    rows = _extract_from_text(text, source="upperLower")
    logger.info("upperLowerPrice.md: {r}건 추출", r=len(rows))
    return rows
