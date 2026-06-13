# Phase 2 — 과업 2-2 작성 근거: factory 잔여 치환 + 통합 사용자 매뉴얼

- 일시: 2026-06-13
- 작업자: Phase 2 워커 (subagent)
- 범위: `/Users/tajun/spJavis/auto-korea-stock-javis` 내부만 (원본 두 구repo 미접촉). git commit/push 없음(작업트리만). 시크릿 미출력·`.env` 미접촉.

## A. factory 잔여 8히트 치환 (1-2b 이슈 I-A 해소)

근거 기준: `phase1/paths-factory.md` §5 I-A가 특정한 정확히 그 8히트(파일:라인)를 치환 전 grep으로 재실측 — **완전 일치 확인 후** 치환.

| 파일 | 라인 | 구경로 → 신경로 |
|---|---|---|
| `factory/docs/integrated-user-command-manual.md` | 199 | AW-구 → `…/auto-korea-stock-javis/factory` (저장소 지도 표) |
| 〃 | 200 | KRT-구 → `…/auto-korea-stock-javis/engine` (저장소 지도 표) |
| 〃 | 642 | KRT-구 → engine (daily-ops `cd` 복붙 명령) |
| 〃 | 643 | KRT-구 → engine (`.venv/bin/python` 복붙 명령) |
| 〃 | 678 | AW-구 → factory (§5.1 경로 상수 `ROOT` 정의점) |
| 〃 | 687 | KRT-구 → engine (§5.1 경로 상수 `KRT_ROOT` 정의점) |
| `factory/docs/architectural-decision-records.md` | 10 | KRT-구 → engine (ADR-001 Decision, 후행 `/` 보존) |
| `factory/AGENTS.md` | 1281 | KRT-구 → engine (§10 빌드 인스턴스 서술의 배포 경로 백틱 리터럴) |

- 치환 값: `ENGINE_ROOT = /Users/tajun/spJavis/auto-korea-stock-javis/engine`, `FACTORY_ROOT = /Users/tajun/spJavis/auto-korea-stock-javis/factory` — 1-2b와 동일 값(phase1/paths-factory.md 헤더 기준).
- 원칙 준수: **경로 리터럴만** 교체. "AgenticWorkflow (부모)"·"kiwoom-rest-trader (자식)"·"키움 REST 기반 주식 스크리너(kiwoom-rest-trader)" 같은 **명칭·역사 서술은 불변** (원문 의미 불변).
- 검증 (실측): 치환 후 `grep '/Users/tajun/spJavis/kiwoom-rest-trader\|/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector'` 3파일 = **0히트** (grep exit 1). 신경로 grep = 정확히 위 8라인에서 검출. integrated manual 내 `auto-korea-stock-javis` 카운트 = 6 (치환 6 = 4 KRT + 2 AW, I-A의 "(4+2)" 표기와 일치).

## B. 통합 매뉴얼 `docs/AKSJ-USER-MANUAL.md` — 섹션별 출처 맵

생성 위치: `/Users/tajun/spJavis/auto-korea-stock-javis/docs/AKSJ-USER-MANUAL.md` (docs/ 신설). 새 동작 창작 0 — 전 내용이 아래 출처의 값-동등 인용.

| 매뉴얼 절 | 내용 | 출처 (값-동등 인용원) |
|---|---|---|
| ① 한 장 요약 | engine=일일 스크리너 / factory=동결 공장, 일방향 문, prompt/ 동결 | 루트 `CLAUDE.md` 정체성·§2.2·§2.3; factory 통합 매뉴얼 §0.1·§1.4 |
| ② 매일 아침 운영 | 1줄 명령(`cd ${AKSJ_ROOT} && claude` → "오늘 스캔해줘") + 복붙판(`engine && .venv/bin/python -m scripts.run_full_research_flow $(date +%Y%m%d)`) + background 필수·80분~6시간·7시간 watchdog + 종료 코드 0/1/2 | 과업 지시 명령 원문; 루트 `CLAUDE.md` §3(실측표·10-15분 stale 경고)·§5·§6(engine에서 열기 권장 병기); engine `CLAUDE.md` Path Constants:13·Execution Template:137; engine `docs/user_command_manual.md`:10(종료 코드) |
| ③ 14 Intent 표 | engine/CLAUDE.md:18-33 표를 **문자 그대로 복사** (요약·재서술 없음) + 혼합/모호 규칙·"시작" 진입 | engine `CLAUDE.md` Intent Routing(:16-40) + Start Routing(:42-50) |
| ④ 결과 읽는 법 | researchedCompany=최종 집계, stage 깔때기 표(통과 파일 6종+break 규칙), masterReference 수기 기입 4단계+보존 | engine `docs/user_command_manual.md` §C(:78-87)·산출물 표(:301-316)·분기 규칙(:318-330); factory 통합 매뉴얼 §3.2·§3.7; 보존 사실 = `phase1/fix-1-5-overwrite.md`(plain_text.py 수정, 305 passed) |
| ⑤ 튜닝 루프 | `run_prefetch` 1회 → `run_filters` N회(API 0회·<3분) + Claude 루프 6단계 + TS-1~5 요지 | engine `docs/user_command_manual.md` §B(:36-59); factory 통합 매뉴얼 §3.6(Master Sequence·TS표)·§4.2(루프 — 시간만 실측 정정); engine `CLAUDE.md` Safety Rules(:60-67) |
| ⑥ 트러블슈팅 | 에러 9종 표 **engine/CLAUDE.md:74-84 원문 인용**(원인 칼럼 포함 — factory §3.9 축약판보다 충실) + 증상표(factory §3.9, 30분→실측 정정 각주) + 격리 규칙 | engine `CLAUDE.md` Error Classification; factory 통합 매뉴얼 §3.9; engine `docs/user_command_manual.md`:318-330 |
| ⑦ 시크릿 규칙 | .env 단일 보관·0600·example 플레이스홀더만·값 노출 금지 | 루트 `CLAUDE.md` §4 전문 |

## C. 출처 간 충돌 5건과 판정 (규칙: 코드/실측 우선)

| # | 충돌 | 판정·매뉴얼 표기 | 근거 |
|---|---|---|---|
| 1 | 소요 시간: factory §3.3/§4.2·engine 문서 "10-15분" vs 실측 "80분~6시간" | **80분~6시간** 채택, "10-15분 = stale" 경고 명기 | 루트 `CLAUDE.md` §3 (EXECUTION_REPORT 실측 인용) — 코드/실측 우선 |
| 2 | watchdog: factory §3.5 Chain 1 "30분" vs engine `CLAUDE.md`:137 "7시간" | **7시간** 채택, 증상표 원문 "30분" 행은 각주로 정정 인용 | 루트 `CLAUDE.md` §3 "기존 30분 watchdog도 비현실"; engine CLAUDE.md가 현행 |
| 3 | Stage 2-1 임계: engine user_command_manual:244 "+10%" vs 코드 `_DAILY_SURGE_THRESHOLD=0.15` | **+15% (0.15)** 채택, 각주¹ | **코드 실측** `engine/src/kiwoom/itemFilter/chartDayPreFilter.py:51` (grep) — factory §3.2 정오 노트와도 일치 |
| 4 | Stage 3 밴드: engine user_command_manual:251 "[-10%,+20%]" vs 코드 `-0.15/0.50` | **[-15%,+50%]** 채택, 각주¹ | **코드 실측** `engine/src/kiwoom/itemFilter/chartDayFilter.py:68-69` (grep) |
| 5 | masterReference 재스캔 거동: engine 문서 "③에서 빈 파일 자동 생성"(구버전은 항상 덮어씀) vs 수선 후 "없을 때만 생성·기존 보존" | **보존** 채택 — "이제 재스캔에도 보존됨" 명기 | `phase1/fix-1-5-overwrite.md` (TDD red→green, 전체 305 passed, plain_text.py 보존 분기) |

부수 판정: 세션 오픈 위치 — 과업 지시의 1줄 명령(루트에서 `claude`)을 본문 채택, 루트 `CLAUDE.md` §5·§6의 "일일 운영은 engine에서 열기" 권장은 참고 박스로 병기(두 출처 모두 보존, 충돌 아님 — 루트 라우터가 사용 발화를 engine으로 위임).

확인 못함(매뉴얼에 미기재·미단정): factory §3.5의 "로그 500행 초과 시 회전"·tuning-log "≥200행 회전" 등 스킬 내부 세부치는 코드 대조를 본 과업에서 수행하지 않아 매뉴얼 본문에서 제외(스킬 참조 문서 관할). 면책 문구·표현 정책은 engine CLAUDE.md 원문 그대로.

## D. 산출물·변경 파일 (git status 관할 외 — 작업트리만)

| 구분 | 파일 |
|---|---|
| 신규 | `docs/AKSJ-USER-MANUAL.md` (통합 매뉴얼) · `phase2/manual.md` (본 문서) |
| 수정 (8히트 치환) | `factory/docs/integrated-user-command-manual.md` (6) · `factory/docs/architectural-decision-records.md` (1) · `factory/AGENTS.md` (1) |

검증 요약: 구경로 리터럴 3파일 0히트(grep exit 1, 실측) · 치환은 경로 문자열만(명칭 서술 불변) · 매뉴얼 수치는 코드 grep(임계 2건)·실측 문서(시간 2건)·TDD 보고(보존 1건)로 각각 교차 확인.
