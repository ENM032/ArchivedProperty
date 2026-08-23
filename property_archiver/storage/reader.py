"""
Archive reader and cryptographic validator with recursive hierarchical directory discovery.
"""

import json
import logging
import os
from pathlib import Path

from property_archiver.core.exceptions import CorruptedArchiveError, StorageError
from property_archiver.core.hasher import calculate_file_sha256
from property_archiver.models.archive import ArchiveManifest, ArchiveMetadata
from property_archiver.models.listing import ListingRecord

logger = logging.getLogger(__name__)


class ArchiveReader:
    """Reads, parses, and cryptographically validates archived listings on disk."""

    @staticmethod
    def find_all_listing_dirs(archive_base: Path | str) -> list[Path]:
        """
        Recursively discover all directory paths containing a valid listing.json.
        Supports flat, hierarchical, and mixed layouts transparently.
        """
        base_dir = Path(archive_base).resolve()
        listings_root = base_dir / "listings" if (base_dir / "listings").exists() else base_dir
        results: list[Path] = []

        if not listings_root.exists():
            return results

        for root, dirs, files in os.walk(listings_root):
            # Skip internal staging and snapshots directories
            dirs[:] = [d for d in dirs if not d.startswith(".staging_") and d not in ("snapshots", "images")]
            if "listing.json" in files:
                results.append(Path(root))

        # Sort for consistent ordering
        results.sort(key=lambda p: p.name)
        return results

    @staticmethod
    def find_listing_dir(archive_base: Path | str, listing_id: str) -> Path | None:
        """Find the directory for a specific listing ID in flat or hierarchical layout."""
        clean_id = listing_id.strip().upper()
        for p in ArchiveReader.find_all_listing_dirs(archive_base):
            if p.name.upper() == clean_id:
                return p
        return None

    @staticmethod
    def load_listing(archive_dir: Path | str) -> ListingRecord:
        """Load and deserialize the normalized listing.json model."""
        path = Path(archive_dir) / "listing.json"
        if not path.exists():
            raise StorageError(f"Listing definition not found in archive: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ListingRecord.model_validate(data)
        except Exception as exc:
            raise CorruptedArchiveError(f"Corrupted or invalid listing.json at {path}: {exc}") from exc

    @staticmethod
    def load_metadata(archive_dir: Path | str) -> ArchiveMetadata:
        """Load crawl metadata from metadata.json."""
        path = Path(archive_dir) / "metadata.json"
        if not path.exists():
            raise StorageError(f"Metadata file not found in archive: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ArchiveMetadata.model_validate(data)
        except Exception as exc:
            raise CorruptedArchiveError(f"Corrupted metadata.json at {path}: {exc}") from exc

    @staticmethod
    def load_manifest(archive_dir: Path | str) -> ArchiveManifest:
        """Load SHA-256 checksum manifest."""
        path = Path(archive_dir) / "checksums.json"
        if not path.exists():
            raise StorageError(f"Checksum manifest not found in archive: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ArchiveManifest.model_validate(data)
        except Exception as exc:
            raise CorruptedArchiveError(f"Corrupted checksums.json at {path}: {exc}") from exc

    @staticmethod
    def validate_integrity(archive_dir: Path | str) -> tuple[bool, list[str]]:
        """Verify that every file listed in checksums.json matches its recorded SHA-256 digest."""
        archive_path = Path(archive_dir)
        errors: list[str] = []

        try:
            manifest = ArchiveReader.load_manifest(archive_path)
        except Exception as exc:
            return False, [f"Failed to load checksums.json: {exc}"]

        for rel_filepath, expected_sha in manifest.files.items():
            full_path = archive_path / rel_filepath
            if not full_path.exists():
                errors.append(f"Missing expected archive file: {rel_filepath}")
                continue

            actual_sha = calculate_file_sha256(full_path)
            if actual_sha != expected_sha:
                errors.append(
                    f"Integrity failure in {rel_filepath}: expected {expected_sha[:12]}..., got {actual_sha[:12]}..."
                )

        return (len(errors) == 0), errors
