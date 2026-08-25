"""
Decoupled HTTP Server serving RESTful API routes, static frontend assets, and CRUD operations
with graceful shutdown handlers (Ctrl+C, 'q' + Enter, SIGINT, SIGTERM).
"""

import json
import logging
import mimetypes
import os
import signal
import sys
import threading
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
                        self.send_error(status)
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
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Disposition", f"attachment; filename={filename}")
                self.send_header("Content-Length", str(len(bytes_data)))
                self.end_headers()
                self.wfile.write(bytes_data)
                return

            # 6. API: Placeholder SVG (White & Navy Theme)
            if path == "/api/placeholder":
                svg = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect fill="#f8fafc" stroke="#e2e8f0" stroke-width="2" width="600" height="400"/><text fill="#001d3d" font-family="sans-serif" font-size="22" dy="8" font-weight="bold" x="50%" y="50%" text-anchor="middle">No Image Preview</text></svg>'
                self._send_response_bytes(svg.encode("utf-8"), "image/svg+xml")
                return

            # 7. Static Frontend Asset Dispatcher
            self._serve_static_file(path)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def do_POST(self):
        """Dispatch POST requests to API controllers."""
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            path = parsed_url.path

            if path == "/api/fetch":
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                try:
                    payload = json.loads(body.decode("utf-8"))
                    target = payload.get("target", "")
                    data, status = handle_fetch_listing(self.archive_dir, target)
                    self._send_json_response(data, status)
                except Exception as exc:
                    self._send_json_response({"success": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return

            # Update / Edit Listing
            if path.startswith("/api/listings/") and path.endswith("/edit"):
                parts = [p for p in path.split("/") if p]
                if len(parts) == 4:
                    listing_id = parts[2]
                    content_length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(content_length)
                    try:
                        payload = json.loads(body.decode("utf-8"))
                        data, status = handle_update_listing(self.archive_dir, listing_id, payload)
                        self._send_json_response(data, status)
                    except Exception as exc:
                        self._send_json_response({"success": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

            self.send_error(HTTPStatus.NOT_FOUND, "Resource not found")
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

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

            self.send_error(HTTPStatus.NOT_FOUND, "Resource not found")
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _serve_static_file(self, req_path: str):
        """Safely serve static HTML, CSS, JS from frontend directory."""
        if req_path in ("/", "/index.html", "/dashboard"):
            rel_path = "index.html"
        else:
            rel_path = req_path.lstrip("/")

        file_path = (FRONTEND_DIR / rel_path).resolve()
        if not str(file_path).startswith(str(FRONTEND_DIR.resolve())):
            self.send_error(HTTPStatus.FORBIDDEN, "Access denied")
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, f"File {rel_path} not found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        if file_path.suffix == ".js":
            mime_type = "application/javascript; charset=utf-8"
        elif file_path.suffix == ".css":
            mime_type = "text/css; charset=utf-8"
        elif file_path.suffix == ".html":
            mime_type = "text/html; charset=utf-8"

        with open(file_path, "rb") as f:
            content = f.read()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

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
    """Manager for running the threaded dashboard HTTP server with graceful shutdown."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, archive_dir: Path | str = "./archive"):
        self.host = host
        self.port = port
        self.archive_dir = Path(archive_dir).resolve()
        self.server = ReusableThreadingHTTPServer((self.host, self.port), DashboardRequestHandler)
        self.server.archive_dir = self.archive_dir  # type: ignore
        self._is_running = False
        self._stop_event = threading.Event()

    def start(self, enable_terminal_input: bool = True):
        """Start serving requests indefinitely with graceful terminal quit support."""
        self._is_running = True
        self._stop_event.clear()
        logger.info("Dashboard server running at http://%s:%s (Archive: %s)", self.host, self.port, self.archive_dir)

        # Setup OS signal handlers
        def _handle_signal(sig, frame):
            self.stop()

        try:
            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)
        except (ValueError, AttributeError):
            pass

        # Terminal input listener ('q' + Enter or 'quit' + Enter)
        if enable_terminal_input and sys.stdin and sys.stdin.isatty():
            def _terminal_listener():
                try:
                    while self._is_running:
                        line = sys.stdin.readline()
                        if not line:  # EOF / Ctrl+D
                            self.stop()
                            break
                        cmd = line.strip().lower()
                        if cmd in ("q", "quit", "exit", "stop"):
                            self.stop()
                            break
                except Exception:
                    pass

            t_listener = threading.Thread(target=_terminal_listener, daemon=True)
            t_listener.start()

        try:
            while self._is_running and not self._stop_event.is_set():
                self.server.serve_forever(poll_interval=0.5)
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            self.stop()

    def stop(self):
        """Gracefully shutdown and close socket."""
        if not self._is_running:
            return
        self._is_running = False
        self._stop_event.set()
        try:
            self.server.shutdown()
        except Exception:
            pass
        try:
            self.server.server_close()
        except Exception:
            pass
        logger.info("Dashboard server stopped cleanly.")

    def start_background(self) -> threading.Thread:
        """Start serving in a background thread."""
        thread = threading.Thread(target=lambda: self.start(enable_terminal_input=False), daemon=True)
        thread.start()
        return thread
