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
        ├── checksums.json    # Cryptographic SHA-256 manifest of every file
        └── images/           # High-resolution preserved image assets
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
| `listing_status` | `string` | Listing status (`"active"`, `"sold"`, `"withdrawn"`) |
| `listing_date` | `string (YYYY-MM-DD) | null` | Date when the property was listed |
| `description` | `string | null` | Full textual description |
| `erf_size_m2` | `float | null` | Land / Erf size in square meters |
| `floor_size_m2` | `float | null` | Floor / building size in square meters |
| `price` | `object` | Pricing sub-model (`amount`, `currency`, `rates_and_taxes_monthly`, `levies_monthly`) |
| `location` | `object` | Location sub-model (`street_address`, `suburb`, `city`, `province`, `country`, `latitude`, `longitude`, `breadcrumbs`) |
| `features` | `object` | Features sub-model (`bedrooms`, `bathrooms`, `garages`, `has_pool`, `has_garden`, `has_alarm`, etc., and `raw_features_list`) |
| `agent` | `object | null` | Agent/agency contact details |
| `images` | `array<object>` | Preserved images (`order_index`, `original_url`, `resolved_url`, `local_filename`, `sha256`, `width`, `height`, `mime_type`, `file_size_bytes`) |
| `videos` | `array<object>` | Preserved video embeds (`provider`, `url`, `title`) |
| `raw_json_ld` | `array<object>` | Lossless raw JSON-LD blocks extracted from page |
| `open_graph` | `object` | Captured OpenGraph metadata tags |
| `meta_tags` | `object` | Captured standard HTML meta tags |
| `content_fingerprint` | `string` | SHA-256 hash of semantic data for change detection |

---

## 3. Checksums Manifest (`checksums.json`)

```json
{
  "schema_version": "1.0.0",
  "listing_id": "T4710876",
  "archived_at": "2026-08-20T13:47:10.120412Z",
  "archiver_version": "1.0.0",
  "files": {
    "listing.json": "a319a86973c4c4a9e87d5e089f20af29b8e00e936b96c3c5632a1c4a01592048",
    "raw.html": "5b568547a6ed94359ae471fe5b7d2521c11a26ced71468cabff0570cb9f7f4a6",
    "images/001_OHWDrL0sRYBS5V4yxQIos2.jpg": "e5772349cca951624bdb128107bf8cfae278aba53a444fdc46dbd33310459635",
    "metadata.json": "4b7dc9aa274e73811ea77f5e04b5c0797de6670e92dc1c72a5bef400ad8984c8"
  }
}
```
