# Phase 1 — 과업 1-2a: engine 구역 경로 치환 보고

- 작성: Phase 1 워커 (2026-06-13)
- 기준 문서: `/Users/tajun/spJavis/auto-korea-stock-javis/phase0/path-inventory.md` (§3 KRT 치환검토 13히트/7파일, §0 command grep 강제, §6 정정)
- 구 경로: `/Users/tajun/spJavis/kiwoom-rest-trader`
- 새 경로(ENGINE_ROOT): `/Users/tajun/spJavis/auto-korea-stock-javis/engine`
- 원본 repo 무변경 확인: `cd /Users/tajun/spJavis/kiwoom-rest-trader && git status --porcelain` → 출력 0건 (읽기 전용 grep/cmp만 수행).

## 1. 치환 실행 결과 (4파일 10행 11건 — 전부 완료)

| # | 파일 (engine/ 기준) | 행 | 건수 | 치환 내용 |
|---|---|---|---|---|
| a | `CLAUDE.md` | 7 | 1 | `KRT_ROOT = /Users/tajun/spJavis/auto-korea-stock-javis/engine` — **이 1행만 수정**. KRT_PYTHON·KRT_REPORTS·KRT_FILTERS·KRT_SCRIPTS(8~11행)는 `${KRT_ROOT}` 파생이므로 단일 정의점 갱신으로 **KRT_* 5상수 전부** 신경로로 해소. 그 외 행 무수정, 총 150행 유지(`wc -l` 확인) |
| b | `.claude/skills/stock-scan/references/pre-flight-checks.md` | 31·49·53·68·87·109·121 | 8 | 리터럴 절대경로 → ENGINE_ROOT 절대경로 (49행은 리터럴 2회 — test -x + --version 체이닝). 치환 후 신경로 히트 행번호가 정확히 31·49·53·68·87·109·121로 일치 확인 |
| c | `scripts/_measure_ref.py` | 4 | 1 | `REPORTS = Path("/Users/tajun/.../reports")` → `REPORTS = Path(__file__).resolve().parents[1] / "reports"` — 절대경로 제거, 코드 자기참조 SOT화 (phase0 §3.1 권장안 채택) |
| d | `docs/user_command_manual.md` | 4 | 1 | "프로젝트 루트(\`...\`)" 백틱 내 경로 1건 → ENGINE_ROOT. 3행의 `kiwoom-rest-trader` 명칭 언급은 경로가 아니므로 보존(과업 범위: 루트 경로 1건) |

검산: phase0 §3의 치환필요 10행(코드 1 + CLAUDE 1 + pre-flight 7 + manual 1) 전부 처리. 13히트 = 위 10행(11건은 49행 2회 포함 occurrence 기준) + bak 3히트(아래 §2).

## 2. 제외 대상 (치환 안 함 — 삭제 후보 목록)

phase0 §3.3의 삭제 후보 4건은 **engine 트리에 존재하지 않음** (monorepo build 시 미복사된 것으로 확인):

```bash
cd engine && find . -name "*.bak.*" -o -name "skills.bak*" -o -name "*.tgz"   # → 출력 0건
```

| 삭제 후보 (phase0 기준) | engine 내 상태 |
|---|---|
| `CLAUDE.md.bak.20260531_180735` / `_183746` / `_193809` | **부재** — 조치 불요 |
| `.claude/skills.bak.20260531_210355.tgz` | **부재** — 조치 불요 |

(원본 KRT에는 그대로 존재 — 읽기 전용이므로 미접촉.)

## 3. 잔여 전수표 (치환 후 grep — 전부 의도적 보존)

검증 명령 (phase0 §0 경고에 따라 `command grep` 사용 — 셸 grep은 ugrep alias로 gitignore 파일 무음 누락):

```bash
# 과업 지정 검증 (py/md 한정)
command grep -rn "spJavis/kiwoom-rest-trader" engine/ --include="*.py" --include="*.md" -l
# 전체 잔여 (바이너리 제외)
cd engine && command grep -rl "spJavis/kiwoom-rest-trader" . --exclude-dir=.venv -I
```

| 잔여 파일 | 히트(행) | 분류 | 근거 |
|---|---|---|---|
| `logs/research_flow_20260510_184508.log` | 128 | 의도적 보존(로그성) | 실행 로그 원문 — phase0 §3.3 제외 영역 |
| `reports/TUNING_RESUME_20260605.md` | 1 (:45) | 의도적 보존(이력문서) | 리포트 본문 내 명령 스니펫 — phase0 §3.3 |
| `reports/masterReference_전체_현재조건_분석_20260514_20260601.md` | 1 (:214) | 의도적 보존(이력문서) | 〃 |
| `reports/masterReference_run_filters_튜닝_시뮬레이션_20260603.md` | 1 (:106) | 의도적 보존(이력문서) | 〃 |

위 4파일 외 잔여 **0**. `*.py`/`*.md` 한정 잔여는 reports 이력문서 3건뿐 — 코드·스킬·문서(활성) 잔여 0.

### 정정추기(수치 해명): 로그 240 vs 128

phase0 §1의 "logs 240히트"는 패턴 `/Users/tajun` 기준, 본 과업 패턴 `spJavis/kiwoom-rest-trader` 기준으로는 동일 파일이 128행. engine 사본은 원본과 바이트 동일(`cmp` → IDENTICAL, 원본 240/128 동일 재현). **모순 아님 — 패턴 차이.**

## 4. 스모크 테스트 (_measure_ref.py)

`ENGINE_ROOT/.venv/bin/python` 존재 확인(Python 3.12.7) 후 import 스모크:

```bash
cd engine && .venv/bin/python -c "import sys; sys.path.insert(0,'scripts'); import _measure_ref as m; \
  print('SMOKE_OK REPORTS=', m.REPORTS); \
  assert str(m.REPORTS)=='/Users/tajun/spJavis/auto-korea-stock-javis/engine/reports'"
```

결과: **성공** — `SMOKE_OK REPORTS= /Users/tajun/spJavis/auto-korea-stock-javis/engine/reports`, assert 통과. (스크립트가 top-level 실행형이라 import 시 본문도 read-only 실행됨 — 기본 8개 날짜에 대해 `TOTAL ref=54 PASS=23 FAIL=31` 출력, engine/reports 실데이터로 end-to-end 동작 확인. 부수효과 없음 — 읽기+print만.)

## 5. 치환 후 신경로 검증 수치

| 파일 | 신경로 히트 | 기대 | 판정 |
|---|---|---|---|
| `CLAUDE.md` | 1행 (:7) | 1 | 일치 |
| `pre-flight-checks.md` | 7행/8건 (:31·49·53·68·87·109·121) | 7행/8건 | 일치 |
| `docs/user_command_manual.md` | 1행 (:4) | 1 | 일치 |
| `scripts/_measure_ref.py` | 0 (절대경로 자체 제거) | 0 | 일치 (자기참조) |

## 6. 이슈

- 없음 (블로커 0). bak/tgz 삭제 후보는 engine에 이미 부재 — Phase 1 후속 삭제 작업 불요.
- 참고: pre-flight-checks.md 33행의 `"kiwoom-rest-trader 프로젝트 경로를 찾을 수 없습니다"` 및 user_command_manual.md 3행의 `kiwoom-rest-trader` **명칭** 언급은 경로 리터럴이 아니므로 보존(과업 범위 외). 명칭 리브랜딩이 필요하면 별도 과업으로.
