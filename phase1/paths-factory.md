# Phase 1 — 과업 1-2b: factory 구역 경로 치환 보고서

- 작성: Phase 1 워커 (2026-06-13)
- 기준 문서: `phase0/path-inventory.md` (AW 86히트/19파일), `phase0/claude-isolation-design.md` (§4-B)
- 새 경로 값: `ENGINE_ROOT = /Users/tajun/spJavis/auto-korea-stock-javis/engine`, `FACTORY_ROOT = /Users/tajun/spJavis/auto-korea-stock-javis/factory`
- 원칙 준수: **살아있는 설정·테스트·에이전트 지침만 치환** — 역사 기록(outputs·state.yaml·로그) 전부 보존. git commit/push 없음(작업트리 편집만 — `git status --short` 실측, HEAD `e6a1ef7` 불변).

## 1. 치환 실행 내역 (12파일 30라인)

### a) `factory/prompt/.claude/codegen/infra_schema.py` 16-17행 (2라인)

| 라인 | 전 | 후 |
|---|---|---|
| 16 | `KRT_ROOT = "/Users/tajun/spJavis/kiwoom-rest-trader"` | `KRT_ROOT = "/Users/tajun/spJavis/auto-korea-stock-javis/engine"` |
| 17 | `AW_ROOT = "/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector"` | `AW_ROOT = "/Users/tajun/spJavis/auto-korea-stock-javis/factory"` |

(인벤토리 I-1 라인 정정 반영 — 실측 16-17행이 맞음을 재확인.)

### b) `factory/prompt/.claude/tests/conftest.py` 9-10행 (2라인 — env override 기본값만)

| 라인 | 변경 |
|---|---|
| 9 | `os.environ.get("KRT_ROOT", ...)` 기본값 → ENGINE_ROOT 값 (env 주입 구조는 그대로) |
| 10 | `os.environ.get("AW_ROOT", ...)` 기본값 → FACTORY_ROOT 값 |

주의: 7-18행은 `[CODEGEN:START]` 블록(infra_schema.py에서 생성). (a)와 (b)를 동일 값으로 동시 치환했으므로 codegen 값-동등성 게이트 정합 유지 — §3.② 64 green이 증거.

### c) agents 9파일 + commands 1파일 (26라인 — 전부 구 kiwoom 경로 → ENGINE_ROOT; 구 AW 경로는 이 10파일에 0건이었음, 치환 전 grep 실측)

| 파일 | 치환 라인 | 인벤토리 대조 |
|---|---|---|
| `factory/.claude/agents/architect.md` | 16, 36 | 일치 (2) |
| `factory/.claude/agents/claude-md-builder.md` | 19, 36, 37 | 일치 (3) |
| `factory/.claude/agents/error-analyzer.md` | 14 (1라인 2경로) | 일치 (1라인) |
| `factory/.claude/agents/infra-validator.md` | 16, 17, 18 | 일치 (3) |
| `factory/.claude/agents/param-extractor.md` | 14, 15 | 일치 (2) |
| `factory/.claude/agents/pipeline-analyzer.md` | 14, 15, 16 | 일치 (3) |
| `factory/.claude/agents/scan-builder.md` | 18, 22, 34 | 일치 (3) |
| `factory/.claude/agents/smoke-tester.md` | 15, 16, 17 | 일치 (3) |
| `factory/.claude/agents/tune-builder.md` | 18, 22, 34 | 일치 (3) |
| `factory/.claude/commands/accept-system.md` | 7, 8, 9 | 일치 (3) |

치환 후 `command grep -rn "/Users/tajun" factory/.claude/agents/ factory/.claude/commands/` = 26라인 전부 새 ENGINE_ROOT 경로, 구경로 0건.

## 2. 보존 처리 (치환 금지 — 역사 기록)

| 대상 | 잔존 구경로 | 처리 |
|---|---|---|
| `factory/prompt/.claude/state.yaml` :31,32,33 | KRT-구 3건 | **역사 보존 — 동결 SOT.** 절대 경로가 남아 있으나 의도적으로 그대로 둠 (validate_state_yaml.py 차단 훅 대상이기도 함). 차기 빌드 재가동 시에만 마이그레이션 스크립트로 치환 (인벤토리 §5-3) |
| `factory/prompt/outputs/*` (en+ko) | KRT-구 186 + AW-구 2 | 보존 — 빌드 비행기록. (참고: "/Users/tajun" 전체 192 중 잔여 4건은 pyenv python 심볼릭링크 경로로 두 repo와 무관 — step-10-validation-report.md:51,264 ×2) |
| DECISION-LOG.md | **0건** (grep 실측) | 해당 없음 |
| pacs/verification 로그 | `pacs-logs/` 디렉토리가 모노레포 factory에 **부재**(ls 실측 — git 이주에 미포함된 것으로 보임) | 해당 없음 — 보존 대상 자체가 없음 |
| README 인용문 | 루트 md 중 구경로는 AGENTS.md:1281 1건뿐, README 히트 0 | §4 분류표에서 별도 분류 |

## 3. 검증 결과 (전부 실측)

### ① import 검증 — PASS

```
$ python3 -c "import sys; sys.path.insert(0,'.../factory/prompt/.claude/codegen'); import infra_schema; print(infra_schema.KRT_ROOT, infra_schema.AW_ROOT)"
/Users/tajun/spJavis/auto-korea-stock-javis/engine /Users/tajun/spJavis/auto-korea-stock-javis/factory
```

### ② pytest — 기대치와 정확히 일치

| 스위트 | 결과 | 기대 | 판정 |
|---|---|---|---|
| `factory/tests/` 단독 | **64 passed** (0.58s) | 64 green | PASS |
| `factory/prompt/.claude/tests/` 단독 | **54 passed, 1 failed** (0.16s) | 55중 54 green | PASS(기대 일치) |
| 합산 명령 그대로 (`python3 -m pytest tests/ prompt/.claude/tests/ -q`) | **118 passed, 1 failed** (0.71s, 119 collected = 64+55) | — | 일치 |

유일한 fail = `test_step_08_claude_md.py::test_line_count` — `AssertionError: CLAUDE.md is 150 lines (expected 80-130)`. 이것은 기지(旣知)의 줄수 기준 드리프트이며 경로와 무관. **핵심 검증점 충족 증거**: ⓐ 같은 파일의 `test_exists`(`CLAUDE_MD.exists()`, test_step_08_claude_md.py:12)가 green — `CLAUDE_MD = KRT_ROOT / "CLAUDE.md"`(:6,8)가 새 conftest 기본값으로 해석됨. ⓑ fail 메시지 본문이 실제 키움 CLAUDE.md 내용("키움 REST API 종목 스크리너...")을 150줄로 읽어들임 — 즉 `engine/CLAUDE.md`(실존 20,308 bytes, ls 실측)가 **새 위치에서 정상으로 읽혔다**. ⓒ env 변수 KRT_ROOT/AW_ROOT 미설정 상태 실행이므로 기본값 경로가 검증된 것이 맞음.

### ③ 잔여 구경로 grep 전수 분류표 (factory 구역, `command grep` 사용 — 인벤토리 I-2 함정 회피)

총계(텍스트, `--exclude-dir=.git,__pycache__ -I`): **KRT-구 1,002히트 / AW-구 3,730히트** — 아래 분류 합계와 완전 일치(누락 0).

| 분류 | KRT-구 | AW-구 | 성격 | 처분 |
|---|---|---|---|---|
| `.claude/` 전체 (agents·commands·hooks·skills·settings) | **0** | **0** | 살아있는 기계장치 | **본 과업으로 소거 완료** |
| `prompt/.claude/codegen/*.py` + `tests/*.py` | **0** | **0** | 살아있는 코드·테스트 | **본 과업으로 소거 완료** |
| `tests/` (최상위 64 테스트) | **0** | **0** | — | 원래 0 (인벤토리 §4.3 참고와 일치) |
| `prompt/.claude/state.yaml` | 3 | 0 | **동결 SOT** | **역사 보존** (의도적 잔존 — §2) |
| `state.yaml.bak` + `.testsnap-1780187139` | 6 | 0 | SOT 백업/스냅샷 | 보존(삭제 후보 — 인벤토리 §4.4) |
| `prompt/outputs/` (en+ko 산출물) | 186 | 2 | 빌드 비행기록 | 역사 보존 |
| `prompt/workflow.md`·`workflow-coding.md`·`workflow-idea.md`·`prd.md` | 40 | 5 | 빌드 스펙(◇ — 비행기록) | 역사 보존. **단 차기 빌드 재실행 결정 시 치환 필요**(인벤토리 §5-5) |
| `docs/integrated-user-command-manual.md`(4+2)·`docs/architectural-decision-records.md`(1+0)·`AGENTS.md:1281`(1+0) | 6 | 2 | 살아있는 문서(인벤토리 ◆)이나 **1-2b 지시 범위(a/b/c) 밖** | **미치환 — 후속 문서 과업 또는 마스터 결정 필요** (§5 이슈 I-A) |
| `prompt-runner/` (logs 4,395급 stream.jsonl + execution.log 7 + report.md) | 761 | 3,721 | 러너 실행 로그 | 역사 보존 (인벤토리 제외 영역). runner `*.py` 자체는 히트 0 (grep 실측) |
| `.claude/context-snapshots/` | — | — | 모노레포에 **부재**(gitignored — 격리설계 §C군대로 미이주) | 해당 없음 |
| **합계** | **1,002** | **3,730** | | |

(참고: 모노레포 이주본의 outputs 186은 인벤토리 원본 기준 KRT-구 분과 일치 — 원본 "192"는 `/Users/tajun` 전체 패턴 합산으로 KRT 186 + AW 2 + pyenv 4 = 192 재검산 일치.)

## 4. 변경 파일 최종 목록 (git status 실측 — factory 구역 12파일, 커밋 없음)

```
M factory/.claude/agents/{architect,claude-md-builder,error-analyzer,infra-validator,
   param-extractor,pipeline-analyzer,scan-builder,smoke-tester,tune-builder}.md   (9)
M factory/.claude/commands/accept-system.md                                       (1)
M factory/prompt/.claude/codegen/infra_schema.py                                  (1)
M factory/prompt/.claude/tests/conftest.py                                        (1)
```

engine 측 4파일(`engine/CLAUDE.md` 등) 동시 수정 상태는 병행 과업 1-2a의 것 — 본 과업은 미접촉.

## 5. 이슈

- **I-A (범위 밖 잔존 — 결정 필요)**: `docs/integrated-user-command-manual.md`(:199,200,642,643,678,687 — 678·687이 Path Constants 정의점), `docs/architectural-decision-records.md:10`, `AGENTS.md:1281` 합계 8히트는 인벤토리에서 ◆(치환 필요)로 분류된 **살아있는 문서**지만 1-2b 지시 범위(a/b/c)에 없어 미치환. 후속 과업 배정 권고.
- **I-B (기지 드리프트)**: `test_line_count` fail은 engine/CLAUDE.md 150줄 vs 빌드 당시 기준 80-130 — 경로 치환과 무관한 기존 베이스라인 드리프트. 기준 갱신 여부는 마스터 게이트 결정 사항.
- **I-C (확인 못함)**: `pacs-logs/` 부재 사유 — gitignore 때문인지 filter-repo 누락인지 원본 repo 비교는 본 과업에서 미수행(읽기 전용 원본 grep만 인벤토리에서 인용). 이주 완전성 검증은 1-1 보고서 관할.
- **I-D (재가동 전제)**: `prompt/workflow*.md`·`prd.md`의 ◇ 45히트와 `state.yaml` 3히트는 의도적 잔존 — factory를 **차기 빌드에 재가동하려면** 이 두 군의 치환(state.yaml은 마이그레이션 스크립트 경유)이 선행돼야 함.

---
## [정정 추기 — 검증관 실측, 2026-06-13]
§3.③ KRT-구 총계 1,002히트/prompt-runner 761은 집계 꼬리 절단 — 실측 **1,057/816** (차이 55 = 히트≤5 소형 .stream.jsonl 21개 누락). 오차 전량이 '역사 보존(러너 로그)' 분류 내부로 미분류 잔여는 여전히 0 — 결론 불변, 수치만 정정.
