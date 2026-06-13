# Phase 1 — 과업 1-3: engine venv 재구축 + lock 고정

- 일시: 2026-06-13
- 작업자: Phase 1 워커 (subagent)
- 작업 범위: /Users/tajun/spJavis/auto-korea-stock-javis/engine (원본 repo 무수정)

## 1. Lock 원본 확인

- `/tmp/aksj_engine_freeze.txt` 존재 확인: `wc -l` → **48줄** (기대값 48과 일치). 재생성 불필요 — 원본 repo 미접촉.
- 첫 5줄(샘플): aiolimiter==1.2.1 / annotated-types==0.7.0 / anyio==4.13.0 / black==26.3.1 / certifi==2026.4.22

## 2. venv 재구축

명령:
```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine
python3 -m venv .venv
.venv/bin/pip install --quiet -r /tmp/aksj_engine_freeze.txt
```
- 결과: **exit 0** (`INSTALL_EXIT=0`). 개별 패키지 실패 **없음** (0건).
- 인터프리터: `.venv/bin/python --version` → **Python 3.12.7** (시스템 `python3 --version`과 동일).
- 참고(무해): pip 자체 업그레이드 알림만 출력됨 (24.2 → 26.1.2). lock 재현성 위해 pip 업그레이드는 하지 않음.

## 3. Lock 영구화

```
cp /tmp/aksj_engine_freeze.txt /Users/tajun/spJavis/auto-korea-stock-javis/engine/requirements.lock.txt
```
- `wc -l engine/requirements.lock.txt` → **48줄**.
- 설치본 대조: `diff <(.venv/bin/pip freeze | sort) <(sort requirements.lock.txt)` → **차이 0건 (identical)**. 설치된 48개 패키지 = lock 48줄 완전 일치.

## 4. 스모크 테스트

| 항목 | 명령 | 결과 |
|---|---|---|
| import 스모크 | `.venv/bin/python -c "import pandas, numpy, httpx, websockets, pydantic; print('imports OK')"` | **imports OK** |
| 전체 테스트 | `cd engine && .venv/bin/python -m pytest tests/ -q` | **301 passed in 9.61s** (기대값 301 passed와 일치, 실패/스킵/경고 라인 없음) |

## 5. 결론

- engine venv 재구축 **완료**. lock(48 패키지) 그대로 설치, freeze 대조 완전 일치, import 스모크 OK, pytest 301/301 통과.
- 산출물:
  - `/Users/tajun/spJavis/auto-korea-stock-javis/engine/.venv/` (Python 3.12.7, 48 패키지)
  - `/Users/tajun/spJavis/auto-korea-stock-javis/engine/requirements.lock.txt` (48줄)
- git commit/push 미수행 (마스터 게이트 대기), 원본 두 repo 미접촉, 시크릿 미출력.
