"""ka10059 응답값 검증·이상 탐지 디버그 스크립트.

실전 도메인에 ka10059 를 호출해 **raw JSON 전체** 를 보존하고, 우리가 파싱한
DataFrame 과 대조해 부호·단위·날짜·0합 invariant 를 검증한다.

실행::

    .venv/bin/python -m scripts.debug_ka10059_005930

출력물::

    data/debug/ka10059_005930_<YYYYMMDDHHMMSS>.json   (raw 응답 전체)

콘솔::

    1) 모듈이 폐기한 필드 목록 (extra="ignore" 대상)
    2) raw vs 파싱 결과 한 행 side-by-side
    3) 0합 invariant 검증: 개인+외국인+기관계+기타법인+내외국인 ≈ 0
    4) 날짜 정합성: 주말 포함 여부, 정렬, 중복
    5) 이상치 탐지: 부호/규모 이상
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from src.kiwoom.config import config
from src.kiwoom.investor.investor import (
    InvestorFlowClient,
    InvestorFlowRecord,
    get_investor_flow,
)

_STK_CD = "005930"
_BARS = 16
_DEBUG_DIR = Path("data/debug")


# 0합 invariant 에 들어가는 모든 시장 참여자 키.
# (ka10059 응답의 모든 투자자/기관 카테고리 — 합치면 거래대금이 0이 되어야 함.)
_ALL_PARTICIPANTS = (
    "ind_invsr",       # 개인
    "frgnr_invsr",     # 외국인
    "fnnc_invt",       # 금융투자  ┐
    "insrnc",          # 보험      │
    "invtrt",          # 투신      │
    "etc_fnnc",        # 기타금융  │ → 기관계(orgn) = 이 8 항목 합계
    "bank",            # 은행      │
    "penfnd_etc",      # 연기금등  │
    "samo_fund",       # 사모펀드  │
    "natn",            # 국가      ┘
    "etc_corp",        # 기타법인
    "natfor",          # 내외국인
)


def _to_int(v: Any) -> int:
    """'+1234' / '-1234' / '' / None → int (부호 보존)."""
    if v in (None, ""):
        return 0
    try:
        return int(str(v).strip())
    except ValueError:
        try:
            return int(float(str(v).strip()))
        except ValueError:
            return 0


async def main() -> int:
    today = datetime.now().strftime("%Y%m%d")
    logger.info("=== ka10059 디버그 시작 ===")
    logger.info("종목={s} 기준일={d} mode={m} url={u}",
                s=_STK_CD, d=today, m=config.mode, u=config.base_url)

    # ── 1. raw 응답 캡처 (단발 호출, 페이징 없이 1페이지만) ───────────────────
    client = InvestorFlowClient()
    body = {
        "dt": today,
        "stk_cd": _STK_CD,
        "amt_qty_tp": "1",
        "trde_tp": "0",
        "unit_tp": "1000",
    }
    raw_json, cont_yn, next_key = await client.post(body)
    rows = raw_json.get("stk_invsr_orgn", [])
    logger.info("응답 행 수={n} cont-yn={c} next-key={k}",
                n=len(rows), c=cont_yn, k=next_key)

    _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    dump_path = _DEBUG_DIR / f"ka10059_{_STK_CD}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    dump_path.write_text(
        json.dumps(raw_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("raw JSON 덤프 → {p}", p=dump_path)

    if not rows:
        logger.error("응답이 비어있음 — 디버그 중단")
        return 1

    # ── 2. extra="ignore" 가 폐기한 필드 목록 ─────────────────────────────────
    parsed_keys = set(InvestorFlowRecord.model_fields.keys())
    raw_keys = set(rows[0].keys())
    discarded = sorted(raw_keys - parsed_keys)
    print()
    print("─── (1) 모듈이 폐기한 필드 (extra='ignore') ───")
    print(f"파싱 모델 필드: {sorted(parsed_keys)}")
    print(f"raw 응답 필드 ({len(raw_keys)}개): {sorted(raw_keys)}")
    print(f"폐기된 필드 ({len(discarded)}개): {discarded}")

    # ── 3. raw vs 파싱 한 행 비교 ─────────────────────────────────────────────
    print()
    print("─── (2) raw vs 파싱 한 행 (최신 거래일) ───")
    first_raw = rows[0]
    first_parsed = InvestorFlowRecord.model_validate(first_raw).model_dump()
    print(f"날짜: {first_raw.get('dt')}")
    for k in ("ind_invsr", "frgnr_invsr", "orgn"):
        rv = first_raw.get(k)
        pv = first_parsed.get(k)
        ok = "✓" if _to_int(rv) == pv else "✗"
        print(f"  {k:14s}  raw={str(rv):>15s}  parsed={pv:>15,d}  {ok}")

    # ── 4. 0합 invariant: 모든 참여자 합 ≈ 0 (양방향 거래의 본질) ────────────
    print()
    print("─── (3) 0합 invariant 검증 (모든 참여자 순매수 합) ───")
    print("기대값: ind_invsr + frgnr_invsr + 기관세분류8종 + etc_corp + natfor ≈ 0")
    print(f"{'날짜':<10s} {'개인':>12s} {'외국인':>12s} {'기관계(합)':>12s} {'기타법인':>10s} {'내외국인':>10s} {'전체합':>12s}")
    n_anomaly = 0
    for r in rows[:_BARS]:
        ind = _to_int(r.get("ind_invsr"))
        frg = _to_int(r.get("frgnr_invsr"))
        # 기관계는 응답의 orgn 값 사용 (기관 8개 세분류의 합과 같아야 함).
        org = _to_int(r.get("orgn"))
        org_8sum = sum(_to_int(r.get(k)) for k in (
            "fnnc_invt", "insrnc", "invtrt", "etc_fnnc",
            "bank", "penfnd_etc", "samo_fund", "natn",
        ))
        etc_corp = _to_int(r.get("etc_corp"))
        natfor = _to_int(r.get("natfor"))
        total = ind + frg + org + etc_corp + natfor

        # 기관계 무결성: orgn vs 8 세분류 합
        org_consistent = (org == org_8sum)

        # 0합 허용오차: 단위가 백만원이고 응답이 라운딩됨 → ±수십 단위까지 허용.
        # 보수적으로 |total| < max(절댓값들의 합) * 0.5% 로 본다.
        magnitudes = abs(ind) + abs(frg) + abs(org) + abs(etc_corp) + abs(natfor)
        tol = max(int(magnitudes * 0.005), 100)
        ok = abs(total) <= tol

        flag = "" if ok else " ← 0합 이상"
        flag2 = "" if org_consistent else " [orgn≠Σ세분류]"
        if not ok or not org_consistent:
            n_anomaly += 1
        print(
            f"{r.get('dt'):<10s} "
            f"{ind:>12,d} {frg:>12,d} {org:>12,d} "
            f"{etc_corp:>10,d} {natfor:>10,d} {total:>12,d}"
            f"{flag}{flag2}"
        )
    print(f"이상 행: {n_anomaly}/{min(len(rows), _BARS)}")

    # ── 5. 파사드 결과와 raw 비교 + 날짜 정합성 ────────────────────────────────
    df = await get_investor_flow(_STK_CD, bars=_BARS)
    print()
    print("─── (4) 파사드 DataFrame 정합성 ───")
    print(f"행 수: {len(df)} (요구={_BARS})")
    print(f"정렬: {'오름차순 ✓' if list(df['dt']) == sorted(df['dt']) else '✗ 오름차순 아님'}")
    print(f"중복: {'없음 ✓' if df['dt'].is_unique else '✗ 중복 존재'}")

    # 주말 포함 여부 (월=0 ~ 일=6 → 토=5, 일=6 발견 시 이상)
    weekends = [d for d in df["dt"] if datetime.strptime(d, "%Y%m%d").weekday() >= 5]
    print(f"주말 행: {'없음 ✓' if not weekends else '✗ ' + str(weekends)}")

    # 인접 거래일 간 휴장 갭 (>5일이면 의심)
    dates = [datetime.strptime(d, "%Y%m%d") for d in df["dt"]]
    gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates) - 1)]
    long_gaps = [(df["dt"].iloc[i], df["dt"].iloc[i+1], g)
                 for i, g in enumerate(gaps) if g > 5]
    print(f"5일 이상 갭: {long_gaps if long_gaps else '없음 ✓'}")

    # ── 6. 단위 sanity check ─────────────────────────────────────────────────
    print()
    print("─── (5) 단위 sanity (백만원 가정 검증) ───")
    avg_abs = (df["ind_invsr"].abs() + df["frgnr_invsr"].abs() + df["orgn"].abs()).mean() / 3
    print(f"투자자 3종 평균 |순매수금액|: {avg_abs:,.0f}")
    print("→ 단위가 백만원이면 약 {:,.0f} 억원 / {:,.2f} 조원".format(avg_abs / 100, avg_abs / 1_000_000))
    print("→ 단위가 천원이면 약 {:,.0f} 백만원 / {:,.2f} 십억원 (작아서 비현실)".format(avg_abs / 1000, avg_abs / 1_000_000))
    print("→ 단위가 원이면 약 {:,.0f} 천원 (말도 안 됨)".format(avg_abs / 1000))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
