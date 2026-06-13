# 실행보고서 — auto-korea-stock-javis 통합 프로젝트 (조사·계획 단계)

> **작성:** Master Claude · 2026-06-13
> **명령:** "master(AgenticWorkflow-main-stock-filtering-collector)와 slave(kiwoom-rest-trader)의 기능을 한 개 project로 통합하라. user-manual을 차례로 읽고 통합 운영 방안과 빌드 계획을 심층 수립하고 실행보고서를 작성하라." (주인님, 2026-06-12)
> **상태:** 조사 100% 완료 · 계획 수립 완료 · **빌드 착수 전 — 주인님 결정 5건 대기**
> **자매 문서:** `BUILD_PLAN.md` (Phase 0~4 로드맵, 승인 대상)

---

## 1. 수행 절차 (어떻게 조사했나)

| 단계 | 방법 | 규모 |
|------|------|------|
| 1 | user-manual 3종 마스터 직접 정독 (AGENTICWORKFLOW-USER-MANUAL.md → docs/integrated-user-command-manual.md → kiwoom docs/user_command_manual.md) | 110KB |
| 2 | 워커 5기 병렬 심층 매핑 (master repo · slave repo · 인계계약 · 타깃폴더 · 운영/리스크) | 도구호출 198회 |
| 3 | 적대 검증관 1기가 5개 보고서 교차검증 — 모순 3건 적발, 실제 코드를 열어 판정 | 약 40개 주장 재검증 |
| 4 | 보안 사고 발견 → 즉시 대응 (본 보고서 §5) | 2026-06-12~13 |

모든 주장에는 파일 근거가 있으며, 보고서끼리 어긋난 수치는 코드 실측값으로 판정했다 (soul §6-b 할루시네이션 방지).

---

## 2. 두 시스템의 실체 — 통념과 달랐던 핵심 사실

### 2.1 "master = 수집기"가 아니다 — master는 **공장**이다

- **AgenticWorkflow-main-stock-filtering-collector** = 주식 데이터를 직접 수집하지 않는다. **kiwoom-rest-trader라는 '제품'을 설계·빌드·배포한 워크플로우 공장 + 비행기록장치**다 (README:224-237 "공장이자 비행기록장치").
- 12단계 빌드(Research 1-3 → Planning 4-7 → Implementation 8-12)로 제품의 오케스트레이션 레이어(CLAUDE.md + stock-scan/filter-tune 스킬)를 생성해 **1회성(genesis)으로 배포**했다.
- 수집·필터링·보고는 **전부 slave(kiwoom-rest-trader)가 수행**한다.

### 2.2 slave의 실체 — 조회 전용 5-Stage 스크리너 (주문 기능 0)

- 매 영업일 장 마감 후: ①상하한가(ka10017) ②조건검색 9개식(WebSocket) → organizedCompany.md(약 600~1,600종목) → Stage 0 prefetch(종목당 6 API) → **Stage 1~5 기술 필터**(MA 정배열 Type A~E → 240분 장기추세 → +15% 급등 차단 → MA612 밴드 → 수급 → 적자 제외) → researchedCompany.md (예: 20260611 스캔 1,601 → 22종목).
- **주문·계좌 코드 전무** (kt100*/ordr grep 0건) — 실거래(돈) 위험 현재 0.
- 운영은 스케줄러 없이 **한국어 자연어(14 Intent) 수동 트리거**. 실측 소요 80분~6시간 (문서의 "10-15분"은 진부화).

### 2.3 두 시스템 사이에 자동 데이터 인계는 **없다**

- 런타임 인계 0건. 잔존 결합은 ①빌드타임 배포 스크립트의 byte-identity 계약 ②제품 ADR이 공장 repo에, 공장 가드레일 테스트가 제품 repo에 있는 **교차 분산** ③하드코딩 절대경로(KRT_ROOT 등).
- "master 데이터"의 실체 = `reports/<날짜>/masterReference.md` — **사용자(소장님)가 수기로 채우는 정답지**(탈락분석·stageMasterFilter 학습 기준).

### 2.4 의도된 설계 철학 — "모드 경계"

제품(사용)→공장(빌드) 역방향 진입은 **구조적으로 차단**되어 있다 (kiwoom CLAUDE.md "만들 수 있는 분기가 생기면 그 자체가 결함"). **통합은 이 설계 결정의 의식적 재해석을 요구한다** — BUILD_PLAN §2에서 "한 지붕, 두 구역, 일방향 문" 구조로 계승할 것을 제안한다.

---

## 3. 타깃 디렉토리 진단 — 그대로 쓰면 안 된다

`/Users/tajun/spJavis/auto-korea-stock-javis/`의 현재 내용물:

| 진단 | 근거 |
|------|------|
| **4월 16일자 원판 AgenticWorkflow 템플릿의 사본** (업스트림 zip과 바이트 동일) | AgenticWorkflow-main-260418.zip 대조 — 차이 0건 |
| **2개월치 진화 누락** — 25개 파일이 구버전, tests/·prompt/workflow.md·12단계 빌드 산출물·docs 4종 전부 부재 | collector와 diff -rq |
| **숨김파일 누락 복사** — .claude/(에이전트 16·훅 29·스킬), .gitignore 등 탈락 | Finder 복사 패턴 |
| git 저장소 아님 | git status 실패 |

**결론: 이 사본을 통합 베이스로 쓰면 2개월의 자산이 조용히 소실된다.** 베이스는 진화 완료된 두 실repo로 해야 한다 (결정 요청 ①).

---

## 4. 확정 결함·괴리 목록 (통합 전 수선 대상)

| # | 결함 | 근거 | 처리 |
|---|------|------|------|
| 1 | **masterReference 포맷 드리프트**: 6/11부터 "이름(코드)" 형식 등장 — Filter_condition_update는 신포맷 파싱 OK, **stageMasterFilter는 폴더 매칭 실패**(학습 조용히 깨짐) | reports/20260518 vs 20260611 실파일 + stageMasterFilter.py:138-171 | Phase 0 |
| 2 | masterReference.md가 **매 스캔마다 0바이트로 덮어써짐** — 당일 수기 입력 소실 함정 | plain_text.py:73-75 | Phase 0~1 |
| 3 | **파라미터 카운트 SOT 불일치**: 인벤토리 75 vs README 87 vs 실측 76/87 | validate_param_values 스코프 재정의 필요 | Phase 0 |
| 4 | 문서 실행시간 "10-15분" vs **실측 80분~6시간** — 30분 watchdog도 비현실 | screener_state.json 실측 | Phase 1 문서·로직 갱신 |
| 5 | 하드코딩 절대경로 산재 (kiwoom CLAUDE.md·infra_schema.py:15-16·_measure_ref.py:4 등 — **전수조사 미완**) | 워커+검증관 발견 | Phase 0 전수 grep |
| 6 | 공장 빌드 SOT가 `completed_degraded` — Step 12 사람 최종검수 미수행 상태로 종결 | prompt/.claude/state.yaml | Phase 4에서 정신 계승 |
| 7 | backupMasterCompanys/ = 빈 디렉터리, 참조 0건 (잔재) | 전체 grep | 정리 대상 |

---

## 5. 보안 사고 및 대응 일지 (2026-06-12~13, 완결)

### 발견 (워커 조사 중)
- 실제 키움 APP_KEY/SECRET_KEY가 **git 추적 파일 `.env.example`에 평문 수록**된 채 GitHub(simonP2006/kiwoom-rest-trader, 비공개 추정)에 push됨.
- 실전서버 OAuth 토큰 캐시 `data/.token_cache.json`도 git 추적·push됨 (push 시점엔 만료 토큰).
- 평문 키 사본 4곳 산재 + zip 스냅샷 9개에 실 .env 포함.

### 대응 (시간순)
| 시각 | 조치 | 주체 |
|------|------|------|
| 6-12 | `git rm .env.example` + push (현재 스냅샷에서 제거) | 주인님 |
| 6-13 | 이력에서 키 복원 가능함을 검증으로 확인 → 키 재발급 권고 | master |
| 6-13 | **키움 키 재발급(rotate)** — 옛 키 폐기 확인(서버 8001 거부 실측) → **GitHub 이력 속 키 = 죽은 키** | 주인님 |
| 6-13 | **B 조치**: token_cache git 추적 해제 + .gitignore 등록 + push (`3a751c8`) → 추적 시크릿 0건 검증 | master |
| 6-13 | `.env.example` 플레이스홀더 견본으로 재생성 + push (`359fb57`) | master |
| 6-13 | 신키 기입 실수(`.env.example`에 붙여넣음) **커밋 전 포착** → `.env`로 이식 + 견본 복구 + 권한 600 | master |
| 6-13 | **신키 토큰 발급 성공** — 스크리너 정상 가동 복귀 | master 검증 |

### 잔여 (선택)
- **C. git 이력 정화**(filter-repo + force push): 옛 키가 죽었으므로 위생작업으로 강등. Phase 0에서 일괄 처리 권고 (비가역 — 별도 승인).
- 옛 키 평문 사본 3개 삭제 (비가역 삭제 — 지시 시 처리).

---

## 6. 통합 전략 (권고안)

### 6.1 세 가지 안 비교

| 안 | 내용 | 평가 |
|----|------|------|
| A. 느슨한 병치 | 두 repo를 폴더만 한곳에 모음 | 통합 효과 없음 — 기각 |
| **B. 모노레포 + 구역 분리 (권고)** | 한 repo 안에 `engine/`(제품)과 `factory/`(공장)을 두고, 루트에 **통합 오케스트레이션 레이어**(spJavis 마스터 방법론) 신설. 모드 경계는 "한 지붕, 두 구역, **일방향 문**"으로 계승 | 통합 운영 + 설계 철학 보존 + 경로/시크릿/문서 단일화 |
| C. 완전 융합 | 공장 코드를 제품 안에 녹여 단일 시스템화 | 모드 경계 파괴 — 제품→빌드 오염 위험, 원설계 ADR 위반. 기각 |

### 6.2 권고 구조 (B안 골격)

```
auto-korea-stock-javis/            ← 새 git repo (단일)
├── CLAUDE.md                      ← 통합 라우터: "시작"→사용모드 / "빌드"→공장모드 (일방향 문)
├── soul.md · BUILD_PLAN.md · SESSION_STATE.md (Javis 거버넌스)
├── engine/                        ← kiwoom-rest-trader 전체 (사용 모드 전용 구역)
│   └── (src·scripts·reports·.venv 재구축·.env 비추적)
├── factory/                       ← AgenticWorkflow 전체 (빌드 모드 전용 구역)
│   └── (prompt 비행기록·workflow-generator/executor·검증 훅)
└── ops/                           ← 신설: 일일 운영(daily-ops 1줄 명령·launchd·로그 정책)
```

### 6.3 통합 운영 방식 (매뉴얼 3종 + 주인님 운영 패턴 종합)

- **매일 아침 1줄**: `cd auto-korea-stock-javis && claude` → "오늘 스캔해줘" — 기존 14 Intent 전부 보존.
- 필터 개선이 필요할 때만 공장 구역 가동(파라미터 튜닝은 filter-tune으로 충분, 구조 변경은 factory의 12단계 빌드 정신 계승).
- 자동화(Phase 3): launchd 일일 스캔 + 실패 시 fail-loud 알림 (선례 com.envscan 침묵 실패의 반면교사).

상세 단계·게이트·검증 기준은 `BUILD_PLAN.md` 참조.

---

## 7. 주인님 결정 요청 5건 (denylist 해당 항목)

| # | 결정 | 권고 기본값 (gemini 변증 R1 반영 v2) |
|---|------|------------|
| ① | **베이스 선택**: 타깃 폴더의 구템플릿 사본 처리 | 진화된 두 실repo를 베이스로. 구사본은 **프로젝트 밖** `/Users/tajun/spJavis-tools/_archive/aksj-template-260416/`으로 이동(가역) — 워크스페이스 안에 두면 검색·컨텍스트 오염 (R1-4) |
| ② | **이름·원격 전략**: 로컬 `auto-korea-stock-javis` vs GitHub `auto-korea-stock-manager` 불일치 | 통합명 = **auto-korea-stock-javis**로 통일, GitHub에 동명 비공개 repo 신설(기존 2개는 force-push 없이 비공개 아카이브 동결) |
| ③ | **모드 경계 정책** | B안 "한 지붕, 두 구역, 일방향 문" + **.claude 물리 격리**(루트 최소화, 차단형 훅 승격 금지 — R1-1) |
| ④ | **git 이력 처리** | ~~기존 repo 파괴적 정화~~ → **신규 모노레포를 이력 보존형(filter-repo 경로 재작성+히스토리 병합)으로 구축하되 시크릿 blob만 제외** — blame 보존 + 시크릿 0 동시 달성 (R1-3·R1-6). 기존 repo는 건드리지 않음 |
| ⑤ | **reports/ 운영 데이터 이주 범위** (20260514~0611 스캔 이력, 비버전관리·단일 사본) | 전체를 engine/reports로 이주 + 외장/클라우드 1차 백업 생성 |

**범위 비포함(명시):** 자동매매(주문) 기능 — 현재 코드에 없으며, 추가는 별도 승인 전 금지 (soul §7 denylist).

---

## 8. 다음 단계

1. 주인님 결정 ①~⑤ 수신
2. BUILD_PLAN 승인 (ANCHOR: 승인 전 코드 0줄)
3. Phase 0 착수 (기반 정리 — 베이스라인·수선·위생)
4. 게이트: gemini+master 수렴, 코드 단계는 +pytest (soul §7 축1 강등규칙)

---

## 9. 변증 기록 (soul §5 — 감사 추적)

**R1 (2026-06-13, gemini-flash-latest — pro 일일쿼터 소진으로 flash 사용):** 7지적 / 총평 NEEDS-REVISION.

| # | 심각도 | 지적 | 마스터 판정 |
|---|--------|------|------------|
| 1 | HIGH | 루트 .claude 전역 훅이 일일 스캔에 레이턴시·오탐 간섭 | **수용** → BUILD_PLAN §2 4항 물리 격리 |
| 2 | HIGH | 베이스라인을 (테스트 없는) 타깃 폴더에서 돌리는 순서 오류 | **소명** — 원의도는 기존 실repo 실행. 문구 모호성 인정 → 0-2 명문화 |
| 3 | HIGH | 단순 복사 이주 시 git 이력·blame 상실 | **수용(상위 개선)** → 1-1 filter-repo 이력 보존형 병합 + 시크릿 blob 제외 |
| 4 | MED | 구사본을 워크스페이스 내 아카이브 시 grep·컨텍스트 오염 | **수용** → 0-1 프로젝트 밖 이격 |
| 5 | MED | 동결된 factory와의 파라미터 동기화는 과잉설계 | **수용** → 0-5 engine 단독 축소 |
| 6 | LOW | 옛 키 사망 후 기존 repo 파괴적 이력 정화는 무익·유해 | **수용** → 0-7 폐기, #3 방식으로 대체 |
| 7 | LOW | launchd로 80분~6h 작업 자동화는 슬립·잠금에 취약 | **수용** → Phase 3 수동 기본값, 자동화는 별도 검토 |

**R2 (2026-06-13, gemini-flash-latest):** R1 7개 지적 **전부 "반영됨"** 판정 + 신규 결함 **없음** → **CONVERGED**. 게이트(gemini+master 수렴) 충족 — 계획 문서는 주인님 승인 대기 상태로 확정. (codex는 soul §5 가용성 정책상 best-effort — 본 단계는 비코드 계획이라 쿼터 보존, 미호출.)
