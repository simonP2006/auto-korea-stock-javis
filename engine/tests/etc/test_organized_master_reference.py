"""save_organized_company — masterReference.md 부가 생성 동작 검증.

organizedCompany.md 저장 직후 동일 디렉터리에 ``masterReference.md`` 가
없으면 빈(0바이트) 파일로 생성하고, 기존 파일이 있으면 보존하는지
확인한다 (과업 1-5 수선 반영). 네트워크 의존 없음.
"""

from __future__ import annotations

from pathlib import Path

from src.kiwoom.organizedCompany.models import OrganizedStock
from src.kiwoom.organizedCompany.saveReport import save_organized_company


def _stock(nm: str, rt: float) -> OrganizedStock:
    return OrganizedStock(stk_cd="", stk_nm=nm, flu_rt=rt, source="upperLower")


def test_master_reference_created_empty_with_stocks(tmp_path: Path) -> None:
    """종목이 있을 때 organizedCompany.md 와 함께 빈 masterReference.md 생성."""
    stocks = [_stock("삼성전자", 12.3), _stock("현대해상", 5.1)]

    org_path = save_organized_company(
        stocks, date="20260516", reports_root=tmp_path,
    )

    master_path = tmp_path / "20260516" / "masterReference.md"
    assert org_path.exists() and org_path.stat().st_size > 0
    assert master_path.exists()
    assert master_path.stat().st_size == 0
    assert master_path.read_text(encoding="utf-8") == ""


def test_master_reference_created_when_zero_stocks(tmp_path: Path) -> None:
    """종목 0건이면 organizedCompany.md 0바이트 + masterReference.md 0바이트."""
    org_path = save_organized_company(
        [], date="20260516", reports_root=tmp_path,
    )

    master_path = tmp_path / "20260516" / "masterReference.md"
    assert org_path.exists() and org_path.stat().st_size == 0
    assert master_path.exists()
    assert master_path.stat().st_size == 0


def test_existing_master_reference_preserved(tmp_path: Path) -> None:
    """기존에 내용이 있던 masterReference.md 는 보존된다 (과업 1-5 수선).

    구버전은 매 실행마다 0바이트로 덮어써서 같은 날 사용자가 수기
    기입한 종목 리스트가 재스캔 시 소실됐다. 이제 덮어쓰지 않는다.
    """
    out_dir = tmp_path / "20260516"
    out_dir.mkdir(parents=True, exist_ok=True)
    master_path = out_dir / "masterReference.md"
    original = "미리 들어있던 내용\n줄2\n"
    master_path.write_text(original, encoding="utf-8")
    assert master_path.stat().st_size > 0

    save_organized_company(
        [_stock("삼성전자", 1.0)], date="20260516", reports_root=tmp_path,
    )

    assert master_path.exists()
    assert master_path.read_text(encoding="utf-8") == original
