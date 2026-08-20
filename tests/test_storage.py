"""
Tests for archive writer, reader, atomic filesystem updates, and manifest verification.
"""

from datetime import datetime
from pathlib import Path
import pytest

from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.models.property_details import PriceInfo
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter


def test_archive_writer_and_reader(tmp_path: Path):
    writer = ArchiveWriter()
    
    listing = ListingRecord(
        listing_id="T8888",
        canonical_url="https://www.privateproperty.co.za/for-sale/listing/T8888",
        title="Luxury House",
        price=PriceInfo(amount=3200000.0, formatted_display="R 3 200 000")
    )
    raw_html = "<html><body><h1>Luxury House</h1></body></html>"
    metadata = ArchiveMetadata(
        listing_id="T8888",
        source_url=listing.canonical_url,
        archiver_version="1.0.0",
        fetch_mode="file",
        http_status=200
    )

    archive_dir = writer.write_archive(
        listing=listing,
        raw_html=raw_html,
        metadata=metadata,
        output_base_dir=tmp_path
    )

    assert archive_dir.exists()
    assert (archive_dir / "raw.html").exists()
    assert (archive_dir / "listing.json").exists()
    assert (archive_dir / "metadata.json").exists()
    assert (archive_dir / "checksums.json").exists()

    # Read back and verify integrity
    loaded_listing = ArchiveReader.load_listing(archive_dir)
    assert loaded_listing.listing_id == "T8888"
    assert loaded_listing.price.amount == 3200000.0

    is_valid, errors = ArchiveReader.validate_integrity(archive_dir)
    assert is_valid is True
    assert len(errors) == 0

    # Test tampering detection
    with open(archive_dir / "raw.html", "w") as f:
        f.write("TAMPERED DATA")

    is_valid_tampered, tamper_errors = ArchiveReader.validate_integrity(archive_dir)
    assert is_valid_tampered is False
    assert any("Checksum mismatch" in e for e in tamper_errors)
