# AgenticWorkflow

**어떤 에이전트 워크플로우로든 분화할 수 있는 만능줄기세포(Pluripotent Stem Cell) 프레임워크.**

복잡한 작업을 **워크플로우로 설계**하고, 그 워크플로우를 **실제로 구현**하여 동작시키는 것이 목표입니다.
줄기세포가 어떤 세포로든 분화하듯, 이 프레임워크는 하나의 코드베이스에서 연구·분석·개발·자동화 등
어떤 도메인의 에이전트 워크플로우든 생성하고 실행할 수 있습니다.

그리고 줄기세포의 분화에서 가장 중요한 사실 — **분화된 모든 세포는 부모의 전체 게놈을 그대로 갖고 있습니다.**
이 코드베이스에서 태어나는 모든 자식 시스템은, 목적은 다르지만, 부모의 전체 DNA(절대 기준, 품질 보장, 안전장치, 기억 체계 등)를
구조적으로 내장합니다. 상세: [`soul.md`](soul.md)

## 프로젝트 목표

```
Phase 1: 워크플로우 설계  →  workflow.md (설계도)
Phase 2: 워크플로우 구현  →  실제 동작하는 시스템 (최종 산출물)
```

워크플로우를 만드는 것은 중간 산출물입니다. **워크플로우에 기술된 내용이 실제로 동작하는 것**이 최종 목표입니다.

## 워크플로우 구조

모든 워크플로우는 3단계로 구성됩니다:

1. **Research** — 정보 수집 및 분석
2. **Planning** — 계획 수립, 구조화, 사람의 검토/승인
3. **Implementation** — 실제 실행 및 산출물 생성

## 프로젝트 구조

```
AgenticWorkflow/
├── CLAUDE.md              # Claude Code 전용 지시서 (경량 TOC)
├── AGENTS.md              # 모든 AI 에이전트 공통 지시서 (Hub — 방법론 SOT)
├── GEMINI.md              # Gemini CLI 전용 (Spoke)
├── AGENTICWORKFLOW-USER-MANUAL.md                    # 사용자 매뉴얼
├── AGENTICWORKFLOW-ARCHITECTURE-AND-PHILOSOPHY.md    # 설계 철학 및 아키텍처 전체 조감도
├── DECISION-LOG.md           # 프레임워크 설계 결정 로그 (ADR 51개; 제품 ADR은 docs/architectural-decision-records.md에 별도 14개)
├── COPYRIGHT.md              # 저작권
├── soul.md                   # 프로젝트 영혼 (자식 시스템에 유전되는 DNA 정의)
├── docs/                     # 문서
│   ├── code-convention.md             # 제품 빌드 코딩 규약 (Stock Filter)
│   ├── code-quality-guide.md          # 제품 빌드 품질 기준 (5개 가중 차원)
│   ├── architectural-decision-records.md  # 제품 ADR 14개 (루트 DECISION-LOG와 별도 네임스페이스)
│   └── protocols/            # 상세 프로토콜 (on-demand 참조)
│       ├── autopilot-execution.md       # 워크플로우 실행 체크리스트 + NEVER DO
│       ├── quality-gates.md             # L0-L2 4계층 + P1 검증 14항목 상세
│       ├── ulw-mode.md                  # ULW 강화 규칙 3개 + 런타임 메커니즘
│       ├── context-preservation-detail.md  # Hook 내부 메커니즘 + D-7 인스턴스
│       └── code-change-protocol.md      # CCP 3단계 + CAP + 비례성 규칙
├── .claude/
│   ├── settings.json      # Hook 설정 (7개 이벤트 + permissions.deny Layer 0)
│   ├── agents/            # 서브에이전트 16개 (제네릭 3: reviewer/fact-checker/translator + 빌드 전용 13: param-extractor/pipeline-analyzer/error-analyzer/research-integrator/architect/{claude-md,scan,tune}-{designer,builder}/infra-validator/smoke-tester)
│   ├── commands/          # Slash Commands 10개 (/install, /maintenance, /run-prompts, /resume-prompts, /setup-prompts, /verify-prompts, /review-research, /review-design, /review-translation, /accept-system)
│   ├── hooks/scripts/     # 29개 .py (24 Hook + Setup 2 + 테스트 3) — Safety/Validation에 validate_state_yaml.py(차단형 SOT 가드, exit 2) + monitor_translation_output.py 추가
│   ├── context-snapshots/ # 런타임 스냅샷 (gitignored)
│   └── skills/
│       ├── workflow-generator/ # 워크플로우 설계·생성 (designer)
│       ├── workflow-executor/  # 워크플로우 실행 오케스트레이터 (runtime executor) — 12단계 빌드 구동, SOT 단독 기록
│       └── doctoral-writing/   # 박사급 학술 글쓰기
├── prompt-runner/            # 프롬프트 러너 — 110개 프롬프트 자동 순차 실행 도구
│   ├── run.py                # 세션 ID 캡처·재개, 3계층 검증, stagnation 감지
│   ├── manifest.json         # 110개 프롬프트 메타데이터 (해시, 크기, /clear 플래그)
│   ├── prompt-refining-strategy.md  # 프롬프트 재설계 프레임워크
│   └── prompts/              # 001.txt ~ 110.txt (35개 세션, /clear 블록 포함)
├── prompt/                   # 워크플로우 실행 인스턴스 (kiwoom-rest-trader stock-filter 빌드)
│   ├── workflow.md           # 실행된 12단계 스펙 (855줄)
│   ├── workflow-coding.md    # 구현 청사진 (2143줄) / prd.md (776줄) / workflow-idea/
│   ├── prd-research/         # 4라운드 PRD 심층조사 (raw 20 + synthesis 16)
│   ├── .claude/state.yaml    # SOT (current_step:12, status:completed_degraded)
│   ├── .claude/codegen/      # 6모듈 값-동등성 파이프라인 (infra_schema → generate/validate_infra, param_ast/validate_param_values, unit_conversion)
│   ├── .claude/tests/        # pytest L1 (55 테스트) / .claude/step-registry.yaml
│   ├── outputs/              # 12단계 산출물 (EN 10 + KO 10 + pacs-logs/)
│   └── (4개 DeepDive PRD 심층조사 프레임워크 + crystalize/distill 헬퍼)
├── tests/                    # 최상위 pytest 스위트 (codegen 17 + SOT 스키마 21 + 상태머신 불변식 26 = 64)
├── translations/glossary.yaml  # 번역 용어 사전 (@translator SOT, 466개 용어)
└── coding-resource/            # 이론적 기반 자료
    └── recursive language models.pdf  # MIT CSAIL RLM 논문
```

## 스킬

| 스킬 | 설명 |
|------|------|
| **workflow-generator** | Research → Planning → Implementation 3단계 구조의 `workflow.md`를 설계·생성. Sub-agents, Agent Teams, Hooks, Skills를 조합한 구현 설계 포함. |
| **workflow-executor** | 생성된 `workflow.md`를 **실제로 실행**하는 런타임 오케스트레이터(designer에 대응하는 executor). SOT(`state.yaml`) 단독 기록, 단계별 에이전트 디스패치(Step 1·6 팀 병렬, Step 9 순차), L0-L2 게이트 + pytest + 번역, F-1~F-14 폴백, Step 12 사람 검수 강제. |
| **doctoral-writing** | 박사급 학위 논문의 학문적 엄밀성과 명료성을 갖춘 글쓰기 지원. 한국어·영어 모두 지원. |

## 사용자 서브에이전트 (Sub-agents)

`.claude/agents/`에 정의된 전문 에이전트 **16개**. 아래 **제네릭 3종**은 워크플로우의 `Review:`/`Translation:` 필드로 호출되고, **빌드 전용 13종**은 `workflow-executor`가 단계별로 디스패치합니다. 각자 부모 DNA(절대 기준, 품질 게이트, SOT, pACS 자기채점)를 내장합니다.

| 서브에이전트 | 역할 | 주 호출 지점 |
|------------|------|-------------|
| **@reviewer** | 적대적 리뷰어 — Enhanced L2 품질 계층. 산출물을 공격적으로 비판하여 약점·논리적 비약·미검증 주장을 발굴. 독립적 pACS(F/C/L) 재채점 | `Review:` 필드가 지정된 단계 |
| **@fact-checker** | 사실 검증 전문가 — claim-by-claim 분석. 외부 출처 검증(WebSearch/WebFetch) + 인용 정확성 + 수치·날짜·고유명사 크로스체크 | `Review:` 필드에 `+ @fact-checker` 추가 시 |
| **@translator** | 영→한 번역 전문가 — `translations/glossary.yaml` 용어 사전 기반 일관성. 7단계 프로토콜(pre-mortem → 번역 → 자기검토 → pACS) + 4계층 완결성 검증. ADR-051로 `memory: project` 채택 | `Translation: @translator` 필드가 지정된 단계 |

### 빌드 전용 서브에이전트 (13개 — stock-filter 워크플로우)

`workflow-executor`가 `prompt/workflow.md`의 12단계를 구동하며 Step별로 호출하는 일회성 빌드 에이전트. 제네릭 3종과 달리 minimal frontmatter(`name`/`description` 없음, `model`+`tools`+`maxTurns`)를 사용하며, `error-analyzer`만 `sonnet`(나머지 `opus`)입니다.

| 서브에이전트 | Step | 역할 |
|------------|------|------|
| **param-extractor** / **pipeline-analyzer** / **error-analyzer**(sonnet) | 1 | 리서치 팀 — 파라미터 인벤토리·파이프라인 분석·에러 패턴 |
| **research-integrator** | 2 | 리서치 결과 통합 |
| **architect** | 4 | 아키텍처 설계 |
| **claude-md-designer** | 5 | CLAUDE.md 청사진 설계 |
| **scan-designer** / **tune-designer** | 6 | 스캔·필터튠 청사진 설계 (팀) |
| **claude-md-builder** | 8 | CLAUDE.md 빌드 |
| **scan-builder** / **tune-builder** | 9 | 스캔·필터튠 코드 빌드 (순차) |
| **infra-validator** | 10 | 인프라 검증 |
| **smoke-tester** | 11 | 스모크 테스트 |

## 슬래시 명령어 (Slash Commands)

`.claude/commands/`에 정의된 10개 명령어. 세션 내에서 `/명령어`로 호출합니다.

| 명령어 | 역할 |
|--------|------|
| `/install` | Setup Init 검증 — Python, PyYAML, 스크립트 구문, 디렉터리, SOT 쓰기 패턴 무결성 확인 |
| `/maintenance` | 주기적 건강 검진 — stale archives, knowledge-index, work_log 크기, doc-code 동기화(DC-1~DC-6) |
| `/review-research` | Research 결과 검토 — Step 3 사람 승인 게이트, 승인 시 `current_step:4` |
| `/review-design` | 설계 검토 — Step 7 사람 승인 게이트, 승인 시 `current_step:8` |
| `/review-translation` | 번역 현황 대시보드 — SOT `translation_tasks`/`outputs.*-ko`를 읽어 단계별 pACS·glossary 상태 표시 (재번역 시 `@translator` 호출) |
| `/accept-system` | 최종 시스템 검수 — Step 12 게이트, 10개 시나리오, **항상 사람 검증 필요**(Autopilot 자동승인 예외) |
| `/setup-prompts` | 프롬프트 러너 초기화 — 110개 프롬프트의 placeholder(제목·목표) 치환 |
| `/verify-prompts` | 프롬프트 파일 무결성 검증 — 해시·크기·구문 확인 |
| `/run-prompts` | 프롬프트 러너 시작 — 001.txt부터 순차 자동 실행 |
| `/resume-prompts` | 중단된 러너 재개 — `state.json`에 저장된 마지막 위치부터 이어서 실행 |

## 프롬프트 러너 (Prompt Runner)

장시간 다단계 프롬프트 시퀀스를 **무인 자동 실행**하는 도구입니다. 110개의 번호가 매겨진 프롬프트 블록(`001.txt`~`110.txt`)을 순서대로 Claude Code에 주입하며, 대략 2~3 프롬프트마다 `/clear`로 컨텍스트를 분리하여 **총 35개 독립 세션**으로 병렬 탐색·검증·통합을 수행합니다. (이 러너는 2026-05-26에 실행 완료 — 75 실행 + 35 clear, 0 실패. 검출된 21건 suspicious는 모두 `context window` 키워드 오탐.)

### 핵심 기능

- **세션 관리**: pipe 모드로 세션 ID 캡처 후 `--resume`으로 이어 실행. `/clear` 블록 자동 처리
- **3계층 검증**:
  1. **Silent Failure 키워드 탐지** — `error_during_tool`·`aborted`·`failed to complete`·`context window` 등 실패 지표 감지 시 재시도
  2. **파일 변경 스냅샷** — 프롬프트 실행 전·후 파일 시스템 diff로 실제 산출물 확인
  3. **State Tracking** — `state.json`에 실행 상태·완료 보고서 저장 (재개 기반)
- **Extended Thinking**: 프롬프트당 ~16K 토큰의 확장 사고 예산 할당
- **Stagnation Watchdog**: idle timeout 감지 시 자동 회수
- **Rate-limit 대응**: intelligent retry + 지수 백오프
- **완료 보고서 강제 주입**: 각 프롬프트 종료 시 meta(exit code, session ID, 소요 시간, 파일 변경 목록) 자동 기록

### 역할

Research 단계의 **병렬 심층조사 자동화**가 주 용도입니다. `prompt/` 디렉터리의 PRD 프레임워크(기술 개발·코딩 구현·외부 통합 심층조사)와 결합하여, 각 세션이 독립적으로 특정 관점을 탐색한 뒤 최종 통합 단계에서 `final-research.md`로 수렴합니다.

상세: `prompt-runner/prompt-refining-strategy.md`

## Context Preservation System

컨텍스트 토큰 초과, `/clear`, 컨텍스트 압축 시 작업 내역이 상실되는 것을 방지하는 자동 저장·복원 시스템입니다. 5개의 Hook 스크립트가 작업 내역을 MD 파일로 자동 저장하고, 새 세션 시작 시 RLM 패턴(포인터 + 요약 + 완료 상태 + Git 상태)으로 이전 맥락을 복원합니다. Knowledge Archive에는 세션별 phase(단계), phase_flow(다단계 전환 흐름), primary_language(주요 언어), error_patterns(Error Taxonomy 12패턴 분류 + resolution 매칭), tool_sequence(RLE 압축 도구 시퀀스), final_status(세션 종료 상태), tags(경로 기반 검색 태그), session_duration_entries(세션 길이) 메타데이터가 자동 기록됩니다. 스냅샷의 설계 결정은 품질 태그 우선순위로 정렬되어 노이즈가 제거되고, 스냅샷 압축 시 IMMORTAL 섹션이 우선 보존되며(압축 감사 추적 포함), 모든 파일 쓰기에 atomic write(temp → rename) 패턴이 적용됩니다. P1 할루시네이션 봉쇄로 KI 스키마 검증, 부분 실패 격리, SOT 쓰기 패턴 검증, SOT 스키마 검증이 결정론적으로 수행됩니다.

| 스크립트 | 트리거 | 역할 |
|---------|--------|------|
| `context_guard.py` | (Hook 디스패처) | Hook 통합 진입점. `--mode`에 따라 적절한 스크립트로 라우팅 |
| `save_context.py` | SessionEnd, PreCompact | 전체 스냅샷 저장 |
| `restore_context.py` | SessionStart | 포인터+요약으로 복원 |
| `update_work_log.py` | PostToolUse | 9개 도구(Edit, Write, Bash, Task, NotebookEdit, TeamCreate, SendMessage, TaskCreate, TaskUpdate) 작업 로그 누적, 75% threshold 시 자동 저장 |
| `generate_context_summary.py` | Stop | 매 응답 후 증분 스냅샷 + Knowledge Archive 아카이빙 (30초 throttling, E5 Guard) |
| `_context_lib.py` | (공유 라이브러리) | 파싱, 생성, SOT 캡처, 토큰 추정, Smart Throttling, Autopilot 상태 읽기·검증, ULW 감지·준수 검증, 절삭 상수 중앙화(10개), sot_paths() 경로 통합, 다단계 전환 감지, 결정 품질 태그 정렬, Error Taxonomy 12패턴 분류+Resolution 매칭, IMMORTAL-aware 압축+감사 추적, E5 Guard 중앙화, Knowledge Archive 통합(부분 실패 격리), KI 스키마 검증, SOT 스키마 검증, Adversarial Review P1 검증, Translation P1 검증, pACS P1 검증, Cross-Step Traceability P1 검증, Domain Knowledge P1 검증, Predictive Debugging P1, Abductive Diagnosis Layer(사전 증거 수집 + 사후 검증 + KA 아카이빙 + Fast-Path) |
| `setup_init.py` | Setup (`--init`) | 세션 시작 전 인프라 건강 검증 (Python, PyYAML, 스크립트 구문, 디렉터리) + SOT 쓰기 패턴 검증(P1 할루시네이션 봉쇄) |
| `output_secret_filter.py` | PostToolUse (Bash\|Read) | 도구 출력 시크릿 탐지 — 3-tier 추출(tool_response→file_path→transcript), 25+ 패턴, 2-패스 스캔(raw+decoded). P1 할루시네이션 봉쇄 |
| `security_sensitive_file_guard.py` | PostToolUse (Edit\|Write) | 보안 민감 파일 수정 경고 — `.env`, `credentials`, `*.pem` 등 12개 패턴. exit 0 (경고 전용) |
| `validate_state_yaml.py` | PostToolUse (Write\|Edit) | `prompt/.claude/state.yaml` SOT 스키마 검증 — 무효 status/current_step/translation/output-key 쓰기를 **exit 2로 차단**(유일한 차단형 PostToolUse 훅). `infra_schema.py` enum import |
| `monitor_translation_output.py` | PostToolUse (Write) | `.ko.md` 번역 출력 비차단 모니터 — 크기·glossary·미번역 블록 점검(T-1~T-3, 항상 exit 0) |
| `setup_maintenance.py` | Setup (`--maintenance`) | 주기적 건강 검진 (stale archives, knowledge-index 무결성, work_log 크기, doc-code 동기화 검증(DC-1~DC-6)) |
| `block_destructive_commands.py` | PreToolUse (Bash) | 위험 명령 실행 전 차단 (git push --force, git reset --hard, rm -rf / 등). exit code 2 + stderr 피드백 (P1 할루시네이션 봉쇄) |
| `block_test_file_edit.py` | PreToolUse (Edit\|Write) | TDD 모드(`.tdd-guard` 존재) 시 테스트 파일 수정 차단. exit code 2 + stderr 피드백 |
| `predictive_debug_guard.py` | PreToolUse (Edit\|Write) | 에러 이력 기반 위험 파일 사전 경고. `risk-scores.json` 캐시 조회 → 임계값 초과 시 stderr 경고 (exit code 0, 경고 전용) |
| `diagnose_context.py` | (독립 스크립트) | Abductive Diagnosis 사전 증거 수집 — 품질 게이트 FAIL 시 증거 번들(retry history, upstream evidence, hypothesis priority) 수집. Orchestrator가 수동 호출 |
| `validate_diagnosis.py` | (독립 스크립트) | Abductive Diagnosis P1 사후 검증 — AD1-AD10 구조적 무결성 검증. Orchestrator가 수동 호출 |

**테스트 커버리지**: Safety Hook 3종에 대해 **131개 자동화 테스트** (output_secret_filter: 44 — 단위 22+Tier3 통합 8+Tier1 통합 9+Tier2 통합 5 / security_sensitive_file_guard: 44 / block_destructive_commands: 43). `setup_init.py`가 세션 시작 시 전체 검증, `setup_maintenance.py`가 DC-1~DC-6으로 doc-code 동기화 검증.

## Autopilot Mode

워크플로우를 무중단으로 실행하는 모드입니다. `(human)` 단계를 품질 극대화 기본값으로 자동 승인하고, `(hook)` exit code 2는 그대로 차단합니다.

- **Anti-Skip Guard**: 각 단계 완료 시 산출물 파일 존재 + 최소 크기(100 bytes) 검증
- **Decision Log**: 자동 승인 결정은 `autopilot-logs/step-N-decision.md`에 기록
- **런타임 강화**: Hook 기반 컨텍스트 주입 + 스냅샷 내 Autopilot 상태 보존

상세: `AGENTS.md §5.1`

## ULW (Ultrawork) Mode

프롬프트에 `ulw`를 포함하면 활성화되는 **철저함 강도(thoroughness intensity) 오버레이**입니다. Autopilot(자동화 축)과 **직교**하여 어떤 조합이든 가능합니다.

- **I-1. Sisyphus Persistence**: 최대 3회 재시도, 각 시도는 다른 접근법. 100% 완료 또는 불가 사유 보고
- **I-2. Mandatory Task Decomposition**: TaskCreate → TaskUpdate → TaskList 필수
- **I-3. Bounded Retry Escalation**: 동일 대상 3회 초과 재시도 금지(품질 게이트는 별도 예산 적용)
- **Compliance Guard**: Python Hook이 3개 강화 규칙의 준수를 결정론적으로 검증 (스냅샷 IMMORTAL 보존)

상세: `docs/protocols/ulw-mode.md`

## 4계층 품질 보장 (Quality Assurance Stack)

워크플로우 각 단계의 산출물이 **기능적 목표를 100% 달성했는지** 검증하는 다계층 품질 보장 시스템입니다.

| 계층 | 이름 | 검증 대상 | 성격 |
|------|------|---------|------|
| **L0** | Anti-Skip Guard | 파일 존재 + ≥ 100 bytes | 결정론적 (Hook) |
| **L1** | Verification Gate | 기능적 목표 100% 달성 | 의미론적 (Agent 자기검증) |
| **L1.5** | pACS Self-Rating | F/C/L 3차원 신뢰도 | Pre-mortem Protocol 기반 |
| **L2** | Adversarial Review (Enhanced) | 적대적 검토 (`@reviewer` + `@fact-checker`) | `Review:` 필드 지정 단계 |

- **검증 기준 선행 선언**: 워크플로우의 각 단계에 `Verification` 필드로 구체적·측정 가능한 기준을 Task 앞에 정의
- **pACS (predicted Agent Confidence Score)**: Pre-mortem Protocol 후 F(Factual Grounding), C(Completeness), L(Logical Coherence) 채점. min-score 원칙: pACS = min(F,C,L)
- **행동 트리거**: GREEN(≥70) 자동 진행, YELLOW(50-69) 플래그 후 진행, RED(<50) 재작업
- **Adversarial Review (L2)**: `@reviewer`(코드/산출물 비판적 분석) + `@fact-checker`(외부 사실 검증) Sub-agent로 독립적 검토. P1 검증(`validate_review.py`)으로 리뷰 품질 보장
- **Team 3계층 검증**: L1(Teammate 자기검증) + L1.5(pACS 자기채점) + L2(Team Lead 종합검증 + 단계 pACS)
- **검증 로그**: `verification-logs/step-N-verify.md`, `pacs-logs/step-N-pacs.md`
- **Abductive Diagnosis**: 품질 게이트(Verification/pACS/Review) FAIL → 재시도 사이에 3단계 구조화된 진단(P1 사전 증거 수집 → LLM 원인 분석 → P1 사후 검증) 수행. Fast-Path(FP1-FP3)로 결정론적 단축 가능
- **하위 호환**: `Verification` 필드 없는 기존 워크플로우는 Anti-Skip Guard만으로 동작

상세: `AGENTS.md §5.3`, `§5.4`, `§5.5`, `§5.6`

## 실제 적용 사례 — Stock Filter 빌드 (Worked Instance)

이 저장소는 프레임워크가 **자기 자신을 사용해 만든 첫 자식 시스템**의 빌드 흔적을 품고 있습니다. `soul.md`의 "DNA 유전"이 추상이 아니라 실제로 작동했음을 보여주는 worked instance입니다. `workflow-generator`로 설계하고 `workflow-executor`로 실행한 **키움 REST 기반 주식 스크리너**가 그것이며, 산출 제품은 별도 저장소(`kiwoom-rest-trader`)에 배포되었습니다. 이 저장소의 `prompt/`는 그 제품을 만든 **공장이자 비행기록장치(flight recorder)**이지 제품 자체가 아닙니다.

| 구성 요소 | 위치 | 내용 |
|----------|------|------|
| 실행 스펙 | `prompt/workflow.md` | 실행된 12단계 워크플로우 (855줄) |
| SOT | `prompt/.claude/state.yaml` | `current_step:12`, `status:completed_degraded`, `translation_tasks`, `outputs`(EN+KO), autopilot 결정 로그 |
| 실행자 | `workflow-executor` 스킬 | SOT 단독 쓰기, 16-에이전트 디스패치, 4계층 게이트, F-1~F-14 폴백, Step 12 hard-block |
| 값-동등성 코드젠 | `prompt/.claude/codegen/` (6모듈) | `infra_schema.py`(빌드 SOT) → 결정론적 생성·검증, `param_ast`/`validate_param_values`로 87개 Final 상수 무할루시네이션 검증 ("code doesn't lie") |
| 검증 | `tests/`(64) + `prompt/.claude/tests/`(55) | 제품 pytest L1 **119 테스트** (프레임워크 Safety Hook 131 테스트와 별도) |
| 제품 문서 | `docs/*.md` | code-convention / code-quality-guide / architectural-decision-records(제품 ADR 14개) |

> **현재 상태(2026-05-31)**: Step 11까지 기능적으로 완료(`completed_degraded`)되었으나 **Step 12 사람 최종 검수는 Autopilot 자동승인으로 대체되어 실제 수행되지 않았습니다.** 빌드 자체의 설계 결정은 루트 `DECISION-LOG.md` ADR-052~056에 기록되어 있습니다.

## 절대 기준

이 프로젝트의 모든 설계·구현 의사결정에 적용되는 최상위 규칙:

1. **품질 최우선** — 속도, 비용, 작업량보다 최종 결과물의 품질이 유일한 기준
2. **단일 파일 SOT** — Single Source of Truth + 계층적 메모리 구조로 데이터 일관성 보장
3. **코드 변경 프로토콜 (CCP)** — 코드 변경 전 의도 파악 → 영향 범위 분석 → 변경 설계 3단계 수행. 분석 깊이는 변경 규모에 비례. **코딩 기준점(CAP-1~4)**: 코딩 전 사고, 단순성 우선, 목표 기반 실행, 외과적 변경
4. **품질 > SOT, CCP** — 세 기준이 충돌하면 품질이 우선. SOT와 CCP는 수단이지 목적이 아님

## 이론적 기반

`coding-resource/recursive language models.pdf` — 장기기억(long-term memory) 구현에 필수적인 이론을 담은 논문입니다. 에이전트가 세션을 넘어 지식을 축적하고 활용하는 메커니즘의 이론적 토대입니다.

## AI 도구 호환성

이 프로젝트는 **Hub-and-Spoke 패턴**으로 모든 AI CLI 도구에서 동일한 방법론이 자동 적용됩니다.

**Hub (방법론 SOT):**

| 파일 | 역할 |
|------|------|
| `AGENTS.md` | 모든 AI 도구 공통 — 절대 기준, 설계 원칙, 워크플로우 구조 정의 |

**Spoke (도구별 확장):**

| AI CLI 도구 | 시스템 프롬프트 파일 | 자동 적용 |
|------------|-------------------|----------|
| Claude Code | `CLAUDE.md` | Yes |
| Gemini CLI | `GEMINI.md` + `.gemini/settings.json` | Yes |
| Codex CLI | `AGENTS.md` (직접 읽음) | Yes |
| Copilot CLI | `.github/copilot-instructions.md` | Yes |
| Cursor | `.cursor/rules/agenticworkflow.mdc` | Yes |

모든 Spoke 파일의 절대 기준과 설계 원칙은 `AGENTS.md`와 동일합니다. 차이는 도구별 구현 매핑의 구체성뿐입니다.

## 문서 읽기 순서

| 순서 | 문서 | 목적 |
|------|------|------|
| 1 | **README.md** (이 파일) | 프로젝트 개요 파악 |
| 1.5 | [`soul.md`](soul.md) | 프로젝트 영혼 — 규칙 아래의 이유, DNA 유전 철학 |
| 2 | [`AGENTICWORKFLOW-ARCHITECTURE-AND-PHILOSOPHY.md`](AGENTICWORKFLOW-ARCHITECTURE-AND-PHILOSOPHY.md) | 설계 철학과 아키텍처 이해 |
| 2.5 | [`DECISION-LOG.md`](DECISION-LOG.md) | 모든 설계 결정의 맥락과 근거 추적 (ADR) |
| 3 | [`AGENTICWORKFLOW-USER-MANUAL.md`](AGENTICWORKFLOW-USER-MANUAL.md) | 실제 사용법 학습 |
| 4 | `AGENTS.md` / `CLAUDE.md` | 사용하는 AI 도구에 맞는 지시서 참조 |
| 5 | `docs/protocols/*.md` | 특정 주제(Autopilot·ULW·품질 게이트·CCP·Context Preservation) 심화 |

> 이 코드베이스로 만든 개별 프로젝트의 사용법과 혼동하지 마세요.
> 개별 프로젝트의 매뉴얼은 해당 프로젝트 내에 별도로 존재합니다.
