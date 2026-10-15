# Lab 4 — 공개 하네스 써 보고 비교하기

같은 과제(`task.md`)를 **하네스 미적용 · 내 하네스 · Superpowers · gstack** 으로 풀고 `compare.md` 를 채운다.

## 1. 설치

회사 정책으로 플러그인 마켓플레이스가 막혀 있으면 관리자에게 문의한다. 설치는 **대화형 Claude Code 안에서** 한다.

### Superpowers — 브레인스토밍 → 계획 → 실행, 테스트 먼저

```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

다시 켠 뒤: `/superpowers:brainstorm` · `/superpowers:write-plan` · `/superpowers:execute-plan`.
버전에 따라 명령 대신 스킬(`superpowers:brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development` …)이 스스로 불리는 방식이다 — `/plugin` 목록과 `/help` 로 확인.

### gstack — 역할별 명령 묶음 (스킬 폴더에 설치)

```bash
git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup
```

명령: `/office-hours`(아이디어 다듬기) · `/plan-eng-review`(설계 검토) · `/review`(PR 리뷰) · `/qa`(브라우저 QA) · `/cso`(보안 점검).
`./setup` 이 필요한 도구를 안내한다 — 막히면 공식 README 를 본다.

### Anthropic 공식 마켓플레이스

공식 마켓플레이스 이름은 `claude-plugins-official` (GitHub `anthropics/claude-plugins-official`). 대화형에서 `/plugin` → Discover 탭에서 고른다. 목록에 없으면:

```bash
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin marketplace list
claude plugin install <플러그인>@claude-plugins-official
claude plugin details <플러그인>       # 구성 요소와 예상 토큰 비용
```

`anthropics/claude-code` 저장소에도 예시 플러그인 모음이 있다 (`/plugin marketplace add anthropics/claude-code` — 확인 필요).

### 더 볼 것 (설명만)

| 이름 | 성격 |
|---|---|
| Everything Claude Code | 스킬·에이전트·훅·규칙을 크게 모아 둔 설정 모음. 필요한 것만 골라 쓰는 참고서 |
| wshobson/agents | 분야별 서브에이전트·플러그인 대량 모음. 역할 정의 문장을 참고하기 좋다 |
| claude-flow | 여러 Agent 를 무리 지어 돌리는 오케스트레이션 도구. 구조가 무겁고 토큰을 많이 쓴다 |

## 2. 같은 과제 돌리기

`sample_app/` — 재고·문의 분류 앱. 테스트 10개 중 2개가 실패한다 (버그 2개). 채점용 인수 테스트 3개(`acceptance/`)는 Agent 에게 보여 주지 않고 끝난 뒤에만 넣는다.

```bash
./lab4_public_harness/run_task.sh bare
./lab4_public_harness/run_task.sh mine          # lab8_final_plugin/my-harness 를 --plugin-dir 로
./lab4_public_harness/run_task.sh superpowers   # 설치한 플러그인(user 설정)으로
./lab4_public_harness/run_task.sh gstack
./lab4_public_harness/run_task.sh bare --dry-run
```

Windows 는 `python lab4_public_harness/run_task.py bare`.

| 하네스 | 실제 옵션 |
|---|---|
| bare | `--setting-sources=` |
| mine | `--setting-sources= --plugin-dir ../lab8_final_plugin/my-harness` |
| superpowers · gstack | `--setting-sources=user` (내 PC 에 설치한 것. 다른 user 설정도 같이 들어온다) — 섞이는 게 싫으면 저장소를 클론하고 `--plugin-dir <폴더>` |

공통: `--permission-mode acceptEdits`, 허용 도구는 읽기·편집·`Bash(python -m unittest*)`·`Bash(git *)` 등. 작업은 임시 폴더 복사본에서.

## 3. 대화형으로도 한 번

헤드리스는 질문 없이 끝까지 간다. 공개 하네스의 장점(되묻기·계획 승인)은 대화형에서 보인다.

```bash
cd <run_task 가 출력한 작업 폴더>
claude
> (task.md 내용을 붙여 넣는다)
```

끝나면 `/context` 로 쓴 양을 보고 (토큰 수는 헤드리스 결과가 더 정확하다) `compare.md` 에 적는다.
