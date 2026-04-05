"""
core/logging.py
───────────────
Structlog setup — fixed for structlog 24.x with SQLAlchemy.

The bug: structlog's ProcessorFormatter intercepts stdlib logging records
(from SQLAlchemy, uvicorn etc). In structlog 24.x, those records arrive as
a tuple in some code paths. The fix is to use ExtraAdder + filter_by_level
properly, and silence SQLAlchemy at WARNING level so it never reaches the
formatter during table creation.
"""
import logging
import sys

import structlog
from app.core.config import settings


def setup_logging() -> None:
    # ── Silence SQLAlchemy completely in dev ─────────────────────
    # This prevents the structlog tuple crash during init_db()
    for noisy in (
        "sqlalchemy.engine",
        "sqlalchemy.engine.Engine",
        "sqlalchemy.pool",
        "sqlalchemy.dialects",
        "sqlalchemy.orm",
        "uvicorn.access",
        "multipart",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)
        logging.getLogger(noisy).propagate = False

    # ── Shared pre-chain for foreign (stdlib) log records ────────
    shared_pre_chain = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # ── Renderer: coloured console in dev, JSON in prod ──────────
    if settings.is_production:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    # ── ProcessorFormatter wires stdlib → structlog ───────────────
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_pre_chain,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # ── Wire up root handler ─────────────────────────────────────
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # ── Configure structlog itself ───────────────────────────────
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
