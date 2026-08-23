"""
Tests for GeoHierarchyBuilder and geographic sorting.
"""

from property_archiver.core.hierarchy import GeoHierarchyBuilder, clean_geo_name
from property_archiver.models.listing import ListingRecord
from property_archiver.models.property_details import LocationInfo, PriceInfo


def test_clean_geo_name():
    assert clean_geo_name("gauteng") == "Gauteng"
    assert clean_geo_name("kyalami-hills") == "Kyalami Hills"
    assert clean_geo_name("  sandton  ") == "Sandton"
    assert clean_geo_name(None, "Default") == "Default"


def test_extract_geo_keys():
    rec = ListingRecord(
        listing_id="T1",
        canonical_url="https://test.com",
        location=LocationInfo(
            province="Gauteng",
            city="Johannesburg",
            region="Rivonia, Sandton",
            suburb="Rivonia",
            breadcrumbs=["South Africa", "Gauteng", "Johannesburg", "Sandton", "Rivonia"]
        )
    )
    prov, area, sub = GeoHierarchyBuilder.extract_geo_keys(rec)
    assert prov == "Gauteng"
    assert "Sandton" in area
    assert sub == "Rivonia"


def test_build_tree_and_aggregates():
    rec1 = ListingRecord(
        listing_id="T1",
        canonical_url="https://test.com/1",
        price=PriceInfo(amount=4000000.0),
        location=LocationInfo(province="Gauteng", city="Johannesburg", region="Sandton", suburb="Rivonia"),
        listing_status="active"
    )
    rec2 = ListingRecord(
        listing_id="T2",
        canonical_url="https://test.com/2",
        price=PriceInfo(amount=2000000.0),
        location=LocationInfo(province="Gauteng", city="Johannesburg", region="Midrand", suburb="Kyalami Hills"),
        listing_status="under_offer",
        is_under_offer=True
    )
    rec3 = ListingRecord(
        listing_id="T3",
        canonical_url="https://test.com/3",
        price=PriceInfo(amount=6000000.0),
        location=LocationInfo(province="Western Cape", city="Cape Town", region="Atlantic Seaboard", suburb="Camps Bay"),
        listing_status="sold",
        is_sold=True
    )

    tree = GeoHierarchyBuilder.build_tree([rec1, rec2, rec3])
    assert tree.total_listings == 3
    assert tree.total_value_zar == 12000000.0
    assert tree.avg_price_zar == 4000000.0
    assert tree.active_count == 1
    assert tree.under_offer_count == 1
    assert tree.sold_count == 1

    assert "Gauteng" in tree.children
    assert "Western Cape" in tree.children

    gauteng = tree.children["Gauteng"]
    assert gauteng.total_listings == 2
    assert gauteng.total_value_zar == 6000000.0

    # Filter test
    filtered = GeoHierarchyBuilder.build_tree([rec1, rec2, rec3], filter_province="Gauteng")
    assert filtered.total_listings == 2
    assert "Western Cape" not in filtered.children
