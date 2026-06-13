# BUILD_PLAN — auto-korea-stock-javis (master+slave 통합)

> **상태: v2 (gemini 변증 R1 반영) — 주인님 승인 대기** (승인 전 코드 0줄 원칙)
> 근거 조사: `EXECUTION_REPORT.md` (워커 5+1 심층 매핑, 2026-06-13)
> 변증 이력: gemini R1 7지적 → 6수용·1소명(문구 명확화). 상세 EXECUTION_REPORT §9.
> 게이트 정책: 각 Phase 종료 = **gemini + master 수렴** (코드 포함 단계는 **+pytest 그린**) → 커밋 → SESSION_STATE 갱신 (soul §7 축1)

---

## 0. 목표 / 비목표

**목표:** 공장(AgenticWorkflow)과 제품(kiwoom-rest-trader)을 단일 프로젝트 `auto-korea-stock-javis`로 통합하되, ①일일 스크리닝 운영(14 Intent)은 무손실 보존 ②"모드 경계" 철학은 "한 지붕, 두 구역, 일방향 문"으로 계승 ③경로·시크릿·문서·테스트를 단일 기준으로 재정렬.

**비목표(명시):** 자동매매(주문) 기능 추가 — 별도 승인 전 금지. 필터 알고리즘 자체의 변경(통합은 이사이지 개조가 아님 — 파라미터 튜닝 루프는 보존).

## 1. 아키텍처 (승인 대상 골격)

```
auto-korea-stock-javis/                ← 새 단일 git repo
├── CLAUDE.md                          ← 통합 라우터 (아래 §2)
├── BUILD_PLAN.md · EXECUTION_REPORT.md · SESSION_STATE.md
├── engine/      = 현 kiwoom-rest-trader  (사용 모드 구역; .venv 재구축, reports/ 이주)
├── factory/     = 현 AgenticWorkflow     (빌드 모드 구역; prompt/ 비행기록 동결 보존)
└── ops/         = 신설 (daily-ops 1줄 명령, launchd 템플릿, 로그·백업 정책, paths 단일 SOT)
```

## 2. 모드 경계 계승 규칙 (불변항)

- 루트 CLAUDE.md가 **단일 진입 라우터**: 사용 발화("시작"/스캔/튜닝 등 14 Intent) → engine 구역만. 빌드 발화(명시적 "공장 빌드 모드") → factory 구역만.
- **engine 구역 코드·스킬에서 factory를 호출하는 경로를 만들지 않는다** (원설계 kiwoom CLAUDE.md:58 계승). 역방향 문은 사람(주인님)의 명시 발화로만 열린다.
- factory의 `prompt/`(12단계 비행기록)는 **읽기 전용 동결** — 수정 금지.
- **[gemini R1-1 수용] .claude 물리 격리**: 루트 `.claude`에는 최소 라우팅 설정만 둔다. 훅(특히 factory의 7이벤트 차단형 훅)과 스킬은 각 구역의 `.claude`에 잔류시키고 **루트로 승격(hoist)하지 않는다** — 일일 스캔(80분~6h)이 공장 훅 레이턴시·오탐 차단에 노출되는 것을 차단. 일일 운영 세션은 `engine/`에서 열어도 된다.

## 3. Phase 로드맵

### Phase 0 — 기반 정리 (코드 이동 전 선행, 대부분 가역)
| # | 작업 | 검증 기준 |
|---|------|----------|
| 0-1 | 구템플릿 사본 → **프로젝트 밖** `/Users/tajun/spJavis-tools/_archive/aksj-template-260416/`로 이동 (결정① · gemini R1-4 수용 — 워크스페이스 grep 오염 방지) | 이동 후 diff 무손실 |
| 0-2 | **테스트 그린 베이스라인**: **기존 실repo 경로에서** engine pytest(전 스위트) + factory tests/ 실행·기록 (gemini R1-2 문구 명확화 — 타깃 폴더가 아님) | 이주 전 합격선 문서화 |
| 0-3 | **절대경로 전수 인벤토리**: 두 repo 전체 `/Users/tajun` grep → 파손 지점 목록 | 목록 완전성 gemini 교차 |
| 0-4 | **masterReference 파서 드리프트 수선**: canonical 포맷 "이름(코드)" 확정 + stageMasterFilter `_read_name_list` 접미사 분리 보강 + 회귀 테스트 | 신·구 포맷 모두 파싱 pytest |
| 0-5 | 파라미터 SOT 재기준선 — **engine 단독** (filter-tune 신뢰 목적; 동결된 factory 문서와의 동기화는 하지 않음, gemini R1-5 수용) | validate_param_values 스코프 명문화 |
| 0-6 | reports/ 이주 매니페스트 + **1차 백업 생성** (결정⑤) | 백업 무결성 해시 대조 |
| 0-7 | ~~기존 repo 파괴적 이력 정화~~ → **폐기** (gemini R1-6 수용: 옛 키 사망으로 보안 이득 없음). 대체: Phase 1-1의 신규 모노레포 이력 재작성 시 시크릿 blob(.env.example 구버전·token_cache)을 **제외하고** 구축 — 기존 두 repo는 force-push 없이 비공개 아카이브로 동결 | 신규 repo 이력 내 시크릿 grep 0건 |
| 0-8 | .claude **구역 격리 설계** (병합이 아니라 격리 — §2 4항; 루트 최소화 + 구역별 잔류 + 중첩 스킬 세션 누출 통제) | 설계서 gemini 검토 |

### Phase 1 — 모노레포 이주 (코드 단계, +pytest)
| # | 작업 | 검증 기준 |
|---|------|----------|
| 1-1 | **이력 보존형 모노레포 구축** (gemini R1-3 수용): `git filter-repo`로 두 repo 이력을 각각 `engine/`·`factory/` 경로로 재작성(+시크릿 blob 제외) → 두 히스토리를 병합해 단일 repo 구성 — 전체 커밋 이력·blame 보존 | 트리 무손실 diff + `git log --follow` 표본 추적 + 이력 내 시크릿 0건 |
| 1-2 | **경로 단일 SOT**: ops/paths 정의 → 하드코딩 절대경로 전부 치환 (0-3 목록 기준) | 잔여 grep 0건 + pytest |
| 1-3 | engine .venv 재구축 + 의존성 고정(pip freeze 대조) | 토큰 발급 + run_filters 스모크 |
| 1-4 | 루트 CLAUDE.md 통합 라우터 작성 (14 Intent 보존 + 모드 경계 §2) | 시나리오 표 전수 통과 |
| 1-5 | masterReference 0바이트 덮어쓰기 함정 수선 (기존 내용 보존 로직) | 회귀 pytest |
| 1-6 | 0-2 베이스라인과 동등 이상 그린 재확인 | 전 스위트 pytest |

### Phase 2 — 통합 운영 레이어
| # | 작업 | 검증 기준 |
|---|------|----------|
| 2-1 | daily-ops 표준화: 아침 1줄 명령 + 4-step 완료 핸들러 실측치 보정(80분~6h 기준 watchdog) | 실스캔 1회 E2E |
| 2-2 | 문서 대통합: 통합 매뉴얼 개정판 (integrated-user-command-manual 승계, 실측치 반영) | 값-동등성 원칙 검수 |
| 2-3 | screener_state·tuning-log 등 상태 파일 경로 정합 | 세션 연속성 시나리오 |

### Phase 3 — 운영 강화 (선택적, 주인님 취향 확인 후)
| # | 작업 | 검증 기준 |
|---|------|----------|
| 3-1 | **수동 14 Intent 운영 = 기본값 유지** (gemini R1-7 수용: 80분~6h 작업은 macOS 슬립·잠금·네트워크 단절에 취약). 자동화 욕구 확인 시에만 별도 검토 — (a) `caffeinate`+전원연결 조건의 launchd 또는 (b) 상시 가동 환경(클라우드/미니PC) 이전. 어느 쪽이든 **fail-loud 알림** 필수 (com.envscan 침묵실패 반면교사) | 채택 시: 의도 실패 주입 시 알림 수신 |
| 3-2 | reports/ 보존·회전 정책 + 정기 백업 | 복원 리허설 |

### Phase 4 — 검증·인수
| # | 작업 | 검증 기준 |
|---|------|----------|
| 4-1 | 전체 게이트: pytest 전 스위트 + gemini 변증 + master 독립 검증 | 4자 수렴 |
| 4-2 | 실데이터 E2E: 당일 스캔 → 결과 → 탈락분석 → 튜닝 → 재필터 풀사이클 | 매뉴얼 시나리오 전수 |
| 4-3 | **주인님 최종 인수** — 공장 Step 12 하드블록 정신 계승 (자동승인 금지) | 주인님 승인 |

## 4. 리스크 레지스터 (요약)

| 리스크 | 완화 |
|--------|------|
| 이주 중 경로 파손 | 0-3 전수 인벤토리 선행 + 1-2 일괄 치환 + pytest |
| reports/ 단일 사본 유실 | 0-6 백업 선행 (이주 전 필수) |
| **git 이력·blame 상실** (R1-3) | 1-1 filter-repo 이력 보존형 병합 — 단순 복사 금지 |
| **루트 훅의 일일 운영 간섭** (R1-1) | §2 4항 .claude 물리 격리 — 차단형 훅 루트 승격 금지 |
| .claude 중첩 스킬 오염 (이미 세션 누출 중) | 0-8 격리 설계 |
| **구사본의 grep/컨텍스트 오염** (R1-4) | 0-1 프로젝트 밖 이격 |
| 빌드 SOT degraded 상태 승계 | factory는 동결 보존 — 새 빌드는 새 인스턴스로 |
| 자동화 침묵 실패·슬립 중단 (R1-7) | 수동 기본값 + 채택 시 fail-loud·전원조건 |

## 5. denylist 매핑 (soul §7)

- 구사본 이동(0-1)·이력 정화(0-7)·기존 repo 아카이브 전환 = **개별 명시 승인 후 실행**.
- GitHub 신규 repo 생성·push(결정②) = 외부 발행 — **승인 후 실행**.
- 그 외 Phase 작업은 로드맵 내·가역 — 게이트 수렴 시 자동 진행.
