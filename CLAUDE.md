# CLAUDE.md — auto-korea-stock-javis 통합 라우터 (모노레포 루트)

> **정체성(1줄):** 통합 한국주식 스크리너 프로젝트 — **사용(일일 스크리닝) = `engine/`, 빌드(공장) = `factory/`**.
> 이 문서는 두 구역을 가르는 **단일 진입 라우터**이며 구역 선택 규칙만 담는다. 운영 상세는 각 구역의 CLAUDE.md에 위임한다.

---

## 1. Path Constants (경로 단일 기준)

```
AKSJ_ROOT     = /Users/tajun/spJavis/auto-korea-stock-javis
ENGINE_ROOT   = ${AKSJ_ROOT}/engine                 # 사용 모드 구역 (구 kiwoom-rest-trader)
FACTORY_ROOT  = ${AKSJ_ROOT}/factory                # 빌드 모드 구역 (구 AgenticWorkflow)
ENGINE_PYTHON = ${ENGINE_ROOT}/.venv/bin/python     # Python 3.12.7
```

- engine/CLAUDE.md의 `KRT_*` 상수는 Phase 1-2에서 신 경로로 치환 완료 — 두 문서의 경로는 동일하다(충돌 시 본 표 우선).

## 2. 라우팅 규칙 — "한 지붕, 두 구역, 일방향 문"

### 2.1 기본값 = engine (사용 모드)

스캔·튜닝·조회·비교·복원·이론 질문 등 **모든 사용 발화는 engine 구역**이다.

- **15 Intent는 이름만 인지하고, 상세 라우팅(발화 예시·Action·분기 규칙)은 `engine/CLAUDE.md`의
  Intent Routing 표에 위임한다 — 여기 복제 금지:**
  `SCAN_TODAY · SCAN_SEPARATED · SCAN_RANGE · SCAN_PAST · SHOW_RESULTS · WHY_REJECTED · SHOW_PARAMS · CHANGE_PARAM ·
  RERUN_FILTERS · RESTORE · COMPARE · COMPARE_PARAMS · THEORY_GUIDE · CONFIRM · ASK_MODULE`
- "시작" / "시작하자" / "워크플로우 시작하자" 류 **진입 발화 → engine/CLAUDE.md의 Start Routing 절**(사용 모드 진입).
  루트 세션에서는 factory의 스킬(workflow-executor·workflow-generator)이 함께 노출되지만,
  **이런 발화로 그 스킬들을 호출하지 않는다** (사용 발화의 종착지는 항상 engine).
- Mixed-intent 규칙·모호성 1회 질문(AskUserQuestion) 규칙도 engine/CLAUDE.md를 그대로 따른다.
- **모든 실행은 `cd ${ENGINE_ROOT}`에서 수행한다.**
  EXEC_PATTERN: `cd ${ENGINE_ROOT} && ${ENGINE_PYTHON} -m {module} {args}`

### 2.2 factory 진입 — 명시 발화만 (일방향 문)

- factory(빌드 구역) 진입 조건은 **단 하나**: 주인님의 명시 발화 **"공장 빌드 모드"**.
- 그 외 **어떤 분기·조건·플래그·키워드 유추·메뉴 항목으로도 factory에 진입하지 않는다.**
  진입 가능한 분기를 만들 수 있는 구조가 생기면 그 자체가 결함이다 (engine 모드 경계 절 계승).
- **engine 구역의 코드·스킬에서 factory를 호출하는 경로를 만들지 않는다.**
  (factory가 빌드 타깃으로 engine을 읽는 방향만 열려 있다 — 문은 일방향이며, 역방향은 사람의 명시 발화로만 열린다.)
- 빌드 세션은 `cd ${FACTORY_ROOT}`에서 연다 — factory의 훅·에이전트·커맨드는 그 구역 안에서만 동작한다.

### 2.3 factory/prompt/ 동결 (읽기 전용)

- `${FACTORY_ROOT}/prompt/` (12단계 빌드 비행기록 + `prompt/.claude/` 상태 파일)는 **읽기 전용 동결**이다.
- 어떤 모드·어떤 세션에서도 수정하지 않는다. 새 빌드가 필요하면 동결본 수정이 아니라 새 빌드 인스턴스로 한다.

## 3. 실행 규약 (engine 작업 공통)

| 모듈 | 실행 방식 | 소요 (실측) |
|---|---|---|
| `run_full_research_flow` · `run_prefetch` | **Bash `run_in_background:true` 필수** (Bash 600s cap 초과) | **80분 ~ 6시간** |
| `run_filters` · 개별 필터 모듈 | 동기(foreground) 가능 | < 3분 |

- **시간 기준 경고:** engine 문서 곳곳의 "10-15분" 표기는 **진부(stale)하다 — 신뢰 금지.**
  실측치 80분~6시간을 기준으로 소요 안내·watchdog·완료 판단을 한다
  (실측 근거: EXECUTION_REPORT. watchdog은 7시간 기준으로 보정 완료 — phase2/timing-fix.md).
- **masterReference 영구 보존(주인님 지령 2026-06-13):** 날짜별 `masterReference.md`/`.log`와 `tuning-log.md`는
  **튜닝 핵심 자원**으로 git 추적 대상이다. 스캔·탈락분석·수기 기입 후 변경분을 커밋·push하라
  (`git add engine/reports/*/masterReference.* engine/reports/tuning-log.md && git commit && git push`).
  재스캔 시 수기 입력은 코드가 보존한다(plain_text.py 보존 분기 — 빈 초기화 금지).
- 백그라운드 시작 안내·완료 4-step 핸들러는 engine/CLAUDE.md Execution Template을 따르되,
  사용자에게 말하는 소요 시간만 위 실측치로 정정해 안내한다.
- `source .venv/bin/activate && python …` 형태 금지 — `${ENGINE_PYTHON}` 직접 호출만 허용.

## 4. 시크릿 규칙

- API 키·시크릿은 **`${ENGINE_ROOT}/.env` 한 곳에만** 둔다 (권한 0600).
- `*.example` 파일(`engine/.env.example` 등)에는 **실제 값 기입 금지** — 플레이스홀더만 허용.
- `.env`의 값을 cat·echo·로그·보고서·커밋 어디에도 노출하지 않는다.

## 5. .claude 격리 (1줄 원칙)

- **차단형 훅(factory의 7이벤트 exit-2 훅)은 루트 `.claude`로 승격(hoist) 금지** — 루트 `.claude`는 최소 라우팅만 두고,
  일일 운영 세션은 `${ENGINE_ROOT}/`에서 열어 훅 0건·스킬 2개(stock-scan·filter-tune)의 깨끗한 환경을 보장한다.

## 6. 세션 오픈 위치 가이드 (요약)

| 목적 | 여는 위치 | 이유 |
|---|---|---|
| 일일 스크리닝 운영 (14 Intent) | `${ENGINE_ROOT}/` | 훅 0건 · engine 스킬 2개만 노출 — 라우팅 오발·레이턴시 면역 |
| 공장 빌드 (명시 발화 후) | `${FACTORY_ROOT}/` | 빌드 훅·에이전트·커맨드가 해당 구역에서만 정상 동작 |
| 횡단 관리·라우팅 점검 | `${AKSJ_ROOT}/` (루트) | 본 라우터 적용 — 단, 실행은 §2.1에 따라 `cd ${ENGINE_ROOT}` |

> 문서 충돌 시 우선순위: 경로 = 본 문서 §1 → 그 외 운영 상세 = 각 구역 CLAUDE.md → 통합 원칙 = BUILD_PLAN.md §2.
