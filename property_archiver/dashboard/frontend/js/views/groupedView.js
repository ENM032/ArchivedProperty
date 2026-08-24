/**
 * Grouped Location Accordion View Renderer (Province -> Area -> Suburb).
 */
import { formatZAR } from '../utils/formatters.js';
import { createCardElement } from './gridView.js';

export function renderGroupedView(listings) {
    const container = document.getElementById('grouped-view-container');
    if (!container) return;
    container.innerHTML = '';

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
                    <strong>${provCount}</strong> Properties | Total: <strong>${formatZAR(provVal)}</strong> | Avg: <strong>${formatZAR(avgProv)}</strong>
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
