"""정리된 종목 리스트를 단순 텍스트로 저장한다.

저장 경로: ``reports/<YYYYMMDD>/organizedCompany.md``

포맷(사용자 명시):
    - 줄당 종목명 1개
    - 등락률 내림차순(facade에서 정렬됨 → 첫 줄이 가장 등락률 높은 종목)
    - 헤더/번호/등락률/구분자 모두 미표시
    - UTF-8, LF 줄바꿈, 마지막에 trailing newline 1개
    - 종목 0건이면 빈 파일(0바이트)

확장자는 ``.md`` 지만 실제 본문은 마크다운 표가 아니다(사용자 요청).

부가 동작: organizedCompany.md 저장 직후 동일 디렉터리에 항상
``masterReference.md`` 를 빈 파일(0바이트)로 생성한다. 기존 파일이
있어도 매번 빈 파일로 덮어쓴다(사용자 명시 — 항상 비어있어야 함).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.organizedCompany.models import OrganizedStock

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_FILENAME: Final[str] = "organizedCompany.md"
_MASTER_REFERENCE_FILENAME: Final[str] = "masterReference.md"


def render_plain_text(stocks: list[OrganizedStock]) -> str:
    """종목 리스트를 줄단위 텍스트로 변환.

    빈 리스트면 빈 문자열을 반환한다(파일 0바이트 저장용).
    """
    if not stocks:
        return ""
    return "\n".join(s.stk_nm for s in stocks) + "\n"


def save_organized_company(
    stocks: list[OrganizedStock],
    *,
    date: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """``reports/<YYYYMMDD>/organizedCompany.md`` 로 저장하고 경로 반환.

    Args:
        stocks: 정렬·중복제거가 끝난 종목 리스트.
        date: ``YYYYMMDD``. ``None`` 이면 오늘.
        reports_root: 보고서 루트.

    Returns:
        저장된 ``organizedCompany.md`` ``Path``.
    """
    yyyymmdd = date or datetime.now().strftime("%Y%m%d")
    out_dir = reports_root / yyyymmdd
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _FILENAME

    text = render_plain_text(stocks)
    out_path.write_text(text, encoding="utf-8")
    logger.info(
        "organizedCompany.md 저장: {p} ({n}건, {b} bytes)",
        p=out_path, n=len(stocks), b=len(text.encode("utf-8")),
    )

    # organizedCompany.md 생성 직후 동일 디렉터리에 빈 masterReference.md 를
    # 항상 생성한다. 기존 내용이 있어도 매번 0바이트로 덮어쓴다.
    master_path = out_dir / _MASTER_REFERENCE_FILENAME
    master_path.write_text("", encoding="utf-8")
    logger.info("masterReference.md 생성(빈 파일): {p}", p=master_path)

    return out_path
