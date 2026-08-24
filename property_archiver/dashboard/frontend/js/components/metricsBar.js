/**
 * Top Metrics Summary Bar Component.
 */
import { formatZAR } from '../utils/formatters.js';

export function renderMetrics(listings) {
    const container = document.getElementById('metrics-container');
    if (!container) return;

    const totalCount = listings.length;
    const totalImgs = listings.reduce((sum, item) => sum + (item.images_count || 0), 0);

    let totalVal = 0;
    let activeCount = 0, offerCount = 0, soldCount = 0;

    listings.forEach(item => {
        if (item.price && item.price.amount) totalVal += item.price.amount;
        if (item.listing_status === 'under_offer' || item.is_under_offer) offerCount++;
        else if (item.listing_status === 'sold' || item.is_sold) soldCount++;
        else activeCount++;
    });

    const activePct = totalCount ? Math.round((activeCount / totalCount) * 100) : 0;

    container.innerHTML = `
        <div class="metric-card">
            <div class="metric-title">Archived Properties</div>
            <div class="metric-value">${totalCount}</div>
            <div class="metric-sub">Across South African portals</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Preserved Images</div>
            <div class="metric-value">${totalImgs}</div>
            <div class="metric-sub">High-resolution verified assets</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Total Portfolio Value</div>
            <div class="metric-value">${formatZAR(totalVal)}</div>
            <div class="metric-sub">Sum of asking prices</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">Status Breakdown</div>
            <div class="metric-value">${activePct}% Active</div>
            <div class="metric-sub">${activeCount} Active | ${offerCount} Under Offer | ${soldCount} Sold</div>
        </div>
    `;
}
