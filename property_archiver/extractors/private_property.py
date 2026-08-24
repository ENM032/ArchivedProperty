"""
Production extractor for Private Property South Africa (privateproperty.co.za).

Implements a resilient multi-tier extraction pipeline:
1. Deobfuscation of embedded inline listing state (reconstructing full 56-image gallery, primary and co-agents)
2. Status and badge lifecycle analysis (detecting 'Under Offer', 'Sold', 'Reduced', 'On Show')
3. JSON-LD parsing with recursive @graph support (Breadcrumbs, Residence, Schema.org)
4. Land size normalization (supporting hectares 'ha' and m²)
5. Semantic DOM extraction (Details, Features, Prices, Video iframes)
6. Fallback DOM and regex media discovery
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from property_archiver.core.exceptions import ExtractionError
from property_archiver.core.hasher import calculate_content_fingerprint
from property_archiver.extractors.base import BaseExtractor
from property_archiver.models.listing import ListingRecord
from property_archiver.models.media import ImageRecord, VideoRecord
from property_archiver.models.property_details import (
    AgentInfo,
    LocationInfo,
    PriceInfo,
    PropertyFeatures,
)

logger = logging.getLogger(__name__)

# Regular expressions for data parsing
PRICE_CLEAN_RE = re.compile(r"[^0-9.]")
LISTING_ID_RE = re.compile(r"/(T\d+|\d+)(?:[/?#]|$)")
SIZE_NUM_RE = re.compile(r"([0-9\s\xa0\u202f]+(?:[.,]\d+)?)")
PP_IMG_HASH_RE = re.compile(r"images\.(?:pp|privateproperty)\.co\.za/listing/(\d+)/([A-Za-z0-9]+)")


class PrivatePropertyExtractor(BaseExtractor):
    """Extractor for Private Property South Africa listings."""

    PORTAL_NAME = "privateproperty.co.za"

    def can_handle(self, url_or_html: str) -> bool:
        """Check if URL or HTML belongs to Private Property."""
        if "privateproperty.co.za" in url_or_html.lower():
            return True
        if "images.pp.co.za" in url_or_html:
            return True
        return False

    def extract(self, html: str, url: str) -> ListingRecord:
        """Extract all publicly available listing information from HTML."""
        if not html:
            raise ExtractionError("Cannot extract from empty HTML document.")

        soup = BeautifulSoup(html, "html.parser")

        # Step 1: Extract Listing ID
        listing_id = self._extract_listing_id(url, soup)

        # Step 2: Attempt Deobfuscation of Embedded Listing State Bundle
        bundle_data = self._extract_embedded_bundle(soup)
        bundle_params = bundle_data.get("bundleParams", {}) if bundle_data else {}

        # Step 3: Extract JSON-LD metadata (including recursive @graph)
        raw_json_ld, json_ld_residence, breadcrumbs = self._extract_json_ld(soup)

        # Step 4: Extract Meta / OpenGraph tags
        meta_tags, og_tags = self._extract_meta_tags(soup)

        # Step 5: Extract Status, Badges & Lifecycle ('Under Offer', 'Sold', 'Reduced', 'On Show')
        status, badges, is_under_offer, is_sold, is_on_show, is_reduced, on_show_details = self._extract_status(
            soup, og_tags, bundle_params
        )

        # Step 6: Extract Location & Geo
        location = self._extract_location(url, soup, json_ld_residence, breadcrumbs, og_tags, bundle_params)

        # Step 7: Extract Pricing details
        price = self._extract_price(soup, og_tags, bundle_params)

        # Step 8: Extract Property details, sizes, and hectare conversions
        prop_type, listing_date, erf_size, land_size_raw, floor_size = self._extract_details(
            soup, json_ld_residence, bundle_params
        )

        # Detect transaction type (For Sale / Buy vs To Rent)
        listing_type = "for_sale"
        url_lower = url.lower()
        if "to-rent" in url_lower or "for-rent" in url_lower or "/rent/" in url_lower:
            listing_type = "to_rent"
        elif bundle_params.get("listingType") and "rent" in str(bundle_params.get("listingType")).lower():
            listing_type = "to_rent"

        # Step 9: Extract Features & Amenities
        features = self._extract_features(soup, json_ld_residence)

        # Step 10: Extract Multi-Agent & Agency details (primary agent + co-agents)
        primary_agent, co_agents = self._extract_agents(soup, bundle_params)

        # Step 11: Extract Title & Description
        title = self._extract_title(soup, og_tags, bundle_params)
        description = self._extract_description(soup, og_tags)

        # Step 12: Extract Media (All Gallery Images & Videos)
        images = self._extract_images(html, soup, listing_id, bundle_params)
        videos = self._extract_videos(soup, bundle_params)

        # Build normalized ListingRecord
        record = ListingRecord(
            schema_version="1.0.0",
            portal_name=self.PORTAL_NAME,
            listing_id=listing_id,
            canonical_url=url,
            extracted_at=datetime.now(timezone.utc),
            title=title,
            listing_type=listing_type,
            property_type=prop_type,
            listing_status=status,
            status_badges=badges,
            is_under_offer=is_under_offer,
            is_sold=is_sold,
            is_on_show=is_on_show,
            is_price_reduced=is_reduced,
            on_show_details=on_show_details,
            listing_date=listing_date,
            description=description,
            erf_size_m2=erf_size,
            land_size_raw=land_size_raw,
            floor_size_m2=floor_size,
            price=price,
            location=location,
            features=features,
            agent=primary_agent,
            co_agents=co_agents,
            images=images,
            videos=videos,
            raw_json_ld=raw_json_ld,
            open_graph=og_tags,
            meta_tags=meta_tags,
        )

        # Compute content fingerprint
        record.content_fingerprint = calculate_content_fingerprint(record.model_dump(mode="json"))
        return record

    def _extract_embedded_bundle(self, soup: BeautifulSoup) -> dict[str, Any] | None:
        """
        Private Property encodes complete listing details (including all 56 photos and co-agent contacts)
        into an obfuscated inline JavaScript script that reconstructs JSON via token array substitution:
        window[...] = JSON.parse(Y.map($ => D[$]).join(''))
        Natively deobfuscates this payload in Python.
        """
        for s in soup.find_all("script"):
            text = s.string or s.get_text() or ""
            if "JSON.parse" in text and ("map(" in text or "join(" in text):
                try:
                    d_match = re.search(r"const\s+[A-Za-z0-9_$]+\s*=\s*(\[.*?\]);", text, re.DOTALL)
                    if not d_match:
                        continue
                    d_tokens = json.loads(d_match.group(1))

                    y_match = re.search(r"\[([0-9,\s]+)\]\s*;\s*window", text)
                    if y_match:
                        y_indices = [int(x.strip()) for x in y_match.group(1).split(",") if x.strip()]
                    else:
                        int_lists = re.findall(r"\[([0-9]{1,4}(?:\s*,\s*[0-9]{1,4}){50,})\]", text)
                        if not int_lists:
                            continue
                        y_indices = [int(x.strip()) for x in int_lists[0].split(",") if x.strip()]

                    reconstructed = "".join(d_tokens[i] for i in y_indices)
                    data = json.loads(reconstructed)
                    if isinstance(data, dict) and ("bundleParams" in data or "galleryPhotos" in data):
                        return data
                except Exception as exc:
                    logger.debug("Failed parsing obfuscated bundle script: %s", exc)

        return None

    def _extract_status(
        self, soup: BeautifulSoup, og_tags: dict[str, str], bundle_params: dict[str, Any]
    ) -> tuple[str, list[str], bool, bool, bool, bool, dict[str, Any] | None]:
        """Extract listing lifecycle status and visual badges."""
        status = "active"
        badges: list[str] = []
        is_under_offer = False
        is_sold = False
        is_on_show = False
        is_reduced = False
        on_show_details = None

        if bundle_params:
            if bundle_params.get("isUnderOffer"):
                is_under_offer = True
                status = "under_offer"
                badges.append("Under Offer")

            if bundle_params.get("isSold") or bundle_params.get("listingStatus") == "Sold":
                is_sold = True
                status = "sold"
                badges.append("Sold")

            if bundle_params.get("isOnShow") or bundle_params.get("onShowDetails"):
                is_on_show = True
                badges.append("On Show")
                if isinstance(bundle_params.get("onShowDetails"), dict):
                    on_show_details = bundle_params["onShowDetails"]

            if bundle_params.get("isReduced") or bundle_params.get("isPriceReduced"):
                is_reduced = True
                badges.append("Reduced")

            raw_badges = bundle_params.get("badges") or bundle_params.get("tags") or []
            if isinstance(raw_badges, list):
                for b in raw_badges:
                    b_text = b.get("text") if isinstance(b, dict) else str(b)
                    if b_text and b_text not in badges:
                        badges.append(b_text)

        badge_elements = soup.find_all(
            class_=re.compile(r"badge|banner|ribbon|tag|label|listing-banners|listing-details__badge", re.I)
        )
        for el in badge_elements:
            text = el.get_text(" ", strip=True)
            if not text or len(text) > 40:
                continue

            text_clean = text.strip()
            text_lower = text_clean.lower()

            if "under offer" in text_lower or "offer pending" in text_lower or "under contract" in text_lower:
                is_under_offer = True
                status = "under_offer"
                if "Under Offer" not in badges:
                    badges.append("Under Offer")
            elif "sold" in text_lower:
                is_sold = True
                status = "sold"
                if "Sold" not in badges:
                    badges.append("Sold")
            elif "on show" in text_lower or "show house" in text_lower:
                is_on_show = True
                if "On Show" not in badges:
                    badges.append("On Show")
            elif "reduced" in text_lower or "price drop" in text_lower:
                is_reduced = True
                if "Reduced" not in badges:
                    badges.append("Reduced")
            elif "auction" in text_lower:
                if "Auction" not in badges:
                    badges.append("Auction")
            elif "withdrawn" in text_lower or "off market" in text_lower:
                status = "withdrawn"
                if "Withdrawn" not in badges:
                    badges.append("Withdrawn")

        og_title = og_tags.get("og:title", "")
        if "under offer" in og_title.lower():
            is_under_offer = True
            status = "under_offer"
        elif "sold" in og_title.lower():
            is_sold = True
            status = "sold"

        badges = list(dict.fromkeys(badges))
        return status, badges, is_under_offer, is_sold, is_on_show, is_reduced, on_show_details

    def _extract_listing_id(self, url: str, soup: BeautifulSoup) -> str:
        """Extract listing ID from URL path or fallback to DOM."""
        match = LISTING_ID_RE.search(url)
        if match:
            return match.group(1)

        for item in soup.find_all(class_=re.compile(r"property-details__list-item|breadcrumb", re.I)):
            text = item.get_text(" ", strip=True)
            id_match = re.search(r"Listing number\s*(T\d+|\d+)", text, re.I)
            if id_match:
                return id_match.group(1)

        parsed = urlparse(url)
        segments = [s for s in parsed.path.split("/") if s]
        if segments:
            return segments[-1]

        return "unknown_listing"

    def _extract_json_ld(self, soup: BeautifulSoup) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
        """Parse all schema.org JSON-LD blocks including recursive @graph unpack."""
        raw_blocks: list[dict[str, Any]] = []
        residence_block: dict[str, Any] = {}
        breadcrumbs: list[str] = []

        def _process_item(data: dict[str, Any]):
            nonlocal residence_block, breadcrumbs
            data_type = data.get("@type")
            if data_type in ("Residence", "SingleFamilyResidence", "RealEstateListing", "House", "Place"):
                residence_block = data
            elif data_type == "BreadcrumbList":
                items = data.get("itemListElement", [])
                for it in items:
                    if isinstance(it, dict):
                        item_obj = it.get("item", {})
                        name = item_obj.get("name") if isinstance(item_obj, dict) else it.get("name")
                        if name:
                            breadcrumbs.append(str(name).strip())

            if "@graph" in data and isinstance(data["@graph"], list):
                for sub in data["@graph"]:
                    if isinstance(sub, dict):
                        _process_item(sub)

        for tag in soup.find_all("script", type="application/ld+json"):
            if not tag.string:
                continue
            try:
                data = json.loads(tag.string.strip())
                if isinstance(data, dict):
                    raw_blocks.append(data)
                    _process_item(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            raw_blocks.append(item)
                            _process_item(item)
            except Exception as exc:
                logger.debug("Failed parsing JSON-LD script block: %s", exc)

        return raw_blocks, residence_block, breadcrumbs

    def _extract_meta_tags(self, soup: BeautifulSoup) -> tuple[dict[str, str], dict[str, str]]:
        """Extract standard and OpenGraph metadata."""
        meta_tags: dict[str, str] = {}
        og_tags: dict[str, str] = {}

        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property") or ""
            content = meta.get("content") or ""
            if not name or not content:
                continue
            name_clean = name.strip()
            content_clean = content.strip()

            meta_tags[name_clean] = content_clean
            if name_clean.startswith("og:"):
                og_tags[name_clean] = content_clean

        return meta_tags, og_tags

    def _extract_location(
        self,
        url: str,
        soup: BeautifulSoup,
        json_ld: dict[str, Any],
        breadcrumbs: list[str],
        og_tags: dict[str, str],
        bundle_params: dict[str, Any],
    ) -> LocationInfo:
        """Extract address, suburb, city, province, and GPS coordinates."""
        loc = LocationInfo(breadcrumbs=breadcrumbs)

        address_dict = json_ld.get("address", {}) if isinstance(json_ld.get("address"), dict) else {}
        loc.street_address = address_dict.get("streetAddress")
        loc.region = address_dict.get("addressLocality")
        loc.province = address_dict.get("addressRegion")

        geo_dict = json_ld.get("geo", {}) if isinstance(json_ld.get("geo"), dict) else {}
        if geo_dict.get("@type") == "GeoCoordinates":
            try:
                loc.latitude = float(geo_dict.get("latitude")) if geo_dict.get("latitude") is not None else None
                loc.longitude = float(geo_dict.get("longitude")) if geo_dict.get("longitude") is not None else None
            except (ValueError, TypeError):
                pass
        
        map_coords = bundle_params.get("mapCoOrdinates", {})
        if isinstance(map_coords, dict) and loc.latitude is None:
            try:
                loc.latitude = float(map_coords.get("latitude")) if map_coords.get("latitude") is not None else None
                loc.longitude = float(map_coords.get("longitude")) if map_coords.get("longitude") is not None else None
            except (ValueError, TypeError):
                pass

        if bundle_params.get("suburbName") and not loc.suburb:
            loc.suburb = bundle_params["suburbName"]

        if breadcrumbs:
            if len(breadcrumbs) >= 2 and not loc.province:
                loc.province = breadcrumbs[1]
            if len(breadcrumbs) >= 3 and not loc.city:
                loc.city = breadcrumbs[2]
            if len(breadcrumbs) >= 4 and not loc.region:
                loc.region = breadcrumbs[3]
            if len(breadcrumbs) >= 5 and not loc.suburb:
                loc.suburb = breadcrumbs[4]

        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 6:
            if not loc.province:
                loc.province = parts[1].replace("-", " ").title()
            if not loc.city:
                loc.city = parts[2].replace("-", " ").title()
            if not loc.region:
                loc.region = parts[3].replace("-", " ").title()
            if not loc.suburb:
                loc.suburb = parts[4].replace("-", " ").title()
            if not loc.street_address:
                loc.street_address = parts[5].replace("-", " ").title()

        return loc

    def _extract_price(
        self, soup: BeautifulSoup, og_tags: dict[str, str], bundle_params: dict[str, Any]
    ) -> PriceInfo:
        """Extract asking price, rates, taxes, and monthly levies."""
        price_info = PriceInfo()

        price_disp = bundle_params.get("priceDisplay", {})
        if isinstance(price_disp, dict):
            raw_p = price_disp.get("price")
            if raw_p:
                clean_p = re.sub(r"[^0-9.]", "", str(raw_p).replace("\xa0", "").replace("\u202f", ""))
                try:
                    price_info.amount = float(clean_p)
                    price_info.formatted_display = f"R {int(price_info.amount):,}".replace(",", " ")
                except ValueError:
                    pass

        if price_info.amount is None:
            for el in soup.find_all(class_=re.compile(r"price|listing-details__price|details-page-top", re.I)):
                text = el.get_text(" ", strip=True)
                match = re.search(r"R\s*([0-9\s\xa0\u202f,]+)", text)
                if match:
                    price_str = match.group(1).replace(" ", "").replace("\xa0", "").replace("\u202f", "").replace(",", "")
                    try:
                        price_info.amount = float(price_str)
                        price_info.formatted_display = f"R {int(price_info.amount):,}".replace(",", " ")
                        break
                    except ValueError:
                        pass

        for item in soup.find_all(class_=re.compile(r"property-details__list-item", re.I)):
            text = item.get_text(" ", strip=True)
            if "rates and taxes" in text.lower():
                val_match = re.search(r"R\s*([0-9\s\xa0\u202f,]+)", text, re.I)
                if val_match:
                    num_str = val_match.group(1).replace(" ", "").replace("\xa0", "").replace("\u202f", "").replace(",", "")
                    try:
                        price_info.rates_and_taxes_monthly = float(num_str)
                    except ValueError:
                        pass
            elif "levies" in text.lower() or "levy" in text.lower():
                val_match = re.search(r"R\s*([0-9\s\xa0\u202f,]+)", text, re.I)
                if val_match:
                    num_str = val_match.group(1).replace(" ", "").replace("\xa0", "").replace("\u202f", "").replace(",", "")
                    try:
                        price_info.levies_monthly = float(num_str)
                    except ValueError:
                        pass

        return price_info

    def _extract_details(
        self, soup: BeautifulSoup, json_ld: dict[str, Any], bundle_params: dict[str, Any]
    ) -> tuple[str | None, Any | None, float | None, str | None, float | None]:
        """
        Extract property type, listing date, erf size (with hectare conversion), raw land size, and floor size.
        """
        property_type: str | None = None
        listing_date = None
        erf_size_m2: float | None = None
        land_size_raw: str | None = None
        floor_size_m2: float | None = None

        for item in soup.find_all(class_=re.compile(r"property-details__list-item", re.I)):
            text = item.get_text(" ", strip=True)
            text_lower = text.lower()

            if "property type" in text_lower:
                val_elem = item.find(class_=re.compile(r"property-details__value", re.I))
                if val_elem:
                    property_type = val_elem.get_text(strip=True)
                else:
                    property_type = text.replace("Property type", "").strip()

            elif "listing date" in text_lower:
                val_elem = item.find(class_=re.compile(r"property-details__value", re.I))
                date_str = val_elem.get_text(strip=True) if val_elem else text.replace("Listing date", "").strip()
                try:
                    parsed_dt = date_parser.parse(date_str)
                    listing_date = parsed_dt.date()
                except Exception:
                    pass

            elif "land size" in text_lower or "erf size" in text_lower:
                val_elem = item.find(class_=re.compile(r"property-details__value", re.I))
                size_str = val_elem.get_text(strip=True) if val_elem else text
                land_size_raw = size_str.strip()

                # Check for hectares vs square meters
                match = SIZE_NUM_RE.search(size_str.replace("\xa0", "").replace("\u202f", "").replace(" ", "").replace(",", "."))
                if match:
                    try:
                        raw_val = float(match.group(1))
                        if "ha" in size_str.lower() or "hectare" in size_str.lower():
                            erf_size_m2 = raw_val * 10000.0
                        else:
                            erf_size_m2 = raw_val
                    except ValueError:
                        pass

            elif "floor size" in text_lower or "building size" in text_lower:
                val_elem = item.find(class_=re.compile(r"property-details__value", re.I))
                size_str = val_elem.get_text(strip=True) if val_elem else text
                match = SIZE_NUM_RE.search(size_str.replace("\xa0", "").replace("\u202f", "").replace(" ", "").replace(",", "."))
                if match:
                    try:
                        floor_size_m2 = float(match.group(1))
                    except ValueError:
                        pass

        if not property_type and bundle_params.get("propertyType"):
            property_type = bundle_params["propertyType"]

        if not property_type and json_ld.get("@type"):
            ld_type = json_ld.get("@type")
            if ld_type in ("SingleFamilyResidence", "Residence", "House"):
                property_type = "House"

        return property_type, listing_date, erf_size_m2, land_size_raw, floor_size_m2

    def _extract_features(self, soup: BeautifulSoup, json_ld: dict[str, Any]) -> PropertyFeatures:
        """Extract structured amenities, counts, and boolean feature flags."""
        features = PropertyFeatures()

        add_props = json_ld.get("additionalProperty", [])
        if isinstance(add_props, list):
            for prop in add_props:
                if isinstance(prop, dict):
                    name = str(prop.get("name", "")).strip().lower()
                    val_str = str(prop.get("value", "")).strip()
                    try:
                        val_float = float(val_str)
                        if "bedroom" in name:
                            features.bedrooms = val_float
                        elif "bathroom" in name:
                            features.bathrooms = val_float
                        elif "garage" in name:
                            features.garages = val_float
                    except ValueError:
                        pass

        for item in soup.find_all(class_=re.compile(r"property-features__list-item", re.I)):
            text = item.get_text(" ", strip=True)
            if not text:
                continue

            features.raw_features_list.append(text)
            text_lower = text.lower()

            val_span = item.find(class_=re.compile(r"property-features__value", re.I))
            val_num: float | None = None
            if val_span:
                try:
                    val_num = float(val_span.get_text(strip=True))
                except ValueError:
                    pass

            if "bedroom" in text_lower:
                features.bedrooms = val_num if val_num is not None else features.bedrooms or 1.0
            elif "bathroom" in text_lower:
                features.bathrooms = val_num if val_num is not None else features.bathrooms or 1.0
            elif "en-suite" in text_lower or "ensuite" in text_lower:
                features.en_suites = val_num if val_num is not None else 1.0
            elif "lounge" in text_lower:
                features.lounges = val_num if val_num is not None else 1.0
            elif "dining" in text_lower:
                features.dining_rooms = val_num if val_num is not None else 1.0
            elif "garage" in text_lower:
                features.garages = val_num if val_num is not None else 1.0
            elif "pool" in text_lower:
                features.has_pool = True
            elif "garden" in text_lower:
                features.has_garden = True
            elif "security post" in text_lower or "guard" in text_lower:
                features.has_security_post = True
            elif "access gate" in text_lower:
                features.has_access_gate = True
            elif "alarm" in text_lower:
                features.has_alarm = True
            elif "intercom" in text_lower:
                features.has_intercom = True
            elif "fence" in text_lower or "fenced" in text_lower:
                features.has_fencing = True
            elif "staff" in text_lower or "domestic" in text_lower:
                features.has_staff_quarters = True
            elif "patio" in text_lower:
                features.has_patio = True
            elif "balcony" in text_lower:
                features.has_balcony = True
            elif "built in cupboard" in text_lower or "bic" in text_lower:
                features.has_built_in_cupboards = True
            elif "walk in closet" in text_lower:
                features.has_walk_in_closet = True
            elif "scullery" in text_lower:
                features.has_scullery = True
            elif "laundry" in text_lower:
                features.has_laundry = True
            elif "entrance hall" in text_lower:
                features.has_entrance_hall = True
            elif "kitchen" in text_lower:
                features.has_kitchen = True
                if val_num is not None:
                    features.kitchens = val_num
            elif "tv room" in text_lower or "family room" in text_lower:
                features.has_family_tv_room = True
            elif "fireplace" in text_lower:
                features.has_fireplace = True
            elif "guest toilet" in text_lower:
                features.has_guest_toilet = True
            elif "irrigation" in text_lower:
                features.has_irrigation_system = True
            elif "aircon" in text_lower or "air conditioning" in text_lower:
                features.has_aircon = True
            elif "storage" in text_lower or "store room" in text_lower:
                features.has_storage = True
            elif "study" in text_lower or "office" in text_lower:
                features.study_rooms = val_num if val_num is not None else 1.0
            elif "solar" in text_lower or "inverter" in text_lower:
                features.has_solar_inverter = True
            elif "pet friendly" in text_lower:
                features.is_pet_friendly = True
            elif "furnished" in text_lower:
                features.is_furnished = True

        features.raw_features_list = list(dict.fromkeys(features.raw_features_list))
        return features

    def _extract_agents(
        self, soup: BeautifulSoup, bundle_params: dict[str, Any]
    ) -> tuple[AgentInfo | None, list[AgentInfo]]:
        """Extract primary agent and all co-listing agents and agency info."""
        primary_agent: AgentInfo | None = None
        co_agents: list[AgentInfo] = []

        agency_info = bundle_params.get("agencyInfo", {})
        agency_name = agency_info.get("name") if isinstance(agency_info, dict) else None
        agency_logo = agency_info.get("logoUrl") if isinstance(agency_info, dict) else None

        # 1. From bundleParams contactDetails
        contacts = bundle_params.get("contactDetails", [])
        if isinstance(contacts, list) and contacts:
            for idx, c in enumerate(contacts):
                if isinstance(c, dict):
                    ag = AgentInfo(
                        agent_name=c.get("name"),
                        agency_name=agency_name,
                        agency_logo_url=c.get("image") or agency_logo,
                        profile_url=c.get("agentPageUrl"),
                    )
                    if idx == 0:
                        primary_agent = ag
                    else:
                        co_agents.append(ag)

        # 2. DOM fallback if no contact details in bundle
        if not primary_agent:
            dom_agent = AgentInfo(agency_name=agency_name, agency_logo_url=agency_logo)
            found = False
            for el in soup.find_all(class_=re.compile(r"agent|seller|contact|agency", re.I)):
                img = el.find("img")
                if img and img.get("src") and not dom_agent.agency_logo_url:
                    dom_agent.agency_logo_url = img["src"]
                    found = True

            for a in soup.find_all("a", href=re.compile(r"estate-agency|estate-agent|branch", re.I)):
                text = a.get_text(strip=True)
                if text and not dom_agent.agency_name:
                    dom_agent.agency_name = text
                    found = True

            if found:
                primary_agent = dom_agent

        return primary_agent, co_agents

    def _extract_title(
        self, soup: BeautifulSoup, og_tags: dict[str, str], bundle_params: dict[str, Any]
    ) -> str | None:
        """Extract headline title."""
        if bundle_params.get("title"):
            return str(bundle_params["title"]).strip()

        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
            if title:
                return title

        if "og:title" in og_tags:
            return og_tags["og:title"]

        if soup.title and soup.title.string:
            return soup.title.string.strip()

        return None

    def _extract_description(self, soup: BeautifulSoup, og_tags: dict[str, str]) -> str | None:
        """Extract complete property description."""
        desc_elem = soup.find(class_=re.compile(r"details-page-description|property-description|overview", re.I))
        if desc_elem:
            for btn in desc_elem.find_all(["button", "a"]):
                if any(w in btn.get_text().lower() for w in ["show more", "show less", "read more"]):
                    btn.decompose()
            text = desc_elem.get_text("\n", strip=True)
            if text:
                return text

        if "og:description" in og_tags:
            return og_tags["og:description"]

        return None

    def _extract_images(
        self, html: str, soup: BeautifulSoup, listing_id: str, bundle_params: dict[str, Any]
    ) -> list[ImageRecord]:
        """Discover and deduplicate all 56 high-resolution gallery images."""
        images: list[ImageRecord] = []
        seen_hashes: set[str] = set()

        gallery_photos = bundle_params.get("galleryPhotos", [])
        if isinstance(gallery_photos, list) and gallery_photos:
            for idx, p in enumerate(gallery_photos):
                if not isinstance(p, dict):
                    continue

                alt = p.get("altText") or ""
                high_res_url = None
                orig_url = p.get("mediumUrl") or ""

                target_search_str = f"{p.get('srcSet', '')} {orig_url}"
                match = PP_IMG_HASH_RE.search(target_search_str)
                if match:
                    lid, img_hash = match.groups()
                    if img_hash not in seen_hashes:
                        seen_hashes.add(img_hash)
                        high_res_url = f"https://images.pp.co.za/listing/{lid}/{img_hash}/1600/1066/contain/jpegorpng"
                        if not orig_url:
                            orig_url = f"https://images.pp.co.za/listing/{lid}/{img_hash}/600/450/contain/jpegorpng"
                        images.append(
                            ImageRecord(
                                order_index=idx,
                                original_url=orig_url,
                                resolved_url=high_res_url,
                                alt_text=alt,
                                is_hero=(idx == 0),
                            )
                        )
                elif orig_url:
                    images.append(
                        ImageRecord(
                            order_index=idx,
                            original_url=orig_url,
                            resolved_url=orig_url,
                            alt_text=alt,
                            is_hero=(idx == 0),
                        )
                    )

            if images:
                return images

        discovered_hashes: list[tuple[str, str, str | None]] = []

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy")
            if not src:
                continue
            match = PP_IMG_HASH_RE.search(src)
            if match:
                lid, img_hash = match.groups()
                if img_hash not in seen_hashes:
                    seen_hashes.add(img_hash)
                    alt = img.get("alt")
                    discovered_hashes.append((lid, img_hash, alt))

        for lid, img_hash in PP_IMG_HASH_RE.findall(html):
            if img_hash not in seen_hashes:
                seen_hashes.add(img_hash)
                discovered_hashes.append((lid, img_hash, None))

        for idx, (lid, img_hash, alt) in enumerate(discovered_hashes):
            high_res_url = f"https://images.pp.co.za/listing/{lid}/{img_hash}/1600/1066/contain/jpegorpng"
            orig_url = f"https://images.pp.co.za/listing/{lid}/{img_hash}/600/450/contain/jpegorpng"
            images.append(
                ImageRecord(
                    order_index=idx,
                    original_url=orig_url,
                    resolved_url=high_res_url,
                    alt_text=alt,
                    is_hero=(idx == 0),
                )
            )

        return images

    def _extract_videos(self, soup: BeautifulSoup, bundle_params: dict[str, Any]) -> list[VideoRecord]:
        """Extract embedded video frames (YouTube, Matterport 3D, Vimeo)."""
        videos: list[VideoRecord] = []

        if bundle_params.get("videoTourUrl"):
            v_url = bundle_params["videoTourUrl"]
            provider = "YouTube" if "youtube" in v_url else "Video"
            videos.append(VideoRecord(provider=provider, url=v_url, title="Video Tour"))

        if bundle_params.get("virtualTourUrl"):
            vt_url = bundle_params["virtualTourUrl"]
            videos.append(VideoRecord(provider="Matterport 3D", url=vt_url, title="Virtual Tour"))

        for iframe in soup.find_all("iframe"):
            src = iframe.get("src") or ""
            if not src:
                continue

            if any(v.url == src for v in videos):
                continue

            provider = "Unknown"
            if "youtube.com" in src or "youtu.be" in src:
                provider = "YouTube"
            elif "vimeo.com" in src:
                provider = "Vimeo"
            elif "matterport.com" in src:
                provider = "Matterport 3D"

            title_elem = iframe.find_previous(["h2", "h3", "div"], class_=re.compile(r"video|title", re.I))
            title = title_elem.get_text(strip=True) if title_elem else None

            videos.append(
                VideoRecord(
                    provider=provider,
                    url=src,
                    title=title,
                )
            )

        return videos
