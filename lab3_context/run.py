"""Lab 3 — 컨텍스트 엔지니어링 실험 4가지. 변형마다 헤드리스 한 번(또는 몇 번) 돌려 토큰을 표로 비교한다.

실행:  python lab3_context/run.py --exp a          (a·b·c·d 중 하나, 또는 all)
       python lab3_context/run.py --exp all --dry-run
고칠 곳: 각 변형 폴더의 CLAUDE.md · a_lean/SKILL.md · c_subagent/agents.json · 아래 QUESTION·D_TURNS

  a  매뉴얼을 CLAUDE.md 에 통째로      vs  CLAUDE.md 는 짧게 + 매뉴얼은 스킬로
  b  로그 파일을 통째로 읽기            vs  Grep 으로 필요한 줄만
  c  조사를 메인 대화에서 직접          vs  researcher 서브에이전트에게 위임
  d  긴 세션(같은 세션을 이어서) 끝 질문 vs  새 세션에서 같은 질문

표 읽는 법: 메인 토큰 = 메인 대화가 쓴 토큰(컨텍스트 크기에 비례). 전체 토큰 = 서브에이전트까지 합친 값.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import config, headless, workspace

HERE = Path(__file__).resolve().parent
MANUAL = (HERE / "manual.md").read_text(encoding="utf-8")

# TODO(실습): 질문을 바꿔 보세요. a 는 「매뉴얼이 필요 없는 질문」일 때 차이가 가장 크다.
QUESTION = {
    "a": "다음 문의를 IT/구매/인사/보안/기타 중 하나로만 분류해. 한 단어로. 문의: 모니터 화면이 깜빡여요",
    "b": "P-207 설비의 정지 시간(downtime_min)이 가장 긴 3건을 날짜와 함께 알려줘.",
    "c": "펌프(P- 로 시작) 설비의 고장 패턴을 조사해서 3줄로 요약하고, 그 요약으로 다음 달 정비 계획을 5줄로 써줘.",
}
# TODO(실습): d 의 앞선 대화. 길수록 끝 질문의 입력 토큰이 커진다.
D_TURNS = [
    "매뉴얼 3장(설비 정비 일반 기준)을 요약해줘.",
    "부록 A 에서 원심펌프 점검 주기를 모두 표로 보여줘.",
    "안전 수칙 4.1~4.5 를 신입 사원용 문장으로 바꿔줘.",
    "출장비 규정을 예시 하나로 설명해줘.",
]
D_FINAL = "노트북 교체는 어디에 신청해? 한 줄로."


# ---------------------------------------------------------------- 실습 자료 (가상 설비 이력)
def make_log(rows=1500, seed=7):
    """가상 설비 이력 CSV — 매번 같은 내용. 크기가 커서 통째로 읽으면 토큰이 많이 든다."""
    rnd = random.Random(seed)
    kinds = {"P": "원심펌프", "M": "전동기", "C": "컨베이어", "F": "송풍기", "R": "감속기"}
    ids = [f"{k}-{n}" for k in kinds for n in range(201, 216)]
    events = [("정기점검", 0, "이상 없음"), ("진동 상승", 30, "베어링 마모 의심"), ("돌발 정지", 90, "과부하 트립"),
              ("누설", 45, "메커니컬 씰 교체"), ("온도 상승", 20, "윤활유 보충"), ("소음", 15, "커플링 정렬")]
    lines = ["date,equip_id,type,event,downtime_min,note"]
    for i in range(rows):
        eid = rnd.choice(ids)
        ev, base, note = rnd.choice(events)
        day = f"2026-{1 + i * 9 // rows:02d}-{1 + rnd.randrange(28):02d}"
        lines.append(f"{day},{eid},{kinds[eid[0]]},{ev},{base + rnd.randrange(0, 40) if base else 0},{note}")
    return "\n".join(lines) + "\n"


def skill_md():
    return (HERE / "a_lean" / "SKILL.md").read_text(encoding="utf-8") + "\n" + MANUAL


VARIANTS = {
    # 키: (실험, 설명, 작업 폴더 만들기, run() 옵션)
    "a_bloated": ("a", "CLAUDE.md 에 매뉴얼 전문", lambda: workspace.build("lab3-a_bloated", write={
        "CLAUDE.md": (HERE / "a_bloated" / "CLAUDE.md").read_text(encoding="utf-8") + MANUAL}), {}),
    "a_lean": ("a", "짧은 CLAUDE.md + 스킬", lambda: workspace.build("lab3-a_lean", write={
        "CLAUDE.md": (HERE / "a_lean" / "CLAUDE.md").read_text(encoding="utf-8"),
        ".claude/skills/hanbit-manual/SKILL.md": skill_md()}), {}),
    "b_whole": ("b", "통째로 Read", lambda: workspace.build("lab3-b_whole", copy={"CLAUDE.md": HERE / "b_whole" / "CLAUDE.md"},
                                                           write={"data/equipment_log.csv": make_log()}), {}),
    "b_grep": ("b", "Grep 으로 필요한 줄만", lambda: workspace.build("lab3-b_grep", copy={"CLAUDE.md": HERE / "b_grep" / "CLAUDE.md"},
                                                              write={"data/equipment_log.csv": make_log()}), {}),
    "c_inline": ("c", "메인이 직접 조사", lambda: workspace.build("lab3-c_inline", copy={"CLAUDE.md": HERE / "c_inline" / "CLAUDE.md"},
                                                             write={"data/equipment_log.csv": make_log()}), {}),
    "c_subagent": ("c", "researcher 에게 위임", lambda: workspace.build("lab3-c_subagent", copy={
        "CLAUDE.md": HERE / "c_subagent" / "CLAUDE.md"}, write={"data/equipment_log.csv": make_log()}),
        {"agents_json": (HERE / "c_subagent" / "agents.json").read_text(encoding="utf-8")}),
}

TOOLS = "Read,Grep,Glob,Skill,Agent"


def one(key, prompt, ws, extra, args, resume=None, fixture=None):
    r = headless.run(prompt, cwd=ws, model=config.HEADLESS_MODEL, setting_sources="project", tools=TOOLS,
                     allowed_tools=TOOLS, resume=resume, dry_run=args.dry_run,
                     fixture=fixture or f"lab3_context.json#{key}", **extra)
    if args.show_cmd:
        print("  $", r["cmd_str"])
    return r


def row(key, label, r):
    return {"v": key, "desc": label, "in": r["input_tokens"], "cr": r["cache_read"], "cw": r["cache_write"],
            "out": r["output_tokens"], "total": r["total_tokens"], "all": r["all_tokens"], "turns": r["turns"],
            "answer": r["text"].strip().replace("\n", " ")[:60]}


COLS = [("v", "변형"), ("desc", "설명"), ("in", "in"), ("cr", "캐시읽기"), ("cw", "캐시쓰기"), ("out", "out"),
        ("total", "메인 토큰"), ("all", "전체 토큰"), ("turns", "턴")]


def run_exp(exp, args):
    rows = []
    if exp == "d":
        ws = VARIANTS["a_lean"][2]()
        sid = None
        for i, q in enumerate(D_TURNS + [D_FINAL]):
            r = one("d_long", q, ws, {}, args, resume=sid)
            sid = r["session_id"] or sid
            rows.append(row(f"d_long#{i+1}", "이어서 " + ("끝 질문" if q == D_FINAL else f"{i+1}턴"), r))
        r = one("d_fresh", D_FINAL, VARIANTS["a_lean"][2](), {}, args)
        rows.append(row("d_fresh", "새 세션 끝 질문", r))
    else:
        for key, (e, label, make_ws, extra) in VARIANTS.items():
            if e != exp:
                continue
            ws = make_ws()
            print(f"  [{key}] 작업 폴더 {ws}")
            rows.append(row(key, label, one(key, QUESTION[exp], ws, extra, args)))
    headless.print_table(rows, COLS, title=f"=== 실험 {exp} ===")
    for r in rows:
        print(f"  {r['v']}: {r['answer']}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="a", choices=["a", "b", "c", "d", "all"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show-cmd", action="store_true")
    ap.add_argument("--track", default=config.TRACK, help="(이 실습은 트랙과 무관 — 공통 자료 사용)")
    args = ap.parse_args()
    headless.banner(args.dry_run)
    out = {}
    for exp in (["a", "b", "c", "d"] if args.exp == "all" else [args.exp]):
        out[exp] = run_exp(exp, args)
    if not args.dry_run:
        res = HERE / "results"
        res.mkdir(exist_ok=True)
        path = res / f"context_{args.exp}.json"
        path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
