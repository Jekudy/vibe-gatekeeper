from __future__ import annotations

import json
from typing import Any

import httpx
from cryptography.fernet import Fernet

from ops.healing.snapshot import Snapshot, create_snapshot, restore_snapshot


def test_create_snapshot_encrypts_env_dump(monkeypatch: Any) -> None:
    monkeypatch.setenv("COOLIFY_BASE_URL", "https://coolify.example.invalid")
    key = Fernet.generate_key().decode("ascii")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/v1/applications/app-uuid":
            return httpx.Response(
                200,
                json={"docker_registry_image_tag": "sha-caebb519", "restart_count": 12},
            )
        if request.method == "GET" and request.url.path == "/api/v1/applications/app-uuid/envs":
            return httpx.Response(
                200,
                json={"data": [{"key": "BOT_TOKEN", "value": "123456:test"}]},
            )
        return httpx.Response(404)

    monkeypatch.setattr(
        "ops.healing.snapshot._build_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )

    snapshot = create_snapshot("coolify-token", "app-uuid", key)

    assert snapshot.prod_image_sha == "sha-caebb519"
    assert snapshot.restart_count == 12
    assert "123456:test" not in snapshot.env_dump_encrypted
    assert snapshot.env_hash.startswith("sha256:")


def test_restore_snapshot_patches_image_and_env(monkeypatch: Any) -> None:
    monkeypatch.setenv("COOLIFY_BASE_URL", "https://coolify.example.invalid")
    key = Fernet.generate_key().decode("ascii")
    sent_requests: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_requests.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        "ops.healing.snapshot._build_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    snapshot = Snapshot.from_env_dump(
        prod_image_sha="sha-caebb519",
        restart_count=12,
        env_dump={"BOT_TOKEN": "123456:test"},
        env_key=key,
        trigger_signal={"coolify_status": "red"},
    )

    restore_snapshot(snapshot, "coolify-token", "app-uuid", key)

    assert sent_requests[0] == (
        "PATCH",
        "/api/v1/applications/app-uuid",
        {"docker_registry_image_tag": "sha-caebb519"},
    )
    assert sent_requests[1] == (
        "PATCH",
        "/api/v1/applications/app-uuid/envs",
        {"envs": [{"key": "BOT_TOKEN", "value": "123456:test"}]},
    )
