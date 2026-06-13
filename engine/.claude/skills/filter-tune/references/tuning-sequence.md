# Tuning Sequence — 상세 (Master Sequence + 6 Branches + Error Handlers + Regex Catalogue)

> SKILL.md §3·§4의 long-form companion. 모든 spec verbatim과 Korean string은 SKILL.md에 normative — 본 파일은 implementer가 작업 시 참조하는 narrative + flow chart + 회복 handler.

---

## §A. Master Sequence — `PARAM_CHANGE(param_id, new_value)` (8-step + SHORTCUT)

### Flow chart (informative)

```
User: "Type A 허용오차 -5%로 완화해줘"
  │
  ▼
Step 0 [TS-4]  multi-param 감지                              ──┐ if multi → warn + AskUserQuestion
  │                                                            │ if proceed → loop Steps 1-8 per param
  ▼                                                            │
Step 1 [B-9, TS-3]                                             │
  ├─ Step 1.0 keyword pre-check (Review#3, PRIMARY guard)      │
  │     cup_nga / 당기순이익 / financeFilter / Stage 5 키워드  │
  │     → C-4 REJECT, turn 종료                                │
  ├─ Step 1.1 catalog resolution (parameter-catalog.md)        │
  │     실패 시 §5 anti-conflation 우선, 그래도 모호 → AUQ    │
  ├─ Step 1.2 Stage 5 hard-block (catalog → SECONDARY guard)   │
  │     financeFilter 소유 → C-4 verbatim REJECT, 종료         │
  └─ Step 1.3 Range Map lookup + check                         │
        in-range / not danger → 진행                           │
        in danger → Korean warn + AUQ                          │
        out-of-range → REJECT (override 불가)                  │
  ▼                                                            │
Step 2 [B-17]  shared constant 영향 공개                       │
  ├ shared (`_ALIGN_TOL_LOOSE` 유일) → 4-tuple verbatim list   │ (SHORTCUT: in-range AND private →
  └ private → skip                                             │  Steps 2-3 silent, 시퀀스 0→1→4→5→6→7→8)
  ▼                                                            │
Step 3 [B-10]  masterReference.log gap 추정 (ADR-009)          │
  ├ 부재/empty → "추정 데이터 없음"                            │
  ├ N/M < 0.5 → "추정 데이터 부족"                             │
  └ 정상 → "{M}개 중 {N}개 추출. {delta} {direction}..."        │
  ▼                                                            │
Step 4 [B-7]  confirmation 표 + AskUserQuestion                │
  ├ 적용 → Step 5                                              │
  ├ 다른 값 → 새 값 → Steps 1-4 loop                           │
  └ 취소 → "변경을 취소했습니다." abort                        │
  ▼                                                            │
Step 5 [B-8, TS-2, TS-2a, R-9]                                 │
  ├ R-9 lock acquire — mkdir filter-tune.lock (atomic)         │
  │     실패 → BLOCKED Korean + abort exit 2                   │
  ├ cp .bak.$(date +%Y%m%d_%H%M%S) — TS-2                      │
  ├ ls -t .bak.* count > 5 → grep tuning-log gate (TS-2a)      │
  │     매치 → rm oldest / 미매치 → KEEP + warn                │
  └ screener_state.current_backup_files append                 │
  ▼                                                            │
Step 6  Edit Final 상수 값                                      │
  ├ R-2/B-13e: grep -n '\b{var}\b' → 0 hits → fuzzy fallback   │
  ├ Final[ 검증 (line containing matched var)                  │
  ├ unit-conversion.md 적용 → new_value literal                │
  └ adjacent `# 이전: {old}` comment auto-update (idempotent)  │
  ▼                                                            │
Step 7 [B-16]  tuning-log + state + lock release               │
  ├ 8-column verbatim row append:                              │
  │   | datetime | param_id | param_name | old_value | new_value |
  │     stocks_passed_before | stocks_passed_after | notes |    │
  ├ wc -l 헤더 제외 ≥ 200 → tuning-log.YYYYMM.md rotate         │
  ├ state.json last_param_changes append (confirmed=false)     │
  └ rmdir filter-tune.lock — Step 5와 대칭 (try/finally)       │
  ▼                                                            │
Step 8 [TS-5]  rerun 제안                                       │
  └ "변경 적용됐습니다. 필터를 다시 돌려볼까요? (run_filters 동기 실행 — 보통 1-3분 소요)"
  ▼
END (main thread가 stock-scan RERUN_FILTERS routing)
```

### Step-by-step checkpoint

각 Step의 "내부 검증 항목":

**Step 0**:
- [ ] 사용자 message tokenize.
- [ ] catalog 한국어 alias / `_VAR_NAME` 매치 횟수 카운트.
- [ ] 연접 절(`그리고/또/도/와/,`) 검사.
- [ ] count ≥ 2 → multi-param 분기.

**Step 1.0 (keyword pre-check)**:
- [ ] 원본 발화 lower-case 사본에서 5개 키워드 substring 스캔.
- [ ] `순이익` + 변경의도 동사 공존 여부.
- [ ] 매치 시 C-4 verbatim → exit.

**Step 1.1 (catalog)**:
- [ ] `references/parameter-catalog.md` 한국어 alias 테이블 lookup.
- [ ] 모호 발화 → `references/shared-constants.md` look-alike pair 우선.
- [ ] 여전히 모호 → AskUserQuestion (4옵션: 후보 3 + 취소).

**Step 1.2 (Stage 5 secondary)**:
- [ ] 해소된 `param_id` 의 owning module 확인.
- [ ] `financeFilter.py` → C-4 verbatim exit.

**Step 1.3 (Range)**:
- [ ] `references/range-map.md` row lookup.
- [ ] new_value vs physical_range, danger_zone 비교.
- [ ] danger_zone hit → Korean warn template substitute + AUQ.
- [ ] out-of-range hit → Korean REJECT template substitute + exit.

**Step 2**:
- [ ] `references/shared-constants.md` §1 lookup.
- [ ] `_ALIGN_TOL_LOOSE` → 4-tuple verbatim list emit.
- [ ] 그 외 → skip.

**Step 3**:
- [ ] `screener_state.last_scan_date` → `${KRT_REPORTS}/{date}/masterReference.log`.
- [ ] fallback: glob newest mtime.
- [ ] 부재/empty → "추정 데이터 없음" advisory.
- [ ] regex 카탈로그(§D)로 (actual, threshold, unit) 추출.
- [ ] would_pass(new_value) 재계산.
- [ ] N/M < 0.5 → "추정 데이터 부족".
- [ ] 정상 → delta + direction Korean line.

**Step 4**:
- [ ] confirmation 표 헤더 + 1-row.
- [ ] tolerance: `-X.X% (×Y.YYY, raw=Z.ZZZ)` 동시.
- [ ] ratio: `Z%` (raw).
- [ ] integer: bare (`2일`).
- [ ] Appendix: Step 2 영향 / Step 3 delta.
- [ ] AUQ 3옵션.

**Step 5**:
- [ ] `mkdir ${KRT_REPORTS}/filter-tune.lock 2>/dev/null` → exit code 분기.
- [ ] BLOCKED → Korean + exit 2.
- [ ] `cp ${KRT_FILTERS}/{file} ${KRT_FILTERS}/{file}.bak.$(date +%Y%m%d_%H%M%S)`.
- [ ] `ls -t .bak.*` count > 5 → grep tuning-log + 아카이브 → 매치 rm / 미매치 KEEP+warn.
- [ ] state.json `current_backup_files` append + 회전 path 제거.

**Step 6**:
- [ ] `grep -n '\b{var}\b' ${KRT_FILTERS}/{file}` 결과 분기.
- [ ] 0 hits → fuzzy fallback `grep -in '{trimmed}'`.
- [ ] ≥1 hits → matched line의 `Final[` substring 확인.
- [ ] `references/unit-conversion.md`로 user_pct → raw literal 변환.
- [ ] **[자동 검증]** tolerance 계열이면 Edit 직전 `${KRT_PYTHON} .claude/skills/filter-tune/scripts/unit_conversion.py --verify {new_literal} {부호포함_user_pct}` → exit 1 시 Edit 중단·재계산 (SKILL §11).
- [ ] `Edit(old_string=…Final[type] = {old}…, new_string=…Final[type] = {new}…)`.
- [ ] 직전 라인 `# 이전:` 패턴 → 2차 Edit으로 갱신/추가.

**Step 7**:
- [ ] datetime KST ISO 8601.
- [ ] stocks_passed_before = state.last_results_summary.passed_count (또는 null).
- [ ] stocks_passed_after = `pending` (transient — filter-tune이 이후 backfill; stock-scan 미작성).
- [ ] notes = `{motivation} | 미확정`.
- [ ] `>>` append (헤더 부재 시 헤더 선재 작성).
- [ ] `wc -l ${KRT_REPORTS}/tuning-log.md` 헤더 제외 → ≥ 200 시 rotate.
- [ ] state.json append: `{date, param, old, new, file, confirmed:false}`.
- [ ] `rmdir ${KRT_REPORTS}/filter-tune.lock` (try/finally — 실패 path에서도).

**Step 8**:
- [ ] Korean prompt verbatim emit.
- [ ] main thread 제어 반환 (CLAUDE.md routing이 RERUN_FILTERS 라우팅 담당).

---

## §B. Branch Detail (6 branches)

### §B.1 `SHOW_PARAMS(stage?)` flow

```
parse stage hint → resolve target Stages
  ├ "Stage 5 어떻게 바꿔" 변경의도 → Step 1.5 C-4 안내 + read-only 요약
  ├ "전체" / 없음 → 5 Stage 표 sequential
  └ 특정 Stage → 해당 모듈 단일 표

각 Stage:
  grep -n 'Final\[' ${KRT_FILTERS}/{module}.py → 전체 Final 변수 enumerate
  grep -n '_VAR_NAME' → 현재 literal 추출
  Korean 5-column 표 (ID / 변수명 / 현재 값 / 의미 / 이론적 근거)
  공유 변수 행에 ⚠️공유 marker

footer:
  references/parameter-catalog.md cross-reference
  UX nudge: "파라미터 변경은 ... 같이 말씀해주세요."
```

### §B.2 `CHANGE_PARAM` → §A master sequence (defer)

### §B.3 `CONFIRM` flow

```
read screener_state.last_param_changes
  ├ 최신 confirmed=false 행 → 진행
  └ 없음 → "확정할 미확정 변경 이력이 없습니다." + 종료

tuning-log.md (또는 archive)에서 datetime 매치 행 → notes에 "| ✓ 확정" suffix Edit
state.json confirmed=true 갱신 (atomic write)
ack verbatim: "현재 설정이 확정되었습니다."
```

### §B.4 `RESTORE` flow

```
Step 1: target file 해소
  ├ message hint → 단일 file_basename
  └ 모호 → AUQ (top-3 최근 last_param_changes)

Step 2a primary:
  ls -t ${KRT_FILTERS}/{file}.bak.* | head -1
  ├ non-empty → AUQ "가장 최근 백업({path}) 복원할까요?" (예/아니)
  │   예 → mkdir lock → cp .bak → rmdir lock
  │       tuning-log append "복원 (from {bak}) | ✓ 복원"
  │       state.json append confirmed=true
  │       ack: "{file}을 {ts} 시점 백업으로 복원했습니다."
  │   아니 → end
  └ empty → Step 2b fallback

Step 2b fallback (B-8 KEY FEATURE):
  read tuning-log.md + 모든 tuning-log.YYYYMM.md (oldest-first)
  filter rows where param_id == target
  identify chronologically LAST row before current → old_value column = restore target
  §5 B-13e var-name check
  AUQ "⚠️ 백업 파일이 없어 튜닝 로그에서 이전 값을 찾았습니다: {old}. Edit으로 직접 복원할까요? (.bak 부재 시 재변경 후 이전 값 복귀 불가)"
    ├ 진행 → mkdir lock → Edit → rmdir lock
    │   ack verbatim: "백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다. ({param_id}: {was} → {to})"
    │   tuning-log append "로그 기반 복원 (백업 부재) | ✓ 복원"
    ├ 다른 행 선택 → row picker AUQ
    └ 취소 → end

Step 2c both fail:
  Korean: "{param_id}의 백업도, 변경 이력도 찾을 수 없습니다. 현재 값이 최초 설정값으로 보입니다. 참조용 PRD §5.1 카탈로그 값({prd_default})으로 강제 복원하시겠습니까?"
  AUQ 수락 → 정방향 PARAM_CHANGE (master sequence Steps 0-8) with new_value=prd_default
```

### §B.5 `THEORY_GUIDE` flow

```
parse context: theory name / Stage / market regime (강세|약세|횡보)
read references/theory-guide.md 매칭 섹션 verbatim
시장 regime 감지 시:
  강세 → 정배열 완화 + 과열 강화 트랙
  약세 → §2.2 패턴 C 수비 vs 기회 양 트랙 + "어느 방향으로 가시겠습니까?"
  횡보 → VCP 강조 트랙
구체 param 명시 시: §3 권장 범위 표 인용
```

### §B.6 `ASK_MODULE` flow

```
match user input vs 9 active modules + Filter_condition_update.py
emit references/parameter-catalog.md §Module Index 행 (역할 + Phase 1 상태)
stageMasterFilter.py → Phase 2 deflection verbatim
financeFilter.py → ⚠️ Phase 2 hardcoded 안내 (변경 의도 없으면 informational, 있으면 C-4 redirect)
```

### §B.7 `COMPARE_EXPERIMENTS` flow

```
read tuning-log.md + (scoped: tuning-log.YYYYMM.md archives)
filter scope: 이 세션 / 오늘 / 이번 달
render 6-column Korean 비교 표 (#, 시각, param, 변경 전→후, 통과 변화, 비고)
narrative summary:
  read-time backfill: 최신 pending 행을 screener_state.last_results_summary로 해소 (scan_date 게이트, turn당 ≤1행)
  max stocks_passed_after row (해소된 행만) → "가장 통과 종목 많았던 설정" (FR-8 — 투자 추천 아님)
  ✓ 확정 행 highlight
  잔여 pending/미측정 row → advisory
disclaimer 1-line: "(투자판단·책임은 본인에게 있습니다)"
```

---

## §C. TS-1~5 Enforcement Matrix (per step / per branch)

| Step / Branch | TS-1 | TS-2 | TS-2a | TS-3 | TS-4 | TS-5 | R-9 | C-4 (Stage 5) |
|---|---|---|---|---|---|---|---|---|
| §A Step 0 | — | — | — | — | ✅ multi-param 감지 | — | — | — |
| §A Step 1.0 | — | — | — | — | — | — | — | ✅ PRIMARY |
| §A Step 1.1 | — | — | — | — | — | — | — | — |
| §A Step 1.2 | — | — | — | — | — | — | — | ✅ SECONDARY |
| §A Step 1.3 | — | — | — | ✅ range / danger 검증 | — | — | — | — |
| §A Step 2 | — | — | — | — | — | — | — | — |
| §A Step 3 | — | — | — | — | — | — | — | — |
| §A Step 4 | — | — | — | — | — | — | — | — |
| §A Step 5 | — | ✅ cp .bak | ✅ ≤5 + tuning-log gate | — | — | — | ✅ acquire (mkdir) | — |
| §A Step 6 | ✅ Final[ 검증 + var-name | — | — | — | — | — | — | — |
| §A Step 7 | — | — | ✅ rotation cross-ref archives | — | — | — | ✅ release (rmdir) | — |
| §A Step 8 | — | — | — | — | — | ✅ rerun prompt | — | — |
| §B.1 SHOW_PARAMS | — | — | — | — | — | — | — | ✅ Step 1.5 |
| §B.3 CONFIRM | — | — | — | — | — | — | — | — |
| §B.4 RESTORE | ✅ Final[ on Edit | — | — | — | — | — | ✅ Step 2a/2b | — |
| §B.5 THEORY_GUIDE | — | — | — | — | — | — | — | — (informational) |
| §B.6 ASK_MODULE | — | — | — | — | — | — | — | ✅ financeFilter 행 안내 |
| §B.7 COMPARE_EXPERIMENTS | — | — | — | — | — | — | — | — |

**Stage 5 hard-block coverage 합계 = 4 위치** (§A Step 1.0 + §A Step 1.2 + §B.1 Step 1.5 + §B.6 financeFilter row).

---

## §D. ADR-009 Gap-Extractor Regex Catalogue

Step 3 [B-10]이 `masterReference.log` 줄에서 `(actual, threshold, unit)` 추출 시 사용. 5개 dominant reason format:

| 패턴 키 | 예시 reason text | named groups |
|---|---|---|
| `MA_ALIGNMENT` | `"MA60(7,195) < MA306×0.965(7,198)"` | `actual=7195`, `threshold=7198`, `unit=원` |
| `MA_BAND_PCT` | `"종가(2,500) vs MA612(1,629.58) +53.41% — 밴드 [-15.0%, +50.0%]"` | `actual_pct=53.41`, `lower=-15.0`, `upper=50.0` |
| `DAILY_SURGE` | `"금일 일봉 +16.44% — 15% 이상 급상승"` | `actual_pct=16.44`, `threshold_pct=15.0` |
| `INVESTOR_CONSEC` | `"외국인 3회 연속 매도 (≥ 2)"` | `actual_days=3`, `threshold_days=2` |
| `FINANCE_CUP_NGA` | `"당기순이익 -70억원 < 0 (적자)"` | `actual_won=-70`, `threshold_won=0` |

### Worked example — MA_ALIGNMENT

```
입력 line: "MA60(7,195) < MA306×0.965(7,198) — Type A 정배열 실패"
regex: r"MA60\((?P<actual>[\d,]+)\)\s*<\s*MA306×(?P<mult>[\d.]+)\((?P<threshold>[\d,]+)\)"
추출: actual=7195, mult=0.965, threshold=7198 → tolerance 0.035 (current).
new tolerance 0.05 적용 시 threshold' = MA306 × 0.95 → would_pass 재계산.
```

### Worked example — INVESTOR_CONSEC

```
입력 line: "외국인 3회 연속 매도 (≥ 2)"
regex: r"외국인 (?P<actual>\d+)회 연속 매도 \(≥\s*(?P<threshold>\d+)\)"
추출: actual=3, threshold=2.
new threshold 4 적용 → would_pass = (actual=3 < 4) = True (= 통과).
원래 actual=3 ≥ 2 → 제외였음. → "추가 통과 예상" 1건.
```

집계:
```
parsed_total = N parsed / M total rows
delta = count(would_pass | new) - count(would_pass | current)
Korean line: "masterReference.log {M}개 행 중 {N}개에서 gap 추출. {delta} {direction} (추정 정확도 {N/M*100:.0f}%)."
N/M < 0.5 → "추정 데이터 부족" advisory만, delta 미제공.
```

---

## §E. Error Recovery Handlers

| 시나리오 | 트리거 | 회복 동작 |
|---|---|---|
| **R-9 lock contention** | Step 5 mkdir 실패 (EEXIST) | Korean: `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."` exit 2. 사용자 재시도 시 stale lock 의심되면 `ls -ld ${KRT_REPORTS}/filter-tune.lock` mtime 노출 후 수동 `rmdir` 가이드. |
| **R-7 state.json 손상** | `json.JSONDecodeError` 캐치 | `mv screener_state.json screener_state.json.corrupt.$(date +%s)`. Skill은 default empty arrays로 계속. CLAUDE.md가 사용자-facing 안내 (B-12 표면). |
| **B-13e var-name not found** | Step 6 grep 0 hits | fuzzy fallback `grep -in '{trimmed}'` → top-3 후보 Korean 렌더 + AUQ. 미해결 시 abort + Korean `"변수명을 확인할 수 없어 변경을 취소했습니다."`. |
| **B-8 백업 + 로그 모두 부재** | RESTORE Step 2c | PRD §5.1 catalog default로 강제 복원 → 사용자 명시 승인 시 forward PARAM_CHANGE. |
| **Edit failure (file write error)** | Edit tool exception | lock 즉시 rmdir (finally). state.json rollback (append하지 않음). Korean `"Edit 실행 중 오류 — 변경이 적용되지 않았습니다. 기술 정보: {exc}"` |
| **tuning-log append 실패** | `>>` IO error | lock rmdir (finally). 백업은 이미 생성됨 → 사용자에게 수동 entry 작성 가이드 + RESTORE primary 안내. |
| **rotation 도중 충돌** | mv 실패 | lock rmdir (finally). Korean `"로그 회전 중 오류 — tuning-log.md 일관성 점검 후 재시도 권장."`. |
| **Backup 디렉터리 권한 거부** | `cp` IO error | lock rmdir (finally). Korean `"백업 파일 생성 권한이 없습니다. ${KRT_FILTERS} 권한을 확인해주세요."` |

**lock release invariant**: 모든 error path가 `rmdir ${KRT_REPORTS}/filter-tune.lock`을 try/finally semantic으로 호출해야 stuck-lock 방지.

---

## §F. Korean Message Library (verbatim, 번역 검토용 consolidated)

본 섹션은 사용자-facing 한국어 string 전체를 한 곳에 모아 번역 일관성을 검토할 수 있게 한다 (FR-8 framing pass).

### TS-4 multi-param 경고
- `"한 번에 하나씩 변경을 권장합니다. 동시에 여러 파라미터를 바꾸면 어느 변경이 결과에 어떤 영향을 줬는지 분리하기 어렵습니다. 어떻게 진행하시겠습니까?"`
- 옵션: `"하나씩 차례대로 변경하기"` / `"한 번에 모두 변경하기 (영향 추적 불가)"` / `"취소"`
- 진행 prompt: `"{param_id}_N 변경이 완료됐습니다. 다음 파라미터({param_id}_N+1)를 계속 진행할까요?"`

### Stage 5 hard-block (C-4)
- `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. 당기순이익 판정(cup_nga < 0)이 하드코딩 비교문이고 Final 상수가 존재하지 않습니다. Phase 2에서 상수화를 검토합니다."`
- SHOW_PARAMS 변경의도 동반: `"Stage 5는 현재 코드 구조상 파라미터 변경이 불가합니다. Phase 2에서 상수화를 검토합니다."`

### TS-3 range
- danger zone: `"허용오차 -{X}%면 사실상 필터가 무력화됩니다. 정말 이 값으로 진행할까요?"` 옵션 `"그대로 진행"` / `"안전 범위 권장값({suggested})으로 변경"` / `"취소"`.
- out-of-range REJECT: `"{param_korean_name}의 물리적 범위는 {range_min} ~ {range_max}입니다. 입력하신 {new_value}는 범위를 벗어났습니다. (이론적 근거: {basis})"`

### B-17 공유 상수 경고
- `"⚠️ 이 상수는 공유 상수입니다. 변경 시 다음 조건들이 동시에 영향을 받습니다:`
- ` • Type B — 120분 MA10-MA20 근접 판정`
- ` • Type B — MA60-MA306 근접 판정`
- ` • Type C — MA60-MA306 장기추세 leg`
- ` • Type D — 60분 4선 정배열 fallback`
- `특정 Type만 조정하려면 해당 Type 전용 상수 신설이 필요합니다 (TS-1 로직 변경 — 사용자 명시적 승인 필요)."`

### B-10 gap 추정
- `"masterReference.log {M}개 행 중 {N}개에서 gap 추출. {delta} {direction} (추정 정확도 {N/M*100:.0f}%)."`
- 부재: `"추정 데이터 없음 — masterReference.log이 비어있거나 부재합니다. 정확한 영향은 변경 후 run_filters 재실행으로 확인하세요."`

### B-7 confirmation
- 옵션 (AUQ): `"적용 (Edit 진행)"` / `"다른 값으로 시도"` / `"취소"`.
- 새 값 prompt: `"새로운 값을 입력해주세요"`.
- 취소 ack: `"변경을 취소했습니다."`

### R-9 lock
- BLOCKED: `"⚠️ 다른 파라미터 변경 작업이 진행 중입니다. 잠시 후 다시 시도해주세요."`
- stock-scan 사이드: `"⚠️ 파라미터 변경 중이라 스캔을 시작할 수 없습니다. 변경이 끝난 뒤 다시 시도해주세요."`

### TS-2a rotation
- KEEP+warn: `"백업 {N}개 한도를 초과했지만 가장 오래된 백업이 튜닝 로그에 기록되지 않아 보존합니다. 수동 정리를 권장합니다."`

### B-13e var-name
- REJECT (not Final): `"이 변수는 Final 타입이 아닙니다. TS-1에 따라 변경할 수 없습니다."`
- fuzzy fallback: `"⚠️ '{variable_name}' 변수를 찾지 못했습니다. 변수명이 변경된 것 같습니다. 다음 후보들이 있습니다: • {c1} (line {N1}) • {c2} (line {N2}) • {c3} (line {N3}) 어떤 변수를 변경할까요?"`

### TS-5 재실행 제안
- `"변경 적용됐습니다. 필터를 다시 돌려볼까요? (run_filters 동기 실행 — 보통 1-3분 소요)"`
- 거부 시: `"알겠습니다. 필요할 때 \"필터 재실행\"이라고 말씀하시면 됩니다."`

### CONFIRM
- ack verbatim: `"현재 설정이 확정되었습니다."`
- 없음: `"확정할 미확정 변경 이력이 없습니다."`

### RESTORE
- primary AUQ: `"가장 최근 백업({backup_path})에서 복원합니다. 진행할까요?"`
- primary ack: `"{file_basename}을 {backup_timestamp} 시점 백업으로 복원했습니다."`
- fallback AUQ: `"⚠️ 백업 파일이 없어 튜닝 로그에서 이전 값을 찾았습니다: {old_value_in_log}. Edit으로 직접 복원할까요? (.bak 파일이 없으므로 다시 변경하면 이 단계 이전 값으로는 돌아갈 수 없습니다.)"`
- fallback ack: `"백업 파일이 삭제되었으나 튜닝 로그에서 이전 값을 복원했습니다. ({param_id}: {current_was} → {restored_to})"`
- both-fail: `"{param_id}의 백업도, 변경 이력도 찾을 수 없습니다. 현재 값이 최초 설정값으로 보입니다. 참조용 PRD §5.1 카탈로그 값({prd_catalog_value})으로 강제 복원하시겠습니까?"`

### ASK_MODULE Phase 2 deflection
- `"stageMasterFilter.py는 별도 누적-확장 풀(positive coverage) 산출용 모듈입니다. 현재 5-Stage 파이프라인과 독립적으로 동작하며, Phase 1에서는 파라미터 튜닝 대상에서 제외됩니다. Phase 2 안정화 이후 검토 예정입니다."`

### THEORY_GUIDE 약세장 종료
- `"어느 방향으로 가시겠습니까?"`

### COMPARE_EXPERIMENTS 면책
- `"(투자판단·책임은 본인에게 있습니다)"`

### SHOW_PARAMS footer
- `"파라미터 변경은 \"{변수명}를 {새값}으로 바꿔줘\" 같이 말씀해주세요."`
