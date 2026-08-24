"""
Atomic archive writer supporting flat and hierarchical (Province/Area/Suburb) filesystem layouts,
Windows-safe directory swaps, historical snapshot ledgers, and delete/update operations.
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from property_archiver import __version__
from property_archiver.config import ArchiverSettings, settings
from property_archiver.core.change_detector import ChangeDetector
from property_archiver.core.exceptions import StorageError
from property_archiver.core.hasher import calculate_file_sha256
from property_archiver.core.hierarchy import GeoHierarchyBuilder
from property_archiver.core.security import safe_join_path, sanitize_filename
from property_archiver.models.archive import ArchiveManifest, ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.storage.reader import ArchiveReader

logger = logging.getLogger(__name__)


class ArchiveWriter:
    """Writes, updates, and deletes listing data, assets, and historical snapshots atomically on disk."""

    def __init__(self, config: ArchiverSettings | None = None):
        self.config = config or settings

    def create_staging_dir(self, listing_id: str, output_base_dir: Path | str | None = None) -> tuple[Path, Path]:
        """Create a staging directory and images subfolder for safe downloads."""
        base_dir = Path(output_base_dir or self.config.archive_dir).resolve()
        safe_lid = sanitize_filename(listing_id or "listing")
        timestamp = int(datetime.now(timezone.utc).timestamp())
        staging_dir = safe_join_path(base_dir, "listings", f".staging_{safe_lid}_{timestamp}")
        images_dir = staging_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return staging_dir, images_dir

    
    def write_archive(
        self,
        listing: ListingRecord,
        raw_html: bytes | str,
        metadata: ArchiveMetadata,
        output_base_dir: Path | str | None = None
    ) -> Path:
        """Convenience method creating staging and committing archive in one call."""
        staging_dir, _ = self.create_staging_dir(listing.listing_id, output_base_dir)
        return self.commit_archive(staging_dir, listing, raw_html, metadata, output_base_dir)

    def commit_archive(
        self,
        staging_dir: Path,
        listing: ListingRecord,
        raw_html: bytes | str,
        metadata: ArchiveMetadata,
        output_base_dir: Path | str | None = None
    ) -> Path:
        """
        Finalize, hash, and atomically commit the staging directory into the permanent archive.
        Respects flat vs hierarchical layout settings.
        """
        base_dir = Path(output_base_dir or self.config.archive_dir).resolve()
        safe_lid = sanitize_filename(listing.listing_id or "listing")

        # Determine target path based on layout configuration
        if getattr(self.config, "archive_layout", "hierarchical") == "hierarchical":
            rel_path = GeoHierarchyBuilder.get_hierarchical_relpath(listing)
            target_dir = safe_join_path(base_dir, "listings", rel_path)
        else:
            target_dir = safe_join_path(base_dir, "listings", safe_lid)

        target_dir.parent.mkdir(parents=True, exist_ok=True)

        # Write raw.html
        raw_html_bytes = raw_html.encode("utf-8") if isinstance(raw_html, str) else raw_html
        raw_path = staging_dir / "raw.html"
        with open(raw_path, "wb") as f:
            f.write(raw_html_bytes)

        # Write listing.json
        listing_json_path = staging_dir / "listing.json"
        with open(listing_json_path, "w", encoding="utf-8") as f:
            f.write(listing.model_dump_json(indent=2))

        # Write metadata.json
        meta_path = staging_dir / "metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(metadata.model_dump_json(indent=2))

        # Build checksums.json
        checksums: dict[str, str] = {
            "listing.json": calculate_file_sha256(listing_json_path),
            "raw.html": calculate_file_sha256(raw_path),
            "metadata.json": calculate_file_sha256(meta_path),
        }

        images_dir = staging_dir / "images"
        if images_dir.exists():
            for img_file in sorted(images_dir.iterdir()):
                if img_file.is_file():
                    checksums[f"images/{img_file.name}"] = calculate_file_sha256(img_file)

        manifest = ArchiveManifest(
            schema_version="1.0.0",
            archiver_version=__version__,
            listing_id=listing.listing_id,
            total_files=len(checksums),
            files=checksums,
        )
        manifest_path = staging_dir / "checksums.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        # Maintain historical diffs if updating an existing archive
        history_file = target_dir / "history.json"
        history_records = []
        if target_dir.exists() and (target_dir / "listing.json").exists():
            try:
                old_listing = ArchiveReader.load_listing(target_dir)
                if history_file.exists():
                    history_records = json.loads(history_file.read_text(encoding="utf-8"))

                diff = ChangeDetector.compare_records(old_listing, listing)
                if not diff.is_identical:
                    history_records.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "event": "scraped_update",
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
                    })
            except Exception as exc:
                logger.warning("Failed computing change history for %s: %s", listing.listing_id, exc)

        if history_records:
            staging_history = staging_dir / "history.json"
            staging_history.write_text(json.dumps(history_records, indent=2), encoding="utf-8")

        # Atomic directory swap
        self._safe_atomic_replace(staging_dir, target_dir)
        logger.info("Successfully committed archive to %s", target_dir)
        return target_dir

    @staticmethod
    def delete_archive(archive_dir: Path | str, listing_id: str) -> bool:
        """
        Delete an archived listing directory completely and clean up any empty parent directories.
        """
        base_dir = Path(archive_dir).resolve()
        listing_dir = ArchiveReader.find_listing_dir(base_dir, listing_id)
        if not listing_dir or not listing_dir.exists():
            return False

        try:
            shutil.rmtree(listing_dir)
            logger.info("Deleted archive directory: %s", listing_dir)

            # Clean up empty parent directories (e.g. suburb -> area -> province)
            parent = listing_dir.parent
            listings_root = (base_dir / "listings").resolve()
            while parent != listings_root and parent.is_relative_to(listings_root):
                try:
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                        logger.debug("Cleaned up empty directory: %s", parent)
                        parent = parent.parent
                    else:
                        break
                except OSError:
                    break

            return True
        except Exception as exc:
            logger.error("Failed deleting archive %s: %s", listing_id, exc)
            raise StorageError(f"Failed deleting archive {listing_id}: {exc}") from exc

    @staticmethod
    def update_listing(archive_dir: Path | str, listing_id: str, updates: dict[str, Any]) -> ListingRecord:
        """
        Update user annotations, status, or details in an existing archive and record a history event.
        """
        base_dir = Path(archive_dir).resolve()
        listing_dir = ArchiveReader.find_listing_dir(base_dir, listing_id)
        if not listing_dir or not listing_dir.exists():
            raise StorageError(f"Listing {listing_id} not found in archive")

        record = ArchiveReader.load_listing(listing_dir)
        old_status = record.listing_status
        old_notes = record.user_notes
        old_rating = record.user_rating

        # Apply allowed fields
        if "listing_status" in updates:
            record.listing_status = str(updates["listing_status"]).lower()
            if record.listing_status == "under_offer":
                record.is_under_offer = True
                record.is_sold = False
            elif record.listing_status == "sold":
                record.is_sold = True
                record.is_under_offer = False
            elif record.listing_status == "active":
                record.is_sold = False
                record.is_under_offer = False

        if "user_notes" in updates:
            record.user_notes = updates["user_notes"]

        if "user_tags" in updates:
            tags = updates["user_tags"]
            if isinstance(tags, str):
                record.user_tags = [t.strip() for t in tags.split(",") if t.strip()]
            elif isinstance(tags, list):
                record.user_tags = [str(t).strip() for t in tags if str(t).strip()]

        if "user_rating" in updates:
            rating_val = updates["user_rating"]
            record.user_rating = int(rating_val) if rating_val is not None else None

        # Write updated listing.json
        listing_json_path = listing_dir / "listing.json"
        with open(listing_json_path, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))

        # Append manual edit to history.json
        history_file = listing_dir / "history.json"
        history_records = []
        if history_file.exists():
            try:
                history_records = json.loads(history_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        history_records.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "manual_edit",
            "updated_fields": list(updates.keys()),
            "status_changed": (old_status != record.listing_status),
            "old_status": old_status,
            "new_status": record.listing_status,
        })
        history_file.write_text(json.dumps(history_records, indent=2), encoding="utf-8")

        # Update checksums.json
        manifest_file = listing_dir / "checksums.json"
        if manifest_file.exists():
            try:
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest_data["files"]["listing.json"] = calculate_file_sha256(listing_json_path)
                manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
            except Exception:
                pass

        logger.info("Successfully updated listing %s", listing_id)
        return record

    def _safe_atomic_replace(self, staging_dir: Path, target_dir: Path):
        """Perform a robust atomic directory swap with Windows lock retry backoff."""
        if not target_dir.exists():
            staging_dir.rename(target_dir)
            return

        backup_dir = target_dir.parent / f".backup_{target_dir.name}_{int(time.time())}"
        target_dir.rename(backup_dir)

        max_retries = 5
        for attempt in range(max_retries):
            try:
                staging_dir.rename(target_dir)
                break
            except OSError as exc:
                if attempt == max_retries - 1:
                    backup_dir.rename(target_dir)
                    raise StorageError(f"Atomic swap failed for {target_dir}: {exc}") from exc
                time.sleep(0.1 * (2 ** attempt))

        shutil.rmtree(backup_dir, ignore_errors=True)
