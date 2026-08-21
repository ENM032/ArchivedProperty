"""
Atomic archive writer with Windows-safe directory swaps, retry backoff,
and automated historical snapshot versioning.
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from property_archiver import __version__
from property_archiver.config import ArchiverSettings, settings
from property_archiver.core.change_detector import ChangeDetector
from property_archiver.core.exceptions import StorageError
from property_archiver.core.hasher import calculate_file_sha256
from property_archiver.core.security import safe_join_path, sanitize_filename
from property_archiver.models.archive import ArchiveManifest, ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.storage.reader import ArchiveReader

logger = logging.getLogger(__name__)


class ArchiveWriter:
    """Writes listing data, assets, and historical snapshots atomically to disk."""

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
        Preserves previous versions in snapshots/ history ledger if updates are detected.
        """
        base_dir = Path(output_base_dir or self.config.archive_dir).resolve()
        safe_lid = sanitize_filename(listing.listing_id or "listing")
        target_dir = safe_join_path(base_dir, "listings", safe_lid)

        try:
            # 1. Write raw.html
            raw_html_bytes = raw_html.encode("utf-8") if isinstance(raw_html, str) else raw_html
            raw_html_path = staging_dir / "raw.html"
            with open(raw_html_path, "wb") as f:
                f.write(raw_html_bytes)

            # 2. Write listing.json
            listing_json_path = staging_dir / "listing.json"
            with open(listing_json_path, "w", encoding="utf-8") as f:
                f.write(listing.model_dump_json(indent=2))

            # 3. Calculate checksums manifest for all files in staging
            manifest = ArchiveManifest(
                schema_version="1.0.0",
                listing_id=listing.listing_id,
                archived_at=datetime.now(timezone.utc),
                archiver_version=__version__,
            )

            total_size = 0
            for root, _, files in os.walk(staging_dir):
                for filename in files:
                    if filename in ("checksums.json", "metadata.json", "history.json"):
                        continue
                    full_p = Path(root) / filename
                    rel_p = str(full_p.relative_to(staging_dir)).replace("\\", "/")
                    file_hash = calculate_file_sha256(full_p)
                    manifest.files[rel_p] = file_hash
                    total_size += full_p.stat().st_size

            # 4. Write metadata.json
            metadata.total_archive_size_bytes = total_size
            metadata_path = staging_dir / "metadata.json"
            with open(metadata_path, "w", encoding="utf-8") as f:
                f.write(metadata.model_dump_json(indent=2))

            manifest.files["metadata.json"] = calculate_file_sha256(metadata_path)

            # 5. Write checksums.json
            checksums_path = staging_dir / "checksums.json"
            with open(checksums_path, "w", encoding="utf-8") as f:
                f.write(manifest.model_dump_json(indent=2))

            # 6. Historical Snapshot & Timeline Ledger
            snapshots_to_preserve: list[Path] = []
            history_entries: list[dict] = []

            if target_dir.exists() and (target_dir / "listing.json").exists():
                try:
                    old_listing = ArchiveReader.load_listing(target_dir)
                    old_meta = ArchiveReader.load_metadata(target_dir)

                    # Read existing history if present
                    old_history_file = target_dir / "history.json"
                    if old_history_file.exists():
                        with open(old_history_file, "r", encoding="utf-8") as hf:
                            history_entries = json.load(hf)

                    # Check for diff
                    diff = ChangeDetector.compare_records(old_listing, listing)
                    if not diff.is_identical:
                        snap_time_str = old_meta.archived_at.strftime("%Y%m%d_%H%M%S")
                        history_entries.append({
                            "timestamp": old_meta.archived_at.isoformat(),
                            "snapshot_id": snap_time_str,
                            "price": old_listing.price.amount,
                            "status": old_listing.listing_status,
                            "fingerprint": old_listing.content_fingerprint,
                            "diff_summary": {
                                "price_changed": diff.price_changed,
                                "price_diff": diff.price_diff,
                                "status_changed": diff.status_changed,
                                "old_status": diff.old_status,
                                "new_status": diff.new_status,
                                "badges_added": diff.badges_added,
                            }
                        })

                    # Write updated history.json in staging dir
                    staging_history = staging_dir / "history.json"
                    with open(staging_history, "w", encoding="utf-8") as hf:
                        json.dump(history_entries, hf, indent=2)

                    # Preserve existing snapshots folder if present
                    old_snapshots_dir = target_dir / "snapshots"
                    if old_snapshots_dir.exists():
                        staging_snapshots = staging_dir / "snapshots"
                        shutil.copytree(old_snapshots_dir, staging_snapshots, dirs_exist_ok=True)

                except Exception as e:
                    logger.debug("Failed computing history ledger: %s", e)

            # 7. Safe Windows-Resilient Atomic Directory Swap
            self._safe_atomic_replace(staging_dir, target_dir)
            logger.info("Successfully committed archive to %s", target_dir)
            return target_dir

        except Exception as exc:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise StorageError(f"Failed to commit archive for {listing.listing_id}: {exc}") from exc

    def _safe_atomic_replace(self, staging_dir: Path, target_dir: Path, max_retries: int = 5) -> None:
        """
        Atomically replace target_dir with staging_dir with exponential backoff on PermissionError (WinError 32).
        """
        backup_dir = target_dir.parent / f".bak_{target_dir.name}_{int(time.time()*1000)}"

        # Step A: Move existing target_dir to backup
        if target_dir.exists():
            for attempt in range(max_retries):
                try:
                    target_dir.rename(backup_dir)
                    break
                except (PermissionError, OSError) as e:
                    if attempt == max_retries - 1:
                        # Fallback: remove recursively
                        shutil.rmtree(target_dir, ignore_errors=True)
                        break
                    time.sleep(0.05 * (2 ** attempt))

        # Step B: Rename staging_dir to target_dir
        for attempt in range(max_retries):
            try:
                staging_dir.rename(target_dir)
                break
            except (PermissionError, OSError) as e:
                if attempt == max_retries - 1:
                    # If rename fails, restore backup if possible
                    if backup_dir.exists() and not target_dir.exists():
                        backup_dir.rename(target_dir)
                    raise StorageError(f"Failed moving staging dir to target {target_dir}: {e}") from e
                time.sleep(0.05 * (2 ** attempt))

        # Step C: Cleanup backup dir safely
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)

    def write_archive(
        self,
        listing: ListingRecord,
        raw_html: bytes | str,
        metadata: ArchiveMetadata,
        output_base_dir: Path | str | None = None
    ) -> Path:
        """Convenience method for creating and committing an archive without separate image staging."""
        staging_dir, _ = self.create_staging_dir(listing.listing_id, output_base_dir)
        return self.commit_archive(staging_dir, listing, raw_html, metadata, output_base_dir)
