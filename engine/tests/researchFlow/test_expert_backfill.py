"""전문가 픽 일괄 backfill 드라이버 검증 (네트워크 없음, mock 전용).

- 픽 파서: 섹션·빈줄·--- 구분·중복날짜 병합·이름 공백·오류 케이스.
- NameResolver: 디스크 tier 우선 → ka10099 fallback(1회 캐시) → 미해석 None(날조 금지).
- 디스크 유니언 맵: reports/* upperLowerPrice.md 파싱 + _AL 접미사 제거.
- masterReference 원문 기입 + UNRESOLVED 사이드카.
- 배치 회복력: 한 날짜 실패해도 다음 날짜 계속.
- dry-run: 네트워크·파일쓰기 0.
- 요약 표 + 종료코드.
- ka10099 클라이언트: MockTransport 로 페이징·양시장·코드정규화.
"""

from __future__ import annotations

import json

import httpx
import pytest

import src.kiwoom.researchFlow.expert_backfill as eb
from src.kiwoom.instrumentList import (
    InstrumentListClient,
    get_instrument_name_to_code,
)
from src.kiwoom.researchFlow.backfill import BackfillError
from src.kiwoom.researchFlow.expert_backfill import (
    DateResult,
    ExpertBackfillError,
    NameResolver,
    batch_exit_code,
    build_disk_name_to_code_map,
    parse_picks_file,
    render_summary,
    run_expert_batch,
)
from src.kiwoom.researchFlow.models import PrefetchManifest, PrefetchStatus


# ──────────────────────────────────────────────────────────────────────
# 픽 파서
# ──────────────────────────────────────────────────────────────────────


def test_parse_sections_blank_and_dash_separators(tmp_path) -> None:
    p = tmp_path / "picks.txt"
    p.write_text(
        "# 20260106\n"
        "에피소드컴퍼니\n"
        "케이엠더블유\n"
        "\n"
        "---\n"
        "# 20260107\n"
        "  대원강업  \n"  # 양끝 공백 → strip
        "삼성전자\n",
        encoding="utf-8",
    )
    assert parse_picks_file(p) == [
        ("20260106", ["에피소드컴퍼니", "케이엠더블유"]),
        ("20260107", ["대원강업", "삼성전자"]),
    ]


def test_parse_duplicate_date_sections_merge(tmp_path) -> None:
    p = tmp_path / "picks.txt"
    p.write_text(
        "# 20260106\nA\n\n# 20260107\nB\n\n# 20260106\nC\n", encoding="utf-8",
    )
    assert parse_picks_file(p) == [
        ("20260106", ["A", "C"]),  # 병합, 첫 등장 순서
        ("20260107", ["B"]),
    ]


def test_parse_header_without_space(tmp_path) -> None:
    p = tmp_path / "picks.txt"
    p.write_text("#20260106\nA\n", encoding="utf-8")
    assert parse_picks_file(p) == [("20260106", ["A"])]


def test_parse_name_before_header_raises(tmp_path) -> None:
    p = tmp_path / "picks.txt"
    p.write_text("삼성전자\n# 20260106\nA\n", encoding="utf-8")
    with pytest.raises(ExpertBackfillError, match="날짜 헤더 이전"):
        parse_picks_file(p)


def test_parse_bad_header_raises(tmp_path) -> None:
    p = tmp_path / "picks.txt"
    p.write_text("# 2026\nA\n", encoding="utf-8")
    with pytest.raises(ExpertBackfillError, match="날짜 헤더 형식 오류"):
        parse_picks_file(p)


def test_parse_missing_file_raises(tmp_path) -> None:
    with pytest.raises(ExpertBackfillError, match="픽 파일 없음"):
        parse_picks_file(tmp_path / "nope.txt")


# ──────────────────────────────────────────────────────────────────────
# NameResolver
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolver_disk_tier_wins_no_fetch() -> None:
    calls: list[int] = []

    async def _fetcher() -> dict[str, str]:
        calls.append(1)
        return {"삼성전자": "999999"}  # 사용되면 잘못된 코드

    r = NameResolver({"삼성전자": "005930"}, instrument_fetcher=_fetcher)
    assert await r.resolve("삼성전자") == "005930"
    assert calls == []  # 디스크 히트 → fallback 미호출


@pytest.mark.asyncio
async def test_resolver_fallback_tier_fetched_once() -> None:
    calls: list[int] = []

    async def _fetcher() -> dict[str, str]:
        calls.append(1)
        return {"케이엠더블유": "032500"}

    r = NameResolver({}, instrument_fetcher=_fetcher)
    assert await r.resolve("케이엠더블유") == "032500"
    assert await r.resolve("케이엠더블유") == "032500"  # 캐시
    assert len(calls) == 1
    assert r.instrument_fetched is True


@pytest.mark.asyncio
async def test_resolver_unresolved_returns_none_never_fabricates() -> None:
    async def _fetcher() -> dict[str, str]:
        return {"삼성전자": "005930"}

    r = NameResolver({}, instrument_fetcher=_fetcher)
    assert await r.resolve("대원강원") is None  # 오타 — 어느 tier 에도 없음


@pytest.mark.asyncio
async def test_resolver_no_fetcher_skips_fallback() -> None:
    r = NameResolver({"A": "000001"}, instrument_fetcher=None)
    assert await r.resolve("A") == "000001"
    assert await r.resolve("B") is None
    assert r.instrument_fetched is False


# ──────────────────────────────────────────────────────────────────────
# 디스크 유니언 맵
# ──────────────────────────────────────────────────────────────────────


def test_build_disk_union_map_strips_al_suffix(tmp_path) -> None:
    reports = tmp_path / "reports"
    d = reports / "20260106"
    d.mkdir(parents=True)
    (d / "upperLowerPrice.md").write_text(
        "| # | 종목코드 | 종목명 | 등락률 |\n"
        "|---|---|---|---|\n"
        "| 1 | 032500_AL | 케이엠더블유 | +5.0 |\n",
        encoding="utf-8",
    )
    assert build_disk_name_to_code_map([reports]) == {"케이엠더블유": "032500"}


# ──────────────────────────────────────────────────────────────────────
# 배치 — 라벨 기입 · 회복력 · dry-run
# ──────────────────────────────────────────────────────────────────────


def _fake_manifest(date: str, stocks) -> PrefetchManifest:
    m = PrefetchManifest(date=date)
    for c in stocks:
        m.by_stock[c.stk_cd] = PrefetchStatus(
            chart60="ok", chart120="ok", chart240="ok",
            chartDay="ok", investor="ok", finance="skipped",
        )
    return m


def _patch_collection(monkeypatch, *, fail_dates=()) -> list[str]:
    """backfill/filter/save 를 가짜로 대체. 호출된 날짜 리스트를 반환(누적)."""
    called: list[str] = []

    async def _fake_backfill(date, *, stocks=None, reports_root=None, allow_nonbusiness=False):
        called.append(date)
        if date in fail_dates:
            raise BackfillError(f"{date} 비거래일(테스트)")
        return _fake_manifest(date, stocks or [])

    async def _fake_filter(date, *, reports_root=None, finance_policy="require", code_map=None):
        return []

    monkeypatch.setattr(eb, "backfill_prefetch_all", _fake_backfill)
    monkeypatch.setattr(eb, "filter_today", _fake_filter)
    monkeypatch.setattr(eb, "save_backfill_results", lambda *a, **k: None)
    return called


@pytest.mark.asyncio
async def test_masterreference_verbatim_and_unresolved_sidecar(
    monkeypatch, tmp_path
) -> None:
    _patch_collection(monkeypatch)
    root = tmp_path / "bf"
    resolver = NameResolver(
        {"에피소드컴퍼니": "419530"}, instrument_fetcher=None,
    )
    picks = tmp_path / "picks.txt"
    picks.write_text("# 20260106\n에피소드컴퍼니\n대원강원\n", encoding="utf-8")

    results = await run_expert_batch(picks, reports_root=root, resolver=resolver)
    dr = results[0]

    assert dr.requested == ["에피소드컴퍼니", "대원강원"]
    assert dr.resolved == [("에피소드컴퍼니", "419530")]
    assert dr.unresolved == ["대원강원"]
    assert dr.collected_ok == 1

    # masterReference.md = 주인님 이름 원문 verbatim(해석 성패 무관 전부).
    mr = (root / "20260106" / "masterReference.md").read_text(encoding="utf-8")
    assert mr == "에피소드컴퍼니\n대원강원\n"
    # 미해석 사이드카 = 오타 이름만.
    un = (root / "20260106" / "masterReference.UNRESOLVED.txt").read_text(
        encoding="utf-8",
    )
    assert un == "대원강원\n"


@pytest.mark.asyncio
async def test_no_unresolved_writes_no_sidecar(monkeypatch, tmp_path) -> None:
    _patch_collection(monkeypatch)
    root = tmp_path / "bf"
    resolver = NameResolver({"삼성전자": "005930"}, instrument_fetcher=None)
    picks = tmp_path / "picks.txt"
    picks.write_text("# 20260106\n삼성전자\n", encoding="utf-8")

    results = await run_expert_batch(picks, reports_root=root, resolver=resolver)
    assert results[0].unresolved == []
    assert (root / "20260106" / "masterReference.md").exists()
    assert not (root / "20260106" / "masterReference.UNRESOLVED.txt").exists()


@pytest.mark.asyncio
async def test_batch_continues_past_failing_date(monkeypatch, tmp_path) -> None:
    called = _patch_collection(monkeypatch, fail_dates={"20260106"})
    root = tmp_path / "bf"
    resolver = NameResolver(
        {"A": "000001", "B": "000002"}, instrument_fetcher=None,
    )
    picks = tmp_path / "picks.txt"
    picks.write_text("# 20260106\nA\n\n# 20260107\nB\n", encoding="utf-8")

    results = await run_expert_batch(picks, reports_root=root, resolver=resolver)

    assert len(results) == 2
    assert results[0].date == "20260106" and results[0].error != ""
    assert results[1].date == "20260107" and results[1].error == ""
    assert results[1].collected_ok == 1
    assert called == ["20260106", "20260107"]  # 실패 후에도 계속
    assert batch_exit_code(results) == 1  # 실패 → exit 1


@pytest.mark.asyncio
async def test_dry_run_no_writes_no_collection(monkeypatch, tmp_path) -> None:
    async def _boom_backfill(*a, **k):
        raise AssertionError("dry-run 에서 backfill 호출됨")

    async def _boom_filter(*a, **k):
        raise AssertionError("dry-run 에서 filter 호출됨")

    monkeypatch.setattr(eb, "backfill_prefetch_all", _boom_backfill)
    monkeypatch.setattr(eb, "filter_today", _boom_filter)

    root = tmp_path / "bf"
    resolver = NameResolver({"삼성전자": "005930"}, instrument_fetcher=None)
    picks = tmp_path / "picks.txt"
    picks.write_text("# 20260106\n삼성전자\n미해석종목\n", encoding="utf-8")

    results = await run_expert_batch(
        picks, reports_root=root, dry_run=True, resolver=resolver,
    )
    dr = results[0]
    assert dr.resolved == [("삼성전자", "005930")]
    assert dr.unresolved == ["미해석종목"]
    assert dr.collected_ok is None and dr.passed is None
    # 파일 쓰기 0 — 출력 루트가 아예 생성되지 않았거나 비어 있어야.
    assert (not root.exists()) or (list(root.rglob("*")) == [])
    assert batch_exit_code(results) == 1  # 미해석 잔존


def test_default_resolver_dryrun_disables_fetcher(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(eb, "build_disk_name_to_code_map", lambda roots: {})
    r = eb._build_default_resolver(tmp_path / "bf", dry_run=True)
    assert r._fetcher is None


def test_default_resolver_live_enables_fetcher(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(eb, "build_disk_name_to_code_map", lambda roots: {})
    r = eb._build_default_resolver(tmp_path / "bf", dry_run=False)
    assert r._fetcher is not None


@pytest.mark.asyncio
async def test_only_date_filters_and_missing_raises(monkeypatch, tmp_path) -> None:
    _patch_collection(monkeypatch)
    root = tmp_path / "bf"
    resolver = NameResolver({"A": "000001", "B": "000002"}, instrument_fetcher=None)
    picks = tmp_path / "picks.txt"
    picks.write_text("# 20260106\nA\n\n# 20260107\nB\n", encoding="utf-8")

    results = await run_expert_batch(
        picks, reports_root=root, only_date="20260107", resolver=resolver,
    )
    assert [r.date for r in results] == ["20260107"]

    with pytest.raises(ExpertBackfillError, match="해당하는 섹션이"):
        await run_expert_batch(
            picks, reports_root=root, only_date="20991231", resolver=resolver,
        )


# ──────────────────────────────────────────────────────────────────────
# 요약 · 종료코드
# ──────────────────────────────────────────────────────────────────────


def test_render_summary_columns_and_exit_code() -> None:
    results = [
        DateResult(
            date="20260106", requested=["A", "B", "C"],
            resolved=[("A", "1"), ("B", "2")], unresolved=["C"],
            collected_ok=2, passed=1,
        ),
        DateResult(
            date="20260107", requested=["D"], resolved=[("D", "4")],
            unresolved=[], collected_ok=1, passed=1,
        ),
        DateResult(
            date="20260108", requested=["E"], resolved=[("E", "5")],
            unresolved=[], error="비거래일",
        ),
    ]
    s = render_summary(results)
    assert "날짜 | 요청 | 해석 | 수집ok | 필터통과 | 미해석명" in s
    assert "20260106 | 3 | 2 | 2 | 1 | C" in s
    assert "20260107 | 1 | 1 | 1 | 1 |" in s
    assert "20260108 | 1 | 1 | - | - |" in s and "비거래일" in s
    assert "합계 | 5 | 4 | - | - | 미해석 1건" in s

    assert batch_exit_code(results) == 1
    assert batch_exit_code(results[1:2]) == 0  # 미해석·오류 없는 날짜만


# ──────────────────────────────────────────────────────────────────────
# ka10099 클라이언트 (MockTransport — 라이브 없음)
# ──────────────────────────────────────────────────────────────────────


class _FakeAuth:
    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        return "test-token"

    def invalidate(self) -> None:
        pass


class _FakeConfig:
    @property
    def base_url(self) -> str:
        return "https://api.example"


@pytest.mark.asyncio
async def test_ka10099_client_paginates_both_markets(monkeypatch) -> None:
    # 페이지 딜레이 제거(테스트 가속).
    monkeypatch.setattr(
        "src.kiwoom.instrumentList.instrument_list._PAGE_DELAY_SEC", 0.0,
    )

    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        mrkt = body["mrkt_tp"]
        cont = request.headers.get("cont-yn")
        if mrkt == "0":  # 코스피: 2페이지
            if cont != "Y":
                return httpx.Response(
                    200,
                    json={"list": [{"code": "005930", "name": "삼성전자"}],
                          "return_code": 0},
                    headers={"cont-yn": "Y", "next-key": "k1"},
                )
            return httpx.Response(
                200,
                json={"list": [{"code": "000660", "name": "SK하이닉스"}],
                      "return_code": 0},
                headers={"cont-yn": "N"},
            )
        # 코스닥: 1페이지, 코드에 _AL 접미사 → 정규화 대상
        return httpx.Response(
            200,
            json={"list": [{"code": "032500_AL", "name": "케이엠더블유"}],
                  "return_code": 0},
            headers={"cont-yn": "N"},
        )

    client = InstrumentListClient(
        auth=_FakeAuth(), config=_FakeConfig(),
        transport=httpx.MockTransport(_handler),
    )
    name_to_code = await get_instrument_name_to_code(client=client)

    assert name_to_code == {
        "삼성전자": "005930",
        "SK하이닉스": "000660",
        "케이엠더블유": "032500",  # _AL 제거
    }
