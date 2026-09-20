/**
 * Base API Client wrapper with error handling, offline detection, and CRUD methods.
 */
export async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            let errMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const body = await response.json();
                if (body.error) errMessage = body.error;
                if (body.detail) errMessage += ` (${body.detail})`;
            } catch (_) {}
            throw new Error(errMessage);
        }
        return await response.json();
    } catch (err) {
        if (err.name === 'TypeError' && err.message.toLowerCase().includes('fetch')) {
            throw new Error('Dashboard server unreachable. Please make sure "ap serve" is running.');
        }
        throw err;
    }
}

export async function fetchListings() {
    return apiFetch('/api/listings');
}

export async function fetchListingDetails(id) {
    return apiFetch(`/api/listings/${id}`);
}

export async function fetchCompareDiff(idA, idB) {
    return apiFetch(`/api/compare?a=${idA}&b=${idB}`);
}

export async function archiveListing(target) {
    return apiFetch('/api/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target })
    });
}

export async function deleteListingApi(id) {
    return apiFetch(`/api/listings/${id}`, {
        method: 'DELETE'
    });
}

export async function updateListingApi(id, updates) {
    return apiFetch(`/api/listings/${id}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
    });
}
