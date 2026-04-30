from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from ops.healing.crypto import decrypt, encrypt


@dataclass(frozen=True)
class Snapshot:
    ts: str
    prod_image_sha: str
    env_hash: str
    env_dump_encrypted: str
    restart_count: int
    trigger_signal: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env_dump(
        cls,
        prod_image_sha: str,
        restart_count: int,
        env_dump: dict[str, str],
        env_key: str,
        trigger_signal: dict[str, Any],
    ) -> Snapshot:
        encoded_env = json.dumps(env_dump, sort_keys=True, separators=(",", ":"))
        return cls(
            ts=datetime.now(UTC).isoformat(),
            prod_image_sha=prod_image_sha,
            env_hash=_env_hash(env_dump),
            env_dump_encrypted=encrypt(encoded_env, env_key),
            restart_count=restart_count,
            trigger_signal=trigger_signal,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Snapshot:
        return cls(
            ts=str(value["ts"]),
            prod_image_sha=str(value["prod_image_sha"]),
            env_hash=str(value["env_hash"]),
            env_dump_encrypted=str(value["env_dump_encrypted"]),
            restart_count=int(value["restart_count"]),
            trigger_signal=dict(value.get("trigger_signal", {})),
        )

    def decrypt_env_dump(self, env_key: str) -> dict[str, str]:
        value = json.loads(decrypt(self.env_dump_encrypted, env_key))
        if not isinstance(value, dict):
            raise ValueError("snapshot env dump must decrypt to a JSON object")
        return {str(key): str(raw_value) for key, raw_value in value.items()}


def _coolify_base_url() -> str:
    value = os.environ.get("COOLIFY_BASE_URL")
    if not value:
        raise KeyError("missing required env var: COOLIFY_BASE_URL")
    return value.rstrip("/")


def _build_client() -> httpx.Client:
    return httpx.Client(timeout=20)


def _headers(coolify_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {coolify_token}", "Content-Type": "application/json"}


def _env_hash(env_dump: dict[str, str]) -> str:
    encoded = json.dumps(env_dump, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _normalise_envs(payload: Any) -> dict[str, str]:
    raw_items = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
    if not isinstance(raw_items, list):
        raise ValueError("Coolify env response must be a list or data list")
    envs: dict[str, str] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("Coolify env item must be an object")
        envs[str(item["key"])] = str(item["value"])
    return envs


def create_snapshot(coolify_token: str, app_uuid: str, env_key: str) -> Snapshot:
    base_url = _coolify_base_url()
    with _build_client() as client:
        app_response = client.get(
            f"{base_url}/api/v1/applications/{app_uuid}",
            headers=_headers(coolify_token),
        )
        app_response.raise_for_status()
        app_payload = app_response.json()

        env_response = client.get(
            f"{base_url}/api/v1/applications/{app_uuid}/envs",
            headers=_headers(coolify_token),
        )
        env_response.raise_for_status()
        env_dump = _normalise_envs(env_response.json())

    return Snapshot.from_env_dump(
        prod_image_sha=str(app_payload["docker_registry_image_tag"]),
        restart_count=int(app_payload["restart_count"]),
        env_dump=env_dump,
        env_key=env_key,
        trigger_signal={},
    )


def restore_snapshot(
    snapshot: Snapshot,
    coolify_token: str,
    app_uuid: str,
    env_key: str,
) -> None:
    base_url = _coolify_base_url()
    env_dump = snapshot.decrypt_env_dump(env_key)
    envs = [{"key": key, "value": value} for key, value in sorted(env_dump.items())]
    with _build_client() as client:
        image_response = client.patch(
            f"{base_url}/api/v1/applications/{app_uuid}",
            headers=_headers(coolify_token),
            json={"docker_registry_image_tag": snapshot.prod_image_sha},
        )
        image_response.raise_for_status()
        env_response = client.patch(
            f"{base_url}/api/v1/applications/{app_uuid}/envs",
            headers=_headers(coolify_token),
            json={"envs": envs},
        )
        env_response.raise_for_status()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or restore healing snapshots.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--output", required=True)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("--input", required=True)

    return parser


def main() -> int:
    args = _build_parser().parse_args()
    coolify_token = os.environ["COOLIFY_API_TOKEN"]
    app_uuid = os.environ["COOLIFY_APP_UUID"]
    env_key = os.environ["HEALING_ENV_KEY"]

    if args.command == "create":
        snapshot = create_snapshot(coolify_token, app_uuid, env_key)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return 0

    if args.command == "restore":
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        restore_snapshot(Snapshot.from_dict(payload), coolify_token, app_uuid, env_key)
        return 0

    raise ValueError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
