/**
 * Application Bootstrap & Lifecycle Manager with Deep-Linking & Scroll Position Persistence.
 */
import { fetchListings } from './api/apiClient.js?v=2.0.2';
import { store } from './state/store.js?v=2.0.2';
import { showToast } from './utils/dom.js?v=2.0.2';
import { renderMetrics } from './components/metricsBar.js?v=2.0.2';
import { initFilterBar, populateProvinces, syncFilterControlsFromStore, resetFilters } from './components/filterBar.js?v=2.0.2';
import { renderGridView } from './views/gridView.js?v=2.0.2';
import { renderGroupedView } from './views/groupedView.js?v=2.0.2';
import { renderMapView } from './views/mapView.js?v=2.0.2';
import { openCompareModal } from './components/compareModal.js?v=2.0.2';
import { openArchiveModal } from './components/archiveModal.js?v=2.0.2';
import { openDossier } from './components/dossierModal.js?v=2.0.2';
import { loadDashboardState, saveDashboardState } from './utils/storage.js?v=2.0.2';

let isInitialLoad = true;

export async function loadDashboardData() {
    const previousScrollY = window.scrollY;

    try {
        const listings = await fetchListings();
        store.rawListings = listings || [];
        populateProvinces();
        syncFilterControlsFromStore();
        store.applyFilters(true);

        // Handle Deep Linking Parameters (take precedence over stored state)
        const params = new URLSearchParams(window.location.search);
        const viewParam = params.get('view');
        if (viewParam && ['grid', 'grouped', 'map'].includes(viewParam)) {
            document.querySelectorAll('.view-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.view === viewParam);
            });
            store.setView(viewParam);
        } else {
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
    const empty = document.getElementById('empty-state');

    const hasResults = state.filteredListings && state.filteredListings.length > 0;

    grid.style.display = (state.currentView === 'grid') ? 'grid' : 'none';
    grouped.style.display = (state.currentView === 'grouped') ? 'flex' : 'none';
    mapContainer.style.display = (state.currentView === 'map') ? 'block' : 'none';

    if (empty) {
        empty.style.display = (!hasResults && state.currentView !== 'map') ? 'block' : 'none';
    }

    if (state.currentView === 'grid') {
        renderGridView(state.filteredListings);
    } else if (state.currentView === 'grouped') {
        renderGroupedView(state.filteredListings);
    } else if (state.currentView === 'map') {
        renderMapView(state.filteredListings);
    }
}

function setupGlobalNavigation() {
    const addClick = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.onclick = fn;
    };

    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            store.setView(btn.dataset.view);
        };
    });

    addClick('btn-open-compare', openCompareModal);
    addClick('btn-open-archive', openArchiveModal);
    addClick('btn-open-export', () => {
        const format = prompt("Export Format: Enter 'csv', 'sqlite', 'jsonl', or 'geojson':", "csv");
        if (format && ['csv', 'sqlite', 'jsonl', 'geojson'].includes(format.toLowerCase().trim())) {
            window.location.href = `/api/export?format=${format.toLowerCase().trim()}`;
        }
    });
    addClick('btn-empty-reset', () => resetFilters());

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

// Bootstrap on DOM Ready or immediately if DOM is already parsed
function bootstrap() {
    initFilterBar();
    setupGlobalNavigation();
    store.subscribe(handleStateChange);
    loadDashboardData();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
} else {
    bootstrap();
}
