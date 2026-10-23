import logging
from typing import Any, Optional
from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx_var

logger = logging.getLogger("app.exceptions")


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "BAD_REQUEST",
        details: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


def format_error_response(
    code: str,
    message: str,
    request_id: str,
    details: Optional[Any] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> JSONResponse:
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": jsonable_encoder(details) if details is not None else None,
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", request_id_ctx_var.get())
    logger.warning("Application exception [%s]: %s", exc.code, exc.message)
    return format_error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=req_id,
        status_code=exc.status_code,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", request_id_ctx_var.get())
    serializable_errors = jsonable_encoder(exc.errors())
    logger.warning("Validation failed: %s", serializable_errors)
    return format_error_response(
        code="VALIDATION_ERROR",
        message="Invalid request payload or parameters.",
        details=serializable_errors,
        request_id=req_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", request_id_ctx_var.get())
    return format_error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        details=None,
        request_id=req_id,
        status_code=exc.status_code,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = getattr(request.state, "request_id", request_id_ctx_var.get())
    logger.exception("Unhandled server exception: %s", exc)
    return format_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred.",
        details=None,
        request_id=req_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
