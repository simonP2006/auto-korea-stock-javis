# Step 1 — Error Pattern Classification

> Generated: 2026-05-29
> Search roots: `/Users/tajun/spJavis/kiwoom-rest-trader/scripts/`, `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/`

## Custom Exception Class Hierarchy

| Class | Base Class | Defined In (file:line) | Docstring/Purpose |
|---|---|---|---|
| `KiwoomAuthError` | `RuntimeError` | `src/kiwoom/auth.py:34` | 키움 OAuth 인증 실패 시 발생하는 예외 |
| `KiwoomApiError` (auth-bearing REST) | `RuntimeError` | `src/kiwoom/etc/foreigner.py:74`; same class re-declared in 8 modules (chart60/120/240/Day client `models.py`, `upperLowerPrice.py:214`, `finance/finance.py:82`, `investor/investor.py:88`) | ka1xxxx 호출 실패 — attrs: `code`(return_code/HTTP), `msg`(return_msg), `api_id`(TR ID). Same name, **independent class objects per module** |
| `KiwoomConditionError` | `RuntimeError` | `src/kiwoom/conditionCompany/models.py:28` | 조건검색 WebSocket(ka10171/ka10172) 호출 실패. attrs: `code`, `msg`, `api_id` |
| `OrganizeError` | `RuntimeError` | `src/kiwoom/organizedCompany/facade.py:33` | 입력 파일이 모두 부재 등 진행 불가 오류 |
| `ResearchError` | `RuntimeError` | `src/kiwoom/researchFlow/facade.py:107` | 입력 부재 등 진행 불가 오류 (organizedCompany.md / prefetchManifest.json) |
| `PrefetchError` | `RuntimeError` | `src/kiwoom/researchFlow/prefetch.py:76` | 입력 부재 등 Stage 0 진행 불가 오류 |

> Note: `KiwoomApiError` is **defined separately in each module** (chart60/120/240/Day/foreigner/finance/investor/upperLower). Functionally identical but not a shared symbol — `except KiwoomApiError` from one import won't catch the others. This is an architectural quirk worth surfacing.

## Full Error Inventory

| # | Error Class | Trigger Condition | Exit Code | Stderr/Log Pattern | Source (file:line) | Raise Sites | Catch Sites | Korean Message |
|---|---|---|---|---|---|---|---|---|
| 1 | `KiwoomAuthError` | OAuth 토큰 발급/검증 실패 (HTTP 에러, non-200, JSON 파싱, 키움 거부, 스키마 검증) | N/A (전파됨) | `"토큰 발급 HTTP 오류: {exc}"`, `"토큰 발급 실패 status={status} body={body}"`, `"토큰 응답이 JSON이 아님: {body}"`, `"키움 인증 거부 return_code={rc} return_msg={msg}"`, `"토큰 응답 스키마 검증 실패: {data}"` | `src/kiwoom/auth.py:34` | 5 (`auth.py:173, 176, 183, 188, 195`) | 0 — 명시적 핸들러 없음(상위 `except Exception` 으로 흡수) | "키움 인증에 실패했습니다. APP_KEY·SECRET_KEY 설정을 확인하고, 잠시 후 다시 시도해주세요." |
| 2 | `KiwoomApiError` | REST API 호출 실패 (HTTP 전송 오류, non-200, JSON 파싱 실패, 응답 shape 오류, return_code≠0, 재시도 한도 초과) | N/A | `"transport error: {exc}"`, `"non-200 body={body}"`, `"응답이 JSON이 아님: {body}"`, `"{list_key} 가 리스트가 아님: {type}"`, `"재시도 {N}회 초과"`, return_msg 직접 노출 | `src/kiwoom/etc/foreigner.py:74` 외 7곳 | 39 (예: `chart60/getData/client.py:113`, `finance/finance.py:239`) | 0 — 명시적 핸들러 없음(상위 `except Exception` 으로 흡수) | "키움 데이터 조회에 실패했습니다. 잠시 후 다시 시도하거나 네트워크 상태를 확인해주세요." |
| 3 | `KiwoomConditionError` | 조건검색 WebSocket 실패 (LOGIN 타임아웃, transport error, return_code≠0, MISSING 조건명, SHAPE 오류, 재시도 한도 초과) | N/A | `"transport error: {exc}"`, `"LOGIN 응답 {N}초 초과"`, `"서버에 저장되지 않은 조건명: {missing}"`, `"data 가 리스트가 아님: {type}"`, `"재시도 {N}회 초과"` | `src/kiwoom/conditionCompany/models.py:28` | 7 (예: `ws_client.py:149,177,217,226`, `search.py:73`, `conditions.py:99`) | 4 (`scripts/run_condition_research.py:37`, `scripts/run_prefetch.py:104`, `src/kiwoom/conditionCompany/facade.py:104`, `src/kiwoom/researchFlow/facade.py:555`) | "조건검색 서버 응답에 실패했습니다. 설정한 조건명이 키움 HTS에 저장되어 있는지 확인해주세요." |
| 4 | `OrganizeError` | `conditionResearch.md`·`upperLowerPrice.md` 두 입력 파일이 **모두** 부재이거나 추출 0건 | 1 (`run_organize_company.py:36`) | `"입력 파일 부재 또는 추출 0건: {cond_path}, {upper_path}"` | `src/kiwoom/organizedCompany/facade.py:33` | 1 (`organizedCompany/facade.py:66`) | 3 (`scripts/run_organize_company.py:34`, `scripts/run_prefetch.py:116`, `src/kiwoom/researchFlow/facade.py:479`) | "수집된 종목 데이터가 없습니다. 조건검색·상하한가 수집을 먼저 실행해주세요." |
| 5 | `ResearchError` | `organizedCompany.md` 부재/공백, 또는 `prefetchManifest.json` 부재 | 1 (`run_research_flow.py:46`, `run_filters.py:61`) | `"organizedCompany.md 없음: {path}"`, `"organizedCompany.md 가 비어있음: {path}"`, `"prefetchManifest.json 없음 — 먼저 Stage 0 prefetch 를 실행하세요"` | `src/kiwoom/researchFlow/facade.py:107` | 3 (`researchFlow/facade.py:328, 332, 337`) | 4 (`scripts/run_research_flow.py:44`, `scripts/run_filters.py:58`, `scripts/debug_researched_company.py:85`, `researchFlow/facade.py:600`) | "필터링에 필요한 데이터 파일이 없습니다. 먼저 데이터 수집(prefetch)을 실행해주세요." |
| 6 | `PrefetchError` | Stage 0 prefetch 진입 전 `organizedCompany.md` 부재/공백 | 1 (`run_prefetch.py:157`) | `"organizedCompany.md 없음: {path}"`, `"organizedCompany.md 가 비어있음: {path}"` | `src/kiwoom/researchFlow/prefetch.py:76` | 2 (`researchFlow/prefetch.py:311, 315`) | 2 (`scripts/run_prefetch.py:150`, `researchFlow/facade.py:591`) | "종목 사전 수집을 시작할 데이터가 없습니다. 조건검색·상하한가 단계를 먼저 완료해주세요." |
| 7 | `httpx.HTTPError` (포함 `ConnectError`, `TimeoutException`) | 네트워크 오류, 타임아웃, DNS 실패 등 — 즉시 `KiwoomApiError(code="HTTP")` 또는 `KiwoomAuthError`로 래핑 | N/A | `"transport error: {exc}"` (랩핑 후) | (catch only) | 0 직접 raise | 9 (`auth.py:172`, `etc/foreigner.py:289`, `chart60/getData/client.py:112`, `chart120/.../client.py:112`, `chart240/.../client.py:112`, `chartDay/.../client.py:112`, `upperLowerPrice.py:607`, `finance/finance.py:238`, `investor/investor.py:242`) | "키움 서버에 연결할 수 없습니다. 인터넷 연결과 키움 서버 상태를 확인한 뒤 다시 시도해주세요." |
| 8 | `asyncio.TimeoutError` | WebSocket LOGIN/응답 타임아웃 — `KiwoomConditionError(code="LOGIN_TIMEOUT" 또는 "WS")`로 래핑 | N/A | `"LOGIN 응답 {N}초 초과"` | (catch only) | 0 직접 raise | 2 (`conditionCompany/ws_client.py:140, 215`) | "키움 조건검색 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요." |
| 9 | `ConnectionClosed` / `WebSocketException` | 조건검색 WebSocket 연결 끊김 — `KiwoomConditionError(code="WS")`로 래핑 | N/A | `"ws transport error trnm={a} attempt={n}/{m} err={e}"` | (catch only, from `websockets` 라이브러리) | 0 직접 raise | 1 (`conditionCompany/ws_client.py:140`) | "조건검색 연결이 끊어졌습니다. 네트워크 상태를 확인한 뒤 다시 시도해주세요." |
| 10 | `FileNotFoundError` | 보고서 날짜 폴더, 종목 폴더, `chart{60,120,240,Day}.md`, `finance.md`, `investor.md`, `chartDay.md` 등 파일 부재 | 2 (script 상위에서 `except Exception` → exit 2) | `"날짜 폴더 없음: {target}"`, `"chart60.md 없음: {path}"`, `"chartDay.md 없음: {path}"`, `"finance.md 없음: {path}"`, `"investor.md 없음: {path}"`, `"종목 폴더 없음: stock={stock} date_dir={dir}"`, `"master 종목 폴더 없음"` | (built-in) | 40+ (`itemFilter/*Filter.py`의 다수: 예 `financeFilter.py:198, 202, 217, 228`; `chart60Filter.py:327, 346, 357`; `stageMasterFilter.py:204, 209`) | 9 (각 filter `except (ValueError, FileNotFoundError)`: `chart60Filter.py:565`, `chart240Filter.py:450`, `chartDayFilter.py:657`, `chartDayPreFilter.py:316`, `chart60_120Filter.py:789`, `financeFilter.py:365`, `investorFilter.py:479`, `stageMasterFilter.py:436, 603`; 추가 `Filter_condition_update.py:143`, `researchFlow/facade.py:336`) | "필요한 데이터 파일을 찾을 수 없습니다. 먼저 해당 단계의 데이터 수집을 실행해주세요." |
| 11 | `ValueError` | 파싱 실패 (시계열 표 행 0개, finance 당기순이익 행 미발견), 잘못된 인자 (`days·bars` 동시 지정, `window<1`, `stage_idx` 범위 외, `exchange` 값 부정), feature 결측, 캘리브레이션 초기화 실패 | 2 (script 상위에서 `except Exception` → exit 2) | `"chart60.md 시계열 표 파싱 실패 (행 0개): {path}"`, `"finance.md 당기순이익 행 파싱 실패: {path}"`, `"days 와 bars 는 동시에 지정할 수 없습니다"`, `"window must be >= 1, got {window}"`, `"알 수 없는 exchange: {exchange}"`, `"봉 없음"`, `"필수 피처 결측"`, `"init 불가: feature={feat} positive 값 0개"` | (built-in) | 20+ (`itemFilter/*Filter.py` 파싱; `chart{60,120,240,Day}/getData/facade.py:94 등`; `_exchange.py:70`; `stageMasterFilter.py:212,218,240`; `researchFlow/saveReport/plain_text.py:145`) | 9 (필터들 `except (ValueError, FileNotFoundError)`; 일부 모듈 내부 파싱 fallback) | "데이터 형식이 올바르지 않습니다. 수집된 데이터가 손상되었을 수 있으니 다시 수집해보세요." |
| 12 | `RuntimeError` (stageMaster 자가검증) | stageMaster 임계값 확장 후에도 master 종목이 통과하지 못함 (캘리브레이션 로직 오류 신호) | 2 (script 상위 `except Exception`) | `"확장 후에도 master 미통과: date={date} name={name} feats={feats}"` | (built-in) | 1 (`stageMasterFilter.py:354`) | 0 — 캘리브레이션 fail-fast | "필터 캘리브레이션 검증에 실패했습니다. 관리자에게 문의해주세요." |
| 13 | `OSError` | 파일 캐시 손상/읽기 실패 (`.token_cache.json`), 토큰 캐시 chmod 실패, 통계 파일 OS 오류 | N/A (대부분 무시·pass) | `"토큰 캐시 파일 손상, 무시: {err}"` | (built-in) | 0 직접 raise | 3 (`auth.py:204` (`json.JSONDecodeError, ValueError, OSError`), `auth.py:217` (chmod, silenced), `financeFilter.py:291`) | "임시 데이터 파일에 접근할 수 없습니다. 디스크 권한과 여유 공간을 확인해주세요." |
| 14 | `Exception` (generic catch-all) | 상위 단계에서 예측 못한 모든 예외 — 스크립트는 exit 2로 종료, 모듈은 격리(`# noqa: BLE001`) 후 다음 종목 진행 | 2 (모든 `scripts/run_*.py` 의 `except Exception` 경로) | `"예상치 못한 예외: {e}"`, `"{type}: {exc}"` | (built-in) | 0 | 20+ (스크립트 전체 + `researchFlow/facade.py:387,544,558,623`, `prefetch.py:122,132,149,161,178,190,212,224`, `Filter_condition_update.py:145,291`) | "예기치 못한 오류가 발생했습니다. 잠시 후 다시 시도하거나 로그를 확인해주세요." |

## Known-Type Coverage Confirmation

| Known Type | Found? | If not present, explanation |
|---|---|---|
| KiwoomAuthError | YES | `src/kiwoom/auth.py:34` — 5 raise sites, 0 명시적 catch (상위 generic Exception 흡수) |
| KiwoomApiError | YES | **6+ 확인**: `etc/foreigner.py:74`, `chart60/getData/models.py:33`, `chart120/getData/models.py:33`, `chart240/getData/models.py:33`, `chartDay/getData/models.py:23`, `upperLowerPrice/upperLowerPrice.py:214`, `finance/finance.py:82`, `investor/investor.py:88` — 총 **8개 모듈에서 독립 정의**(같은 이름, 다른 클래스 객체) |
| KiwoomConditionError | YES | `conditionCompany/models.py:28` — 7 raise, 4 catch |
| ResearchError | YES | `researchFlow/facade.py:107` — 3 raise, 4 catch |
| OrganizeError | YES | `organizedCompany/facade.py:33` — 1 raise, 3 catch |
| PrefetchError | YES | `researchFlow/prefetch.py:76` — 2 raise, 2 catch |
| httpx.ConnectError | INDIRECTLY | 직접 catch 없음. `except httpx.HTTPError`(상위 베이스 클래스)로 흡수 — `ConnectError`·`TimeoutException`·`ReadTimeout` 모두 `HTTPError`의 서브클래스이므로 잡힘. 즉시 `KiwoomApiError(code="HTTP")` / `KiwoomAuthError`로 래핑됨 |
| httpx.TimeoutException | INDIRECTLY | 위와 동일 — `httpx.HTTPError` 캐치 9곳에서 흡수 |
| FileNotFoundError | YES | itemFilter 전반 + researchFlow에서 raise·catch 모두 빈번. 40+ raise sites, 9+ catch sites |

## Newly Discovered Types (beyond known list)

| Type | Notes |
|---|---|
| `ValueError` (built-in) | 20+ raise sites in itemFilter parsers + argument validation. Caught in pairs with `FileNotFoundError`. 사실상 도메인 데이터 무결성 오류 신호로 쓰임 — Korean message: 데이터 형식·인자 오류로 안내. |
| `RuntimeError` (built-in, stageMaster) | `stageMasterFilter.py:354` — 캘리브레이션 자가검증 fail-fast. 일반 RuntimeError 와는 구별되는 단일 의미. |
| `OSError` (built-in) | 토큰 캐시 파일 손상/권한 오류 시에만 등장. 대부분 silent (`pass` 또는 로그 후 무시). |
| `asyncio.TimeoutError` | WebSocket LOGIN/응답 대기 타임아웃. `KiwoomConditionError`로 즉시 래핑되므로 사용자에게 노출되는 표면 클래스는 `KiwoomConditionError`. |
| `ConnectionClosed` / `WebSocketException` (from `websockets` 라이브러리) | WS transport 실패. `KiwoomConditionError(code="WS")`로 래핑. |
| `Exception` (generic) | 모든 스크립트 진입점에 fail-safe catch가 있음. exit 2로 안전 종료 + loguru `exception()` 트레이스 기록. |

## Korean Message Style Guide (auto-derived)

- **(a) 무슨 일이 일어났는지 명확히** — "키움 인증에 실패했습니다", "데이터 파일을 찾을 수 없습니다" 같이 도메인 용어 사용하되 코드명·예외명·HTTP 상태코드·`return_code` 같은 기술 잔재는 노출하지 않는다.
- **(b) 사용자가 다음에 할 행동을 1문장 안에 제시** — "키 설정을 확인하세요", "먼저 prefetch를 실행해주세요", "네트워크를 확인한 뒤 다시 시도해주세요" 등 **명령형 안내**.
- **(c) 일시적·구조적 오류 구분** — 네트워크/타임아웃은 "잠시 후 다시", 입력 부재는 "먼저 ○○를 실행", 설정 오류는 "○○를 확인" 으로 어휘를 일관 매핑한다.
- **(d) Jargon 금지** — `return_code`, `HTTPError`, `JSON 스키마`, `ka10171`, `stage_idx` 등은 모두 제거. 대신 "조건검색 서버", "수집 단계", "데이터 파일" 같은 상위 개념어로 치환.

## Verification Self-Check

- [x] ≥5 distinct error types documented (target: more) — **14개 분류** 작성
- [x] All 9 known types addressed — 6 직접 발견 + 2 간접 흡수(`ConnectError`/`TimeoutException`) + 1 직접 발견(`FileNotFoundError`)
- [x] Every entry has a Korean message — 14/14
- [x] Custom exception class discovery via grep performed — `grep -rn "class .*Error\|class .*Exception"` 1회 + raise/except/exit/stderr 보조 grep 4회
- [x] Each Korean message: (a) explains what happened, (b) suggests user action, (c) avoids jargon

## Architectural Notes (for downstream consumers)

1. **`KiwoomApiError` 의 8개 독립 정의**가 가장 큰 함정. 어느 한 모듈의 `KiwoomApiError`를 import해 `except`로 사용하면 다른 모듈에서 raise된 동명 클래스를 잡지 못한다. 사용자 메시지 매핑 시에는 이름 기준(`type(exc).__name__ == "KiwoomApiError"`) 또는 공통 베이스(`RuntimeError`)로 처리해야 안전하다.
2. **`KiwoomApiError`·`KiwoomAuthError`에 명시적 catch가 0개** — 모두 스크립트 진입점의 `except Exception`이 흡수해 exit 2 로 종료한다. 사용자 친화 메시지 변환 레이어를 도입하려면 이 진입점 핸들러에서 `type(exc).__name__` 또는 `code` 속성을 분기해야 한다.
3. **종료 코드 컨벤션**이 일관된다: `0` 정상 / `1` 입력 부재(`*Error` 도메인 예외) / `2` 기타 예외. 사용자 메시지 매핑 시 exit code 자체를 1차 분류 키로 사용 가능.
4. **httpx · WebSocket 저수준 예외는 모두 도메인 예외로 래핑** 되어 사용자에게 직접 노출되지 않는다. 따라서 최종 메시지 매핑 테이블은 도메인 예외 6종(`KiwoomAuthError`, `KiwoomApiError`, `KiwoomConditionError`, `OrganizeError`, `ResearchError`, `PrefetchError`) + 빌트인 3종(`FileNotFoundError`, `ValueError`, generic `Exception`)에 집중하면 사용자 표면을 99% 커버한다.
