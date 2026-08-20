"""
Tests for PrivateProperty extractor on full test fixture, missing data, and malformed HTML.
"""

from pathlib import Path
import pytest

from property_archiver.extractors.private_property import PrivatePropertyExtractor


def test_private_property_full_extraction(sample_html_content: str, sample_url: str):
    extractor = PrivatePropertyExtractor()
    assert extractor.can_handle(sample_url) is True

    listing = extractor.extract(sample_html_content, sample_url)

    # 1. Listing ID & Core Attributes
    assert listing.listing_id == "T4710876"
    assert listing.portal_name == "privateproperty.co.za"
    assert listing.property_type in ("House", "4 Bedroom House")
    assert listing.title == "4 Bedroom House in Rivonia"
    assert listing.listing_date is not None
    assert str(listing.listing_date) == "2024-07-15"

    # 2. Price
    assert listing.price.amount == 4999000.0
    assert listing.price.formatted_display == "R 4 999 000"
    assert listing.price.rates_and_taxes_monthly == 2495.0

    # 3. Location & GPS
    assert listing.location.street_address == "13 Winston Avenue"
    assert listing.location.suburb == "Rivonia"
    assert listing.location.city == "Johannesburg"
    assert listing.location.province == "Gauteng"
    assert listing.location.country == "South Africa"
    assert listing.location.latitude == -26.043712
    assert listing.location.longitude == 28.055459
    assert len(listing.location.breadcrumbs) >= 5

    # 4. Sizes & Specs
    assert listing.erf_size_m2 == 1983.0
    assert listing.features.bedrooms == 4.0
    assert listing.features.bathrooms == 3.5
    assert listing.features.en_suites == 2.0
    assert listing.features.lounges == 3.0
    assert listing.features.garages == 3.0

    # 5. Boolean Amenities
    assert listing.features.has_pool is True
    assert listing.features.has_alarm is True
    assert listing.features.has_access_gate is True
    assert listing.features.has_staff_quarters is True
    assert listing.features.has_built_in_cupboards is True
    assert listing.features.has_patio is True
    assert listing.features.has_garden is True
    assert listing.features.has_kitchen is True
    assert listing.features.has_fireplace is True
    assert listing.features.has_aircon is True
    assert len(listing.features.raw_features_list) >= 20

    # 6. Description & Video
    assert listing.description is not None
    assert "Michael Sutton Design" in listing.description
    assert len(listing.videos) >= 1
    assert "youtube" in listing.videos[0].url.lower()

    # 7. Agent & Agency
    assert listing.agent is not None
    assert listing.agent.agent_name == "Alistair Dempster"

    # 8. All 56 Gallery Images
    assert len(listing.images) == 56
    hero_image = listing.images[0]
    assert hero_image.is_hero is True
    assert "1600/1066" in hero_image.resolved_url
    assert hero_image.order_index == 0
    assert "photo number 1" in (hero_image.alt_text or "")

    last_image = listing.images[55]
    assert last_image.order_index == 55
    assert "photo number 56" in (last_image.alt_text or "")

    # 9. Fingerprint & Raw Preservation
    assert listing.content_fingerprint is not None
    assert len(listing.raw_json_ld) >= 2
    assert len(listing.open_graph) >= 1


def test_extraction_malformed_html(malformed_html_content: str):
    extractor = PrivatePropertyExtractor()
    listing = extractor.extract(malformed_html_content, "https://www.privateproperty.co.za/for-sale/test/T999999")

    assert listing.listing_id == "T999999"
    assert listing.title == "Just a Title Without Data"
    assert listing.price.amount is None
    assert listing.erf_size_m2 is None
    assert len(listing.images) == 0
    assert listing.content_fingerprint is not None
