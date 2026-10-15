"""Stop: 끝내기 전에 전체 테스트를 돌리고, 실패하면 끝내지 못하게 한다."""
import json
import subprocess
import sys

e = json.load(sys.stdin)
if e.get("stop_hook_active"):
    sys.exit(0)
r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                   capture_output=True, text=True, timeout=120)
if r.returncode != 0:
    print("테스트 실패 상태로는 끝낼 수 없다. 고친 뒤 다시 끝낸다.\n" + r.stderr[-1500:], file=sys.stderr)
    sys.exit(2)
