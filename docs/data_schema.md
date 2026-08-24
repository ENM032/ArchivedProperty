# Canonical Data Schema Reference (v1.0.0)

Every archived listing is normalized into a strictly validated Pydantic model (`ListingRecord`) and saved as `listing.json`.

---

## Field Specifications

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Schema specification version (`"1.0.0"`). |
| `portal_name` | `str` | Source portal identifier (e.g. `"privateproperty.co.za"`). |
| `listing_id` | `str` | Unique portal identifier (e.g. `"T4710876"`). |
| `canonical_url` | `str` | Full canonical URL of the listing. |
| `extracted_at` | `datetime` | UTC timestamp of extraction. |
| `title` | `str` | Headline title of the listing. |
| `listing_type` | `str` | Transaction classification (`"for_sale"` or `"to_rent"`). |
| `property_type` | `str` | Physical structure category (`"House"`, `"Apartment"`, `"Townhouse"`, `"Vacant Land"`, `"Commercial"`, `"Farm"`). |
| `listing_status` | `str` | Lifecycle status (`"active"`, `"under_offer"`, `"sold"`, `"withdrawn"`). |
| `status_badges` | `list[str]` | Visual badges on the page (`["Under Offer", "Reduced"]`). |
| `is_under_offer` | `bool` | True if marked Under Offer. |
| `is_sold` | `bool` | True if marked Sold. |
| `is_on_show` | `bool` | True if scheduled for public viewing. |
| `is_price_reduced`| `bool` | True if price was discounted. |
| `erf_size_m2` | `float` | Land size normalized to square meters (auto-converts hectares: $1\text{ ha} = 10,000\text{ m}^2$). |
| `land_size_raw` | `str` | Original raw size string (e.g. `"2.5 ha"`, `"1983 m²"`). |
| `floor_size_m2` | `float` | Building floor area in square meters. |
| `price.amount` | `float` | Asking price numerical amount in ZAR. |
| `price.rates_and_taxes_monthly` | `float` | Municipal rates & taxes in ZAR. |
| `price.levies_monthly` | `float` | Body corporate / HOA levies in ZAR. |
| `location.suburb` | `str` | Suburb name (e.g. `"Rivonia"`). |
| `location.city` | `str` | Area / City name (e.g. `"Sandton"`). |
| `location.province` | `str` | Province name (e.g. `"Gauteng"`). |
| `location.latitude` | `float` | GPS latitude coordinate. |
| `location.longitude` | `float` | GPS longitude coordinate. |
| `agent` | `AgentInfo` | Lead estate agent details. |
| `co_agents` | `list[AgentInfo]`| Co-listing agents and team members. |
| `images` | `list[ImageRecord]`| Preserved high-resolution gallery images. |
| `content_fingerprint` | `str` | Cryptographic SHA-256 hash of semantic listing data. |
