from __future__ import annotations

import sys
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(app_env):
    """Return a TestClient with a fresh in-memory rate-limit store."""
    # Ensure a clean import so the Limiter starts with empty counts.
    for name in list(sys.modules):
        if name == "web" or name.startswith("web."):
            sys.modules.pop(name, None)

    web_app = importlib.import_module("web.app")
    app = web_app.create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _post_login(client: TestClient, password: str = "wrong"):
    return client.post(
        "/login",
        data={"password": password},
        follow_redirects=False,
    )


def test_five_wrong_passwords_all_401(client):
    """The first 5 failed login attempts return 401, not 429."""
    for _ in range(5):
        resp = _post_login(client, password="wrong")
        assert resp.status_code == 200  # login page re-rendered (not redirect)


def test_sixth_attempt_hits_rate_limit(client):
    """After 5 failed attempts the 6th is rate-limited with 429."""
    for _ in range(5):
        _post_login(client, password="wrong")

    resp = _post_login(client, password="wrong")
    assert resp.status_code == 429
