# PRD Research Archive

> 이 폴더는 PRD.md 제작을 위한 심층조사 결과를 구조화하여 저장한다.
> 최종 PRD는 여기 저장된 조사 결과를 종합하여 생성된다.

## Folder Structure

```
prd-research/
├── README.md              ← 이 파일 (확장 규칙, 네이밍 규약)
├── _index.yaml            ← 전체 라운드 마스터 인덱스
├── round-01/              ← 1차 조사
│   ├── _round-meta.yaml   ← 라운드 메타데이터
│   ├── raw/               ← Teammate 원본 산출물 (전문)
│   │   ├── T01-workflow-architect.md
│   │   ├── T02-scenario-explorer.md
│   │   ├── T03-operator-analyst.md
│   │   └── T04-sustainability-strategist.md
│   └── synthesis/         ← 교차 분석·통합 결과
│       ├── S01-convergence.md        ← Green/Yellow/Red Zone 합의 분석
│       ├── S02-risk-register.md      ← 위험 가정 + 파킹 로트 통합
│       ├── S03-key-findings.md       ← 핵심 발견 (정의 문제, 아키텍처 수렴 등)
│       └── S04-prd-direction.md      ← PRD 섹션별 방향 조언
├── round-02/              ← (미래) 2차 심층조사
│   └── ...
└── round-NN/              ← N차 추가 조사
```

## Naming Conventions

### Round Folders
- Pattern: `round-{NN}/` (zero-padded 2 digits)
- Example: `round-01/`, `round-02/`, `round-13/`
- 라운드 번호는 시간순으로 단조 증가

### Raw Teammate Files
- Pattern: `T{NN}-{teammate-slug}.md`
- NN: teammate 번호 (round 내 순번)
- slug: kebab-case teammate 식별자
- Example: `T01-workflow-architect.md`, `T05-security-auditor.md`

### Synthesis Files
- Pattern: `S{NN}-{topic-slug}.md`
- NN: synthesis 문서 순번
- slug: 분석 주제의 kebab-case
- Example: `S01-convergence.md`, `S02-risk-register.md`

## File Metadata Schema

모든 `.md` 파일은 YAML frontmatter를 포함해야 한다:

```yaml
---
# Required
round: 1                                    # 조사 차수
type: raw | synthesis                        # 원본 vs 통합 분석
created: "2026-05-25T23:15:00+09:00"        # 생성 시점 (KST)

# For raw files
teammate: workflow-architect                 # teammate 식별자
axis: workflow-architecture                  # 조사 축
question_summary: "..."                      # 원본 질문 요약 (1-2문장)
assumption_axis: "A vs B"                    # 가정 축 명칭
branch_a: "Self-Contained"                   # 가정 A 레이블
branch_b: "Integrated"                       # 가정 B 레이블
web_search_count: 22                         # WebSearch 호출 횟수
sources: [...]                               # 참조 출처 목록

# For synthesis files
input_files: [...]                           # 입력으로 사용한 파일 목록
cross_cutting_axes: [...]                    # 교차 분석한 축 목록
---
```

## Extension Rules

### 새 조사 라운드 추가 시
1. `round-{NN}/` 폴더 생성 (다음 번호)
2. `_round-meta.yaml` 작성 (라운드 목적, 입력, 예상 산출물)
3. `raw/` 에 teammate 산출물 저장
4. `synthesis/` 에 교차 분석 저장
5. `_index.yaml` 에 새 라운드 항목 추가

### 기존 라운드 수정 시
- 원본 파일 수정 금지 (append-only)
- 수정이 필요하면 같은 round 내에 `_corrections/` 폴더 생성
- 수정 파일에 원본 파일 참조 + 수정 사유 명시

### 종합 단계 (모든 라운드 통합)
- `_index.yaml` 에서 전체 라운드 목록 확인
- 각 round의 `synthesis/` 폴더가 재조합 단위
- 라운드 간 충돌은 후속 라운드가 우선 (최신 조사가 이전 조사를 갱신)
