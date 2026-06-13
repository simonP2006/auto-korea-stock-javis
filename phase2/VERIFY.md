# Phase 2 적대 검증 보고서 (VERIFY)

- 검증자: Phase 2 적대 검증관 (subagent)
- 일시: 2026-06-13 (KST)
- 대상: `phase2/timing-fix.md` · `phase2/manual.md` · `phase2/state-paths.md` (+ 산출물 `docs/AKSJ-USER-MANUAL.md`)
- 방법: 전 항목 실측 재실행 (pytest 재실행, grep 재실측, 코드/문서 직독, tar 추출 해시 대조). git 미접촉(작업트리만), 원본 두 구repo 미접촉, 시크릿 미출력.
- **종합 판정: PASS_WITH_NOTES** — 5개 항목 중 4개 완전 PASS, ②는 실질 PASS이나 분류표에 경미한 누락 1건(아래 N-1).

---

## ① engine pytest 재실행 — PASS

```
cd /Users/tajun/spJavis/auto-korea-stock-javis/engine && .venv/bin/python -m pytest tests/ -q
→ 305 passed in 9.47s
```

- timing-fix.md §3① "305 passed in 9.44s", state-paths.md §4 "305 passed in 9.51s"와 **건수 일치(305 green, 실패 0)**. 소요 초 차이는 정상 변동.

## ② "10-15분" 잔여 grep ↔ 분류표 1:1 — PASS (누락 1건 노트)

repo 전역 재실측 (`grep -rn "10-15분|10~15분|10-15"` *.md/*.py/*.json, phase2/ 제외) + 별도 `30분|30-min` grep (engine 살아있는 문서·스킬·src):

| 분류표 항목 | 실측 결과 | 판정 |
|---|---|---|
| A-1 background-execution.md §7 영문 verbatim | :112-113 ADR-012 원문 인용 + :119 보정 노트 — **정확히 그 두 곳뿐** | 일치 |
| A-2 formulas.py `[30분]` 도메인 표기 | :37, :74, :114 — 30분봉 차트 타임프레임, engine src 내 다른 "30분" 0건 | 일치 |
| B-1 루트 CLAUDE.md §3 경고문 | :57 존재. "Phase 2-1에서 보정 예정" 문구가 stale인 점도 보고서 §5.1이 스스로 정확히 적시 | 일치 |
| B-2 EXECUTION_REPORT.md | :35, :70 | 일치 |
| B-3 phase1/VERIFY.md · root-router.md | 존재 (인용) | 일치 |
| B-4 factory/prompt/** "10개 파일" | 실 runtime 추정치 파일 = 정확히 10개 (workflow.md · workflow-idea.md · step-4/5/6/11 en+ko 8개) | 일치 (노트 N-2) |
| B-5 factory/docs/integrated-user-command-manual.md | :180,343,458,459,464,493,494,632,641,649 잔존 — 범위 외 선언대로 미수정 | 일치 |
| 핵심 주장 "범위 내(engine 살아있는 문서·스킬) 0건" | engine/CLAUDE.md · stock-scan 스킬 전체에서 한국어 "10-15분"/"30분" **0건 재확인** (A-1 영문 인용 제외) | **확인** |

**N-1 (분류표 누락 — 경미)**: `factory/docs/architectural-decision-records.md:89`의 영문 `10-15+ min runtime`(ADR-012 Context 원문)이 분류표에 없다. 성격은 A-1(ADR-012 verbatim)·B-5(factory 레거시 문서)와 동일해 실질 위험 0이나, "잔여 발생처 분류표"의 완전성 주장에는 구멍이다. 후속 표 1행 추가 권고.

**N-2 (집계 뉘앙스)**: factory/prompt/** 에서 "10-15분/min" 문자열을 포함한 파일은 총 12개 — B-4의 10개(스캔 runtime 추정치) 외에 `prd-research/round-01/raw/T03`(운영자 일일 사용 시간)·`round-02/raw/T04`(비기술 사용자 셋업 시간) 2개는 **스캔 runtime이 아닌 맥락**이라 B-4 서술("빌드 당시 추정치")과는 부합하나, 위치 버킷(factory/prompt/**) 기준 집계와는 어긋남. 동결 구역이라 실무 영향 없음.

**참고**: `docs/AKSJ-USER-MANUAL.md:57`에도 "10-15분"이 등장하나 B-1과 동일한 stale 경고 인용(과업 2-2 신설 문서)이며 분류표(과업 2-1a) 시점상 대상 아님.

## ③ factory 살아있는 문서 구경로 8히트 해소 — PASS

- 구경로 리터럴 grep (`/Users/tajun/spJavis/kiwoom-rest-trader`, `/Users/tajun/spJavis/AgenticWorkflow…`): `factory/docs/*` · `factory/AGENTS.md` · `factory/CLAUDE.md` = **0히트** (실측).
- 신경로(`auto-korea-stock-javis`) grep = **정확히 8라인**: integrated-user-command-manual.md **:199, :200, :642, :643, :678(ROOT 정의점), :687(KRT_ROOT 정의점)** + architectural-decision-records.md **:10(후행 `/` 보존 확인)** + AGENTS.md **:1281**.
- `phase1/paths-factory.md` §5 I-A가 특정한 8히트(파일:라인)와 **1:1 일치**. "kiwoom-rest-trader (자식)"·"키움 REST 기반 주식 스크리너(kiwoom-rest-trader)" 등 **명칭 서술은 불변** 확인 (경로 리터럴만 치환 원칙 준수).
- `factory/prompt-runner/logs/`에 구 절대경로 다수 잔존하나, 이는 paths-factory.md §3에서 "역사 보존(인벤토리 제외 영역)"으로 기 분류된 러너 실행 로그 — **살아있는 문서 아님, 8히트 범위 밖** (정합).

## ④ 신설 매뉴얼 직독 — PASS (모순 0 · 창작 0)

`docs/AKSJ-USER-MANUAL.md` 전문을 engine/CLAUDE.md · 루트 CLAUDE.md · engine docs · 코드와 대조:

| 검증점 | 방법 | 결과 |
|---|---|---|
| 14 Intent 표 "원문 그대로" | 매뉴얼 :69-84 ↔ engine/CLAUDE.md :18-33 `diff` | **byte-identical** |
| 경로 | engine·factory 경로 ↔ 루트 CLAUDE.md §1 | 일치 |
| 시간 | 80분~6시간 / 7시간 watchdog / run_filters <3분 ↔ 루트 §3 표·engine :13·:137 | 일치 |
| 명령 실재 | `scripts/run_full_research_flow.py`·`run_prefetch.py`·`run_filters.py`·`Filter_condition_update.py` 존재 확인 | 전부 실재 |
| "날짜 생략 시 오늘" | run_full_research_flow.py:53 (`sys.argv[1] if len>1 else None`) + user_command_manual.md:7-8 | 코드 일치 — 창작 아님 |
| Stage 2-1 +15% 각주¹ | `chartDayPreFilter.py:51 _DAILY_SURGE_THRESHOLD = 0.15` (라인 번호까지 정확) | 일치 |
| Stage 3 밴드 각주¹ | `chartDayFilter.py:68-69 = -0.15 / 0.50` | 일치 |
| Stage 1·2·5 서술 | chart60_120(Type A~ + 4선 정배열)·chart240(최근 3봉 MA60≥MA306×0.975)·finance(당기순이익<0 제외) 코드 직독 | 일치 |
| 에러 9종 표 | 매뉴얼 :181-189 ↔ engine/CLAUDE.md :76-84 | 행 단위 일치 |
| 종료 코드 0/1/2 | user_command_manual.md:10 | 일치 |
| masterReference 보존 | `organizedCompany/saveReport/plain_text.py:77-81` (없을 때만 생성, 기존 보존 분기 실재) | 일치 — fix-1-5 반영 정확 |
| append·공백 구분(콤마 불가)·break 규칙·격리 규칙 | user_command_manual.md :69, :83, :294, :318-330 | 전부 일치 |
| 증상표 각주² (30분→7시간 정정 인용) | factory §3.9 원문 :592 "스캔이 30분 넘게 안 끝남" 실재 — 각주가 원문을 정확히 식별·정정 | 일치 |
| factory §3.2 정오 노트 인용 | integrated manual :349 (0.15 / -0.15/0.50) 실재 | 일치 |
| TS-1~5 요지 | engine/CLAUDE.md :60-67 | 값-동등 |
| 시크릿 §⑦ | 루트 §4 3개 항목 동일 + 4번째 항목(인증 실패 시 에디터 점검)은 §4 노출금지 원칙의 파생 안내 — **모순 아님, 새 시스템 동작 주장 아님** | 모순 0 |
| 세션 오픈 위치 | 본문=루트 오픈 + 참고박스=engine 오픈(루트 §5·§6) 병기 — 루트 라우터가 사용 발화를 engine으로 위임하므로 양립 | 모순 0 |

**판정: Intent 표·경로·시간 모순 0건, 창작된 명령·동작 0건.** 매뉴얼의 모든 수치·라인 인용을 실측했고 전부 적중했다.

## ⑤ screener_state.json 백업 + JSON 유효 + 키 — PASS

- **백업 실재**: Phase 0-6 1차 백업 `/Users/tajun/spJavis-tools/_backup/aksj-reports-20260613.tar.gz` (76,190,681 B) 존재. sha256 `eacc70c4…f27753` — `phase0/reports-backup.md` §3 기록과 **일치** (무결성 확인).
- **백업 내 JSON 유효**: tar에서 `reports/screener_state.json` 추출(`tar -xzO`, 무수정) → `json.loads` 성공, 4키 정상.
- **라이브 파일과 대조**: 백업본 sha256 `3fab754d…9e9011b` = 라이브 `engine/reports/screener_state.json` sha256 — **byte-identical** (백업 후 변경 0, state-paths.md "1바이트도 수정 안 함" 주장과 정합).
- **키·값 정상**: `last_scan_date`=20260611 · `last_param_changes`=[] · `current_backup_files`=[] · `last_results_summary`(scan_date/passed_count=22/by_stage 120→107→89→41→27→22/note) — state-paths.md §5 표와 전건 일치.
- `*.bak.*` 사이드 백업은 없음 — 과업 2-3이 무수정이었으므로 백업 의무 미발동(state-paths.md §3 선언과 정합). 별도 `aksj-stageMasterFilter_state-20260613.tar.gz`(1,309 B)도 실재.

---

## 결론·후속 권고

1. **3개 보고서의 핵심 주장 전부 실측 재현됨** — 날조·과장 수치 미발견. 보고서들이 스스로 한계(루트 §3 stale 문구, 범위 외 잔존)를 적시한 점도 정확.
2. 후속 1줄 작업 2건 (마스터 결정 사항):
   - (a) timing-fix.md §4 분류표에 `factory/docs/architectural-decision-records.md:89` 1행 추가 (N-1).
   - (b) 루트 CLAUDE.md §3 "Phase 2-1에서 보정 예정" → "보정 완료(phase2/timing-fix.md)" 갱신 (timing-fix.md §5.1 기 권고).
3. state-paths.md §6의 역사 문서 3개(구경로 6건)는 보고대로 상태/감지 경로와 무관 — 치환은 후속 과업 판단 유지.
