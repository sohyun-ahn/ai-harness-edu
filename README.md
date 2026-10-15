# 하네스 엔지니어링 실습

> ※ 모든 회사(「한빛스틸」)·인물·문서·단가는 실습용 가상 자료입니다.

## 진행 방법

1. 강의 첫 시간에 `labs.zip` 을 받아 압축을 푼다.
2. 실습마다 강의 장표 「실습 N 진행」이 가리키는 폴더를 VS Code로 열고 Claude Code 를 켠다.
3. **하네스 미적용**으로 먼저 실행 → 장표에 있는 하네스 파일(CLAUDE.md · Skill · Hook …)을 같은 경로로 직접 만든다 → **하네스 적용**으로 같은 요청 → 비교.
4. 요청문은 장표에서 「복사」해 붙여 넣는다. 코드는 직접 쓰지 않는다.

| 장표 | 실습 폴더 | 하네스 (장표에 있음) |
|---|---|---|
| 1-1 같은 질문 열 번 | `lab1_1_same_question/` | CLAUDE.md |
| 2-1 Skill · Sub Agent | `lab2_1_parts/` | SKILL.md · reviewer.md |
| 2-2 Claude로 Hook 만들기 | `lab2_hook_by_claude/project/` | Hook 요청문 |
| 2-3 업무 처리 하네스 | `work_harness/workspace/` | CLAUDE.md · Skill 두 개 |
| 3-1 컨텍스트 | `lab3_context/` | — |
| 4-1 공개 하네스 | `lab4_public_harness/` | — |
| 5-1 · 5-2 멀티에이전트 | `lab5_multiagent/` · `work_harness/workspace/` | extractor · verifier · 나누기 규칙 |
| 6-1 토큰 | `lab6_tokens/` | — |
| 7-1 평가 · 회귀 | `lab7_eval_regression/` | — |
| 7-2 메타 하네스 · 내 업무 | `meta_harness/` (이 폴더를 VS Code로) | 요청문 · 부록 ⑨ ⑩ |
| 8-1 개발 멀티에이전트 하네스 · 내 업무 툴 | `meta_harness/` 로 만들고 `final_dev_harness/` 에서 개발 | 메타 하네스 · 부록 ⑦ ⑧ |

## 강사용 참고

코드는 이미 다 들어 있다. 실습에서는 **프롬프트·설정·규칙 파일만** 바꾸고 결과가 어떻게 달라지는지 잰다. 고칠 곳에는 `TODO(실습)` 표시가 있다. 코드를 고쳐야 할 일이 생기면 직접 쓰지 말고 Claude Code 에게 시킨다.

실행 엔진은 **Claude Code 헤드리스 모드**(`claude -p`)다. API 키 없이 회사 Business(Team) 계정 로그인으로 돈다. 토큰은 결과 JSON 의 `usage` 로 잰다.

## 두 가지 시나리오 (같은 코드, 다른 데이터) — 하나를 고른다

| 트랙 | Agent | 입력 → 출력 |
|---|---|---|
| `pangyo` | 문의 대응 라우팅 | 사내 문의 → 분류(IT·구매·인사·보안·기타) → 분야별 답변 초안 → 검증 |
| `pohang` | 사양서 추출·견적 | 사양서 → 품목 JSON(품목·규격·재질·수량·단위·비고) → 견적 → 검증 |

스크립트는 `--track pangyo|pohang` 으로 고른다. 기본값은 `common/config.py` 의 `TRACK`.

## 준비 (한 번만)

1. **Claude Code 설치** — 최신 명령은 공식 설치 문서에서 확인한다. 회사 PC 정책으로 막히면 강사에게.
   ```bash
   curl -fsSL https://claude.ai/install.sh | bash          # macOS · Linux
   npm install -g @anthropic-ai/claude-code                # Node.js 가 있으면 (Windows 포함)
   ```
2. **로그인** — 터미널에서 `claude` → 로그인 방식에서 Claude 계정(회사 Business/Team 조직) → 브라우저 로그인. 확인: `claude auth status`.
3. **Python 3.10 이상** — 본 실습은 표준 라이브러리만 쓴다. 설치할 패키지 없음.
4. VS Code 에서 `labs` 폴더를 열고 모든 명령은 **`labs/` 에서** 실행한다.

```bash
claude --version
claude auth status
python lab1_harness_vs_bare/run.py --dry-run      # 호출 없이 흐름 확인 (Windows 는 python 또는 py)
```

- 터미널에 `ANTHROPIC_API_KEY` 가 설정돼 있으면 Claude Code 가 그 키(API 요금)를 쓸 수 있다. 회사 계정으로 돌리려면 비워 둔다.
- `--bare` 옵션은 API 키로만 인증하므로 이 실습에서는 쓰지 않는다. 대신 `--setting-sources=` 로 내 PC 설정을 끊는다.

## 할당량과 토큰

- 스크립트 한 번 = `claude -p` 여러 번. Business 요금제는 계정별 사용 한도에서 빠진다. 결과에 찍히는 `cost`(USD)는 API 기준 참고값이며 실제 청구와 다를 수 있다 → **토큰으로 비교한다.**
- 모든 실행 스크립트에 `--dry-run` 이 있다: `common/fixtures/` 의 저장된 출력으로 같은 파싱·표·그림을 만든다 (할당량 0). 처음에는 dry-run 으로 흐름을 보고, 그다음 작게(`-n 3`) 돌린다.
- `--show-cmd` 를 붙이면 실제 `claude` 명령이 찍힌다.
- 모델: `common/config.py` 의 `HEADLESS_MODEL`(기본 `sonnet`), 채점·분류용 `HEADLESS_CHEAP_MODEL`(`haiku`).

| 토큰 칸 | 뜻 |
|---|---|
| in | 캐시에 없던 새 입력 |
| 캐시읽기 | 캐시에서 읽은 입력 — Claude Code 기본 시스템 프롬프트·도구 설명이 대부분 여기 |
| 캐시쓰기 | 이번에 캐시에 새로 쓴 입력 |
| out | 모델이 쓴 출력 |
| 메인 토큰 | 위 넷의 합 (메인 대화) · **전체 토큰** = 서브에이전트까지 (`modelUsage` 합) |

## 실습 목록 (강의 장 순서)

| Lab | 실행 | 바꿔 볼 것 | 보는 것 |
|---|---|---|---|
| 1. [하네스 미적용 vs 하네스](lab1_harness_vs_bare/) | `python lab1_harness_vs_bare/run.py --track pangyo -n 5` | `harness/CLAUDE.md` | 같은 입력 N번 → 서로 다른 답 수, JSON 형식, 평균 토큰 |
| 2. [Claude Code 부품](lab2_claude_code_parts/) | 대화형 `cd lab2_claude_code_parts/project && claude` · `python lab2_claude_code_parts/check.py` | `SKILL.md`, `agents/reviewer.md`, `commands/*.md`, `guard_rules.py` | 스킬·서브에이전트·명령·훅이 실제로 작동하는지 (이벤트로 판정) |
| 3. [컨텍스트 엔지니어링](lab3_context/) | `python lab3_context/run.py --exp a` (a·b·c·d·all) | 변형별 CLAUDE.md, `SKILL.md`, `agents.json` | 통째로 vs 스킬로 · 통째로 읽기 vs Grep · 직접 vs 서브에이전트 · 긴 세션 vs 새 세션 |
| 4. [공개 하네스 비교](lab4_public_harness/) | `./lab4_public_harness/run_task.sh bare` (mine·superpowers·gstack) | `PREFIX`, 설치한 플러그인 | 같은 과제의 토큰·시간·테스트 통과·건너뛴 단계 → `compare.md` |
| 5. [멀티에이전트](lab5_multiagent/) | `python lab5_multiagent/run.py --track pangyo --ids Q10` | `project/.claude/agents/*.md`, `skills/orchestrate-*` | 위임 순서, 줄별 토큰, HTML 타임라인 |
| 6. [토큰 경제학](lab6_tokens/) | `python lab6_tokens/bench.py --levers baseline,brief` | `BRIEF`, 레버 설정, 플러그인 | 레버별 토큰 증감 · `quiz.md` 「몇 토큰일까?」 |
| 7. [평가·회귀](lab7_eval_regression/) | `python lab7_eval_regression/run_suite.py --track pangyo -n 10 --k 3` · `compare.py` | `metrics.md`, `judge_prompt.md`, `WEIGHTS`, `RULES` | 지표·judge 일치율(kappa)·전후 비교(회귀면 종료 코드 1) |
| 8. [최종 과제: 플러그인](lab8_final_plugin/) | `claude plugin validate ./lab8_final_plugin/my-harness` | `my-harness/` 전부 | 설치 가능한 하네스 + 평가셋 20건 + 비교표 |
| 선택. [Agent SDK 판](sdk_optional/) | `sdk_optional/README.md` | — | **API 키 필요.** 같은 내용을 파이썬 SDK 로 |

API 를 부르지 않는 스크립트: `lab2 … check.py --hook-only`, `lab5 … visualize.py`, `lab6 … quiz.py`, `lab7 … agreement.py`, `lab7 … compare.py`, 그리고 모든 `--dry-run`.

## 헤드리스 한눈에

```bash
echo "질문" | claude -p --output-format json --model sonnet \
  --setting-sources=project --tools Read,Grep,Glob --allowedTools Read,Grep,Glob --permission-mode dontAsk
```

| 옵션 | 이 실습에서 쓰는 곳 |
|---|---|
| `-p` · `--output-format json` / `stream-json --verbose` | 모든 실행 · 이벤트가 필요한 Lab 2·4·5 |
| `--setting-sources=` / `=project` / `=user` | 하네스 미적용 · 작업 폴더의 CLAUDE.md·.claude 만 · 설치한 플러그인 |
| `--tools` · `--allowedTools` · `--permission-mode` | 쓸 수 있는 도구 · 묻지 않고 허용할 도구 · 나머지는 거절(`dontAsk`) |
| `--append-system-prompt` · `--system-prompt` | Lab 6 짧게 지시 · Lab 7 judge |
| `--agents '<JSON>'` | Lab 3 c · Lab 6 서브에이전트 |
| `--plugin-dir` | Lab 4 · Lab 8 |
| `--resume <세션 ID>` | Lab 3 d |
| `--model` | 모든 실행 · Lab 6 모델 라우팅 |

공용 코드: `common/headless.py`(실행·파싱), `common/workspace.py`(임시 작업 폴더), `common/checks.py`(규칙 검증), `common/scoring.py`(채점), `common/data.py`.

## 폴더 구조

```
labs/
├── common/                 headless.py workspace.py config.py data.py checks.py scoring.py parse.py fixtures/
├── data/                   pangyo/(문의 30건, FAQ 5개)  pohang/(사양서 10건, 정답, 단가표)
├── lab1_harness_vs_bare/   run.py harness/CLAUDE.md
├── lab2_claude_code_parts/ check.py project/(CLAUDE.md, .claude/{skills,agents,commands,hooks,settings.json}, src/)
├── lab3_context/           run.py manual.md a_*/ b_*/ c_*/
├── lab4_public_harness/    run_task.sh run_task.py task.md compare.md sample_app/ acceptance/
├── lab5_multiagent/        run.py visualize.py sample_events.jsonl sample_timeline.html project/.claude/
├── lab6_tokens/            bench.py tasks.json quiz.md quiz.py
├── lab7_eval_regression/   run_suite.py compare.py judge.py agreement.py make_synthetic.py agent.py metrics.md results/
├── lab8_final_plugin/      my-harness/ .claude-plugin/marketplace.json
└── sdk_optional/           (API 키 필요) Agent SDK 판
```

## 막힐 때

| 증상 | 확인 |
|---|---|
| `'claude' 명령을 찾을 수 없습니다` | 설치 후 새 터미널, `claude --version`. 경로가 다르면 `common/config.py` 의 `CLAUDE_BIN` |
| 결과가 비고 `is_error` | `claude auth status` 로 로그인 확인. `--show-cmd` 로 나온 명령을 직접 실행해 오류 문구 확인 |
| 사용 한도 초과 메시지 | 잠시 쉬거나 `-n`·`--k` 를 줄이고 `--dry-run` 으로 진행 |
| 결과가 `JSON 형식이 아님` | CLAUDE.md 의 출력 형식 문장을 지웠는지 |
| 훅이 안 걸린다 | 가상 환경·`python` 명령 (Windows 는 `py`), `/hooks` 로 등록 확인 |
| 플러그인이 안 보인다 | 대화형에서 `/plugin` 목록, 회사 정책으로 마켓플레이스가 막혔는지 |
| `FileNotFoundError` | `labs/` 에서 실행했는지 |
