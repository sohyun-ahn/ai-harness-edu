# 평가셋 (eval/)

- `dataset.jsonl` — 한 줄에 한 건. 지금 3건은 형식 예시다. **20건 이상**으로 채운다.
- 구성 권장: 평범한 경우 12 · 까다로운 경우 8 (두 의도, 프롬프트 주입, 범위 밖, 정보 부족, 수량 불일치·누락 …).
- 정답 필드는 `data/README.md` 의 형식을 따른다 (판교: `gold_intent`, `must_include`, `must_not`, `needs_human` / 포항: `items`, `needs_human`).
- 합성 케이스는 `synthetic: true, reviewed: false` 로 넣고, 사람이 검토한 뒤 `reviewed: true` 로 바꾼다.
- 돌리는 법: `lab7_eval_regression/run_suite.py` 를 이 데이터셋으로 돌리도록 Claude Code 에게 시킨다 (예: 「run_suite.py 에 --dataset 옵션을 추가해서 my-harness/eval/dataset.jsonl 을 읽게 해줘」).
