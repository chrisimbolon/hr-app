"""shared/schemas/base.py"""
import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UUIDSchema(BaseSchema):
    id: uuid.UUID


class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime


class ApiResponse(BaseSchema, Generic[T]):
    """Standard API response envelope."""
    success: bool = True
    data: T
    message: str | None = None


class PaginatedResponse(BaseSchema, Generic[T]):
    success: bool = True
    data: list[T]
    total: int
    page: int
    pages: int
    page_size: int