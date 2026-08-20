"""
Diffing and change detection engine across listing snapshots.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from property_archiver.models.listing import ListingRecord
from property_archiver.storage.reader import ArchiveReader


@dataclass
class ListingDiff:
    """Detailed record of changes between two listing versions."""
    listing_id: str
    is_identical: bool
    price_changed: bool = False
    old_price: float | None = None
    new_price: float | None = None
    price_diff: float | None = None
    status_changed: bool = False
    old_status: str | None = None
    new_status: str | None = None
    badges_added: list[str] = field(default_factory=list)
    badges_removed: list[str] = field(default_factory=list)
    spec_changes: list[str] = field(default_factory=list)
    added_features: list[str] = field(default_factory=list)
    removed_features: list[str] = field(default_factory=list)
    images_count_change: tuple[int, int] = (0, 0)
    description_changed: bool = False


class ChangeDetector:
    """Compares two listing records or archive directories for meaningful updates."""

    @staticmethod
    def compare_records(old: ListingRecord, new: ListingRecord) -> ListingDiff:
        """Compare two ListingRecord instances."""
        diff = ListingDiff(
            listing_id=old.listing_id,
            is_identical=(old.content_fingerprint == new.content_fingerprint)
        )

        # Price comparison
        if old.price.amount != new.price.amount:
            diff.price_changed = True
            diff.old_price = old.price.amount
            diff.new_price = new.price.amount
            if old.price.amount is not None and new.price.amount is not None:
                diff.price_diff = new.price.amount - old.price.amount

        # Status & Lifecycle comparison
        if old.listing_status != new.listing_status:
            diff.status_changed = True
            diff.old_status = old.listing_status
            diff.new_status = new.listing_status

        # Badges comparison
        old_badges = set(old.status_badges)
        new_badges = set(new.status_badges)
        diff.badges_added = sorted(list(new_badges - old_badges))
        diff.badges_removed = sorted(list(old_badges - new_badges))

        # Specification comparison
        if old.features.bedrooms != new.features.bedrooms:
            diff.spec_changes.append(f"Bedrooms: {old.features.bedrooms} -> {new.features.bedrooms}")
        if old.features.bathrooms != new.features.bathrooms:
            diff.spec_changes.append(f"Bathrooms: {old.features.bathrooms} -> {new.features.bathrooms}")
        if old.features.garages != new.features.garages:
            diff.spec_changes.append(f"Garages: {old.features.garages} -> {new.features.garages}")
        if old.erf_size_m2 != new.erf_size_m2:
            diff.spec_changes.append(f"Erf size: {old.erf_size_m2}m² -> {new.erf_size_m2}m²")

        # Features comparison
        old_feats = set(old.features.raw_features_list)
        new_feats = set(new.features.raw_features_list)
        diff.added_features = sorted(list(new_feats - old_feats))
        diff.removed_features = sorted(list(old_feats - new_feats))

        # Media comparison
        diff.images_count_change = (len(old.images), len(new.images))

        # Description comparison
        if (old.description or "").strip() != (new.description or "").strip():
            diff.description_changed = True

        return diff

    @staticmethod
    def compare_archives(archive_path_a: Path | str, archive_path_b: Path | str) -> ListingDiff:
        """Compare two archived listings on disk."""
        rec_a = ArchiveReader.load_listing(archive_path_a)
        rec_b = ArchiveReader.load_listing(archive_path_b)
        return ChangeDetector.compare_records(rec_a, rec_b)
