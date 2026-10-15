import unittest

from inquiry import classify, route


class InquiryTest(unittest.TestCase):
    def test_password(self):
        self.assertEqual(classify("비밀번호를 잊어버렸어요"), "IT")

    def test_vpn(self):
        self.assertEqual(classify("재택 중인데 VPN 접속이 안 돼요"), "IT")

    def test_security_first(self):
        self.assertEqual(classify("피싱 메일을 받았어요"), "보안")

    def test_other(self):
        self.assertEqual(classify("주차 등록은 어떻게 하나요"), "기타")

    def test_route_refund_needs_human(self):
        r = route("납품받은 부품이 불량이에요. 환불해 주세요")
        self.assertEqual((r["intent"], r["team"], r["needs_human"]), ("구매", "구매팀", True))


if __name__ == "__main__":
    unittest.main()
