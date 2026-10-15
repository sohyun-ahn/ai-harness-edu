"""SessionStart: 세션을 열 때 오늘 기록(out/YYYY-MM-DD.md)이 아직 없으면
Claude가 어제 운동 여부를 먼저 묻도록 안내를 넣는다. 예약 실행이 아니다 — 사용자가 켜야만 동작한다."""
import json
import os
import sys
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8")
try:
    e = json.load(sys.stdin)
except Exception:
    e = {}
root = os.environ.get("CLAUDE_PROJECT_DIR") or e.get("cwd") or os.getcwd()
today = date.today()
yesterday = today - timedelta(days=1)

if os.path.exists(os.path.join(root, "out", f"{today.isoformat()}.md")):
    sys.exit(0)  # 오늘은 이미 확인했다

has_prev = os.path.exists(os.path.join(root, "out", f"{yesterday.isoformat()}.md"))
msg = (
    f"[일일 운동 확인] 오늘은 {today.isoformat()} 이고 오늘 기록(out/{today.isoformat()}.md)이 아직 없다. "
    f"사용자의 첫 메시지에 답하기 전에 workout-recommend Skill 의 1단계대로 먼저 묻는다: "
    f"「어제({yesterday.month}/{yesterday.day}) 운동하셨나요?」 "
    + (f"어제 추천 루틴(out/{yesterday.isoformat()}.md 의 「오늘 루틴」)을 함께 보여 준다. " if has_prev
       else "어제 추천 기록이 없으므로 첫날(기록 없음)로 다룬다. ")
    + "사용자가 답하지 않거나 다른 말을 하면 어제는 미수행으로 기록하고 오늘 루틴을 추천한다."
)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}, ensure_ascii=False))
