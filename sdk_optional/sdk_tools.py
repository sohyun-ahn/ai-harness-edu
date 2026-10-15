"""Agent 가 쓰는 사용자 정의 도구 — 지식베이스 검색(판교), 단가 조회(포항)."""
from claude_agent_sdk import create_sdk_mcp_server, tool

from common.data import find_price, load_kb


def _text(s):
    return {"content": [{"type": "text", "text": s}]}


@tool("search_kb", "사내 FAQ 에서 관련 조항을 찾는다. 조항 ID(예: IT-3)와 내용을 돌려준다.", {"query": str})
async def search_kb(args):
    words = [w for w in args["query"].split() if len(w) >= 2]
    kb = load_kb()
    scored = sorted(kb.items(), key=lambda kv: -sum(w in kv[1] or w in kv[0] for w in words))
    top = [f"[{cid}] {body}" for cid, body in scored[:3]]
    return _text("\n".join(top) if top else "관련 조항 없음")


@tool("get_price", "단가표에서 품목·규격의 단가(원)를 찾는다.", {"item": str, "spec": str})
async def get_price(args):
    row = find_price(args["item"], args["spec"])
    if row is None:
        return _text(f"단가표에 없음: {args['item']} / {args['spec']}")
    return _text(f"{row['품목']} | {row['규격']} | 단위 {row['단위']} | 단가 {row['단가']}원")


# 서버 이름이 "tools" 이므로 Agent 쪽 도구 이름은 mcp__tools__search_kb 형식이 된다.
SERVER = create_sdk_mcp_server(name="tools", version="1.0.0", tools=[search_kb, get_price])
TOOL_NAMES = {"pangyo": ["mcp__tools__search_kb"], "pohang": ["mcp__tools__get_price"]}
