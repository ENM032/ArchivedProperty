"""
Tests for PortfolioExporter (CSV, SQLite, JSONL, GeoJSON).
"""

import json
import sqlite3
from pathlib import Path
import pytest

from property_archiver.export.exporter import PortfolioExporter


def test_export_csv(tmp_path: Path):
    out_csv = tmp_path / "test_portfolio.csv"
    PortfolioExporter.export_csv("./archive", out_csv)
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8")
    assert "listing_id" in content
    assert "T4710876" in content


def test_export_sqlite(tmp_path: Path):
    out_db = tmp_path / "test_portfolio.db"
    PortfolioExporter.export_sqlite("./archive", out_db)
    assert out_db.exists()

    conn = sqlite3.connect(out_db)
    cursor = conn.cursor()
    cursor.execute("SELECT listing_id, price_amount, suburb FROM listings")
    rows = cursor.fetchall()
    assert len(rows) >= 1
    assert rows[0][0] == "T4710876"
    assert rows[0][1] == 4999000.0
    assert rows[0][2] == "Rivonia"

    cursor.execute("SELECT count(*) FROM listing_images")
    img_count = cursor.fetchone()[0]
    assert img_count >= 50
    conn.close()


def test_export_jsonl(tmp_path: Path):
    out_jsonl = tmp_path / "test_portfolio.jsonl"
    PortfolioExporter.export_jsonl("./archive", out_jsonl)
    assert out_jsonl.exists()
    lines = out_jsonl.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1
    first_record = json.loads(lines[0])
    assert first_record["listing_id"] == "T4710876"


def test_export_geojson(tmp_path: Path):
    out_geojson = tmp_path / "test_portfolio.geojson"
    PortfolioExporter.export_geojson("./archive", out_geojson)
    assert out_geojson.exists()
    data = json.loads(out_geojson.read_text(encoding="utf-8"))
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    feat = data["features"][0]
    assert feat["geometry"]["type"] == "Point"
    assert feat["geometry"]["coordinates"] == [28.055459, -26.043712]
    assert feat["properties"]["listing_id"] == "T4710876"
