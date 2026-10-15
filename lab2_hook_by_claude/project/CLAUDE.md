# ops-tools

고객 데이터 도구 모음 (교육용 가상 저장소).

- DB 실행: `python3 tools/db.py --env dev|prod "SQL"`
- 운영 DB(`db/prod.db`, `--env prod`)에 쓰기(UPDATE · INSERT · DELETE · 덮어쓰기) 전에는 반드시 사용자 허락을 받는다.
- 개발 DB(`dev`)는 자유롭게 써도 된다.
- `.env`는 열지 않는다.
