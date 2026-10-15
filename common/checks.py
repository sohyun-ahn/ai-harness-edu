"""규칙으로 확인하는 검증 — LLM 없이 돌아가므로 공짜이고 매번 같은 결과를 낸다."""
import re

from common.data import find_price, load_kb

CLAUSE_RE = re.compile(r"(?<![A-Z])[A-Z]{2,4}-\d+(?!\d)")  # "IT-1을" 처럼 조사가 붙어도 잡는다
NUM_RE = re.compile(r"\d+(?:\.\d+)?")


def unknown_clauses(output):
    """[판교] 답변·인용에 나온 조항 ID 중 지식베이스에 없는 것 (= 지어낸 근거)."""
    kb = load_kb()
    text = str(output.get("reply", "")) + " " + " ".join(map(str, output.get("citations") or []))
    return sorted({c for c in CLAUSE_RE.findall(text) if c not in kb})


def numbers_not_in_source(items, source):
    """[포항] 추출한 규격·수량의 숫자 중 원문에 없는 것 (= 지어낸 숫자)."""
    src_numbers = set(NUM_RE.findall(source.replace(",", "")))  # 원문의 숫자 토큰 (1,500 → 1500)
    missing = set()
    for it in items or []:
        for field in ("규격", "수량"):
            for n in NUM_RE.findall(str(it.get(field) or "")):
                if n not in src_numbers:
                    missing.add(n)
    return sorted(missing)


def quote_errors(quote):
    """[포항] 견적 산수 확인: 단가가 단가표와 같은지, 금액 = 단가 × 수량, 합계 = 금액 합."""
    errors, total = [], 0
    for line in (quote or {}).get("lines", []):
        row = find_price(line.get("품목", ""), line.get("규격", ""))
        price, qty, amount = line.get("단가"), line.get("수량"), line.get("금액")
        if row and price != row["단가"]:
            errors.append(f"{line.get('품목')} 단가 {price} ≠ 단가표 {row['단가']}")
        if isinstance(price, (int, float)) and isinstance(qty, (int, float)):
            if amount != price * qty:
                errors.append(f"{line.get('품목')} 금액 {amount} ≠ {price}×{qty}")
            total += price * qty
    if quote and quote.get("total") != total:
        errors.append(f"합계 {quote.get('total')} ≠ 계산값 {total}")
    return errors


INTENTS = {"IT", "구매", "인사", "보안", "기타"}


def verify(track, output, source):
    """하네스 관문: 결과를 내보내기 전 규칙 검사. 문제 목록(빈 목록이면 통과)."""
    if not isinstance(output, dict):
        return ["JSON 형식이 아님"]
    problems = []
    if track == "pangyo":
        if output.get("intent") not in INTENTS:
            problems.append(f"분류 라벨 오류: {output.get('intent')}")
        if unknown_clauses(output):
            problems.append(f"없는 조항 인용: {unknown_clauses(output)}")
        if not output.get("citations") and not output.get("needs_human"):
            problems.append("근거 조항 없이 답함")
    else:
        if numbers_not_in_source(output.get("items"), source):
            problems.append(f"원문에 없는 숫자: {numbers_not_in_source(output.get('items'), source)}")
        problems += quote_errors(output.get("quote"))
    return problems


def expected_total(items):
    """[포항] 정답 항목으로 계산한 기대 견적 합계 (수량·단가가 없는 항목은 건너뜀)."""
    total = 0
    for it in items:
        row = find_price(it["품목"], it["규격"])
        if row and isinstance(it.get("수량"), int):
            total += row["단가"] * it["수량"]
    return total
