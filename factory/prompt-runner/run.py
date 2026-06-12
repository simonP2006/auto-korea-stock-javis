#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  run.py — Claude Code 프롬프트 순차 자동 실행기 (최종판)
  
  방식: pipe 모드 (-p) + 세션 ID 캡처 (--resume)
  
  작동 원리:
    1. 세션의 첫 프롬프트: claude -p --output-format stream-json --verbose < prompt.txt
       → JSON 응답에서 session_id 추출하여 저장
    2. 같은 세션의 후속 프롬프트: claude -p --resume $session_id < prompt.txt
       → 정확히 해당 세션을 이어서 실행
    3. /clear를 만나면: session_id를 버림
       → 다음 프롬프트에서 새 세션 시작, 새 session_id 캡처
    4. 프로세스 종료 = 작업 완료 (100% 결정론적)
  
  사용법:
    python3 run.py                    # 전체 실행 (1번부터)
    python3 run.py --resume           # 중단 지점부터 재개
    python3 run.py --from 34          # 34번부터 시작 (새 세션)
    python3 run.py --dry-run          # 실행 없이 순서 확인
    python3 run.py --verify           # 프롬프트 파일 무결성 검증
    
  환경 변수:
    MAX_TURNS=0           에이전트 최대 턴 수 (0 = 무제한)
    TIMEOUT=0             프롬프트당 최대 실행 시간 (0 = 무제한)
    SKIP_PERMISSIONS=1    권한 확인 건너뛰기
═══════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import signal
import hashlib
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════
#  상수 정의 — 변경 불가
# ═══════════════════════════════════════════════════════════════

TOTAL_PROMPTS = 110

# /clear 위치: 이 번호에서는 세션을 종료하고, 다음 번호에서 새 세션 시작
CLEAR_POSITIONS = frozenset({3, 6, 9, 12, 14, 17, 20, 23, 26, 29, 33, 36, 39, 42, 47, 50, 53, 58, 61, 64, 67, 70, 73, 76, 79, 82, 85, 88, 91, 95, 98, 101, 104, 107, 110})

# 각 /clear 직후의 번호 = 새 세션 시작점
# 1번도 포함 (최초 시작)
NEW_SESSION_STARTS = frozenset({1, 4, 7, 10, 13, 15, 18, 21, 24, 27, 30, 34, 37, 40, 43, 48, 51, 54, 59, 62, 65, 68, 71, 74, 77, 80, 83, 86, 89, 92, 96, 99, 102, 105, 108})


# ═══════════════════════════════════════════════════════════════
#  최고 성능 모델 자동 선택
# ═══════════════════════════════════════════════════════════════

# 모델 우선순위: 높은 숫자 = 더 최신·고성능
# 새 모델 출시 시 이 목록에 추가하면 자동 선택됨
_MODEL_PRIORITY: list[tuple[int, str]] = [
    (1000, "claude-opus-4-6"),          # 최우선: opus 4.6
    (990,  "claude-opus-4-5"),          # opus 4.5
    (980,  "claude-opus-4-0"),          # opus 4.0
    (970,  "claude-opus-4"),            # opus 4 (별칭)
    (500,  "claude-sonnet-4-6"),        # sonnet 4.6 (fallback)
    (490,  "claude-sonnet-4-5"),        # sonnet 4.5 (fallback)
]

# Extended thinking (max effort) 토큰 예산 — 최대값으로 고정
THINKING_BUDGET_TOKENS = 16000   # Claude Opus의 extended thinking 최대


def _resolve_best_model() -> str:
    """
    Anthropic API에서 사용 가능한 모델 목록을 조회하여
    _MODEL_PRIORITY 기준으로 가장 우선순위 높은 모델을 반환합니다.

    API 조회 실패 시 _MODEL_PRIORITY의 최상위 모델로 fallback.
    """
    import urllib.request
    import urllib.error

    fallback = _MODEL_PRIORITY[0][1]  # 목록 최상위

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.warning("ANTHROPIC_API_KEY 미설정 — 모델 자동 조회 불가, fallback: " + fallback)
        return fallback

    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        available = {m["id"] for m in data.get("data", [])}
    except Exception as e:
        log.warning(f"모델 목록 조회 실패 ({e}) — fallback: {fallback}")
        return fallback

    # 우선순위 순서로 사용 가능한 첫 번째 모델 반환
    for _, model_id in sorted(_MODEL_PRIORITY, key=lambda x: x[0], reverse=True):
        if model_id in available:
            return model_id

    log.warning(f"우선순위 목록에서 사용 가능한 모델 없음 — fallback: {fallback}")
    return fallback


# 프로세스 시작 시 한 번만 조회 (모든 110단계에서 동일 모델 사용)
_BEST_MODEL: str | None = None


def get_best_model() -> str:
    """캐싱된 최고 성능 모델 ID를 반환합니다."""
    global _BEST_MODEL
    if _BEST_MODEL is None:
        _BEST_MODEL = _resolve_best_model()
        log.info(f"✦ 선택된 모델: {_BEST_MODEL} (thinking: {THINKING_BUDGET_TOKENS:,} tokens)")
    return _BEST_MODEL

# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent.resolve()
PROMPTS_DIR = SCRIPT_DIR / "prompts"
LOGS_DIR = SCRIPT_DIR / "logs"
STATE_FILE = SCRIPT_DIR / "state.json"


# ═══════════════════════════════════════════════════════════════
#  로깅
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('runner')

# 파일 로그도 추가
file_handler = logging.FileHandler(SCRIPT_DIR / "execution.log", encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s │ %(levelname)s │ %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
))
log.addHandler(file_handler)


# ═══════════════════════════════════════════════════════════════
#  상태 관리 (state.json)
# ═══════════════════════════════════════════════════════════════

def state_init() -> dict:
    """새 상태 생성"""
    s = {
        "total": TOTAL_PROMPTS,
        "current_step": 1,
        "current_session_id": None,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed": [],
        "clears": [],
        "failed": [],
        "sessions": {},  # {session_id: [step1, step2, ...]}
    }
    _state_save(s)
    return s


def state_load() -> dict:
    """기존 상태 로드"""
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _state_save(s: dict):
    """상태 저장"""
    s["last_updated"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(s, f, indent=2, ensure_ascii=False)


def state_record_complete(s: dict, step: int):
    s["completed"].append(step)
    s["current_step"] = step + 1
    # 세션 기록
    sid = s.get("current_session_id")
    if sid:
        s["sessions"].setdefault(sid, []).append(step)
    _state_save(s)


def state_record_clear(s: dict, step: int):
    s["clears"].append(step)
    s["current_session_id"] = None  # 세션 ID 해제
    s["current_step"] = step + 1
    _state_save(s)


def state_update_session_id(s: dict, session_id: str):
    s["current_session_id"] = session_id
    _state_save(s)


def state_record_fail(s: dict, step: int):
    s["failed"].append(step)
    _state_save(s)


def state_finish(s: dict):
    s["status"] = "done"
    s["finished_at"] = datetime.now().isoformat()
    _state_save(s)



# ═══════════════════════════════════════════════════════════════
#  3겹 검증 시스템
# ═══════════════════════════════════════════════════════════════

# ─── 1겹: 조용한 실패 키워드 ───
# 주의: rate limit 관련은 여기에 넣지 않음 (run_with_retry에서 자동 재시도)
SILENT_FAILURE_KEYWORDS = [
    # 컨텍스트 초과
    "context window",
    "context_window_overflow",
    "token limit",
    "conversation is too long",
    "too many tokens",
    # Claude Code 실제 오류 패턴
    "error_during_tool",
    "i was interrupted",
    "i'm sorry, i can't",
    "i cannot continue",
    "task was interrupted",
    "aborted",
    "failed to complete",
    "could not complete",
    "unable to complete",
]

# ─── 세션 만료 감지 키워드 ───
# --resume $session_id 사용 시 세션이 만료/삭제된 경우 Claude Code가 출력하는 오류 패턴
# 이 패턴 감지 시 run_with_retry는 session_id=None으로 폴백해 새 세션을 시작한다
SESSION_EXPIRED_KEYWORDS = [
    "session not found",
    "no such session",
    "session does not exist",
    "invalid session",
    "session expired",
    "session.*not.*exist",
    "unknown session",
    "cannot resume",
    "resume failed",
]

# ─── 대화형 프롬프트 자동 응답 패턴 ───
# 이 패턴이 출력에 감지되면 stdin으로 "1\n"을 자동 전송 (1번/Yes 자동 선택)
AUTO_RESPOND_PATTERNS = [
    # ── 영어 패턴 ──
    "do you want to proceed",
    "would you like to proceed",
    "proceed? (y/n)",
    "proceed (y/n)",
    "1. yes",
    "1) yes",
    "1: yes",
    "enter your choice",
    "select an option",
    "select option",
    "would you like to",
    "press enter to continue",
    "type 'yes' to confirm",
    "confirm? (y/n)",
    "(y/n):",
    "[y/n]",
    "continue? [y",
    # ── 한국어 패턴 ──
    "진행하시겠습니까",
    "진행 하시겠습니까",
    "계속하시겠습니까",
    "계속 하시겠습니까",
    "실행하시겠습니까",
    "승인하시겠습니까",
    "진행할까요",
    "계속할까요",
    "1. 예",
    "1) 예",
    "예 (yes)",
    "예(yes)",
]


# ─── 2겹: 파일 변화 감지 ───
def snapshot_project_files(project_dir: Path = None) -> dict:
    """
    프로젝트 폴더의 파일 상태를 스냅샷합니다.
    
    Returns: {filepath: (size, mtime)} 딕셔너리
    """
    if project_dir is None:
        project_dir = Path.cwd()
    
    snapshot = {}
    skip_dirs = {'.git', 'node_modules', '.venv', '__pycache__', 'prompt-runner'}
    
    try:
        for item in project_dir.rglob('*'):
            # 스킵할 디렉토리
            if any(skip in item.parts for skip in skip_dirs):
                continue
            if item.is_file():
                try:
                    stat = item.stat()
                    snapshot[str(item.relative_to(project_dir))] = (stat.st_size, stat.st_mtime)
                except (OSError, ValueError):
                    pass
    except Exception:
        pass
    
    return snapshot


def diff_snapshots(before: dict, after: dict) -> dict:
    """
    두 스냅샷을 비교하여 변경 사항을 반환합니다.
    
    Returns: {
        "created": [새로 생긴 파일들],
        "modified": [수정된 파일들],
        "deleted": [삭제된 파일들],
        "total_changes": 총 변경 수
    }
    """
    before_keys = set(before.keys())
    after_keys = set(after.keys())
    
    created = sorted(after_keys - before_keys)
    deleted = sorted(before_keys - after_keys)
    
    modified = []
    for f in before_keys & after_keys:
        if before[f] != after[f]:
            modified.append(f)
    modified.sort()
    
    return {
        "created": created,
        "modified": modified,
        "deleted": deleted,
        "total_changes": len(created) + len(modified) + len(deleted),
    }


# ═══════════════════════════════════════════════════════════════
#  강제 완료 보고 템플릿 주입
# ═══════════════════════════════════════════════════════════════

COMPLETION_REPORT_TEMPLATE = """

---
[MANDATORY COMPLETION REPORT - DO NOT SKIP - THIS IS REQUIRED]

Before finishing this step, you MUST write a completion report using EXACTLY this format.
This report is used to monitor quality, detect hallucination, and improve the automation pipeline.
Be brutally honest. Do not inflate or soften results.

## 📋 STEP COMPLETION REPORT

### 1. INSTRUCTIONS RECEIVED
(Summarize the key instructions from this prompt in 3-5 bullet points)
- 
- 
- 

### 2. FEATURES / TOOLS USED
(List every Claude Code feature you actually invoked. If you did NOT use something, write ✗)
- agent-teams / teammate: [✓ used N teammates / ✗ not used — reason: ]
- Agent Swarm / orchestrator: [✓ / ✗ — reason: ]
- Sub-agents: [✓ N sub-agents spawned / ✗]
- Task Management System: [✓ / ✗]
- fork: [✓ / ✗]
- hooks: [✓ / ✗]
- commands: [✓ / ✗]
- skills: [✓ / ✗]
- Task verification / TDD: [✓ / ✗]
- Web search / fetch: [✓ / ✗]
- Source of Truth (SOT): [✓ implemented / ✗ not implemented]

### 3. DELIVERABLES PRODUCED
(List every file created, modified, or deleted with their paths)
CREATED:
- 
MODIFIED:
- 
DELETED:
- 

### 4. OBJECTIVE COMPLETION ASSESSMENT
(Rate each instruction from section 1 as: ✅ DONE / ⚠ PARTIAL / ❌ NOT DONE)
Rate the overall completion: ___% complete

Explain what was NOT completed and why (be specific, not vague):


### 5. HONESTY FLAGS
(Answer yes/no + explanation for each)
- Did you skip any instruction because it was too complex? [YES/NO]:
- Did you make assumptions without explicit confirmation? [YES/NO]:
- Did you produce placeholder/stub code instead of real implementation? [YES/NO]:
- Did you hallucinate file contents you did not actually verify? [YES/NO]:
- Did you run out of turns before completing the task? [YES/NO]:
- Is there anything the next step needs to know about the current state? [YES/NO]:

### 6. NEXT STEP RISK
(What could go wrong in the next prompt if this step's output is incomplete?)


---
[END OF MANDATORY COMPLETION REPORT]
"""


MAX_EFFORT_INSTRUCTION = """[MANDATORY SYSTEM RULES - ALWAYS FOLLOW THESE BEFORE ANYTHING ELSE]

## Rule 1: Maximum Thinking
Use maximum extended thinking. Think deeply, exhaustively, and step-by-step before every action and response. Do not take shortcuts. Do not skip steps. Pursue the highest possible quality.

## Rule 2: WebFetch / Network Hang Prevention (CRITICAL)
WebFetch and external HTTP requests can silently hang forever, blocking you and all parent agents.
You MUST follow these rules for every WebFetch or web request:

1. **30-second mental timeout**: If a WebFetch has not returned within what feels like 30 seconds, assume it has hung. Do NOT wait longer.
2. **Never block on a single URL**: If WebFetch on one URL hangs or fails, immediately move on. Use WebSearch results you already have, or try a different source.
3. **Prefer these sources** (more reliable, less likely to hang):
   - Official documentation sites (docs.*, *.readthedocs.io, developer.*)
   - GitHub (github.com, raw.githubusercontent.com)
   - Wikipedia, MDN, Stack Overflow
   - Avoid: personal blogs, unknown CDNs, self-hosted sites
4. **Parallel tool calls**: If you call WebFetch and WebSearch in parallel and WebSearch returns first, DO NOT wait for WebFetch. Proceed with WebSearch results immediately. A partial result is better than a deadlock.
5. **On any network failure**: Log the failure, record the URL as unreachable, and continue with available information. Never retry a hanging URL more than once.
6. **If you are a sub-agent**: Treat any unresponsive tool call as a timeout after one attempt. Return your partial results to the parent agent immediately rather than waiting indefinitely.

## Rule 3: Anti-Deadlock
If you spawn sub-agents (teammates/Task), each sub-agent MUST return a result within a reasonable time even if some of their tool calls fail. Sub-agents should never block the parent indefinitely.

---
"""


def build_augmented_prompt(prompt_file: Path) -> str:
    """
    원본 프롬프트 끝에 강제 완료 보고 템플릿을 붙여서 반환합니다.
    /clear 프롬프트에는 주입하지 않습니다.
    """
    content = prompt_file.read_text(encoding='utf-8')
    if content.strip() == "/clear":
        return content
    return MAX_EFFORT_INSTRUCTION + content + COMPLETION_REPORT_TEMPLATE


def _save_completion_report(step: int, logs_dir: Path) -> None:
    """
    {step:03d}.stream.jsonl에서 content_block_delta 텍스트를 연결하여
    완전한 텍스트를 재구성한 뒤 STEP COMPLETION REPORT 섹션을 추출합니다.

    핵심 문제: .log 파일은 display_text 청크마다 '\\n'을 붙여 저장하므로
    마커 문자열이 청크 경계에서 쪼개지면 검색에 실패합니다.
    → .stream.jsonl에서 content_block_delta 텍스트를 \\n 없이 연결하면
      원본 그대로의 완전한 텍스트가 복원됩니다.
    """
    report_file = logs_dir / f"{step:03d}.report.md"
    stream_file = logs_dir / f"{step:03d}.stream.jsonl"

    combined = ""

    # stream.jsonl에서 모든 텍스트 델타를 \n 없이 연결 → 단편화 해소
    if stream_file.exists():
        parts: list[str] = []
        try:
            for raw in stream_file.read_text(encoding='utf-8').splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                    msg_type = obj.get("type", "")

                    if msg_type == "content_block_delta":
                        # 스트리밍 텍스트 청크 — \n 없이 그대로 이어붙임
                        delta = obj.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            parts.append(text)

                    elif msg_type == "assistant":
                        # 비스트리밍 전체 메시지
                        msg = obj.get("message", {})
                        if isinstance(msg, dict):
                            text = msg.get("text", "")
                        elif isinstance(msg, str):
                            text = msg
                        else:
                            text = ""
                        if text:
                            parts.append(text)

                    elif msg_type == "result":
                        # 최종 요약 — 구분을 위해 줄바꿈 포함
                        t = obj.get("result", "")
                        if t:
                            parts.append("\n" + t)

                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        combined = "".join(parts)

    # stream.jsonl가 없거나 비어 있으면 .log 파일로 fallback
    if not combined:
        log_file = logs_dir / f"{step:03d}.log"
        if log_file.exists():
            try:
                combined = log_file.read_text(encoding='utf-8')
            except Exception:
                combined = ""

    report_marker = "## 📋 STEP COMPLETION REPORT"
    end_marker    = "[END OF MANDATORY COMPLETION REPORT]"

    if report_marker not in combined:
        report_file.write_text(
            f"# Step {step:03d} — 완료 보고서 없음\n\n"
            f"> ⚠ Claude가 MANDATORY COMPLETION REPORT 지시를 무시했습니다.\n\n"
            f"## 원시 결과 (일부)\n```\n{combined[:1000]}\n```\n",
            encoding='utf-8',
        )
        return

    start = combined.index(report_marker)
    end   = combined.find(end_marker)
    body  = combined[start:end].strip() if end > 0 else combined[start:].strip()

    report_file.write_text(
        f"# Step {step:03d} — COMPLETION REPORT\n\n{body}\n",
        encoding='utf-8',
    )
    log.info(f"[{step:03d}] 완료 보고서 저장: {report_file.name}")


# ═══════════════════════════════════════════════════════════════
#  핵심: 단일 프롬프트 실행
# ═══════════════════════════════════════════════════════════════

def run_single_prompt(
    step: int,
    prompt_file: Path,
    session_id: str = None,
    max_turns: int = 0,
    timeout: int = 0,
    skip_permissions: bool = False,
    project_dir: Path = None,
    model: str = None,
    idle_timeout: int = 0,
) -> tuple:  # (verdict: str, session_id: str, duration: int)
    """
    단일 프롬프트를 실행합니다.
    --output-format stream-json으로 실시간 스트리밍합니다.
    
    stream-json은 줄 단위 JSON을 실시간으로 출력합니다:
      {"type":"assistant","message":{"type":"text","text":"..."}}
      {"type":"result","session_id":"...","cost_usd":...}
    """
    
    import threading
    
    # ─── stdin 쓰기 락 — write_stdin 스레드와 process_stream 스레드 간 동시 접근 방지 ───
    stdin_lock = threading.Lock()
    
    # ─── 명령 구성 ───
    cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose"]
    
    if session_id:
        # 특정 세션 ID로 이어받기 — bare --continue 금지
        # (bare --continue는 시스템 최근 세션을 이어받아 무관한 세션에 진입할 수 있음)
        cmd.extend(["--resume", session_id])
    
    # ── max-turns: 0이면 무제한 (될 때까지 실행) ──
    if max_turns > 0:
        cmd.extend(["--max-turns", str(max_turns)])
    
    # ── 모델 강제: 항상 자동 선택된 최고 성능 모델 사용 ──
    effective_model = get_best_model()
    if model and model != effective_model:
        log.warning(f"[{step:03d}] --model '{model}' 무시 → 자동 선택 모델 '{effective_model}' 강제 사용")
    cmd.extend(["--model", effective_model])
    
    # ── Extended thinking (max effort): 환경변수로 활성화 ──
    # CLI 플래그 미지원 → 환경변수(CLAUDE_CODE_MAX_THINKING_TOKENS)로 전달
    
    # pipe 모드에서는 권한 확인 팝업에 응답할 수 없으므로 항상 활성화
    cmd.append("--dangerously-skip-permissions")
    
    # ─── 환경변수 (agent-teams 활성화 + max effort) ───
    env = os.environ.copy()
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
    # Extended thinking (max effort) — Claude Code가 인식하는 환경변수
    env["CLAUDE_CODE_MAX_THINKING_TOKENS"] = str(THINKING_BUDGET_TOKENS)
    env["ANTHROPIC_THINKING_BUDGET_TOKENS"] = str(THINKING_BUDGET_TOKENS)
    
    # ─── 로그 파일 ───
    log_file = LOGS_DIR / f"{step:03d}.log"
    log_raw_file = LOGS_DIR / f"{step:03d}.stream.jsonl"
    log_err_file = LOGS_DIR / f"{step:03d}.error.log"
    log_meta_file = LOGS_DIR / f"{step:03d}.meta.json"
    
    # ─── 상태 ───
    is_new = (session_id is None)
    mode_str = "새 세션" if is_new else "이어가기"
    start_time = time.time()
    is_running = True
    has_output = False
    result_session_id = None
    detected_failure_keyword = None  # 1겹 검증: 조용한 실패 키워드
    last_output_time = time.time()   # 워치독: 마지막 출력 시각
    stagnation_killed = False        # 워치독이 kill했는지 여부
    
    # idle_timeout: 파라미터 → 환경변수 → 기본값 1200초(20분) 순으로 적용
    STAGNATION_LIMIT = idle_timeout if idle_timeout > 0 else int(os.environ.get("IDLE_TIMEOUT", "7200"))
    
    # ─── 경과 시간 타이머 + 정체 워치독 ───
    def timer_loop():
        nonlocal stagnation_killed
        while is_running:
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            silent = int(time.time() - last_output_time)
            
            if has_output:
                status = f"📝 출력 중... (정체: {silent}s)"
            else:
                status = "⏳ 작업 중..."
            
            print(f"\r  ⏱ [{step:03d}/{TOTAL_PROMPTS}] {mode_str} │ {mins:02d}:{secs:02d} │ {status}   ",
                  end='', flush=True)
            
            # 정체 감지: 출력이 한 번이라도 있었고, STAGNATION_LIMIT 초간 추가 출력 없음
            if has_output and silent >= STAGNATION_LIMIT and not stagnation_killed:
                stagnation_killed = True
                log.warning(f"\n[{step:03d}] ⏰ 정체 감지 — {STAGNATION_LIMIT//60}분간 출력 없음 (WebFetch hang 가능)")
                log.warning(f"[{step:03d}]   → 프로세스 강제 종료 후 재시도합니다")
                try:
                    proc.kill()
                except Exception:
                    pass
                break
            
            time.sleep(1)
    
    # ─── stream-json 파싱 + 실시간 표시 ───
    def process_stream(pipe, raw_f, text_f):
        nonlocal has_output, result_session_id, detected_failure_keyword, last_output_time
        
        for raw_bytes in pipe:
            # 바이너리 파이프에서 읽은 줄을 UTF-8 디코딩
            if isinstance(raw_bytes, bytes):
                raw_line = raw_bytes.decode('utf-8', errors='replace')
            else:
                raw_line = raw_bytes
            line = raw_line.strip()
            if not line:
                continue
            
            # 원본 JSONL 저장
            raw_f.write(line + '\n')
            raw_f.flush()
            
            # ─── 1겹 검증: 실시간 키워드 감지 ───
            line_lower = line.lower()
            for kw in SILENT_FAILURE_KEYWORDS:
                if kw in line_lower:
                    detected_failure_keyword = kw
                    break
            
            # ─── 대화형 프롬프트 자동 응답 (raw 줄 기준 선행 감지) ───
            # JSON 파싱 전에 raw 텍스트에서도 패턴 감지 (비-JSON 출력 대응)
            # auto_responded: 이 줄에서 이미 응답했으면 True → 2차 중복 전송 방지
            auto_responded = False
            if any(pat in line_lower for pat in AUTO_RESPOND_PATTERNS):
                try:
                    with stdin_lock:
                        if not proc.stdin.closed:
                            proc.stdin.write(b"1\n")
                            proc.stdin.flush()
                    auto_responded = True
                    auto_msg = "🤖 [자동 응답] 1 (Yes) — 대화형 프롬프트 감지"
                    print(f"\r{' ' * 80}\r  {auto_msg}", flush=True)
                    text_f.write(auto_msg + '\n')
                    text_f.flush()
                    last_output_time = time.time()
                    log.info(f"[{step:03d}] 자동 응답 전송: 1 (Yes) ← \"{line[:80]}\"")
                except Exception as e:
                    log.warning(f"[{step:03d}] 자동 응답 전송 실패: {e}")
            
            # JSON 파싱
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            msg_type = obj.get("type", "")
            
            # ─── 텍스트 출력 추출 ───
            display_text = None
            
            if msg_type == "assistant":
                # Claude의 응답 텍스트
                msg = obj.get("message", {})
                if isinstance(msg, dict):
                    display_text = msg.get("text", "")
                elif isinstance(msg, str):
                    display_text = msg
            
            elif msg_type == "content_block_delta":
                # 스트리밍 텍스트 청크 — 즉시 실시간 출력 (타이머 줄 지우고 바로 출력)
                delta = obj.get("delta", {})
                chunk = delta.get("text", "")
                if chunk:
                    has_output = True
                    last_output_time = time.time()
                    # 타이머 줄이 있으면 지우고 청크 직접 출력 (줄바꿈 없이 이어서)
                    print('\r' + ' ' * 80 + '\r', end='', flush=True)
                    print(chunk, end='', flush=True)
                    text_f.write(chunk)
                    text_f.flush()
                display_text = None  # 이미 출력했으므로 하단 출력 블럭 skip
            
            elif msg_type == "result":
                # 최종 결과 — session_id 캡처 + subtype 에러 감지
                result_session_id = obj.get("session_id")
                result_text = obj.get("result", "")
                subtype = obj.get("subtype", "")
                
                if subtype in ("error", "error_during_tool", "interrupted"):
                    # result 레벨 오류: 조용한 실패로 표시
                    if not detected_failure_keyword:
                        detected_failure_keyword = f"result.subtype={subtype}"
                    display_text = f"\n⚠ 결과 오류 ({subtype}): {result_text[:200]}\n"
                elif result_text:
                    # result 필드는 Claude Code가 자동 생성하는 짧은 요약문
                    # 보고서 본문은 스트리밍 청크(content_block_delta)에 있음
                    # 보고서 추출은 _save_completion_report()가 .stream.jsonl에서 수행
                    display_text = f"\n{'─'*40}\n📋 결과 요약:\n{result_text[:300]}\n{'─'*40}\n"
            
            elif msg_type == "tool_use":
                # 도구 사용 — 이름과 핵심 입력 표시
                tool_name = obj.get("name", obj.get("tool", ""))
                tool_input = obj.get("input", {})
                if tool_name:
                    if tool_name in ("Task", "task"):
                        # agent-teams Task 호출: 지시 내용 표시
                        task_desc = str(tool_input.get("description", tool_input.get("prompt", "")))[:80]
                        display_text = f"🤖 [Task → {task_desc}]"
                    else:
                        display_text = f"🔧 [{tool_name}]"
            
            elif msg_type == "tool_result":
                # 도구 결과 — 에러는 전체, 정상은 첫 줄 요약 표시
                is_error = obj.get("is_error", False)
                result_content = obj.get("content", "")
                if isinstance(result_content, list):
                    result_content = " ".join(c.get("text", "") for c in result_content if isinstance(c, dict))
                result_content = str(result_content).strip()
                if is_error:
                    display_text = f"❌ 도구 오류: {result_content[:200]}"
                elif result_content:
                    # 정상 결과 — 첫 줄만 요약 표시 (너무 길면 생략)
                    first_line = result_content.split("\n")[0][:120]
                    display_text = f"  ↳ {first_line}" if first_line else None
            
            elif msg_type == "system":
                # 시스템 초기화 메시지 — 모델명 표시
                sys_subtype = obj.get("subtype", "")
                if sys_subtype == "init":
                    model_name = obj.get("model", "")
                    tools = obj.get("tools", [])
                    tool_names = [t.get("name", "") for t in tools if isinstance(t, dict)]
                    display_text = f"🚀 모델: {model_name} | 도구: {', '.join(tool_names[:5])}"
            
            elif msg_type in ("agent_start", "subagent_start"):
                # 서브에이전트 시작
                agent_id = obj.get("agent_id", obj.get("id", ""))
                display_text = f"👾 서브에이전트 시작: {agent_id}"
            
            elif msg_type in ("agent_end", "subagent_end", "subagent_result"):
                # 서브에이전트 완료
                agent_id = obj.get("agent_id", obj.get("id", ""))
                display_text = f"✔ 서브에이전트 완료: {agent_id}"
            
            # ─── 화면 출력 ───
            if display_text and display_text.strip():
                has_output = True
                last_output_time = time.time()   # 워치독 타이머 리셋
                
                # ── 대화형 프롬프트 자동 응답 (display_text 기준 2차 감지) ──
                # raw 줄에서 못 잡은 경우(JSON 안에 포함된 질문)를 처리
                # auto_responded=True면 이미 이 줄에서 전송했으므로 건너뜀 (이중 전송 방지)
                if not auto_responded:
                    dt_lower = display_text.lower()
                    if any(pat in dt_lower for pat in AUTO_RESPOND_PATTERNS):
                        try:
                            with stdin_lock:
                                if not proc.stdin.closed:
                                    proc.stdin.write(b"1\n")
                                    proc.stdin.flush()
                            auto_msg = "🤖 [자동 응답] 1 (Yes) — 대화형 프롬프트 감지"
                            log.info(f"[{step:03d}] 자동 응답(2차) 전송: 1 (Yes)")
                            text_f.write(auto_msg + '\n')
                            text_f.flush()
                        except Exception:
                            pass
                
                # 타이머 줄 지우기
                print(f"\r{' ' * 80}\r", end='', flush=True)
                print(f"  {display_text}", flush=True)
                # 텍스트 로그에도 저장
                text_f.write(display_text + '\n')
                text_f.flush()
    
    # ─── 시작 ───
    print(f"\n{'─' * 60}")
    log.info(f"[{step:03d}/{TOTAL_PROMPTS}] 실행 시작 ({mode_str})")
    print(f"{'─' * 60}")
    
    # ─── 프롬프트 + 강제 보고 템플릿 조합 ───
    augmented_prompt = build_augmented_prompt(prompt_file)
    augmented_bytes = augmented_prompt.encode('utf-8')
    
    timer_thread = threading.Thread(target=timer_loop, daemon=True)
    timer_thread.start()
    
    try:
        with open(log_raw_file, 'w', encoding='utf-8') as raw_f, \
             open(log_file, 'w', encoding='utf-8') as text_f, \
             open(log_err_file, 'w', encoding='utf-8') as err_f:
            
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(project_dir) if project_dir else None,
            )
            
            # stdin에 augmented 프롬프트 쓰기 (별도 스레드 — deadlock 방지)
            # ※ stdin을 닫지 않음 — 대화형 프롬프트 자동 응답을 위해 열어둠
            # ※ stdin_lock으로 process_stream 스레드와의 동시 접근 보호
            def write_stdin():
                try:
                    with stdin_lock:
                        proc.stdin.write(augmented_bytes)
                        proc.stdin.flush()
                        proc.stdin.close()  # EOF 전달 — 닫지 않으면 Claude Code가 EOF 대기로 데드락
                except BrokenPipeError:
                    pass
                except Exception:
                    pass
            
            t_stdin = threading.Thread(target=write_stdin, daemon=True)
            
            stderr_chunks = []
            
            def read_stderr():
                for raw_bytes in proc.stderr:
                    line = raw_bytes.decode('utf-8', errors='replace') if isinstance(raw_bytes, bytes) else raw_bytes
                    err_f.write(line)
                    err_f.flush()
                    stderr_chunks.append(line)
            
            t_out = threading.Thread(
                target=process_stream,
                args=(proc.stdout, raw_f, text_f)
            )
            t_err = threading.Thread(target=read_stderr)
            
            t_stdin.start()
            t_out.start()
            t_err.start()
            
            try:
                proc.wait()  # 타임아웃 없음 — 완료될 때까지 대기
            except KeyboardInterrupt:
                proc.kill()
                is_running = False
                t_out.join(timeout=5)
                t_err.join(timeout=5)
                raise
            
            is_running = False
            t_out.join()
            t_err.join()
            
            returncode = proc.returncode
            stderr_text = ''.join(stderr_chunks)
            
    except Exception as e:
        is_running = False
        duration = int(time.time() - start_time)
        log.error(f"[{step:03d}] 실행 오류: {e}")
        return ("failed", session_id, duration)
    
    is_running = False
    duration = int(time.time() - start_time)
    mins, secs = divmod(duration, 60)
    
    # ─── 결과 판정 (3겹 검증 포함) ───
    print()
    
    # idle 워치독이 kill한 경우 → suspicious로 처리 (자동 skip)
    if stagnation_killed:
        log.warning(f"[{step:03d}] 💀 idle_killed — {STAGNATION_LIMIT//60}분간 출력 없어 강제 종료 ({mins}분 {secs}초 소요)")
        meta = {
            "step": step,
            "exit_code": "idle_killed",
            "verdict": "suspicious",
            "failure_keyword": f"idle_timeout_{STAGNATION_LIMIT}s",
            "duration_sec": duration,
            "new_session": is_new,
            "session_id": result_session_id,
            "timestamp": datetime.now().isoformat(),
            "prompt_md5": hashlib.md5(prompt_file.read_bytes()).hexdigest(),
        }
        log_meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
        _save_completion_report(step, logs_dir=LOGS_DIR)
        return ("suspicious", result_session_id, duration)
    
    if returncode == 0:
        # exit_code=0이어도 조용한 실패 가능 → 1겹 검증
        if detected_failure_keyword:
            log.warning(f"[{step:03d}] ⚠ 조용한 실패 감지: '{detected_failure_keyword}'")
            log.warning(f"[{step:03d}] exit_code=0이지만 작업이 완료되지 않았을 수 있습니다.")
            
            meta = {
                "step": step,
                "exit_code": 0,
                "verdict": "suspicious",
                "failure_keyword": detected_failure_keyword,
                "duration_sec": duration,
                "new_session": is_new,
                "session_id": result_session_id,
                "timestamp": datetime.now().isoformat(),
                "prompt_md5": hashlib.md5(prompt_file.read_bytes()).hexdigest(),
            }
            log_meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
            
            _save_completion_report(step, logs_dir=LOGS_DIR)
            return ("suspicious", result_session_id, duration)
        
        log.info(f"[{step:03d}] ✅ 완료 — {mins}분 {secs}초 소요")
        
        meta = {
            "step": step,
            "exit_code": 0,
            "verdict": "success",
            "duration_sec": duration,
            "new_session": is_new,
            "session_id": result_session_id,
            "timestamp": datetime.now().isoformat(),
            "prompt_md5": hashlib.md5(prompt_file.read_bytes()).hexdigest(),
        }
        log_meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
        
        # ── 완료 보고서 별도 파일 저장 ──
        _save_completion_report(step, logs_dir=LOGS_DIR)
        
        # 항상 실제 session_id 반환 — "CONTINUE" 센티널 사용 금지
        return ("success", result_session_id, duration)
    else:
        log.error(f"[{step:03d}] ❌ 실패 — exit code: {returncode}, {mins}분 {secs}초 소요")
        if stderr_text:
            log.error(f"[{step:03d}] {stderr_text[:200]}")
        
        return ("failed", None, duration)


# ═══════════════════════════════════════════════════════════════
#  재시도 로직
# ═══════════════════════════════════════════════════════════════

def run_with_retry(
    step: int,
    prompt_file: Path,
    session_id: str = None,
    max_retries: int = 3,
    project_dir: Path = None,
    model: str = None,
    idle_timeout: int = 0,
    **kwargs,
) -> tuple:  # (verdict, session_id, total_duration)
    """
    재시도를 포함한 프롬프트 실행.
    
    일반 오류: 3회 재시도 (15초, 30초, 60초 대기)
    Rate limit: 5분 간격으로 최대 60회 재시도 (= 최대 5시간 대기)
    """
    
    total_duration = 0
    rate_limit_retries = 0
    MAX_RATE_LIMIT_RETRIES = 30  # 10분 × 30 = 최대 5시간
    RATE_LIMIT_WAIT = 600  # 10분
    
    attempt = 0
    
    while True:
        attempt += 1
        
        if attempt > 1 and rate_limit_retries == 0:
            # 일반 재시도
            if attempt > max_retries:
                break
            wait = 15 * (2 ** (attempt - 2))
            log.warning(f"[{step:03d}] 재시도 {attempt}/{max_retries} — {wait}초 대기")
            time.sleep(wait)
        
        verdict, sid, dur = run_single_prompt(
            step, prompt_file, session_id, project_dir=project_dir, model=model, idle_timeout=idle_timeout, **kwargs
        )
        total_duration += dur
        
        if verdict == "success":
            return ("success", sid, total_duration)
        
        if verdict == "suspicious":
            # 조용한 실패: 재시도 없이 즉시 반환 (메인 루프에서 사용자에게 판단 요청)
            return ("suspicious", sid, total_duration)
        
        # ─── 오류 분석 ───
        is_rate_limit = False
        err_file = LOGS_DIR / f"{step:03d}.error.log"
        stdout_file = LOGS_DIR / f"{step:03d}.log"
        stream_file = LOGS_DIR / f"{step:03d}.stream.jsonl"
        
        for check_file in [err_file, stdout_file, stream_file]:
            if check_file.exists():
                content = check_file.read_text(encoding='utf-8').lower()
                if any(kw in content for kw in ["rate limit", "hit your limit", "too many", "try again", "rate_limit", "overloaded"]):
                    is_rate_limit = True
                    break
        
        # ─── 세션 만료 감지 → session_id=None 폴백 ───
        is_session_expired = False
        for check_file in [err_file, stdout_file, stream_file]:
            if check_file.exists():
                content_lower = check_file.read_text(encoding='utf-8').lower()
                if any(kw in content_lower for kw in SESSION_EXPIRED_KEYWORDS):
                    is_session_expired = True
                    break
        
        if is_session_expired and session_id is not None:
            log.warning(f"[{step:03d}] ⚠ 세션 만료/삭제 감지 (session_id: {session_id[:16]}...)")
            log.warning(f"[{step:03d}]   → session_id=None으로 폴백, 새 세션으로 재시도")
            session_id = None   # 새 세션 시작
            attempt = 0         # 재시도 카운터 리셋 (새 세션이므로 공정한 3회 기회 부여)
            rate_limit_retries = 0
            continue
        
        if is_rate_limit:
            rate_limit_retries += 1
            if rate_limit_retries > MAX_RATE_LIMIT_RETRIES:
                log.error(f"[{step:03d}] Rate limit 대기 {MAX_RATE_LIMIT_RETRIES}회 초과. 중단.")
                break
            
            mins_waited = rate_limit_retries * RATE_LIMIT_WAIT // 60
            log.warning(f"")
            log.warning(f"[{step:03d}] ⏸ Rate Limit 감지!")
            log.warning(f"[{step:03d}] {RATE_LIMIT_WAIT // 60}분 후 자동 재시도 ({rate_limit_retries}/{MAX_RATE_LIMIT_RETRIES})")
            log.warning(f"[{step:03d}] 지금까지 대기: {mins_waited}분")
            log.warning(f"")
            
            # 카운트다운 표시
            for remaining in range(RATE_LIMIT_WAIT, 0, -1):
                mins, secs = divmod(remaining, 60)
                print(f"\r  ⏸ Rate Limit 대기 중... {mins:02d}:{secs:02d} ", end='', flush=True)
                time.sleep(1)
            print(f"\r  ▶ 재시도 시작                              ")
            
            # rate limit 재시도에서는 attempt 카운터 리셋
            attempt = 0
            continue
        
        # 일반 오류는 attempt 카운터로 처리
        rate_limit_retries = 0  # rate limit이 아니면 리셋
    
    return ("failed", session_id, total_duration)


# ═══════════════════════════════════════════════════════════════
#  프롬프트 파일 무결성 검증
# ═══════════════════════════════════════════════════════════════

def verify_prompts() -> bool:
    """모든 프롬프트 파일의 존재와 무결성을 검증"""
    
    log.info("프롬프트 파일 검증 시작...")
    errors = 0
    
    for i in range(1, TOTAL_PROMPTS + 1):
        f = PROMPTS_DIR / f"{i:03d}.txt"
        
        if not f.exists():
            log.error(f"  ❌ 파일 없음: {f}")
            errors += 1
            continue
        
        content = f.read_text(encoding='utf-8')
        
        # /clear 파일 검증
        if i in CLEAR_POSITIONS:
            if content.strip() != "/clear":
                log.error(f"  ❌ #{i:03d}: /clear 파일인데 내용이 다름: {repr(content[:50])}")
                errors += 1
        else:
            if len(content.strip()) == 0:
                log.error(f"  ❌ #{i:03d}: 빈 파일")
                errors += 1
    
    # NEW_SESSION_STARTS 검증
    for ns in NEW_SESSION_STARTS:
        if ns > 1:
            prev = ns - 1
            if prev not in CLEAR_POSITIONS:
                log.error(f"  ❌ 논리 오류: #{ns}가 새 세션인데 #{prev}가 /clear가 아님")
                errors += 1
    
    if errors == 0:
        log.info(f"  ✅ {TOTAL_PROMPTS}개 파일 검증 완료 — 무결")
        return True
    else:
        log.error(f"  ❌ {errors}개 오류 발견")
        return False


# ═══════════════════════════════════════════════════════════════
#  진행 표시
# ═══════════════════════════════════════════════════════════════

def show_progress(step: int, state: dict):
    completed = len(state["completed"])
    clears = len(state["clears"])
    failed = len(state["failed"])
    done = completed + clears
    pct = done * 100 // TOTAL_PROMPTS
    
    bar_len = 30
    filled = pct * bar_len // 100
    bar = "█" * filled + "░" * (bar_len - filled)
    
    print(f"\n{'═' * 56}")
    print(f"  Prompt Runner │ Step {step}/{TOTAL_PROMPTS}")
    print(f"  [{bar}] {pct}%")
    print(f"  완료: {completed}  /clear: {clears}  실패: {failed}")
    sid = state.get("current_session_id", "")
    if sid:
        print(f"  세션: {sid[:20]}...")
    print(f"{'═' * 56}\n")


# ═══════════════════════════════════════════════════════════════
#  드라이런
# ═══════════════════════════════════════════════════════════════

def dry_run(start_from: int = 1):
    """실행 순서를 미리 보여줌"""
    
    print(f"\n{'═' * 70}")
    print(f"  드라이런 — 실행 순서 미리보기 (Step {start_from}~{TOTAL_PROMPTS})")
    print(f"{'═' * 70}\n")
    
    session_num = 0
    session_id = "(none)"
    exec_count = 0
    
    for step in range(start_from, TOTAL_PROMPTS + 1):
        f = PROMPTS_DIR / f"{step:03d}.txt"
        size = f.stat().st_size if f.exists() else 0
        
        if step in CLEAR_POSITIONS:
            print(f"  #{step:03d}  ── /clear ── 세션 종료, session_id 해제")
            session_id = "(none)"
        
        elif step in NEW_SESSION_STARTS:
            session_num += 1
            session_id = f"(세션{session_num}에서 캡처)"
            print(f"  #{step:03d}  ▶ 새 세션{session_num} 시작  "
                  f"claude -p --output-format stream-json --verbose < {step:03d}.txt  ({size}B)")
            exec_count += 1
        
        else:
            print(f"  #{step:03d}    이어가기       "
                  f"claude -p --output-format stream-json --verbose --resume $sid < {step:03d}.txt  ({size}B)")
            exec_count += 1
    
    print(f"\n{'─' * 70}")
    print(f"  실행 프롬프트: {exec_count}개")
    print(f"  /clear:       {len(CLEAR_POSITIONS)}개")
    print(f"  세션 수:      {session_num}개")
    print(f"{'─' * 70}\n")


# ═══════════════════════════════════════════════════════════════
#  플레이스홀더 자동 치환
# ═══════════════════════════════════════════════════════════════

PLACEHOLDER_TITLE = "[ 여기에 만들기 원하는 것 입력 ]"
PLACEHOLDER_GOAL = "( 여기에 내가 이 서비스를 만드는 가장 중요한 목적, 혹은 결과물의 모양과 수준을 적는다 )"


def setup_prompts(title: str, goal: str) -> bool:
    """
    110개 프롬프트 파일의 플레이스홀더를 치환합니다.
    
    ① "[ 여기에 만들기 원하는 것 입력 ]" → title  (14개 파일)
    ② "( 여기에 내가 이 서비스를 만드는... )" → goal  (6개 파일)
    
    Returns: 성공 여부
    """
    
    log.info(f"{'═' * 56}")
    log.info(f"  플레이스홀더 치환")
    log.info(f"  ① 프로젝트: {title}")
    log.info(f"  ② 목표: {goal}")
    log.info(f"{'═' * 56}")
    
    replaced_title = 0
    replaced_goal = 0
    
    for i in range(1, TOTAL_PROMPTS + 1):
        filepath = PROMPTS_DIR / f"{i:03d}.txt"
        content = filepath.read_text(encoding='utf-8')
        
        new_content = content
        
        if PLACEHOLDER_TITLE in new_content:
            new_content = new_content.replace(PLACEHOLDER_TITLE, title)
            replaced_title += 1
        
        if PLACEHOLDER_GOAL in new_content:
            new_content = new_content.replace(PLACEHOLDER_GOAL, goal)
            replaced_goal += 1
        
        if new_content != content:
            filepath.write_text(new_content, encoding='utf-8')
    
    log.info(f"  치환 완료: ①={replaced_title}개, ②={replaced_goal}개")
    
    # 검증: 잔여 플레이스홀더 확인
    remaining = 0
    for i in range(1, TOTAL_PROMPTS + 1):
        content = (PROMPTS_DIR / f"{i:03d}.txt").read_text(encoding='utf-8')
        if PLACEHOLDER_TITLE in content or PLACEHOLDER_GOAL in content:
            remaining += 1
    
    if remaining > 0:
        log.error(f"  ❌ 치환 실패: {remaining}개 파일에 플레이스홀더 잔여")
        return False
    
    log.info(f"  ✅ 잔여 플레이스홀더 0개 — 치환 완벽")
    return True


def check_needs_setup() -> bool:
    """플레이스홀더가 아직 남아있는지 확인"""
    for i in range(1, TOTAL_PROMPTS + 1):
        content = (PROMPTS_DIR / f"{i:03d}.txt").read_text(encoding='utf-8')
        if PLACEHOLDER_TITLE in content or PLACEHOLDER_GOAL in content:
            return True
    return False


def _print_report_summary(logs_dir: Path, completed_steps: list) -> None:
    """
    전체 실행 후 완료 보고서 현황을 요약하여 출력합니다.
    부분 완료, 정직 플래그 등을 집계합니다.
    """
    partial_completions = []
    honesty_flags = []
    report_count = 0
    
    for step in completed_steps:
        report_file = logs_dir / f"{step:03d}.report.md"
        if not report_file.exists():
            continue
        
        content = report_file.read_text(encoding='utf-8')
        
        if "완료 보고서 없음" in content:
            continue
        
        report_count += 1
        
        # 부분 완료 감지 (달성도 %)
        import re
        pct_match = re.search(r'(\d+)%\s*complete', content, re.IGNORECASE)
        if pct_match:
            pct = int(pct_match.group(1))
            if pct < 80:
                partial_completions.append((step, pct))
        
        # 정직 플래그 감지 (YES 답변)
        yes_flags = re.findall(r'-\s.*?:\s*\[YES\]', content, re.IGNORECASE)
        if yes_flags:
            honesty_flags.append((step, len(yes_flags)))
    
    print(f"\n{'═' * 60}")
    print(f"  📊 완료 보고서 분석")
    print(f"{'═' * 60}")
    print(f"  보고서 수신: {report_count}/{len(completed_steps)}개")
    
    if partial_completions:
        print(f"\n  ⚠ 부분 완료 (80% 미만): {len(partial_completions)}개")
        for step, pct in partial_completions:
            print(f"    Step {step:03d}: {pct}%")
    
    if honesty_flags:
        print(f"\n  🚩 정직 플래그 있음: {len(honesty_flags)}개 스텝")
        for step, cnt in honesty_flags:
            print(f"    Step {step:03d}: {cnt}개 YES 플래그")
    
    if not partial_completions and not honesty_flags:
        print(f"\n  ✅ 이상 없음")
    
    print(f"\n  보고서 위치: {logs_dir}/{{step:03d}}.report.md")
    print(f"{'═' * 60}\n")


# ═══════════════════════════════════════════════════════════════
#  메인 실행
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Claude Code 프롬프트 순차 자동 실행기 (pipe + session ID)'
    )
    parser.add_argument('--resume', action='store_true',
                        help='중단 지점부터 재개')
    parser.add_argument('--from', dest='start_from', type=int, default=0,
                        help='특정 번호부터 시작 (새 세션)')
    parser.add_argument('--dry-run', action='store_true',
                        help='실행 없이 순서 확인')
    parser.add_argument('--verify', action='store_true',
                        help='프롬프트 파일 무결성 검증')
    parser.add_argument('--skip-permissions', action='store_true',
                        help='(deprecated) pipe 모드에서는 항상 --dangerously-skip-permissions가 적용됩니다.')
    parser.add_argument('--input', type=str, default=None,
                        help='입력 JSON 파일 (title과 goal을 파일로 전달)')
    parser.add_argument('--title', type=str, default=None,
                        help='프로젝트 제목 (무엇을 만들 것인가)')
    parser.add_argument('--goal', type=str, default=None,
                        help='최종 목표 (결과물의 수준과 형태)')
    parser.add_argument('--max-turns', type=int, default=0,
                        help='에이전트 최대 턴 수 (기본: 0 = 무제한, 될 때까지 실행)')
    parser.add_argument('--timeout', type=int, default=0,
                        help='프롬프트당 최대 실행 시간 초 (기본: 0 = 무제한, 될 때까지 실행)')
    parser.add_argument('--delay', type=int, default=60,
                        help='프롬프트 사이 대기 시간 초 (기본: 60, 0=대기 없음)')
    parser.add_argument('--project-dir', type=str, default=None,
                        help='Claude Code 실행 기준 디렉토리 (hooks/commands/skills 로드 위치). '
                             '미지정 시 run.py 실행 위치 기준.')
    parser.add_argument('--idle-timeout', type=int, default=7200,
                        help='출력 없을 때 hang 판정 기준 초 (기본: 7200=2시간, 0=환경변수 IDLE_TIMEOUT 사용)')
    parser.add_argument('--model', type=str, default=None,
                        help='사용할 Claude 모델 (자동 선택되므로 보통 불필요)')
    
    args = parser.parse_args()
    
    # ─── --input JSON 파일에서 title/goal 로드 ───
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            log.error(f"입력 파일 없음: {args.input}")
            sys.exit(1)
        with open(input_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        if 'title' not in input_data or 'goal' not in input_data:
            log.error("입력 JSON에 'title'과 'goal' 키가 필요합니다.")
            sys.exit(1)
        args.title = input_data['title']
        args.goal = input_data['goal']
        log.info(f"입력 파일 로드: {args.input}")
    
    # ─── title/goal이 없으면 직접 물어보기 ───
    if not args.title and not args.goal and not args.resume and not args.verify:
        if check_needs_setup():
            print()
            print("═" * 56)
            print("  프로젝트 정보를 입력하세요")
            print("═" * 56)
            print()
            print("① 무엇을 만들 것인가? (제목)")
            args.title = input("   → ").strip()
            print()
            print("② 최종 결과물의 수준과 형태는? (목표)")
            args.goal = input("   → ").strip()
            print()
            
            if not args.title or not args.goal:
                log.error("제목과 목표를 모두 입력해야 합니다.")
                sys.exit(1)
    
    # 환경 변수 오버라이드
    max_turns = int(os.environ.get("MAX_TURNS", args.max_turns))
    timeout = int(os.environ.get("TIMEOUT", args.timeout))
    delay = int(os.environ.get("DELAY", args.delay))
    skip_perms = os.environ.get("SKIP_PERMISSIONS", "0") == "1" or args.skip_permissions
    
    # ─── 프로젝트 디렉토리 확정 ───
    if args.project_dir:
        project_dir = Path(args.project_dir).resolve()
        if not project_dir.is_dir():
            log.error(f"--project-dir 경로가 존재하지 않습니다: {project_dir}")
            sys.exit(1)
    else:
        project_dir = Path.cwd()
    log.info(f"프로젝트 디렉토리: {project_dir}")
    claude_dir = project_dir / ".claude"
    if claude_dir.is_dir():
        log.info(f"  .claude/ 폴더 감지 — hooks/commands/skills 로드됩니다")
    else:
        log.warning(f"  ⚠ .claude/ 폴더 없음 ({project_dir}) — hooks/commands/skills 비활성")
    
    # ─── 1. 플레이스홀더 치환 (최우선 실행) ───
    if args.title and args.goal:
        if not setup_prompts(args.title, args.goal):
            log.error("플레이스홀더 치환 실패. 중단합니다.")
            sys.exit(1)
    elif args.title or args.goal:
        log.error("--title과 --goal은 반드시 함께 사용해야 합니다.")
        sys.exit(1)
    
    # ─── 2. 검증 모드 ───
    if args.verify:
        ok = verify_prompts()
        sys.exit(0 if ok else 1)
    
    # ─── 3. 드라이런 모드 ───
    if args.dry_run:
        start = args.start_from if args.start_from > 0 else 1
        if args.resume and STATE_FILE.exists():
            start = state_load()["current_step"]
        dry_run(start)
        sys.exit(0)
    
    # ─── 4. 플레이스홀더 잔여 검사 (실행 모드에서만) ───
    if check_needs_setup():
        log.error("프롬프트에 플레이스홀더가 남아있습니다.")
        log.error("--title과 --goal을 지정하세요:")
        log.error('  python3 run.py --title "프로젝트 제목" --goal "최종 목표"')
        sys.exit(1)
    
    # ─── 5. 시작점 결정 ───
    if args.resume and STATE_FILE.exists():
        state = state_load()
        start_from = state["current_step"]
        log.info(f"이전 상태에서 재개: Step {start_from}")
        if start_from > TOTAL_PROMPTS:
            log.info(f"  ※ current_step({start_from}) > TOTAL_PROMPTS({TOTAL_PROMPTS}) — 이미 완료된 상태입니다.")
            sys.exit(0)
    elif args.start_from > 0:
        if args.start_from > TOTAL_PROMPTS:
            log.error(f"--from {args.start_from}은 TOTAL_PROMPTS({TOTAL_PROMPTS})를 초과합니다.")
            sys.exit(1)
        state = state_init()
        start_from = args.start_from
        state["current_step"] = start_from
        _state_save(state)
        log.info(f"Step {start_from}부터 시작 (새 세션)")
    else:
        state = state_init()
        start_from = 1
    
    # ─── 6. 사전 검증 ───
    LOGS_DIR.mkdir(exist_ok=True)
    
    if not verify_prompts():
        log.error("프롬프트 파일 검증 실패. 중단합니다.")
        sys.exit(1)
    
    # ─── 실행 시작 ───
    log.info(f"{'═' * 56}")
    log.info(f"  Claude Code 프롬프트 자동 실행 시작")
    log.info(f"  범위: Step {start_from} ~ {TOTAL_PROMPTS}")
    log.info(f"  모델: {get_best_model()} (자동 선택) | thinking: {THINKING_BUDGET_TOKENS:,} tokens")
    log.info(f"  max_turns: {'무제한' if max_turns == 0 else max_turns}, timeout: {'무제한' if timeout == 0 else f'{timeout}초'}")
    log.info(f"  idle_timeout: {args.idle_timeout}초 ({args.idle_timeout//60}분) — 출력 없으면 hang 판정")
    log.info(f"  프롬프트 간 대기: {delay}초 (적응형)")
    log.info(f"  프로젝트: {project_dir}")
    log.info(f"{'═' * 56}")
    
    main_start = time.time()
    use_continue = False   # 기본: 새 세션
    current_session_id = None  # 현재 실행 중인 세션의 실제 ID (--resume에 사용)

    # ─── --resume 재개 시 이전 세션 복원 ───
    if args.resume and STATE_FILE.exists():
        saved_sid = state.get("current_session_id")
        if start_from not in NEW_SESSION_STARTS:
            # 세션 블록 중간 재개: 저장된 session_id로 --resume 이어받기
            use_continue = True
            current_session_id = saved_sid  # None이어도 괜찮음 (아래에서 처리)
            if saved_sid:
                log.info(f"  이전 세션 복원: {saved_sid[:24]}...")
                log.info(f"  Step {start_from}부터 --resume {saved_sid[:8]}...로 이어갑니다")
            else:
                log.warning(f"  ⚠ 저장된 session_id 없음 — 새 세션으로 대체 시작")
                use_continue = False
        else:
            log.info(f"  Step {start_from}은 새 세션 시작점 → 새 세션으로 시작")
    
    for step in range(start_from, TOTAL_PROMPTS + 1):
        
        # ─── /clear 처리 ───
        if step in CLEAR_POSITIONS:
            log.info(f"[{step:03d}] /clear → 세션 종료")
            use_continue = False       # 다음 프롬프트는 새 세션
            current_session_id = None  # 세션 ID 해제
            state_record_clear(state, step)
            continue
        
        # ─── 진행 표시 ───
        show_progress(step, state)
        
        # ─── 세션 판단 ───
        prompt_file = PROMPTS_DIR / f"{step:03d}.txt"
        
        if step in NEW_SESSION_STARTS:
            use_continue = False       # 새 세션
            current_session_id = None  # 세션 ID 초기화

        # session_arg: 이어가기면 실제 session_id, 새 세션이면 None
        # "CONTINUE" 문자열 센티널 완전 제거 — 실제 ID만 사용
        session_arg = current_session_id if use_continue else None
        
        # ─── 2겹 검증: 실행 전 스냅샷 ───
        snapshot_before = snapshot_project_files(project_dir)
        
        # ─── 실행 ───
        verdict, sid, duration = run_with_retry(
            step=step,
            prompt_file=prompt_file,
            session_id=session_arg,
            max_retries=3,
            max_turns=max_turns,
            timeout=timeout,
            skip_permissions=skip_perms,
            project_dir=project_dir,
            model=args.model,
            idle_timeout=args.idle_timeout,
        )
        
        # ─── 세션 ID 갱신 — 매 step마다 최신 session_id 추적 ───
        # (새 세션이든 이어가기든 Claude는 항상 result에 session_id를 반환함)
        if sid:
            current_session_id = sid
            state_update_session_id(state, sid)
            if not use_continue:
                log.info(f"[{step:03d}] 새 세션 ID: {sid[:24]}...")
            else:
                log.debug(f"[{step:03d}] 세션 ID 확인: {sid[:24]}...")
        
        # ─── 2겹 검증: 실행 후 스냅샷 비교 ───
        snapshot_after = snapshot_project_files(project_dir)
        changes = diff_snapshots(snapshot_before, snapshot_after)
        
        # ─── 판정 ───
        if verdict == "success":
            # exit_code=0 + 키워드 없음
            if changes["total_changes"] == 0:
                # 파일 변화 없음 — 분석·성찰 프롬프트에서는 정상
                log.info(f"[{step:03d}] 파일 변화 0건 (분석·성찰 프롬프트 정상)")
            else:
                log.info(f"[{step:03d}] 파일 변화: +{len(changes['created'])} ~{len(changes['modified'])} -{len(changes['deleted'])}")
            
            use_continue = True
            state_record_complete(state, step)
        
        elif verdict == "suspicious":
            # 1겹 감지: 조용한 실패 키워드 발견 → 항상 자동 건너뛰기
            if changes["total_changes"] == 0:
                log.warning(f"[{step:03d}] ⚠ 조용한 실패 키워드 감지 + 파일 변화 0건 → 자동 건너뜀")
            else:
                log.warning(
                    f"[{step:03d}] ⚠ 조용한 실패 키워드 감지 + 파일 변화 {changes['total_changes']}건 → 자동 건너뜀"
                )
                log.warning(f"[{step:03d}]   변화 파일: "
                            f"+{len(changes['created'])} ~{len(changes['modified'])} -{len(changes['deleted'])}")
            
            # stagnation kill(sid=None)이면 세션 상태 불명확 → 안전하게 새 세션 전환
            # 키워드 감지(sid 존재)면 세션은 유효하므로 이어가기 유지
            if sid is None:
                log.warning(f"[{step:03d}]   stagnation kill — 세션 상태 불명확 → 다음 step은 새 세션")
                use_continue = False
                current_session_id = None
            else:
                use_continue = True
            state_record_complete(state, step)
        
        else:  # "failed"
            state_record_fail(state, step)
            log.error(f"[{step:03d}] 최종 실패. 중단합니다.")
            log.error(f"  재개 명령: python3 run.py --resume")
            sys.exit(1)
        
        # ─── 프롬프트 간 대기 (rate limit 방지) ───
        # 여기에 도달 = 성공 또는 건너뛰기로 다음 단계 진행
        if delay > 0 and step < TOTAL_PROMPTS:
            next_step = step + 1
            if next_step not in CLEAR_POSITIONS:
                # ── 적응형 딜레이: 프롬프트 크기 + 실행 시간 기반 ──
                prompt_size = prompt_file.stat().st_size
                if prompt_size < 150:
                    # 매우 짧은 프롬프트(승인·릴레이): 최소 대기
                    actual_delay = min(delay, 10)
                elif prompt_size < 500:
                    # 짧은 프롬프트: 절반 대기
                    actual_delay = min(delay, max(10, delay // 2))
                else:
                    # 긴 프롬프트(에이전트 작업): 설정된 full 대기
                    actual_delay = delay
                
                for remaining in range(actual_delay, 0, -1):
                    print(f"\r  ⏸ 다음 프롬프트까지 {remaining}초 대기... ({prompt_size}B)   ", end='', flush=True)
                    time.sleep(1)
                print(f"\r{' ' * 60}\r", end='', flush=True)
    
    # ─── 완료 ───
    state_finish(state)
    
    total_sec = int(time.time() - main_start)
    hours = total_sec // 3600
    mins = (total_sec % 3600) // 60
    
    log.info(f"{'═' * 56}")
    log.info(f"  ✅ 전체 실행 완료!")
    log.info(f"  소요 시간: {hours}시간 {mins}분")
    log.info(f"  완료: {len(state['completed'])}개")
    log.info(f"  /clear: {len(state['clears'])}개")
    log.info(f"{'═' * 56}")
    
    # ─── 완료 보고서 현황 요약 ───
    _print_report_summary(LOGS_DIR, state["completed"])


# ═══════════════════════════════════════════════════════════════
#  시그널 핸들러
# ═══════════════════════════════════════════════════════════════

def signal_handler(signum, frame):
    print()
    log.warning("사용자 중단 (Ctrl+C)")
    log.info("현재 상태가 state.json에 저장되었습니다.")
    log.info("재개: python3 run.py --resume")
    sys.exit(130)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == '__main__':
    main()
