# Lab 3 — 컨텍스트 엔지니어링

컨텍스트 창에 **무엇이, 언제** 들어가는지를 바꾸고 토큰으로 잰다.

| 실험 | A | B | 기대 |
|---|---|---|---|
| a | `a_bloated` 매뉴얼 전문을 CLAUDE.md 에 | `a_lean` 짧은 CLAUDE.md + 매뉴얼은 스킬 | 매뉴얼이 필요 없는 질문에서 B 의 입력이 훨씬 작다 |
| b | `b_whole` 로그를 통째로 Read | `b_grep` Grep 으로 그 줄만 | B 가 훨씬 작다. 답은 같아야 한다 |
| c | `c_inline` 메인이 직접 조사 | `c_subagent` researcher(haiku)에게 위임 | B 의 **메인** 토큰이 작다. 전체 토큰은 비슷하거나 더 클 수도 |
| d | `d_long` 4턴 이어온 세션의 끝 질문 | `d_fresh` 새 세션에서 같은 질문 | 같은 질문인데 A 가 더 크다 — 앞 대화가 매번 따라 들어간다 |

```bash
python lab3_context/run.py --exp a
python lab3_context/run.py --exp all --dry-run
```

```
=== 실험 a ===
변형       설명                       in  캐시읽기  캐시쓰기  out  메인 토큰  전체 토큰  턴
---------  -------------------------  --  --------  --------  ---  ---------  ---------  --
a_bloated  CLAUDE.md 에 매뉴얼 전문     …
a_lean     짧은 CLAUDE.md + 스킬        …
```

- 작업 폴더는 매번 임시 폴더(`…/labs-ws/lab3-<변형>`)에 새로 만든다. 경로가 출력된다.
- 로그(`data/equipment_log.csv`, 1,500줄)는 실행할 때 만든다. 가상 자료다.
- 캐시 읽기가 큰 것은 Claude Code 시스템 프롬프트·도구 설명이 이미 캐시에 있어서다. 변형끼리는 **메인 토큰 차이**를 본다.
- 결과: `lab3_context/results/context_<exp>.json`

## 대화형으로 들여다보기: `/context`, `/compact`

```bash
cd <출력된 작업 폴더>     # 예: /tmp/labs-ws/lab3-a_bloated
claude
```

1. `/context` — Memory files(CLAUDE.md), Skills, Custom agents, Messages 가 각각 몇 토큰인지. `a_bloated` 와 `a_lean` 을 나란히 비교한다.
2. 질문 몇 개를 주고받은 뒤 다시 `/context` → Messages 가 늘어난 만큼 다음 질문마다 다시 들어간다.
3. `/compact 결정 사항과 설비 ID 만 남겨` — 앞 대화를 요약으로 바꾼다. 다시 `/context` 로 줄어든 양을 본다.
4. 요약 뒤에 앞에서 정한 사실을 물어 본다 → 빠진 것이 있는가. 남길 것은 `/compact` 뒤 지시로 적는다.
5. `/clear` — 완전히 새로 시작. 일이 바뀌면 이어가지 말고 새로 연다 (실험 d).

## 해 볼 것

1. `a_lean/SKILL.md` 의 `description` 을 「매뉴얼」 한 단어로 줄이고 매뉴얼이 **필요한** 질문(예: 「P-210 점검 주기는?」)을 `QUESTION["a"]` 에 → 스킬이 불리는가.
2. `b_grep/CLAUDE.md` 의 「파일 전체를 Read 하지 않는다」를 지우면 무엇을 하나.
3. `c_subagent/agents.json` 의 `model` 을 `sonnet` 으로 → 전체 토큰은 비슷해도 비싼 모델이 쓴 양이 늘어난다.
4. `D_TURNS` 를 8개로 늘린다 → 끝 질문의 입력이 어떻게 늘어나는가.
