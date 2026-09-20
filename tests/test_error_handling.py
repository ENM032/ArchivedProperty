"""
Comprehensive error handling & fault-tolerance tests for Property Archiver.
"""

from http import HTTPStatus
import json
from pathlib import Path
from click.testing import CliRunner
import pytest

from property_archiver.cli import main
from property_archiver.core.exceptions import (
    CorruptedArchiveError,
    FetchError,
    HTTPStatusError,
    NetworkTimeoutError,
    PropertyArchiverError,
    SecurityError,
    StorageError,
)
from property_archiver.dashboard.routes.listings import handle_get_listing
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.models.property_details import LocationInfo, PriceInfo
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter


def test_exception_context():
    err = PropertyArchiverError("Something went wrong", context={"file": "listing.json", "line": 42})
    assert err.message == "Something went wrong"
    assert err.context["line"] == 42


def test_corrupted_listing_json_raises_corrupted_archive_error(tmp_path: Path):
    corrupt_dir = tmp_path / "listings" / "gauteng" / "sandton" / "rivonia" / "T999999"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "listing.json").write_text("{ this is malformed json !!!", encoding="utf-8")

    with pytest.raises(CorruptedArchiveError) as exc_info:
        ArchiveReader.load_listing(corrupt_dir)

    assert "Corrupt or malformed JSON" in str(exc_info.value)
    assert exc_info.value.context.get("line") is not None


def test_missing_listing_json_raises_storage_error(tmp_path: Path):
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    with pytest.raises(StorageError) as exc_info:
        ArchiveReader.load_listing(empty_dir)

    assert "not found in archive" in str(exc_info.value)


def test_corrupted_metadata_json_raises_corrupted_archive_error(tmp_path: Path):
    listing_dir = tmp_path / "listing_dir"
    listing_dir.mkdir()
    (listing_dir / "metadata.json").write_text("not json at all", encoding="utf-8")

    with pytest.raises(CorruptedArchiveError) as exc_info:
        ArchiveReader.load_metadata(listing_dir)

    assert "Corrupt metadata.json" in str(exc_info.value)


def test_validate_checksums_detects_tampered_files(tmp_path: Path):
    writer = ArchiveWriter()
    rec = ListingRecord(
        listing_id="T123456",
        canonical_url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/T123456",
        title="Test House",
        price=PriceInfo(amount=1000000.0),
        location=LocationInfo(province="Gauteng", region="Sandton", suburb="Rivonia"),
    )
    meta = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T123456",
        source_url=rec.canonical_url,
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )
    out_dir = writer.write_archive(rec, "<html>test</html>", meta, output_base_dir=tmp_path)

    # Verify initially valid
    is_valid, errors = ArchiveReader.validate_checksums(out_dir)
    assert is_valid is True
    assert len(errors) == 0

    # Tamper with raw.html
    (out_dir / "raw.html").write_text("<html>tampered content</html>", encoding="utf-8")

    is_valid_after, errors_after = ArchiveReader.validate_checksums(out_dir)
    assert is_valid_after is False
    assert any("raw.html" in e for e in errors_after)


def test_staging_cleanup_on_write_failure(tmp_path: Path, monkeypatch):
    writer = ArchiveWriter()
    rec = ListingRecord(
        listing_id="T888888",
        canonical_url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/T888888",
        title="Fail House",
        price=PriceInfo(amount=2000000.0),
        location=LocationInfo(province="Gauteng", region="Sandton", suburb="Rivonia"),
    )
    meta = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T888888",
        source_url=rec.canonical_url,
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )

    # Force failure in _commit_directory_atomic
    def _mock_commit_fail(*args, **kwargs):
        raise OSError("Simulated disk write failure")

    monkeypatch.setattr(writer, "_commit_directory_atomic", _mock_commit_fail)

    with pytest.raises(StorageError):
        writer.write_archive(rec, "<html>fail</html>", meta, output_base_dir=tmp_path)

    # Verify no dangling .staging directories left behind in listings/
    listings_dir = tmp_path / "listings"
    if listings_dir.exists():
        stubs = [d.name for d in listings_dir.iterdir() if d.name.startswith(".staging_")]
        assert len(stubs) == 0


def test_handle_get_listing_not_found(tmp_path: Path):
    data, status = handle_get_listing(tmp_path, "NON_EXISTENT_ID")
    assert status == HTTPStatus.NOT_FOUND
    assert data["code"] == "LISTING_NOT_FOUND"
    assert "not found" in data["error"].lower()
