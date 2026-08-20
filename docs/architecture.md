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
                         │   • Tier 1: JS Deobfuscation  │
                         │   • Tier 2: Status & Badges   │
                         │   • Tier 3: JSON-LD / Schema  │
                         │   • Tier 4: OpenGraph / Meta  │
                         │   • Tier 5: Semantic DOM      │
                         │   • Tier 6: Media Discovery   │
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
                         │   • Full 56-image resolution  │
                         │   • High-res 1600x1066 URLs   │
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

## 2. Core Subsystems & Key Innovations

### A. JavaScript Deobfuscation Engine
Private Property encodes full listing metadata, all 56 high-resolution gallery photos, and agent contact cards inside an obfuscated inline script:
```javascript
window[...] = JSON.parse(Y.map($ => D[$]).join(''));
```
The extractor parses the token array `D` (1,600+ string tokens) and index mapping array `Y` (17,900+ integer indices), executing the token replacement natively in Python. This allows capturing all 56 gallery photos and real agent profiles without requiring headless Chrome or Node.js.

### B. Status & Lifecycle Detector (`docs/listing_lifecycle_and_status.md`)
Detects whether listings are `active`, `under_offer`, `sold`, `withdrawn`, `reduced`, or `on_show` by analyzing application state (`bundleParams.isUnderOffer`), DOM badge containers, and OpenGraph headers.

### C. Security & SSRF Prevention Layer (`property_archiver/core/security.py`)
- Scheme enforcement (`http`/`https`).
- DNS resolution checks actively blocking private/loopback/link-local IPv4 and IPv6 subnets (`127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `::1`, `fc00::/7`).
- Path-traversal protection and cross-platform filename sanitization.

### D. Image Preservation Pipeline (`property_archiver/images/downloader.py`)
- Downloads all 56 high-resolution images concurrently using a bounded thread pool.
- Validates image headers with Pillow and computes SHA-256 digests.

### E. Atomic Storage & Integrity Manifests (`property_archiver/storage/`)
- Uses staging folders (`.staging_<id>_<timestamp>`) and atomic directory renaming.
- Generates `checksums.json` containing SHA-256 hashes for all 56 images, raw HTML, metadata, and normalized JSON.
