# Web Dashboard User & Architecture Guide

The Property Archiver Dashboard is an embedded Single Page Application (SPA) designed for market analysis, spatial exploration, and listing comparison.

---

## 1. Quick Launch

Launch the local web dashboard from the CLI:
```bash
# Launch on default port (http://127.0.0.1:8000)
property-archiver serve

# Launch on custom port without auto-opening browser
property-archiver serve --port 8080 --no-open
```

---

## 2. Core Dashboard Features

### A. View Modes
1. **Grid View**: Responsive property cards displaying thumbnail photos, badges, pricing, key specs, and addresses.
2. **Grouped Location View**: Collapsible accordions organized by **Province $\rightarrow$ Area $\rightarrow$ Suburb** with aggregate property counts, total valuations, and average prices.
3. **Interactive GIS Map View**: Fullscreen Leaflet / OpenStreetMap view plotting GPS pins with popup property dossiers.

### B. Cascading & Intent Filters
- **Transaction Intent**: Filter by `All Intents`, `For Sale (Buy)`, or `To Rent`.
- **Property Type**: Instant filtering by `House`, `Apartment`, `Townhouse`, `Vacant Land`, `Commercial`, or `Farm`.
- **Status Filter**: `Active`, `Under Offer`, `Sold`.
- **Cascading Location Drill-Down**: Province dropdown updates Area dropdown, which dynamically updates Suburb choices.

### C. Property Dossier Modal
Clicking any property card opens an in-depth dossier:
- **Photo Carousel & Thumbnail Strip**: Full-screen photo viewer.
- **Specifications & Rates**: Bedrooms, bathrooms, garages, erf size, monthly rates & taxes, and levies.
- **Interactive Mini-Map**: Centered on property GPS coordinates.
- **Agent Info**: Primary listing agent and co-agents.

### D. Side-by-Side Comparison
Click **Compare Listings** to evaluate two properties or historical snapshots with highlighted price and specification diffs.

---

## 3. Frontend Architecture & State Management

The frontend runs purely on **native ES6 modules** with **zero build dependencies**:

```
frontend/
├── index.html             # Semantic structure
├── css/                   # Design tokens & BEM component partials
└── js/
    ├── app.js             # Bootstrap & global navigation
    ├── state/store.js     # Central reactive store & filter engine
    ├── api/apiClient.js   # Fetch API wrapper
    ├── views/             # View renderers (gridView, groupedView, mapView)
    └── components/        # Isolated UI components (filterBar, dossierModal, etc.)
```
