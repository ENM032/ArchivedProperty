"""
Route handlers for comparing two listing snapshots or properties.
"""

from http import HTTPStatus
from pathlib import Path
from typing import Any

from property_archiver.core.change_detector import ChangeDetector
from property_archiver.storage.reader import ArchiveReader


def handle_compare(archive_dir: Path, id_a: str, id_b: str) -> tuple[dict[str, Any], HTTPStatus]:
    """Compare two archived properties and return a structured diff."""
    try:
        dir_a = ArchiveReader.find_listing_dir(archive_dir, id_a)
        dir_b = ArchiveReader.find_listing_dir(archive_dir, id_b)
        if not dir_a or not dir_b:
            return {"error": "One or both listings not found"}, HTTPStatus.NOT_FOUND

        diff = ChangeDetector.compare_archives(dir_a, dir_b)
        return {
            "listing_id": diff.listing_id,
            "is_identical": diff.is_identical,
            "price_changed": diff.price_changed,
            "old_price": diff.old_price,
            "new_price": diff.new_price,
            "price_diff": diff.price_diff,
            "status_changed": diff.status_changed,
            "old_status": diff.old_status,
            "new_status": diff.new_status,
            "badges_added": diff.badges_added,
            "badges_removed": diff.badges_removed,
            "spec_changes": diff.spec_changes,
            "added_features": diff.added_features,
            "removed_features": diff.removed_features,
        }, HTTPStatus.OK
    except Exception as exc:
        return {"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR
