"""
Archive reader and cryptographic validator with recursive hierarchical directory discovery
and resilient, descriptive error handling.
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

        try:
            for root, dirs, files in os.walk(listings_root):
                # Skip internal staging, snapshots, and image directories
                dirs[:] = [d for d in dirs if not d.startswith(".staging_") and d not in ("snapshots", "images")]
                if "listing.json" in files:
                    results.append(Path(root))
        except OSError as os_err:
            logger.error("Filesystem traversal error in %s: %s", listings_root, os_err)

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
            raise StorageError(f"Listing definition not found in archive: {path}", context={"path": str(path)})

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ListingRecord.model_validate(data)
        except json.JSONDecodeError as jde:
            raise CorruptedArchiveError(
                f"Corrupt or malformed JSON in {path} (line {jde.lineno}, col {jde.colno}): {jde.msg}",
                context={"path": str(path), "line": jde.lineno, "column": jde.colno}
            )
        except Exception as exc:
            raise StorageError(f"Failed deserializing listing from {path}: {exc}", context={"path": str(path)})

    @staticmethod
    def load_metadata(archive_dir: Path | str) -> ArchiveMetadata:
        """Load and deserialize metadata.json."""
        path = Path(archive_dir) / "metadata.json"
        if not path.exists():
            raise StorageError(f"Metadata definition not found in archive: {path}", context={"path": str(path)})

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ArchiveMetadata.model_validate(data)
        except json.JSONDecodeError as jde:
            raise CorruptedArchiveError(
                f"Corrupt metadata.json in {path}: {jde.msg}",
                context={"path": str(path)}
            )
        except Exception as exc:
            raise StorageError(f"Failed deserializing metadata from {path}: {exc}", context={"path": str(path)})

    @staticmethod
    def load_manifest(archive_dir: Path | str) -> ArchiveManifest | None:
        """Load checksums.json manifest if present."""
        path = Path(archive_dir) / "checksums.json"
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ArchiveManifest.model_validate(data)
        except Exception as exc:
            logger.warning("Manifest reading failed for %s: %s", path, exc)
            return None

    @staticmethod
    def validate_checksums(archive_dir: Path | str) -> tuple[bool, list[str]]:
        """Cryptographically verify all files against checksums.json."""
        archive_path = Path(archive_dir).resolve()
        manifest = ArchiveReader.load_manifest(archive_path)
        if not manifest:
            return False, ["Missing checksums.json manifest"]

        errors: list[str] = []
        for rel_file, expected_hash in manifest.files.items():
            full_path = archive_path / rel_file
            if not full_path.exists():
                errors.append(f"Missing file: {rel_file}")
                continue

            try:
                actual_hash = calculate_file_sha256(full_path)
                if actual_hash != expected_hash:
                    errors.append(f"Hash mismatch for {rel_file}: expected {expected_hash}, got {actual_hash}")
            except Exception as exc:
                errors.append(f"Error calculating hash for {rel_file}: {exc}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_integrity(archive_dir: Path | str) -> tuple[bool, list[str]]:
        """Alias for validate_checksums."""
        return ArchiveReader.validate_checksums(archive_dir)
