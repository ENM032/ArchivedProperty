"""
Multi-format export engine: CSV, SQLite, JSON Lines, and GeoJSON (GIS).
"""

import csv
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from property_archiver.models.listing import ListingRecord
from property_archiver.storage.reader import ArchiveReader

logger = logging.getLogger(__name__)


class PortfolioExporter:
    """Exports archived property collections into analytical and spatial formats."""

    @staticmethod
    def load_all_listings(archive_dir: Path | str) -> list[ListingRecord]:
        """Load all valid listing records from the archive directory."""
        base_dir = Path(archive_dir).resolve() / "listings"
        records: list[ListingRecord] = []

        if not base_dir.exists():
            return records

        for item in base_dir.iterdir():
            if item.is_dir() and (item / "listing.json").exists():
                try:
                    rec = ArchiveReader.load_listing(item)
                    records.append(rec)
                except Exception as exc:
                    logger.warning("Failed loading listing %s for export: %s", item.name, exc)

        return records

    @staticmethod
    def export_csv(archive_dir: Path | str, output_path: Path | str) -> Path:
        """Export all listings to a flattened CSV spreadsheet."""
        records = PortfolioExporter.load_all_listings(archive_dir)
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        rows: list[dict[str, Any]] = []
        for r in records:
            rows.append({
                "listing_id": r.listing_id,
                "portal": r.portal_name,
                "title": r.title,
                "property_type": r.property_type,
                "listing_status": r.listing_status,
                "is_under_offer": r.is_under_offer,
                "is_sold": r.is_sold,
                "is_on_show": r.is_on_show,
                "is_price_reduced": r.is_price_reduced,
                "status_badges": ", ".join(r.status_badges),
                "price_amount": r.price.amount,
                "price_currency": r.price.currency,
                "rates_taxes_monthly": r.price.rates_and_taxes_monthly,
                "levies_monthly": r.price.levies_monthly,
                "street_address": r.location.street_address,
                "suburb": r.location.suburb,
                "city": r.location.city,
                "province": r.location.province,
                "country": r.location.country,
                "latitude": r.location.latitude,
                "longitude": r.location.longitude,
                "bedrooms": r.features.bedrooms,
                "bathrooms": r.features.bathrooms,
                "en_suites": r.features.en_suites,
                "lounges": r.features.lounges,
                "garages": r.features.garages,
                "erf_size_m2": r.erf_size_m2,
                "land_size_raw": r.land_size_raw,
                "floor_size_m2": r.floor_size_m2,
                "has_pool": r.features.has_pool,
                "has_garden": r.features.has_garden,
                "has_alarm": r.features.has_alarm,
                "has_security_post": r.features.has_security_post,
                "has_staff_quarters": r.features.has_staff_quarters,
                "has_aircon": r.features.has_aircon,
                "primary_agent_name": r.agent.agent_name if r.agent else None,
                "agency_name": r.agent.agency_name if r.agent else None,
                "co_agents_count": len(r.co_agents),
                "images_count": len(r.images),
                "canonical_url": r.canonical_url,
                "extracted_at": r.extracted_at.isoformat(),
            })

        if rows:
            with open(out_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        else:
            with open(out_file, "w", encoding="utf-8") as f:
                f.write("listing_id,title,price_amount,status\n")

        return out_file

    @staticmethod
    def export_sqlite(archive_dir: Path | str, output_path: Path | str) -> Path:
        """Export all listings into an indexed relational SQLite database."""
        records = PortfolioExporter.load_all_listings(archive_dir)
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if out_file.exists():
            out_file.unlink()

        conn = sqlite3.connect(out_file)
        cursor = conn.cursor()

        # Create Schema
        cursor.execute("""
        CREATE TABLE listings (
            listing_id TEXT PRIMARY KEY,
            portal_name TEXT,
            title TEXT,
            property_type TEXT,
            listing_status TEXT,
            is_under_offer INTEGER,
            is_sold INTEGER,
            is_on_show INTEGER,
            is_price_reduced INTEGER,
            price_amount REAL,
            rates_taxes_monthly REAL,
            levies_monthly REAL,
            street_address TEXT,
            suburb TEXT,
            city TEXT,
            province TEXT,
            latitude REAL,
            longitude REAL,
            erf_size_m2 REAL,
            floor_size_m2 REAL,
            bedrooms REAL,
            bathrooms REAL,
            garages REAL,
            agent_name TEXT,
            agency_name TEXT,
            images_count INTEGER,
            canonical_url TEXT,
            extracted_at TEXT,
            content_fingerprint TEXT
        )
        """)

        cursor.execute("CREATE INDEX idx_listings_suburb ON listings(suburb)")
        cursor.execute("CREATE INDEX idx_listings_status ON listings(listing_status)")
        cursor.execute("CREATE INDEX idx_listings_price ON listings(price_amount)")

        cursor.execute("""
        CREATE TABLE listing_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            listing_id TEXT,
            order_index INTEGER,
            local_filename TEXT,
            resolved_url TEXT,
            sha256 TEXT,
            width INTEGER,
            height INTEGER,
            FOREIGN KEY (listing_id) REFERENCES listings(listing_id)
        )
        """)

        for r in records:
            cursor.execute("""
            INSERT INTO listings VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """, (
                r.listing_id,
                r.portal_name,
                r.title,
                r.property_type,
                r.listing_status,
                int(r.is_under_offer),
                int(r.is_sold),
                int(r.is_on_show),
                int(r.is_price_reduced),
                r.price.amount,
                r.price.rates_and_taxes_monthly,
                r.price.levies_monthly,
                r.location.street_address,
                r.location.suburb,
                r.location.city,
                r.location.province,
                r.location.latitude,
                r.location.longitude,
                r.erf_size_m2,
                r.floor_size_m2,
                r.features.bedrooms,
                r.features.bathrooms,
                r.features.garages,
                r.agent.agent_name if r.agent else None,
                r.agent.agency_name if r.agent else None,
                len(r.images),
                r.canonical_url,
                r.extracted_at.isoformat(),
                r.content_fingerprint,
            ))

            for img in r.images:
                cursor.execute("""
                INSERT INTO listing_images (listing_id, order_index, local_filename, resolved_url, sha256, width, height)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    r.listing_id,
                    img.order_index,
                    img.local_filename,
                    img.resolved_url,
                    img.sha256,
                    img.width,
                    img.height,
                ))

        conn.commit()
        conn.close()
        return out_file

    @staticmethod
    def export_jsonl(archive_dir: Path | str, output_path: Path | str) -> Path:
        """Export all listings as line-delimited JSON (JSONL)."""
        records = PortfolioExporter.load_all_listings(archive_dir)
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            for r in records:
                f.write(r.model_dump_json() + "\n")

        return out_file

    @staticmethod
    def export_geojson(archive_dir: Path | str, output_path: Path | str) -> Path:
        """Export all listings with GPS coordinates as a standard GeoJSON FeatureCollection."""
        records = PortfolioExporter.load_all_listings(archive_dir)
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        features: list[dict[str, Any]] = []
        for r in records:
            if r.location.latitude is not None and r.location.longitude is not None:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [r.location.longitude, r.location.latitude]
                    },
                    "properties": {
                        "listing_id": r.listing_id,
                        "title": r.title,
                        "price_amount": r.price.amount,
                        "price_display": r.price.formatted_display,
                        "status": r.listing_status,
                        "is_under_offer": r.is_under_offer,
                        "is_sold": r.is_sold,
                        "street_address": r.location.street_address,
                        "suburb": r.location.suburb,
                        "city": r.location.city,
                        "bedrooms": r.features.bedrooms,
                        "bathrooms": r.features.bathrooms,
                        "erf_size_m2": r.erf_size_m2,
                        "canonical_url": r.canonical_url,
                        "hero_image_url": r.images[0].resolved_url if r.images else None,
                    }
                })

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)

        return out_file
