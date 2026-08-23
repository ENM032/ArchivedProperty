"""
Geographic hierarchy model and tree builder for South African real estate.
Structures archives into Province -> Area/City -> Suburb -> Listing.
"""

from dataclasses import dataclass, field
from typing import Any

from property_archiver.models.listing import ListingRecord


def clean_geo_name(name: str | None, default: str = "Unknown") -> str:
    """Normalize geographic names (strip whitespace, title case)."""
    if not name or not name.strip():
        return default
    cleaned = name.strip()
    # Normalize common abbreviations or separators
    cleaned = cleaned.replace("-", " ")
    return " ".join(word.capitalize() for word in cleaned.split())


@dataclass
class GeoNode:
    """A node in the geographic hierarchy tree (Province, Area, Suburb, or Listing)."""
    name: str
    level: str  # 'root', 'province', 'area', 'suburb', 'listing'
    children: dict[str, "GeoNode"] = field(default_factory=dict)
    listings: list[ListingRecord] = field(default_factory=list)
    total_listings: int = 0
    total_value_zar: float = 0.0
    avg_price_zar: float = 0.0
    active_count: int = 0
    under_offer_count: int = 0
    sold_count: int = 0

    def compute_aggregates(self) -> None:
        """Recursively calculate aggregate counts, values, and status ratios."""
        self.total_listings = len(self.listings)
        self.total_value_zar = sum(r.price.amount for r in self.listings if r.price.amount)
        self.active_count = sum(1 for r in self.listings if r.listing_status == "active" and not r.is_under_offer and not r.is_sold)
        self.under_offer_count = sum(1 for r in self.listings if r.listing_status == "under_offer" or r.is_under_offer)
        self.sold_count = sum(1 for r in self.listings if r.listing_status == "sold" or r.is_sold)

        for child in self.children.values():
            child.compute_aggregates()
            self.total_listings += child.total_listings
            self.total_value_zar += child.total_value_zar
            self.active_count += child.active_count
            self.under_offer_count += child.under_offer_count
            self.sold_count += child.sold_count

        if self.total_listings > 0 and self.total_value_zar > 0:
            self.avg_price_zar = self.total_value_zar / self.total_listings
        else:
            self.avg_price_zar = 0.0


class GeoHierarchyBuilder:
    """Builds and filters geographic hierarchy trees from listing collections."""

    @staticmethod
    def extract_geo_keys(record: ListingRecord) -> tuple[str, str, str]:
        """
        Extract (Province, Area/City, Suburb) from a listing record with fallback cascades.
        """
        loc = record.location

        # 1. Province
        province = clean_geo_name(loc.province, "Unassigned Province")

        # 2. Area / Region / City
        area = None
        if loc.region and loc.region.lower() != loc.suburb.lower() if loc.suburb else False:
            # Region often contains "Sandton" or "Midrand" or "Rivonia, Sandton"
            area = loc.region.split(",")[-1].strip()
        elif loc.city and loc.city.lower() != province.lower():
            area = loc.city
        elif loc.breadcrumbs and len(loc.breadcrumbs) >= 4:
            area = loc.breadcrumbs[3]  # [South Africa, Gauteng, Johannesburg, Sandton, Rivonia]

        area = clean_geo_name(area, loc.city or "General Area")

        # 3. Suburb
        suburb = None
        if loc.suburb:
            suburb = loc.suburb
        elif loc.street_address:
            suburb = loc.street_address
        elif loc.breadcrumbs and len(loc.breadcrumbs) >= 5:
            suburb = loc.breadcrumbs[4]

        suburb = clean_geo_name(suburb, "General Suburb")

        return province, area, suburb

    @staticmethod
    def build_tree(
        records: list[ListingRecord],
        filter_province: str | None = None,
        filter_area: str | None = None,
        filter_suburb: str | None = None,
        filter_status: str | None = None,
    ) -> GeoNode:
        """
        Build a complete hierarchical tree from a list of records with optional filters.
        """
        root = GeoNode(name="South Africa", level="root")

        for r in records:
            # Filter checks
            if filter_status and filter_status != "all":
                if filter_status == "active" and (r.listing_status != "active" or r.is_under_offer or r.is_sold):
                    continue
                elif filter_status == "under_offer" and (r.listing_status != "under_offer" and not r.is_under_offer):
                    continue
                elif filter_status == "sold" and (r.listing_status != "sold" and not r.is_sold):
                    continue

            prov, area, sub = GeoHierarchyBuilder.extract_geo_keys(r)

            if filter_province and filter_province.lower() not in prov.lower():
                continue
            if filter_area and filter_area.lower() not in area.lower():
                continue
            if filter_suburb and filter_suburb.lower() not in sub.lower():
                continue

            # Traverse / Create tree nodes
            if prov not in root.children:
                root.children[prov] = GeoNode(name=prov, level="province")
            prov_node = root.children[prov]

            if area not in prov_node.children:
                prov_node.children[area] = GeoNode(name=area, level="area")
            area_node = prov_node.children[area]

            if sub not in area_node.children:
                area_node.children[sub] = GeoNode(name=sub, level="suburb")
            sub_node = area_node.children[sub]

            sub_node.listings.append(r)

        root.compute_aggregates()
        return root
