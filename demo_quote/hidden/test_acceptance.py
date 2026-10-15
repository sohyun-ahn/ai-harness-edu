"""숨은 인수 테스트 (Agent에게 보이지 않음). 2026Q3 확정 정책 (초안 + 09-02 회의록) 기준."""
import unittest
from decimal import Decimal as D, ROUND_DOWN

from quote.errors import QuoteError
from quote.models import Order
from quote.pricing import calc_quote


def f10(x):
    return (D(x) / 10).quantize(D("1"), rounding=ROUND_DOWN) * 10


def expect(subtotal, rate, rush):
    disc = f10(subtotal * rate)
    sur = f10((subtotal - disc) * D("0.08")) if rush else D("0")
    return disc, sur, subtotal - disc + sur


class Policy(unittest.TestCase):
    def check(self, order, subtotal, rate):
        q = calc_quote(order)
        disc, sur, total = expect(subtotal, D(rate), order.rush)
        self.assertEqual(q.subtotal, subtotal, "소계")
        self.assertEqual(q.discount, disc, "할인액")
        self.assertEqual(q.surcharge, sur, "할증액")
        self.assertEqual(q.total, total, "최종 금액")

    def test_01_under_threshold(self):
        self.check(Order("SS400", D("10"), D("50")), D("49000000"), "0")

    def test_02_just_below_100(self):
        self.check(Order("SS400", D("10"), D("99.9")), D("97902000"), "0")

    def test_03_boundary_100(self):
        self.check(Order("SS400", D("10"), D("100")), D("98000000"), "0.03")

    def test_04_just_below_300(self):
        self.check(Order("SS400", D("10"), D("299")), D("293020000"), "0.03")

    def test_05_boundary_300(self):
        self.check(Order("SS400", D("10"), D("300")), D("294000000"), "0.045")

    def test_06_tier_a(self):
        self.check(Order("SS400", D("10"), D("120"), tier="A"), D("117600000"), "0.04")

    def test_07_cap_5(self):
        self.check(Order("SS400", D("10"), D("300"), tier="A"), D("294000000"), "0.05")

    def test_08_rush_no_discount(self):
        self.check(Order("SS400", D("10"), D("50"), rush=True), D("49000000"), "0")

    def test_09_rush_after_discount(self):
        self.check(Order("SS400", D("10"), D("120"), rush=True), D("117600000"), "0.03")

    def test_10_floor_everywhere(self):
        self.check(Order("STS304", D("5"), D("101.337"), rush=True), D("390147450"), "0.03")
        q = calc_quote(Order("STS304", D("5"), D("101.337"), rush=True))
        self.assertEqual(q.total, D("408718470"))

    def test_11_thin_plate(self):
        self.check(Order("SM490", D("2.9"), D("100")), D("116000000"), "0.03")


class Errors(unittest.TestCase):
    def code(self, order):
        with self.assertRaises(QuoteError) as cm:
            calc_quote(order)
        return cm.exception.code

    def test_12_zero_tons(self):
        self.assertEqual(self.code(Order("SS400", D("10"), D("0"))), "E102")

    def test_13_negative_tons(self):
        self.assertEqual(self.code(Order("SS400", D("10"), D("-5"))), "E102")

    def test_14_unknown_tier(self):
        self.assertEqual(self.code(Order("SS400", D("10"), D("10"), tier="Z")), "E105")


class Types(unittest.TestCase):
    def test_15_decimal(self):
        q = calc_quote(Order("SS400", D("10"), D("120"), rush=True, tier="A"))
        for name in ("discount", "surcharge", "total"):
            self.assertIsInstance(getattr(q, name), D, name)


if __name__ == "__main__":
    unittest.main()
