"""재고 확인 — data/stock.json에서 주문 수량 가능 여부를 확인합니다."""

import json
from pathlib import Path

from tools.menu import load_menu

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "stock.json"

SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_stock",
        "description": (
            "메뉴의 남은 재고를 확인하고 요청 수량만큼 주문 가능한지 알려준다. "
            "주문서를 만들기 전에 반드시 확인한다. "
            "menu_id를 생략하면 전체 메뉴의 재고 목록을 반환한다 — 손님이 재고 현황을 물으면 생략하고 호출한다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "menu_id": {
                    "type": "string",
                    "description": "메뉴 id (search_menu 결과의 id). 생략하면 전체 재고 반환",
                },
                "quantity": {"type": "integer", "description": "주문 수량 (생략 시 1)"},
            },
            "required": [],
        },
    },
}


def load_stock() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def check_stock(menu_id: str = "", quantity: int = 1) -> dict:
    stock = load_stock()
    if not menu_id:  # 전체 재고 현황
        names = {m["id"]: m["name"] for m in load_menu()}
        return {
            "stock": [
                {"menu_id": mid, "name": names.get(mid, mid), "remaining": remaining}
                for mid, remaining in stock.items()
            ]
        }
    if menu_id not in stock:
        return {"error": f"재고 정보에 없는 메뉴 id: {menu_id}"}
    remaining = stock[menu_id]
    return {
        "menu_id": menu_id,
        "requested": quantity,
        "remaining": remaining,
        "available": remaining >= quantity,
    }
