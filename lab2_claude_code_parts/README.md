# Lab 2 — Claude Code 부품 네 가지

`project/` 는 부품이 다 붙은 작은 프로젝트다.

| 부품 | 파일 | 언제 작동 | 확인 방법 |
|---|---|---|---|
| CLAUDE.md | `project/CLAUDE.md` | 세션 시작 때 항상 | `/context` 에 Memory files 로 보임 |
| 스킬 | `.claude/skills/incident-report/SKILL.md` | 요청이 `description` 과 맞을 때 Claude 가 호출 | 「장애 보고서」 요청 → 양식대로 |
| 서브에이전트 | `.claude/agents/reviewer.md` | 「리뷰해줘」 → `Agent` 도구로 위임. 읽기 도구만 | `/agents` 목록, 위임 표시 |
| 슬래시 명령 | `.claude/commands/triage.md`, `spec-check.md` | 사람이 `/triage …` 로 직접 | 네 줄 형식 |
| 훅 | `.claude/settings.json` → `hooks/guard.py` | 도구 실행 **직전**마다 (모델 판단과 무관) | `[가드레일]` 메시지 |

## 1. 대화형으로 둘러보기

가상 환경이 켜진 터미널에서 (훅의 `python` 명령 때문):

```bash
cd lab2_claude_code_parts/project
claude
```

| 입력 | 볼 것 |
|---|---|
| `/context` | CLAUDE.md·스킬 설명·에이전트 설명이 각각 몇 토큰인지 |
| `/agents` | `reviewer` 가 보이는지, 도구가 Read·Grep·Glob 뿐인지 |
| 어제 14시에 MES 가 20분 멈췄어. 장애 보고서 양식으로 정리해줘 | 스킬 호출, 없는 시각을 `(확인 필요)` 로 |
| src/order_api.py 리뷰해줘 | reviewer 로 위임, 줄 번호 붙은 표 |
| `/triage 노트북이 안 켜져요` · `/spec-check ../../data/pohang/specs/S06_수량불일치.txt` | 명령 본문대로 |
| .env 에 API_KEY=test 써줘 · build 폴더 rm -rf 로 지워줘 | 훅이 막고 이유를 말하는지 |
| `/hooks` | 등록된 훅 확인 |

Windows 에서 `python` 이 안 잡히면 `.claude/settings.json` 의 `python` 을 `py` 로. macOS 에서 가상 환경 없이 켤 때는 `python3`.

## 2. 헤드리스로 확인

```bash
python lab2_claude_code_parts/check.py --hook-only     # 훅 스크립트만 (호출 없음)
python lab2_claude_code_parts/check.py                 # 4건 · stream-json 이벤트로 판정
python lab2_claude_code_parts/check.py --dry-run
```

```
[통과] 스킬: Skill 도구로 incident-report 호출
[통과] 서브에이전트: reviewer 안에서 쓴 도구: ['Grep', 'Read']
[통과] 훅: .env 쓰기 시도 1번 · 훅 차단 1번 · 파일 생김=False
[통과] 슬래시 명령: 명령 본문의 네 줄 형식으로 답함
```

판정은 답 글이 아니라 **이벤트**로 한다 — `Skill` / `Agent` 도구 호출이 실제로 있었는지, 그 안에서 무슨 도구를 썼는지, 도구 결과에 `[가드레일]` 이 찍혔는지.

## 해 볼 것

1. `SKILL.md` 의 `description` 을 모호하게 바꾸고 다시 → 스킬이 안 불리는 문장을 찾는다.
2. `reviewer.md` 의 `tools:` 에 `Edit` 를 넣고 「리뷰하고 고쳐줘」 → 리뷰어가 파일을 고치는가. 다시 빼 둔다.
3. `guard_rules.py` 에 막을 패턴 하나 추가 (예: `curl … | sh`) → `--hook-only` 로 먼저 확인.
4. 헤드리스에서 `/triage` 가 펼쳐지지 않으면 결과를 강사에게 알린다 (버전마다 다를 수 있음 — 확인 필요).
