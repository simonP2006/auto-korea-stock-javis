# pre-flight-checks.md

PRD B-13 사전 검증 체크 5개의 canonical 정의. Step 4 architecture §5 verbatim 인용.

각 체크는: **ID — Check 설명 — Bash 명령어 — 기대 exit code — 실패 시 한국어 메시지 + 복구 안내** 형식.

stock-scan은 (a)(b)(c)(d)를 적용; (e)는 filter-tune 전용 (본 Skill 범위 외).

---

## 타이밍 다이어그램

```
세션 시작 (CLAUDE.md onboarding):
   → (a), (b), (c)                                [lightweight, sub-second]

본 Skill 첫 Bash 실행 직전 (R-11 caveat — OQ-3 권한 probe):
   → (b) 재실행 (dangling symlink 방어 — R-10) + 권한 probe

SHOW_RESULTS / WHY_REJECTED / RERUN_FILTERS 직전 (target date X):
   → (d) prefetchManifest 무결성                  [JSON parse, ~50ms]

filter-tune Edit 전 (본 Skill 범위 외 — 언급만):
   → (e)                                          [grep, ~10ms]
```

---

## (a) `KRT_ROOT` 존재 확인

- **Bash**: `test -d /Users/tajun/spJavis/auto-korea-stock-javis/engine`
- **기대 exit**: `0`
- **실패 시**: AskUserQuestion — `"kiwoom-rest-trader 프로젝트 경로를 찾을 수 없습니다. 정확한 절대 경로를 알려주세요."` 사용자 응답으로 CLAUDE.md `Path Constants` 보정 (one-shot onboarding only — workflow §Error Handling `on_path_not_found` 정책).

복구 흐름:
```
fail (a)
  └── AskUserQuestion (경로 재확인)
       ├── 사용자가 새 경로 제공 → 검증 → 성공 시 진행
       └── 사용자가 모름/취소 → "프로젝트를 찾지 못해 실행을 중단합니다." 종료
```

---

## (b) Python venv 실행파일 + 권한 probe

R-10 dangling pyenv symlink 방어를 위해 `test -x` + 실제 `--version` 호출 chaining 필수.

- **Bash**: `[ -x /Users/tajun/spJavis/auto-korea-stock-javis/engine/.venv/bin/python ] && /Users/tajun/spJavis/auto-korea-stock-javis/engine/.venv/bin/python --version`
- **기대 exit**: `0`, stdout `Python 3.12.x`
- **실패 시 (test -x 실패)**: `"가상환경 Python 실행파일이 없습니다. cd ${KRT_ROOT} && python3.12 -m venv .venv && pip install -r requirements.txt 를 먼저 실행해주세요."` — 이후 모든 실행 체인 차단.
- **실패 시 (test -x 성공인데 --version 실패 = dangling symlink — R-10)**: 동일 한국어 메시지 + 차단.
- **권한 probe 실패 (R-11)**: 첫 `cd ${KRT_ROOT} && .venv/bin/python --version` 호출이 permission-denied로 거부되면 사용자에게 `"Bash(cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && *)"`를 `.claude/settings.local.json`의 allow 목록에 추가하라고 안내하거나 `/install` slash command 사용을 제안.

복구 흐름:
```
fail (b)
  ├── test -x 실패          → "venv 생성 명령 안내" → 사용자가 venv 재생성 후 재시도
  ├── --version 실패 (R-10) → "venv가 pyenv 깨진 symlink일 수 있음 — venv 재생성 안내"
  └── permission-denied (R-11)
       └── settings.local.json allow rule 추가 안내 (Edit, NEVER overwrite) 또는 `/install`
```

---

## (c) reports/ 디렉터리 쓰기 권한

- **Bash**: `test -w /Users/tajun/spJavis/auto-korea-stock-javis/engine/reports`
- **기대 exit**: `0`
- **실패 시**: `"reports/ 디렉터리에 쓰기 권한이 없습니다. chmod u+w 또는 디스크 여유 공간을 확인해주세요."`

복구 흐름:
```
fail (c)
  ├── chmod 안내           → 사용자가 권한 부여 후 재시도
  └── 디스크 여유 공간 확인 → df -h 권장 (안내만)
```

---

## (d) prefetchManifest.json 무결성 (SHOW_RESULTS / WHY_REJECTED / RERUN_FILTERS 직전)

Fix-Step10-A 방어적 sentinel set: `isinstance` 필터를 명시적 비-ok value set 비교로 교체 (Review #1).

- **Bash**:
  ```
  python3 -c "import json,sys; p='/Users/tajun/spJavis/auto-korea-stock-javis/engine/reports/{YYYYMMDD}/prefetchManifest.json'; d=json.load(open(p)); errs=sum(1 for s in d['by_stock'].values() for v in s.values() if v not in ('ok','empty','null',None,'')); print(f'OK_total={len(d[\"by_stock\"])} ERR={errs}'); sys.exit(0 if errs==0 else 1)"
  ```
- **기대 exit**: `0` (zero errored stocks).
- **날짜 해소**: 명시 인자 → 오늘 KST `date +%Y%m%d` → 모호 시 AskUserQuestion.
- **실패 시 (파일 미존재 — FileNotFoundError raised by json.load)**: `"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."` 후 체인 halt.
- **실패 시 (파일 존재 + errs>0)**: count 한국어 보고 → `"{date} prefetch에서 {ERR}개 종목 오류. 실패 종목만 재수집하시겠습니까?"` 안내.
- **KeyError fallback**: manifest 구조 변경(legacy report 디렉터리에 `by_stock` 누락) 시 stock-scan이 KeyError trap → `"manifest 형식을 알 수 없습니다 — prefetch를 다시 실행해주세요."`로 downgrade.

복구 흐름:
```
fail (d)
  ├── FileNotFoundError    → SCAN_PREFETCH_ONLY 안내
  ├── errs > 0             → "실패 종목 재수집" 안내
  └── KeyError (legacy)    → "manifest 형식 미상 — prefetch 재실행" 안내
```

---

## (e) 파라미터 변수명 grep (filter-tune 전용 — stock-scan 범위 외)

본 Skill은 `Final` 상수를 절대 Edit하지 않으므로 (e)는 실행 대상이 아니다. 경계 문서화 목적으로만 언급:

- **Bash (filter-tune이 실행)**: `grep -n '\b{VARIABLE_NAME}\b' /Users/tajun/spJavis/auto-korea-stock-javis/engine/{file_path}`
- **기대**: exit 0 AND `wc -l ≥ 1`.
- **실패 시 (0 hit)**: filter-tune Skill이 `"변수명이 변경된 것 같습니다. 다음 파일에서 비슷한 변수를 찾았습니다: {fuzzy results}"` 안내 + Edit 차단 + 사용자 재확인.

stock-scan은 이 체크를 절대 직접 수행하지 않는다.

---

## R-9 advisory lock 체크 (stock-scan이 실행 체인 1/2/3/8 전에 수행)

`(a)(b)(c)(d)`와 별개로, 모든 실행 체인(1, 2, 3, 8)은 Bash invocation 직전 다음을 추가 확인:

- **Bash**: `test -d /Users/tajun/spJavis/auto-korea-stock-javis/engine/reports/filter-tune.lock`
  (락은 filter-tune이 `mkdir`로 생성하는 **디렉터리**다 — `test -f`는 디렉터리에 대해 false를 반환하므로 반드시 `test -d`를 사용한다. filter-tune SKILL.md §3 Step 5 mkdir / Step 7 rmdir과 대칭.)
- **존재 시 (exit 0)**: 거부 — `"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`
- stock-scan은 락을 생성·해제하지 않는다 (filter-tune 측 책임).

---

## (a)~(e) Cross-reference

| 체크 | 적용 체인 | 출처 |
|---|---|---|
| (a) | 세션 시작 (1회만) | PRD B-13, Step 4 architecture §5 |
| (b) | 세션 첫 Bash 직전 (1회만) + R-10 dangling symlink + R-11 권한 | 동 |
| (c) | 세션 시작 (1회만) | 동 |
| (d) | Chain 4 SHOW_RESULTS, Chain 5 WHY_REJECTED, Chain 8 RERUN_FILTERS | 동 (Fix-Step10-A 방어적 sentinel) |
| (e) | filter-tune Skill 전용 — N/A | 본 Skill 범위 외 |
| R-9 lock | Chain 1, 2, 3, 8 (Bash invocation 전) | Step 4 §10 Risk Register R-9 |
