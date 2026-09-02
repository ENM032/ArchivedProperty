# CLI User Guide (`ap`)

`ap` (**ArchivedProperty**) provides a suite of terminal commands for archiving, exploring, filtering, editing, and analyzing South African real estate property listings.

---

## 1. Archiving Listings (`ap fetch`)

Pass any full property listing URL directly from your browser. The URL resolver automatically handles canonicalization and extraction.

```bash
# Archive directly with a full URL
ap fetch https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876

# Archive without images (metadata & HTML only for fast analysis)
ap fetch https://www.privateproperty.co.za/for-sale/gauteng/sandton/rivonia/4-bedroom-house-in-rivonia/T4710876 --no-images

# Archive multiple URLs in batch
ap fetch https://www.privateproperty.co.za/.../T4710876 https://www.privateproperty.co.za/.../T5275166

# Archive from a text file containing one URL per line
ap fetch urls.txt
```

---

## 2. Interactive Web Dashboard (`ap serve`)

Launch the local web dashboard:
```bash
# Launch on default port (http://127.0.0.1:8000)
ap serve

# Launch on custom port without auto-opening browser
ap serve --port 8080 --no-open
```
> **Graceful Quit**: Press `Ctrl+C` or type `q` + `Enter` in the terminal to cleanly stop the server.

---

## 3. Terminal Hierarchy Tree Explorer (`ap tree`)

Inspect your local archive structured hierarchically by **Province $\rightarrow$ Area / Metro $\rightarrow$ Suburb $\rightarrow$ Listing**:

```bash
# View complete nationwide archive hierarchy
ap tree

# Filter by province and area
ap tree --province "Gauteng" --area "Sandton"

# Filter by suburb and status
ap tree --suburb "Rivonia" --status active
```

---

## 4. Editing & User Annotations (`ap edit`)

Update lifecycle status, add private notes, tags, or star ratings:

```bash
# Mark as under offer with custom notes and tags
ap edit T4710876 --status=under_offer --notes="Offer submitted" --tags="Prime, High ROI" --rating=5

# Update star rating
ap edit T4710876 --rating=4
```

---

## 5. Deleting an Archive (`ap delete`)

Permanently delete an archived property:

```bash
# Delete with confirmation prompt
ap delete T4710876

# Delete immediately without prompt
ap delete T4710876 --yes
```

---

## 6. Multi-Format Regional Export (`ap export`)

Export property records to CSV, SQLite, GeoJSON, or JSONL:

```bash
# Export filtered suburb to CSV
ap export --format=csv --suburb="Rivonia" --output="rivonia.csv"

# Export entire portfolio to SQLite database
ap export --format=sqlite --output="portfolio.db"

# Export geospatial coordinates to GeoJSON
ap export --format=geojson --output="map.geojson"
```

---

## 7. Integrity Validation & Inspection (`ap validate` / `ap inspect`)

```bash
# Verify cryptographic SHA-256 integrity
ap validate T4710876

# Inspect raw JSON-LD specifications and details
ap inspect T4710876
```
