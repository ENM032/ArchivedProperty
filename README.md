# Property Archiver (`property-archiver`)

A production-grade, secure, modular, and resilient tool for archiving publicly accessible South African property listings (specifically tailored for [Private Property South Africa](https://www.privateproperty.co.za)) for legitimate offline archiving, research, and longitudinal comparison.

---

## 1. Overview & Key Capabilities

- **Resilient Multi-Tier Extractor**: Combines Schema.org JSON-LD structured data, OpenGraph metadata, semantic HTML structures, and fallback regex extraction to ensure maximum field capture even when page layouts shift.
- **First-Class High-Resolution Image Preservation**: Automatically discovers all gallery assets, reconstructs original high-resolution photo URLs (e.g. `1600x1066`), deduplicates by asset hash, verifies image integrity with Pillow, and records SHA-256 checksums.
- **Cryptographic Archive Manifests**: Every archived listing includes a `checksums.json` manifest recording SHA-256 hashes for raw HTML, metadata, normalized JSON, and media assets.
- **Atomic Storage**: Writes to a temporary staging folder first and performs an atomic directory swap, guaranteeing that crashes or network drops cannot corrupt existing archives.
- **Change Detection & Diffing**: Identifies semantic updates between multiple archival snapshots (price modifications, rate adjustments, status transitions, newly added/removed features, or revised descriptions).
- **Security-First Architecture**: Built-in SSRF guards (blocking private, link-local, loopback IPv4/IPv6 ranges and unapproved hosts), path-traversal protection, response payload size limits, and safe filename sanitization.
- **Offline & Batch Ingestion**: Supports archiving directly from local HTML snapshots as well as live HTTP(S) crawling with polite rate limiting and jittered exponential backoff.

---

## 2. Archival Directory Structure

Each listing is stored in a self-contained, versioned folder:

```
archive/
└── listings/
    └── T4710876/
        ├── raw.html          # Byte-exact raw HTML snapshot as served
        ├── listing.json      # Normalized listing data conforming to schema v1.0.0
        ├── metadata.json     # Provenance data (timings, headers, archiver version)
        ├── checksums.json    # Cryptographic SHA-256 manifest of all files
        └── images/           # High-resolution gallery assets
            ├── 001_OHWDrL0sRYBS5V4yxQIos2.jpg
            ├── 002_QfBaAogURQxOa3iC6KATv2.jpg
            ├── 003_PzdR5Oi5ROOW799BiUIN75.jpg
            └── ...
```

---

## 3. Installation & Setup

### Prerequisites
- Python 3.10+
- `pip` or `uv`

### Installation
```bash
# Clone or navigate to the repository
cd ArchivedProperty

# Install in editable mode
pip install -e .

# Or install with dev/test dependencies
pip install -e ".[dev]"
```

---

## 4. CLI Usage & Examples

### Ingest a Live Listing URL
```bash
property-archiver fetch https://www.privateproperty.co.za/for-sale/gauteng/johannesburg/sandton/rivonia/13-winston-avenue/T4710876 --output ./archive
```

### Ingest an Offline Local HTML Snapshot
```bash
property-archiver fetch ./tests/fixtures/sample_listing.html --output ./archive
```

### Inspect an Existing Archive
```bash
property-archiver inspect ./archive/listings/T4710876
```

### Validate Checksum Integrity
```bash
property-archiver validate ./archive/listings/T4710876
```

### Compare Two Archive Snapshots (Diff Engine)
```bash
property-archiver compare ./archive/listings/T4710876_v1 ./archive/listings/T4710876_v2
```

### Batch Ingestion
Create a text file `urls.txt` with one URL per line:
```bash
property-archiver batch urls.txt --output ./archive
```

---

## 5. Configuration & Environment Variables

All settings can be customized via CLI flags or prefixed environment variables (`ARCHIVER_*`):

| Variable | Default | Description |
|---|---|---|
| `ARCHIVER_ARCHIVE_DIR` | `./archive` | Base directory for storing listing archives |
| `ARCHIVER_USER_AGENT` | `PropertyArchiver/1.0...` | Custom User-Agent header |
| `ARCHIVER_REQUEST_TIMEOUT_SEC` | `25.0` | Timeout per HTTP request in seconds |
| `ARCHIVER_RATE_LIMIT_DELAY_SEC` | `1.0` | Polite delay between requests to same domain |
| `ARCHIVER_MAX_RETRIES` | `3` | Maximum retry attempts on 429/5xx errors |
| `ARCHIVER_MAX_CONCURRENCY` | `4` | Maximum parallel worker threads for image downloading |
| `ARCHIVER_MAX_RESPONSE_SIZE_BYTES` | `52428800` (50MB) | Max response size to avoid resource exhaustion |
| `ARCHIVER_DOWNLOAD_IMAGES` | `true` | Set `false` to skip downloading image media |

---

## 6. Architecture & Data Flow

```
Input (URL or HTML File)
          │
          ▼
┌───────────────────────────┐
│ Security & SSRF Guard     │ -> Checks scheme, private IPs, allowed hosts
└───────────────────────────┘
          │
          ▼
┌───────────────────────────┐
│ Fetcher (httpx Engine)    │ -> Polite rate limiting, jitter, backoff
└───────────────────────────┘
          │
          ▼
┌───────────────────────────┐
│ Extractor Pipeline        │
│  ├─ JSON-LD Parser        │ -> Breadcrumbs, coordinates, specifications
│  ├─ OpenGraph & Meta      │ -> Title, social descriptions, fallback tags
│  ├─ Semantic DOM Parser   │ -> Details, features list, rates, taxes
│  └─ Media Resolver        │ -> High-res gallery discovery & deduplication
└───────────────────────────┘
          │
          ▼
┌───────────────────────────┐
│ Normalizer & Validator    │ -> Pydantic v2 validation & type coercion
└───────────────────────────┘
          │
          ▼
┌───────────────────────────┐
│ Image Downloader          │ -> Concurrency-bounded streaming, Pillow validation, SHA-256
└───────────────────────────┘
          │
          ▼
┌───────────────────────────┐
│ Atomic Archive Writer     │ -> Staging directory -> checksums manifest -> atomic rename
└───────────────────────────┘
```

---

## 7. Maintenance & Updating Extractors

When Private Property updates its website markup, update the designated extractor located at:
`property_archiver/extractors/private_property.py`

### Extractor Extension Points
- **JSON-LD Schema**: Handled in `_extract_json_ld()`. Check if `@type` changed (e.g. `SingleFamilyResidence`, `Residence`, `House`).
- **DOM CSS Selectors**: Centralized in `_extract_details()` and `_extract_features()`. Update class name regexes (`property-details__list-item`, `property-features__list-item`).
- **Image URL Resolvers**: Located in `_extract_images()`. If CDN patterns shift from `images.pp.co.za/listing/{id}/{hash}/{w}/{h}/...`, adjust `PP_IMG_HASH_RE`.

---

## 8. Running the Test Suite

```bash
# Run all unit, fixture, and integration tests
pytest -v

# Run with test coverage report
pytest --cov=property_archiver tests/
```

---

## 9. Legal & Ethical Considerations

- **Public Data Only**: This tool only extracts publicly visible data intended for human viewing. It does not access private accounts or bypass access controls.
- **Polite Crawling**: Respect target servers by retaining default rate limits (`rate_limit_delay_sec >= 1.0`), avoiding high concurrency, and obeying server error signals.
- **Privacy**: Does not harvest unnecessary private individual personal data.
