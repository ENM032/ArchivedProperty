"""
Tests for ArchiveWriter (flat, hierarchical, update, delete), ArchiveReader (recursive discovery), and integrity validation.
"""

from pathlib import Path
import pytest

from property_archiver.config import ArchiverSettings
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.models.property_details import LocationInfo, PriceInfo
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter


def test_write_read_update_and_delete_archive(tmp_path: Path):
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

    # 1. Verify hierarchical path: listings/gauteng/sandton/rivonia/T_TEST_100
    rel_path = archive_path.relative_to(tmp_path)
    assert str(rel_path).replace("\\", "/") == "listings/gauteng/sandton/rivonia/T_TEST_100"

    # 2. Verify recursive discovery finds it
    dirs = ArchiveReader.find_all_listing_dirs(tmp_path)
    assert len(dirs) == 1
    assert dirs[0] == archive_path

    # 3. Test update_listing (Edit & Annotations)
    updates = {
        "listing_status": "under_offer",
        "user_notes": "Great investment prospect",
        "user_tags": ["Prime", "High ROI"],
        "user_rating": 5
    }
    updated = ArchiveWriter.update_listing(tmp_path, "T_TEST_100", updates)
    assert updated.listing_status == "under_offer"
    assert updated.is_under_offer is True
    assert updated.user_notes == "Great investment prospect"
    assert updated.user_tags == ["Prime", "High ROI"]
    assert updated.user_rating == 5

    # Verify history.json recorded the edit
    history_file = archive_path / "history.json"
    assert history_file.exists()
    import json
    history = json.loads(history_file.read_text(encoding="utf-8"))
    assert len(history) >= 1
    assert history[-1]["event"] == "manual_edit"

    # 4. Test delete_archive (Delete feature)
    assert ArchiveWriter.delete_archive(tmp_path, "T_TEST_100") is True
    assert not archive_path.exists()
    assert len(ArchiveReader.find_all_listing_dirs(tmp_path)) == 0
