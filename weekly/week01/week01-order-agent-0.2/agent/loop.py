"""에이전트 루프 — 도구를 부를지, 몇 번 부를지, 언제 멈출지를 모델이 결정합니다.

이 while 루프가 하네스의 씨앗입니다. 지금은 루프뿐이지만, 여기에
가드레일·검증·메모리가 붙으면 하네스 엔지니어링이 됩니다.
"""

import json

from llm.client import complete
from tools import TOOL_SCHEMAS, execute

SYSTEM_PROMPT = """\
너는 분식집 '분식왕'의 주문 접수 점원이다. 한국어로 정중하고 간결하게 응대한다.

규칙:
- 메뉴 이름·가격·옵션은 절대 지어내지 말고 반드시 search_menu로 확인한다
- 메뉴판을 보여달라고 하면 search_menu를 검색어 없이 호출해 전체 메뉴를
  카테고리별로 가격·옵션까지 목록으로 정리해 보여준다
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


def run_agent(user_message: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    order_sheet = None

    for _ in range(MAX_TURNS):
        response = complete(messages, tools=TOOL_SCHEMAS)
        message = response.choices[0].message

        # 도구 호출이 없으면 모델이 답을 확정한 것 — 루프를 멈춥니다
        if not message.tool_calls:
            final = {"message": (message.content or "").strip()}
            if order_sheet:
                final.update(order_sheet)  # items, total
            return final

        # 모델의 도구 호출 결정과 실행 결과를 대화 이력에 쌓고 재호출합니다
        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            result = execute(call.function.name, arguments)
            if call.function.name == "create_order" and "items" in result:
                order_sheet = result
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    return {"message": "죄송합니다, 주문 처리가 길어졌어요. 다시 한 번 말씀해 주시겠어요?"}
