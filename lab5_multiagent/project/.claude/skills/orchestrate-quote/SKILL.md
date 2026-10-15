---
name: orchestrate-quote
description: 사양서를 extractor → estimator → verifier-quote 순서로 처리하는 지휘 절차. 사양서 추출·견적 요청이면 쓴다.
---

# 사양서 처리 순서 (건너뛰지 않는다)

<!-- TODO(실습): 순서·재시도 횟수·출력 칸을 바꿔 보세요. -->

1. `extractor` 에게 사양서 원문 전체를 넘긴다 → 품목 JSON.
2. `estimator` 에게 품목 JSON 을 넘긴다 → 견적.
3. `verifier-quote` 에게 원문 + 품목 JSON + 견적을 넘긴다.
4. verdict 가 fail 이면 문제를 붙여 해당 단계(1 또는 2)를 **한 번만** 다시 하고 3번을 다시 한다. 그래도 fail 이면 needs_human true.
5. 메인은 직접 추출·계산하지 않는다. 결과를 모아 아래 JSON 하나만 출력한다.

```json
{"items": [{"품목": "", "규격": "", "재질": "", "수량": 0, "단위": "EA", "비고": ""}],
 "quote": {"lines": [{"품목": "", "규격": "", "수량": 0, "단가": 0, "금액": 0}], "total": 0},
 "needs_human": false, "verdict": "pass", "reason": "검증 메모", "trace": ["extractor", "estimator", "verifier-quote"]}
```
