#!/usr/bin/env python3
"""agent_watch — Claude Code 에이전트 실시간 대시보드 서버 (표준 라이브러리만).

  python3 server.py            # http://127.0.0.1:7777 열기
  python3 server.py --port 8000
  python3 server.py --load logs/*.jsonl   # 지난 세션 기록을 불러와서 보기

Hook(hook.py)이 보낸 이벤트로 「누가 언제 무엇을 했는지」를,
세션 기록 파일(transcript)로 「토큰을 얼마나 썼는지」를 모은다.
받은 이벤트는 logs/<세션>.jsonl 에도 남는다.
"""
import argparse
import json
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"
LOCK = threading.Lock()
SESSIONS = {}          # session_id → 상태
CLIENTS = []           # SSE 구독 큐


def new_session(sid, e):
    return {"id": sid, "cwd": e.get("cwd", ""), "transcript": e.get("transcript_path", ""),
            "started": e["_t"], "updated": e["_t"], "status": "실행 중", "prompt": "",
            "agents": {"main": {"id": "main", "type": "메인", "start": e["_t"], "end": None, "status": "실행 중"}},
            "events": [], "usage": {}, "_offsets": {}, "_msgs": {}}


def agent_key(e):
    return e.get("agent_id") or "main"


def on_event(e, log=True):
    sid = e.get("session_id", "?")
    name = e.get("hook_event_name", "")
    with LOCK:
        s = SESSIONS.get(sid)
        if s is None:
            s = SESSIONS[sid] = new_session(sid, e)
        s["updated"] = e["_t"]
        if e.get("transcript_path"):
            s["transcript"] = e["transcript_path"]
        ag = agent_key(e)
        if name == "UserPromptSubmit":
            s["prompt"] = (e.get("prompt") or "")[:200]
            s["status"] = "실행 중"
            s["agents"]["main"].update(status="실행 중", end=None)
        elif name == "SubagentStart":
            s["agents"][ag] = {"id": ag, "type": e.get("agent_type", "?"), "start": e["_t"], "end": None, "status": "실행 중"}
        elif name == "SubagentStop":
            a = s["agents"].setdefault(ag, {"id": ag, "type": e.get("agent_type", "?"), "start": e["_t"]})
            a.update(end=e["_t"], status="완료")
        elif name == "Stop":
            s["status"] = "대기"
            s["agents"]["main"].update(status="대기")
        elif name == "SessionEnd":
            s["status"] = "종료"
            s["agents"]["main"].update(status="종료", end=e["_t"])
        ev = {"t": e["_t"], "event": name, "cwd": s["cwd"], "agent": ag, "agent_type": e.get("agent_type") or "메인",
              "tool": e.get("tool_name"), "id": e.get("tool_use_id"), "target": target(e),
              "ms": e.get("duration_ms"), "error": (e.get("error") or "")[:200],
              "size": (e.get("tool_response") or {}).get("size")}
        s["events"].append(ev)
        if log:
            LOGS.mkdir(exist_ok=True)
            with open(LOGS / f"{sid}.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    broadcast({"kind": "event", "session": sid, "event": ev})


def target(e):
    i = e.get("tool_input") or {}
    cwd = (e.get("cwd") or "").rstrip("/") + "/"
    for k in ("file_path", "command", "pattern", "subagent_type", "skill", "url", "query", "description"):
        if i.get(k):
            return str(i[k]).replace(cwd, "").replace(cwd[:-1], ".")[:160]   # 프로젝트 기준 상대 경로로
    return ""


# ── 토큰: transcript를 이어 읽는다 (메시지 id로 중복 제거) ──────────────────
def read_usage(s):
    tp = s.get("transcript")
    if not tp:
        return False
    files = {"main": Path(tp)}
    sub = Path(tp[:-6]) / "subagents" if tp.endswith(".jsonl") else None
    if sub and sub.exists():
        for f in sub.glob("agent-*.jsonl"):
            files[f.stem[len("agent-"):]] = f
    changed = False
    for ag, f in files.items():
        if not f.exists():
            continue
        off = s["_offsets"].get(str(f), 0)
        if f.stat().st_size <= off:
            continue
        with open(f, encoding="utf-8") as fh:
            fh.seek(off)
            chunk = fh.read()
        end = chunk.rfind("\n") + 1          # 다 쓰인 줄까지만
        s["_offsets"][str(f)] = off + len(chunk[:end].encode("utf-8"))
        for line in chunk[:end].splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = r.get("message")
            if not isinstance(m, dict) or not m.get("usage"):
                continue
            u = m["usage"]
            s["_msgs"][(ag, m.get("id"))] = {
                "agent": ag, "model": m.get("model", "?"), "ts": iso(r.get("timestamp")),
                "in": u.get("input_tokens", 0) or 0, "out": u.get("output_tokens", 0) or 0,
                "cr": u.get("cache_read_input_tokens", 0) or 0, "cw": u.get("cache_creation_input_tokens", 0) or 0}
            changed = True
    if changed:
        agg = {}
        for v in s["_msgs"].values():
            a = agg.setdefault(v["agent"], {"in": 0, "out": 0, "cr": 0, "cw": 0, "calls": 0, "model": v["model"]})
            for k in ("in", "out", "cr", "cw"):
                a[k] += v[k]
            a["calls"] += 1
            a["model"] = v["model"]
        s["usage"] = agg
        # 시간에 따른 누적 토큰 (에이전트별) — 그래프용
        series, run = [], {}
        for v in sorted(s["_msgs"].values(), key=lambda x: x["ts"] or 0):
            run[v["agent"]] = run.get(v["agent"], 0) + v["in"] + v["out"] + v["cr"] + v["cw"]
            series.append([v["ts"], v["agent"], run[v["agent"]]])
        s["usage_series"] = series
    return changed


def iso(t):
    """transcript 시각 (ISO, UTC) → epoch 초."""
    if not t:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def poll_usage():
    while True:
        time.sleep(1)
        with LOCK:
            items = list(SESSIONS.items())
        for sid, s in items:
            if time.time() - s["updated"] > 3600:
                continue
            with LOCK:
                ch = read_usage(s)
                usage, series = s["usage"], s.get("usage_series", [])
            if ch:
                broadcast({"kind": "usage", "session": sid, "usage": usage, "series": series})


def snapshot():
    with LOCK:
        return {sid: {k: v for k, v in s.items() if not k.startswith("_")} for sid, s in SESSIONS.items()}


def broadcast(msg):
    data = json.dumps(msg, ensure_ascii=False)
    for q in list(CLIENTS):
        q.put(data)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.path != "/event":
            return self.send_error(404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            on_event(json.loads(self.rfile.read(n)))
        except Exception as ex:      # 잘못된 이벤트가 와도 서버는 산다
            print("이벤트 오류:", ex)
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self.path = self.path.split("?")[0]
        if self.path in ("/", "/index.html"):
            body = (HERE / "dashboard.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/state":
            body = json.dumps(snapshot(), ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            q = queue.Queue()
            CLIENTS.append(q)
            try:
                while True:
                    try:
                        data = q.get(timeout=15)
                        self.wfile.write(f"data: {data}\n\n".encode())
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                CLIENTS.remove(q)
        else:
            self.send_error(404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--load", nargs="*", default=[], help="지난 세션 기록 (logs/*.jsonl)")
    a = ap.parse_args()
    for f in a.load:
        for line in open(f, encoding="utf-8"):
            if line.strip():
                on_event(json.loads(line), log=False)
        for s in SESSIONS.values():
            read_usage(s)
    threading.Thread(target=poll_usage, daemon=True).start()
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    except OSError:
        raise SystemExit(f"포트 {a.port}을(를) 이미 쓰고 있다 — Agent Watch가 이미 켜져 있으면 브라우저로 http://127.0.0.1:{a.port} 만 열면 된다.\n"
                         f"새로 켜려면: pkill -f server.py 후 다시 실행 · 다른 포트: python3 server.py --port 8000")
    print(f"agent_watch: http://127.0.0.1:{a.port}  (멈추기 Ctrl+C)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
