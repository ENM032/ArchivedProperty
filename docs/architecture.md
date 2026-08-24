# System Architecture & Technical Design

`property-archiver` is designed as a secure, high-throughput, and decoupled system for ingesting, validating, versioning, analyzing, and visualizing South African real estate data.

---

## 1. High-Level Component Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CLI & REST Clients                              │
│         (property-archiver fetch, tree, export, serve, compare)             │
└───────────────────────┬─────────────────────────────┬───────────────────────┘
                        │                             │
                        ▼                             ▼
       ┌────────────────────────────────┐   ┌────────────────────────────────┐
       │   Ingestion & Extraction       │   │   Web Dashboard & REST API     │
       │   - SSRF Guard                 │   │   - server.py (Dispatcher)     │
       │   - Fetcher (httpx Engine)     │   │   - routes/listings.py         │
       │   - Extractor (JSON-LD + DOM)  │   │   - routes/hierarchy.py        │
       │   - Smart Image Downloader     │   │   - routes/compare.py          │
       │   - Change Detector & History  │   │   - routes/export.py           │
       └───────────────┬────────────────┘   └───────────────┬────────────────┘
                       │                                    │
                       │     ┌────────────────────────┐     │
                       ├────►│ Decoupled ES6 Frontend ├─────┤
                       │     │ - State Store          │     │
                       │     │ - Grid/Grouped/Map     │     │
                       │     │ - Modular CSS Tokens   │     │
                       │     └────────────────────────┘     │
                       ▼                                    ▼
       ┌─────────────────────────────────────────────────────────────────────┐
       │                 Storage & Export Management Layer                   │
       │  - Hierarchical Storage (Province / Area / Suburb / Listing ID)     │
       │  - SHA-256 Checksum Manifests (checksums.json)                      │
       │  - Exporters: CSV, Relational SQLite (portfolio.db), GeoJSON, JSONL │
       └─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion & Image Pipeline (with Smart Caching)

1. **URL Resolution & Normalization**:
   - Short IDs (e.g. `T4710876`) are resolved to canonical portal URLs.
2. **SSRF Guard**:
   - Validates schemes, whitelists domains, resolves DNS, and blocks private/loopback/link-local IPv4 & IPv6 ranges.
3. **Resilient HTTP Fetcher**:
   - Incorporates polite rate limiting, jittered exponential backoff for transient 429/5xx codes, and payload size bounds.
4. **Multi-Source Extraction Pipeline**:
   - Priority 1: Schema.org JSON-LD (`@graph` unpacking, coordinates, structural specifications).
   - Priority 2: Semantic HTML & DOM selectors (rates, levies, features list, multi-agent cards).
   - Priority 3: OpenGraph & meta tags fallback.
5. **Smart Local Image Caching**:
   - Before requesting photos from the CDN, the downloader checks whether matching image hashes exist in the local archive.
   - Cached photos are verified and copied instantly, reducing re-archival time from ~8s to <1s.
6. **Atomic Directory Swapping**:
   - Commits to staging first; verifies SHA-256 digests; swaps atomically to avoid corrupt archives.

---

## 3. Storage Hierarchy Layout

By default, archives are stored in the **tiered South African regional hierarchy**:

$$\text{archive/listings/}\langle\text{province}\rangle\text{/}\langle\text{area}\rangle\text{/}\langle\text{suburb}\rangle\text{/}\langle\text{id}\rangle\text{/}$$

```
archive/listings/gauteng/sandton/rivonia/T4710876/
├── raw.html          # Byte-exact snapshot of source markup
├── listing.json      # Canonical normalized schema (v1.0.0)
├── metadata.json     # Scraping provenance, timing, and headers
├── checksums.json    # Cryptographic SHA-256 manifest
├── history.json      # Append-only price and spec change ledger
└── images/           # High-resolution gallery assets
    ├── 001_OHWDrL0sRYBS5V4yxQIos2.jpg
    └── ...
```

---

## 4. Web Dashboard Decoupled Architecture

The dashboard is decoupled into an HTTP REST server and a zero-build native ES6 frontend:

```
property_archiver/dashboard/
├── server.py              # Lightweight Threading HTTP Server & static file streamer
├── routes/                # Micro-controllers (<100 lines each)
│   ├── listings.py        # /api/listings, /api/listings/{id}, image streaming
│   ├── hierarchy.py       # /api/hierarchy regional tree calculation
│   ├── compare.py         # /api/compare snapshot diffs
│   └── export.py          # /api/export downloads
└── frontend/              # Static Frontend Web App
    ├── index.html         # Pure Semantic HTML
    ├── css/               # Modular CSS Token & BEM files
    └── js/                # Native ES6 Modules (store, views, components, api)
```
