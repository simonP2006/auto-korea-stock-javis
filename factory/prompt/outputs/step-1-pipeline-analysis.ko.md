# Step 1 — 파이프라인 의존성 그래프 및 산출 스키마

> 생성일: 2026-05-29

본 문서는 `kiwoom-rest-trader` 의 종목 스크리닝 파이프라인을 (a) 호출 체인, (b) 산출 파일 포맷, (c) `masterReference.log` 스키마 세 축으로 분석한다. 모든 경로는 절대 경로로 표기한다.

---

## (a) 실행 파이프라인 호출 체인

### `/Users/tajun/spJavis/kiwoom-rest-trader/scripts/run_full_research_flow.py`

**진입점(Entry point)** (라인 69-70):
```python
if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

**CLI 인터페이스** — argparse 미사용, `sys.argv` 직접 파싱.
- 인자 0개 → 오늘 (`datetime.now().strftime("%Y%m%d")`).
- 인자 1개 (`YYYYMMDD`) → 해당 일자 백필 실행.
- 종료 코드: `0` 정상 / `1` ③·④ 스킵 / `2` 예외.

**임포트(Imports)**:
- `from src.kiwoom.researchFlow import FullFlowSummary, run_full_flow`

**호출 체인(Call chain)** — `run_full_flow()` 단일 함수에 모든 단계 위임. 내부 위임 트리:

```
run_full_research_flow.py
└── researchFlow.facade.run_full_flow(date)
    ├── ① _stage_upper_lower_price()
    │       └── upperLowerPrice.get_upper_lower_price()
    │       └── save_upper_lower_price_markdown()         → reports/<날짜>/upperLowerPrice.md
    │
    ├── ② _stage_condition_research()
    │       └── conditionCompany.run_all_conditions()
    │       └── conditionCompany.saveReport.save_condition_research()
    │                                                     → reports/<날짜>/conditionResearch.md
    │
    ├── ③ _stage_organized_company()
    │       └── organizedCompany.organize_today()
    │       └── organizedCompany.saveReport.save_organized_company()
    │                                                     → reports/<날짜>/organizedCompany.md
    │
    ├── Stage 0  researchFlow.prefetch.prefetch_all()
    │       └── (종목별 6 API 일괄 호출)
    │                                                     → reports/<날짜>/<종목>/chart60.md
    │                                                     → reports/<날짜>/<종목>/chart120.md
    │                                                     → reports/<날짜>/<종목>/chart240.md
    │                                                     → reports/<날짜>/<종목>/chartDay.md
    │                                                     → reports/<날짜>/<종목>/investor.md
    │                                                     → reports/<날짜>/<종목>/finance.md
    │                                                     → reports/<날짜>/prefetchManifest.json
    │
    ├── Stage 1~5  researchFlow.facade.filter_today()
    │       └── 종목별 _run_filter_pipeline():
    │           ├── Stage 1   chart60_120_filter_stock()    → stage1_chart60_120_passed.md
    │           ├── Stage 2   chart240_filter_stock()       → stage2_chart240_passed.md
    │           ├── Stage 2-1 chartday_pre_filter_stock()   → stage2_1_chartDayPre_passed.md
    │           ├── Stage 3   chartday_filter_stock()       → stage3_chartDay_passed.md
    │           ├── Stage 4   investor_filter_stock()       → stage4_investor_passed.md
    │           └── Stage 5   finance_filter_stock()        → stage5_finance_passed.md
    │       └── researchFlow.saveReport.save_researched_company()
    │                                                     → reports/<날짜>/researchedCompany.md
    │       └── researchFlow.saveReport.save_all_stages_passed()
    │
    └── C. itemFilter.Filter_condition_update.run_filter_condition_update(yyyymmdd)
                                                          → reports/<날짜>/masterReference.log (append)
```

핵심 위임 위치: `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/researchFlow/facade.py` (`run_full_flow`, `filter_today`, `_run_filter_pipeline`).

### `/Users/tajun/spJavis/kiwoom-rest-trader/scripts/run_prefetch.py`

**진입점(Entry point)** (라인 185-186):
```python
if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

**CLI 인터페이스** — argparse 미사용, `sys.argv` 직접 파싱.
- 인자 0개 → 오늘.
- 인자 1개 (`YYYYMMDD`) → 백필.
- 종료 코드: `0` 정상 / `1` ③ 0건/실패 → Stage 0 스킵 / `2` 예외.

**임포트(Imports)** (모두 직접 호출):
- `from src.kiwoom.conditionCompany import KiwoomConditionError, run_all_conditions`
- `from src.kiwoom.conditionCompany.saveReport import save_condition_research`
- `from src.kiwoom.organizedCompany import OrganizeError, organize_today`
- `from src.kiwoom.organizedCompany.saveReport import save_organized_company`
- `from src.kiwoom.researchFlow import PrefetchError, prefetch_all`
- `from src.kiwoom.upperLowerPrice.upperLowerPrice import get_upper_lower_price, save_upper_lower_price_markdown`

**호출 체인(Call chain)** (`run_full_research_flow` 의 ①·②·③ + Stage 0 까지만, 필터 단계 없음):

```
run_prefetch.py
├── ① get_upper_lower_price() + save_upper_lower_price_markdown()
├── ② run_all_conditions() + save_condition_research()
├── ③ organize_today() + save_organized_company()
└── Stage 0  researchFlow.prefetch.prefetch_all()
```

**분리 의도**: "수집 1회 / 필터 N회" 워크플로우 — `run_prefetch.py` 로 한 번 데이터 수집한 뒤 `run_filters.py` 로 필터 룰을 반복 튜닝.

### `/Users/tajun/spJavis/kiwoom-rest-trader/scripts/run_filters.py`

**진입점(Entry point)** (라인 87-88):
```python
if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
```

**CLI 인터페이스** — argparse 미사용.
- 인자 0개 → 오늘.
- 인자 1개 (`YYYYMMDD`).
- 종료 코드: `0` 정상 / `1` `ResearchError` (입력 부재) / `2` 예외.

**임포트(Imports)**:
- `from src.kiwoom.researchFlow import ResearchError, filter_today`
- `from src.kiwoom.researchFlow.saveReport import save_all_stages_passed, save_researched_company`

**주의**: 본 스크립트는 `Filter_condition_update` 를 **호출하지 않는다**. 즉 `masterReference.log` 는 `run_full_research_flow` 경유 시에만 갱신된다.

**호출 체인(Call chain)**:

```
run_filters.py
└── researchFlow.filter_today(date)
    └── (Stage 1~5 종목별 평가 — 위 run_full_flow 의 Stage 1~5 블록과 동일)
└── save_researched_company()
└── save_all_stages_passed()
```

### 필터별 독립 실행 가능성(Independent invocability per filter)

7개 필터 모듈 모두 `__main__` 블록 보유. 모두 `python -m src.kiwoom.itemFilter.<모듈>` 형태로 단독 실행 가능.

| 필터 모듈 | `__main__` 보유 여부 | 단독 CLI 인자 | 비고 |
|---|---|---|---|
| `chart60_120Filter.py` | 예 (라인 1071) | `<stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` (인자 없으면 `--all`) | argparse 미사용. 단일 종목/일괄 모드 지원. |
| `chart240Filter.py` | 예 (라인 686) | `<stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` | 동일 패턴. |
| `chartDayPreFilter.py` | 예 (라인 522) | `<stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` | 동일 패턴. |
| `chartDayFilter.py` | 예 (라인 909) | `<stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` | 동일 패턴. |
| `investorFilter.py` | 예 (라인 695) | `<stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` | 동일 패턴. |
| `financeFilter.py` | 예 (라인 543) | `<stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` | 동일 패턴. |
| `chart60Filter.py` | 예 (라인 819) | `<stock> [YYYYMMDD]` 또는 `--all [YYYYMMDD]` | 보조 모듈 — 파이프라인엔 미포함 (chart60_120 으로 통합됨). |
| `Filter_condition_update.py` | 예 (라인 299) | `[YYYYMMDD ...]` (다중 일자 순차 실행) | `python -m src.kiwoom.itemFilter.Filter_condition_update 20260518 20260519 20260520` |
| `stageMasterFilter.py` | 예 (라인 713) | argparse 서브커맨드: `bootstrap` / `daily-update` / `validate` / `filter <YYYYMMDD>` / `show` | 7개 모듈 중 유일하게 argparse 사용. |

---

## (b) 산출 포맷 카탈로그(Output Format Catalog)

**공통 포맷 규칙** (`/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/researchFlow/saveReport/plain_text.py` 라인 13-28 명시):
- 줄당 종목명 1개 — 헤더/번호/등락률/구분자/Type 라벨 모두 미표시.
- 입력 순서 = `organizedCompany.md` 의 등락률 내림차순 보존.
- UTF-8, LF 줄바꿈, 마지막에 trailing newline 1개.
- 통과 종목 0건이면 빈 파일 (0 bytes).
- 확장자는 `.md` 지만 본문은 마크다운 표가 아님 — 후속 모듈이 다시 입력으로 사용하기 위함.

### `stage1_chart60_120_passed.md`

**출처(Source)**: `save_stage_passed(results, stage_idx=1)` (`plain_text.py:123-164`), 내부 `render_stage_passed()` 의 `"\n".join(r.candidate.stk_nm for r in passed) + "\n"` (라인 120).

**샘플(Sample)** (verbatim, `/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/stage1_chart60_120_passed.md`):
```
이브이첨단소재
코칩
유성티엔에스
삼화콘덴서
한성크린텍
LG에너지솔루션
...
```

**Type 패턴(A/B/C/D/E) 포함 여부?** **아니오.**
- 증거: `render_stage_passed()` 는 `r.candidate.stk_nm` 만 출력. Type 결과는 `chart60_120Filter` 내부 `r.extra["type_results"]` 에만 보관되며 (`chart60_120Filter.py:1018-1022` 의 `_print_single` stdout 한정), `.md` 파일에는 기록되지 않는다.
- 만약 Type 정보가 필요하면 `Filter_condition_update.run_filter_condition_update()` 가 재평가하여 `masterReference.log` 의 reason 문자열에 텍스트로 (예: `A:120분 4선정배열 실패: …; B:120분 Type B 조건 실패: …; C:120분 수렴 실패: …; D:60분 보조조건 실패 …; E:120분 MA10 < MA20×0.984 …`) 기록함.

### `stage2_chart240_passed.md`

**출처(Source)**: `save_stage_passed(results, stage_idx=2)`, 동일 포맷.

**샘플(Sample)** (`/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/stage2_chart240_passed.md`):
```
이브이첨단소재
코칩
유성티엔에스
...
```

종목명 단일 컬럼, 부가 메타데이터 없음.

### `stage2_1_chartDayPre_passed.md`

**출처(Source)**: `save_stage_passed(results, stage_idx=3)` (슬롯 3 = chartDayPre — `_STAGE_FILENAMES` 매핑 참조), 동일 포맷.

**샘플(Sample)** (`/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/stage2_1_chartDayPre_passed.md`):
```
LG에너지솔루션
더블유씨피
삼성전기
...
```

**중요**: `stage2_1_chartDayPre_passed.md` 가 Stage 2 (chart240) **이후** 의 정확한 통과 종목 집합이라는 보장은 없다. `plain_text.py:114-117` 의 정의에 따르면 "Stage N 까지 도달해서 그 단계를 통과한 종목" 이므로 Stage 1 → Stage 2-1 흐름 전체를 통과한 종목들이다. 단계 진입 자체는 `_run_filter_pipeline` 의 early-break 로직(`facade.py:259-299`)이 보장.

### `stage3_chartDay_passed.md`

**출처(Source)**: `save_stage_passed(results, stage_idx=4)`, 동일 포맷.

**샘플(Sample)** (`/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/stage3_chartDay_passed.md`):
```
캐프
화신정공
아바텍
...
```

### `stage4_investor_passed.md`

**출처(Source)**: `save_stage_passed(results, stage_idx=5)`, 동일 포맷.

**샘플(Sample)** (`/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/stage4_investor_passed.md`):
```
캐프
화신정공
국보디자인
세기상사
...
```

### `stage5_finance_passed.md`

**출처(Source)**: `save_stage_passed(results, stage_idx=6)`, 동일 포맷.

**샘플(Sample)** (`/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/stage5_finance_passed.md`):
```
캐프
화신정공
국보디자인
NC
...
```

내용은 **`researchedCompany.md` 와 동일**해야 한다 (Stage 5 = 최종 단계). `saveReport/__init__.py:9` 의 주석이 이를 확인.

### `researchedCompany.md` (및 변종)

#### `researchedCompany.md` — 정본(canonical)

**출처(Source)**: `save_researched_company(results)` (`plain_text.py:68-97`).
**필터**: `final_selected=True` 인 종목만 (`render_plain_text` 라인 62).
**샘플(Sample)** (`/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/researchedCompany.md`):
```
캐프
화신정공
국보디자인
NC
대륙제관
...
```

Stage 5 finance 까지 모두 통과한 종목명을 줄단위로 기록. `stage5_finance_passed.md` 와 내용이 동일.

#### `researchedCompany.p1.md` — **레거시(legacy) / 고아(orphan) 파일**

- **생성 코드**: `kiwoom-rest-trader` 현재 코드베이스 내에 `.p1` 을 쓰는 코드 **존재하지 않음** (`grep -rn ".p1.md\|p1_md" src/` 결과 0건).
- **관계**: 과거 버전의 `researchedCompany.md` 백업/스냅샷으로 추정. 2026-05-21·19·18 폴더에만 존재.
- **역할**: 비활성 — 현재 파이프라인 산출물 아님.

#### `researchedCompany.p2.md` — **레거시(legacy) / 고아(orphan) 파일**

- **생성 코드**: 동일하게 src 내에 생성 코드 부재.
- **관계**: 과거 버전 스냅샷. p1 보다 더 많은 종목을 포함(예: 20260521 의 p1=13, p2=34).
- **역할**: 비활성.

#### `masterConditionCompany.md`

- **생성 코드**: `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/stageMasterFilter.py:483` — `out_path = out_dir / _OUTPUT_FILENAME` (`_OUTPUT_FILENAME = "masterConditionCompany.md"`, 라인 61). `save_filter_plain_text()` → `render_plain_text()` (라인 462-467).
- **관계**: 별도 누적-확장(append-only) 필터 산출물. Stage 1~5 파이프라인과는 **독립** — `stageMasterFilter.py` 의 4-feature 밴드 (close_over_ma20, close_over_ma10, ma20_over_ma60, close_over_ma306) 평가 결과.
- **포맷**: `researchedCompany.md` 와 동일 (종목명 줄단위).
- **역할**: `researchFlow.facade.run_full_flow` 가 호출하지 않음 — 별도 CLI (`python -m src.kiwoom.itemFilter.stageMasterFilter filter <YYYYMMDD>`) 로만 생성. 종목 풀 확장(positive coverage) 용도.

#### SHOW_RESULTS 체인을 위한 권장 정본(canonical) 파일

**`researchedCompany.md`** — 근거:
1. `run_full_research_flow.py` / `run_filters.py` 양쪽이 모두 직접 생성하는 유일한 파이프라인 종착 파일.
2. `Filter_condition_update.run_filter_condition_update()` 가 명시적으로 `_RESEARCHED_MD = "researchedCompany.md"` 를 전제 조건으로 참조 (라인 67, 182-188).
3. `final_selected=True` (Stage 1·2·2-1·3·4·5 모두 통과) 의 정확한 정의를 갖는다.
4. `stage5_finance_passed.md` 와 내용이 동일하지만 의미상 더 명확한 "최종 통과" 시맨틱.
5. `.p1`/`.p2` 는 코드 부재로 폐기 후보, `masterConditionCompany.md` 는 별도 풀(stageMasterFilter)의 산출물이므로 동일 시맨틱이 아님.

---

## (c) `masterReference.log` 스키마

**소스 코드**: `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/Filter_condition_update.py`
**쓰기 모드**: `open("a", encoding="utf-8")` (라인 254-256) — **append**, 덮어쓰지 않음. 재실행 시 새 블록이 누적.

### 포맷 (코드 원문 그대로, verbatim from code)

블록 단위 구조 (`run_filter_condition_update` 라인 204-252):

```
<sep>
[YYYY-MM-DD HH:MM:SS] masterReference 분석 (date=YYYYMMDD, 대상 N종목)
<sep>

### <종목명>(<종목코드>)        ← 종목코드는 master_reference.md 원본 형식에 따라 선택적
- <Stage 라벨> — <stage_name> (<passed_file>)<file_note>: [<category>] <reason>
- <Stage 라벨> — <stage_name> (<passed_file>): [<category>] 본 단계 자체는 통과(재평가) — 이전 단계 탈락으로 미도달 / 사유: <reason>
...
(기록 YYYY-MM-DD HH:MM:SS)

### <종목명>(<종목코드>)
- (전 Stage 통과 — 기록 대상 없음)
(기록 YYYY-MM-DD HH:MM:SS)

<공백 줄>
```

여기서 `<sep>` 는 `"=" * 78`. 종목별 섹션은 빈 줄로 구분. 한 블록 내 모든 종목은 동일 stamp 를 공유.

핵심 포맷 문자열 (verbatim):
- 헤더: `f"[{stamp}] masterReference 분석 (date={yyyymmdd}, 대상 {len(targets)}종목)"` (라인 208-210)
- 종목 헤더: `f"### {disp}"` (라인 229) where `disp = f"{nm}({cd})" if cd else nm`
- Stage 라인: `f"- {label} — {stage_name} ({passed_file}){file_note}: {detail}"` (라인 242-244)
- 통과 케이스: `f"[{category}] 본 단계 자체는 통과(재평가) — 이전 단계 탈락으로 미도달 / 사유: {reason}"` (라인 154-156)
- 탈락 케이스: `f"[{category}] {reason}"` (라인 157)
- 푸터: `f"(기록 {stamp})"` (라인 250)

### 필드별 세부 분석(Field-by-field breakdown)

| 필드 | 출처 | 예시 | 비고 |
|---|---|---|---|
| `<sep>` | `"=" * 78` (라인 205) | `==============================================================================` | 78자 고정. |
| stamp (헤더) | `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` (라인 202) | `2026-05-28 21:01:34` | 블록 단위. |
| `date=` | `yyyymmdd` 인자 (또는 오늘) | `date=20260528` | YYYYMMDD. |
| `대상 N종목` | `len(targets)` | `대상 7종목` | `masterReference.md` 의 종목 개수. |
| `### <disp>` | `_parse_entry` 의 `(nm, cd)` (라인 95-101) | `### 아이텍`, `### 푸른기술` | 코드 있으면 `종목명(코드)` 형식. |
| label | `_STAGES[i][0]` (라인 72-85) | `Stage 1`, `Stage 2-1` | 6개 고정값. |
| stage_name | `_STAGES[i][1]` | `chart60_120`, `chart240`, `chartDayPre`, `chartDay`, `investor`, `finance` | |
| passed_file | `_STAGES[i][2]` | `stage1_chart60_120_passed.md` 등 | |
| file_note | `"  (※ 결과 파일 부재)"` 또는 빈 문자열 (라인 218) | (대부분 빈 문자열) | Stage 결과 파일 부재 시 표시. |
| category | `r.category` (StageOutcome) | `제외`, `선정`, `정상`, `정배열`, `장기추세` 등 | `[]` 로 둘러쌈. |
| reason | `r.reason` (StageOutcome) | "외국인 3회 연속 매도 (≥ 2)" 등 | 자유 텍스트. |
| 푸터 stamp | `(기록 ...)` | `(기록 2026-05-28 21:01:34)` | 동일 블록의 stamp. |

### 격차값(Gap value) 포함 여부: **부분적(Partial) — 텍스트 내장만, 구조화 필드 없음**

**증거(Evidence)** — `Filter_condition_update.py:152-157`:
```python
if selected:
    return (
        f"[{category}] 본 단계 자체는 통과(재평가) — "
        f"이전 단계 탈락으로 미도달 / 사유: {reason}"
    )
return f"[{category}] {reason}"
```
출력에는 `reason` 문자열만 그대로 들어가며 별도 `actual=`/`threshold=`/`gap=` **구조화 필드는 없다**.

다만 각 필터의 `reason` 자체에는 실제값과 임계값이 **자연어 형태로** 포함되어 있다:
- Stage 1: `"A:120분 4선정배열 실패: ts=2026-05-27 11:00 MA60(7,195) < MA306×0.965(7,198)"` (실제 7195 vs 임계 7198, gap 텍스트 부재)
- Stage 2: `"최근 3봉 MA60↔MA306 실패 — ts=2026-05-27 13:00 MA60(2,107.58) < MA306×0.975(2,153.41)"` (실제 vs 임계, gap 부재)
- Stage 2-1: `"금일 일봉 +16.44% — 15% 이상 급상승"` (실제 16.44%, 임계 15%, 산술 gap=+1.44%p 텍스트 부재)
- Stage 3: `"종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%] 이탈"` (괴리율 +53.41% 포함, 임계 상한 +50.0% 포함; gap = +3.41%p 미명시)
- Stage 4: `"외국인 3회 연속 매도 (≥ 2)"` (실제 3 vs 임계 2; gap=+1일 텍스트 부재)
- Stage 5: `"당기순이익 -70억원 < 0 (적자)"` (실제 -70억; gap=-70억 텍스트 부재)

**결론**: FR-5.2 영향 추정용 **수치형 gap 필드는 없음**. 정규식 파서가 reason 본문에서 실제값/임계값을 추출하더라도 (1) 단위 비균질(원, %, 회, 억원), (2) 포맷 비표준(쉼표 천단위, 부호 위치, 임계값이 `×0.975` 같은 곱셈식)이라 자동 추출 신뢰도 낮음.

**최소 패치 제안**:
1. 각 `<Filter>FilterResult` 데이터클래스에 `gap_metrics: dict[str, float]` 필드를 추가하고, 각 evaluator (예: `chart60_120Filter.evaluate_chart60_120`) 가 비교 시 `{ "MA60_minus_MA306x0.965": actual - threshold, ... }` 로 채우게 한다.
2. `_analyze_stock` (`Filter_condition_update.py:133-157`) 의 반환 문자열 끝에 `f" [gap: {', '.join(f'{k}={v:+.4f}' for k, v in r.gap_metrics.items())}]"` 를 append.
3. 그 결과 로그 한 줄에 `[gap: ma60_minus_ma306x0.965=-3.0000, …]` 형태의 정량 부록이 붙어 정규식 파서가 안정적으로 추출 가능.

### 예시 로그 라인 (`/Users/tajun/spJavis/kiwoom-rest-trader/reports/20260528/masterReference.log` 원문 그대로)

```
### 아이텍
- Stage 1 — chart60_120 (stage1_chart60_120_passed.md): [제외] 전 타입 미매칭 — A:120분 4선정배열 실패: ts=2026-05-27 11:00 MA60(7,195) < MA306×0.965(7,198); B:120분 Type B 조건 실패: ts=2026-05-27 09:00 MA10(8,015) > MA60×0.97(6,987) — MA60 대비 3% 이상 아래여야 함; C:120분 수렴 실패: ts=2026-05-27 09:00 수렴 폭 11.28% > 3.5% (min=7,203 max=8,015); D:120분 엉킴 조건 실패: ts=2026-05-27 09:00 MA60(7,203) < MA306×0.985(7,349); E:120분 MA10 < MA20×0.984 (최근 2봉 모두) — 단기 정렬 미시작
- Stage 2 — chart240 (stage2_chart240_passed.md): [장기추세] 본 단계 자체는 통과(재평가) — 이전 단계 탈락으로 미도달 / 사유: 최근 3봉 모두 MA60 ≥ MA306×0.975
- Stage 4 — investor (stage4_investor_passed.md): [제외] 외국인 3회 연속 매도 (≥ 2)
- Stage 5 — finance (stage5_finance_passed.md): [제외] 당기순이익 -70억원 < 0 (적자)
(기록 2026-05-28 21:01:34)

### 에스엠벡셀
- Stage 2 — chart240 (stage2_chart240_passed.md): [제외] 최근 3봉 MA60↔MA306 실패 — ts=2026-05-27 13:00 MA60(2,107.58) < MA306×0.975(2,153.41)
- Stage 3 — chartDay (stage3_chartDay_passed.md): [제외] MA612 밴드/양봉 실패 — 종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%] 이탈
(기록 2026-05-28 21:01:34)

### 애드바이오텍
- Stage 2-1 — chartDayPre (stage2_1_chartDayPre_passed.md): [제외] 금일 일봉 +16.44% — 15% 이상 급상승
- Stage 5 — finance (stage5_finance_passed.md): [제외] 당기순이익 -33억원 < 0 (적자)
(기록 2026-05-24 20:01:46)
```

---

## 검증 자가 점검(Verification Self-Check)

- [x] Sub-task (a): 3개 스크립트 추적 완료 (`run_full_research_flow.py`, `run_prefetch.py`, `run_filters.py`) + 9개 필터 모듈 (`chart60_120Filter`, `chart240Filter`, `chartDayPreFilter`, `chartDayFilter`, `investorFilter`, `financeFilter`, `chart60Filter`, `Filter_condition_update`, `stageMasterFilter`) `__main__` 블록 모두 라인 번호와 함께 명시.
- [x] Sub-task (b): 5종 stage*_passed.md (stage1·2·2_1·3·4·5) 포맷 + 4종 변종 (`researchedCompany.md`, `.p1.md`, `.p2.md`, `masterConditionCompany.md`) 설명 완료.
- [x] Sub-task (c): `masterReference.log` 포맷 + gap-value 답변 (Partial — 자연어 텍스트로만 포함, 구조화 필드 없음, 최소 패치 제안 포함) + 실제 로그 발췌 3블록.
- [x] SHOW_RESULTS canonical 파일 명명: **`researchedCompany.md`** + 5가지 근거.
