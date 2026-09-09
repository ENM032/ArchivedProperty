/**
 * Leaflet GIS Interactive Map View Renderer with LayerGroup Marker Batching.
 */
import { formatZAR } from '../utils/formatters.js';
import { openDossier } from '../components/dossierModal.js';

let mapInstance = null;
let markersLayer = null;

export function renderMapView(listings) {
    const mapContainer = document.getElementById('map-view-container');
    if (!mapContainer) return;

    if (!mapInstance) {
        // Initialize Leaflet Map centered on South Africa
        mapInstance = L.map('map-view-container', {
            preferCanvas: true,
        }).setView([-29.0, 24.5], 6);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(mapInstance);

        markersLayer = L.layerGroup().addTo(mapInstance);
    } else {
        setTimeout(() => mapInstance.invalidateSize(), 100);
    }

    // Clear previous markers layer atomically
    if (markersLayer) {
        markersLayer.clearLayers();
    }

    const validCoordinates = [];

    listings.forEach(item => {
        const lat = item.location?.latitude;
        const lng = item.location?.longitude;

        if (lat && lng && !isNaN(lat) && !isNaN(lng)) {
            validCoordinates.push([lat, lng]);

            const statusClass = item.is_sold ? 'sold' : (item.is_under_offer ? 'under_offer' : 'active');
            const statusLabel = item.is_sold ? 'Sold' : (item.is_under_offer ? 'Under Offer' : 'Active');
            const heroImg = item.hero_image_url || '/api/placeholder';

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

            const marker = L.marker([lat, lng]).bindPopup(popupContent);
            markersLayer.addLayer(marker);
        }
    });

    if (validCoordinates.length > 0) {
        const bounds = L.latLngBounds(validCoordinates);
        mapInstance.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }
}

// Global hook for popup action
window._openDossierFromMap = (id) => {
    openDossier(id);
};
