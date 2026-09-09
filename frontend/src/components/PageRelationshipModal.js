/**
 * PageRelationshipModal.js
 * Modal displaying Incoming and Outgoing internal link relationships for a specific page.
 * Includes interactive switcher, location/heading metadata, and drill-down to Link Detail.
 */

import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';
import { GrowthDetailModal } from './GrowthDetailModal.js';
import { Pagination } from './Pagination.js';

export class PageRelationshipModal {
    static getRoot() {
        let root = document.getElementById('page-relationship-modal-root');
        if (!root) {
            root = document.createElement('div');
            root.id = 'page-relationship-modal-root';
            document.body.appendChild(root);
        }
        return root;
    }

    static close() {
        const root = document.getElementById('page-relationship-modal-root');
        if (root) root.innerHTML = '';
    }

    static escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    static async open(targetUrl, initialTab = 'incoming') {
        const root = this.getRoot();
        const projectId = projectStore.getSelectedProjectId();

        let currentTab = initialTab;
        let incomingLinks = [];
        let outgoingLinks = [];
        let isLoading = true;
        let pageData = null;
        let searchFilter = '';
        let currentPage = 1;
        const pageSize = 20;

        const renderModal = () => {
            const safeUrl = this.escapeHtml(targetUrl);
            const activeList = currentTab === 'incoming' ? incomingLinks : outgoingLinks;

            // Pre-pagination search
            let filteredList = activeList;
            if (searchFilter.trim()) {
                const q = searchFilter.toLowerCase().trim();
                filteredList = activeList.filter(l => {
                    const src = (l.source_page || l.source || '').toLowerCase();
                    const tgt = (l.target_page || l.target || '').toLowerCase();
                    const anc = (l.anchor_text || '').toLowerCase();
                    const sec = (l.source_section || '').toLowerCase();
                    return src.includes(q) || tgt.includes(q) || anc.includes(q) || sec.includes(q);
                });
            }

            const paginated = Pagination.paginateArray(filteredList, currentPage, pageSize);
            currentPage = paginated.currentPage;

            let tableRows = '';
            if (isLoading) {
                tableRows = `
                    <tr>
                        <td colspan="6" style="padding: 40px; text-align: center; color: var(--text-secondary);">
                            <div class="crawl-spinner" style="width: 24px; height: 24px; border: 3px solid var(--primary); border-top-color: transparent; border-radius: 50%; margin: 0 auto 12px auto;"></div>
                            Analyzing incoming and outgoing page relationships...
                        </td>
                    </tr>
                `;
            } else if (filteredList.length === 0) {
                const emptyMsg = currentTab === 'incoming'
                    ? (searchFilter ? 'No incoming links match your search.' : 'No incoming internal links discovered for this page (Orphan Page).')
                    : (searchFilter ? 'No outgoing links match your search.' : 'No outgoing internal links discovered on this page.');
                tableRows = `
                    <tr>
                        <td colspan="6" style="padding: 36px; text-align: center; color: var(--text-secondary);">
                            ${emptyMsg}
                        </td>
                    </tr>
                `;
            } else {
                tableRows = paginated.items.map((item, idx) => {
                    const isIncoming = currentTab === 'incoming';
                    const oppositeUrl = this.escapeHtml(isIncoming ? (item.source_page || item.source || '') : (item.target_page || item.target || ''));
                    const anchor = this.escapeHtml(item.anchor_text || '(No Anchor Text)');
                    const section = item.source_section || 'Main Content';
                    const heading = item.nearest_heading ? this.escapeHtml(item.nearest_heading) : 'Not Available';
                    const statusCode = item.status_code !== undefined ? item.status_code : (item.target_status_code || 200);

                    let statusBadge = '<span class="badge badge-success" style="font-size: 11px;">200 OK</span>';
                    if (statusCode >= 400 || statusCode === 0) {
                        statusBadge = `<span class="badge badge-critical" style="font-size: 11px;">${statusCode === 0 ? 'Dead' : `HTTP ${statusCode}`}</span>`;
                    } else if (statusCode >= 300) {
                        statusBadge = `<span class="badge badge-warning" style="font-size: 11px;">HTTP ${statusCode}</span>`;
                    }

                    return `
                        <tr style="border-bottom: 1px solid var(--border); cursor: pointer;" class="rel-row" data-idx="${idx}">
                            <td style="padding: 10px 14px; max-width: 280px;">
                                <div style="font-family: monospace; font-size: 12px; color: var(--primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${oppositeUrl}">
                                    ${oppositeUrl}
                                </div>
                            </td>
                            <td style="padding: 10px 14px; font-weight: 500; font-size: 12.5px; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${anchor}">
                                ${anchor}
                            </td>
                            <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">${section}</td>
                            <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${heading}">${heading}</td>
                            <td style="padding: 10px 14px;">${statusBadge}</td>
                            <td style="padding: 10px 14px; text-align: right;">
                                <button class="btn btn-secondary btn-sm btn-view-link-detail" data-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                                    Inspect Link
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            root.innerHTML = `
                <div style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 16px;">
                    <div class="card" style="width: 100%; max-width: 880px; max-height: 90vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 14px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); border: 1px solid var(--border); overflow: hidden;">
                        <!-- HEADER -->
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle);">
                            <div>
                                <h2 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                                    Page Link Relationships
                                </h2>
                                <div style="font-family: monospace; font-size: 12px; color: var(--text-secondary); margin-top: 3px; word-break: break-all;">
                                    ${safeUrl}
                                </div>
                            </div>
                            <button id="btn-close-rel-modal" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer; padding: 4px 8px; line-height: 1; border-radius: 6px;" title="Close">✕</button>
                        </div>

                        <!-- KPI SUMMARY BAR -->
                        <div style="padding: 12px 20px; background: var(--bg-card); border-bottom: 1px solid var(--border); display: flex; gap: 16px; flex-wrap: wrap;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 12px; color: var(--text-secondary);">Incoming Internal Links:</span>
                                <span class="badge badge-info" style="font-size: 12px; font-weight: 800;">${incomingLinks.length}</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 12px; color: var(--text-secondary);">Outgoing Internal Links:</span>
                                <span class="badge badge-info" style="font-size: 12px; font-weight: 800;">${outgoingLinks.length}</span>
                            </div>
                            ${incomingLinks.length === 0 && !isLoading ? `
                                <span class="badge badge-critical" style="font-size: 11px; font-weight: 700;">ORPHAN PAGE (0 Inbound)</span>
                            ` : ''}
                        </div>

                        <!-- CONTROLS & SUB-TABS -->
                        <div style="padding: 12px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            <div style="display: flex; gap: 8px;">
                                <button id="btn-rel-tab-incoming" class="btn btn-sm ${currentTab === 'incoming' ? 'btn-primary' : 'btn-secondary'}" style="font-size: 12px;">
                                    Incoming Links (${incomingLinks.length})
                                </button>
                                <button id="btn-rel-tab-outgoing" class="btn btn-sm ${currentTab === 'outgoing' ? 'btn-primary' : 'btn-secondary'}" style="font-size: 12px;">
                                    Outgoing Links (${outgoingLinks.length})
                                </button>
                            </div>
                            <input type="text" id="rel-search-input" value="${this.escapeHtml(searchFilter)}" placeholder="Search page, anchor, section..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                        </div>

                        <!-- TABLE CONTAINER -->
                        <div style="padding: 0; overflow-y: auto; flex: 1;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; color: var(--text-secondary); position: sticky; top: 0; z-index: 1;">
                                        <th style="padding: 10px 14px;">${currentTab === 'incoming' ? 'Source Page' : 'Target Page'}</th>
                                        <th style="padding: 10px 14px;">Anchor Text</th>
                                        <th style="padding: 10px 14px;">Location</th>
                                        <th style="padding: 10px 14px;">Nearest Heading</th>
                                        <th style="padding: 10px 14px;">Status</th>
                                        <th style="padding: 10px 14px; text-align: right;">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tableRows}
                                </tbody>
                            </table>
                        </div>

                        <!-- PAGINATION & FOOTER -->
                        <div style="padding: 10px 20px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <div id="rel-pagination-slot"></div>
                            <button class="btn btn-secondary btn-sm" id="btn-rel-modal-close-footer">Close</button>
                        </div>
                    </div>
                </div>
            `;

            // Event Listeners
            const closeBtn = root.querySelector('#btn-close-rel-modal');
            const closeFooterBtn = root.querySelector('#btn-rel-modal-close-footer');
            if (closeBtn) closeBtn.onclick = () => this.close();
            if (closeFooterBtn) closeFooterBtn.onclick = () => this.close();

            const tabIncBtn = root.querySelector('#btn-rel-tab-incoming');
            const tabOutBtn = root.querySelector('#btn-rel-tab-outgoing');
            if (tabIncBtn) tabIncBtn.onclick = () => { currentTab = 'incoming'; currentPage = 1; renderModal(); };
            if (tabOutBtn) tabOutBtn.onclick = () => { currentTab = 'outgoing'; currentPage = 1; renderModal(); };

            const searchInput = root.querySelector('#rel-search-input');
            if (searchInput) {
                searchInput.oninput = (e) => {
                    searchFilter = e.target.value;
                    currentPage = 1;
                    renderModal();
                };
            }

            // Bind inspect buttons & row clicks
            root.querySelectorAll('.btn-view-link-detail').forEach(btn => {
                btn.onclick = (e) => {
                    e.stopPropagation();
                    const idx = parseInt(btn.getAttribute('data-idx'), 10);
                    const item = paginated.items[idx];
                    if (item) GrowthDetailModal.showLinkDetail(item);
                };
            });

            root.querySelectorAll('.rel-row').forEach(row => {
                row.onclick = () => {
                    const idx = parseInt(row.getAttribute('data-idx'), 10);
                    const item = paginated.items[idx];
                    if (item) GrowthDetailModal.showLinkDetail(item);
                };
            });

            // Pagination rendering
            const pageSlot = root.querySelector('#rel-pagination-slot');
            if (pageSlot && filteredList.length > 0) {
                const pag = new Pagination({
                    totalItems: filteredList.length,
                    currentPage,
                    pageSize,
                    onPageChange: (newPage) => {
                        currentPage = newPage;
                        renderModal();
                    }
                });
                pageSlot.appendChild(pag.render());
            }
        };

        // Render initial loading frame
        renderModal();

        // Fetch both incoming and outgoing relationships
        try {
            const [incRes, outRes] = await Promise.all([
                apiClient.get(`/api/projects/${projectId}/internal-links/incoming?url=${encodeURIComponent(targetUrl)}`).catch(() => ({ incoming_links: [] })),
                apiClient.get(`/api/projects/${projectId}/internal-links/outgoing?url=${encodeURIComponent(targetUrl)}`).catch(() => ({ outgoing_links: [] }))
            ]);

            incomingLinks = incRes.incoming_links || [];
            outgoingLinks = outRes.outgoing_links || [];
            isLoading = false;
            renderModal();
        } catch (e) {
            console.error("Failed to load page relationships:", e);
            isLoading = false;
            renderModal();
        }
    }
}
