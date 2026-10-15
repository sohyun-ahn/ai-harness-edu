"""PreToolUse: 원본(inputs/) 수정 · 외부 전송을 막는다."""
import json
import re
import sys

e = json.load(sys.stdin)
i = e.get("tool_input", {})
path = str(i.get("file_path", "")).replace("\\", "/")
cmd = str(i.get("command", ""))
if e.get("tool_name") in ("Write", "Edit", "MultiEdit") and re.search(r"(^|/)inputs/", path):
    print("차단: inputs/ 원본은 고치지 않는다. 결과는 out/ 에 만든다.", file=sys.stderr)
    sys.exit(2)
if re.search(r"(^|[;&|(]\s*)(mail|sendmail|mutt|curl|wget|scp|sftp|ftp|nc)\s", cmd):
    print("차단: 메일 발송 · 외부 전송은 하지 않는다. 초안까지만.", file=sys.stderr)
    sys.exit(2)
if re.search(r"(>>?|\brm\b|\bmv\b|sed -i|\btee\b)\s*[^|;&]*(^|[\s/'\"])inputs/", cmd):
    print("차단: inputs/ 원본은 고치지 않는다.", file=sys.stderr)
    sys.exit(2)
