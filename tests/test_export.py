"""
Tests for PortfolioExporter (CSV, SQLite, JSONL, GeoJSON) and regional geographic filters.
"""

import json
import sqlite3
from pathlib import Path
import pytest

from property_archiver.export.exporter import PortfolioExporter


def test_export_csv_filtered(tmp_path: Path):
    out_csv = tmp_path / "test_lonehill.csv"
    PortfolioExporter.export_csv("./archive", out_csv, filter_suburb="Lonehill")
    assert out_csv.exists()
    content = out_csv.read_text(encoding="utf-8")
    assert "listing_id" in content
    assert "T5333193" in content
    assert "T4710876" not in content  # Rivonia should be filtered out


def test_export_sqlite_filtered(tmp_path: Path):
    out_db = tmp_path / "test_rivonia.db"
    PortfolioExporter.export_sqlite("./archive", out_db, filter_suburb="Rivonia")
    assert out_db.exists()

    conn = sqlite3.connect(out_db)
    cursor = conn.cursor()
    cursor.execute("SELECT listing_id, price_amount, suburb, area, province FROM listings")
    rows = cursor.fetchall()
    assert len(rows) >= 1
    assert all(r[2] == "Rivonia" for r in rows)
    assert all(r[3] == "Sandton" for r in rows)
    assert all(r[4] == "Gauteng" for r in rows)
    ids = [r[0] for r in rows]
    assert "T4710876" in ids
    conn.close()


def test_export_jsonl(tmp_path: Path):
    out_jsonl = tmp_path / "test_portfolio.jsonl"
    PortfolioExporter.export_jsonl("./archive", out_jsonl)
    assert out_jsonl.exists()
    lines = out_jsonl.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1
    records = [json.loads(l) for l in lines]
    ids = [r["listing_id"] for r in records]
    assert "T4710876" in ids


def test_export_geojson(tmp_path: Path):
    out_geojson = tmp_path / "test_portfolio.geojson"
    PortfolioExporter.export_geojson("./archive", out_geojson)
    assert out_geojson.exists()
    data = json.loads(out_geojson.read_text(encoding="utf-8"))
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1
    feat_ids = [f["properties"]["listing_id"] for f in data["features"]]
    assert "T4710876" in feat_ids
