"""
Archive loader, validator, and inspector.
"""

import json
from pathlib import Path

from property_archiver.core.exceptions import CorruptedArchiveError, StorageError
from property_archiver.core.hasher import calculate_file_sha256
from property_archiver.models.archive import ArchiveManifest, ArchiveMetadata
from property_archiver.models.listing import ListingRecord


class ArchiveReader:
    """Reads and validates existing listing archives."""

    @staticmethod
    def load_listing(archive_path: Path | str) -> ListingRecord:
        """Load and parse listing.json from an archive directory."""
        path = Path(archive_path)
        listing_file = path / "listing.json"
        if not listing_file.exists():
            raise StorageError(f"Missing listing.json in archive directory: {path}")

        try:
            with open(listing_file, "r", encoding="utf-8") as f:
                return ListingRecord.model_validate_json(f.read())
        except Exception as e:
            raise StorageError(f"Failed to parse listing.json in {path}: {e}") from e

    @staticmethod
    def load_metadata(archive_path: Path | str) -> ArchiveMetadata:
        """Load and parse metadata.json from an archive directory."""
        path = Path(archive_path)
        meta_file = path / "metadata.json"
        if not meta_file.exists():
            raise StorageError(f"Missing metadata.json in archive directory: {path}")

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                return ArchiveMetadata.model_validate_json(f.read())
        except Exception as e:
            raise StorageError(f"Failed to parse metadata.json in {path}: {e}") from e

    @staticmethod
    def load_manifest(archive_path: Path | str) -> ArchiveManifest:
        """Load and parse checksums.json from an archive directory."""
        path = Path(archive_path)
        manifest_file = path / "checksums.json"
        if not manifest_file.exists():
            raise StorageError(f"Missing checksums.json in archive directory: {path}")

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                return ArchiveManifest.model_validate_json(f.read())
        except Exception as e:
            raise StorageError(f"Failed to parse checksums.json in {path}: {e}") from e

    @staticmethod
    def validate_integrity(archive_path: Path | str) -> tuple[bool, list[str]]:
        """
        Validate all files in the archive against their recorded SHA-256 checksums.
        Returns (is_valid, list_of_errors).
        """
        path = Path(archive_path)
        try:
            manifest = ArchiveReader.load_manifest(path)
        except Exception as exc:
            return False, [f"Manifest error: {exc}"]

        errors: list[str] = []
        for rel_file, expected_hash in manifest.files.items():
            target_file = path / rel_file
            if not target_file.exists():
                errors.append(f"Missing file: {rel_file}")
                continue

            actual_hash = calculate_file_sha256(target_file)
            if actual_hash.lower() != expected_hash.lower():
                errors.append(
                    f"Checksum mismatch for {rel_file}: expected {expected_hash}, got {actual_hash}"
                )

        return (len(errors) == 0), errors
