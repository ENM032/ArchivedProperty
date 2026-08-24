/**
 * Archive New Listing Ingestion Modal Component.
 */
import { archiveListing } from '../api/apiClient.js';
import { showToast } from '../utils/dom.js';
import { loadDashboardData } from '../app.js';

export function openArchiveModal() {
    const container = document.getElementById('archive-modal-container');
    if (!container) return;

    container.innerHTML = `
        <div id="archive-modal" class="modal-backdrop open">
            <div class="modal-content" style="max-width: 500px;">
                <div class="modal-header">
                    <h3>Archive New Listing</h3>
                    <button class="modal-close" id="btn-close-archive">&times;</button>
                </div>
                <div class="modal-body">
                    <div style="margin-bottom: 1rem;">
                        <label style="color: var(--text-muted); font-size: 0.85rem; display: block; margin-bottom: 0.35rem;">Listing ID or Full URL</label>
                        <input type="text" id="fetch-target-input" class="search-input" placeholder="e.g. T4710876 or https://www.privateproperty.co.za/...">
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem;">
                        <button class="btn btn-secondary" id="btn-cancel-archive">Cancel</button>
                        <button class="btn btn-primary" id="btn-do-fetch">Start Archiving</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('btn-close-archive').onclick = () => { container.innerHTML = ''; };
    document.getElementById('btn-cancel-archive').onclick = () => { container.innerHTML = ''; };

    document.getElementById('btn-do-fetch').onclick = async () => {
        const target = document.getElementById('fetch-target-input').value.trim();
        if (!target) {
            showToast("Please enter a Listing ID or URL", "error");
            return;
        }

        const btn = document.getElementById('btn-do-fetch');
        btn.innerText = "Archiving...";
        btn.disabled = true;

        try {
            const data = await archiveListing(target);
            if (data.success) {
                showToast(`Successfully archived ${data.listing_id}!`, "success");
                container.innerHTML = '';
                await loadDashboardData();
            } else {
                showToast(`Archiving failed: ${data.error}`, "error");
            }
        } catch (err) {
            showToast("Network error: " + err.message, "error");
        } finally {
            btn.innerText = "Start Archiving";
            btn.disabled = false;
        }
    };
}
