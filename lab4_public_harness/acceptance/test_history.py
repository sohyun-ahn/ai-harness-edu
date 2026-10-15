"""채점용 인수 테스트 — 작업이 끝난 뒤 run_task.py 가 tests/ 에 복사해서 돌린다. Agent 에게는 보여 주지 않는다."""
import unittest

from inventory import Inventory


class HistoryTest(unittest.TestCase):
    def test_history_order(self):
        inv = Inventory()
        inv.add("볼트 M20", 10)
        inv.remove("볼트 M20", 3)
        inv.add("너트 M20", 4)
        self.assertEqual(inv.history("볼트 M20"), [("add", 10), ("remove", 3)])

    def test_failed_remove_not_recorded(self):
        inv = Inventory()
        inv.add("볼트 M20", 1)
        with self.assertRaises(ValueError):
            inv.remove("볼트 M20", 5)
        self.assertEqual(inv.history("볼트 M20"), [("add", 1)])

    def test_empty(self):
        self.assertEqual(Inventory().history("없는 품목"), [])


if __name__ == "__main__":
    unittest.main()
