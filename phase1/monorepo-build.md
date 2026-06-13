# Phase 1-1 — 이력 보존형 모노레포 구축 보고서

- 일시: 2026-06-13
- 도구: git-filter-repo `a40bce548d2c` (pip3 --user 설치, `python3 -m git_filter_repo` 호출)
- 스테이징: `/tmp/aksj_stage` / 타깃: `/Users/tajun/spJavis/auto-korea-stock-javis`
- 원본 2개 repo는 `git clone --no-local` 소스로만 사용, 무수정 (HEAD 확인: krt `a9a8f51`, aw `da328e3`).

## 절차 및 수치

### STEP 3 — engine (kiwoom-rest-trader)
| 단계 | 결과 |
|---|---|
| clone 직후 커밋 수 | 7 |
| 3a 시크릿 purge (`--invert-paths --path .env.example --path data/.token_cache.json`) | 완료. purge 후 grep 0건 |
| purge 후 커밋 수 | **5** (시크릿 파일만 건드린 커밋 2개가 empty화되어 filter-repo가 자동 prune) |
| 3b `--to-subdirectory-filter engine` | 완료. HEAD 트리 = `engine` 단일 디렉토리 |

### STEP 4 — factory (AgenticWorkflow-main-stock-filtering-collector)
| 단계 | 결과 |
|---|---|
| clone 직후 커밋 수 | 3 |
| 4a 시크릿 스캔 `grep -iE '\.env$|token|secret|\.key$'` | 히트 2건: `.claude/hooks/scripts/_test_secret_filter.py`, `.claude/hooks/scripts/output_secret_filter.py` |
| 히트 판정 | **시크릿 아님** — 시크릿 *탐지용* PostToolUse 훅 코드 + 테스트. 하드코딩 자격증명 패턴 grep 0건. purge하지 않고 보존 |
| 4b `--to-subdirectory-filter factory` | 완료. HEAD 트리 = `factory` 단일 디렉토리, 3커밋 유지 |

### STEP 5 — 타깃 병합
1. `git init -b main` (기존 .git 없음 확인 후)
2. 루트 `.gitignore` (.DS_Store, engine/.env, engine/.venv/, engine/reports/, engine/data/, engine/logs/) + BUILD_PLAN.md + EXECUTION_REPORT.md + phase0/ → 커밋 `6360542`
3. `krt/main` merge (`--allow-unrelated-histories`) → engine/ 이력 유입
4. `aw/main` merge (`--allow-unrelated-histories`) → factory/ 이력 유입
5. remote krt·aw 제거 (`git remote -v` 공백 확인)

### STEP 6 — engine/.env.example 재생성
원본 repo의 현재 플레이스홀더 버전 복사. `grep -c 'your_kiwoom'` = **2** (플레이스홀더 확인). 커밋 완료.

### STEP 7 — 비추적 운영 데이터 (git 밖)
- `engine/.env` 복사 + `chmod 600` (`-rw-------` 확인)
- `engine/reports/`, `engine/logs/`, `engine/data/` rsync -a
- `engine/data/.token_cache.json` 삭제 (새 환경에서 자동 재발급)
- `.venv` 미복사 (Phase 1-3에서 재구축)

## STEP 8 — 종합 검증

| # | 항목 | 결과 |
|---|---|---|
| 8a | 총 커밋 수 | **12** = krt 5 + aw 3 + 신규 2(founding docs, .env.example) + 머지 2 |
| 8b | 이력 추적성 | `engine/src/kiwoom/auth.py` → `18282c2 2026-06-12 22:56 first commit` / `factory/README.md` → `17ba20b 2026-06-12 21:56 first commit` + `99b87f0 2026-06-12 20:11 Initial commit`. 6/12 초기 커밋까지 도달 |
| 8c | 시크릿 부재 | `git log --all --name-only` grep 결과 `engine/.env.example` 1건만 (STEP 6 신규 플레이스홀더). 구 `.env.example`·`data/.token_cache.json` 이력 0건 |
| 8d | 트리 동등성 | engine: diff 65줄 전부 비추적 아티팩트(Only in: .DS_Store, __pycache__, .pytest_cache, *.bak, backupMasterCompanys 등). **content `differ` 0건**. 한글 파일명 10쌍(기본*.xls 등)은 macOS NFD/NFC 정규화 차이로 양쪽 'Only in' 표기 — md5 전수 대조 **10/10 동일**, `키움 REST API 문서.pdf`도 MATCH. factory: 전부 비추적 아티팩트(agent-memory, autopilot-logs, __pycache__ 등), content differ 0건 |
| 8e | git status | `nothing to commit, working tree clean`, branch `main` |

## 발견 사항
1. krt 커밋 7→5: `.env.example`/`.token_cache.json`만 변경한 커밋 2개가 purge로 empty화되어 자동 제거됨 (의도된 동작, 이력 손실 아님 — 해당 커밋의 유일 내용이 소각 대상).
2. aw 시크릿 스캔 히트 2건은 시크릿 탐지 훅 코드로 판정, 보존.
3. 한글 파일명 NFC/NFD 차이는 git 체크아웃 정규화 특성 — 내용 동일, 조치 불요.

## 커밋 그래프 (최종)
```
git log --oneline --graph 요지: main = founding docs → merge(engine 5c) → merge(factory 3c) → .env.example
총 12 커밋, remote 0개, 원격 push 없음 (전 작업 로컬).
```
