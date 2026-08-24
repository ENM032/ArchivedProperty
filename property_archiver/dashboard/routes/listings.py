"""
Route handlers for listing resources, details, image streaming, and fetch ingestion.
"""

import json
import logging
import mimetypes
from http import HTTPStatus
from pathlib import Path
from typing import Any

from property_archiver.config import settings
from property_archiver.core.fetcher import Fetcher
from property_archiver.core.hierarchy import GeoHierarchyBuilder
from property_archiver.core.security import safe_join_path
from property_archiver.extractors import get_extractor_for_url_or_html
from property_archiver.images.downloader import ImageDownloader
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter
from property_archiver.utils.url_resolver import resolve_input_targets

logger = logging.getLogger(__name__)


def handle_list_listings(archive_dir: Path) -> tuple[dict[str, Any] | list[Any], HTTPStatus]:
    """Return summary array for all discovered listings."""
    listing_dirs = ArchiveReader.find_all_listing_dirs(archive_dir)
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
                "listing_type": getattr(record, "listing_type", "for_sale"),
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

    return results, HTTPStatus.OK


def handle_get_listing(archive_dir: Path, listing_id: str) -> tuple[dict[str, Any], HTTPStatus]:
    """Return full details, metadata, and manifest for a specific listing."""
    try:
        listing_dir = ArchiveReader.find_listing_dir(archive_dir, listing_id)
        if not listing_dir:
            return {"error": f"Listing {listing_id} not found"}, HTTPStatus.NOT_FOUND

        record = ArchiveReader.load_listing(listing_dir)
        metadata = ArchiveReader.load_metadata(listing_dir)
        manifest = ArchiveReader.load_manifest(listing_dir)

        return {
            "listing": record.model_dump(mode="json"),
            "metadata": metadata.model_dump(mode="json"),
            "checksums": manifest.model_dump(mode="json"),
        }, HTTPStatus.OK
    except Exception as exc:
        return {"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR


def handle_get_image(archive_dir: Path, listing_id: str, filename: str) -> tuple[bytes | None, str, HTTPStatus]:
    """Retrieve image binary content safely."""
    try:
        listing_dir = ArchiveReader.find_listing_dir(archive_dir, listing_id)
        if not listing_dir:
            return None, "text/plain", HTTPStatus.NOT_FOUND

        img_path = safe_join_path(listing_dir / "images", filename)
        if not img_path.exists() or not img_path.is_file():
            return None, "text/plain", HTTPStatus.NOT_FOUND

        mime_type, _ = mimetypes.guess_type(str(img_path))
        mime_type = mime_type or "image/jpeg"

        with open(img_path, "rb") as f:
            return f.read(), mime_type, HTTPStatus.OK
    except Exception:
        return None, "text/plain", HTTPStatus.FORBIDDEN


def handle_fetch_listing(archive_dir: Path, target: str) -> tuple[dict[str, Any], HTTPStatus]:
    """Execute ingestion & archival for a target URL or ID."""
    resolved = resolve_input_targets([target])
    if not resolved:
        return {"success": False, "error": f"Invalid target: {target}"}, HTTPStatus.BAD_REQUEST

    target_url = resolved[0]
    cfg = settings.model_copy()
    cfg.archive_dir = archive_dir
    cfg.download_images = True

    try:
        fetcher = Fetcher(config=cfg)
        result = fetcher.fetch_url(target_url)

        extractor = get_extractor_for_url_or_html(result.url)
        listing = extractor.extract(result.text, result.url)

        writer = ArchiveWriter(config=cfg)
        staging_dir, images_dir = writer.create_staging_dir(listing.listing_id, cfg.archive_dir)

        if listing.images:
            existing_dir = ArchiveReader.find_listing_dir(archive_dir, listing.listing_id)
            existing_images_dir = (existing_dir / "images") if (existing_dir and (existing_dir / "images").exists()) else None

            downloader = ImageDownloader(config=cfg)
            listing.images = downloader.download_all(listing.images, images_dir, existing_images_dir=existing_images_dir)

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

        return {
            "success": True,
            "listing_id": listing.listing_id,
            "title": listing.title,
            "archive_path": str(archive_path),
        }, HTTPStatus.OK
    except Exception as exc:
        return {"success": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR
