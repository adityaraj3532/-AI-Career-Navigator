from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import RequestIdMiddleware
from app.core.redis import close_redis

settings = get_settings()
setup_logging(settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup actions
    yield
    # Shutdown actions
    await close_redis()


def create_application() -> FastAPI:
    app = FastAPI(
        title="AI Career Navigator API",
        version="1.0.0",
        description="Backend API services for AI Career Navigator",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Middleware registration
    app.add_middleware(RequestIdMiddleware)

    # Exception handler registration
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Router mounting
    app.include_router(api_v1_router, prefix="/v1")

    # Root alias for container orchestrators
    @app.get("/health", include_in_schema=False)
    async def root_health():
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app


app = create_application()
