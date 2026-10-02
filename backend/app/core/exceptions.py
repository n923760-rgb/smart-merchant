from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status = 400
    code = "APPLICATION_ERROR"
    message = "Request failed."


class NotFoundError(AppError):
    status, code, message = 404, "NOT_FOUND", "Resource not found."


class ValidationError(AppError):
    status, code, message = 422, "VALIDATION_ERROR", "Invalid request."


class PermissionDeniedError(AppError):
    status, code, message = 403, "INSUFFICIENT_PERMISSION", "You do not have access to this action."


class ConflictError(AppError):
    status, code, message = 409, "CONFLICT", "Resource conflicts with existing data."


class AuthenticationError(AppError):
    status, code, message = 401, "AUTHENTICATION_FAILED", "Authentication failed."


class RateLimitedError(AppError):
    status, code, message = 429, "RATE_LIMITED", "Try again later."


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": {},
            "request_id": getattr(request.state, "request_id", None),
        },
    )
