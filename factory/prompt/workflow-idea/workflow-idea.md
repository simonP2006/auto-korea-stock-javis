---
document: Workflow Idea Meeting Record
version: "0.5.0"
created: "2026-05-26"
updated: "2026-05-26"
status: idea-exploration (audit gap-fill applied)
source_session: "7d6c9e50-35e6-4c95-ab94-c9e0b49568a6"
prd_reference: "prompt/prd.md v0.3.0-draft"
note: "확정 설계가 아닌 가능성 탐색 기록. 이후 성찰·수정이 계속된다."
---

# Workflow Idea Meeting Record

> **제1 핵심 목적**: (1) 종목 스크리너에게 특정일 데이터를 수집·필터링하도록 명령할 수 있어야 한다. (2) 사용자가 필터 조건을 fine-tuning하기 쉽게 도울 수 있어야 한다. **이것이 가장 큰 목표이다.**

> **핵심 제약**: 사용자는 코드 구현 능력이 전혀 없다. 모든 것은 로컬 macOS에서 Claude Code가 자동 실행한다.

---

## 1. 회의 구성

### 1.1 Teammate 구성

| ID | Teammate | 역할 | 담당 축 |
|---|---|---|---|
| T1 | arch-teammate | 소프트웨어 아키텍트 | 산출물 구조, Research 단계 설계, 상태 관리 |
| T2 | ux-teammate | UX/인터랙션 설계 | 한국어 의도 인식, 에러 래핑, 멀티스텝 체인, 확인 플로우, 세션 연속성 |
| T3 | safety-teammate | 안전/신뢰성 설계 | 백업 전략, 범위 검증, 공유 상수, 원자적 변경, 영향 추정, 튜닝 로그 |
| T4 | integration-teammate | 시스템 통합 | Pre-flight 검증, 실행 래핑, 출력 파싱, 장시간 실행, 에러 분류, 날짜 처리, CWD 관리 |

### 1.2 참조 파일 (실제 Read 검증 완료)

- `prompt/prd.md` (v0.3.0-draft, 777행, 전문 2회 Read)
- `kiwoom-rest-trader/docs/user_command_manual.md` (331행, 전문 Read)
- `kiwoom-rest-trader/src/kiwoom/itemFilter/chart60_120Filter.py` (상단 60행 Read)
- `kiwoom-rest-trader/src/kiwoom/itemFilter/investorFilter.py` (상단 40행 Read)
- `kiwoom-rest-trader/src/kiwoom/itemFilter/Filter_condition_update.py` (상단 60행 Read)
- `kiwoom-rest-trader/src/kiwoom/itemFilter/` 디렉터리 구조 (Glob 확인)

---

## 2. 아이디어 목록

### B-1. 산출물 아키텍처: CLAUDE.md + 2-Skill 구조

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md(라우팅 테이블 + 경로 상수 + 안전 규칙 ~70행) + `stock-scan` 스킬(실행 오케스트레이션) + `filter-tune` 스킬(파라미터 튜닝). 두 핵심목적이 완전히 다른 인터랙션 패턴(fire-and-forget vs 반복 대화)이므로 분리. |
| **제1 목적 연결** | 핵심목적 1 → `stock-scan`, 핵심목적 2 → `filter-tune`. CLAUDE.md는 양쪽 디스패치 허브. |
| **트레이드오프** | (+) 컨텍스트 효율 — 스캔만 할 때 튜닝 카탈로그 200행 미로드. (-) 2개 스킬 유지 부담. (-) "필터 바꾸고 다시 돌려줘" 같은 혼합 의도는 CLAUDE.md 라우팅이 처리해야 함. 대안: 단일 mega-CLAUDE.md는 매 세션 컨텍스트 낭비. 단일 스킬은 두 모드 혼재. |
| **로컬 실행 적합성** | ✅ 완전 적합 — CLAUDE.md와 스킬 파일은 로컬 텍스트 파일. |
| **출처** | T1 (arch-teammate) |

---

### B-2. CLAUDE.md ↔ Skill 경계 설계

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md에는 (a) 의도→스킬 라우팅 테이블(~20개 패턴), (b) `KRT_ROOT` 등 경로 상수, (c) 안전 규칙 불변(TS-1~5), (d) 출력 형식 규약(숫자 표기: 한국식 천 단위 쉼표 "4,805원", 퍼센트 "-3.5%", 배수 "0.965배"), (e) 표현 정책(FR-8.2/8.3)만. 파라미터 카탈로그, 필터 의존 그래프, 예시 대화 등은 스킬 references/에 위치. |
| **제1 목적 연결** | 라우팅 테이블이 "사용자 → 올바른 스킬"의 유일한 다리. 실패하면 두 핵심목적 모두 무너짐. |
| **트레이드오프** | (+) CLAUDE.md 경량 유지(~70-100행). (-) 너무 얇으면 라우팅 실패, 너무 두꺼우면 컨텍스트 낭비. **핵심 위험**: 파라미터 카탈로그(references/)가 실제 Python `Final` 상수와 비동기화 가능. **완화**: 스킬 첫 단계에서 `grep -n 'Final' src/kiwoom/itemFilter/*.py`로 실시간 추출, 카탈로그는 문서화 역할만. |
| **로컬 실행 적합성** | ✅ 완전 적합 |
| **출처** | T1 (arch-teammate) |

---

### B-3. 한국어 의도 인식 인코딩

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md에 의도 클러스터 매핑 테이블 삽입. ~10개 클러스터(SCAN_TODAY, WHY_REJECTED, CHANGE_PARAM 등)에 각 2-3개 예시 한국어 표현 + 실행 액션 매핑. 모호한 경우 "최대 1회 한국어 선택지 확인 질문" 폴백 규칙. |
| **제1 목적 연결** | 비기술 사용자의 한국어 입력 → Python 명령 변환의 핵심 레이어. 없으면 Claude가 추측하여 오작동. |
| **트레이드오프** | (+) Claude의 일반화 능력이 마이너 변형 처리. (-) 정적 테이블은 모든 발화 커버 불가. (-) 위험 케이스: false confidence("조건 완화해줘"를 구체적 파라미터로 잘못 매핑) — 확인 플로우(B-7)가 안전망. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 프롬프트 엔지니어링, 런타임 비용 없음 |
| **출처** | T2 (ux-teammate) |

**의도 클러스터 예시 (확정이 아닌 초안)**:

```
| 의도 클러스터 | 예시 표현 | 실행 액션 |
|---|---|---|
| SCAN_TODAY | "오늘 스캔", "오늘 종목 돌려줘" | run_full_research_flow / run_prefetch+run_filters |
| SCAN_RANGE | "이번 주 전부", "월~금 수집" | loop: run per trading day |
| SHOW_RESULTS | "결과 보여줘", "통과 종목" | Read researchedCompany.md + stage*_passed.md |
| WHY_REJECTED | "X 왜 빠졌어", "X 탈락 이유" | masterReference chain (B-5) |
| SHOW_PARAMS | "Stage N 조건 보여줘" | Read Final constants + format table |
| CHANGE_PARAM | "X 조건을 Y로 바꿔" | confirm (B-7) → Edit Final → log |
| RERUN_FILTERS | "필터만 다시 돌려줘" | run_filters (no API) |
| RESTORE | "원래대로 되돌려줘" | restore from .bak file |
| COMPARE | "어제랑 비교", "변경 전후 비교" | diff two result sets (아래 실행 체인 참조) |
| THEORY_GUIDE | "약세장 어떻게", "이론적 근거" | FR-7 theory mapping |
| CONFIRM | "이걸로 확정", "현재 설정 유지" | tuning-log에 확정 마킹 + 세션 종료 안내 (FR-6.5) |
| ASK_MODULE | "stageMasterFilter 뭐야", "다른 필터?" | 보조 모듈 존재·역할 설명 + Phase 2 안내 (PRD §6.4) |
```

**COMPARE 실행 체인 (3차 적대적 성찰 추가 — FR-2.4 구체화)**:

```
CHAIN: COMPARE(date_a, date_b) — 교차 날짜 비교
  Step 1: Read reports/{date_a}/researchedCompany.md → set_a
  Step 2: Read reports/{date_b}/researchedCompany.md → set_b
    CHECKPOINT: 어느 한쪽 미존재 → "{date} 결과가 없습니다. 해당 날짜 스캔이 필요합니다"
  Step 3: Compute diff → common / added_in_b / removed_from_a
  Step 4: 파라미터 변경 여부 확인 → tuning-log.md에서 date_a~date_b 구간 변경 이력 추출
  Step 5: 한국어 비교 테이블 출력 + 파라미터 변경 있었으면 "※ 이 기간에 파라미터가 변경되었습니다" 명시
  FORMAT: "공통 {N}개 | {date_b}에만 {M}개 추가 | {date_a}에서 {K}개 탈락"

CHAIN: COMPARE_PARAMS(before, after) — 변경 전후 비교 (동일 날짜, 파라미터 변경)
  Step 1: 변경 전 결과 = tuning-log.md의 stocks_passed_before
  Step 2: 변경 후 결과 = 현재 researchedCompany.md (run_filters 재실행 후)
  Step 3: diff → 한국어 비교 테이블
```

---

### B-4. 에러 래핑 절대 규칙

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md에 절대 기준급 규칙: "모든 Python stderr/traceback을 한국어로 변환. 원문은 '기술 상세(영문)' 라벨로 접힌 상태 첨부." 에러 분류표: KiwoomAuthError → "키움 인증 만료", httpx.ConnectError → "키움 서버 연결 실패", exit code 1 → "수집 데이터 없음" 등. |
| **제1 목적 연결** | 영어 에러 = 사용자 이탈 트리거(PRD §3). 핵심목적 1의 생존 조건. |
| **트레이드오프** | (+) 사용자 신뢰 유지. (-) Claude가 과도 요약하여 유의미한 정보 손실 가능. **완화**: "접힌 상세" 패턴으로 원문 보존. (-) 에러 분류표는 kiwoom-rest-trader 코드 변경 시 갱신 필요. |
| **로컬 실행 적합성** | ✅ 완전 적합 — stdout/stderr 후처리만 |
| **출처** | T2 (ux-teammate), T4 (integration-teammate) |

**에러 분류표 초안**:

```
| Exit Code | 소스 | 에러 유형 | 한국어 메시지 | Claude 대응 |
|---|---|---|---|---|
| 1 | run_full_research_flow | organizedCompany 0건 | "조건검색 결과가 없습니다" | 해당 날짜 시장 개장 여부 확인 |
| 1 | run_filters | prefetchManifest 부재 | "수집 데이터가 없습니다" | run_prefetch 먼저 실행 제안 |
| 2 | 모든 스크립트 | unhandled exception | stderr에서 확인 | traceback 읽고 KiwoomAuthError vs httpx.ConnectError 분류 |
| — | auth.py | KiwoomAuthError | "키움 인증이 만료되었습니다" | 재인증 안내 |
| — | async pipeline | httpx.ConnectError | "키움 서버 연결 실패" | 시간 후 재시도 안내 |
```

---

### B-5. 멀티스텝 워크플로우 체인 인코딩

| 항목 | 내용 |
|---|---|
| **핵심** | 복잡한 상호작용(예: "삼성전자 왜 빠졌어?")을 번호 매긴 단계 시퀀스로 스킬 문서에 인코딩. 각 단계에 체크포인트(실패 시 한국어 분기 메시지) 포함. 파일 경로는 하드코딩 대신 glob으로 동적 탐색. |
| **제1 목적 연결** | FR-3(탈락 분석)은 핵심목적 2의 최고가치 인터랙션. 단계 누락 시 분석 불가. |
| **트레이드오프** | (+) 체인 인코딩으로 Claude의 단계 누락 방지. (-) 경직된 체인은 코드 구조 변경에 취약. **완화**: 동적 탐색(glob) + 체크포인트 분기. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 순수 파일 I/O |
| **출처** | T2 (ux-teammate) |

**WHY_REJECTED 체인 예시 (초안)**:

```
CHAIN: WHY_REJECTED(stock_name, date=YYYYMMDD)
  Step 1: Find stock folder → glob reports/{date}/*{stock_name}*/
    CHECKPOINT: 미발견 → "해당 종목은 {date} 수집 대상에 포함되지 않았습니다"
  Step 2: Write stock_name to reports/{date}/masterReference.md
  Step 3: Run Filter_condition_update {date}
  Step 4: Read reports/{date}/masterReference.log → extract latest block for stock
  Step 5: Parse rejection stage + condition + values → Korean explanation
    FORMAT: "Stage N에서 탈락: {조건} = {실제값}. 기준 {기준값}({허용오차}). {gap} 미달."
```

**⚠️ masterReference.log 회전 규칙 (감사 보완 — PRD §6.5)**: masterReference.log는 append 방식이므로 무한 증가. 500행 초과 시 `masterReference.log.YYYYMM`로 아카이빙 후 신규 로그 시작. Claude가 과거 분석 참조 시 아카이브도 검색해야 한다. 이 회전 규칙을 stock-scan 스킬의 WHY_REJECTED 체인 마지막에 체크 로직으로 인코딩.

---

### B-6. 실행 래핑 템플릿

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md에 단일 실행 템플릿 — `cd /Users/tajun/spJavis/kiwoom-rest-trader && .venv/bin/python -m {module} {args}`. `source .venv/bin/activate` 대신 `.venv/bin/python` 직접 경로 사용(쉘 상태 비의존). `KRT_ROOT` 변수로 경로 1곳만 관리. |
| **제1 목적 연결** | 핵심목적 1의 기술적 기반. 잘못된 CWD/Python 경로는 모든 실행 실패의 원인. |
| **트레이드오프** | (+) `.venv/bin/python`은 `activate`보다 안정적(쉘 상태 불변). (+) 경로 1곳 관리. (-) 프로젝트 경로 이동 시 1곳만 수정이나, 수정 자체를 잊을 수 있음. (-) 환경변수가 필요한 경우 누락 가능(현재 시스템은 불필요). |
| **로컬 실행 적합성** | ✅ 완전 적합 |
| **출처** | T4 (integration-teammate) |

**템플릿 상수 초안**:

```
KRT_ROOT = /Users/tajun/spJavis/kiwoom-rest-trader
KRT_PYTHON = ${KRT_ROOT}/.venv/bin/python
KRT_REPORTS = ${KRT_ROOT}/reports
KRT_FILTERS = ${KRT_ROOT}/src/kiwoom/itemFilter

실행 패턴: cd ${KRT_ROOT} && ${KRT_PYTHON} -m {module} {args}
```

---

### B-7. 파라미터 변경 확인 플로우 (Two-phase Commit)

| 항목 | 내용 |
|---|---|
| **핵심** | 변경 요청 시 → (1) 변경 전/후 값 테이블 표시 → (2) "적용할까요?" 확인 → (3) 승인 후에만 Edit 실행 → (4) 변경 직후 diff 한국어 요약. 백업→편집→로그 기록 순서로 순차 실행, 편집 실패 시 백업이 이미 존재하므로 안전. |
| **제1 목적 연결** | FR-5, FR-6의 안전한 실행. 잘못된 임계값이 투자 결과에 영향 → 확인은 기능이지 마찰이 아님. |
| **트레이드오프** | (+) 투자 관련 시스템에서 확인 절차는 안전장치. (-) 변경마다 한 번의 추가 대화 턴 소요. |
| **로컬 실행 적합성** | ✅ 완전 적합 — Claude Code의 대화 흐름 내 처리 |
| **출처** | T2 (ux-teammate), T3 (safety-teammate) |

**확인 플로우 순서**:

```
1. 사용자: "Type A 허용오차를 -5%로 완화해줘"
2. Claude: [Read] chart60_120Filter.py → 현재 _TYPE_A_ALIGN_TOL = 0.965
3. Claude: 변경 요약 테이블 표시
   | 파라미터 | 현재 값 | 변경 후 |
   | _TYPE_A_ALIGN_TOL | -3.5% (0.965) | -5.0% (0.950) |
   + 영향 예측 (B-10) + 범위 검증 (B-9)
4. Claude: "적용할까요?"
5. 사용자: "해봐"
6. Claude: [Bash] cp → 백업 생성 (B-8)
7. Claude: [Edit] 상수 값 변경
8. Claude: [Edit] tuning-log.md 행 추가
9. Claude: "변경 완료. 필터를 다시 돌려볼까요?"
```

---

### B-8. 백업 전략: Sibling-File + 5개 회전

| 항목 | 내용 |
|---|---|
| **핵심** | `<filename>.bak.<YYYYMMDD_HHmmss>` 형태로 원본 옆에 저장. `sorted(glob("*.bak.*"))`로 시간순 정렬, 5개 초과 시 가장 오래된 것 삭제. `.gitignore`에 `*.bak.*` 추가. 삭제 전 해당 설정이 tuning-log에 기록되었는지 확인(TS-2a). **⚠️ 복원 안전 규칙 (3차 적대적 성찰 추가)**: (1) 복원 시도 전 대상 `.bak` 파일이 실제 존재하는지 `glob("*.bak.*")` 확인. 미존재 시 "백업 파일이 삭제되었습니다" 한국어 안내. (2) `.bak` 파일 소실 시 **tuning-log.md 기반 복원 경로**: 로그에서 해당 파라미터의 old_value를 추출하여 Edit으로 직접 복원. 이 경로를 B-22 MASTER_SEQUENCE의 RESTORE 분기에 인코딩. |
| **제1 목적 연결** | TS-2, TS-2a 이행. "원래대로 되돌려줘" 명령(FR-6.4)의 물리적 기반. |
| **트레이드오프** | (+) 원본 옆 배치 → 경로 혼란 최소화. (+) 시간순 정렬로 회전 간단. (-) 소스 트리 오염 → `.gitignore` 필요. (-) 5개 회전으로 과거 "좋은 설정"의 .bak 소실 가능 → tuning-log 기반 복원이 폴백(비기술 사용자도 Claude가 대행하므로 문제 없음). 대안: 별도 `backups/` 디렉터리는 경로 혼란 유발. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 순수 파일시스템 작업 (cp, glob, rm) |
| **출처** | T3 (safety-teammate) |

---

### B-9. 범위 검증: 선언적 Range Map

| 항목 | 내용 |
|---|---|
| **핵심** | 스킬 references/에 파라미터별 `[물리적 범위, 위험 구간, 경고 메시지]` 테이블 삽입. Edit 전 Claude가 이 테이블 대조. 범위 밖 → 거부, 위험 구간 → 경고 + 이론적 근거 제시. |
| **제1 목적 연결** | TS-3, FR-5.5 이행. 허용오차 30%면 필터 무력화 — 사전 차단 필수. |
| **트레이드오프** | (+) 선언적(프롬프트 레벨) → Claude가 우회 불가. (+) 런타임 비용 0. (-) 정적 스냅샷이므로 새 상수 추가 시 수동 업데이트 필요. Phase 1(~30개 파라미터, 안정 코드)에서는 충분. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 순수 프롬프트 엔지니어링 |
| **출처** | T3 (safety-teammate) |

**Range Map 초안 예시**:

```
| ID | 타입 | 물리적 범위 | 위험 구간 | 경고 메시지 |
|---|---|---|---|---|
| S1-1 | tolerance | [0.00, 0.50] | > 0.15 | "허용오차 15% 초과 시 정배열 판정이 사실상 무효화됩니다" |
| S1-5 | ratio | [0.00, 1.00] | > 0.20 | "수렴 임계값 20% 초과 시 수렴 판정이 무의미합니다" |
| S4-1 | int | [1, 16] | = 1 | "외국인 1일 매도만으로 제외하면 대부분 종목이 탈락합니다" |
| S4-1 | int | [1, 16] | ≥ 10 | "10일 연속 매도까지 허용하면 수급 필터가 사실상 무력화됩니다" |
```

**⚠️ 단위 변환 규칙 (2차 성찰 추가)**: Range Map의 `물리적 범위`는 **tolerance ratio** 단위다 (하방 이격 비율). Python 코드의 실제 값(multiplier)과는 `tolerance = 1 - 코드값` 관계. 예: 코드값 `0.965` ↔ tolerance `0.035` ↔ 사용자 표현 `-3.5%`. Range Map 대조 시 반드시 코드값을 tolerance로 변환한 후 비교해야 한다. 세 가지 표현(코드 배수, tolerance 비율, 사용자 퍼센트)이 공존하므로 스킬 구현 시 변환 로직을 명시적으로 인코딩할 것.

**⚠️ 단위 변환 SOT 위치 (3차 적대적 성찰 추가)**: 변환 공식은 `filter-tune` 스킬의 `references/unit-conversion.md`에 SOT로 1곳 정의. Range Map 대조, 사용자 입력 파싱, 결과 보고 등 3곳에서 이 SOT를 참조하여 변환 로직 중복 방지. 변환 공식: `tolerance = 1 - multiplier`, `user_pct = tolerance × 100`, `multiplier = 1 - (user_pct / 100)`.

**⚠️ Range Map 위험 구간 근거 (3차 적대적 성찰 추가)**: Range Map의 위험 구간 임계값(예: tolerance > 0.15)은 이론 문헌에서 정확한 수치 기준이 부재한 경우 **경험적 판단**에 기반한다. 이를 명시하기 위해 Range Map 테이블에 `근거` 칼럼 추가를 권장: `이론 기반`(문헌 인용 가능) 또는 `경험적 판단`(필터 무력화 지점의 합리적 추정). 이 구분은 사용자가 위험 경고의 신뢰도를 판단하는 데 도움이 된다.

---

### B-10. 영향 추정: masterReference.log Gap 분석

| 항목 | 내용 |
|---|---|
| **핵심** | 파라미터 변경 시, masterReference.log에서 해당 Stage 탈락 종목의 실제값을 추출하고, 변경 후 허용 범위와 비교하여 "약 N개 추가 통과 예상" 추정. 항상 "정확한 결과는 필터 재실행 필요" 안내 동반. 필터 로직 재구현 없이 Gap 비교만으로 방향성 제시. |
| **제1 목적 연결** | FR-5.2(a) 정확한 구현. 변경 전 방향성 판단 → fine-tuning 의사결정 지원. |
| **트레이드오프** | (+) 필터 로직 재구현 불필요 — 로그 읽기+비교만. (-) masterReference.log에 수치 Gap 데이터가 없으면 정밀도 저하. (-) Cascading 효과 반영 불가(Stage 1 통과해도 Stage 3 탈락 가능) — 이 한계를 사용자에게 명시 필수. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 순수 파일 읽기 + 산술 비교 |
| **출처** | T3 (safety-teammate) |
| **⚠️ 전제조건** | masterReference.log의 실제 출력 포맷 검증 필요 (Research 단계 필수 조사 C-2) |

---

### B-11. 장시간 실행 전략: 기본 분리 모드

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md 규칙: "일일 스크리닝은 기본적으로 `run_prefetch`(1회, 10-15분) + `run_filters`(즉시, 반복 가능) 2단계로 실행. `run_full_research_flow`는 사용자 명시 요청 시에만 사용." prefetch는 `run_in_background`로 실행 가능, 완료 후 알림. **⚠️ 백그라운드 완료 후 처리 시퀀스 (3차 적대적 성찰 추가)**: `run_in_background` 완료 알림 수신 시 → (1) stdout에서 처리 종목 수 추출 → (2) stderr 존재 여부 확인 → (3) B-4 에러 분류표 적용 → (4) 한국어 결과/에러 보고. 이 시퀀스를 stock-scan 스킬에 명시적으로 인코딩하여, 백그라운드 실행 결과가 에러 래핑 없이 사용자에게 노출되는 것을 방지. |
| **제1 목적 연결** | 핵심목적 2(반복 튜닝)의 물리적 기반 — prefetch 1회 후 `run_filters` N회가 기존 시스템의 설계 의도. 핵심목적 1의 사용자 경험(장시간 무응답 방지). |
| **트레이드오프** | (+) 튜닝 루프(prefetch 1회 → filters N회)에 최적. (+) 사용자에게 단계별 진행 보고 가능. (-) prefetchManifest.json 부재 시 run_filters 실패 → 폴백 규칙 필요. (-) 사용자가 "그냥 한 번에 해줘"를 원할 때도 분리 제안하면 마찰 발생. |
| **로컬 실행 적합성** | ✅ 완전 적합 — Claude Code Bash 도구의 run_in_background 활용 |
| **출처** | T4 (integration-teammate) |

---

### B-12. 세션 연속성: screener_state.json + 기존 Hook 활용

| 항목 | 내용 |
|---|---|
| **핵심** | 기존 Context Preservation System의 Hook에 `screener_state.json`(last_scan_date, last_param_changes, last_results_summary) 추가. 세션 시작 시 로드하여 "지난 세션 요약" 자동 제공. tuning-log.md와 함께 세션 간 연속성 보장. |
| **제1 목적 연결** | "지난번 설정 뭐였지?"(FR-6.3, SC-2.7)에 답변 가능. 세션 간 튜닝 히스토리 연속성. |
| **트레이드오프** | (+) 기존 Hook 인프라 재활용(거의 무비용 구현). (-) Claude Code 외부에서 파일 수동 수정 시 비동기화 가능. **완화**: 세션 시작 시 실제 `Final` 상수와 기록값 대조, 불일치 시 한국어 경고. (-) screener_state.json 포맷 설계 필요. **⚠️ Hook 인프라 가용성 주의**: 배포 위치(B-19)에 따라 AgenticWorkflow의 Context Preservation Hook 인프라를 사용할 수 없을 수 있음. 선택지 (A) kiwoom-rest-trader 내부 또는 (B) 별도 디렉터리 배치 시, Hook 없이 screener_state.json을 관리하는 대안 필요(예: CLAUDE.md 규칙으로 세션 시작/종료 시 수동 읽기/쓰기 인코딩). C-8에서 확정 필요. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 로컬 JSON 파일 읽기/쓰기 |
| **출처** | T2 (ux-teammate) |

**screener_state.json 초안**:

```json
{
  "last_scan_date": "20260526",
  "last_param_changes": [
    {"timestamp": "2026-05-26T14:30:22", "stage": 1, "param": "_TYPE_A_ALIGN_TOL", "old": 0.965, "new": 0.950}
  ],
  "last_results_summary": {"total_input": 2450, "final_passed": 12, "stage1_passed": 82},
  "current_backup_files": ["chart60_120Filter.py.bak.20260526_143022"]
}
```

---

### B-13. Pre-flight 검증

| 항목 | 내용 |
|---|---|
| **핵심** | 세션 시작 시 경량 검증: (a) kiwoom-rest-trader 디렉터리 존재, (b) `.venv/bin/python` 실행 가능, (c) `reports/` 쓰기 권한. 전체 검증(패키지 import, API 상태)은 첫 실행 요청 시 1회. **⚠️ 추가 검증 항목 (3차 적대적 성찰 추가)**: (d) **prefetch 완료 후 입력 종목 수 검증**: `run_prefetch` 완료 시 stdout 또는 `prefetchManifest.json`에서 수집 종목 수를 추출, 기대치(~2,500)의 90% 미만이면 "수집이 불완전합니다. {N}/{기대}개 종목만 수집되었습니다. 결과가 부정확할 수 있습니다" 경고. (e) **파라미터 변수명 존재 검증 (PRD R-2 감지)**: 파라미터 변경 시도 전 `grep -n '{변수명}' {파일경로}`로 대상 변수가 코드에 존재하는지 확인. 미존재 시 "변수명이 변경된 것 같습니다. 유사한 이름을 검색합니다" → 자동 탐색 + 사용자 알림. |
| **제1 목적 연결** | FR-1.7 이행. 전제조건 미충족 → 영어 에러 → 사용자 이탈의 연쇄 차단. (d)는 불완전 데이터 기반 튜닝 방지, (e)는 코드 리팩토링 후 파라미터 변경 실패 방지. |
| **트레이드오프** | (+) 매 세션 ~2초 추가이나 venv 손상 조기 감지. (-) 매번 검증은 과도할 수 있음 → 경량/전체 분리로 완화. (-) API 인증 상태는 실제 호출 전까지 확인 불가. (+) (d)는 prefetch 부분 성공(exit 0이나 종목 수 부족) 감지 — 기존 에러 래핑(B-4)이 커버하지 못하는 사각지대. (+) (e)는 kiwoom-rest-trader 리팩토링 후에도 시스템 적응 가능. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 파일시스템 + import 체크 |
| **출처** | T4 (integration-teammate) |

---

### B-14. 출력 파싱 전략

| 항목 | 내용 |
|---|---|
| **핵심** | stage*_passed.md 파일은 줄 단위 종목 목록 (Markdown 테이블이 아닌 단순 텍스트). Claude는 줄 수 세기 + 목록 읽기로 결과 보고. 방어적 규칙: 파이프(`|`) 문자 포함 시 Markdown 테이블로 처리, 데이터 행만 카운트. |
| **제1 목적 연결** | FR-2(결과 해석)의 기술적 기반. 잘못 파싱하면 결과 왜곡. |
| **트레이드오프** | (+) 단순 포맷이므로 파싱 실패 가능성 극히 낮음. (-) 포맷 변경 시 방어적 규칙이 커버. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 순수 파일 읽기 |
| **출처** | T4 (integration-teammate) |
| **⚠️ 전제조건** | stage*_passed.md 실제 포맷 검증 필요 (Research 단계 필수 조사 C-6-2) |

---

### B-15. 날짜 해석 규칙

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md에 날짜 해석 규칙 블록: (1) "오늘" = `date +%Y%m%d`, (2) "어제" = 이전 영업일(주말 건너뜀), (3) "이번 주" = 이번 주 월~금 중 오늘 이하, (4) 과거 날짜 유효성은 `reports/{date}/` 디렉터리 존재로 판단, (5) 미래/당일은 weekday 체크. |
| **제1 목적 연결** | 사용자가 "어제 돌려줘"라고 할 때 오늘이 월요일이면 금요일로 해석해야 함. 잘못된 날짜 → 데이터 부재 에러. |
| **트레이드오프** | (+) 디렉터리 존재 체크로 공휴일 하드코딩 회피. (-) 당일 첫 수집 전에는 디렉터리 미존재 → "아직 수집하지 않았습니다" 분기 필요. (-) 한국 시장 공휴일 하드코딩은 연도별 갱신 필요이므로 회피. |
| **로컬 실행 적합성** | ✅ 완전 적합 — date 산술 + 파일시스템 존재 체크 |
| **출처** | T4 (integration-teammate) |

---

### B-16. 튜닝 로그: Append-only Markdown + 월별 아카이빙

| 항목 | 내용 |
|---|---|
| **핵심** | `reports/tuning-log.md`에 append-only Markdown 테이블. 행: `| datetime | param_id | param_name | old_value | new_value | stocks_passed_before | stocks_passed_after | notes |`. 200행 초과 시 `tuning-log.YYYYMM.md`로 아카이빙 + 신규 파일. **⚠️ 조합별 비교 뷰 (3차 적대적 성찰 추가 — FR-6.3 구체화)**: "설정 A: 15개, 설정 B: 22개" 같은 조합별 비교는 tuning-log.md의 `stocks_passed_after` 칼럼을 시간순으로 읽어 Claude가 동적으로 생성. 별도 저장 구조 불필요 — tuning-log.md가 이미 변경-결과 매핑을 포함하므로, Claude가 "이 세션에서의 실험 결과를 정리해줘" 요청 시 log를 읽어 비교 테이블을 생성. |
| **제1 목적 연결** | FR-6.6 정확한 구현. "지난번 좋았던 설정"(SC-2.7) 조회 가능. FR-6.3(조합 실험 결과 추적)도 log 기반으로 해결. |
| **트레이드오프** | (+) Claude Code 외부에서도 사람이 읽을 수 있는 Markdown. (+) append-only = 데이터 손실 없음. (-) Claude Code 외부에서 파라미터 수정하면 로그에 미반영. **완화**: 세션 시작 시 현재 값 vs 마지막 로그 엔트리 비교. 대안: YAML/JSONL은 기계 파싱에 유리하나 사용자(비기술)가 읽기 어려움. |
| **로컬 실행 적합성** | ✅ 완전 적합 — Edit tool로 append, Bash로 mv(아카이빙) |
| **출처** | T3 (safety-teammate), T1 (arch-teammate) |

---

### B-17. 공유 상수 처리: 정적 의존 맵

| 항목 | 내용 |
|---|---|
| **핵심** | 스킬 reference에 공유 상수별 영향 범위 맵 삽입. `_ALIGN_TOL_LOOSE` → [Type B: MA10-MA20, Type B: MA60-MA306, Type C: MA60-MA306, Type D: 60분 정배열]. 변경 감지 시 의무적 다중 영향 경고 + "특정 Type만 변경하려면 전용 상수 신설 필요(TS-1 예외, 명시적 승인 필요)" 안내. |
| **제1 목적 연결** | PRD §5.4 이행. 사용자가 공유 상수의 다중 영향을 모르면 의도치 않은 필터 변경 발생. |
| **트레이드오프** | (+) 정적 맵은 현재 1개 공유 상수에 비례적. (-) 코드 변경으로 새 공유 상수 발생 시 수동 갱신 필요. 대안: AST 파싱으로 동적 탐지 가능하나, 1개 상수에 과도한 복잡성. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 프롬프트 내 정적 데이터 |
| **출처** | T3 (safety-teammate) |

---

### B-18. Research 단계 필수 조사 항목

| 항목 | 내용 |
|---|---|
| **핵심** | workflow.md의 Research 단계에서 Implementation 전 반드시 4가지 산출물 생산 필요: (1) 필터 의존 그래프 — 어떤 필터가 어떤 파일 읽는지, 실행 순서, 독립 실행 가능 여부. (2) 파라미터 전수 인벤토리 — 모든 `Final` 상수의 이름/타입/현재값/유효범위/소속 필터/의미. (3) 출력 스키마 — 각 산출물 파일의 정확한 포맷. (4) 에러 분류 — 실제 발생 가능한 예외 유형과 stderr 패턴. |
| **제1 목적 연결** | 이 4가지 조사 없이 Implementation에 진입하면 추측 기반 구현 → 품질 저하(절대 기준 1 위반). |
| **트레이드오프** | (+) 철저한 사전 조사 → 구현 품질 보장. (-) 1-2시간 Research 에이전트 시간 소요. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 코드 분석(Read, Grep) |
| **출처** | T1 (arch-teammate), T4 (integration-teammate) 합의 |

---

### B-19. 배포 위치 결정: 산출물이 어디에 살 것인가 [P0]

| 항목 | 내용 |
|---|---|
| **핵심** | CLAUDE.md + 2개 스킬(B-1)이 최종적으로 배치되는 위치를 결정해야 한다. 선택지: (A) `kiwoom-rest-trader/` 내부에 직접 배치 — Claude Code가 해당 디렉터리에서 작동, (B) 별도 디렉터리(예: `stock-filtering-collector/`)에 배치 — kiwoom-rest-trader를 외부 시스템으로 참조, (C) `AgenticWorkflow/` 내부에 하위 프로젝트로 배치 — 기존 Hook·Context Preservation 인프라 활용 가능. 각 선택지에 따라 B-12(Hook 활용), B-6(경로 상수), 전체 스킬 구조가 달라진다. |
| **제1 목적 연결** | 배포 위치가 미정이면 모든 경로 상수(B-6), Hook 가용성(B-12), Pre-flight 검증(B-13)의 전제가 불확실. 핵심목적 1·2 모두의 구현 기반. |
| **트레이드오프** | (A) (+) 경로 최단, 실행 단순. (-) kiwoom-rest-trader 리포에 Claude 전용 파일 혼재. (B) (+) 관심사 분리. (-) 크로스 디렉터리 참조 복잡성. (C) (+) Hook 인프라 무비용 재활용. (-) AgenticWorkflow 프레임워크 의존성 발생, 프레임워크 학습 곡선. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 어떤 선택이든 로컬 파일시스템 내 배치 |
| **출처** | 성찰 — 메타 레벨 공백 식별 |
| **⚠️ 전제조건** | C-8(배포 위치 미결정)에서 확정 필요. B-12, B-6, B-13에 연쇄 영향. |

---

### B-20. Implementation 구축 순서: 무엇을 먼저 만들 것인가 [P0]

| 항목 | 내용 |
|---|---|
| **핵심** | workflow.md의 Implementation 단계에서 산출물을 어떤 순서로 구축할지 정의. 제안 순서: (1) CLAUDE.md 골격(경로 상수 + 안전 규칙) → (2) stock-scan 스킬 MVP(단일 날짜 실행 + 결과 보고) → (3) filter-tune 스킬 MVP(단일 파라미터 변경 + 확인 플로우) → (4) 교차 기능(혼합 의도 라우팅, 세션 연속성) → (5) 엣지 케이스(다중 날짜, 에러 분류 전체). 각 단계에 "최소 동작 검증" 기준 포함. |
| **제1 목적 연결** | 구축 순서 없이 Implementation에 진입하면 산발적 구현 → 핵심 기능(실행·튜닝)이 엣지 케이스에 묻힘. 핵심목적 1(CLAUDE.md + stock-scan)과 핵심목적 2(filter-tune)의 우선순위를 명시. |
| **트레이드오프** | (+) MVP 우선 → 조기 검증 가능. (+) 의존 관계 순서(CLAUDE.md → 스킬)로 병렬 작업 방지. (-) 엣지 케이스(다중 날짜, 에러 분류)가 후순위로 밀릴 수 있음 — 핵심 기능 안정화가 전제이므로 수용 가능. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 구축 순서는 파일 생성·편집 순서일 뿐 |
| **출처** | 성찰 — Implementation ordering 부재 식별 |

---

### B-21. 구축 후 검증 전략: 어떻게 동작을 확인할 것인가 [P1]

| 항목 | 내용 |
|---|---|
| **핵심** | 구축된 CLAUDE.md + 스킬이 실제로 의도대로 동작하는지 검증하는 전략. (1) Smoke test 시나리오: "오늘 스캔해줘" → stock-scan 정상 실행, "Stage 1 조건 보여줘" → 파라미터 테이블 출력 등 5-7개 골든 패스. (2) 안전 검증: TS-1 위반 시도("필터 로직 바꿔줘") → 거부 확인. (3) 에러 경로: venv 없는 상태에서 실행 → 한국어 에러 래핑 확인. 모든 검증은 실제 Claude Code 세션에서 수동 수행(자동 테스트 프레임워크 불필요). |
| **제1 목적 연결** | 산출물이 "프롬프트 파일"이므로 유닛 테스트 불가. 실제 사용 시나리오로만 검증 가능. 검증 없이 완료 선언하면 절대 기준 1(품질) 위반. |
| **트레이드오프** | (+) 실사용 환경에서 직접 검증 → 가장 높은 신뢰도. (-) 수동 검증이므로 시간 소요. (-) kiwoom-rest-trader API 의존 시나리오는 API 접속 가능 시에만 검증 가능. **완화**: API 불필요 시나리오(파라미터 조회, 범위 검증)를 우선 검증. |
| **로컬 실행 적합성** | ✅ 완전 적합 — Claude Code 세션에서 직접 실행 |
| **출처** | 성찰 — 검증/테스트 아이디어 부재 식별 |

---

### B-22. 핵심목적 2 통합 튜닝 흐름: B-7/8/9/10/16/17 연결 [P1]

| 항목 | 내용 |
|---|---|
| **핵심** | 핵심목적 2 관련 6개 아이디어(B-7 확인 플로우, B-8 백업, B-9 범위 검증, B-10 영향 추정, B-16 튜닝 로그, B-17 공유 상수)가 개별 존재하나, 하나의 End-to-End 튜닝 사이클로 통합되지 않았음. 통합 흐름: 사용자 요청 → B-9(범위 검증) → B-17(공유 상수 경고) → B-10(영향 추정) → B-7(확인 테이블 + 승인) → B-8(백업) → Edit → B-16(로그 기록) → "필터 재실행?" 제안. 이 순서를 filter-tune 스킬의 마스터 시퀀스로 인코딩. |
| **제1 목적 연결** | 핵심목적 2("사용자가 필터 조건을 fine-tuning하기 쉽게 도울 수 있어야 한다")의 직접 구현. 6개 아이디어가 각각 동작해도 순서·분기가 인코딩되지 않으면 Claude가 단계를 누락하거나 순서를 뒤집을 수 있음. |
| **트레이드오프** | (+) 마스터 시퀀스 1곳에서 튜닝 흐름 전체 관리. (+) 단계 누락 방지. (-) 경직된 시퀀스는 "빠르게 바꿔줘" 류의 급한 요청에 마찰. **완화**: "간소 모드" 분기(범위 내 + 비공유 상수 → B-10/B-17 스킵) 고려. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 프롬프트 내 시퀀스 인코딩 |
| **출처** | 성찰 — 핵심목적 2 관련 아이디어의 통합 흐름 부재 식별 |

**통합 튜닝 시퀀스 (초안)**:

```
MASTER_SEQUENCE: PARAM_CHANGE(param_id, new_value)
  Step 0: [TS-4] 복수 파라미터 동시 변경 감지 → "한 번에 하나씩 변경을 권장합니다.
          여러 파라미터를 동시에 바꾸면 어떤 변경이 효과를 냈는지 분리할 수 없습니다.
          그래도 진행할까요?" 경고. 사용자 승인 시 각 파라미터에 대해 Step 1~8 순차 적용.
  Step 1: [B-9] Range Map 대조 → 범위 밖이면 REJECT + 사유
  Step 2: [B-17] 공유 상수 여부 확인 → 공유이면 영향 범위 경고
  Step 3: [B-10] masterReference.log Gap 분석 → "약 N개 추가 통과 예상"
    FALLBACK: masterReference.log 미존재 시(첫 사용 등) → Step 3 스킵,
              Step 4에서 "추정 데이터 없음. 변경 후 필터 재실행으로 실제 영향을 확인합니다" 안내
  Step 4: [B-7] 변경 전/후 테이블 + Step 2-3 결과 통합 표시 → "적용할까요?"
  Step 5: [B-8] 백업 생성 (sibling-file)
  Step 6: Edit Final 상수 값 변경
  Step 7: [B-16] tuning-log.md에 행 추가
  Step 8: "필터를 다시 돌려볼까요?" 제안

  SHORTCUT: 범위 내 + 비공유 상수 → Step 2, 3 스킵 가능

BRANCH: CONFIRM — "이걸로 확정할게" (FR-6.5)
  Step 1: tuning-log.md 마지막 행에 notes 칼럼 "✓ 확정" 마킹
  Step 2: "현재 설정이 확정되었습니다. 다음 세션에서도 이 설정으로 시작합니다." 안내
  Step 3: screener_state.json의 last_param_changes를 "confirmed" 상태로 갱신
```

---

### B-23. 면책조항 자동 삽입 메커니즘 [P2]

| 항목 | 내용 |
|---|---|
| **핵심** | FR-8("모든 결과 출력에 면책조항 포함")을 체계적으로 구현. CLAUDE.md에 "결과 보고 시 항상 면책 블록 삽입" 규칙 + 면책 템플릿 정의 + **표현 정책(FR-8.2/8.3)** 인코딩. 면책 대상: 스크리닝 결과 보고, 파라미터 변경 후 재실행 결과, 영향 추정(B-10). 면책 불필요: 파라미터 조회, 에러 메시지, 시스템 상태 보고. **표현 정책**: (O) "기술적 완성도가 높은 종목", "필터 조건을 충족한 종목" / (X) "이 종목을 사세요", "매수 추천", "유망 종목". 종목 결과를 "추천"이 아닌 "선별 결과"로 프레이밍. |
| **제1 목적 연결** | FR-8 정확한 이행. 투자 관련 정보 제공 시 법적 보호 + 사용자의 올바른 기대 설정. |
| **트레이드오프** | (+) 선언적 규칙 → Claude가 규칙 따르면 100% 적용. (-) 매번 면책 표시 → UX 피로 가능. **완화**: 짧은 1줄 면책("⚠️ 투자 판단은 본인 책임이며, 이 결과는 참고 자료일 뿐입니다.") + 동일 세션 내 첫 번째만 전체 면책, 이후 축약. |
| **로컬 실행 적합성** | ✅ 완전 적합 — 프롬프트 규칙 |
| **출처** | 성찰 — FR-8 독립 메커니즘 부재 식별 |

---

### B-24. 다중 날짜 순차 실행 전략 [P2]

| 항목 | 내용 |
|---|---|
| **핵심** | "이번 주 전부 돌려줘"(SCAN_RANGE 의도)의 구현 전략. (1) 영업일 목록 생성: weekday 체크 + `reports/{date}/` 존재 여부로 과거 날짜 필터링. (2) 순차 실행: 날짜별 `run_full_research_flow` 또는 `run_prefetch` + `run_filters`. (3) 진행률 보고: "3/5일 완료" 형태. (4) 부분 실패 처리: 특정 날짜 실패 시 나머지 계속 + 실패 날짜 보고. Filter_condition_update.py가 이미 다중 날짜를 space-separated args로 지원하므로 활용 가능. |
| **제1 목적 연결** | SCAN_RANGE(B-3 의도 클러스터)의 구체적 실행 전략. 핵심목적 1의 확장 사용 패턴. |
| **트레이드오프** | (+) 기존 시스템의 다중 날짜 지원 활용. (-) 5일 순차 실행 시 50-75분 소요 → `run_in_background` 필수. (-) 날짜별 독립 실행이므로 중간 결과 축적 불가(각 날짜가 별도 리포트). |
| **로컬 실행 적합성** | ✅ 완전 적합 — Bash 반복 실행 |
| **출처** | 성찰 — B-3 SCAN_RANGE 의도의 구현 전략 부재 식별 |

---

### B-25. 최초 사용자 온보딩 시나리오 [P2]

| 항목 | 내용 |
|---|---|
| **핵심** | 사용자가 처음 Claude Code 세션을 열었을 때의 경험 설계. (1) Pre-flight 검증(B-13) 자동 실행. (2) 검증 통과 시 "무엇을 할 수 있는지" 한국어 안내(3-5개 핵심 명령 예시). (3) 첫 실행 제안: "오늘 날짜로 스크리닝을 해볼까요?" (4) 첫 실행 후 결과 해석 가이드. 반복 사용자(screener_state.json 존재)는 "지난 세션 요약"으로 분기. |
| **제1 목적 연결** | 사용자("코드 구현 능력이 전혀 없다")의 첫 접점. 온보딩 실패 → 시스템 전체 미사용. |
| **트레이드오프** | (+) 비기술 사용자에게 필수적인 첫인상 관리. (-) 반복 사용자에게 온보딩이 반복되면 마찰. **완화**: screener_state.json 존재 여부로 신규/재방문 분기. |
| **로컬 실행 적합성** | ✅ 완전 적합 — CLAUDE.md 규칙 + JSON 파일 존재 체크 |
| **출처** | 성찰 — 최초 사용 시나리오 부재 식별 |

---

## 3. 상충·미해결 지점

### C-1. 파라미터 카탈로그 SOT 이중성

**현상**: PRD는 "SOT는 항상 Python 소스"라고 선언하면서, 스킬 references/에 카탈로그(범위 검증용 B-9)를 둬야 한다.

**해결 방향 (미확정)**: 카탈로그는 문서화 + 범위 검증용, 실제 값은 항상 코드에서 실시간 추출. 두 레이어의 역할 분리가 핵심. 카탈로그에 "현재 값" 필드를 두지 않고 "유효 범위"와 "경고 규칙"만 두면 비동기화 문제가 해소됨.

**해결 필요 시점**: workflow.md 작성 시 B-9 상세 설계 단계.

---

### C-2. masterReference.log Gap 데이터 가용성

**현상**: FR-5.2의 Gap 기반 추정(B-10)은 masterReference.log의 출력 포맷에 의존. 실제 log가 수치 Gap을 포함하는지 미검증.

**해결 방향 (미확정)**: Research 단계에서 Filter_condition_update.py를 실행하여 실제 log 출력 확인. Gap 미포함 시 → (a) Stage 수준 추정("이 Stage에서 N개 탈락")으로 퇴보하거나, (b) 필터 모듈의 `filter_stock()` 반환값에서 직접 Gap 추출하는 보조 스크립트 검토.

**해결 필요 시점**: workflow.md Research 단계 (Implementation 진입 전 필수).

---

### C-3. `_ALIGN_TOL_LOOSE` 공유 상수 딜레마

**현상**: 이 상수 변경 시 Type B/C/D 동시 영향. "특정 Type만 변경" → 전용 상수 신설 → 코드 로직 수정 → TS-1("상수만 변경") 위반.

**해결 방향 (미확정)**: Phase 1에서는 공유 영향 경고 + 사용자 승인으로 처리. 전용 상수 분리는 Phase 2로 이관. TS-1 예외 승인 플로우를 스킬에 인코딩해 두되, Phase 1에서는 실행하지 않음.

**해결 필요 시점**: filter-tune 스킬 Implementation 단계.

---

### C-4. Stage 5 튜닝 불가

**현상**: financeFilter.py는 `Final` 상수가 없음(하드코딩된 `cup_nga < 0`). 사용자가 "적자 기준 완화" 요청 시 대응 불가.

**해결 방향 (미확정)**: CLAUDE.md에 명시적 한계 인코딩: "Stage 5 조건 변경 요청 시 → '현재 코드 구조상 변경 불가. Phase 2에서 상수화를 검토합니다' 안내." Phase 2에서 `_FINANCE_NGA_THRESHOLD: Final[int] = 0` 상수 신설 검토.

**해결 필요 시점**: Phase 1 범위에서는 안내 규칙만 인코딩하면 충분.

---

### C-5. 날짜 해석의 시장 휴일 문제

**현상**: 한국 시장 공휴일 목록 하드코딩은 연도별 갱신 필요.

**해결 방향 (미확정)**: 과거 날짜는 `reports/{date}/` 디렉터리 존재로 판단. 미래/당일은 weekday 체크. 공휴일 하드코딩 회피. kiwoom-rest-trader에 `_exchange.py` 등 휴일 로직이 있으면 활용 가능(Research 단계에서 확인).

**해결 필요 시점**: stock-scan 스킬 Implementation 단계.

---

### C-6. Research 단계 필수 조사 목록 (합의)

4개 teammate의 합의로 도출된 Implementation 전 필수 조사 항목:

| # | 조사 항목 | 관련 아이디어 | 관련 FR | 조사 대상 |
|---|---|---|---|---|
| 1 | masterReference.log 실제 출력 포맷 (Gap 수치 포함 여부) | B-10 | FR-3.4, FR-5.2 | Filter_condition_update.py 실행 결과 |
| 2 | stage*_passed.md 정확한 포맷 — **특히 Stage 1에서 Type A/B/C/D/E 패턴 유형 정보 포함 여부** (FR-2.2 "각 종목이 통과한 패턴 요약" 구현의 전제. 미포함 시 `filter_stock()` 반환값의 `category` 필드 등 대안 경로 조사 필요) | B-14 | FR-2.1, FR-2.2, FR-6.2 | reports/YYYYMMDD/ 내 실제 파일 + `filter_stock()` 반환값 구조 |
| 3 | kiwoom-rest-trader 실제 에러 패턴 | B-4 | FR-1.5 | 실행 스크립트 stderr + 예외 처리 코드 |
| 4 | 각 필터 모듈의 `Final` 상수 현재 값 전수 추출 | B-9 | FR-4.1 | grep -n 'Final' src/kiwoom/itemFilter/*.py |

---

### C-7. FR-7(이론 가이드) 독립 아이디어 부족

**현상**: 회의에서 FR-7에 대한 독립 아이디어가 도출되지 않음. B-9(Range Map)에 이론적 근거가 포함되어 있으나, 시장 레짐 인식(FR-7.2)이나 파라미터별 권장 범위(FR-7.3)에 대한 체계적 접근이 부족.

**해결 방향 (미확정)**: filter-tune 스킬의 references/에 부록 A(PRD)의 이론↔필터 매핑 문서를 포함. 시장 레짐별 조정 가이드(강세/약세/횡보)를 별도 테이블로 작성. 이론 문헌(Minervini, Weinstein, Wyckoff, VCP, CANSLIM)의 파라미터 권장 범위를 정리.

**해결 필요 시점**: filter-tune 스킬 Implementation 단계.

---

### C-8. 배포 위치 미결정

**현상**: B-1(2-Skill 구조), B-6(경로 상수), B-12(세션 연속성), B-13(Pre-flight) 등 대부분의 아이디어가 "CLAUDE.md + 스킬 파일이 어디에 존재하는가"를 전제하지만, 실제 배포 위치가 결정되지 않았음. 선택지 (A) kiwoom-rest-trader 내부, (B) 별도 디렉터리, (C) AgenticWorkflow 내부 — 각각 Hook 인프라 가용성, 경로 상수 구조, 디렉터리 오염 정도가 다름.

**해결 방향 (미확정)**: B-19에서 3가지 선택지의 트레이드오프를 정리했으나, 사용자의 실제 사용 패턴(Claude Code를 어느 디렉터리에서 여는가)과 기존 AgenticWorkflow 프레임워크 활용 의향에 따라 결정 필요. 이 결정이 B-6, B-12, B-13에 연쇄 영향을 미치므로 workflow.md Planning 단계 초기에 확정해야 함.

**해결 필요 시점**: workflow.md Planning 단계 초기 (Implementation 구조 전체에 영향).

---

### C-9. 메타 레벨 공백: 아이디어는 시스템 행동을 기술하나, 구축 방법은 기술하지 않는다

**현상**: B-1~B-18의 아이디어는 "완성된 시스템이 어떻게 동작해야 하는가"를 기술하지만, "그 시스템을 어떻게 구축하는가"(workflow.md의 핵심 관심사)에 대한 아이디어가 부족했음. 성찰에서 B-19(배포 위치), B-20(구축 순서), B-21(검증 전략)을 추가하여 부분 해소.

**해결 방향 (미확정)**: workflow.md 작성 시 B-19~B-21을 Research/Planning 단계의 핵심 입력으로 활용. 추가로 "스킬 파일 간 의존 관계"(CLAUDE.md → stock-scan → filter-tune의 참조 구조)와 "반복적 개선 루프"(구축 → 검증 → 수정 사이클)에 대한 구체화가 필요할 수 있음.

**해결 필요 시점**: workflow.md 작성 시.

---

### C-10. B-11 디폴트 실행 방식 vs FR-1.1 명세 긴장

**현상**: B-11은 "일일 스크리닝은 기본적으로 `run_prefetch` + `run_filters` 분리 모드"를 제안. 그러나 PRD FR-1.1은 "오늘 종목 스캔해줘" → 방식 A(`run_full_research_flow`) 자동 실행을 명시. B-3 의도 클러스터에서 `run_full_research_flow / run_prefetch+run_filters` 양쪽 병기로 미결 상태.

**해결 방향 (미확정)**: (a) PRD 충실: SCAN_TODAY는 run_full_research_flow 디폴트, 사용자가 "나눠서 해줘"라고 하면 분리 모드. (b) B-11 우선: 항상 분리 모드, "한 번에 해줘"만 run_full_research_flow. (c) 혼합: 첫 실행은 run_full_research_flow(온보딩 간결), 이후 튜닝 세션에서는 분리 모드 제안.

**해결 필요 시점**: workflow.md Planning 단계 — CLAUDE.md 라우팅 테이블 확정 시.

---

## 4. FR ↔ 아이디어 매핑 (커버리지 검증)

| PRD 요구사항 | 매핑된 아이디어 | 커버리지 |
|---|---|---|
| FR-1 (스크리너 실행) | B-6, B-11, B-13, B-15, B-24 | ✅ 충분 (B-24: 다중 날짜, B-13(d): 입력 검증, B-11: 백그라운드 에러 처리) |
| FR-2 (결과 해석) | B-3, B-14 | ✅ 강화 (B-3 COMPARE 체인: FR-2.4 교차 날짜 비교 구체화) |
| FR-3 (탈락 분석) | B-5 | ✅ 충분 |
| FR-4 (파라미터 가시화) | B-2, B-9 | ✅ 충분 |
| FR-5 (파라미터 변경) | B-7, B-8, B-9, B-10, B-17, B-22 | ✅ 충분 (B-22: 통합 흐름) |
| FR-6 (반복 실험) | B-11, B-12, B-16, B-22, B-3(CONFIRM) | ✅ 강화 (B-22: 튜닝 사이클+확정 분기, B-16: FR-6.3 조합 비교 뷰, B-8: tuning-log 기반 복원) |
| FR-7 (이론 가이드) | B-9 (부분) | ⚠️ 부분 — C-7 참조 |
| FR-8 (면책) | B-4, B-23 | ✅ 강화 (B-23: 면책 메커니즘 + 표현 정책 FR-8.2/8.3) |
| — (메타: 구축) | B-19, B-20, B-21, B-25 | ✅ 신규 — 구축 방법론 |

---

## 5. 메타데이터

### 5.1 저장 규칙

1. 이 파일은 **확정 설계가 아닌 가능성 탐색 기록**이다. 이후 성찰·수정이 계속된다.
2. 각 아이디어의 트레이드오프 양면(+/-)을 반드시 보존한다. 한쪽만 남기지 않는다.
3. "로컬 실행 적합성" 태그는 모든 아이디어에 필수이다.
4. 상충·미해결 지점(§3)은 "해결 방향(미확정)"으로 표기하며, 확정 결론을 내리지 않는다.
5. 새 아이디어 추가 시 B-{N+1} 번호를 부여하고, 해당 FR 연결을 §4에 반영한다.
6. 아이디어 삭제 시 본문에서 제거하되, §4 커버리지에서 해당 FR의 다른 커버 아이디어가 있는지 확인한다.

### 5.2 향후 성찰 진입점

- workflow.md 작성 시 이 파일을 1차 입력으로 사용.
- **[P0] B-19(배포 위치)와 C-8이 최우선 결정 사항** — B-6, B-12, B-13에 연쇄 영향.
- **[P0] B-20(구축 순서)가 workflow.md Implementation 단계의 골격** 결정.
- B-1(2-Skill 구조)의 확정 여부가 전체 구조의 분기점.
- B-22(통합 튜닝 흐름)가 filter-tune 스킬의 마스터 시퀀스 — 핵심목적 2의 핵심.
- C-6(Research 필수 조사)이 해결되어야 Implementation 진입 가능.
- C-7(FR-7 이론 가이드)은 filter-tune 스킬 설계 시 보완.
- C-9(메타 레벨 공백)는 B-19~B-21로 부분 해소되었으나, workflow.md 작성 시 추가 구체화 필요.
- C-10(B-11 vs FR-1.1 디폴트 실행 방식)은 CLAUDE.md 라우팅 테이블 확정 시 C-8과 함께 해소.

**전수 감사 누락 보완 요약** (v0.5.0):
- B-3: CONFIRM(FR-6.5 설정 확정) + ASK_MODULE(PRD §6.4 보조 모듈 질문 대응) 의도 클러스터 추가.
- B-2: CLAUDE.md 경계에 숫자 표기 규칙(§7.3) + 표현 정책(FR-8.2/8.3) 명시.
- B-5: masterReference.log 500행 아카이빙 회전 규칙(PRD §6.5) 추가.
- B-22: TS-4 복수 파라미터 동시 변경 경고(Step 0) + CONFIRM 분기 추가.
- B-23: FR-8.2/8.3 표현 정책(O/X 프레이밍, 추천 금지) 인코딩.
- C-10: B-11 디폴트 실행 방식 vs FR-1.1 명세 긴장을 미해결 지점으로 등록.
- §4: FR-6, FR-8 커버리지 강화 반영.

**3차 적대적 성찰 반영 요약** (v0.4.0):
- B-8: 백업 파일 존재 검증 + tuning-log 기반 복원 폴백 경로 추가.
- B-9: 단위 변환 SOT 위치(`references/unit-conversion.md`) + Range Map 위험 구간 근거 구분 칼럼 추가.
- B-11: `run_in_background` 완료 후 에러 체크 시퀀스 명시.
- B-13: (d) prefetch 입력 종목 수 검증 + (e) 파라미터 변수명 존재 검증(PRD R-2 감지).
- B-3: COMPARE 의도의 교차 날짜·변경 전후 비교 실행 체인 구체화(FR-2.4).
- B-16: FR-6.3 조합별 비교 뷰를 tuning-log 기반 동적 생성으로 해결.
- §4 FR 매핑: FR-1, FR-2, FR-6 커버리지 강화 반영.
