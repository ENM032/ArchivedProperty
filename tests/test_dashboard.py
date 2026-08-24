"""
Tests for Unified Dashboard HTTP server, REST endpoints, static assets, and CRUD operations.
"""

import json
import urllib.request
from pathlib import Path
import pytest

from property_archiver.dashboard.server import DashboardServer
from property_archiver.storage.writer import ArchiveWriter
from property_archiver.models.listing import ListingRecord
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.property_details import LocationInfo, PriceInfo


@pytest.fixture(scope="module")
def running_server(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("dash_test_archive")
    writer = ArchiveWriter()
    
    # Create sample listing for API tests
    rec = ListingRecord(
        listing_id="T_API_TEST_1",
        canonical_url="https://test.com/listing",
        title="API Test House in Rivonia",
        price=PriceInfo(amount=4500000.0, formatted_display="R 4 500 000"),
        location=LocationInfo(province="Gauteng", region="Sandton", suburb="Rivonia"),
        listing_status="active"
    )
    meta = ArchiveMetadata(
        schema_version="1.0.0",
        listing_id="T_API_TEST_1",
        source_url="https://test.com/listing",
        archiver_version="1.0.0",
        fetch_mode="test",
        http_status=200,
        response_headers={},
        fetch_duration_sec=0.1,
    )
    writer.write_archive(rec, "<html>test</html>", meta, output_base_dir=tmp_dir)

    server = DashboardServer(host="127.0.0.1", port=8002, archive_dir=tmp_dir)
    thread = server.start_background()
    yield "http://127.0.0.1:8002", tmp_dir
    server.server.shutdown()


def test_dashboard_root_html(running_server):
    url, _ = running_server
    req = urllib.request.Request(f"{url}/")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        html = res.read().decode("utf-8")
        assert "<title>Property Archiver - Unified Dashboard</title>" in html
        assert "app.js" in html


def test_api_list_listings(running_server):
    url, _ = running_server
    req = urllib.request.Request(f"{url}/api/listings")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode("utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 1
        ids = [item["listing_id"] for item in data]
        assert "T_API_TEST_1" in ids


def test_api_update_listing(running_server):
    url, _ = running_server
    payload = json.dumps({
        "listing_status": "under_offer",
        "user_notes": "API Note Test",
        "user_tags": ["API Tag"],
        "user_rating": 4
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{url}/api/listings/T_API_TEST_1/edit",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode("utf-8"))
        assert data["success"] is True
        assert data["listing"]["listing_status"] == "under_offer"
        assert data["listing"]["user_notes"] == "API Note Test"
        assert data["listing"]["user_rating"] == 4


def test_api_delete_listing(running_server):
    url, _ = running_server
    req = urllib.request.Request(f"{url}/api/listings/T_API_TEST_1", method="DELETE")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode("utf-8"))
        assert data["success"] is True
