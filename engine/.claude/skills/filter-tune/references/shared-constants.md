# Shared Constants Registry

> §3 Step 2 [B-17] 공유 상수 영향 공개 + §5 anti-conflation 디스앰비귀에이션의 SOT.
>
> 핵심 구분:
> - **공유 (shared)**: 단일 Final 상수가 ≥2개 (Type, condition) tuple에서 동시에 소비. 변경 시 다중 동시 영향.
> - **Look-alike (혼동 유사)**: 별개 Final 상수가 비슷한 이름/의미를 가져 사용자 발화 시 혼동 위험. **별개 변수이므로 propagation 없음** — 디스앰비귀에이션만 필요.

---

## 1. Active shared constants (B-17 trigger)

현재 active 공유 상수는 **단 1개**.

### `_ALIGN_TOL_LOOSE` — chart60_120Filter.py:120 — value `0.015` (-1.5%, ×0.985)

**Affected (Type, condition) tuples** (PRD §5.4 verbatim influence-list):

- **Type B** — 120분 MA10-MA20 근접 판정 (`_check_type_b` 내부 호출)
- **Type B** — MA60-MA306 근접 판정 (동 함수 내 장기추세 leg)
- **Type C** — MA60-MA306 장기추세 leg (`_check_type_c` 내부)
- **Type D** — 60분 4선 정배열 fallback (`_check_type_d`에서 strict 60m 정렬 실패 시 `_is_4ma_aligned(b, _ALIGN_TOL_LOOSE)` 호출)

**변경 영향 (Korean verbatim, §3 Step 2 출력)**:
> `"⚠️ 이 상수는 공유 상수입니다. 변경 시 다음 조건들이 동시에 영향을 받습니다:`
> ` • Type B — 120분 MA10-MA20 근접 판정`
> ` • Type B — MA60-MA306 근접 판정`
> ` • Type C — MA60-MA306 장기추세 leg`
> ` • Type D — 60분 4선 정배열 fallback`
> `특정 Type만 조정하려면 해당 Type 전용 상수 신설이 필요합니다 (TS-1 로직 변경 — 사용자 명시적 승인 필요)."`

**Variant 신설 요청 시**: TS-1 위반(상수 *값* 변경 → 상수 *추가*). 사용자에게 명시적 승인 요청. Phase 2 검토. Type E는 이미 `_TYPE_E_MA60_OVER_MA306_TOL = 0.035`로 분리 완료 — 동일한 패턴을 Type B/C/D 개별로 적용하는 작업.

---

## 2. Look-alike pairs (NOT shared but 혼동 유사) — 디스앰비귀에이션 필요

이하 모든 쌍은 **별개의 모듈-수준 Final 상수**다. 이름·의미가 유사하므로 사용자 발화에 모호함이 있을 시 §5 anti-conflation 표에 따라 AskUserQuestion으로 명시 해소한다. **변경 propagation 없음** — A를 바꿔도 B는 그대로.

### Pair 1: `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` (Step 1 §Critical Distinctions verbatim)

| Property | `_ALIGN_TOL_LOOSE` | `_MA_ALIGNMENT_TOLERANCE` |
|---|---|---|
| Owning module | `chart60_120Filter.py` | `chart60Filter.py` |
| Line | 120 | 75 |
| Value | `0.015` (×0.985, −1.5% slack) | `0.005` (×0.995, −0.5% slack) |
| Slack | Loose (3× wider) | Strict |
| Scope | **Shared** — Type B (60m & 120m), Type C MA60-MA306 leg, Type D 60m fallback (chart60_120Filter 내) | Sole alignment tolerance for standalone chart60Filter 4MA check |
| 변경 영향 | Cross-cut Type B/C/D — Stage 1 recall/precision 광범위 시프트 | Localized to chart60Filter only — cross-stage propagation 없음 |
| When to loosen | Stage 1 over-rejects in trending market | Standalone chart60 over-rejects |

**디스앰비귀에이션 질문 (verbatim)**:
> `"두 가지 다른 변수가 있습니다: (1) chart60_120Filter의 Type B/C/D 공유 허용오차 (-1.5%) vs (2) chart60Filter 단독 모듈 4선 정배열 (-0.5%). 어느 쪽을 변경할까요?"`

**Default**: Stage 1 production은 chart60_120Filter — `_ALIGN_TOL_LOOSE` 우선. 단 사용자 발화에 `"chart60Filter"` / `"단독"` / `"strict"` 키워드가 명시되면 `_MA_ALIGNMENT_TOLERANCE`로 routing.

### Pair 2: `_REQUIRED_CONSECUTIVE_BARS` 3-way independent

`chart60Filter.py:78` (value `3`) / `chart240Filter.py:81` (value `3`) / `chartDayFilter.py:72` (value `3`).

- **동일 이름, 동일 현재 값, 별개 모듈 상수** — 각각 module-scope.
- Stage 3는 추가로 `_REQUIRED_ALIGNED_BARS = 2` 가짐 → 규칙은 "3개 중 ≥2개" (단순 "all 3"이 아님).
- 튜닝 시 하나만 변경 → 나머지 두 개 그대로.

**디스앰비귀에이션 질문 (verbatim)**:
> `"세 개 모듈에서 독립적으로 선언되어 있습니다: chart60 / chart240 / chartDay. 어느 Stage의 윈도우 크기를 바꿀까요?"`

### Pair 3: MA60-MA306 허용오차 3-way (Step 1 §Critical Distinctions verbatim)

| Variable | File:Line | Value | Timeframe | 비고 |
|---|---|---|---|---|
| `_MA60_MA306_TOLERANCE` | chart240Filter.py:80 | `0.07` (-7.0%) | 240분 | Stage 2 long-term gate (Phase B 2026-07-05: 구 0.025) |
| `_MA60_MA306_LOWER_TOL` | chartDayFilter.py:63 | `0.15` (-15%) | 일봉 | Stage 3 envelope floor (deep — daily volatility 반영) |
| `_TYPE_E_MA60_OVER_MA306_TOL` | chart60_120Filter.py:156 | `0.035` (-3.5%) | 120분 (Type E 전용) | `_ALIGN_TOL_LOOSE`에서 split (Type E V-rebound 보호) |

**디스앰비귀에이션 질문 (verbatim)**:
> `"세 가지 다른 시간프레임에 있습니다: (1) Stage 2 240분 (-2.5%) (2) Stage 3 일봉 하한 (-15%) (3) Stage 1 Type E 전용 (-3.5%). 어느 쪽인가요?"`

### Pair 4: Window-size 4-way

| Variable | File:Line | Value | Semantic |
|---|---|---|---|
| `_REQUIRED_STATIC_BARS` | chart60_120Filter.py:116 | `8` | Type A/B/C/D static window (`bars[-8:]`) |
| `_REQUIRED_CONSECUTIVE_BARS` | chart60/240/Day 3-way | `3` (각각 독립) | per-stage consecutive |
| `_REQUIRED_BARS` | investorFilter.py:43 | `16` | Stage 4 minimum sampling |
| `_TYPE_D_DYNAMIC_WINDOW` | chart60_120Filter.py:138 | `16` | Type D close>MA60 ratio window |
| `_TYPE_E_DYNAMIC_WINDOW` | chart60_120Filter.py:145 | `8` | Type E close>MA60 ratio window |
| `_TYPE_E_SHORT_ALIGN_WINDOW` | chart60_120Filter.py:149 | `2` | Type E short-alignment recent window |

**디스앰비귀에이션**: §5 표 verbatim에 따라 4-row 표 렌더 후 사용자 선택.

### Pair 5: regex 패턴 (`_STOCK_DIR_PATTERN`, `_TABLE_ROW_PATTERN`)

**`_STOCK_DIR_PATTERN`**: 동일 logical regex `r"^(.+?)\((\d{4,6})\)$"`로 chart60 / chartDay / investor / finance에 독립 선언. chart60_120 / chart240은 re-import해 재사용.

**`_TABLE_ROW_PATTERN`**: 구조적으로 **다르다** — column count가 timeseries마다 다름:
- chart60Filter — 10 groups (60m: timestamp HH:MM + 4 MA columns).
- chartDayFilter — 11 groups (daily: 1 extra MA612 column).
- investorFilter — 4 groups (signed integer 3 컬럼).
- financeFilter — `_CUP_NGA_ROW_PATTERN` (table이 아닌 단일 row).

이들은 **튜닝 비대상**(regex 구조) — `references/range-map.md` 비대상 행이 안내함. 사용자 변경 의도 시 TS-1 위반으로 REJECT.

---

## 3. 변경 propagation 빠른 참조

| Variable | 변경 시 동시 영향 받는 곳 |
|---|---|
| `_ALIGN_TOL_LOOSE` (공유) | Type B (2개 조건) + Type C + Type D = 4 tuple |
| `_TYPE_A_ALIGN_TOL` | Type A 60m + 120m = 2 tuple (단일 변수 → 두 timeframe 적용은 design, 분리 가능 시 Phase 2) |
| 기타 모든 Final 상수 | 1 tuple (private — propagation 없음) |

**디자인 invariant**: Step 2 [B-17]은 위 표의 `_ALIGN_TOL_LOOSE` 행 1개에 대해서만 사용자-facing 영향 공개를 emit. 나머지 변수는 SHORTCUT (§3 SHORTCUT) 발동.
