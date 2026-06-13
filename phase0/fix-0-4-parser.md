# Phase 0-4: stageMasterFilter masterReference 파서 드리프트 수선

- 일시: 2026-06-13 (워커 보고)
- 대상 repo: `/Users/tajun/spJavis/kiwoom-rest-trader` (branch `main`)
- 커밋: `a9a8f51` — `fix(stageMasterFilter): accept 이름(코드) masterReference format (Phase 0-4)` (**push 안 함** — 마스터 게이트 대기)

## 1. 버그 (확정 근거)

`reports/<날짜>/masterReference.md` 포맷 드리프트:

- 구형 (종목명만): `reports/20260518/masterReference.md` 1행 `영림원소프트랩`
- 신형 (종목명(코드)): `reports/20260611/masterReference.md` 1행 `삼현철강(017480)`

`src/kiwoom/itemFilter/Filter_condition_update.py`는 `_parse_entry`(95–101행)와
`_NAME_CODE_RE`(88행, `^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$`)로 신형을 처리하지만,
`src/kiwoom/itemFilter/stageMasterFilter.py`는 (수정 전 기준):

- `_read_name_list`(140–146행): 줄을 `strip()`만 하고 원문 그대로 반환
- `_stock_dir`(161–173행): `p.name.startswith(name + "(")` 접두 매칭

→ 신형 입력 `삼현철강(017480)`이면 `"삼현철강(017480)("` 접두를 찾게 되어 종목 폴더 매칭
실패 → `_extract_master_features`(수정 전 202–206행)에서
`FileNotFoundError("master 종목 폴더 없음")` — 누적 학습(`accumulate_date`)이 깨짐.

## 2. 변경 내용 (수정 파일 2개만)

### `src/kiwoom/itemFilter/stageMasterFilter.py` (+34 / −3)

입력 파싱만 보강. 필터 수치 로직·Final 상수·다른 파일 일절 미변경 (diff로 확인).

1. `import re` 추가 (38행).
2. `_NAME_CODE_RE` 상수 추가 (86–90행) — `Filter_condition_update.py` 88행과 **동일 패턴**
   `^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$` (끝의 4~6자리 코드 괄호만 코드로 인정).
3. `_split_name_code(line) -> (이름, 코드)` 헬퍼 신설 (147–157행) —
   `Filter_condition_update._parse_entry`와 동등 규칙. 코드 없으면 `(이름, "")`.
4. `_read_name_list` (160–167행): 각 줄을 `_split_name_code(ln)[0]`으로 정규화 —
   구형/신형 모두 **순수 종목명 리스트** 반환. 빈 줄·공백 줄 무시는 기존 그대로.
5. `_stock_dir` (182–203행): 입력을 `_split_name_code`로 분리. 코드가 있으면
   `<이름>(<코드>)` 정확 일치 폴더 우선, 없거나 미발견 시 기존과 동일한
   `이름(` 접두 매칭으로 폴백 — 구형 경로 동작 100% 보존.

파급 효과: `read_master_reference`·`read_organized_company`·`accumulate_date`·
`filter_date`·`cmd_validate`가 모두 위 두 함수를 경유하므로 양 포맷에서 일관 동작.
`accumulate_date`(338–344행)의 master ∈ organizedCompany 집합 비교도 양쪽이
순수 이름으로 정규화되어 포맷 혼재 시 오경보가 사라짐.

### `tests/test_stageMasterFilter_parse.py` (신규, 18 테스트)

TDD — 수정 전 실행 시 red 확인(`ImportError: cannot import name '_split_name_code'`,
드리프트 케이스 자체도 미수정 코드에선 실패 설계). 실파일 포맷을 픽스처로 모사:

| 그룹 | 테스트 | 픽스처 모사 원본 |
|---|---|---|
| 이름·코드 분리 | `test_split_name_code` ×6 (구형/신형/4자리 ETF 코드/비코드 괄호 `씨아이에스(주)`/양끝 공백 2종) | `reports/20260611` 실폴더 `1Q K반도체TOP2+(0182)` 포함 |
| 리스트 읽기 | 구형·신형·혼합(빈 줄/공백 줄)·파일 부재·`read_master_reference` 신형 ×5 | `reports/20260518`·`reports/20260611` masterReference.md 실내용 |
| 폴더 해석 | 구형 이름·신형 이름(코드)·미존재 2종·날짜 폴더 부재·접두 교차매칭 방지(삼성전자/삼성전자우) ×5 | 실폴더 명명 규칙 `<이름>(<코드>)` |
| 통합(학습 경로) | 신형/구형 masterReference → `_extract_master_features` 끝까지 + 4-feature 실수치 검증 ×2 | `reports/20260611/삼현철강(017480)/chartDay.md` 실포맷(헤더+시계열 표) |

## 3. 테스트 결과

| 시점 | 명령 | 결과 |
|---|---|---|
| 베이스라인 (수정 전) | `.venv/bin/python -m pytest tests/ -q` | **283 passed** (9.57s) |
| TDD red (테스트만 추가) | `pytest tests/test_stageMasterFilter_parse.py -q` | collection ERROR (`_split_name_code` ImportError) — 의도된 red |
| 수정 후 신규 | `pytest tests/test_stageMasterFilter_parse.py -q` | **18 passed** (0.18s) |
| 수정 후 전체 | `.venv/bin/python -m pytest tests/ -q` | **301 passed** (9.46s) = 283 + 18, **회귀 0** |

## 4. 실데이터 스모크 (read-only, 상태 파일 미변경)

`read_master_reference` + `_stock_dir`를 실 reports에 적용:

- `20260518` (구형): masters=10, 전 종목 폴더 해석 성공 (`all_resolved=True`)
- `20260611` (신형): masters=3 (`삼현철강`·`블루콤`·`넥스턴앤롤코리아`), 전 종목 폴더 해석 성공 — 수정 전에는 0/3이던 드리프트 케이스

## 5. 커밋

```
a9a8f51 fix(stageMasterFilter): accept 이름(코드) masterReference format (Phase 0-4)
 2 files changed, 248 insertions(+), 3 deletions(-)
 - src/kiwoom/itemFilter/stageMasterFilter.py   (+34 / −3)
 - tests/test_stageMasterFilter_parse.py        (신규)
```

git status clean. **push 하지 않음** — 마스터 게이트(gemini·codex·pytest 4자 수렴) 후 push.

## 6. 비고 / 한계

- 코드 자리수는 `\d{4,6}`로 `Filter_condition_update`와 동일하게 맞춤 — 과업 문구는
  "6자리코드"였으나 "동등한 규칙" 요건과 실데이터(ETF 4자리 폴더 `1Q ...(0182)`)를
  근거로 동일 패턴을 채택. 6자리 한정으로 좁히면 두 파서가 다시 어긋남.
- `_stock_dir` 폴백: 코드가 있는데 해당 코드 폴더가 없으면 이름 접두 매칭으로 폴백 —
  `Filter_condition_update._resolve_ident`(126–130행)의 "코드 우선, 없으면 이름" 철학과 일치.
- `stageMasterFilter_state.json`(누적 상태)은 본 과업에서 건드리지 않음. 드리프트 기간
  (신형 포맷 도입일~현재)에 누락된 daily-update 재누적 여부는 마스터 판단 사항.
