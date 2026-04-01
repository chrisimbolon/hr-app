"""
core/exceptions.py
──────────────────
Domain exceptions + global FastAPI exception handlers.
All errors return a consistent JSON envelope.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Standard error envelope ──────────────────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


# ── Domain exceptions ────────────────────────────────────────────

class HadirException(Exception):
    """Base exception for all domain errors."""
    def __init__(self, message: str, code: str = "HADIR_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(HadirException):
    def __init__(self, entity: str, id: str = ""):
        super().__init__(
            message=f"{entity} not found" + (f": {id}" if id else ""),
            code="NOT_FOUND",
            status_code=404,
        )


class ConflictError(HadirException):
    def __init__(self, message: str):
        super().__init__(message=message, code="CONFLICT", status_code=409)


class ValidationError(HadirException):
    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422)


class AuthorizationError(HadirException):
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class BusinessRuleError(HadirException):
    """Raised when a domain business rule is violated."""
    def __init__(self, message: str):
        super().__init__(message=message, code="BUSINESS_RULE_VIOLATION", status_code=422)


# ── FastAPI exception handlers ───────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(HadirException)
    async def hadir_exception_handler(request: Request, exc: HadirException):
        field = getattr(exc, "field", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "field": field,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        first_error = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(loc) for loc in first_error.get("loc", []))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": first_error.get("msg", "Validation failed"),
                    "field": field,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        import structlog
        log = structlog.get_logger()
        log.error("unhandled_exception", exc=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "field": None,
                },
            },
        )