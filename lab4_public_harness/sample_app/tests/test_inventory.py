import unittest

from inventory import Inventory


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self.inv = Inventory()
        self.inv.add("볼트 M20", 10)

    def test_add(self):
        self.inv.add("볼트 M20", 5)
        self.assertEqual(self.inv.stock("볼트 M20"), 15)

    def test_add_rejects_zero(self):
        with self.assertRaises(ValueError):
            self.inv.add("볼트 M20", 0)

    def test_remove(self):
        self.inv.remove("볼트 M20", 3)
        self.assertEqual(self.inv.stock("볼트 M20"), 7)

    def test_remove_more_than_stock(self):
        with self.assertRaises(ValueError):
            self.inv.remove("볼트 M20", 11)
        self.assertEqual(self.inv.stock("볼트 M20"), 10)

    def test_low_stock(self):
        self.inv.add("너트 M20", 2)
        self.assertEqual(self.inv.low_stock({"볼트 M20": 5, "너트 M20": 5, "와셔 M20": 1}), ["너트 M20", "와셔 M20"])


if __name__ == "__main__":
    unittest.main()
