"""Єдиний формат помилок API: {"status": код, "message": опис}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("tourmate")


class AppError(Exception):
    """Помилка бізнес-логіки з HTTP-статусом."""

    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message


def not_found(what: str) -> AppError:
    return AppError(404, f"{what} not found")


def _body(status: int, message: str, **extra) -> JSONResponse:
    return JSONResponse({"status": status, "message": message, **extra}, status_code=status)


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, e: AppError):
        return _body(e.status, e.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, e: RequestValidationError):
        # 400 замість типового 422: методичні вказівки визначають 400 для некоректного запиту.
        errors = [
            {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
            for err in e.errors()
        ]
        return _body(400, "Validation error", errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, e: StarletteHTTPException):
        return _body(e.status_code, str(e.detail))

    @app.exception_handler(IntegrityError)
    async def integrity_error(_: Request, e: IntegrityError):
        log.warning("integrity error: %s", e.orig)
        return _body(409, "Data conflict")

    @app.exception_handler(Exception)
    async def unhandled(_: Request, e: Exception):
        log.exception("unhandled error")
        return _body(500, "Internal server error")
