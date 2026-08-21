# Data Export & GIS Guide

## 1. Overview

`property-archiver` features a unified export engine for turning archived listings into tabular spreadsheets, relational databases, streaming JSONL, and geospatial GIS files.

```bash
# Export to CSV spreadsheet
property-archiver export --format=csv --output=portfolio.csv

# Export to indexed relational SQLite database
property-archiver export --format=sqlite --output=portfolio.db

# Export to streaming JSON Lines (for data lakes / BigQuery)
property-archiver export --format=jsonl --output=portfolio.jsonl

# Export to GeoJSON FeatureCollection (for QGIS / Mapbox / ArcGIS)
property-archiver export --format=geojson --output=portfolio.geojson
```

---

## 2. Export Formats Explained

### A. CSV Spreadsheet (`--format=csv`)
- Flattens all 27 feature flags, pricing metrics, rates, GPS coordinates, land sizes, and agent contact details into a clean tabular layout for Excel, Google Sheets, or Pandas.

### B. Relational SQLite Database (`--format=sqlite`)
- Creates an indexed schema with relational tables:
  - `listings`: Primary table with indexes on `suburb`, `listing_status`, and `price_amount`.
  - `listing_images`: Relational table linking image hashes, dimensions, local paths, and SHA-256 digests.

### C. GeoJSON Spatial GIS (`--format=geojson`)
- Converts all listings with GPS coordinates into standard WGS84 GeoJSON `Feature` objects with `Point` geometries (`[longitude, latitude]`) and rich metadata attributes for spatial analysis and map visualization.

### D. JSON Lines (`--format=jsonl`)
- Outputs one complete `ListingRecord` JSON document per line, ideal for feeding vector databases, Elasticsearch, or cloud data warehouses.
