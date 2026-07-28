"""Validation tests for POST /api/trip/."""
from __future__ import annotations

import pytest

URL = "/api/trip/"


def _body(**overrides):
    body = {
        "origin": "Harare, Zimbabwe",
        "destination": "Beitbridge, Zimbabwe",
    }
    body.update(overrides)
    return body


@pytest.mark.django_db(transaction=True)
class TestTripValidation:
    def test_missing_origin(self, api_client, mock_geo_router):
        resp = api_client.post(URL, {"destination": "Beitbridge, Zimbabwe"}, format="json")
        assert resp.status_code == 400

    def test_missing_destination(self, api_client, mock_geo_router):
        resp = api_client.post(URL, {"origin": "Harare, Zimbabwe"}, format="json")
        assert resp.status_code == 400

    def test_empty_body(self, api_client, mock_geo_router):
        resp = api_client.post(URL, {}, format="json")
        assert resp.status_code == 400

    def test_unknown_origin_fails(self, api_client, mock_geo_router):
        resp = api_client.post(URL, _body(origin="Unknown City, ZZ"), format="json")
        assert resp.status_code == 400
        assert "origin" in resp.json()["error"].lower()
