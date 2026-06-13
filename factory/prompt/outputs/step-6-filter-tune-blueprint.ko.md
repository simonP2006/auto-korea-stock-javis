# Step 6 — filter-tune SKILL 블루프린트

> 생성일: 2026-05-30
> 목표 배포 경로: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/`
> 본 블루프린트로부터 Step 9 `@tune-builder`가 생성
> 스킬 커버리지: PG-2 — 파라미터 튜닝 (최상위 목표)
> 출처: PRD FR-4..FR-8 / TS-1..TS-5 / §5 / §6.4 / §7.3, workflow.md §6 (268-303행), workflow-idea B-7/B-8/B-9/B-10/B-16/B-17/B-22, Step 1 param-inventory (75개 Final 상수), Step 1 pipeline-analysis §(c) (gap-value ADR-009), Step 2 research §6/§8, Step 4 아키텍처 (경로 상수, ADR-009/010/011/012, R-9 lock 시맨틱, 스키마), Step 5 CLAUDE.md 블루프린트 (§3 라우팅, §4 TS verbatim, §5 오류 테이블)

## 블루프린트 표기 규약

- **(spec)** = Step 9 `@tune-builder`가 최종 SKILL.md에 Verbatim 복사하는 문자 그대로의 텍스트/구조
- **(source)** = 추적성 앵커 (PRD / workflow-idea / Step 산출물 / ADR)
- **(estimate)** = 최종 SKILL.md에 기여하는 대략적인 줄 수

블루프린트 자체는 700행을 초과할 수 있는데, 이는 근거, 시퀀스 세부, 분기 폴백, 참조 파일 계획을 모두 담기 때문이며 — 이 중 어느 것도 최종 SKILL.md에 그대로 상속되지 않는다. 최종 SKILL.md는 약 134행으로 추정되며 (§10 참조), 참조 파일은 6개 파일에 걸쳐 추가로 약 980행을 분담한다.

---

## §1. SKILL.md 헤더 및 발생 조건

### 프론트매터 — **(spec)**

```yaml
---
name: filter-tune
description: Kiwoom filter parameter tuning — interactive Korean-language fine-tuning with safety rails (TS-1~5 enforced). Handles SHOW_PARAMS, CHANGE_PARAM, CONFIRM, RESTORE, COMPARE_EXPERIMENTS, THEORY_GUIDE, ASK_MODULE.
model: opus
tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
maxTurns: 40
---
```

**근거**:
- `model: opus` — PRD §3 사용자 페르소나는 깊은 이론 지식을 갖춘 시니어 한국인 트레이더이다. 튜닝 대화는 Minervini/Weinstein/VCP/CANSLIM 추론 + ADR-009에 따른 `masterReference.log`로부터 gap 수치 추출을 수반한다. Sonnet은 이론 매핑 정확도를 떨어뜨릴 수 있다.
- `tools` 리스트는 `Task`를 명시적으로 제외하며 (스킬 내부에서 서브에이전트 디스패치 없음 — Skill은 메인 세션 내에서 직렬로 실행됨), TS-3 범위 위반 + TS-4 다중 파라미터 + B-7 확인 게이트를 위해 `AskUserQuestion`을 명시적으로 포함한다.
- `maxTurns: 40`은 8단계 마스터 시퀀스 (사용자 프롬프트 1회 → 내부 최대 6턴)를 수용한다. 사용자가 stock-scan을 재방문하기 전까지 튜닝 세션당 최대 약 6회 실행된다.

### CLAUDE.md 의도 테이블을 통한 발생 — **(source: Step 5 §3)**

CLAUDE.md는 다음 7개 의도 클러스터를 이 스킬로 라우팅한다:

| 클러스터 | 마스터 액션 (SKILL §3/§4) |
|---|---|
| `SHOW_PARAMS` | §4 SHOW_PARAMS 분기 |
| `CHANGE_PARAM` | §3 PARAM_CHANGE 마스터 시퀀스 (8단계) |
| `CONFIRM` | §4 CONFIRM 분기 |
| `RESTORE` | §4 RESTORE 분기 (primary + tuning-log 폴백) |
| `COMPARE` (파라미터 범위로 한정된 경우) | §4 COMPARE_EXPERIMENTS 분기 |
| `THEORY_GUIDE` | §4 THEORY_GUIDE 분기 |
| `ASK_MODULE` | §4 ASK_MODULE 분기 (Phase 2 디플렉션을 동반한 인라인 응답) |

> Step 5 §3의 혼합 의도 규칙 ("필터 바꾸고 다시 돌려줘")은 순차적으로 `CHANGE_PARAM` → 사용자 확인 → stock-scan `RERUN_FILTERS`를 트리거한다. 마스터 시퀀스 Step 8의 핸드오프가 그 이음매다.

---

## §2. 경로 상수 참조

Step 4 §1로부터 Verbatim 상속 (Step 5 블루프린트에 따라 CLAUDE.md §2에도 문서화). Skill은 이러한 shell-style 변수를 참조할 뿐 — 재정의하지 않는다. 모든 경로 보간은 Bash 호출 시점에 일어난다.

| 변수 | 값 | 본 스킬에서의 사용처 |
|---|---|---|
| `${KRT_ROOT}` | `/Users/tajun/spJavis/kiwoom-rest-trader` | 모든 `cd` 호출의 유일한 접두사 (ADR-007 venv 직접 호출 규약에 따름). |
| `${KRT_PYTHON}` | `${KRT_ROOT}/.venv/bin/python` | **본 스킬에서 호출되지 않음** — filter-tune은 Python 스크립트를 실행하지 않으며, 상수를 편집하고 파일을 읽기만 한다. (편집 후 재실행은 Step 8 핸드오프를 통해 stock-scan으로 위임된다.) |
| `${KRT_REPORTS}` | `${KRT_ROOT}/reports` | `masterReference.log`의 원본, `screener_state.json`, `tuning-log.md`, R-9 권고 잠금 `filter-tune.lock`의 대상 경로. |
| `${KRT_FILTERS}` | `${KRT_ROOT}/src/kiwoom/itemFilter` | **Edit의 유일한 쓰기 대상.** TS-1 + Step 4 §2 "Files explicitly NOT modified"에 따라 — Edit은 이 디렉터리 아래 `*.py` 파일 내부의 `Final` 상수 값으로만 한정된다. 절대 다른 경로 금지. |
| `${KRT_SCRIPTS}` | `${KRT_ROOT}/scripts` | 읽기 전용; SCAN_TODAY/RERUN_FILTERS 체인을 사용자에게 설명할 때에만 참조된다. 본 스킬에서 호출되지 않는다. |

**본 스킬 내부에서 사용되는 핵심 절대 경로 상수**:

| 경로 | 용도 |
|---|---|
| `${KRT_REPORTS}/tuning-log.md` | Append 대상 (마스터 시퀀스 Step 7). `COMPARE_EXPERIMENTS` 및 `RESTORE` 폴백에서 읽음. |
| `${KRT_REPORTS}/tuning-log.YYYYMM.md` | 활성 로그가 200행을 초과할 때의 아카이브 대상 (FR-6.6 / B-16 회전). 활성 로그에서 항목이 누락된 경우 `RESTORE` 폴백에서 읽음. |
| `${KRT_REPORTS}/screener_state.json` | 원자적 읽기/쓰기 — `last_param_changes` 배열 유지. (스키마는 Step 4 §4 참조.) |
| `${KRT_REPORTS}/filter-tune.lock` | R-9 권고 잠금 센티넬 파일. Step 5에서 생성, Step 7에서 제거. 이것이 존재하는 동안 stock-scan은 백그라운드 스캔 시작을 거부한다. |
| `${KRT_REPORTS}/{YYYYMMDD}/masterReference.log` | 읽기 전용 — ADR-009 정규식 추출에 따른 Step 3 gap-영향 추정. |

---

## §3. 마스터 튜닝 시퀀스 — `PARAM_CHANGE(param_id, new_value)` (B-22 완전 통합)

### 시퀀스 다이어그램 (참고용)

```
User: "Type A 허용오차 -5%로 완화해줘"
  │
  ▼
Step 0 [TS-4]  multi-param detection                        ──┐ if multi → warn + AskUserQuestion
  │                                                            │ if proceed → loop Steps 1-8 per param
  ▼                                                            │
Step 1 [B-9, TS-3]  Range Map lookup + Stage 5 hard-block      │
  │  ├ out-of-range → REJECT (Korean + theoretical basis)      │
  │  └ Stage 5 → REJECT (C-4: "현재 코드 구조상 변경 불가...")  │
  ▼                                                            │
Step 2 [B-17]  Shared constant impact                          │ (SHORTCUT skips Steps 2-3
  │  ├ shared → list affected Types/conditions                 │  if in-range AND not shared)
  │  └ private → skip                                          │
  ▼                                                            │
Step 3 [B-10]  masterReference.log gap analysis                │
  │  └ "약 N개 추가 통과 예상" (or "추정 데이터 없음")          │
  ▼                                                            │
Step 4 [B-7]  Confirmation table + AskUserQuestion             │
  │  ├ user 취소 → abort                                       │
  │  ├ user 다른 값 → loop Steps 1-4 with new_value            │
  │  └ user 적용 → proceed                                     │
  ▼                                                            │
Step 5 [B-8, TS-2, TS-2a, R-9]  Backup + lock acquire          │
  │  ├ acquire ${KRT_REPORTS}/filter-tune.lock                 │
  │  ├ cp {file} {file}.bak.$(date +%Y%m%d_%H%M%S)             │
  │  └ rotation: if >5 .bak files, gate on tuning-log presence │
  ▼                                                            │
Step 6  Edit Final constant value                              │
  │  ├ B-13e variable-name presence check (R-2/§5)             │
  │  ├ unit conversion (refs/unit-conversion.md)               │
  │  └ adjacent comment auto-update                            │
  ▼                                                            │
Step 7 [B-16]  tuning-log.md append + rotation + lock release  │
  │  ├ row format (FR-6.6)                                     │
  │  ├ rotate if >200 rows → tuning-log.YYYYMM.md              │
  │  ├ update screener_state.json.last_param_changes           │
  │  └ rm ${KRT_REPORTS}/filter-tune.lock                      │
  ▼                                                            │
Step 8 [TS-5]  Rerun suggestion                                │
  │  └ "필터를 다시 돌려볼까요?" → route to stock-scan RERUN_FILTERS
  ▼
END
```

### Step 0 [TS-4] — 다중 파라미터 감지 — **(spec)**

**트리거**: 사용자 메시지가 단일 턴 내에서 (한국어 이름 또는 변수명 기준으로) 2개 이상의 서로 다른 `param_id`를 참조하는 경우.

**감지 휴리스틱** (SKILL.md용 의사코드):
- 사용자 메시지를 토큰화하고, `references/parameter-catalog.md`에 대비하여 알려진 파라미터의 한국어 별칭이나 `_VARIABLE_NAME`의 출현 횟수를 센다.
- `count >= 2`이고 절들이 접속사 ("그리고", "또", "도", "와", 쉼표 나열)로 연결된 경우: 다중 파라미터 분기로 진행한다.

**한국어 경고 (verbatim, source PRD TS-4 + workflow-idea B-22 274행)**:
> `"한 번에 하나씩 변경을 권장합니다. 동시에 여러 파라미터를 바꾸면 어느 변경이 결과에 어떤 영향을 줬는지 분리하기 어렵습니다. 어떻게 진행하시겠습니까?"`

**AskUserQuestion 선택지 (3개, PRD P4 ≤4)**:
1. `"하나씩 차례대로 변경하기"` → 각 `param_id`마다 Steps 1-8을 직렬로 루프. 각 완료 후 다음을 프롬프트: `"{param_id}_N 변경이 완료됐습니다. 다음 파라미터({param_id}_N+1)를 계속 진행할까요?"` 확인 시 다음으로 진행, 거부 시 남은 항목 중단.
2. `"한 번에 모두 변경하기 (영향 추적 불가)"` → 사용자가 인과 귀속 손실을 수용; 중간 확인 없이 각 파라미터마다 Steps 1-7을 루프; Step 8은 최종에 한 번만 emit.
3. `"취소"` → 전체 PARAM_CHANGE 중단.

**멱등성**: 본 세션에서 Step 0가 이미 실행되었고 사용자가 옵션 2를 명시적으로 긍정한 경우, 동일 turn-cluster 내에서 재경고하지 않는다.

### Step 1 [B-9, TS-3] — Range Map 조회 + Stage 5 하드 차단 — **(spec)**

**작업**:

**Step 1.0 — 키워드 사전 점검 (Review#3 수정, 카탈로그 조회 BEFORE에 발동)**:
어떤 해석 시도보다 먼저, raw 사용자 발화를 스캔하여 Stage-5 / financeFilter / 당기순이익 키워드를 탐지한다. 트리거 조건 (다음 중 임의):
- 부분 문자열 `cup_nga` (대소문자 무시)
- 부분 문자열 `당기순이익` ("net income"의 한국어)
- 부분 문자열 `financeFilter` 또는 `finance_filter` 또는 `finance Filter` (대소문자 무시)
- 부분 문자열 `Stage 5` 또는 `stage5` 또는 `재무 단계` 또는 `5단계`
- 부분 문자열 `순이익` AND 변경 의도 동사 (`바꿔`, `변경`, `수정`, `튜닝`, `올려`, `내려`, `늘려`, `줄여`)

어느 하나라도 적중 시 → 아래 Step 1.2와 동일한 verbatim C-4 메시지로 REJECT하고 본 턴을 종료한다. **근거**: workflow.md §6 286행 및 PRD §5.1 Stage 5 주의사항에 따라, financeFilter는 `Final` 상수가 제로(0)이므로 — 카탈로그 조회가 실패하거나 §5 퍼지 폴백을 통해 비-Stage-5 후보를 반환하여 하드 차단을 조용히 우회할 수 있다. 키워드 사전 점검은 **1차** Stage 5 가드이며; 아래 카탈로그 기반 Step 1.2는 카탈로그가 실수로 Stage 5 파라미터를 등록한 경우를 위한 **2차** 가드다.

1. `references/parameter-catalog.md`를 통해 자연어 별칭으로부터 `param_id`를 해석한다. 실패 시 → AskUserQuestion으로 모호성 해소 (예: "60-분 정배열 허용오차" → `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` — §5 Anti-Conflation Disambiguation 참조).
2. **Stage 5 (financeFilter) 하드 차단 (C-4, 2차 가드)**: 해석된 `param_id`가 `financeFilter.py` 소유라면 (Step 1.0 사전 점검에도 불구하고 카탈로그 조회가 어떻게든 Stage 5 행을 반환한 경우), 다음과 같이 REJECT한다:
   > `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. 당기순이익 판정(cup_nga < 0)이 하드코딩 비교문이고 Final 상수가 존재하지 않습니다. Phase 2에서 상수화를 검토합니다."` (CLAUDE.md TS-1 예외 조항 및 PRD §5.1 Stage 5 주의사항으로부터 verbatim.)
   Skill은 Step 2에 진입하지 않고 본 턴을 종료한다.
3. **Range 조회**: `references/range-map.md`를 `param_id`로 키잉 → (물리적 범위, 위험 구간, 이론적 근거).
4. **범위 검사**:
   - `new_value`가 ∈ 물리적 범위 AND ∉ 위험 구간 → Step 2로 진행.
   - `new_value`가 ∈ 위험 구간 (퇴화한 필터 거동을 유발하는 물리적 범위의 부분 집합, 예: tolerance ≥ 0.30 → "사실상 필터 무력화") → 한국어 경고 + AskUserQuestion emit. PRD FR-5.5 verbatim 스타일: `"허용오차 -{X}%면 사실상 필터가 무력화됩니다. 정말 이 값으로 진행할까요?"` 선택지: (a) 그대로 진행 (b) 안전 범위 권장값으로 변경 ({suggested}) (c) 취소.
   - `new_value` ∉ 물리적 범위 → REJECT (오버라이드 경로 없음). 한국어 메시지 포맷: `"{param_korean_name}의 물리적 범위는 {range_min} ~ {range_max}입니다. 입력하신 {new_value}는 범위를 벗어났습니다. (이론적 근거: {basis})"`.

**범위 이탈 거부 예시** (SKILL 구현자를 위한 설명용; 참조 파일이 전 75개를 보유):
- `_TYPE_A_ALIGN_TOL = -0.50` → REJECT `"허용오차의 물리적 범위는 0.00 ~ 0.50입니다. 입력하신 -0.50은 범위를 벗어났습니다. (이론적 근거: tolerance는 비대칭 슬랙 폭이므로 부호는 양수, 50% 초과 시 정배열 개념 자체가 무의미)"`
- `_THRESHOLD_FOREIGN_CONSEC_SELL = 0` → REJECT `"정수 임계값의 물리적 범위는 1 ~ 16입니다. (16봉 데이터 한계). 0은 조건 자체를 끄는 의미이므로 임계값으로 부적합."`

### Step 2 [B-17] — 공유 상수 영향 — **(spec)**

**작업**:
1. `references/shared-constants.md`에서 `param_id`가 "shared constants" 레지스트리에 등록되어 있는지 확인한다.
2. **shared**인 경우 (현재 정확히 **하나**의 항목: `chart60_120Filter.py:120`의 `_ALIGN_TOL_LOOSE`): 영향 받는 모든 (Type, condition) 튜플을 나열하는 한국어 영향 공시를 emit한다. Verbatim 포맷:
   > `"⚠️ 이 상수는 공유 상수입니다. 변경 시 다음 조건들이 동시에 영향을 받습니다:`
   > ` • Type B — 120분 MA10-MA20 근접 판정`
   > ` • Type B — MA60-MA306 근접 판정`
   > ` • Type C — MA60-MA306 장기추세 leg`
   > ` • Type D — 60분 4선 정배열 fallback`
   > `특정 Type만 조정하려면 해당 Type 전용 상수 신설이 필요합니다 (TS-1 로직 변경 — 사용자 명시적 승인 필요)."`
3. **private**인 경우 (그 외 모든 param_id): 건너뛰고 — Step 3으로 직접 진행.

**출처**: PRD §5.4 verbatim 영향 리스트 + Step 1 param-inventory "Critical Distinctions" + Step 2 §6 모호성 해소 테이블.

### Step 3 [B-10] — `masterReference.log`로부터의 영향 미리보기 (ADR-009 하이브리드) — **(spec)**

**작업**:
1. 사용 가능한 최신 `masterReference.log`를 해석한다: `${KRT_REPORTS}/{latest_date}/masterReference.log`이며 `latest_date` = `screener_state.json.last_scan_date` (폴백: `reports/*/masterReference.log` 중 수정 시각이 가장 최근인 것을 glob).
2. 부재/비어있음 시: `"추정 데이터 없음 — masterReference.log이 비어있거나 부재합니다. 정확한 영향은 변경 후 run_filters 재실행으로 확인하세요."`를 ANNOUNCE한다. 이 안내문을 가지고 Step 4로 건너뛴다.
3. 존재하는 경우: ADR-009 정규식 카탈로그 (`references/gap-extractor.md` — `tuning-sequence.md`와 동거)를 호출하여, `param_id`가 변경 대상 파라미터에 해당하는 모든 행의 reason 텍스트로부터 `(actual, threshold, unit)`을 추출한다. 행별 `would_pass`를 new_value로 재계산한다.
4. 집계:
   - `parsed_total = N parsed / M total rows` (Step 4 OQ-1에 따른 투명성).
   - `delta = count(would_pass | new) - count(would_pass | current)`
   - 한국어 라인: `"masterReference.log {M}개 행 중 {N}개에서 gap 추출. {delta} {direction} (추정 정확도 {N/M*100:.0f}%)."` 여기서 `direction`은 delta > 0이면 `"개 추가 통과 예상"`, delta < 0이면 `"개 추가 탈락 예상"`, delta = 0이면 `"개 변화 없음"`.
5. `N/M < 0.5`인 경우 (Step 4 R-4 폴백 임계값): "추정 데이터 부족"으로 처리 — 안내문을 emit하고 수치 delta 없이 진행한다.

**정규식 카탈로그** (`references/tuning-sequence.md` §gap-extractor에 보관됨 — 지배적인 reason 포맷 상위 5종):
| 패턴 키 | 예시 reason 텍스트 | 추출된 명명 그룹 |
|---|---|---|
| `MA_ALIGNMENT` | `"MA60(7,195) < MA306×0.965(7,198)"` | `actual=7195`, `threshold=7198`, `unit=원` |
| `MA_BAND_PCT` | `"종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%]"` | `actual_pct=53.41`, `lower=-15.0`, `upper=50.0` |
| `DAILY_SURGE` | `"금일 일봉 +16.44% — 15% 이상 급상승"` | `actual_pct=16.44`, `threshold_pct=15.0` |
| `INVESTOR_CONSEC` | `"외국인 3회 연속 매도 (≥ 2)"` | `actual_days=3`, `threshold_days=2` |
| `FINANCE_CUP_NGA` | `"당기순이익 -70억원 < 0 (적자)"` | `actual_won=-70`, `threshold_won=0` |

### Step 4 [B-7] — 확인 — **(spec)**

**한국어 테이블 포맷** (verbatim 레이아웃, workflow-idea B-7 + PRD FR-5.6 따름):

```
| 파라미터 | 현재 값 | 변경 후 |
|---|---|---|
| {var_name} ({Korean meaning}) | {current_value_display} | {new_value_display} |
```

**표시 규약** (PRD §7.3 / CLAUDE.md §6 따름):
- Tolerance: raw (`0.035`) 및 퍼센트 폼 (`-3.5% (×0.965)`) 양쪽 렌더.
- Ratio: raw (`0.50`) 및 퍼센트 폼 (`50%`) 양쪽 렌더.
- Integer: 그대로 (`2일`) 렌더.

**경고 발생 시 부록**:
- Step 2가 shared-constant 경고를 emit했다면 → 영향 리스트 재emit (압축형: "공유 상수 — Type B/C/D 4개 조건 영향").
- Step 3이 delta를 계산했다면 → 다음을 추가: `"예상 영향: 약 {delta}개 종목 추가 통과 (추정 정확도 {N/M*100:.0f}%)"`.
- Step 3이 "추정 데이터 없음"을 announce했다면 → 다음을 추가: `"예상 영향: 추정 데이터 없음 (run_filters 재실행으로 정확한 결과 확인)"`.

**AskUserQuestion** (PRD P4에 따라 3개 옵션):
1. `"적용 (Edit 진행)"` → Step 5로 진행.
2. `"다른 값으로 시도"` → `"새로운 값을 입력해주세요"`를 묻는 후속 AskUserQuestion; 수신 시 new_value로 Steps 1-4 루프.
3. `"취소"` → 마스터 시퀀스 중단; `"변경을 취소했습니다."` emit.

### Step 5 [B-8, TS-2, TS-2a, R-9] — 회전 동반 백업 + lock 획득 — **(spec)**

**작업** (엄격한 순서로):

1. **R-9 권고 잠금 획득 (atomic — TOCTOU-safe, Review#2 수정)**:
   ```bash
   if mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null; then
     # lock acquired — proceed
     true
   else
     # contention — another instance owns the lock; refuse
     echo "BLOCKED" >&2; exit 2
   fi
   ```
   `mkdir`은 POSIX 파일시스템에서 atomic하다 (한 프로세스가 성공하고 다른 프로세스는 `EEXIST`로 실패한다). 잠금은 파일이 아닌 **디렉터리**이다 — Step 7에서 `rmdir`을 통해 해제된다. `BLOCKED` 시: 한국어 메시지 `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."`를 emit. 시퀀스 중단. 종료 코드 `2`는 stock-scan/filter-tune 오류 카탈로그와 정렬된다 (0=ok, 1=domain *Error, 2=other). (stock-scan은 이 디렉터리가 존재하는 동안 백그라운드 스캔을 대칭적으로 거부한다 — Step 4 §10 R-9 완화책.)

2. **백업 생성 (TS-2)**:
   ```bash
   cp ${KRT_FILTERS}/{file_basename} ${KRT_FILTERS}/{file_basename}.bak.$(date +%Y%m%d_%H%M%S)
   ```
   결과 백업 경로를 캡처; 이후 `screener_state.json.current_backup_files`에 추가된다.

3. **백업 회전 (TS-2a, ≤ 5 보존)**:
   ```bash
   ls -t ${KRT_FILTERS}/{file_basename}.bak.* 2>/dev/null
   ```
   - 반환된 카운트가 ≤ 5이면 → 회전 없음.
   - 카운트가 6+이면 → **가장 오래된** 백업에 대해서만:
     - `grep -l "{oldest_timestamp}" ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.*.md` → 일치가 있다면 (해당 백업이 도입한 값이 튜닝 로그에 기록되어 있다면) → `rm {oldest_backup}`.
     - 일치가 없다면 → 백업을 KEEP하고 한국어 경고 emit: `"백업 {N}개 한도를 초과했지만 가장 오래된 백업이 튜닝 로그에 기록되지 않아 보존합니다. 수동 정리를 권장합니다."` (PRD 442행에 따른 TS-2a 게이트.)

4. **상태 동기화**: `screener_state.json` 읽기 → 새 백업 경로를 `current_backup_files` 배열에 추가; 삭제된 백업 경로 제거.

### Step 6 — `Final` 상수 값 Edit — **(spec)**

**Edit 사전 검증** (R-2, B-13e — canonical 인코딩은 §5 참조):
- `grep -n '\b{variable_name}\b' ${KRT_FILTERS}/{file_path}` (단어 경계 앵커).
- 0 hits → 퍼지 폴백 + AskUserQuestion 트리거 (§5 프로토콜). 미해결 시 중단.
- ≥ 1 hits → 매치된 라인에 `Final[` 타이핑 어노테이션이 포함되어 있는지 확인. 그렇지 않다면 → REJECT `"이 변수는 Final 타입이 아닙니다. TS-1에 따라 변경할 수 없습니다."` (방어적: grep이 주석이나 독스트링과 매치하는 드문 경우를 잡는다.)

**Edit 작업**:
- Claude Code의 `Edit` 도구 사용.
- `old_string`: 현재 값을 포함한 라인 — 고유한 매치를 위한 충분한 컨텍스트로서 `: Final[type] = current_value_literal` 부분 포함.
- `new_string`: `current_value_literal`이 `new_value_literal`로 교체된 동일한 라인 (사용자-퍼센트 → raw-값 변환에 `references/unit-conversion.md` 사용).

**단위 변환 예시** (`references/unit-conversion.md`로부터 verbatim):
- 사용자가 `_TYPE_A_ALIGN_TOL`에 대해 `"-5%"`라고 말함 → `tolerance = 0.05` → 리터럴 `0.05`.
- 사용자가 `_TYPE_C_CONVERGE_PCT`에 대해 `"3%"`라고 말함 → `ratio = 0.03` → 리터럴 `0.03`.
- 사용자가 `_THRESHOLD_FOREIGN_CONSEC_SELL`에 대해 `"외국인 매도 2일"`이라고 말함 → 정수 `2` → 리터럴 `2`.

**주석 갱신 규칙 (workflow.md에 따른 agent verification #9)**:
- 상수 선언 직전 라인이 `# 이전: {old_value}` 또는 `# 마지막 변경: ...` 형태의 주석이라면, 두 번째 Edit 호출을 통해 새로운 `# 이전: {prior_old_value} (변경: YYYY-MM-DD)` 주석을 갱신하거나 추가한다. 멱등 — 절대로 중복된 끝트머리 주석을 누적하지 않는다.

**사전 점검 순서** (Step 4 §5 타이밍 다이어그램): R-10/R-11 사전 점검 `(a)/(b)/(c)`는 CLAUDE.md 세션 시작 시점에 이미 실행되었다. Step 6은 **check (e)** (변수명 존재 확인) — Edit별 가드 — 만 재실행한다.

### Step 7 [B-16] — `tuning-log.md` append + 회전 + 상태 갱신 + lock 해제 — **(spec)**

**Tuning-log 행 포맷 (PRD FR-6.6 verbatim 8-열 스키마)**:

```
| {datetime} | {param_id} | {param_name} | {old_value} | {new_value} | {stocks_passed_before} | {stocks_passed_after} | {notes} |
```

**컬럼 명세**:
- `datetime` — KST 오프셋이 포함된 ISO 8601, 포맷 `YYYY-MM-DDTHH:mm:ss+09:00`.
- `param_id` — 전체 Python 변수명, 예: `_TYPE_A_ALIGN_TOL`.
- `param_name` — `references/parameter-catalog.md`로부터의 한국어 의미, 예: `Type A 4선 정배열 허용오차`.
- `old_value` / `new_value` — raw 값 (예: `0.035`) — 사용자-퍼센트 폼이 아님. (다운스트림 정규식을 위한 영구 포맷; 사용자 노출 렌더링은 읽기 시점에 일어난다.)
- `stocks_passed_before` — Step 7 진입 시점의 `screener_state.json.last_results_summary.passed_count` 값 (PRD FR-6.6 베이스라인 출처). 포맷: 정수 또는 사전 스캔 기록이 없는 경우 `null`.
- `stocks_passed_after` — 쓰기 시점에는 플레이스홀더 `pending`. 다음 RERUN_FILTERS 완료 시 실제 정수로 갱신됨 (stock-scan Skill이 자체 SHOW_RESULTS 처리 시 교차 쓰기).
- `notes` (비고) — **최소 콘텐츠 (workflow.md에 따른 agent verification #10)**: `(motivation) | (decision_status)`. 예:
  - `Stage 1 통과율 77% 탈락에 따른 허용오차 완화 시도 | 미확정`
  - `과도한 통과 — 백업 복원 | ✓ 복원`
  - `세션 최종 결과 — 확정 | ✓ 확정` (CONFIRM 분기에서 설정)

**Atomic append**:
- Bash `>>`로 선행 `|`와 후행 `|\n`을 포함한 전체 행 사용. `tuning-log.md` 부재 시 첫 호출에서 헤더를 사전 생성 (Step 10 `@infra-validator`가 이미 헤더를 시드하므로 방어적인 처리).

**회전 (FR-6.6 + B-16 — 200행 임계)**:
- Append 직전 카운트: `wc -l ${KRT_REPORTS}/tuning-log.md` (헤더 행 제외).
- 행 카운트가 ≥ 200이면 → atomic 회전:
  ```bash
  mv ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.$(date +%Y%m).md
  # then write fresh header + new row to ${KRT_REPORTS}/tuning-log.md
  ```
- 이후 질의 (COMPARE_EXPERIMENTS, RESTORE 폴백)는 workflow-idea B-16 아카이브 검색 요구사항에 따라 `tuning-log.md` AND `tuning-log.*.md`를 모두 glob해야 한다.

**state.json 갱신**:
- `screener_state.json` 읽기 (R-7에 따른 json.JSONDecodeError 폴백).
- `last_param_changes` 배열에 추가:
  ```json
  {
    "date": "{datetime}",
    "param": "{param_id}",
    "old": {old_value},
    "new": {new_value},
    "file": "src/kiwoom/itemFilter/{file_basename}",
    "confirmed": false
  }
  ```
- Atomic write: `json.dump(state, tmp_fp)` → `mv tmp final` (Step 4 §4 atomicity 규칙 따름).

**Lock 해제 (R-9)**: `rmdir ${KRT_REPORTS}/filter-tune.lock` (Step 5 Review#2 수정에 따라 잠금은 디렉터리). `try/finally` 등가물로 래핑 (셸 시맨틱: Step 7 내 어떤 선행 단계가 오류 났더라도, 잠금 stuck을 방지하기 위해 실패 핸들러에서 제거 시도).

### Step 8 [TS-5] — 재실행 제안 — **(spec)**

**한국어 메시지 (verbatim, PRD TS-5 + workflow-idea B-22)**:
> `"변경 적용됐습니다. 필터를 다시 돌려볼까요? (run_filters 동기 실행 — 보통 1-3분 소요)"`

**라우팅**:
- 본 SKILL은 질문을 emit하고 메인 스레드로 제어를 반환한다.
- CLAUDE.md 라우팅 테이블 (§3 Step 5 블루프린트)은 `"네/응/해줘"` 확인 응답을 잡아 stock-scan `RERUN_FILTERS` 클러스터로 라우팅한다.
- 사용자가 거부한 경우 (`"아니"` / `"나중에"`): `"알겠습니다. 필요할 때 \"필터 재실행\"이라고 말씀하시면 됩니다."` emit 후 시퀀스 종료.

### SHORTCUT (B-22)

`param_id`가 범위 내 AND 공유 상수가 아닌 경우 (Step 2가 "private"를 반환):
- Step 2 건너뛰기 (emit할 shared 경고 없음).
- Step 3 건너뛰기 (여전히 조용히 계산되지만, 행별 delta는 별도의 사용자 일시정지 없이 Step 4 확인 부록에 흡수된다).
- 시퀀스는 다음과 같이 된다: 0 → 1 → 4 → 5 → 6 → 7 → 8.

**근거**: 대부분의 파라미터 (75개 중 74개)는 private이며 범위 내에 있다; 모든 확인을 8개의 명시적 단계로 게이팅하면 대화 길이가 과도해진다. Shortcut은 모든 안전 보장을 유지하는데, 이는 in-range / private의 경우 Steps 2-3이 사용자 행동을 요하는 어떤 출력도 emit하지 않기 때문이다.

---

## §4. 6개 분기 정의

아래 각 분기에는 다음이 명세된다: 트리거 (한국어 발화 클래스), 한국어 메시지 출력 골격, 내부 단계 시퀀스, 폴백 거동.

### 분기 1: `SHOW_PARAMS(stage?)` — **(source: FR-4.1, FR-4.3)**

**트리거**: `"Stage N 조건 보여줘"`, `"전체 필터 설정 요약"`, `"지금 파라미터 뭐야?"`, `"투자자 수급 임계값 알려줘"`.

**Step 1 — Stage 해석**:
- 사용자 메시지에서 stage 힌트를 파싱한다: `"Stage 1|2|2-1|3|4|5"` 또는 모듈명 (`"chart60_120"`, `"investorFilter"`) 또는 테마 문구 (`"수급"` → Stage 4, `"재무"` → Stage 5).
- 부재 / "전체"라면 → 5개 stage 모두.

**Step 1.5 — Stage 5 하드 차단 (C-4)**:
- 사용자가 암묵적 변경 의도와 함께 Stage 5 파라미터 세부를 명시적으로 요청한 경우 (`"Stage 5 조건 어떻게 바꿔?"`):
  > `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. Phase 2에서 상수화를 검토합니다."` (workflow.md 286행에 따라 verbatim)

  그 다음 읽기 전용 뷰: 현재 거동 요약 (`cup_nga < 0 → 제외`, missing → PASS — 하드코딩) 및 `references/parameter-catalog.md` Stage 5 섹션 참조.

**Step 2 — 라이브 Final 상수 읽기**:
- 범위 내 각 Stage의 파일 `${KRT_FILTERS}/{module}.py`에 대해, `grep -n 'Final\[' ${KRT_FILTERS}/{module}.py`를 사용하여 열거; 각 변수에 대해 또한 `grep -n '_VAR_NAME'`으로 현재 리터럴을 읽는다.
- 결정적으로: **절대로 `references/parameter-catalog.md`에서 값을 읽지 말 것** — 카탈로그는 문서이고; 코드가 SOT다 (PRD §5.1 SOT 선언에 따름).

**Step 3 — 한국어 테이블 포맷** (FR-4.1):

```
## Stage 1 — chart60_120Filter.py (60분/120분봉 MA 정배열)

| ID | 변수명 | 현재 값 | 한국어 의미 | 이론적 근거 |
|---|---|---|---|---|
| S1-1 | _TYPE_A_ALIGN_TOL | -3.5% (×0.965, raw=0.035) | Type A 4선 정배열 허용오차 — MA10≥MA20≥MA60≥MA306 인접 비교 시 허용 최대 하방 이격 | Minervini SEPA |
| S1-2 | _ALIGN_TOL_LOOSE ⚠️공유 | -1.5% (×0.985, raw=0.015) | (공유) Type B 120분 MA10-MA20 근접 / Type B MA60-MA306 / Type C MA60-MA306 / Type D 60분 fallback | 상승 초입 + 장기 추세 |
| ... | | | | |
```

- 유일한 공유 상수 행에 ⚠️공유 마커.
- "전체" 모드의 경우: 5개 stage 테이블을 순차적으로 렌더 (Stage 5는 읽기 전용 요약).

**Step 4 — Footer**:
- 이론 심층 분석을 위한 `references/parameter-catalog.md` 교차 참조 추가.
- `"파라미터 변경은 \"{변수명}를 {새값}으로 바꿔줘\" 같이 말씀해주세요."` 추가 (FR-4.2에 따른 UX 안내).

### 분기 2: `CHANGE_PARAM(param_id, new_value)`

이것은 §3의 마스터 시퀀스다. 별도 분기 로직 없음 — 완전성을 위해 여기 나열할 뿐이다.

### 분기 3: `CONFIRM` — **(source: FR-6.5)**

**트리거**: `"이걸로 확정할게"`, `"현재 설정 유지"`, `"지금 게 제일 나아"`, `"OK 이대로 가자"`.

**Step 1 — 마지막 파라미터 변경 위치 파악**:
- `screener_state.json` 읽기 → `last_param_changes` 배열.
- `confirmed == false`인 가장 최근 항목 식별. 없다면 → `"확정할 미확정 변경 이력이 없습니다."` emit 후 종료.

**Step 2 — tuning-log.md 마지막 행 비고 갱신**:
- `tuning-log.md`에서 `datetime`이 last_param_changes 항목의 `date`와 매치되는 행을 찾는다.
- Edit을 사용하여 `notes` 컬럼에 접미사 `| ✓ 확정`을 설정한다 (이전 motivation 텍스트 보존).
- 행이 아카이브된 `tuning-log.YYYYMM.md`에 있는 경우 (변경과 확정 사이에 회전이 발생함 — 드물지만 가능): 대신 아카이브 파일을 편집한다.

**Step 3 — state.json 갱신**:
- 매치된 항목에 `last_param_changes[*].confirmed = true` 설정.
- Step 4 §4에 따른 atomic write.

**Step 4 — 한국어 ack**:
> `"현재 설정이 확정되었습니다."` (workflow.md 287행에 따라 verbatim FR-6.5)

### 분기 4: `RESTORE` — **(source: FR-6.4 + B-8 폴백)**

**트리거**: `"원래대로 되돌려줘"`, `"이전 값으로 복원"`, `"백업으로 돌려놔"`, `"{N분 전} 값으로 돌려"`.

**Step 1 — 대상 파일 해석**:
- 사용자 메시지가 파일/파라미터 힌트를 포함하면 → 단일 `{file_basename}`으로 해석.
- 모호하다면 → AskUserQuestion: `"어떤 파라미터를 복원할까요?"` — `last_param_changes` 중 가장 최근 항목 상위 3개를 나열.

**Step 2a — Primary 경로: 백업 glob**:
```bash
ls -t ${KRT_FILTERS}/{file_basename}.bak.* 2>/dev/null | head -1
```
- 출력이 비어있지 않다면 → primary 경로:
  - 한국어 확인: `"가장 최근 백업({backup_path})에서 복원합니다. 진행할까요?"` AskUserQuestion (예/아니).
  - 예 시: R-9 lock 획득 → `cp {backup_path} ${KRT_FILTERS}/{file_basename}` → lock 해제.
  - `tuning-log.md`에 RESTORE 항목 추가: `| {datetime} | {param_id} | {korean_meaning} | {current_before_restore} | {restored_value} | ... | 복원 (from {backup_filename}) | ✓ 복원 |`.
  - `screener_state.json.last_param_changes`에 `confirmed=true`로 추가 (복원은 사용자 의도에 의해 암묵적으로 확정된 것으로 본다).
  - 한국어 ack: `"{file_basename}을 {backup_timestamp} 시점 백업으로 복원했습니다."`

**Step 2b — 폴백 경로: tuning-log → Edit (B-8 폴백, KEY FEATURE)**:

이것은 `*.bak.*` 파일이 존재하지 않을 때 (회전으로 빠지거나, 수동 삭제되었거나, 애초에 생성된 적이 없는 경우) 작동한다. 이것이 FR-6.4의 **결정적 회복력 기능**이다 — 이것이 없다면 백업 회전 이후 파라미터 손실은 되돌릴 수 없다.

알고리즘:
1. `tuning-log.md` 및 모든 `tuning-log.YYYYMM.md` 아카이브를 읽는다 (가장 최근 변경 이력이 재구성 가능하도록 오래된 순으로 순회).
2. 대상에 매치되는 `param_id`로 행을 필터링한다.
3. 시간순으로 현재 값 직전의 마지막 행을 식별한다 — 그 행의 `old_value` 컬럼이 복원 대상이다.
4. **B-13e 변수명 확인** (§5) — `param_id`가 동일한 라인의 코드에 여전히 존재함을 확인.
5. AskUserQuestion: `"⚠️ 백업 파일이 없어 튜닝 로그에서 이전 값을 찾았습니다: {old_value_in_log}. Edit으로 직접 복원할까요? (.bak 파일이 없으므로 다시 변경하면 이 단계 이전 값으로는 돌아갈 수 없습니다.)"` 선택지: (a) 진행 (b) 다른 행 선택 (c) 취소.
6. 진행 시: R-9 lock 획득 → 상수 Edit → lock 해제.
7. 한국어 ack (workflow.md 288행에 따라 verbatim):
   > `"백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다. ({param_id}: {current_was} → {restored_to})"`
8. `tuning-log.md`에 RESTORE 항목을 다음 notes로 추가: `"로그 기반 복원 (백업 부재) | ✓ 복원"`.

**Step 2c — 두 경로 모두 실패**:
- `*.bak.*`도 `param_id`에 대한 튜닝 로그 행도 존재하지 않음.
- 한국어 메시지: `"{param_id}의 백업도, 변경 이력도 찾을 수 없습니다. 현재 값이 최초 설정값으로 보입니다. 참조용 PRD §5.1 카탈로그 값({prd_catalog_value})으로 강제 복원하시겠습니까?"` AskUserQuestion → 수락 시, `new_value = prd_catalog_value`로 forward PARAM_CHANGE (마스터 시퀀스 Steps 0-8)로 처리.

### 분기 5: `THEORY_GUIDE(stage?, context?)` — **(source: FR-7)**

**트리거**: `"약세장에서는 어떻게 바꿔야 해?"`, `"정배열 이론적 근거"`, `"Minervini 기준이 뭐야?"`, `"VCP가 무슨 뜻이야?"`.

**Step 1 — 컨텍스트 해석**:
- 이론명 (`Minervini` / `Weinstein` / `Wyckoff` / `VCP` / `CANSLIM`), stage 표시자, 시장 국면 키워드 (`강세` / `약세` / `횡보`)를 파싱.

**Step 2 — `references/theory-guide.md` 읽기**:
- 매치된 섹션을 verbatim으로 렌더한다. Theory-guide.md 구조 (PRD §5.3에 따름):

| 이론 | Stage 매핑 | 앵커 참조 |
|---|---|---|
| Minervini SEPA | Stage 1 Type A, Stage 3 | 정배열 허용오차 통상 -2%~-5% |
| Weinstein Stage Analysis | Stage 2 (240m), Stage 1 Type B | MA60≥MA306 기준 |
| Wyckoff | Stage 4 (수급 조건) | 스마트머니 이탈 징후 |
| VCP (Volatility Contraction) | Stage 1 Type C/E, Stage 2-1 (preexclusion) | 수렴 폭 3.5%~10% |
| CANSLIM-N (Current earnings) | Stage 5 (당기순이익) | 적자 제외 (Phase 2 상수화 필요) |

**Step 3 — 시장 국면 가이던스 (FR-7.2)**:
- 사용자가 `약세`를 언급하는 경우: PRD §5.2 패턴 C (386-393행)를 verbatim으로 emit — 방어적 (수급 강화) vs 기회주의적 (정배열 완화 + 장기추세 강화) 2-트랙 가이던스, `"어느 방향으로 가시겠습니까?"`로 종료.
- 사용자가 `강세`를 언급하는 경우: 미러 — 과열 필터 강화 (Stage 2-1 급등 임계값을 +10%로) + 돌파 포착을 위한 정배열 완화 권장.
- 사용자가 `횡보`를 언급하는 경우: 중간 지점 — VCP 수렴 감지 강조 (Stage 1 Type C, 더 빠듯한 VCP 포착을 위해 `_TYPE_C_CONVERGE_PCT`를 2.5%로 낮춤).

**Step 4 — 파라미터-이론 연결 테이블** (FR-7.3):
- 사용자가 `"이 파라미터 권장 범위가 뭐야?"`라고 묻는 경우 (param이 구체적인 경우): 이론적 인용과 함께 `references/theory-guide.md` 파라미터별 권장 범위를 emit.

### 분기 6: `ASK_MODULE(module_name)` — **(source: PRD §6.4 + workflow.md 290행)**

**트리거**: `"stageMasterFilter는 뭐야?"`, `"chart60Filter는 왜 있어?"`, `"다른 필터도 있어?"`.

**Step 1 — 모듈 식별**:
- 사용자 입력을 9개 활성 모듈 + `Filter_condition_update.py`에 대해 매치.

**Step 2 — 설명**:

| 모듈 | 역할 | Phase 1 튜닝 상태 |
|---|---|---|
| `chart60_120Filter.py` | Stage 1 — Type A/B/C/D/E 패턴 감지 | **활성 튜닝 대상** |
| `chart240Filter.py` | Stage 2 — 240m 장기 추세 | **활성 튜닝 대상** |
| `chartDayPreFilter.py` | Stage 2-1 — 당일 급등 제외 | **활성 튜닝 대상** |
| `chartDayFilter.py` | Stage 3 — 일봉 MA 정배열 + MA612 밴드 | **활성 튜닝 대상** |
| `investorFilter.py` | Stage 4 — 외국인/기관/개인 수급 | **활성 튜닝 대상** |
| `financeFilter.py` | Stage 5 — 당기순이익 | ⚠️ Phase 2 (하드코딩, Final 상수 없음) |
| `chart60Filter.py` | 독립 strict 60m MA 정배열 (메인 파이프라인에 포함되지 않음; 파싱 헬퍼 용도로만 chart60_120Filter가 재임포트) | Phase 1 프로덕션 파이프라인에 포함되지 않음 |
| `Filter_condition_update.py` | masterReference.log writer (오케스트레이션 헬퍼) | **튜닝 가능 임계값 없음** — 구조적 전용 |
| `stageMasterFilter.py` | Phase 2 모듈 — 4-feature 밴드 커버리지 확장 | **Phase 1에서 제외됨** (PRD §6.4에 따름) |

**Step 3 — `stageMasterFilter.py`에 대한 Phase 2 디플렉션**:
- 한국어 메시지: `"stageMasterFilter.py는 별도 누적-확장 풀(positive coverage) 산출용 모듈입니다. 현재 5-Stage 파이프라인과 독립적으로 동작하며, Phase 1에서는 파라미터 튜닝 대상에서 제외됩니다. Phase 2 안정화 이후 검토 예정입니다."`

### 분기 7: `COMPARE_EXPERIMENTS` — **(source: workflow.md 291행 + B-16 조합 뷰)**

**트리거**: `"이 세션 실험 결과 정리해줘"`, `"여러 설정 비교"`, `"오늘 튜닝 기록 보여줘"`, `"어떤 설정이 통과 가장 많았어?"`.

**Step 1 — 출처 읽기** (B-16에 따라 `tuning-log.md`가 유일한 데이터 출처):
- 활성 `tuning-log.md` 읽기.
- 사용자 메시지가 더 긴 윈도우를 명시하는 경우 (`"이번 달"` / `"지난 달"`): 매치되는 `tuning-log.YYYYMM.md` 아카이브도 추가로 읽음.

**Step 2 — 범위 필터링**:
- `"이 세션"` (기본 범위) → `datetime ≥ session_start_time`인 항목 (session_start는 `screener_state.json.last_scan_date` 경계 또는 state가 null이면 첫 행의 날짜로부터 도출).
- `"오늘"` → 오늘 일자 항목 (KST).
- `"이번 달"` → 현재 YYYYMM 내 일자 항목.

**Step 3 — 한국어 비교 테이블**:

```
## 이 세션 튜닝 실험 비교

| # | 변경 시각 | 파라미터 | 변경 전 → 후 | 통과 변화 | 비고 |
|---|---|---|---|---|---|
| 1 | 2026-05-30 14:23 | _TYPE_A_ALIGN_TOL (Type A 정배열 허용오차) | 0.035 → 0.05 | 17 → 22 (+5) | Stage 1 통과율 완화 | 미확정 |
| 2 | 2026-05-30 14:41 | _TYPE_E_SPREAD_PCT (Type E 수렴 폭) | 0.10 → 0.08 | 22 → 19 (-3) | E 과잉 통과 조정 | 미확정 |
| 3 | 2026-05-30 15:02 | _THRESHOLD_FOREIGN_CONSEC_SELL (외국인 연속매도) | 2 → 3 | 19 → 24 (+5) | 약세장 수급 완화 | ✓ 확정 |
```

**Step 4 — 한국어 서술 요약** (FR-6.3):
- `stocks_passed_after`가 최대인 행 식별 → "가장 통과 종목 많았던 설정"으로 권장하되, FR-8에 따라 이것이 투자 권유가 **아님**을 명시.
- `✓ 확정`으로 표시된 행 식별 → 사용자 앵커로 강조.
- 어떤 행이라도 `stocks_passed_after = pending`인 경우 (사용자가 해당 변경 후 RERUN_FILTERS를 실행하지 않음) → 안내문 emit.

**Step 5 — 면책조항** (FR-8.1):
- CLAUDE.md §6 단문 규칙에 따라 끝에 한 줄: `"(투자판단·책임은 본인에게 있습니다)"`.

---

## §5. 파라미터 변수명 검증 (B-13e / R-2)

매 `Edit` 호출 전에 (마스터 시퀀스의 Step 6, RESTORE primary 경로의 Step 2, RESTORE 폴백의 Step 6 등가):

### Canonical 검증 프로토콜

```bash
grep -n '\b{variable_name}\b' ${KRT_FILTERS}/{file_path}
```

**결정 트리**:
1. **≥ 1 hit AND 라인에 `Final[` 포함** → Edit 진행.
2. **≥ 1 hit BUT 매치된 어떤 라인에도 `Final[` 없음** → REJECT `"이 변수는 Final 타입이 아닙니다. TS-1에 따라 변경할 수 없습니다."` (주석 / 독스트링을 잡는다.)
3. **0 hits** → 퍼지 폴백 진입:
   - `grep -in '{partial_name_trimmed_of_underscores_and_caps}' ${KRT_FILTERS}/{file_path}` — 대소문자 무시 부분 매치.
   - 한국어로 상위 3개 후보를 렌더:
     > `"⚠️ '{variable_name}' 변수를 찾지 못했습니다. 변수명이 변경된 것 같습니다. 다음 후보들이 있습니다:`
     > `  • {candidate_1} (line {N1})`
     > `  • {candidate_2} (line {N2})`
     > `  • {candidate_3} (line {N3})`
     > `어떤 변수를 변경할까요?"`
   - AskUserQuestion 4개 선택지: 상위 3개 후보 + `"취소"`.

**Anti-Conflation Disambiguation (Step 1 §Critical Distinctions에 따름)**:

사용자 메시지가 모호한 한국어 문구를 포함하는 경우, 해석 전에 AskUserQuestion을 강제한다:

| 모호한 한국어 문구 | 가능한 변수 | 모호성 해소 질문 |
|---|---|---|
| `"60분 정배열 허용오차"` | `_ALIGN_TOL_LOOSE` (chart60_120Filter.py, 0.015, Type B/C/D 공유) vs `_MA_ALIGNMENT_TOLERANCE` (chart60Filter.py, 0.005, 독립 strict) | `"두 가지 다른 변수가 있습니다: (1) chart60_120Filter의 Type B/C/D 공유 허용오차 (-1.5%) vs (2) chart60Filter 단독 모듈 4선 정배열 (-0.5%). 어느 쪽을 변경할까요?"` |
| `"평가 봉 수"` | `_REQUIRED_CONSECUTIVE_BARS` (chart60Filter, chart240Filter, chartDayFilter에서 선언 — 모두 현재 3, 모두 독립) | `"세 개 모듈에서 독립적으로 선언되어 있습니다: chart60 / chart240 / chartDay. 어느 Stage의 윈도우 크기를 바꿀까요?"` |
| `"MA60-MA306 허용오차"` | `_MA60_MA306_TOLERANCE` (chart240, 0.025) vs `_MA60_MA306_LOWER_TOL` (chartDay, 0.15) vs `_TYPE_E_MA60_OVER_MA306_TOL` (chart60_120 Type E, 0.035) | `"세 가지 다른 시간프레임에 있습니다: (1) Stage 2 240분 (-2.5%) (2) Stage 3 일봉 하한 (-15%) (3) Stage 1 Type E 전용 (-3.5%). 어느 쪽인가요?"` |
| `"창 크기"` / `"윈도우"` | `_REQUIRED_STATIC_BARS` (8) vs `_REQUIRED_CONSECUTIVE_BARS` (세 모듈에서 3) vs `_REQUIRED_BARS` (16, investor) vs `_TYPE_D_DYNAMIC_WINDOW` (16) | 4행 테이블 렌더; 사용자에게 선택 요청. |

**근거**: Step 1 param-inventory는 혼동이 발생하면 전체 stage를 조용히 잘못 튜닝할 수 있는 4+개 유사 명칭 그룹을 문서화한다. 검증 프로토콜은 어떤 Edit 전에도 단일 질문 게이트를 강제한다.

---

## §6. 백업 / 복원 프로토콜 (TS-2 / TS-2a)

| 액션 | 명령 | 명명 규약 | 비고 |
|---|---|---|---|
| **Create** | `cp ${KRT_FILTERS}/{file} ${KRT_FILTERS}/{file}.bak.$(date +%Y%m%d_%H%M%S)` | `{file}.bak.20260530_142345` | 마스터 시퀀스의 Step 5. 명명 포맷은 `ls -t` 정렬 + tuning-log 타임스탬프 join을 위해 **필수**. |
| **List** | `ls -t ${KRT_FILTERS}/{file}.bak.*` | 최신순 | RESTORE primary 경로 + Step 5 회전 카운트에 사용. |
| **Rotate** | 카운트 > 5이면 → `grep -l '{oldest_ts}' ${KRT_REPORTS}/tuning-log.md ${KRT_REPORTS}/tuning-log.*.md` → 매치 시: `rm {oldest}`. 매치 없으면: KEEP + 경고. | 로그 확인 후에만 | TS-2a 게이트 (PRD 442행). |
| **Restore (primary)** | `cp ${KRT_FILTERS}/{file}.bak.{newest_ts} ${KRT_FILTERS}/{file}` | 최신 .bak | RESTORE 분기 Step 2a. |
| **Restore (fallback)** | `tuning-log.md` + 아카이브 읽기 → `param_id`에 대한 마지막 행 식별 → 그 행의 `old_value` 컬럼으로 상수 Edit | .bak 없을 때 | B-8 폴백 (workflow.md 288행에 따른 KEY FEATURE). |

**Lock 시맨틱** (R-9):
- 백업 생성, Edit, tuning-log append는 Step 5에서 Step 7까지 보유되는 `filter-tune.lock` 센티넬 아래에서 atomic하다.
- stock-scan은 어떤 백그라운드 `run_full_research_flow` / `run_prefetch`를 시작하기 전에 `filter-tune.lock` 존재를 읽고 다음으로 거부한다: `"⚠️ 파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."` (Step 4 R-9 완화책 verbatim.)

---

## §7. `references/` 파일 계획 (스킬 검증 요구사항에 따라 ≥ 6 파일)

### `references/parameter-catalog.md` (~300행)

**용도**: Step 1 param-inventory로부터의 모든 75개 `Final` 상수에 대한 문서 참조. 현재 값에 대한 SOT가 **결코 아님** — 코드가 항상 런타임에 라이브로 읽힘.

**구조**:
- Stage별 그룹화 (0 / 1 / 1-adjacent / 2 / 2-1 / 3 / 4 / 5).
- 파라미터별: 변수명, file:line, 이론적 한국어 의미, PRD §5.1 ID 앵커, 이론적 근거 인용 (Minervini/Weinstein 등), 유사 명칭 형제 교차 참조.
- 상단에 명시적인 **"current value source: live code via grep — do NOT cite this file as authoritative"** 면책조항.

**커버리지**: Step 1 param-inventory §Coverage Self-Check에 열거된 75개 상수 전부를 포함해야 한다. 문서 전용 상수 (파일명, 정규식, 라벨, 디스패치 테이블 등)는 완전성을 위해 포함되지만 명시적으로 `# 튜닝 비대상 (구조/식별)`로 표시된다.

### `references/range-map.md` (~150행)

**용도**: Step 1로부터의 모든 75개 상수 (모든 Stage 0-4 + Stage 5 명시적 하드 차단 행)를 커버하는 TS-3 범위 검증 조회 테이블.

**행별 구조**:
| param_id | physical_range | danger_zone | warning_korean | basis |
|---|---|---|---|---|
| `_TYPE_A_ALIGN_TOL` | 0.00 ~ 0.50 | ≥ 0.30 | `"허용오차 -30%는 사실상 필터 무력화"` | Minervini -2%~-5% 권장; > 30% 신호 손실 |
| `_ALIGN_TOL_LOOSE` | 0.00 ~ 0.30 | ≥ 0.15 | `"15%는 정배열 개념 자체가 무력화"` | Stage 1 공유 — Type B/C/D 팬아웃 (Type A보다 좁은 위험 구간) |
| `_TYPE_B_BELOW_MA60_RATIO` | 0.50 ~ 1.00 | ≤ 0.85 or ≥ 1.00 | `"0.85 이하면 거의 모든 종목 통과 (조건 무력화)"` | Weinstein Stage 1→2 — MA60 3% 아래가 canonical |
| `_TYPE_C_CONVERGE_PCT` | 0.00 ~ 0.30 | ≥ 0.10 | `"수렴 폭 10% 초과면 VCP 수렴 개념 아님"` | PRD §5.3에 따라 VCP 3.5%~10% |
| `_TYPE_E_SPREAD_PCT` | 0.00 ~ 0.30 | ≥ 0.20 | `"확산 폭 20% 초과면 정배열 직전 의미 없음"` | VCP 더 넓은 변형 |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 0.0 ~ 1.0 | ≤ 0.20 or ≥ 0.90 | `"비율 90% 이상이면 거의 모든 종목 탈락"` | 60일선 지지 지속성 |
| `_DAILY_SURGE_THRESHOLD` | 0.05 ~ 0.30 | ≤ 0.05 or ≥ 0.30 | `"+30% 이상은 상한가 부근 — 의미 없음"` | 작전주 경계 +15% canonical |
| `_THRESHOLD_FOREIGN_CONSEC_SELL` | 1 ~ 16 | ≥ 12 | `"12일 이상은 거의 모든 종목 탈락"` | Wyckoff 스마트머니 분배 |
| `_THRESHOLD_INDI_CONSEC_BUY` | 1 ~ 16 | ≤ 1 | `"1일은 통상 매수가 매수 시그널이 아님"` | 역발상 신호 |
| `_MA60_MA306_LOWER_TOL` | 0.00 ~ 0.50 | ≥ 0.40 | `"하한 -40% 이하면 깊은 하락 종목도 통과"` | Stage 3 엔벨로프 |
| ... (75개 전체 커버) |

**커버리지 요구사항**: Step 1에서 식별된 75개 상수 전체를 Stage별로 그룹화하여 언급해야 한다. 위의 10개 예시는 대표적인 것이며; 파일은 권위 있게 전체 TS-3 범위 게이트를 인코딩한다.

### `references/unit-conversion.md` (~30행)

**용도**: tolerance ↔ multiplier ↔ user-percent 변환의 SOT. 마스터 시퀀스의 Step 6 + 확인 테이블 렌더링의 Step 4에 사용.

**콘텐츠**:

```
# Unit Conversion (TS-1 안전성 보장)

## tolerance ↔ multiplier ↔ user-percent (3가지 폼)

- `tolerance = 1 - multiplier`
- `multiplier = 1 - tolerance`
- `user_pct = tolerance × 100`
- `tolerance = user_pct / 100`

## Examples

| User says | tolerance (raw) | multiplier (×) | user-percent display |
|---|---|---|---|
| "-5%로 완화" | 0.05 | 0.95 | -5.0% (×0.95) |
| "-3%로 완화" | 0.03 | 0.97 | -3.0% (×0.97) |
| "-1.5%" (현재 _ALIGN_TOL_LOOSE) | 0.015 | 0.985 | -1.5% (×0.985) |
| "-3.5%" (현재 _TYPE_A_ALIGN_TOL) | 0.035 | 0.965 | -3.5% (×0.965) |
| "-15%" (Stage 3 _MA60_MA306_LOWER_TOL) | 0.15 | 0.85 | -15.0% (×0.85) |
| "+45%" (Stage 3 upper band) | 0.45 (literal in code) | 1.45 | +45.0% (×1.45) |
| "+50%" (Stage 3 _CLOSE_VS_MA612_UPPER) | 0.50 | 1.50 | +50.0% (×1.50) |

## Ratio constants (NOT tolerances)

These are pure fractions and use NO sign convention:

| Variable | Korean | Raw | Display |
|---|---|---|---|
| `_TYPE_B_BELOW_MA60_RATIO` | MA60 대비 상한 비율 | 0.97 | 3% 이상 아래 (97% 미만) |
| `_TYPE_D_CLOSE_OVER_MA60_RATIO` | 60분 close>MA60 비율 | 0.50 | 50% |
| `_TYPE_E_CLOSE_OVER_MA60_RATIO` | 60분 MA60 위 지지 | 0.75 | 75% |
| `_DAILY_SURGE_THRESHOLD` | 일봉 등락률 상한 | 0.15 | +15% |

## Convergence percent (raw = display/100)

| Variable | Raw | Display |
|---|---|---|
| `_TYPE_C_CONVERGE_PCT` | 0.035 | 3.5% |
| `_TYPE_E_SPREAD_PCT` | 0.10 | 10% |

## Integer thresholds

No conversion — value is bare integer (days/bars/count).
```

### `references/shared-constants.md` (~50행)

**용도**: Step 2 (B-17) 공유 상수 조회. 현재 단일 공유 상수 + 유사 명칭에 대한 anti-conflation 테이블 (Step 1 §Critical Distinctions에 따름).

**콘텐츠 스케치**:

```
# Shared Constants Registry

## Active shared constants (B-17 trigger)

### _ALIGN_TOL_LOOSE — chart60_120Filter.py:120 — value 0.015 (-1.5%)
**Affected (Type, condition) tuples**:
- Type B: 120분 MA10-MA20 근접 판정 (S1-2)
- Type B: MA60-MA306 근접 판정 (S1-4)
- Type C: MA60-MA306 장기추세 leg
- Type D: 60분 4선 정배열 fallback (when strict 60m alignment fails)

**When variant needed**: see PRD §5.4 — TS-1 conflict (would require Final 신설) — requires explicit user 승인.

## Anti-conflation pairs (NOT shared but look alike — disambiguation required)

| Pair | Files | Discrimination criterion |
|---|---|---|
| `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` | chart60_120Filter:120 vs chart60Filter:75 | "60-분 정배열 허용오차" — chart60_120 (Stage 1 production) is the default |
| `_REQUIRED_CONSECUTIVE_BARS` (3-way independent) | chart60:78, chart240:81, chartDay:72 | Each scoped to its module; tuning one does NOT propagate |
| `_MA60_MA306_TOLERANCE` vs `_MA60_MA306_LOWER_TOL` vs `_TYPE_E_MA60_OVER_MA306_TOL` | chart240:78 vs chartDay:63 vs chart60_120:156 | 3 different timeframes (240m / daily / 120m Type E) |
| `_TYPE_D_DYNAMIC_WINDOW` vs `_TYPE_E_DYNAMIC_WINDOW` | both chart60_120 | window sizes 16 vs 8 for different ratios (50% vs 75%) |
| `_STOCK_DIR_PATTERN` (5 modules) | chart60, chartDay, investor, finance, +re-imports | Logically identical regex; structurally independent declarations |
```

### `references/theory-guide.md` (~250행)

**용도**: FR-7 이론 매핑 + 시장 국면 가이던스. THEORY_GUIDE 분기에서 읽음.

**구조**:

```
# Theory Guide — 이론 기반 파라미터 튜닝

## 1. Theory ↔ Stage Mapping (PRD §5.3 verbatim)

### Minervini SEPA (Specific Entry Point Analysis)
- **Stages**: Stage 1 Type A (60m/120m 4선 정배열), Stage 3 (일봉 정배열)
- **Anchor**: 정배열 허용오차 통상 -2%~-5%
- **Tunable parameters**:
  - `_TYPE_A_ALIGN_TOL` (Stage 1) — recommend keep at -2%~-5%
  - `_MA10_MA20_MA60_TOLERANCE` (Stage 3) — wider OK because daily volatility is larger
- **Loosen when**: Stage 1 over-rejects in trending market (>70% drop)
- **Tighten when**: too many noisy candidates (Stage 1 < 30% drop)

### Weinstein Stage Analysis
- **Stages**: Stage 2 (240m long-term), Stage 1 Type B (rising-from-below)
- **Anchor**: MA60 ≥ MA306 — long-term trend up
- **Tunable parameters**:
  - `_MA60_MA306_TOLERANCE` (Stage 2) — recommend -2%~-3%
  - `_TYPE_B_BELOW_MA60_RATIO` — entry zone definition
- **Loosen when**: scanning rotational sectors at cycle low
- **Tighten when**: scanning continuation patterns mid-bull

### Wyckoff (Smart Money Distribution)
- **Stages**: Stage 4 (investor flow)
- **Anchor**: foreign / institutional sell sequences signal distribution
- **Tunable parameters**:
  - `_THRESHOLD_FOREIGN_CONSEC_SELL` (default 2 days) — Wyckoff Phase D signal
  - `_THRESHOLD_INST_CONSEC_SELL` (default 8 days) — slower institutional unwinding
  - `_THRESHOLD_INDI_CONSEC_BUY` (default 3 days) — contrarian retail signal
- **Loosen (= raise threshold)**: bull market — retail buying not yet distributive
- **Tighten (= lower threshold)**: bear/correction — defensive screening

### VCP (Volatility Contraction Pattern)
- **Stages**: Stage 1 Type C, Type E
- **Anchor**: 수렴 폭 3.5%~10%
- **Tunable parameters**:
  - `_TYPE_C_CONVERGE_PCT` — tight VCP (default 3.5%)
  - `_TYPE_E_SPREAD_PCT` — about-to-align V-rebound (default 10%)
- **Loosen when**: scanning post-IPO / post-correction setup base
- **Tighten when**: late-cycle topping bases

### CANSLIM-N (Current earnings)
- **Stages**: Stage 5 (financeFilter) — currently NOT tunable in Phase 1
- **Anchor**: 적자 제외 (cup_nga ≥ 0)
- **Tunable parameters**: ⚠️ none (hardcoded). Phase 2 consideration: add `_NET_INCOME_MIN_THRESHOLD = 0` and expose for tuning.

## 2. Market Regime Adjustment (FR-7.2)

### 강세장 (Bull market — uptrend confirmed)
- Loosen Stage 1 alignment (favour breakout capture)
- Tighten Stage 2-1 surge threshold (more frequent overheating)
- Loosen Stage 4 investor flow (retail buying less distributive)

### 약세장 (Bear market — downtrend or post-correction)
- (Defensive) Tighten Stage 4 — foreign sell ≥ 1 day
- (Defensive) Tighten Stage 1 alignment — only fully-confirmed setups
- (Opportunistic) Loosen Stage 1 + tighten Stage 2 — bottom-fishing rotational candidates

### 횡보장 (Sideways)
- Emphasize VCP — lower `_TYPE_C_CONVERGE_PCT` to 2.5% for tighter base detection
- Lower `_TYPE_E_SPREAD_PCT` to 7-8% — focus on about-to-align setups

## 3. Per-Parameter Recommended Ranges (FR-7.3)

Per-Stage tables citing theoretical anchor + recommended low/high bounds (avoid danger zone) + canonical default. Coverage: every actively tunable parameter from Stages 1-4 (~25 rows).

## 4. Data-Driven Suggestion Patterns (FR-7.4)

When user invokes WHY_REJECTED or COMPARE → filter-tune may proactively suggest tuning if the data shows a clear pattern:
- "Stage 1에서 80% 탈락" → "Type A 허용오차 완화 검토"
- "외국인 매도 평균 1.8일" → "수급 임계값을 2일에서 3일로 완화 검토"
```

### `references/tuning-sequence.md` (~200행)

**용도**: 마스터 시퀀스 (8 단계) + 모든 6 분기 + ADR-009 gap-extractor 정규식 카탈로그의 verbose 인코딩. 간결한 SKILL.md §3의 "long-form" 동반 문서.

**구조**:
- §A 마스터 시퀀스 흐름도 (텍스트) + 단계별 체크포인트 리스트
- §B 6개 분기 흐름도
- §C TS-1~5 enforcement 매트릭스 (단계별 / 분기별)
- §D 작업 예시를 동반한 ADR-009 gap-extractor 정규식 카탈로그
- §E 오류 복구 핸들러 (R-9 lock 경합, R-7 state.json 손상, B-13e 변수명 변경, B-8 백업 고갈)
- §F 한국어 메시지 라이브러리 (verbatim 문자열) — 번역 검토를 위해 모든 사용자 노출 문자열을 통합 (FR-8 framing pass)

**특별한 역할**: 이 파일은 workflow.md Step 7의 @reviewer가 Step 1 param-inventory + PRD §5.5 + Step 4 ADR들에 대해 완전성을 검증하기 위해 교차 참조하는 파일이다.

---

## §8. 안전 규칙 enforcement 지점 (Step 5 §4로부터 verbatim 인용)

5개 PRD 안전 규칙 + TS-2a + R-9는 §3 마스터 시퀀스 및 §4 분기의 특정 지점에서 enforce된다:

| 규칙 | enforce 위치 | SKILL.md 앵커 |
|---|---|---|
| **TS-1** ("Final 상수 값만 변경") | §3 Step 6 — 매치된 라인의 `Final[` 부분 문자열 존재로 Edit 게이팅. §3 Step 1의 Stage 5 하드 차단. | §3 Step 1 + Step 6 |
| **TS-2** ("변경 전 백업") | §3 Step 5 — 어떤 Edit 전이든 `cp`. 상태 `current_backup_files` 배열도 갱신. | §3 Step 5 |
| **TS-2a** ("백업 5개 한도 + tuning-log 게이트") | §3 Step 5 — 회전 게이트: `tuning-log.md` + 아카이브에 대한 `grep -l`. | §3 Step 5 (회전 블록) |
| **TS-3** ("범위 검증") | §3 Step 1 — Range Map 조회 동반 REJECT (out-of-range) 또는 warn + AskUserQuestion (위험 구간). | §3 Step 1 |
| **TS-4** ("한 번에 하나") | §3 Step 0 — 다중 파라미터 감지 + 3옵션 AskUserQuestion. | §3 Step 0 |
| **TS-5** ("변경 후 재실행 제안") | §3 Step 8 — 명시적 한국어 프롬프트 + RERUN_FILTERS 핸드오프. | §3 Step 8 |
| **R-9** (권고 잠금) | §3 Step 5 획득 / §3 Step 7 해제. stock-scan은 백그라운드 스캔 시작 전에 존재를 읽음. | §3 Step 5 + Step 7 |

**Stage 5 하드 차단 커버리지** (workflow.md C-4 + 286행에 따름): 심층 방어를 위해 세 곳에서 enforce된다:
1. §3 Step 1 (PARAM_CHANGE 마스터 시퀀스) — primary REJECT 게이트.
2. §4 분기 1 SHOW_PARAMS — 명시적 "변경 불가" 어노테이션 포함 읽기 전용 요약.
3. §4 분기 6 ASK_MODULE — `financeFilter.py` 행에 명시적 "Phase 2" 표시.

---

## §9. `screener_state.json` 읽기/쓰기 지점

Step 4 §4 스키마에 따름. `json.dump(state, tmp_fp); mv tmp final`을 통한 atomic write (Step 4 §4 atomicity 규칙).

| 작업 | Read | Write | 비고 |
|---|---|---|---|
| 세션 시작 (CLAUDE.md 온보딩으로부터의 핸드오프) | ✅ grep을 통해 현재 Final 값에 대해 `confirmed=false`인 `last_param_changes[*]` 확인 | — | B-12에 따른 외부 변경 경고 (CLAUDE.md §10). Filter-tune은 실제로 이를 실행하지 않음 — CLAUDE.md가 함, 다만 스킬은 경고 상태가 있다면 소비한다. |
| Step 5 (백업 생성) | ✅ — | ✅ `current_backup_files`에 추가 | `cp` 완료 후. |
| Step 6 (Edit) | — | — | (Edit 자체는 상태를 쓰지 않음.) |
| Step 7 (Edit 후) | — | ✅ `confirmed=false`로 `last_param_changes`에 추가 | Step 4 §4 스키마에 따름. |
| Step 5 회전 | — | ✅ 회전된 `.bak` 경로를 `current_backup_files`에서 제거 | 회전이 어떤 백업을 제거했다면. |
| CONFIRM 분기 | ✅ 가장 최근 `confirmed=false` 항목 식별 | ✅ `confirmed=true`로 설정 | tuning-log 행의 `✓ 확정` 마크와 짝을 이룸. |
| RESTORE 분기 (모든 경로) | ✅ — | ✅ `confirmed=true`로 복원 항목 추가 | 복원은 사용자에 의해 암묵적으로 확정됨. |
| 모든 경로 | — | atomic write: `tmp + mv` | Step 4 §4에 따름. |
| R-7 (손상된 상태) | ✅ `json.JSONDecodeError` 캐치 | ✅ 손상된 파일을 `.corrupt.{ts}`로 백업 | Skill은 상태를 부재로 처리하고 기본 빈 배열로 진행. CLAUDE.md (스킬 아님)가 사용자 노출 폴백을 처리. |

---

## §10. 길이 추정 (최종 SKILL.md)

| 섹션 | 추정 줄 수 |
|---|---|
| 프론트매터 (YAML) | 8 |
| §1 발생 조건 (한국어 의도 클러스터 테이블) | 6 |
| §2 경로 상수 참조 | 8 |
| §3 8단계 마스터 시퀀스 (간결 폼, verbosity는 tuning-sequence.md에 위임) | 50 |
| §4 6 분기 (간결 폼, tuning-sequence.md에 위임) | 36 |
| §5 파라미터명 검증 | 6 |
| §6 백업/복원 프로토콜 테이블 | 8 |
| §7 references/ 개요 | 6 |
| §8 안전 규칙 enforcement 매트릭스 | 6 |
| §9 state.json I/O 테이블 | 6 |
| 헤더/푸터 주석 | 4 |
| **SKILL.md 합계** | **~144 lines** |

추가로 6개 참조 파일: **~30 + ~50 + ~150 + ~200 + ~250 + ~300 = ~980 lines** 분담.

**압축 정책** (SKILL.md > 130인 경우 — workflow.md 목표):
- §4 분기를 분기당 단일 라인으로 압축하고 `tuning-sequence.md §B`로 교차 참조. 약 25행 절약.
- §3 8 단계를 단계당 단계명 + 1행 요약으로 압축하고 `tuning-sequence.md §A`로 교차 참조. 약 30행 절약.
- 합산: 추정 약 89행 — 130 이하로 충분히 들어옴.

**130-150이 허용된다면 압축 불필요**; 마스터 시퀀스 세부는 정보 밀도가 높으며 SKILL.md 본체에 속한다고 볼 수 있다. Step 9 `@tune-builder`가 최종 줄 수에 기반하여 결정한다.

---

## §11. 검증 자체 점검

- [x] 마스터 시퀀스에 **8개 번호 단계**가 있고, 각각이 TS 규칙 인용 (TS-3/-4/-2/-1/-5) + 체크포인트 + 한국어 메시지를 가짐
- [x] **6개 분기** 명세 (SHOW_PARAMS, PARAM_CHANGE→§3, CONFIRM, RESTORE, THEORY_GUIDE, ASK_MODULE, COMPARE_EXPERIMENTS) — §4 서브헤더로 집계: SHOW_PARAMS / CHANGE_PARAM(→§3) / CONFIRM / RESTORE / THEORY_GUIDE / ASK_MODULE / COMPARE_EXPERIMENTS — = 6개의 별개 분기 (CHANGE_PARAM은 §3 마스터 시퀀스에 위임; 6개는 SHOW / CONFIRM / RESTORE / THEORY / ASK / COMPARE)
- [x] Range Map이 Step 1로부터 **75개 Final 상수 전부**를 커버 (§7 `references/range-map.md` 요구사항에서 명세; 10개 대표 예시 표시; 커버리지 게이트 "Stage별로 그룹화한 75개 상수를 커버해야 함")
- [x] 백업 규약 `*.bak.YYYYMMDD_HHmmss` enforce + TS-2a 회전 게이트 존재 (§3 Step 5, §6)
- [x] TS-1~5 enforcement 지점이 §3 / §4 / §8 매트릭스에 표시됨 — 5개 셀 모두 채워짐
- [x] 이론 가이드가 PRD §5.3 앵커 참조 (Minervini SEPA / Weinstein / Wyckoff / VCP / CANSLIM) — `references/theory-guide.md` §1에 전체 매핑
- [x] references/ 리스트 = **6개 파일** (`parameter-catalog`, `range-map`, `unit-conversion`, `shared-constants`, `theory-guide`, `tuning-sequence`) — §7 열거
- [x] 파라미터 구조 검증: §3 Step 6가 Edit 전 매치된 라인의 `Final[` 부분 문자열 검증 (주석/독스트링 거부)
- [x] 주석 갱신 규칙: §3 Step 6가 인접 `# 이전: {old_value}` 주석 자동 갱신 로직 포함 (agent verification #9)
- [x] Tuning log 비고 최소: §3 Step 7이 구체적 예시와 함께 `(motivation) | (decision_status)` 포맷 명세 (agent verification #10)
- [x] 백업 고갈 복구: §4 RESTORE 분기 Step 2b가 B-8 폴백 (tuning-log → Edit), §4 + §6 + §10에서 명확히 표기
- [x] R-9 권고 잠금: §3 Step 5 획득 / Step 7 해제 — bash 명령 + try/finally 해제 시맨틱과 함께 codified
- [x] OQ-3 (ADR-011) 디스패치가 stock-scan과 일관: §3 + §9가 CLAUDE.md §5에 따라 `type(exc).__name__` 사용; SKILL은 참조로 디스패치 테이블을 상속 (중복 없음)
- [x] **Stage 5 하드 차단 (C-4) 커버리지** — 세 위치: §3 Step 1 (PARAM_CHANGE), §4 SHOW_PARAMS Step 1.5, §4 ASK_MODULE financeFilter 행
- [x] 유사 명칭에 대한 Anti-conflation 테이블 (§5)이 `_ALIGN_TOL_LOOSE` vs `_MA_ALIGNMENT_TOLERANCE` + `_REQUIRED_CONSECUTIVE_BARS` 3-way + 3-way MA60-MA306 + 윈도우 크기 4-way 커버
- [x] 가능한 경우 PRD/Step 5로부터의 verbatim 한국어 메시지 (검증됨: TS-5 메시지, FR-6.5 확인, B-8 폴백 메시지, B-12 외부 변경 포맷, PRD FR-5.5 위험 구간 메시지)
- [x] 모든 경로 참조는 `${KRT_…}` 변수를 통함 — **(spec)** 블록에 하드코딩된 절대 경로 없음
- [x] 블루프린트일 뿐 — `/Users/tajun/spJavis/kiwoom-rest-trader/`에 파일이 쓰여지지 않음
- [x] Tuning-log 8-열 스키마: `datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes` — FR-6.6 / workflow.md 281행으로부터 verbatim
- [x] 200행에서 Tuning-log 회전 → `tuning-log.YYYYMM.md` 아카이브 — FR-6.6 + B-16; COMPARE_EXPERIMENTS + RESTORE 폴백에서 아카이브 검색 필요
- [x] ADR-009 gap-extractor 정규식 카탈로그: 5개의 지배적 패턴이 §3 Step 3 + `references/tuning-sequence.md §D`에 문서화
- [x] 다중 파라미터 TS-4 감지 휴리스틱 (토큰화 + 접속사 인식) + 3옵션 AskUserQuestion이 §3 Step 0에 존재
- [x] 면책 문구 (FR-8.1 축약 폼)는 COMPARE_EXPERIMENTS Step 5에서 emit

---

## §12. 출처 추적성 매트릭스

| SKILL 섹션 | PRD 앵커 | workflow-idea 앵커 | Step 산출물 앵커 |
|---|---|---|---|
| §1 프론트매터 | §3 (사용자 페르소나 — opus 모델) | B-1 (skill 구조) | — |
| §2 경로 상수 | §6.1 경로 | B-6 (실행 템플릿) | Step 4 §1, §6 |
| §3 마스터 시퀀스 | §5.5 TS-1..5, FR-5, FR-6 | B-7/8/9/10/16/17/22 | Step 4 §4 (상태 스키마), §10 R-9; ADR-009, ADR-011, ADR-012 |
| §3 Step 1 Stage 5 차단 | §5.1 Stage 5 주의, §10 비목표 (Phase 2) | C-4 (workflow.md 286행) | Step 1 param-inventory Stage 5 섹션 |
| §3 Step 2 공유 상수 | §5.4 공유 상수 주의사항 | B-17 | Step 1 §Critical Distinctions |
| §3 Step 3 gap 추출 | FR-5.2 | B-10 | Step 1 pipeline-analysis §(c); ADR-009 (Step 4 OQ-1) |
| §3 Step 4 확인 | FR-5.6 + §7.3 수치 포맷팅 | B-7 | Step 5 §6 (CLAUDE.md 포맷 규칙) |
| §3 Step 5 백업 + lock | TS-2, TS-2a + R-9 완화책 | B-8 | Step 4 §10 R-9 |
| §3 Step 6 Edit + B-13e | FR-5.1, FR-5.4, TS-1 | B-13e (변수명 존재) | Step 4 §5 사전 점검 (e); Step 1 §Critical Distinctions |
| §3 Step 7 tuning-log + 상태 | FR-6.6 | B-16 (200행 회전) | Step 4 §4 스키마 |
| §3 Step 8 재실행 제안 | TS-5, FR-5.6 | B-22 | Step 5 §3 혼합 의도 규칙 |
| §4 SHOW_PARAMS | FR-4.1, FR-4.3 | (CLAUDE.md 라우팅) | Step 5 §3 의도 클러스터 |
| §4 CONFIRM | FR-6.5 | (workflow.md 287행) | Step 5 §10 상태 시맨틱 |
| §4 RESTORE | FR-6.4 + B-8 폴백 | (workflow.md 288행) | Step 1 inventory (변수명 연속성); Step 4 §4 상태 |
| §4 THEORY_GUIDE | FR-7.1, FR-7.2, FR-7.3, FR-7.4 | (workflow.md 289행) | PRD §5.3 매핑 |
| §4 ASK_MODULE | §6.4 모듈 인터페이스 | (workflow.md 290행) | Step 2 §7 (Phase 1 vs Phase 2 경계) |
| §4 COMPARE_EXPERIMENTS | FR-6.3 | B-16 조합 뷰 (workflow.md 291행) | Step 4 §4 last_results_summary |
| §5 변수명 검증 | TS-1 + FR-5.1 | B-13e | Step 1 §Critical Distinctions (anti-conflation); Step 4 §5 (e) |
| §6 백업/복원 프로토콜 | TS-2, TS-2a, FR-6.4 | B-8 | Step 4 §4 (state.json.current_backup_files) |
| §7 references/ 계획 | FR-4.1, FR-7, §5.4, §5.5 | (workflow.md 295-301행) | 모든 Step 1-4 산출물 |
| §8 안전 enforcement 매트릭스 | §5.5 TS-1~5 | B-7/B-8/B-9/B-17/B-22 | Step 4 R-9 |
| §9 state.json I/O | §3 (재방문 사용자) | B-12 | Step 4 §4 스키마 |

모든 섹션이 ≥ 1개 PRD 앵커 + ≥ 1개 workflow-idea 앵커 + ≥ 1개 Step 산출물로 추적된다. ADR-009/011/012는 해당 섹션에 흡수됨.

---

## §13. Step 9 `@tune-builder` 핸드오프 지침

Step 9가 본 블루프린트를 읽을 때, 빌더는 반드시:

1. **쓰기 대상**: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` (및 `references/` 아래 6개 참조 파일).
2. **순서**: SKILL.md 섹션을 정확히 다음 순서로 emit — 프론트매터 → §1 트리거 → §2 경로 상수 → §3 마스터 시퀀스 (8 단계 + SHORTCUT) → §4 6 분기 → §5 변수 검증 → §6 백업 프로토콜 → §7 references/ 개요 → §8 안전 enforcement 매트릭스 → §9 state.json I/O.
3. **Verbatim 복사** 모든 **(spec)** 블록 — 이모지 경고 (⚠️), 체크마크 (✓), 인라인 코드 스팬, 한국어 표현 포함. 한국어 문자열에 대한 의역 금지.
4. **경로 치환**: `${KRT_*}`를 리터럴 그대로 둘 것 — Claude Code의 셸이 Bash 호출 시점에 치환한다.
5. **줄 예산**: emit 후 SKILL.md에 `wc -l`. > 150이면 §10 압축 적용: §3 단계 본문을 `tuning-sequence.md §A` 교차 참조로 1행 요약으로 압축; §4 분기 본문을 `tuning-sequence.md §B` 교차 참조로 1행 요약으로 압축. 목표 ~89-130행.
6. **한국어 정확성**: 한국어 문장의 모든 공백 보존. 모든 한글-로마자 경계 공백 보존. 한국어 구두점에 하이픈 대신 em-dash (—) 사용.
7. **추가 섹션 없음**: 이 블루프린트가 명세하지 않은 Examples / Glossary / Troubleshooting 섹션을 추가하지 말 것.
8. **참조 파일**: 각각은 `.claude/skills/filter-tune/references/` 아래에 별도 파일로 생성되어야 한다. 6개 파일은 필수 (검증 기준). 참조 콘텐츠를 SKILL.md에 인라인하지 말 것.
9. **Range Map 커버리지 게이트**: `references/range-map.md`는 Step 1 param-inventory §Coverage Self-Check로부터의 75개 `Final` 상수 각각에 대해 행을 포함해야 한다. Stage 5 행은 존재하지만 "튜닝 불가 (Phase 2)"로 표시된다. Step 11의 @reviewer가 이 게이트를 검증한다.
10. **Stage 5 하드 차단 삼중 방어**: C-4 메시지가 (a) §3 Step 1 PARAM_CHANGE 마스터 시퀀스, (b) §4 SHOW_PARAMS 분기 Step 1.5, (c) §4 ASK_MODULE financeFilter 행에 등장하는지 확인. 세 위치 — 둘도 넷도 아님.

---

*블루프린트 완성. 구현은 Step 9에서 일어남 (`@tune-builder`가 본 spec으로부터 `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` + 6개 참조 파일을 작성). 교차 참조 리뷰는 Step 11에서.*
