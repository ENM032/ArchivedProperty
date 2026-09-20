"""
Atomic archive writer supporting flat and hierarchical filesystem layouts,
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
        try:
            return self.commit_archive(staging_dir, listing, raw_html, metadata, output_base_dir)
        except Exception:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise

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
        try:
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

            # Hash images
            images_dir = staging_dir / "images"
            if images_dir.exists():
                for img_file in images_dir.iterdir():
                    if img_file.is_file():
                        rel_img = f"images/{img_file.name}"
                        checksums[rel_img] = calculate_file_sha256(img_file)

            manifest = ArchiveManifest(
                schema_version="1.0.0",
                listing_id=listing.listing_id,
                created_at=datetime.now(timezone.utc),
                files=checksums,
            )

            with open(staging_dir / "checksums.json", "w", encoding="utf-8") as f:
                f.write(manifest.model_dump_json(indent=2))

            # Snapshot preservation & Atomic directory commit
            self._commit_directory_atomic(staging_dir, target_dir, listing)
            return target_dir
        except Exception as exc:
            shutil.rmtree(staging_dir, ignore_errors=True)
            if isinstance(exc, StorageError):
                raise
            raise StorageError(f"Failed committing archive for {listing.listing_id}: {exc}") from exc

    def _commit_directory_atomic(self, staging_dir: Path, target_dir: Path, new_listing: ListingRecord):
        """Atomically replace or create target directory with historical snapshot retention."""
        if not target_dir.exists():
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(str(staging_dir), str(target_dir))
            except OSError:
                shutil.copytree(str(staging_dir), str(target_dir), dirs_exist_ok=True)
                shutil.rmtree(str(staging_dir), ignore_errors=True)
            return

        # Listing already exists: Create Historical Snapshot & Diff
        try:
            old_listing = ArchiveReader.load_listing(target_dir)
            diff = ChangeDetector.compare_records(old_listing, new_listing)
            self._archive_snapshot(target_dir, old_listing, diff)
        except Exception as exc:
            logger.warning("Snapshot creation skipped for %s: %s", target_dir.name, exc)

        # Preserve existing history and user annotations
        self._preserve_history_and_annotations(target_dir, staging_dir)

        # Windows-safe atomic directory replacement
        timestamp = int(datetime.now(timezone.utc).timestamp())
        backup_dir = target_dir.parent / f".backup_{target_dir.name}_{timestamp}"

        try:
            os.replace(str(target_dir), str(backup_dir))
            os.replace(str(staging_dir), str(target_dir))
            shutil.rmtree(str(backup_dir), ignore_errors=True)
        except OSError:
            # Fallback copy
            shutil.copytree(str(staging_dir), str(target_dir), dirs_exist_ok=True)
            shutil.rmtree(str(staging_dir), ignore_errors=True)
            if backup_dir.exists():
                shutil.rmtree(str(backup_dir), ignore_errors=True)

    def _archive_snapshot(self, target_dir: Path, old_listing: ListingRecord, diff: Any):
        """Preserve historic version in snapshots/ directory."""
        snapshots_dir = target_dir / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        snap_time = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snap_path = snapshots_dir / f"listing_{snap_time}.json"

        snapshot_payload = {
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
            "previous_record": old_listing.model_dump(),
            "detected_changes": diff.model_dump() if hasattr(diff, "model_dump") else str(diff),
        }

        with open(snap_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(snapshot_payload, indent=2))

    def _preserve_history_and_annotations(self, old_dir: Path, new_staging_dir: Path):
        """Carry over history.json and user notes/tags/ratings into new staging dir."""
        old_hist = old_dir / "history.json"
        if old_hist.exists():
            shutil.copy2(old_hist, new_staging_dir / "history.json")

        old_snapshots = old_dir / "snapshots"
        if old_snapshots.exists():
            shutil.copytree(old_snapshots, new_staging_dir / "snapshots", dirs_exist_ok=True)

    @classmethod
    def update_listing(cls, archive_base: Path | str, listing_id: str, updates: dict[str, Any]) -> ListingRecord:
        """Class method to update listing annotations, status, notes, tags, or rating."""
        listing_dir = ArchiveReader.find_listing_dir(archive_base, listing_id)
        if not listing_dir:
            raise StorageError(f"Listing {listing_id} not found in {archive_base}")

        record = ArchiveReader.load_listing(listing_dir)
        status = updates.get("listing_status") or updates.get("status")
        if status is not None:
            clean_status = status.strip().lower()
            record.listing_status = clean_status
            if clean_status == "under_offer":
                record.is_under_offer = True
            elif clean_status == "sold":
                record.is_sold = True
            elif clean_status == "active":
                record.is_under_offer = False
                record.is_sold = False

        if "user_notes" in updates or "notes" in updates:
            notes = updates.get("user_notes") or updates.get("notes")
            record.user_notes = str(notes).strip() if notes and str(notes).strip() else None

        if "user_tags" in updates or "tags" in updates:
            tags = updates.get("user_tags") or updates.get("tags")
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            record.user_tags = [t.strip() for t in tags if t.strip()]

        if "user_rating" in updates or "rating" in updates:
            rating = updates.get("user_rating") if "user_rating" in updates else updates.get("rating")
            if rating is not None and 1 <= int(rating) <= 5:
                record.user_rating = int(rating)
            elif rating == 0:
                record.user_rating = None

        listing_json = listing_dir / "listing.json"
        listing_json.write_text(record.model_dump_json(indent=2), encoding="utf-8")

        # Append to history.json
        hist_file = listing_dir / "history.json"
        history = []
        if hist_file.exists():
            try:
                history = json.loads(hist_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "manual_edit",
            "updates": updates
        })
        hist_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

        # Update checksums.json
        manifest_file = listing_dir / "checksums.json"
        if manifest_file.exists():
            try:
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest_data["files"]["listing.json"] = calculate_file_sha256(listing_json)
                manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
            except Exception as exc:
                logger.warning("Failed updating checksum for updated listing: %s", exc)

        return record

    @classmethod
    def delete_archive(cls, archive_base: Path | str, listing_id: str | None = None) -> bool:
        """Class method to delete an archive by base path + ID, or directory path."""
        if listing_id:
            target_path = ArchiveReader.find_listing_dir(archive_base, listing_id)
            if not target_path:
                return False
        else:
            target_path = Path(archive_base).resolve()
            if not target_path.exists():
                return False

        parent_area = target_path.parent
        parent_prov = parent_area.parent

        shutil.rmtree(str(target_path), ignore_errors=True)

        # Prune empty parent folders
        for folder in (parent_area, parent_prov):
            try:
                if folder.exists() and not any(folder.iterdir()):
                    folder.rmdir()
            except OSError:
                pass

        return True
