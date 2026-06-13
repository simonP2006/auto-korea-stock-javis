# auto-korea-stock-javis

키움증권 REST API 기반 **한국 주식 5-Stage 종목 스크리너** + 그 제품을 만든 **빌드 공장**을 단일 프로젝트로 통합한 모노레포.

> 두 시스템(제품 `kiwoom-rest-trader` + 공장 `AgenticWorkflow`)을 "한 지붕, 두 구역, 일방향 문" 구조로 통합. 상세 경위: [`EXECUTION_REPORT.md`](EXECUTION_REPORT.md) · 로드맵: [`BUILD_PLAN.md`](BUILD_PLAN.md)

## 빠른 시작

```
cd /Users/tajun/spJavis/auto-korea-stock-javis && claude
```
세션이 열리면 한 마디: **"오늘 스캔해줘"**

전체 사용법(매일 아침 운영·결과 읽는 법·튜닝·트러블슈팅)은 **[`docs/AKSJ-USER-MANUAL.md`](docs/AKSJ-USER-MANUAL.md)** 한 문서에 있다.

## 구조

| 디렉토리 | 역할 | 비고 |
|----------|------|------|
| `engine/` | **일일 스크리너 (제품)** — 키움 REST로 수집 → 5-Stage 필터 → 종목 선별 | 매일 사용하는 곳 |
| `factory/` | **빌드 공장 (동결)** — engine을 만든 워크플로우·비행기록 | 읽기 전용, 평소 안 건드림 |
| `docs/` | 통합 사용자 매뉴얼 | |
| `phase0/` `phase1/` `phase2/` | 통합 빌드 감사 기록 (검증 로그) | |

## 모드 경계 (불변 규칙)

- **사용 발화**("오늘 스캔", 14 Intent) → `engine/` 만.
- **"공장 빌드 모드"** 명시 발화 → `factory/` (그 외 어떤 경로로도 빌드 진입 불가 — 일방향 문).
- `factory/prompt/`(12단계 비행기록)는 **읽기 전용 동결**.

자세한 라우팅 규칙은 루트 [`CLAUDE.md`](CLAUDE.md) 참조.

## 운영 핵심

- **소요 시간(실측):** `run_full_research_flow` = **80분~6시간** (background 필수). `run_filters`(필터만) = <3분.
- **튜닝 핵심 자원:** 날짜별 `masterReference.md`·`.log`와 `tuning-log.md`는 git으로 영구 보존(재스캔에도 수기 입력 보존). 스캔 후 변경분 커밋.
- **시크릿:** 키움 키는 `engine/.env` 에만. `.env.example`은 견본(가짜 값)이며 실제 키 기입 금지. `.env`·토큰 캐시·`reports/` 대용량 데이터는 git 제외.

## 데이터 출처

키움증권 OpenAPI (REST + WebSocket 조건검색). 조회 전용 — **주문(매매) 기능 없음.** 산출물은 기술적 분석 도구의 결과이며 매수·매도 추천이 아니다.
