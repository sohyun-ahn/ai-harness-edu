# Lab 7 — 평가와 회귀 테스트

하네스를 바꿨을 때 **좋아졌는지, 무엇이 나빠졌는지**를 숫자로 본다. 평가 대상은 코드가 아니라 하네스 파일이다.

| `--agent` | 평가 대상 (고칠 파일) |
|---|---|
| `single` | `lab1_harness_vs_bare/harness/CLAUDE.md` |
| `multi` | `lab5_multiagent/project/.claude/` (agents, skills) |

## 1. 평가 설계

1. `metrics.md` — 지표·가중치를 팀 기준으로. 가중치는 `common/scoring.py` 의 `WEIGHTS` 와 맞춘다.
2. judge 와 사람 채점 일치율 (호출 없음):
   ```bash
   python lab7_eval_regression/agreement.py
   ```
   ```
   정확히 같은 점수   : 60%
   Cohen's kappa(1–5) : 0.48
   합격/불합격 일치   : 80%  (기준 4점 이상)
   ```
3. 진짜 judge (haiku · `--system-prompt` 로 기본 시스템 프롬프트를 바꾸고 도구 없음):
   ```bash
   python lab7_eval_regression/judge.py -n 10
   python lab7_eval_regression/agreement.py --judge lab7_eval_regression/judge_scores.csv
   ```
   kappa 가 낮으면 `judge_prompt.md` 를 고치고 다시.
4. 합성 케이스: `python lab7_eval_regression/make_synthetic.py -n 3` → 모든 줄 `synthetic: true, reviewed: false`. 사람이 검토하기 전에는 평가에 쓰지 않는다.

## 2. 회귀 테스트

```bash
python lab7_eval_regression/run_suite.py --track pangyo -n 10 --k 3           # 기준 결과
#  → harness/CLAUDE.md 를 고친다 (예: 「환불 약속 금지」 줄 삭제)
python lab7_eval_regression/run_suite.py --track pangyo -n 10 --k 3           # 다시
python lab7_eval_regression/compare.py results/<첫번째>.json results/<두번째>.json   # 회귀면 종료 코드 1
```

결과 없이 비교 방식만: `python lab7_eval_regression/compare.py results/sample_before.json results/sample_after.json` (품질은 올랐지만 비용 회귀로 실패) · `… sample_after_ok.json` (통과).

호출 없이 스위트 흐름만: `python lab7_eval_regression/run_suite.py -n 5 --k 2 --dry-run`

채점: 판교 — 분류 일치, `must_include` 포함률, `must_not` 위반, 없는 조항 인용(환각), `needs_human` 일치, 선택 `--judge`. 포항 — 필드 F1, 원문에 없는 숫자(환각), 견적 산수, `needs_human` 일치. 토큰은 `avg_total_tokens`(메인)·`avg_all_tokens`(서브 포함)로 남고, `compare.py` 는 토큰 20% 넘게 늘면 회귀로 본다.

`--engine sdk` 는 `sdk_optional/` 의 Agent 로 같은 채점을 한다 (API 키 필요).

CI 예시: `ci_example/eval.yml` (수동 실행 · 헤드리스 · 인증은 `CLAUDE_CODE_OAUTH_TOKEN` 또는 API 키).
