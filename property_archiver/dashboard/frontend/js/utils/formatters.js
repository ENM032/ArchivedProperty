/**
 * Data and Currency formatters supporting standard values, POA, and Auctions.
 */
export function formatZAR(amount, priceObj = null) {
    if (typeof amount === 'object' && amount !== null) {
        priceObj = amount;
        amount = priceObj.amount;
    }
    if (priceObj) {
        if (priceObj.is_poa || priceObj.price?.is_poa || priceObj.formatted_display === 'POA') {
            return 'POA';
        }
        if (priceObj.is_auction || priceObj.price?.is_auction) {
            if (priceObj.formatted_display) return priceObj.formatted_display;
            if (amount && !isNaN(amount)) return `Auction (${formatZAR(amount)})`;
            return 'Auction';
        }
        if (priceObj.formatted_display && (amount === null || amount === undefined || isNaN(amount))) {
            return priceObj.formatted_display;
        }
    }
    if (amount === null || amount === undefined || isNaN(amount)) return 'Price N/A';
    return 'R ' + Math.round(amount).toLocaleString('en-ZA');
}

export function formatCompactZAR(amount, priceObj = null) {
    if (typeof amount === 'object' && amount !== null) {
        priceObj = amount;
        amount = priceObj.amount;
    }
    if (priceObj) {
        if (priceObj.is_poa || priceObj.price?.is_poa || priceObj.formatted_display === 'POA') {
            return 'POA';
        }
        if (priceObj.is_auction || priceObj.price?.is_auction) {
            return 'Auction';
        }
    }
    if (amount === null || amount === undefined || isNaN(amount) || amount === 0) return 'Price N/A';
    if (amount >= 1_000_000) {
        const val = amount / 1_000_000;
        return `R ${val % 1 === 0 ? val.toFixed(0) : val.toFixed(2).replace(/\.?0+$/, '')}M`;
    }
    if (amount >= 1_000) {
        const val = amount / 1_000;
        return `R ${val % 1 === 0 ? val.toFixed(0) : val.toFixed(0)}k`;
    }
    return 'R ' + Math.round(amount);
}

export function formatDate(isoString) {
    if (!isoString) return '';
    return new Date(isoString).toLocaleDateString('en-ZA');
}

export function getStatusBadgeInfo(item) {
    if (!item) return { statusClass: 'active', statusLabel: 'Active' };
    const rawStatus = (item.listing_status || '').toLowerCase().trim();
    if (item.is_sold || rawStatus === 'sold') {
        return { statusClass: 'sold', statusLabel: 'Sold' };
    }
    if (item.is_under_offer || rawStatus === 'under_offer' || rawStatus === 'under offer') {
        return { statusClass: 'under_offer', statusLabel: 'Under Offer' };
    }
    if (item.is_auction || rawStatus === 'auction') {
        return { statusClass: 'auction', statusLabel: 'Auction' };
    }
    if (item.is_poa || rawStatus === 'poa' || item.price?.is_poa) {
        return { statusClass: 'poa', statusLabel: 'POA' };
    }
    if (rawStatus === 'delisted') {
        return { statusClass: 'delisted', statusLabel: 'Delisted' };
    }
    if (rawStatus === 'withdrawn') {
        return { statusClass: 'withdrawn', statusLabel: 'Withdrawn' };
    }
    if (rawStatus === 'pending') {
        return { statusClass: 'pending', statusLabel: 'Pending' };
    }
    if (rawStatus && rawStatus !== 'active') {
        const titleCased = rawStatus.charAt(0).toUpperCase() + rawStatus.slice(1).replace(/_/g, ' ');
        return { statusClass: rawStatus.replace(/[^a-z0-9_-]/g, '_'), statusLabel: titleCased };
    }
    return { statusClass: 'active', statusLabel: 'Active' };
}
