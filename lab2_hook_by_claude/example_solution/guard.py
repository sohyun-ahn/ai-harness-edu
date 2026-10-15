#!/usr/bin/env python3
"""PreToolUse guard: 막으면 exit 2 + stderr 한 줄, 통과하면 exit 0."""
import fnmatch
import json
import os
import re
import shlex
import sys

PROJECT = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
CWD = PROJECT

MSG_PROD = "운영 DB 쓰기는 사용자 허락 필요"
MSG_ENV = ".env 읽기·출력 금지"
MSG_RM = "rm -rf 금지"
MSG_FORCE = "git push --force 금지"


class Block(Exception):
    pass


# ---------------------------------------------------------------- 경로 판별

GLOB = re.compile(r"[*?\[]")
PROD_NAME = re.compile(r"^prod\.db(-wal|-shm|-journal)?$")
ENV_RE = re.compile(r"(?<![\w.])\.env(\.[\w.-]*)?(?![\w-])")
ENV_EXEMPT = {"example", "sample", "template", "dist"}


def _clean(p):
    p = p.strip()
    if p.startswith("file:"):
        p = p[5:]
    return p.split("?", 1)[0]


def _abs(p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(CWD, p)


def is_prod_path(p):
    p = _clean(p)
    if not p:
        return False
    base = os.path.basename(p.rstrip("/"))
    if PROD_NAME.match(base):
        return True
    if GLOB.search(base) and fnmatch.fnmatch("prod.db", base):
        return True
    try:
        real = os.path.basename(os.path.realpath(_abs(p)))
    except (OSError, ValueError):
        return False
    return bool(PROD_NAME.match(real))


def env_mention(text):
    for m in ENV_RE.finditer(text):
        suffix = (m.group(1) or "").strip(".").lower().split(".")[0]
        if suffix in ENV_EXEMPT:
            continue
        return True
    return False


def is_env_path(p):
    if not p:
        return False
    base = os.path.basename(p.rstrip("/"))
    if env_mention(base):
        return True
    try:
        return env_mention(os.path.basename(os.path.realpath(_abs(p))))
    except (OSError, ValueError):
        return False


def glob_hits_env(tok):
    base = os.path.basename(tok.rstrip("/"))
    return base.startswith(".") and bool(GLOB.search(base)) and fnmatch.fnmatch(".env", base)


def token_touches_env(tok):
    if tok.startswith("--exclude") or "!.env" in tok:
        return False
    return env_mention(tok) or glob_hits_env(tok)


# ---------------------------------------------------------------- SQL 판별

WRITE_KW = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|TRUNCATE|"
    r"BEGIN|COMMIT|SAVEPOINT|RELEASE|ROLLBACK|ANALYZE|LOAD_EXTENSION|WRITEFILE)\b|\bREPLACE\s+INTO\b",
    re.I,
)
WRITE_SQL = re.compile(
    r"\b(UPDATE\s+\S+\s+SET|INSERT\s+(OR\s+\w+\s+)?INTO|DELETE\s+FROM|DROP\s+(TABLE|INDEX|VIEW|TRIGGER)|"
    r"ALTER\s+TABLE|REPLACE\s+INTO|CREATE\s+(TABLE|INDEX|VIEW|TRIGGER))\b",
    re.I,
)


def sql_is_readonly(sql):
    s = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    s = re.sub(r"--[^\n]*", " ", s)
    s = re.sub(r"'(?:[^']|'')*'", "''", s)
    s = re.sub(r'"(?:[^"]|"")*"', '""', s)
    for st in (x.strip() for x in s.split(";")):
        if not st:
            continue
        first = re.match(r"\w+", st)
        if not first or first.group(0).upper() not in ("SELECT", "WITH", "EXPLAIN", "VALUES"):
            return False
        if WRITE_KW.search(st):
            return False
    return True


def check_sql_for_other_db(sql):
    if re.search(r"\bATTACH\b", sql, re.I) and re.search(r"prod", sql, re.I):
        raise Block(MSG_PROD)


# ---------------------------------------------------------------- 토큰화

PUNCT = ";&|<>()\n"
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
SHELL_WORDS = {"if", "then", "else", "elif", "do", "while", "until", "!", "{", "}", "fi", "done"}
WRAPPER_VALUE_OPTS = {
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-U"},
    "xargs": {"-I", "-n", "-P", "-L", "-s", "-d", "-E", "-a"},
    "nice": {"-n"},
    "ionice": {"-c", "-n", "-p"},
    "env": {"-u", "-C", "-S"},
    "timeout": {"-s", "-k"},
}
WRAPPERS = {"sudo", "doas", "command", "builtin", "exec", "nohup", "time", "nice", "ionice", "env",
            "xargs", "timeout", "stdbuf", "setsid", "caffeinate"}
ASSIGN = re.compile(r"^[A-Za-z_]\w*=")


def tokenize(s):
    lex = shlex.shlex(s, posix=True, punctuation_chars=PUNCT)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def is_punct(tok):
    return bool(tok) and all(c in PUNCT for c in tok)


def is_redirect(tok):
    return is_punct(tok) and ("<" in tok or ">" in tok)


def split_segments(tokens):
    """[(tokens, piped_in)] — ; && || | 줄바꿈 ( ) 로 나눈다."""
    segs, cur, piped, next_piped = [], [], False, False
    for t in tokens:
        if is_punct(t) and not is_redirect(t):
            if cur:
                segs.append((cur, piped))
            cur, piped = [], False
            next_piped = t in ("|", "|&")
            piped = next_piped
            continue
        cur.append(t)
    if cur:
        segs.append((cur, piped))
    return segs


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1")


def strip_heredocs(cmd):
    """(heredoc 본문 제거한 명령, 본문들)"""
    bodies = []
    while True:
        m = HEREDOC.search(cmd)
        if not m:
            return cmd, bodies
        delim = m.group(2)
        nl = cmd.find("\n", m.end())
        if nl < 0:
            return cmd, bodies
        rest = cmd[nl + 1:]
        lines = rest.split("\n")
        end = None
        for i, ln in enumerate(lines):
            if ln.strip() == delim:
                end = i
                break
        body = "\n".join(lines[:end]) if end is not None else rest
        after = "\n".join(lines[end + 1:]) if end is not None else ""
        bodies.append(body)
        cmd = cmd[:m.start()] + " " + cmd[m.end():nl] + "\n" + after


def strip_prefix(toks):
    toks = list(toks)
    while toks:
        t = toks[0]
        if ASSIGN.match(t) or t in SHELL_WORDS:
            toks.pop(0)
            continue
        name = os.path.basename(t)
        if name in WRAPPERS:
            toks.pop(0)
            val_opts = WRAPPER_VALUE_OPTS.get(name, set())
            while toks and toks[0].startswith("-") and toks[0] != "--":
                o = toks.pop(0)
                if o in val_opts and toks:
                    toks.pop(0)
            if toks and toks[0] == "--":
                toks.pop(0)
            if name == "timeout" and toks and not toks[0].startswith("-"):
                toks.pop(0)
            while toks and (ASSIGN.match(toks[0]) and name == "env"):
                toks.pop(0)
            continue
        break
    return toks


# ---------------------------------------------------------------- 명령별 검사

def check_rm(args):
    r = f = False
    for a in args:
        if a == "--":
            break
        if a.startswith("--"):
            r = r or a == "--recursive"
            f = f or a == "--force"
        elif a.startswith("-") and len(a) > 1:
            r = r or ("r" in a or "R" in a)
            f = f or "f" in a
    if r and f:
        raise Block(MSG_RM)
    if any(is_prod_path(a) for a in args if not a.startswith("-")):
        raise Block(MSG_PROD)


GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def check_git(args):
    i = 0
    while i < len(args):
        a = args[i]
        if not a.startswith("-"):
            break
        i += 2 if a in GIT_VALUE_OPTS else 1
    if i >= len(args):
        return
    sub, rest = args[i], args[i + 1:]
    if sub == "push":
        for a in rest:
            if a == "--":
                break
            if a.startswith("--force"):
                raise Block(MSG_FORCE)
            if re.match(r"^-[A-Za-z]+$", a) and "f" in a[1:]:
                raise Block(MSG_FORCE)
            if a.startswith("+") and len(a) > 1:
                raise Block(MSG_FORCE)
    if sub in ("checkout", "restore", "rm", "mv", "clean", "switch") and any(is_prod_path(a) for a in rest):
        raise Block(MSG_PROD)


def py_script_arg(args):
    """(인라인 코드 여부, 스크립트 경로)"""
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-c" or (a.startswith("-") and not a.startswith("--") and "c" in a[1:] and a != "-"):
            return True, None
        if a == "-m":
            return True, None
        if a == "-":
            return True, None
        if a.startswith("-"):
            i += 2 if a in ("-W", "-X") else 1
            continue
        return False, a
    return True, None


def check_python(args, raw, piped, has_stdin_redirect):
    inline, script = py_script_arg(args)
    if inline or piped or has_stdin_redirect:
        text = raw
        if re.search(r"prod", text, re.I) and re.search(r"sqlite|\.db\b|db\.py|connect|execute", text, re.I):
            raise Block(MSG_PROD)
        if "-m" in args and "sqlite3" in args and any(is_prod_path(a) for a in args):
            raise Block(MSG_PROD)
        return
    if os.path.basename(script) == "db.py":
        return
    try:
        path = _abs(script)
        if os.path.getsize(path) > 1_000_000:
            return
        with open(path, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError:
        return
    if re.search(r"prod", body, re.I) and re.search(r"sqlite|connect", body, re.I) and WRITE_SQL.search(body):
        raise Block(MSG_PROD)


def dyn(s):
    return bool(re.search(r"[$`]", s))


def check_db_py(args):
    env, sqls, i = None, [], 0
    while i < len(args):
        a = args[i]
        m = re.match(r"^--e(?:n(?:v)?)?=(.*)$", a)
        if m:
            env = m.group(1)
        elif re.match(r"^--e(?:n(?:v)?)?$", a):
            env = args[i + 1] if i + 1 < len(args) else None
            i += 1
        elif not a.startswith("-") or a.startswith("--"):
            if not a.startswith("--") or True:
                sqls.append(a)
        i += 1
    if env is None:
        return
    if dyn(env):
        raise Block(MSG_PROD)
    if env == "prod":
        for s in sqls:
            if dyn(s) or not sql_is_readonly(s):
                raise Block(MSG_PROD)
    else:
        for s in sqls:
            check_sql_for_other_db(s)


SQLITE_VALUE_OPTS = {"-init", "-cmd", "-separator", "-newline", "-nullvalue", "-vfs", "-mmap", "-maxsize", "-lookaside", "-A"}


def check_sqlite3(args, piped, has_stdin_redirect):
    db, sqls, i = None, [], 0
    while i < len(args):
        a = args[i]
        if a.startswith("-") and a != "-":
            if a in SQLITE_VALUE_OPTS and i + 1 < len(args):
                val = args[i + 1]
                if a == "-cmd":
                    sqls.append(val)
                elif a == "-init" and is_prod_path(val):
                    raise Block(MSG_PROD)
                i += 2
                continue
            i += 1
            continue
        if db is None:
            db = a
        else:
            sqls.append(a)
        i += 1
    if db is None:
        return
    if dyn(db) or (GLOB.search(db) and is_prod_path(db)):
        raise Block(MSG_PROD)
    if is_prod_path(db):
        if piped or has_stdin_redirect or not sqls:
            raise Block(MSG_PROD)
        for s in sqls:
            if dyn(s) or not sql_is_readonly(s):
                raise Block(MSG_PROD)
    else:
        for s in sqls:
            check_sql_for_other_db(s)


def check_copy_like(prog, args):
    pos, target = [], None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-t", "--target-directory") and i + 1 < len(args):
            target = args[i + 1]
            i += 2
            continue
        if a.startswith("--target-directory="):
            target = a.split("=", 1)[1]
        elif not a.startswith("-"):
            pos.append(a)
        i += 1
    if prog == "mv":
        if any(is_prod_path(a) for a in pos) or (target and is_prod_path(target)):
            raise Block(MSG_PROD)
        return
    dst = target or (pos[-1] if pos else None)
    if dst and is_prod_path(dst):
        raise Block(MSG_PROD)
    if target is None and pos and os.path.isdir(_abs(dst or "")):
        for s in pos[:-1]:
            if os.path.basename(s.rstrip("/")) == "prod.db" and False:
                pass


GREP_FAMILY = {"grep", "egrep", "fgrep", "rg", "ag", "ack"}


def covers_project_root(path):
    if GLOB.search(path):
        return glob_hits_env(path) or os.path.basename(path) in ("*",) and False
    try:
        real = os.path.realpath(_abs(path))
    except (OSError, ValueError):
        return False
    return PROJECT == real or PROJECT.startswith(real.rstrip("/") + "/")


def check_recursive_grep(prog, args):
    flags = [a for a in args if a.startswith("-")]
    pos = [a for a in args if not a.startswith("-")]
    recursive = any(a in ("--recursive", "--dereference-recursive") or
                    (re.match(r"^-[A-Za-z]+$", a) and re.search(r"[rR]", a[1:])) for a in flags)
    if prog == "rg":
        hidden = "--hidden" in flags or any(re.match(r"^-[A-Za-z]*u{2,}", a) for a in flags) or "-." in flags
        if not hidden:
            return
        targets = pos[1:] if pos else []
        if not targets or any(covers_project_root(t) for t in targets):
            raise Block(MSG_ENV)
        return
    if not recursive:
        return
    targets = pos[1:]
    if any(a.startswith("-e") or a.startswith("--regexp") or a == "-f" for a in flags):
        targets = pos
    if any(covers_project_root(t) for t in targets):
        raise Block(MSG_ENV)


READ_OK = {"ls", "stat", "file", "wc", "du", "cat", "head", "tail", "less", "more", "shasum", "sha256sum",
           "sha1sum", "md5", "md5sum", "cksum", "grep", "egrep", "fgrep", "rg", "strings", "xxd", "hexdump",
           "od", "test", "[", "[[", "echo", "printf", "cd", "pushd", "readlink", "realpath", "basename",
           "dirname", "cmp", "diff", "which", "lsof", "find", "git", "sqlite3", "python", "python3",
           "chmod"}


def check_segment(toks, piped, raw, depth):
    if depth > 4:
        return
    for t in toks:
        for inner in re.findall(r"\$\(([^()]*)\)|`([^`]*)`", t):
            for sub in inner:
                if sub:
                    analyze(sub, depth + 1)

    redirect_in = any(t.startswith("<") and is_redirect(t) for t in toks)
    for i, t in enumerate(toks[:-1]):
        if is_redirect(t) and ">" in t and is_prod_path(toks[i + 1]):
            raise Block(MSG_PROD)

    cmd = strip_prefix(toks)
    if not cmd:
        return
    # 리다이렉션 토큰/대상은 인자 판별에서 제외
    clean, skip = [], False
    for t in cmd:
        if skip:
            skip = False
            continue
        if is_redirect(t):
            skip = True
            continue
        clean.append(t)
    if not clean:
        return
    prog, args = os.path.basename(clean[0]), clean[1:]

    if prog == "db.py" or (args and os.path.basename(args[0]) == "db.py" and re.match(r"^python[\d.]*$", prog)):
        check_db_py(args[1:] if prog != "db.py" else args)
        return
    if prog == "rm":
        check_rm(args)
        return
    if prog == "git":
        check_git(args)
        return
    if re.match(r"^python[\d.]*$", prog) or prog in ("pypy", "pypy3"):
        check_python(args, raw, piped, redirect_in)
        return
    if prog == "sqlite3":
        check_sqlite3(args, piped, redirect_in)
        return
    if prog in SHELLS:
        for j, a in enumerate(args):
            if a.startswith("-") and not a.startswith("--") and "c" in a[1:] and j + 1 < len(args):
                analyze(args[j + 1], depth + 1)
                break
        return
    if prog == "eval":
        analyze(" ".join(args), depth + 1)
        return
    if prog in GREP_FAMILY:
        check_recursive_grep(prog, args)
    if prog == "find":
        for j, a in enumerate(args):
            if a in ("-exec", "-execdir", "-ok", "-okdir"):
                check_segment(args[j + 1:], False, raw, depth + 1)
    if prog in ("cp", "install", "mv", "rsync", "ln"):
        check_copy_like("mv" if prog == "mv" else "cp", args)
        return
    if prog == "dd":
        if any(a.startswith("of=") and is_prod_path(a[3:]) for a in args):
            raise Block(MSG_PROD)
        return
    if prog not in READ_OK and any(is_prod_path(a) for a in args if not a.startswith("-")):
        raise Block(MSG_PROD)


def analyze(cmd, depth=0):
    body, heredocs = strip_heredocs(cmd)
    try:
        tokens = tokenize(body)
    except ValueError:
        tokens = body.split()
    for t in tokens:
        if token_touches_env(t):
            raise Block(MSG_ENV)
    for h in heredocs:
        if env_mention(h):
            raise Block(MSG_ENV)
    for seg, piped in split_segments(tokens):
        check_segment(seg, piped, cmd, depth)
        cmd0 = strip_prefix(seg)
        if heredocs and cmd0 and os.path.basename(cmd0[0]) in SHELLS:
            for h in heredocs:
                analyze(h, depth + 1)


# ---------------------------------------------------------------- 도구별 진입점

PATH_KEYS = ("file_path", "path", "notebook_path")


def check_tool(name, inp):
    global CWD
    if name == "Bash":
        analyze(inp.get("command", ""))
    elif name in ("Read", "Edit", "MultiEdit", "Write", "NotebookEdit"):
        p = next((inp[k] for k in PATH_KEYS if inp.get(k)), "")
        if is_env_path(p):
            raise Block(MSG_ENV)
        if name != "Read" and is_prod_path(p):
            raise Block(MSG_PROD)
    elif name == "Grep":
        for k in ("path", "glob"):
            v = inp.get(k) or ""
            if v and (token_touches_env(v) or is_env_path(v)):
                raise Block(MSG_ENV)
        if inp.get("output_mode") == "content" or True:
            p = inp.get("path") or ""
            if p and inp.get("glob") is None and is_env_path(p):
                raise Block(MSG_ENV)


def main():
    global CWD
    try:
        event = json.load(sys.stdin)
        CWD = os.path.realpath(event.get("cwd") or PROJECT)
        check_tool(event.get("tool_name", ""), event.get("tool_input") or {})
    except Block as b:
        print(str(b), file=sys.stderr)
        sys.exit(2)
    except Exception as e:  # noqa: BLE001 — 검사 실패 시 열어두지 않는다
        print(f"guard 내부 오류로 차단: {type(e).__name__}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
