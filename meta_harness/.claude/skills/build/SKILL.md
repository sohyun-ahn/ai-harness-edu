---
name: build
description: 승인된 design.md 대로 하네스 파일을 생성할 때. docs/<이름>/APPROVED 가 있을 때만 쓴다.
---

# build

## 시작 전 확인
- docs/<이름>/APPROVED 가 있는가. 없으면 시작하지 않고 design 단계로 돌아간다
- design.md 를 읽는다. **설계서에 없는 파일 · 규칙은 만들지 않는다**

## 생성
대상 폴더(기본 `out/<이름>/`)에 design.md 의 「파일 목록」대로만 만든다.
- 설계에 있는 것만: CLAUDE.md · `.claude/skills/*/SKILL.md` · `.claude/agents/*.md` · `.claude/hooks/*` · `.claude/settings.json`
- Skill 의 `description` 에는 무엇을 하는지와 호출 조건을 적는다
- Hook 은 design.md 의 「하면 안 되는 것」을 그대로 차단한다. 만든 뒤 차단 입력 · 통과 입력으로 한 번씩 실행해 본다
- 규칙마다 design.md 에 적힌 근거와 어긋나지 않게 쓴다. 범용 문장은 쓰지 않는다
- eval 입력 파일을 `docs/<이름>/eval/` 에 만든다 (design.md 의 「시험 설계」대로)

## 끝나면
만든 파일 목록과 Hook 확인 결과를 보여 주고 harness-reviewer 검토로 넘긴다. 설계에서 바꾼 것이 있으면 이유와 함께 알린다.
