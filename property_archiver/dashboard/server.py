"""
Decoupled HTTP Server serving RESTful API routes, static frontend assets, and CRUD operations
with graceful shutdown handlers and standardized JSON error middleware.
"""

import json
import logging
import mimetypes
import os
import signal
import sys
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from property_archiver.dashboard.routes.compare import handle_compare
from property_archiver.dashboard.routes.export import handle_export
from property_archiver.dashboard.routes.hierarchy import handle_get_hierarchy
from property_archiver.dashboard.routes.listings import (
    handle_delete_listing,
    handle_fetch_listing,
    handle_get_image,
    handle_get_listing,
    handle_list_listings,
    handle_update_listing,
)

logger = logging.getLogger(__name__)
FRONTEND_DIR = Path(__file__).parent / "frontend"


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server that immediately frees its address/port upon close."""
    allow_reuse_address = True
    daemon_threads = True


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """Router and dispatcher for REST APIs and Static Frontend files."""

    server_version = "PropertyArchiverDashboard/2.0"

    @property
    def archive_dir(self) -> Path:
        return self.server.archive_dir  # type: ignore

    def do_GET(self):
        """Dispatch GET requests to API routes or static files."""
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path
            query = urllib.parse.parse_qs(parsed_url.query)

            # 1. API: Listings Collection
            if path == "/api/listings":
                data, status = handle_list_listings(self.archive_dir)
                self._send_json_response(data, status)
                return

            # 2. API: Geographic Hierarchy
            if path == "/api/hierarchy":
                data, status = handle_get_hierarchy(self.archive_dir, query)
                self._send_json_response(data, status)
                return

            # 3. API: Single Listing or Image Stream
            if path.startswith("/api/listings/"):
                parts = [p for p in path.split("/") if p]
                if len(parts) == 3:
                    data, status = handle_get_listing(self.archive_dir, parts[2])
                    self._send_json_response(data, status)
                    return
                elif len(parts) == 5 and parts[3] == "image":
                    bytes_data, mime, status = handle_get_image(self.archive_dir, parts[2], parts[4])
                    if status == HTTPStatus.OK and bytes_data:
                        self._send_response_bytes(bytes_data, mime)
                    else:
                        self._send_json_response({"error": "Image not found", "code": "IMAGE_NOT_FOUND", "status": 404}, HTTPStatus.NOT_FOUND)
                    return

            # 4. API: Comparison
            if path == "/api/compare":
                id_a = query.get("a", [""])[0]
                id_b = query.get("b", [""])[0]
                data, status = handle_compare(self.archive_dir, id_a, id_b)
                self._send_json_response(data, status)
                return

            # 5. API: Multi-format Export
            if path == "/api/export":
                fmt = query.get("format", ["csv"])[0]
                bytes_data, mime, filename, status = handle_export(self.archive_dir, fmt)
                if status == HTTPStatus.OK and bytes_data:
                    self.send_response(status)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Disposition", f"attachment; filename={filename}")
                    self.send_header("Content-Length", str(len(bytes_data)))
                    self.end_headers()
                    self.wfile.write(bytes_data)
                else:
                    self._send_json_response({"error": "Export failed", "code": "EXPORT_ERROR", "status": status}, status)
                return

            # 6. API Placeholder Image
            if path == "/api/placeholder":
                self._serve_placeholder()
                return

            # 7. Static Asset Serving
            self._serve_static_file(path)
        except Exception as exc:
            logger.exception("Server error processing GET %s: %s", self.path, exc)
            self._send_json_response({
                "error": "Internal Server Error",
                "detail": str(exc),
                "code": "INTERNAL_SERVER_ERROR",
                "status": 500
            }, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self):
        """Dispatch POST requests for fetching new listings or updating metadata."""
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path

            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"

            try:
                payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            except json.JSONDecodeError:
                self._send_json_response({
                    "error": "Invalid JSON in request payload",
                    "code": "INVALID_JSON",
                    "status": 400
                }, HTTPStatus.BAD_REQUEST)
                return

            if path == "/api/fetch":
                target = payload.get("target") or payload.get("url")
                if not target:
                    self._send_json_response({
                        "error": "Missing required field 'target' or 'url'",
                        "code": "MISSING_FIELD",
                        "status": 400
                    }, HTTPStatus.BAD_REQUEST)
                    return
                data, status = handle_fetch_listing(self.archive_dir, target)
                self._send_json_response(data, status)
                return

            if path.startswith("/api/listings/") and path.endswith("/edit"):
                parts = [p for p in path.split("/") if p]
                if len(parts) == 4:
                    listing_id = parts[2]
                    data, status = handle_update_listing(self.archive_dir, listing_id, payload)
                    self._send_json_response(data, status)
                    return

            self._send_json_response({
                "error": f"Endpoint not found: POST {path}",
                "code": "ENDPOINT_NOT_FOUND",
                "status": 404
            }, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            logger.exception("Server error processing POST %s: %s", self.path, exc)
            self._send_json_response({
                "error": "Internal Server Error",
                "detail": str(exc),
                "code": "INTERNAL_SERVER_ERROR",
                "status": 500
            }, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self):
        """Dispatch DELETE requests for removing archived listings."""
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path

            if path.startswith("/api/listings/"):
                parts = [p for p in path.split("/") if p]
                if len(parts) == 3:
                    listing_id = parts[2]
                    data, status = handle_delete_listing(self.archive_dir, listing_id)
                    self._send_json_response(data, status)
                    return

            self._send_json_response({
                "error": f"Endpoint not found: DELETE {path}",
                "code": "ENDPOINT_NOT_FOUND",
                "status": 404
            }, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            logger.exception("Server error processing DELETE %s: %s", self.path, exc)
            self._send_json_response({
                "error": "Internal Server Error",
                "detail": str(exc),
                "code": "INTERNAL_SERVER_ERROR",
                "status": 500
            }, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static_file(self, rel_path: str):
        """Safely serve frontend static assets with correct MIME types."""
        clean_path = rel_path.lstrip("/")
        if not clean_path or clean_path == "":
            clean_path = "index.html"

        file_path = (FRONTEND_DIR / clean_path).resolve()
        if not str(file_path).startswith(str(FRONTEND_DIR.resolve())):
            self._send_json_response({"error": "Forbidden", "code": "FORBIDDEN", "status": 403}, HTTPStatus.FORBIDDEN)
            return

        if not file_path.exists() or not file_path.is_file():
            self._send_json_response({"error": "File not found", "code": "NOT_FOUND", "status": 404}, HTTPStatus.NOT_FOUND)
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self._send_response_bytes(content, mime_type)
        except Exception as exc:
            self._send_json_response({"error": f"Failed reading asset: {exc}", "code": "ASSET_READ_ERROR", "status": 500}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_placeholder(self):
        """Serve a minimal SVG placeholder image."""
        svg = """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250" viewBox="0 0 400 250">
            <rect width="400" height="250" fill="#001d3d"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#5a6a80" font-family="sans-serif" font-size="16">No Photo Archived</text>
        </svg>"""
        self._send_response_bytes(svg.encode("utf-8"), "image/svg+xml")

    def _send_json_response(self, data: Any, status: HTTPStatus = HTTPStatus.OK):
        """Serialize data to JSON and send response headers with UTF-8 encoding."""
        try:
            payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            logger.error("Failed sending JSON response: %s", exc)

    def _send_response_bytes(self, data: bytes, mime_type: str, status: HTTPStatus = HTTPStatus.OK):
        """Send raw binary content with Content-Type."""
        try:
            self.send_response(status)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            logger.error("Failed sending byte response: %s", exc)

    def log_message(self, format: str, *args: Any):
        """Suppress standard HTTP server request log spam in console unless debug logging."""
        logger.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


class DashboardServer:
    """Encapsulated Dashboard HTTP server lifecycle controller."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, archive_dir: Path | str = "./archive"):
        self.host = host
        self.port = port
        self.archive_dir = Path(archive_dir).resolve()
        self.server: ReusableThreadingHTTPServer | None = None
        self._is_running = False

    def start_background(self) -> threading.Thread:
        """Start HTTP server in a background daemon thread for testing or non-blocking execution."""
        thread = threading.Thread(target=self.start, kwargs={"enable_terminal_input": False}, daemon=True)
        thread.start()
        time.sleep(0.15)
        return thread

    def start(self, enable_terminal_input: bool = True):
        """Start HTTP server with graceful shutdown listeners."""
        self.server = ReusableThreadingHTTPServer((self.host, self.port), DashboardRequestHandler)
        self.server.archive_dir = self.archive_dir  # type: ignore
        self._is_running = True

        def _signal_handler(signum, frame):
            logger.info("Received termination signal %s, shutting down...", signum)
            self.stop()

        try:
            signal.signal(signal.SIGINT, _signal_handler)
            if hasattr(signal, "SIGTERM"):
                signal.signal(signal.SIGTERM, _signal_handler)
        except (ValueError, AttributeError):
            pass

        if enable_terminal_input:
            t = threading.Thread(target=self._terminal_input_listener, daemon=True)
            t.start()

        logger.info("Dashboard running at http://%s:%d", self.host, self.port)
        try:
            self.server.serve_forever()
        except (KeyboardInterrupt, Exception):
            pass
        finally:
            self.stop()

    def _terminal_input_listener(self):
        """Listens on stdin for user typing 'q' + Enter to gracefully quit."""
        while self._is_running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                if line.strip().lower() in ("q", "quit", "exit"):
                    print("\nQuitting dashboard server...")
                    self.stop()
                    break
            except Exception:
                break

    def stop(self):
        """Shutdown and release socket immediately."""
        self._is_running = False
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None
