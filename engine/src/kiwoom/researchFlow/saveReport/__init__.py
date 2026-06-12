"""researchFlow 결과 저장 서브패키지.

저장 산출물 (``reports/<YYYYMMDD>/`` 직속):
    - ``researchedCompany.md`` — 최종(=Stage 4) 통과 종목명 (단순 텍스트)
    - ``stage1_chart60_120_passed.md`` — Stage 1 통과 종목명
    - ``stage2_chart240_passed.md``    — Stage 2 통과 종목명
    - ``stage3_chartDay_passed.md``    — Stage 3 통과 종목명
    - ``stage4_investor_passed.md``    — Stage 4 통과 종목명
      (= researchedCompany.md 와 동일 내용)
    - ``prefetchManifest.json`` — Stage 0 일괄 수집 결과 매니페스트 (JSON)

사용 예::

    from src.kiwoom.researchFlow.saveReport import (
        save_researched_company,
        save_all_stages_passed,
        save_prefetch_manifest,
        load_prefetch_manifest,
    )

    path = save_researched_company(results, date="20260515")
    paths = save_all_stages_passed(results, date="20260515")
    save_prefetch_manifest(manifest)
    manifest = load_prefetch_manifest("20260515")
"""

from src.kiwoom.researchFlow.saveReport.plain_text import (
    render_plain_text,
    render_stage_passed,
    save_all_stages_passed,
    save_researched_company,
    save_stage_passed,
)
from src.kiwoom.researchFlow.saveReport.prefetch_manifest import (
    load_prefetch_manifest,
    save_prefetch_manifest,
)

__all__ = [
    "load_prefetch_manifest",
    "render_plain_text",
    "render_stage_passed",
    "save_all_stages_passed",
    "save_prefetch_manifest",
    "save_researched_company",
    "save_stage_passed",
]
