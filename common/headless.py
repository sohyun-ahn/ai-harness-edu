"""Claude Code 헤드리스 모드(`claude -p`)를 한 번 실행하고 결과·토큰을 dict 로 돌려준다.

API 키 없이, Claude Code 에 로그인한 계정(Business/Team)으로 돈다. 실습에서는 이 파일을 고치지 않는다.

    from common import headless
    r = headless.run("안녕", cwd="/tmp/x", model="haiku")
    print(r["text"], r["total_tokens"])

dry-run: 실제로 부르지 않고 common/fixtures/ 에 저장해 둔 출력을 같은 방식으로 파싱한다 (할당량 0).
         dry_run=True 를 넘기거나 환경 변수 LABS_DRY_RUN=1.

토큰 읽는 법 (Business 요금제에서는 cost 가 청구액과 다를 수 있다 → 토큰으로 비교한다)
  input_tokens  캐시에 없던 새 입력      cache_read   캐시에서 읽은 입력 (싸다)
  cache_write   이번에 캐시에 쓴 입력    output_tokens 모델이 쓴 출력
  total_tokens  위 넷의 합 — 메인 대화만. 서브에이전트까지 합친 값은 all_tokens (modelUsage 기준)
"""
import json
import os
import re
import shlex
import shutil
import subprocess
import threading
import time
from pathlib import Path

from common import config

FIXTURES = Path(__file__).resolve().parent / "fixtures"
_fixture_calls = {}
_flags = None


# ---------------------------------------------------------------- 명령 만들기
def available_flags():
    """설치된 `claude --help` 에 나오는 옵션 이름. 버전에 없는 옵션(예: --max-turns)은 넘기지 않는다."""
    global _flags
    if _flags is None:
        try:
            out = subprocess.run([config.CLAUDE_BIN, "--help"], capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.TimeoutExpired):
            out = ""
        _flags = set(re.findall(r"(--[a-z][a-zA-Z-]+)", out))
    return _flags


def _csv(v):
    return v if isinstance(v, str) else ",".join(v)


def build_cmd(*, system_prompt=None, system_append=None, model=None, tools=None, allowed_tools=None,
              disallowed_tools=None, agents_json=None, plugin_dirs=None, settings=None, setting_sources=None,
              permission_mode="dontAsk", max_turns=None, add_dirs=None, resume=None, session_id=None,
              stream=False, extra_args=None):
    """claude 명령 목록. 프롬프트는 stdin 으로 넘기므로 여기 없다."""
    cmd = [config.CLAUDE_BIN, "-p", "--output-format", "stream-json" if stream else "json"]
    if stream:
        cmd.append("--verbose")                       # stream-json 은 --verbose 가 있어야 한다
    if model:
        cmd += ["--model", model]
    if system_prompt is not None:
        cmd += ["--system-prompt", system_prompt]     # 기본 시스템 프롬프트를 통째로 바꾼다
    if system_append:
        cmd += ["--append-system-prompt", system_append]
    if tools is not None:
        cmd += ["--tools", _csv(tools)]               # 쓸 수 있는 내장 도구 목록 ("" = 도구 없음)
    if allowed_tools:
        cmd += ["--allowedTools", _csv(allowed_tools)]  # 묻지 않고 허용
    if disallowed_tools:
        cmd += ["--disallowedTools", _csv(disallowed_tools)]
    if agents_json:
        cmd += ["--agents", agents_json if isinstance(agents_json, str) else json.dumps(agents_json, ensure_ascii=False)]
    for d in plugin_dirs or []:
        cmd += ["--plugin-dir", str(d)]
    if settings:
        cmd += ["--settings", settings if isinstance(settings, str) else json.dumps(settings, ensure_ascii=False)]
    if setting_sources is not None:
        cmd.append("--setting-sources=" + _csv(setting_sources))  # "" = 내 PC 설정·CLAUDE.md 안 읽음
    if permission_mode:
        cmd += ["--permission-mode", permission_mode]
    for d in add_dirs or []:
        cmd += ["--add-dir", str(d)]
    if resume:
        cmd += ["--resume", resume]
    if session_id:
        cmd += ["--session-id", session_id]
    if max_turns and "--max-turns" in available_flags():
        cmd += ["--max-turns", str(max_turns)]
    return cmd + list(extra_args or [])


def show_cmd(cmd, cwd=None):
    """사람이 읽을 수 있게 한 줄로 (긴 값은 줄인다)."""
    short = [a if len(a) <= 80 else a[:60] + "…" for a in cmd]
    return (f"(cd {shlex.quote(str(cwd))} && " if cwd else "") + "echo '<프롬프트>' | " + shlex.join(short) + (")" if cwd else "")


# ---------------------------------------------------------------- 실행
def run(prompt, *, cwd=None, system_append=None, system_prompt=None, model=None, allowed_tools=None,
        disallowed_tools=None, tools=None, agents_json=None, plugin_dirs=None, settings=None,
        setting_sources=None, permission_mode="dontAsk", max_turns=None, add_dirs=None, resume=None,
        session_id=None, stream=False, timeout=None, dry_run=False, fixture=None, on_event=None,
        extra_args=None) -> dict:
    """`claude -p` 한 번 → {text, input_tokens, output_tokens, cache_read, cache_write, total_tokens,
    all_tokens, cost, turns, duration_ms, session_id, is_error, subtype, events(stream 일 때), cmd}."""
    cmd = build_cmd(system_prompt=system_prompt, system_append=system_append, model=model, tools=tools,
                    allowed_tools=allowed_tools, disallowed_tools=disallowed_tools, agents_json=agents_json,
                    plugin_dirs=plugin_dirs, settings=settings, setting_sources=setting_sources,
                    permission_mode=permission_mode, max_turns=max_turns, add_dirs=add_dirs, resume=resume,
                    session_id=session_id, stream=stream, extra_args=extra_args)
    dry = dry_run or os.environ.get("LABS_DRY_RUN") == "1"
    t0 = time.time()
    if dry:
        stdout, stderr, code = _load_fixture(fixture, stream), "", 0
    else:
        if not shutil.which(config.CLAUDE_BIN):
            raise RuntimeError(f"'{config.CLAUDE_BIN}' 명령을 찾을 수 없습니다. Claude Code 를 설치하고 `claude` 로 로그인하세요."
                               " (설치 없이 흐름만 보려면 --dry-run)")
        timeout = timeout or config.HEADLESS_TIMEOUT
        if stream:
            stdout, stderr, code = _run_stream(cmd, prompt, cwd, timeout, on_event)
        else:
            try:
                p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd, timeout=timeout)
                stdout, stderr, code = p.stdout, p.stderr, p.returncode
            except subprocess.TimeoutExpired:
                stdout, stderr, code = "", f"시간 초과 ({timeout}초)", -1
    out = parse_stream(stdout) if stream else parse_json(stdout)
    if dry and stream and on_event:
        for ev in out["events"]:
            on_event(ev)
    if out["subtype"] == "no_result":
        out["text"] = (stderr or stdout or "")[-800:]
    out.update(cmd=cmd, cmd_str=show_cmd(cmd, cwd), returncode=code, dry_run=dry,
               wall_ms=int((time.time() - t0) * 1000))
    return out


def _run_stream(cmd, prompt, cwd, timeout, on_event):
    """stream-json 을 줄 단위로 읽으며 받은 시각(_ts, ms)을 붙인다 → 타임라인 그림에 쓴다."""
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, cwd=cwd, bufsize=1)
    timer = threading.Timer(timeout, p.kill)
    timer.start()
    t0 = time.time()
    lines = []
    try:
        p.stdin.write(prompt)
        p.stdin.close()
        for line in p.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev["_ts"] = int((time.time() - t0) * 1000)
            lines.append(json.dumps(ev, ensure_ascii=False))
            if on_event:
                on_event(ev)
        p.wait()
    finally:
        timer.cancel()
    return "\n".join(lines), p.stderr.read(), p.returncode


# ---------------------------------------------------------------- 파싱
def _empty():
    return {"text": "", "input_tokens": 0, "output_tokens": 0, "cache_read": 0, "cache_write": 0,
            "total_tokens": 0, "all_tokens": 0, "cost": 0.0, "turns": 0, "duration_ms": 0,
            "session_id": None, "is_error": True, "subtype": "no_result", "model_usage": {}, "raw": None}


def from_result(res):
    """result 메시지(dict) 하나 → 표준 dict."""
    out = _empty()
    u = res.get("usage") or {}
    inp, outp = u.get("input_tokens", 0) or 0, u.get("output_tokens", 0) or 0
    cr, cw = u.get("cache_read_input_tokens", 0) or 0, u.get("cache_creation_input_tokens", 0) or 0
    mu = res.get("modelUsage") or {}
    all_tokens = sum((v.get("inputTokens", 0) or 0) + (v.get("outputTokens", 0) or 0)
                     + (v.get("cacheReadInputTokens", 0) or 0) + (v.get("cacheCreationInputTokens", 0) or 0)
                     for v in mu.values())
    out.update(text=res.get("result") or "", input_tokens=inp, output_tokens=outp, cache_read=cr, cache_write=cw,
               total_tokens=inp + outp + cr + cw, all_tokens=all_tokens or inp + outp + cr + cw,
               cost=res.get("total_cost_usd") or 0.0, turns=res.get("num_turns") or 0,
               duration_ms=res.get("duration_ms") or 0, session_id=res.get("session_id"),
               is_error=bool(res.get("is_error")), subtype=res.get("subtype"), model_usage=mu, raw=res)
    return out


def parse_json(stdout):
    """--output-format json 출력 → 표준 dict. (버전에 따라 메시지 배열로 나와도 result 를 찾는다)"""
    stdout = (stdout or "").strip()
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = None
        for line in reversed(stdout.splitlines()):
            try:
                data = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if isinstance(data, list):
        data = next((m for m in reversed(data) if isinstance(m, dict) and m.get("type") == "result"), None)
    return from_result(data) if isinstance(data, dict) else _empty()


def parse_stream(stdout):
    """--output-format stream-json 출력(줄마다 JSON) → 표준 dict + events(원본 이벤트 목록)."""
    events = []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    res = next((e for e in reversed(events) if e.get("type") == "result"), None)
    out = from_result(res) if res else _empty()
    out["events"] = events
    return out


def tool_uses(events):
    """이벤트에서 도구 호출만 뽑는다 → [{id, name, input, parent}] (parent = 서브에이전트 안이면 그 Agent 호출 id)."""
    calls = []
    for e in events or []:
        if e.get("type") != "assistant":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if b.get("type") == "tool_use":
                calls.append({"id": b.get("id"), "name": b.get("name"), "input": b.get("input") or {},
                              "parent": e.get("parent_tool_use_id")})
    return calls


def tool_results(events):
    """{tool_use_id: (is_error, 결과 문자열)}"""
    out = {}
    for e in events or []:
        if e.get("type") != "user":
            continue
        content = (e.get("message") or {}).get("content")
        for b in content if isinstance(content, list) else []:
            if b.get("type") == "tool_result":
                c = b.get("content")
                text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                out[b.get("tool_use_id")] = (bool(b.get("is_error")), text)
    return out


# ---------------------------------------------------------------- dry-run 용 저장 출력
def _load_fixture(fixture, stream):
    """fixture: 'lab1_bare_pangyo' | 'lab6_bench.json#baseline/t1' | 파일 경로. 목록이면 부를 때마다 다음 것."""
    name, key = (str(fixture).split("#", 1) + [None])[:2] if fixture else (None, None)
    path = None
    if name:
        exts = [".jsonl", ".json"] if stream else [".json", ".jsonl"]
        cand = [Path(name), FIXTURES / name] + [FIXTURES / f"{name}{e}" for e in exts]
        path = next((p for p in cand if p.is_file()), None)
    if path is None:
        path = FIXTURES / ("default_stream.jsonl" if stream else "default.json")
        key = None
    if path.suffix == ".jsonl":
        return path.read_text(encoding="utf-8")
    data = json.loads(path.read_text(encoding="utf-8"))
    if key is not None:
        data = data.get(key, data.get("*"))
    if isinstance(data, list):
        tag = f"{path}#{key}"
        i = _fixture_calls.get(tag, 0)
        _fixture_calls[tag] = i + 1
        data = data[i % len(data)]
    return json.dumps(data, ensure_ascii=False)  # stream 으로 읽으면 result 이벤트 하나짜리가 된다


# ---------------------------------------------------------------- 출력 도우미
def banner(dry_run):
    if dry_run or os.environ.get("LABS_DRY_RUN") == "1":
        print("[dry-run] 저장된 출력(common/fixtures/)으로 돈다. claude 를 부르지 않는다 — 숫자는 예시다.\n")


def tok_line(r):
    return (f"in {r['input_tokens']:,} + 캐시읽기 {r['cache_read']:,} + 캐시쓰기 {r['cache_write']:,}"
            f" / out {r['output_tokens']:,} = {r['total_tokens']:,}")


def print_table(rows, cols, title=None):
    """rows: [dict], cols: [(키, 머리글)] — 숫자는 천 단위 쉼표."""
    def fmt(v):
        if isinstance(v, bool):
            return "O" if v else "X"
        if isinstance(v, int):
            return f"{v:,}"
        if isinstance(v, float):
            return f"{v:,.4f}" if v < 1 else f"{v:,.1f}"
        return str(v)
    cells = [[fmt(r.get(k, "")) for k, _ in cols] for r in rows]
    heads = [h for _, h in cols]
    width = [max(_w(h), *(_w(c[i]) for c in cells)) if cells else _w(h) for i, h in enumerate(heads)]
    if title:
        print(f"\n{title}")
    print("  ".join(_pad(h, width[i]) for i, h in enumerate(heads)))
    print("  ".join("-" * w for w in width))
    for c in cells:
        print("  ".join(_pad(x, width[i], right=bool(re.fullmatch(r"[-+]?[\d,.]+%?|[OX]", x))) for i, x in enumerate(c)))


def _w(s):
    """화면 폭 (한글은 2칸)."""
    return sum(2 if ord(ch) > 0x1100 else 1 for ch in str(s))


def _pad(s, w, right=False):
    gap = " " * (w - _w(s))
    return gap + s if right else s + gap
