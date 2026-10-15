from decimal import Decimal, ROUND_DOWN


def floor10(amount: Decimal) -> Decimal:
    """10원 미만 절사. 회사 금액 계산은 모두 이 함수를 거친다."""
    return (Decimal(amount) / 10).quantize(Decimal("1"), rounding=ROUND_DOWN) * 10
