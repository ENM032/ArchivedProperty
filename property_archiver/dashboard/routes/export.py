"""
Route handlers for multi-format portfolio downloads.
"""

from http import HTTPStatus
from pathlib import Path

from property_archiver.export.exporter import PortfolioExporter


def handle_export(archive_dir: Path, export_fmt: str) -> tuple[bytes, str, str, HTTPStatus]:
    """Generate export content and return bytes, MIME type, filename."""
    temp_dir = Path("./scratch")
    temp_dir.mkdir(parents=True, exist_ok=True)
    fmt = export_fmt.lower()

    if fmt == "sqlite":
        out_file = temp_dir / "portfolio.db"
        PortfolioExporter.export_sqlite(archive_dir, out_file)
        return out_file.read_bytes(), "application/x-sqlite3", "portfolio.db", HTTPStatus.OK

    elif fmt == "jsonl":
        out_file = temp_dir / "portfolio.jsonl"
        PortfolioExporter.export_jsonl(archive_dir, out_file)
        return out_file.read_bytes(), "application/x-ndjson; charset=utf-8", "portfolio.jsonl", HTTPStatus.OK

    elif fmt == "geojson":
        out_file = temp_dir / "portfolio.geojson"
        PortfolioExporter.export_geojson(archive_dir, out_file)
        return out_file.read_bytes(), "application/geo+json; charset=utf-8", "portfolio.geojson", HTTPStatus.OK

    else:
        out_file = temp_dir / "portfolio.csv"
        PortfolioExporter.export_csv(archive_dir, out_file)
        return out_file.read_bytes(), "text/csv; charset=utf-8", "portfolio.csv", HTTPStatus.OK
