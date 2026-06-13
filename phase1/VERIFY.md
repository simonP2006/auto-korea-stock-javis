# Phase 1 Wave-2 적대 검증 보고 (VERIFY)

- 검증자: Phase 1 적대 검증관 (subagent)
- 일시: 2026-06-13 (재실행 기반 — 모든 수치는 본 검증 세션의 직접 명령 출력)
- 범위: phase1/*.md 6종 (venv-rebuild · fix-1-5-overwrite · paths-engine · paths-factory · root-router · integration-check) 표본 재실행 + 직독 대조
- 준수: 원본 두 repo 읽기 전용(`git status --porcelain` 조회만), git commit/push 0건, 시크릿 미출력, .env 미접촉

## 종합 판정: **PASS (조건부 — 경미한 수치 오류 1건 + 과대귀속 1건, 게이트 차단 사유 아님)**

| 검증 항목 | 판정 |
|---|---|
| ① engine pytest 재실행 = 보고 일치 | **PASS** |
| ② run_filters 20260611 재실행 — 22 유지 + masterReference 보존 | **PASS** |
| ③ 경로 치환 잔여 grep — 미분류 잔여 0 | **PASS** (단, 1-2b 총계 수치 오류 — §3-B) |
| ④ 루트 CLAUDE.md vs engine/CLAUDE.md 모순 | **모순 0** (진부 항 2건 후속 정리 권고) |
| ⑤ 날조·무근거 주장 스캔 | 날조 0 · 무근거(과대귀속) 1 · 미재검증 1 |

---

## ① engine pytest 재실행 — PASS

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m pytest tests/ -q
→ 305 passed in 9.46s   (fail 0)
```

- 1-6 보고치 `305 passed in 9.47s` 및 1-5 보고치 `305 passed in 9.59s`와 **일치**.
- 1-3 기준선 301 + 1-5 신규 4 = 305 산식 정합. 1-5 신규 테스트 파일 단독 재실행도 green:
  `pytest tests/etc/test_master_reference_preserve_fix.py tests/etc/test_organized_master_reference.py -q → 7 passed`
  (4 신규 + 교체본 `test_existing_master_reference_preserved` 포함 — 테스트명 grep 실측).
- factory 측도 재실행: `python3 -m pytest tests/ prompt/.claude/tests/ -q → 1 failed, 118 passed in 0.66s`,
  실패는 동일 기지 항목 `test_step_08_claude_md.py::test_line_count` (engine/CLAUDE.md `wc -l`=150 실측, 기준 80-130) — 1-2b·1-6 보고와 일치, 신규 회귀 0.

## ② run_filters 20260611 재실행 — PASS (핵심 수용 기준 충족)

사전 상태 (재실행 전 실측): `masterReference.md` 3행 = 삼현철강(017480)·블루콤(033560)·넥스턴앤롤코리아(089140), MD5 `258327de6ac7dc36ec9ef2f0b20a6f8c`; `researchedCompany.md` 22행, MD5 `370a0b13f9794611031e964affe023e6`.

```
cd engine && /usr/bin/time .venv/bin/python -m scripts.run_filters 20260611
→ exit 0 / 9.90s real
→ filter_today 종료 — 입력 1601 / 통과 22 / 탈락 1579
→ stage1 120 → stage2 107 → stage2_1 89 → stage3 41 → stage4 27 → stage5 22
```

사후 상태: `researchedCompany.md` **22행, MD5 동일**(370a0b13…) · `masterReference.md` **3행, MD5 동일**(258327de…) — **수기 3종목 바이트 단위 보존**. 1-6 보고의 모든 수치(1601/22/1579, 스테이지 체인, 22행, 3종목)와 일치. `masterReference.log`도 미변경(mtime 6/11 22:29 유지) — 본 재실행의 잔류 부수효과 없음(산출물은 gitignore 확인: `git check-ignore` → ignored).

### 주의 — 1-6의 "(1-5 수선 효과)" 귀속은 과대 (§5-2 상세)

코드 추적 실측: 수선된 쓰기 경로 `save_organized_company()`(engine/src/kiwoom/organizedCompany/saveReport/plain_text.py:45, 보존 분기 :76-81)의 호출자는
`facade.py:482(_stage_organized_company ← run_full_flow 전용)` · `scripts/run_prefetch.py:129` · `scripts/run_organize_company.py:41` **뿐**이다.
`run_filters → filter_today`는 masterReference.md를 **읽기만** 하며(쓰기 호출 grep 0건), 수정 전 코드로도 run_filters는 이 파일을 덮어쓰지 않았다.
→ run_filters 스모크의 보존 관찰은 **수용 기준으로서는 유효하나 1-5 수선의 증거로는 공허(vacuous)**. 수선의 실증거는 신규 4테스트의 Red→Green(②테스트가 덮어쓰기 재현 후 보존 단언으로 전환)이며, 이는 본 검증에서 green 재확인됨. **풀스캔(run_full_research_flow/run_prefetch) 경로의 라이브 보존 검증은 Phase 2 스캔 시 1회 확인 권고.**

## ③ 경로 치환 잔여 grep 전수 대조 — 미분류 잔여 0 (단, 1-2b 총계 수치 오류)

검증 명령(보고서와 동일 조건, `command grep` 사용):

### A. engine 구역 — 1-2a 분류표와 완전 일치

```
command grep -rc "spJavis/kiwoom-rest-trader" engine/ --exclude-dir=.venv -I | grep -v ':0$'
→ logs/research_flow_20260510_184508.log:128
→ reports/TUNING_RESUME_20260605.md:1
→ reports/masterReference_전체_현재조건_분석_20260514_20260601.md:1
→ reports/masterReference_run_filters_튜닝_시뮬레이션_20260603.md:1
command grep -rc "spJavis/AgenticWorkflow-…" engine/ … → 0건
```

- 잔여 4파일 = 1-2a §3 표의 4행과 **1:1 대응, 미분류 잔여 0**. 전부 로그·이력문서(의도적 보존).
- 신경로 검증치 재현: pre-flight-checks.md 신경로 히트 행 = `31 49 53 68 87 109 121`(7행)·occurrence 8건, user_command_manual.md:4 = 1건, engine/CLAUDE.md:7 `KRT_ROOT = …/auto-korea-stock-javis/engine`(grep -n 실측), `_measure_ref.py:4` = `Path(__file__).resolve().parents[1] / "reports"` — 1-2a §1·§5와 전부 일치.

### B. factory 구역 — 분류 커버리지 완전 / **총계 수치 오류 1건**

```
command grep -r "<구경로>" factory/ --exclude-dir=.git --exclude-dir=__pycache__ -I | wc -l
→ KRT-구 1,057   /   AW-구 3,730
```

| 분류 (1-2b §3.③ 표) | 보고 KRT | 실측 KRT | 보고 AW | 실측 AW | 판정 |
|---|---|---|---|---|---|
| `.claude/`·codegen·tests (살아있는 구역) | 0 | **0** | 0 | **0** | 일치 |
| state.yaml | 3 | **3** | 0 | 0 | 일치 |
| state.yaml.bak + .testsnap | 6 | **6** | 0 | 0 | 일치 |
| prompt/outputs | 186 | **186** | 2 | **2** | 일치 |
| workflow*.md·prd.md | 40 | **40** (20+15+3+2) | 5 | **5** (2+3+0+0) | 일치 |
| docs 2종 + AGENTS.md | 6 | **6** (4+1+1) | 2 | **2** | 일치 |
| prompt-runner/ | **761** | **816** | 3,721 | **3,721** | **KRT 불일치 (-55)** |
| **합계** | **1,002** | **1,057** | **3,730** | **3,730** | **KRT 총계 불일치** |

- **오류 내용**: 1-2b의 "총계 KRT-구 1,002 — 분류 합계와 완전 일치(누락 0)" 주장은 수치상 거짓. 실측 1,057. 차이 55는 전부 `prompt-runner/logs/*.stream.jsonl` 중 **히트 ≤5인 소형 파일 21개의 꼬리 합**(5+5+4+4+4+3×5+2×7+1×4=55) — 집계 시 꼬리 절단으로 추정.
- **영향 평가**: 오차는 전량 "러너 실행 로그 = 역사 보존" 분류 내부에 갇혀 있음. per-file 전수 실측 결과 **분류표 밖 파일 0** — 살아있는 구역(.claude·codegen·tests) 잔여 0 재확인. 과업 ③의 FAIL 조건("미분류 잔여")에는 **해당 없음**. 단, 보고서 수치는 1,057/816으로 **정정 필요**.
- 1-2b §5 이슈란의 범위 밖 잔존(I-A: docs 6+2히트, AGENTS.md:1281)·재가동 전제(I-D)는 실측과 일치 — 은폐 없음.

## ④ 루트 CLAUDE.md ↔ engine/CLAUDE.md 모순 직독 — 모순 0

두 문서 전문 직독 + root-router.md §② 12행 대조표 재검:

1. **Path 상수**: engine:7 `KRT_ROOT = …/auto-korea-stock-javis/engine` = 루트 §1 `ENGINE_ROOT` 값과 **동일** — 충돌 없음.
2. **14 Intent**: 루트 나열 14개 = engine Intent Routing 표 Cluster 열 14개, 이름·순서 전수 일치(직접 대조). 상세 미복제 — 위임 구조 준수.
3. **실행 규약**: run_filters <3분(양쪽 일치) · background 필수(일치) · `source activate` 금지(일치) · EXEC_PATTERN 의미 동일.
4. **소요 시간 10-15분 vs 80분~6h / 30분 watchdog**: 침묵 충돌 아님 — 루트 §3이 "진부·신뢰 금지"를 **명시 선언**하고 우선순위를 고정(root-router §② #9·#12 판정 타당).
5. **모드 경계**: 양쪽 모두 "명시 발화만 factory 진입·역방향 호출 금지" — 일치.

**진부(stale) 항 2건 — 모순은 아니나 후속 정리 권고**:
- (a) 루트 §1 과도기 우선규칙(:17)이 "engine `KRT_*`가 **아직 구 경로**를 가리키는 동안"이라는 조건문인데, 1-2a 완료로 조건이 이미 거짓 → 조항 공허化. 루트 문서 스스로 "치환 완료 시 자연 소멸" 명기 + root-router §④-1이 삭제 필요를 기록했으므로 기만 아님. **루트 :17의 구경로 리터럴 1건 포함, 마스터 게이트에서 해당 항 삭제 권고.**
- (b) engine/CLAUDE.md:58 "별도 저장소(AgenticWorkflow `workflow-executor`)에 존재" — 빌드 시스템은 이제 동일 모노레포 factory/ 구역. **명칭·소재 서술 진부**(경로 리터럴 아님 — 1-2a §6의 명칭 보존 방침과 동궤). 경계 규칙 자체는 루트와 동일 방향이라 모순 아님. 명칭 리브랜딩 과업에 포함 권고.

## ⑤ 날조·무근거 주장 스캔

추가 검증한 사실 주장 (전부 실측 재현):

| 주장 (출처) | 재검 결과 |
|---|---|
| lock 48줄·freeze 대조 identical (1-3) | `wc -l`=48, `diff <(pip freeze|sort) <(sort lock)` → 차이 0 — **사실** |
| Python 3.12.7 (1-3·1-4) | `.venv/bin/python --version` → 3.12.7 — **사실** |
| 루트 CLAUDE.md 86줄 (1-4) | `wc -l`=86 — **사실** |
| engine/CLAUDE.md 150줄 유지 (1-2a) | `wc -l`=150 — **사실** |
| git HEAD `e6a1ef7` 불변·커밋 0 (1-2b·1-6) | `git rev-parse HEAD`=e6a1ef73… · log -1 동일 — **사실** |
| 변경 수정 18 + untracked 9 (1-6) | `git status --porcelain` → M 18 / ?? 9 — **사실** (본 VERIFY.md로 10번째 추가됨) |
| reports 산출물 gitignored (1-6) | `git check-ignore` → ignored — **사실** |
| 원본 두 repo 미접촉 (1-2a·공통) | 두 원본 `git status --porcelain` 각 0건 — **사실** |

판정:
- **날조(존재하지 않는 사실) 발견 0건.**
- **무근거(과대귀속) 1건**: 1-6 §2 "masterReference 보존 **(1-5 수선 효과)**" — 보존 관찰은 사실이나 run_filters 경로는 수선 대상 코드(save_organized_company)를 호출하지 않으므로 인과 귀속이 성립하지 않음(§② 주의 참조). 수선 자체는 단위테스트로 별도 입증됨 — 결론 훼손 없음, 문구 정정 권고.
- **미재검증 1건**: 1-6 §4 토큰 라이브 발급(TOKEN_OK len=86) — 외부 라이브 API 호출이라 적대 검증에서 의도적으로 재실행하지 않음. **확인 못함**(반증 근거도 없음).
- **수치 오류 1건**: §③-B의 1-2b KRT-구 총계 1,002(실측 1,057)·prompt-runner 761(실측 816).

## 게이트 권고

1. **수용**: ①②③④ 핵심 기준 전부 충족 — 커밋 게이트 진행 가능.
2. **정정 요구(경미)**: 1-2b §3.③ 수치 1,002→1,057·761→816 정정(분류 커버리지는 무결). 1-6 §2 "(1-5 수선 효과)" 문구를 "(보존 확인 — 단 수선 경로는 풀스캔 전용, 실증거는 단위테스트)"로 정정.
3. **후속 과업 등록**: (a) 루트 §1 과도기 항 삭제(이미 공허) (b) engine:58 AgenticWorkflow 명칭 진부 (c) 1-2b I-A 잔존 8히트 (d) 풀스캔 경로 masterReference 보존 라이브 1회 확인(Phase 2 스캔 겸용).
