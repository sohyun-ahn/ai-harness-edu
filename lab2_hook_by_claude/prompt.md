# Claude에게 줄 요청 (값만 바꿔 쓰기)

아래를 Claude Code 대화창에 붙여 넣는다. 「막을 것 · 허용할 것」 목록만 우리 상황에 맞게 고친다.

---

이 프로젝트에 PreToolUse Hook을 만들어 줘.

막을 것:
- 운영 DB(db/prod.db, `--env prod`)에 쓰는 모든 동작 — UPDATE · INSERT · DELETE · DROP, sqlite3 직접 실행, python으로 직접 접속, 파일 덮어쓰기(cp · mv · Write)
- `rm -rf`
- `.env` 읽기 · 출력 (Read 도구, cat 등)
- `git push --force`

허용할 것:
- 운영 DB 조회(SELECT)
- 개발 DB(dev)는 읽기 · 쓰기 모두
- 일반 코드 수정, 리포트 실행, 일반 git push

조건:
- `.claude/hooks/guard.py`에 만들고 `.claude/settings.json`에 등록
- 막을 때는 exit 2와 함께 이유를 한 줄로 (「운영 DB 쓰기는 사용자 허락 필요」처럼)
- 표준 라이브러리만
- 다 만들면 `python3 ../check_hook.py`로 시험하고, 실패한 사례가 있으면 고쳐서 다시 시험
