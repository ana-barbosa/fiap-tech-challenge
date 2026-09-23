import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from . import chroma_store, config, pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("etl")

_state: dict = {"status": "starting", "last_run_at": None, "last_error": None}


def _poll_loop() -> None:
    while True:
        try:
            stats = pipeline.run_once()
            _state.update(stats)
            _state["status"] = "ok"
            _state["last_error"] = None
            logger.info("ETL cycle complete: %s", stats)
        except Exception as exc:
            _state["status"] = "error"
            _state["last_error"] = str(exc)
            logger.exception("ETL cycle failed")
        time.sleep(config.POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    chroma_store.warm_up()
    threading.Thread(target=_poll_loop, daemon=True).start()
    yield


app = FastAPI(title="ETL Service", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict:
    return _state
