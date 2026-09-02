"""
Sync Engine for automated listing lifecycle updates, price tracking, status transitions,
delisting detection, and historic change ledger management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Callable

from property_archiver.config import ArchiverSettings, settings
from property_archiver.core.change_detector import ChangeDetector
from property_archiver.core.exceptions import FetchError, HTTPStatusError
from property_archiver.core.fetcher import Fetcher
from property_archiver.core.hasher import calculate_file_sha256
from property_archiver.extractors import get_extractor_for_url_or_html
from property_archiver.images.downloader import ImageDownloader
from property_archiver.models.archive import ArchiveMetadata
from property_archiver.models.listing import ListingRecord
from property_archiver.storage.reader import ArchiveReader
from property_archiver.storage.writer import ArchiveWriter

logger = logging.getLogger(__name__)


@dataclass
class SyncListingEvent:
    listing_id: str
    event_type: str  # "price_drop", "price_increase", "status_transition", "delisted", "spec_update", "unchanged", "error"
    title: str | None = None
    suburb: str | None = None
    old_value: Any = None
    new_value: Any = None
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SyncResult:
    total_scanned: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    delisted_count: int = 0
    failed_count: int = 0
    events: list[SyncListingEvent] = field(default_factory=list)


class SyncEngine:
    """Orchestrates portfolio re-scraping, change detection, and lifecycle tracking."""

    DELIST_INDICATORS = [
        "no longer available",
        "this property has been removed",
        "page not found",
        "mandate has expired",
        "listing is inactive",
        "this listing is no longer active",
        "listing not found",
    ]

    def __init__(self, config: ArchiverSettings | None = None):
        self.config = config or settings

    def discover_targets(
        self,
        archive_dir: Path | str,
        filter_province: str | None = None,
        filter_area: str | None = None,
        filter_suburb: str | None = None,
        filter_status: str | None = "active_or_offer",
    ) -> list[Path]:
        """Discover listing directories matching the geographic and lifecycle filter criteria."""
        base_dir = Path(archive_dir).resolve()
        all_dirs = ArchiveReader.find_all_listing_dirs(base_dir)
        targets: list[Path] = []

        for ldir in all_dirs:
            try:
                rec = ArchiveReader.load_listing(ldir)
                
                # Geographic filters
                if filter_province and filter_province.lower() not in (rec.location.province or "").lower():
                    continue
                if filter_area and filter_area.lower() not in (rec.location.region or rec.location.city or "").lower():
                    continue
                if filter_suburb and filter_suburb.lower() not in (rec.location.suburb or "").lower():
                    continue

                # Status filter (default: active_or_offer skips sold/delisted)
                st = (rec.listing_status or "active").lower()
                if filter_status == "active_or_offer":
                    if st in ("sold", "delisted", "withdrawn") and not rec.is_under_offer:
                        continue
                elif filter_status and filter_status != "all":
                    if filter_status.lower() != st:
                        continue

                targets.append(ldir)
            except Exception as exc:
                logger.warning("Skipping target discovery for %s: %s", ldir.name, exc)

        return targets

    def sync_single(
        self,
        listing_dir: Path,
        dry_run: bool = False,
        no_images: bool = False,
        fetcher: Fetcher | None = None,
    ) -> SyncListingEvent:
        """Fetch live URL, evaluate lifecycle status, detect changes, and commit updates."""
        listing_dir = Path(listing_dir).resolve()
        old_record = ArchiveReader.load_listing(listing_dir)
        target_url = old_record.canonical_url
        lid = old_record.listing_id
        suburb = old_record.location.suburb or "Unknown"

        fetch_engine = fetcher or Fetcher(config=self.config)

        try:
            fetch_res = fetch_engine.fetch_url(target_url)
        except HTTPStatusError as http_err:
            if http_err.status_code in (404, 410, 301, 302):
                return self._handle_delisted(listing_dir, old_record, f"HTTP {http_err.status_code}", dry_run)
            logger.error("HTTP error fetching %s (%s): %s", lid, target_url, http_err)
            return SyncListingEvent(listing_id=lid, event_type="error", title=old_record.title, suburb=suburb, details=str(http_err))
        except FetchError as fetch_err:
            logger.error("Network fetch error for %s (%s): %s", lid, target_url, fetch_err)
            return SyncListingEvent(listing_id=lid, event_type="error", title=old_record.title, suburb=suburb, details=str(fetch_err))

        # Check soft 404 / delisting text
        content_lower = fetch_res.text.lower()
        if any(ind in content_lower for ind in self.DELIST_INDICATORS):
            return self._handle_delisted(listing_dir, old_record, "Delist text detected on page", dry_run)

        # Re-extract fresh listing record
        try:
            extractor = get_extractor_for_url_or_html(fetch_res.url)
            new_record = extractor.extract(fetch_res.text, fetch_res.url)
        except Exception as parse_err:
            logger.error("Failed parsing live listing %s: %s", lid, parse_err)
            return SyncListingEvent(listing_id=lid, event_type="error", title=old_record.title, suburb=suburb, details=f"Parse Error: {parse_err}")

        # Preserve user annotations
        new_record.user_notes = old_record.user_notes
        new_record.user_tags = old_record.user_tags
        new_record.user_rating = old_record.user_rating

        # Compute semantic diff
        diff = ChangeDetector.compare_records(old_record, new_record)
        if diff.is_identical:
            return SyncListingEvent(listing_id=lid, event_type="unchanged", title=old_record.title, suburb=suburb, details="No changes detected")

        # Determine primary event type
        if diff.price_changed:
            p_diff = diff.price_diff or 0
            event_type = "price_drop" if p_diff < 0 else "price_increase"
            pct = ((new_record.price.amount - old_record.price.amount) / old_record.price.amount) * 100 if old_record.price.amount else 0
            details = f"R {old_record.price.amount:,.0f} -> R {new_record.price.amount:,.0f} ({pct:+.1f}%)"
            old_val, new_val = old_record.price.amount, new_record.price.amount
        elif diff.status_changed:
            event_type = "status_transition"
            details = f"{diff.old_status.upper()} -> {diff.new_status.upper()}"
            old_val, new_val = diff.old_status, diff.new_status
        else:
            event_type = "spec_update"
            details = ", ".join(diff.spec_changes) if diff.spec_changes else "Specifications updated"
            old_val, new_val = None, None

        if not dry_run:
            self._apply_update(listing_dir, new_record, fetch_res, diff, no_images)

        return SyncListingEvent(
            listing_id=lid,
            event_type=event_type,
            title=new_record.title,
            suburb=suburb,
            old_value=old_val,
            new_value=new_val,
            details=details,
        )

    def _handle_delisted(self, listing_dir: Path, old_record: ListingRecord, reason: str, dry_run: bool) -> SyncListingEvent:
        """Mark listing as delisted without removing historic assets."""
        lid = old_record.listing_id
        suburb = old_record.location.suburb or "Unknown"

        if old_record.listing_status == "delisted":
            return SyncListingEvent(listing_id=lid, event_type="unchanged", title=old_record.title, suburb=suburb, details="Already marked delisted")

        if not dry_run:
            old_record.listing_status = "delisted"
            (listing_dir / "listing.json").write_text(old_record.model_dump_json(indent=2), encoding="utf-8")

            # Append to history.json
            hist_file = listing_dir / "history.json"
            history = []
            if hist_file.exists():
                try:
                    history = json.loads(hist_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "delisted",
                "reason": reason,
                "previous_status": old_record.listing_status,
            })
            hist_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

        return SyncListingEvent(
            listing_id=lid,
            event_type="delisted",
            title=old_record.title,
            suburb=suburb,
            details=f"Delisted / Removed from portal ({reason})",
        )

    def _apply_update(self, listing_dir: Path, new_record: ListingRecord, fetch_res: Any, diff: Any, no_images: bool):
        """Write updated listing, metadata, and history into disk archive."""
        # Smart Image Download (Fast delta lookup)
        if not no_images and new_record.images:
            images_dir = listing_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            downloader = ImageDownloader(config=self.config)
            new_record.images = downloader.download_all(new_record.images, images_dir, existing_images_dir=images_dir)

        # Overwrite raw.html
        (listing_dir / "raw.html").write_bytes(fetch_res.content)

        # Overwrite listing.json
        listing_json_path = listing_dir / "listing.json"
        listing_json_path.write_text(new_record.model_dump_json(indent=2), encoding="utf-8")

        # Update metadata.json
        metadata = ArchiveMetadata(
            schema_version="1.0.0",
            listing_id=new_record.listing_id,
            source_url=fetch_res.url,
            archiver_version="1.0.0",
            fetch_mode="http",
            http_status=fetch_res.status_code,
            response_headers=fetch_res.headers,
            fetch_duration_sec=fetch_res.duration_sec,
            total_images_discovered=len(new_record.images),
            total_images_archived=sum(1 for img in new_record.images if img.local_filename is not None),
            content_fingerprint=new_record.content_fingerprint,
        )
        (listing_dir / "metadata.json").write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

        # Append to history.json
        hist_file = listing_dir / "history.json"
        history = []
        if hist_file.exists():
            try:
                history = json.loads(hist_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "scraped_update",
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
        })
        hist_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

        # Update checksums.json
        manifest_file = listing_dir / "checksums.json"
        if manifest_file.exists():
            try:
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest_data["files"]["listing.json"] = calculate_file_sha256(listing_json_path)
                manifest_data["files"]["raw.html"] = calculate_file_sha256(listing_dir / "raw.html")
                manifest_data["files"]["metadata.json"] = calculate_file_sha256(listing_dir / "metadata.json")
                manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
            except Exception:
                pass
