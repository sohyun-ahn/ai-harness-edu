"""자재 재고 관리 (실습용 가상 앱)."""


class Inventory:
    def __init__(self):
        self._stock = {}

    def add(self, item, qty):
        """입고. qty 는 1 이상."""
        if qty <= 0:
            raise ValueError("수량은 1 이상이어야 합니다")
        self._stock[item] = self._stock.get(item, 0) + qty

    def remove(self, item, qty):
        """출고. 재고보다 많이 꺼내면 ValueError, 재고는 그대로."""
        if qty <= 0:
            raise ValueError("수량은 1 이상이어야 합니다")
        current = self._stock.get(item, 0)
        self._stock[item] = current - qty

    def stock(self, item):
        return self._stock.get(item, 0)

    def low_stock(self, minimums):
        """{품목: 최소 재고} 를 받아 최소 재고보다 적은 품목 목록 (이름순)."""
        return sorted(item for item, minimum in minimums.items() if self.stock(item) < minimum)
