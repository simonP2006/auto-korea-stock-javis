# Phase 1 — 과업 1-5: masterReference.md 0바이트 덮어쓰기 함정 수선 (TDD)

- 일시: 2026-06-13
- 작업자: Phase 1 워커 (subagent)
- 작업 범위: /Users/tajun/spJavis/auto-korea-stock-javis/engine (원본 두 repo 미접촉)
- git commit/push 미수행 (마스터 게이트 대기)

## 1. 버그 확정 근거

`engine/src/kiwoom/organizedCompany/saveReport/plain_text.py` 73-75행(수정 전):

```python
# organizedCompany.md 생성 직후 동일 디렉터리에 빈 masterReference.md 를
# 항상 생성한다. 기존 내용이 있어도 매번 0바이트로 덮어쓴다.
master_path = out_dir / _MASTER_REFERENCE_FILENAME
master_path.write_text("", encoding="utf-8")
```

- `save_organized_company()` 가 매 실행마다 `masterReference.md` 를 무조건 `""` 로 write → 같은 날 사용자가 수기 기입한 종목 리스트가 재스캔 시 소실.
- 모듈 docstring(14-16행)과 기존 테스트 `engine/tests/etc/test_organized_master_reference.py:46-60` (`test_existing_master_reference_overwritten_empty`)이 이 버그 동작을 "스펙"으로 박제하고 있었음 → 수선과 함께 갱신 필요.

## 2. TDD 절차

### 2-1. Red — 실패 테스트 먼저

신규 파일: `engine/tests/etc/test_master_reference_preserve_fix.py` (4 tests)

| # | 테스트 | 계약 |
|---|---|---|
| ① | `test_creates_empty_master_reference_when_absent` | 파일 없으면 0바이트 생성 (기존 동작 보존) |
| ② | `test_preserves_existing_master_reference_with_content` | 내용 있으면 보존 (덮어쓰기 금지) |
| ③ | `test_existing_empty_master_reference_is_harmless` | 빈 파일 존재 시 그대로 (재실행 무해) |
| ④ | `test_organized_company_still_written_when_master_preserved` | 보존 분기에서도 organizedCompany.md 쓰기 경로 불변 |

수정 전 실행 결과 (red 확인):

```
.venv/bin/python -m pytest tests/etc/test_master_reference_preserve_fix.py -q
→ 1 failed, 3 passed
FAILED ...::test_preserves_existing_master_reference_with_content
AssertionError: assert '' == '사용자 수기 기입 종목\n삼성전자\n현대해상\n'
```

②가 정확히 버그를 재현(수기 내용이 '' 로 소실). ①③은 현행 동작상 통과 — 의도된 보존 계약.

### 2-2. Green — 최소 수정

`plain_text.py` 의 masterReference 쓰기 로직만 변경 (다른 산출물 쓰기 경로 불변 — organizedCompany.md 쓰기(63-70행)는 한 글자도 안 건드림):

```diff
     master_path = out_dir / _MASTER_REFERENCE_FILENAME
-    master_path.write_text("", encoding="utf-8")
-    logger.info("masterReference.md 생성(빈 파일): {p}", p=master_path)
+    if not master_path.exists():
+        master_path.write_text("", encoding="utf-8")
+        logger.info("masterReference.md 생성(빈 파일): {p}", p=master_path)
+    else:
+        logger.info("masterReference.md 기존 파일 보존(덮어쓰기 안 함): {p}", p=master_path)
```

부수 갱신(코드 동작과 문서 일치):
- `plain_text.py` 모듈 docstring 14-17행: "항상 0바이트 덮어쓴다" → "없을 때만 생성, 기존 파일 절대 덮어쓰지 않음" 으로 정정.
- `engine/tests/etc/test_organized_master_reference.py`: 버그를 스펙으로 박제했던 `test_existing_master_reference_overwritten_empty` → `test_existing_master_reference_preserved` 로 교체(보존 단언). 파일 docstring도 동기화. 테스트 수 변화 없음(1개 교체).

## 3. 변경 파일 요약 (git diff --stat)

```
engine/src/kiwoom/organizedCompany/saveReport/plain_text.py | 19 ++++++++++++-------
engine/tests/etc/test_organized_master_reference.py         | 19 ++++++++++++-------
2 files changed, 24 insertions(+), 14 deletions(-)
?? engine/tests/etc/test_master_reference_preserve_fix.py    (신규, 4 tests)
```

소스 코드 변경은 `plain_text.py` 단 1개 파일, masterReference 분기 한 곳뿐.

## 4. 전체 테스트 결과 (회귀 검증)

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m pytest tests/ -q
→ 305 passed in 9.59s
```

| 항목 | 수 |
|---|---|
| 1-3 보고 기준선 (phase1/venv-rebuild.md §4) | 301 passed |
| 신규 테스트 (test_master_reference_preserve_fix.py) | +4 |
| 기존 테스트 교체 (overwritten→preserved, 수 불변) | ±0 |
| 수정 후 전체 | **305 passed, 0 failed** |
| 회귀 | **0** (301 → 305, 기존 전부 green) |

## 5. 결론

- 매 스캔마다 masterReference.md 를 0바이트로 밀어버리던 함정 제거. 이제 파일이 없을 때만 빈 파일 생성, 기존 파일(사용자 수기 기입 포함)은 보존.
- 다른 산출물(organizedCompany.md) 쓰기 경로 불변 — 테스트 ④로 단언.
- 시크릿 미출력, .env 미접촉, 원본 두 repo 미접촉, git 커밋 미수행.
