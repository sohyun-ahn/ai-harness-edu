# Lab 6 — 토큰 경제학

고정 과제 5개(`tasks.json`: 분류·추출·요약·코드 설명·테스트 실행)에 **레버를 하나씩** 걸고 토큰을 잰다. Business 요금제에서는 `cost` 가 실제 청구와 다를 수 있어 **토큰으로** 비교한다.

| 레버 | 무엇을 바꾸나 | 줄어드는 곳 |
|---|---|---|
| `brief` | `--append-system-prompt` 로 「답만, 최대 3줄」 | out |
| `haiku` · `sonnet` · `opus` | `--model` (분류·추출 과제만) | 단가 — 토큰 수보다 모델별 단가 차이가 크다 |
| `cache` | 긴 고정 앞부분을 붙여 같은 요청 3번 | 2·3회차의 새 입력 → 캐시 읽기로 |
| `subagent` | `--agents` 로 요약을 haiku 서브에이전트에 | 메인 컨텍스트 (전체는 아님) |
| `caveman` | 출력 말투를 극단적으로 줄이는 플러그인 | out |
| `ponytail` | 플러그인 (동작은 README 확인) | 확인 필요 |
| `rtk` | 셸 명령 출력(테스트·git·ls)을 줄여서 넘기는 CLI 프록시 | 도구 결과로 들어가는 입력 |

```bash
python lab6_tokens/bench.py --levers baseline,brief
python lab6_tokens/bench.py --levers haiku,sonnet,opus
python lab6_tokens/bench.py --levers cache,subagent
python lab6_tokens/bench.py --levers all --dry-run
python lab6_tokens/quiz.py              # quiz.md 정답
```

결과는 `results/tokens_<시각>.json`. 표 두 개가 나온다 — 레버 × 과제, 기준선 대비 (같은 과제끼리).

## 플러그인 설치 (대화형 Claude Code 안에서)

```
/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman

/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

- 플러그인을 켜는 방법(명령·자동)은 각 README 를 확인하고 `bench.py` 의 `prefix` 를 맞춘다. 기본값 `/caveman ` 은 확인 필요.
- 플러그인 레버는 `--setting-sources=user` 로 돈다 → 내 PC 에 설치한 다른 플러그인·CLAUDE.md 도 같이 들어온다. 비교 전후에 `/plugin` 으로 나머지를 꺼 둔다.
- 안 깔려 있으면 그 레버는 `[건너뜀]` 으로 넘어간다.

**rtk** — 명령 출력 압축 CLI. 설치 방법은 공식 README 확인. 설치 후 `rtk --version` 이 되면 `--levers baseline,rtk --tasks t5` 로 비교한다.

## 해 볼 것

1. `quiz.md` 에 예상값을 먼저 적고 돌린다.
2. `BRIEF` 문장을 바꿔 out 이 더 줄어드는지. 답의 품질(맞았나)도 같이 본다 — 짧아도 틀리면 손해.
3. `cache` 의 앞부분 맨 앞에 시각 문자열을 넣으면? (캐시가 깨진다 → 캐시 쓰기가 매번)
4. 레버를 겹쳐 본다: `LEVERS` 에 `haiku` + `brief` 조합을 하나 추가해 달라고 Claude Code 에게 시킨다.
