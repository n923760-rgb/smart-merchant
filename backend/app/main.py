import redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import AppError, handle_app_error
from app.core.logging import configure_logging
from app.core.middleware import request_middleware

settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Organization-ID", "X-Bootstrap-Key"],
    expose_headers=["X-Request-ID"],
)
app.middleware("http")(request_middleware)
app.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            "message": "Resource not found." if exc.status_code == 404 else str(exc.detail),
            "details": {},
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Invalid request.",
            "details": {"fields": [".".join(map(str, error["loc"])) for error in exc.errors()]},
            "request_id": request.state.request_id,
        },
    )


app.include_router(router)


@app.get("/health/live")
def live():
    return {"status": "alive"}


@app.get("/health/ready")
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        redis.Redis.from_url(settings.redis_url).ping()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "code": "DEPENDENCY_UNAVAILABLE",
                "message": "Service not ready.",
                "details": {},
            },
        )
    return {"status": "ready"}
