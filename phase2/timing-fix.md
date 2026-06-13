# Phase 2-1a — 실측 시간·watchdog 보정 보고서

> 작업일: 2026-06-13 · 워커: Phase 2 worker (과업 2-1a)
> 결론: **완료** — 범위 내 "10-15분" 잔여 0건, watchdog 30분 → 7시간 보정, pytest 305 green 유지.

---

## 1. 근거 (실측 출처 — 날조 수치 없음)

| 출처 | 내용 |
|---|---|
| `engine/reports/screener_state.json` (`last_results_summary.note`) | **"실행 21:09→22:28 KST(~80분, 야간 0610 6h 대비 빠름)"** — 0611 스캔 ~80분, 0610 야간 스캔 ~6시간 실측 |
| `EXECUTION_REPORT.md` L35 | "실측 소요 80분~6시간 (문서의 '10-15분'은 진부화)" |
| `EXECUTION_REPORT.md` §4 결함표 #4 (L70) | "문서 실행시간 '10-15분' vs **실측 80분~6시간** — 30분 watchdog도 비현실 \| screener_state.json 실측 \| Phase 1 문서·로직 갱신" |
| 루트 `CLAUDE.md` §3 | "engine 문서 곳곳의 '10-15분' 표기는 진부(stale) — 신뢰 금지. 실측치 80분~6시간 기준" + "Phase 2-1에서 문서·로직 보정 예정" (= 본 과업) |
| `BUILD_PLAN.md` 2-1 (L61) | "4-step 완료 핸들러 실측치 보정(80분~6h 기준 watchdog)" |

**watchdog 7시간 산정 근거**: 실측 정상 범위 최대치 6시간 + 여유 1시간 = 7시간 무완료 시 이상 판정 (과업 지시의 보정 원칙 그대로; 별도 수치 날조 없음).

---

## 2. 수정 내역 (파일별 전체 목록)

### 2-1. `engine/CLAUDE.md` — 4곳

| 행(구) | 구 표기 | 신 표기 |
|---|---|---|
| 13 | `(10-15+ min, exceeds Bash 600s cap — ADR-012)` | `(실측 80분~6시간, exceeds Bash 600s cap — ADR-012)` |
| 117 | 온보딩 `"(약 10-15분 소요됩니다.)"` | `"(실측 기준 80분~6시간 걸립니다 — 데이터량·시간대에 따라 달라요. 백그라운드로 돌고 끝나면 보고드립니다.)"` |
| 123 | 모드 메뉴 `(약 10-15분)` | `(실측 80분~6시간, 데이터량·시간대 따라 변동)` |
| 137 | `(10-15+ min …)` + 안내 `"약 10-15분 소요…"` + `30분 timeout watchdog` | `(실측 80분~6시간 …)` + `"실측 기준 80분~6시간 소요됩니다(데이터량·시간대에 따라 변동)…"` + **7시간 watchdog (실측 최대 6시간 + 여유 1시간 — 7시간 무완료 시 이상으로 판정)** |

### 2-2. `engine/.claude/skills/stock-scan/SKILL.md` — 3곳 (L48-49, 179, 204)

- 백그라운드 안내 verbatim → 실측 문구로 교체.
- "30분 watchdog" → "**7시간 watchdog** (실측 최대 6시간 + 여유 1시간): 7시간 무완료 시 이상으로 판정" + fallback 메시지 `"실행이 실측 범위(80분~6시간)를 넘겼습니다. …"`.
- §8 references 목록·§10 self-check 체크리스트의 "30분 watchdog" 표기 동기화.

### 2-3. `references/execution-chains.md` — 6곳 (L20, 27-30, 35, 70, 75, 88)

- ADR-012 mandate 사유: `10-15분 실 runtime` → `실측 80분~6시간 runtime`.
- Chain 1 Step 4 예상 소요 안내 verbatim, Step 6 watchdog(30분→7시간+판정 기준), Chain 2 Step 2 prefetch 안내, Step 4 watchdog, Chain 8 재시도 비용 설명(`10-15분 비용` → `장시간 prefetch(실측 80분~6시간) 비용`) 전부 교체.

### 2-4. `references/output-templates.md` — 2곳 (§9, L207-211)

- 실행 시작 안내·watchdog fallback **verbatim 템플릿 원천**을 교체 — SKILL.md·execution-chains.md·background-execution.md와 문자열 동일(3파일 cross-check 완료).

### 2-5. `references/background-execution.md` — §1·§2·§3·§6 전면 + §7 보정 노트

- §1 표: full flow·prefetch 실 runtime `~10-15분` → `실측 80분~6시간` (run_filters `< 3분`, Filter_condition_update `~30s`는 실측 이슈 없음 — 유지).
- §2 한국어 안내 verbatim 교체 (Chain 2 변형 포함).
- §3 제목 `30분 watchdog` → `7시간 watchdog` + 산정 근거 1줄(실측 출처 명기) + 구현 노트의 timer·경과 인식 기준 7시간으로 갱신 (+7시간 미만 문의 시 "실측 범위 내 정상 진행 중" 안내 분기 추가).
- §6 escalation: `추가 30분(총 60분)` → `추가 1시간(총 8시간)` — 구조(1단계 watchdog → 거부 시 추가 escalation)는 보존, 간격만 신 기준에 비례 조정. 메시지에 "실측 최대치(6시간)를 크게 초과" 명시. **(8시간은 실측 주장 아님 — watchdog 7h + 1h의 정책 파라미터임을 명기)**
- §7 ADR-012 verbatim 인용(영문 "10-15+ min", "30-min timeout safeguard")은 **역사적 인용으로 보존**하되, 직후에 "시간 수치 보정 노트 (Phase 2-1a)" 추가 — 수치는 진부화, mandate는 유효(실측이 길수록 오히려 강화)임을 명시.

---

## 3. 검증 결과

### ① pytest — 305 green 유지

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m pytest tests/ -q
→ 305 passed in 9.44s
```

- 사전 grep으로 `engine/tests/` 내 "10-15"·"30분"·"watchdog"·"소요" 문자열 단언 **0건 확인** → 가드레일 테스트 갱신 불필요(깨진 테스트 없음).

### ② 잔여 grep — 범위 내 0건

```
grep -rn "10-15분\|10~15분\|30분" engine/CLAUDE.md engine/.claude/skills/stock-scan/
→ (no matches, exit 1)
```

(영문 변형 "10-15+ min"·"30-min"은 background-execution.md §7 ADR-012 verbatim 인용 + 그 보정 노트 안에만 잔존 — 아래 분류표 A-1.)

---

## 4. 잔여 발생처 분류표 (보존 결정·범위 외)

| # | 위치 | 표기 | 분류 | 처리 |
|---|---|---|---|---|
| A-1 | `engine/.claude/skills/stock-scan/references/background-execution.md` §7 | 영문 `10-15+ min` / `30-min` (ADR-012 원문 인용) | **역사적 verbatim 인용** | 보존 + 직후 보정 노트로 무력화 (한국어 grep 비대상) |
| A-2 | `engine/src/kiwoom/conditionCompany/formulas.py` L37·74·114 | `주가이평비교:[30분]` 등 | **도메인 의미 — 30분봉 차트 타임프레임** (실행시간 무관) | 수정 금지 — 키움 조건검색식 정의 |
| B-1 | 루트 `CLAUDE.md` §3 | "'10-15분' 표기는 진부 — 신뢰 금지" / "기존 30분 watchdog도 비현실 — Phase 2-1에서 보정 예정" | 경고문(인용) — 본 과업 완료로 "보정 예정"이 stale해짐 | **범위 외** — 후속 1줄 갱신 권고 (§5 이슈) |
| B-2 | `EXECUTION_REPORT.md` | 실측 대비 인용 다수 | 역사 감사 문서 (본 과업의 근거 원천) | 보존 |
| B-3 | `phase1/VERIFY.md` · `phase1/root-router.md` | 인용 | Phase 1 작업 기록 (역사) | 보존 |
| B-4 | `factory/prompt/**` (workflow.md, step-4/5/6/11 outputs 등 10개 파일) | 빌드 당시 추정치 | **동결 읽기 전용** (루트 CLAUDE.md §2.3) | 보존 의무 — 수정 금지 |
| B-5 | `factory/docs/integrated-user-command-manual.md` | 구 매뉴얼 추정치 | factory 구역 레거시 문서 | 범위 외 — 통합 매뉴얼 재작성 시점(후속 Phase)에 일괄 처리 권고 |

---

## 5. 이슈·후속 권고

1. **루트 `CLAUDE.md` §3의 "Phase 2-1에서 문서·로직 보정 예정" 문구가 본 과업 완료로 stale** — "보정 완료(phase2/timing-fix.md)"로 1줄 갱신 권고. 루트 라우터는 과업 범위(engine) 밖이라 미수정 (마스터 승인 후 처리).
2. **watchdog verbatim 메시지의 단일 원천은 `output-templates.md` §9** — 4개 파일(SKILL.md·execution-chains.md·output-templates.md·background-execution.md)에 동일 문자열로 동기화 완료. 향후 변경 시 4곳 동시 갱신 필요.
3. §6 escalation의 "총 8시간"은 실측 주장이 아닌 정책 파라미터(7h watchdog + 1h)다 — 문서에도 동일하게 명기함.
4. 실측 표본은 현재 2건(0611 ~80분 / 0610 ~6h)이다. 향후 스캔 누적으로 범위가 좁혀지면 watchdog 7시간을 재보정할 수 있다 (screener_state.json note가 회차별 실측을 계속 기록 중).

---
## [정정 추기 — 검증관, 2026-06-13]
§4 분류표 누락 1행 추가: factory/docs/architectural-decision-records.md:89 영문 "10-15+ min runtime"(ADR-012 Context 원문) — A-1과 동일한 레거시 verbatim 역사 인용, 보존. B-4 집계는 'runtime 추정치 기준 10파일'(문자열 보유 기준으로는 12파일 — prd-research 비-runtime 맥락 2개 제외) 기준 명시.
