"""Public service catalogue endpoint tests."""


class TestServices:
    def test_services_are_available_without_authentication(self, api_client):
        resp = api_client.get("/api/services/")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["services"]

    def test_services_only_accept_get(self, api_client):
        resp = api_client.post("/api/services/", {}, format="json")

        assert resp.status_code == 405
