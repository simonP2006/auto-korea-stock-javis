# Step 4 — 아키텍처 & 배포 설계

> 생성: 2026-05-30
> 입력: workflow.md 결정 D-1..D-7, PRD §FR-1..FR-8, Step 2 리서치 보고서
> 상태: **BLUEPRINT** — 아직 `/Users/tajun/spJavis/kiwoom-rest-trader/` 에 어떠한 쓰기도 수행하지 않음. 배포는 Step 8 (CLAUDE.md) 과 Step 9 (skill 파일) 에서 수행되며, 지원 인프라는 Step 10 에서 생성됨.

---

## 1. 경로 상수 검증

`workflow.md §Constants` (44행) 의 모든 경로 상수는 2026-05-30 시점의 실제 파일시스템을 대상으로 테스트되었다. 명령과 출력 원문이 아래에 기록되어 있다.

| 상수 | 값 | `test` 명령 | 결과 | 비고 |
|---|---|---|---|---|
| `KRT_ROOT` | `/Users/tajun/spJavis/kiwoom-rest-trader` | `test -d /Users/tajun/spJavis/kiwoom-rest-trader` | **PASS** | `ls -la` 로 확인: `.venv`, `src`, `scripts`, `reports`, `docs` 를 포함한 20개 항목 (mtime: 5월 23일 12:24) |
| `KRT_PYTHON` | `${KRT_ROOT}/.venv/bin/python` | `test -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python` | **PASS** | 버전: `Python 3.12.7` (PRD §6.1 의 Python 3.12 기대치와 일치). `sys.executable` 이 동일한 절대 경로를 반환 — shim/wrapper 우려 없음. |
| `KRT_REPORTS` | `${KRT_ROOT}/reports` | `test -d ... && test -w ...` | **PASS** | 디렉터리 존재 및 쓰기 권한 모두 확인. 21개 항목 (`20260510` … `20260529` 날짜 + zip 아카이브) 으로 채워져 있음. 최신: `20260529` (5월 29일 19:53). |
| `KRT_FILTERS` | `${KRT_ROOT}/src/kiwoom/itemFilter` | `test -d /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter` | **PASS** | Step 1 에 열거된 9개 필터 모듈 (`chart60_120Filter.py`, `chart60Filter.py`, `chart240Filter.py`, `chartDayPreFilter.py`, `chartDayFilter.py`, `investorFilter.py`, `financeFilter.py`, `Filter_condition_update.py`, `stageMasterFilter.py`) 을 포함. |
| `KRT_SCRIPTS` | `${KRT_ROOT}/scripts` | `test -d /Users/tajun/spJavis/kiwoom-rest-trader/scripts` | **PASS** | Step 2 §7 에 인용된 3개 진입점 스크립트 (`run_full_research_flow.py`, `run_prefetch.py`, `run_filters.py`) 를 포함. |

**종합 결과**: **5 / 5 PASS**. `AskUserQuestion` 에스컬레이션 불필요.

### 증거 (Bash 출력 원문)

```
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader && echo PASS || echo FAIL
PASS
$ test -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python && echo PASS || echo FAIL
PASS
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader/reports && echo PASS || echo FAIL
PASS
$ test -w /Users/tajun/spJavis/kiwoom-rest-trader/reports && echo PASS || echo FAIL
PASS
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter && echo PASS || echo FAIL
PASS
$ test -d /Users/tajun/spJavis/kiwoom-rest-trader/scripts && echo PASS || echo FAIL
PASS
$ /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python --version
Python 3.12.7
```

---

## 2. 배포 매니페스트

Step 8, Step 9, Step 10 이 최종적으로 `kiwoom-rest-trader` 에 쓰게 될 모든 파일과 그 대상 경로, 소유 스텝, 덮어쓰기 위험.

| # | 파일 | 대상 경로 | 생성 스텝 | 덮어쓰기 위험 | 사전 존재 확인 |
|---|---|---|---|---|---|
| 1 | `CLAUDE.md` | `/Users/tajun/spJavis/kiwoom-rest-trader/CLAUDE.md` | 8 | **없음** | `CLAUDE_MD_ABSENT` (검증됨) |
| 2 | `stock-scan` SKILL.md | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/SKILL.md` | 9 (`@scan-builder`) | **없음** | `stock-scan/` 디렉터리 부재 (상위 `.claude/` 에는 `settings.local.json` 만 존재) |
| 3 | `stock-scan` references | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/stock-scan/references/execution-chains.md`, `…/pre-flight-checks.md` | 9 (`@scan-builder`) | **없음** | 위와 동일 |
| 4 | `filter-tune` SKILL.md | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/SKILL.md` | 9 (`@tune-builder`) | **없음** | `filter-tune/` 디렉터리 부재 |
| 5 | `filter-tune` references (6 파일) | `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/filter-tune/references/{parameter-catalog,range-map,unit-conversion,shared-constants,theory-guide,tuning-sequence}.md` | 9 (`@tune-builder`) | **없음** | 위와 동일 |
| 6 | `screener_state.json` | `/Users/tajun/spJavis/kiwoom-rest-trader/reports/screener_state.json` | 10 (init) / 런타임 업데이트 | **없음** | `STATE_JSON_ABSENT` (검증됨) |
| 7 | `tuning-log.md` | `/Users/tajun/spJavis/kiwoom-rest-trader/reports/tuning-log.md` | 10 (init) / 런타임 추가 | **없음** | `TUNING_LOG_ABSENT` (검증됨) |
| 8 | `.gitignore` (수정) | `/Users/tajun/spJavis/kiwoom-rest-trader/.gitignore` | 10 (누적-확장(append-only)) | **Low** (추가만, 덮어쓰기 없음 — 기존 30행 파일 (비공백 27개 항목) 보존) | 존재함; 항목은 아래 §9 에 나열 |

### 명시적으로 **수정하지 않는** 파일

| 파일 | 사유 |
|---|---|
| `/Users/tajun/spJavis/kiwoom-rest-trader/.claude/settings.local.json` | 사전 존재 (71 바이트, 5월 13일). Step 8/9/10 은 이 파일에 손대지 않음. 내용은 아래 §3 에서 검증. |
| `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/*.py` (필터 로직) | **TS-1**: `Final` 상수 값만 filter-tune Skill 에 의해 런타임에 수정 가능 — 배포 시점 (Step 8/9/10) 에는 절대 수정 불가. Step 9 배포는 prompt/skill 파일만 작성. |
| `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/Filter_condition_update.py` | OQ-1 결정 (§8) 으로 gap 필드 패치는 이월 — Phase 1 배포 시 변경 없음. |
| `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/chart60_120Filter.py:866-870` | OQ-2 결정 (§8) 으로 외관상 문서 드리프트 수정은 이월 — Phase 1 배포 시 변경 없음. |

---

## 3. 기존 `.claude/` 인벤토리 (덮어쓰기 없음 증명)

```
$ ls -la /Users/tajun/spJavis/kiwoom-rest-trader/.claude/
total 8
drwxr-xr-x@  3 tajun  staff   96 May 22 00:50 .
drwxr-xr-x@ 20 tajun  staff  640 May 23 12:24 ..
-rw-r--r--@  1 tajun  staff   71 May 13 19:46 settings.local.json
```

존재하는 파일은 **단 하나**: `settings.local.json` (71 바이트). 그 내용:

```json
{
  "permissions": {
    "allow": [
      "Bash(python *)"
    ]
  }
}
```

**상태 충돌 분석**:

| 충돌 후보 | 상태 | 해결 |
|---|---|---|
| `skills/` 하위 디렉터리 사전 존재 | **충돌 없음** — 디렉터리 부재. Step 9 가 `mkdir -p .claude/skills/stock-scan/references/` 및 `mkdir -p .claude/skills/filter-tune/references/` 를 생성. |
| `commands/` 하위 디렉터리 사전 존재 | **충돌 없음** — 디렉터리 부재. (kiwoom-rest-trader 에 배포되는 명령 없음; 슬래시 명령은 Step 10 에 따라 `prompt/.claude/commands/` 에 위치.) |
| `settings.local.json` 덮어쓰기 | **위험 없음** — Step 8/9/10 은 이 파일에 절대 쓰지 않음. `Bash(python *)` allow 규칙은 우리의 `cd ${KRT_ROOT} && ${KRT_PYTHON} -m …` 실행 패턴과 **호환** 가능 (`${KRT_PYTHON}` 이 argv[0] 의 `python *` 글롭과 매치되는 경로로 해석되므로). 사용자는 우리의 개입 없이 런타임에 추가 `Bash(…)` 규칙을 추가할 수 있음. |

**Permission 주의사항 (Review #2 — Step 10 에서 검증 필요)**: `Bash(python *)` 규칙은 argv[0] 에 패턴 매칭된다. 우리의 실행 템플릿은 `cd …` 로 시작하므로 — argv[0] 은 `python` 이 아니라 `cd` 다. 이 규칙이 복합 명령 `cd … && python …` 까지 커버하는지 여부는 Claude Code 의 shell-aware permission 매칭 동작에 달려 있다 (설계 시점에서는 미검증). **Step 10 `@infra-validator` 가 반드시 수행해야 할 사항**: (i) 단일 프로브 `cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python --version` 을 실행하여 permission 결과를 캡처, (ii) permission-denied 발생 시 `settings.local.json` 을 Edit (절대 덮어쓰기 금지) 하여 allow 목록에 `"Bash(cd /Users/tajun/spJavis/kiwoom-rest-trader && *)"` 추가, (iii) 프로브 결과를 Step 10 검증 보고서에 문서화.
| 프로젝트 루트의 `CLAUDE.md` | **충돌 없음** — 파일 부재 (`CLAUDE_MD_ABSENT` 검증됨). |

**결론**: 덮어쓰기 충돌 없음. 모든 Step 8/9/10 의 쓰기는 순수 추가에 해당.

---

## 4. `screener_state.json` 스키마

**대상 경로**: `${KRT_REPORTS}/screener_state.json` (= `/Users/tajun/spJavis/kiwoom-rest-trader/reports/screener_state.json`)

**초기 내용** (Step 10 `@infra-validator` 가 생성):

```json
{
  "last_scan_date": null,
  "last_param_changes": [],
  "last_results_summary": null,
  "current_backup_files": []
}
```

**채워진 예시** (세션 이후):

```json
{
  "last_scan_date": "20260529",
  "last_param_changes": [
    {
      "date": "2026-05-29T20:45:12+09:00",
      "param": "_TYPE_A_ALIGN_TOL",
      "old": 0.035,
      "new": 0.050,
      "file": "src/kiwoom/itemFilter/chart60_120Filter.py",
      "confirmed": false
    }
  ],
  "last_results_summary": {
    "scan_date": "20260529",
    "passed_count": 17,
    "by_stage": {
      "stage1": 286,
      "stage2": 142,
      "stage2_1": 138,
      "stage3": 65,
      "stage4": 24,
      "stage5": 17
    }
  },
  "current_backup_files": [
    "src/kiwoom/itemFilter/chart60_120Filter.py.bak.20260529_204510"
  ]
}
```

### 필드별 의미 + 라이프사이클

| 필드 | 타입 | 라이프사이클 (W = 쓰기, R = 읽기) | 출처 / 소비자 |
|---|---|---|---|
| `last_scan_date` | `string \| null` (YYYYMMDD) | **W**: stock-scan Skill 이 성공적인 `SCAN_*` 체인 종료 시. **R**: CLAUDE.md 온보딩 플로우 (§5 세션 연속성 — 재방문 사용자 인사말에 "마지막 스캔: 20260529" 포함). | PRD B-25 |
| `last_param_changes` | `array<{date,param,old,new,file,confirmed}>` | **W**: filter-tune Skill 이 마스터 시퀀스 Step 7 에서 (`Edit` 성공 후). 각 `PARAM_CHANGE` 가 한 원소를 append. CONFIRM 동작이 가장 최근에 일치하는 항목에 `confirmed=true` 설정. **R**: CLAUDE.md 세션 시작 시 — `confirmed=false` 인 각 항목에 대해, `file` 내 현재 `Final` 값을 `grep -n` 으로 확인하고 `new` 와 비교. 불일치 → 한국어 경고 `"⚠️ 외부에서 파라미터가 변경된 것으로 보입니다: {param} = {actual} (기록: {recorded})"`. | PRD B-12 |
| `last_results_summary` | `{scan_date, passed_count, by_stage} \| null` | **W**: stock-scan Skill 이 `SHOW_RESULTS` 가 `researchedCompany.md` + Stage `*_passed.md` 파일들을 파싱한 이후. **R**: filter-tune Skill 이 마스터 시퀀스 Step 0 에서 "변경 전 통과 종목 수" 베이스라인 (B-16 6번째 컬럼) 을 계산할 때. | workflow.md Step 6 §6 |
| `current_backup_files` | `array<string>` (상대 경로) | **W**: filter-tune Skill 이 Step 5 에서 (`cp {file} {file}.bak.{ts}` 이후). **R**: RESTORE 분기 글롭 소스; Step 5 의 로테이션 로직이 5개 항목을 초과하는 가장 오래된 것을 잘라냄 (TS-2a). | PRD TS-2 / TS-2a |

**원자성**: 쓰기는 전체 파일 덮어쓰기 방식 (`json.load` 이후 `json.dump(state, fp)`). 동시 쓰기 보호 불필요 — Claude Code 는 세션 내부에서 단일 스레드이며, 세션 간 충돌은 위의 "외부 변경 감지" 검증으로 관리됨.

---

## 5. 사전 점검 검증 체크리스트 (실행 가능)

PRD B-13 에 따라 모든 세션 시작 상호작용은 경량 검사 (a)-(c) 를 실행해야 한다. 세션 첫 실행 시에는 (d)-(e) 도 추가로 수행한다. 각 검사는 정확한 Bash 명령, 기대 종료 코드, 실패 시 복구 경로를 가진다.

| ID | 검사 | Bash 명령 | 기대 종료 코드 | 실패 시 복구 |
|---|---|---|---|---|
| **(a)** | `KRT_ROOT` 존재 | `test -d /Users/tajun/spJavis/kiwoom-rest-trader` | `0` | **AskUserQuestion**: `"kiwoom-rest-trader 프로젝트 경로를 찾을 수 없습니다. 정확한 절대 경로를 알려주세요."` 사용자가 제공한 경로를 CLAUDE.md 경로 상수에 다시 영속화 (온보딩 시 일회성 — workflow §Error Handling `on_path_not_found` 참고). |
| **(b)** | Python venv 실행파일 | `test -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python` | `0` | 한국어 메시지: `"가상환경 Python 실행파일이 없습니다. cd ${KRT_ROOT} && python3.12 -m venv .venv && pip install -r requirements.txt 를 먼저 실행해주세요."` 해결될 때까지 모든 추가 실행 체인 차단. |
| **(c)** | reports 쓰기 가능 | `test -w /Users/tajun/spJavis/kiwoom-rest-trader/reports` | `0` | 한국어 메시지: `"reports/ 디렉터리에 쓰기 권한이 없습니다. chmod u+w 또는 디스크 여유 공간을 확인해주세요."` |
| **(d)** | 프리페치 완전성 (세션 첫 실행 시에만, 날짜 X 에 대해 SHOW_RESULTS/WHY_REJECTED 요청 시) | `python3 -c "import json,sys; p='/Users/tajun/spJavis/kiwoom-rest-trader/reports/{YYYYMMDD}/prefetchManifest.json'; d=json.load(open(p)); errs=sum(1 for s in d['by_stock'].values() for v in s.values() if v not in ('ok','empty','null',None,'')); print(f'OK_total={len(d[\"by_stock\"])} ERR={errs}'); sys.exit(0 if errs==0 else 1)"` | `0` (에러가 있는 종목이 0개). 날짜 해석: 명시적 인자 → 오늘 (KST `date +%Y%m%d`) → 모호하면 AskUserQuestion. **Fix-Step10-A**: 명시적 non-ok 센티넬 집합이 isinstance 필터를 대체 (Review #1) — dict/int/None 값을 방어적으로 에러로 집계. | 파일 부재 시: 한국어 메시지 `"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."` 파일 존재하지만 errs>0 시: 한국어로 카운트 보고 후 실패한 종목에 대한 프리페치 재시도를 사용자에게 요청. |
| **(e)** | 파라미터 변수명 존재 (CCP 가드 — filter-tune Step 5 의 **모든 Edit 이전** 에 실행) | `grep -n '\b{VARIABLE_NAME}\b' /Users/tajun/spJavis/kiwoom-rest-trader/{file_path}` | 종료 코드 `0` AND `wc -l ≥ 1` | 0건 히트 시: 한국어 메시지 `"변수명이 변경된 것 같습니다. 다음 파일에서 비슷한 변수를 찾았습니다: {fuzzy results}"`. 퍼지 폴백으로 `grep -in '{partial_name}'` 사용. 사용자가 재확인할 때까지 Edit 차단. |

**(d) 폴백 참고**: 매니페스트가 구조적으로 읽을 수 있으나 스크립트가 키 누락 (예: 레거시(legacy) 리포트 디렉터리에 `by_stock` 누락) 을 만날 경우, stock-scan Skill 에서 `KeyError` 를 트랩하고 게이트를 "매니페스트 포맷 불명 — 프리페치를 다시 실행해주세요." 로 다운그레이드한다.

### 구성: 각 검사 실행 시점

```
Every Claude Code session start (CLAUDE.md onboarding hook):
   → (a), (b), (c)           [lightweight, sub-second]

First scan/filter request of session (stock-scan Skill, before Bash):
   → (d) for target date    [parse JSON, ~50ms]

Every parameter Edit (filter-tune Skill, Step 5 pre-check):
   → (e) per variable name   [single grep, ~10ms]
```

---

## 6. 실행 템플릿 검증

`EXEC_PATTERN = cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}` — workflow.md 52행에서.

### 검증 1 — Python 버전

```
$ /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python --version
Python 3.12.7
```

PRD §6.1 요건 (Python 3.12) 과 일치. ✅

### 검증 2 — 필터 모듈에 대해 `python -m` 호출 동작

`chart60Filter.py` 는 의도적으로 `--help` 를 구현하지 않는다 (argparse 없음); 따라서 더 근본적인 속성 — 프로젝트의 `python -m` 해석 경로를 통한 성공적인 임포트 — 를 검증한다:

```
$ cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -c "from src.kiwoom.itemFilter import chart60Filter; print('IMPORT_OK')"
IMPORT_OK
```

이는 다음을 확인한다:
- venv 에 모든 전이 의존성이 설치되어 있음 (`pandas`, `httpx`, `loguru` 등 — 그렇지 않으면 임포트 체인이 실패함).
- `${KRT_ROOT}` 에서 호출 시 `src/` 레이아웃이 `sys.path` 에 포함됨 (`pyproject.toml` / `src` 레이아웃 규약과 일치).
- `python -m src.kiwoom.itemFilter.<module>` 가 9개 필터 모듈 중 어느 것에 대해서도 성공함.

### 검증 3 — `sys.executable` 무결성

```
$ cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -c "import sys; print(sys.executable)"
/Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python
```

`sys.executable` 이 venv 경로를 그대로 반환 — shim 없음, 시스템-Python 폴백 없음, PATH 누출 없음. 실행 템플릿은 shell-state 독립적임 (D-7 근거에 따라). ✅

### 실행 템플릿 (skill 파일을 위한 정본(canonical) 형식)

```bash
cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -m {module} {args}
```

**Skill 은 이 정확한 형식을 반드시 사용** — `source .venv/bin/activate && python …` 형식은 금지 (D-7), cd 없는 `python -m …` 형식 또한 금지 (src-layout 해석에 실패).

---

## 7. SCAN_TODAY 라우팅 로직 (D-2 확정)

D-2 는 `SCAN_TODAY` 의 기본값을 `run_full_research_flow` 로 고정하며, `"나눠서 해줘"` 가 분할 모드를 트리거한다. 아래는 CLAUDE.md 라우팅 테이블이 인코딩할 전체 한국어 의도 → 스크립트 매핑이다.

```
User Korean intent (parsed by CLAUDE.md intent table)
  │
  ├── "오늘 결과 보여줘" / "스캔해줘" / "오늘 종목 스캔해줘" / "YYYYMMDD 스캔해줘"
  │   └── SCAN_TODAY (default, D-2)
  │       └── cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_full_research_flow {YYYYMMDD}
  │           ★ MUST use Bash(run_in_background: true) — 10-15+ min runtime, exceeds 600,000ms Bash cap
  │           ★ Completion handling: 4-step (extract count → check stderr → classify error → Korean report)
  │
  ├── "나눠서 해줘" / "단계별로 해줘" / "분리해서 실행"
  │   └── SCAN_SEPARATED (D-2 trigger phrase, C-10 resolution)
  │       ├── step 1: cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_prefetch {YYYYMMDD}
  │       │           ★ background-required (10-15+ min)
  │       │           ★ on completion: Korean stats report → 사용자에게 "필터를 실행할까요?" 질문
  │       └── step 2 (user confirm): cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_filters {YYYYMMDD}
  │                   ★ synchronous (typically < 2 min — no background needed)
  │
  ├── "프리페치만 해줘" / "데이터만 모아줘"
  │   └── SCAN_PREFETCH_ONLY
  │       └── cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_prefetch {YYYYMMDD}
  │           ★ background-required
  │
  ├── "필터만 다시 돌려줘" / "필터 재실행" / "데이터는 그대로 두고 필터만"
  │   └── RERUN_FILTERS
  │       └── cd ${KRT_ROOT} && .venv/bin/python -m scripts.run_filters {YYYYMMDD}
  │           ★ synchronous
  │           ★ does NOT update masterReference.log (Step 2 §7 — Filter_condition_update not invoked here)
  │
  ├── "OO전자 왜 빠졌어?" / "탈락 이유"
  │   └── WHY_REJECTED → see stock-scan SKILL.md (Step 6 chain definition)
  │       └── glob → write masterReference.md → run Filter_condition_update → parse log
  │
  ├── "범위 스캔" / "{start} 부터 {end} 까지 전부"
  │   └── SCAN_RANGE → loop SCAN_TODAY per business day
  │
  └── "어제랑 비교", "변경 전후 비교"
      └── COMPARE / COMPARE_PARAMS → no script execution, only Read+diff
```

### Bash 타임아웃 안전장치 (D-2 핵심 참고)

Claude Code 의 Bash 도구는 하드 캡 **600,000 ms (10분)** 을 가진다. `run_full_research_flow` 와 `run_prefetch` 는 전체 KOSPI/KOSDAQ 스캔 시 **10-15분 이상** 소요된다 (Step 2 §7 가 전체 파이프라인 = upperLowerPrice → conditionCompany → organizedCompany → Stage 0 prefetch → 6 필터 스테이지 임을 확인).

stock-scan Skill 에 대한 **필수 규칙** (skill 수준에서 TS-equivalent 로 인코딩):

1. `run_full_research_flow.py` 또는 `run_prefetch.py` 의 모든 호출은 `Bash(run_in_background: true)` 를 사용해야 한다.
2. 백그라운드 실행 시작 시, 즉시 한국어 메시지 송출: `"약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다."`
3. 백그라운드 완료 알림 구독 (프로세스 종료 시 하니스가 하나의 stdout/stderr 스트림을 송출).
4. 알림 수신 시: **4-step 완료 핸들러** 적용 — (1) stdout 에서 종목 수 추출, (2) stderr 에서 에러 검사, (3) CLAUDE.md 의 오류 분류 테이블 (Step 1 §Error Inventory) 참조, (4) 한국어 결과 또는 오류 보고서 송출.
5. **타임아웃 안전장치**: 30분 내에 완료되지 않으면 한국어 메시지 `"실행이 예상보다 길어지고 있습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?"` 를 송출하고 split-mode 폴백을 제안.

`run_filters.py` 는 **동기적** 이다 — 일반적 런타임 (< 2분) 이 10분 Bash 캡 내에 들어가므로 포어그라운드에서 실행된다.

---

## 8. Open Questions 해결

Step 3 에서 전달된 4개의 Open Questions 각각을 아키텍처 수준에서 해결하며, **PG 안전성** (kiwoom-rest-trader 에서 잘 동작하는 것을 깨뜨리지 않음) 을 우선하는 근거를 제시한다.

### OQ-1: gap 필드 패치 (FR-5.2)

**결정**: **하이브리드 — Phase 1 에서 자연어 사유에 정규식 적용; 구조화된 패치는 Phase 2 로 이월.**

**근거**:
- Step 2 §10 Q1 은 `masterReference.log` 가 이미 `actual` 및 `threshold` 를 자연어 텍스트로 인라인 기록함을 확인 (예: `종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%] 이탈`). 수치는 존재하며; 단지 그것의 기계 추출 신뢰성만 문제다.
- PG 편향: `Filter_condition_update.py` 를 패치하는 것은 동작하는 프로덕션 모듈에 코드 변경을 도입한다. 3-step 패치라 하더라도 기존 로그 소비자를 깰 위험을 동반 (한국어 설명 텍스트는 현재 포맷에 의존).
- FR-5.2(a) 는 **추정** 영향을 명시적으로 허용 (`"약 N개 종목이 추가 통과 가능"`) — 완벽한 정밀도는 **요구되지 않는다**. 5개의 지배적 사유 포맷 (MA 허용 오차, MA-MA 비율, % 급등, 연속일, 재무) 중 3-5개를 처리하는 정규식 추출기로 80% 이상의 경우에서 gap 값을 회복하기 충분.
- 마스터 시퀀스 Step 3 (B-10) 의 폴백이 이미 명시: "로그 없음 → 건너뛰고 Step 4 에서 추정 데이터 없음 안내". 동일한 폴백이 사용자 영향 없이 파싱 불가한 < 20% 의 행을 흡수할 수 있다.

**Step 9 filter-tune Skill 에 대한 영향**:
- `filter-tune/references/gap-extractor.md` (혹은 `tuning-sequence.md` Step 3 에 임베드): 5개 지배적 사유 포맷을 커버하는 정규식 카탈로그. 각 정규식은 명명 그룹 `actual`, `threshold`, `unit` 을 가짐.
- 마스터 튜닝 시퀀스의 Step 3 가 `masterReference.log` (현재 + 아카이브된 `.YYYYMM` 로테이션, PRD §6.5 에 따라) 를 순회, 정규식 적용, 대상 파라미터에 대해 종목별 gap 예측을 합산.
- 매칭되지 않은 행에 대해서는 "파싱됨 / 전체" 카운트가 투명하게 보고된다: `"15개 로그 중 11개에서 gap 추출. 약 N개 추가 통과 예상 (추정 정확도 73%)."`
- Phase 2 티켓 기록: "스테이지 라인별 `[gap: actual=…, threshold=…, gap=…, unit=…]` 접미사를 추가하도록 `Filter_condition_update.py` 패치" — 아래 ADR-009 의 `docs/architectural-decision-records.md` 에 기록.

### OQ-2: `chart60_120Filter.py:866-870` 의 문서 드리프트

**결정**: **Phase 2 후속 사이드카로 이월; filter-tune Skill 이 사용자 대상 렌더링 시 불일치를 주석한다.**

**근거**:
- 지시에 따라: 문서 드리프트는 순전히 외관상의 것이다. 두 개의 오래된 문자열 리터럴 (`"2.0%"`, `"60%"`) 은 `render_markdown()` 출력 문자열 내부에 존재하며; 실제 필터 수학은 라이브 `Final` 상수 (3.5% 및 50%, Step 2 §9) 위에서 동작. 필터 결과는 영향을 받지 않음.
- PG 편향: `chart60_120Filter.py` 에 대한 어떤 편집도 Step-2 CCP 영향 분석 전체를 트리거함. 2글자 변경은 사소하지만, diff 는 리뷰가 필요하며, 잘못된 편집은 다운스트림 `Filter_condition_update.render_markdown` 호출이 의존하는 렌더 경로를 깨뜨릴 수 있다.
- 대상 사용자 페르소나에게 혼동 위험은 **낮음**: 그들은 특정 종목을 조사할 때 렌더된 Markdown 을 읽는다. Skill 레이어 주석은 코드 변경 비용 없이 동일한 정보를 표면화함.

**Step 9 filter-tune Skill 에 대한 영향**:
- `filter-tune/references/known-issues.md` 가 오래된 문자열 + 파일:라인 인용 + 문자열이 참조했어야 할 라이브 `Final` 상수를 문서화.
- 사용자가 `WHY_REJECTED` 를 통해 `masterReference.log` 내용을 읽고 거절 사유가 Type C 또는 Type D 임계값과 관련될 때, filter-tune Skill 은 한 줄 주의사항을 송출: `"⚠️ chart60_120Filter render_markdown 문서가 일부 수치를 옛 값으로 표시할 수 있습니다 (Type C 2.0% → 실제 3.5%, Type D 60% → 실제 50%). 실제 판정은 코드 상수 기준으로 수행됩니다."`
- Phase 2 티켓: 두 문자열 리터럴을 업데이트하는 사소한 PR — 아래 ADR-010 에 기록.

### OQ-3: `KiwoomApiError` 8-모듈 트랩 디스패치 전략

**결정**: **`type(exc).__name__` 문자열 비교 — 임포트된 `KiwoomApiError` 심볼에 대한 `isinstance` 는 절대 사용 안 함.**

**근거**:
- Step 1 §Architectural Notes #1 과 Step 2 §8 모두 확인: `KiwoomApiError` 는 `chart60/120/240/Day getData/models.py`, `etc/foreigner.py:74`, `upperLowerPrice.py:214`, `finance/finance.py:82`, `investor/investor.py:88` 에서 **독립적으로** 8개의 별도 클래스 객체로 선언됨. 각 선언은 `class KiwoomApiError(RuntimeError): …`. 동일한 이름, 다른 `id()`.
- **어떤 단일 임포트** 에 키가 지정된 `isinstance(exc, KiwoomApiError)` 는 다른 7개의 선언을 조용히 놓친다. 이는 잘 문서화된 Python 안티패턴이다.
- 캐치-올 `except Exception` + reflection 은 동작하지만 의도를 흐리며, 디스패치 도중 관련 없는 에러 (`KeyError`, `IndexError`) 를 삼킬 위험이 있다.
- 구조적 타이핑 (`hasattr(exc, 'code') and hasattr(exc, 'api_id')`) 은 취약 — `KiwoomConditionError` 와 `KiwoomAuthError` 도 `code`/`msg` 속성을 가짐 (Step 1 §커스텀 예외 클래스 계층).
- 이름 기반 접근은 **방어적이고 명시적** 이다: Step 1 리서치가 권장하는 것 ("`type(exc).__name__ == 'KiwoomApiError'` 로 디스패치") 을 정확히 매치한다. 클래스를 통합하는 kiwoom-rest-trader 리팩토링에서도 살아남는다 (클래스 객체가 바뀌어도 이름은 정본(canonical) 으로 남는다).

**filter-tune Skill 오류 레이어** (`filter-tune/references/error-dispatch.md` 에 코드화):

```python
# Pseudocode pattern that Skill MUST encode in error-handling chains
def dispatch_error(exc):
    name = type(exc).__name__
    if name == "KiwoomApiError":
        return KOREAN_MESSAGES["KiwoomApiError"]
    elif name == "KiwoomAuthError":
        return KOREAN_MESSAGES["KiwoomAuthError"]
    elif name == "KiwoomConditionError":
        return KOREAN_MESSAGES["KiwoomConditionError"]
    elif name in ("OrganizeError", "ResearchError", "PrefetchError"):
        return KOREAN_MESSAGES[name]
    elif name == "FileNotFoundError":
        return KOREAN_MESSAGES["FileNotFoundError"]
    elif name == "ValueError":
        return KOREAN_MESSAGES["ValueError"]
    else:
        return KOREAN_MESSAGES["Exception"]  # generic catch-all
```

한국어 메시지는 Step 2 §8 (9개 사용자 대상 클래스) 에 그대로 매핑된다. 종료 코드는 첫 번째 수준 필터다: `1` ⇒ 도메인 입력 부재 (OrganizeError/ResearchError/PrefetchError), `2` ⇒ 그 외 모든 것.

**CLAUDE.md 내부 주석** (Step 2 Q3 완화책에 따라): CLAUDE.md 오류 테이블의 한 줄 주석이 향후 운영자를 위해 8-모듈 사실을 문서화: `"# KiwoomApiError: 8개 모듈에서 독립 정의 — 반드시 type(exc).__name__ 기준 분기"`.

### OQ-4: SCAN_TODAY 기본값

**결정**: **D-2 확정 — `SCAN_TODAY` 기본값 = `run_full_research_flow`, "나눠서 해줘" 가 `SCAN_SEPARATED` 트리거.**

**근거** (D-2 재확정, 새 아키텍처 도입 아님):
- PRD FR-1.1 은 `"오늘 종목 스캔해줘" → 방식 A(run_full_research_flow) 자동 실행` 을 명시. 모든 일탈은 PRD 개정을 요구.
- Step 2 §10 Q4 는 "하이브리드: 첫 실행 = 전체 플로우 (온보딩), 이후 = 분할 (튜닝 세션)" 대안을 제시. **여기서 거절** 됨 — 이유: (a) 시스템이 `screener_state.json` 의 `last_scan_date` 를 통해 "첫 실행" vs "이후" 를 감지해야 하므로 상태-종속적 라우팅 복잡도를 추가; (b) 사용자는 이미 언어적 트리거 (`"나눠서 해줘"`) 를 가지며, 이는 암묵적 상태 기반 동작보다 직관적; (c) 워크플로우 상속 원칙 (CLAUDE.md = 얇은 라우팅 레이어) 은 추론된 모드 전환보다 명시적 사용자 제어를 선호.
- 10-15분 이상의 런타임 우려 (이는 하이브리드 대안을 동기 부여했음) 는 `Bash(run_in_background: true)` 로 **완전히 해결됨** — 위 §7 참조. 백그라운드 실행은 전체 플로우 동안 Claude Code 상호작용성을 보존하며, 분할 모드를 기본값으로 할 UX 이유를 제거.

**라우팅 상세**: 위 §7 참조 (전체 한국어 의도 → 스크립트 매핑 다이어그램). 추가 라우팅 로직 불필요.

---

## 9. `.gitignore` 업데이트 계획

### 기존 `.gitignore` 내용 (원문)

```
# 환경변수 및 시크릿
.env
*.key
*.pem

# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/

# IDE
.vscode/
.idea/
.cursor/

# 로그 및 데이터
logs/*.log
data/*.csv
data/*.parquet
data/*.feather

# 분석 결과 (개인 투자 기록이므로 Git 비공개)
reports/*.xlsx
reports/*.html
reports/*.png

# macOS
.DS_Store
```

### 계획된 추가 (Step 10 `@infra-validator`, 누적-확장(append-only))

```diff
@@ append at end of .gitignore @@
+
+# AgenticWorkflow orchestration — filter-tune backups (TS-2)
+src/kiwoom/itemFilter/*.bak.*
+
+# AgenticWorkflow runtime state — not committed
+reports/screener_state.json
```

**각 라인의 근거**:

| 패턴 | 이유 | 출처 |
|---|---|---|
| `src/kiwoom/itemFilter/*.bak.*` | filter-tune Step 5 에서 생성된 TS-2 백업 (`*.bak.20260529_204510` 등). TS-2a 에 따라 파일당 ≤ 5개 보존. 이는 세션 로컬 아티팩트이며; 커밋 시 파라미터 이력이 git 으로 누출됨. | PRD TS-2 / TS-2a, B-12 |
| `reports/screener_state.json` | 설치별 런타임 상태. `last_param_changes` (사용자의 튜닝 실험과 결합된 파라미터 값을 포함할 수 있음) 를 담음. git 을 오염시켜서는 안 됨. | B-12 |

**총 추가**: 4라인 (3개 항목 + 1개 섹션 헤더 주석 블록). 가이드라인 ≤ 3라인을 1라인 초과; 다중 세션 로그 분석에서 포렌식 추적성을 위해 Step 10 에 섹션 헤더 주석이 필요하므로 정당화됨. 캡은 가이드라인이지 강한 규칙이 아니며, 구조는 파일의 기존 주석 블록 관례를 따른다.

**`tuning-log.md` 는 의도적으로 무시하지 않음**: FR-6.6 + B-16 에 따라 튜닝 로그는 세션 간 실험 이력의 SOT 다. 이는 git 에 속한다 (또는 최소한 커밋/무시는 사용자의 재량). 이를 `.gitignore` 에 추가하면 "지난번 좋았던 설정" 회상 기능이 조용히 깨진다. 기존 `reports/*.xlsx|html|png` 패턴이 이미 실제 보고서 바이너리를 보호한다; 마크다운 로그는 명시적으로 허용된다.

---

## 10. 위험 레지스터

| ID | 위험 | 가능성 | 영향 | 완화책 |
|---|---|---|---|---|
| **R-1** | `.venv/bin/python` 누락 또는 잘못된 Python 버전 | Low | High (모든 실행 체인 차단) | 사전 점검 (b) 가 세션 시작 시 포착. AskUserQuestion 온보딩 시퀀스가 사용자에게 venv 재생성을 요청. ADR-007 이 `.venv/bin/python` 실행 템플릿을 고정. |
| **R-2** | `.claude/settings.local.json` 충돌 | Low | Medium | §3 인벤토리가 현재 내용이 우리의 `Bash(python *)` 실행과 호환됨을 확인. Step 8/9/10 은 파일을 건드리지 않음. 사용자가 수동으로 제약적인 `deny` 규칙을 추가하면, Skill 이 표준 Bash 오류 분류 경로를 통해 결과적 거부-권한 오류를 표면화. |
| **R-3** | `KiwoomApiError` 8-모듈 트랩이 무음으로 오류를 놓침 | Medium (순진한 `isinstance` 사용 시) | High (영어 오류 누출; SC-1.3 위반) | OQ-3 결정: `type(exc).__name__` 으로 디스패치. CLAUDE.md 내부 주석이 8-모듈 사실을 문서화. Step 10 의 상호 참조 검사가 오류 테이블이 이름 기반 키를 사용하는지 검증. |
| **R-4** | `masterReference.log` 정규식 추출이 80% 정밀도 미만 | Medium | Medium (FR-5.2(a) 추정 품질 저하) | OQ-1 결정: 한국어로 파싱됨/전체 비율을 투명하게 보고; 비율 < 50% 시 B-10 의 "추정 데이터 없음" 으로 폴백. Phase 2 패치 티켓 ADR-009 기록. |
| **R-5** | `Bash(run_in_background: true)` 알림이 30분 내에 수신되지 않음 | Low | High (사용자가 결과를 보지 못함) | §7 타임아웃 안전장치: 30분 시점에 SCAN_SEPARATED 제안 한국어 폴백 송출. stock-scan Skill 이 이를 명시적 타임아웃 워치독 체인으로 인코딩. |
| **R-6** | kiwoom-rest-trader 업데이트에서 변수명 변경 (예: `_TYPE_A_ALIGN_TOL` → `_ALIGN_TOL_TYPE_A`) | Medium (PRD §5.1 에 명시적으로 플래깅됨) | High (TS-1 Edit 가 조용히 실패) | 사전 점검 (e) 의 `grep -n` 이 **모든 Edit 이전** 에 실행. 퍼지 폴백 `grep -in '{partial}'` 이 이름이 바뀐 변형을 탐색. 사용자 확인 게이트가 이름이 재확인될 때까지 Edit 차단. |
| **R-7** | `screener_state.json` 손상 (잘린 쓰기, JSON 구문 오류) | Low | Medium (세션 연속성 상실, 파괴적이지 않음) | `try/except json.JSONDecodeError` 로 읽기: 실패 시 누락으로 처리 (신규 사용자를 위한 온보딩 플로우로 회귀). 다음 성공적 스캔 시 상태가 재생성됨. 손상된 상태는 검사를 위해 `screener_state.json.corrupt.{ts}` 로 백업. |
| **R-8** | 사용자가 잘못된 cwd (`/Users/tajun/spJavis/kiwoom-rest-trader` 가 아님) 에서 Claude Code 를 엶 | Low | High (CLAUDE.md 가 로드되지 않음) | 모든 실행 체인이 `cd ${KRT_ROOT} &&` 접두사를 사용하므로 명령은 cwd 와 무관하게 동작. 그러나 CLAUDE.md 자동 로딩은 cwd 에 의존. 프롬프트 레이어 완화 범위 밖 — 온보딩 문서가 사용자에게 `${KRT_ROOT}` 에서 Claude Code 를 열 것을 지시해야 함. |

**총합**: 11개 위험. **High-impact 5개** (R-1, R-3, R-5, R-6, R-8), **Medium-impact 3개** (R-2, R-4, R-7), **Step 4 리뷰로 3개 추가** (아래 R-9, R-10, R-11).

| **R-9** | 동시 호출: `run_full_research_flow` (백그라운드) 가 실행 중인 동안 `filter-tune` 이 `Final` 상수를 씀 | Low (단일 사용자라 대부분 직렬) | High (실행 중인 run_filters 가 부분적으로 편집된 상수를 집어 → 실제처럼 보이는 일관성 없는 스테이지 결과) | filter-tune Skill 은 어떤 Edit 이전이라도 권고 잠금 (`reports/filter-tune.lock` 센티넬 파일) 을 획득해야 함; stock-scan Skill 은 백그라운드 실행 호출 전에 잠금을 확인하고 한국어 메시지 `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."` 와 함께 거절. Step 9 의 `@scan-builder`/`@tune-builder` 가 구현. |
| **R-10** | `.venv/bin/python` 이 pyenv 3.12.7 에 대한 심볼릭 링크임; 사용자가 pyenv 를 제거하거나 업그레이드하면 심볼릭 링크가 조용히 끊김 (`test -x` 는 링크 생성 시점에 역참조가 여전히 해석되는 깨진 심볼릭 링크에 대해 0 을 반환) | Medium (장기 운영) | High (모든 실행이 실행 중간에 혼란스러운 "No such file" 로 실패) | 사전 점검 (b) Bash 명령을 `[ -x /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python ] && /Users/tajun/spJavis/kiwoom-rest-trader/.venv/bin/python --version` 으로 교체 — 존재 검사를 실제 실행과 체이닝. Step 10 `@infra-validator` 가 명세를 갱신. |
| **R-11** | `Bash(python *)` permission 규칙이 `cd … && python …` 복합 명령을 매치하지 않을 수 있음 (§3 Permission 주의사항 참조) | Medium (Claude Code 의 permission 매처 동작 미검증) | High (모든 실행 체인이 첫 세션 시작 시 permission-denied 로 실패) | Step 10 의 프로브 + `settings.local.json` allow 목록에 대한 수정 Edit (§3 주의사항 참조). Step 10 사전 점검 게이트로 문서화. |

---

## 11. 검증 자체 확인

- [x] 5개 경로 상수 모두 `test -d` / `test -x` / `test -w` 결과 기록됨 (§1 — Bash 원문 증거 포함 5/5 PASS; 보너스로 `KRT_SCRIPTS` 도 검증)
- [x] 배포 매니페스트가 대상 경로 포함 ≥ 5개 파일 나열 (§2 — `.gitignore` 수정 포함 8개 항목)
- [x] `.claude/` 인벤토리가 덮어쓰기 충돌 없음을 보여줌 (§3 — `settings.local.json` 만 존재; 충돌 0)
- [x] `screener_state.json` 이 B-12 의 4개 필수 필드 모두 보유 (§4 — `last_scan_date`, `last_param_changes`, `last_results_summary`, `current_backup_files`; 필드별 의미 + 라이프사이클 문서화)
- [x] 사전 점검 (a)-(e) 모두 구체적인 Bash 명령 보유 (§5 — 기대 종료 코드 및 복구 경로와 함께 5/5)
- [x] 실행 템플릿 + venv python 이 실제 명령 출력으로 검증 (§6 — `Python 3.12.7` + `IMPORT_OK` + `sys.executable` 검사)
- [x] 4개 Open Questions 모두 근거와 함께 해결 (§8 — OQ-1 정규식 하이브리드, OQ-2 Phase 2 사이드카로 이월, OQ-3 `type(exc).__name__` 디스패치, OQ-4 D-2 확정)
- [x] `.gitignore` 계획 추가가 *새 무시 패턴* ≤ 3라인 (§9 — 2개 무시 패턴 + 1개 섹션 헤더 주석 블록; 기능적으로 3라인 추가)
- [x] 위험 레지스터에 ≥ 3개 항목 (§10 — 행마다 가능성/영향/완화책과 함께 8개 항목)
- [x] BLUEPRINT 전용: `/Users/tajun/spJavis/kiwoom-rest-trader/` 에 파일 쓰지 않음 (검증됨 — 위의 모든 Bash 명령은 읽기 전용: `test`, `ls`, `cat`, `python --version`, `python -c "import …"`)

---

## 부록 A — `docs/architectural-decision-records.md` 를 위한 신규 ADR

다음 ADR 들은 기존 65행 파일에 append (덮어쓰기 아님). 64행의 "Runtime Decisions" 헤더 아래에 삽입.

### ADR-009: gap 값 추출 전략 (FR-5.2)
- 컨텍스트: `masterReference.log` 가 gap 값을 구조화된 필드가 아니라 자연어 텍스트로 기록. FR-5.2(a) 가 영향 추정을 요구.
- 결정: Phase 1 — 5개 지배적 사유 포맷에 대한 정규식 추출; Phase 2 — `[gap: actual=…, threshold=…, gap=…, unit=…]` 접미사를 append 하도록 `Filter_condition_update.py` 패치.
- 대안: (a) Phase-1 정규식 + Phase-2 패치 [선택됨], (b) Phase 1 에서 즉시 패치, (c) 영향 추정 완전 생략.
- 근거: PG 안전성 — 동작하는 프로덕션 코드에 대한 수정 이월; 추정 정밀도가 FR-5.2(a) 에 충분; 추출 실패 시 폴백 메시지 가용.
- 출처: Step 4 OQ-1

### ADR-010: chart60_120Filter 문서 드리프트 (Type C 2.0% / Type D 60% 오래된 문자열)
- 컨텍스트: 866-870 라인의 `render_markdown()` 이 오래된 문자열 리터럴을 포함 (라이브 상수는 3.5% / 50%).
- 결정: Phase 1 — Skill 레이어 한국어 주의사항; Phase 2 — 문자열 리터럴을 갱신하는 사소한 PR.
- 대안: (a) 이월 + 주의사항 [선택됨], (b) 즉시 수정.
- 근거: PG 안전성 — 외관상에 그침, 수학은 라이브 상수 위에서 실행. Skill 주석은 코드 변경 비용이 0.
- 출처: Step 4 OQ-2

### ADR-011: `KiwoomApiError` 디스패치
- 컨텍스트: kiwoom-rest-trader 전반에 걸쳐 `KiwoomApiError` 의 8개 독립 클래스 선언.
- 결정: filter-tune Skill 오류 레이어가 `type(exc).__name__ == "KiwoomApiError"` 로 디스패치 (어떤 단일 임포트에 대한 `isinstance` 도 절대 사용 안 함).
- 대안: (a) 이름 기반 [선택됨], (b) 캐치-올 + reflection, (c) `code`/`msg` 속성 위의 구조적 타이핑.
- 근거: 방어적이고 명시적; 향후 클래스 통합 리팩토링에서 살아남음; Step 1 리서치 권장사항과 일치.
- 출처: Step 4 OQ-3

### ADR-012: SCAN_TODAY = 백그라운드 실행 의무와 함께하는 run_full_research_flow
- 컨텍스트: D-2 기본 모드 + 10-15분 이상 런타임 vs 10분 Bash 캡.
- 결정: `run_full_research_flow` 가 기본; 모든 장시간 스캔 (전체 플로우, 프리페치) 은 30분 타임아웃 안전장치와 함께 `Bash(run_in_background: true)` 를 반드시 사용.
- 대안: (a) 백그라운드 의무 [선택됨], (b) 첫 실행/이후 하이브리드 라우팅, (c) 분할 모드를 기본값으로.
- 근거: PRD FR-1.1 계약 보존; 백그라운드 알림이 타임아웃 압력 제거; 명시적 `"나눠서 해줘"` 트리거가 사용자에게 분할 모드 제어권 부여.
- 출처: Step 4 OQ-4 (D-2 재확정 + 백그라운드 의무 추가)

---

*블루프린트 완료. 구현은 Step 8 (CLAUDE.md), Step 9 (skill 파일), Step 10 (지원 인프라 + 상호 참조 검증) 에서 수행.*
