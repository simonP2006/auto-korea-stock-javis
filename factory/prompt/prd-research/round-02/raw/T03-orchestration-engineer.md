---
round: 2
type: raw
teammate: orchestration-engineer
axis: orchestration-scheduling
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
question_summary: "파이프라인 실행 구조, 상태 관리, 에러 처리, launchd 스케줄링, 관찰 가능성을 분석하여 주식 분석 시스템의 최적 오케스트레이션 수준 결정"
assumption_axis: "Lightweight vs Advanced Orchestration"
branch_a: "Lightweight Orchestration (순차 파이프라인, 수동 에러 복구)"
branch_b: "Advanced Orchestration (검증 게이트, 자동 재시도, 이상탐지)"
web_search_count: 19
local_execution_tags:
  LOCAL_OK: ["Sequential pipeline", "pipeline_state.json", "DuckDB state", "launchd StartCalendarInterval", "pipeline.log", "Data validation gates", "Retry with backoff", "Anomaly detection", "macOS notifications", "Circuit breaker"]
  LOCAL_PARTIAL: ["pandas_market_calendars (XKRX)"]
  LOCAL_BLOCKED: []
sources:
  - "Coding Data Pipeline Design Patterns in Python (amsayed.medium.com)"
  - "Pipeline Pattern in Python (pybit.es)"
  - "Data Pipeline Design Patterns (startdataengineering.com)"
  - "API Error Handling & Retry Strategies: Python Guide 2026 (easyparser.com)"
  - "Building a Resilient Retry-Oriented Python Data Ingestion Engine (medium.com)"
  - "launchd plist examples (alvinalexander.com)"
  - "Setting up a LaunchAgent macOS (davidhamann.de)"
  - "Automate macOS tasks with Python and launchctl (hackmag.com)"
  - "Comparison Guide — Workflow Orchestration (devtechie.com)"
  - "Decoding Data Orchestration Tools (freeagent.com)"
  - "Prefect vs Dagster"
  - "KRX Market Hours & Holidays 2026 (tradinghours.com)"
  - "pandas_market_calendars documentation (XKRX)"
  - "pykrx GitHub Issues (#276, #240, #151)"
  - "FinanceDataReader GitHub"
  - "DuckDB backup strategies"
  - "Agentic AI Workflow Patterns 2025 (skywork.ai)"
  - "Agentic Design Patterns 2026 (sitepoint.com)"
  - "Python checkpointing for pipelines"
---

# T03: Orchestration Engineer — Investigation Report

## Executive Summary

최적 오케스트레이션: "Lightweight Plus" — 순차 파이프라인(Branch 3.1) 기반 + 데이터 검증 게이트·수집 재시도·점수 이상탐지 3가지 외과적 추가(Branch 3.2). Prefect/Dagster 등 오케스트레이션 프레임워크는 4단계 파이프라인에 과잉. 총 오케스트레이션 코드 ~150줄.

---

## Branch 3.1: Lightweight Orchestration — Findings

### 1. Sequential Pipeline Design [LOCAL-OK]

main.py가 각 단계 함수를 순차 호출:
```
collect() → analyze() → score() → summarize()
```

"Pipe and filter" 패턴. 각 단계는 입력 → 처리 → DuckDB 기록. 실패 시 Python traceback + exit. `/scan` 또는 launchd가 동일 main.py 호출.

### 2. State Management — File-Based [LOCAL-OK]

pipeline_state.json: last_successful_run, status, failed_stage, error_message, data_date, stock_count. DuckDB = 데이터 영속성. JSON = 파이프라인 메타데이터.

체크포인트/재개 없음. 실패 시 처음부터 재실행 (2-5분 파이프라인에 허용 가능).

### 3. Failure Recovery — Manual [LOCAL-OK]

- collect 실패 → DuckDB 어제 데이터 사용 + status: "stale_data"
- score 실패 → 마지막 유효 점수 유지
- DuckDB 손상 → 백업 복원 (파일 복사 패턴)
- 한국어 에러 메시지: "오늘 데이터 수집 실패. 어제 데이터로 분석합니다."

### 4. Scheduling — launchd [LOCAL-OK]

**핵심 발견**: launchd `StartCalendarInterval`은 Mac 수면 시 깨어날 때 누적 미실행 병합 실행. 이것이 정확히 필요한 동작.

주말/공휴일: 파이프라인 실행하되 "신규 데이터 없음" 감지 → 정상 종료 (5초 낭비, 허용 가능).

### 5. Observability — Minimal [LOCAL-OK]

pipeline.log + Python logging. ~1KB/일. Claude가 pipeline_state.json 읽어 상태 보고.

### Branch 3.1 결론: Where It Breaks

**침묵적 실패 (Silent Failure)가 치명적**:
1. pykrx가 모든 종가를 0으로 반환 → 에러 없음, 쓰레기 점수 산출
2. pykrx가 2,500 중 1,800종목만 반환 → 700종목 누락, 사용자 모름
3. Mac 1주 꺼짐 → 5일 전 캐시 데이터로 분석, 신선도 경고 부재
4. 평균 점수 30% 급변 → 점수 버그 또는 시장 레짐 변화, 아무도 감지 안 함

이것이 pykrx GitHub 이슈에 문서화된 실제 실패 모드.

---

## Branch 3.2: Advanced Orchestration — Findings

### 1. Smart Pipeline Design [LOCAL-OK]

```
collect → [행 수 검증] → [가격 합리성 검증] → analyze → [NaN 비율 검증] → score → [점수 분포 검증] → summarize
```

**프레임워크 평가**: Prefect/Dagster/Luigi — 멀티-DAG, 멀티-팀 프로덕션용. 단일 사용자 4단계에 과잉. 재시도+검증 로직 ~50줄 커스텀 Python으로 충분.

### 2. State Management — DuckDB Table [LOCAL-OK]

```sql
CREATE TABLE pipeline_runs (
    run_id INTEGER PRIMARY KEY, run_date DATE, stage TEXT,
    status TEXT, started_at TIMESTAMP, completed_at TIMESTAMP,
    error_message TEXT, retry_count INTEGER, record_count INTEGER
);
```

체크포인트/재개: 마지막 성공 단계부터 재시작. 2-5분 파이프라인에서 최대 3분 절약. 구현 ~30줄.

### 3. Failure Recovery — Automated [LOCAL-OK]

| Stage | Retries | Backoff | Rationale |
|-------|---------|---------|-----------|
| collect | 3 | 30s/60s/120s | pykrx 네트워크 의존, 문서화된 불안정 |
| analyze | 1 | immediate | 결정론적, 실패=코드 버그 |
| score | 1 | immediate | 결정론적 |
| summarize | 1 | immediate | 파일 I/O만 |

폴백 체인: pykrx → FinanceDataReader → DuckDB 캐시.

3일 연속 실패 → alert.json → Claude 세션에서 경고: "주의: 최근 3일간 데이터 수집 실패."

### 4. Scheduling — Intelligent [LOCAL-OK]

KRX 공휴일 캘린더: `pandas_market_calendars` XKRX. 비거래일 사전 감지 → 스킵.

macOS 알림: `osascript -e 'display notification "스캔 완료: 상위 20 종목 업데이트" with title "주식 스캐너"'`

### 5. Observability — Structured [LOCAL-OK]

```sql
CREATE TABLE pipeline_metrics (
    metric_date DATE, collection_duration_sec REAL,
    stocks_collected INTEGER, stocks_scored INTEGER,
    avg_score REAL, score_stddev REAL,
    top10_turnover INTEGER, pipeline_success BOOLEAN
);
```

이상탐지 (3개 임계값 검사):
- stocks_collected 30일 평균 대비 >10% 감소 → 경고
- avg_score 전일 대비 >20% 변동 → 경고
- top10_turnover > 7 (70% 변동) → 경고

### 6. Planning & Reflection Patterns [LOCAL-PARTIAL]

**평가**: 에이전틱 반성/계획 패턴은 LLM 기반 의사결정용. 이 파이프라인은 결정론적 계산. **카테고리 오류**.

유용한 유일한 요소(이상탐지)는 관찰 가능성 레이어의 단순 임계값 검사로 더 적합하게 구현.

---

## Branch 3.1 vs 3.2 Synthesis

### Recommended: "Lightweight Plus"

3.1 기반 + **3가지 외과적 추가**:

| Component | Source | Implementation |
|-----------|--------|---------------|
| 파이프라인 구조 | 3.1 | 순차 main.py |
| 상태 관리 | 3.1 | pipeline_state.json |
| 스케줄링 | 3.1 | launchd StartCalendarInterval |
| 로깅 | 3.1 | pipeline.log |
| **+ 데이터 검증 게이트** | 3.2 | ~30줄: 행 수, 가격 합리성, NaN 비율 |
| **+ 수집 재시도** | 3.2 | ~20줄: collect만 3회 재시도 30s/60s/120s |
| **+ 점수 이상탐지** | 3.2 | ~15줄: avg_score/stock_count 전일 대비 >20% |
| DuckDB 백업 | 3.1 | 파이프라인 전 파일 복사, 7일 보관 |

**총 오케스트레이션 코드: ~150줄.** [LOCAL-OK]

**Deferred to Phase 2+**: KRX 공휴일 캘린더, FinanceDataReader 폴백, pipeline_metrics 이력, macOS 알림.

### Parking Lot

1. pykrx 비거래일 반환값: 빈 DataFrame? 에러? → 실증 테스트
2. FinanceDataReader OHLCV 컬럼 호환성 → 프로토타입 비교
3. pykrx 데이터 가용 시점 (장 마감 15:30 후 언제?) → 16:00/17:00/18:00 테스트
4. DuckDB 1년 후 크기 → 2500×365×10×8바이트 ≈ 73MB raw, 압축 20-40MB
5. osascript 알림이 launchd 트리거 시 작동하는지 → macOS 테스트
6. pykrx IP 차단 임계값 → 보수적 추정 <100 req/min
