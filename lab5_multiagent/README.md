# Lab 5 — 멀티에이전트: Supervisor + 서브에이전트

메인(Supervisor)은 직접 일하지 않고 **순서를 지키며 맡기고, 검증한다.** 서브에이전트는 각자 컨텍스트에서 일하고 요약만 돌려준다.

| 트랙 | 순서 (스킬이 강제) | 서브에이전트 (`project/.claude/agents/`) |
|---|---|---|
| pangyo | classifier → responder-<분야> → verifier-inquiry | `classifier`(haiku) · `responder-it/buy/hr/sec/general`(sonnet, Read·Grep) · `verifier-inquiry`(haiku) |
| pohang | extractor → estimator → verifier-quote | `extractor`(sonnet) · `estimator`(haiku, Grep 으로 단가표) · `verifier-quote`(haiku) |

지휘 절차는 `project/.claude/skills/orchestrate-<track>/SKILL.md`. 검증 실패 시 한 번만 다시, 그래도 실패면 `needs_human`.

## 1. 실행 → 이벤트 저장 → 타임라인

```bash
python lab5_multiagent/run.py --track pangyo --ids Q10
python lab5_multiagent/run.py --track pohang --ids S06
python lab5_multiagent/run.py --track pangyo --dry-run              # sample_events.jsonl 로
python lab5_multiagent/visualize.py lab5_multiagent/sample_events.jsonl -o lab5_multiagent/sample_timeline.html
```

- `run.py` 는 `claude -p --output-format stream-json --verbose` 로 돌리고, 받은 시각(`_ts`)을 붙여 `runs/*.jsonl` 로 저장한다.
- 서브에이전트 안에서 나온 이벤트에는 `parent_tool_use_id`(= 메인의 `Agent` 호출 id)가 붙는다 → 이것으로 줄을 나눈다.
- 콘솔에는 줄별 토큰, 위임 순서와 기대 순서 일치 여부, 코드 검증(`common/checks.py`) 결과가 나온다.
- `sample_timeline.html` 을 브라우저로 연다. 막대에 마우스를 올리면 도구 입력·결과가 보인다.

대화형으로: `cd <작업 폴더> && claude` → `/agents` 로 목록 확인 → 「orchestrate-inquiry 로 처리: 납품 부품 불량인데 환불해 주실 거죠?」.

## 해 볼 것

1. `SKILL.md` 에서 3번(검증) 단계를 지운다 → 타임라인에서 verifier 줄이 사라지고, `EXPECTED` 순서 확인이 X.
2. `verifier-inquiry.md` 의 `model` 을 `sonnet` 으로 → 줄별 토큰과 시간 변화.
3. `responder-buy.md` 에서 「환불 약속 금지」 줄을 지우고 Q10 → verifier 가 잡는가, 재시도가 일어나는가.
4. 판교 `Q26`(프롬프트 주입), 포항 `S07`(수량 누락)을 넣어 본다.
5. 서브에이전트 줄의 토큰 합과 메인 토큰을 비교 — 「메인 컨텍스트는 작게, 전체 비용은?」

## 2. (선택·실험 기능) Agent Teams 와 비교

> **실험 기능.** 이름·동작·설정 방법이 바뀔 수 있다. 이 저장소에서는 검증하지 않았다. 토큰을 훨씬 많이 쓴다.

서브에이전트는 **메인에게만** 보고한다. Agent Teams 는 리더 하나와 팀원 여럿이 **작업 목록과 메일함을 같이 쓰며** 서로 직접 말을 주고받는다.

```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1      # Windows: $env:CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"
claude
> 팀을 만들어 줘: 분류 담당, 답변 담당, 검증 담당. 검증 담당은 답변 담당에게 직접 고칠 점을 보내.
```

| | 서브에이전트 (이 Lab) | Agent Teams |
|---|---|---|
| 보고 | 메인에게만, 끝날 때 요약 한 번 | 팀원끼리 메일함으로 수시로 |
| 일 나누기 | 메인이 순서대로 맡김 | 공유 작업 목록에서 각자 가져감 |
| 컨텍스트 | 각자 따로, 메인은 요약만 받음 | 각자 따로 (세션 여러 개) |
| 잘 맞는 일 | 순서가 정해진 처리 · 검증 관문 | 서로 반박·토론이 필요한 조사, 큰 병렬 작업 |
| 비용 | 낮음~중간 | 높음 |

비교할 것: 같은 문의를 두 방식으로 → 걸린 시간, 토큰(대화형 `/context`), 검증 단계를 건너뛰었는가.
