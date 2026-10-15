# 실습 데이터

> ※ 모든 회사(「한빛스틸」)·인물·문서·단가는 실습용 가상 자료입니다. 실제 회사 규정·가격과 관계없습니다.

## pangyo — 문의 대응 라우팅

| 파일 | 내용 |
|---|---|
| `inquiries.jsonl` | 사내 문의 30건. Q25~Q30 은 까다로운 경우(`edge` 필드: 두 의도, 프롬프트 주입, 범위 밖, 정보 부족, 욕설·비방, 모호) |
| `kb/*.md` | 분야별 FAQ. 조항 ID(IT-3, BUY-2 …)가 답변 근거가 된다 |

`inquiries.jsonl` 한 줄의 필드

- `gold_intent` — 정답 분류: IT · 구매 · 인사 · 보안 · 기타
- `must_include` — 답변(또는 인용 조항)에 꼭 들어가야 하는 사실
- `must_not` — 들어가면 안 되는 말 (환불 약속, 비밀번호 안내 등)
- `needs_human` — 사람 확인으로 넘겨야 하는지

## pohang — 사양서 추출·견적

| 파일 | 내용 |
|---|---|
| `specs/*.txt` | 사양서 10건. 표·문장·탭 구분·도면 요약·영문 혼용 형식이 섞여 있다 |
| `gold.jsonl` | 사양서별 정답 JSON (`items`, `needs_human`) |
| `price_table.csv` | 품목·규격별 단가(원) |

- S06 — 본문(12 EA)과 표(10 EA)의 수량이 다르다 → 수량 `null`, 사람 확인
- S07 — 수량이 비어 있다 → 수량 `null`, 사람 확인
- 비고(`비고`)는 자유 문장이라 채점(필드 F1)에서 뺀다

## 실습에서 Agent 에게 보여 주는 것

스크립트는 임시 작업 폴더(`<임시 폴더>/labs-ws/…`)를 만들고 **정답이 없는 근거 자료만** 복사한다 (`common/workspace.py`).

| 트랙 | 작업 폴더의 `data/` | 보여 주지 않는 것 |
|---|---|---|
| pangyo | `kb/*.md` | `inquiries.jsonl` 의 정답 필드 (문의 원문만 프롬프트로) |
| pohang | `price_table.csv` | `gold.jsonl` (사양서 원문만 프롬프트로) |

## 다른 실습 자료

| 자료 | 위치 | 비고 |
|---|---|---|
| 사내 업무 매뉴얼 (긴 문서) | `lab3_context/manual.md` | 컨텍스트 실험용. 부서 FAQ 조항 + 정비 기준 + 부록 표 |
| 설비 이력 로그 1,500줄 | 실행할 때 생성 (`lab3_context/run.py` 의 `make_log`) | 같은 시드라 매번 같은 내용 |
| 재고·문의 샘플 앱 | `lab4_public_harness/sample_app/` | 버그 2개, 테스트 10개 (2개 실패) |
| 평가셋 예시 | `lab8_final_plugin/my-harness/eval/dataset.jsonl` | 형식 예시 3건 → 20건으로 채운다 |
| 저장된 헤드리스 출력 | `common/fixtures/` | `--dry-run` 용. 숫자는 예시 |
