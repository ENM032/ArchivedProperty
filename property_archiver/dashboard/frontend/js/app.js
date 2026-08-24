/**
 * Application Bootstrap & Lifecycle Manager.
 */
import { fetchListings } from './api/apiClient.js';
import { store } from './state/store.js';
import { showToast } from './utils/dom.js';
import { renderMetrics } from './components/metricsBar.js';
import { initFilterBar, populateProvinces } from './components/filterBar.js';
import { renderGridView } from './views/gridView.js';
import { renderGroupedView } from './views/groupedView.js';
import { initMap, updateMapMarkers } from './views/mapView.js';
import { openCompareModal } from './components/compareModal.js';
import { openArchiveModal } from './components/archiveModal.js';

export async function loadDashboardData() {
    try {
        const listings = await fetchListings();
        store.setListings(listings);
        populateProvinces();
    } catch (err) {
        showToast("Failed loading listings: " + err.message, "error");
    }
}

function handleStateChange(state) {
    renderMetrics(state.rawListings);

    const grid = document.getElementById('property-grid');
    const grouped = document.getElementById('grouped-view-container');
    const mapContainer = document.getElementById('map-view-container');

    grid.style.display = (state.currentView === 'grid') ? 'grid' : 'none';
    grouped.style.display = (state.currentView === 'grouped') ? 'flex' : 'none';
    mapContainer.style.display = (state.currentView === 'map') ? 'block' : 'none';

    if (state.currentView === 'grid') {
        renderGridView(state.filteredListings);
    } else if (state.currentView === 'grouped') {
        renderGroupedView(state.filteredListings);
    } else if (state.currentView === 'map') {
        initMap();
        updateMapMarkers(state.filteredListings);
    }
}

function setupGlobalNavigation() {
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            store.setView(btn.dataset.view);
        };
    });

    document.getElementById('btn-open-compare').onclick = openCompareModal;
    document.getElementById('btn-open-archive').onclick = openArchiveModal;
    document.getElementById('btn-open-export').onclick = () => {
        const format = prompt("Export Format: Enter 'csv', 'sqlite', 'jsonl', or 'geojson':", "csv");
        if (format && ['csv', 'sqlite', 'jsonl', 'geojson'].includes(format.toLowerCase().trim())) {
            window.location.href = `/api/export?format=${format.toLowerCase().trim()}`;
        }
    };
}

// Bootstrap on DOM Ready
window.addEventListener('DOMContentLoaded', () => {
    initFilterBar();
    setupGlobalNavigation();
    store.subscribe(handleStateChange);
    loadDashboardData();
});
