# 심화 과제 (선택)

> Agent SDK 판(API 키 필요). 코드는 뼈대 예시이며, 실제로 만들 때는 Claude Code 에게 「이 뼈대로 sdk_optional/lab3_sdk_agent 코드를 고쳐서 만들어줘」라고 시킨다.
> ※ 모든 데이터는 실습용 가상 자료입니다.

## A. 자동 리뷰 Agent

PR 의 변경 내용(diff)을 읽고 팀 리뷰 기준으로 의견을 다는 Agent. 읽기 도구만 주고, 리뷰 기준은 스킬(Lab 2)로 분리한다.

```python
options = ClaudeAgentOptions(
    model=config.MODEL,
    system_prompt="너는 코드 리뷰어다. 기준: (1) 비밀 값 하드코딩 (2) 예외 처리 누락 (3) 테스트 없는 로직. "
                  "근거가 되는 줄 번호를 반드시 적고, 확신이 없으면 '확인 필요' 로 둔다.",
    allowed_tools=["Read", "Grep", "Glob", "Bash(git diff:*)"],   # 쓰기 도구 없음
    permission_mode="dontAsk",
    cwd="/path/to/repo",
)
r = await run_once("main 대비 바뀐 내용을 리뷰해서 JSON 목록으로: [{file, line, severity, comment}]", options)
```

평가: 사람이 단 리뷰 의견 20건을 정답으로 두고 재현율(놓친 지적)과 정밀도(쓸데없는 지적)를 잰다. Lab 7 의 judge 일치율 방식을 그대로 쓴다.

## B. 설계 ↔ 리뷰 반복 루프

설계 Agent 가 초안을 내면 리뷰 Agent 가 점수와 고칠 점을 주고, 기준 점수를 넘거나 횟수가 차면 멈춘다. **멈춤 조건이 없으면 비용이 끝없이 늘어난다.**

```python
MAX_ROUNDS, PASS = 3, 4
draft, feedback = None, ""
for round_no in range(1, MAX_ROUNDS + 1):
    draft = (await run_once(f"요구사항: {req}\n이전 리뷰: {feedback}\n설계안을 고쳐라.", designer_opts))["text"]
    review = extract_json((await run_once(f"이 설계안을 1–5점으로 평가: {draft}", reviewer_opts))["text"])
    print(round_no, review["score"])
    if review["score"] >= PASS:
        break
    feedback = review["issues"]
else:
    print("기준 미달 → 사람 검토로 넘김")
```

확인할 것: 라운드마다 점수·비용을 기록해서 「몇 라운드부터 점수가 더 오르지 않는가」를 본다. 같은 모델이 쓰고 같은 모델이 채점하면 점수가 후해진다 — 리뷰어는 다른 모델이나 규칙 검사와 섞는다.

## C. 장기 세션 — resume 과 compaction

여러 날 이어지는 작업(예: 설비 이력 정리)은 세션을 저장했다가 이어간다. 대화가 길어지면 Claude Code 가 앞 내용을 요약(compaction)하는데, 이때 중요한 결정이 빠질 수 있다.

```python
# 1) 세션 ID 저장
r = await run_once("3월 정기 수리 대상 설비 목록을 정리하자.", opts)
Path("session.txt").write_text(r["session_id"])

# 2) 다음 날 이어서
opts.resume = Path("session.txt").read_text()
r = await run_once("어제 정리한 목록에서 펌프만 다시 보여줘.", opts)

# 3) 요약 직전에 꼭 남길 것을 기록 (PreCompact 훅)
async def before_compact(input_data, tool_use_id, context):
    Path("decisions.log").open("a", encoding="utf-8").write(f"{input_data}\n")
    return {}
opts.hooks = {"PreCompact": [HookMatcher(hooks=[before_compact])]}
```

평가: 같은 질문을 (a) 새 세션 (b) resume 세션 (c) 요약이 일어난 뒤 세션에서 던지고, 앞에서 정한 사실을 얼마나 유지하는지 Lab 7 방식으로 점수를 매긴다. 토큰은 `cache_read` 가 늘고 `input_tokens` 가 줄어드는지 본다.
