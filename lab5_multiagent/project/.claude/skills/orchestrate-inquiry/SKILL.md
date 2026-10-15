---
name: orchestrate-inquiry
description: 사내 문의를 classifier → responder-<분야> → verifier-inquiry 순서로 처리하는 지휘 절차. 사내 문의 처리 요청이면 쓴다.
---

# 사내 문의 처리 순서 (건너뛰지 않는다)

<!-- TODO(실습): 순서·재시도 횟수·출력 칸을 바꿔 보세요. 단계를 빼면 타임라인(visualize.py)에서 바로 보인다. -->

1. `classifier` 에게 문의 원문을 그대로 넘긴다 → 라벨.
2. 라벨에 맞는 담당에게 문의 원문을 넘긴다: IT→`responder-it`, 구매→`responder-buy`, 인사→`responder-hr`, 보안→`responder-sec`, 기타→`responder-general`.
3. `verifier-inquiry` 에게 문의 원문 + 초안 + 근거 ID 를 넘긴다.
4. verdict 가 fail 이면 문제를 붙여 2번을 **한 번만** 다시 하고 3번을 다시 한다. 그래도 fail 이면 needs_human true.
5. 메인은 직접 답을 쓰거나 조항을 찾지 않는다. 결과를 모아 아래 JSON 하나만 출력한다.

```json
{"intent": "구매", "reply": "답변 3문장 이내", "citations": ["BUY-4"], "needs_human": true,
 "verdict": "pass", "reason": "검증 메모", "trace": ["classifier", "responder-buy", "verifier-inquiry"]}
```
