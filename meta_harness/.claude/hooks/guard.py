"""PreToolUse: 승인(docs/<이름>/APPROVED) 전에는 docs/ 밖에 쓰지 못하게 막는다.
APPROVED 는 Claude가 만들지 못한다 (사람만)."""
import glob
import json
import os
import re
import sys

e = json.load(sys.stdin)
i = e.get("tool_input", {}) or {}
tool = e.get("tool_name", "")
root = os.environ.get("CLAUDE_PROJECT_DIR") or e.get("cwd") or os.getcwd()
root = os.path.abspath(root).replace("\\", "/")


def block(msg):
    sys.stderr.reconfigure(encoding="utf-8")  # Windows 기본 코드페이지에서 한글이 깨지지 않게
    print(f"[승인 게이트] {msg}", file=sys.stderr)
    sys.exit(2)


def rel(p):
    """프로젝트 루트 기준 상대 경로 (슬래시)."""
    p = p.strip("'\"").replace("\\", "/")
    if re.match(r"^([A-Za-z]:)?/", p):
        p = os.path.abspath(p).replace("\\", "/")
        if p.lower().startswith(root.lower() + "/"):
            return p[len(root) + 1:]
        return p  # 프로젝트 밖
    return os.path.normpath(p).replace("\\", "/")


def approved(name=None):
    return bool(glob.glob(os.path.join(root, "docs", name or "*", "APPROVED")))


def allowed(path):
    r = rel(path)
    if r.startswith("docs/"):
        return True
    m = re.match(r"^out/([^/]+)/", r)
    return approved(m.group(1)) if m else approved()


file = str(i.get("file_path", ""))
cmd = str(i.get("command", ""))

# 1) APPROVED 는 사람만 만든다
if os.path.basename(file.replace("\\", "/")) == "APPROVED":
    block("APPROVED 는 사용자가 직접 만든다. 설계 요약을 보여 주고 기다릴 것")
if "APPROVED" in cmd and re.search(r"(>|\btouch\b|\bcp\b|\bmv\b|\btee\b|\bln\b|write|open\()", cmd):
    block("APPROVED 는 사용자가 직접 만든다. 설계 요약을 보여 주고 기다릴 것")

# 2) Write/Edit: 승인 전에는 docs/ 밖 금지
if tool in ("Write", "Edit", "MultiEdit") and file and not allowed(file):
    block("아직 승인 전 · design.md 요약을 보여 주고 사용자가 docs/<이름>/APPROVED 를 만들 때까지 docs/ 밖에는 쓰지 않는다")

# 3) Bash: 쓰기 동작의 대상이 docs/ 밖이면 금지 (승인 전)
if tool == "Bash":
    targets = []
    for m in re.finditer(r"(?<![0-9&])>>?\s*([^\s|;&<>]+)", cmd):  # 리다이렉트
        targets.append(m.group(1))
    for m in re.finditer(r"\b(tee|touch|mkdir|rm|cp|mv|sed\s+-i\S*|install|ln)\b([^|;&\n]*)", cmd):
        for tok in m.group(2).split():
            if not tok.startswith("-") and not re.match(r"^s[/|#]", tok):
                targets.append(tok)
    for t in targets:
        if t in ("/dev/null", "&1", "&2") or t.startswith("$"):
            continue
        if not allowed(t):
            block(f"아직 승인 전 · Bash 로도 docs/ 밖({t})에는 쓰지 않는다")
    if re.search(r"\bpython3?\s+-c\b|\bnode\s+(-e|--eval)\b", cmd) and re.search(r"write|open\(", cmd) and not approved():
        block("아직 승인 전 · 스크립트로 파일을 쓰지 않는다")
sys.exit(0)
