/**
 * Property Detail Dossier Modal with Edit, Annotate, and Delete Actions.
 */
import { fetchListingDetails, deleteListingApi, updateListingApi } from '../api/apiClient.js';
import { formatZAR, formatDate } from '../utils/formatters.js';
import { showToast } from '../utils/dom.js';
import { store } from '../state/store.js';
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
    const history = data.history || [];

    const userTags = l.user_tags || [];
    const userRating = l.user_rating || 0;
    const userNotes = l.user_notes || '';

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
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <button id="btn-toggle-edit" class="btn btn-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.8rem;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                            Edit / Annotate
                        </button>
                        <button id="btn-delete-listing" class="btn btn-danger" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; background-color: var(--accent-red); color: white;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            Delete
                        </button>
                        <button class="modal-close" id="btn-close-dossier">&times;</button>
                    </div>
                </div>
                <div class="modal-body">
                    <!-- Inline Edit Drawer -->
                    <div id="edit-drawer" style="display: none; background-color: #1e293b; border: 1px solid var(--primary); border-radius: var(--radius-md); padding: 1.25rem; margin-bottom: 1.5rem;">
                        <h4 style="color: var(--primary); font-size: 1rem; margin-bottom: 1rem;">Edit Status & Annotations</h4>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
                            <div>
                                <label style="display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.35rem;">Listing Lifecycle Status</label>
                                <select id="edit-status-select" class="select-filter" style="width: 100%;">
                                    <option value="active" ${l.listing_status === 'active' ? 'selected' : ''}>Active</option>
                                    <option value="under_offer" ${l.listing_status === 'under_offer' ? 'selected' : ''}>Under Offer</option>
                                    <option value="sold" ${l.listing_status === 'sold' ? 'selected' : ''}>Sold</option>
                                    <option value="withdrawn" ${l.listing_status === 'withdrawn' ? 'selected' : ''}>Withdrawn</option>
                                </select>
                            </div>
                            <div>
                                <label style="display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.35rem;">Star Rating (1 to 5)</label>
                                <select id="edit-rating-select" class="select-filter" style="width: 100%;">
                                    <option value="" ${!userRating ? 'selected' : ''}>No Rating</option>
                                    <option value="1" ${userRating === 1 ? 'selected' : ''}>★ (1 Star)</option>
                                    <option value="2" ${userRating === 2 ? 'selected' : ''}>★★ (2 Stars)</option>
                                    <option value="3" ${userRating === 3 ? 'selected' : ''}>★★★ (3 Stars)</option>
                                    <option value="4" ${userRating === 4 ? 'selected' : ''}>★★★★ (4 Stars)</option>
                                    <option value="5" ${userRating === 5 ? 'selected' : ''}>★★★★★ (5 Stars)</option>
                                </select>
                            </div>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.35rem;">Custom Tags (comma-separated)</label>
                            <input type="text" id="edit-tags-input" class="search-input" value="${userTags.join(', ')}" placeholder="e.g. Shortlisted, High ROI, Good Rental Yield">
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.35rem;">Private Notes</label>
                            <textarea id="edit-notes-input" class="search-input" rows="3" placeholder="Add custom notes about this property...">${userNotes}</textarea>
                        </div>
                        <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
                            <button id="btn-cancel-edit" class="btn btn-secondary">Cancel</button>
                            <button id="btn-save-edit" class="btn btn-primary">Save Changes</button>
                        </div>
                    </div>

                    <!-- User Notes & Tags Section -->
                    <div class="info-card" id="user-annotations-card" style="${(userNotes || userTags.length > 0 || userRating > 0) ? 'display:block;' : 'display:none;'}">
                        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 0.35rem; margin-bottom: 0.75rem;">
                            <h4 style="color: var(--primary); margin: 0; border: none; padding: 0;">User Annotations</h4>
                            <div style="color: var(--accent-amber); font-size: 1.1rem;">${'★'.repeat(userRating)}</div>
                        </div>
                        ${userTags.length > 0 ? `
                            <div style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.75rem;">
                                ${userTags.map(t => `<span class="user-tag-chip">${t}</span>`).join('')}
                            </div>
                        ` : ''}
                        ${userNotes ? `<p style="font-size: 0.9rem; color: var(--text-main); font-style: italic; white-space: pre-wrap;">"${userNotes}"</p>` : ''}
                    </div>

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

    document.getElementById('btn-close-dossier').onclick = () => { container.innerHTML = ''; };

    // Toggle Edit Form
    const editDrawer = document.getElementById('edit-drawer');
    document.getElementById('btn-toggle-edit').onclick = () => {
        editDrawer.style.display = editDrawer.style.display === 'none' ? 'block' : 'none';
    };
    document.getElementById('btn-cancel-edit').onclick = () => {
        editDrawer.style.display = 'none';
    };

    // Save Edit Form
    document.getElementById('btn-save-edit').onclick = async () => {
        const status = document.getElementById('edit-status-select').value;
        const ratingVal = document.getElementById('edit-rating-select').value;
        const notes = document.getElementById('edit-notes-input').value;
        const tags = document.getElementById('edit-tags-input').value;

        const updates = {
            listing_status: status,
            user_rating: ratingVal ? parseInt(ratingVal) : null,
            user_notes: notes,
            user_tags: tags.split(',').map(t => t.strip ? t.strip() : t.trim()).filter(Boolean),
        };

        try {
            const res = await updateListingApi(l.listing_id, updates);
            if (res.success) {
                showToast("Listing updated successfully!", "success");
                store.updateListing(l.listing_id, res.listing);
                container.innerHTML = '';
                openDossier(l.listing_id);
            }
        } catch (err) {
            showToast("Failed updating listing: " + err.message, "error");
        }
    };

    // Delete Archive Action
    document.getElementById('btn-delete-listing').onclick = async () => {
        if (confirm(`Are you sure you want to permanently delete archive '${l.listing_id}'? This cannot be undone.`)) {
            try {
                await deleteListingApi(l.listing_id);
                showToast(`Archive ${l.listing_id} deleted successfully.`, "success");
                container.innerHTML = '';
                store.removeListing(l.listing_id);
            } catch (err) {
                showToast("Failed deleting archive: " + err.message, "error");
            }
        }
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
