"""PreToolUse: 회귀 테스트 파일 수정 · 위험 명령 · 패키지 설치를 막는다."""
import json
import sys

e = json.load(sys.stdin)
i = e.get("tool_input", {})
path = i.get("file_path", "")
cmd = i.get("command", "")

if path.endswith("tests/test_pricing.py"):
    print("차단: tests/test_pricing.py는 회귀 기준이라 수정 금지. 새 테스트 파일을 만든다.", file=sys.stderr)
    sys.exit(2)
for bad in ("rm -rf", "pip install", "git push"):
    if bad in cmd:
        print(f"차단: '{bad}'는 이 저장소에서 쓰지 않는다.", file=sys.stderr)
        sys.exit(2)
