/**
 * Reactive Central Store for Property Archiver Dashboard.
 */
class Store {
    constructor() {
        this.rawListings = [];
        this.filteredListings = [];
        this.currentView = 'grid'; // 'grid' | 'grouped' | 'map'
        this.activeFilters = {
            search: '',
            listingType: 'all',
            propertyType: 'all',
            status: 'all',
            sort: 'date-desc',
            province: 'all',
            area: 'all',
            suburb: 'all'
        };
        this.listeners = [];
    }

    subscribe(callback) {
        this.listeners.push(callback);
    }

    notify() {
        this.listeners.forEach(cb => cb(this));
    }

    setListings(listings) {
        this.rawListings = listings;
        this.applyFilters();
    }

    setView(view) {
        this.currentView = view;
        this.notify();
    }

    updateFilters(newFilters) {
        this.activeFilters = { ...this.activeFilters, ...newFilters };
        this.applyFilters();
    }

    applyFilters() {
        const { search, listingType, propertyType, status, sort, province, area, suburb } = this.activeFilters;
        const query = search.toLowerCase().trim();

        let filtered = this.rawListings.filter(item => {
            const matchesQuery = !query ||
                (item.listing_id && item.listing_id.toLowerCase().includes(query)) ||
                (item.title && item.title.toLowerCase().includes(query)) ||
                (item.location && item.location.suburb && item.location.suburb.toLowerCase().includes(query));

            const lType = (item.listing_type || 'for_sale').toLowerCase();
            const matchesListingType = (listingType === 'all') || (lType === listingType);

            const pType = (item.property_type || '').toLowerCase();
            const matchesPropType = (propertyType === 'all') || (pType.includes(propertyType));

            const itemStatus = (item.listing_status || 'active').toLowerCase();
            const matchesStatus = (status === 'all') ||
                (status === 'active' && itemStatus === 'active' && !item.is_under_offer && !item.is_sold) ||
                (status === 'under_offer' && (itemStatus === 'under_offer' || item.is_under_offer)) ||
                (status === 'sold' && (itemStatus === 'sold' || item.is_sold));

            const p = item.geo_hierarchy?.province || item.location?.province;
            const a = item.geo_hierarchy?.area || item.location?.region || item.location?.city;
            const s = item.geo_hierarchy?.suburb || item.location?.suburb;

            const matchesProv = (province === 'all' || p === province);
            const matchesArea = (area === 'all' || a === area);
            const matchesSub = (suburb === 'all' || s === suburb);

            return matchesQuery && matchesListingType && matchesPropType && matchesStatus && matchesProv && matchesArea && matchesSub;
        });

        filtered.sort((a, b) => {
            if (sort === 'date-desc') return new Date(b.extracted_at) - new Date(a.extracted_at);
            if (sort === 'date-asc') return new Date(a.extracted_at) - new Date(b.extracted_at);
            if (sort === 'price-desc') return (b.price?.amount || 0) - (a.price?.amount || 0);
            if (sort === 'price-asc') return (a.price?.amount || 0) - (b.price?.amount || 0);
            if (sort === 'beds-desc') return (b.features?.bedrooms || 0) - (a.features?.bedrooms || 0);
            return 0;
        });

        this.filteredListings = filtered;
        this.notify();
    }
}

export const store = new Store();
