# output-templates.md

모든 한국어 출력 템플릿의 canonical 사본. PRD §7.3 + Step 5 §6 verbatim. SKILL.md §5에서 본 파일을 참조.

본 파일의 모든 한국어 문자열은 **재번역 금지** — 그대로 인용한다.

---

## §1. 한국어 숫자 형식 (PRD §7.3 verbatim)

Skill MUST reproduce these forms exactly:

| 단위 | 형식 | 예 |
|---|---|---|
| 가격 | 천단위 콤마 + `원` | `4,805원` |
| 등락률 | `±N.N%` | `-3.5%` |
| 배수 | `N.NNN배` | `0.965배` |
| 횟수 | 천단위 콤마 + `회` | `5,234회` |
| 금액 | `N,NNN억원` | `1,234억원` |
| 비율 표시 | `M/N개` 또는 `A개 → B개` | `15/350개`, `82개 → 45개` |

**금지**: `￦`, `KRW`, `4,805 KRW`, 영어 locale, 과학적 표기 (`4.8e3`).

---

## §2. SHOW_RESULTS Korean template

Chain 4 + Chain 1 / Chain 2 / Chain 8 최종 emission에서 사용:

```
[{date} 스캔 결과]

| Stage | 입력 | 통과 | 탈락률 |
|---|---|---|---|
| 1 (chart60_120)   | 2,398 | 1,234 | 48.5% |
| 2 (chart240)      | 1,234 |   567 | 54.0% |
| 2-1 (chartDayPre) |   567 |   542 |  4.4% |
| 3 (chartDay)      |   542 |   128 | 76.4% |
| 4 (investor)      |   128 |    34 | 73.4% |
| 5 (finance)       |    34 |    17 | 50.0% |
| 최종              |       |    17 |       |

[최종 통과 종목]
- 삼성전자(005930)
- SK하이닉스(000660)
- ... (전체 목록: ${KRT_REPORTS}/{date}/researchedCompany.md)

* Type 상세는 Stage 1 재평가로 확인 가능 (예: "삼성전자 왜 통과했어?")

⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.
```

세션 첫 emission이 아니면 마지막 줄을 `(투자판단·책임은 본인에게 있습니다)` 1줄 축약으로 교체. `disclaimer.md` 참조.

---

## §3. Prefetch stats Korean template (Chain 2 Step 5)

```
[데이터 수집 완료 — {date}]
- 대상 종목: {total}개
- 성공: {ok_count}개
- 빈 데이터: {empty_count}개
- 오류: {err_count}개

prefetchManifest.json 위치: ${KRT_REPORTS}/{date}/prefetchManifest.json
```

---

## §4. WHY_REJECTED Korean template (Chain 5 Step 6)

```
[{stock_name} 탈락 분석 — {date}]

Stage {N}에서 탈락: {조건} = {실제값}. 기준 {기준값}. {gap} 미달.

[전체 Stage 평가 이력 (재평가 결과)]
- Stage 1 (chart60_120): {category} — {reason 요약}
- Stage 2 (chart240): {category} — {reason 요약}
- Stage 2-1 (chartDayPre): {category} — {reason 요약}
- Stage 3 (chartDay): [제외] {reason 전문}        ← 실제 탈락 지점
- Stage 4 (investor): (이전 단계 탈락으로 미도달)
- Stage 5 (finance): (이전 단계 탈락으로 미도달)

기록 시각: {YYYY-MM-DD HH:MM:SS}

(투자판단·책임은 본인에게 있습니다)
```

**전 Stage 통과 케이스** (`r.extra`에 기록 없음): `"{stock_name}은(는) 5-Stage 전부 통과한 종목입니다 — 탈락 사유가 없습니다."`

**예시 (Stage 3 MA612 band breach)**:
`"Stage 3에서 탈락: 종가가 MA612 대비 +53.41%. 기준 상한 +50.0%. 3.41%p 초과."`

**regex miss fallback**: `"수치 추출 실패 — 원문 그대로 표시"` + raw `reason` 텍스트 인용.

**로그 회전 (B-5)**: `"로그 회전: masterReference.log → masterReference.log.{YYYYMM} (500행 초과)"`.

---

## §5. SCAN_RANGE summary Korean template (Chain 3 Step 4)

```
[범위 스캔 완료 — {start}~{end} ({N}영업일)]

| 날짜 | 통과 종목 수 |
|---|---|
| 2026-05-26 (월) | 15 |
| 2026-05-27 (화) | 22 |
| 2026-05-28 (수) | 17 |
...

- 합집합 (어느 날이든 통과): {N_union}종목
- 교집합 (모든 날 통과): {N_intersect}종목 — {list}

⚠️ 주의: 한국 공휴일은 자동 제외되지 않습니다. 통과 0건인 날은 휴장일일 수 있습니다.
(투자판단·책임은 본인에게 있습니다)
```

**범위 시작 전 경고** (Step 1): `"⚠️ 주의: 한국 공휴일은 자동으로 제외되지 않습니다. 결과 폴더가 비어있다면 휴장일일 수 있습니다."`

**시작 확인** (Step 2): `"총 {N}영업일 스캔 예정 (예상 소요: ~{N*15}분). 진행할까요?"`

**진행률** (Step 3): `"{i}/{N}일 완료 — {d_i}: {count}종목 통과"`

**오류 시** (Step 3): `"{d_i} 에서 오류 발생. 나머지 영업일을 계속할까요?"`

**중단** (Checkpoint): `"연속 오류로 범위 스캔을 중단했습니다."`

---

## §6. COMPARE Korean template (Chain 6)

```
[비교: {date_a} vs {date_b}]

| 구분 | 종목 수 |
|---|---|
| 공통 ({date_a} ∩ {date_b}) | {N_common} |
| {date_a} 에만 (탈락) | {N_only_a} |
| {date_b} 에만 (추가) | {N_only_b} |

[공통 종목] {comma-separated list}
[탈락] {list_only_a}
[추가] {list_only_b}

{선택적 — tuning-log 인용 시}: 참고: {date_a}~{date_b} 기간 동안 파라미터 변경 {N}건 발견: {param_id_list}

(투자판단·책임은 본인에게 있습니다)
```

---

## §7. COMPARE_PARAMS Korean template (Chain 7)

```
[파라미터 변경 전후 비교]

변경: {param_id}: {old_value} → {new_value}
시각: {before_datetime} → {after_datetime}

| 구분 | 종목 수 |
|---|---|
| 변경 전 | {before_count} |
| 변경 후 | {after_count} ({delta:+d}) |
| 공통 | {N_common} |
| 추가 | {N_added} |
| 탈락 | {N_removed} |

[추가된 종목] {list}
[탈락한 종목] {list}

(투자판단·책임은 본인에게 있습니다)
```

`{before_count}` / `{after_count}` 출처: `tuning-log.md` 8-column 스키마의 `stocks_passed_before` / `stocks_passed_after` 칼럼 (filter-tune이 8개 칼럼 전부의 sole writer; `stocks_passed_after`는 filter-tune이 `screener_state.last_results_summary`에서 backfill하며 `pending`일 수 있음). stock-scan은 READS만 — **`{after_count}`가 `pending`/`미측정`이면 위 표의 "변경 후" 행을 `"재실행 필요"`로 렌더하고 `({delta:+d})`를 생략(정수 파싱 금지).**

**tuning-log 행 not found**: `"해당 변경 이력을 tuning-log.md에서 찾을 수 없습니다."`

---

## §8. Error report Korean template (SKILL.md §6 dispatch에서 사용)

```
[오류 발생]
{Korean summary 1 sentence}
원인: {cause}
조치: {user action}

기술 정보:
  {raw error excerpt — last 5 lines of stderr or exception type+message}
```

`{Korean summary}` / `{cause}` / `{user action}`은 CLAUDE.md `§Error Classification` 9-row 표를 참조 (verbatim 동일). 본 Skill은 표를 중복 보관하지 않는다.

**재시도 예산 stop 메시지** (동일 `type(exc).__name__` 2회 연속):
`"동일 오류({exc_name})가 2회 반복되었습니다. 추가 시도를 중단합니다. 원인: {cause}. 조치: {action}."`

**JSON corruption 알림** (R-7, screener_state.json 손상 시):
`"⚠️ screener_state.json 손상 감지. 손상 파일을 백업했습니다: {state_path}.corrupt.{ts}. 새로운 상태로 시작합니다."`

---

## §9. ADR-012 백그라운드 실행 한국어 문자열

**실행 시작 안내** (Chain 1 Step 4, Chain 2 Step 2):
`"약 10-15분 소요됩니다. 완료되면 자동으로 결과를 보고합니다."`

**30분 watchdog timeout fallback** (Chain 1 Step 6, Chain 2 Step 4):
`"실행이 예상보다 길어지고 있습니다. SCAN_SEPARATED 모드로 다시 시도하시겠습니까?"`

**Chain 1 / Chain 8 결과 파일 미생성**:
`"결과 파일이 생성되지 않았습니다 — 파이프라인이 중간 단계에서 종료되었을 수 있습니다. 기술 정보: stderr 마지막 줄 첨부."`

**Chain 2 manifest 미생성**:
`"prefetchManifest.json 이 생성되지 않았습니다. Stage 0 prefetch 가 실패한 것으로 보입니다."`

**Chain 2 filter 실행 확인 질문** (AskUserQuestion, PRD P4):
질문: `"필터를 실행할까요?"`
옵션: `["네, 지금 필터 실행", "잠시 후 직접 실행"]`

**R-9 lock 거부**:
`"파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`

**Chain 4 결과 부분 존재**:
`"결과 파일이 부분적으로만 존재합니다 (researchedCompany.md 있음, 단계별 파일 부재). 필터 실행이 비정상 종료되었을 수 있습니다."`

**Chain 4 결과 없음 redirect**:
`"{date} 결과가 없습니다. 스캔을 먼저 실행할까요?"`

**Chain 5 종목 미수집**:
`"해당 종목은 수집 대상에 포함되지 않았습니다. 조건검색·상하한가 수집 단계에 들어오지 않은 종목입니다."`

**Chain 5 전 Stage 통과**:
`"{stock_name}은(는) 5-Stage 전부 통과한 종목입니다 — 탈락 사유가 없습니다."`

**Chain 1 캐시 hit 단축**:
`"이미 스캔된 결과가 있습니다. 다시 실행할까요?"`

**Chain 1 날짜 형식 오류**:
`"날짜 형식이 올바르지 않습니다 (YYYYMMDD). 예: 20260530"`

**Chain 8 / pre-flight (d) prefetchManifest 미존재**:
`"{date} 의 prefetchManifest.json 이 없습니다. 데이터 수집을 먼저 실행해주세요 (SCAN_PREFETCH_ONLY)."`

---

## §10. 표현 정책 (PRD §7.3 / FR-8.2/8.3 / B-23)

| (O) 권장 | (X) 금지 |
|---|---|
| `"기술적 완성도가 높은 종목"` | `"매수 추천"` |
| `"필터 조건을 충족한 종목"` | `"이 종목을 사세요"` |
| `"선별 결과"` | `"유망 종목"` |
| `"5-Stage 통과"` | `"상승 예측"` |
|  | `"이익 보장"` |

상세 정책 및 면책 부착 규칙은 `disclaimer.md` 참조.

---

## §11. Jargon 금지 (Step 1 §Style Guide (d))

사용자 메시지 본문에 노출 금지:
- `return_code`, `HTTPError`, `JSON 스키마`, `ka10171`, `stage_idx`, `traceback`, `exc.__name__`

상위 개념어로 치환:
- "조건검색 서버", "수집 단계", "데이터 파일", "예외 분류"

영어 stderr / exit code / traceback은 `기술 정보:` 라벨로 접어서 부착 (한국어 요약이 항상 본문 첫 줄).
