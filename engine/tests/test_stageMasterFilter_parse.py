"""stageMasterFilter 입력 파싱 — masterReference.md 포맷 드리프트 회귀 테스트.

reports/<날짜>/masterReference.md 는 두 포맷이 공존한다:

- 구형 (예: ``reports/20260518``): 종목명만 — ``영림원소프트랩``
- 신형 (예: ``reports/20260611``): 종목명(코드) — ``삼현철강(017480)``

stageMasterFilter 는 :func:`Filter_condition_update._parse_entry` 와 동등한
규칙(끝의 ``(4~6자리코드)`` 분리, 없으면 이름만)으로 양 포맷을 모두 받아야
한다. 네트워크 의존 없음 — ``tmp_path`` 로 실제 reports 구조를 모사한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.kiwoom.itemFilter.stageMasterFilter import (
    _extract_master_features,
    _read_name_list,
    _split_name_code,
    _stock_dir,
    read_master_reference,
)

_DATE = "20260611"

# 실파일 reports/20260611/삼현철강(017480)/chartDay.md 포맷 모사 (1봉 축약).
_CHARTDAY_MD = """\
# 삼현철강(017480) 일봉 차트 + MA 분석

## 기본 정보
- **종목코드**: 017480 (API 호출 코드: `017480_AL`)
- **종목명**: 삼현철강
- **취득 시각**: 2026-06-11 21:09:51
- **일봉 행 수**: 1봉

## 최근 봉 스냅샷
- **최근 봉 일자**: 2026-06-11

## 일봉 시계열 (날짜 오름차순)

| 날짜 | 시가 | 고가 | 저가 | 종가 | 거래량 | MA10 | MA20 | MA60 | MA306 | MA612 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-06-11 | 4,975 | 5,090 | 4,955 | 5,050 | 105,070 | 4,905.00 | 4,894.50 | 4,785.25 | 4,580.28 | 4,693.76 |
"""


def _make_stock_dir(reports_root: Path, dirname: str) -> Path:
    sd = reports_root / _DATE / dirname
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "chartDay.md").write_text(_CHARTDAY_MD, encoding="utf-8")
    return sd


# ─────────────────────────────────────────────────────────────────────────────
# 이름·코드 분리 (_split_name_code) — Filter_condition_update._parse_entry 동등
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        # 구형: 이름만
        ("영림원소프트랩", ("영림원소프트랩", "")),
        # 신형: 이름(6자리코드)
        ("삼현철강(017480)", ("삼현철강", "017480")),
        # ETF형 4자리 코드 (reports/20260611 실폴더 "1Q K반도체TOP2+(0182)")
        ("1Q K반도체TOP2+(0182)", ("1Q K반도체TOP2+", "0182")),
        # 괄호가 코드가 아니면 전체가 이름
        ("씨아이에스(주)", ("씨아이에스(주)", "")),
        # 양끝 공백 허용
        ("  삼현철강(017480)  ", ("삼현철강", "017480")),
        ("  영림원소프트랩  ", ("영림원소프트랩", "")),
    ],
)
def test_split_name_code(line: str, expected: tuple[str, str]) -> None:
    assert _split_name_code(line) == expected


# ─────────────────────────────────────────────────────────────────────────────
# _read_name_list / read_master_reference — 양 포맷 + 공백·빈줄 혼합
# ─────────────────────────────────────────────────────────────────────────────


def test_read_name_list_old_format(tmp_path: Path) -> None:
    """구형 (reports/20260518 모사): 종목명만 줄단위."""
    p = tmp_path / "masterReference.md"
    p.write_text("영림원소프트랩\n케이아이엔엑스\n디지아이\n", encoding="utf-8")
    assert _read_name_list(p) == ["영림원소프트랩", "케이아이엔엑스", "디지아이"]


def test_read_name_list_new_format_strips_code(tmp_path: Path) -> None:
    """신형 (reports/20260611 모사): 종목명(코드) → 이름만 반환."""
    p = tmp_path / "masterReference.md"
    p.write_text(
        "삼현철강(017480)\n블루콤(033560)\n넥스턴앤롤코리아(089140)\n",
        encoding="utf-8",
    )
    assert _read_name_list(p) == ["삼현철강", "블루콤", "넥스턴앤롤코리아"]


def test_read_name_list_mixed_formats_blank_and_whitespace(tmp_path: Path) -> None:
    """구형·신형 혼합 + 빈 줄·공백 줄은 무시, 양끝 공백 제거."""
    p = tmp_path / "masterReference.md"
    p.write_text(
        "영림원소프트랩\n"
        "\n"
        "  삼현철강(017480)  \n"
        "   \n"
        "케이아이엔엑스\n"
        "블루콤(033560)\n",
        encoding="utf-8",
    )
    assert _read_name_list(p) == [
        "영림원소프트랩", "삼현철강", "케이아이엔엑스", "블루콤",
    ]


def test_read_name_list_missing_file(tmp_path: Path) -> None:
    assert _read_name_list(tmp_path / "없는파일.md") == []


def test_read_master_reference_new_format(tmp_path: Path) -> None:
    md = tmp_path / _DATE / "masterReference.md"
    md.parent.mkdir(parents=True)
    md.write_text("삼현철강(017480)\n블루콤(033560)\n", encoding="utf-8")
    assert read_master_reference(_DATE, tmp_path) == ["삼현철강", "블루콤"]


# ─────────────────────────────────────────────────────────────────────────────
# _stock_dir — 종목 폴더 해석 (폴더명은 항상 "<이름>(<코드>)")
# ─────────────────────────────────────────────────────────────────────────────


def test_stock_dir_resolves_bare_name(tmp_path: Path) -> None:
    """구형 입력(이름만) → 접두 매칭으로 폴더 해석 (기존 동작 유지)."""
    sd = _make_stock_dir(tmp_path, "삼현철강(017480)")
    assert _stock_dir(_DATE, "삼현철강", tmp_path) == sd


def test_stock_dir_resolves_name_with_code(tmp_path: Path) -> None:
    """신형 입력("이름(코드)") → 동일 폴더 해석 (드리프트 버그 회귀)."""
    sd = _make_stock_dir(tmp_path, "삼현철강(017480)")
    assert _stock_dir(_DATE, "삼현철강(017480)", tmp_path) == sd


def test_stock_dir_missing_returns_none(tmp_path: Path) -> None:
    _make_stock_dir(tmp_path, "삼현철강(017480)")
    assert _stock_dir(_DATE, "없는종목", tmp_path) is None
    assert _stock_dir(_DATE, "없는종목(000001)", tmp_path) is None


def test_stock_dir_no_date_dir(tmp_path: Path) -> None:
    assert _stock_dir("20991231", "삼현철강", tmp_path) is None


def test_stock_dir_prefix_does_not_cross_match(tmp_path: Path) -> None:
    """이름이 접두 관계인 두 종목(삼성전자/삼성전자우)을 혼동하지 않는다."""
    sd_a = _make_stock_dir(tmp_path, "삼성전자(005930)")
    sd_b = _make_stock_dir(tmp_path, "삼성전자우(005935)")
    assert _stock_dir(_DATE, "삼성전자", tmp_path) == sd_a
    assert _stock_dir(_DATE, "삼성전자우", tmp_path) == sd_b
    assert _stock_dir(_DATE, "삼성전자(005930)", tmp_path) == sd_a
    assert _stock_dir(_DATE, "삼성전자우(005935)", tmp_path) == sd_b


# ─────────────────────────────────────────────────────────────────────────────
# 통합: 신형 masterReference → 피처 추출까지 (학습 경로가 깨지지 않는지)
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_master_features_new_format_end_to_end(tmp_path: Path) -> None:
    """신형 masterReference.md 로도 master 피처 추출이 성공해야 한다.

    드리프트 버그: 신형 입력이면 _stock_dir 매칭 실패 →
    FileNotFoundError("master 종목 폴더 없음") 로 학습이 깨졌다.
    """
    _make_stock_dir(tmp_path, "삼현철강(017480)")
    md = tmp_path / _DATE / "masterReference.md"
    md.write_text("삼현철강(017480)\n", encoding="utf-8")

    masters = read_master_reference(_DATE, tmp_path)
    feats = _extract_master_features(_DATE, masters, tmp_path)

    assert len(feats) == 1
    f = feats[0]
    assert f["__name__"] == "삼현철강"
    # 실수치 검증 (chartDay.md 마지막 봉: close=5050, MA20=4894.50)
    assert f["close_over_ma20"] == pytest.approx(
        (5050 / 4894.50 - 1) * 100.0, abs=1e-9,
    )
    assert f["close_over_ma10"] == pytest.approx(
        (5050 / 4905.00 - 1) * 100.0, abs=1e-9,
    )
    assert f["ma20_over_ma60"] == pytest.approx(
        (4894.50 / 4785.25 - 1) * 100.0, abs=1e-9,
    )
    assert f["close_over_ma306"] == pytest.approx(
        (5050 / 4580.28 - 1) * 100.0, abs=1e-9,
    )


def test_extract_master_features_old_format_end_to_end(tmp_path: Path) -> None:
    """구형 masterReference.md 경로는 기존대로 동작 (회귀 방지)."""
    _make_stock_dir(tmp_path, "삼현철강(017480)")
    md = tmp_path / _DATE / "masterReference.md"
    md.write_text("삼현철강\n", encoding="utf-8")

    masters = read_master_reference(_DATE, tmp_path)
    feats = _extract_master_features(_DATE, masters, tmp_path)
    assert len(feats) == 1
    assert feats[0]["__name__"] == "삼현철강"
