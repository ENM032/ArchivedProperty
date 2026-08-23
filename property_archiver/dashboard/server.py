"""
Embedded HTTP server and REST API with recursive listing discovery,
export engine, and /api/hierarchy endpoint.
"""

import io
import json
import logging
import mimetypes
import os
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from property_archiver.config import settings
from property_archiver.core.change_detector import ChangeDetector
from property_archiver.core.fetcher import Fetcher
from property_archiver.core.hierarchy import GeoHierarchyBuilder, GeoNode
from property_archiver.core.security import safe_join_path
from property_archiver.dashboard.app_html import DASHBOARD_HTML
from property_archiver.export.exporter import PortfolioExporter
from property_archiver.extractors import get_extractor_for_url_or_html
from property_archiver.images.downloader import ImageDownloader
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter
from property_archiver.utils.url_resolver import resolve_input_targets

logger = logging.getLogger(__name__)


def serialize_geo_node(node: GeoNode) -> dict[str, Any]:
    """Serialize a GeoNode and its subtree to a clean JSON-friendly dict."""
    return {
        "name": node.name,
        "level": node.level,
        "total_listings": node.total_listings,
        "total_value_zar": node.total_value_zar,
        "avg_price_zar": node.avg_price_zar,
        "active_count": node.active_count,
        "under_offer_count": node.under_offer_count,
        "sold_count": node.sold_count,
        "children": {k: serialize_geo_node(v) for k, v in node.children.items()},
        "listings": [
            {
                "listing_id": r.listing_id,
                "portal_name": r.portal_name,
                "title": r.title,
                "property_type": r.property_type,
                "listing_status": r.listing_status,
                "is_under_offer": r.is_under_offer,
                "is_sold": r.is_sold,
                "status_badges": r.status_badges,
                "price": r.price.model_dump(),
                "location": r.location.model_dump(),
                "features": r.features.model_dump(),
                "erf_size_m2": r.erf_size_m2,
                "floor_size_m2": r.floor_size_m2,
                "images_count": len(r.images),
                "hero_image_url": f"/api/listings/{r.listing_id}/image/{r.images[0].local_filename}" if (r.images and r.images[0].local_filename) else None,
                "extracted_at": r.extracted_at.isoformat(),
            }
            for r in node.listings
        ]
    }


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Handles REST API and Single-Page Application requests for the Dashboard."""

    server_version = "PropertyArchiverDashboard/1.0"

    @property
    def archive_dir(self) -> Path:
        return self.server.archive_dir  # type: ignore

    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. Root SPA HTML
        if path in ("/", "/index.html", "/dashboard"):
            self._send_html_response(DASHBOARD_HTML)
            return

        # 2. API: List all archived listings (recursive)
        if path == "/api/listings":
            self._handle_api_list_listings()
            return

        # 3. API: Geographic Hierarchy Tree
        if path == "/api/hierarchy":
            self._handle_api_hierarchy(query)
            return

        # 4. API: Single listing details or image
        if path.startswith("/api/listings/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 3:
                listing_id = parts[2]
                self._handle_api_get_listing(listing_id)
                return
            elif len(parts) == 5 and parts[3] == "image":
                listing_id = parts[2]
                image_filename = parts[4]
                self._handle_api_get_image(listing_id, image_filename)
                return

        # 5. API: Compare two archives
        if path == "/api/compare":
            id_a = query.get("a", [""])[0]
            id_b = query.get("b", [""])[0]
            self._handle_api_compare(id_a, id_b)
            return

        # 6. API: Multi-format export (CSV, SQLite, JSONL, GeoJSON)
        if path == "/api/export":
            export_fmt = query.get("format", ["csv"])[0].lower()
            self._handle_api_export(export_fmt)
            return

        # 7. Placeholder SVG image
        if path == "/api/placeholder":
            svg = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect fill="#1e293b" width="600" height="400"/><text fill="#94a3b8" font-family="sans-serif" font-size="24" dy="10.5" font-weight="bold" x="50%" y="50%" text-anchor="middle">No Image Preview</text></svg>'
            self._send_response_bytes(svg.encode("utf-8"), "image/svg+xml")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Resource not found")

    def do_POST(self):
        """Handle POST requests."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/fetch":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode("utf-8"))
                target = payload.get("target")
                if not target:
                    self._send_json_response({"success": False, "error": "Target URL/ID is required"}, HTTPStatus.BAD_REQUEST)
                    return
                self._handle_api_fetch_listing(target)
            except Exception as exc:
                self._send_json_response({"success": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Resource not found")

    def _handle_api_list_listings(self):
        """Return array of summary records for all discovered listings."""
        listing_dirs = ArchiveReader.find_all_listing_dirs(self.archive_dir)
        results: list[dict[str, Any]] = []

        for item in listing_dirs:
            try:
                record = ArchiveReader.load_listing(item)
                hero_url = None
                if record.images:
                    for img in record.images:
                        if img.local_filename and (item / "images" / img.local_filename).exists():
                            hero_url = f"/api/listings/{record.listing_id}/image/{img.local_filename}"
                            break

                prov, area, sub = GeoHierarchyBuilder.extract_geo_keys(record)

                results.append({
                    "listing_id": record.listing_id,
                    "portal_name": record.portal_name,
                    "title": record.title,
                    "property_type": record.property_type,
                    "listing_status": record.listing_status,
                    "is_under_offer": record.is_under_offer,
                    "is_sold": record.is_sold,
                    "status_badges": record.status_badges,
                    "price": record.price.model_dump(),
                    "location": record.location.model_dump(),
                    "geo_hierarchy": {
                        "province": prov,
                        "area": area,
                        "suburb": sub,
                    },
                    "features": record.features.model_dump(),
                    "erf_size_m2": record.erf_size_m2,
                    "land_size_raw": record.land_size_raw,
                    "floor_size_m2": record.floor_size_m2,
                    "images_count": len(record.images),
                    "hero_image_url": hero_url,
                    "extracted_at": record.extracted_at.isoformat(),
                })
            except Exception as exc:
                logger.error("Failed loading listing %s: %s", item.name, exc)

        self._send_json_response(results)

    def _handle_api_hierarchy(self, query: dict[str, list[str]]):
        """Return complete geographic hierarchy tree with aggregate statistics."""
        records = PortfolioExporter.load_all_listings(self.archive_dir)
        prov = query.get("province", [None])[0]
        area = query.get("area", [None])[0]
        sub = query.get("suburb", [None])[0]
        status = query.get("status", ["all"])[0]

        tree_root = GeoHierarchyBuilder.build_tree(
            records=records,
            filter_province=prov,
            filter_area=area,
            filter_suburb=sub,
            filter_status=status,
        )
        self._send_json_response(serialize_geo_node(tree_root))

    def _handle_api_get_listing(self, listing_id: str):
        """Return full details for a listing."""
        try:
            listing_dir = ArchiveReader.find_listing_dir(self.archive_dir, listing_id)
            if not listing_dir:
                self.send_error(HTTPStatus.NOT_FOUND, f"Listing {listing_id} not found")
                return

            record = ArchiveReader.load_listing(listing_dir)
            metadata = ArchiveReader.load_metadata(listing_dir)
            manifest = ArchiveReader.load_manifest(listing_dir)

            self._send_json_response({
                "listing": record.model_dump(mode="json"),
                "metadata": metadata.model_dump(mode="json"),
                "checksums": manifest.model_dump(mode="json"),
            })
        except Exception as exc:
            self._send_json_response({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_api_get_image(self, listing_id: str, filename: str):
        """Serve an archived image file safely."""
        try:
            listing_dir = ArchiveReader.find_listing_dir(self.archive_dir, listing_id)
            if not listing_dir:
                self.send_error(HTTPStatus.NOT_FOUND, "Listing not found")
                return

            img_path = safe_join_path(listing_dir / "images", filename)
            if not img_path.exists() or not img_path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "Image not found")
                return

            mime_type, _ = mimetypes.guess_type(str(img_path))
            mime_type = mime_type or "image/jpeg"

            with open(img_path, "rb") as f:
                img_bytes = f.read()

            self._send_response_bytes(img_bytes, mime_type)
        except Exception:
            self.send_error(HTTPStatus.FORBIDDEN, "Access denied")

    def _handle_api_compare(self, id_a: str, id_b: str):
        """Compare two listings or snapshots."""
        try:
            dir_a = ArchiveReader.find_listing_dir(self.archive_dir, id_a)
            dir_b = ArchiveReader.find_listing_dir(self.archive_dir, id_b)
            if not dir_a or not dir_b:
                self.send_error(HTTPStatus.NOT_FOUND, "One or both listings not found")
                return

            diff = ChangeDetector.compare_archives(dir_a, dir_b)
            self._send_json_response({
                "listing_id": diff.listing_id,
                "is_identical": diff.is_identical,
                "price_changed": diff.price_changed,
                "old_price": diff.old_price,
                "new_price": diff.new_price,
                "price_diff": diff.price_diff,
                "status_changed": diff.status_changed,
                "old_status": diff.old_status,
                "new_status": diff.new_status,
                "badges_added": diff.badges_added,
                "badges_removed": diff.badges_removed,
                "spec_changes": diff.spec_changes,
                "added_features": diff.added_features,
                "removed_features": diff.removed_features,
            })
        except Exception as exc:
            self._send_json_response({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_api_export(self, export_fmt: str):
        """Export portfolio in requested format."""
        temp_dir = Path("./scratch")
        temp_dir.mkdir(parents=True, exist_ok=True)

        if export_fmt == "sqlite":
            out_file = temp_dir / "portfolio.db"
            PortfolioExporter.export_sqlite(self.archive_dir, out_file)
            with open(out_file, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-sqlite3")
            self.send_header("Content-Disposition", "attachment; filename=portfolio.db")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        elif export_fmt == "jsonl":
            out_file = temp_dir / "portfolio.jsonl"
            PortfolioExporter.export_jsonl(self.archive_dir, out_file)
            with open(out_file, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=portfolio.jsonl")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        elif export_fmt == "geojson":
            out_file = temp_dir / "portfolio.geojson"
            PortfolioExporter.export_geojson(self.archive_dir, out_file)
            with open(out_file, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/geo+json; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=portfolio.geojson")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        else:
            out_file = temp_dir / "portfolio.csv"
            PortfolioExporter.export_csv(self.archive_dir, out_file)
            with open(out_file, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=portfolio.csv")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    def _handle_api_fetch_listing(self, target: str):
        """Execute ingestion & archival for a target from the dashboard UI."""
        resolved = resolve_input_targets([target])
        if not resolved:
            self._send_json_response({"success": False, "error": f"Invalid target: {target}"}, HTTPStatus.BAD_REQUEST)
            return

        target_url = resolved[0]
        cfg = settings.model_copy()
        cfg.archive_dir = self.archive_dir
        cfg.download_images = True

        fetcher = Fetcher(config=cfg)
        result = fetcher.fetch_url(target_url)

        extractor = get_extractor_for_url_or_html(result.url)
        listing = extractor.extract(result.text, result.url)

        writer = ArchiveWriter(config=cfg)
        staging_dir, images_dir = writer.create_staging_dir(listing.listing_id, cfg.archive_dir)

        if listing.images:
            downloader = ImageDownloader(config=cfg)
            listing.images = downloader.download_all(listing.images, images_dir)

        metadata = ArchiveMetadata(
            schema_version="1.0.0",
            listing_id=listing.listing_id,
            source_url=result.url,
            archiver_version="1.0.0",
            fetch_mode="http",
            http_status=result.status_code,
            response_headers=result.headers,
            fetch_duration_sec=result.duration_sec,
            total_images_discovered=len(listing.images),
            total_images_archived=sum(1 for img in listing.images if img.local_filename is not None),
            content_fingerprint=listing.content_fingerprint,
        )

        archive_path = writer.commit_archive(
            staging_dir=staging_dir,
            listing=listing,
            raw_html=result.content,
            metadata=metadata,
            output_base_dir=cfg.archive_dir,
        )

        self._send_json_response({
            "success": True,
            "listing_id": listing.listing_id,
            "title": listing.title,
            "archive_path": str(archive_path),
        })

    def _send_html_response(self, html_content: str):
        content_bytes = html_content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content_bytes)))
        self.end_headers()
        self.wfile.write(content_bytes)

    def _send_json_response(self, data: Any, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_response_bytes(self, content_bytes: bytes, mime_type: str):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content_bytes)))
        self.end_headers()
        self.wfile.write(content_bytes)

    def log_message(self, format, *args):
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


class DashboardServer:
    """Manager for running the threaded dashboard HTTP server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, archive_dir: Path | str = "./archive"):
        self.host = host
        self.port = port
        self.archive_dir = Path(archive_dir).resolve()
        self.server = ThreadingHTTPServer((self.host, self.port), DashboardRequestHandler)
        self.server.archive_dir = self.archive_dir  # type: ignore

    def start(self):
        """Start serving requests indefinitely."""
        logger.info("Dashboard server starting on http://%s:%s (Archive: %s)", self.host, self.port, self.archive_dir)
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Dashboard server stopped by user.")
        finally:
            self.server.server_close()

    def start_background(self) -> threading.Thread:
        """Start serving in a background thread."""
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread
