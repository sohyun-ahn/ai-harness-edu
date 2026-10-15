from decimal import Decimal

from .errors import QuoteError
from .models import Order, Quote
from .money import floor10

# 톤당 기본 단가 (원)
BASE_PRICE = {
    "SS400": Decimal("980000"),
    "SM490": Decimal("1120000"),
    "STS304": Decimal("3850000"),
}

THIN_EXTRA = Decimal("40000")   # 3mm 미만 박판 할증 (톤당)


def unit_price(order: Order) -> Decimal:
    if order.grade not in BASE_PRICE:
        raise QuoteError("E101", order.grade)
    if not (Decimal("1.0") <= order.thickness_mm <= Decimal("100")):
        raise QuoteError("E103", str(order.thickness_mm))
    price = BASE_PRICE[order.grade]
    if order.thickness_mm < 3:
        price += THIN_EXTRA
    return price


def calc_quote(order: Order) -> Quote:
    """견적 계산.

    할인·할증 정책: docs/wiki/영업_단가정책_2025.md 참고 (미구현)
    """
    price = unit_price(order)
    subtotal = floor10(price * order.tons)
    return Quote(unit_price=price, subtotal=subtotal, total=subtotal)
