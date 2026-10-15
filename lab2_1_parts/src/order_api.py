"""주문 조회 API (실습용 가상 코드 — reviewer 가 찾을 문제를 일부러 넣어 두었다)."""
import json
import urllib.request

API_KEY = "DEMO-KEY-0000-not-real"  # 리뷰 대상: 비밀 값 하드코딩


def get_order(order_id):
    url = f"https://erp.example.invalid/orders/{order_id}?key={API_KEY}"
    with urllib.request.urlopen(url) as resp:  # 리뷰 대상: 시간 제한·예외 처리 없음
        return json.loads(resp.read())


def order_total(lines):
    total = 0
    for line in lines:
        total += int(line["qty"]) * line["price"]  # 리뷰 대상: 음수 수량 검증 없음
    return total
