# Web Dashboard User & Architecture Guide

The Property Archiver Dashboard is a Single Page Application (SPA) designed for market analysis, spatial exploration, and listing management.

---

## 1. UI Showcase

### Grid View
![Grid View](images/01_dashboard_grid_view.png)

### Regional Grouped View
![Grouped View](images/02_dashboard_grouped_view.png)

### GIS Map View
![Map View](images/03_dashboard_map_view.png)

### Property Dossier Modal
![Dossier Modal](images/04_dashboard_dossier_modal.png)

---

## 2. Launching the Dashboard

```bash
# Launch on default port (http://127.0.0.1:8000)
property-archiver serve

# Launch on custom port without auto-opening browser
property-archiver serve --port 8080 --no-open
```

---

## 3. Features & Workflow

### A. View Modes
1. **Grid View**: Responsive property cards with badges, pricing, specs, tags, and star ratings.
2. **Grouped Location View**: Collapsible accordions organized by **Province $\rightarrow$ Area $\rightarrow$ Suburb** with aggregate property counts, total valuations, and average prices.
3. **Interactive GIS Map View**: Fullscreen Leaflet / OpenStreetMap view plotting GPS pins with popup property dossiers.

### B. Cascading & Intent Filters
- **Transaction Intent**: Filter by `All Intents`, `For Sale (Buy)`, or `To Rent`.
- **Property Type**: Instant filtering by `House`, `Apartment`, `Townhouse`, `Vacant Land`, `Commercial`, or `Farm`.
- **Status Filter**: `Active`, `Under Offer`, `Sold`, `Withdrawn`.
- **Cascading Location Drill-Down**: Province dropdown updates Area dropdown, which dynamically updates Suburb choices.

### C. Property Dossier & Annotation
Clicking any property card opens an in-depth dossier:
- **Photo Carousel & Thumbnail Strip**: Full-screen photo viewer.
- **Specifications & Rates**: Bedrooms, bathrooms, garages, erf size, monthly rates & taxes, and levies.
- **Interactive Mini-Map**: Centered on property GPS coordinates.
- **Inline Edit Drawer**: Update status, add custom notes, tag chips, and star ratings.
- **Delete Archive**: Permanently removes the archive from disk with confirmation.
