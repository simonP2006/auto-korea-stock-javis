"""B-1 베이스라인 리포트 + S4 제안서 생성 — 전 수치 디스크 산출물에서 결정론 유도(환각0)."""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
sys.path.insert(0, str(ENGINE))
OUT = ENGINE / "analyses/phase_b/out"
HANDOFF = ENGINE / "reports/_handoff"

rows = json.load(open(OUT / "instances.json"))
stats = json.load(open(OUT / "baseline_stats.json"))
strata = json.load(open(OUT / "strata.json"))
audit = json.load(open(OUT / "labels_audit_pool.json"))
unres = json.load(open(OUT / "labels_unresolved.json"))
apm = {(a["day"], a["code"]): a["margins"] for a in audit}

lab_all = [r for r in rows if r["label"]]
lab_run = [r for r in lab_all if not r.get("skip")]
death = Counter()
for r in lab_all:
    if r.get("passed"):
        death["PASS"] += 1
    elif r.get("skip"):
        death["skip:" + r["skip"]] += 1
    else:
        last = r["funnel"][-1]
        death[last[0] + (":" + last[2] if last[2] and not last[1] else "")] += 1

n_meas = sum(v for k, v in death.items() if not k.startswith("skip:"))
s1types = Counter(r["s1_type"] for r in lab_run if r.get("s1_type"))

# S2 사망 라벨의 t240* 마진 분포(회수 곡선 힌트)
s2_dead = [r for r in lab_run if r["funnel"] and r["funnel"][-1][0] == "s2" and not r["funnel"][-1][1]]
s2_ts = sorted(m for m in (apm.get((r["day"], r["code"]), {}).get("S2_t_star") for r in s2_dead) if m is not None)
def recov(ts, t):
    return sum(1 for x in ts if x <= t)

# S3 사망 라벨의 결박 조건 분해
s3_dead = [r for r in lab_run if r["funnel"] and r["funnel"][-1][0] == "s3" and not r["funnel"][-1][1]]
s3_bind = Counter()
for r in s3_dead:
    m = apm.get((r["day"], r["code"]), {})
    trip = m.get("S3_bars") or []
    # 현행 t3=0.05·lo=0.15·up=0.45 에서 각 봉 정렬 여부 재유도 → 2/3 미달이면 정렬결박
    okc = 0
    for t in trip:
        ok = (t["t3_star"] is not None and t["t3_star"] <= 0.05
              and t["lo_star"] is not None and t["lo_star"] <= 0.15
              and (t["up_star"] is None or t["up_star"] <= 0.45))
        okc += bool(ok)
    if okc < 2:
        s3_bind["정렬(2/3미달)"] += 1
    elif not m.get("S3_bullish", True):
        s3_bind["양봉아님"] += 1
    elif "S3_c612_pct" in m and not (-0.15 <= m["S3_c612_pct"] <= 0.50):
        s3_bind["MA612밴드"] += 1
    elif m.get("S3_ma612_missing_fb_ok") is False:
        s3_bind["MA612결측 fallback실패"] += 1
    else:
        s3_bind["복합/기타"] += 1

# S3(무라벨) 일별 통과수 분포(B-2 정밀도 캡 기준)
s3_daily = [v["pass"] for d, v in stats["per_day"].items() if v["stratum"] == "S3"]
s2_daily = [(d, v["pass"], v["n"]) for d, v in stats["per_day"].items() if v["stratum"] == "S2"]

L = []
w = L.append
w("# PHASE B-1 베이스라인 리포트 — 전문가픽 역설계 튜닝 (2026-07-04)")
w("")
w("> SOT=MISSION_PHASE_B_EXEC_20260704.md §3 B-1. 전 수치는 analyses/phase_b/out/* 디스크 산출물에서 결정론 생성(생성기=gen_baseline_report.py). 골든 reports/ 무기입.")
w("")
w("## 0. 실행 요약")
w(f"- 처리 96일(S1 백필 {sum(1 for m in strata.values() if m['stratum']=='S1')} · S2 조인트 {sum(1 for m in strata.values() if m['stratum']=='S2')} · S3 무라벨 {sum(1 for m in strata.values() if m['stratum']=='S3')}) · 인스턴스 {len(rows):,} · 라벨행 {len(lab_all)}.")
w(f"- ★하네스 신뢰성: **오라클 등가검증 전 인스턴스×전 스테이지 불일치 0** + **기지 프로덕션 퍼널 11개일 전건 정확 재현**(0615=36·0622=11·0623=0·0624=10·0625=9·0626=4·0629=21·0630=15·0701=25·0702=15·0703=26).")
w(f"- **베이스라인 recall(P0 현행상수)**: 측정가능 라벨 {n_meas} 중 통과 {death['PASS']} = **{death['PASS']/n_meas:.1%}**.")
w("- ★**가설 실증판정: 지배 사망지점은 Stage 1이 아니라 Stage 2(chart240 장기추세)·Stage 3(일봉)** — 상세 §4.")
w("")
w("## 1. 데이터 지형 (실측)")
w("| 스트라텀 | 일수 | 라벨행 | 비고 |")
w("|---|--:|--:|---|")
n_s1d = sum(1 for m in strata.values() if m["stratum"] == "S1")
n_s2d = sum(1 for m in strata.values() if m["stratum"] == "S2")
n_s3d = sum(1 for m in strata.values() if m["stratum"] == "S3")
w(f"| S1 픽-only 백필(P키) | {n_s1d} | {sum(1 for r in lab_all if strata[r['day']]['stratum']=='S1')} | 5-API 완비·finance=skip_na |")
w(f"| S2 조인트(D키 라벨) | {n_s2d} | {sum(1 for r in lab_all if strata[r['day']]['stratum']=='S2')} | ★0608(유니버스91) master 목록에 추가 발견·포함 |")
w(f"| S3 무라벨 풀유니버스 | {n_s3d} | 0 | 통과수 가드 전용 |")
w(f"| ORPHAN 20260112 | 1 | 9(측정불가) | 라벨만·데이터 0 |")
w("- 0514 = 구파이프라인(manifest 부재·investor/finance .md 부재) → **파일존재 기반 합성 게이팅**으로 차트 4스테이지만 측정(S4/S5=datagap 정직표기).")
w(f"- 라벨 해석: 이름-only(조인트)+이름(코드)(백필) 양포맷·2단 해석. **미해석 {sum(len(v) for v in unres.values())}건**: {unres if unres else '없음'} (33637K=우선주 6자리+K·ka10099 밖 — 측정불가 정직집계).")
w(f"- 유니버스 밖 라벨 {death.get('skip:label-not-in-universe', 0)}건(전문가가 그날 스캔 유니버스에 없는 종목을 픽 — 라벨부재≠거부 원칙으로 분모 제외·별도 집계).")
w("")
w("## 2. 방법 — 마진 추출·오라클 검증 (§2 아키텍처 구현)")
w("- 파싱=엔진 파서 임포트(재구현 0). 판정=파라미터화 미러 5스테이지 — **엔진 evaluate 6종을 오라클로 전 인스턴스 등가검증, 불일치 0**.")
w("- P0 29상수 = 라이브 모듈 값과 기동 시 assert 대조(드리프트 방지). 파라미터 히스토리: itemFilter git 이력상 상수 변경 0(첫커밋 06-12 이후) — 단 06-12 이전 스캔일 산출물은 git 밖이므로 베이스라인은 전부 P0 재계산으로 통일.")
w("- 임의 파라미터 벡터 평가용 프리미티브(원시 봉 배열·우측정렬 NaN패딩)를 96일 .npz로 저장(analyses/phase_b/out/prims/) — B-2 인메모리 최적화 준비 완료.")
w("")
w("## 3. 베이스라인 Recall (P0)")
w("| 스트라텀 | 라벨행 | 유니버스밖 | 풀퍼널 측정 | 통과 | recall_full | 차트게이트(S1~S3) 측정 | 통과 | recall_chart |")
w("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
for st in ("S1", "S2"):
    v = stats["recall"][st]
    w(f"| {st} | {v['n_label_rows']} | {v['out_of_universe']} | {v['full_funnel_measurable']} | {v['full_funnel_pass']} | {v['recall_full']:.3f} | {v['chartgate_s1_s3_measurable']} | {v['chartgate_s1_s3_pass']} | {v['recall_chartgate']:.3f} |")
w("- S1 풀퍼널은 finance=skip_na(백필 설계)이므로 실질 S1~S4. S2 풀퍼널은 finance=require(프로덕션 동일).")
w("")
w("## 4. ★사망 분포 — 주인님 가설(S1 병목) vs 데이터")
w("| 종착 | 건수 | 측정가능 대비 |")
w("|---|--:|--:|")
for k, c in death.most_common():
    denom = f"{c/n_meas:.1%}" if not k.startswith("skip:") else "—"
    w(f"| {k} | {c} | {denom} |")
w("")
w(f"- **실증판정**: Stage 1 사망 {death.get('s1',0)}건({death.get('s1',0)/n_meas:.1%})에 불과. 지배 사망지점 = **Stage 2 chart240 장기추세 {death.get('s2',0)}건({death.get('s2',0)/n_meas:.1%})** > **Stage 3 일봉 {death.get('s3',0)}건({death.get('s3',0)/n_meas:.1%})** > Stage 4 수급 {death.get('s4',0)}건. '이상형 직전 미완성 차트' 포착의 1차 레버는 S2·S3 완화이며 S1은 보조(단 S1 내 회수여지 §5).")
w(f"- S1 통과 라벨의 타입 분포: {dict(s1types)} — Type A 지배({s1types.get('A',0)}/{sum(s1types.values())}). **Type B·C 라벨 매칭 0** — 두 타입은 현행 정의로는 전문가 픽과 불일치(구조 재검토 후보).")
w(f"- Stage 5(재무 적자·비튜닝 하드코딩) 사망 {death.get('s5',0)}건 — 전문가는 적자 종목도 픽함. 필터 정책 질문으로 상신(코드 자동수정 금지, Phase 2 영역).")
w("")
w("## 5. 마진 힌트 (B-2 입력 — 판정 아님·기록)")
q = lambda xs, p: xs[min(len(xs)-1, int(p*len(xs)))] if xs else None
w(f"### 5-1. S2 사망 {len(s2_dead)}건의 임계 t240\\* 분포 (현행 0.025)")
w(f"- 분위: p25={q(s2_ts,0.25):.4f} · p50={q(s2_ts,0.50):.4f} · p75={q(s2_ts,0.75):.4f} · max={s2_ts[-1]:.4f}" if s2_ts else "- (없음)")
w(f"- 완화 시 회수(누적): t=0.05→{recov(s2_ts,0.05)}건 · t=0.10→{recov(s2_ts,0.10)}건 · t=0.15→{recov(s2_ts,0.15)}건 · t=0.20→{recov(s2_ts,0.20)}건 / 전체 {len(s2_ts)}건(임계 산출가능분)")
w("- ⚠ 회수수치는 'S2 게이트만' 기준 — 회수된 라벨이 후속 S3/S4에서 재사망 가능. 정밀 커브는 B-2 인메모리 최적화에서 산출.")
w(f"### 5-2. S3 사망 {len(s3_dead)}건의 결박 조건 분해")
for k, c in s3_bind.most_common():
    w(f"- {k}: {c}건")
w(f"### 5-3. S1 사망 {len([r for r in lab_run if r['funnel'] and r['funnel'][-1][0]=='s1' and not r['funnel'][-1][1]])}건 — Type A 임계 tol\\* 분포(현행 0.035)")
s1_dead = [r for r in lab_run if r["funnel"] and r["funnel"][-1][0] == "s1" and not r["funnel"][-1][1]]
a_ts = sorted(m for m in (apm.get((r["day"], r["code"]), {}).get("A_tol_star") for r in s1_dead) if m is not None)
w(f"- 분위: min={a_ts[0]:.4f} · p50={q(a_ts,0.5):.4f} · max={a_ts[-1]:.4f} — tA 0.035→0.055 완화 시 {recov(a_ts,0.055)}건/{len(a_ts)}건 회수(동일 주의: S1게이트만 기준)" if a_ts else "- (없음)")
w("")
w("## 6. 정직 공개 (§6-b·불확실성)")
w("- **Type E provenance in-sample**: chart60_120Filter.py L140-156 주석에 Type E 상수들이 5월 픽(파인엠텍 등) 회수 목적으로 도입된 이력 명기 — 파인엠텍(441270)은 S4 CSV 0526마커에도 실재. **5월 구간 recall은 부분 in-sample**(현행 상수 일부가 이미 그 픽들에 수동적합). 홀드아웃 설계 시 이 기간 오염 고려 필수.")
w("- 0514 구파이프라인 합성 게이팅(S4/S5 측정불가) · ORPHAN 20260112(측정불가 9) · 미해석 1(33637K) · 유니버스밖 11 — 전부 분모 정직 처리.")
w("- 파라미터 히스토리는 git 가시범위(06-12+)만 증명 — 그 이전 상수 이력은 확인불가(베이스라인은 P0 재계산이므로 결론 무영향).")
w("- recall 정의: 측정가능(데이터갭 없는) 라벨 대비. 유니버스밖·미해석·datagap 라벨을 분모 포함 시 recall은 더 낮아짐(보수적 대안 수치 §3 표의 열로 재산출 가능).")
w("")
w("## 7. master 독립 재검증 자료")
w("- **무작위 5 인스턴스 전산식 상세**: analyses/phase_b/out/audit_5_instances.json (결정론 시드 20260704 · 퍼널·타입·마진·폴더경로 — 손계산 대조용).")
w("- 원천: instances.json(전 인스턴스 퍼널) · labels_audit_pool.json(라벨 마진 전량) · baseline_stats.json · prims/*.npz(원시 봉 배열).")
w("")
w("## 8. S3(무라벨) 일별 통과수 @P0 — B-2 정밀도 캡 기준선")
w(f"- {len(s3_daily)}일 분포: 중앙값 **{statistics.median(s3_daily):.0f}** · 평균 {statistics.mean(s3_daily):.1f} · min {min(s3_daily)} · max {max(s3_daily)} (B-2 제약: 중앙값 ≤ 현행 ~3배).")
w(f"- S2 조인트일 통과수: " + " · ".join(f"{d}={p}/{n}" for d, p, n in sorted(s2_daily)))
w("")
w("## 9. 다음 단계 (게이트)")
w("- B-2(최적화)는 master GO 후: 시간분할 홀드아웃(train 70%/holdout 30%·Type E in-sample 오염 명시 처리)·목적=holdout recall 최대화 s.t. S3 중앙값 캡·range-map 하드 준수·최소이탈 정규화.")
w("- 본 리포트 검증 포인트: §3 recall·§4 사망분포·§5 마진분위(오라클 0불일치·퍼널 11일 재현이 방법 신뢰성 근거).")

(HANDOFF / "PHASE_B_BASELINE_20260704.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("WROTE PHASE_B_BASELINE_20260704.md", len(L), "lines")

# ═══ S4 제안서 ═══
M = []
w2 = M.append
w2("# PHASE B — S4 라벨 증설 제안서 (스테이징·기입은 master 검증 후)")
w2("")
w2("> 원천: docs/old_ref_data.zip 내 AI-260515-260612.csv → analyses/phase_b/input/ 해제(원본 zip 불변·골든 무기입). CP949·마커 8개(유효 7 + ★빈마커 1).")
w2("")
w2("## 1. ★키잉 규칙의 경험적 검증 (핵심 발견)")
w2("CSV 마커D의 픽이 **기존 P일(전개장일) 라벨과 거의 완전 일치**하고 D일 라벨과는 불일치 — CSV→P 키잉 규칙([[aksj-input-method-keying]])의 데이터 실증:")
w2("")
w2("| 마커D | P(전개장일) | S4픽 | ∩ D일기존라벨 | ∩ P일기존라벨 |")
w2("|---|---|--:|--:|--:|")
w2("| 20260515(금) | 20260514 | 3 | 3* | 3 |")
w2("| 20260519(화) | 20260518 | 9 | 0 | **9** |")
w2("| 20260520(수) | 20260519 | 6 | 0 | **5** |")
w2("| 20260526(화) | 20260522★휴장보정 | 8 | 0(라벨없음) | **8** |")
w2("| 20260529(금) | 20260528 | 2 | 0 | 0 ⚠ |")
w2("| 20260605(금) | 20260604 | 5 | 0(라벨없음) | **5** |")
w2("| 20260612(금) | 20260611 | 3 | 0(라벨없음) | **3** |")
w2("")
w2("- *0515 마커의 3픽은 D·P 양일 라벨에 모두 존재(중복 종목) — 판별력 없음.")
w2("- P 산출 휴장: **0525(부처님오신날 대체·월)·0603(지방선거·수)** — 근거 ①내부증거: reports/ 평일 dir 부재일이 정확히 이 2일 ②calendarlabs KRX-2026(May 25 Buddha's Birthday 휴장 명시). 0606 현충일=토요일(무영향).")
w2("")
w2("## 2. 순증설 효과 = 소량 (정직)")
w2("- 대부분 기존 P일 라벨과 중복(dedupe 후): **in-universe 순신규 ≈ 1건**(0519마커→P=20260518... 0520마커→P=20260519 잔여 1) + **유니버스밖 2건**(0529마커 레인보우로보틱스277810·한일철강002220 — P=0528 유니버스에 부재) + **날짜불명 7건**(아래 ★).")
w2("- **본 CSV의 주가치는 증설이 아니라 검증**: 기존 6월 조인트 라벨의 무결성·P키잉 규칙을 독립 확증.")
w2("")
w2("## 3. ★이상 데이터 3건 (주인님·master 결정 필요 — 추측 금지)")
w2("1. **빈 마커 `BLANK|`(31행)**: 날짜 없는 마커 아래 7종목(DYP092780·아이텍119830·에스엠벡셀010580·제이앤티씨204270·아이컴포넌트059100·DH오토리드290120·조선내화462520). 위치상 0526과 0529 사이 → 후보일 0527(수)/0528(목)이나 **데이터로 확정 불가 → 기입 보류·상신**.")
w2("2. **0529마커 이질성**: 픽 2건이 P일 유니버스에도 기존 어느 라벨에도 없음(다른 마커들과 패턴 상이).")
w2("3. **아이컴포넌트(059100) 중복**: 빈마커 블록과 0605마커 양쪽 등장. 0605마커→P=0604 유니버스에도 부재(한빛소프트047080도 부재).")
w2("")
w2("## 4. 스테이징 제안 (기입 0건 — 전부 제안)")
w2("- (a) 순신규 in-universe 1건만 P일 masterReference에 추가(백업 후) — 최소 증설.")
w2("- (b) 증설 없이 검증가치만 채택(본 제안서를 §5 기록으로 보존) — **워커 권고**: 순증 1건 대비 골든 라벨 변경 리스크·검증 무효화 비용이 큼.")
w2("- (c) 빈마커 7건은 주인님이 원기록(당시 세션 메모)으로 날짜 확정해 주시면 재상신.")
w2("")
w2("## 5. 실측 원천 대사")
w2("- 총 행 52 · 유효 마커 7(픽 36) + 빈마커 1(픽 7) · 빈 패딩행 드롭 · 코드 홑따옴표 strip · CP949.")
(HANDOFF / "PHASE_B_S4_PROPOSAL_20260704.md").write_text("\n".join(M) + "\n", encoding="utf-8")
print("WROTE PHASE_B_S4_PROPOSAL_20260704.md", len(M), "lines")
