"""분식왕 주문 접수 API — /order가 에이전트 루프를 호출합니다."""

import os
from pathlib import Path

from dotenv import load_dotenv, set_key
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.loop import run_agent

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

app = FastAPI(title="분식왕 주문 에이전트", version="0.1.0")


class OrderRequest(BaseModel):
    message: str


class SettingsUpdate(BaseModel):
    gemini_api_key: str | None = None
    model: str | None = None


@app.post("/order")
def order(request: OrderRequest) -> dict:
    try:
        return run_agent(request.message)
    except Exception as exc:  # 시연용 — 실패 원인이 화면에 보이게 (첫 줄만)
        reason = str(exc).splitlines()[0] if str(exc) else repr(exc)
        return {"message": "죄송합니다, 주문 처리 중 문제가 생겼어요.", "error": reason}


def _settings_view() -> dict:
    key = os.environ.get("GEMINI_API_KEY", "")
    return {
        "model": os.environ.get("MODEL", ""),
        "gemini_api_key_set": bool(key),
        "gemini_api_key_hint": f"…{key[-4:]}" if len(key) >= 8 else "",
    }


@app.get("/settings")
def get_settings() -> dict:
    return _settings_view()


@app.put("/settings")
def update_settings(update: SettingsUpdate) -> dict:
    """웹 화면의 ⚙️ 설정 저장 — .env 파일에 기록하고 즉시 적용합니다. 로컬 시연용."""
    ENV_PATH.touch(exist_ok=True)
    for env_key, value in (
        ("GEMINI_API_KEY", update.gemini_api_key),
        ("MODEL", update.model),
    ):
        if value:  # 빈 값은 기존 설정 유지
            set_key(ENV_PATH, env_key, value.strip())
            os.environ[env_key] = value.strip()
    return _settings_view()


# 웹 주문 화면 — API 라우트보다 뒤에 마운트해야 /order가 가려지지 않습니다.
# 경로는 이 파일 기준 절대 경로 — 어느 디렉터리에서 실행해도 동작합니다.
app.mount("/", StaticFiles(directory=BASE_DIR / "web", html=True), name="web")
