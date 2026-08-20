"""
Atomic archive writer. Writes raw HTML, normalized JSON, metadata, images, and checksums manifest.
"""

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from property_archiver import __version__
from property_archiver.config import ArchiverSettings, settings
from property_archiver.core.exceptions import StorageError
from property_archiver.core.hasher import calculate_file_sha256
from property_archiver.core.security import safe_join_path, sanitize_filename
from property_archiver.models.archive import ArchiveManifest, ArchiveMetadata
from property_archiver.models.listing import ListingRecord

logger = logging.getLogger(__name__)


class ArchiveWriter:
    """Writes listing data and assets atomically to the filesystem."""

    def __init__(self, config: ArchiverSettings | None = None):
        self.config = config or settings

    def create_staging_dir(self, listing_id: str, output_base_dir: Path | str | None = None) -> tuple[Path, Path]:
        """
        Create a staging directory and images subfolder for downloading assets before committing.
        Returns (staging_dir, images_dir).
        """
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
        Finalize, hash, and atomically commit the staging directory into the permanent archive directory.
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

            # 3. Calculate checksums manifest for all files in staging directory (including images)
            manifest = ArchiveManifest(
                schema_version="1.0.0",
                listing_id=listing.listing_id,
                archived_at=datetime.now(timezone.utc),
                archiver_version=__version__,
            )

            total_size = 0
            for root, _, files in os.walk(staging_dir):
                for filename in files:
                    if filename in ("checksums.json", "metadata.json"):
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

            # Add metadata.json to manifest
            manifest.files["metadata.json"] = calculate_file_sha256(metadata_path)

            # 5. Write checksums.json
            checksums_path = staging_dir / "checksums.json"
            with open(checksums_path, "w", encoding="utf-8") as f:
                f.write(manifest.model_dump_json(indent=2))

            # Atomic swap: remove existing target dir if present, then rename staging_dir
            if target_dir.exists():
                shutil.rmtree(target_dir)

            staging_dir.rename(target_dir)
            logger.info("Successfully committed archive to %s", target_dir)
            return target_dir

        except Exception as exc:
            if staging_dir.exists():
                shutil.rmtree(staging_dir, ignore_errors=True)
            raise StorageError(f"Failed to commit archive for {listing.listing_id}: {exc}") from exc

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
