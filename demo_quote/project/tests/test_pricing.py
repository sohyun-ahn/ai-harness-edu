"""기존 견적 계산 회귀 테스트. 이 파일은 회귀 기준이라 수정하지 않는다."""
import unittest
from decimal import Decimal

from quote.errors import QuoteError
from quote.models import Order
from quote.pricing import calc_quote


class TestPricing(unittest.TestCase):
    def test_basic(self):
        q = calc_quote(Order("SS400", Decimal("10"), Decimal("20")))
        self.assertEqual(q.subtotal, Decimal("19600000"))

    def test_thin_extra(self):
        q = calc_quote(Order("SM490", Decimal("2.5"), Decimal("10")))
        self.assertEqual(q.unit_price, Decimal("1160000"))

    def test_fraction_floor(self):
        q = calc_quote(Order("STS304", Decimal("5"), Decimal("1.333")))
        self.assertEqual(q.subtotal, Decimal("5132050"))

    def test_unknown_grade(self):
        with self.assertRaises(QuoteError) as cm:
            calc_quote(Order("XX999", Decimal("10"), Decimal("1")))
        self.assertEqual(cm.exception.code, "E101")

    def test_thickness_range(self):
        with self.assertRaises(QuoteError) as cm:
            calc_quote(Order("SS400", Decimal("0.5"), Decimal("1")))
        self.assertEqual(cm.exception.code, "E103")


if __name__ == "__main__":
    unittest.main()
