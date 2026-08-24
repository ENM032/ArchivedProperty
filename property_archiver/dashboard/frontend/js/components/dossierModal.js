/**
 * Property Detail Dossier Modal Component.
 */
import { fetchListingDetails } from '../api/apiClient.js';
import { formatZAR, formatDate } from '../utils/formatters.js';
import { showToast } from '../utils/dom.js';
import { initGallery } from './gallery.js';

let dossierMiniMap = null;

export async function openDossier(listingId) {
    try {
        const data = await fetchListingDetails(listingId);
        renderDossierModal(data);
    } catch (err) {
        showToast("Failed loading listing dossier: " + err.message, "error");
    }
}

function renderDossierModal(data) {
    const container = document.getElementById('dossier-modal-container');
    const l = data.listing;
    const m = data.metadata;

    container.innerHTML = `
        <div id="dossier-modal" class="modal-backdrop open">
            <div class="modal-content">
                <div class="modal-header">
                    <div>
                        <h2 style="font-size: 1.35rem;">${l.title || 'Listing ' + l.listing_id}</h2>
                        <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">
                            ${l.location?.street_address || ''}, ${l.location?.suburb || ''}, ${l.location?.city || ''} | Portal: ${l.portal_name}
                        </div>
                    </div>
                    <button class="modal-close" id="btn-close-dossier">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="gallery-viewer" id="gallery-container">
                        <img id="gallery-main-img" class="main-gallery-img" src="" alt="Property Photo">
                        <button id="gallery-prev-btn" class="gallery-nav-btn gallery-prev">&#10094;</button>
                        <button id="gallery-next-btn" class="gallery-nav-btn gallery-next">&#10095;</button>
                        <div id="gallery-counter" class="gallery-caption">1 / 1</div>
                    </div>
                    <div class="thumb-strip" id="gallery-thumb-strip"></div>

                    <div class="section-grid">
                        <div>
                            <div class="info-card">
                                <h4>Property Overview & Description</h4>
                                <p style="white-space: pre-line; font-size: 0.9rem; color: var(--text-muted);">${l.description || 'No description provided.'}</p>
                            </div>
                            <div class="info-card">
                                <h4>Features & Amenities (${l.features?.raw_features_list?.length || 0})</h4>
                                <div class="amenities-tag-grid">
                                    ${(l.features?.raw_features_list || []).map(a => `<span class="amenity-tag">${a}</span>`).join('')}
                                </div>
                            </div>
                        </div>
                        <div>
                            <div class="info-card">
                                <h4>Key Specifications</h4>
                                <div style="font-size: 0.9rem; display: flex; flex-direction: column; gap: 0.5rem;">
                                    <div><strong>Type:</strong> ${l.property_type || 'N/A'} (${l.listing_type === 'to_rent' ? 'To Rent' : 'For Sale'})</div>
                                    <div><strong>Bedrooms:</strong> ${l.features?.bedrooms || 'N/A'}</div>
                                    <div><strong>Bathrooms:</strong> ${l.features?.bathrooms || 'N/A'}</div>
                                    <div><strong>Garages:</strong> ${l.features?.garages || 'N/A'}</div>
                                    <div><strong>Land Size:</strong> ${l.erf_size_m2 ? l.erf_size_m2.toLocaleString() + ' m²' : 'N/A'} ${l.land_size_raw ? '(' + l.land_size_raw + ')' : ''}</div>
                                </div>
                            </div>
                            <div class="info-card">
                                <h4>Pricing & Rates</h4>
                                <div style="font-size: 0.9rem; display: flex; flex-direction: column; gap: 0.5rem;">
                                    <div><strong>Asking Price:</strong> ${formatZAR(l.price?.amount)}</div>
                                    <div><strong>Rates & Taxes:</strong> ${l.price?.rates_and_taxes_monthly ? formatZAR(l.price.rates_and_taxes_monthly) + '/mo' : 'N/A'}</div>
                                    <div><strong>Levies:</strong> ${l.price?.levies_monthly ? formatZAR(l.price.levies_monthly) + '/mo' : 'N/A'}</div>
                                    <div><strong>Status:</strong> <span style="color: var(--primary); font-weight: bold;">${(l.listing_status || 'active').toUpperCase()}</span></div>
                                </div>
                            </div>
                            <div class="info-card">
                                <h4>Geospatial Coordinates</h4>
                                <div style="font-size: 0.85rem; color: var(--text-muted);">
                                    ${l.location?.latitude ? `GPS: ${l.location.latitude}, ${l.location.longitude}` : 'GPS coordinates not provided'}
                                </div>
                                <div id="dossier-mini-map"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('btn-close-dossier').onclick = () => {
        container.innerHTML = '';
    };

    initGallery(l.listing_id, l.images);

    if (l.location && l.location.latitude && l.location.longitude) {
        setTimeout(() => {
            dossierMiniMap = L.map('dossier-mini-map').setView([l.location.latitude, l.location.longitude], 15);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(dossierMiniMap);
            L.marker([l.location.latitude, l.location.longitude]).addTo(dossierMiniMap);
        }, 200);
    }
}
