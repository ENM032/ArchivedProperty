# Unified Web Dashboard Guide

## 1. Overview

`property-archiver` includes a built-in, local, zero-dependency web dashboard. It enables visual browsing, filtering, search, full image gallery inspection, CSV exports, and direct in-browser listing archiving.

```
+-----------------------------------------------------------------------------------+
|  PROPERTY ARCHIVER DASHBOARD                 [Export CSV]  [+ Archive Listing]   |
+-----------------------------------------------------------------------------------+
| [4 Properties]  [224 Images Preserved]  [R 19,996,000 Portfolio]  [75% Active]    |
+-----------------------------------------------------------------------------------+
| [Search by ID, Suburb, Title...]             [Status: All v]  [Sort: Price High v]|
+-----------------------------------------------------------------------------------+
| +-------------------------+ +-------------------------+ +-----------------------+ |
| | [Hero Photo]  [ACTIVE]  | | [Hero Photo] [UNDER OFFER]| | [Hero Photo]  [SOLD] | |
| | R 4,999,000             | | R 3,250,000             | | R 8,500,000           | |
| | 4 Bed House in Rivonia  | | 2 Bed Flat in Rosebank  | | 5 Bed House in Bryan. | |
| | 4 Beds | 3.5 Baths | 3G | | 2 Beds | 2 Baths | 1G   | | 5 Beds | 5 Baths | 4G | |
| +-------------------------+ +-------------------------+ +-----------------------+ |
+-----------------------------------------------------------------------------------+
```

---

## 2. Launching the Dashboard

### Start the Dashboard Server
```bash
property-archiver serve
```
*(Or use the alias: `property-archiver dashboard`)*

Options:
- `--port 8000`: Set custom port (default: 8000).
- `--host 127.0.0.1`: Set host binding.
- `--archive-dir ./archive`: Specify path to archive folder.
- `--no-open`: Do not auto-launch browser.

### Open a Specific Property Dossier
```bash
property-archiver view T4710876
```
*(Launches the dashboard and directly opens the property dossier modal with full 56-photo carousel).*

---

## 3. Key Dashboard Capabilities

1. **Portfolio Metrics**: Real-time stats on total properties, preserved photos, total market value, and active/under offer/sold ratios.
2. **Interactive Gallery Carousel**: Full 56-photo carousel with thumbnail strip, zoom, and alt-text tags.
3. **Structured Dossier**: Complete overview of specs, rates/taxes, levies, amenities, and agent profile cards.
4. **Live In-Browser Archiving**: Click "Archive Listing", type `T4710876` or paste a URL, and archive it directly with live progress toasts.
5. **Spreadsheet Export**: Instant one-click CSV export of all archived properties.
6. **Cryptographic Manifest Verification**: Inspect SHA-256 hashes and tamper-proof provenance.
