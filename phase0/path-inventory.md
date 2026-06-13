# Phase 0 — 과업 0-3: 절대경로(`/Users/tajun`) 전수 인벤토리

- 작성: Phase 0 워커 (2026-06-13)
- 대상 repo:
  1. `/Users/tajun/spJavis/kiwoom-rest-trader` (이하 **KRT**)
  2. `/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector` (이하 **AW**)
- 패턴: `/Users/tajun` (대소문자 구분, 고정 문자열)
- 제외: `.git`, `.venv`, `node_modules`, `logs`(KRT), `reports` 데이터 본문(KRT), `*.zip`/`*.tgz` 아카이브 본문, `prompt-runner/logs`(AW), `.claude/context-snapshots`(AW). 단 제외 영역도 **집계 수치는 별도 기록**(§5).
- 포함 강제 확인: `.claude/settings*.json` · `SKILL.md` · `.claude/commands/` · `.claude/hooks/` 스크립트 — 전부 grep 수행 완료(§3.4, §4.2).

## 0. 방법론 주의 (검증 과정에서 발견된 함정)

이 환경의 셸 `grep`은 **ugrep 래퍼 + `--ignore-files`**(gitignore 존중)로 alias되어 있어, 최초 실행에서 gitignore된 파일(KRT의 `CLAUDE.md.bak.*`, `reports/*.md`, `logs/*`; AW의 `prompt-runner/logs`, `context-snapshots` 등)이 **무음 누락**되었다. 본 인벤토리는 `command grep`(시스템 grep 직접 호출, `-rn -I`)으로 재실행해 확정했다. **후속 과업에서도 전수 스캔 시 `command grep` 사용 필수.**

검증 명령(재현용):

```bash
cd <repo> && command grep -rn "/Users/tajun" . \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules \
  --exclude='*.zip' -I
```

## 1. 총괄 수치 (전부 실측, `command grep -c` 합산)

| 구분 | KRT | AW |
|---|---|---|
| repo 전체 텍스트 히트(기본 제외만 적용) | **256** | **5,878** |
| 제외 영역(로그/스냅샷) 히트 | 240 (`logs/`) + 3 (`reports/`) | 4,395 (`prompt-runner/logs/`) + 1,191 (`.claude/context-snapshots/`) |
| **인벤토리 대상(치환 검토) 히트** | **13** (7파일) | **86** (19파일) |
| 인벤토리 대상 중 로그성(치환 불필요) | 3 (bak 3건) | 206 (outputs 192 + bak/snap 6 + 기타 8) |

검산: AW 5,878 − 4,395 − 1,191 = 292 = 86(치환 검토) + 206(로그성). KRT 256 = 13 + 240 + 3.

## 2. 알려진 3건 대조 결과

| 사전 정보 | 실측 결과 | 판정 |
|---|---|---|
| KRT `CLAUDE.md` Path Constants | `CLAUDE.md:7` — `KRT_ROOT = /Users/tajun/spJavis/kiwoom-rest-trader` | 확인 (1건, 라인 7) |
| AW `prompt/.claude/codegen/infra_schema.py:15-16` | 실제 히트는 **16-17행** (15행은 주석 `# === Path Constants ===`) — `:16 KRT_ROOT`, `:17 AW_ROOT` | **라인 정정** (15-16 → 16-17) |
| KRT `scripts/_measure_ref.py:4` | `:4` — `REPORTS = Path("/Users/tajun/spJavis/kiwoom-rest-trader/reports")` | 확인 |

## 3. KRT (kiwoom-rest-trader) 전수 목록

### 3.1 [코드 상수] — 치환 필요

| 파일:라인 | 내용 요지 | 치환 필요 | 권장 치환 |
|---|---|---|---|
| `scripts/_measure_ref.py:4` | `REPORTS = Path("/Users/tajun/spJavis/kiwoom-rest-trader/reports")` | **필요** | `Path(__file__).resolve().parents[1] / "reports"` 또는 신설 `ops/paths.py` SOT의 `REPORTS_DIR` import |

KRT의 `src/`, `tests/`, `analyses/`, `data/`, `backupMasterCompanys/`에는 히트 0 — **하드코딩 코드 상수는 이 1건이 전부**.

### 3.2 [스킬/문서] — 치환 필요

| 파일:라인 | 내용 요지 | 치환 필요 | 권장 치환 |
|---|---|---|---|
| `CLAUDE.md:7` | Path Constants 선언부 `KRT_ROOT = /Users/tajun/spJavis/kiwoom-rest-trader` | **필요(단일 정의점)** | 이주 시 이 1곳만 새 경로로 갱신 — 나머지 문서는 `${KRT_ROOT}` 참조로 통일 |
| `.claude/skills/stock-scan/references/pre-flight-checks.md:31` | `test -d /Users/tajun/spJavis/kiwoom-rest-trader` | 필요 | `test -d ${KRT_ROOT}` |
| `〃:49` | `.venv/bin/python` 존재+버전 probe (리터럴 2회) | 필요 | `${KRT_ROOT}/.venv/bin/python` |
| `〃:53` | settings.local.json allow 패턴 예시 `"Bash(cd /Users/tajun/... && *)"` | 필요 | `"Bash(cd ${KRT_ROOT} && *)"` 표기 + 실제값은 CLAUDE.md 참조 안내 |
| `〃:68` | `test -w .../reports` | 필요 | `test -w ${KRT_ROOT}/reports` |
| `〃:87` | python3 인라인 — prefetchManifest.json 경로 리터럴 | 필요 | `${KRT_ROOT}/reports/{YYYYMMDD}/prefetchManifest.json` |
| `〃:109` | `grep -n ... /Users/tajun/.../{file_path}` | 필요 | `${KRT_ROOT}/{file_path}` |
| `〃:121` | `test -d .../reports/filter-tune.lock` | 필요 | `${KRT_ROOT}/reports/filter-tune.lock` |
| `docs/user_command_manual.md:4` | "모든 명령은 프로젝트 루트(`/Users/tajun/...`)에서" | 필요 | `${KRT_ROOT}` 표기로 교체 |

참고: `.claude/skills/stock-scan/SKILL.md`, `.claude/skills/filter-tune/**`(SKILL.md·references·scripts 전체)는 **히트 0** (확인).

### 3.3 [로그성(치환 불필요)]

| 파일(:라인) | 성격 | 비고 |
|---|---|---|
| `CLAUDE.md.bak.20260531_180735:7` / `.bak.20260531_183746:7` / `.bak.20260531_193809:7` | CLAUDE.md 백업 3종 (각 1히트, 동일 라인 7) | 치환 불필요 — 이주 시 **삭제 후보** |
| `logs/research_flow_20260510_184508.log` | 실행 로그, **240히트** | 치환 불필요 (제외 영역, 집계만) |
| `reports/TUNING_RESUME_20260605.md:45` | 리포트 본문 내 `KRT=...` 명령 스니펫 | 치환 불필요 (이력 기록) |
| `reports/masterReference_전체_현재조건_분석_20260514_20260601.md:214` | `cd /Users/tajun/...` 스니펫 | 치환 불필요 (이력 기록) |
| `reports/masterReference_run_filters_튜닝_시뮬레이션_20260603.md:106` | `KRT=...` 스니펫 | 치환 불필요 (이력 기록) |
| `.claude/skills.bak.20260531_210355.tgz` | 스킬 백업 아카이브 — 내부 텍스트에 **7히트**(pre-flight-checks.md 사본, `tar -xOzf`로 확인) | 치환 불필요 — 이주 시 삭제 후보 |

### 3.4 [설정/훅] — 히트 0 확인

- `.claude/settings.local.json` — 히트 **0** (grep 수행, 무매치).
- KRT에는 `.claude/hooks/`, `.claude/commands/` 디렉토리 없음 (`.claude/` 구성: `settings.local.json`, `skills/`, `skills.bak...tgz` — ls로 확인).

## 4. AW (AgenticWorkflow-main-stock-filtering-collector) 전수 목록

### 4.1 [코드 상수] — 치환 필요

| 파일:라인 | 내용 요지 | 치환 필요 | 권장 치환 |
|---|---|---|---|
| `prompt/.claude/codegen/infra_schema.py:16` | `KRT_ROOT = "/Users/tajun/spJavis/kiwoom-rest-trader"` | **필요** | `os.environ.get("KRT_ROOT", <상대 추론>)` — conftest.py:9 패턴과 통일, 또는 ops/paths 단일 SOT |
| `prompt/.claude/codegen/infra_schema.py:17` | `AW_ROOT = "/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector"` | **필요** | `Path(__file__).resolve().parents[2]` (repo 자기참조) + env override |
| `prompt/.claude/tests/conftest.py:9` | `KRT_ROOT = Path(os.environ.get("KRT_ROOT", "/Users/tajun/..."))` | 필요(기본값만) | env 주입 구조 **이미 존재** — 하드코딩 fallback만 상대경로/에러로 교체 |
| `prompt/.claude/tests/conftest.py:10` | `AW_ROOT = Path(os.environ.get("AW_ROOT", "/Users/tajun/..."))` | 필요(기본값만) | 동일 |

### 4.2 [설정/훅]

| 파일:라인 | 내용 요지 | 치환 필요 | 권장 치환 |
|---|---|---|---|
| `prompt/.claude/state.yaml:31` | `step-8-claude-md: "/Users/tajun/.../CLAUDE.md"` | **필요(이주 시)** | 이주 마이그레이션 스크립트로 일괄 치환, 또는 `${KRT_ROOT}` 상대화 후 reader 측 해석 |
| `prompt/.claude/state.yaml:32` | `step-9-stock-scan-skill: ".../skills/stock-scan/"` | 필요(이주 시) | 〃 |
| `prompt/.claude/state.yaml:33` | `step-9-filter-tune-skill: ".../skills/filter-tune/"` | 필요(이주 시) | 〃 |
| `.claude/settings.json` | 히트 **0** (확인) | — | — |
| `.claude/hooks/scripts/*.py` (훅 스크립트 전체) | 텍스트 히트 **0** (확인 — `__pycache__/*.pyc` 바이너리 매치만 존재) | 불필요 | `.pyc`는 재컴파일 시 자동 갱신되는 재생성물 — 이주 시 `__pycache__` 삭제로 충분 |

### 4.3 [스킬/문서] — 치환 필요(◆) / 조건부(◇: 빌드 기록 성격, 재실행 계획 있을 때만)

| 파일:라인 | 히트수 | 내용 요지 | 판정 |
|---|---|---|---|
| `.claude/agents/param-extractor.md:14,15` | 2 | KRT_FILTERS 등 경로 상수 주입 | ◆ `${KRT_ROOT}` 참조화 |
| `.claude/agents/pipeline-analyzer.md:14,15,16` | 3 | KRT_SCRIPTS/REPORTS/FILTERS | ◆ |
| `.claude/agents/error-analyzer.md:14` | 1 | Search paths 2개(1라인) | ◆ |
| `.claude/agents/architect.md:16,36` | 2 | KRT_ROOT + `ls -la` 지시 | ◆ |
| `.claude/agents/claude-md-builder.md:19,36,37` | 3 | Deploy 대상 + 인벤토리 지시 | ◆ |
| `.claude/agents/scan-builder.md:18,22,34` | 3 | cross-ref + deploy 경로 | ◆ |
| `.claude/agents/tune-builder.md:18,22,34` | 3 | 〃 | ◆ |
| `.claude/agents/infra-validator.md:16,17,18` | 3 | 배포 검증 대상 경로 | ◆ |
| `.claude/agents/smoke-tester.md:15,16,17` | 3 | 배포 검증 대상 경로 | ◆ |
| `.claude/commands/accept-system.md:7,8,9` | 3 | 휴먼 게이트 — 배포 산출물 경로 | ◆ |
| `AGENTS.md:1281` | 1 | 서사 본문 — 자식 repo 경로 언급 | ◆ (문서 갱신) |
| `docs/integrated-user-command-manual.md:199,200,642,643,678,687` | 6 | 부모/자식 repo 경로표 + 실행 명령 + Path Constants | ◆ (678·687이 정의점 — 이 2곳을 SOT로) |
| `docs/architectural-decision-records.md:10` | 1 | Decision: 배포 위치 | ◆ |
| `prompt/workflow.md:7,24,25,26,27,28,29,30,47,96,337,347,358,359,386,401,499` | 17 | 빌드 스펙 — Deliverables 표·KRT_ROOT·검증 명령 | ◇ (재실행 시 ◆; 순수 비행기록이면 보존) |
| `prompt/workflow-coding.md:17,18,19,25,26,398,399,435,436,437,473,512,696,713,714,745,749,761,1189,1190,1684,1973,1974` | 23 | 빌드 코딩 스펙 — 사전 점검·에이전트 컨텍스트·코드 발췌 | ◇ |
| `prompt/workflow-idea/workflow-idea.md:172,181` | 2 | KRT_ROOT 단일 변수 관리 아이디어(원조 발상) | ◇ |
| `prompt/prd.md:459,470,474` | 3 | PRD — 프로젝트 루트·실행 전제·명령 | ◇ |

소계: ◆ 31히트 + ◇ 45히트 + 코드 상수 4 + state.yaml 3 + (4.4의 인벤토리 대상 로그성 제외) = **86히트** (§1과 일치: agents 23 + commands 3 + AGENTS 1 + docs 7 + workflow류 45 + py 4 + yaml 3 = 86).

참고: `.claude/skills/`(doctoral-writing·workflow-executor·workflow-generator — SKILL.md 포함) 히트 **0** (확인). 루트 `CLAUDE.md`·`GEMINI.md`·`soul.md`·`tests/` 히트 **0**.

### 4.4 [로그성(치환 불필요)]

| 파일(:라인) | 히트수 | 성격 |
|---|---|---|
| `prompt/.claude/state.yaml.bak:27,28,29` | 3 | SOT 백업 — 삭제 후보 |
| `prompt/.claude/state.yaml.testsnap-1780187139:31,32,33` | 3 | 테스트 스냅샷 — 삭제 후보 |
| `prompt/outputs/step-*.md` (en+ko 20파일) | **192** | 빌드 비행기록 산출물 (step-4-architecture 40×2, step-10-validation 21×2, step-1-pipeline 15×2 등) — 이력 보존, 치환 불필요 |
| `pacs-logs/step-11-translation-pacs.md:18` | 1 | pACS 기록 |
| `prompt-runner/execution.log:1,21,25,38,610,614,616` | 7 | 러너 실행 로그 |
| `prompt-runner/logs/**` (stream.jsonl·report.md) | **4,395** | 제외 영역 — 집계만 |
| `.claude/context-snapshots/**` | **1,191** | 제외 영역 — 집계만 |
| `**/__pycache__/*.pyc` (hooks 29개·codegen 5개·tests 12개 바이너리 매치) | n/a | 컴파일 산출물 — `__pycache__` 삭제로 해결, 치환 불필요 |

## 5. 권장 치환 전략 (이주 시)

1. **코드(3파일 5라인)**: 단일 paths SOT로 수렴.
   - KRT: `scripts/_paths.py`(신설) — `PROJECT_ROOT = Path(__file__).resolve().parents[1]`; `_measure_ref.py:4`가 import.
   - AW: `infra_schema.py:16-17`을 자기참조 상대경로 + `os.environ` override로 교체(이미 `conftest.py:9-10`에 env 패턴 존재 — 이것을 표준으로 채택하고 fallback만 제거).
2. **문서/스킬/에이전트(리터럴 ~40라인)**: 리터럴 → `${KRT_ROOT}` / `${AW_ROOT}` 표기 통일. 실제 값 정의는 repo당 1곳만 유지 — KRT `CLAUDE.md:7`, AW `docs/integrated-user-command-manual.md:678,687` (또는 양쪽 모두 신설 `ops/paths` 문서 1곳).
3. **state.yaml(SOT)**: 손편집 금지(validate_state_yaml.py 차단 훅 존재) — 이주 마이그레이션 스크립트로 3개 키 일괄 치환.
4. **로그성 전부**: 치환하지 않음. `*.bak`·`testsnap`·`skills.bak...tgz`·`__pycache__`는 이주 시 삭제 후보.
5. **prompt/ 비행기록(◇ 45히트)**: AGENTS.md:1281이 명시하듯 "공장이자 비행기록장치" — 재실행 계획이 확정될 때만 치환, 아니면 이력 그대로 보존.

## 6. 이슈

- **I-1 (라인 정정)**: 알려진 건 `infra_schema.py:15-16`은 실측 **16-17** — 후속 과업 참조 시 주의.
- **I-2 (도구 함정)**: 셸 `grep` alias(ugrep `--ignore-files`)가 gitignore 파일을 무음 누락 — 전수 스캔은 `command grep` 강제.
- **I-3 (확인 못함)**: `*.zip`/`*.tgz` 중 KRT `skills.bak.tgz`만 내부 검사함(7히트). AW에 zip 파일 존재 여부는 미탐색(발견된 아카이브 없음 — `command grep -rln` 출력에 미등장). `.pyc` 바이너리 내부의 경로는 매치 사실만 기록, 라인 단위 미분해(바이너리).
