# 메타 하네스 · 하네스를 만드는 하네스

사용자의 업무에 맞는 하네스(CLAUDE.md · Skill · Hook · Sub Agent)를 만든다. 이 폴더가 만드는 것은 업무 자체의 결과물이 아니라 업무를 처리할 **하네스**다.
유형별 예시는 `templates/README.md` 에 있다.

## 순서 (건너뛰지 않는다)
1. 인터뷰 — interview Skill → docs/<이름>/interview.md
2. 설계 — design Skill → docs/<이름>/design.md. 요약을 보여 주고 **멈춘다**
3. 사용자 승인 — 사용자가 docs/<이름>/APPROVED 를 만들 때까지 대기. 그 전에는 docs/ 밖에 쓰지 못한다 (guard Hook이 막는다)
4. 생성 — build Skill → 대상 폴더(기본 out/<이름>/)에 설계대로 파일 생성
5. 검토 — harness-reviewer Sub Agent → docs/<이름>/review.md → 지적 반영
6. 시험 — try Skill → docs/<이름>/try/ 에 하네스 미적용 · 적용 비교표
7. 판정 — **사람**이 한다. 비교표와 검토 결과를 보여 주고 멈춘다. Claude는 「좋다 · 나쁘다」를 판정하지 않는다

## 원칙
- 범용 규칙 금지: 「정확하게」「꼼꼼히」 같은 어디에나 맞는 문장은 쓰지 않는다. 이 업무에서만 의미가 있는 규칙만 쓴다
- 인터뷰에 나온 것만: 규칙 · 기준 · 금지 사항은 인터뷰 답변에 근거가 있어야 한다. 근거 없으면 「확인 필요」로 남기고 지어내지 않는다
- 부품은 필요한 것만: CLAUDE.md · Skill · Hook · Sub Agent 중 이 업무에 필요한 것만 만든다. 넣지 않는 부품은 이유를 design.md 에 적는다
- 하네스마다 docs/<이름>/ 에 interview.md · design.md · review.md · try/ 를 남긴다 (<이름>은 영문 소문자 · 하이픈)
- docs/<이름>/APPROVED 는 사람만 만든다

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
| --- | --- | --- | --- |
| 2026-10-15 | 메타 하네스 처음 구성 | 전체 | - |
