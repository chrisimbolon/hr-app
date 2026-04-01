"""
main.py
────────
HaDir HRMS FastAPI application factory.
Registers all module routers, middleware, exception handlers.
"""
from contextlib import asynccontextmanager

import structlog
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import (AuditMiddleware, RateLimitMiddleware,
                                 RequestContextMiddleware)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    setup_logging()
    await init_db()
    log.info(
        "hadir_api.started",
        version=settings.APP_VERSION,
        env=settings.ENV,
    )
    yield
    await close_db()
    log.info("hadir_api.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="HaDir HRMS — Indonesia SaaS HR & Attendance Platform",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost registered last) ───
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestContextMiddleware)

    # ── Exception handlers ───────────────────────────────────────
    register_exception_handlers(app)

    # ── Sentry (production only) ─────────────────────────────────
    if settings.SENTRY_DSN and settings.is_production:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
            environment=settings.ENV,
        )

    # ── Mount module routers ─────────────────────────────────────
    _register_routers(app)

    # ── Health check ─────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health():
        return {
            "status": "ok",
            "version": settings.APP_VERSION,
            "env": settings.ENV,
        }

    return app


def _register_routers(app: FastAPI) -> None:
    """Mount all module routers with versioned prefix."""
    from app.modules.attendance.presentation.api.v1.routes import \
        router as attendance_router
    from app.modules.audit.presentation.api.v1.routes import \
        router as audit_router
    from app.modules.auth.presentation.api.v1.routes import \
        router as auth_router
    from app.modules.employee.presentation.api.v1.routes import \
        router as employee_router
    from app.modules.leave.presentation.api.v1.routes import \
        router as leave_router
    from app.modules.payroll.presentation.api.v1.routes import \
        router as payroll_router

    V1 = "/v1"

    app.include_router(auth_router,       prefix=f"{V1}/auth",       tags=["Auth"])
    app.include_router(employee_router,   prefix=f"{V1}/employees",  tags=["Employees"])
    app.include_router(attendance_router, prefix=f"{V1}/attendance", tags=["Attendance"])
    app.include_router(leave_router,      prefix=f"{V1}/leave",      tags=["Leave"])
    app.include_router(payroll_router,    prefix=f"{V1}/payroll",    tags=["Payroll"])
    app.include_router(audit_router,      prefix=f"{V1}/audit",      tags=["Audit"])


app = create_app()
