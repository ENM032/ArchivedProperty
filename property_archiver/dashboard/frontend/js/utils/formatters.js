/**
 * Data and Currency formatters.
 */
export function formatZAR(amount) {
    if (amount === null || amount === undefined) return 'Price N/A';
    return 'R ' + Math.round(amount).toLocaleString('en-ZA');
}

export function formatDate(isoString) {
    if (!isoString) return '';
    return new Date(isoString).toLocaleDateString('en-ZA');
}
