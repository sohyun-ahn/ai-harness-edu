#!/usr/bin/env python3
"""Claude Code Hook → agent_watch 서버로 이벤트를 보낸다.

서버가 꺼져 있어도 Claude 작업을 막지 않는다 (항상 exit 0, 0.5초 안에 포기).
"""
import json
import os
import sys
import time
import urllib.request

PORT = os.environ.get("AGENT_WATCH_PORT", "7777")

try:
    e = json.load(sys.stdin)
    e["_t"] = time.time()
    tr = e.get("tool_response")
    if tr is not None:                      # 응답 본문은 크기만 남긴다
        e["tool_response"] = {"size": len(json.dumps(tr, ensure_ascii=False))}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/event", data=json.dumps(e).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=0.5)
except Exception:
    pass
sys.exit(0)
