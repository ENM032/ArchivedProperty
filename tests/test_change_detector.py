"""
Tests for change detector and diffing between listing snapshots including status transitions.
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
    rec1.content_fingerprint = calculate_content_fingerprint(rec1.model_dump(mode="json"))

    rec2 = ListingRecord(
        listing_id="T1",
        canonical_url="https://www.privateproperty.co.za/1",
        price=PriceInfo(amount=2000000.0),
        features=PropertyFeatures(bedrooms=3.0, has_pool=True)
    )
    rec2.content_fingerprint = calculate_content_fingerprint(rec2.model_dump(mode="json"))

    diff = ChangeDetector.compare_records(rec1, rec2)
    assert diff.is_identical is True
    assert diff.price_changed is False
    assert diff.status_changed is False


def test_change_detector_status_transition_under_offer_and_sold():
    rec1 = ListingRecord(
        listing_id="T1",
        canonical_url="https://www.privateproperty.co.za/1",
        listing_status="active",
        status_badges=[]
    )
    rec1.content_fingerprint = calculate_content_fingerprint(rec1.model_dump(mode="json"))

    rec2 = ListingRecord(
        listing_id="T1",
        canonical_url="https://www.privateproperty.co.za/1",
        listing_status="under_offer",
        status_badges=["Under Offer"],
        is_under_offer=True
    )
    rec2.content_fingerprint = calculate_content_fingerprint(rec2.model_dump(mode="json"))

    diff = ChangeDetector.compare_records(rec1, rec2)
    assert diff.is_identical is False
    assert diff.status_changed is True
    assert diff.old_status == "active"
    assert diff.new_status == "under_offer"
    assert "Under Offer" in diff.badges_added
