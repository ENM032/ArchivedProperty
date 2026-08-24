/**
 * Flat Card Grid View Renderer.
 */
import { formatZAR, formatDate } from '../utils/formatters.js';
import { openDossier } from '../components/dossierModal.js';

export function renderGridView(listings) {
    const grid = document.getElementById('property-grid');
    const empty = document.getElementById('empty-state');
    if (!grid) return;
    grid.innerHTML = '';

    if (listings.length === 0) {
        if (empty) empty.style.display = 'block';
        return;
    }
    if (empty) empty.style.display = 'none';

    listings.forEach(item => {
        const card = createCardElement(item);
        grid.appendChild(card);
    });
}

export function createCardElement(item) {
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
            <div class="card-price">${formatZAR(item.price?.amount)}</div>
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
                <span>${formatDate(item.extracted_at)}</span>
            </div>
        </div>
    `;
    return card;
}
