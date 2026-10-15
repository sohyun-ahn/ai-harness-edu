"""[SDK 전용 · ANTHROPIC_API_KEY 필요] SDK 한 번 실행하고 결과·토큰·비용을 dict 로 돌려주는 도우미."""
import json

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, query

from common.parse import extract_json  # noqa: F401  (예전 import 경로 유지)


async def run_once(prompt, options, verbose=False) -> dict:
    """query() 한 번 실행 → {text, cost, turns, 토큰, 지연, session_id}."""
    out = {"text": "", "cost": 0.0, "turns": 0, "input_tokens": 0,
           "output_tokens": 0, "cache_read": 0, "duration_ms": 0,
           "session_id": None, "subtype": None, "is_error": False}
    async for message in query(prompt=prompt, options=options):
        if verbose and isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print("  [assistant]", block.text[:120].replace("\n", " "))
                elif hasattr(block, "name"):  # ToolUseBlock
                    print("  [tool]", block.name, json.dumps(block.input, ensure_ascii=False)[:120])
        if isinstance(message, ResultMessage):
            usage = message.usage or {}  # main loop 토큰만 들어 있다
            out.update(
                text=message.result or "",
                cost=message.total_cost_usd or 0.0,
                turns=message.num_turns,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_read=usage.get("cache_read_input_tokens", 0),
                duration_ms=message.duration_ms,
                session_id=message.session_id,
                subtype=message.subtype,
                is_error=message.is_error,
            )
    return out
