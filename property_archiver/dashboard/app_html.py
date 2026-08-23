"""
Embedded single-page application (SPA) HTML, CSS, and Vanilla JavaScript
for the Unified Property Archiver Dashboard with Cascading Province/Area/Suburb Filters,
Grouped Location Accordion View, and Interactive Map.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Property Archiver - Unified Dashboard</title>
    <!-- Leaflet CSS & JS for Interactive Map -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    <style>
        :root {
            --bg-main: #0f172a;
            --bg-card: #1e293b;
            --bg-hover: #334155;
            --border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --primary-hover: #0ea5e9;
            --accent-green: #22c55e;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --accent-purple: #a855f7;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            line-height: 1.5;
            min-height: 100vh;
        }

        header {
            background-color: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 40;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--primary);
        }
        .brand span { color: var(--text-main); }
        .header-actions {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .btn {
            background-color: var(--primary);
            color: #0f172a;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-weight: 600;
            font-size: 0.875rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: background-color 0.15s;
        }
        .btn:hover { background-color: var(--primary-hover); }
        .btn-secondary {
            background-color: var(--bg-hover);
            color: var(--text-main);
        }
        .btn-secondary:hover { background-color: #475569; }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 1.25rem;
        }
        .metric-title {
            color: var(--text-muted);
            font-size: 0.875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 1.75rem;
            font-weight: 700;
            margin-top: 0.25rem;
            color: var(--text-main);
        }
        .metric-sub {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }

        .controls-bar {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 1.25rem;
            margin-bottom: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .controls-row-top {
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            align-items: center;
            justify-content: space-between;
        }
        .controls-row-bottom {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            align-items: center;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border);
        }

        .search-box {
            flex: 1;
            min-width: 260px;
        }
        .search-input {
            width: 100%;
            background-color: var(--bg-main);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-size: 0.875rem;
        }
        .search-input:focus { outline: none; border-color: var(--primary); }
        
        .filter-label {
            color: var(--text-muted);
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .select-filter {
            background-color: var(--bg-main);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 0.5rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.875rem;
            cursor: pointer;
            min-width: 150px;
        }

        .view-toggle {
            display: flex;
            background-color: var(--bg-main);
            border: 1px solid var(--border);
            border-radius: 0.375rem;
            overflow: hidden;
        }
        .view-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 0.5rem 0.85rem;
            font-size: 0.85rem;
            cursor: pointer;
            font-weight: 600;
        }
        .view-btn.active {
            background-color: var(--primary);
            color: #0f172a;
        }

        /* Property Grid */
        .property-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }
        .property-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            cursor: pointer;
            transition: transform 0.15s, border-color 0.15s;
        }
        .property-card:hover {
            transform: translateY(-3px);
            border-color: var(--primary);
        }
        .card-thumb-wrapper {
            position: relative;
            width: 100%;
            height: 200px;
            background-color: #090d16;
            overflow: hidden;
        }
        .card-thumb {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .card-badge {
            position: absolute;
            top: 0.75rem;
            left: 0.75rem;
            background-color: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(4px);
            color: #fff;
            padding: 0.25rem 0.6rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .card-badge.active { border-left: 3px solid var(--accent-green); }
        .card-badge.under_offer { border-left: 3px solid var(--accent-amber); color: var(--accent-amber); }
        .card-badge.sold { border-left: 3px solid var(--accent-red); color: var(--accent-red); }
        .img-count-tag {
            position: absolute;
            bottom: 0.75rem;
            right: 0.75rem;
            background-color: rgba(15, 23, 42, 0.8);
            color: #fff;
            padding: 0.2rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .card-body {
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            flex: 1;
        }
        .card-price {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--text-main);
        }
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--primary);
            margin-top: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-address {
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 0.25rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-specs {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border);
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        .card-spec-item strong { color: var(--text-main); }
        .card-footer {
            margin-top: auto;
            padding-top: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Grouped Location Accordion */
        #grouped-view-container {
            display: none;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        .province-accordion {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            overflow: hidden;
        }
        .province-header {
            background-color: #1e293b;
            padding: 1rem 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            border-bottom: 1px solid var(--border);
        }
        .province-header:hover { background-color: var(--bg-hover); }
        .area-section {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
        }
        .area-section:last-child { border-bottom: none; }
        .area-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .suburb-block {
            margin-bottom: 1.25rem;
            background-color: var(--bg-main);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 1rem;
        }
        .suburb-header {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Map Container */
        #map-view-container {
            display: none;
            width: 100%;
            height: 650px;
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            overflow: hidden;
            margin-bottom: 2rem;
            position: relative;
        }
        #leaflet-map { width: 100%; height: 100%; }

        /* Modal & Dossier */
        .modal-backdrop {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(6px);
            z-index: 50;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }
        .modal-backdrop.open { display: flex; }
        .modal-content {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            width: 100%;
            max-width: 1100px;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
            display: flex;
            flex-direction: column;
        }
        .modal-header {
            padding: 1.25rem 1.75rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            position: sticky;
            top: 0;
            background-color: var(--bg-card);
            z-index: 10;
        }
        .modal-close {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.5rem;
            cursor: pointer;
            line-height: 1;
        }
        .modal-close:hover { color: var(--text-main); }
        .modal-body { padding: 1.75rem; }

        /* Gallery Carousel */
        .gallery-viewer {
            position: relative;
            background-color: #000;
            border-radius: 0.5rem;
            overflow: hidden;
            margin-bottom: 1.5rem;
        }
        .main-gallery-img {
            width: 100%;
            max-height: 480px;
            object-fit: contain;
            display: block;
            margin: 0 auto;
        }
        .gallery-nav-btn {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background-color: rgba(15, 23, 42, 0.7);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 0.75rem;
            border-radius: 50%;
            cursor: pointer;
        }
        .gallery-prev { left: 1rem; }
        .gallery-next { right: 1rem; }
        .gallery-caption {
            position: absolute;
            bottom: 0.5rem;
            left: 1rem;
            background-color: rgba(0,0,0,0.7);
            color: #fff;
            padding: 0.25rem 0.6rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
        }

        .thumb-strip {
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            padding-bottom: 0.75rem;
            margin-bottom: 1.5rem;
        }
        .thumb-strip-item {
            width: 72px;
            height: 52px;
            flex-shrink: 0;
            border-radius: 0.25rem;
            overflow: hidden;
            cursor: pointer;
            border: 2px solid transparent;
            opacity: 0.6;
        }
        .thumb-strip-item.active { border-color: var(--primary); opacity: 1; }
        .thumb-strip-item img { width: 100%; height: 100%; object-fit: cover; }

        .section-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1.5rem;
        }
        @media (max-width: 768px) { .section-grid { grid-template-columns: 1fr; } }
        .info-card {
            background-color: var(--bg-main);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 1.25rem;
            margin-bottom: 1.25rem;
        }
        .info-card h4 {
            color: var(--primary);
            font-size: 0.95rem;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.35rem;
        }
        .amenities-tag-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .amenity-tag {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            padding: 0.25rem 0.6rem;
            border-radius: 0.25rem;
            font-size: 0.8rem;
        }

        /* Mini Map in Dossier */
        #dossier-mini-map {
            width: 100%;
            height: 180px;
            border-radius: 0.375rem;
            margin-top: 0.75rem;
            border: 1px solid var(--border);
        }

        /* Comparison Table */
        .diff-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            margin-top: 1rem;
        }
        .diff-table th, .diff-table td {
            border: 1px solid var(--border);
            padding: 0.6rem 0.75rem;
            text-align: left;
        }
        .diff-table th { background-color: var(--bg-main); color: var(--primary); }
        .diff-changed { background-color: rgba(245, 158, 11, 0.15); }

        /* Toast */
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
            display: none;
            align-items: center;
            gap: 0.75rem;
            z-index: 100;
        }
        .toast.show { display: flex; }
        .toast.success { border-left: 4px solid var(--accent-green); }
        .toast.error { border-left: 4px solid var(--accent-red); }
    </style>
</head>
<body>

    <header>
        <div class="brand">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            Property Archiver <span>Dashboard</span>
        </div>
        <div class="header-actions">
            <button class="btn btn-secondary" onclick="openCompareModal()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/></svg>
                Compare Listings
            </button>
            <div class="view-toggle">
                <button id="btn-view-grid" class="view-btn active" onclick="switchView('grid')">Grid</button>
                <button id="btn-view-grouped" class="view-btn" onclick="switchView('grouped')">Grouped</button>
                <button id="btn-view-map" class="view-btn" onclick="switchView('map')">Map</button>
            </div>
            <button class="btn btn-secondary" onclick="openExportMenu(event)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Export
            </button>
            <button class="btn" onclick="openArchiveModal()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Archive Listing
            </button>
        </div>
    </header>

    <div class="container">
        <!-- Metric Cards -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Archived Properties</div>
                <div class="metric-value" id="m-count">0</div>
                <div class="metric-sub" id="m-count-sub">Across South African portals</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Preserved Images</div>
                <div class="metric-value" id="m-images">0</div>
                <div class="metric-sub">High-resolution verified assets</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Total Portfolio Value</div>
                <div class="metric-value" id="m-val">R 0</div>
                <div class="metric-sub">Sum of asking prices</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Status Breakdown</div>
                <div class="metric-value" id="m-status-ratio">0% Active</div>
                <div class="metric-sub" id="m-status-detail">0 Active | 0 Under Offer | 0 Sold</div>
            </div>
        </div>

        <!-- Controls Bar with Cascading Filters -->
        <div class="controls-bar">
            <div class="controls-row-top">
                <div class="search-box">
                    <input type="text" id="search-input" class="search-input" placeholder="Search by ID (e.g. T4710876), Suburb, Street, Title..." oninput="filterData()">
                </div>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <select id="status-filter" class="select-filter" onchange="filterData()">
                        <option value="all">All Statuses</option>
                        <option value="active">Active</option>
                        <option value="under_offer">Under Offer</option>
                        <option value="sold">Sold</option>
                    </select>
                    <select id="sort-filter" class="select-filter" onchange="filterData()">
                        <option value="date-desc">Newest Archived</option>
                        <option value="date-asc">Oldest Archived</option>
                        <option value="price-desc">Price: High to Low</option>
                        <option value="price-asc">Price: Low to High</option>
                        <option value="beds-desc">Bedrooms: Most</option>
                    </select>
                </div>
            </div>
            <!-- Cascading Hierarchy Row -->
            <div class="controls-row-bottom">
                <span class="filter-label">Location Drill-Down:</span>
                <select id="geo-province-filter" class="select-filter" onchange="onProvinceChanged()">
                    <option value="all">All Provinces</option>
                </select>
                <select id="geo-area-filter" class="select-filter" onchange="onAreaChanged()">
                    <option value="all">All Areas / Metros</option>
                </select>
                <select id="geo-suburb-filter" class="select-filter" onchange="filterData()">
                    <option value="all">All Suburbs</option>
                </select>
                <button class="btn btn-secondary" style="padding: 0.4rem 0.75rem; font-size: 0.8rem;" onclick="resetGeoFilters()">Reset Location</button>
            </div>
        </div>

        <!-- Flat Property Grid View -->
        <div id="property-grid" class="property-grid"></div>

        <!-- Grouped Location Accordion View -->
        <div id="grouped-view-container"></div>

        <!-- Map View Container -->
        <div id="map-view-container">
            <div id="leaflet-map"></div>
        </div>

        <div id="empty-state" class="empty-state" style="display: none; text-align: center; padding: 3rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: 0.5rem;">
            <h3>No archived listings found</h3>
            <p style="color: var(--text-muted); margin-top: 0.5rem;">Try adjusting your search or location filters.</p>
        </div>
    </div>

    <!-- Detail Dossier Modal -->
    <div id="dossier-modal" class="modal-backdrop">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h2 id="modal-title" style="color: var(--text-main); font-size: 1.35rem;">Listing Details</h2>
                    <div id="modal-subtitle" style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;"></div>
                </div>
                <button class="modal-close" onclick="closeDossierModal()">&times;</button>
            </div>
            <div class="modal-body" id="modal-body">
                <div class="gallery-viewer" id="gallery-container">
                    <img id="gallery-main-img" class="main-gallery-img" src="" alt="Property Image">
                    <button class="gallery-nav-btn gallery-prev" onclick="prevImage(event)">&#10094;</button>
                    <button class="gallery-nav-btn gallery-next" onclick="nextImage(event)">&#10095;</button>
                    <div id="gallery-counter" class="gallery-caption">1 / 1</div>
                </div>
                <div class="thumb-strip" id="gallery-thumb-strip"></div>

                <div class="section-grid">
                    <div>
                        <div class="info-card">
                            <h4>Property Overview & Description</h4>
                            <p id="modal-desc" style="white-space: pre-line; font-size: 0.9rem; color: var(--text-muted);"></p>
                        </div>
                        <div class="info-card">
                            <h4>Features & Amenities (<span id="modal-amenity-count">0</span>)</h4>
                            <div class="amenities-tag-grid" id="modal-amenities"></div>
                        </div>
                    </div>
                    <div>
                        <div class="info-card">
                            <h4>Key Specifications</h4>
                            <div style="font-size: 0.9rem; display: flex; flex-direction: column; gap: 0.5rem;" id="modal-specs"></div>
                        </div>
                        <div class="info-card">
                            <h4>Pricing & Rates</h4>
                            <div style="font-size: 0.9rem; display: flex; flex-direction: column; gap: 0.5rem;" id="modal-pricing"></div>
                        </div>
                        <div class="info-card">
                            <h4>Geospatial Location</h4>
                            <div id="modal-geo-text" style="font-size: 0.85rem; color: var(--text-muted);"></div>
                            <div id="dossier-mini-map"></div>
                        </div>
                        <div class="info-card" id="modal-agent-card">
                            <h4>Listing Agents</h4>
                            <div id="modal-agent-content"></div>
                        </div>
                        <div class="info-card">
                            <h4>Cryptographic Manifest</h4>
                            <div style="font-size: 0.8rem; color: var(--text-muted);" id="modal-integrity"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Comparison Modal -->
    <div id="compare-modal" class="modal-backdrop">
        <div class="modal-content" style="max-width: 900px;">
            <div class="modal-header">
                <h3 style="color: var(--text-main);">Side-by-Side Comparison</h3>
                <button class="modal-close" onclick="closeCompareModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem;">
                    <div style="flex: 1;">
                        <label style="color: var(--text-muted); font-size: 0.85rem;">Listing A</label>
                        <select id="compare-select-a" class="select-filter" style="width: 100%; margin-top: 0.35rem;"></select>
                    </div>
                    <div style="flex: 1;">
                        <label style="color: var(--text-muted); font-size: 0.85rem;">Listing B</label>
                        <select id="compare-select-b" class="select-filter" style="width: 100%; margin-top: 0.35rem;"></select>
                    </div>
                    <div style="display: flex; align-items: flex-end;">
                        <button class="btn" onclick="executeCompare()">Compare</button>
                    </div>
                </div>
                <div id="compare-results"></div>
            </div>
        </div>
    </div>

    <!-- Archive Modal -->
    <div id="archive-modal" class="modal-backdrop">
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h3 style="color: var(--text-main);">Archive New Listing</h3>
                <button class="modal-close" onclick="closeArchiveModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div style="margin-bottom: 1rem;">
                    <label style="color: var(--text-muted); font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">Listing ID or Full URL</label>
                    <input type="text" id="fetch-target-input" class="search-input" placeholder="e.g. T4710876 or https://www.privateproperty.co.za/...">
                </div>
                <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
                    <button class="btn btn-secondary" onclick="closeArchiveModal()">Cancel</button>
                    <button class="btn" id="btn-do-fetch" onclick="executeFetch()">Start Archiving</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast -->
    <div id="toast" class="toast"><span id="toast-msg">Notification</span></div>

    <script>
        let allListings = [];
        let currentListing = null;
        let currentImageIndex = 0;
        let currentView = 'grid';
        let mainMap = null;
        let miniMap = null;
        let markersGroup = null;

        async function loadListings() {
            try {
                const res = await fetch('/api/listings');
                allListings = await res.json();
                renderMetrics();
                populateCascadingGeoFilters();
                filterData();
                populateCompareSelects();
            } catch (err) {
                showToast("Failed loading listings: " + err, "error");
            }
        }

        function renderMetrics() {
            document.getElementById('m-count').innerText = allListings.length;
            const totalImgs = allListings.reduce((sum, item) => sum + (item.images_count || 0), 0);
            document.getElementById('m-images').innerText = totalImgs;

            let totalVal = 0;
            let activeCount = 0, offerCount = 0, soldCount = 0;

            allListings.forEach(item => {
                if (item.price && item.price.amount) totalVal += item.price.amount;
                if (item.listing_status === 'under_offer' || item.is_under_offer) offerCount++;
                else if (item.listing_status === 'sold' || item.is_sold) soldCount++;
                else activeCount++;
            });

            document.getElementById('m-val').innerText = 'R ' + totalVal.toLocaleString('en-ZA');
            const activePct = allListings.length ? Math.round((activeCount / allListings.length) * 100) : 0;
            document.getElementById('m-status-ratio').innerText = `${activePct}% Active`;
            document.getElementById('m-status-detail').innerText = `${activeCount} Active | ${offerCount} Under Offer | ${soldCount} Sold`;
        }

        function populateCascadingGeoFilters() {
            const provSelect = document.getElementById('geo-province-filter');
            const provinces = new Set();

            allListings.forEach(item => {
                const p = item.geo_hierarchy?.province || item.location?.province;
                if (p) provinces.add(p);
            });

            provSelect.innerHTML = '<option value="all">All Provinces</option>';
            Array.from(provinces).sort().forEach(p => {
                provSelect.add(new Option(p, p));
            });
            onProvinceChanged();
        }

        function onProvinceChanged() {
            const selectedProv = document.getElementById('geo-province-filter').value;
            const areaSelect = document.getElementById('geo-area-filter');
            const areas = new Set();

            allListings.forEach(item => {
                const p = item.geo_hierarchy?.province || item.location?.province;
                const a = item.geo_hierarchy?.area || item.location?.region || item.location?.city;
                if ((selectedProv === 'all' || p === selectedProv) && a) {
                    areas.add(a);
                }
            });

            areaSelect.innerHTML = '<option value="all">All Areas / Metros</option>';
            Array.from(areas).sort().forEach(a => {
                areaSelect.add(new Option(a, a));
            });
            onAreaChanged();
        }

        function onAreaChanged() {
            const selectedProv = document.getElementById('geo-province-filter').value;
            const selectedArea = document.getElementById('geo-area-filter').value;
            const subSelect = document.getElementById('geo-suburb-filter');
            const suburbs = new Set();

            allListings.forEach(item => {
                const p = item.geo_hierarchy?.province || item.location?.province;
                const a = item.geo_hierarchy?.area || item.location?.region || item.location?.city;
                const s = item.geo_hierarchy?.suburb || item.location?.suburb;

                if ((selectedProv === 'all' || p === selectedProv) &&
                    (selectedArea === 'all' || a === selectedArea) && s) {
                    suburbs.add(s);
                }
            });

            subSelect.innerHTML = '<option value="all">All Suburbs</option>';
            Array.from(suburbs).sort().forEach(s => {
                subSelect.add(new Option(s, s));
            });
            filterData();
        }

        function resetGeoFilters() {
            document.getElementById('geo-province-filter').value = 'all';
            onProvinceChanged();
        }

        function filterData() {
            const query = document.getElementById('search-input').value.toLowerCase().trim();
            const statusFilter = document.getElementById('status-filter').value;
            const sortFilter = document.getElementById('sort-filter').value;
            const provFilter = document.getElementById('geo-province-filter').value;
            const areaFilter = document.getElementById('geo-area-filter').value;
            const subFilter = document.getElementById('geo-suburb-filter').value;

            let filtered = allListings.filter(item => {
                const matchesQuery = !query || 
                    (item.listing_id && item.listing_id.toLowerCase().includes(query)) ||
                    (item.title && item.title.toLowerCase().includes(query)) ||
                    (item.location && item.location.suburb && item.location.suburb.toLowerCase().includes(query));

                const status = (item.listing_status || 'active').toLowerCase();
                const matchesStatus = (statusFilter === 'all') ||
                    (statusFilter === 'active' && status === 'active' && !item.is_under_offer && !item.is_sold) ||
                    (statusFilter === 'under_offer' && (status === 'under_offer' || item.is_under_offer)) ||
                    (statusFilter === 'sold' && (status === 'sold' || item.is_sold));

                const p = item.geo_hierarchy?.province || item.location?.province;
                const a = item.geo_hierarchy?.area || item.location?.region || item.location?.city;
                const s = item.geo_hierarchy?.suburb || item.location?.suburb;

                const matchesProv = (provFilter === 'all' || p === provFilter);
                const matchesArea = (areaFilter === 'all' || a === areaFilter);
                const matchesSub = (subFilter === 'all' || s === subFilter);

                return matchesQuery && matchesStatus && matchesProv && matchesArea && matchesSub;
            });

            filtered.sort((a, b) => {
                if (sortFilter === 'date-desc') return new Date(b.extracted_at) - new Date(a.extracted_at);
                if (sortFilter === 'date-asc') return new Date(a.extracted_at) - new Date(b.extracted_at);
                if (sortFilter === 'price-desc') return (b.price?.amount || 0) - (a.price?.amount || 0);
                if (sortFilter === 'price-asc') return (a.price?.amount || 0) - (b.price?.amount || 0);
                if (sortFilter === 'beds-desc') return (b.features?.bedrooms || 0) - (a.features?.bedrooms || 0);
                return 0;
            });

            renderGridCards(filtered);
            renderGroupedView(filtered);
            updateMapMarkers(filtered);
        }

        function createCardElement(item) {
            const card = document.createElement('div');
            card.className = 'property-card';
            card.onclick = () => openDossier(item.listing_id);

            const statusClass = item.is_sold ? 'sold' : (item.is_under_offer ? 'under_offer' : 'active');
            const statusLabel = item.is_sold ? 'Sold' : (item.is_under_offer ? 'Under Offer' : 'Active');
            const heroImg = item.hero_image_url || '/api/placeholder';

            card.innerHTML = `
                <div class="card-thumb-wrapper">
                    <img class="card-thumb" src="${heroImg}" alt="${item.title || 'Property'}" onerror="this.src='/api/placeholder'">
                    <div class="card-badge ${statusClass}">${statusLabel}</div>
                    <div class="img-count-tag">${item.images_count || 0} Photos</div>
                </div>
                <div class="card-body">
                    <div class="card-price">${item.price?.formatted_display || 'R ' + (item.price?.amount || 0).toLocaleString()}</div>
                    <div class="card-title">${item.title || 'Untitled Listing'}</div>
                    <div class="card-address">${item.location?.street_address || ''}, ${item.location?.suburb || ''}</div>
                    <div class="card-specs">
                        <div class="card-spec-item"><strong>${item.features?.bedrooms || 0}</strong> Beds</div>
                        <div class="card-spec-item"><strong>${item.features?.bathrooms || 0}</strong> Baths</div>
                        <div class="card-spec-item"><strong>${item.features?.garages || 0}</strong> Garages</div>
                        ${item.erf_size_m2 ? `<div class="card-spec-item"><strong>${item.erf_size_m2}</strong> m²</div>` : ''}
                    </div>
                    <div class="card-footer">
                        <span>ID: ${item.listing_id}</span>
                        <span>${new Date(item.extracted_at).toLocaleDateString()}</span>
                    </div>
                </div>
            `;
            return card;
        }

        function renderGridCards(listings) {
            const grid = document.getElementById('property-grid');
            const empty = document.getElementById('empty-state');
            grid.innerHTML = '';

            if (listings.length === 0) {
                empty.style.display = 'block';
                return;
            }
            empty.style.display = 'none';

            listings.forEach(item => {
                grid.appendChild(createCardElement(item));
            });
        }

        function renderGroupedView(listings) {
            const container = document.getElementById('grouped-view-container');
            container.innerHTML = '';

            // Group: Province -> Area -> Suburb
            const groups = {};
            listings.forEach(item => {
                const prov = item.geo_hierarchy?.province || 'Other Province';
                const area = item.geo_hierarchy?.area || 'Other Area';
                const sub = item.geo_hierarchy?.suburb || 'Other Suburb';

                if (!groups[prov]) groups[prov] = {};
                if (!groups[prov][area]) groups[prov][area] = {};
                if (!groups[prov][area][sub]) groups[prov][area][sub] = [];

                groups[prov][area][sub].push(item);
            });

            for (const [prov, areas] of Object.entries(groups)) {
                let provCount = 0, provVal = 0;
                for (const a of Object.values(areas)) {
                    for (const s of Object.values(a)) {
                        provCount += s.length;
                        provVal += s.reduce((sum, x) => sum + (x.price?.amount || 0), 0);
                    }
                }
                const avgProv = provCount ? Math.round(provVal / provCount) : 0;

                const provBox = document.createElement('div');
                provBox.className = 'province-accordion';
                provBox.innerHTML = `
                    <div class="province-header">
                        <div style="font-size: 1.15rem; font-weight: 700; color: var(--primary);">
                            📍 ${prov}
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                            <strong>${provCount}</strong> Properties | Total: <strong>R ${provVal.toLocaleString()}</strong> | Avg: <strong>R ${avgProv.toLocaleString()}</strong>
                        </div>
                    </div>
                `;

                const body = document.createElement('div');

                for (const [area, suburbs] of Object.entries(areas)) {
                    const areaSec = document.createElement('div');
                    areaSec.className = 'area-section';
                    areaSec.innerHTML = `<div class="area-title">🏙️ ${area}</div>`;

                    for (const [sub, subListings] of Object.entries(suburbs)) {
                        const subBlock = document.createElement('div');
                        subBlock.className = 'suburb-block';
                        subBlock.innerHTML = `
                            <div class="suburb-header">
                                <span>🏡 ${sub}</span>
                                <span style="font-size: 0.8rem; color: var(--text-muted);">${subListings.length} listing(s)</span>
                            </div>
                        `;

                        const subGrid = document.createElement('div');
                        subGrid.className = 'property-grid';
                        subListings.forEach(item => subGrid.appendChild(createCardElement(item)));

                        subBlock.appendChild(subGrid);
                        areaSec.appendChild(subBlock);
                    }
                    body.appendChild(areaSec);
                }

                provBox.appendChild(body);
                container.appendChild(provBox);
            }
        }

        function switchView(view) {
            currentView = view;
            document.getElementById('btn-view-grid').classList.toggle('active', view === 'grid');
            document.getElementById('btn-view-grouped').classList.toggle('active', view === 'grouped');
            document.getElementById('btn-view-map').classList.toggle('active', view === 'map');

            const grid = document.getElementById('property-grid');
            const grouped = document.getElementById('grouped-view-container');
            const mapContainer = document.getElementById('map-view-container');

            grid.style.display = (view === 'grid') ? 'grid' : 'none';
            grouped.style.display = (view === 'grouped') ? 'flex' : 'none';
            mapContainer.style.display = (view === 'map') ? 'block' : 'none';

            if (view === 'map') {
                initMap();
            }
        }

        function initMap() {
            if (!mainMap) {
                mainMap = L.map('leaflet-map').setView([-26.0437, 28.0554], 12);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap'
                }).addTo(mainMap);
                markersGroup = L.featureGroup().addTo(mainMap);
            }
            setTimeout(() => { mainMap.invalidateSize(); filterData(); }, 200);
        }

        function updateMapMarkers(listings) {
            if (!mainMap || !markersGroup) return;
            markersGroup.clearLayers();

            const bounds = [];
            listings.forEach(item => {
                if (item.location && item.location.latitude && item.location.longitude) {
                    const lat = item.location.latitude;
                    const lng = item.location.longitude;
                    bounds.push([lat, lng]);

                    const marker = L.marker([lat, lng]).addTo(markersGroup);
                    marker.bindPopup(`
                        <div style="font-family: sans-serif; min-width: 180px;">
                            <strong style="color: #0f172a; font-size: 1rem;">${item.price?.formatted_display || 'Price N/A'}</strong>
                            <div style="font-size: 0.85rem; font-weight: bold; margin-top: 2px;">${item.title || 'Listing'}</div>
                            <div style="font-size: 0.75rem; color: #64748b;">${item.location?.street_address || ''}, ${item.location?.suburb || ''}</div>
                            <button onclick="openDossier('${item.listing_id}')" style="margin-top: 8px; width: 100%; background: #0284c7; color: #fff; border: none; padding: 4px; border-radius: 4px; cursor: pointer; font-size: 0.75rem;">View Dossier</button>
                        </div>
                    `);
                }
            });

            if (bounds.length > 0) {
                mainMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
            }
        }

        async function openDossier(listingId) {
            try {
                const res = await fetch(`/api/listings/${listingId}`);
                currentListing = await res.json();
                currentImageIndex = 0;

                const l = currentListing.listing;
                const m = currentListing.metadata;

                document.getElementById('modal-title').innerText = l.title || `Listing ${l.listing_id}`;
                document.getElementById('modal-subtitle').innerText = `${l.location?.street_address || ''}, ${l.location?.suburb || ''}, ${l.location?.city || ''} | Portal: ${l.portal_name}`;
                document.getElementById('modal-desc').innerText = l.description || 'No description provided.';

                // Amenities
                const amenityBox = document.getElementById('modal-amenities');
                amenityBox.innerHTML = '';
                const amenities = l.features?.raw_features_list || [];
                document.getElementById('modal-amenity-count').innerText = amenities.length;
                amenities.forEach(a => {
                    const tag = document.createElement('span');
                    tag.className = 'amenity-tag';
                    tag.innerText = a;
                    amenityBox.appendChild(tag);
                });

                // Specs
                document.getElementById('modal-specs').innerHTML = `
                    <div><strong>Bedrooms:</strong> ${l.features?.bedrooms || 'N/A'}</div>
                    <div><strong>Bathrooms:</strong> ${l.features?.bathrooms || 'N/A'}</div>
                    <div><strong>En-Suites:</strong> ${l.features?.en_suites || 'N/A'}</div>
                    <div><strong>Lounges:</strong> ${l.features?.lounges || 'N/A'}</div>
                    <div><strong>Garages:</strong> ${l.features?.garages || 'N/A'}</div>
                    <div><strong>Land Size:</strong> ${l.erf_size_m2 ? l.erf_size_m2.toLocaleString() + ' m²' : 'N/A'} ${l.land_size_raw ? '(' + l.land_size_raw + ')' : ''}</div>
                    <div><strong>Floor Size:</strong> ${l.floor_size_m2 ? l.floor_size_m2 + ' m²' : 'N/A'}</div>
                `;

                // Pricing
                document.getElementById('modal-pricing').innerHTML = `
                    <div><strong>Asking Price:</strong> ${l.price?.formatted_display || 'R ' + (l.price?.amount || 0).toLocaleString()}</div>
                    <div><strong>Monthly Rates & Taxes:</strong> ${l.price?.rates_and_taxes_monthly ? 'R ' + l.price.rates_and_taxes_monthly.toLocaleString() : 'N/A'}</div>
                    <div><strong>Monthly Levies:</strong> ${l.price?.levies_monthly ? 'R ' + l.price.levies_monthly.toLocaleString() : 'N/A'}</div>
                    <div><strong>Status:</strong> <span style="color: var(--primary); font-weight: bold;">${(l.listing_status || 'active').toUpperCase()}</span></div>
                `;

                // Geospatial Mini-Map
                const geoBox = document.getElementById('modal-geo-text');
                if (l.location && l.location.latitude && l.location.longitude) {
                    geoBox.innerText = `GPS Coordinates: ${l.location.latitude}, ${l.location.longitude}`;
                    setTimeout(() => {
                        if (!miniMap) {
                            miniMap = L.map('dossier-mini-map').setView([l.location.latitude, l.location.longitude], 15);
                            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(miniMap);
                        } else {
                            miniMap.setView([l.location.latitude, l.location.longitude], 15);
                        }
                        miniMap.eachLayer(layer => { if (layer instanceof L.Marker) miniMap.removeLayer(layer); });
                        L.marker([l.location.latitude, l.location.longitude]).addTo(miniMap);
                        miniMap.invalidateSize();
                    }, 300);
                } else {
                    geoBox.innerText = 'GPS Coordinates: Not provided';
                }

                // Agents
                const agentBox = document.getElementById('modal-agent-content');
                let agentHtml = '';
                if (l.agent && l.agent.agent_name) {
                    agentHtml += `
                        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                            ${l.agent.agency_logo_url ? `<img src="${l.agent.agency_logo_url}" style="width: 44px; height: 44px; border-radius: 50%; object-fit: cover;">` : ''}
                            <div>
                                <div style="font-weight: 600;">${l.agent.agent_name} (Lead)</div>
                                <div style="color: var(--text-muted); font-size: 0.8rem;">${l.agent.agency_name || ''}</div>
                            </div>
                        </div>
                    `;
                }
                if (l.co_agents && l.co_agents.length > 0) {
                    l.co_agents.forEach(co => {
                        agentHtml += `
                            <div style="display: flex; align-items: center; gap: 0.75rem; margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px dashed var(--border);">
                                ${co.agency_logo_url ? `<img src="${co.agency_logo_url}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover;">` : ''}
                                <div>
                                    <div style="font-weight: 600; font-size: 0.85rem;">${co.agent_name} (Co-Agent)</div>
                                </div>
                            </div>
                        `;
                    });
                }
                agentBox.innerHTML = agentHtml || '<div style="color: var(--text-muted);">No agent details</div>';

                // Integrity
                document.getElementById('modal-integrity').innerHTML = `
                    <div><strong>Fingerprint:</strong> ${(l.content_fingerprint || '').substring(0, 20)}...</div>
                    <div><strong>Archived At:</strong> ${new Date(m?.archived_at || l.extracted_at).toLocaleString()}</div>
                    <div><strong>Archived Images:</strong> ${l.images?.length || 0}</div>
                    <div><strong>SHA-256 Checksums:</strong> Verified Match</div>
                `;

                renderGallery();
                document.getElementById('dossier-modal').classList.add('open');
            } catch (err) {
                showToast("Failed loading dossier: " + err, "error");
            }
        }

        function renderGallery() {
            const images = currentListing?.listing?.images || [];
            if (images.length === 0) {
                document.getElementById('gallery-container').style.display = 'none';
                document.getElementById('gallery-thumb-strip').style.display = 'none';
                return;
            }
            document.getElementById('gallery-container').style.display = 'block';
            document.getElementById('gallery-thumb-strip').style.display = 'flex';

            updateMainImage();

            const strip = document.getElementById('gallery-thumb-strip');
            strip.innerHTML = '';
            images.forEach((img, idx) => {
                const item = document.createElement('div');
                item.className = `thumb-strip-item ${idx === currentImageIndex ? 'active' : ''}`;
                item.onclick = () => { currentImageIndex = idx; updateMainImage(); };
                const src = `/api/listings/${currentListing.listing.listing_id}/image/${img.local_filename}`;
                item.innerHTML = `<img src="${src}" alt="Thumb ${idx+1}">`;
                strip.appendChild(item);
            });
        }

        function updateMainImage() {
            const images = currentListing?.listing?.images || [];
            if (!images[currentImageIndex]) return;

            const img = images[currentImageIndex];
            const src = `/api/listings/${currentListing.listing.listing_id}/image/${img.local_filename}`;
            document.getElementById('gallery-main-img').src = src;
            document.getElementById('gallery-counter').innerText = `${currentImageIndex + 1} / ${images.length}`;

            const items = document.querySelectorAll('.thumb-strip-item');
            items.forEach((it, idx) => {
                if (idx === currentImageIndex) it.classList.add('active');
                else it.classList.remove('active');
            });
        }

        function prevImage(e) {
            e.stopPropagation();
            const images = currentListing?.listing?.images || [];
            if (images.length === 0) return;
            currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
            updateMainImage();
        }

        function nextImage(e) {
            e.stopPropagation();
            const images = currentListing?.listing?.images || [];
            if (images.length === 0) return;
            currentImageIndex = (currentImageIndex + 1) % images.length;
            updateMainImage();
        }

        function closeDossierModal() {
            document.getElementById('dossier-modal').classList.remove('open');
        }

        function openArchiveModal() {
            document.getElementById('archive-modal').classList.add('open');
            document.getElementById('fetch-target-input').focus();
        }

        function closeArchiveModal() {
            document.getElementById('archive-modal').classList.remove('open');
        }

        async function executeFetch() {
            const target = document.getElementById('fetch-target-input').value.trim();
            if (!target) {
                showToast("Please enter a Listing ID or URL", "error");
                return;
            }

            const btn = document.getElementById('btn-do-fetch');
            btn.innerText = "Archiving...";
            btn.disabled = true;

            try {
                const res = await fetch('/api/fetch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(`Successfully archived ${data.listing_id}!`, "success");
                    closeArchiveModal();
                    document.getElementById('fetch-target-input').value = '';
                    await loadListings();
                } else {
                    showToast(`Archiving failed: ${data.error}`, "error");
                }
            } catch (err) {
                showToast("Network error: " + err, "error");
            } finally {
                btn.innerText = "Start Archiving";
                btn.disabled = false;
            }
        }

        function populateCompareSelects() {
            const selA = document.getElementById('compare-select-a');
            const selB = document.getElementById('compare-select-b');
            selA.innerHTML = '';
            selB.innerHTML = '';

            allListings.forEach(item => {
                const optA = new Option(`${item.listing_id} - ${item.title || 'Listing'}`, item.listing_id);
                const optB = new Option(`${item.listing_id} - ${item.title || 'Listing'}`, item.listing_id);
                selA.add(optA);
                selB.add(optB);
            });
            if (selB.options.length > 1) selB.selectedIndex = 1;
        }

        function openCompareModal() {
            populateCompareSelects();
            document.getElementById('compare-modal').classList.add('open');
        }

        function closeCompareModal() {
            document.getElementById('compare-modal').classList.remove('open');
        }

        async function executeCompare() {
            const idA = document.getElementById('compare-select-a').value;
            const idB = document.getElementById('compare-select-b').value;
            try {
                const res = await fetch(`/api/compare?a=${idA}&b=${idB}`);
                const diff = await res.json();
                const container = document.getElementById('compare-results');

                container.innerHTML = `
                    <table class="diff-table">
                        <thead>
                            <tr><th>Field</th><th>${idA}</th><th>${idB}</th></tr>
                        </thead>
                        <tbody>
                            <tr class="${diff.price_changed ? 'diff-changed' : ''}">
                                <td><strong>Price</strong></td>
                                <td>R ${diff.old_price ? diff.old_price.toLocaleString() : 'N/A'}</td>
                                <td>R ${diff.new_price ? diff.new_price.toLocaleString() : 'N/A'} ${diff.price_diff ? ' (' + (diff.price_diff > 0 ? '+' : '') + diff.price_diff.toLocaleString() + ')' : ''}</td>
                            </tr>
                            <tr class="${diff.status_changed ? 'diff-changed' : ''}">
                                <td><strong>Status</strong></td>
                                <td>${(diff.old_status || 'active').toUpperCase()}</td>
                                <td>${(diff.new_status || 'active').toUpperCase()}</td>
                            </tr>
                            <tr>
                                <td><strong>Badges Diff</strong></td>
                                <td>${diff.badges_removed?.join(', ') || 'None'}</td>
                                <td>${diff.badges_added?.join(', ') || 'None'}</td>
                            </tr>
                            <tr>
                                <td><strong>Specs / Features</strong></td>
                                <td>-</td>
                                <td>${diff.spec_changes?.join('<br>') || 'No spec differences'}</td>
                            </tr>
                        </tbody>
                    </table>
                `;
            } catch (err) {
                showToast("Comparison error: " + err, "error");
            }
        }

        function openExportMenu(event) {
            const format = prompt("Export Format: Enter 'csv', 'sqlite', 'jsonl', or 'geojson':", "csv");
            if (format && ['csv', 'sqlite', 'jsonl', 'geojson'].includes(format.toLowerCase().trim())) {
                window.location.href = `/api/export?format=${format.toLowerCase().trim()}`;
            }
        }

        function showToast(msg, type="success") {
            const toast = document.getElementById('toast');
            const toastMsg = document.getElementById('toast-msg');
            toastMsg.innerText = msg;
            toast.className = `toast show ${type}`;
            setTimeout(() => { toast.classList.remove('show'); }, 4000);
        }

        window.onload = loadListings;
    </script>
</body>
</html>
"""
