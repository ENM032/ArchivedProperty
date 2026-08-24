/**
 * Interactive Leaflet GIS Map View Renderer.
 */
import { formatZAR } from '../utils/formatters.js';
import { openDossier } from '../components/dossierModal.js';

let mainMap = null;
let markersGroup = null;

export function initMap() {
    if (!mainMap) {
        mainMap = L.map('leaflet-map').setView([-26.0437, 28.0554], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(mainMap);
        markersGroup = L.featureGroup().addTo(mainMap);
    }
    setTimeout(() => { mainMap.invalidateSize(); }, 200);
}

export function updateMapMarkers(listings) {
    if (!mainMap || !markersGroup) return;
    markersGroup.clearLayers();

    const bounds = [];
    listings.forEach(item => {
        if (item.location && item.location.latitude && item.location.longitude) {
            const lat = item.location.latitude;
            const lng = item.location.longitude;
            bounds.push([lat, lng]);

            const marker = L.marker([lat, lng]).addTo(markersGroup);
            const popupDiv = document.createElement('div');
            popupDiv.style.fontFamily = 'sans-serif';
            popupDiv.style.minWidth = '180px';
            popupDiv.innerHTML = `
                <strong style="color: #0f172a; font-size: 1rem;">${formatZAR(item.price?.amount)}</strong>
                <div style="font-size: 0.85rem; font-weight: bold; margin-top: 2px;">${item.title || 'Listing'}</div>
                <div style="font-size: 0.75rem; color: #64748b;">${item.location?.street_address || ''}, ${item.location?.suburb || ''}</div>
            `;
            const btn = document.createElement('button');
            btn.innerText = 'View Dossier';
            btn.style.cssText = 'margin-top: 8px; width: 100%; background: #0284c7; color: #fff; border: none; padding: 4px; border-radius: 4px; cursor: pointer; font-size: 0.75rem;';
            btn.onclick = () => openDossier(item.listing_id);
            popupDiv.appendChild(btn);

            marker.bindPopup(popupDiv);
        }
    });

    if (bounds.length > 0) {
        mainMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
}
