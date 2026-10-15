#!/usr/bin/env python3
"""Agent SDK로 만든 멀티에이전트 문의 응대 봇 — 분류 → 응대 → 검증 → (필요하면) 사람에게.

  pip install claude-agent-sdk          # Python 3.10+
  python bot.py --n 10                   # 앞 10건 처리 · 채점 (labs/data/pangyo)
  python bot.py --ids Q07 Q21            # 골라서

인증: API 키가 없으면 이 PC에 로그인된 Claude Code 계정으로 돈다 (내 PC · 내 사용).
사내 서비스로 배포해 여러 사람이 쓰게 하려면 API 키(또는 Bedrock · Vertex)를 쓴다.

하네스 부품
  Tool      search_kb(domain) 사내 규정 조회 · escalate(reason) 사람에게 넘김   ← create_sdk_mcp_server
  Sub Agent classifier(Haiku · 도구 없음) · responder(규정 조회만) · verifier(규정 조회만)
  Hook      PreToolUse: 허용 도구 외 차단 · PostToolUse: 근거 로그(logs/audit.jsonl)
  제한       max_turns · effort · 내 PC 설정 끊기(setting_sources=[])
"""
import argparse
import asyncio
import json
import os
import re
import time
from pathlib import Path

from claude_agent_sdk import (AgentDefinition, AssistantMessage, ClaudeAgentOptions, HookMatcher, ResultMessage,
                              TextBlock, create_sdk_mcp_server, query, tool)

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data" / "pangyo"
LOGS = HERE / "logs"
DOMAINS = {"IT": "it", "구매": "purchase", "인사": "hr", "보안": "security", "기타": "general"}
MODELS = {"ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-5-5",      # 별칭도 5.5 세대로 고정
          "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-5-5",
          "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5-5"}

# ── 도구 ────────────────────────────────────────────────
ESCALATED = {}


@tool("search_kb", "사내 규정 조회. domain: IT · 구매 · 인사 · 보안 · 기타 중 하나. 규정 원문(조항 번호 포함)을 돌려준다.",
      {"domain": str})
async def search_kb(args):
    name = DOMAINS.get(args.get("domain", "").strip(), "general")
    return {"content": [{"type": "text", "text": (DATA / "kb" / f"{name}.md").read_text(encoding="utf-8")}]}


@tool("escalate", "사람(담당자)에게 넘긴다. 규정에 없거나 판단 · 승인이 필요한 문의일 때.", {"inquiry_id": str, "reason": str})
async def escalate(args):
    ESCALATED[args.get("inquiry_id", "?")] = args.get("reason", "")
    return {"content": [{"type": "text", "text": "담당자에게 전달함"}]}


KB = create_sdk_mcp_server("kb", tools=[search_kb, escalate])
T_SEARCH, T_ESC = "mcp__kb__search_kb", "mcp__kb__escalate"

# ── Sub Agent ───────────────────────────────────────────
AGENTS = {
    "classifier": AgentDefinition(
        description="문의 분류 담당. 문의 하나를 받아 분야와 사람 필요 여부를 JSON으로 돌려준다.",
        prompt=("너는 사내 문의 분류 담당이다. 분야는 IT · 구매 · 인사 · 보안 · 기타 중 하나.\n"
                "사람이 필요한 경우: 규정 예외 요청, 개인 사정 판단, 징계 · 분쟁, 규정으로 답할 수 없는 일.\n"
                '반환: {"intent": "...", "needs_human": true|false, "why": "한 줄"} 만.'),
        tools=[], model="haiku", effort="low"),
    "responder": AgentDefinition(
        description="분야별 응대 담당. 분야와 문의를 받아 규정을 조회하고 답변 초안을 쓴다.",
        prompt=("너는 사내 응대 담당이다. 반드시 search_kb로 해당 분야 규정을 읽고 답한다.\n"
                "- 규정에 있는 내용만, 조항 번호(예: IT-1)를 함께 적는다\n"
                "- 규정에 없는 약속 · 수치 · 예외 허용은 쓰지 않는다\n"
                "- 3~4문장, 존댓말"),
        tools=[T_SEARCH], model="sonnet", effort="low"),
    "verifier": AgentDefinition(
        description="검증 담당. 문의 · 분야 · 답변 초안을 받아 규정과 대조해 통과 여부를 판정한다. 고치지 않는다.",
        prompt=("너는 검증 담당이다. search_kb로 규정을 읽고 답변 초안을 대조한다.\n"
                "실패 조건: 조항 번호 없음 · 규정에 없는 내용 · 규정과 다른 수치 · 지킬 수 없는 약속 · 분야 오분류.\n"
                '반환: {"pass": true|false, "reason": "한 줄"} 만.'),
        tools=[T_SEARCH], model="sonnet", effort="low"),
}

SUPERVISOR = """너는 사내 문의 응대 감독이다. 직접 답을 쓰지 않고 Sub Agent에게 맡긴다.
순서 (반드시 지킨다)
1. classifier에게 문의를 넘겨 분야 · 사람 필요 여부를 받는다
2. needs_human 이면 escalate 도구로 넘기고 끝낸다 (답변 초안 없이)
3. responder에게 분야와 문의를 넘겨 초안을 받는다
4. verifier에게 문의 · 분야 · 초안을 넘긴다. 실패면 이유를 붙여 responder에게 한 번만 다시 맡기고 다시 검증한다
5. 두 번째도 실패면 escalate
마지막 출력은 JSON 한 줄만:
{"id": "...", "intent": "IT|구매|인사|보안|기타 (classifier가 준 분야 이름 그대로)", "answer": "최종 답변 (사람에게 넘겼으면 빈 문자열)", "escalated": true|false, "verified": true|false}"""


# ── Hook ────────────────────────────────────────────────
ALLOWED = {"Agent", "Task", T_SEARCH, T_ESC}


async def guard(inp, tool_use_id, ctx):
    if inp.get("tool_name") not in ALLOWED:
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": f"응대 봇에서 쓰지 않는 도구: {inp.get('tool_name')}"}}
    return {}


async def audit(inp, tool_use_id, ctx):
    LOGS.mkdir(exist_ok=True)
    rec = {"t": time.time(), "tool": inp.get("tool_name"), "agent": inp.get("agent_type") or "supervisor",
           "input": inp.get("tool_input"), "session": inp.get("session_id")}
    with open(LOGS / "audit.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {}


def options():
    return ClaudeAgentOptions(
        system_prompt=SUPERVISOR, model="claude-sonnet-5-5", effort="low",
        agents=AGENTS, mcp_servers={"kb": KB},
        tools=["Agent", "Task"], allowed_tools=["Agent", "Task", T_SEARCH, T_ESC],
        hooks={"PreToolUse": [HookMatcher(hooks=[guard])], "PostToolUse": [HookMatcher(hooks=[audit])]},
        setting_sources=[], max_turns=20, cwd=str(HERE), env=MODELS,
        permission_mode="dontAsk")


async def handle(q):
    t0 = time.time()
    final, res, agents_used = "", None, []
    async for m in query(prompt=f'문의 ID {q["id"]}: {q["text"]}', options=options()):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock):
                    final = b.text
                elif getattr(b, "name", "") in ("Agent", "Task"):
                    agents_used.append((b.input or {}).get("subagent_type", "?"))
        elif isinstance(m, ResultMessage):
            res = m
    out = {}
    hit = re.search(r"\{.*\}", (res.result if res and res.result else final) or "", re.S)
    if hit:
        try:
            out = json.loads(hit.group(0))
        except json.JSONDecodeError:
            pass
    mu = (res.model_usage or {}) if res else {}
    tokens = sum(sum((v.get(k) or 0) for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens"))
                 for v in mu.values())
    usage = {k: sum((v.get(k) or 0) for v in mu.values()) for k in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")}
    return {"q": q, "out": out, "agents": agents_used, "sec": round(time.time() - t0, 1), "tokens": tokens, "usage": usage,
            "models": sorted(mu.keys()), "escalated_tool": q["id"] in ESCALATED}


def grade(r):
    q, o = r["q"], r["out"]
    esc = bool(o.get("escalated")) or r["escalated_tool"]
    ans = o.get("answer") or ""
    g = {"intent": o.get("intent") == q["gold_intent"], "escalate": esc == q["needs_human"]}
    if not q["needs_human"] and not esc:
        g["include"] = all(k in ans for k in q["must_include"])
        g["not"] = not any(k in ans for k in q["must_not"])
    g["ok"] = all(g.values())
    return g


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    qs = [json.loads(l) for l in (DATA / "inquiries.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    qs = [q for q in qs if q["id"] in a.ids] if a.ids else qs[:a.n]
    sem = asyncio.Semaphore(a.parallel)

    async def run(q):
        async with sem:
            return await handle(q)
    rs = await asyncio.gather(*[run(q) for q in qs])
    ok = 0
    for r in rs:
        g = grade(r)
        ok += g["ok"]
        print(f'{r["q"]["id"]} {"O" if g["ok"] else "X"}  분류 {r["out"].get("intent", "-"):<3} (정답 {r["q"]["gold_intent"]})'
              f'  사람 {"예" if r["out"].get("escalated") or r["escalated_tool"] else "-"}  위임 {"→".join(r["agents"])}'
              f'  {r["sec"]}s  {r["tokens"]:,}토큰  {",".join(m.replace("claude-", "") for m in r["models"])}'
              f'  {" ".join(k for k, v in g.items() if not v and k != "ok")}')
    print(f"\n정답 {ok}/{len(rs)} · 평균 {sum(r['sec'] for r in rs) / len(rs):.0f}초 · 평균 {sum(r['tokens'] for r in rs) / len(rs):,.0f}토큰")
    LOGS.mkdir(exist_ok=True)
    (LOGS / "last_run.json").write_text(json.dumps([{**r, "grade": grade(r)} for r in rs], ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
