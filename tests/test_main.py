import pytest

from app import main


pytestmark = pytest.mark.asyncio


class SuccessfulSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement):
        return None


class FailingSession:
    async def __aenter__(self):
        raise RuntimeError("database offline")

    async def __aexit__(self, exc_type, exc, tb):
        return False


async def test_health_reports_ok_database_when_select_succeeds(monkeypatch):
    monkeypatch.setattr(main, "AsyncSessionLocal", lambda: SuccessfulSession())

    result = await main.health()

    assert result == {"status": "ok", "db": "ok", "version": "1.0.0"}


async def test_health_reports_unreachable_database_when_select_fails(monkeypatch):
    monkeypatch.setattr(main, "AsyncSessionLocal", lambda: FailingSession())

    result = await main.health()

    assert result == {"status": "ok", "db": "unreachable", "version": "1.0.0"}


async def test_app_registers_expected_routes_and_middleware():
    routes = {route.path for route in main.app.routes}

    assert "/health" in routes
    assert "/auth/login" in routes
    assert "/admin/users" in routes
    assert "/patients" in routes
    assert "/lab/upload" in routes
    assert any(middleware.cls.__name__ == "CORSMiddleware" for middleware in main.app.user_middleware)
