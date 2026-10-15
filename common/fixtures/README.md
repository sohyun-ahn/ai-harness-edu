# 저장된 헤드리스 출력 (dry-run 용)

`--dry-run` 을 붙이면 `common/headless.py` 가 `claude` 를 부르지 않고 이 파일들을 실제 출력처럼 파싱한다.
숫자·답은 **예시**다 — 흐름과 표·그림 모양을 확인하는 용도로만 쓴다.

| 파일 | 형식 | 쓰는 곳 |
|---|---|---|
| `*.json` | `claude -p --output-format json` 의 result 객체 (목록이면 부를 때마다 다음 것, `파일#키` 로 고름) | Lab 1·3·6·7 |
| `*.jsonl` | `--output-format stream-json --verbose` 이벤트 (+ 받은 시각 `_ts`) | Lab 2·4·5 |
| `default.json`, `default_stream.jsonl` | 맞는 저장본이 없을 때 | — |

실제로 한 번 돌린 결과(`lab5_multiagent/runs/*.jsonl` 등)를 여기에 복사해 저장본으로 써도 된다.
