"""주문서 생성 — 항목·옵션·합계를 계산해 주문서 json을 만듭니다.

단가와 합계는 모델이 아니라 이 코드가 메뉴판 기준으로 계산합니다.
LLM은 항목을 고르고, 돈 계산은 결정적인 코드가 맡습니다.
"""

from tools.menu import load_menu
from tools.stock import load_stock

SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_order",
        "description": (
            "확정된 주문 항목들로 주문서를 만든다. 단가·합계는 메뉴판 기준으로 계산된다. "
            "메뉴 확인(search_menu)과 재고 확인(check_stock)을 마친 뒤 마지막에 호출한다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "주문 항목 목록",
                    "items": {
                        "type": "object",
                        "properties": {
                            "menu_id": {
                                "type": "string",
                                "description": "메뉴 id (search_menu 결과의 id)",
                            },
                            "quantity": {"type": "integer", "description": "수량"},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "선택한 옵션 이름 목록 (메뉴판의 옵션 이름 그대로)",
                            },
                        },
                        "required": ["menu_id", "quantity"],
                    },
                }
            },
            "required": ["items"],
        },
    },
}


def create_order(items: list[dict]) -> dict:
    menu = {m["id"]: m for m in load_menu()}
    stock = load_stock()

    order_items = []
    total = 0
    for entry in items:
        item = menu.get(entry.get("menu_id"))
        if item is None:
            return {"error": f"메뉴에 없는 id: {entry.get('menu_id')}"}

        quantity = int(entry.get("quantity", 0))
        if quantity < 1:
            return {"error": f"{item['name']}: 수량이 올바르지 않습니다 ({quantity})"}

        # 재고를 한 번 더 확인합니다 — 모델이 확인을 건너뛰어도 코드가 막는 가드레일
        remaining = stock.get(item["id"], 0)
        if remaining < quantity:
            return {"error": f"{item['name']}: 재고 부족 (남은 수량 {remaining})"}

        option_prices = {o["name"]: o["price"] for o in item["options"]}
        options = entry.get("options") or []
        unknown = [name for name in options if name not in option_prices]
        if unknown:
            return {
                "error": f"{item['name']}에 없는 옵션: {unknown} (가능한 옵션: {list(option_prices)})"
            }

        unit_price = item["price"] + sum(option_prices[name] for name in options)
        subtotal = unit_price * quantity
        order_items.append(
            {
                "name": item["name"],
                "quantity": quantity,
                "options": options,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
        total += subtotal

    return {"items": order_items, "total": total}
