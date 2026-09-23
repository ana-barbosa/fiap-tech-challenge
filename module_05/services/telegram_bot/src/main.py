import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from . import bot, config, offset_store, telegram_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_bot")


class _HealthCheckLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HealthCheckLogFilter())

_state: dict = {"status": "starting", "last_update_id": None, "last_error": None}

ERROR_BACKOFF_SECONDS = 5


def _poll_loop() -> None:
    offset = offset_store.read_offset()
    while True:
        try:
            updates = telegram_client.get_updates(offset, config.GETUPDATES_TIMEOUT_SECONDS)
            for update in updates:
                bot.process_update(update)
                offset = update["update_id"] + 1
                offset_store.write_offset(offset)
                _state["last_update_id"] = update["update_id"]
            _state["status"] = "ok"
            _state["last_error"] = None
            logger.info("Poll cycle complete: %d update(s) processed", len(updates))
        except Exception as exc:
            _state["status"] = "error"
            _state["last_error"] = str(exc)
            logger.exception("Poll cycle failed")
            time.sleep(ERROR_BACKOFF_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_poll_loop, daemon=True).start()
    yield


app = FastAPI(title="Telegram Bot Service", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


class PushRequest(BaseModel):
    chat_id: int
    text: str


@app.get("/health")
def health() -> dict:
    return _state


@app.post("/push")
def push(data: PushRequest) -> dict:
    telegram_client.send_message(data.chat_id, data.text)
    return {"status": "sent"}
