import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { internalLinksService } from '../services/internalLinks.js';
import { AIAnchorModal } from '../components/AIAnchorModal.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class InternalLinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'internal-links-view';
        this.activeTab = 'graph'; // graph, broken, orphans, anchors, opportunities
        this.graphPage = 1;
        this.brokenPage = 1;
        this.brokenTypeFilter = 'all'; // all, internal, external
        this.brokenSearch = '';
        this.orphansPage = 1;
        this.anchorsPage = 1;
        this.opportunitiesPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Links & Navigation</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Inspect internal link structure, detect broken internal & external links, and optimize page connectivity.</p>
                </div>
                <div id="links-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px; flex-wrap: wrap;">
                <button class="btn ${this.activeTab === 'graph' ? 'btn-primary' : 'btn-secondary'}" id="tab-graph-btn" style="font-size: 13px;">Links Between Your Pages</button>
                <button class="btn ${this.activeTab === 'broken' ? 'btn-primary' : 'btn-secondary'}" id="tab-broken-btn" style="font-size: 13px; display: inline-flex; align-items: center; gap: 6px;">
                    Broken Links
                    <span id="tab-broken-badge" style="display: none; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 700; background: rgba(239, 68, 68, 0.2); color: #ef4444;"></span>
                </button>
                <button class="btn ${this.activeTab === 'orphans' ? 'btn-primary' : 'btn-secondary'}" id="tab-orphans-btn" style="font-size: 13px;">Pages With No Links</button>
                <button class="btn ${this.activeTab === 'anchors' ? 'btn-primary' : 'btn-secondary'}" id="tab-anchors-btn" style="font-size: 13px;">Link Text</button>
                <button class="btn ${this.activeTab === 'opportunities' ? 'btn-primary' : 'btn-secondary'}" id="tab-opps-btn" style="font-size: 13px;">Suggested Page Links</button>
            </div>

            <div id="links-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading link data...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('links-content');
        const actionsContainer = document.getElementById('links-actions');
        if (!container) return;

        document.getElementById('tab-graph-btn')?.addEventListener('click', () => { this.activeTab = 'graph'; this.graphPage = 1; this.mounted(); });
        document.getElementById('tab-broken-btn')?.addEventListener('click', () => { this.activeTab = 'broken'; this.brokenPage = 1; this.mounted(); });
        document.getElementById('tab-orphans-btn')?.addEventListener('click', () => { this.activeTab = 'orphans'; this.orphansPage = 1; this.mounted(); });
        document.getElementById('tab-anchors-btn')?.addEventListener('click', () => { this.activeTab = 'anchors'; this.anchorsPage = 1; this.mounted(); });
        document.getElementById('tab-opps-btn')?.addEventListener('click', () => { this.activeTab = 'opportunities'; this.opportunitiesPage = 1; this.mounted(); });

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
                return;
            }

            const safeProjName = (selectedProj.name || 'website').replace(/[^a-zA-Z0-9_-]/g, '_');
            const todayStr = new Date().toISOString().split('T')[0];

            const sectionMap = {
                graph: 'graph',
                orphans: 'orphans',
                anchors: 'anchors',
                opportunities: 'opportunities',
                broken: 'broken'
            };

            const filenameLabelMap = {
                graph: 'Internal-Links',
                orphans: 'Orphan-Pages',
                anchors: 'Link-Text',
                opportunities: 'Suggested-Links',
                broken: 'Broken-Links'
            };

            const tabLabelMap = {
                graph: 'Internal Links',
                orphans: 'Orphan Pages',
                anchors: 'Link Text',
                opportunities: 'Suggested Links',
                broken: 'Broken Links'
            };

            const section = sectionMap[this.activeTab] || 'graph';
            const tabLabel = tabLabelMap[this.activeTab] || 'Internal Links';
            const filenameLabel = filenameLabelMap[section] || 'Internal-Links';

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <button id="btn-export-il-pdf" class="btn btn-secondary btn-sm">Download Report (PDF)</button>
                    <button id="btn-export-il-csv" class="btn btn-secondary btn-sm">Download ${tabLabel} (CSV)</button>
                `;

                const pdfBtn = document.getElementById('btn-export-il-pdf');
                const csvBtn = document.getElementById('btn-export-il-csv');
                if (pdfBtn) pdfBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/internal-links/report.pdf`, `${safeProjName}-Internal-Links-${todayStr}.pdf`, e.currentTarget);
                if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/internal-links/export.csv?section=${section}`, `${safeProjName}-${filenameLabel}-${todayStr}.csv`, e.currentTarget);
            }

            // -------------------------------------------------------------
            // SUB-TAB: BROKEN LINKS
            // -------------------------------------------------------------
            if (this.activeTab === 'broken') {
                const brokenData = await internalLinksService.getBrokenLinks(
                    projectId,
                    this.brokenTypeFilter,
                    1000,
                    0,
                    this.brokenSearch
                );

                const allBroken = brokenData.broken_links || [];
                const totalBroken = brokenData.total_unfiltered !== undefined ? brokenData.total_unfiltered : (brokenData.total || 0);
                const internalBroken = brokenData.internal_count || 0;
                const externalBroken = brokenData.external_count || 0;

                // Update tab badge if broken links exist
                const badgeEl = document.getElementById('tab-broken-badge');
                if (badgeEl) {
                    if (totalBroken > 0) {
                        badgeEl.innerText = `${totalBroken}`;
                        badgeEl.style.display = 'inline-block';
                    } else {
                        badgeEl.style.display = 'none';
                    }
                }

                const paginated = Pagination.paginateArray(allBroken, this.brokenPage, this.pageSize);
                this.brokenPage = paginated.currentPage;

                let tableRows = paginated.items.map(b => {
                    const isInternal = b.link_type === 'internal';
                    const typeBadge = isInternal
                        ? `<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); font-weight: 700; font-size: 11px;">INTERNAL</span>`
                        : `<span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); font-weight: 700; font-size: 11px;">EXTERNAL</span>`;

                    const statusCode = b.status_code || 0;
                    let statusBadgeClass = 'badge-critical';
                    let statusLabel = `HTTP ${statusCode}`;
                    if (statusCode === 0) {
                        statusBadgeClass = 'badge-critical';
                        statusLabel = 'Unreachable / Timeout';
                    } else if (statusCode === 404) {
                        statusBadgeClass = 'badge-critical';
                        statusLabel = '404 Not Found';
                    } else if (statusCode === 403 || statusCode === 401) {
                        statusBadgeClass = 'badge-warning';
                        statusLabel = `${statusCode} Blocked`;
                    } else if (statusCode >= 500) {
                        statusBadgeClass = 'badge-critical';
                        statusLabel = `${statusCode} Server Error`;
                    }

                    const safeSource = this.escapeHtml(b.source || '');
                    const safeTarget = this.escapeHtml(b.target || '');
                    const safeAnchor = this.escapeHtml(b.anchor_text || '(No Anchor Text)');
                    const safeError = this.escapeHtml(b.error || statusLabel);

                    return `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 12px 16px; max-width: 250px;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <span style="font-family: monospace; font-size: 12px; color: var(--primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeSource}">${safeSource}</span>
                                    <button class="btn-copy-url" data-url="${safeSource}" title="Copy source URL" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); padding: 2px 4px; font-size: 12px;">📋</button>
                                </div>
                            </td>
                            <td style="padding: 12px 16px; max-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <span style="font-family: monospace; font-size: 12px; color: #ef4444; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeTarget}">${safeTarget}</span>
                                    <button class="btn-copy-url" data-url="${safeTarget}" title="Copy target URL" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); padding: 2px 4px; font-size: 12px;">📋</button>
                                    <a href="${safeTarget}" target="_blank" rel="noopener noreferrer" style="color: var(--text-secondary); font-size: 12px; text-decoration: none;" title="Open link">↗</a>
                                </div>
                            </td>
                            <td style="padding: 12px 16px; font-size: 12.5px; color: var(--text-primary); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeAnchor}">${safeAnchor}</td>
                            <td style="padding: 12px 16px;">${typeBadge}</td>
                            <td style="padding: 12px 16px;"><span class="badge ${statusBadgeClass}" style="font-size: 11.5px; font-weight: 700;">${statusLabel}</span></td>
                            <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${safeError}</td>
                        </tr>
                    `;
                }).join('');

                container.innerHTML = `
                    <!-- SUMMARY KPI CARDS -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
                        <div class="kpi-card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Broken Links</div>
                            <div style="font-size: 26px; font-weight: 800; color: ${totalBroken > 0 ? '#ef4444' : '#10b981'}; margin-top: 4px;">${totalBroken}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Internal & outbound broken targets</div>
                        </div>
                        <div class="kpi-card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Internal Broken Links</div>
                            <div style="font-size: 26px; font-weight: 800; color: ${internalBroken > 0 ? '#ef4444' : '#10b981'}; margin-top: 4px;">${internalBroken}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Dead links to pages on your domain</div>
                        </div>
                        <div class="kpi-card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">External Broken Links</div>
                            <div style="font-size: 26px; font-weight: 800; color: ${externalBroken > 0 ? '#f59e0b' : '#10b981'}; margin-top: 4px;">${externalBroken}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Outbound links pointing to dead websites</div>
                        </div>
                    </div>

                    <!-- CONTROLS: FILTER & SEARCH -->
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Broken Links Directory (${allBroken.length})</h3>
                                <div style="display: flex; gap: 6px; margin-left: 8px;">
                                    <button class="btn btn-sm ${this.brokenTypeFilter === 'all' ? 'btn-primary' : 'btn-secondary'}" id="filter-broken-all" style="font-size: 12px; padding: 4px 10px;">All (${totalBroken})</button>
                                    <button class="btn btn-sm ${this.brokenTypeFilter === 'internal' ? 'btn-primary' : 'btn-secondary'}" id="filter-broken-internal" style="font-size: 12px; padding: 4px 10px;">Internal (${internalBroken})</button>
                                    <button class="btn btn-sm ${this.brokenTypeFilter === 'external' ? 'btn-primary' : 'btn-secondary'}" id="filter-broken-external" style="font-size: 12px; padding: 4px 10px;">External (${externalBroken})</button>
                                </div>
                            </div>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <input type="text" id="broken-search-input" value="${this.escapeHtml(this.brokenSearch)}" placeholder="Search source or target URL..." style="padding: 6px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                                <button id="btn-export-broken-csv" class="btn btn-secondary btn-sm" style="font-size: 12px;">Export CSV</button>
                            </div>
                        </div>

                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 16px;">Source Page</th>
                                        <th style="padding: 12px 16px;">Target URL ${renderTooltip('The unreachable destination URL.')}</th>
                                        <th style="padding: 12px 16px;">Anchor Text</th>
                                        <th style="padding: 12px 16px;">Type</th>
                                        <th style="padding: 12px 16px;">HTTP Status</th>
                                        <th style="padding: 12px 16px;">Error / Reason</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tableRows.length > 0 ? tableRows : `
                                        <tr>
                                            <td colspan="6" style="padding: 40px; text-align: center; color: var(--text-secondary);">
                                                <div style="font-size: 28px; margin-bottom: 8px;">✓</div>
                                                <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">No broken links detected!</div>
                                                <div style="font-size: 12.5px; margin-top: 4px;">All verified internal and external link targets resolved with healthy status codes.</div>
                                            </td>
                                        </tr>
                                    `}
                                </tbody>
                            </table>
                        </div>
                        <div id="broken-pagination-slot"></div>
                    </div>
                `;

                // Wire Filter and Search Event Handlers
                document.getElementById('filter-broken-all')?.addEventListener('click', () => {
                    this.brokenTypeFilter = 'all';
                    this.brokenPage = 1;
                    this.mounted();
                });
                document.getElementById('filter-broken-internal')?.addEventListener('click', () => {
                    this.brokenTypeFilter = 'internal';
                    this.brokenPage = 1;
                    this.mounted();
                });
                document.getElementById('filter-broken-external')?.addEventListener('click', () => {
                    this.brokenTypeFilter = 'external';
                    this.brokenPage = 1;
                    this.mounted();
                });

                const searchInput = document.getElementById('broken-search-input');
                if (searchInput) {
                    searchInput.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter') {
                            this.brokenSearch = searchInput.value;
                            this.brokenPage = 1;
                            this.mounted();
                        }
                    });
                }

                const exportBrokenBtn = document.getElementById('btn-export-broken-csv');
                if (exportBrokenBtn) {
                    exportBrokenBtn.onclick = (e) => {
                        let exportUrl = `/api/projects/${projectId}/internal-links/broken/export.csv`;
                        if (this.brokenTypeFilter !== 'all') {
                            exportUrl += `?type=${this.brokenTypeFilter}`;
                        }
                        apiClient.downloadFile(exportUrl, `${safeProjName}-Broken-Links-${todayStr}.csv`, e.currentTarget);
                    };
                }

                // Copy URL buttons
                container.querySelectorAll('.btn-copy-url').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        const urlToCopy = btn.getAttribute('data-url');
                        if (urlToCopy) {
                            try {
                                await navigator.clipboard.writeText(urlToCopy);
                                const origText = btn.innerText;
                                btn.innerText = '✓';
                                setTimeout(() => btn.innerText = origText, 1500);
                            } catch (err) {
                                console.error("Copy failed", err);
                            }
                        }
                    });
                });

                if (allBroken.length > 0) {
                    const pageSlot = container.querySelector('#broken-pagination-slot');
                    if (pageSlot) {
                        const pag = new Pagination({
                            totalItems: allBroken.length,
                            currentPage: this.brokenPage,
                            pageSize: this.pageSize,
                            onPageChange: (newPage) => {
                                this.brokenPage = newPage;
                                this.mounted();
                            }
                        });
                        pageSlot.appendChild(pag.render());
                    }
                }
                return;
            }

            if (this.activeTab === 'opportunities') {
                const oppsData = await apiClient.get(`/api/projects/${projectId}/internal-links/opportunities`);
                const oppList = oppsData.opportunities || [];
                const paginated = Pagination.paginateArray(oppList, this.opportunitiesPage, this.pageSize);
                this.opportunitiesPage = paginated.currentPage;

                let rows = paginated.items.map(o => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-family: monospace; font-size: 12px; color: var(--primary); padding: 12px 18px; max-width: 240px; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(o.source_page)}</td>
                        <td style="font-family: monospace; font-size: 12px; padding: 12px; max-width: 240px; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(o.target_page)}</td>
                        <td style="padding: 12px;">
                            <button class="btn btn-secondary btn-sm btn-view-anchor-suggestions" data-source="${this.escapeHtml(o.source_page)}" data-target="${this.escapeHtml(o.target_page)}" style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;">
                                ✨ View Suggested Link Text
                            </button>
                        </td>
                        <td style="font-size: 12px; color: var(--text-secondary); padding: 12px;">${this.escapeHtml(o.reason)}</td>
                        <td style="padding: 12px 18px;"><span class="badge ${o.priority === 'HIGH' ? 'badge-critical' : 'badge-warning'}">${this.escapeHtml(o.priority)}</span></td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Suggested Page Links (${oppList.length})</h3>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 20px;">Source Page</th>
                                        <th style="padding: 12px;">Target Page</th>
                                        <th style="padding: 12px;">Suggested Link Text ${renderTooltip('Clickable text to use for the link.')}</th>
                                        <th style="padding: 12px;">Reason</th>
                                        <th style="padding: 12px 20px;">Priority</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${rows.length > 0 ? rows : `<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--text-secondary);">No link suggestions detected. All pages are well connected.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                        <div id="opps-pagination-slot"></div>
                    </div>
                `;

                const pageSlot = container.querySelector('#opps-pagination-slot');
                if (pageSlot && oppList.length > 0) {
                    const pag = new Pagination({
                        totalItems: oppList.length,
                        currentPage: this.opportunitiesPage,
                        pageSize: this.pageSize,
                        onPageChange: (newPage) => {
                            this.opportunitiesPage = newPage;
                            this.mounted();
                        }
                    });
                    pageSlot.appendChild(pag.render());
                }

                container.querySelectorAll('.btn-view-anchor-suggestions').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const src = btn.getAttribute('data-source');
                        const tgt = btn.getAttribute('data-target');
                        if (src && tgt) {
                            AIAnchorModal.show(src, tgt);
                        }
                    });
                });

                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/internal-links?limit=500&offset=0`);
            const links = data.internal_links || [];
            const orphans = data.orphan_pages || [];
            const anchors = data.anchor_texts || [];

            if (this.activeTab === 'orphans') {
                const paginated = Pagination.paginateArray(orphans, this.orphansPage, this.pageSize);
                this.orphansPage = paginated.currentPage;

                let orphanRows = paginated.items.map(url => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-family: monospace; font-size: 13px; color: var(--primary); padding: 12px 20px;">${this.escapeHtml(url)}</td>
                        <td style="padding: 12px;"><span class="badge badge-critical">0 Links Pointing to This Page</span></td>
                        <td style="padding: 12px; font-size: 12.5px; color: var(--text-secondary);">Add a link from your homepage or main menu to help visitors find this page.</td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Pages With No Links (${orphans.length})</h3>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Page URL</th>
                                    <th style="padding: 12px;">Link Status</th>
                                    <th style="padding: 12px;">Recommended Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${orphanRows.length > 0 ? orphanRows : `<tr><td colspan="3" style="padding: 32px; text-align: center; color: var(--text-secondary);">✓ No pages with missing links found. All discovered pages have links pointing to them.</td></tr>`}
                            </tbody>
                        </table>
                        <div id="orphans-pagination-slot"></div>
                    </div>
                `;

                if (orphans.length > 0) {
                    const pageSlot = container.querySelector('#orphans-pagination-slot');
                    if (pageSlot) {
                        const pag = new Pagination({
                            totalItems: orphans.length,
                            currentPage: this.orphansPage,
                            pageSize: this.pageSize,
                            onPageChange: (newPage) => {
                                this.orphansPage = newPage;
                                this.mounted();
                            }
                        });
                        pageSlot.appendChild(pag.render());
                    }
                }
                return;
            }

            if (this.activeTab === 'anchors') {
                const paginated = Pagination.paginateArray(anchors, this.anchorsPage, this.pageSize);
                this.anchorsPage = paginated.currentPage;

                let anchorRows = paginated.items.map(a => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-weight: 600; padding: 12px 20px;">${this.escapeHtml(a.anchor_text)}</td>
                        <td style="padding: 12px;">${a.frequency}</td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; max-width: 650px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Link Text Usage (${anchors.length})</h3>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Link Text</th>
                                    <th style="padding: 12px;">Times Used</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${anchorRows.length > 0 ? anchorRows : `<tr><td colspan="2" style="padding: 32px; text-align: center; color: var(--text-secondary);">No link text records found.</td></tr>`}
                            </tbody>
                        </table>
                        <div id="anchors-pagination-slot"></div>
                    </div>
                `;

                if (anchors.length > 0) {
                    const pageSlot = container.querySelector('#anchors-pagination-slot');
                    if (pageSlot) {
                        const pag = new Pagination({
                            totalItems: anchors.length,
                            currentPage: this.anchorsPage,
                            pageSize: this.pageSize,
                            onPageChange: (newPage) => {
                                this.anchorsPage = newPage;
                                this.mounted();
                            }
                        });
                        pageSlot.appendChild(pag.render());
                    }
                }
                return;
            }

            // Default 'graph'
            const paginated = Pagination.paginateArray(links, this.graphPage, this.pageSize);
            this.graphPage = paginated.currentPage;

            let graphRows = paginated.items.map(l => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="font-family: monospace; font-size: 12px; color: var(--primary); padding: 12px 20px;">${this.escapeHtml(l.source)}</td>
                    <td style="font-family: monospace; font-size: 12px; padding: 12px;">${this.escapeHtml(l.target)}</td>
                    <td style="font-weight: 500; padding: 12px;">${this.escapeHtml(l.anchor_text || '(No Link Text)')}</td>
                </tr>
            `).join('');

            container.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Links Between Your Pages (${links.length})</h3>
                    </div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 20px;">Source Page</th>
                                <th style="padding: 12px;">Destination Page</th>
                                <th style="padding: 12px;">Link Text ${renderTooltip('Text that visitors click to navigate between pages.')}</th>
                            </tr>
                        </thead>
                        <tbody>${graphRows.length > 0 ? graphRows : `<tr><td colspan="3" style="padding: 32px; text-align: center; color: var(--text-secondary);">No page links discovered yet. Run a website scan to map your page links.</td></tr>`}</tbody>
                    </table>
                    <div id="graph-pagination-slot"></div>
                </div>
            `;

            if (links.length > 0) {
                const pageSlot = container.querySelector('#graph-pagination-slot');
                if (pageSlot) {
                    const pag = new Pagination({
                        totalItems: links.length,
                        currentPage: this.graphPage,
                        pageSize: this.pageSize,
                        onPageChange: (newPage) => {
                            this.graphPage = newPage;
                            this.mounted();
                        }
                    });
                    pageSlot.appendChild(pag.render());
                }
            }

        } catch (e) {
            renderBackendOfflineState(container, `We couldn't load this information right now. Please try again.`, () => this.mounted());
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
