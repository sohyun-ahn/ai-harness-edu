"""위험한 명령을 막는 규칙 — Claude Code 훅(guard.py)과 SDK 훅(sdk_optional/sdk_hook.py)이 함께 쓴다."""
import re

# TODO(실습): 막고 싶은 Bash 명령 패턴을 (정규식, 이유) 로 추가해 보세요.
BLOCKED_BASH = [
    (r"\brm\s+-[a-zA-Z]*([rR][a-zA-Z]*f|f[a-zA-Z]*[rR])", "rm -rf 는 되돌릴 수 없습니다"),
    (r"\bgit\s+push\b.*(--force\b|\s-f\b)", "git push --force 는 원격 기록을 덮어씁니다"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard 는 작업 내용을 지웁니다"),
]

# TODO(실습): 쓰기를 막을 파일 이름 패턴
BLOCKED_FILES = [
    (r"(^|[\\/])\.env(\.|$)", ".env 에는 비밀 값이 있어 Agent 가 쓰면 안 됩니다"),
]


def check(tool_name, tool_input):
    """막아야 하면 이유(str), 괜찮으면 None."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        for pattern, reason in BLOCKED_BASH:
            if re.search(pattern, cmd):
                return reason
    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path", "")
        for pattern, reason in BLOCKED_FILES:
            if re.search(pattern, path):
                return reason
    return None
