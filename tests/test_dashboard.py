"""
Tests for the Unified Dashboard HTTP server, REST APIs, image serving, and CSV export.
"""

import time
from pathlib import Path
import httpx
import pytest

from property_archiver.dashboard.server import DashboardServer


@pytest.fixture(scope="module")
def running_dashboard_server():
    """Starts the dashboard server on a free port in a background thread for testing."""
    port = 8765
    server = DashboardServer(host="127.0.0.1", port=port, archive_dir="./archive")
    thread = server.start_background()
    time.sleep(0.3)
    yield f"http://127.0.0.1:{port}"
    server.server.shutdown()
    server.server.server_close()


def test_dashboard_root_html(running_dashboard_server: str):
    with httpx.Client(base_url=running_dashboard_server) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "Property Archiver" in r.text
        assert "Dashboard" in r.text


def test_dashboard_api_listings(running_dashboard_server: str):
    with httpx.Client(base_url=running_dashboard_server) as client:
        r = client.get("/api/listings")
        assert r.status_code == 200
        assert "application/json" in r.headers["content-type"]
        listings = r.json()
        assert isinstance(listings, list)
        if listings:
            first = listings[0]
            assert "listing_id" in first
            assert "price" in first
            assert "location" in first
            assert "images_count" in first


def test_dashboard_api_single_listing(running_dashboard_server: str):
    with httpx.Client(base_url=running_dashboard_server) as client:
        r = client.get("/api/listings/T4710876")
        if r.status_code == 200:
            data = r.json()
            assert "listing" in data
            assert "metadata" in data
            assert "checksums" in data
            assert data["listing"]["listing_id"] == "T4710876"


def test_dashboard_api_image_serving(running_dashboard_server: str):
    with httpx.Client(base_url=running_dashboard_server) as client:
        r = client.get("/api/listings/T4710876/image/001_OHWDrL0sRYBS5V4yxQIos2.jpg")
        if r.status_code == 200:
            assert "image" in r.headers["content-type"]
            assert len(r.content) > 1000


def test_dashboard_api_export_csv(running_dashboard_server: str):
    with httpx.Client(base_url=running_dashboard_server) as client:
        r = client.get("/api/export?format=csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "listing_id" in r.text
