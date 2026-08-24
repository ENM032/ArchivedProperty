"""
Route handlers for geographic hierarchy computation and serializing.
"""

from http import HTTPStatus
from pathlib import Path
from typing import Any

from property_archiver.core.hierarchy import GeoHierarchyBuilder, GeoNode
from property_archiver.export.exporter import PortfolioExporter


def serialize_geo_node(node: GeoNode) -> dict[str, Any]:
    """Serialize a GeoNode tree to a clean JSON-friendly dict."""
    return {
        "name": node.name,
        "level": node.level,
        "total_listings": node.total_listings,
        "total_value_zar": node.total_value_zar,
        "avg_price_zar": node.avg_price_zar,
        "active_count": node.active_count,
        "under_offer_count": node.under_offer_count,
        "sold_count": node.sold_count,
        "children": {k: serialize_geo_node(v) for k, v in node.children.items()},
        "listings": [
            {
                "listing_id": r.listing_id,
                "portal_name": r.portal_name,
                "title": r.title,
                "listing_type": getattr(r, "listing_type", "for_sale"),
                "property_type": r.property_type,
                "listing_status": r.listing_status,
                "is_under_offer": r.is_under_offer,
                "is_sold": r.is_sold,
                "status_badges": r.status_badges,
                "price": r.price.model_dump(),
                "location": r.location.model_dump(),
                "features": r.features.model_dump(),
                "erf_size_m2": r.erf_size_m2,
                "floor_size_m2": r.floor_size_m2,
                "images_count": len(r.images),
                "hero_image_url": f"/api/listings/{r.listing_id}/image/{r.images[0].local_filename}" if (r.images and r.images[0].local_filename) else None,
                "extracted_at": r.extracted_at.isoformat(),
            }
            for r in node.listings
        ]
    }


def handle_get_hierarchy(archive_dir: Path, query: dict[str, list[str]]) -> tuple[dict[str, Any], HTTPStatus]:
    """Compute and return hierarchical tree with aggregate regional metrics."""
    records = PortfolioExporter.load_all_listings(archive_dir)
    prov = query.get("province", [None])[0]
    area = query.get("area", [None])[0]
    sub = query.get("suburb", [None])[0]
    status = query.get("status", ["all"])[0]

    tree_root = GeoHierarchyBuilder.build_tree(
        records=records,
        filter_province=prov,
        filter_area=area,
        filter_suburb=sub,
        filter_status=status,
    )
    return serialize_geo_node(tree_root), HTTPStatus.OK
