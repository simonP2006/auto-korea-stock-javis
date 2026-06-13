# Theory Guide — 이론 기반 파라미터 튜닝

> §4 Branch 5 `THEORY_GUIDE`의 SOT. FR-7.1~7.4 매핑.
>
> 출처: PRD §5.3 / PRD §5.2 시장 regime 가이드 / Step 2 §6 + §8 / Step 6 blueprint §7.

본 가이드는 **이론 → Stage → 튜닝 가능 파라미터 → 권장 범위**의 4-단 매핑을 제공한다. 각 매핑은 사용자가 시장 진단(강세/약세/횡보)과 의사결정 의도(공격/수비, 추세추종/반전)에 따라 합리적 변경 방향을 선택하도록 보조한다.

---

## 1. Theory ↔ Stage Mapping (PRD §5.3 verbatim)

### 1.1 Minervini SEPA (Specific Entry Point Analysis)

- **Stages**: Stage 1 Type A (60m/120m 4선 정배열), Stage 3 (일봉 정배열).
- **Anchor**: 정배열 허용오차 통상 -2%~-5%. 정렬 자체가 "trend 살아있다"의 핵심 시그널 → 너무 느슨하면 noise 흡수, 너무 빡빡하면 노이즈에 master 종목까지 탈락.
- **Tunable parameters**:
  - `_TYPE_A_ALIGN_TOL` (chart60_120, 0.035 = −3.5%) — Stage 1 60m+120m 동시 만족.
  - `_MA10_MA20_MA60_TOLERANCE` (chartDay, 0.05 = −5.0%) — Stage 3 일봉. 더 넓음 (daily volatility).
- **Loosen 권장 시점**: Stage 1 over-rejects (탈락률 > 70%) in 추세 시장 — Minervini 시그널이 살아있는데 단일 노이즈로 탈락.
- **Tighten 권장 시점**: Stage 1 통과 후보 noise 다수 (탈락률 < 30%) — false-positive 다수.

### 1.2 Weinstein Stage Analysis

- **Stages**: Stage 2 (240m long-term gate), Stage 1 Type B (rising-from-below 진입).
- **Anchor**: `MA60 ≥ MA306` — 장기추세 up이 핵심 전제. MA60 vs MA306 격차는 cycle phase의 indicator.
- **Tunable parameters**:
  - `_MA60_MA306_TOLERANCE` (chart240, 0.025 = −2.5%) — Stage 2 240m 베이스 인정 범위.
  - `_TYPE_B_BELOW_MA60_RATIO` (chart60_120, 0.97) — Type B 진입 zone 정의 (MA10/MA20 ≤ MA60×0.97 = 3% 아래).
  - `_ALIGN_TOL_LOOSE` (chart60_120, 0.015) — Type B/C/D 공유 (변경 시 §3 Step 2 영향 공개).
- **Loosen**: 회전(rotational) 섹터를 cycle low 부근에서 탐색할 때.
- **Tighten**: continuation pattern을 mid-bull에서 탐색 (이미 검증된 추세만).

### 1.3 Wyckoff (Smart Money Distribution)

- **Stages**: Stage 4 investorFilter (수급 flow).
- **Anchor**: 외국인/기관 연속 매도 = 분배 시그널 (Phase D-E). 개인 연속 매수 = 역발상 분배 시그널.
- **Tunable parameters**:
  - `_THRESHOLD_FOREIGN_CONSEC_SELL` (default 2일) — Phase D 외국인 분배.
  - `_THRESHOLD_INST_CONSEC_SELL` (default 8일) — 기관 느린 unwinding.
  - `_THRESHOLD_INDI_CONSEC_BUY` (default 3일) — 역발상 retail 시그널.
  - `_THRESHOLD_FOREIGN_TOTAL_SELL` (default 15/16일) — 장기 분배 패턴.
- **Loosen (= raise threshold)**: 강세장 — 단기 retail 매수는 분배 아님.
- **Tighten (= lower threshold)**: 약세/조정 — 수비적 screening.

### 1.4 VCP (Volatility Contraction Pattern — Mark Minervini / William O'Neil)

- **Stages**: Stage 1 Type C, Type E. Stage 2-1 surge exclusion도 V-rebound 위험 차단 측면에서 연관.
- **Anchor**: 수렴 폭 3.5%~10% (점진적 변동성 압축). 좁을수록 base 견고.
- **Tunable parameters**:
  - `_TYPE_C_CONVERGE_PCT` (0.035 = 3.5%) — tight VCP.
  - `_TYPE_E_SPREAD_PCT` (0.10 = 10%) — about-to-align V-rebound (wider variant).
- **Loosen**: post-IPO / post-correction base 탐색 (변동성 더 큼).
- **Tighten**: late-cycle topping base — 가짜 base 회피.

### 1.5 CANSLIM-N (Current earnings — William O'Neil)

- **Stages**: Stage 5 financeFilter — **Phase 1 튜닝 불가** (hardcoded `cup_nga < 0`).
- **Anchor**: 적자 제외 (cup_nga ≥ 0).
- **Tunable parameters**: ⚠️ none — Phase 1.
- **Phase 2 검토**: `_NET_INCOME_MIN_THRESHOLD = 0` 신설 → tuning 가능. 추가로 N (earnings growth) / A (annual earnings) / S (supply) / L (leader) / I (institutional) / M (market direction) 항목별 module 분리도 검토.

---

## 2. Market Regime Adjustment (FR-7.2)

### 2.1 강세장 (Bull market — uptrend confirmed)

진단 키워드: `"강세"` / `"상승추세"` / `"bull"`.

- **Stage 1 정배열 완화** — breakout 포착 우선. `_TYPE_A_ALIGN_TOL`를 0.035 → 0.05 (±2~3%p 완화 검토).
- **Stage 2-1 surge 강화** — 과열 종목 빈번. `_DAILY_SURGE_THRESHOLD`를 0.15 → 0.10 (-5%p 강화).
- **Stage 4 수급 완화** — retail 매수는 분배 시그널 약함. `_THRESHOLD_INDI_CONSEC_BUY`를 3 → 5일 완화 검토.

### 2.2 약세장 (Bear market — downtrend / 조정)

진단 키워드: `"약세"` / `"조정"` / `"bear"` / `"하락"`.

PRD §5.2 패턴 C (verbatim 핵심): **수비(defensive)** 트랙과 **기회(opportunistic)** 트랙 둘로 갈림. 사용자 의도 확인 후 한 트랙 권장.

**수비 트랙** (자본 보존 우선):
- `_THRESHOLD_FOREIGN_CONSEC_SELL` 2 → 1일 (수급 신호 민감).
- `_TYPE_A_ALIGN_TOL` 0.035 → 0.025 (정렬 엄격화 — 확정된 setup만).

**기회 트랙** (저점 매수 회전 종목):
- `_TYPE_A_ALIGN_TOL` 0.035 → 0.05 (정렬 완화 — 회전 candidate 포착).
- `_MA60_MA306_TOLERANCE` (Stage 2) 0.025 → 0.04 (장기추세 강화 — base 신뢰 가능 종목만).

종료 멘트 verbatim: `"어느 방향으로 가시겠습니까?"`

### 2.3 횡보장 (Sideways)

진단 키워드: `"횡보"` / `"박스권"` / `"sideways"`.

- VCP 강조 — `_TYPE_C_CONVERGE_PCT`를 0.035 → 0.025로 좁힘 (tight base 검출 우선).
- `_TYPE_E_SPREAD_PCT`를 0.10 → 0.08 (about-to-align setup 집중).
- Stage 4 default 유지.

---

## 3. Per-Parameter Recommended Ranges (FR-7.3)

`SHOW_PARAMS`로 사용자가 구체 param의 권장 범위를 요청할 때 본 표를 인용.

### Stage 1 (chart60_120Filter)

| param_id | 권장 범위 | 안전 default | 이론 anchor |
|---|---|---|---|
| `_TYPE_A_ALIGN_TOL` | 0.02 ~ 0.08 | `0.035` | Minervini SEPA −2%~−5% |
| `_ALIGN_TOL_LOOSE` (공유) | 0.01 ~ 0.05 | `0.015` | Weinstein Stage 1→2 |
| `_TYPE_B_BELOW_MA60_RATIO` | 0.93 ~ 0.99 | `0.97` | rising-from-below 3% margin |
| `_TYPE_C_CONVERGE_PCT` | 0.025 ~ 0.07 | `0.035` | VCP tight |
| `_TYPE_E_SPREAD_PCT` | 0.05 ~ 0.15 | `0.10` | VCP wider variant |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | 0.60 ~ 0.85 | `0.75` | fresh-breakout |

### Stage 2 (chart240Filter)

| param_id | 권장 범위 | 안전 default | 이론 anchor |
|---|---|---|---|
| `_MA60_MA306_TOLERANCE` | 0.015 ~ 0.05 | `0.025` | Weinstein 240m base |

### Stage 2-1 (chartDayPreFilter)

| param_id | 권장 범위 | 안전 default | 이론 anchor |
|---|---|---|---|
| `_DAILY_SURGE_THRESHOLD` | 0.08 ~ 0.20 | `0.15` | 작전주 경계 +15% |

### Stage 3 (chartDayFilter)

| param_id | 권장 범위 | 안전 default | 이론 anchor |
|---|---|---|---|
| `_MA10_MA20_MA60_TOLERANCE` | 0.03 ~ 0.10 | `0.05` | Minervini daily (volatility 반영) |
| `_MA60_MA306_LOWER_TOL` | 0.10 ~ 0.25 | `0.15` | envelope floor |
| `_CLOSE_VS_MA612_UPPER` | 0.30 ~ 0.80 | `0.50` | master 위치 허용 |

### Stage 4 (investorFilter)

| param_id | 권장 범위 | 안전 default | 이론 anchor |
|---|---|---|---|
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | 1 ~ 5일 | `2일` | Wyckoff Phase D |
| `_THRESHOLD_INST_CONSEC_SELL` | 5 ~ 12일 | `8일` | 기관 unwinding |
| `_THRESHOLD_INDI_CONSEC_BUY` | 2 ~ 6일 | `3일` | 역발상 시그널 |
| `_THRESHOLD_FOREIGN_TOTAL_SELL` | 10 ~ 16일 | `15일` | long-term distribution |

---

## 4. Data-Driven Suggestion Patterns (FR-7.4)

`WHY_REJECTED` / `COMPARE`가 명확한 패턴을 보일 때 filter-tune이 proactively 제안할 수 있는 룰. 본 Skill은 직접 적용하지 않으며, 사용자에게 제안만.

- **"Stage 1에서 80% 탈락" 패턴** → `"Type A 허용오차 완화 검토 (현재 -3.5% → -5% 시도)"`.
- **"외국인 매도 평균 1.8일" 패턴** → `"수급 임계값을 2일에서 3일로 완화 검토"`.
- **"Stage 3 envelope 하단 근처에서 다수 탈락"** → `"_MA60_MA306_LOWER_TOL 완화 검토 (-15% → -20%)"`.
- **"Stage 2-1 surge로 다수 종목 제외"** → 강세장 진단 가능 → 정배열 완화 트랙 안내.

이러한 패턴은 명확할 때만 emit. 모호하면 단순 `SHOW_RESULTS` 안내로 종료 (P4: 불필요한 자극 회피).

---

## 5. 이론 일치 검증 (사용자 요청 시)

`THEORY_GUIDE` 발화에 구체 param이 명시된 경우, 본 가이드의 §3 권장 범위 표를 인용하여 `"현재 값 {raw} ({display})은 권장 범위 {low}~{high} 내에 있습니다 (이론 anchor: {theory})"` 형식으로 응답. 권장 범위 밖이면 `"권장 범위 {low}~{high}를 벗어났습니다. 의도된 조정인지 확인해주세요."` 추가.
