"""
core/logging.py
───────────────
Structlog setup with JSON output for production (Logtail-friendly)
and colourised console output for development.
"""
import logging
import sys

import structlog
from app.core.config import settings


def setup_logging() -> None:
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,  # IMPORTANT
    ]

    # 🚨 NO renderer here
    processors = shared_processors

    if settings.is_production:
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processor=structlog.processors.JSONRenderer(),
        )
    else:
        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processor=structlog.dev.ConsoleRenderer(colors=True),
        )

    structlog.configure(
        processors=processors,  # ✅ only shared_processors
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),  # ✅ correct
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Silence noisy third-party loggers
    for logger_name in ("uvicorn.access", "sqlalchemy.engine", "multipart"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)