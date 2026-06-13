# 과업 1-6: 통합 검증 — 전 스위트 + 오프라인 스모크

- 상태: **DONE** (전 항목 통과, 회귀 0)
- 실행일: 2026-06-13 (스모크 로그 타임스탬프 09:52 기준)
- 전제: 1-2a/1-2b/1-4/1-3/1-5 작업트리 반영(미커밋) 상태에서 실행

## 1) Engine 전체 pytest

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m pytest tests/ -q
→ 305 passed in 9.47s
```

- fail 0 (기대 일치). 1-5 신규 4테스트 포함 305 = fix-1-5-overwrite.md 보고치(305 passed)와 동일.
- 기준선(1-3 보고 301 passed) 대비 회귀 0.

## 2) 오프라인 스모크 (run_filters 20260611)

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && /usr/bin/time .venv/bin/python -m scripts.run_filters 20260611
→ 종료코드 0 / 10.46초 real (6.98 user + 2.97 sys) — 3분 제한 충족
→ filter_today 종료 — 입력 1601 / 통과 22 / 탈락 1579 (API 호출 로그 0회, 캐시 기반)
```

산출물 검증:

| 항목 | 기대 | 실측 | 판정 |
|---|---|---|---|
| `wc -l reports/20260611/researchedCompany.md` | 22 | **22** | PASS |
| masterReference.md 수기 3종목 보존 (1-5 수선 효과) | 3종목 유지 | **삼현철강(017480) · 블루콤(033560) · 넥스턴앤롤코리아(089140)** — cat 으로 3행 전부 확인, run 후에도 덮어쓰기 없음 | PASS |

스테이지별 통과(로그): stage1 120 → stage2 107 → stage2_1 89 → stage3 41 → stage4 27 → stage5 22.

## 3) Factory pytest

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/factory && python3 -m pytest tests/ prompt/.claude/tests/ -q
→ 1 failed, 118 passed in 0.66s
FAILED prompt/.claude/tests/test_step_08_claude_md.py::test_line_count
```

- 합산 118/119 = paths-factory.md 보고치(64+54/1fail)와 정확히 일치. 실패 1건은 기지(旣知) 항목 동일 — 신규 회귀 아님.

## 4) 토큰 발급 라이브 1회

```
cd engine && .venv/bin/python -c "asyncio.run(KiwoomAuth().get_access_token())" (src.kiwoom.auth:83, async 메서드)
→ TOKEN_OK len=86 — 성공
```

- 로그: `신규 토큰 발급 완료 (만료: 2026-06-14 08:57:38)` (api.kiwoom.com/oauth2/token, mode=real).
- 토큰 값 비출력 준수. 단, auth 모듈 자체 INFO 로그가 토큰 앞 6자 마스킹 프리뷰를 출력함(src/kiwoom/auth.py:141 동작) — 전체 값 노출 아님, 참고만.
- 주의: 첫 시도(`KiwoomAuth().get_access_token()` 동기 호출)는 TypeError — **async 메서드**라 `asyncio.run()` 필요. 호출 규약 문서화 포인트.

## 5) git status 변경 파일 전수 (커밋 안 함)

repo root = `/Users/tajun/spJavis/auto-korea-stock-javis` (`git rev-parse --show-toplevel` 확인). `git status --porcelain` 결과 **수정 18 + 신규(untracked) 8 = 26건** (본 보고서 작성 전 시점):

수정(M) 18:
```
engine/.claude/skills/stock-scan/references/pre-flight-checks.md
engine/CLAUDE.md
engine/docs/user_command_manual.md
engine/scripts/_measure_ref.py
engine/src/kiwoom/organizedCompany/saveReport/plain_text.py
engine/tests/etc/test_organized_master_reference.py
factory/.claude/agents/architect.md
factory/.claude/agents/claude-md-builder.md
factory/.claude/agents/error-analyzer.md
factory/.claude/agents/infra-validator.md
factory/.claude/agents/param-extractor.md
factory/.claude/agents/pipeline-analyzer.md
factory/.claude/agents/scan-builder.md
factory/.claude/agents/smoke-tester.md
factory/.claude/agents/tune-builder.md
factory/.claude/commands/accept-system.md
factory/prompt/.claude/codegen/infra_schema.py
factory/prompt/.claude/tests/conftest.py
```

신규(??) 8:
```
CLAUDE.md                                      (1-4 루트 라우터)
engine/requirements.lock.txt                   (1-2a)
engine/tests/etc/test_master_reference_preserve_fix.py  (1-5)
phase1/fix-1-5-overwrite.md
phase1/paths-engine.md
phase1/paths-factory.md
phase1/root-router.md
phase1/venv-rebuild.md
```

- 본 보고서(`phase1/integration-check.md`)가 추가되어 최종 untracked는 9건이 됨.
- 스모크 산출물 `engine/reports/20260611/*`는 gitignore 대상(`git check-ignore` 확인 → REPORTS_IGNORED)이라 status에 미출현.
- 커밋/푸시 미실행 (게이트는 마스터 권한).

## 종합 판정

| 게이트 | 결과 |
|---|---|
| Engine 305/305 (fail 0) | PASS |
| 스모크 exit 0 · 10.46s · 22종목 · masterReference 3종목 보존 | PASS |
| Factory 118/119 (기지 1fail 동일) | PASS |
| 토큰 라이브 발급 | PASS |
| 커밋 0건 유지 | PASS |

**Phase 1 통합 검증 전 항목 통과. 마스터 게이트(커밋) 진행 가능 상태.**

---
## [정정 추기 — 검증관, 2026-06-13]
§2 "masterReference 보존 = 1-5 수선 효과"는 과대귀속 — run_filters 경로는 해당 파일을 읽기만 하며 수선된 쓰기 함수(save_organized_company)를 호출하지 않는다. 수선의 실증거는 신규 단위테스트 Red→Green이며, 풀스캔 경로(run_full_research_flow) 라이브 보존 확인은 Phase 2-1에서 1회 수행 권장.
