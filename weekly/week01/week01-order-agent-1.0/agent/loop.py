"""에이전트 루프 — 도구를 부를지, 몇 번 부를지, 언제 멈출지를 모델이 결정합니다.

이 while 루프가 하네스의 씨앗입니다. 지금은 루프뿐이지만, 여기에
가드레일·검증·메모리가 붙으면 하네스 엔지니어링이 됩니다.
"""

import json

from llm.client import complete
from tools import TOOL_SCHEMAS, execute
from tools.menu import load_menu

SYSTEM_PROMPT = """\
너는 분식집 '분식왕'의 주문 접수 점원이다. 한국어로 정중하고 간결하게 응대한다.

규칙:
- 손님과의 대화는 이어진다 — 이전에 주고받은 내용(주문하려던 메뉴, 되물은 것)을
  기억하고 이어서 응대한다
- 메뉴 이름·가격·옵션은 절대 지어내지 말고 반드시 search_menu로 확인한다
- 메뉴판을 보여달라고 하면 반드시 search_menu를 검색어 없이 호출한다 —
  이 호출이 있어야 화면에 메뉴판 표가 뜬다. 호출한 뒤 답변은 짧은 안내
  한 문장만 한다 (표 내용은 다시 나열하지 않는다)
- 재고를 물으면 check_stock으로 조회해 알려준다 (menu_id 생략 시 전체 재고,
  남은 수량이 0이면 품절이라고 안내한다)
- 주문서를 만들기 전에 check_stock으로 재고를 확인한다
- 주문이 확정되면 create_order로 주문서를 만든다 (단가·합계는 도구가 계산한다)
- 메뉴에 없는 항목은 정중히 거절하고, 메뉴판에 있는 비슷한 대안을 제시한다
- 재고가 부족하면 가능한 수량이나 다른 메뉴를 제안한다
- 주문 확정 답변은 한두 문장으로 한다 (주문서 표는 시스템이 함께 보여준다).
  메뉴판·재고 안내는 줄바꿈으로 정리된 목록으로 자세히 답한다
- 답변은 일반 텍스트로만 쓴다 (마크다운 기호 ** ## 등 금지)
"""

MAX_TURNS = 8  # 무한 루프 방지 — 도구 왕복 횟수 상한

_MENU_WORDS = ("메뉴", "menu")
_SHOW_WORDS = ("보여", "알려", "뭐", "무엇", "어떤", "있", "추천", "판")


def _wants_menu_board(text: str) -> bool:
    """'메뉴(판) 보여주세요' 류의 요청인지 — 가드레일용 단순 키워드 판별."""
    t = text.lower()
    return any(w in t for w in _MENU_WORDS) and any(w in t for w in _SHOW_WORDS)


def run_agent(user_message: str, history: list[dict] | None = None) -> dict:
    """history: 세션에 쌓인 이전 손님-점원 대화 (user/assistant 메시지 목록)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(history or []),
        {"role": "user", "content": user_message},
    ]
    order_sheet = None
    menu_board = None
    nudged = False

    for _ in range(MAX_TURNS):
        response = complete(messages, tools=TOOL_SCHEMAS)
        message = response.choices[0].message

        # 도구 호출이 없으면 모델이 답을 확정한 것 — 루프를 멈춥니다
        if not message.tool_calls:
            content = (message.content or "").strip()
            # 가드레일 — 보여줄 것(주문서·메뉴판)도 없는데 빈 답이 오면 한 번 재지시
            if not content and not order_sheet and menu_board is None and not nudged:
                nudged = True
                messages.append(
                    {"role": "user", "content": "방금 확인한 내용을 손님에게 한두 문장으로 말해 주세요."}
                )
                continue
            final = {"message": content}
            if order_sheet:
                final.update(order_sheet)  # items, total
                if not final["message"]:
                    final["message"] = "주문이 완료되었습니다. 감사합니다!"
            # 가드레일 — 메뉴판 요청인데 모델이 도구를 안 불렀어도 메뉴판은 뜬다.
            # 결정적으로 처리할 수 있는 UX를 확률적 컴포넌트에만 맡기지 않습니다.
            if menu_board is None and _wants_menu_board(user_message):
                menu_board = load_menu()
            if menu_board:
                final["menu"] = menu_board  # 웹이 메뉴판 표로 렌더링
                if not final["message"]:
                    final["message"] = "분식왕 메뉴판입니다."
            return final

        # 모델의 도구 호출 결정과 실행 결과를 대화 이력에 쌓고 재호출합니다
        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            result = execute(call.function.name, arguments)
            if call.function.name == "create_order" and "items" in result:
                order_sheet = result
            # 메뉴판 전체 조회면 구조 데이터로 응답에 실어 웹이 표로 그리게 합니다
            if call.function.name == "search_menu" and result.get("board"):
                menu_board = result.get("results")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return {"message": "죄송합니다, 주문 처리가 길어졌어요. 다시 한 번 말씀해 주시겠어요?"}
