from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, Base, engine


def test_database_base_collects_all_model_tables():
    import app.models  # noqa: F401

    assert {"users", "patients", "medical_records", "lab_results", "audit_log"} <= set(Base.metadata.tables)


def test_async_session_factory_is_bound_to_application_engine():
    assert AsyncSessionLocal.kw["bind"] is engine
    assert AsyncSessionLocal.class_ is AsyncSession
    assert AsyncSessionLocal.kw["expire_on_commit"] is False
