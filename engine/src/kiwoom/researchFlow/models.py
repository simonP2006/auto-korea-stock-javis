"""researchFlow 도메인 모델.

organizedCompany 의 종목명을 입력으로 받아 chart60_120 → chart240 →
chartDayPre → chartDay → investor → finance 필터를 통과시키는 과정에서
단계별 결과와 종목별 최종 판정을 표현한다.

- ``ResearchCandidate``: 입력 종목명·종목코드 한 쌍.
- ``StageOutcome``: 단일 필터 단계
  (chart60_120/chart240/chartDayPre/chartDay/investor/finance) 결과.
- ``ResearchResult``: 한 종목의 파이프라인 전체 결과.
- ``FullFlowSummary``: 4단(upperLowerPrice/conditionResearch/organizedCompany/
  researchedCompany) 통합 실행 요약.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

StageName = Literal[
    "chart60_120", "chart240", "chartDayPre", "chartDay", "investor", "finance"
]

PrefetchApiName = Literal[
    "chart60", "chart120", "chart240", "chartDay", "investor", "finance"
]
# ``"skipped"`` 는 backfill(과거일 부분수집)에서 finance API 를 의도적으로
# 호출하지 않았음을 나타낸다 — ka10001 은 당일 스냅샷 전용이라 과거 재무를
# 복원할 수 없기 때문. ``"empty"``/``"error"`` (호출은 했으나 실패) 와 구분된다.
PrefetchApiStatus = Literal["ok", "empty", "error", "skipped"]


@dataclass(frozen=True, slots=True)
class ResearchCandidate:
    """입력 종목 1건.

    Attributes:
        stk_nm: 종목명. organizedCompany.md 에서 읽은 원본 그대로.
        stk_cd: 종목코드. 매핑 실패 시 빈 문자열.
    """

    stk_nm: str
    stk_cd: str


@dataclass(slots=True)
class StageOutcome:
    """단일 필터 단계의 판정 결과.

    Attributes:
        name: 단계명 (``"chart60_120"`` / ``"chart240"`` / ``"chartDayPre"`` /
            ``"chartDay"`` / ``"investor"`` / ``"finance"``).
        selected: 해당 단계 통과 여부.
        category: 분류 라벨 (단계별로 의미 다름, 필터 모듈에 위임).
        reason: 사람이 읽을 수 있는 판정 사유.
        report_path: 단계 입력으로 사용된 .md 파일 경로 (저장 성공 시).
    """

    name: StageName
    selected: bool
    category: str
    reason: str
    report_path: Path | None = None


@dataclass(slots=True)
class ResearchResult:
    """한 종목의 파이프라인 전체 결과.

    Attributes:
        candidate: 입력 종목.
        stages: 실제 수행된 단계 결과 (조기 탈락 시 직전 단계까지만 포함).
        final_selected: 모든 단계 통과 여부.
        skip_reason: 코드 매핑 실패·API 예외 등 단계 진입 전 사유.
            정상 단계 평가로 탈락한 경우는 빈 문자열, 실제 사유는 마지막 stage.reason.
    """

    candidate: ResearchCandidate
    stages: list[StageOutcome] = field(default_factory=list)
    final_selected: bool = False
    skip_reason: str = ""


@dataclass(slots=True)
class PrefetchStatus:
    """한 종목에 대한 6개 API 호출 결과 상태.

    각 필드는 ``"ok"`` (정상 .md 저장 완료) / ``"empty"`` (빈 응답 — .md
    미저장 또는 placeholder) / ``"error"`` (예외 발생 — .md 미저장) /
    ``"skipped"`` (의도적 미호출 — backfill 에서 finance 처럼 과거 복원
    불가한 API) 중 하나.

    Attributes:
        chart60·chart120·chart240·chartDay·investor·finance: 각 API 호출
            결과 상태.
        error_messages: API 이름 → 예외 메시지 (``"error"`` 상태인 경우만).
    """

    chart60: PrefetchApiStatus = "error"
    chart120: PrefetchApiStatus = "error"
    chart240: PrefetchApiStatus = "error"
    chartDay: PrefetchApiStatus = "error"
    investor: PrefetchApiStatus = "error"
    finance: PrefetchApiStatus = "error"
    error_messages: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PrefetchManifest:
    """Stage 0 일괄 수집 결과 매니페스트.

    ``prefetchManifest.json`` 으로 디스크에 저장되어 Stage 1~5 필터 단계가
    API 재호출 없이 종목별 데이터 가용성을 판단할 수 있게 한다.

    Attributes:
        date: 실행 대상 날짜 (``YYYYMMDD``).
        by_stock: 종목코드 → :class:`PrefetchStatus` 매핑.
        started_at: Stage 0 시작 시각.
        finished_at: Stage 0 종료 시각.
    """

    date: str
    by_stock: dict[str, PrefetchStatus] = field(default_factory=dict)
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(slots=True)
class FullFlowSummary:
    """4단 통합 실행 요약.

    ``run_full_flow()`` 가 4 개 단계(upperLowerPrice / conditionResearch /
    organizedCompany / researchedCompany) 를 순차 실행한 결과를 한 데 모은다.

    Attributes:
        date: 실행 대상 날짜 (``YYYYMMDD``).
        upper_count: ka10017 응답으로 저장된 종목 수.
            단계 실패 시 0, ``upper_error`` 에 사유 기록.
        condition_unique_count: 조건검색 9개 누적 고유 종목 수.
            단계 실패 시 0, ``condition_error`` 에 사유 기록.
        organized_count: 통합 후 organizedCompany.md 의 종목 수.
            단계 실패 시 0, ``organize_error`` 에 사유 기록.
        research_results: 4 단계(researchedCompany) 종목별 상세 결과.
            organizedCompany 가 0건이거나 실패하면 빈 리스트.
        skipped_stage: 조기 종료 시점의 단계명 (조기 종료 없으면 빈 문자열).
            ``"organizedCompany"`` / ``"researchedCompany"`` 만 사용 —
            1·2 단계는 실패해도 격리되어 전체 흐름을 멈추지 않는다.
        skip_reason: ``skipped_stage`` 가 비지 않을 때의 사유.
        upper_error: 1 단계 예외 메시지(있으면).
        condition_error: 2 단계 예외 메시지(있으면).
        organize_error: 3 단계 예외 메시지(있으면).
    """

    date: str
    upper_count: int = 0
    condition_unique_count: int = 0
    organized_count: int = 0
    research_results: list[ResearchResult] = field(default_factory=list)
    skipped_stage: str = ""
    skip_reason: str = ""
    upper_error: str = ""
    condition_error: str = ""
    organize_error: str = ""

    @property
    def passed_count(self) -> int:
        """4 단계 최종 통과 종목 수 (researchedCompany.md 기록 대상)."""
        return sum(1 for r in self.research_results if r.final_selected)


__all__ = [
    "FullFlowSummary",
    "PrefetchApiName",
    "PrefetchApiStatus",
    "PrefetchManifest",
    "PrefetchStatus",
    "ResearchCandidate",
    "ResearchResult",
    "StageName",
    "StageOutcome",
]
