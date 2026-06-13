# 과업 1-4 — 모노레포 루트 CLAUDE.md 통합 라우터: 설계 근거

- 일시: 2026-06-13 (Phase 1 워커)
- 산출물: `/Users/tajun/spJavis/auto-korea-stock-javis/CLAUDE.md` (신규, **86줄** — `wc -l` 실측, 사양 80~120줄 충족)
- 근거 문서: BUILD_PLAN.md §1(:16-25)·§2(:27-32), phase0/claude-isolation-design.md, engine/CLAUDE.md, EXECUTION_REPORT.md, phase1/monorepo-build.md

---

## ① 섹션별 설계 근거

| 루트 §| 내용 | 근거 |
|---|---|---|
| 정체성 1줄 | 사용=engine, 빌드=factory, "구역 선택 규칙만" | BUILD_PLAN.md:29 "루트 CLAUDE.md가 단일 진입 라우터" + phase0 설계서 §2.4 "루트 라우터는 둘과 겹치지 않게 '구역 선택 규칙만'" |
| §1 Path Constants | AKSJ_ROOT/ENGINE_ROOT/FACTORY_ROOT/ENGINE_PYTHON 4상수 | 과업 지시 ②. ENGINE_PYTHON 실재 검증: `engine/.venv/bin/python --version` → `Python 3.12.7` (명령 실측) |
| §1 과도기 우선규칙 | KRT_*→ENGINE_* 읽기 변환 브리지 | engine/CLAUDE.md:7 `KRT_ROOT = /Users/tajun/spJavis/kiwoom-rest-trader` (구 경로 잔존 — Phase 1-2 미완). 브리지 없이는 루트 상수와 engine 상수가 **충돌 상태로 방치**되므로, 우선순위를 명시 선언해 모순을 해소 |
| §2.1 기본값=engine | 14 Intent 이름 나열 + 상세는 위임 | 과업 지시 "복제하지 말고 위임 참조". 이름 14개는 engine/CLAUDE.md:20-33 표의 Cluster 열 전수 전사(아래 ② #1 대조) |
| §2.1 Start Routing 위임 | "워크플로우 시작하자"도 engine | engine/CLAUDE.md:46이 해당 발화를 사용 모드 진입 예시로 명시. phase0 설계서 §2.1이 지목한 1번 표적(루트 세션에서 workflow-executor 오발) 차단 |
| §2.2 일방향 문 | "공장 빌드 모드" 명시 발화만, 그 외 진입 금지 | BUILD_PLAN.md:29-30 + engine/CLAUDE.md:58 모드 경계 절대 규칙("어떤 분기·조건·플래그·경로로도 도달 불가") 계승 |
| §2.3 prompt/ 동결 | 읽기 전용 | BUILD_PLAN.md:31 + phase0 설계서 §④A "그대로 + 읽기 전용 동결" |
| §3 실행 규약 | background 필수 / 80분~6h / run_filters <3분 | engine/CLAUDE.md:13-14(background 필수·run_filters<3분) + EXECUTION_REPORT.md:35,70(실측 80분~6시간, "10-15분"은 진부) + BUILD_PLAN.md:61(watchdog 80분~6h 기준) |
| §4 시크릿 | .env 단일·*.example 기입 금지 | phase1/monorepo-build.md STEP 6-7: `.env.example`은 플레이스홀더 재생성(`grep -c 'your_kiwoom'`=2), `engine/.env`는 0600 비추적. 루트 .gitignore가 engine/.env 제외 |
| §5 .claude 격리 | 차단형 훅 루트 승격 금지 1줄 | BUILD_PLAN.md:32(gemini R1-1) + phase0 설계서 §2.2(훅 간섭 매트릭스)·§3.2(engine 오픈 시 훅 0건·스킬 2개) |
| §6 오픈 위치 가이드 | engine/factory/루트 3행 표 | phase0 설계서 §3.2 "표의 함의" 1·2·3 요약 — 격리 설계의 실행 지침화 |

## ② engine/CLAUDE.md 모순 대조 표 (검증 기준: 모순 0)

| # | 루트 서술 | engine/CLAUDE.md 대응 | 판정 |
|---|---|---|---|
| 1 | 14 Intent 이름 14개 | :20-33 Cluster 열 — SCAN_TODAY/SCAN_SEPARATED/SCAN_RANGE/SHOW_RESULTS/WHY_REJECTED/SHOW_PARAMS/CHANGE_PARAM/RERUN_FILTERS/RESTORE/COMPARE/COMPARE_PARAMS/THEORY_GUIDE/CONFIRM/ASK_MODULE | **일치** (14/14 전수, 순서 동일) |
| 2 | "시작"·"워크플로우 시작하자" → Start Routing | :44-46 (동일 예시 문자열 포함), :58 | **일치** |
| 3 | run_full_research_flow·run_prefetch background 필수 | :13 `RUN_IN_BACKGROUND = true MANDATORY`, :137 | **일치** |
| 4 | run_filters 동기 <3분 | :14 `RUN_IN_FOREGROUND = ok`, :138 "전형적 < 3분" | **일치** |
| 5 | source activate 금지, .venv/bin/python 직접 호출만 | :139 (D-7) | **일치** |
| 6 | EXEC_PATTERN `cd ROOT && PYTHON -m {module}` | :12, :136 | **일치** (경로 상수명만 ENGINE_*로 — §1 브리지로 정합) |
| 7 | factory 진입 = 명시 발화만, engine→factory 호출 경로 금지 | :58 모드 경계 절대 규칙 | **일치** (계승·강화) |
| 8 | Mixed-intent·모호성 1회 질문 위임 | :35-40 | **일치** (위임이므로 재서술 없음 = 모순 불가) |
| 9 | 소요 80분~6시간 (문서상 10-15분 진부) | :13,117,123,137 "10-15분" | **모순 아님 — 명시 정정 선언**: 침묵 충돌이 아니라 루트가 "engine 문서의 10-15분 표기는 진부·신뢰 금지"를 선언하고 실측치 출처(EXECUTION_REPORT.md:35,70)와 보정 예정(Phase 2-1, BUILD_PLAN.md:61-62)을 함께 명기. 과업 지시 ⑤가 요구한 의도된 우선규칙 |
| 10 | ENGINE_ROOT = 모노레포 경로 | :7-11 KRT_* = 구 repo 경로 | **모순 아님 — §1 과도기 우선규칙으로 명시 브리지**. Phase 1-2 치환 완료 시 항 삭제 예정 |
| 11 | 시크릿 .env 단일·example 금지 | engine/CLAUDE.md에 시크릿 절 없음 (전문 확인) | **모순 불가** (신규 규칙, 충돌면 없음) |
| 12 | 30분 watchdog 비현실 언급 | :137 "30분 timeout watchdog" | #9와 동일 계열 — EXECUTION_REPORT.md:70 "30분 watchdog도 비현실" 인용, Phase 2-1 보정 항목으로 위임 |

**결론: 침묵 모순 0.** 충돌 가능 지점 2곳(#9 시간, #10 경로)은 모두 "어느 쪽을 따를지"의 우선순위를 루트 문서 안에서 명시 선언하는 방식으로 해소했다 — 라우터가 두 문서를 동시에 읽는 세션에서 모델이 임의 선택할 여지를 제거.

## ③ 사양 충족 체크

| 과업 요구 | 충족 | 근거 |
|---|---|---|
| 한국어, 80~120줄 | O — **86줄** | `wc -l` 출력 |
| ① 정체성 1줄 | O | 루트 CLAUDE.md:3 |
| ② Path Constants 4종 | O | :8-20 (§1, 코드블록 :10-15) |
| ③ 라우팅: 사용→engine 위임 + cd ENGINE_ROOT + "공장 빌드 모드"만 factory | O | :22-46 (§2.1-2.2; cd ENGINE_ROOT 의무 :36-37) |
| ④ prompt/ 동결 명기 | O | :48-51 (§2.3) |
| ⑤ background 필수 + 실측 80분~6h + 10-15분 진부 + run_filters <3분 | O | :53-65 (§3) |
| ⑥ 시크릿: ENGINE_ROOT/.env만, *.example 금지 | O | :67-71 (§4) |
| ⑦ .claude 격리 1줄(차단형 훅 루트 승격 금지) | O | :73-76 (§5) |
| 14 Intent 표 복제 금지 | O | 이름 나열만(:30-31), 표·예시·Action 미복제 |
| (그 외 줄 번호 검증) | — | §2 헤더 :22, §2.3 :48, §3 :53, §4 :67, §5 :73, §6 :78 — `grep -n` 실측 대조 완료 |

## ④ 잔여 사항 (후속 과업 의존)

1. **engine/CLAUDE.md:7-11 KRT_* 구 경로 치환** — Phase 1-2 범위. 완료 시 루트 §1 과도기 우선규칙 항 삭제 필요(루트 문서에 자연 소멸 조건 명기済).
2. **engine 문서 "10-15분"·"30분 watchdog" 4곳(:13,117,123,137) 실측 보정** — Phase 2-1 범위(BUILD_PLAN.md:61-62).
3. **루트 settings 상속 여부(git root 판정) 미실측** — phase0 설계서 §3.1(f) 그대로 미해결. Phase 1 게이트에서 3종 실측(`/hooks`·`/permissions`·`$CLAUDE_PROJECT_DIR`) 필요. 결과에 따라 루트 .claude 정책이 더 엄격해질 수 있음.
4. **시나리오 표 전수 통과 검증(BUILD_PLAN 1-4 검증 기준)** — 라우터 문서 작성은 완료했으나 14 Intent + "시작" + "공장 빌드 모드" 발화의 실세션 라우팅 시나리오 테스트는 본 과업에서 미실시(실세션 필요). 게이트에서 master/gemini 변증과 함께 수행 권고.
