# Phase 0 적대 검증 보고 (VERIFY)

- 검증일: 2026-06-13 (적대 검증관, 명령 재실행 기반)
- 대상: `/Users/tajun/spJavis/auto-korea-stock-javis/phase0/` 보고서 6건 + 요약 6건
- 방법: 핵심 주장을 실제 명령 재실행·코드 직독으로 표본 검증. 시크릿(.env) 미접촉.
- **총평: PASS_WITH_NOTES — 날조 없음. 핵심 수치·해시·커밋·코드 전부 실측 일치. 경미한 카운트 오차 3건(claude-isolation) + 교차과업 시점차 1건(param-sot 87→88) 발견.**

---

## ① 과업 0-4 파서 수선 — **검증 통과**

| 주장 | 재실행 결과 | 판정 |
|---|---|---|
| 전체 pytest 301 passed | `.venv/bin/python -m pytest tests/ -q` → **301 passed in 9.85s** | ✅ |
| 베이스라인 283 + 신규 18 | `--ignore=tests/test_stageMasterFilter_parse.py` → **283 passed** / 신규 파일 단독 → **18 passed** | ✅ |
| 커밋 a9a8f51, 2파일만, 248(+)/3(−) | `git show --stat a9a8f51` → `stageMasterFilter.py | 37 ++--` + `tests/test_stageMasterFilter_parse.py | 214 +` = **2 files changed, 248 insertions(+), 3 deletions(-)**. working tree clean(porcelain 0) | ✅ |
| push 안 함 | `git log origin/main..main` → a9a8f51 미push 확인 | ✅ |

### 코드 직독 판정 (신형/구형 처리)

- `src/kiwoom/itemFilter/stageMasterFilter.py:88-90` — `_NAME_CODE_RE = ^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$`. `src/kiwoom/itemFilter/Filter_condition_update.py:88`과 **문자 단위 동일 패턴** 확인.
- `stageMasterFilter.py:147-157` `_split_name_code` — `Filter_condition_update.py:95-101` `_parse_entry`와 동등 로직(strip → match → (nm, cd) / 미매치 시 (s, "")) 확인.
- `stageMasterFilter.py:160-167` `_read_name_list` — 각 줄 `_split_name_code(ln)[0]`로 순수 이름 정규화 확인.
- `stageMasterFilter.py:182-204` `_stock_dir` — 코드 있으면 `<이름>(<코드>)` 정확 일치 우선(196-198), 폴백은 접두 매칭(199-203). **커밋 diff로 수정 전 코드 확인: `startswith(name+"(") and endswith(")")`는 원래부터 존재** — "구형 경로 동작 보존" 주장 정확(변경은 `name`→`nm` 치환 + 정확일치 분기 추가뿐).
- 실데이터 포맷: `reports/20260518/masterReference.md` 1행 `영림원소프트랩`(구형), `reports/20260611/masterReference.md` 1행 `삼현철강(017480)`(신형) — 직접 확인.
- 스모크 재현: `read_master_reference`+`_stock_dir` 재실행 → **20260518 masters=10 resolved=10, 20260611 masters=3 resolved=3** — 보고서 수치와 정확 일치.
- TDD red 전제: `git show 359fb57:...stageMasterFilter.py | grep -c _split_name_code` → **0** — 수정 전 ImportError red는 필연(역사적 주장이나 전제 실증됨).

## ② 과업 0-6 백업 — **검증 통과 (해시·엔트리 전건 일치)**

| 항목 | 보고서 주장 | 재계산 | 판정 |
|---|---|---|---|
| reports tar 파일 엔트리 | 89,319 | `tar -tzf … \| grep -v '/$' \| wc -l` → **89,319** | ✅ |
| 원본 파일 수 | 89,319 | `find reports -type f \| wc -l` → **89,319** | ✅ |
| reports tar SHA-256 | `eacc70c4…f27753` | `shasum -a 256` → **완전 일치** | ✅ |
| state tar SHA-256 | `ec1774e0…c927c6e` | **완전 일치** (엔트리 1: `stageMasterFilter_state.json`) | ✅ |
| 원본 state json SHA-256 | `a2a5d197…5066bd6bb5` | **완전 일치** | ✅ |
| tar 크기 | 76,190,681 B / 1,309 B | `ls -l` 실측 동일 | ✅ |
| 부가 주장 표본 | 날짜 디렉토리 20개 · 20260514 `prefetchManifest.json` 부재 · stage md 5개 · 루트 파일 13개 · 20260522=11,890 · 20260608=560 · 20260611=9,504 · 총 381M | 전건 실측 일치 | ✅ |

## ③ 과업 0-2a/b 베이스라인 — **검증 통과**

### 0-2a engine (재실행)
- **283 passed**: 0-4 신규 테스트 파일 제외 재실행으로 재현(원 HEAD 359fb57 체크아웃은 비가역 회피 — `--ignore` 등가 검증). ✅
- pip freeze: `/tmp/aksj_engine_freeze.txt` 48줄 존재, 인용 라인 정확(25=pandas==3.0.2, 36=pypdf==6.10.2, 37=pytest==9.0.3, 47=websockets==16.0). 현재 .venv `pip freeze` 48개·핵심 8종 버전(pandas 3.0.2/numpy 2.4.4/plotly 6.7.0/pytest 9.0.3/pytest-asyncio 1.3.0/websockets 16.0/mplfinance 0.12.10b0/pypdf 6.10.2) 전부 일치. ✅
- requirements.txt: 32줄/비주석 19선언, `==` 매치 7건은 **전부 섹션 헤더 주석**(`requirements.txt:1,6,11,15,18,21,28` — `# === … ===`)으로 버전 고정 0건 주장 유지. 인용 라인 표본(2 httpx / 12 pandas / 13 numpy / 25 mplfinance 무제약 / 26 plotly) 정확. ✅

### 0-2b factory (보고서 일관성 + 인용 검증, 재실행 안 함 — 지시대로)
- 산술 일관: 64+55=119 수집 / 64+54=118 passed / 1 failed. ✅
- 실패 원인 인용 전건 실측: `kiwoom-rest-trader/CLAUDE.md` = **150줄**(`wc -l`), `prompt/.claude/tests/conftest.py:9` KRT_ROOT 기본값 = `/Users/tajun/spJavis/kiwoom-rest-trader`, `test_step_08_claude_md.py:8` `CLAUDE_MD = KRT_ROOT / "CLAUDE.md"`, `:17` `assert 80 <= len(lines) <= 130`. ✅

## ④ 날조·무근거 주장 스캔 (보고서 6건)

**날조 발견 0건.** 표본 추출한 인용(파일:라인)은 전부 실측과 일치했다. 발견된 경미한 결함:

### F-1. claude-isolation-design.md — 카운트 오차 3건 (off-by-one ×2 + 누락 2라인)
1. `claude-isolation-design.md:14` "engine .claude 총 **22**파일" — 자체 분해(추적 17 + pyc 3 + tgz 1)도 21이고 `find .claude -type f` 실측 **21**. 1개 과다. (추적 17·filter-tune 10·stock-scan 6은 `git ls-files` 실측 일치.)
2. `claude-isolation-design.md:28` "factory git 추적 **72**건(… skills **15** …)" — `git ls-files .claude` 실측 **73**(agents 16 + commands 10 + hooks 29 + 최상위 2 + **skills 16**). skills에서 `workflow-generator/references/state.yaml.example` 1건 누락 추정. (deny 19건·7이벤트 14훅커맨드는 실측 일치.)
3. 동 보고서 "pre-flight-checks.md 절대경로 5곳(31·49·53·68·87)" — `grep -n '/Users/tajun'` 실측 **7라인**(31·49·53·68·87·**109·121**). 109·121도 `/Users/tajun/spJavis/kiwoom-rest-trader` 리터럴 포함(경로 치환 대상 누락). path-inventory의 "7건"이 정확.

### F-2. param-sot.md — 측정 자체는 정확하나 0-4 커밋으로 **현재 HEAD에서 87→88 stale**
- 독립 AST 재집계: **359fb57 시점 stageMasterFilter=11, 총 87** — 보고서 모듈별 수치(FCU 6·chart240 5·chart60 7·chart60_120 26·chartDay 12·chartDayPre 4·finance 6·investor 10·stageMaster 11) 전건 일치. `AgenticWorkflow…/README.md:233`의 "87" 인용도 실재.
- 그러나 0-4 커밋 a9a8f51이 `_NAME_CODE_RE: Final[re.Pattern[str]]`(stageMasterFilter.py:88)을 **추가** → 현재 HEAD AST 재집계 **stageMaster=12, 총 88**. 오라클 재실행도 "Code: **88** Final constants (30 distinct numeric)… HARD 42 passed, 경고 1건(_EPS), exit 0" 출력. 수치 스코프(32선언/30 distinct, 비수치라 무영향)·HARD 42·_EPS 경고 주장은 현재도 유효.
- **조치 필요**: canonical L0=87은 "359fb57 기준"으로 명시하거나 88로 재기재(README:233의 87도 HEAD 기준 stale). 날조 아님 — 과업 실행 순서에 따른 시점차.
- 부수 주장 표본: `chartDayFilter.py.bak.20260601_211732` 라이브와 `diff` IDENTICAL ✅, itemFilter 직전 커밋 fa9f340 ✅.

### F-3. path-inventory.md — 표본 일치, 전수 총합은 미재현
- 표본 실측 일치: `scripts/_measure_ref.py:4` REPORTS 절대경로 ✅, `kiwoom-rest-trader/CLAUDE.md:7` KRT_ROOT 절대경로 ✅, `prompt/.claude/codegen/infra_schema.py:16-17` KRT_ROOT/AW_ROOT(15행은 주석 — 정정 주장 정확) ✅, `prompt/.claude/tests/conftest.py:9-10` ✅, pre-flight-checks.md 7히트 ✅. 내부 검산(256=13+240+3, 5,878−5,586=292=86+206)도 산술 정합.
- **확인 못함**: 총 히트 256/5,878 전수 재카운트는 미수행 — 본 검증 중 pytest 재실행 등으로 로그가 증식해 시점 동일 재현이 불가능(표본+검산 정합으로 갈음).

### F-4. 그 외 "확인 못함" 처리 항목 (날조 아님 — 재현 불가 역사 주장)
- 각 보고서의 실행 시각·수행 시간(9.74s/0.56s/0.15s 등): 당시 출력의 기록으로, 재실행 시간은 당연히 상이(301 suite 9.85s 등). 수치 구조가 전부 재현되므로 신뢰.
- 0-2b factory 스위트 64/55 수집 수: 지시에 따라 재실행 안 함 — 보고서 내부 일관성·인용 검증만.
- claude-isolation의 훅 기동 0.088s 실측, 중첩 발견 동작 관측: 세션 의존 실측 — 재현 안 함. 보고서 스스로 미실측 3건을 "확인 못함"으로 명시(날조 방지 규율 준수 양호).

---

## 종합 판정

| 과업 | 판정 |
|---|---|
| 0-4 파서 수선 | **PASS** — green(301)·커밋 범위(2파일)·코드 동등성·스모크 전건 재현 |
| 0-6 백업 | **PASS** — 엔트리 89,319 일치 + SHA-256 3건 완전 일치 |
| 0-2a engine 베이스라인 | **PASS** — 283 재현, freeze/requirements 인용 전건 정확 |
| 0-2b factory 베이스라인 | **PASS** — 내부 일관 + 실패 원인 인용 전건 실측 일치 |
| 날조 스캔 | **이상 없음** — 단 claude-isolation 카운트 오차 3건(21↔22, 72↔73/skills 15↔16, pre-flight 5↔7곳)과 param-sot 87→88 stale은 후속 정정 필요 |

**게이트 권고**: 0-4 push 승인 가능. 단 push 전후로 (a) param-sot canonical 수치를 88(또는 "359fb57 기준 87 + 0-4로 +1, 비수치") 로 주석 갱신, (b) claude-isolation 이주 체크리스트에 pre-flight-checks.md 109·121행 2곳 추가, (c) 동 보고서 카운트 2건 정정.
