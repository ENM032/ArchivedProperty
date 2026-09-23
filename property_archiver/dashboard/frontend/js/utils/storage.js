/**
 * Safe localStorage State Persistence Utilities for Property Archiver Dashboard.
 */
const STORAGE_KEY = 'ap_dashboard_state';

const DEFAULT_FILTERS = {
    search: '',
    listingType: 'all',
    propertyType: 'all',
    status: 'all',
    sort: 'date-desc',
    province: 'all',
    area: 'all',
    suburb: 'all'
};

export function loadDashboardState() {
    try {
        const serialized = localStorage.getItem(STORAGE_KEY);
        if (!serialized) return null;
        const parsed = JSON.parse(serialized);
        return {
            view: parsed.view || 'grid',
            filters: { ...DEFAULT_FILTERS, ...(parsed.filters || {}) },
            scrollY: typeof parsed.scrollY === 'number' ? parsed.scrollY : 0
        };
    } catch (err) {
        return null;
    }
}

export function saveDashboardState(stateUpdates) {
    try {
        const current = loadDashboardState() || {
            view: 'grid',
            filters: { ...DEFAULT_FILTERS },
            scrollY: 0
        };
        const updated = {
            view: stateUpdates.view !== undefined ? stateUpdates.view : current.view,
            filters: stateUpdates.filters !== undefined ? { ...current.filters, ...stateUpdates.filters } : current.filters,
            scrollY: stateUpdates.scrollY !== undefined ? stateUpdates.scrollY : current.scrollY
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch (err) {
        // Silently ignore storage quota or sandbox restrictions
    }
}
