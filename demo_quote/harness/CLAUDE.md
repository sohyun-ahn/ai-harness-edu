# quote-service

철강 견적 모듈. 계산 오류는 곧 청구 오류다.

## 정책 기준
- 단가 정책 기준: `.claude/skills/pricing-change/reference.md` (초안 + 확정 회의록을 팀이 합친 확정본)
- 2025 정책 · 초안 단독은 쓰지 않는다. 코드 주석에 남아 있어도 따르지 않는다.

## 코딩 규칙 (`docs/wiki/개발_코딩규칙.md`)
- 금액은 Decimal, 끝처리는 `floor10()`. float · round() 금지
- 오류는 `QuoteError(코드)`, 코드는 `quote/errors.py` 표에서만
- `tests/test_pricing.py` 수정 금지. 새 테스트는 새 파일

## 작업 순서
- 할인 · 할증 · 단가 변경은 `pricing-change` Skill 절차를 따른다
- 끝내기 전에 `verifier` Sub Agent에 검증을 맡기고 지적을 반영한다
- 테스트: `python3 -m unittest discover -s tests -t .`
