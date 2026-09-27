/**
 * Reactive Central Store for Property Archiver Dashboard with localStorage Hydration.
 */
import { DEFAULT_FILTERS, loadDashboardState, saveDashboardState } from '../utils/storage.js';

class Store {
    constructor() {
        const savedState = loadDashboardState();
        this.rawListings = [];
        this.filteredListings = [];
        this.currentView = savedState?.view || 'grid';
        this.activeFilters = { ...DEFAULT_FILTERS };
        this.listeners = [];
    }

    subscribe(callback) {
        this.listeners.push(callback);
    }

    notify() {
        this.listeners.forEach(cb => cb(this));
    }

    setListings(listings) {
        this.rawListings = listings || [];
        this.applyFilters(true);
    }

    setView(view) {
        this.currentView = view;
        saveDashboardState({ view: this.currentView });
        this.notify();
    }

    removeListing(listingId) {
        this.rawListings = this.rawListings.filter(item => item.listing_id !== listingId);
        this.applyFilters();
    }

    updateListing(listingId, updatedRecord) {
        const idx = this.rawListings.findIndex(item => item.listing_id === listingId);
        if (idx !== -1) {
            this.rawListings[idx] = { ...this.rawListings[idx], ...updatedRecord };
            this.applyFilters();
        }
    }

    updateFilters(newFilters) {
        this.activeFilters = { ...this.activeFilters, ...newFilters };
        saveDashboardState({ filters: this.activeFilters });
        this.applyFilters();
    }

    resetFilters() {
        this.activeFilters = { ...DEFAULT_FILTERS };
        saveDashboardState({ filters: this.activeFilters });
        this.applyFilters();
    }

    applyFilters(isInitial = false) {
        const { search, listingType, propertyType, status, sort, province, area, suburb } = this.activeFilters;
        const query = search ? search.toLowerCase().trim() : '';

        let filtered = this.rawListings.filter(item => {
            return this._matchesSearch(item, query) &&
                this._matchesListingType(item, listingType) &&
                this._matchesPropertyType(item, propertyType) &&
                this._matchesStatus(item, status) &&
                this._matchesGeo(item, province, area, suburb);
        });

        // If on initial load saved filters filtered out all available listings, auto-recover with clean filters
        if (isInitial && filtered.length === 0 && this.rawListings.length > 0) {
            this.activeFilters = { ...DEFAULT_FILTERS };
            saveDashboardState({ filters: this.activeFilters });
            return this.applyFilters(false);
        }

        this._sortFiltered(filtered, sort);
        this.filteredListings = filtered;
        this.notify();
    }

    _matchesSearch(item, query) {
        if (!query) return true;
        return (item.listing_id && item.listing_id.toLowerCase().includes(query)) ||
            (item.title && item.title.toLowerCase().includes(query)) ||
            (item.location?.suburb && item.location.suburb.toLowerCase().includes(query)) ||
            (item.location?.street_address && item.location.street_address.toLowerCase().includes(query)) ||
            (item.user_notes && item.user_notes.toLowerCase().includes(query)) ||
            (item.user_tags && item.user_tags.some(t => t.toLowerCase().includes(query)));
    }

    _matchesListingType(item, listingType) {
        if (!listingType || listingType === 'all') return true;
        return (item.listing_type || 'for_sale').toLowerCase() === listingType.toLowerCase();
    }

    _matchesPropertyType(item, propertyType) {
        if (!propertyType || propertyType === 'all') return true;
        return (item.property_type || '').toLowerCase().includes(propertyType.toLowerCase());
    }

    _matchesStatus(item, status) {
        const filterStatus = (status || 'all').toLowerCase();
        if (filterStatus === 'all') return true;
        const itemStatus = (item.listing_status || 'active').toLowerCase();

        if (filterStatus === 'active') {
            return itemStatus === 'active' && !item.is_under_offer && !item.is_sold;
        }
        if (filterStatus === 'under_offer') {
            return itemStatus === 'under_offer' || item.is_under_offer;
        }
        if (filterStatus === 'sold') {
            return itemStatus === 'sold' || item.is_sold;
        }
        return itemStatus === filterStatus;
    }

    _matchesGeo(item, province, area, suburb) {
        const p = (item.geo_hierarchy?.province || item.location?.province || '').toLowerCase().trim();
        const a = (item.geo_hierarchy?.area || item.location?.region || item.location?.city || '').toLowerCase().trim();
        const s = (item.geo_hierarchy?.suburb || item.location?.suburb || '').toLowerCase().trim();

        const provTarget = (province || 'all').toLowerCase().trim();
        const areaTarget = (area || 'all').toLowerCase().trim();
        const subTarget = (suburb || 'all').toLowerCase().trim();

        const matchesProv = (provTarget === 'all' || p === provTarget);
        const matchesArea = (areaTarget === 'all' || a === areaTarget);
        const matchesSub = (subTarget === 'all' || s === subTarget);

        return matchesProv && matchesArea && matchesSub;
    }

    _sortFiltered(filtered, sort) {
        filtered.sort((a, b) => {
            if (sort === 'date-desc') return new Date(b.extracted_at) - new Date(a.extracted_at);
            if (sort === 'date-asc') return new Date(a.extracted_at) - new Date(b.extracted_at);
            if (sort === 'price-desc') return (b.price?.amount || 0) - (a.price?.amount || 0);
            if (sort === 'price-asc') return (a.price?.amount || 0) - (b.price?.amount || 0);
            if (sort === 'beds-desc') return (b.features?.bedrooms || 0) - (a.features?.bedrooms || 0);
            return 0;
        });
    }
}

export const store = new Store();
