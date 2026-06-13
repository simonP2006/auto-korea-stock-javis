# 과업 0-8 — .claude 구역 격리 설계서

- 작성일: 2026-06-13 (Phase 0 워커)
- 대상: `kiwoom-rest-trader/.claude` (→ 모노레포 `engine/.claude`) · `AgenticWorkflow-main-stock-filtering-collector/.claude` (→ 모노레포 `factory/.claude`)
- 승인된 설계 원칙(BUILD_PLAN.md:33): 모노레포 루트 `.claude`는 최소(라우팅 CLAUDE.md + 보조 설정만). engine/factory `.claude`는 각자 잔류. **factory의 차단형 훅(exit 2)은 루트로 승격 금지** — 일일 스캔(80분~6h)에 레이턴시·오탐 간섭 방지.
- 검증 방법: 본 문서의 모든 주장은 `파일경로:라인` 근거를 동반한다. 직접 확인 불가 항목은 "확인 못함"으로 명시하고 Phase 1 실측 절차를 제시한다.

---

## ① 두 .claude 트리 전체 인벤토리

### 1.1 engine 측 — `/Users/tajun/spJavis/kiwoom-rest-trader/.claude`

총 22파일 (git 추적 17건 — `git ls-files .claude` 실측 17, pyc 3건은 `.gitignore:7 __pycache__/`로, tgz 1건은 `.gitignore:33 *.bak.*`로 제외 — `git check-ignore -v` 실측).

| 항목 | 경로 | 내용 | git |
|---|---|---|---|
| 설정 | `.claude/settings.local.json` | `permissions.allow` 1건: `"Bash(python *)"` (settings.local.json:2-6). **hooks 없음, deny 없음, settings.json(공유) 없음** | 추적됨(통상 local은 미추적인데 이 repo는 추적 — 이주 시 그대로 따라옴) |
| 스킬 1 | `.claude/skills/filter-tune/` | `SKILL.md` (frontmatter: name=filter-tune, model=opus, tools 7종, maxTurns=40 — SKILL.md:1-7) + references 6 (parameter-catalog, range-map, shared-constants, theory-guide, tuning-sequence, unit-conversion) + scripts 3 (param_ast.py, unit_conversion.py, validate_param_values.py) | 추적 10건 |
| 스킬 2 | `.claude/skills/stock-scan/` | `SKILL.md` (name=stock-scan, model=opus, maxTurns=80 — SKILL.md:1-7) + references 5 (background-execution, disclaimer, execution-chains, output-templates, pre-flight-checks) | 추적 6건 |
| 런타임 잔재 | `.claude/skills/filter-tune/scripts/__pycache__/` 3 pyc | 재생성물 | 미추적 |
| 아카이브 | `.claude/skills.bak.20260531_210355.tgz` | 스킬 백업 tarball | 미추적(gitignore `*.bak.*`) |

**없는 것(실측)**: agents 0, commands 0, hooks 0, settings.json 0. 즉 engine 구역은 "스킬 2 + allow 1건"이 전부다.

### 1.2 factory 측 — `/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector/.claude`

git 추적 72건(`git ls-files .claude` 집계: hooks/scripts 29 + agents 16 + commands 10 + skills 15 + 최상위 2) + 미추적 런타임(context-snapshots ~30파일, pyc 29).

#### (a) settings.json — permissions.deny 19건 + 7이벤트 14훅

- `permissions.deny` 19건 (settings.json:3-23): Bash 15건(curl|sh, curl|bash, wget|sh, wget|bash, sudo, chmod 777, chmod -R 777, osascript, crontab -e, crontab -r, mkfs, dd if=, npm/yarn/pnpm publish) + Write 4건(~/.ssh/*, ~/.zshrc, ~/.bashrc, ~/.profile)
- hooks 7이벤트 14훅커맨드 (settings.json:25-177):

| 이벤트 | matcher | 스크립트 | 차단성 | 근거 |
|---|---|---|---|---|
| Stop | (전체) | context_guard.py --mode=stop → generate_context_summary.py | exit 2 전파 가능(이론상) | settings.json:26-36, context_guard.py:75-78 |
| PostToolUse | Edit\|Write\|Bash\|Task\|NotebookEdit\|TeamCreate\|SendMessage\|TaskCreate\|TaskUpdate | context_guard.py --mode=post-tool → update_work_log.py | 〃 | settings.json:38-47 |
| PostToolUse | **Bash\|Read** | output_secret_filter.py | **비차단(항상 exit 0)** | settings.json:49-57, output_secret_filter.py:6,524-525 |
| PostToolUse | Edit\|Write | security_sensitive_file_guard.py | 비차단(항상 exit 0) | settings.json:59-67, security_sensitive_file_guard.py:6,259-260 |
| PostToolUse | Write\|Edit | **validate_state_yaml.py** | **차단형 exit 2** (단 `prompt/.claude/state.yaml` suffix 매칭 시에만 — 그 외 파일은 즉시 exit 0) | settings.json:69-77, validate_state_yaml.py:5-6,17,22-26,73-75 |
| PostToolUse | Write | monitor_translation_output.py | 비차단(항상 exit 0) | settings.json:79-87, monitor_translation_output.py:6 |
| PreCompact | (전체) | context_guard.py --mode=pre-compact → save_context.py | 비차단 실질 | settings.json:89-99 |
| SessionStart | clear\|compact\|resume\|startup | context_guard.py --mode=restore → restore_context.py | 비차단 실질 | settings.json:100-111 |
| PreToolUse | **Bash** | **block_destructive_commands.py** | **차단형 exit 2** (curl\|sh, wget\|sh, dd, mkfs, git push -f/--force, git reset --hard, git checkout ., git clean -f, rm -rf / 등) | settings.json:112-122, block_destructive_commands.py:4-44 |
| PreToolUse | Edit\|Write | **block_test_file_edit.py** | **차단형 exit 2** (`.tdd-guard` 토글 파일 존재 시에만 발동) | settings.json:124-132, block_test_file_edit.py:8-9,175 |
| PreToolUse | Edit\|Write | predictive_debug_guard.py | 비차단(항상 exit 0) | settings.json:134-142, predictive_debug_guard.py:6,26 |
| SessionEnd | clear\|logout\|prompt_input_exit\|other | save_context.py --trigger sessionend | 비차단. **주의: `test -f` 가드 없음** | settings.json:144-154 (특히 :150) |
| Setup | init | setup_init.py | **차단형 exit 2 가능** (setup_init.py:152,529). `test -f` 가드 없음 | settings.json:155-165 |
| Setup | maintenance | setup_maintenance.py | 비차단. `test -f` 가드 없음 | settings.json:166-175 |

> 차단형(exit 2 가능) 집계: block_destructive_commands.py, block_test_file_edit.py, validate_state_yaml.py, setup_init.py + context_guard.py(전파 경로만 — 디스패치 대상 4종 save/restore/generate/update에서 exit 2 발생 코드는 grep 미검출). 나머지 전부 "항상 exit 0" 설계 명문화.
> 12/14 훅커맨드는 `if test -f ...; then ...; fi` 가드로 스크립트 부재 시 무음 통과. SessionEnd(:150)·Setup(:161,:171) 3건만 무가드 — settings.json을 스크립트 없이 다른 위치에 복사하면 이 3건은 에러를 낸다(루트 승격 금지의 부수 근거).

#### (b) agents 16

| 파일 | model | 비고 |
|---|---|---|
| architect, claude-md-builder, claude-md-designer, fact-checker, infra-validator, param-extractor, pipeline-analyzer, research-integrator, reviewer, scan-builder, scan-designer, smoke-tester, translator, tune-builder, tune-designer | opus | 빌드 전용 13 + 범용 3(translator/reviewer/fact-checker — AgenticWorkflow CLAUDE.md의 .claude/agents 절) |
| error-analyzer | sonnet | 유일한 비-opus |

**절대경로 내장 9건**(`grep -rln "/Users/tajun"` 실측): architect, claude-md-builder, error-analyzer, infra-validator, param-extractor, pipeline-analyzer, scan-builder, smoke-tester, tune-builder — 전부 빌드 타깃 `/Users/tajun/spJavis/kiwoom-rest-trader/...`를 가리킴 (예: pipeline-analyzer.md의 `KRT_FILTERS = /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter`, tune-builder.md의 `ls -la /Users/tajun/spJavis/kiwoom-rest-trader/.claude/skills/`).

#### (c) commands 10

accept-system, install, maintenance, resume-prompts, review-design, review-research, review-translation, run-prompts, setup-prompts, verify-prompts. frontmatter description 보유는 install·maintenance 2건뿐(실측). **절대경로 내장 1건**: accept-system.md (kiwoom-rest-trader 배포 경로 3곳).

#### (d) hooks/scripts 29 .py

런타임/라이브러리 26 (`_context_lib.py` 포함) + 테스트 3 (`_test_block_destructive.py`, `_test_secret_filter.py`, `_test_sensitive_file_guard.py`). pyc 29건 별도(미추적 재생성물). **절대경로 내장 0건** — 전부 `$CLAUDE_PROJECT_DIR` 또는 상대경로 기반 (settings.json:31 등 14훅 전부; validate_state_yaml.py:17은 `os.path.join("prompt",".claude","state.yaml")` suffix 매칭이라 repo 이동에 불변).

#### (e) skills 3 — ★과업 지시문(agents 16·commands 10·hooks 29)에 누락돼 있던 발견사항

| 스킬 | frontmatter | 절대경로 |
|---|---|---|
| workflow-generator | name/description 정상 (SKILL.md:1-4) + references 6 | 0건 |
| workflow-executor | **YAML frontmatter 없음** — H1 제목만 (SKILL.md:1 `# Workflow Executor — Stock Filter Orchestration Build`) + references 2 | 0건 |
| doctoral-writing | name/description 정상 (SKILL.md:1-4) + references 5 | 0건 |

#### (f) 런타임·기타

- `.claude/context-snapshots/` — gitignored(AgenticWorkflow `.gitignore:7`). 스냅샷 md ~12 + sessions/ 19 + knowledge-index.jsonl(절대경로 67건 내장 — grep -c 실측) + work_log.jsonl + risk-scores.json + security.log 등
- `.claude/scheduled_tasks.lock` — **git 추적됨**(lock 파일인데 추적 — 조정 후보)
- 별도 중첩: `prompt/.claude/` (state.yaml SOT + codegen/ + tests/ + step-registry.yaml) — skills/hooks가 아닌 워크플로우 상태 디렉토리. BUILD_PLAN.md:31에 따라 **읽기 전용 동결** 대상

---

## ② 충돌 매트릭스

### 2.1 스킬명 충돌

| | engine: filter-tune | engine: stock-scan | factory: workflow-generator | factory: workflow-executor | factory: doctoral-writing |
|---|---|---|---|---|---|
| 상호 이름 충돌 | — | 없음 | 없음 | 없음 | 없음 |
| 사용자/글로벌 스킬과 이름 충돌 | 없음 | 없음 | 없음 | 없음 | 없음 |

5개 스킬명 전부 유일(본 세션 스킬 레지스트리 실측 — 아래 §3.1 (a) 참조: 5개가 전부 동시 노출되었고 중복 이름 없음).

**실질 충돌은 이름이 아니라 "의도 공간"**: kiwoom CLAUDE.md '모드 경계' 절은 "Infrastructure Build(12단계)는 제품 모드가 아니며 어떤 분기로도 도달 불가"를 절대 규칙으로 못 박는데, 모노레포 루트에서 세션을 열면 workflow-executor("워크플로우 실행")가 engine 스킬과 **같은 세션에 동시 노출**된다(§3.1 (a) 실측). "워크플로우 시작하자" 같은 발화는 kiwoom Start Routing(사용 모드 진입)과 factory workflow-executor(빌드 구동, SKILL.md:6-8 Trigger "orchestrator session begins") 양쪽에 걸린다 — 루트 세션의 라우팅 오발 위험이 본 격리 설계의 1번 표적이다.

### 2.2 훅 이벤트 충돌

engine 훅 = 0건(settings.local.json:1-7에 hooks 키 자체 없음) → **현재 상태에서 이벤트 충돌은 0**. 충돌은 "factory 훅을 루트로 승격하는 순간"에만 발생하며, 그 경우 engine 일일 스캔이 받는 간섭은:

| factory 훅 | engine 스캔(80분~6h, 백그라운드 Bash + 다수 Read/Bash 후속 처리)에 미치는 간섭 |
|---|---|
| PreToolUse Bash: block_destructive_commands.py (exit 2) | 매 Bash 호출 선행 검사. 스크립트 스스로 오탐 한계를 명문화(block_destructive_commands.py:41-44 "문자열 리터럴 내 명령도 차단될 수 있음 — false positive 허용 설계"). 스캔 보고서 문구·로그 인용에 `git reset --hard` 류 문자열이 섞이면 스캔 체인이 중단된다 |
| PostToolUse Bash\|Read: output_secret_filter.py | 매 Bash·Read마다 python3 기동 + 25+ 정규식 전수 스캔(조기 종료 없음 — output_secret_filter.py:29). 실측 기동 하한 ~0.09s/회(`time python3 -c 'pass'` 0.088s, 본 머신) — 훅 3중첩(PreToolUse+context_guard+secret_filter) 시 Bash 1회당 ~0.3s+ 고정세. 수천 회 호출 스캔에서 분 단위 누적 + 키움 API 응답 본문이 토큰 패턴에 걸리면 세션 경고 소음 |
| PostToolUse Edit\|Write: validate_state_yaml.py (exit 2) | suffix `prompt/.claude/state.yaml` 외엔 즉시 exit 0(validate_state_yaml.py:22-26)이라 engine 오탐은 사실상 없음 — 단 호출 고정세는 동일 부담 |
| PreToolUse Edit\|Write: block_test_file_edit.py (exit 2) | `.tdd-guard` 토글 존재 시 engine tests/ 수정까지 차단(block_test_file_edit.py:8-9) — 루트에 토글이 생기면 구역 간 오염 |
| Stop/SessionEnd/PreCompact/SessionStart: context_guard 계열 | 루트 `$CLAUDE_PROJECT_DIR/.claude/context-snapshots`에 스냅샷을 쓰기 시작 — factory 전용 런타임이 루트를 오염 |

→ **승인 원칙(차단형 훅 루트 승격 금지) 재확인이 결론**. 추가로 비차단 훅도 호출 고정세·소음 때문에 루트 승격 비권장.

### 2.3 permissions 겹침

| | engine allow `Bash(python *)` (settings.local.json:4) | factory deny 19건 (settings.json:3-23) |
|---|---|---|
| 패턴 교집합 | **0건** — deny 목록에 python 패턴 없음, allow 목록에 deny 대상 없음 | — |
| 가정적 병합 시 | Claude Code 우선순위 deny>allow이지만 교집합이 없어 동작 변화 없음 | engine 스캔은 curl\|sh·sudo 등을 쓰지 않으므로(EXEC_PATTERN은 `.venv/bin/python -m ...` — kiwoom CLAUDE.md Execution Template) deny 19건이 스캔을 막지는 않음 |
| 이중 집행 중복 | — | deny 4건(curl\|sh, wget\|sh, mkfs, dd if=)이 block_destructive_commands.py(NETWORK_PATTERNS:66-79, SYSTEM_PATTERNS:84-96)와 **중복 방어** — factory 내부에선 의도된 심층방어이므로 유지, 루트 통합 사유로 오용 금지 |

### 2.4 CLAUDE.md 계층 중첩 (충돌면 추가)

모노레포에서는 한 세션에 최대 4겹이 주입된다: ~/.claude/CLAUDE.md(글로벌) + /Users/tajun/spJavis/CLAUDE.md(조상) + 모노레포 루트 CLAUDE.md(신설 라우터) + engine 또는 factory CLAUDE.md. 조상 CLAUDE.md가 세션 시작 시 자동 주입되는 것은 본 세션에서 실측(§3.1 (d)). engine CLAUDE.md(14 Intent 라우팅, ~300줄)와 factory CLAUDE.md(절대 기준·Autopilot, ~200줄)는 luckily 서로 다른 발화 공간을 다루지만, **루트 라우터 CLAUDE.md는 이 둘과 겹치지 않게 "구역 선택 규칙만" 담아야 한다**(BUILD_PLAN.md:29-30).

---

## ③ Claude Code 중첩 .claude 발견 동작 + 세션 오픈 위치별 로드 표

### 3.1 발견 동작 — 본 세션 실측 근거

본 세션(cwd=`/Users/tajun/spJavis/auto-korea-stock-javis`, 마스터 런치 루트는 `/Users/tajun/spJavis`로 추정)에서 직접 관측한 사실:

- **(a) 중첩 `.claude/skills`는 재귀 발견된다 — git repo 경계 무시(하위 방향).** 실측: 본 세션 스킬 목록에 `filter-tune`·`stock-scan`(kiwoom-rest-trader — cwd의 형제 디렉토리, 별도 git repo)과 `workflow-generator`·`workflow-executor`·`doctoral-writing`(AgenticWorkflow — 역시 형제·별도 repo)이 **모두 노출**됨. 기존 관측(메모리: nested .claude/skills discovery)과 일치.
- **(b) 중첩 `.claude/commands`는 발견되지 않는다.** 실측: factory의 10개 커맨드(/install, /maintenance, /accept-system 등) 중 어느 것도 본 세션에 노출되지 않음.
- **(c) 중첩 `.claude/settings.json`의 hooks는 적용되지 않는다.** 간접 실측: 본 세션에서 AgenticWorkflow 파일들에 다수의 Bash·Read를 수행했으나 output_secret_filter 등 훅 stderr 0건. (문서화된 동작 — 설정은 프로젝트 루트+사용자 레벨에서만 로드 — 과도 일치하나, 결정적 증명은 아니므로 Phase 1 실측 항목에 포함)
- **(d) CLAUDE.md는 이중 메커니즘**: 조상 디렉토리 CLAUDE.md는 세션 시작 시 주입(실측: spJavis/CLAUDE.md가 cwd 상위라서 시작 시 주입됨), 하위 디렉토리 CLAUDE.md는 **그 하위 파일을 처음 접근할 때 lazy 주입**(실측: 본 세션에서 두 repo 파일을 읽은 직후 두 CLAUDE.md 전문이 컨텍스트에 자동 주입됨).
- **(e) 중첩 `.claude/agents` 발견 여부 — 확인 못함.** 본 세션엔 Task(서브에이전트) 도구가 없어 실측 불가. commands와 동일하게 비발견으로 추정되나 추정임을 명시.
- **(f) git root 기반 프로젝트 판정 — 확인 못함.** 모노레포 하위 `engine/`에서 세션을 열 때 `$CLAUDE_PROJECT_DIR`이 engine/이 되는지, git root(모노레포 루트)로 승격되어 루트 settings.json이 로드되는지는 현 환경(두 repo가 아직 분리·모노레포 미구축)에서 실측 불가. **Phase 1 게이트 실측 절차**: `cd <monorepo>/engine && claude` → ① `/hooks` 출력에 루트 훅 표시 여부 ② `/permissions`에 루트 deny 표시 여부 ③ `echo $CLAUDE_PROJECT_DIR` (Bash 도구로) 3종 확인. 결과에 따라 §4의 "루트 settings.json 최소주의"가 더 엄격해져야 할 수 있음(루트 훅이 하위 세션에 상속된다면 루트 훅은 0건이어야 한다).

### 3.2 세션 오픈 디렉토리별 로드 표 (모노레포 구축 후)

| 로드 항목 | 루트에서 오픈 (`<monorepo>/`) | `engine/`에서 오픈 | `factory/`에서 오픈 |
|---|---|---|---|
| CLAUDE.md (시작 시) | 글로벌 + spJavis(조상) + **루트 라우터** | 글로벌 + spJavis + **루트(조상)** + engine | 글로벌 + spJavis + **루트(조상)** + factory |
| CLAUDE.md (lazy) | engine·factory CLAUDE.md — 해당 하위 파일 접근 시 주입 (실측 (d)) | factory CLAUDE.md — factory 파일 접근 시 (역방향 문은 사람 발화로만 — BUILD_PLAN.md:30) | engine CLAUDE.md — 빌드 타깃 파일 접근 시 자동 주입(불가피, 빌드 특성상 정상) |
| settings/permissions | 루트 .claude/settings.json만 (engine allow·factory deny **미적용**) | engine settings.local.json (allow `Bash(python *)`) ± 루트 settings(§3.1 (f) 미확정) | factory settings.json deny 19건 ± 루트 settings(〃) |
| hooks | **루트 훅만 — 설계상 0건 유지.** factory 7이벤트 훅 미적용 (실측 (c) 간접) | **0건** (engine에 훅 없음 — settings.local.json:1-7) ± (f) 미확정분 | factory 14훅 전부 — `$CLAUDE_PROJECT_DIR`=factory/라서 경로 그대로 동작 (settings.json:31 등) |
| skills | **5개 전부 노출** (engine 2 + factory 3 — 재귀 발견, 실측 (a)) + 글로벌 | engine 2개만 (filter-tune, stock-scan — factory는 형제라 비발견) + 글로벌 | factory 3개만 + 글로벌 |
| commands | 루트 .claude/commands만(설계상 0) — factory 10개 비노출 (실측 (b)) | 없음 | factory 10개 전부 |
| agents | 루트만(설계상 0) — factory 16개 비노출 추정 (확인 못함 (e)) | 없음 | factory 16개 전부 |

**표의 함의**:
1. **일일 운영 세션은 `engine/`에서 연다**(BUILD_PLAN.md:33 후단과 일치). 이때 노출 스킬이 정확히 2개로 줄어 §2.1의 의도 공간 충돌이 구조적으로 소멸하고, 훅 0건으로 스캔 레이턴시·오탐 면역.
2. **빌드 세션은 `factory/`에서 연다**. 14훅·16에이전트·10커맨드가 무수정으로 동작(전부 $CLAUDE_PROJECT_DIR 기반).
3. **루트 세션은 라우팅·횡단 관리 전용**. 스킬 5개가 모두 보이는 유일한 위치이므로, 루트 CLAUDE.md에 "빌드 스킬(workflow-executor/generator) 호출은 명시적 '공장 빌드 모드' 발화 시에만, 그 외 모든 사용 발화는 engine 구역" 라우팅 규칙을 명문화한다(BUILD_PLAN.md:29). 루트 .claude에는 settings.json을 두더라도 훅 0건·권한 보조 최소만.

---

## ④ 이주 목록 — 그대로 옮기는 것 vs 조정 필요한 것

전제: Phase 1-1은 `git filter-repo`로 이력 보존 이주(BUILD_PLAN.md:51). **git 미추적물(gitignored)은 filter-repo에 실리지 않으므로** 별도 결정이 필요하다(아래 C군).

### A. 그대로 이주 (수정 0건)

| 대상 | 근거 |
|---|---|
| engine `skills/filter-tune/` 전체 (SKILL.md + references 6 + scripts 3) | 절대경로 0건 (grep 실측 — engine 스킬 중 절대경로는 stock-scan 1파일뿐) |
| engine `skills/stock-scan/` 중 SKILL.md + references 4건 (background-execution, disclaimer, execution-chains, output-templates) | 절대경로 0건 (〃) |
| engine `settings.local.json` | 내용 무경로(`Bash(python *)` 1건). 위치만 `engine/.claude/`로 잔류 |
| factory `settings.json` | 절대경로 0 — 14훅 전부 `$CLAUDE_PROJECT_DIR` 기반 (settings.json:31,43,53,...) |
| factory `hooks/scripts/` 29 .py 전체 | 절대경로 0건 (grep 실측). validate_state_yaml.py:17의 suffix 매칭(`prompt/.claude/state.yaml`)도 위치 불변 |
| factory `agents/` 16 중 7건 (claude-md-designer, fact-checker, research-integrator, reviewer, scan-designer, translator, tune-designer) | 절대경로 0건 (grep -rln 실측의 여집합) |
| factory `commands/` 10 중 9건 (accept-system 제외 전부) | 절대경로 0건 (〃) |
| factory `skills/` 3 전체 (workflow-generator, workflow-executor, doctoral-writing) | 절대경로 0건 (grep 실측) |
| `prompt/.claude/` (state.yaml SOT 등) | **그대로 + 읽기 전용 동결** (BUILD_PLAN.md:31). suffix 매칭 훅과의 정합도 자동 유지 |

### B. 조정 필요 (이주 시 또는 이주 직후)

| 대상 | 조정 내용 | 근거 |
|---|---|---|
| engine `skills/stock-scan/references/pre-flight-checks.md` | `/Users/tajun/spJavis/kiwoom-rest-trader` 절대경로 5곳(라인 31, 49, 53, 68, 87) → 모노레포 `engine/` 경로로 치환. :53은 settings.local.json allow 안내 문구 속 경로라 특히 누락 주의 | grep -n 실측 |
| factory `agents/` 9건 (architect, claude-md-builder, error-analyzer, infra-validator, param-extractor, pipeline-analyzer, scan-builder, smoke-tester, tune-builder) + `commands/accept-system.md` | 빌드 타깃 경로 `/Users/tajun/spJavis/kiwoom-rest-trader/...` → `<monorepo>/engine/...` 치환. **단 factory 동결 원칙과의 관계**: BUILD_PLAN.md:31의 동결은 `prompt/`(비행기록)에 한정되고, agents/commands는 재사용 기계장치이므로 치환이 동결 위반이 아님. 권고 = 이주 커밋에서 일괄 치환(방치 시 차기 빌드 인스턴스가 stale 경로로 구 위치에 쓰기 시도하는 위험이 더 큼). 대안(보수) = 치환 보류 + factory CLAUDE.md에 "재가동 전 경로 치환 필수" 경고 1줄 — 어느 쪽이든 **결정 기록 필요** | grep -rln 실측 9+1건 |
| factory `.claude/scheduled_tasks.lock` | lock 파일이 git 추적 중(git ls-files 실측) — 이주 시 추적 제외(.gitignore 추가) 권고 | 추적 실측 |
| engine `kiwoom-rest-trader/CLAUDE.md`의 KRT_* 절대경로 상수 | 본 과업 범위 밖(.claude 외부)이나 stock-scan/filter-tune 스킬이 의존하는 연동 항목이므로 Phase 1 경로 치환 체크리스트에 동반 등재 | kiwoom CLAUDE.md Path Constants 절 |
| 모노레포 루트 `.claude/` (신설) | CLAUDE.md 라우터(구역 선택 규칙만, BUILD_PLAN.md:29-30) + settings.json은 두더라도 **hooks 0건** 고정. §3.1 (f) 실측에서 "루트 설정이 하위 세션에 상속"으로 판명되면 루트 permissions도 최소화 | BUILD_PLAN.md:33 |

### C. 이주 제외 / 별도 처분 (git 미추적 — filter-repo에 안 실림)

| 대상 | 처분 |
|---|---|
| pyc 32건 (engine 3 + factory 29) | 미이주 — 첫 실행 시 재생성 |
| engine `skills.bak.20260531_210355.tgz` | 미이주(gitignore `*.bak.*` — check-ignore 실측). 보존 원하면 모노레포 밖 아카이브로 수동 이동 — **결정 필요(기본: 폐기 가능, 내용물 17파일이 전부 git 이력에 있음)** |
| factory `context-snapshots/` (~30파일) | gitignored(.gitignore:7)라 git 이주 비포함. knowledge-index.jsonl에 구 절대경로 67건(grep -c 실측) — 옮겨도 포인터가 전부 stale. 권고 = **동결 아카이브로 수동 복사**(`factory/.claude/context-snapshots/`에 두면 factory 세션의 restore_context가 과거 인덱스를 읽을 수 있으나 stale 경로 경고 가능) 또는 구 repo와 함께 보존만. **주인님 결정 항목** — RLM 복원 연속성 vs 깨끗한 출발 |

---

## 부록 — 확인 못한 것 (날조 방지 명세)

1. **중첩 `.claude/agents` 비발견** — 추정(commands와 동일 계열)이며 실측 불가였음 (§3.1 (e)).
2. **모노레포 하위 디렉토리 세션의 루트 settings 상속 여부(git root 판정)** — 실측 불가, Phase 1 게이트에 3종 실측 절차 명시 (§3.1 (f)).
3. **중첩 settings.json hooks 비적용** — 간접 증거(훅 stderr 0건)만 확보, 결정적 증명 아님 (§3.1 (c)).
4. context_guard.py의 exit 2 전파(:78)가 실제 발생하는 입력 — 디스패치 대상 스크립트들에서 exit(2) 코드 미검출이므로 이론상 경로로만 기재.
5. 본 세션의 마스터 런치 루트가 `/Users/tajun/spJavis`라는 것 — 스킬 노출 패턴으로부터의 추정.

---
## [정정 추기 — 검증관 실측, 2026-06-13]
- engine .claude 파일 수: 22 → **21** (off-by-one).
- factory git 추적: 72 → **73** (skills 16 — workflow-generator/references/state.yaml.example 누락분).
- engine stock-scan pre-flight-checks.md 절대경로: 5곳 → **7곳** (109·121행 추가). 경로 치환 체크리스트는 path-inventory.md(7건)가 정확본.
