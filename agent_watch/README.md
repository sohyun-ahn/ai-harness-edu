# Agent Watch — Claude Code 에이전트 실시간 대시보드

Claude Code가 일하는 모습을 브라우저에서 실시간으로 본다. 표준 라이브러리만 쓴다 (설치할 것 없음).

- **기본 화면 (간단히)**: 큰 숫자 셋(걸린 시간 · 토큰 · 도구 사용) · 「누가 무엇을 했나」 한 줄씩 · Sub Agent는 한 줄 요약(펼치기) · 에이전트별 토큰 비중 · 주의할 점
- **자세히 보기** (오른쪽 위 버튼): 아래 전부
- 에이전트 타임라인: 메인 · Sub Agent 레인, 도구 호출 하나하나 (읽기 · 수정 · 명령 · 위임 · 실패)
- 에이전트별 토큰: 모델 · 입력 · 캐시 읽기/쓰기 · 출력
- 효율 점검: 캐시 적중률 · 같은 파일 다시 읽기 · 실패한 호출 · 응답 없이 넘어간 호출(차단 · 거부) · 큰 도구 결과 · 느린 도구 · Sub Agent 토큰 비중

VS Code · 터미널 대화 · 헤드리스(`claude -p`) 어디서 돌려도 똑같이 보인다.

## 사용

```bash
python3 server.py                         # 1. 서버 켜기 → http://127.0.0.1:7777 열기
python3 install.py ~/내/프로젝트            # 2. 그 프로젝트에 Hook 켜기 (.claude/settings.local.json)
# 3. 그 프로젝트에서 평소처럼 Claude Code 작업 → 대시보드에 바로 나타남
python3 install.py ~/내/프로젝트 --remove   # 끄기
```

- 지난 세션 다시 보기: `python3 server.py --load logs/*.jsonl`
- 캡처용 정지 화면: `http://127.0.0.1:7777/?static`
- 포트 바꾸기: `python3 server.py --port 8000` + 환경 변수 `AGENT_WATCH_PORT=8000`

## 어떻게 동작하나

| 부분 | 하는 일 |
|---|---|
| `hook.py` | Hook 이벤트(SessionStart · PreToolUse · PostToolUse · PostToolUseFailure · SubagentStart · SubagentStop · Stop …)를 서버로 보낸다. 서버가 꺼져 있어도 작업을 막지 않는다 |
| `server.py` | 이벤트를 모으고, 세션 기록 파일(transcript)과 Sub Agent 기록(`subagents/agent-*.jsonl`)에서 토큰을 읽어 브라우저로 밀어 준다 (SSE) |
| `dashboard.html` | 화면 |
| `install.py` | 프로젝트의 `.claude/settings.local.json`에만 Hook을 넣고 뺀다. 팀 공유 설정(`settings.json`)은 건드리지 않는다 |

- 받은 이벤트는 `logs/<세션>.jsonl`에 남는다 (도구 결과 본문은 남기지 않고 크기만).
- 확인한 버전: Claude Code 2.1.195.
