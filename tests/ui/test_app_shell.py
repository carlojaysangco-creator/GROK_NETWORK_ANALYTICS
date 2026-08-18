"""UI shell construction tests."""

from __future__ import annotations

from network_analytics.shared.config import ApplicationConfig
from network_analytics.ui import create_dash_app


def test_create_dash_app_succeeds(config: ApplicationConfig) -> None:
    app = create_dash_app(config)
    assert app.title == "Network Analytics"


def test_healthz_endpoint(config: ApplicationConfig) -> None:
    app = create_dash_app(config)
    client = app.server.test_client()
    response = client.get("/healthz")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["collection_enabled"] is False
    assert payload["live_topology_enabled"] is False
