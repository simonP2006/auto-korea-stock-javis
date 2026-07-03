"""전문가 픽 일괄 backfill 드라이버 — 이름해석·라벨기입·대사보고.

주인님이 과거 날짜별로 제공한 전문가 종목 픽(종목명 목록)을 입력받아,
날짜별로 다음을 수행한다:

    1. **이름 해석** — 종목명 → 종목코드. 2-tier: (a) 디스크 유니언 맵
       (모든 ``reports/*`` + ``reports_backfill/*`` 의 upperLowerPrice.md /
       conditionResearch.md 스캔), (b) ka10099 전체 종목 마스터 fallback.
       해석 실패 이름은 **절대 조용히 버리지 않고** 크게 보고한다.
    2. **수집·필터** — 해석된 종목을 :func:`backfill_prefetch_all` 로 과거
       기준일 수집(조회전용) 후 ``finance_policy="skip_na"`` 필터 + 저장.
    3. **라벨 기입** — ``<root>/<date>/masterReference.md`` 에 주인님 이름 원문
       그대로, 미해석 이름이 있으면 ``masterReference.UNRESOLVED.txt`` 병기.
    4. **대사 보고** — 날짜별 요청/해석/수집/통과/미해석 요약 표.

입력 픽 파일 형식::

    # 20260106
    에피소드컴퍼니
    케이엠더블유
    ...(한 줄에 종목명 1개)

    # 20260107
    ...

섹션은 빈 줄 및/또는 ``---`` 줄로 구분한다. 같은 날짜 섹션이 여러 번 나오면
병합한다. 이름은 양끝 공백을 제거하고, 빈 줄은 무시한다.

배치 회복력: 한 날짜가 실패(BackfillError: 비거래일·보존범위 밖 등)해도 로그를
남기고 다음 날짜로 계속한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Final

from loguru import logger

from src.kiwoom.instrumentList import get_instrument_name_to_code
from src.kiwoom.researchFlow.backfill import BackfillError, backfill_prefetch_all
from src.kiwoom.researchFlow.backfill_report import (
    count_all_data_ok,
    save_backfill_results,
)
from src.kiwoom.researchFlow.facade import filter_today
from src.kiwoom.researchFlow.models import ResearchCandidate
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map

_DEFAULT_BACKFILL_ROOT: Final[Path] = Path("reports_backfill")
_DEFAULT_UNIVERSE_ROOT: Final[Path] = Path("reports")
_MASTER_REFERENCE: Final[str] = "masterReference.md"
_UNRESOLVED_SIDECAR: Final[str] = "masterReference.UNRESOLVED.txt"

_DATE_HEADER: Final[re.Pattern[str]] = re.compile(r"^#\s*(\d{8})\b")
_DATE_DIR: Final[re.Pattern[str]] = re.compile(r"\d{8}")

# 종목명 → 코드 fallback fetcher 시그니처(0-인자 async).
InstrumentFetcher = Callable[[], Awaitable[dict[str, str]]]


class ExpertBackfillError(RuntimeError):
    """픽 파싱·배치 진행 불가 오류(한국어 메시지)."""


# ──────────────────────────────────────────────────────────────────────
# 픽 파일 파서
# ──────────────────────────────────────────────────────────────────────


def parse_picks_file(path: Path | str) -> list[tuple[str, list[str]]]:
    """전문가 픽 텍스트를 ``[(date, [name, ...]), ...]`` 로 파싱.

    - ``# YYYYMMDD`` 헤더로 섹션 시작, 이후 줄당 종목명 1개.
    - 빈 줄과 ``---``(전부 하이픈) 줄은 구분자로 무시.
    - 같은 날짜가 여러 번 등장하면 **병합**(뒤 섹션 이름을 이어붙임).
    - 이름은 양끝 공백 strip. 첫 등장 순서 보존.

    Raises:
        ExpertBackfillError: 파일 부재 / 날짜 헤더 형식 오류(8자리 아님) /
            날짜 헤더 이전에 종목명 등장 / 유효 섹션 0건.
    """
    p = Path(path)
    if not p.exists():
        raise ExpertBackfillError(f"픽 파일 없음: {p}")

    sections: dict[str, list[str]] = {}
    current: str | None = None
    for lineno, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped:
            continue
        if set(stripped) == {"-"}:  # '---' 등 하이픈만 있는 구분선
            continue
        if stripped.startswith("#"):
            m = _DATE_HEADER.match(stripped)
            if not m:
                raise ExpertBackfillError(
                    f"{p}:{lineno} 날짜 헤더 형식 오류(YYYYMMDD 8자리 필요): "
                    f"{stripped!r}"
                )
            current = m.group(1)
            sections.setdefault(current, [])  # 중복 날짜 섹션 병합
            continue
        if current is None:
            raise ExpertBackfillError(
                f"{p}:{lineno} 날짜 헤더 이전에 종목명 등장: {stripped!r}"
            )
        sections[current].append(stripped)

    if not sections:
        raise ExpertBackfillError(f"픽 파일에 유효한 날짜 섹션이 없습니다: {p}")
    return list(sections.items())


# ──────────────────────────────────────────────────────────────────────
# 이름 → 코드 해석
# ──────────────────────────────────────────────────────────────────────


def build_disk_name_to_code_map(roots: list[Path]) -> dict[str, str]:
    """여러 리포트 루트의 모든 ``<YYYYMMDD>/`` 폴더에서 ``{종목명: 코드}`` 유니언.

    각 날짜 폴더에 대해 기존 :func:`build_name_to_code_map`
    (upperLowerPrice.md + conditionResearch.md, upper 우선, ``_AL`` 접미사 제거)
    를 재사용한다. **최근 날짜 우선**(내림차순 순회, 이름 충돌 시 first-wins)로
    종목코드 재사용 시 더 최근 매핑을 채택한다.

    Args:
        roots: 스캔할 리포트 루트 리스트(예: ``reports/``, ``reports_backfill/``).
            같은 경로가 중복돼도 실경로 기준으로 1회만 스캔한다.
    """
    seen_dirs: set[Path] = set()
    date_dirs: list[Path] = []
    for root in roots:
        rp = Path(root)
        if not rp.exists():
            continue
        for child in rp.iterdir():
            if child.is_dir() and _DATE_DIR.fullmatch(child.name):
                real = child.resolve()
                if real in seen_dirs:
                    continue
                seen_dirs.add(real)
                date_dirs.append(child)

    date_dirs.sort(key=lambda d: d.name, reverse=True)  # 최근 우선

    out: dict[str, str] = {}
    for d in date_dirs:
        for name, code in build_name_to_code_map(d).items():
            out.setdefault(name, code)
    logger.info(
        "디스크 유니언 name→code 맵: 날짜폴더 {n}개 → 고유 이름 {m}개",
        n=len(date_dirs), m=len(out),
    )
    return out


class NameResolver:
    """종목명 → 종목코드 2-tier 해석기.

    tier (a) 디스크 유니언 맵(``disk_map``) 우선, 실패 시 tier (b)
    ``instrument_fetcher``(ka10099 전체 마스터)를 **한 번만** 호출해 캐시.
    ``instrument_fetcher`` 가 ``None`` 이면 tier (b) 를 건너뛴다(dry-run·오프라인).
    """

    def __init__(
        self,
        disk_map: dict[str, str],
        *,
        instrument_fetcher: InstrumentFetcher | None = None,
    ) -> None:
        self._disk = dict(disk_map)
        self._fetcher = instrument_fetcher
        self._instrument_map: dict[str, str] | None = None
        self.instrument_fetched = False

    async def resolve(self, name: str) -> str | None:
        """이름을 코드로 해석. 실패 시 ``None`` (조용히 버리지 않음 — 호출측 보고)."""
        key = name.strip()
        if not key:
            return None
        code = self._disk.get(key)
        if code:
            return code
        if self._fetcher is None:
            return None
        if self._instrument_map is None:
            self._instrument_map = await self._fetcher()
            self.instrument_fetched = True
            logger.info(
                "ka10099 fallback 마스터 적재: {n}개 이름", n=len(self._instrument_map),
            )
        return self._instrument_map.get(key)


def _build_default_resolver(
    reports_root: Path, *, dry_run: bool
) -> NameResolver:
    """디스크 유니언 맵 + (dry-run 아니면) ka10099 fallback 으로 기본 해석기 구성."""
    disk_map = build_disk_name_to_code_map(
        [_DEFAULT_UNIVERSE_ROOT, reports_root]
    )
    fetcher: InstrumentFetcher | None = (
        None if dry_run else get_instrument_name_to_code
    )
    return NameResolver(disk_map, instrument_fetcher=fetcher)


# ──────────────────────────────────────────────────────────────────────
# 날짜별 처리 + 배치
# ──────────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class DateResult:
    """한 날짜 섹션의 처리 결과.

    Attributes:
        date: ``YYYYMMDD``.
        requested: 주인님 이름 원문(중복 날짜 섹션 병합, 순서 보존).
        resolved: 해석 성공 ``(이름, 코드)`` 쌍(요청 이름 1개당 최대 1개).
        unresolved: 해석 실패 이름.
        collected_ok: 5개 데이터 API 전부 ok 종목 수. 미수집(dry-run/실패/
            해석 0건)이면 ``None``.
        passed: 필터 최종 통과 종목 수. 미필터면 ``None``.
        error: 수집 단계 오류 메시지(있으면).
    """

    date: str
    requested: list[str]
    resolved: list[tuple[str, str]] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    collected_ok: int | None = None
    passed: int | None = None
    error: str = ""


def _dedup_candidates(
    resolved: list[tuple[str, str]]
) -> list[ResearchCandidate]:
    """``(이름, 코드)`` 쌍을 코드 기준 dedup 한 ResearchCandidate 리스트(첫 이름 유지)."""
    seen: set[str] = set()
    out: list[ResearchCandidate] = []
    for name, code in resolved:
        if code in seen:
            continue
        seen.add(code)
        out.append(ResearchCandidate(stk_nm=name, stk_cd=code))
    return out


def _write_lines(path: Path, lines: list[str]) -> None:
    """이름 목록을 줄단위 텍스트로 저장(organizedCompany/masterReference 포맷)."""
    text = "\n".join(lines) + "\n" if lines else ""
    path.write_text(text, encoding="utf-8")


async def _process_date(
    date: str,
    requested: list[str],
    *,
    reports_root: Path,
    resolver: NameResolver,
    dry_run: bool,
) -> DateResult:
    """한 날짜 섹션을 해석→(라벨기입)→수집→필터. 실패해도 예외를 삼켜 DateResult 반환."""
    resolved: list[tuple[str, str]] = []
    unresolved: list[str] = []
    for name in requested:
        code = await resolver.resolve(name)
        if code:
            resolved.append((name, code))
        else:
            unresolved.append(name)

    dr = DateResult(
        date=date,
        requested=list(requested),
        resolved=resolved,
        unresolved=unresolved,
    )
    if unresolved:
        logger.warning(
            "[expert-backfill] {d} 미해석 {u}개: {names}",
            d=date, u=len(unresolved), names=", ".join(unresolved),
        )

    if dry_run:
        # parse+resolve+report 만 — 네트워크·파일쓰기 없음.
        return dr

    # 라벨 기입 — 주인님 이름 원문 verbatim(수집 성패와 무관하게 항상).
    date_dir = reports_root / date
    date_dir.mkdir(parents=True, exist_ok=True)
    if requested:
        _write_lines(date_dir / _MASTER_REFERENCE, requested)
    if unresolved:
        _write_lines(date_dir / _UNRESOLVED_SIDECAR, unresolved)

    candidates = _dedup_candidates(resolved)
    if not candidates:
        return dr  # 해석된 종목 0건 — 수집 스킵(미해석은 이미 보고/기록).

    try:
        manifest = await backfill_prefetch_all(
            date, stocks=candidates, reports_root=reports_root,
        )
    except BackfillError as exc:
        dr.error = str(exc)
        logger.error("[expert-backfill] {d} 수집 실패(계속): {e}", d=date, e=exc)
        return dr

    dr.collected_ok = count_all_data_ok(manifest.by_stock)
    code_map = {name: code for name, code in resolved}
    results = await filter_today(
        date,
        reports_root=reports_root,
        finance_policy="skip_na",
        code_map=code_map,
    )
    save_backfill_results(results, date=date, reports_root=reports_root)
    dr.passed = sum(1 for r in results if r.final_selected)
    return dr


async def run_expert_batch(
    picks_file: Path | str,
    *,
    reports_root: Path = _DEFAULT_BACKFILL_ROOT,
    only_date: str | None = None,
    dry_run: bool = False,
    resolver: NameResolver | None = None,
) -> list[DateResult]:
    """픽 파일을 파싱해 날짜별로 처리하고 :class:`DateResult` 리스트 반환.

    Args:
        picks_file: 전문가 픽 텍스트 경로.
        reports_root: 출력 루트(기본 ``reports_backfill/``).
        only_date: 지정 시 그 날짜 섹션만 처리.
        dry_run: True 면 parse+resolve+report 만(네트워크·파일쓰기 0).
        resolver: 주입용 :class:`NameResolver` (테스트/모킹용). ``None`` 이면
            디스크 유니언 맵 + (dry-run 아니면) ka10099 fallback 으로 구성.

    Raises:
        ExpertBackfillError: 파싱 실패 / ``only_date`` 섹션 부재.
    """
    sections = parse_picks_file(picks_file)
    if only_date is not None:
        sections = [(d, names) for d, names in sections if d == only_date]
        if not sections:
            raise ExpertBackfillError(
                f"--only-date {only_date} 에 해당하는 섹션이 픽 파일에 없습니다"
            )

    if resolver is None:
        resolver = _build_default_resolver(reports_root, dry_run=dry_run)

    results: list[DateResult] = []
    for date, names in sections:
        dr = await _process_date(
            date, names,
            reports_root=reports_root, resolver=resolver, dry_run=dry_run,
        )
        results.append(dr)
        logger.info(
            "[expert-backfill] {d} 요청={q} 해석={r} 미해석={u} 수집ok={c} 통과={p}{e}",
            d=date, q=len(dr.requested), r=len(dr.resolved),
            u=len(dr.unresolved), c=dr.collected_ok, p=dr.passed,
            e=f" ERROR={dr.error}" if dr.error else "",
        )
    return results


# ──────────────────────────────────────────────────────────────────────
# 요약 · 종료코드
# ──────────────────────────────────────────────────────────────────────


def batch_exit_code(results: list[DateResult]) -> int:
    """미해석 이름이 남았거나 수집 실패한 날짜가 하나라도 있으면 1, 아니면 0."""
    return 1 if any(r.unresolved or r.error for r in results) else 0


def render_summary(results: list[DateResult]) -> str:
    """날짜별 대사 요약 표: ``날짜 | 요청 | 해석 | 수집ok | 필터통과 | 미해석명``."""
    lines = [
        "날짜 | 요청 | 해석 | 수집ok | 필터통과 | 미해석명",
        "---|---:|---:|---:|---:|---",
    ]
    tot_req = tot_res = tot_unres = 0
    for r in results:
        tot_req += len(r.requested)
        tot_res += len(r.resolved)
        tot_unres += len(r.unresolved)
        note = ", ".join(r.unresolved)
        if r.error:
            note = (note + " | " if note else "") + f"⚠ 수집실패: {r.error}"
        lines.append(
            "{d} | {q} | {res} | {c} | {p} | {u}".format(
                d=r.date,
                q=len(r.requested),
                res=len(r.resolved),
                c=r.collected_ok if r.collected_ok is not None else "-",
                p=r.passed if r.passed is not None else "-",
                u=note,
            )
        )
    lines.append(
        f"합계 | {tot_req} | {tot_res} | - | - | 미해석 {tot_unres}건"
    )
    return "\n".join(lines)


__all__ = [
    "DateResult",
    "ExpertBackfillError",
    "NameResolver",
    "batch_exit_code",
    "build_disk_name_to_code_map",
    "parse_picks_file",
    "render_summary",
    "run_expert_batch",
]
