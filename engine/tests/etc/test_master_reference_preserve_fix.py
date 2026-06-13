"""과업 1-5 — masterReference.md 0바이트 덮어쓰기 함정 수선 회귀 테스트.

확정 버그: save_organized_company 가 매 실행마다 masterReference.md 를
0바이트로 새로 써서, 같은 날 사용자가 수기 기입한 종목 리스트가
재스캔 시 소실된다 (plain_text.py 73-75행 부근).

수선 후 계약(3건):
    ① 파일 없으면 → 0바이트 생성 (기존 동작 보존)
    ② 파일이 존재하고 내용 있으면 → 보존 (덮어쓰기 금지)
    ③ 빈 파일이 이미 존재하면 → 그대로 (재실행 무해)

네트워크 의존 없음.
"""

from __future__ import annotations

from pathlib import Path

from src.kiwoom.organizedCompany.models import OrganizedStock
from src.kiwoom.organizedCompany.saveReport import save_organized_company

_DATE = "20260613"


def _stock(nm: str, rt: float) -> OrganizedStock:
    return OrganizedStock(stk_cd="", stk_nm=nm, flu_rt=rt, source="upperLower")


def test_creates_empty_master_reference_when_absent(tmp_path: Path) -> None:
    """① 파일 없으면 0바이트 masterReference.md 생성 (기존 동작 보존)."""
    master_path = tmp_path / _DATE / "masterReference.md"
    assert not master_path.exists()

    save_organized_company(
        [_stock("삼성전자", 12.3)], date=_DATE, reports_root=tmp_path,
    )

    assert master_path.exists()
    assert master_path.stat().st_size == 0


def test_preserves_existing_master_reference_with_content(tmp_path: Path) -> None:
    """② 내용 있는 masterReference.md 는 재스캔에도 보존 (덮어쓰기 금지).

    같은 날 사용자가 수기 기입한 종목 리스트가 소실되면 안 된다.
    """
    out_dir = tmp_path / _DATE
    out_dir.mkdir(parents=True, exist_ok=True)
    master_path = out_dir / "masterReference.md"
    manual_content = "사용자 수기 기입 종목\n삼성전자\n현대해상\n"
    master_path.write_text(manual_content, encoding="utf-8")

    save_organized_company(
        [_stock("LG에너지솔루션", 3.2)], date=_DATE, reports_root=tmp_path,
    )

    assert master_path.exists()
    assert master_path.read_text(encoding="utf-8") == manual_content


def test_existing_empty_master_reference_is_harmless(tmp_path: Path) -> None:
    """③ 빈 masterReference.md 가 이미 있으면 그대로 (재실행 무해)."""
    out_dir = tmp_path / _DATE
    out_dir.mkdir(parents=True, exist_ok=True)
    master_path = out_dir / "masterReference.md"
    master_path.write_text("", encoding="utf-8")

    save_organized_company(
        [_stock("삼성전자", 1.0)], date=_DATE, reports_root=tmp_path,
    )

    assert master_path.exists()
    assert master_path.stat().st_size == 0
    assert master_path.read_text(encoding="utf-8") == ""


def test_organized_company_still_written_when_master_preserved(
    tmp_path: Path,
) -> None:
    """보존 분기에서도 organizedCompany.md 쓰기 경로는 불변."""
    out_dir = tmp_path / _DATE
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "masterReference.md").write_text("수기 메모\n", encoding="utf-8")

    org_path = save_organized_company(
        [_stock("현대해상", 5.1), _stock("삼성전자", 2.0)],
        date=_DATE,
        reports_root=tmp_path,
    )

    assert org_path == out_dir / "organizedCompany.md"
    assert org_path.read_text(encoding="utf-8") == "현대해상\n삼성전자\n"
