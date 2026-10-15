# 개발 하네스 · 내 업무 툴

Node.js · 외부 패키지 없음 · ES 모듈 · 테스트는 `node --test` (test/*.test.js)

## 순서 (건너뛰지 않는다)
1. 브레인스토밍 — brainstorm Skill → docs/brief.md
2. 구현 기획 — plan Skill → docs/plan.md (서로 겹치지 않는 작업 2~4개)
3. 사용자 컨펌 — 계획 요약을 보여 주고 멈춘다. 사용자가 docs/APPROVED 를 만들기 전에는 src/ · test/ 를 쓰지 않는다
4. 병렬 구현 — docs/ 를 커밋한 뒤 작업마다 implementer Sub Agent에 동시에 맡긴다
5. 통합 — 작업 브랜치를 차례로 병합 → npm test 전체 통과 → reviewer 검토 → 지적 반영
6. 마무리 — README.md: 쓰는 법 · 예시 입력 · 출력 · 테스트 결과

## 원칙
- 테스트 먼저, 그다음 구현
- 작업 범위 밖 파일은 고치지 않는다
- docs/APPROVED 는 사람만 만든다
