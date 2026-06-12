# 사용자 명령어 설명서 (User Command Manual)

kiwoom-rest-trader 에서 `python -m ...` 로 실행 가능한 명령들을 용도별로 정리한다.
모든 명령은 프로젝트 루트(`/Users/tajun/spJavis/kiwoom-rest-trader`)에서,
가상환경(`source .venv/bin/activate`) 활성화 후 실행한다.

명령의 `YYYYMMDD` 부분은 실제 날짜(예: 20260516)로 바꿔서 실행한다. 날짜를
빼고 실행하면 "오늘" 기준으로 동작한다(별도 명시 제외).

공통 종료 코드: `0` 정상 / `1` 입력 부재·진행 불가 / `2` 기타 예외.

각 항목의 코드 블록은 그대로 복사해 프롬프트에 붙여넣을 수 있도록 명령만
담았다.

---

## A. 통합 풀플로우 (수집 + 필터 한 번에) — "방식 A"

```
python -m scripts.run_full_research_flow YYYYMMDD
```

① upperLowerPrice → ② conditionResearch → ③ organizedCompany 수집 +
Stage 0 prefetch(종목별 6 API) + **Stage 1~5 필터** + 결과 저장 +
**C. masterReference 탈락사유 분석**(`masterReference.log` append)까지
전부 1회 실행한다.

가장 단순한 전체 실행 경로. Kiwoom 실 API 를 호출하며 종목 수에 따라 십수 분
소요된다. Stage 1~5 종료 후 `researchedCompany.md` 작성이 끝나면 자동으로
C 단계(`Filter_condition_update`)가 이어 실행된다 — `masterReference.md` 가
비어 있으면 C 는 내부에서 즉시 no-op 종료하므로 안전하다. C 단계 실패는
격리되어 풀플로우 전체를 멈추지 않는다.

---

## B. 수집·필터 분리 워크플로우 (필터 N회 튜닝용) — "방식 B"

수집(1회):

```
python -m scripts.run_prefetch YYYYMMDD
```

①②③ + Stage 0 prefetch (chart60·chart120·chart240·chartDay·investor·finance
6 API 수집) + `prefetchManifest.json` 저장. **필터는 수행하지 않음.**
Kiwoom 실 API 호출.

필터(N회):

```
python -m scripts.run_filters YYYYMMDD
```

prefetch 산출물(.md + manifest)만 읽어 **Stage 1~5 순수 필터** 평가.
**API 호출 0회.** `researchedCompany.md` + `stage*_passed.md` 저장.
prefetch 선행 필수.

필터 룰을 수정하며 반복 평가할 때, `run_prefetch` 1회 → `run_filters` N회 로
API 재호출 없이 빠르게 돌릴 수 있다.

---

## C. masterReference 탈락사유 분석

```
python -m src.kiwoom.itemFilter.Filter_condition_update YYYYMMDD
```

여러 날짜를 **공백 구분**으로 넘기면 순차 실행한다(콤마 구분은 셸이 한 인자로
처리하므로 동작하지 않음). 각 일자 사이에 `--- [N/M] date=... ---` 헤더가 출력된다.

```
python -m src.kiwoom.itemFilter.Filter_condition_update 20260518 20260519 20260520 20260521 20260522
```

다중 일자 실행 시 최종 종료 코드는 일자별 코드 중 가장 큰 값(모두 정상이면 0).

마지막 Stage 까지 끝나고 `researchedCompany.md` 작성 완료 후 실행한다.
`reports/<YYYYMMDD>/masterReference.md` 에 종목이 없으면 아무것도 하지 않고
종료한다. 종목이 있으면 **종목 단위**로, 각 Stage 통과 결과 파일에 그 종목이
없을 때 해당 Stage 필터를 재평가하여 "어떤 조건에 의해 제외되었는지" 사유를
`masterReference.log` 에 기록한다. 종목 섹션 마지막 라인에 기록 날짜-시간을
남기며, 재실행 대비 **append**(덮어쓰기 금지)한다.

`masterReference.md` 는 `run_organize_company` / 풀플로우의 ③ 단계에서 빈
파일(0바이트)로 자동 생성되며, 분석 대상 종목명을 한 줄에 하나씩 사용자가
직접 채워 넣는다.

---

## D. 개별 필터 모듈 단독 실행 (디버그용)

각 필터를 단독으로 돌려 결과 `.md` 를 확인할 때 사용한다(모두 `__main__`
진입점 보유). 필요한 한 줄만 복사해 사용한다.

```
python -m src.kiwoom.itemFilter.chart60_120Filter
```

```
python -m src.kiwoom.itemFilter.chart240Filter
```

```
python -m src.kiwoom.itemFilter.chartDayPreFilter
```

```
python -m src.kiwoom.itemFilter.chartDayFilter
```

```
python -m src.kiwoom.itemFilter.investorFilter
```

```
python -m src.kiwoom.itemFilter.financeFilter
```

```
python -m src.kiwoom.itemFilter.chart60Filter
```

마지막 `chart60Filter` 는 chart60 단독 필터로, `chart60_120Filter` 의
구성요소다.

---

## 표준 사용 순서 요약

- **전체를 한 번에**: A — `run_full_research_flow`
- **필터 룰 반복 튜닝**: B — `run_prefetch` 1회 → `run_filters` N회
- **그 후 탈락 원인 추적**: C — `Filter_condition_update`

### A. 통합 풀플로우 실행 순서도 (process & 산출물)

`python -m scripts.run_full_research_flow YYYYMMDD` 한 번으로 아래 단계가
위→아래로 순차 실행된다. 각 단계의 **입력 / 처리 / 판정기준 / 산출물 / 분기**를
도식화했다. 모든 산출물 경로의 접두사는 `reports/YYYYMMDD/` 이며 도식에서는
파일명만 표기한다.

기호 범례:

```
   ▼      정상 진행 (다음 단계로)
   ╳▶     실패/예외 분기 (격리 또는 종료)
   ◇      조건 분기 (예/아니오 판정)
   ║ … ║  종목별 루프 구간
   ├PASS▶ 해당 Stage 통과 종목 누적
   └DROP▶ 해당 Stage 탈락 → 그 종목 break (이후 Stage 미평가)
```

#### 1단계: 수집 (① → ② → ③)

```
╔══════════════════════════════════════════════════════════════════════════╗
║  $ python -m scripts.run_full_research_flow YYYYMMDD                      ║
║       └ YYYYMMDD 생략 시 = 오늘                                           ║
╚════════════════════════════════════╦═════════════════════════════════════╝
                                     ▼
┌──────────────────────────── ① upperLowerPrice ──────────────────────────┐
│ 입력 : Kiwoom REST  ka10017  (등락률·상한/하한가 목록)                   │
│ 처리 : 전 종목 페이지네이션 수집 → ETF · ETN · 스팩 클라이언트 필터링    │
│ 산출 : 📄 upperLowerPrice.md                                             │
└────────────────┬───────────────────────────────────┬─────────────────────┘
        정상 ▼                                예외 ╳▶ 로그 기록 후 격리
                 │                                    └▶ (멈추지 않고 ② 진행)
                 ▼
┌──────────────────────────── ② conditionResearch ────────────────────────┐
│ 입력 : 조건검색식 9개  (ka10171 목록 / ka10172 검색, WebSocket)          │
│ 처리 : 9개 식 결과를 순차 실행·누적 → 종목명 기준 중복 제거              │
│ 산출 : 📄 conditionResearch.md                                           │
└────────────────┬───────────────────────────────────┬─────────────────────┘
        정상 ▼                                예외 ╳▶ 로그 기록 후 격리
                 │                                    └▶ (멈추지 않고 ③ 진행)
                 ▼
┌──────────────────────────── ③ organizedCompany ─────────────────────────┐
│ 입력 : 📄 upperLowerPrice.md  +  📄 conditionResearch.md                 │
│ 처리 : 파싱 → 종목명 통합·중복제거 → 등락률 내림차순 정렬               │
│        (동일 종목은 upperLower 출처가 conditionRes 를 덮어씀)            │
│ 산출 : 📄 organizedCompany.md          (종목명 1줄 1종목)               │
│        📄 masterReference.md           ← 빈 파일(0 byte) 자동 생성       │
└────────────────┬───────────────────────────────────┬─────────────────────┘
                 │ ◇ 종목 ≥ 1건                       ◇ 0건 / OrganizeError
                 ▼                                    ╳▶ Stage 0·1~5·C 전부
                 │                                       SKIP → 종료 코드 1
                 ▼
       (다음: 2단계 Stage 0 prefetch)
```

#### 2단계: 종목별 데이터 수집 (Stage 0 · prefetch)

```
┌──────────────────────────── Stage 0 · prefetch ─────────────────────────┐
│ 입력 : 📄 organizedCompany.md 의 전 종목                                 │
│ 처리 : 종목마다 6 API 호출·저장                                          │
│        · API 간 0.3s, 종목 간 0.5s 페이싱                                │
│        · rate-limit(1700) / 토큰만료(8005) 자동 재시도                   │
│                                                                          │
│   ║ for 종목 in organizedCompany:                                       ║│
│   ║   ┌─ chart60  ─┐ ┌─ chart120 ─┐ ┌─ chart240 ─┐                     ║│
│   ║   ├─ chartDay ─┤ ├─ investor ─┤ ├─ finance  ─┤                     ║│
│   ║   └────────────┴───── 6개 .md 저장 ───────────┘                     ║│
│   ║   상태 기록: ok / empty / error  →  prefetchManifest.json           ║│
│                                                                          │
│ 산출 : 📂 <종목명(코드)>/                                                │
│           ├ 📄 chart60.md   ├ 📄 chart120.md  ├ 📄 chart240.md          │
│           ├ 📄 chartDay.md  ├ 📄 investor.md  └ 📄 finance.md           │
│        📄 prefetchManifest.json   (종목별 6 API 상태표)                  │
└────────────────┬───────────────────────────────────┬─────────────────────┘
        정상 ▼                                ◇ PrefetchError
                 │                              ╳▶ Stage 1~5·C SKIP
                 ▼                                 → 종료 코드 1
       (다음: 3단계 Stage 1~5 filter)
```

#### 3단계: 필터 (Stage 1 → 2 → 2-1 → 3 → 4 → 5)  ※ API 0회

> manifest + 디스크 .md 만 사용. 종목별 루프로 Stage 1→5 를 **순서대로**
> 평가하며, 한 Stage 라도 탈락(또는 manifest 상태 ≠ ok)이면 그 종목은
> 즉시 `break` 하여 이후 Stage 를 평가하지 않는다.

```
            ┌───────────────────────────────────────────────┐
            │  ║ for 종목 in organizedCompany (입력 N 종목)  ║│
            └───────────────────────┬───────────────────────┘
                                    ▼
   ┌───────────────────── Stage 1 · chart60_120Filter ──────────────────┐
   │ 입력 : 📄 chart60.md + 📄 chart120.md                              │
   │ 기준 : 60·120분 MA 4선 정배열 / Type A~E (수렴·지지·엉킴) 매칭     │
   └───────────────┬───────────────────────────────┬────────────────────┘
        ◇ 매칭 PASS │                               │ DROP / 데이터≠ok
   ├PASS▶ 📄 stage1_chart60_120_passed.md           └DROP▶ break(종목 종료)
                    ▼
   ┌───────────────────── Stage 2 · chart240Filter ─────────────────────┐
   │ 입력 : 📄 chart240.md                                              │
   │ 기준 : 장기추세 — 최근 3봉 MA60 ↔ MA306 정배열 검증                │
   └───────────────┬───────────────────────────────┬────────────────────┘
            ◇ PASS │                               │ DROP / 데이터≠ok
   ├PASS▶ 📄 stage2_chart240_passed.md              └DROP▶ break
                    ▼
   ┌───────────────────── Stage 2-1 · chartDayPreFilter ────────────────┐
   │ 입력 : 📄 chartDay.md                                              │
   │ 기준 : 금일 일봉 +10% 이상 급상승 → 사전 차단(제외)               │
   └───────────────┬───────────────────────────────┬────────────────────┘
            ◇ PASS │                               │ DROP(+10%↑)
   ├PASS▶ 📄 stage2_1_chartDayPre_passed.md         └DROP▶ break
                    ▼
   ┌───────────────────── Stage 3 · chartDayFilter ─────────────────────┐
   │ 입력 : 📄 chartDay.md                                              │
   │ 기준 : 일봉 MA612 밴드[-10%,+20%] & 양봉 & 최근 3봉 정배열         │
   └───────────────┬───────────────────────────────┬────────────────────┘
            ◇ PASS │                               │ DROP(밴드/양봉 실패)
   ├PASS▶ 📄 stage3_chartDay_passed.md              └DROP▶ break
                    ▼
   ┌───────────────────── Stage 4 · investorFilter ─────────────────────┐
   │ 입력 : 📄 investor.md                                              │
   │ 기준 : 외국인·기관 연속매도 / 개인 연속매수 등 수급 조건           │
   └───────────────┬───────────────────────────────┬────────────────────┘
            ◇ PASS │                               │ DROP(수급 불충족)
   ├PASS▶ 📄 stage4_investor_passed.md              └DROP▶ break
                    ▼
   ┌───────────────────── Stage 5 · financeFilter ──────────────────────┐
   │ 입력 : 📄 finance.md                                               │
   │ 기준 : 당기순이익 < 0 (적자) → 제외                                │
   └───────────────┬───────────────────────────────┬────────────────────┘
            ◇ PASS │                               │ DROP(적자)
   ├PASS▶ 📄 stage5_finance_passed.md               └DROP▶ break
                    ▼
        ◇ Stage 1~5 전부 통과 (final_selected = True)
                    ▼
            ║ 다음 종목으로 루프 ║ ── (N 종목 모두 평가 후) ──┐
                                                              ▼
              전 Stage 통과 종목 집계 → 📄 researchedCompany.md
```

#### 4단계: 탈락사유 분석 (C · Filter_condition_update)

```
┌──────────── C · Filter_condition_update   (탈락사유 분석) ───────────────┐
│ 입력 : 📄 masterReference.md  (분석할 종목을 사용자가 직접 기입)         │
│        + 📄 stage1~5_*_passed.md                                         │
│                                                                          │
│        ◇ masterReference.md 가 비어 있는가?                              │
│           ├─ 예  ╳▶ 아무것도 하지 않고 종료 (no-op, 정상)               │
│           └─ 아니오 ▼                                                    │
│                                                                          │
│   ║ for 종목 in masterReference:                                        ║│
│   ║   for Stage in (1,2,2-1,3,4,5):                                     ║│
│   ║     ◇ 종목이 해당 stage_passed.md 에 없는가?                        ║│
│   ║        └─ 예 ▶ 그 Stage 필터를 재평가 → 탈락 조건 도출             ║│
│   ║   종목 섹션 끝에 (기록 날짜-시간) 추가                              ║│
│                                                                          │
│ 산출 : 📄 masterReference.log   (append — 재실행 누적, 덮어쓰기 금지)    │
│ 격리 : C 단계 예외는 풀플로우 종료 코드에 영향 없음                      │
└────────────────────────────────────┬─────────────────────────────────────┘
                                      ▼
                              ✅ 풀플로우 종료
```

#### 산출물 한눈 정리 (모두 `reports/YYYYMMDD/` 하위)

| 순서 | 단계 | 입력 | 산출물 |
|---|---|---|---|
| ① | upperLowerPrice | ka10017 | `upperLowerPrice.md` |
| ② | conditionResearch | 조건검색식 9개 | `conditionResearch.md` |
| ③ | organizedCompany | ①+② .md | `organizedCompany.md`, `masterReference.md`(빈 파일) |
| Stage 0 | prefetch | ③ 전 종목 | `<종목명(코드)>/chart60·120·240·chartDay·investor·finance.md`, `prefetchManifest.json` |
| Stage 1 | chart60_120Filter | chart60·120.md | `stage1_chart60_120_passed.md` |
| Stage 2 | chart240Filter | chart240.md | `stage2_chart240_passed.md` |
| Stage 2-1 | chartDayPreFilter | chartDay.md | `stage2_1_chartDayPre_passed.md` |
| Stage 3 | chartDayFilter | chartDay.md | `stage3_chartDay_passed.md` |
| Stage 4 | investorFilter | investor.md | `stage4_investor_passed.md` |
| Stage 5 | financeFilter | finance.md | `stage5_finance_passed.md` |
| (집계) | 최종 채택 | Stage 1~5 통과 | `researchedCompany.md` |
| C | Filter_condition_update | masterReference.md + stage*_passed.md | `masterReference.log` (append) |

#### 분기·종료 규칙 요약

| 지점 | 조건 | 결과 |
|---|---|---|
| ① · ② | 예외 발생 | 로그 후 **격리** — 다음 단계 계속 진행 |
| ③ | 종목 0건 / OrganizeError | Stage 0·1~5·C **전부 스킵**, 종료 코드 `1` |
| Stage 0 | PrefetchError | Stage 1~5·C **스킵**, 종료 코드 `1` |
| Stage 0 | 특정 종목 일부 API 실패 | 그 종목 manifest 에 `error` → 해당 Stage 에서 자동 탈락 |
| Stage 1~5 | 종목별 예외 | 해당 **종목만** 격리, 다른 종목 계속 |
| Stage 1~5 | 어느 Stage 탈락 | 그 종목 `break` — 이후 Stage 미평가 |
| C | masterReference.md 비어 있음 | no-op 종료 (정상) |
| C | 분석 중 예외 | **격리** — 풀플로우 종료 코드 불변 |
| 전체 | 정상 완료 / 기타 예외 | 종료 코드 `0` / `2` |
