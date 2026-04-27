"""Content hash strategy for ``message_versions`` (T1-07 minimal; T1-08 ratifies).

The hash pins one content state of a message so q&a citations remain stable across
edits (Phase 4). Two versions with identical content produce identical hashes —
``MessageVersionRepo.insert_version`` uses this for idempotency.

Hash inputs (canonical, ordered):
1. ``text`` (or empty string)
2. ``caption`` (or empty string)
3. ``message_kind`` (or 'text' default — legacy rows have NULL kind)
4. ``entities_json`` reserved for T1-08 — currently always ``None``

Output: hex SHA-256 of UTF-8 canonical JSON of the tuple.

T1-08 may extend the input tuple (e.g. add entities) and bump a version tag in the
hash payload. When that happens, all hashes change — backfilled v1 rows persist with
the legacy hash forever; new versions use the new hash. The DB stores whatever the
caller passes; the hash function defines the canonical recipe.
"""

from __future__ import annotations

import hashlib
import json


def compute_content_hash(
    text: str | None,
    caption: str | None,
    message_kind: str | None,
    entities_json: dict | list | None = None,
) -> str:
    """Return hex SHA-256 of a canonical content tuple.

    ``entities_json`` is accepted for forward-compatibility with T1-08 but is currently
    serialized into the canonical form alongside the other fields. If the same tuple is
    passed twice (regardless of dict key order in entities), the same hash is produced.
    """
    payload = json.dumps(
        [
            text or "",
            caption or "",
            message_kind or "text",
            entities_json,  # may be None — JSON-serializable as null
        ],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
