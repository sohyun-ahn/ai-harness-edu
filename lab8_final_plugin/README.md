# Lab 8 — 최종 과제: 내 하네스를 플러그인으로

Lab 1~7 에서 다듬은 것을 `my-harness/` 한 폴더에 모아 **설치 가능한 플러그인**으로 만든다.

```
lab8_final_plugin/
├── .claude-plugin/marketplace.json     GitHub 에 올릴 때의 마켓플레이스 목록 (예시)
└── my-harness/
    ├── .claude-plugin/plugin.json      이름·버전·설명
    ├── skills/                         answer-with-evidence · fix-with-tests
    ├── agents/verifier.md              읽기 전용 검증자
    ├── commands/check.md               /my-harness:check
    ├── hooks/hooks.json + guard.py     위험 명령 차단 (${CLAUDE_PLUGIN_ROOT} 로 경로 지정)
    └── eval/                           평가셋 + 설명
```

## 1. 채우기 (TODO(실습) 표시)

| 가져올 곳 | 넣을 곳 |
|---|---|
| Lab 1 `harness/CLAUDE.md` 규칙·출력 형식 | `skills/answer-with-evidence/SKILL.md` |
| Lab 2 `guard_rules.py` 에 더한 규칙 | `hooks/guard_rules.py` |
| Lab 3 에서 줄인 컨텍스트 (긴 자료는 스킬 안 `references/`) | `skills/*/` |
| Lab 4 공개 하네스에서 가져올 단계 | `skills/fix-with-tests/SKILL.md` |
| Lab 5 verifier 확인 항목 | `agents/verifier.md` |
| Lab 7 평가셋·지표 | `eval/` |

코드가 필요하면 직접 쓰지 말고 Claude Code 에게 시킨다.

## 2. 검사 · 불러오기

```bash
claude plugin validate ./lab8_final_plugin/my-harness            # 플러그인 매니페스트
claude plugin validate ./lab8_final_plugin/my-harness --strict   # 경고도 실패로 (CI 용)
claude plugin validate ./lab8_final_plugin                       # 마켓플레이스 매니페스트
claude --plugin-dir ./lab8_final_plugin/my-harness               # 이번 세션에만 불러오기
```

불러온 세션에서: `/help` 에 `/my-harness:check` 가 보이는지 · `/agents` 에 `verifier` · 「.env 에 써줘」가 막히는지.
헤드리스로 비교: `./lab4_public_harness/run_task.sh mine` (이 폴더를 `--plugin-dir` 로 쓴다).

훅의 `python3` 이 Windows 에서 안 잡히면 `hooks/hooks.json` 에서 `python` 또는 `py` 로 바꾼다.

## 3. GitHub 에 공개

1. 새 저장소에 `lab8_final_plugin/` 의 내용을 그대로 올린다 → 저장소 루트에 `.claude-plugin/marketplace.json`, 그 옆에 `my-harness/`.
2. `marketplace.json` 의 `name`·`owner`, `plugin.json` 의 `author` 를 고친다. 비밀 값·고객 자료가 없는지 확인한다.
3. 다른 사람이 설치:
   ```
   /plugin marketplace add <GitHub 계정>/<저장소>
   /plugin install my-harness@my-team-harness
   ```
4. 버전을 올릴 때: `plugin.json` 의 `version` 을 올리고 `claude plugin tag` 로 태그 (`{name}--v{version}`).

회사 정책상 외부 공개가 안 되면 사내 Git 저장소로 같은 구조를 만든다 (`/plugin marketplace add <사내 Git URL>`).

## 4. 제출물 체크리스트

- [ ] **하네스 구성** — `my-harness/` · `claude plugin validate --strict` 통과
- [ ] **평가셋 20건** — `eval/dataset.jsonl` (까다로운 경우 8건 이상, 합성은 `reviewed: true` 만)
- [ ] **전후 비교표** — 하네스 전(하네스 미적용)·후의 정확도·환각·안전 위반·평균 토큰 (`run_suite.py` 결과 두 개 + `compare.py` 출력)
- [ ] **공개 하네스 대비 표** — Lab 4 `compare.md` (하네스 미적용 · 내 하네스 · Superpowers · gstack)
- [ ] **README** — `my-harness/README.md`: 무엇을 · 어떤 규칙으로 · 어떻게 검증하나, 쓰는 법, 알려진 한계

## 내 하네스 설계표로 시작하기

강의 시작에 고른 `../my_work_spec/내_하네스_설계표.md`를 이 폴더에 복사하고 Claude Code에 요청한다.

```
내_하네스_설계표.md를 읽고 이 업무용 하네스 초안을 my-harness/에 만들어 줘.
CLAUDE.md · Skill 1개 · Hook 규칙 · 평가 문항 5개 (엣지 케이스 2개 포함).
설계표에 없는 규칙은 지어내지 말고 TODO로 남겨.
```

| 설계표 칸 | 하네스 파일 |
|---|---|
| 출력 · 형식 | `CLAUDE.md` |
| 판단 기준 · 사내 규칙 | `skills/<업무>/SKILL.md` + 참고 자료 |
| 쓰는 시스템 · 도구 | 읽기 전용 조회 스크립트 · 도구 정의 |
| 절대 하면 안 되는 것 | `hooks/guard.py` · 권한 deny 규칙 |
| 사람 확인 지점 | 권한 ask 규칙 · 승인 단계 |
| 잘했다의 기준 · 자주 나는 실수 | `eval/dataset.jsonl` · 엣지 케이스 |

그다음 `claude plugin validate ./my-harness` → 평가 문항으로 하네스 미적용 vs 내 하네스 비교 → README에 비교표.
