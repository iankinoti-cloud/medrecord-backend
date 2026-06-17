from app.config import settings
from sqlalchemy import String, JSON
from sqlalchemy.types import TypeDecorator, CHAR
import uuid

if settings.DATABASE_URL.startswith("sqlite"):
    class GUID(TypeDecorator):
        impl = CHAR

        cache_ok = True

        def __init__(self, length=36, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.length = length

        def process_bind_param(self, value, dialect):
            if value is None:
                return value
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

        def process_result_value(self, value, dialect):
            if value is None:
                return value
            return uuid.UUID(value)

    def UUID(*args, **kwargs):
        # return a GUID TypeDecorator suitable for SQLite
        return GUID()

    JSONB = JSON
    INET = String(45)
else:
    from sqlalchemy.dialects.postgresql import UUID as UUID, JSONB as JSONB, INET as INET
