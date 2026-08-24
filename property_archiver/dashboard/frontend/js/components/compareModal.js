/**
 * Side-by-Side Diff Comparison Modal Component.
 */
import { store } from '../state/store.js';
import { fetchCompareDiff } from '../api/apiClient.js';
import { showToast } from '../utils/dom.js';

export function openCompareModal() {
    const container = document.getElementById('compare-modal-container');
    if (!container) return;

    container.innerHTML = `
        <div id="compare-modal" class="modal-backdrop open">
            <div class="modal-content" style="max-width: 900px;">
                <div class="modal-header">
                    <h3>Side-by-Side Comparison</h3>
                    <button class="modal-close" id="btn-close-compare">&times;</button>
                </div>
                <div class="modal-body">
                    <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem;">
                        <div style="flex: 1;">
                            <label style="color: var(--text-muted); font-size: 0.85rem;">Listing A</label>
                            <select id="compare-select-a" class="select-filter" style="width: 100%; margin-top: 0.35rem;"></select>
                        </div>
                        <div style="flex: 1;">
                            <label style="color: var(--text-muted); font-size: 0.85rem;">Listing B</label>
                            <select id="compare-select-b" class="select-filter" style="width: 100%; margin-top: 0.35rem;"></select>
                        </div>
                        <div style="display: flex; align-items: flex-end;">
                            <button id="btn-do-compare" class="btn btn-primary">Compare</button>
                        </div>
                    </div>
                    <div id="compare-results"></div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('btn-close-compare').onclick = () => { container.innerHTML = ''; };

    const selA = document.getElementById('compare-select-a');
    const selB = document.getElementById('compare-select-b');
    store.rawListings.forEach(item => {
        selA.add(new Option(`${item.listing_id} - ${item.title || 'Listing'}`, item.listing_id));
        selB.add(new Option(`${item.listing_id} - ${item.title || 'Listing'}`, item.listing_id));
    });
    if (selB.options.length > 1) selB.selectedIndex = 1;

    document.getElementById('btn-do-compare').onclick = async () => {
        const idA = selA.value;
        const idB = selB.value;
        try {
            const diff = await fetchCompareDiff(idA, idB);
            renderCompareResults(diff, idA, idB);
        } catch (err) {
            showToast("Comparison error: " + err.message, "error");
        }
    };
}

function renderCompareResults(diff, idA, idB) {
    const resBox = document.getElementById('compare-results');
    resBox.innerHTML = `
        <table class="diff-table">
            <thead>
                <tr><th>Field</th><th>${idA}</th><th>${idB}</th></tr>
            </thead>
            <tbody>
                <tr class="${diff.price_changed ? 'diff-changed' : ''}">
                    <td><strong>Price</strong></td>
                    <td>R ${diff.old_price ? diff.old_price.toLocaleString() : 'N/A'}</td>
                    <td>R ${diff.new_price ? diff.new_price.toLocaleString() : 'N/A'} ${diff.price_diff ? ' (' + (diff.price_diff > 0 ? '+' : '') + diff.price_diff.toLocaleString() + ')' : ''}</td>
                </tr>
                <tr class="${diff.status_changed ? 'diff-changed' : ''}">
                    <td><strong>Status</strong></td>
                    <td>${(diff.old_status || 'active').toUpperCase()}</td>
                    <td>${(diff.new_status || 'active').toUpperCase()}</td>
                </tr>
                <tr>
                    <td><strong>Badges Diff</strong></td>
                    <td>${diff.badges_removed?.join(', ') || 'None'}</td>
                    <td>${diff.badges_added?.join(', ') || 'None'}</td>
                </tr>
                <tr>
                    <td><strong>Specifications</strong></td>
                    <td>-</td>
                    <td>${diff.spec_changes?.join('<br>') || 'No spec differences'}</td>
                </tr>
            </tbody>
        </table>
    `;
}
