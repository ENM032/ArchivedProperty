/**
 * Data and Currency formatters.
 */
export function formatZAR(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return 'Price N/A';
    return 'R ' + Math.round(amount).toLocaleString('en-ZA');
}

export function formatCompactZAR(amount) {
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
