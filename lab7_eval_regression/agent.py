"""평가 대상 Agent 실행기 — 같은 입력을 엔진(headless | sdk)과 구성(single | multi)에 따라 돌린다.

single = lab1 하네스 (lab1_harness_vs_bare/harness/CLAUDE.md + 근거 자료)
multi  = lab5 멀티에이전트 (lab5_multiagent/project/.claude)
→ 「하네스를 바꾸기 전후」 = 위 파일을 고치기 전후. 코드는 고치지 않는다.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import config, headless, workspace
from common.parse import extract_json

ASK_SINGLE = {
    "pangyo": "[pangyo] 다음 사내 문의를 IT/구매/인사/보안/기타 중 하나로 분류하고 답변해 주세요.\n\n문의: {x}",
    "pohang": "[pohang] 다음 사양서에서 품목·규격·재질·수량·단위·비고를 뽑고 견적을 내 주세요.\n\n{x}",
}
ASK_MULTI = {
    "pangyo": "orchestrate-inquiry 스킬 순서대로 다음 사내 문의를 처리해 줘.\n\n문의: {x}",
    "pohang": "orchestrate-quote 스킬 순서대로 다음 사양서를 처리해 줘.\n\n{x}",
}
_ws = {}


def _workspace(track, agent):
    key = (track, agent)
    if key not in _ws:
        if agent == "single":
            _ws[key] = workspace.build(f"lab7-single-{track}", track=track,
                                       copy={"CLAUDE.md": ROOT / "lab1_harness_vs_bare" / "harness" / "CLAUDE.md"})
        else:
            proj = ROOT / "lab5_multiagent" / "project"
            _ws[key] = workspace.build(f"lab7-multi-{track}", track=track,
                                       copy={"CLAUDE.md": proj / "CLAUDE.md", ".claude": proj / ".claude"})
    return _ws[key]


def solve(case, track, agent="single", engine="headless", dry_run=False):
    """케이스 하나 → {output(JSON 또는 None), text, 토큰들, cost, duration_ms, ...}."""
    if engine == "sdk":
        return _solve_sdk(case, track, agent)
    tools = "Read,Grep,Glob" if agent == "single" else "Read,Grep,Glob,Skill,Agent"
    ask = ASK_SINGLE if agent == "single" else ASK_MULTI
    r = headless.run(ask[track].format(x=case["input"]), cwd=_workspace(track, agent), model=config.HEADLESS_MODEL,
                     setting_sources="project", tools=None if agent == "multi" else tools, allowed_tools=tools,
                     dry_run=dry_run, fixture=f"lab7_{track}.json#{case['id']}")
    r["output"] = extract_json(r["text"])
    return r


def _solve_sdk(case, track, agent):
    """[API 키 필요] sdk_optional 의 Agent 로. 결과 모양을 headless 와 맞춘다."""
    from sdk_optional.lab3_sdk_agent.agent_multi import run_with_retry
    from sdk_optional.lab3_sdk_agent.agent_single import run_single
    r = asyncio.run(run_single(case["input"], track) if agent == "single" else run_with_retry(case["input"], track))
    r.setdefault("cache_write", 0)
    r["total_tokens"] = r.get("input_tokens", 0) + r.get("output_tokens", 0) + r.get("cache_read", 0)
    r.setdefault("all_tokens", r["total_tokens"])
    return r
