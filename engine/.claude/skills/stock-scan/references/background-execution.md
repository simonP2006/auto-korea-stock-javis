# background-execution.md

ADR-012 enforcement reference. SKILL.md §3 Chain 1 / Chain 2가 본 파일을 참조한다.

---

## §1. ADR-012 mandate — `run_in_background: true` 필수 명령

Bash tool의 hard cap은 **600,000 ms (10분)**. 다음 명령은 실 runtime이 **실측 80분~6시간**(데이터량·시간대 따라 변동)으로 cap을 크게 초과하므로 **반드시** `Bash(run_in_background: true)`로 실행한다:

| 명령 | 체인 | 실 runtime | 백그라운드? |
|---|---|---|---|
| `cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_full_research_flow {date}` | Chain 1 SCAN_TODAY | 실측 80분~6시간 | **YES (필수)** |
| `cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_prefetch {date}` | Chain 2 SCAN_SEPARATED Step 1 | 실측 80분~6시간 | **YES (필수)** |
| `cd ${KRT_ROOT} && ${KRT_PYTHON} -m scripts.run_filters {date}` | Chain 2 Step 2, Chain 8 RERUN_FILTERS | < 3분 | NO (foreground) |
| `cd ${KRT_ROOT} && ${KRT_PYTHON} -m src.kiwoom.itemFilter.Filter_condition_update {date}` | Chain 5 WHY_REJECTED | ~30s | NO (foreground) |

`run_filters`와 `Filter_condition_update`는 600s Bash cap 내 — 명시적으로 `Bash(run_in_background: false)`로 동기 실행. ADR-012의 "long-running scans"는 full flow + prefetch에만 적용된다.

---

## §2. 백그라운드 실행 한국어 안내 (verbatim)

체인이 백그라운드 명령을 launch한 직후, 즉시 emit:

```
실측 기준 80분~6시간 소요됩니다(데이터량·시간대에 따라 변동). 완료되면 자동으로 결과를 보고합니다.
```

(Chain 2 Step 2에서는 동일 의미를 prefetch context로 풀어 `"먼저 데이터 수집(prefetch)을 시작합니다. 실측 기준 80분~6시간 소요됩니다(데이터량·시간대에 따라 변동)."`로 emit — `output-templates.md` §9 참조.)

---

## §3. 7시간 watchdog

기준: **실측 80분~6시간**(EXECUTION_REPORT §4 결함 #4, screener_state.json 실측 — 0611 ~80분 / 0610 야간 ~6h). 정상 범위 최대 6시간 + 여유 1시간 = **7시간 무완료 시 이상으로 판정**한다. (구 watchdog 기준은 진부화된 추정 소요시간에 기반한 것으로 폐기 — 정상 실행을 오탐한다. 구 수치는 §7 ADR-012 verbatim 인용 및 보정 노트 참조.)

백그라운드 launch 후 완료 알림이 7시간 안에 오지 않으면, 한국어 fallback emit + SCAN_SEPARATED 제안:

```
실행이 실측 범위(80분~6시간)를 넘겼습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?
```

watchdog 구현 노트:
- harness가 백그라운드 process exit 시 stdout/stderr stream을 emit한다 (Monitor tool 또는 자동 완료 notification).
- Skill은 7시간 timer를 별도 유지하지 않고 — 사용자가 다른 interaction 없이 백그라운드 launch 후 7시간 경과를 인식 시 위 메시지를 emit. 실용적으로는 사용자가 다시 말을 걸어 "아직 안 끝났어?"라고 물을 때 시간 경과를 확인하고, 7시간 미만이면 "실측 범위(80분~6시간) 내 정상 진행 중" 안내를, 7시간 이상이면 watchdog message를 emit하는 것이 자연스럽다.
- watchdog 발화 후 사용자가 SCAN_SEPARATED를 선택하면 Chain 2 invocation으로 전환 (단, 백그라운드 process는 별도로 계속 진행 중일 수 있음을 사용자에게 알림).

---

## §4. 4-step 완료 핸들러 (PRD B-4 + Step 5 §5)

백그라운드 process exit notification 수신 시, 정확히 다음 4 단계 순서로 처리:

### Step 1 — Stock count 추출 (stdout)

- 1차: `save_researched_company`가 emit하는 최종 라인 검색 — `r"researchedCompany\.md:\s*(\d+)종목 저장"` 정규식.
- 1차 실패 시 fallback: `wc -l < ${KRT_REPORTS}/{date}/researchedCompany.md` 실행 → 행 수를 종목 수로 간주.
- 둘 다 실패 (파일 미존재) → Step 2의 stderr 스캔으로 분기.

### Step 2 — stderr 오류 스캔

- 마지막 20행 슬라이스 (`bash_result.stderr.splitlines()[-20:]`).
- traceback 패턴 또는 `Exception: …` 라인 검색.
- 비어 있고 exit code 0 → success path.
- 비어 있지만 exit code ≠ 0 → "exit ≠ 0 but no traceback" 케이스 → SKILL.md §6 `Exception` (generic) fallback.

### Step 3 — `type(exc).__name__` STRING 분류 (ADR-011)

stderr에서 예외 클래스명을 정규식으로 추출:
```
r'\b(Kiwoom[A-Z][a-zA-Z]+Error|OrganizeError|ResearchError|PrefetchError|FileNotFoundError|ValueError)\b'
```

매칭된 마지막 occurrence를 `exc_name`으로 채택 (가장 최근의 raise가 사용자에게 가장 의미 있음).

분류 매핑은 CLAUDE.md `§Error Classification` 9-row 표 참조 (`KiwoomAuthError` / `KiwoomApiError` / `KiwoomConditionError` / `OrganizeError` / `ResearchError` / `PrefetchError` / `FileNotFoundError` / `ValueError` / `Exception` generic fallback).

**금지**: `isinstance(exc, KiwoomApiError)` — `KiwoomApiError`는 kiwoom-rest-trader의 8개 모듈에 독립 정의되어 import-based catch가 7개를 놓친다 (ADR-011 / OQ-3).

### Step 4 — 한국어 보고서 emit

분기:
- Success (exit 0 + 종목 수 추출 성공): `output-templates.md` SHOW_RESULTS 템플릿 (Chain 1) 또는 prefetch stats (Chain 2 Step 1).
- 실패: `output-templates.md` §8 Error report 템플릿 + `기술 정보:` 라벨로 stderr 마지막 5줄 첨부.

`screener_state.json` 갱신은 Step 4 emit 직후 수행 (성공 path에서만).

---

## §5. 재시도 예산 (agent verification #10)

- 동일 체인 invocation 내에서 동일 `type(exc).__name__`이 2회 연속 관찰 → STOP.
- 한국어 stop 메시지: `"동일 오류({exc_name})가 2회 반복되었습니다. 추가 시도를 중단합니다. 원인: {cause}. 조치: {action}."`
- 무한 retry loop 금지.
- Chain 3 SCAN_RANGE 특별 규칙: 일자 수준에서 2회 연속 동일 오류 발생 시 범위 loop 전체 중단 (현재 일자만 skip하지 않음).

---

## §6. Notification 미수신 escalation

7시간 watchdog이 trigger되었는데 사용자가 SCAN_SEPARATED 제안을 거부한 경우:
- 백그라운드 process는 계속 진행 중 (Skill이 자의적으로 kill하지 않음).
- 추가 1시간 (총 8시간) 경과 시 추가 escalation: `"실행이 8시간 넘게 진행 중입니다 — 실측 최대치(6시간)를 크게 초과했습니다. 프로세스를 확인하시거나 새 터미널에서 종료 후 다시 시도해주세요."`
- 사용자가 명시적으로 kill 요청 시: 해당 백그라운드 job ID를 KillShell 등 표준 메커니즘으로 종료 (구체 도구는 harness 제공). Skill은 강제 종료 명령을 자의적으로 실행하지 않는다.

---

## §7. ADR-012 verbatim 인용 (Step 4 architecture §8 / Appendix A)

> **ADR-012: SCAN_TODAY = run_full_research_flow with background execution mandate**
> - Context: D-2 default mode + 10-15+ min runtime vs 10-min Bash cap.
> - Decision: `run_full_research_flow` is default; all long-running scans (full flow, prefetch) MUST use `Bash(run_in_background: true)` with 30-min timeout safeguard.
> - Alternatives: (a) background mandate [chosen], (b) hybrid first-time/thereafter routing, (c) split mode as default.
> - Rationale: Preserves PRD FR-1.1 contract; background notification eliminates timeout pressure; explicit `"나눠서 해줘"` trigger gives user control over split mode.

본 Skill은 ADR-012의 "MUST"를 그대로 enforce한다 — Chain 1 Step 5와 Chain 2 Step 3에서 `Bash(run_in_background: true)`는 negotiable 하지 않다.

> **시간 수치 보정 노트 (Phase 2-1a)**: 위 인용문은 역사적 verbatim이므로 보존하나, 인용문 속 시간 수치("10-15+ min", "30-min timeout safeguard")는 **진부화**되었다. 실측(EXECUTION_REPORT §4 결함 #4, screener_state.json — 0611 ~80분, 0610 야간 ~6h) 기준 **실 runtime 80분~6시간 · watchdog 7시간**(§3)으로 대체 적용한다. 백그라운드 실행 mandate 자체는 그대로 유효하다(실측이 길수록 mandate는 오히려 강화).
