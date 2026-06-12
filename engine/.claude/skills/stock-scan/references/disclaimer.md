# disclaimer.md

면책조항 + 표현 정책의 canonical 사본. PRD §7.3 / FR-8 / B-23 verbatim. stock-scan이 enforce하는 유일한 안전 규칙(§SKILL.md §9 참조).

---

## §1. 면책조항 풀버전 (세션 첫 emission)

PRD B-23 verbatim:

```
⚠️ 본 결과는 기술적 분석 도구의 산출물이며, 매수·매도 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.
```

세션당 정확히 1회만 emit. 첫 결과 출력 직후 session-scoped flag를 `true`로 toggle.

---

## §2. 면책조항 축약 (이후 동일 세션 내 emission)

```
(투자판단·책임은 본인에게 있습니다)
```

session flag = `true` 이면 결과 출력 마지막에 이 1줄만 부착.

---

## §3. 면책 부착 대상 / 면제 조건

**부착 필수 — 결과 출력 체인 8개 전부**:
- Chain 1 SCAN_TODAY
- Chain 2 SCAN_SEPARATED (filter 단계 종료 후)
- Chain 3 SCAN_RANGE (최종 집계 후)
- Chain 4 SHOW_RESULTS
- Chain 5 WHY_REJECTED
- Chain 6 COMPARE
- Chain 7 COMPARE_PARAMS
- Chain 8 RERUN_FILTERS

**부착 면제**:
- 에러 리포트 (`output-templates.md` §8)
- 사전점검 메시지 (`pre-flight-checks.md`)
- AskUserQuestion prompt
- 진행률 보고 (`"3/5일 완료"`, prefetch 통계 등 중간 단계 — Chain 2 Step 5 prefetch stats는 면책 면제 / Chain 2 Step 8 최종 결과는 부착)
- 시스템 상태 보고 (lock 거부, 캐시 hit 안내 등)
- AskUserQuestion 응답 처리 도중의 transition 메시지

---

## §4. O/X 표현 정책 (PRD §7.3 / FR-8.2/8.3 verbatim)

stock-scan의 모든 한국어 출력은 다음 정책을 준수한다:

### (O) 권장 표현
- `"기술적 완성도가 높은 종목"`
- `"필터 조건을 충족한 종목"`
- `"선별 결과"`
- `"5-Stage 통과"`
- `"통과 종목"`, `"탈락 종목"`
- `"수집 완료"`, `"분석 결과"`
- `"기술적 분석 도구의 산출물"`

### (X) 금지 표현
- `"매수 추천"`
- `"이 종목을 사세요"`
- `"유망 종목"`
- `"상승 예측"`
- `"이익 보장"`
- `"수익 기대"`, `"강력 매수"`, `"매수 신호"`
- `"오를 종목"`, `"수익률 N% 예상"`

LLM이 자연어로 결과를 설명할 때도 이 정책을 준수한다. 사용자가 명시적으로 "이거 사도 돼?"라고 물어도 매수·매도 권유로 응답하지 않으며, 면책조항으로 회피한다.

---

## §5. 세션 flag 운용 (구현 노트)

```
session_state:
  disclaimer_full_emitted: bool   # 초기 false
                                  # 첫 결과 emission 후 true로 toggle
                                  # /clear 또는 새 세션 시작 시 false로 reset
```

본 Skill은 별도 파일에 flag를 저장하지 않는다 — Claude Code 세션 내 추론으로 추적 (`screener_state.json`은 flag를 저장하지 않음 — Step 4 §4 schema 기준).

세션 내 첫 결과 chain emission인지 모호할 때는 풀버전을 emit하는 쪽을 default로 (안전 보수).
