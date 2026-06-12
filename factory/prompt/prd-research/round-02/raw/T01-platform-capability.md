---
round: 2
type: raw
teammate: platform-capability-researcher
axis: platform-capability
investigation_axis: technology-theory
created: "2026-05-26T08:30:00+09:00"
question_summary: "Claude Code 플랫폼의 Hooks, Agent/Teammate, Skills, Commands, MCP 역량과 한계를 분석하여 주식 분석 시스템의 구현 가능 범위를 파악"
assumption_axis: "Maximum Utilization vs Limitation-Aware"
branch_a: "Maximum Utilization (플랫폼 최대 활용)"
branch_b: "Limitation-Aware (한계 인식 관점)"
web_search_count: 16
local_execution_tags:
  LOCAL_OK: ["Hooks system", "Agent/Teammate", "Skills", "Commands", "Slash commands", "DuckDB access", "Python execution", "Permission model", "Context snapshots"]
  LOCAL_PARTIAL: ["MCP (pykrx network)", "pykrx data collection"]
  LOCAL_BLOCKED: []
sources:
  - "Hooks reference — Claude Code Docs (code.claude.com/docs/en/hooks)"
  - "Claude Code Agent Teams: Setup & Usage Guide 2026 (claudefa.st)"
  - "Run agents in parallel — Claude Code Docs"
  - "Connect Claude Code to tools via MCP — Claude Code Docs"
  - "GitHub — sharebook-kr/pykrx-mcp"
  - "GitHub — duckdb/duckdb-skills"
  - "Claude Code Compaction: How Context Compression Works (okhlopkov.com)"
  - "Models, usage, and limits in Claude Code (support.claude.com)"
  - "Claude Code Pricing 2026 (verdent.ai)"
  - "Claude Code Rate Limits & Usage Quotas Explained (truefoundry.com)"
  - "Claude Agent SDK Credit Explained (techsy.io)"
  - "Anthropic's June 15 Billing Change (codersera.com)"
  - "Configure the sandboxed Bash tool — Claude Code Docs"
  - "Claude Code Permissions (claudedirectory.org)"
  - "Run parallel sessions with worktrees — Claude Code Docs"
  - "Best Claude Code Skills in 2026 (toolradar.com)"
---

# T01: Platform Capability Researcher — Investigation Report

## Executive Summary

Claude Code는 주식 분석 시스템 오케스트레이션의 **90%+를 네이티브 기능으로 구현 가능**하다. 핵심 갭 3가지: (1) 자체 스케줄링 불가 → launchd 필요, (2) 컨텍스트 윈도우에 원시 데이터 수용 불가 → summary-first 아키텍처 필수, (3) 컴팩션 시 분석 맥락 소실 → context preservation hooks 필요.

---

## Branch 1.1: Maximum Utilization — Findings

### 1. Claude Code Platform Features (Current State, 2025-2026)

**Hooks System** [LOCAL-OK]

9개 생명주기 이벤트 지원:

| Event | Cadence | Matchers | Key Use |
|-------|---------|----------|---------|
| Setup | Once/session | init, maintenance | Infrastructure validation |
| SessionStart | Once/session | clear, compact, resume | Context restoration |
| UserPromptSubmit | Once/turn | Any | Prompt validation |
| PreToolUse | Every tool call | Tool name | Block/modify tool calls |
| PostToolUse | Every tool call | Tool name | Audit, filter outputs |
| Stop | Once/turn | None | Summary/snapshot |
| StopFailure | Once/turn | None | Error handling |
| PreCompact | On compaction | None | Pre-compression save |
| SessionEnd | Once/session | clear | Final state save |

4종 핸들러: command (스크립트 실행), http (웹 서버 호출), prompt (텍스트 주입), agent (서브에이전트 위임). 기본 타임아웃: 30초(prompt), 60초(agent). exit 0=진행, exit 2=차단.

**Agent/Teammate System** [LOCAL-OK]

- **Sub-agents (TaskCreate/SendMessage)**: 컨텍스트 격리. 부모 오염 없음. 병렬 실행 가능 (API rate limit 범위 내). `isolation: worktree` 지원.
- **Agent Teams (실험적, 2026.2~)**: 2-16개 에이전트, 공유 코드베이스. `CLAUDE_AGENT_TEAMS=1` 필요. 각 에이전트 독립 worktree/branch/context.

**Skills** [LOCAL-OK]

`.claude/skills/<name>/SKILL.md`로 정의. 의도 감지 시 자동 호출 또는 `/name`으로 수동 호출. 다단계 워크플로우 오케스트레이션 가능. references/ 디렉토리로 구조화된 지식 참조.

**Commands** [LOCAL-OK]

`.claude/commands/` 또는 `~/.claude/commands/`에 Markdown 파일. 파일명 = 슬래시 명령어. `/scan`, `/종목분석` 구현 용이.

**MCP (Model Context Protocol)** [LOCAL-PARTIAL]

- Deferred-loaded tools (컨텍스트 소비 최소화)
- pykrx-mcp (sharebook-kr): KOSPI/KOSDAQ 자연어 데이터 접근
- DuckDB skills plugin: 쿼리, 스키마 탐색, state.sql 영속성
- 50+ 공식 서버, 150+ 커뮤니티 서버

### 2. Tool Calling & Function Calling Paradigm

**Built-in Tools** [LOCAL-OK]

Bash, Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, TaskCreate/SendMessage, TeamCreate, NotebookEdit, Monitor.

**Permission Model** [LOCAL-OK]

3-tier: allow (자동 승인) / deny (항상 차단) / ask (사용자 확인). 4 레이어 병합: Enterprise > User > Project > Project-local. 상위 deny는 하위 allow로 재정의 불가.

**Python Script Execution** [LOCAL-OK]

- Bash tool: `python3 script.py` — 파일시스템/네트워크 전체 접근
- Hooks: command 핸들러로 Python 스크립트 호출. JSON stdin/stdout.

### 3. Stock System-Specific Capabilities

**Hooks → 파이프라인 자동 트리거**: SessionStart hook에서 데이터 신선도 확인 → 스캔 필요 시 알림. [LOCAL-OK]

**Agent/Teammate → 분석 병렬화**: 섹터별 서브에이전트 분석 가능. 단, 2,500종목 사전 계산된 점수가 DuckDB에 있으면 병렬화 불필요. **해석 병렬화**(모멘텀/가치/리스크 관점)에 더 유용. [LOCAL-OK]

**Skills → 점수 방법론 캡슐화**: `.claude/skills/stock-scanner/SKILL.md`에 6개 서브스코어 루브릭, 지표 정의, 예시 분석 포함 가능. [LOCAL-OK]

**Commands → /scan, /종목분석 인터페이스**: `/scan` → 파이프라인 실행 + summary.md 읽기 + 한국어 분석. `/종목분석 삼성전자` → DuckDB 개별 종목 쿼리. [LOCAL-OK]

**MCP → 배치 파이프라인에 중복**: 파이프라인이 이미 Python으로 수집/분석. pykrx-mcp는 대화형 ad-hoc 쿼리에만 유용. DuckDB plugin이 더 가치 있음. [LOCAL-PARTIAL]

### 4. Sandboxing & Permission Model

**파일시스템 접근**: 기본 전체 읽기, 프로젝트 디렉토리 쓰기. DuckDB 파일 읽기/쓰기 가능. [LOCAL-OK]

**금융 데이터 보안**: 공개 KRX 데이터이므로 보안 우려 최소. output_secret_filter.py(25+ 패턴), security_sensitive_file_guard.py(12 패턴) 기존 Hook 활용. [LOCAL-OK]

### Branch 1.1 Conclusion

플랫폼 기능 활용률 ~85%:
- Hooks: 9개 중 7개 유용 (UserPromptSubmit, StopFailure 제외)
- Skills: 점수 방법론 캡슐화에 필수
- Commands: 사용자 인터페이스에 필수
- MCP: 선택적 (DuckDB plugin 가치, pykrx-mcp 중복)
- Agent Teams: 과잉 (서브에이전트로 충분)
- Worktrees: 불필요

---

## Branch 1.2: Limitation-Aware — Findings

### 1. Context Window Limitations

- **윈도우 크기**: Max 플랜 1M 토큰
- **2,500종목 원시 데이터**: ~1.875M 토큰 — 윈도우 초과
- **Top-50 summary.md**: ~5,000-10,000 토큰 — 무난
- **컴팩션**: ~95% 용량에서 자동 트리거. 60-70% 해제하나 과거 결정/규약 소실
- **CLAUDE.md**: 컴팩션 생존 (시스템 프롬프트)

**핵심 함의**: summary-first 아키텍처는 최적화가 아니라 **아키텍처적 필수**. [LOCAL-OK]

### 2. Token/Subscription Limitations

| Plan | 월가 | 5시간 토큰 윈도우 |
|------|------|-----------------|
| Max 20x | $200 | ~220,000 토큰 |

일일 스캔 ~20,000-30,000 토큰 → 윈도우의 ~10-15% → 여유 충분. [LOCAL-OK]

Agent SDK Credit (2026.6.15 이후): Max 20x → $200/월. 일일 스캔 ~25K 토큰 × 30일 = 750K 토큰/월 → API 가격 기준 **~$1.50/월** → 예산 내. [LOCAL-OK]

### 3. Hooks System Limitations

- **미지원 이벤트**: OnTimer, OnSchedule, OnFileChange, OnError, OnNetworkRequest
- **타임아웃**: 기본 30초 (pykrx 수집 2-5분에 부족)
- **동기 실행**: 느린 Hook이 Claude 턴 차단 (async: true로 완화)
- **Hook 체인**: 직접 트리거 불가. 파일 기반 간접 전달만 가능.
- **패키지 설치**: Hook 스크립트 런타임에 패키지 설치 불가

### 4. State Management Limitations

- **세션 영속성 없음**: 모든 상태 파일 기반
- **DuckDB 접근**: 단일 작성자/다중 판독자 MVCC. 동시 쓰기 불가.
- **스냅샷**: 텍스트 기반 요약 (전체 대화 재생 아님)

### 5. Workaround Strategies

**컨텍스트 소진 → summary-first**: Python 전체 계산 → summary.md(< 10K 토큰) → Claude 읽기. 비용: 제로. [LOCAL-OK]

**토큰 한도 → 모델 계층화**: 루틴 스캔 = Sonnet, 심층 분석 = Opus. [LOCAL-OK]

**Hook 한계 → 하이브리드 아키텍처**: launchd(스케줄링) + Python(파이프라인) + Hooks(세션 자동화). [LOCAL-OK]

**상태 → DuckDB as SOT**: 모든 데이터/점수/이력 DuckDB. 세션 메모리는 context-snapshots/. [LOCAL-OK]

### Branch 1.2 Conclusion: Top 3 Show-Stopping Limitations

1. **자체 스케줄링 불가** (심각도: HIGH, 완화 비용: LOW) — launchd plist ~20줄로 해결. 잔여 위험: 없음.
2. **원시 데이터 컨텍스트 수용 불가** (심각도: CRITICAL, 완화 비용: ZERO) — summary-first 아키텍처가 기본 설계.
3. **컴팩션 시 분석 맥락 소실** (심각도: MEDIUM, 완화 비용: LOW) — 기존 PreCompact/SessionStart hooks + DuckDB 점수 영속.

---

## Branch 1.1 vs 1.2 Synthesis

### Platform Capability Verdict

| Layer | Technology | Claude Code Role | Tag |
|-------|-----------|-----------------|-----|
| Data Collection | pykrx + launchd | None (외부) | [LOCAL-PARTIAL] |
| Storage | DuckDB | Read via Bash/plugin | [LOCAL-OK] |
| Scoring | pandas-ta + Python | Execute via Bash | [LOCAL-OK] |
| Summarization | Python → summary.md | Read output | [LOCAL-OK] |
| Interpretation | Claude (Opus/Sonnet) | Core value-add | [LOCAL-OK] |
| UI | Slash commands | /scan, /종목분석 | [LOCAL-OK] |
| Session Continuity | Hooks + DuckDB | Context preservation | [LOCAL-OK] |
| Scheduling | launchd | External | [LOCAL-OK] |

**핵심 원칙**: Python = 모든 계산 + 데이터. Claude = 모든 해석 + 사용자 상호작용. 경계 = summary.md.

### Parking Lot

1. pykrx-mcp vs 직접 Python 호출: 배치에 중복, ad-hoc에 유용
2. Agent SDK Credit 활성화: 2026.6.15 이후 일회성 계정 설정 필요
3. DuckDB 동시 접근: launchd 수집 중 Claude 읽기 시 write lock 일시 차단 → 원자적 파일 교체로 완화
4. 컴팩션 타이밍: /분석완료 명령어로 상태 저장 + 컴팩트
5. 모델 자동 선택: claude --model sonnet/opus 프로그래밍 전환 가능 여부 조사 필요
6. 한국어 금융 용어 정확도: 스킬 참조 파일에 용어 사전 필요 여부
