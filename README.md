# Property Archiver (`property-archiver`)

A production-grade, secure, modular, and resilient tool for archiving publicly accessible South African property listings (specifically tailored for [Private Property South Africa](https://www.privateproperty.co.za)) for legitimate offline archiving, research, market analysis, and longitudinal comparison.

---

## 1. Key Capabilities & Features

- **Tiered Geographic Hierarchy**: Automatically sorts and organizes listing archives into an intuitive South African regional hierarchy:
  $$\text{Province} \longrightarrow \text{Area / Metro} \longrightarrow \text{Suburb} \longrightarrow \text{Listing ID}$$
  *(e.g., `archive/listings/gauteng/sandton/rivonia/T4710876/`)*.
- **Property Type & Intent Separation**: Categorizes listings across property types (**House, Apartment, Townhouse, Vacant Land, Farm, Commercial**) and transaction intent (**For Sale / Buy vs To Rent**).
- **Interactive Web Dashboard**: Embedded modern Single Page Application (SPA) with:
  - **Cascading Filters**: Dynamically drills down from Province $\rightarrow$ Area $\rightarrow$ Suburb.
  - **Grouped Accordion View**: Collapsible regional sections with listing counts, total market values, and average prices.
  - **Interactive GIS Map**: Leaflet & OpenStreetMap view plotting all property pins with GPS accuracy.
  - **Full Property Dossiers**: Photo gallery carousel, specifications, rates/levies, amenities tags, mini-maps, and agent information.
  - **Side-by-Side Diff Engine**: Visual comparison mode highlighting price revisions and spec alterations.
- **Smart Image Caching & Deduplication**: High-resolution gallery photo ingestion with instant local hash lookup. Re-archiving a listing takes **<1 second** by skipping redundant network downloads.
- **Cryptographic Integrity Ledger**: Generates a `checksums.json` SHA-256 manifest and maintains an append-only `history.json` diff ledger across successive scrapes.
- **Multi-Format Export Engine**: Export filtered property collections directly to **CSV, indexed relational SQLite (`portfolio.db`), JSON Lines, and GIS GeoJSON FeatureCollections**.
- **CLI Tree Explorer**: Terminal-based Rich tree explorer displaying market valuations, status ratios, and regional breakdowns.

---

## 2. Directory Layout: Flat vs Hierarchical

Property Archiver defaults to the **hierarchical** directory layout:

```
archive/
└── listings/
    └── gauteng/
        └── sandton/
            ├── lonehill/
            │   └── T5513030/
            │       ├── raw.html          # Byte-exact raw HTML snapshot
            │       ├── listing.json      # Normalized JSON data (schema v1.0.0)
            │       ├── metadata.json     # Provenance data (timings, headers, archiver version)
            │       ├── checksums.json    # Cryptographic SHA-256 manifest
            │       ├── history.json      # Version diff ledger & price change timeline
            │       └── images/           # High-resolution verified photos
            │           ├── 001_ABC123.jpg
            │           └── ...
            └── rivonia/
                └── T4710876/
```

> **Note**: The reader engine is fully backward-compatible and automatically discovers listings regardless of whether they are saved in a flat (`listings/T4710876`) or hierarchical structure.

---

## 3. Installation & Setup

### Prerequisites
- Python 3.10+
- `pip` or `uv`

### Installation
```bash
# Clone the repository
git clone https://github.com/ENM032/ArchivedProperty.git
cd ArchivedProperty

# Install in editable mode
pip install -e .

# Or install with dev/test dependencies
pip install -e ".[dev]"
```

---

## 4. CLI Usage & Examples

### Ingest a Listing (URL or Short ID)
```bash
# Ingest using full portal URL
property-archiver fetch https://www.privateproperty.co.za/for-sale/gauteng/johannesburg/sandton/rivonia/13-winston-avenue/T4710876

# Ingest using short listing ID (automatically resolved)
property-archiver fetch T4710876

# Ingest directly from system clipboard
property-archiver fetch --clipboard
```

### Terminal Geographic Tree Explorer (`tree`)
Explore the complete archive hierarchy with valuations and listing status badges in the terminal:
```bash
# View full portfolio tree
property-archiver tree

# Filter by province, area, suburb, or status
property-archiver tree --province=Gauteng --area=Sandton --status=active
```

### Launch the Web Dashboard (`serve` / `dashboard`)
```bash
# Launches the local dashboard at http://127.0.0.1:8000
property-archiver serve

# Launch on a custom port
property-archiver serve --port 8080
```

### Multi-Format & Regional Export (`export`)
Export all or filtered segments of the archived portfolio:
```bash
# Export entire portfolio to CSV
property-archiver export --format=csv --output=portfolio.csv

# Export specific suburb to SQLite database with spatial indexes
property-archiver export --format=sqlite --suburb="Rivonia" --output=rivonia.db

# Export to GeoJSON for QGIS / ArcGIS
property-archiver export --format=geojson --province="Gauteng" --output=gauteng_gis.geojson

# Export to JSON Lines (JSONL) for analytics pipelines
property-archiver export --format=jsonl --output=portfolio.jsonl
```

### Reorganize Archive Layout on Disk (`reorganize`)
Restructure existing on-disk archives between `hierarchical` (Province/Area/Suburb) and `flat` layouts:
```bash
# Preview reorganization with dry-run
property-archiver reorganize --layout=hierarchical --dry-run

# Execute restructuring
property-archiver reorganize --layout=hierarchical
```

### Inspect & Validate Integrity
```bash
# Inspect listing details in a formatted table
property-archiver inspect ./archive/listings/gauteng/sandton/rivonia/T4710876

# Verify SHA-256 cryptographic checksums of all assets
property-archiver validate ./archive/listings/gauteng/sandton/rivonia/T4710876

# Compare two listing snapshots (Diff engine)
property-archiver compare ./archive/listings/.../T4710876 ./archive/listings/.../T5513030
```

### Batch Ingestion
```bash
# Archive multiple listings from a text file (one URL/ID per line)
property-archiver batch urls.txt
```

---

## 5. Property Classification & Intent Separation

Each archived listing is structured with two primary classification fields:

| Field | Values | Description |
|---|---|---|
| `listing_type` | `for_sale`, `to_rent` | Differentiates properties for purchase (**Buy**) vs leases (**Rent**). |
| `property_type` | `House`, `Apartment`, `Townhouse`, `Vacant Land`, `Commercial`, `Farm`, `Industrial` | Captures the physical structural category. |

Both fields are stored in `listing.json`, indexed in `portfolio.db`, exported to CSV/GeoJSON, and filterable in the Web Dashboard.

---

## 6. Configuration & Environment Variables

All settings can be customized via `.env` or prefixed environment variables (`ARCHIVER_*`):

| Variable | Default | Description |
|---|---|---|
| `ARCHIVER_ARCHIVE_DIR` | `./archive` | Root directory for storing listing archives |
| `ARCHIVER_ARCHIVE_LAYOUT` | `hierarchical` | Storage layout: `hierarchical` or `flat` |
| `ARCHIVER_DOWNLOAD_IMAGES` | `true` | Enable/disable downloading gallery images |
| `ARCHIVER_MAX_CONCURRENCY` | `6` | Maximum concurrent worker threads for downloads |
| `ARCHIVER_RATE_LIMIT_DELAY_SEC` | `1.0` | Polite delay between requests to same domain |
| `ARCHIVER_REQUEST_TIMEOUT_SEC` | `25.0` | Socket timeout per HTTP request |
| `ARCHIVER_MAX_RETRIES` | `3` | Maximum retry attempts on transient network errors |
| `ARCHIVER_USER_AGENT` | `Mozilla/5.0...` | Custom User-Agent header |

---

## 7. Running Tests

```bash
# Run all unit, integration, and security tests
pytest -v

# Run with test coverage
pytest --cov=property_archiver tests/
```

---

## 8. Legal & Ethical Considerations

- **Public Data Only**: This tool only archives publicly visible real estate listings for personal offline research and comparison.
- **Polite Crawling**: Built-in polite rate limits (`rate_limit_delay_sec >= 1.0`), bounded concurrency, and smart caching reduce load on portal servers.
