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
