# Unit Conversion (TS-1 안전성 보장)

> §3 Step 4 confirmation 테이블 렌더링 + Step 6 Edit literal 변환의 SOT.

## tolerance ↔ multiplier ↔ user-percent (3가지 폼)

- `tolerance = 1 − multiplier`
- `multiplier = 1 − tolerance`
- `user_pct = tolerance × 100`
- `tolerance = user_pct / 100`

## Examples (tolerance)

| User says | tolerance (raw) | multiplier (×) | user-percent display |
|---|---|---|---|
| "-5%로 완화" | `0.05` | `0.95` | `-5.0% (×0.95)` |
| "-3%로 완화" | `0.03` | `0.97` | `-3.0% (×0.97)` |
| "-1.5%" (현재 `_ALIGN_TOL_LOOSE`) | `0.015` | `0.985` | `-1.5% (×0.985)` |
| "-3.5%" (현재 `_TYPE_A_ALIGN_TOL`) | `0.035` | `0.965` | `-3.5% (×0.965)` |
| "-15%" (Stage 3 `_MA60_MA306_LOWER_TOL`) | `0.15` | `0.85` | `-15.0% (×0.85)` |
| "+45%" (Stage 3 `_MA60_MA306_UPPER_TOL`) | `0.45` (literal) | `1.45` | `+45.0% (×1.45)` |
| "+50%" (Stage 3 `_CLOSE_VS_MA612_UPPER`) | `0.50` | `1.50` | `+50.0% (×1.50)` |

## Ratio constants (NOT tolerances) — 부호 컨벤션 없음

| Variable | Korean | Raw | Display |
|---|---|---|---|
| `_TYPE_B_BELOW_MA60_RATIO` | MA60 대비 상한 비율 | `0.97` | `3% 이상 아래 (97% 미만)` |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 60분 close>MA60 비율 | `0.50` | `50%` |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | 60분 MA60 위 지지 | `0.75` | `75%` |
| `_DAILY_SURGE_THRESHOLD` | 일봉 등락률 상한 | `0.15` | `+15%` |

## Convergence percent (raw = display/100)

| Variable | Raw | Display |
|---|---|---|
| `_TYPE_C_CONVERGE_PCT` | `0.035` | `3.5%` |
| `_TYPE_E_SPREAD_PCT` | `0.10` | `10%` |

## Lower-band tolerance (signed `Final[float]`, 음수 raw 가능)

`_CLOSE_VS_MA612_LOWER`: raw `-0.15` → display `-15.0% (×0.85)`. **음수 부호가 literal에 포함된 유일한 케이스** — Edit 시 `: Final[float] = -0.15` 라인 그대로 매칭.

## Integer thresholds (변환 없음)

bare integer (days / bars / count). 입력 `"외국인 매도 2일"` → literal `2`. 입력 `"평가 봉 수 3"` → literal `3`. 단위는 `일` / `봉` / `개`로 사용자에게 표시하되 literal은 정수.

## 사용자 발화 인식 패턴

`"-N.N%"` / `"N.N% 완화"` / `"N% 강화"` / `"raw N.NNN"` / `"×N.NNN"` / `"N일"` / `"N봉"` 등 모두 위 4개 폼에 mapping (`N` = 임의의 숫자 자리). 모호한 입력은 §3 Step 4 confirmation 테이블에 raw + display 동시 표시로 사용자 재확인.
