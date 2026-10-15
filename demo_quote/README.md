# demo_quote — 하네스 없는 Agent vs 있는 Agent 실측

견적 계산 모듈(가상)에 「할인 · 할증 반영」 과제를 주고, 조건별로 여러 번 돌려 **숨은 인수 테스트 15개**로 채점한다.

| 조건 | 구성 |
|---|---|
| `bare` | 저장소만 (CLAUDE.md · .claude 없음, 내 PC 설정도 끊음) |
| `harness` | + `harness/` — CLAUDE.md · `pricing-change` Skill(정책 확정본 포함) · `verifier` Sub Agent · Hook(테스트 보호 · 끝내기 전 테스트) |
| `superpowers` | + Superpowers 플러그인 |

| 변형 | 내용 |
|---|---|
| `repo` | 2025 정책 · 2026Q3 초안 · 확정 회의록이 모두 `docs/wiki/`에 있음 |
| `ext` | 확정 회의록을 저장소에서 뺌 → 확정본은 하네스 Skill에만 |

```bash
python3 run_demo.py --variant repo --cond bare harness --k 5   # 실제 실행 (계정 사용량 소모)
python3 run_demo.py --watch ...                                 # ../agent_watch 로 실시간 보기 (서버 먼저)
python3 dashboard.py                                            # runs/dashboard.html
```

모델은 `claude-sonnet-5-5`로 고정하고, 별칭(sonnet · haiku · opus)도 5.5 세대로 묶는다 (`ANTHROPIC_DEFAULT_*_MODEL`). Claude Code 2.1.195에서 `--model sonnet`은 Sonnet 4.6을 가리키므로 꼭 전체 이름을 쓴다.

## 결과 (2026-10-14 · Claude Sonnet 5.5 · 19회)

| 변형 · 조건 | 횟수 | 숨은 테스트 (15) | 평균 토큰 (캐시 포함) | 시간 (중앙값) |
|---|---|---|---|---|
| repo · 하네스 미적용 | 5 | 15 · 15 · 15 · 15 · 15 | 31만 | 43초 |
| repo · 내 하네스 | 5 | 15 · 15 · 15 · 15 · 15 | 52만 | 92초 |
| repo · Superpowers | 3 | 0 · 0 · 0 (brainstorming이 질문하고 멈춤) | 20만 | 29초 |
| ext · 하네스 미적용 | 3 | 5 · 13 · 5 | 26만 | 46초 |
| ext · 내 하네스 | 3 | 15 · 15 · 15 | 55만 | 84초 |

- 정보가 저장소에 다 있으면 하네스 미적용도 맞춘다. 하네스는 절차(Skill → 테스트 → verifier)를 매번 지키지만 토큰 약 1.7배.
- 확정 정보가 저장소 밖에 있으면 하네스 미적용 쪽은 2025 시행본(2회) 또는 초안(1회)을 골라 틀린다. 모델은 가정을 밝혔지만 회사가 확정한 사실은 모른다.
- 회귀 테스트(5개)는 모든 실행이 통과, 회귀 테스트 파일을 고친 실행은 없음.
- 이전 Sonnet 4.6 결과는 `runs/old-sonnet46/` (저장소에는 올리지 않음).
