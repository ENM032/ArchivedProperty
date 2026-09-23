/**
 * Leaflet GIS Interactive Map View with Custom Price Badges, Multi-Layer Satellite Switcher,
 * Leaflet.markercluster with Spiderfy, Split-Pane List Sync, and Suburb Centroid Fallback.
 */
import { formatZAR, formatCompactZAR } from '../utils/formatters.js';
import { openDossier } from '../components/dossierModal.js';
import { getFallbackCoordinates } from '../data/suburbCentroids.js';

let mapInstance = null;
let clusterGroup = null;
let baseLayersControl = null;
let currentRenderedListings = [];
let markerRegistry = new Map(); // listing_id -> marker

export function renderMapView(listings) {
    const mapContainer = document.getElementById('map-view-container');
    if (!mapContainer) return;

    currentRenderedListings = listings || [];

    if (!mapInstance) {
        // Step 1: Define Multi-Layer Basemaps (Street, High-Resolution Satellite, Dark Canvas)
        const streetLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        });

        const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
            maxZoom: 19
        });

        const darkLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            maxZoom: 19
        });

        mapInstance = L.map('leaflet-map', {
            preferCanvas: true,
            layers: [streetLayer]
        }).setView([-29.0, 24.5], 6);

        const baseMaps = {
            "🗺️ Street Map": streetLayer,
            "🛰️ Satellite (Esri)": satelliteLayer,
            "🌙 Dark Mode": darkLayer
        };

        baseLayersControl = L.control.layers(baseMaps, null, { position: 'topright' }).addTo(mapInstance);

        // Step 2: Initialize Marker Cluster Group with Spiderfy
        if (typeof L.markerClusterGroup === 'function') {
            clusterGroup = L.markerClusterGroup({
                showCoverageOnHover: false,
                maxClusterRadius: 40,
                spiderfyOnMaxZoom: true,
                disableClusteringAtZoom: 17,
                iconCreateFunction: (cluster) => {
                    const count = cluster.getChildCount();
                    const isLarge = count >= 50;
                    return L.divIcon({
                        html: `<div class="custom-cluster-badge ${isLarge ? 'cluster-large' : ''}"><span>${count}</span></div>`,
                        className: 'custom-cluster-icon',
                        iconSize: [isLarge ? 44 : 38, isLarge ? 44 : 38]
                    });
                }
            });
            mapInstance.addLayer(clusterGroup);
        } else {
            clusterGroup = L.layerGroup().addTo(mapInstance);
        }

        // Viewport bounds filter listener
        mapInstance.on('moveend', () => {
            const chk = document.getElementById('chk-search-in-bounds');
            if (chk && chk.checked) {
                updateVisibleSidePanel();
            }
        });

        const boundsCheckbox = document.getElementById('chk-search-in-bounds');
        if (boundsCheckbox) {
            boundsCheckbox.onchange = () => updateVisibleSidePanel();
        }
    } else {
        setTimeout(() => mapInstance.invalidateSize(), 100);
    }

    // Clear previous markers
    if (clusterGroup) {
        clusterGroup.clearLayers();
    }
    markerRegistry.clear();

    const validCoordinates = [];

    currentRenderedListings.forEach(item => {
        let lat = item.location?.latitude;
        let lng = item.location?.longitude;

        // Fallback to Suburb Centroid Geocoder if GPS is missing from portal
        if (!lat || !lng || isNaN(lat) || isNaN(lng)) {
            const fallback = getFallbackCoordinates(item);
            if (fallback) {
                lat = fallback[0];
                lng = fallback[1];
            }
        }

        if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
            validCoordinates.push([lat, lng]);
            item._computed_coords = [lat, lng];

            const statusClass = item.is_sold ? 'sold' : (item.is_under_offer ? 'under_offer' : 'active');
            const heroImg = item.hero_image_url || '/api/placeholder';
            const priceText = formatCompactZAR(item.price?.amount);

            // Custom HTML Price Pill Pin (Zillow/Airbnb Style)
            const iconHtml = `
                <div class="map-price-chip ${statusClass}" id="map-chip-${item.listing_id}">
                    <span class="status-dot"></span>
                    <span>${priceText}</span>
                </div>
            `;

            const customIcon = L.divIcon({
                className: 'custom-map-pin',
                html: iconHtml,
                iconSize: [85, 28],
                iconAnchor: [42, 14],
                popupAnchor: [0, -16]
            });

            const popupContent = `
                <div style="width: 220px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                    <img src="${heroImg}" 
                         loading="lazy" 
                         decoding="async" 
                         style="width: 100%; height: 110px; object-fit: cover; border-radius: 4px; margin-bottom: 0.5rem;" 
                         onerror="this.src='/api/placeholder'">
                    <div style="font-weight: 700; font-size: 1rem; color: #000814; margin-bottom: 0.25rem;">
                        ${formatZAR(item.price?.amount)}
                    </div>
                    <div style="font-weight: 600; font-size: 0.85rem; color: #001d3d; margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        ${item.title || 'Property'}
                    </div>
                    <div style="font-size: 0.75rem; color: #5a6a80; margin-bottom: 0.5rem;">
                        ${item.location?.suburb || ''}, ${item.location?.region || item.location?.city || ''}
                    </div>
                    <button onclick="window._openDossierFromMap('${item.listing_id}')" 
                            style="width: 100%; background: #003566; color: #ffffff; border: none; padding: 0.4rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; cursor: pointer;">
                        View Dossier
                    </button>
                </div>
            `;

            const marker = L.marker([lat, lng], { icon: customIcon }).bindPopup(popupContent);
            clusterGroup.addLayer(marker);
            markerRegistry.set(item.listing_id, marker);
        }
    });

    if (validCoordinates.length > 0) {
        const bounds = L.latLngBounds(validCoordinates);
        mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }

    updateVisibleSidePanel();
}

function updateVisibleSidePanel() {
    const listContainer = document.getElementById('map-side-list');
    const countBadge = document.getElementById('map-visible-count');
    const chk = document.getElementById('chk-search-in-bounds');
    if (!listContainer) return;

    listContainer.innerHTML = '';

    let visibleItems = currentRenderedListings;
    if (mapInstance && chk && chk.checked) {
        const bounds = mapInstance.getBounds();
        visibleItems = currentRenderedListings.filter(item => {
            if (!item._computed_coords) return false;
            return bounds.contains(item._computed_coords);
        });
    }

    if (countBadge) {
        countBadge.innerText = `${visibleItems.length} properties`;
    }

    if (visibleItems.length === 0) {
        listContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 2rem 1rem;">No properties visible in current map view. Pan or zoom out to see more.</div>';
        return;
    }

    const fragment = document.createDocumentFragment();
    visibleItems.slice(0, 50).forEach(item => {
        const card = document.createElement('div');
        card.className = 'map-compact-card';
        card.id = `side-card-${item.listing_id}`;
        card.onclick = () => openDossier(item.listing_id);

        card.onmouseenter = () => {
            const chip = document.getElementById(`map-chip-${item.listing_id}`);
            if (chip) chip.classList.add('highlighted');
        };
        card.onmouseleave = () => {
            const chip = document.getElementById(`map-chip-${item.listing_id}`);
            if (chip) chip.classList.remove('highlighted');
        };

        const heroImg = item.hero_image_url || '/api/placeholder';
        card.innerHTML = `
            <img class="map-compact-thumb" src="${heroImg}" loading="lazy" decoding="async" alt="${item.title || 'Property'}" onerror="this.src='/api/placeholder'">
            <div class="map-compact-details">
                <div class="map-compact-price">${formatZAR(item.price?.amount)}</div>
                <div class="map-compact-title">${item.title || 'Property'}</div>
                <div class="map-compact-sub">${item.location?.suburb || ''} | ${item.features?.bedrooms || 0}b/${item.features?.bathrooms || 0}ba</div>
            </div>
        `;
        fragment.appendChild(card);
    });

    listContainer.appendChild(fragment);
}

// Global hook for popup action
window._openDossierFromMap = (id) => {
    openDossier(id);
};

export const initMap = renderMapView;
export const updateMapMarkers = renderMapView;
