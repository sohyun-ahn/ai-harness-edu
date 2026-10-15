# Agent SDK 멀티에이전트 문의 응대 봇

`bot.py` — 감독(Sonnet 5.5)이 Sub Agent 셋에게 맡긴다: classifier(Haiku 5.5 · 도구 없음) → responder(규정 조회) → verifier(규정 조회 · 판정). 실패하면 한 번 재작업, 사람이 필요하면 escalate.

- 도구: `search_kb` · `escalate` (SDK 안에서 만든 도구 — `create_sdk_mcp_server`)
- Hook: 허용 도구 외 차단 · 모든 도구 호출을 `logs/audit.jsonl`에 기록 (근거 로깅)
- 채점: `labs/data/pangyo/inquiries.jsonl` 의 정답 분야 · 필수 포함 · 금지 표현 · 사람 필요 여부

```bash
python3.12 -m venv .venv && .venv/bin/pip install claude-agent-sdk
.venv/bin/python bot.py --n 10
```

## 인증
- 내 PC에서 내가 돌릴 때: API 키가 없으면 로그인된 Claude Code 계정으로 돈다 (Max 계정으로 확인).
- 서비스로 띄워 다른 사람이 쓰게 할 때: **API 키(Claude Console) 또는 Bedrock · Vertex · Foundry가 필요하다.** 구독 로그인으로 다른 사람의 요청을 처리하는 것은 허용되지 않는다 ([Claude Code 법률 · 규정 문서](https://code.claude.com/docs/en/legal-and-compliance)).

## 실측 (2026-10-14 · 10건)
정답 8/10 · 평균 27초 · 평균 25만 토큰(대부분 캐시 읽기 19.6만 · 캐시 쓰기 5만)
