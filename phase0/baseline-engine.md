# Phase 0-2a: engine 테스트 그린 베이스라인 (수정 전 기록)

> **본 문서는 어떤 코드 수정도 가하기 전의 베이스라인 기록이다.** (읽기 전용 실행 — 커밋·파일 수정 없음)
>
> - 실행 시각: **2026-06-13 09:18 KST** (pytest 실행 직후 freeze 수행)
> - 대상 repo: `/Users/tajun/spJavis/kiwoom-rest-trader`
> - git HEAD: `359fb57fab39370dffbc78b0b85cd25f9a06329b` (working tree clean — `git status --porcelain` 0건)
> - 인터프리터: `.venv/bin/python` = Python 3.12.7 (`kiwoom-rest-trader/.venv/bin/python --version`)
> - pytest: 9.0.3 (`/tmp/aksj_engine_freeze.txt:37`)

---

## 1. pytest 전체 결과

실행 명령:

```
cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -m pytest tests/ -q
```

결과 (출력 원문 요약줄):

```
283 passed in 9.74s
```

| 항목 | 수 |
|---|---|
| passed | **283** |
| failed | 0 |
| errors | 0 |
| skipped | 0 |

- **실패 테스트: 없음** (전건 통과 — 그린 베이스라인 확정).
- **네트워크 필요 테스트의 실패: 0건.** 실패 자체가 없었으므로 네트워크 기인 실패도 없음. 전체 수행 시간 9.74초로, 실 네트워크 왕복에 의존하는 테스트가 베이스라인 통과를 좌우하지 않았음을 시사 (네트워크 의존 테스트의 존재 여부 자체는 개별 테스트 소스 전수 분석을 하지 않아 **확인 못함**).
- 테스트 트리: `tests/` 하위 `chart60`, `chartDay`, `etc`, `finance`, `investor`, `orchestration`, `upperLowerPrice` 디렉터리 + `__init__.py` (디렉터리 목록으로 확인).

## 2. pip freeze vs requirements.txt

- freeze 산출: `/tmp/aksj_engine_freeze.txt` (48줄 = 48개 패키지)
- requirements: `/Users/tajun/spJavis/kiwoom-rest-trader/requirements.txt` (32줄, 패키지 선언 19개)

### 2.1 버전 고정(`==`) 안 된 패키지 — requirements.txt 선언 19개 전부

requirements.txt에는 정확 고정(`==`)이 **하나도 없다.** 18개는 하한(`>=`)만, 1개(mplfinance)는 제약 자체가 없다.

| # | 패키지 | requirements 선언 (라인) | 실제 설치 버전 (freeze 라인) | 비고 |
|---|---|---|---|---|
| 1 | httpx | `>=0.27.0` (requirements.txt:2) | 0.28.1 (freeze:13) | |
| 2 | websockets | `>=12.0` (requirements.txt:3) | 16.0 (freeze:47) | 메이저 4단계 상회 |
| 3 | aiolimiter | `>=1.1.0` (requirements.txt:4) | 1.2.1 (freeze:1) | |
| 4 | python-dotenv | `>=1.0.0` (requirements.txt:7) | 1.2.2 (freeze:40) | |
| 5 | pydantic | `>=2.5.0` (requirements.txt:8) | 2.13.4 (freeze:31) | |
| 6 | pydantic-settings | `>=2.1.0` (requirements.txt:9) | 2.14.1 (freeze:32) | |
| 7 | pandas | `>=2.2.0` (requirements.txt:12) | **3.0.2** (freeze:25) | **메이저 점프 (2.x→3.x)** |
| 8 | numpy | `>=1.26.0` (requirements.txt:13) | **2.4.4** (freeze:22) | **메이저 점프 (1.x→2.x)** |
| 9 | ta | `>=0.11.0` (requirements.txt:16) | 0.11.0 (freeze:44) | 하한과 동일 |
| 10 | loguru | `>=0.7.2` (requirements.txt:19) | 0.7.3 (freeze:17) | |
| 11 | openpyxl | `>=3.1.2` (requirements.txt:22) | 3.1.5 (freeze:23) | |
| 12 | xlsxwriter | `>=3.2.0` (requirements.txt:23) | 3.2.9 (freeze:48) | |
| 13 | matplotlib | `>=3.8.0` (requirements.txt:24) | 3.10.9 (freeze:18) | |
| 14 | mplfinance | **(버전 제약 전무)** (requirements.txt:25) | 0.12.10b0 (freeze:19) | 유일한 무제약 + **베타(b0) 버전 설치됨** |
| 15 | plotly | `>=5.20.0` (requirements.txt:26) | **6.7.0** (freeze:29) | **메이저 점프 (5.x→6.x)** |
| 16 | pytest | `>=8.0.0` (requirements.txt:29) | **9.0.3** (freeze:37) | 메이저 점프 (8.x→9.x) |
| 17 | pytest-asyncio | `>=0.23.0` (requirements.txt:30) | **1.3.0** (freeze:38) | 0.x→1.x 점프 |
| 18 | black | `>=24.0.0` (requirements.txt:31) | 26.3.1 (freeze:4) | |
| 19 | ruff | `>=0.3.0` (requirements.txt:32) | 0.15.12 (freeze:42) | |

### 2.2 설치돼 있으나 requirements.txt에 없는 패키지 — 29개

freeze 48개 − requirements 선언 19개 = 29개. 대부분 위 19개의 전이(transitive) 의존성으로 추정되나, 전수 의존성 트리 검증은 하지 않았으므로 개별 귀속은 **확인 못함**. 단, 아래 1개는 주목:

- **pypdf==6.10.2** (freeze:36) — requirements.txt 선언 패키지들의 통상 의존성 목록에 보이지 않는 독립 패키지. 수동 설치로 추정되나 설치 경위는 **확인 못함**.

나머지 28개 (freeze 라인 순): annotated-types, anyio, certifi, click, contourpy, cycler, et_xmlfile, fonttools, h11, httpcore, idna, iniconfig, kiwisolver, mypy_extensions, narwhals, packaging, pathspec, pillow, platformdirs, pluggy, Pygments, pyparsing, pytokens, python-dateutil, six, typing-inspection, typing_extensions, (이상 freeze:2–46 사이) — 전형적 전이 의존성 패턴.

## 3. 베이스라인 판정

- **그린 베이스라인 성립**: 283/283 통과, 실패·에러·스킵 0. 이후 어떤 수정 작업이든 이 기준(283 passed) 대비 회귀 여부로 판정 가능.
- **재현성 리스크**: requirements.txt가 전부 하한 제약(또는 무제약)이라 `pip install -r requirements.txt` 재설치 시 현재 .venv와 동일 버전 재현이 보장되지 않음. 특히 pandas 3.x / numpy 2.x / plotly 6.x / websockets 16 / pytest 9 등 메이저 점프 상태에서 그린이므로, 베이스라인 동결이 필요하면 `/tmp/aksj_engine_freeze.txt`를 lock 파일 원본으로 보존할 것.

---
*기록자: Phase 0 워커 (과업 0-2a). 코드·requirements 수정 없음. 시크릿 미접촉.*
