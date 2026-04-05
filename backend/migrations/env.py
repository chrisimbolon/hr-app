"""
migrations/env.py
──────────────────────
Alembic async migration environment.
Discovers all SQLAlchemy models automatically via Base.metadata.
"""
import asyncio
from logging.config import fileConfig

import app.modules.attendance.infrastructure.models  # noqa: F401
import app.modules.audit.infrastructure.models  # noqa: F401
# Import all models — Alembic needs to see them to generate migrations
import app.modules.employee.infrastructure.models  # noqa: F401
import app.modules.leave.infrastructure.models  # noqa: F401
import app.modules.payroll.infrastructure.models  # noqa: F401
from alembic import context
from app.core.config import settings
# Import Base and ALL models so Alembic discovers them
from app.core.database import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

# Override sqlalchemy.url from env (ignores alembic.ini placeholder)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (no DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,          # detect column type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,    # no connection pooling for migrations
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
