"""Stage 0 PrefetchManifest 를 JSON 으로 저장한다.

저장 경로:
    ``reports/<YYYYMMDD>/prefetchManifest.json``

Stage 1~5 필터 진입점이 본 JSON 을 읽어 종목별 API 상태(ok/empty/error)를
즉시 판정한다 — 디스크의 .md 파일을 다시 파싱해 빈응답 패턴을 재검증할
필요가 없도록 하기 위한 인덱스 역할.

JSON 스키마 (예시)::

    {
      "date": "20260515",
      "started_at": "2026-05-15T09:00:00",
      "finished_at": "2026-05-15T09:14:23",
      "by_stock": {
        "005930": {
          "chart60":  "ok",
          "chart120": "ok",
          "chart240": "ok",
          "chartDay": "ok",
          "investor": "empty",
          "error_messages": {}
        },
        ...
      }
    }
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.researchFlow.models import PrefetchManifest, PrefetchStatus

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_FILENAME: Final[str] = "prefetchManifest.json"


def _status_to_dict(s: PrefetchStatus) -> dict[str, object]:
    return {
        "chart60": s.chart60,
        "chart120": s.chart120,
        "chart240": s.chart240,
        "chartDay": s.chartDay,
        "investor": s.investor,
        "finance": s.finance,
        "error_messages": dict(s.error_messages),
    }


def _status_from_dict(d: dict[str, object]) -> PrefetchStatus:
    return PrefetchStatus(
        chart60=str(d.get("chart60", "error")),  # type: ignore[arg-type]
        chart120=str(d.get("chart120", "error")),  # type: ignore[arg-type]
        chart240=str(d.get("chart240", "error")),  # type: ignore[arg-type]
        chartDay=str(d.get("chartDay", "error")),  # type: ignore[arg-type]
        investor=str(d.get("investor", "error")),  # type: ignore[arg-type]
        finance=str(d.get("finance", "error")),  # type: ignore[arg-type]
        error_messages=dict(d.get("error_messages", {}) or {}),
    )


def save_prefetch_manifest(
    manifest: PrefetchManifest,
    *,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """``reports/<manifest.date>/prefetchManifest.json`` 으로 저장하고 경로 반환.

    Args:
        manifest: Stage 0 가 채운 매니페스트.
        reports_root: 보고서 루트.

    Returns:
        저장된 파일 ``Path``.
    """
    out_dir = reports_root / manifest.date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _FILENAME

    payload: dict[str, object] = {
        "date": manifest.date,
        "started_at": (
            manifest.started_at.isoformat() if manifest.started_at else None
        ),
        "finished_at": (
            manifest.finished_at.isoformat() if manifest.finished_at else None
        ),
        "by_stock": {
            stk_cd: _status_to_dict(st)
            for stk_cd, st in manifest.by_stock.items()
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    out_path.write_text(text, encoding="utf-8")

    logger.info(
        "prefetchManifest.json 저장: {p} (종목 {n}건, {b} bytes)",
        p=out_path, n=len(manifest.by_stock), b=len(text.encode("utf-8")),
    )
    return out_path


def load_prefetch_manifest(
    date: str,
    *,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> PrefetchManifest:
    """``reports/<date>/prefetchManifest.json`` 을 읽어 :class:`PrefetchManifest`로 복원.

    Args:
        date: ``YYYYMMDD``.
        reports_root: 보고서 루트.

    Returns:
        복원된 매니페스트.

    Raises:
        FileNotFoundError: JSON 파일이 없을 때.
    """
    in_path = reports_root / date / _FILENAME
    text = in_path.read_text(encoding="utf-8")
    data = json.loads(text)

    by_stock = {
        stk_cd: _status_from_dict(st_dict)
        for stk_cd, st_dict in (data.get("by_stock") or {}).items()
    }
    started = data.get("started_at")
    finished = data.get("finished_at")
    return PrefetchManifest(
        date=str(data.get("date", date)),
        by_stock=by_stock,
        started_at=datetime.fromisoformat(started) if started else None,
        finished_at=datetime.fromisoformat(finished) if finished else None,
    )


__all__ = ["load_prefetch_manifest", "save_prefetch_manifest"]
