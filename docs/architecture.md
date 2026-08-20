# System Architecture & Design

## 1. Architectural Overview

`property-archiver` is a modular, production-ready system for ingesting, validating, extracting, and archiving South African real estate listings from online portals.

```
                           [Listing URL / HTML Snapshot]
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │   Security & SSRF Validator   │
                         │   • URL scheme enforcement    │
                         │   • DNS check vs private IPs  │
                         │   • Hostname allowlist check  │
                         └───────────────────────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │        Fetcher Engine         │
                         │   • httpx HTTP client         │
                         │   • Domain rate limiter       │
                         │   • Exponential backoff+jitter│
                         │   • Max response byte limit   │
                         └───────────────────────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │    Multi-Tier Extractor       │
                         │   • Tier 1: JSON-LD / Schema  │
                         │   • Tier 2: OpenGraph / Meta  │
                         │   • Tier 3: Semantic DOM      │
                         │   • Tier 4: Media Discovery   │
                         └───────────────────────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │    Normalizer & Validator     │
                         │   • Pydantic v2 Schema v1.0.0 │
                         │   • Strict type coercion      │
                         │   • Stable content hash       │
                         └───────────────────────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │   Image Processing Worker     │
                         │   • High-res URL resolution   │
                         │   • Pillow format validation  │
                         │   • Dimension inspection      │
                         │   • SHA-256 computation       │
                         └───────────────────────────────┘
                                         │
                                         ▼
                         ┌───────────────────────────────┐
                         │    Atomic Archive Writer      │
                         │   • .staging directory        │
                         │   • raw.html snapshot         │
                         │   • listing.json              │
                         │   • metadata.json             │
                         │   • checksums.json manifest   │
                         │   • Atomic rename commit      │
                         └───────────────────────────────┘
```

---

## 2. Core Subsystems

### A. Security & SSRF Prevention Layer (`property_archiver/core/security.py`)
- **Scheme Validation**: Enforces `http` and `https` protocols exclusively.
- **DNS Resolution Checks**: Resolves hostnames to IP addresses before initiating requests, actively blocking private, loopback, multicast, or link-local addresses (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `fc00::/7`).
- **Path Traversal Protection**: Implements `safe_join_path` to prevent relative directory escapes (`../../`).
- **Filename Sanitization**: Scrubs cross-platform illegal characters (`\ / : * ? " < > |`) and Windows reserved names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).

### B. Resilient Fetcher (`property_archiver/core/fetcher.py`)
- Built on `httpx.Client`.
- Implements domain-specific rate limiting (`rate_limit_delay_sec`) to guarantee polite crawl behavior.
- Retries on HTTP 429 (Too Many Requests) and 5xx (Server Errors) with exponential backoff and jitter.
- Enforces maximum response body boundaries (`max_response_size_bytes`) to protect against decompression and resource exhaustion attacks.

### C. Multi-Tier Extractor Architecture (`property_archiver/extractors/`)
- Implements `BaseExtractor` abstract base class to support pluggable multi-portal extractors.
- `PrivatePropertyExtractor` processes pages in four cascading layers:
  1. **Structured JSON-LD**: Reads `BreadcrumbList`, `PostalAddress`, `GeoCoordinates`, and `additionalProperty` key-values.
  2. **OpenGraph & Meta Tags**: Captures social titles, canonical URLs, and fallback descriptions.
  3. **Semantic DOM Parsing**: Extracts prices, monthly rates, levies, property type, erf/floor sizes, and structured amenities.
  4. **Media Resolution**: Identifies unique CDN image IDs and synthesizes full 1600x1066 high-resolution URLs.

### D. Image Preservation Pipeline (`property_archiver/images/downloader.py`)
- Downloads images concurrently using a bounded `ThreadPoolExecutor` (default 4 workers).
- Verifies image bytes using `PIL.Image.open()` to detect malformed files or non-image payloads.
- Extracts real dimensions and MIME types, computing SHA-256 digests.

### E. Atomic Storage & Integrity Manifests (`property_archiver/storage/`)
- Downloads and writes everything into a hidden staging directory (`.staging_<id>_<timestamp>`).
- Calculates SHA-256 checksums across all files and outputs `checksums.json`.
- Atomically renames the staging folder to the permanent destination (`archive/listings/<id>`), guaranteeing zero corruption from aborted runs.
