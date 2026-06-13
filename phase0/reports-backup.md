# 과업 0-6: reports/ 이주 매니페스트 + 1차 백업

- 작성: Phase 0 워커 (2026-06-13 09:19 KST 백업 생성)
- 대상 원본: `/Users/tajun/spJavis/kiwoom-rest-trader/reports/` (총 **381M**, 파일 **89,319개** — `du -sh` / `find -type f | wc -l` 실측)
- 원본은 일절 수정·삭제하지 않음 (읽기 + tar만 수행).

---

## 1. 매니페스트

### 1-1. 날짜 디렉토리 (20개)

핵심 산출물 6종 + stage 통과 md 존재 여부를 전수 확인했다.
- 핵심 6종: `masterReference.md` · `conditionResearch.md` · `organizedCompany.md` · `researchedCompany.md` · `prefetchManifest.json` · `upperLowerPrice.md`
- stage md: `stage*_passed.md` (stage1_chart60_120 / stage2_chart240 / stage2_1_chartDayPre / stage3_chartDay / stage4_investor / stage5_finance)

| 날짜 디렉토리 | 파일 수 | 용량 | 핵심 6종 | stage md |
|---|---:|---:|---|---:|
| 20260514 | 3,306 | 14M | 5/6 (`prefetchManifest.json` 없음 — 확인됨, 최초 회차) | 5 |
| 20260515 | 1,771 | 7.0M | 6/6 | 6 |
| 20260516 | 2,121 | 8.4M | 6/6 | 6 |
| 20260518 | 3,471 | 14M | 6/6 | 6 |
| 20260519 | 3,059 | 12M | 6/6 | 6 |
| 20260520 | 1,815 | 7.2M | 6/6 | 6 |
| 20260521 | 9,627 | 38M | 6/6 | 6 |
| 20260522 | 11,890 | 47M | 6/6 | 6 |
| 20260526 | 4,380 | 17M | 6/6 | 6 |
| 20260527 | 1,522 | 6.0M | 6/6 | 6 |
| 20260528 | 2,973 | 12M | 6/6 | 6 |
| 20260529 | 2,852 | 11M | 6/6 | 6 |
| 20260601 | 2,436 | 9.7M | 6/6 | 6 |
| 20260602 | 3,699 | 15M | 6/6 | 6 |
| 20260604 | 5,796 | 23M | 6/6 | 6 |
| 20260605 | 2,959 | 12M | 6/6 | 6 |
| 20260608 | 560 | 2.6M | 6/6 | 6 |
| 20260609 | 11,711 | 46M | 6/6 | 6 |
| 20260610 | 3,854 | 15M | 6/6 | 6 |
| 20260611 | 9,504 | 38M | 6/6 | 6 |
| **소계** | **89,306** | — | | |

- 날짜 디렉토리 내부 구조: 종목별 하위 디렉토리(`종목명(코드)/`) + 루트 산출물 md/json/log (예: `reports/20260608/` 에 `_full_flow_run.log`, `masterReference.log` 포함).

### 1-2. 루트 상태파일 (13개, 89,306 + 13 = 89,319 합치 확인)

| 파일 | 크기 | mtime |
|---|---:|---|
| `screener_state.json` | 971 B | 2026-06-11 22:30 |
| `tuning-log.md` | 148 B | 2026-05-31 07:07 |
| `TUNING_RESUME_20260605.md` | 8,634 B | 2026-06-05 00:11 |
| `_scan_20260611.log` | 7,008,799 B | 2026-06-11 22:28 |
| `20260510.zip` | 3,721,274 B | 2026-05-10 19:30 |
| `20260512.zip` | 2,239,364 B | 2026-05-13 19:47 |
| `20260513.zip` | 4,261,805 B | 2026-05-13 23:55 |
| `20260514.zip` | 7,083,593 B | 2026-05-15 00:17 |
| `20260515.zip` | 3,410,889 B | 2026-05-16 06:29 |
| `masterReference_run_filters_튜닝_시뮬레이션_20260603.md` | 8,397 B | 2026-06-03 23:07 |
| `masterReference_전체_현재조건_분석_20260514_20260601.md` | 14,537 B | 2026-06-03 22:27 |
| `masterReference_탈락종목_보고서_20260518_20260522.md` | 6,852 B | 2026-05-24 21:23 |
| `.DS_Store` | 14,340 B | 2026-06-11 22:13 |

- 참고: zip 5개(20260510~20260515)는 과거 회차의 아카이브. 20260510·20260512·20260513은 zip만 존재하고 풀린 디렉토리는 없음(zip 안에만 보존). 백업 tar에 zip 그대로 포함됨.
- 학습 상태 파일(별도 경로): `/Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter/stageMasterFilter_state.json` (6,136 B, mtime 2026-05-23 20:37) — 별도 백업함.

---

## 2. 백업 산출물

| 백업 파일 | 크기 | 내용 |
|---|---:|---|
| `/Users/tajun/spJavis-tools/_backup/aksj-reports-20260613.tar.gz` | 76,190,681 B (~73M) | `reports/` 전체 (파일 89,319개) |
| `/Users/tajun/spJavis-tools/_backup/aksj-stageMasterFilter_state-20260613.tar.gz` | 1,309 B | `stageMasterFilter_state.json` 1개 |

생성 명령(실행 완료):
```bash
mkdir -p /Users/tajun/spJavis-tools/_backup
tar -czf /Users/tajun/spJavis-tools/_backup/aksj-reports-20260613.tar.gz \
    -C /Users/tajun/spJavis/kiwoom-rest-trader reports
tar -czf /Users/tajun/spJavis-tools/_backup/aksj-stageMasterFilter_state-20260613.tar.gz \
    -C /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter stageMasterFilter_state.json
```

## 3. 검증 결과

1) 엔트리 수 대조 — **일치 (89,319 = 89,319)**
```bash
tar -tzf aksj-reports-20260613.tar.gz | grep -v '/$' | wc -l   # → 89319 (파일 엔트리, 디렉토리 제외)
find /Users/tajun/spJavis/kiwoom-rest-trader/reports -type f | wc -l   # → 89319
tar -tzf aksj-stageMasterFilter_state-20260613.tar.gz   # → stageMasterFilter_state.json (1 엔트리)
```

2) SHA-256 (`shasum -a 256`)
```
eacc70c463622aca195ad37e26d488486d6e67ef0f5b1e7ae205045eb8f27753  aksj-reports-20260613.tar.gz
ec1774e0bea524b34b29064486291a38b7dd27fc702089c77fa5c3357c927c6e  aksj-stageMasterFilter_state-20260613.tar.gz
a2a5d197950814949d407100fd1878890a4c024bc177cf927e52405066bd6bb5  stageMasterFilter_state.json (원본 파일 자체)
```

## 4. 복원 명령

```bash
# 해시 검증 후 복원
shasum -a 256 -c <<'EOF'
eacc70c463622aca195ad37e26d488486d6e67ef0f5b1e7ae205045eb8f27753  /Users/tajun/spJavis-tools/_backup/aksj-reports-20260613.tar.gz
ec1774e0bea524b34b29064486291a38b7dd27fc702089c77fa5c3357c927c6e  /Users/tajun/spJavis-tools/_backup/aksj-stageMasterFilter_state-20260613.tar.gz
EOF

# reports/ 복원 (대상 경로에 reports/ 디렉토리로 풀림 — 기존 reports/가 있으면 덮어씀에 주의)
tar -xzf /Users/tajun/spJavis-tools/_backup/aksj-reports-20260613.tar.gz \
    -C /Users/tajun/spJavis/kiwoom-rest-trader

# 학습 상태 파일 복원
tar -xzf /Users/tajun/spJavis-tools/_backup/aksj-stageMasterFilter_state-20260613.tar.gz \
    -C /Users/tajun/spJavis/kiwoom-rest-trader/src/kiwoom/itemFilter
```

## 5. 비고 / 리스크

- 백업 시점과 `_scan_20260611.log`·`screener_state.json` 최종 수정(06-11 22:28~30) 사이에 추가 스캔 없음 — 06-12~13 신규 날짜 디렉토리 없음 확인.
- `.DS_Store`(macOS 메타파일)도 tar에 포함됨 — 무해.
- 20260514 디렉토리만 `prefetchManifest.json` 부재 — 원본부터 없던 것(파이프라인 도입 전 회차로 추정, 추정임을 명시). 백업 결손 아님.
- 1차 백업본은 단일 사본(로컬 디스크 1곳). 오프사이트/2차 사본은 본 과업 범위 밖 — 후속 과업에서 권장.
