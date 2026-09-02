"""
Unit & integration tests for SyncEngine and `ap sync` command.
"""

from pathlib import Path
from typing import Any
from click.testing import CliRunner
import pytest

from property_archiver.cli import main
from property_archiver.core.exceptions import HTTPStatusError
from property_archiver.core.fetcher import FetchResult
from property_archiver.core.sync import SyncEngine
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.models.property_details import LocationInfo, PriceInfo, PropertyFeatures
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter


class DummyMockFetcher:
    """Mock fetcher returning synthetic HTML responses for sync testing."""

    def __init__(self, responses: dict[str, Any]):
        self.responses = responses

    def fetch_url(self, url: str) -> FetchResult:
        if url in self.responses:
            resp = self.responses[url]
            if isinstance(resp, Exception):
                raise resp
            return resp
        return FetchResult(
            url=url,
            status_code=200,
            headers={},
            content=b"<html><body>Standard</body></html>",
            text="<html><body>Standard</body></html>",
            duration_sec=0.05,
        )


@pytest.fixture
def sync_archive(tmp_path: Path, sample_html_content: str) -> Path:
    """Create test listing archive in tmp_path."""
    writer = ArchiveWriter()
    rec = ListingRecord(
        listing_id="T4710876",
        canonical_url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876",
        title="4 Bedroom House in Rivonia",
        price=PriceInfo(amount=4999000.0, formatted_display="R 4 999 000"),
        location=LocationInfo(province="Gauteng", region="Sandton", suburb="Rivonia"),
        listing_status="active"
    )
    meta = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T4710876",
        source_url=rec.canonical_url,
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )
    writer.write_archive(rec, sample_html_content, meta, output_base_dir=tmp_path)
    return tmp_path


def _generate_reduced_html(html_str: str, new_price_formatted: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_str, "html.parser")
    for s in soup.find_all("script"):
        s.decompose()
    clean = str(soup)
    return clean.replace("\xa0999\xa0000", f"\xa0{new_price_formatted}").replace("4 999 000", f"4 {new_price_formatted}")


def test_sync_detects_price_drop(sync_archive: Path, sample_html_content: str):
    listing_dir = ArchiveReader.find_listing_dir(sync_archive, "T4710876")
    assert listing_dir is not None

    reduced_html = _generate_reduced_html(sample_html_content, "450\xa0000")
    
    mock_fetcher = DummyMockFetcher({
        "https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876": FetchResult(
            url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876",
            status_code=200,
            headers={},
            content=reduced_html.encode("utf-8"),
            text=reduced_html,
            duration_sec=0.05
        )
    })

    engine = SyncEngine()
    event = engine.sync_single(listing_dir, dry_run=False, no_images=True, fetcher=mock_fetcher)

    assert event.event_type == "price_drop"
    assert event.old_value == 4999000.0
    assert event.new_value == 4450000.0

    # Verify listing.json was updated
    updated_rec = ArchiveReader.load_listing(listing_dir)
    assert updated_rec.price.amount == 4450000.0

    # Verify history.json contains the price drop
    import json
    history = json.loads((listing_dir / "history.json").read_text(encoding="utf-8"))
    assert len(history) >= 1
    assert history[-1]["price_changed"] is True


def test_sync_detects_delisting_404(sync_archive: Path):
    listing_dir = ArchiveReader.find_listing_dir(sync_archive, "T4710876")
    assert listing_dir is not None

    mock_fetcher = DummyMockFetcher({
        "https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876": HTTPStatusError("404 Not Found", status_code=404)
    })

    engine = SyncEngine()
    event = engine.sync_single(listing_dir, dry_run=False, fetcher=mock_fetcher)

    assert event.event_type == "delisted"
    updated_rec = ArchiveReader.load_listing(listing_dir)
    assert updated_rec.listing_status == "delisted"


def test_sync_dry_run_safety(sync_archive: Path, sample_html_content: str):
    listing_dir = ArchiveReader.find_listing_dir(sync_archive, "T4710876")
    assert listing_dir is not None

    reduced_html = _generate_reduced_html(sample_html_content, "000\xa0000")
    mock_fetcher = DummyMockFetcher({
        "https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876": FetchResult(
            url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876",
            status_code=200,
            headers={},
            content=reduced_html.encode("utf-8"),
            text=reduced_html,
            duration_sec=0.05
        )
    })

    engine = SyncEngine()
    event = engine.sync_single(listing_dir, dry_run=True, no_images=True, fetcher=mock_fetcher)

    assert event.event_type == "price_drop"
    # In dry-run mode, disk file must remain at original 4999000
    unchanged_rec = ArchiveReader.load_listing(listing_dir)
    assert unchanged_rec.price.amount == 4999000.0


def test_sync_detects_status_transition(sync_archive: Path, sample_html_content: str):
    listing_dir = ArchiveReader.find_listing_dir(sync_archive, "T4710876")
    assert listing_dir is not None

    # Add under-offer badge in HTML
    offer_html = sample_html_content.replace(
        '<div class="listing-details__left-col">',
        '<div class="listing-details__left-col"><div class="badge-container"><span class="badge">Under Offer</span></div>'
    )
    
    mock_fetcher = DummyMockFetcher({
        "https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876": FetchResult(
            url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876",
            status_code=200,
            headers={},
            content=offer_html.encode("utf-8"),
            text=offer_html,
            duration_sec=0.05
        )
    })

    engine = SyncEngine()
    event = engine.sync_single(listing_dir, dry_run=False, no_images=True, fetcher=mock_fetcher)

    assert event.event_type == "status_transition"
    assert event.new_value == "under_offer"
    updated_rec = ArchiveReader.load_listing(listing_dir)
    assert updated_rec.is_under_offer is True


def test_sync_detects_soft_delisting(sync_archive: Path):
    listing_dir = ArchiveReader.find_listing_dir(sync_archive, "T4710876")
    assert listing_dir is not None

    soft_delist_html = "<html><body><h1>This property is no longer available</h1><p>The mandate has expired.</p></body></html>"
    mock_fetcher = DummyMockFetcher({
        "https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876": FetchResult(
            url="https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876",
            status_code=200,
            headers={},
            content=soft_delist_html.encode("utf-8"),
            text=soft_delist_html,
            duration_sec=0.05
        )
    })

    engine = SyncEngine()
    event = engine.sync_single(listing_dir, dry_run=False, fetcher=mock_fetcher)

    assert event.event_type == "delisted"
    updated_rec = ArchiveReader.load_listing(listing_dir)
    assert updated_rec.listing_status == "delisted"


def test_cli_sync_command(sync_archive: Path):
    runner = CliRunner()
    res = runner.invoke(main, ["sync", "--dry-run", "--suburb", "Rivonia", "--archive-dir", str(sync_archive)])
    assert res.exit_code == 0
    assert "Sync Summary" in res.output or "Total Scanned" in res.output
