/**
 * Application Bootstrap & Lifecycle Manager with Deep-Linking & Scroll Position Persistence.
 */
import { fetchListings } from './api/apiClient.js';
import { store } from './state/store.js';
import { showToast } from './utils/dom.js';
import { renderMetrics } from './components/metricsBar.js';
import { initFilterBar, populateProvinces, syncFilterControlsFromStore } from './components/filterBar.js';
import { renderGridView } from './views/gridView.js';
import { renderGroupedView } from './views/groupedView.js';
import { renderMapView } from './views/mapView.js';
import { openCompareModal } from './components/compareModal.js';
import { openArchiveModal } from './components/archiveModal.js';
import { openDossier } from './components/dossierModal.js';
import { loadDashboardState, saveDashboardState } from './utils/storage.js';

let isInitialLoad = true;

export async function loadDashboardData() {
    // Preserve current scroll position before data refresh
    const previousScrollY = window.scrollY;

    try {
        const listings = await fetchListings();
        store.setListings(listings);
        populateProvinces();
        syncFilterControlsFromStore();

        // Handle Deep Linking Parameters (take precedence over stored state)
        const params = new URLSearchParams(window.location.search);
        const viewParam = params.get('view');
        if (viewParam && ['grid', 'grouped', 'map'].includes(viewParam)) {
            document.querySelectorAll('.view-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.view === viewParam);
            });
            store.setView(viewParam);
        } else {
            // Synchronize view button active classes with store's currentView
            document.querySelectorAll('.view-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.view === store.currentView);
            });
        }

        const openId = params.get('open');
        if (openId) {
            setTimeout(() => openDossier(openId), 150);
        }

        // Restore Scroll Position seamlessly after DOM insertion
        requestAnimationFrame(() => {
            if (isInitialLoad) {
                const savedState = loadDashboardState();
                if (savedState?.scrollY && !openId) {
                    window.scrollTo({ top: savedState.scrollY, behavior: 'instant' });
                }
                isInitialLoad = false;
            } else if (previousScrollY > 0) {
                window.scrollTo({ top: previousScrollY, behavior: 'instant' });
            }
        });
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
        renderMapView(state.filteredListings);
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

    // Track scroll position in localStorage (throttled)
    let scrollTimeout = null;
    window.addEventListener('scroll', () => {
        if (scrollTimeout) return;
        scrollTimeout = setTimeout(() => {
            saveDashboardState({ scrollY: window.scrollY });
            scrollTimeout = null;
        }, 200);
    }, { passive: true });
}

// Bootstrap on DOM Ready
window.addEventListener('DOMContentLoaded', () => {
    initFilterBar();
    setupGlobalNavigation();
    store.subscribe(handleStateChange);
    loadDashboardData();
});
