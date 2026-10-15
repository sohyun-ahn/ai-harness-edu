# (선택) Agent SDK 판 실습

> **`ANTHROPIC_API_KEY` 가 필요하다.** Business(Team) 계정 로그인만으로는 돌지 않는다. 키가 없으면 건너뛴다.
> 본 실습(Lab 1~8)은 헤드리스(`claude -p`)로 같은 내용을 다룬다.

Claude Code 를 파이썬 코드 안에서 부르는 판이다. 사용자 정의 도구(`search_kb`·`get_price`)를 MCP 서버로 붙이고, 훅·서브에이전트·재시도를 코드로 짠다.

```bash
pip install -r sdk_optional/requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."          # Windows: $env:ANTHROPIC_API_KEY = "sk-ant-..."
```

| 파일 | 헤드리스 판 | 실행 |
|---|---|---|
| `lab1_compare_runs/compare_runs.py` + `harness_prompt.md` | Lab 1 | `python sdk_optional/lab1_compare_runs/compare_runs.py --track pangyo -n 5` |
| `sdk_hook.py` (규칙은 Lab 2 `guard_rules.py` 공용) | Lab 2 | `python sdk_optional/sdk_hook.py` |
| `lab3_sdk_agent/agent_single.py` | Lab 7 single | `python sdk_optional/lab3_sdk_agent/agent_single.py --track pohang -n 3` |
| `lab3_sdk_agent/agent_multi.py` (Supervisor·재시도·대체 경로) | Lab 5 | `python sdk_optional/lab3_sdk_agent/agent_multi.py --track pangyo --ids Q10 Q26` |
| `lab3_sdk_agent/resume_demo.py` (세션 이어가기) | Lab 3 d | `python sdk_optional/lab3_sdk_agent/resume_demo.py` |
| 평가 스위트 | Lab 7 | `python lab7_eval_regression/run_suite.py --engine sdk -n 5 --k 2` |
| `advanced.md` | — | 자동 리뷰 Agent · 설계↔리뷰 루프 · 장기 세션 |

- 모델 이름·예산 상한: `common/config.py` 의 `MODEL`, `JUDGE_MODEL`, `MAX_BUDGET_USD`.
- 결과마다 비용(`$`)이 찍힌다. API 키 요금은 실제 청구액이다.
- 공용 도우미: `sdk_run.py`(실행·토큰 집계), `sdk_tools.py`(사용자 정의 도구).
