# week01-order-agent — 분식왕 주문 에이전트

가상 분식집 **"분식왕"의 주문 접수 AI 점원**입니다. 1주차 라이브 빌드에서
Claude Code에 지시 프롬프트를 주어 **지시 → 생성 → 검증 → 수정 사이클**로
완성하는 시연용 저장소입니다.

- **v0.1** — 시연 시작점. `/order`가 고정 문자열만 돌려주는 "거짓말하는 API"
- **v1.0** — 시연 종료점. 에이전트 루프가 도구(메뉴 검색·재고 확인·주문서 생성)를
  골라 쓰며 주문서 json을 반환

시연에서 무엇이 만들어졌는지는 태그 간 diff 하나로 볼 수 있습니다.

```bash
git diff v0.1 v1.0
```

## 구조

```plaintext
week01-order-agent
├── app/
│   └── main.py          # FastAPI — /order가 에이전트 루프 호출
├── agent/
│   └── loop.py          # 에이전트 루프 (도구 호출 여부를 모델이 결정)
├── llm/
│   └── client.py        # LiteLLM 래퍼 (MODEL 환경변수로 모델 교체)
├── tools/
│   ├── menu.py          # 메뉴 검색 — data/menu.json
│   ├── stock.py         # 재고 확인 — data/stock.json
│   └── order.py         # 주문서 생성 — 단가·합계는 코드가 계산
├── web/
│   └── index.html       # 웹 주문 화면 (채팅형 UI, /order 호출)
├── data/
│   ├── menu.json        # 메뉴 22개 (이름·가격·옵션)
│   └── stock.json       # 재고 수량
├── .env.example         # GEMINI_API_KEY, MODEL
├── pyproject.toml       # litellm, fastapi 등 의존성 선언
├── PROMPT.md            # 시연에서 사용한 지시 프롬프트 원문
├── Dockerfile
├── compose.yml          # 기본 실행
├── compose.dev.yml      # 개발용 (소스 마운트 + 자동 리로드)
└── README.md
```

시연 시작점(목 API)은 `git checkout v0.1`로 볼 수 있습니다.

## 실행 방법

### 1. 환경변수 준비

```bash
cp .env.example .env
```

`.env`에 [Google AI Studio](https://aistudio.google.com/apikey)에서 발급한
`GEMINI_API_KEY`를 채웁니다. 파일 대신 웹 화면의 **⚙️ 설정** 버튼으로
입력해도 됩니다. 키가 없으면 `/order` 호출이 인증 오류를 돌려줍니다.

`MODEL`은 LiteLLM 모델 문자열입니다. 이 값만 바꾸면 코드 수정 없이
다른 프로바이더로 전환됩니다 (예: `anthropic/claude-sonnet-5`, `ollama/llama3`).

### 2. Docker Compose로 실행

**기본 실행** — 이미지에 구운 코드를 그대로 실행합니다.

```bash
docker compose up --build
```

**개발 모드** — 소스를 컨테이너에 마운트하고 `--reload`로 실행하므로,
코드가 바뀌면 재빌드 없이 즉시 반영됩니다. 라이브 빌드는 이 모드로 진행합니다.

```bash
docker compose -f compose.dev.yml up --build
```

### 3. 주문해 보기

**웹 화면**: <http://localhost:8000> 에 접속해 채팅으로 주문합니다.

- 예시 버튼(정상 주문·메뉴에 없는 항목·재고 초과)이 준비되어 있습니다
- 입력창에 `/clear`를 치면 대화(세션)가 초기화됩니다
- 오른쪽 위 **⚙️ 설정** 버튼에서 `.env`의 `GEMINI_API_KEY`, `MODEL`을
  확인·저장할 수 있습니다. 저장하면 서버의 `.env`에 기록되고 즉시 적용됩니다
  (개발 모드에서는 호스트의 `.env` 파일에 그대로 남습니다). 로컬 시연용
  기능이므로 외부에 공개된 서버에서는 사용하지 마세요.

**curl**:

```bash
curl -s -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -d '{"message": "참치김밥 두 줄이랑 라면 하나, 라면은 치즈 추가"}'
```

응답 — 주문서 json (단가·합계는 모델이 아니라 `tools/order.py`가 계산):

```json
{
  "message": "참치김밥 두 줄과 치즈 추가 라면 하나, 총 13,500원입니다!",
  "items": [
    { "name": "참치김밥", "quantity": 2, "options": [], "unit_price": 4500, "subtotal": 9000 },
    { "name": "라면", "quantity": 1, "options": ["치즈 추가"], "unit_price": 4500, "subtotal": 4500 }
  ],
  "total": 13500
}
```

메뉴에 없는 항목("돈까스 되나요?")이나 재고 초과("김밥 100줄")는 정중히
거절하고 대안을 제시합니다.

### (선택) 로컬에서 uv로 실행

```bash
uv sync
uv run uvicorn app.main:app --reload
```

## 기술 원칙

- 모든 LLM 호출은 **LiteLLM 경유** — 프로바이더 SDK 직접 호출 금지
- 모델 문자열은 환경변수 `MODEL`로 분리 — 이 값만 바꾸면 Gemini도 Claude도
  로컬 모델도 됩니다
- 모듈 분리: `llm/` `tools/` `agent/` — 단일 파일 금지
- 결과는 구조화 출력(주문서 json) — LLM은 채팅이 아니라 시스템 부품

## 브랜치 전략

git flow를 따릅니다.

- `main` — 릴리즈 전용 (v0.1, v1.0 태그)
- `develop` — 통합 브랜치
- `feature/*` — 작업 브랜치
