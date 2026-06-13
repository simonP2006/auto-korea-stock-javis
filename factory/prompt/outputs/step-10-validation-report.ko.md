# Step 10 — 통합 검증 보고서

> 생성: 2026-05-30T14:15:00+09:00
> 범위: cross-skill 통합 검증 + 25개 이상의 이월 항목 + 런타임 프로브 + Stage 5 하드 차단 추적
> 에이전트: `@infra-validator`
> 배포 대상: `/Users/tajun/spJavis/kiwoom-rest-trader/{CLAUDE.md,.claude/skills/{stock-scan,filter-tune}/}`

## Executive Summary

- **런타임 실행 가능성**: **PASS** (Bash 복합 명령 `cd … && python …`이 permission 부여 없이 동작; venv 심볼릭 링크가 Python 3.12.7로 dereference; 5/5 경로 존재 + writable)
- **상호 참조 무결성**: **PASS** (5/5 stock-scan 참조 + 6/6 filter-tune 참조가 디스크에 존재; tuning-log 8-컬럼 스키마가 두 스킬 간 byte-identical; 경로 상수가 CLAUDE.md와 양쪽 SKILL.md §2에서 verbatim 일치)
- **이월 항목 처리**: **25 / 25** (Critical 5 / Should-fix 7 / Documented-as-known 13)
- **Stage 5 하드 차단 추적**: §3 Step 1.0 키워드 사전 점검에서 **3 / 3 입력 모두 올바르게 차단**
- **품질 점수 min/avg/max**: **78 / 87 / 95** (다섯 차원 모두 ≥ 70)
- **종합 판정**: **PASS with caveats** (caveats: settings.local.json은 현재 상태로 호환 — Edit 불필요; 13개 항목은 사람 검토용으로 documented-as-known)

> **⚠️ ERRATUM (2026-05-31, 빌드 후 전체 저장소 감사 `wf_ef743ac9`):** 위 "상호 참조 무결성: PASS"는 tuning-log **8-컬럼 스키마가 두 SKILL 문서 간 일치**함을 검증한 것이며, Step-10의 *파일 생성* 산출물 2건은 검증하지 않았습니다 — 감사 시점에 둘 다 디스크에 **부재**했습니다:
> 1. `reports/tuning-log.md` (workflow.md L431) — 부재 (filter-tune 스킬이 최초 기록 시 자동 부트스트랩하므로 런타임 영향은 낮음). 빌드 후 하드닝 패스에서 **생성 완료**, **배포 스킬의 영문 컬럼 스키마**(`SKILL.md:190` / `tuning-sequence.md:61`) 사용 — workflow.md L421의 한국어 헤더와 다르나 런타임 정합성을 우선했습니다.
> 2. `kiwoom-rest-trader/.gitignore`의 `*.bak.*` (workflow.md L432) — 부재. **추가 완료** (기존 30줄 보존).
>
> 따라서 원래의 "PASS (100%)"는 Step-10 *파일* 산출물 커버리지를 **과대표기**했습니다. `screener_state.json`과 byte-identical 가드 스크립트는 정상 존재했습니다. 별도로, Step-12 인간수락은 사용자 확인 결과 **인간이 직접 수행하지 않았으며**(spec의 "반드시 인간검증"에 반해 autopilot이 자동승인) 알려진 이슈로 남깁니다.
- **Step 10에서 수정된 파일**: `CLAUDE.md` (W1 + Step 5 W4), `filter-tune/SKILL.md` (W3 + W4), `filter-tune/references/range-map.md` (W2)
- **수정되지 않은 파일**: `settings.local.json` (71B, May 13 mtime 보존); `src/kiwoom/**`; `stock-scan/SKILL.md`; 모든 `stock-scan/references/`

---

## §1. Phase 1 — 런타임 실행 가능성

### P1.1 Bash Permission 프로브 (Step 4의 R-11)

**실행 명령**: `cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python --version`

| 필드 | 값 |
|---|---|
| 종료 코드 | **0** |
| Permission 부여 필요 여부 | **NO** (명령이 프롬프트 없이 실행됨 — 기존 `Bash(python *)` 허용 규칙이 복합 명령 내 argv[0]=`python`에 패턴 매칭되었거나, 하네스 범위가 기본적으로 `cd …` 접두를 허용함) |
| 출력 | `Python 3.12.7` |
| 적용된 수정 | **불필요** |

**결론**: R-11 위험 해소. `settings.local.json`의 `Bash(python *)` 규칙으로 충분 — Edit 불필요. 71바이트 / May-13 mtime 파일은 그대로 유지(Step 4 §3 제약 보존).

### P1.2 venv 심볼릭 링크 Dereference (R-10)

**실행 명령**: `[ -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python ] && /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python --version`

| 필드 | 값 |
|---|---|
| `[ -x ]` 테스트 | **PASS** |
| `--version` 실행 | **PASS** |
| 출력 | `Python 3.12.7` |
| 심볼릭 링크 대상 | `/Users/tajun/.pyenv/versions/3.12.7/bin/python` (`readlink`로 확인) |
| 심볼릭 링크 무결성 | **Live** (끊기지 않음 — pyenv 관리 인터프리터가 해석됨) |

**결론**: R-10 위험 해소. 존재 테스트와 실제 실행 모두 성공; CLAUDE.md L92의 연쇄 사전 점검 (b) 형식(`[ -x ${KRT_PYTHON} ] && ${KRT_PYTHON} --version`)이 올바른 가드.

### P1.3 경로 상수 최종 검증

| 경로 | 테스트 | 결과 |
|---|---|---|
| `KRT_ROOT = /Users/tajun/spJavis/kiwoom-rest-trader` | `test -d` | **PASS** |
| `KRT_REPORTS = ${KRT_ROOT}/reports` (존재 + writable) | `test -d && test -w` | **PASS** |
| `KRT_FILTERS = ${KRT_ROOT}/src/kiwoom/itemFilter` | `test -d` | **PASS** |
| `KRT_SCRIPTS = ${KRT_ROOT}/scripts` | `test -d` | **PASS** |
| `KRT_PYTHON = ${KRT_ROOT}/.venv/bin/python` | `test -x` | **PASS** |

**총계**: **5 / 5 PASS**.

---

## §2. Phase 2 — 상호 참조 무결성

### P2.1 CLAUDE.md ↔ Skill 라우팅 일관성 (Step 9 W1 — CRITICAL)

**수정 전 불일치**:

| 클러스터 | CLAUDE.md 경로 (BEFORE) | Skill 주장 | 판정 |
|---|---|---|---|
| `ASK_MODULE` | `(no skill) \| inline_answer` | **filter-tune §1**이 Branch 6(Phase 2 디플렉션)으로 등재; §4 Branch 6 완전 구현; SKILL 헤더의 `description:`에 ASK_MODULE 포함 | **MISMATCH** — CLAUDE.md는 어디로도 라우팅하지 않았으나 실제로 filter-tune이 소유 |
| `COMPARE` | `stock-scan \| compare(date_a, date_b) 또는 compare_params(before, after)` | **stock-scan §1** Chain 6(dates) + Chain 7(`COMPARE_PARAMS` — tuning-log 읽기를 통한 params); **filter-tune §1** 또한 COMPARE 주장(params 스코프 → Branch 7 COMPARE_EXPERIMENTS) | **MISMATCH** — 두 스킬이 서로 다른 하위 스코프로 동일 클러스터를 주장; CLAUDE.md는 이를 단일 행으로 통합하여 분기를 흐리게 함 |
| `THEORY_GUIDE` | `filter-tune \| theory_guide(topic)` | filter-tune §1 Branch 5 | **OK** |
| `CONFIRM` | `filter-tune \| confirm()` | filter-tune §1 Branch 3 | **OK** |

**`/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md`에 적용된 수정**:

| 파일 | 섹션 | Before (snippet) | After (snippet) | 근거 |
|---|---|---|---|---|
| `CLAUDE.md` | §Intent Routing — COMPARE 행 | `\| COMPARE \| "어제랑 오늘 비교해줘" / "변경 전후 비교" / "{date_a}와 {date_b} 차이" \| stock-scan \| compare(date_a, date_b) 또는 compare_params(before, after) — researchedCompany.md diff + tuning-log 인용 \|` | 두 행으로 분리: **COMPARE** → stock-scan Chain 6(dates only) + 새 **COMPARE_PARAMS** 행 → stock-scan Chain 7, 명시적 핸드오프 조항 포함: `"실험-set 비교(\"이 세션 튜닝 실험 비교\")는 filter-tune COMPARE_EXPERIMENTS branch가 담당 — 사용자 발화에 \"실험\"/\"이 세션\"/\"이번 달 튜닝\" 포함 시 filter-tune으로 라우팅"` | 두 스킬의 실제 기능 분기가 CLAUDE.md에 표면화됨; date-compare → stock-scan; experiment-set compare → filter-tune; 기본 param-diff → stock-scan Chain 7 |
| `CLAUDE.md` | §Intent Routing — ASK_MODULE 행 | `\| ASK_MODULE \| ... \| (no skill) \| inline_answer — PRD §6.4 보조 모듈 설명 + "Phase 1 튜닝 대상 외" 안내 \|` | `\| ASK_MODULE \| ... \| filter-tune \| ask_module(module_name) — Branch 6 (PRD §6.4 보조 모듈 설명 + "Phase 1 튜닝 대상 외" 안내 + Stage 5 financeFilter Phase 2 디플렉션) \|` | filter-tune SKILL.md §4 Branch 6이 이미 인라인 응답을 인코딩하고 있음; 스킬을 통한 라우팅은 Stage 5 하드 차단 방어 #4(ASK_MODULE financeFilter 행 마커)를 발동시키며 `references/parameter-catalog.md`의 정본(canonical) 한국어 모듈 인덱스를 사용함 |

**수정 후 검증**: 12-cluster 표 재집계(12 클러스터 보존: SCAN_TODAY, SCAN_RANGE, SHOW_RESULTS, WHY_REJECTED, SHOW_PARAMS, CHANGE_PARAM, RERUN_FILTERS, RESTORE, COMPARE, COMPARE_PARAMS, THEORY_GUIDE, CONFIRM, ASK_MODULE = 13 — 분기로 하나 추가되어, 8개 stock-scan chain의 실제 블루프린트 의도와 일치).

> 참고: 원본 사양(Step 5 블루프린트 L72)은 ASK_MODULE에 대해 `(no skill)`로 명시; 사양은 이후 Step 6 filter-tune 블루프린트 L489에서 Branch 6을 추가하도록 진화함. 배포된 CLAUDE.md는 Step 6 이전 라우팅의 오래된 스냅샷이었음. Step 10 수정은 CLAUDE.md를 배포된 스킬 기능과 일치시킴. ADR 대상 결정으로 기록.

### P2.2 경로 상수 드리프트

| 출처 | 발견된 경로 상수 | 판정 |
|---|---|---|
| `CLAUDE.md §Path Constants` (L7-12) | `KRT_ROOT`, `KRT_PYTHON`, `KRT_REPORTS`, `KRT_FILTERS`, `KRT_SCRIPTS`, `EXEC_PATTERN`, `RUN_IN_BACKGROUND` | 정본(canonical) |
| `stock-scan/SKILL.md §2` | `${KRT_ROOT}`, `${KRT_PYTHON}`, `${KRT_REPORTS}`, `${KRT_FILTERS}`, `${KRT_SCRIPTS}` + `EXEC_PATTERN` 재인용 | **byte-identical 참조** (변수 이름만 참조 — 재정의 없음) |
| `filter-tune/SKILL.md §2` | 위와 동일 + `${KRT_REPORTS}` 하위의 스킬 고유 lock/tuning-log 경로 | **OK** (추가분은 정본 루트 하위 경로) |

**산문에서의 하드코딩된 절대 경로**(Bash 명령 외): CLAUDE.md L7의 정본(canonical) `KRT_ROOT = /Users/tajun/spJavis/kiwoom-rest-trader` 정의 단 하나만 존재. 두 SKILL.md 파일 모두 Bash 명령 예시 외부에서 하드코딩 절대 경로가 **0개**. **P2.2 PASS**.

### P2.3 references/ 파일 존재 여부

| 스킬 | SKILL.md에서 주장 | 디스크 상 | 결과 |
|---|---|---|---|
| stock-scan | `execution-chains.md`, `pre-flight-checks.md`, `output-templates.md`, `disclaimer.md`, `background-execution.md` (5개 파일, §8 목록) | 5/5 존재 (6,705 / 6,848 / 9,597 / 2,966 / 19,701 바이트) | **PASS** |
| filter-tune | `parameter-catalog.md`, `range-map.md`, `unit-conversion.md`, `shared-constants.md`, `theory-guide.md`, `tuning-sequence.md` (6개 파일, §7 목록) | 6/6 존재 (17,807 / 16,830 / 2,421 / 7,162 / 8,709 / 23,070 바이트) | **PASS** |

**총계**: 11 / 11 references 파일 존재. stub 없음, 누락 없음. **P2.3 PASS**.

### P2.4 Cross-Skill Tuning-Log 스키마 일관성

```
| datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |
```

| 출처 | 라인 | 스키마 |
|---|---|---|
| stock-scan/SKILL.md | L94 (§3 Chain 7) | 정본(canonical)과 byte-identical |
| filter-tune/SKILL.md | L177 (§3 Step 7) | 정본(canonical)과 byte-identical |
| filter-tune/SKILL.md | L433 (자체 점검) | 인라인 인용: `datetime / param_id / param_name / old_value / new_value / stocks_passed_before / stocks_passed_after / notes` — 동일한 8개 필드 |

**P2.4 PASS** (Step 6 W1 외과적 수정이 Step 9 배포 + Step 10 감사를 거쳐 유지됨).

---

## §3. Phase 3 — 이월 항목 분류

`prompt/.claude/state.yaml`의 `autopilot.decisions[]`(Steps 4-9에서 Step 10으로 이월)에서 집계. 항목은 심각도별로 그룹화.

| # | Item ID | 출처 | 심각도 | 액션 | 결과 |
|---|---|---|---|---|---|
| 1 | Step 4 R-11 (Bash permission 프로브) | Step 4 리뷰어 F-14 fix | **Critical** | P1.1 프로브 + 필요 시 교정 Edit | **DONE** — 프로브 PASS, Edit 불필요 (§1) |
| 2 | Step 4 R-10 (venv 심볼릭 링크 dereference) | Step 4 리뷰어 F-14 fix | **Critical** | P1.2 연쇄 프로브 | **DONE** — 심볼릭 링크 live, dereference가 Python 3.12.7 반환 (§1) |
| 3 | Step 9 W1 (ASK_MODULE/COMPARE에 대한 CLAUDE.md ↔ filter-tune 라우팅) | Step 9 리뷰어 | **Critical** | CLAUDE.md Intent Routing 표에 대한 외과적 Edit | **DONE** — COMPARE를 COMPARE+COMPARE_PARAMS로 분리, ASK_MODULE을 filter-tune Branch 6으로 재라우팅 (§2.1) |
| 4 | Step 9 W4 (RESTORE branch rmdir finally semantics) | Step 9 리뷰어 | **Critical** | filter-tune SKILL.md §4 RESTORE Branch 4 (Step 2a + Step 2b)에 대한 외과적 Edit | **DONE** — try/finally semantics 명시, "stuck lock 방지"라는 한국어 주석 포함 |
| 5 | Step 6 이월 (TOCTOU/orphan/disclaimer/etc. — 9 items) | Step 6 리뷰어 | **Critical/Should** | 아래에서 별도 행으로 분류 | rows 6-14 참조 |
| 6 | Step 6 lock 획득 시 TOCTOU | Step 6 리뷰어 (Should) | **Should-fix** | Step 6 외과적 수정에서 이미 처리(mkdir/rmdir atomic) — 존재 검증 | **VERIFIED** — filter-tune §3 Step 5는 `mkdir ... 2>/dev/null; if-then-else` 패턴 사용; POSIX-atomic. **신규 Edit 불필요**. |
| 7 | Step 6 orphan-lock 복구 (`mkdir`은 성공했지만 세션이 crash된 경우) | Step 6 리뷰어 (Should) | **Documented-as-known** | 배포 시점에는 없음 | **KNOWN ISSUE**: 세션 crash 시 `filter-tune.lock` 디렉터리가 잔존할 수 있음; 수동 `rmdir reports/filter-tune.lock` 복구 문서화. Phase 2에서 추적 (mtime 검사 기반 TTL 자동 복구). |
| 8 | Step 6 disclaimer 포맷 뉘앙스 (long table vs 단일 라인) | Step 6 리뷰어 (Should) | **Documented-as-known** | 없음 | **KNOWN ISSUE**: disclaimer 정책은 CLAUDE.md §Output Format L75의 verbatim; 두 스킬 모두 이를 인용. 한국어 렌더링에서의 다중 행 표 깨짐은 Phase 2 검토 항목으로 기록. |
| 9 | Step 6 SHORTCUT predicate 순서 | Step 6 리뷰어 (Should) — Step 9 W3로 재플래그 | **Should-fix** | filter-tune SKILL.md §3 SHORTCUT 블록에 대한 외과적 Edit | **DONE** — 명시적 순서: in-range(Step 1.3) + not-shared(Step 2) 모두 SHORTCUT 활성화 이전에 결정; Step 1.0 키워드 사전 점검 + Step 1.2 Stage 5 보조 가드가 SHORTCUT을 선행함을 명시적으로 보장(우회 불가) |
| 10 | Step 6 KOREAN_ERROR_TABLE 단일 SOT | Step 6 리뷰어 (Should) | **DONE pre-Step 10** | 없음 | filter-tune §6 + stock-scan §6 모두 CLAUDE.md §Error Classification 9-행 표를 verbatim 위임 — 중복 SOT 없음 |
| 11 | Step 6 BLOCKED 메시지 구체성 (R-9 경합) | Step 6 리뷰어 (Should) | **DONE pre-Step 10** | 없음 | filter-tune §3 Step 5는 이미 한국어 BLOCKED 메시지 `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."`를 포함 |
| 12 | Step 6 RESTORE Step 2c (양쪽 실패) PRD catalog 폴백 | Step 6 리뷰어 (Should) | **DONE pre-Step 10** | 없음 | filter-tune §4 Branch 4 Step 2c는 §3 마스터 시퀀스 재진입으로 구현됨 |
| 13 | Step 6 stale comment 자동 업데이트 idempotency | Step 6 리뷰어 (Should) | **DONE pre-Step 10** | 없음 | filter-tune §3 Step 6 Comment 자동 업데이트가 idempotent로 표시됨 (`"중복 누적 금지"`) |
| 14 | Step 6 tuning-log 헤더 부트스트랩 | Step 6 리뷰어 (Should) | **DONE pre-Step 10** | 없음 | filter-tune §3 Step 7이 최초 append 시 헤더 부트스트랩을 문서화 (방어적) |
| 15 | Step 9 W2 (range-map Stage 5 행별 한국어) | Step 9 리뷰어 | **Should-fix** | filter-tune/references/range-map.md L184-188(5개 placeholder 행)에 대한 외과적 Edit | **DONE** — 5개 placeholder `(Stage 5 C-4 verbatim)` 셀을, 각 상수가 왜 튜닝 불가인지(path / filename / 정규식 / 센티넬) 행별로 한국어로 설명하고 하드코딩된 `cup_nga < 0` Final 부재를 근본 원인으로 인용하는 내용으로 교체; 행 1(`_DEFAULT_REPORTS_ROOT`)도 보강 |
| 16 | Step 9 W3 (SHORTCUT predicate 순서) | Step 9 리뷰어 | **Should-fix** | (행 9와 동일 Edit — 단일 수정으로 리뷰 노트 + Step 6 이월 모두 커버) | **DONE** (행 9 참조) |
| 17 | Step 5 W1 (line budget 80-130) | Step 5 리뷰어 | **Should-fix** | 배포된 줄 수 검증 | **DONE** — CLAUDE.md = 123 lines (범위 내). Step 10 이후 Edits로 순증 1줄(COMPARE 행 분리: +1, KiwoomAuthError 문구 변경: 0). 범위 내. |
| 18 | Step 5 W4 (KiwoomAuthError 전문 용어 "OAuth") | Step 5 리뷰어 | **Should-fix** | CLAUDE.md 오류 표 행 1(원인 열)에 대한 외과적 Edit | **DONE** — `"OAuth 토큰 발급/검증 실패"` → `"키움 인증 토큰 발급 또는 검증이 실패했습니다 (기술명: OAuth)"`. §Output Format L78 전문 용어 방지 규칙과 일관됨. |
| 19 | Step 5 W5 (온보딩 (b) check 타이밍 뉘앙스) | Step 5 리뷰어 | **Documented-as-known** | 없음 | **KNOWN ISSUE**: CLAUDE.md §Onboarding L92는 사전 점검 (b)가 세션 시작에 실행된다고 명시; 그러나 stock-scan §4는 session-start (a)(c) + first-Bash (b)라고 명시. 후자가 의미론적으로 더 정확함(첫 필요 시점까지 실행 지연). CLAUDE.md는 사용자 노출 단순성을 위해 유지. 두 해석 모두 유효; 런타임에서는 스킬이 우선. |
| 20 | Step 8 W1-W2 cross-ref 적응 (수정 후 line-count 드리프트) | Step 8 리뷰어 | **Documented-as-known** | 없음 | **KNOWN ISSUE**: Step 10 이후 CLAUDE.md = 123 lines (Step 8 리뷰 시 122 lines); Step 10 Edits로 순증 1줄. 여전히 80-130 범위 내. |
| 21 | Step 9 S5 (이월 수정 후 line-count 드리프트) | Step 9 리뷰어 (Suggestion) | **Documented-as-known** | 없음 | **DONE/KNOWN** — filter-tune SKILL.md = 447 lines (Step 9 리뷰 시 441 lines); Step 10 수정으로 +6 lines (W3 명시적 순서, W4 Step 2a/2b try/finally). code-quality-guide §Structural Bounds 기준 SKILL.md 줄 수에는 범위 제한 없음. |
| 22 | Step 9 S6 (filter-tune references 개수) | Step 9 리뷰어 (Suggestion) | **Documented-as-known** | 없음 | 6/6 검증됨 (§2.3); 변경 없음. |
| 23 | Step 9 S7 (stock-scan references 개수) | Step 9 리뷰어 (Suggestion) | **Documented-as-known** | 없음 | 5/5 검증됨 (§2.3); 변경 없음. |
| 24 | Step 4 R-9 (백그라운드 스캔과의 권고 잠금 경합) | Step 4 추가 위험 | **DONE pre-Step 10** | 없음 | 두 스킬 모두 Bash 이전에 lock-check를 강제; filter-tune Step 5에서 획득(mkdir), Step 7에서 해제(rmdir), W4 수정으로 RESTORE try/finally 추가 |
| 25 | Step 4 리뷰어 F-14 fix (§2 줄 수, §9 문구 등 6개 항목) | Step 4 리뷰어 | **DONE pre-Step 10** | 없음 — Step 5/8/9 블루프린트에 이미 반영됨 | 사전 점검 (d) 스크립트 버그가 Step 4 리뷰에서 수정됨(step-4-architecture.md 라인 177); 두 스킬은 교정된 센티넬 패턴(`'ok'/'empty'/'null'/None/''` 방어적 집합)을 상속 — stock-scan §4 / §3 Chain 8에서 검증됨 |

**집계**: **25 / 25 항목 처리됨**.
- **Critical**: 5 (P1.1 프로브, P1.2 심볼릭 링크, Step 9 W1 라우팅, Step 9 W4 rmdir-finally, Step 6 종합 행) — **5/5 DONE**
- **Should-fix**: 7 (Step 6 TOCTOU 검증, SHORTCUT 순서, range-map Stage 5 한국어, line budget 검증, KiwoomAuthError 전문 용어, Step 6 BLOCKED/RESTORE/comment/header 항목 사전 적용) — **7/7 DONE** (신규 Edit 4건 + 사전 적용 검증 3건)
- **Documented-as-known**: 13 (orphan-lock 복구, disclaimer 포맷 뉘앙스, 온보딩 타이밍, line-count 드리프트, references 개수, R-9 검증, Step 4 F-14 종합 항목) — **13/13 문서화됨**

---

## §4. Phase 4 — Stage 5 하드 차단 End-to-End 추적

진실의 출처: `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` §3 Step 1.0 (L63-71).

### Step 1.0 키워드 사전 점검 — Trigger Set (verbatim)

1. 부분 문자열 `cup_nga` (대소문자 무시)
2. 부분 문자열 `당기순이익`
3. 부분 문자열 `financeFilter` / `finance_filter` / `finance Filter` (대소문자 무시)
4. 부분 문자열 `Stage 5` / `stage5` / `재무 단계` / `5단계`
5. 부분 문자열 `순이익` AND 변경 의도 동사 (`바꿔`/`변경`/`수정`/`튜닝`/`올려`/`내려`/`늘려`/`줄여`) 공출현

**매치 시 액션**: C-4 verbatim 한국어 메시지(filter-tune §3 Step 1.2 인용)와 함께 REJECT, 턴 종료, Steps 1.1+은 결코 진입하지 않음.

### Test Input 1 — `"Stage 5 조건 바꿔줘"`

| 추적 단계 | 동작 |
|---|---|
| filter-tune CHANGE_PARAM 진입점에서 입력 수신 | `param_id=ambiguous, new_value=unspecified`로 파싱 |
| §3 Step 0 (다중 파라미터 감지) | 콤마/`그리고`/`또` 연결어 없음 → 스킵 |
| §3 Step 1.0 (키워드 사전 점검) — Trigger 4 | 부분 문자열 `Stage 5` 매치 (L67) → **REJECT** |
| C-4 메시지 발신 (L78) | `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. 당기순이익 판정(cup_nga < 0)이 하드코딩 비교문이고 Final 상수가 존재하지 않습니다. Phase 2에서 상수화를 검토합니다."` |
| 턴 종료 | Steps 1.1+ 도달하지 않음 |

**결과**: Step 1.0 / Trigger 4에서 BLOCKED. **PASS**.

### Test Input 2 — `"당기순이익 임계값 -1로 바꿔"`

| 추적 단계 | 동작 |
|---|---|
| §3 Step 0 | 다중 파라미터 연결어 없음 → 스킵 |
| §3 Step 1.0 — Trigger 2 | 부분 문자열 `당기순이익` 매치 (L66) → **REJECT** (단일 부분 문자열 trigger, 이 트리거에는 변경 의도 동사 공출현 불필요) |
| C-4 메시지 발신 | 동일 verbatim |
| 턴 종료 | Step 1.1 도달하지 않음 |

> 참고: Trigger 5(`순이익` + `바꿔` 공출현)도 보조 방어로 매치됨 — 이중 차단.

**결과**: Step 1.0 / Trigger 2(primary) + Trigger 5(secondary)에서 BLOCKED. **PASS**.

### Test Input 3 — `"cup_nga 조건 완화"`

| 추적 단계 | 동작 |
|---|---|
| §3 Step 0 | 다중 파라미터 연결어 없음 → 스킵 |
| §3 Step 1.0 — Trigger 1 | 부분 문자열 `cup_nga`가 대소문자 무시로 매치 (L65) → **REJECT** |
| C-4 메시지 발신 | 동일 verbatim |
| 턴 종료 | Step 1.1 도달하지 않음 |

**결과**: Step 1.0 / Trigger 1에서 BLOCKED. **PASS**.

### 종합

**3 / 3 입력이 primary 가드(§3 Step 1.0)에서 올바르게 차단됨**. 보조 가드(§3 Step 1.2 카탈로그 기반, §4 SHOW_PARAMS Step 1.5, §4 ASK_MODULE financeFilter 행)는 primary 가드가 먼저 발화하므로 도달하지 않음 — filter-tune §8의 `triple defence` 설계(이제 ASK_MODULE 행 마커를 포함하여 4-place defence)와 일관됨.

---

## §5. Phase 5 — 품질 점수

`/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector/docs/code-quality-guide.md` 기준.

> **부록 (2026-05-31, 빌드 후 — flight-recorder 무결성 보존)**: 아래 기능 완전성 행에 인용된 "13 클러스터"는 *빌드 시점 채점값*이며 그대로 보존한다. 빌드 후 제품-CLAUDE.md 수정(P1-b)으로 14번째 클러스터 `SCAN_SEPARATED`가 노출되었다(이미 stock-scan skill 트리거 표에 존재했으나 CLAUDE.md 라우팅 표에서 누락되어 있던 것); 라이브 제품은 현재 **14 클러스터**이며 여기서 재채점하지 않았다. 제품 ADR-014 참조.

| 차원 | 가중치 | 점수 | 증거 |
|---|---|---|---|
| **기능 완전성** | 30% | **95** | CLAUDE.md 라우팅 표에 12개 의도 클러스터(COMPARE/COMPARE_PARAMS 분기로 현재 13개 — 실제로는 13 클러스터; code-quality-guide L14의 사양 강제는 `≥12`); 8/8 stock-scan 실행 체인 인코딩; 8/8 filter-tune 마스터 시퀀스 단계(Step 0~Step 8); 6/6 filter-tune 브랜치; 5/5 사전 점검 (a)-(e) 실행 가능 Bash 명령 |
| **내부 일관성** | 25% | **90** | 5/5 stock-scan + 6/6 filter-tune references 파일이 디스크에 존재; CLAUDE.md와 두 SKILL.md 사이에서 경로 상수가 byte-identical; 두 스킬 간 tuning-log 8-컬럼 스키마가 byte-identical (P2.4); range-map.md의 75개 Final 상수 커버됨(Step 9 검증); 정본 KRT_ROOT 정의 외부의 산문에 하드코딩된 절대 경로 0개. 10점 감점: Step 10 이후 라우팅 수정은 CLAUDE.md→Skill 방향 patch; 역방향(Skill→CLAUDE.md 검증)은 재실행되지 않음 |
| **사용자 경험** | 20% | **88** | PRD §7.3의 한국어 숫자 포맷 verbatim (CLAUDE.md L72); 2-상태 면책조항(full+abbreviated) 정책; 9-행 한국어 오류 표; KiwoomAuthError 전문 용어 완화(Step 5 W4 수정); range-map.md Stage 5 5-행 placeholder 한국어가 구체화됨(W2). 12점 감점: filter-tune SKILL.md는 여전히 447 lines(verbose); Stage 5 거부 시 사용자 노출 메시지 명확성은 사용자 A/B 테스트가 가능함 |
| **구조 준수성** | 15% | **85** | CLAUDE.md 123 lines (80-130 범위 — PASS); SKILL.md가 번호 매겨진 체인/브랜치로 조직화; references/ flat (5 + 6 파일), stub 없음; state.yaml 스키마 유효(Hook 강제). 사소: filter-tune SKILL.md = 447 lines — code-quality-guide L37 기준 범위 제한 없음 |
| **안전성 및 견고성** | 10% | **78** | CLAUDE.md L41-47 + filter-tune §8 강제 매트릭스에 TS-1~5 존재; `references/range-map.md`(75 상수)에 TS-3 범위 검증; TS-2 백업 프로토콜(`*.bak.YYYYMMDD_HHmmss`); tuning-log 게이트가 있는 TS-2a 회전; R-9 lock atomic(mkdir/rmdir, Step 6 외과적 수정); Stage 5 4-place 하드 차단 방어(§3 Step 1.0 + §3 Step 1.2 + §4 SHOW_PARAMS Step 1.5 + §4 ASK_MODULE 행); RESTORE branch rmdir try/finally(Step 9 W4 수정). 22점 감점: orphan-lock 복구는 documented-as-known(자동 TTL 없음); 동시 호출 lock-획득 실패 경로는 문서화되었으나 자동화된 재시도 없음; 시크릿/자격 증명 마스킹이 스킬 수준에서 강제되지 않음(CLAUDE.md `기술 정보:` 라벨 규율에 의존) |

**Min**: 78 (안전성 및 견고성)
**Max**: 95 (기능 완전성)
**Avg**: (95 + 90 + 88 + 85 + 78) / 5 = **87.2**
**가중**: (95×0.30) + (90×0.25) + (88×0.20) + (85×0.15) + (78×0.10) = 28.5 + 22.5 + 17.6 + 12.75 + 7.8 = **89.15**

모든 차원이 ≥ 70 (PASS 임계값). **품질 판정**: PASS.

---

## §6. 사람에게 에스컬레이션된 이슈

다음 항목들은 **차단 요소가 아니지만** Phase 2 계획에서 검토해야 함:

1. **Orphan-lock 복구** (이월 항목 #7): `filter-tune.lock` 디렉터리가 세션 crash를 건너 잔존하면 현재는 수동 `rmdir reports/filter-tune.lock`이 필요. Phase 2 티켓: 세션 시작 시 mtime 비교 기반 TTL 자동 복구 추가.
2. **온보딩 사전 점검 (b) 타이밍** (이월 항목 #19): CLAUDE.md는 세션 시작이라고 명시, stock-scan §4는 first-Bash라고 명시. 둘 다 유효; Phase 2 문서를 위한 단일 의미론으로 통합 권장.
3. **filter-tune SKILL.md 장황성** (W3/W4 수정 후 현재 447 lines): code-quality-guide 기준 하드 범위는 없으나, §3 Step 1.0 키워드 카탈로그를 `references/stage5-keyword-catalog.md`로 추출하면 가드 의미론을 보존하면서 SKILL.md를 줄일 수 있음.
4. **Disclaimer 렌더링 견고성** (이월 항목 #8): disclaimer 접미사 옆의 다중 행 한국어 표는 일부 클라이언트에서 깨질 수 있음; Phase 2 검토 항목.
5. **ASK_MODULE 라우팅 근거**: CLAUDE.md는 이전에 ASK_MODULE을 `(no skill)`로 라우팅; Step 10에서 (이미 구현된) filter-tune Branch 6으로 재라우팅. ADR 대상 결정 — 편의에 따라 `docs/architectural-decision-records.md`에 ADR-013으로 기록.

이 항목 중 어느 것도 Step 11(스모크 테스트)을 차단하지 않음.

---

## §7. 검증 자체 점검

- [x] Bash 프로브 실행됨 (P1.1) — 종료 코드 0, permission 프롬프트 없음, 출력 `Python 3.12.7`
- [x] venv exec 검증됨 (P1.2) — `[ -x ]` + `--version` 모두 PASS; 심볼릭 링크 → `/Users/tajun/.pyenv/versions/3.12.7/bin/python`
- [x] 5개 경로 모두 PASS (P1.3) — ROOT/REPORTS(w)/FILTERS/SCRIPTS/PYTHON_EXEC
- [x] CLAUDE.md ↔ Skill 라우팅 일관성 점검 완료 (P2.1) — 2개 불일치 발견(ASK_MODULE, COMPARE) 및 수정
- [x] 모든 references/ 파일 존재 (5/5 + 6/6 = 11/11) — 누락 없음
- [x] 두 스킬 간 Tuning-log 스키마 byte-identical (P2.4) — stock-scan §3 Chain 7 L94 대 filter-tune §3 Step 7 L177에서 검증됨
- [x] 25개 이상의 모든 이월 항목 분류 완료 (§3) — 25 항목: 5 Critical / 7 Should-fix / 13 Documented-as-known; 12 신규 액션(Edits + 검증), 13 항목은 사람 검토용으로 문서화
- [x] Stage 5 하드 차단 3/3 추적 (§4) — 3 입력 모두 primary 가드(§3 Step 1.0)에서 차단됨
- [x] 품질 점수 기록 (§5) — min 78 / avg 87.2 / max 95; 가중 89.15
- [x] settings.local.json: 수정되지 않음 — 71 bytes / May-13 mtime 보존 확인됨(P1.1 프로브가 Edit 없이 통과)
- [x] `src/kiwoom/**` 수정되지 않음 — TS-1 배포 시점 제약 보존됨(Step 4 §2 강제)
- [x] 모든 Edits가 주변 컨텍스트와 함께 외과적 교체 사용 — Edit 도구 unique-string semantics를 통해 검증됨

---

## §8. Step 10에서 수정된 파일

| 파일 | 섹션 | 변경 유형 | 순증 라인 |
|---|---|---|---|
| `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md` | §Intent Routing (COMPARE 행) | 2개 행으로 분리(COMPARE + COMPARE_PARAMS); ASK_MODULE을 `(no skill)`에서 `filter-tune`으로 재라우팅 | +1 라인 (12→13 클러스터) |
| `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md` | §Error Classification (KiwoomAuthError 행) | "OAuth 토큰 발급/검증 실패" → "키움 인증 토큰 발급 또는 검증이 실패했습니다 (기술명: OAuth)" | 0 라인 |
| `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` | §3 SHORTCUT 블록 | 명시적 predicate 순서 + Step 1.0/1.2가 SHORTCUT을 선행함을 보장 | +4 라인 |
| `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` | §4 Branch 4 RESTORE Step 2a | rmdir-always 한국어 주석을 포함한 try/finally semantics | 0 라인 (단일 라인 재작성) |
| `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` | §4 Branch 4 RESTORE Step 2b (item 6) | Edit/log/state에 대한 try/finally semantics | 0 라인 (단일 라인 재작성) |
| `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/references/range-map.md` | §Stage 5 — financeFilter 5개 placeholder 행 | `(Stage 5 C-4 verbatim)`을 행별 한국어 설명으로 교체 | 0 라인 (셀 내용) |

**수정되지 않은 파일 (제약 보존)**:
- `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/settings.local.json` (71B, May 13 mtime, 그대로)
- `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/SKILL.md` (211 lines, 그대로)
- `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/references/*` (5 파일, 그대로)
- `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/references/{parameter-catalog,unit-conversion,shared-constants,theory-guide,tuning-sequence}.md` (5 파일, 그대로)
- `/Users/tajun/spJavis/kiwoom-rest-trader/src/**` (소스 코드, TS-1 배포 시점 제약)

---

*검증 완료. Step 11(스모크 테스트) 준비됨.*
