---
round: 2
type: raw
teammate: integration-specialist
axis: integration-stack
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
question_summary: "pykrx, DuckDB, pandas-ta, uv, MCP 생태계, Agent SDK를 분석하여 주식 분석 시스템의 최적 통합 범위와 외부 연동 전략 도출"
assumption_axis: "Minimal Integration vs Active Integration"
branch_a: "Minimal Integration (최소 연동 — 필수 의존성만)"
branch_b: "Active Integration (적극 연동 — MCP·Agent SDK·폴백)"
web_search_count: 22
local_execution_tags:
  LOCAL_OK: ["DuckDB 1.5.2", "pandas-ta", "uv", "macOS notifications (osascript)", "External validation links", "Bootstrap script", "Fallback provider pattern"]
  LOCAL_PARTIAL: ["pykrx 1.2.8 (KRX network)", "pykrx-mcp (network)", "claude -p headless (Anthropic API)", "pykrx-openapi (KRX OpenAPI)"]
  LOCAL_BLOCKED: []
sources:
  - "pykrx GitHub Repository (github.com/sharebook-kr/pykrx)"
  - "pykrx PyPI (pypi.org/project/pykrx/)"
  - "pykrx Releases (github.com/sharebook-kr/pykrx/releases)"
  - "KRX Login Issue #244 (github.com/sharebook-kr/pykrx)"
  - "KRX Login Milestone #2 (github.com/sharebook-kr/pykrx)"
  - "pykrx Rate Limit Issue #151"
  - "pykrx IP Block Issue #31"
  - "pykrx-openapi Documentation (github.com/raccoonyy/pykrx-openapi)"
  - "pykrx-mcp GitHub (github.com/sharebook-kr/pykrx-mcp)"
  - "DuckDB Speeding Up In-Process Analytics (opensourceforu.com)"
  - "DuckDB vs Polars 2026 Benchmarks (pyinns.com)"
  - "DuckDB Concurrency Documentation (duckdb.org)"
  - "DuckDB vs SQLite Comparison (DataCamp)"
  - "DuckDB vs SQLite (Analytics Vidhya)"
  - "pandas-ta vs TA-Lib (Sling Academy)"
  - "pandas-ta Official Site (pandas-ta.dev)"
  - "pandas-ta-classic GitHub (xgboosted)"
  - "uv Python Package Manager (DataCamp)"
  - "Best Python Package Managers 2026 (scopir.com)"
  - "FinanceDataReader GitHub"
  - "korea-stock-analyzer-mcp (Mrbaeksang)"
  - "korea-stock-mcp (jjlabsio)"
  - "macos-notifications PyPI"
  - "Claude Code Headless Mode Documentation"
  - "Claude Agent SDK Billing Changes June 2026"
  - "Agent SDK Credit $200/month (claudefa.st)"
  - "Claude Code Headless Mode Issue #36324"
  - "KRX Data Marketplace Registration"
---

# T04: Integration Specialist — Investigation Report

## Executive Summary

핵심 통합 스택: pykrx 1.2.8 + DuckDB 1.5.2 + pandas-ta + uv. 외부 의존성 4개, 모두 pip 설치 가능, C 컴파일러 불필요. MCP 서버는 배치 파이프라인에 중복이며 Phase 2 대화형 탐색에서만 가치. 비기술 사용자 설치 목표: 5단계, 15분.

---

## Branch 4.1: Minimal Integration — Findings

### 1. pykrx Deep-Dive [LOCAL-PARTIAL]

**현황 (2026년 5월)**: v1.2.8 최신 릴리스. KRX 로그인 마일스톤(#2) 완료(2026.1.31, 11개 이슈 해결). CI/CD 정비, pyproject.toml 채택, ruff 포매터 표준화.

**핵심 브레이킹 체인지 (2025.12.27)**: KRX "정보 데이터 시스템" → **KRX 데이터 마켓플레이스** 교체, 로그인 필수화. `KRX_ID`/`KRX_PW` 환경변수 필요.

- KRX Data Marketplace 등록 **무료** — 네이버/카카오 소셜 로그인
- 비기술 사용자 영향: 일회성 계정 등록 + 환경변수 2개 설정

**사용 가능 데이터**: OHLCV(일별), 시가총액, 펀더멘털(PER/PBR/EPS/BPS/DIV/DPS), 섹터/업종, 기관/외국인 매매, 공매도.

**속도 제한**:
- 비공식 스크래퍼 — KRX가 과도 트래픽 IP 차단 명시
- 최소 `time.sleep(1)` 권장
- KRX "차단 해제 불가" 정책
- `get_market_ohlcv_by_ticker(date)`: 전 종목 1회 요청 (2,500개별 요청 불필요)

**데이터 지연**: 장 마감(15:30 KST) 후 정확한 가용 시점 미확인. 실증 테스트 필요.

**pykrx vs pykrx-openapi**:
- **pykrx** (sharebook-kr): KRX Data Marketplace 스크래핑. 더 성숙, 1K+ GitHub 스타, 307K+ PyPI 다운로드.
- **pykrx-openapi** (raccoonyy): KRX OpenAPI, API 키 신청(1 영업일 승인), 12개월 사용 기간.
- 권장: pykrx 우선, IP 차단 시 pykrx-openapi 폴백.

### 2. DuckDB Deep-Dive [LOCAL-OK]

**현재 버전**: v1.5.2 (2026.4). DuckLake 확장, AES-256 암호화(v1.4), Vortex 컬럼형 포맷.

**성능**: 2,500종목 × 250일 × 20지표 = 62.5만 행 — DuckDB에게 사소한 규모. 분석 쿼리 밀리초 단위. 조인/집계 SQLite 대비 **최대 50x 빠름**.

**저장 용량**: 5년 데이터 추정 **50-150MB** (컬럼형 압축 적용). macOS 시스템에서 무시 가능.

**동시 접근**: 단일 작성자/다중 판독자 MVCC. 파이프라인 쓰기 중 Claude 읽기 **정상 동작** — MVCC 스냅샷으로 일관된 읽기. 순차 파이프라인이므로 동시 쓰기 비이슈.

**DuckDB > SQLite 이유**: SQLite는 행 지향(OLTP 최적화), 분석 쿼리(SUM/AVG/GROUP BY) 8-50x 느림. DuckDB는 컬럼형·벡터화·분석 전용. "분석을 위한 SQLite."

**스키마 설계**:
```sql
CREATE TABLE ohlcv (
    ticker VARCHAR, date DATE,
    open INTEGER, high INTEGER, low INTEGER, close INTEGER,
    volume BIGINT, market_cap BIGINT,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE indicators (
    ticker VARCHAR, date DATE,
    sma5 FLOAT, sma20 FLOAT, sma60 FLOAT, sma120 FLOAT, sma200 FLOAT,
    rsi14 FLOAT, macd FLOAT, macd_signal FLOAT,
    adx14 FLOAT, bbands_upper FLOAT, bbands_lower FLOAT, bbands_squeeze FLOAT,
    atr14 FLOAT, obv BIGINT, volume_sma20 FLOAT,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE scores (
    ticker VARCHAR, date DATE,
    ma_alignment FLOAT, base_formation FLOAT, volume_behavior FLOAT,
    momentum FLOAT, breakout_readiness FLOAT, relative_strength FLOAT,
    total_score FLOAT,
    PRIMARY KEY (ticker, date)
);
```

### 3. pandas-ta Deep-Dive [LOCAL-OK]

**현황**: 130+ 지표 네이티브, 200+ (TA-Lib 포함). pandas-ta-classic 포크는 200+ 지표 + 60 캔들 패턴.

**6개 서브스코어 커버리지**:

| 서브스코어 | 필요 지표 | pandas-ta 지원 |
|-----------|----------|---------------|
| MA Alignment | SMA(5,20,60,120,200) | `ta.sma()` — 네이티브 |
| Base Formation | Bollinger %B, ATR | `ta.bbands()`, `ta.atr()` — 네이티브 |
| Volume Behavior | Volume SMA, OBV | `ta.obv()`, `ta.sma()` — 네이티브 |
| Momentum | RSI(14), MACD, ADX(14) | `ta.rsi()`, `ta.macd()`, `ta.adx()` — 네이티브 |
| Breakout Readiness | Bollinger squeeze, ATR 수축 | `ta.squeeze()` — 네이티브 |
| Relative Strength | 가격/지수 수익률 비율 | 커스텀 계산 (사소함) |

**성능**: 종목당 250일 × 15지표 < 10ms. 2,500종목: ~25초 (멀티프로세싱 시 5-10초).

**pandas-ta > TA-Lib**: TA-Lib은 C, 2-5x 빠르나 C 컴파일러 필요(Apple Silicon 설치 실패 빈번). 우리 규모에서 속도 차이 무의미(둘 다 30초 이내). **설치 단순성이 결정적**.

### 4. uv (Python 환경 관리) [LOCAL-OK]

macOS는 Python 3 미포함. 비기술 사용자에게 Python 설치가 필수.

**uv 선택 이유**: Rust 기반, venv 80x 빠름, 패키지 설치 5-40x 빠름. Python 자체 설치 가능(`uv python install 3.12`). 설치: `curl -LsSf https://astral.sh/uv/install.sh | sh` 1줄.

**Bootstrap 스크립트**:
```bash
#!/bin/bash
set -e
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env"
fi
cd "$(dirname "$0")"
uv python install 3.12
uv venv --python 3.12
uv pip install pykrx duckdb pandas-ta
uv run python -c "import pykrx; import duckdb; import pandas_ta; print('All dependencies OK')"
```

### 5. MCP 없이 무엇을 잃는가 [LOCAL-OK]

**pykrx-MCP 없이**: Claude가 Bash tool로 Python 실행. `python -c "from pykrx import stock; ..."` — **완벽히 동작**.

**DuckDB-MCP 없이**: Claude가 Python subprocess로 SQL 실행. 또는 summary.md(최종 출력) 읽기 — DB 접근 불필요.

**파이프라인은 MCP 없이 완전 동작**:
```
launchd → Python → pykrx(수집) → DuckDB(저장) → pandas-ta(계산) → scores(기록) → summary.md(생성)
                                                                                        ↓
                                                                   Claude Read tool로 summary.md 읽기
```

MCP는 대화형 탐색 편의층. 배치 파이프라인에 불필요. 비용: 대화형 세션에서 쿼리당 ~5줄 추가 Python.

### Branch 4.1 결론

**최소 통합 표면**:

| 컴포넌트 | 필수? | 복잡도 |
|---------|------|--------|
| Python 3.12 | Yes | uv 자동 설치 |
| uv | Yes | curl 1줄 |
| pykrx | Yes | pip install + KRX 계정(무료) |
| DuckDB | Yes | pip install |
| pandas-ta | Yes | pip install |
| MCP 서버 | No | 배치에 불필요 |
| TA-Lib (C) | No | pandas-ta 충분 |
| 외부 API | No | pykrx가 모든 데이터 커버 |

**총 외부 의존성: 4개**. 모두 pip 설치 가능. C 컴파일러 불필요. KRX 계정 무료 등록 1회.

---

## Branch 4.2: Active Integration — Findings

### 1. MCP 서버 생태계 [LOCAL-PARTIAL]

**a) pykrx-mcp** (sharebook-kr): Claude에서 한국 주식 데이터 직접 쿼리. 배치에는 **중복** — 2,500종목 = 2,500 MCP 호출(Python 배치보다 나쁨). 대화형 ad-hoc에만 유용.

**b) korea-stock-mcp** (jjlabsio): DART 공시 데이터 통합. Phase 2 펀더멘털 분석 보완에 유용. Phase 1 불필요.

**c) korea-stock-analyzer-mcp** (Mrbaeksang): 6개 투자 대가 전략, RSI/MACD/볼린저. 우리 파이프라인과 **경쟁관계** — 같은 지표 중복 계산, 불일치 위험.

**MCP 종합 평가**: 배치 파이프라인에 **중복**. 대화형 Claude 세션에서만 빛남. 파이프라인은 순수 Python 유지.

### 2. 데이터 소스 폴백 아키텍처 [LOCAL-PARTIAL]

**Tier 1 — pykrx (주)**: KRX Data Marketplace 스크래핑. 가장 성숙, 최대 커뮤니티.
**Tier 2 — pykrx-openapi (부)**: KRX OpenAPI, API 키(1 영업일 승인), 12개월 갱신.
**Tier 3 — FinanceDataReader (보)**: 1,438 GitHub 스타. JSONDecodeError 보고 이력(간헐적).

```python
class FallbackProvider(StockDataProvider):
    def __init__(self):
        self.providers = [PykrxProvider(), PykrxOpenAPIProvider(), FDRProvider()]

    def get_ohlcv(self, ticker, start, end):
        for provider in self.providers:
            try:
                return provider.get_ohlcv(ticker, start, end)
            except Exception as e:
                logger.warning(f"{provider.__class__.__name__} failed: {e}")
                continue
        raise RuntimeError("All data providers failed")
```

### 3. 알림 통합 [LOCAL-OK]

**macOS 네이티브 알림**: osascript(의존성 0, 모든 macOS 동작):
```python
subprocess.run(['osascript', '-e',
    'display notification "3 new stocks scored >80" with title "Stock Scanner"'])
```

macOS-notifications 라이브러리(액션 버튼, 답장)와 pync(terminal-notifier 래퍼)도 가능하나, osascript가 가장 단순하고 충분.

### 4. 외부 검증 소스 (출력 전용 통합) [LOCAL-OK]

URL 자동 생성만으로 높은 가치:

```markdown
| Rank | Ticker | Name | Score | Links |
|------|--------|------|-------|-------|
| 1 | 005930 | Samsung | 87.3 | [Naver](https://finance.naver.com/item/main.naver?code=005930) · [Chart](https://www.tradingview.com/chart/?symbol=KRX:005930) |
```

비용 0, 위험 0, 사용자 편의성 극대화. **필수 포함**.

### 5. Agent SDK 통합 [LOCAL-PARTIAL]

**헤드리스 모드 (`claude -p`)**: 프로그래밍 용도 완전 지원. `--allowedTools`, `--max-turns`, `--max-budget-usd` 가드레일.

**Agent SDK Credit (2026.6.15 이후)**: Max 20x → $200/월. 일일 스캔 ~7K 토큰/실행 × 30일 = ~210K 토큰/월 → **~$1.50/월**. $200 크레딧의 1% 미만.

**안정성 우려**: 무인 실행 시 과도 비용/의도치 않은 행동 보고. 완화: `--max-turns 15`, `--max-budget-usd 1.00`, 명시적 도구 허용목록. 해석 전용(좁은 범위) 작업에 적합.

### Branch 4.2 결론

| 통합 | 가치 | 복잡도 | 비율 | 판정 |
|------|-----|--------|------|------|
| 외부 링크 (Naver/TradingView) | 높음 | 거의 0 | 탁월 | **필수** |
| macOS 알림 (osascript) | 중간 | 거의 0 | 탁월 | **필수** |
| 데이터 소스 폴백 (Protocol) | 높음 | 중간 | 좋음 | **Phase 1** |
| Claude 헤드리스 한국어 요약 | 높음 | 중간 | 좋음 | **Phase 2** |
| pykrx-mcp | 낮음 | 중간 | 나쁨 | **Phase 2 또는 스킵** |
| korea-stock-mcp (DART) | 중간 | 중간 | 보통 | **Phase 2** |
| korea-stock-analyzer-mcp | 낮음 | 중간 | 나쁨 | **스킵** (중복) |

---

## Branch 4.1 vs 4.2 Synthesis

### 기술 스택 현실 점검

| 기술 | 프로덕션 준비? | 위험 수준 | 비고 |
|------|-------------|---------|------|
| **pykrx 1.2.8** | Yes, 단서 있음 | 중간 | KRX 로그인 적응 완료. 위험: IP 차단. 완화: 속도 제한 + 폴백. |
| **DuckDB 1.5.2** | Yes | 낮음 | 성숙, 우리 데이터 규모에 사소함. |
| **pandas-ta** | Yes | 낮음 | 필요 지표 전체 네이티브 지원. C 의존성 없음. |
| **uv** | Yes | 낮음 | 2026 Python 툴링 산업 표준. |
| **claude -p** | Yes, 가드레일 포함 | 중간 | 좁은 범위 작업에 안정적. 6월 과금 변경 유리. |

### 통합 우선순위 매트릭스

**Phase 0 — Bootstrap (Day 1)**: uv + Python 3.12, pykrx + DuckDB + pandas-ta, KRX 계정, 환경변수.

**Phase 1 — Core Pipeline (Week 1)**: 파이프라인(pykrx→DuckDB→pandas-ta→scores→summary.md), 외부 링크, osascript 알림, 데이터 소스 폴백.

**Phase 2 — Automation (Week 2)**: launchd plist, claude -p 한국어 요약, 예산/턴 가드레일.

**Phase 3 — Enhancement (Month 2+)**: pykrx-mcp, korea-stock-mcp, pykrx-openapi.

### 비기술 사용자 설치 복잡도

**첫 설치 5단계**:
1. Terminal 열기
2. `curl -LsSf https://astral.sh/uv/install.sh | sh` (uv 설치)
3. `./bootstrap.sh` (Python + 의존성 설치)
4. https://data.krx.co.kr/ → 네이버/카카오 ID로 가입
5. `.env` 파일에 KRX_ID/KRX_PW 설정

예상 시간: 비기술 사용자 **10-15분** (스크린샷 가이드 제공 시).

### Parking Lot

1. pykrx 정확한 데이터 가용 시점 (장 마감 후 지연) → 15:35/16:00/16:30 실증 테스트
2. KRX OpenAPI 무료 여부 확인 → 등록 시 검증
3. `get_market_ohlcv_by_ticker(date)` 범위 → KOSPI+KOSDAQ 동시 반환 여부 확인
4. pandas-ta numba JIT Apple Silicon 호환성 → 부트스트랩 시 테스트
5. claude -p 구독 계정(Max) 사용 가능 여부 → GitHub issue #36324
6. 5년 초기 로딩 시간 → 배치 수집 예상 60-90분, 진행률 표시 필요
