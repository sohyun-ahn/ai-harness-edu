from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Order:
    """견적 요청 한 건."""
    grade: str                 # 강종 (SS400, SM490, STS304)
    thickness_mm: Decimal      # 두께 (mm)
    tons: Decimal              # 수량 (톤)
    rush: bool = False         # 긴급 출하 여부
    tier: str = "B"            # 고객 등급 (A, B)


@dataclass
class Quote:
    """견적 결과. 금액은 모두 원 단위 Decimal."""
    unit_price: Decimal        # 톤당 단가 (두께 할증 포함)
    subtotal: Decimal          # 단가 × 수량
    total: Decimal             # 최종 청구 금액
