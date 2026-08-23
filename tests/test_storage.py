"""
Tests for ArchiveWriter (flat & hierarchical), ArchiveReader (recursive discovery), and integrity validation.
"""

from pathlib import Path
import pytest

from property_archiver.config import ArchiverSettings
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.models.property_details import LocationInfo, PriceInfo
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter


def test_write_and_read_hierarchical_archive(tmp_path: Path):
    cfg = ArchiverSettings(archive_dir=tmp_path, archive_layout="hierarchical")
    writer = ArchiveWriter(config=cfg)

    listing = ListingRecord(
        listing_id="T_TEST_100",
        canonical_url="https://test.com/listing",
        title="Test Hierarchical House",
        price=PriceInfo(amount=3500000.0, formatted_display="R 3 500 000"),
        location=LocationInfo(
            province="Gauteng",
            city="Johannesburg",
            region="Sandton",
            suburb="Rivonia"
        ),
        listing_status="active"
    )

    metadata = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T_TEST_100",
        source_url="https://test.com/listing",
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )

    archive_path = writer.write_archive(
        listing=listing,
        raw_html="<html><body>Hello</body></html>",
        metadata=metadata,
        output_base_dir=tmp_path
    )

    # Verify hierarchical path: listings/gauteng/sandton/rivonia/T_TEST_100
    rel_path = archive_path.relative_to(tmp_path)
    assert str(rel_path).replace("\\", "/") == "listings/gauteng/sandton/rivonia/T_TEST_100"

    # Verify recursive discovery finds it
    dirs = ArchiveReader.find_all_listing_dirs(tmp_path)
    assert len(dirs) == 1
    assert dirs[0] == archive_path

    # Verify find_listing_dir works by ID
    found_dir = ArchiveReader.find_listing_dir(tmp_path, "T_TEST_100")
    assert found_dir == archive_path

    # Verify loaded data
    loaded_listing = ArchiveReader.load_listing(archive_path)
    assert loaded_listing.listing_id == "T_TEST_100"
    assert loaded_listing.title == "Test Hierarchical House"

    # Verify integrity
    is_valid, errors = ArchiveReader.validate_integrity(archive_path)
    assert is_valid is True
    assert len(errors) == 0
