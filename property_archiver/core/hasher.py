"""
Hashing and fingerprinting utilities for content integrity and change detection.
"""

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


def calculate_sha256(data: bytes) -> str:
    """Compute hex SHA-256 digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def calculate_file_sha256(filepath: Path | str, chunk_size: int = 65536) -> str:
    """Compute hex SHA-256 digest of a file in streaming chunks."""
    h = hashlib.sha256()
    path = Path(filepath)
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def _json_default_serializer(obj: Any) -> Any:
    """Handle dates, datetimes, and custom objects during JSON serialization."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)


def canonical_json_dumps(data: Any) -> str:
    """Serialize data into canonical JSON with sorted keys for consistent hashing."""
    return json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        default=_json_default_serializer,
    )


def calculate_content_fingerprint(data: dict[str, Any], excluded_keys: set[str] | None = None) -> str:
    """
    Calculate a stable fingerprint for a listing dictionary.
    Excludes non-semantic fields like timestamps, run IDs, or metadata headers.
    """
    default_excludes = {
        "extracted_at",
        "archived_at",
        "fingerprint",
        "crawl_timestamp",
        "fetch_duration_sec",
    }
    excludes = default_excludes | (excluded_keys or set())

    filtered = {k: v for k, v in data.items() if k not in excludes}
    canonical_json = canonical_json_dumps(filtered)
    return calculate_sha256(canonical_json.encode("utf-8"))
