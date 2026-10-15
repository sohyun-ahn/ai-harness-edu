# my-harness

> TODO(실습): 한 문단으로 — 어떤 업무를, 어떤 규칙으로, 어떻게 검증하는 하네스인가.

| 구성 | 파일 | 하는 일 |
|---|---|---|
| 스킬 | `skills/answer-with-evidence` | 근거 찾기 → 답 → 자체 검증 |
| 스킬 | `skills/fix-with-tests` | 테스트 먼저 → 최소 수정 → 다시 테스트 |
| 서브에이전트 | `agents/verifier.md` | 읽기 전용 검증, haiku |
| 명령 | `commands/check.md` | `/my-harness:check` |
| 훅 | `hooks/hooks.json` → `guard.py` | rm -rf · git push --force · .env 쓰기 차단 |
| 평가셋 | `eval/dataset.jsonl` | 20건 이상 |

## 쓰는 법

```bash
claude --plugin-dir ./my-harness            # 이번 세션만
```

## 전후 비교

| 지표 | 하네스 전 | 하네스 후 |
|---|---|---|
| 정확도 | | |
| 환각 | | |
| 안전 위반 | | |
| 평균 토큰 | | |
