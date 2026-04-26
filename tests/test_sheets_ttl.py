from __future__ import annotations

from tests.conftest import import_module


class _Clock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def monotonic(self) -> float:
        return self.now


def test_get_client_retries_after_ttl_on_none(app_env, monkeypatch) -> None:
    sheets = import_module("bot.services.sheets")
    clock = _Clock()
    configured = False
    credential_loads = []
    client = object()

    def is_configured() -> bool:
        return configured

    def load_credentials(creds_file: str, scopes: list[str]) -> object:
        credential_loads.append((creds_file, scopes))
        return object()

    monkeypatch.setattr(sheets.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(sheets, "_is_configured", is_configured)
    monkeypatch.setattr(sheets.Credentials, "from_service_account_file", load_credentials)
    monkeypatch.setattr(sheets.gspread, "authorize", lambda creds: client)

    assert sheets._get_client() is None
    assert credential_loads == []

    configured = True
    clock.now += sheets._CLIENT_TTL_SECONDS + 1

    assert sheets._get_client() is client
    assert len(credential_loads) == 1


def test_get_client_caches_within_ttl(app_env, monkeypatch) -> None:
    sheets = import_module("bot.services.sheets")
    clock = _Clock(now=100.0)
    credential_loads = []
    clients = [object(), object()]
    authorize_calls = 0

    def load_credentials(creds_file: str, scopes: list[str]) -> object:
        credential_loads.append((creds_file, scopes))
        return object()

    def authorize(creds: object) -> object:
        nonlocal authorize_calls
        client = clients[authorize_calls]
        authorize_calls += 1
        return client

    monkeypatch.setattr(sheets.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(sheets, "_is_configured", lambda: True)
    monkeypatch.setattr(sheets.Credentials, "from_service_account_file", load_credentials)
    monkeypatch.setattr(sheets.gspread, "authorize", authorize)

    assert sheets._get_client() is clients[0]
    clock.now += sheets._CLIENT_TTL_SECONDS - 1
    assert sheets._get_client() is clients[0]
    assert len(credential_loads) == 1
    assert authorize_calls == 1

    clock.now += 2
    assert sheets._get_client() is clients[1]
    assert len(credential_loads) == 2
    assert authorize_calls == 2
