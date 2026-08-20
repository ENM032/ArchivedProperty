"""
Tests for Pydantic model serialization, validation, and JSON export.
"""

from datetime import date, datetime
from property_archiver.models.listing import ListingRecord
from property_archiver.models.media import ImageRecord, VideoRecord
from property_archiver.models.property_details import LocationInfo, PriceInfo, PropertyFeatures


def test_listing_record_serialization():
    record = ListingRecord(
        schema_version="1.0.0",
        portal_name="privateproperty.co.za",
        listing_id="T1001",
        canonical_url="https://www.privateproperty.co.za/for-sale/listing/T1001",
        title="Modern Apartment",
        price=PriceInfo(amount=1500000.0, formatted_display="R 1 500 000"),
        location=LocationInfo(suburb="Sandton", city="Johannesburg"),
        features=PropertyFeatures(bedrooms=2.0, bathrooms=2.0, has_pool=True),
        images=[
            ImageRecord(
                order_index=0,
                original_url="https://images.pp.co.za/1.jpg",
                resolved_url="https://images.pp.co.za/1_high.jpg",
                is_hero=True
            )
        ]
    )

    json_str = record.model_dump_json()
    reloaded = ListingRecord.model_validate_json(json_str)

    assert reloaded.listing_id == "T1001"
    assert reloaded.price.amount == 1500000.0
    assert reloaded.features.has_pool is True
    assert len(reloaded.images) == 1
    assert reloaded.images[0].is_hero is True
