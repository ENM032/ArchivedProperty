/**
 * Filter & Location Drill-Down Toolbar Component with Search Debouncing & State Retention.
 */
import { store } from '../state/store.js';

function debounce(fn, delay = 180) {
    let timer = null;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

export function initFilterBar() {
    const container = document.getElementById('filter-bar-container');
    if (!container) return;

    container.innerHTML = `
        <div class="controls-row-top">
            <div class="search-box">
                <input type="text" id="search-input" class="search-input" placeholder="Search by ID (e.g. T4710876), Suburb, Street, Title...">
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center;">
                <select id="listing-type-filter" class="select-filter">
                    <option value="all">All Intents (Buy/Rent)</option>
                    <option value="for_sale">For Sale (Buy)</option>
                    <option value="to_rent">To Rent</option>
                </select>
                <select id="prop-type-filter" class="select-filter">
                    <option value="all">All Property Types</option>
                    <option value="house">House</option>
                    <option value="apartment">Apartment</option>
                    <option value="townhouse">Townhouse</option>
                    <option value="land">Vacant Land</option>
                    <option value="commercial">Commercial</option>
                    <option value="farm">Farm</option>
                </select>
                <select id="status-filter" class="select-filter">
                    <option value="all">All Statuses</option>
                    <option value="active">Active</option>
                    <option value="under_offer">Under Offer</option>
                    <option value="sold">Sold</option>
                    <option value="auction">Auction</option>
                    <option value="poa">POA (Price on Request)</option>
                    <option value="delisted">Delisted</option>
                    <option value="withdrawn">Withdrawn</option>
                </select>
                <select id="sort-filter" class="select-filter">
                    <option value="date-desc">Newest Archived</option>
                    <option value="date-asc">Oldest Archived</option>
                    <option value="price-desc">Price: High to Low</option>
                    <option value="price-asc">Price: Low to High</option>
                    <option value="beds-desc">Bedrooms: Most</option>
                </select>
            </div>
        </div>
        <div class="controls-row-bottom">
            <span class="filter-label">Location Drill-Down:</span>
            <select id="geo-province-filter" class="select-filter"><option value="all">All Provinces</option></select>
            <select id="geo-area-filter" class="select-filter"><option value="all">All Areas / Metros</option></select>
            <select id="geo-suburb-filter" class="select-filter"><option value="all">All Suburbs</option></select>
            <button id="btn-reset-filters" class="btn btn-secondary" style="padding: 0.4rem 0.75rem; font-size: 0.8rem;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.25rem;"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                Reset Filters
            </button>
        </div>
    `;

    bindFilterEvents();
    syncFilterControlsFromStore();
    populateProvinces();
}

function bindFilterEvents() {
    const setEvent = (id, event, handler) => {
        const el = document.getElementById(id);
        if (el) el[event] = handler;
    };

    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.oninput = debounce((e) => {
            store.updateFilters({ search: e.target.value });
        }, 180);
    }

    setEvent('listing-type-filter', 'onchange', (e) => store.updateFilters({ listingType: e.target.value }));
    setEvent('prop-type-filter', 'onchange', (e) => store.updateFilters({ propertyType: e.target.value }));
    setEvent('status-filter', 'onchange', (e) => store.updateFilters({ status: e.target.value }));
    setEvent('sort-filter', 'onchange', (e) => store.updateFilters({ sort: e.target.value }));

    setEvent('geo-province-filter', 'onchange', (e) => onProvinceChanged(e.target.value, true));
    setEvent('geo-area-filter', 'onchange', (e) => onAreaChanged(e.target.value, true));
    setEvent('geo-suburb-filter', 'onchange', (e) => store.updateFilters({ suburb: e.target.value }));
    setEvent('btn-reset-filters', 'onclick', () => resetFilters());
}

export function resetFilters() {
    store.resetFilters();
    populateProvinces();
    syncFilterControlsFromStore();
}

export function syncFilterControlsFromStore() {
    const f = store.activeFilters;
    const searchInput = document.getElementById('search-input');
    if (searchInput) searchInput.value = f.search || '';

    const setSelectVal = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) el.value = val;
    };

    setSelectVal('listing-type-filter', f.listingType || 'all');
    setSelectVal('prop-type-filter', f.propertyType || 'all');
    setSelectVal('status-filter', f.status || 'all');
    setSelectVal('sort-filter', f.sort || 'date-desc');
    setSelectVal('geo-province-filter', f.province || 'all');
    setSelectVal('geo-area-filter', f.area || 'all');
    setSelectVal('geo-suburb-filter', f.suburb || 'all');
}

export function populateProvinces() {
    const provSelect = document.getElementById('geo-province-filter');
    if (!provSelect) return;
    const provinces = new Set();
    store.rawListings.forEach(item => {
        const p = item.geo_hierarchy?.province || item.location?.province;
        if (p && p.trim()) provinces.add(p.trim());
    });

    const currentSelected = (store.activeFilters.province || 'all').trim();
    provSelect.innerHTML = '<option value="all">All Provinces</option>';
    Array.from(provinces).sort().forEach(p => provSelect.add(new Option(p, p)));

    const match = Array.from(provinces).find(p => p.toLowerCase() === currentSelected.toLowerCase());
    if (currentSelected !== 'all' && match) {
        provSelect.value = match;
    } else {
        provSelect.value = 'all';
        store.activeFilters.province = 'all';
    }

    onProvinceChanged(provSelect.value, false);
}

function onProvinceChanged(prov, triggerStoreUpdate = true) {
    const areaSelect = document.getElementById('geo-area-filter');
    if (!areaSelect) return;
    const areas = new Set();
    const provLower = (prov || 'all').toLowerCase().trim();

    store.rawListings.forEach(item => {
        const p = (item.geo_hierarchy?.province || item.location?.province || '').toLowerCase().trim();
        const a = (item.geo_hierarchy?.area || item.location?.region || item.location?.city || '').trim();
        if ((provLower === 'all' || p === provLower) && a) {
            areas.add(a);
        }
    });

    let selectedArea = 'all';
    const currentSelected = (store.activeFilters.area || 'all').toLowerCase().trim();
    const match = Array.from(areas).find(a => a.toLowerCase() === currentSelected);

    if (currentSelected !== 'all' && match) {
        selectedArea = match;
    }

    areaSelect.innerHTML = '<option value="all">All Areas / Metros</option>';
    Array.from(areas).sort().forEach(a => areaSelect.add(new Option(a, a)));
    areaSelect.value = selectedArea;

    if (triggerStoreUpdate) {
        store.updateFilters({ province: prov, area: selectedArea });
    } else {
        store.activeFilters.area = selectedArea;
    }
    onAreaChanged(selectedArea, triggerStoreUpdate);
}

function onAreaChanged(area, triggerStoreUpdate = true) {
    const subSelect = document.getElementById('geo-suburb-filter');
    if (!subSelect) return;
    const prov = (document.getElementById('geo-province-filter')?.value || store.activeFilters.province || 'all').toLowerCase().trim();
    const areaLower = (area || 'all').toLowerCase().trim();
    const suburbs = new Set();

    store.rawListings.forEach(item => {
        const p = (item.geo_hierarchy?.province || item.location?.province || '').toLowerCase().trim();
        const a = (item.geo_hierarchy?.area || item.location?.region || item.location?.city || '').toLowerCase().trim();
        const s = (item.geo_hierarchy?.suburb || item.location?.suburb || '').trim();

        if ((prov === 'all' || p === prov) && (areaLower === 'all' || a === areaLower) && s) {
            suburbs.add(s);
        }
    });

    let selectedSub = 'all';
    const currentSelected = (store.activeFilters.suburb || 'all').toLowerCase().trim();
    const match = Array.from(suburbs).find(s => s.toLowerCase() === currentSelected);

    if (currentSelected !== 'all' && match) {
        selectedSub = match;
    }

    subSelect.innerHTML = '<option value="all">All Suburbs</option>';
    Array.from(suburbs).sort().forEach(s => subSelect.add(new Option(s, s)));
    subSelect.value = selectedSub;

    if (triggerStoreUpdate) {
        store.updateFilters({ area: area, suburb: selectedSub });
    } else {
        store.activeFilters.suburb = selectedSub;
    }
}
