"""stage_master 누적 확장(append-only) 필터.

핵심 동작
---------

날짜 X 를 시간순으로 하나씩 흘려보내며, 그 날짜의 ``masterReference.md`` 종목이
모두 통과되도록 4-feature 밴드를 **최소 확장** 한다. 한 번 통과 보장된
master 는 영구히 떨어지지 않는다 (monotonic — 밴드는 늘어나기만 함).

- 입력 모집단:   ``reports/<날짜>/organizedCompany.md`` (종목명 라인 단위)
- positive(반드시 통과): ``reports/<날짜>/masterReference.md``
- 피처:           ``chartDay.md`` 의 가장 최근 봉 (4-feature)
- 임계값 저장:   ``src/kiwoom/itemFilter/stageMasterFilter_state.json``

피처 4종 (단위: %)::

    close_over_ma20 = (close / MA20 − 1) × 100
    close_over_ma10 = (close / MA10 − 1) × 100
    ma20_over_ma60  = (MA20  / MA60 − 1) × 100
    close_over_ma306= (close / MA306− 1) × 100   (MA306 결측 시 면제)

CLI::

    python -m src.kiwoom.itemFilter.stageMasterFilter bootstrap
    python -m src.kiwoom.itemFilter.stageMasterFilter daily-update [YYYYMMDD]
    python -m src.kiwoom.itemFilter.stageMasterFilter validate
    python -m src.kiwoom.itemFilter.stageMasterFilter filter <YYYYMMDD>
    python -m src.kiwoom.itemFilter.stageMasterFilter show

본 모듈은 키움 API 를 호출하지 않는다. ``chartDayFilter`` 의 파싱 인프라
(:func:`parse_chartday_md`, :class:`ChartDayBar`)를 재사용한다.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.itemFilter.chartDayFilter import (
    ChartDayBar,
    _latest_date_dir,
    _split_stock_dirname,
    parse_chartday_md,
)

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_CHARTDAY_FILENAME: Final[str] = "chartDay.md"
_ORG_FILENAME: Final[str] = "organizedCompany.md"
_MASTER_FILENAME: Final[str] = "masterReference.md"
_OUTPUT_FILENAME: Final[str] = "masterConditionCompany.md"

_STATE_PATH: Final[Path] = Path(__file__).resolve().parent / "stageMasterFilter_state.json"
_STATE_BACKUP_PATH: Final[Path] = _STATE_PATH.with_suffix(_STATE_PATH.suffix + ".bak")

# 부트스트랩 기본 날짜 — 14·15(positive chartDay 0% 커버), 16(master 빈 파일)을
# 제외한 최초 가용 5거래일.
_DEFAULT_BOOTSTRAP_DATES: Final[tuple[str, ...]] = (
    "20260518", "20260519", "20260520", "20260521", "20260522",
)

# 평가 대상 4-feature.
_FEATURES: Final[tuple[str, ...]] = (
    "close_over_ma20",
    "close_over_ma10",
    "ma20_over_ma60",
    "close_over_ma306",
)
# MA306 결측 시 평가/확장이 면제되는 피처.
_OPTIONAL_FEATURES: Final[frozenset[str]] = frozenset({"close_over_ma306"})

# 경계값 부동소수점 노이즈 마진.
_EPS: Final[float] = 1e-6

# masterReference.md 신형 포맷 "종목명(코드)" 분리용 — Filter_condition_update.
# _parse_entry 와 동일 규칙 (끝의 4~6자리 코드 괄호만 코드로 인정).
_NAME_CODE_RE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$"
)


# ─────────────────────────────────────────────────────────────────────────────
# 상태 모델
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class FilterState:
    """누적 임계값 + 처리 이력."""

    thresholds: dict[str, dict[str, float]] = field(default_factory=dict)
    accumulated_dates: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)

    def is_initialized(self) -> bool:
        return bool(self.thresholds)

    def to_json(self) -> dict:
        return {
            "version": 1,
            "thresholds": self.thresholds,
            "accumulated_dates": self.accumulated_dates,
            "history": self.history,
        }

    @classmethod
    def from_json(cls, data: dict) -> "FilterState":
        return cls(
            thresholds={k: dict(v) for k, v in data.get("thresholds", {}).items()},
            accumulated_dates=list(data.get("accumulated_dates", [])),
            history=list(data.get("history", [])),
        )


def load_state(path: Path = _STATE_PATH) -> FilterState:
    if not path.exists():
        return FilterState()
    return FilterState.from_json(json.loads(path.read_text(encoding="utf-8")))


def save_state(state: FilterState, path: Path = _STATE_PATH) -> None:
    if path.exists():
        shutil.copy2(path, _STATE_BACKUP_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 입력 IO
# ─────────────────────────────────────────────────────────────────────────────


def _split_name_code(line: str) -> tuple[str, str]:
    """한 줄을 ``(종목명, 종목코드)`` 로 분리. 코드 없으면 빈 문자열.

    구형 "종목명" / 신형 "종목명(코드)" 양 포맷 호환 —
    :func:`Filter_condition_update._parse_entry` 와 동등 규칙.
    """
    s = line.strip()
    m = _NAME_CODE_RE.match(s)
    if m:
        return m.group("nm").strip(), m.group("cd")
    return s, ""


def _read_name_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        _split_name_code(ln)[0]
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]


def read_organized_company(
    date: str, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[str]:
    return _read_name_list(reports_root / date / _ORG_FILENAME)


def read_master_reference(
    date: str, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[str]:
    return _read_name_list(reports_root / date / _MASTER_FILENAME)


def _stock_dir(
    date: str, name: str, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path | None:
    """종목명 → ``<name>(코드)`` 형식 폴더 경로. 없으면 None.

    ``name`` 은 구형 "종목명" / 신형 "종목명(코드)" 모두 허용.
    코드가 있으면 정확 일치 폴더를 우선하고, 없거나 미발견 시
    기존과 동일하게 ``이름( `` 접두 매칭으로 해석한다.
    """
    date_dir = reports_root / date
    if not date_dir.exists():
        return None
    nm, cd = _split_name_code(name)
    if cd:
        exact = date_dir / f"{nm}({cd})"
        if exact.is_dir():
            return exact
    for p in date_dir.iterdir():
        if not p.is_dir():
            continue
        if p.name.startswith(nm + "(") and p.name.endswith(")"):
            return p
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 피처 추출
# ─────────────────────────────────────────────────────────────────────────────


def _compute_features(bar: ChartDayBar) -> dict[str, float | None]:
    out: dict[str, float | None] = {k: None for k in _FEATURES}
    if bar.close is None or bar.close == 0:
        return out
    for ma_name in ("ma10", "ma20", "ma60"):
        if getattr(bar, ma_name) in (None, 0):
            return out
    out["close_over_ma20"] = (bar.close / bar.ma20 - 1) * 100.0
    out["close_over_ma10"] = (bar.close / bar.ma10 - 1) * 100.0
    out["ma20_over_ma60"] = (bar.ma20 / bar.ma60 - 1) * 100.0
    if bar.ma306 not in (None, 0):
        out["close_over_ma306"] = (bar.close / bar.ma306 - 1) * 100.0
    return out


def _extract_master_features(
    date: str, names: list[str], reports_root: Path,
) -> list[dict]:
    """master 종목들의 피처 벡터. 데이터 결손은 명시적 에러."""
    out: list[dict] = []
    for name in names:
        sd = _stock_dir(date, name, reports_root)
        if sd is None:
            raise FileNotFoundError(
                f"master 종목 폴더 없음: date={date} name={name}"
            )
        chartday = sd / _CHARTDAY_FILENAME
        if not chartday.exists():
            raise FileNotFoundError(f"chartDay.md 없음: {chartday}")
        bars, _meta = parse_chartday_md(chartday)
        if not bars:
            raise ValueError(f"봉 없음: {chartday}")
        feats = _compute_features(bars[-1])
        for k in _FEATURES:
            if k in _OPTIONAL_FEATURES:
                continue
            if feats[k] is None:
                raise ValueError(
                    f"필수 피처 결측: date={date} name={name} feature={k}"
                )
        feats["__name__"] = name
        feats["__date__"] = date
        out.append(feats)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 임계값 초기화·확장
# ─────────────────────────────────────────────────────────────────────────────


def _init_thresholds(positives: list[dict]) -> dict[str, dict[str, float]]:
    """첫 캘리브레이션: positive 값들의 [min, max] 밴드."""
    thresholds: dict[str, dict[str, float]] = {}
    for feat in _FEATURES:
        vals = [p[feat] for p in positives if p.get(feat) is not None]
        if not vals:
            if feat in _OPTIONAL_FEATURES:
                continue
            raise ValueError(f"init 불가: feature={feat} positive 값 0개")
        thresholds[feat] = {"lo": min(vals), "hi": max(vals)}
    return thresholds


def _expand_thresholds(
    thresholds: dict[str, dict[str, float]], positives: list[dict],
) -> list[dict]:
    """master 통과를 위한 밴드 최소 확장 (monotonic).

    Returns: 확장 이벤트 리스트.
    """
    events: list[dict] = []
    for pos in positives:
        for feat in _FEATURES:
            v = pos.get(feat)
            if v is None:
                continue
            if feat not in thresholds:
                # optional feature가 init 시 전원 결측이었으나 이번에 값 등장.
                thresholds[feat] = {"lo": v, "hi": v}
                events.append({
                    "trigger_master": pos["__name__"],
                    "feature": feat,
                    "side": "init",
                    "old": None,
                    "new_lo": v,
                    "new_hi": v,
                })
                continue
            band = thresholds[feat]
            if v < band["lo"] - _EPS:
                events.append({
                    "trigger_master": pos["__name__"],
                    "feature": feat,
                    "side": "lo",
                    "old": band["lo"],
                    "new": v,
                })
                band["lo"] = v
            if v > band["hi"] + _EPS:
                events.append({
                    "trigger_master": pos["__name__"],
                    "feature": feat,
                    "side": "hi",
                    "old": band["hi"],
                    "new": v,
                })
                band["hi"] = v
    return events


def _features_pass(feats: dict, thresholds: dict[str, dict[str, float]]) -> bool:
    for k in _FEATURES:
        v = feats.get(k)
        band = thresholds.get(k)
        if v is None:
            if k in _OPTIONAL_FEATURES:
                continue
            return False
        if band is None:
            if k in _OPTIONAL_FEATURES:
                continue
            return False
        if not (band["lo"] - _EPS <= v <= band["hi"] + _EPS):
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# 단일 날짜 누적
# ─────────────────────────────────────────────────────────────────────────────


def accumulate_date(
    state: FilterState, date: str,
    *, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> dict:
    if date in state.accumulated_dates:
        logger.warning("이미 누적된 날짜 — 건너뜀: {d}", d=date)
        return {"date": date, "action": "skip-already-accumulated",
                "masters_in": 0, "expansions": []}

    masters = read_master_reference(date, reports_root)
    if not masters:
        logger.warning("masterReference.md 비어 있음: {d}", d=date)
        event = {"date": date, "action": "skip-empty-masters",
                 "masters_in": 0, "expansions": []}
        state.accumulated_dates.append(date)
        state.history.append(event)
        return event

    org = read_organized_company(date, reports_root)
    if org:
        org_set = set(org)
        not_in_org = [m for m in masters if m not in org_set]
        if not_in_org:
            logger.warning(
                "master 중 organizedCompany 미포함 ({n}건): {names}",
                n=len(not_in_org), names=not_in_org,
            )

    positives = _extract_master_features(date, masters, reports_root)

    if not state.is_initialized():
        state.thresholds = _init_thresholds(positives)
        action, expansions = "init", []
    else:
        action = "expand"
        expansions = _expand_thresholds(state.thresholds, positives)

    # 자가검증: 확장 후 모든 master가 실제로 통과되는지.
    for pos in positives:
        if not _features_pass(pos, state.thresholds):
            raise RuntimeError(
                f"확장 후에도 master 미통과: date={date} "
                f"name={pos['__name__']} feats={pos}"
            )

    state.accumulated_dates.append(date)
    event = {
        "date": date,
        "action": action,
        "masters_in": len(positives),
        "expansions": expansions,
        "thresholds_after": {k: dict(v) for k, v in state.thresholds.items()},
    }
    state.history.append(event)
    return event


# ─────────────────────────────────────────────────────────────────────────────
# 평가 / 필터링 (운용 단계)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StageMasterResult:
    stk_cd: str
    stk_nm: str
    report_path: Path | None
    latest_bar: ChartDayBar | None
    selected: bool
    reason: str
    close_over_ma20: float | None = None
    close_over_ma10: float | None = None
    ma20_over_ma60: float | None = None
    close_over_ma306: float | None = None
    extra: dict = field(default_factory=dict)


def evaluate_bar(
    bar: ChartDayBar, thresholds: dict[str, dict[str, float]],
) -> tuple[bool, str, dict]:
    """단일 봉을 현재 임계값으로 평가."""
    feats = _compute_features(bar)
    extra: dict = {k: feats.get(k) for k in _FEATURES}
    extra["ma306_skipped"] = False

    for k in _FEATURES:
        v = feats.get(k)
        band = thresholds.get(k)
        if v is None:
            if k in _OPTIONAL_FEATURES:
                extra["ma306_skipped"] = True
                continue
            return False, f"{k} 결측", extra
        if band is None:
            if k in _OPTIONAL_FEATURES:
                continue
            return False, f"thresholds[{k}] 미정의", extra
        if not (band["lo"] - _EPS <= v <= band["hi"] + _EPS):
            return (
                False,
                f"{k}={v:+.2f}% ∉ [{band['lo']:+.2f}%, {band['hi']:+.2f}%]",
                extra,
            )
    return True, "통과", extra


def filter_date(
    date: str,
    state: FilterState,
    *, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[StageMasterResult]:
    org_names = read_organized_company(date, reports_root)
    results: list[StageMasterResult] = []
    for name in org_names:
        sd = _stock_dir(date, name, reports_root)
        if sd is None:
            continue
        chartday = sd / _CHARTDAY_FILENAME
        if not chartday.exists():
            continue
        try:
            bars, meta = parse_chartday_md(chartday)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("파싱 실패 {n}: {e}", n=name, e=exc)
            continue
        if not bars:
            continue
        ok, reason, extra = evaluate_bar(bars[-1], state.thresholds)
        parsed = _split_stock_dirname(sd.name)
        stk_nm = meta.get("stk_nm") or (parsed[0] if parsed else name)
        stk_cd = meta.get("stk_cd") or (parsed[1] if parsed else "")
        results.append(StageMasterResult(
            stk_cd=stk_cd, stk_nm=stk_nm, report_path=chartday,
            latest_bar=bars[-1], selected=ok, reason=reason,
            close_over_ma20=extra.get("close_over_ma20"),
            close_over_ma10=extra.get("close_over_ma10"),
            ma20_over_ma60=extra.get("ma20_over_ma60"),
            close_over_ma306=extra.get("close_over_ma306"),
            extra=extra,
        ))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 출력 (organizedCompany.md 와 동일 형식 — 종목명 줄단위)
# ─────────────────────────────────────────────────────────────────────────────


def render_plain_text(results: list[StageMasterResult]) -> str:
    """선정 종목명만 줄단위로 연결 (organizedCompany.md 형식)."""
    selected = [r for r in results if r.selected]
    if not selected:
        return ""
    return "\n".join(r.stk_nm for r in selected) + "\n"


def save_filter_plain_text(
    results: list[StageMasterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    current = now or datetime.now()
    if date_dir is None:
        date_dir = current.strftime("%Y%m%d")
    text = render_plain_text(results)
    out_dir = output_root / date_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _OUTPUT_FILENAME
    out_path.write_text(text, encoding="utf-8")
    sel = sum(1 for r in results if r.selected)
    logger.info(
        "필터 결과 저장: {p} (선정 {s}/{n}건)",
        p=out_path, s=sel, n=len(results),
    )
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI 서브커맨드
# ─────────────────────────────────────────────────────────────────────────────


def _print_thresholds(state: FilterState) -> None:
    for k in _FEATURES:
        band = state.thresholds.get(k)
        if band is None:
            print(f"  {k}: (미정의)")
        else:
            print(f"  {k}: [{band['lo']:+.6f}%, {band['hi']:+.6f}%]")


def cmd_bootstrap(
    dates: list[str], *, force: bool = False,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> int:
    state = load_state()
    if state.is_initialized() and not force:
        print("[오류] 이미 누적된 상태입니다 (accumulated_dates="
              f"{state.accumulated_dates}).")
        print("       완전 재시작은 --force, 일일 갱신은 daily-update 사용.")
        return 2
    if force:
        # 백업 후 빈 상태로 시작
        if _STATE_PATH.exists():
            shutil.copy2(_STATE_PATH, _STATE_BACKUP_PATH)
        state = FilterState()

    print(f"=== bootstrap: dates={list(dates)} ===")
    for d in dates:
        event = accumulate_date(state, d, reports_root=reports_root)
        print(
            f"  [{d}] {event['action']}  masters={event['masters_in']}  "
            f"expansions={len(event['expansions'])}"
        )
        for ev in event["expansions"]:
            print(
                f"     · {ev['feature']} {ev['side']}: "
                f"old={ev.get('old')} new={ev.get('new', ev.get('new_lo'))}"
                f"  (trigger: {ev['trigger_master']})"
            )
    save_state(state)
    print()
    print("최종 임계값:")
    _print_thresholds(state)
    print(f"\n상태 파일: {_STATE_PATH}")
    return 0


def cmd_daily_update(
    date: str | None,
    *, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> int:
    state = load_state()
    if not state.is_initialized():
        print("[오류] 상태 파일이 비어 있습니다. 먼저 bootstrap 실행.")
        return 2
    if date is None:
        latest = _latest_date_dir(reports_root)
        if latest is None:
            print("[오류] reports/ 하위에 날짜 폴더가 없습니다.")
            return 2
        date = latest.name
    print(f"=== daily-update: date={date} ===")
    event = accumulate_date(state, date, reports_root=reports_root)
    print(
        f"  [{date}] {event['action']}  masters={event['masters_in']}  "
        f"expansions={len(event['expansions'])}"
    )
    for ev in event["expansions"]:
        print(
            f"     · {ev['feature']} {ev['side']}: "
            f"old={ev.get('old')} new={ev.get('new', ev.get('new_lo'))}"
            f"  (trigger: {ev['trigger_master']})"
        )
    save_state(state)
    print("\n최종 임계값:")
    _print_thresholds(state)
    return 0


def cmd_validate(
    *, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> int:
    state = load_state()
    if not state.is_initialized():
        print("[오류] 상태 파일이 비어 있습니다.")
        return 2
    print("=" * 72)
    print(f"validate: accumulated_dates={state.accumulated_dates}")
    print("=" * 72)
    all_ok = True
    total_masters = 0
    total_pass = 0
    for d in state.accumulated_dates:
        masters = read_master_reference(d, reports_root)
        if not masters:
            print(f"[{d}] master=0 (skip)")
            continue
        ok_count = 0
        fail_rows: list[tuple[str, str]] = []
        for name in masters:
            sd = _stock_dir(d, name, reports_root)
            if sd is None or not (sd / _CHARTDAY_FILENAME).exists():
                fail_rows.append((name, "chartDay.md 없음"))
                continue
            try:
                bars, _ = parse_chartday_md(sd / _CHARTDAY_FILENAME)
            except (ValueError, FileNotFoundError) as exc:
                fail_rows.append((name, f"파싱 실패: {exc}"))
                continue
            if not bars:
                fail_rows.append((name, "봉 없음"))
                continue
            ok, reason, _ = evaluate_bar(bars[-1], state.thresholds)
            if ok:
                ok_count += 1
            else:
                fail_rows.append((name, reason))
        total_masters += len(masters)
        total_pass += ok_count
        status = "OK" if not fail_rows else "FAIL"
        print(f"[{d}] {ok_count}/{len(masters)}  {status}")
        for nm, rs in fail_rows:
            print(f"   ✗ {nm}: {rs}")
            all_ok = False
    print("=" * 72)
    print(
        f"전체: {total_pass}/{total_masters} 통과 — "
        f"{'PASS' if all_ok else 'FAIL'}"
    )
    return 0 if all_ok else 1


def cmd_filter(
    date: str, *, reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> int:
    state = load_state()
    if not state.is_initialized():
        print("[오류] 상태 파일이 비어 있습니다. 먼저 bootstrap 실행.")
        return 2
    results = filter_date(date, state, reports_root=reports_root)
    sel = sum(1 for r in results if r.selected)
    print(
        f"=== filter [{date}]: 분석 {len(results)} / "
        f"선정 {sel} / 제외 {len(results) - sel} ==="
    )
    path = save_filter_plain_text(
        results,
        output_root=reports_root,
        date_dir=date,
    )
    print(f"리포트: {path}")
    return 0


def cmd_show() -> int:
    state = load_state()
    if not state.is_initialized():
        print("상태: 미초기화 (bootstrap 필요)")
        return 0
    print("===== stageMasterFilter 상태 =====")
    print(f"누적 날짜: {', '.join(state.accumulated_dates)}")
    print("\n임계값:")
    _print_thresholds(state)
    if state.history:
        print(f"\n이력 ({len(state.history)} 단계, 최근 5개):")
        for h in state.history[-5:]:
            print(
                f"  [{h['date']}] {h['action']}  "
                f"masters_in={h.get('masters_in', 0)}  "
                f"expansions={len(h.get('expansions', []))}"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="stageMasterFilter",
        description="stage_master 누적 확장 필터 (append-only)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_boot = sub.add_parser("bootstrap", help="초기 누적 (5거래일)")
    p_boot.add_argument(
        "--dates", nargs="+", default=list(_DEFAULT_BOOTSTRAP_DATES),
        help=f"누적 대상 날짜들 (기본: {' '.join(_DEFAULT_BOOTSTRAP_DATES)})",
    )
    p_boot.add_argument(
        "--force", action="store_true",
        help="기존 상태를 백업 후 처음부터 다시 시작",
    )

    p_daily = sub.add_parser("daily-update", help="오늘 날짜 누적")
    p_daily.add_argument("date", nargs="?", default=None, help="YYYYMMDD (생략 시 최신)")

    sub.add_parser("validate", help="누적 날짜 전체 master 통과 검증")

    p_filt = sub.add_parser("filter", help="현재 임계값으로 organizedCompany 필터링")
    p_filt.add_argument("date", help="YYYYMMDD")

    sub.add_parser("show", help="현재 상태 출력")

    args = parser.parse_args(argv)
    if args.cmd == "bootstrap":
        return cmd_bootstrap(args.dates, force=args.force)
    if args.cmd == "daily-update":
        return cmd_daily_update(args.date)
    if args.cmd == "validate":
        return cmd_validate()
    if args.cmd == "filter":
        return cmd_filter(args.date)
    if args.cmd == "show":
        return cmd_show()
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FilterState",
    "StageMasterResult",
    "accumulate_date",
    "evaluate_bar",
    "filter_date",
    "load_state",
    "main",
    "render_plain_text",
    "save_filter_plain_text",
    "save_state",
]
