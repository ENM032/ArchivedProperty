"""
Tests for change detector and diffing between listing snapshots.
"""

from property_archiver.core.change_detector import ChangeDetector
from property_archiver.core.hasher import calculate_content_fingerprint
from property_archiver.models.listing import ListingRecord
from property_archiver.models.property_details import PriceInfo, PropertyFeatures


def test_change_detector_identical():
    rec1 = ListingRecord(
        listing_id="T1",
        canonical_url="https://www.privateproperty.co.za/1",
        price=PriceInfo(amount=2000000.0),
        features=PropertyFeatures(bedrooms=3.0, has_pool=True)
    )
    rec1.content_fingerprint = calculate_content_fingerprint(rec1.model_dump())

    rec2 = ListingRecord(
        listing_id="T1",
        canonical_url="https://www.privateproperty.co.za/1",
        price=PriceInfo(amount=2000000.0),
        features=PropertyFeatures(bedrooms=3.0, has_pool=True)
    )
    rec2.content_fingerprint = calculate_content_fingerprint(rec2.model_dump())

    diff = ChangeDetector.compare_records(rec1, rec2)
    assert diff.is_identical is True
    assert diff.price_changed is False


def test_change_detector_price_and_feature_change():
    rec1 = ListingRecord(
        listing_id="T1",
        canonical_url="https://www.privateproperty.co.za/1",
        price=PriceInfo(amount=2000000.0),
        features=PropertyFeatures(bedrooms=3.0, raw_features_list=["Pool", "Alarm"])
    )
    rec1.content_fingerprint = calculate_content_fingerprint(rec1.model_dump())

    rec2 = ListingRecord(
        listing_id="T1",
        canonical_url="https://www.privateproperty.co.za/1",
        price=PriceInfo(amount=1850000.0),
        features=PropertyFeatures(bedrooms=3.0, raw_features_list=["Pool", "Alarm", "Solar Inverter"])
    )
    rec2.content_fingerprint = calculate_content_fingerprint(rec2.model_dump())

    diff = ChangeDetector.compare_records(rec1, rec2)
    assert diff.is_identical is False
    assert diff.price_changed is True
    assert diff.old_price == 2000000.0
    assert diff.new_price == 1850000.0
    assert diff.price_diff == -150000.0
    assert "Solar Inverter" in diff.added_features
