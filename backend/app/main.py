"""TourMate API. Запуск: uvicorn app.main:app --reload"""
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import errors
from .config import CORS_ORIGINS
from .routers import auth, personal, places, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("tourmate")

app = FastAPI(title="TourMate API", version="1.0.0")
API = "/api/v1"

# Підготовка до інтеграції з frontend: CORS для клієнта Flutter Web.
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Журнал запитів: метод, шлях, статус, тривалість."""
    start = time.perf_counter()
    response = await call_next(request)
    log.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000)
    return response


errors.install(app)
for r in (auth.router, users.router, places.router, personal.router):
    app.include_router(r, prefix=API)


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}
