# Lab 1 — 하네스 미적용 vs 하네스

같은 입력을 N번 넣는다. 바뀌는 것은 **작업 폴더**뿐이다.

| | 작업 폴더 | 설정 | 도구 |
|---|---|---|---|
| (a) 하네스 미적용 | 빈 임시 폴더 | `--setting-sources=` (내 PC 의 CLAUDE.md·설정 안 읽음) | `--tools ""` (없음) |
| (b) 하네스 | `harness/CLAUDE.md` + `data/`(FAQ 또는 단가표) | `--setting-sources=project` | `Read,Grep,Glob` |

Claude Code 기본 시스템 프롬프트는 양쪽 다 남아 있다. 빼는 것은 **우리가 붙인 하네스**뿐이다.

```bash
python lab1_harness_vs_bare/run.py --track pangyo -n 5 --show-cmd
python lab1_harness_vs_bare/run.py --track pohang -n 5
python lab1_harness_vs_bare/run.py --track pangyo -n 3 --dry-run     # 할당량 0
```

```
=== (a) 하네스 미적용 (5회) · 작업 폴더 /tmp/labs-ws/lab1-bare ===
 1. 라벨=IT(본문에서 추정) | in 3 + 캐시읽기 0 + 캐시쓰기 4,812 / out 318 = 5,133 | 턴 1 | 7421ms
 …
 → 서로 다른 라벨 2개 (최빈 'IT(본문에서 추정)' 3/5) | 서로 다른 답 5개 | JSON 형식 0/5 | 평균 토큰 …
=== (b) 하네스 (5회) …
 → 서로 다른 라벨 1개 (최빈 'IT' 5/5) | … | JSON 형식 5/5 | …
```

## 해 볼 것

1. `harness/CLAUDE.md` 의 출력 형식 블록을 지우고 다시 → JSON 형식 비율·서로 다른 답 수.
2. 규칙 한 줄 추가 → 평균 토큰이 얼마나 느나. CLAUDE.md 는 **매 호출마다** 들어간다.
3. 「근거 찾는 법」 줄을 지우고 → 턴 수(도구 호출)와 토큰.
4. 작업 폴더로 들어가서 직접 본다: `cd <출력된 작업 폴더> && claude` → `/context`

`SAMPLE_ID` 로 입력을 바꾼다. 까다로운 입력: 판교 `Q25`(두 의도) · `Q26`(프롬프트 주입), 포항 `S06`(수량 불일치) · `S07`(수량 누락).
