# AKSJ 통합 사용자 매뉴얼 (auto-korea-stock-javis User Manual)

> **독자**: 주인님(운영자). 매일 아침 이 프로젝트를 *사용*하는 데 필요한 모든 것을 한 문서에 담았다.
> **출처 원칙**: 모든 값·명령·표는 `engine/CLAUDE.md` · `engine/docs/user_command_manual.md` · 루트 `CLAUDE.md` · `factory/docs/integrated-user-command-manual.md`에서 값-동등 인용했다. 문서끼리 어긋나는 값(소요 시간·임계값)은 **코드 `Final` 상수와 실측치를 우선**해 표기했고, 그 지점마다 각주로 밝혔다.

---

## ① 한 장 요약 — 이 프로젝트가 무엇인가

**auto-korea-stock-javis(AKSJ)**는 한국주식 종목 스크리너 모노레포다. 한 지붕 아래 두 구역이 있다:

| 구역 | 경로 | 정체 | 주인님이 쓰는 빈도 |
|---|---|---|---|
| **engine** | `/Users/tajun/spJavis/auto-korea-stock-javis/engine` | **일일 스크리너 (제품)** — 키움 REST API로 종목을 수집하고 5-Stage 필터로 선별. 매일 아침 돌리는 것이 이것. | 매일 |
| **factory** | `/Users/tajun/spJavis/auto-korea-stock-javis/factory` | **동결 공장** — engine을 *만든* 빌드 시스템(AgenticWorkflow). `factory/prompt/`는 빌드 비행기록으로 **읽기 전용 동결**. | 거의 없음 |

- **무엇을 하는가**: 매 영업일, ① 상·하한가/등락률 종목 + ② 조건검색식 9개 결과를 수집·통합하고, 종목마다 6개 API 데이터(분봉·일봉 차트, 수급, 재무)를 내려받은 뒤(Stage 0 prefetch), **Stage 1~5 기술적 필터**(분봉 정배열 → 장기추세 → 급등 배제 → 일봉 밴드 → 수급 → 흑자)를 통과한 종목만 `researchedCompany.md`에 남긴다.
- **두 구역의 관계 (일방향 문)**: 일상의 모든 발화(스캔·튜닝·조회·비교)는 **engine 구역**이다. factory 진입 조건은 단 하나 — 주인님의 명시 발화 **"공장 빌드 모드"** — 이며, 그 외 어떤 분기로도 진입하지 않는다. (루트 `CLAUDE.md` §2)
- **결과물의 성격**: "기술적 완성도가 높은 종목"의 선별이지 매수 추천이 아니다. ⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.

---

## ② 매일 아침 운영

### 방법 1 — Claude Code 자연어 (권장)

```
cd /Users/tajun/spJavis/auto-korea-stock-javis && claude
```

세션이 열리면 한 마디:

> **"오늘 스캔해줘"**

이것으로 끝. Claude가 백그라운드로 풀플로우(`run_full_research_flow`)를 돌리고, 완료되면 Stage별 통과 현황을 한국어로 보고한다.

> 참고(루트 `CLAUDE.md` §5·§6): 가장 깨끗한 일일 운영 환경은 `cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && claude` — 훅 0건, 스킬 2개(stock-scan·filter-tune)만 노출된다. 루트에서 열어도 라우터가 모든 사용 발화를 engine으로 보낸다.

### 방법 2 — 직접 명령 복붙판 (Claude 없이)

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m scripts.run_full_research_flow $(date +%Y%m%d)
```

- 특정 날짜는 `$(date +%Y%m%d)` 자리에 `YYYYMMDD`(예: `20260613`)를 직접 넣는다. 날짜 생략 시 오늘 기준.
- `source .venv/bin/activate && python …` 형태는 **금지** — `.venv/bin/python` 직접 호출만 허용한다. (루트 `CLAUDE.md` §3)

### 소요 시간 — 반드시 알아둘 것

| 모듈 | 실행 방식 | 소요 (실측) |
|---|---|---|
| `run_full_research_flow` · `run_prefetch` | **background 필수** (Bash 600초 cap 초과) | **80분 ~ 6시간** (데이터량·시간대 따라 변동) |
| `run_filters` · 개별 필터 모듈 | 동기(foreground) 가능 | < 3분 |

- Claude Code 세션에서는 `Bash(run_in_background:true)`로 돌고, **7시간 watchdog**(실측 최대 6시간 + 여유 1시간)이 걸린다 — 7시간 무완료 시 이상으로 판정하고 SCAN_SEPARATED 재시도를 제안한다. (engine `CLAUDE.md` Execution Template)
- 터미널에서 직접 돌릴 때도 같은 이유로 자리를 비워도 되는 환경(절전 꺼짐 등)에서 실행한다.
- ⚠️ engine 문서 곳곳의 "10-15분" 표기는 **진부(stale)** — 신뢰 금지. 실측 80분~6시간이 기준이다. (루트 `CLAUDE.md` §3)

### 종료 코드 (직접 실행 시)

`0` 정상 / `1` 입력 부재·진행 불가(수집 0건 등) / `2` 기타 예외. (engine `docs/user_command_manual.md`)

---

## ③ 14 Intent 표 — Claude 세션에서 쓸 수 있는 말

engine/CLAUDE.md의 Intent Routing 표 **원문 그대로** (요약 아님):

| Cluster | 한국어 발화 예시 (≥2) | Skill | Action |
|---|---|---|---|
| SCAN_TODAY    | "오늘 종목 스캔해줘" / "오늘 돌려줘" / "오늘 스캔 돌려줘" / "{YYYYMMDD} 스캔" | stock-scan | scan_today(date=오늘 또는 인자) — **default = run_full_research_flow ; run_in_background:true** (ADR-012) |
| SCAN_SEPARATED | "나눠서 해줘" / "단계별로 해줘" / "분리해서 실행" | stock-scan | scan_separated(date) — Chain 2. prefetch(데이터 수집)만 실행, 필터 미실행(`run_filters` 미호출) (B-11) |
| SCAN_RANGE    | "이번 주 월~금 전부 수집해줘" / "{start}부터 {end}까지 스캔" / "지난 한 주 다 돌려줘" | stock-scan | scan_range(start, end) — 영업일 루프, 각 날짜에 SCAN_TODAY 적용 (B-24) |
| SHOW_RESULTS  | "오늘 결과 보여줘" / "통과 종목 알려줘" / "최종 선별 목록" | stock-scan | show_results(date) — Read `researchedCompany.md` + stage*_passed.md 종합 |
| WHY_REJECTED  | "삼성전자가 왜 빠졌어?" / "OO전자 탈락 이유" / "왜 떨어졌어?" | stock-scan | why_rejected(stock_name, date) — masterReference 체인 (B-5) |
| SHOW_PARAMS   | "Stage 1 조건 보여줘" / "전체 필터 설정 요약" / "지금 파라미터 뭐야?" | filter-tune | show_params(stage 또는 'all') — Read Final 상수 + 한국어 의미 테이블 |
| CHANGE_PARAM  | "Type A 허용오차 -5%로 완화해줘" / "외국인 매도 조건 좀 강화해줘" | filter-tune | change_param(param_id, new_value) — Master Sequence 8-step (B-22) |
| RERUN_FILTERS | "필터만 다시 돌려줘" / "데이터는 그대로 두고 필터만" / "필터 재실행" | stock-scan | rerun_filters(date) — `run_filters` 동기 실행, prefetchManifest 검증 선행 |
| RESTORE       | "원래대로 되돌려줘" / "이전 값으로 복원" / "백업으로 돌려놔" | filter-tune | restore(file?, ts?) — `*.bak.*` 최신본 복원 (TS-2) |
| COMPARE       | "어제랑 오늘 비교해줘" / "{date_a}와 {date_b} 차이" | stock-scan | compare(date_a, date_b) — researchedCompany.md diff + tuning-log 인용 (Chain 6) |
| COMPARE_PARAMS | "변경 전후 비교" / "이전 설정과 지금 차이" | stock-scan | compare_params(before, after) — tuning-log 8-column 행 diff (Chain 7). 실험-set 비교 (`"이 세션 튜닝 실험 비교"`)는 filter-tune COMPARE_EXPERIMENTS branch가 담당 — 발화에 **명시적 실험 마커**(`"실험"`/`"튜닝 실험"`)가 있을 때만 filter-tune으로 직행. 결과 마커(날짜 토큰·`"결과"`/`"통과 종목"`/`"전후"`)가 있으면 COMPARE_PARAMS. **둘 다 없는 모호 발화**(예: "이번 세션 비교해줘" — `"세션"` 단독으로는 silent 라우팅 금지)는 1회 한정 AskUserQuestion("결과 비교" vs "튜닝 실험 비교") 후 분기 (PRD P4) |
| THEORY_GUIDE  | "약세장에서는 어떻게 바꿔야 해?" / "정배열 이론적 근거" / "Minervini 기준" | filter-tune | theory_guide(topic) — FR-7 이론 매핑 (Minervini/Weinstein/Wyckoff/VCP/CANSLIM) |
| CONFIRM       | "이걸로 확정할게" / "현재 설정 유지" / "지금 게 제일 나아" | filter-tune | confirm() — tuning-log 마지막 행 "✓ 확정", screener_state.last_param_changes[*].confirmed=true (FR-6.5) |
| ASK_MODULE    | "stageMasterFilter는 뭐야?" / "다른 필터도 있어?" / "chart60Filter 역할" | filter-tune | ask_module(module_name) — Branch 6 (PRD §6.4 보조 모듈 설명 + "Phase 1 튜닝 대상 외" 안내 + Stage 5 financeFilter Phase 2 deflection) |

**같이 알아둘 두 규칙** (engine `CLAUDE.md`):

- **혼합 발화**: "필터 바꾸고 다시 돌려줘" → ① CHANGE_PARAM 완료 → ② 사용자 확인 후 RERUN_FILTERS. 한 번에 합쳐 실행하지 않는다.
- **모호하면**: 최대 1회 한국어 선택지 질문(3-4개). 모호함 없으면 질문 없이 진행.
- 그냥 **"시작"**이라고만 해도 된다 — Onboarding(환경 점검 + 지난 스캔 요약 + 모드 메뉴)으로 진입한다.

---

## ④ 결과 읽는 법

스캔 산출물은 전부 `engine/reports/YYYYMMDD/` 아래에 쌓인다.

### 4-1. 최종 결과 = `researchedCompany.md`

Stage 1~5를 **전부** 통과한 종목의 최종 집계 파일. "오늘 결과 보여줘"(SHOW_RESULTS)가 읽는 canonical 파일이 이것이다.

### 4-2. Stage 깔때기 — 어디서 얼마나 걸러졌나

종목은 아래 순서로 평가되며, **한 Stage라도 탈락하면 즉시 break**(이후 Stage 미평가):

| 순서 | Stage / 모듈 | 기준 (코드 `Final` 상수 기준) | 통과 파일 |
|---|---|---|---|
| 1 | chart60_120Filter | 60·120분 MA 4선 정배열 / Type A~E 매칭 | `stage1_chart60_120_passed.md` |
| 2 | chart240Filter | 최근 3봉 MA60 ↔ MA306 정배열 | `stage2_chart240_passed.md` |
| 2-1 | chartDayPreFilter | 금일 일봉 **+15% 이상 급상승 → 제외** (`_DAILY_SURGE_THRESHOLD=0.15`)¹ | `stage2_1_chartDayPre_passed.md` |
| 3 | chartDayFilter | 일봉 MA612 **밴드 [-15%, +50%]**(`_CLOSE_VS_MA612_LOWER/_UPPER=-0.15/0.50`)¹ · 양봉 · 정배열 | `stage3_chartDay_passed.md` |
| 4 | investorFilter | 외국인·기관 연속매도 / 개인 연속매수 등 수급 | `stage4_investor_passed.md` |
| 5 | financeFilter | 당기순이익 < 0 (적자) → 제외 | `stage5_finance_passed.md` |

> ¹ engine `docs/user_command_manual.md` 순서도의 "+10%" · "[-10%,+20%]" 표기는 코드와 어긋난 진부 값 — **코드 실측**(`chartDayPreFilter.py:51`, `chartDayFilter.py:68-69`)이 우선이다. (factory 통합 매뉴얼 §3.2 정오 노트와 일치)

각 `stage*_passed.md`의 줄 수를 차례로 보면 "82개 → 45개 → …" 식의 **탈락 깔때기**가 보인다. SHOW_RESULTS가 이 단계별 탈락률 표를 자동으로 만들어 준다.

그 앞단 수집 산출물: `upperLowerPrice.md`(상하한가) → `conditionResearch.md`(조건검색 9개식) → `organizedCompany.md`(통합·중복제거 — 이 종목들이 깔때기의 입구 N) → 종목별 폴더 `<종목명(코드)>/`에 6개 데이터 .md + `prefetchManifest.json`(종목별 수집 상태 ok/empty/error).

### 4-3. masterReference 수기 기입법 — "왜 빠졌는지" 추적

탈락 사유 분석의 입력 파일은 `reports/YYYYMMDD/masterReference.md`다.

1. **생성**: 스캔의 ③ organizedCompany 단계에서 빈 파일(0바이트)로 자동 생성된다.
2. **기입**: 궁금한 종목명을 **한 줄에 하나씩** 주인님이 직접 적는다. 예:
   ```
   삼성전자
   현대해상
   ```
3. **분석 실행**: 다음 중 하나 —
   - Claude에게 "삼성전자가 왜 빠졌어?" (WHY_REJECTED — 종목명 추가 기입과 분석 실행을 Claude가 대신함)
   - 직접: `cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m src.kiwoom.itemFilter.Filter_condition_update YYYYMMDD` (여러 날짜는 공백 구분, 콤마 불가)
   - 풀플로우(방식 A)를 돌리면 마지막 C 단계에서 자동 실행 (파일이 비어 있으면 무해한 no-op)
4. **결과 읽기**: `masterReference.log`에 종목별로 "어느 Stage의 어떤 조건에 걸렸는지"가 **append**(누적, 덮어쓰기 없음)로 기록된다. 섹션 끝의 기록 날짜-시간으로 최신 블록을 구분한다.

> **이제 재스캔에도 보존된다**: 과거에는 재스캔 때마다 `masterReference.md`가 0바이트로 덮어써져 수기 기입이 소실되는 함정이 있었으나, Phase 1-5 수선으로 **파일이 없을 때만 빈 파일을 생성하고 기존 파일(수기 기입 포함)은 절대 덮어쓰지 않는다**. (engine `plain_text.py` 수정 + 전체 305 테스트 green — `phase2`의 근거 문서 및 `phase1/fix-1-5-overwrite.md` 참조)

### 4-4. 결과 화면의 표기 약속

- 한국식 숫자: `4,805원` · `-3.5%` · `15/350개` · `82개 → 45개`.
- "필터 조건을 충족한 종목"이지 "매수 추천"이 아니다 — 세션 첫 결과에 풀버전 면책 1회, 이후 1줄 축약.

---

## ⑤ 튜닝 루프 — 데이터는 한 번, 필터는 N번

필터 파라미터를 실험할 때 매번 풀스캔(80분~6시간)을 돌리는 것은 낭비다. **수집과 필터를 분리**한다:

```
1회:  run_prefetch YYYYMMDD     ← 수집 + Stage 0 prefetch (background 필수, 실측 80분~6시간, 실 API 호출)
N회:  run_filters  YYYYMMDD     ← Stage 1~5 순수 필터 재평가 (<3분, API 호출 0회 — 디스크 캐시만)
```

복붙판:

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m scripts.run_prefetch $(date +%Y%m%d)
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m scripts.run_filters $(date +%Y%m%d)
```

Claude 세션 루프 (factory 통합 매뉴얼 §4.2 daily-ops 루프):

1. "나눠서 해줘" (SCAN_SEPARATED) — prefetch만.
2. "Stage 1 조건 보여줘" (SHOW_PARAMS) — 현재 `Final` 상수 가시화.
3. "Type A 허용오차 -5%로 완화해줘" (CHANGE_PARAM) — 8-step Master Sequence: 범위 검증 → 영향 예측 → 확인 질문 → **자동 백업**(`*.bak.타임스탬프`, 최근 5개 유지) → `Final` 상수만 Edit → tuning-log 기록.
4. "필터만 다시 돌려줘" (RERUN_FILTERS) — before/after 비교 표.
5. 마음에 들 때까지 3-4 반복. 되돌리려면 "원래대로 복원" (RESTORE).
6. "이걸로 확정할게" (CONFIRM) — tuning-log에 "✓ 확정".

안전 규칙 (TS-1~5, non-negotiable 요지): `Final` 상수 **값만** 변경(로직 코드 불변, Stage 5는 상수가 없어 Phase 1 튜닝 불가) · 변경 전 자동 백업 · 범위 검증 · 한 번에 한 파라미터 · 변경 후 재필터 제안. 실험 이력은 `engine/reports/tuning-log.md`(8-column)에 쌓인다.

---

## ⑥ 트러블슈팅

### 에러 9종 표 (engine `CLAUDE.md` Error Classification 인용)

| `type(exc).__name__` | 한국어 요약 | 원인 | 사용자 행동 |
|---|---|---|---|
| `KiwoomAuthError`       | 키움 인증에 실패했습니다.                | 키움 인증 토큰 발급 또는 검증이 실패했습니다 (기술명: OAuth)  | 키움 API 인증 설정(키/시크릿)을 확인하고, 잠시 후 다시 시도해주세요. |
| `KiwoomApiError`        | 키움 데이터 조회에 실패했습니다.         | REST API 호출 실패 (HTTP, JSON, return_code≠0, 재시도 초과). **8개 모듈 독립 정의 — 이름 기준 분기 필수.** | 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요. |
| `KiwoomConditionError`  | 조건검색 서버 응답에 실패했습니다.       | WebSocket LOGIN/transport/return_code≠0/MISSING/SHAPE        | 설정한 조건명이 키움 HTS에 저장되어 있는지 확인해주세요. |
| `OrganizeError`         | 수집된 종목 데이터가 없습니다.           | conditionResearch.md·upperLowerPrice.md 두 입력 모두 부재    | 조건검색·상하한가 수집을 먼저 실행해주세요. |
| `ResearchError`         | 필터링에 필요한 데이터 파일이 없습니다.  | organizedCompany.md 또는 prefetchManifest.json 부재         | 먼저 데이터 수집을 실행해주세요. |
| `PrefetchError`         | 종목 사전 수집을 시작할 데이터가 없습니다. | Stage 0 prefetch 진입 전 organizedCompany.md 부재          | 조건검색·상하한가 단계를 먼저 완료해주세요. |
| `FileNotFoundError`     | 필요한 데이터 파일을 찾을 수 없습니다.   | 보고서 폴더·종목 폴더·chart/finance/investor.md 부재         | 먼저 해당 단계의 데이터 수집을 실행해주세요. |
| `ValueError`            | 데이터 형식이 올바르지 않습니다.         | 시계열 표 파싱 실패, 잘못된 인자                            | 수집된 데이터가 손상되었을 수 있으니 다시 수집해보세요. |
| `Exception` (generic)   | 예기치 못한 오류가 발생했습니다.         | 분류되지 않은 모든 예외                                     | 잠시 후 다시 시도하거나 로그를 확인해주세요. |

종료 코드 1차 분류: `1` = 도메인 입력 부재(OrganizeError/ResearchError/PrefetchError), `2` = 그 외 모든 예외.

### 증상 → 어디를 보라 (factory 통합 매뉴얼 §3.9 인용, 시간 기준만 실측으로 정정²)

| 증상 | 원인 후보 | 대처 |
|---|---|---|
| 스캔이 오래 안 끝남 | 정상 범위가 실측 80분~6시간² — **7시간** 초과 시 이상 | watchdog 판정 → SCAN_SEPARATED 재시도 제안 |
| `exit 1` + 통과 0 | `OrganizeError`/`PrefetchError` (수집 0건) | 수집 단계 먼저 실행 |
| 결과 파일이 생성되지 않음 | 파이프라인 중간 종료 | stderr 마지막 줄 확인 |
| "파라미터 변경 중…스캔 불가" | `filter-tune.lock` 잔류 | 변경 완료 대기 / stale lock 수동 `rmdir` |
| 결과가 어제와 같음 (재스캔 안 됨) | cache-hit | "다시 실행" 선택 |

> ² 원문(factory §3.9)은 "30분 넘게 안 끝남 → watchdog"이었으나, 30분 watchdog은 실측(80분~6시간)과 어긋나 비현실 — 루트 `CLAUDE.md` §3과 engine `CLAUDE.md`의 **7시간 watchdog** 기준으로 정정 인용.

추가 팁:
- ① upperLowerPrice·② conditionResearch 단계의 예외는 **격리**되어 다음 단계로 계속 진행한다 — 한쪽 수집이 죽어도 전체가 멈추지 않는다.
- 특정 종목만 데이터 일부 실패 시 `prefetchManifest.json`에 `error`로 기록되고 해당 Stage에서 자동 탈락한다.
- C(탈락분석) 단계 실패는 격리 — 풀플로우 종료 코드에 영향 없음.

---

## ⑦ 시크릿 규칙 (루트 `CLAUDE.md` §4)

- API 키·시크릿은 **`engine/.env` 한 곳에만** 둔다 (권한 0600).
- `*.example` 파일(`engine/.env.example` 등)에는 **실제 값 기입 금지** — 플레이스홀더만.
- `.env`의 값을 cat·echo·로그·보고서·커밋 **어디에도 노출하지 않는다**.
- 인증 실패(`KiwoomAuthError`) 시에도 키 값을 화면에 띄워 확인하지 말고, `.env` 파일을 에디터로 직접 열어 점검한다.

---

*문서 충돌 시 우선순위: 경로 = 루트 `CLAUDE.md` §1 → 운영 상세 = 각 구역 CLAUDE.md → 본 매뉴얼은 위 출처들의 값-동등 통합본이며, 본 매뉴얼과 코드/실측이 어긋나면 코드/실측이 우선한다.*
