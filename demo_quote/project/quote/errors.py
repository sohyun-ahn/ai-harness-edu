"""견적 오류 코드표. 새 오류는 이 표에 코드를 추가해서 쓴다."""

CODES = {
    "E101": "등록되지 않은 강종",
    "E102": "수량 오류",
    "E103": "두께 범위 오류",
    "E104": "단가표 조회 실패",
    "E105": "고객 등급 오류",
}


class QuoteError(Exception):
    def __init__(self, code: str, detail: str = ""):
        if code not in CODES:
            raise ValueError(f"등록되지 않은 오류 코드: {code}")
        self.code = code
        super().__init__(f"[{code}] {CODES[code]} {detail}".strip())
