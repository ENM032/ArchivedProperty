"""
Tests for Unified Dashboard HTTP server, REST endpoints, and /api/hierarchy.
"""

import json
import urllib.request
from pathlib import Path
import pytest

from property_archiver.dashboard.server import DashboardServer


@pytest.fixture(scope="module")
def running_server():
    server = DashboardServer(host="127.0.0.1", port=8001, archive_dir="./archive")
    thread = server.start_background()
    yield "http://127.0.0.1:8001"
    server.server.shutdown()


def test_dashboard_root_html(running_server: str):
    req = urllib.request.Request(f"{running_server}/")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        html = res.read().decode("utf-8")
        assert "<title>Property Archiver - Unified Dashboard</title>" in html
        assert "Grouped" in html


def test_api_list_listings(running_server: str):
    req = urllib.request.Request(f"{running_server}/api/listings")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode("utf-8"))
        assert isinstance(data, list)
        assert len(data) >= 1
        ids = [item["listing_id"] for item in data]
        assert "T4710876" in ids


def test_api_hierarchy(running_server: str):
    req = urllib.request.Request(f"{running_server}/api/hierarchy")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        tree = json.loads(res.read().decode("utf-8"))
        assert tree["name"] == "South Africa"
        assert tree["total_listings"] >= 1
        assert "Gauteng" in tree["children"]


def test_api_get_single_listing(running_server: str):
    req = urllib.request.Request(f"{running_server}/api/listings/T4710876")
    with urllib.request.urlopen(req) as res:
        assert res.status == 200
        data = json.loads(res.read().decode("utf-8"))
        assert "listing" in data
        assert data["listing"]["listing_id"] == "T4710876"
        assert data["listing"]["title"] == "4 Bedroom House in Rivonia"
