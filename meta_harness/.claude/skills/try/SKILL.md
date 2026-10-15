---
name: try
description: 만든 하네스를 시험할 때. eval 입력마다 하네스 미적용 · 적용으로 claude -p 를 돌려 비교표를 만든다. 판정은 하지 않는다.
---

# try

## 준비
- 대상: `out/<이름>/` (design.md 의 대상 폴더), eval 입력: `docs/<이름>/eval/`
- 작업 폴더를 `docs/<이름>/try/` 아래에 만든다 (원본을 건드리지 않는다)
  - `bare/` : eval 입력만 복사
  - `applied/` : eval 입력 + 대상 폴더의 CLAUDE.md · .claude/ 복사

## 실행 (eval 입력마다 · 둘 다 같은 요청문)
```
cd docs/<이름>/try/bare    && claude -p --setting-sources "" --permission-mode acceptEdits "<요청문>"
cd docs/<이름>/try/applied && claude -p --setting-sources project --permission-mode acceptEdits "<요청문>"
```
- 출력은 `docs/<이름>/try/<입력번호>_bare.txt` · `_applied.txt` 로 저장한다
- `claude` 가 PATH 에 없으면 VS Code 확장 폴더의 `native-binary/claude.exe` 경로를 쓴다
- 각 실행이 만든 파일 목록도 함께 기록한다

## 비교표: docs/<이름>/try/compare.md
| 입력 | 확인 항목 (design.md) | 미적용 | 적용 | 근거 (파일 · 줄) |
|---|---|---|---|---|

- 칸에는 「충족 / 미충족 / 해당 없음」과 **사실**(실제로 나온 문장 · 숫자)만 적는다
- Hook · 금지 사항 입력에서는 차단됐는지, 어떤 메시지가 나왔는지를 적는다
- 사람 확인 지점에서 멈추는지 적는다

## 하지 않는 것
- 「적용이 더 낫다」「통과」 같은 **판정은 하지 않는다**. 판정은 사람이 한다
- 결과를 보기 좋게 고치려고 하네스를 이 단계에서 수정하지 않는다. 고칠 점은 compare.md 맨 아래 「관찰」에 사실로만 적는다
