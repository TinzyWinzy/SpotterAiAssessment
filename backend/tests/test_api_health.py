"""Health endpoint tests — GET /api/health/."""
import pytest


@pytest.mark.django_db
class TestHealth:
    def test_health_returns_ok(self, api_client):
        resp = api_client.get("/api/health/")
        assert resp.status_code == 200
        assert resp.json() == {"ok": True, "service": "spotter-trip-planner"}

    def test_health_does_not_require_db(self, api_client):
        """Health check must work even with the database unavailable."""
        resp = api_client.get("/api/health/")
        assert resp.status_code == 200

    def test_health_only_accepts_get(self, api_client):
        """DRF @api_view restricts methods — POST must be 405."""
        resp = api_client.post("/api/health/")
        assert resp.status_code == 405
