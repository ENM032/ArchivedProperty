# Data Schema & Archive Format

## 1. Archive Directory Structure

Every archived property is stored in an isolated, self-contained directory under `archive/listings/<listing_id>/`:

```
archive/
└── listings/
    └── T4710876/
        ├── raw.html          # Byte-exact raw HTML snapshot as served by server
        ├── listing.json      # Normalized JSON record conforming to Schema v1.0.0
        ├── metadata.json     # Crawl provenance metadata (timings, headers, archiver version)
        ├── history.json      # Historical timeline ledger tracking price drops & status changes
        ├── checksums.json    # Cryptographic SHA-256 manifest of every file
        └── images/           # High-resolution preserved image assets (all 56 gallery photos)
            ├── 001_OHWDrL0sRYBS5V4yxQIos2.jpg
            ├── 002_QfBaAogURQxOa3iC6KATv2.jpg
            └── ...
```

---

## 2. Listing Schema Specification (`listing.json`)

The normalized listing model is validated using Pydantic v2.

### Field Definitions

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | Version of the schema specification (e.g. `"1.0.0"`) |
| `portal_name` | `string` | Source portal identifier (e.g. `"privateproperty.co.za"`) |
| `listing_id` | `string` | Portal unique listing identifier (e.g. `"T4710876"`) |
| `canonical_url` | `string` | Canonical URL of the listing |
| `extracted_at` | `string (ISO 8601)` | UTC timestamp when data was parsed |
| `title` | `string | null` | Headline title of the listing |
| `property_type` | `string | null` | Property category (`"House"`, `"Apartment"`, `"Townhouse"`) |
| `listing_status` | `string` | Listing status (`"active"`, `"under_offer"`, `"sold"`, `"withdrawn"`) |
| `status_badges` | `array<string>` | Discovered visual badges (`["Under Offer", "Reduced", "On Show"]`) |
| `is_under_offer` | `boolean` | Flag for Under Offer / Contract Pending |
| `is_sold` | `boolean` | Flag for Sold listings |
| `is_on_show` | `boolean` | Flag for active On Show scheduled viewings |
| `is_price_reduced` | `boolean` | Flag for discounted listings |
| `on_show_details` | `object | null` | Structured date and times for viewings |
| `listing_date` | `string (YYYY-MM-DD) | null` | Date when the property was listed |
| `description` | `string | null` | Full textual description |
| `erf_size_m2` | `float | null` | Land / Erf size normalized to square meters (auto-converts `ha` to $	ext{m}^2$) |
| `land_size_raw` | `string | null` | Original raw land size string (e.g. `"2.5 ha"`, `"1983 m²"`) |
| `floor_size_m2` | `float | null` | Floor / building size in square meters |
| `price` | `object` | Pricing sub-model (`amount`, `currency`, `rates_and_taxes_monthly`, `levies_monthly`) |
| `location` | `object` | Location sub-model (`street_address`, `suburb`, `city`, `province`, `country`, `latitude`, `longitude`, `breadcrumbs`) |
| `features` | `object` | Features sub-model (`bedrooms`, `bathrooms`, `garages`, `has_pool`, `has_garden`, `has_alarm`, etc., and `raw_features_list`) |
| `agent` | `object | null` | Primary listing agent (`agent_name`, `agency_name`, `agency_logo_url`, `profile_url`) |
| `co_agents` | `array<object>` | Additional co-listing agents and team members |
| `images` | `array<object>` | Preserved images (all 56 gallery photos with `order_index`, `resolved_url`, `sha256`, `width`, `height`) |
| `videos` | `array<object>` | Preserved video embeds (`provider`, `url`, `title`) |
| `raw_json_ld` | `array<object>` | Lossless raw JSON-LD blocks extracted from page (with `@graph` support) |
| `open_graph` | `object` | Captured OpenGraph metadata tags |
| `meta_tags` | `object` | Captured standard HTML meta tags |
| `content_fingerprint` | `string` | SHA-256 hash of semantic data for change detection |
