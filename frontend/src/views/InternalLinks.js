import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { internalLinksService } from '../services/internalLinks.js';
import { AIAnchorModal } from '../components/AIAnchorModal.js';
import { GrowthDetailModal } from '../components/GrowthDetailModal.js';
import { PageRelationshipModal } from '../components/PageRelationshipModal.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class InternalLinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'internal-links-view';
        this.activeTab = 'graph'; // graph, broken, orphans, anchors, opportunities
        
        // Search & Filter state
        this.graphPage = 1;
        this.graphSearch = '';
        this.graphSectionFilter = 'all';
        this.graphRelFilter = 'all';

        this.brokenPage = 1;
        this.brokenTypeFilter = 'all'; // all, internal, external
        this.brokenStatusFilter = 'all'; // all, 404, 403, 500, timeout
        this.brokenSearch = '';

        this.orphansPage = 1;
        this.orphansSearch = '';

        this.anchorsPage = 1;
        this.anchorsSearch = '';

        this.opportunitiesPage = 1;
        this.oppsSearch = '';

        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Links & Navigation</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Trace internal link structure, verify broken internal & external links, and inspect exact DOM locations.</p>
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
                <button class="btn ${this.activeTab === 'orphans' ? 'btn-primary' : 'btn-secondary'}" id="tab-orphans-btn" style="font-size: 13px;">Pages With No Links (Orphans)</button>
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
            // SUB-TAB 1: LINKS BETWEEN YOUR PAGES (GRAPH & LINK RECORDS)
            // -------------------------------------------------------------
            if (this.activeTab === 'graph') {
                const data = await apiClient.get(`/api/projects/${projectId}/internal-links?limit=5000&offset=0`);
                const allLinks = data.internal_links || [];
                const summary = data.summary || {};
                const totalInternalLinks = summary.total_internal_links || allLinks.length;
                const totalAuditedPages = summary.total_audited_pages || 0;
                const orphanCount = summary.orphan_pages_count || 0;
                const deepCount = summary.deep_pages_count || 0;
                const deadEndCount = summary.dead_end_pages_count || 0;

                // PRE-PAGINATION FILTER & SEARCH
                let filtered = allLinks;
                if (this.graphSectionFilter !== 'all') {
                    filtered = filtered.filter(l => (l.source_section || 'other').toLowerCase() === this.graphSectionFilter.toLowerCase());
                }
                if (this.graphRelFilter !== 'all') {
                    filtered = filtered.filter(l => (l.rel || (l.is_nofollow ? 'nofollow' : 'follow')).toLowerCase().includes(this.graphRelFilter.toLowerCase()));
                }
                if (this.graphSearch.trim()) {
                    const q = this.graphSearch.toLowerCase().trim();
                    filtered = filtered.filter(l => {
                        const src = (l.source || l.source_page || '').toLowerCase();
                        const tgt = (l.target || l.target_page || '').toLowerCase();
                        const anc = (l.anchor_text || '').toLowerCase();
                        const sec = (l.source_section || '').toLowerCase();
                        const hdg = (l.nearest_heading || '').toLowerCase();
                        return src.includes(q) || tgt.includes(q) || anc.includes(q) || sec.includes(q) || hdg.includes(q);
                    });
                }

                const paginated = Pagination.paginateArray(filtered, this.graphPage, this.pageSize);
                this.graphPage = paginated.currentPage;

                let rows = paginated.items.map((l, idx) => {
                    const safeSrc = this.escapeHtml(l.source || l.source_page || '');
                    const safeTgt = this.escapeHtml(l.target || l.target_page || '');
                    const safeAnc = this.escapeHtml(l.anchor_text || '(No Anchor Text)');
                    const section = this.escapeHtml(l.source_section || 'Main Content');
                    const heading = l.nearest_heading ? this.escapeHtml(l.nearest_heading) : 'Not Available';
                    const rel = this.escapeHtml(l.rel || (l.is_nofollow ? 'nofollow' : 'follow'));
                    const statusCode = l.status_code !== undefined ? l.status_code : 200;

                    let statusBadge = '<span class="badge badge-success" style="font-size: 11px;">200 OK</span>';
                    if (statusCode >= 400 || statusCode === 0) {
                        statusBadge = `<span class="badge badge-critical" style="font-size: 11px;">${statusCode === 0 ? 'Dead' : `HTTP ${statusCode}`}</span>`;
                    } else if (statusCode >= 300) {
                        statusBadge = `<span class="badge badge-warning" style="font-size: 11px;">HTTP ${statusCode}</span>`;
                    }

                    return `
                        <tr style="border-bottom: 1px solid var(--border);" class="graph-link-row" data-idx="${idx}">
                            <td style="padding: 12px 14px; max-width: 220px;">
                                <div style="display: flex; align-items: center; gap: 4px;">
                                    <a href="#" class="btn-open-page-rel" data-url="${safeSrc}" style="font-family: monospace; font-size: 12px; color: var(--primary); text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeSrc}">${safeSrc}</a>
                                </div>
                            </td>
                            <td style="padding: 12px 14px; max-width: 220px;">
                                <div style="display: flex; align-items: center; gap: 4px;">
                                    <a href="#" class="btn-open-page-rel" data-url="${safeTgt}" style="font-family: monospace; font-size: 12px; color: var(--primary); text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeTgt}">${safeTgt}</a>
                                </div>
                            </td>
                            <td style="padding: 12px 14px; font-weight: 500; font-size: 12.5px; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeAnc}">
                                ${safeAnc}
                            </td>
                            <td style="padding: 12px 14px; font-size: 12px; color: var(--text-secondary);">${section}</td>
                            <td style="padding: 12px 14px; font-size: 12px; color: var(--text-secondary); max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${heading}">${heading}</td>
                            <td style="padding: 12px 14px; font-family: monospace; font-size: 11px; color: var(--text-secondary);">${rel}</td>
                            <td style="padding: 12px 14px;">${statusBadge}</td>
                            <td style="padding: 12px 14px; text-align: right;">
                                <button class="btn btn-secondary btn-sm btn-inspect-graph-link" data-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                                    Inspect Link
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');

                container.innerHTML = `
                    <!-- SUMMARY KPI CARDS -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Internal Links</div>
                            <div style="font-size: 24px; font-weight: 800; color: var(--primary); margin-top: 4px;">${totalInternalLinks}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Across ${totalAuditedPages} audited pages</div>
                        </div>
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Orphan Pages</div>
                            <div style="font-size: 24px; font-weight: 800; color: ${orphanCount > 0 ? '#ef4444' : '#10b981'}; margin-top: 4px;">${orphanCount}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">0 inbound internal links</div>
                        </div>
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Deep Pages (Depth > 3)</div>
                            <div style="font-size: 24px; font-weight: 800; color: ${deepCount > 0 ? '#f59e0b' : '#10b981'}; margin-top: 4px;">${deepCount}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Hard for search engines to crawl</div>
                        </div>
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Dead-End Pages</div>
                            <div style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${deadEndCount}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">0 outbound internal links</div>
                        </div>
                    </div>

                    <!-- CONTROLS: FILTER & SEARCH -->
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Internal Link Directory (${filtered.length})</h3>
                                <div style="display: flex; gap: 6px;">
                                    <select id="select-graph-section" style="padding: 4px 8px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                                        <option value="all" ${this.graphSectionFilter === 'all' ? 'selected' : ''}>All Sections</option>
                                        <option value="main" ${this.graphSectionFilter === 'main' ? 'selected' : ''}>Main Content</option>
                                        <option value="header" ${this.graphSectionFilter === 'header' ? 'selected' : ''}>Header / Nav</option>
                                        <option value="footer" ${this.graphSectionFilter === 'footer' ? 'selected' : ''}>Footer</option>
                                        <option value="sidebar" ${this.graphSectionFilter === 'sidebar' ? 'selected' : ''}>Sidebar</option>
                                    </select>
                                    <select id="select-graph-rel" style="padding: 4px 8px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                                        <option value="all" ${this.graphRelFilter === 'all' ? 'selected' : ''}>All Rel Attributes</option>
                                        <option value="follow" ${this.graphRelFilter === 'follow' ? 'selected' : ''}>Follow Only</option>
                                        <option value="nofollow" ${this.graphRelFilter === 'nofollow' ? 'selected' : ''}>Nofollow Only</option>
                                    </select>
                                </div>
                            </div>
                            <input type="text" id="graph-search-input" value="${this.escapeHtml(this.graphSearch)}" placeholder="Search source, target, anchor..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                        </div>

                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 14px;">Source Page</th>
                                        <th style="padding: 12px 14px;">Destination Page</th>
                                        <th style="padding: 12px 14px;">Anchor Text</th>
                                        <th style="padding: 12px 14px;">Location</th>
                                        <th style="padding: 12px 14px;">Nearest Heading</th>
                                        <th style="padding: 12px 14px;">Rel</th>
                                        <th style="padding: 12px 14px;">Status</th>
                                        <th style="padding: 12px 14px; text-align: right;">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${rows.length > 0 ? rows : `<tr><td colspan="8" style="padding: 36px; text-align: center; color: var(--text-secondary);">No internal links found matching your filters.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                        <div id="graph-pagination-slot"></div>
                    </div>
                `;

                // Bind Filter & Search Events
                const sectionSelect = document.getElementById('select-graph-section');
                if (sectionSelect) sectionSelect.onchange = (e) => { this.graphSectionFilter = e.target.value; this.graphPage = 1; this.mounted(); };

                const relSelect = document.getElementById('select-graph-rel');
                if (relSelect) relSelect.onchange = (e) => { this.graphRelFilter = e.target.value; this.graphPage = 1; this.mounted(); };

                const searchInput = document.getElementById('graph-search-input');
                if (searchInput) {
                    searchInput.oninput = (e) => {
                        this.graphSearch = e.target.value;
                        this.graphPage = 1;
                        this.mounted();
                    };
                }

                // Bind Inspect buttons
                container.querySelectorAll('.btn-inspect-graph-link').forEach(btn => {
                    btn.onclick = (e) => {
                        e.stopPropagation();
                        const idx = parseInt(btn.getAttribute('data-idx'), 10);
                        const record = paginated.items[idx];
                        if (record) GrowthDetailModal.showLinkDetail(record);
                    };
                });

                // Bind Page Relationship Popups on URL click
                container.querySelectorAll('.btn-open-page-rel').forEach(btn => {
                    btn.onclick = (e) => {
                        e.preventDefault();
                        const url = btn.getAttribute('data-url');
                        if (url) PageRelationshipModal.open(url);
                    };
                });

                // Pagination
                if (filtered.length > 0) {
                    const pageSlot = container.querySelector('#graph-pagination-slot');
                    if (pageSlot) {
                        const pag = new Pagination({
                            totalItems: filtered.length,
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
                return;
            }

            // -------------------------------------------------------------
            // SUB-TAB 2: BROKEN LINKS
            // -------------------------------------------------------------
            if (this.activeTab === 'broken') {
                const brokenData = await internalLinksService.getBrokenLinks(
                    projectId,
                    this.brokenTypeFilter,
                    2000,
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

                // Status code breakdown
                const count404 = allBroken.filter(b => b.status_code === 404).length;
                const count5xx = allBroken.filter(b => b.status_code >= 500).length;
                const countDead = allBroken.filter(b => b.status_code === 0 || !b.status_code).length;

                // Pre-pagination filter by status
                let filteredBroken = allBroken;
                if (this.brokenStatusFilter === '404') {
                    filteredBroken = filteredBroken.filter(b => b.status_code === 404);
                } else if (this.brokenStatusFilter === '403') {
                    filteredBroken = filteredBroken.filter(b => b.status_code === 403 || b.status_code === 401);
                } else if (this.brokenStatusFilter === '500') {
                    filteredBroken = filteredBroken.filter(b => b.status_code >= 500);
                } else if (this.brokenStatusFilter === 'timeout') {
                    filteredBroken = filteredBroken.filter(b => b.status_code === 0 || !b.status_code);
                }

                const paginated = Pagination.paginateArray(filteredBroken, this.brokenPage, this.pageSize);
                this.brokenPage = paginated.currentPage;

                let tableRows = paginated.items.map((b, idx) => {
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

                    const safeSource = this.escapeHtml(b.source || b.source_page || '');
                    const safeTarget = this.escapeHtml(b.target || b.url || '');
                    const safeAnchor = this.escapeHtml(b.anchor_text || '(No Anchor Text)');
                    const section = this.escapeHtml(b.source_section || 'Main Content');

                    return `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 12px 14px; max-width: 250px;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <span style="font-family: monospace; font-size: 12px; color: var(--primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeSource}">${safeSource}</span>
                                    <button class="btn-copy-url" data-url="${safeSource}" title="Copy source URL" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); padding: 2px 4px; font-size: 12px;">📋</button>
                                </div>
                            </td>
                            <td style="padding: 12px 14px; max-width: 260px;">
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    <a href="#" class="btn-open-broken-detail" data-target="${safeTarget}" data-idx="${idx}" style="font-family: monospace; font-size: 12px; color: #ef4444; font-weight: 600; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="Click to view all source pages for this broken URL">${safeTarget}</a>
                                    <button class="btn-copy-url" data-url="${safeTarget}" title="Copy target URL" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); padding: 2px 4px; font-size: 12px;">📋</button>
                                </div>
                            </td>
                            <td style="padding: 12px 14px; font-size: 12.5px; color: var(--text-primary); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${safeAnchor}">${safeAnchor}</td>
                            <td style="padding: 12px 14px;">${typeBadge}</td>
                            <td style="padding: 12px 14px;"><span class="badge ${statusBadgeClass}" style="font-size: 11.5px; font-weight: 700;">${statusLabel}</span></td>
                            <td style="padding: 12px 14px; font-size: 12px; color: var(--text-secondary);">${section}</td>
                            <td style="padding: 12px 14px; text-align: right;">
                                <button class="btn btn-secondary btn-sm btn-inspect-broken-link" data-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                                    Inspect Link
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');

                container.innerHTML = `
                    <!-- SUMMARY KPI CARDS -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Broken Links</div>
                            <div style="font-size: 24px; font-weight: 800; color: ${totalBroken > 0 ? '#ef4444' : '#10b981'}; margin-top: 4px;">${totalBroken}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Internal & outbound broken targets</div>
                        </div>
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Internal Broken Links</div>
                            <div style="font-size: 24px; font-weight: 800; color: ${internalBroken > 0 ? '#ef4444' : '#10b981'}; margin-top: 4px;">${internalBroken}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Dead links to pages on your domain</div>
                        </div>
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">External Broken Links</div>
                            <div style="font-size: 24px; font-weight: 800; color: ${externalBroken > 0 ? '#f59e0b' : '#10b981'}; margin-top: 4px;">${externalBroken}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Outbound links pointing to dead websites</div>
                        </div>
                        <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">404 Not Found</div>
                            <div style="font-size: 24px; font-weight: 800; color: ${count404 > 0 ? '#ef4444' : '#10b981'}; margin-top: 4px;">${count404}</div>
                            <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Missing web resources</div>
                        </div>
                    </div>

                    <!-- CONTROLS: FILTER & SEARCH -->
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Broken Links Directory (${filteredBroken.length})</h3>
                                <div style="display: flex; gap: 6px;">
                                    <button class="btn btn-sm ${this.brokenTypeFilter === 'all' ? 'btn-primary' : 'btn-secondary'}" id="filter-broken-all" style="font-size: 12px; padding: 4px 10px;">All (${totalBroken})</button>
                                    <button class="btn btn-sm ${this.brokenTypeFilter === 'internal' ? 'btn-primary' : 'btn-secondary'}" id="filter-broken-internal" style="font-size: 12px; padding: 4px 10px;">Internal (${internalBroken})</button>
                                    <button class="btn btn-sm ${this.brokenTypeFilter === 'external' ? 'btn-primary' : 'btn-secondary'}" id="filter-broken-external" style="font-size: 12px; padding: 4px 10px;">External (${externalBroken})</button>
                                    <select id="select-broken-status" style="padding: 4px 8px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                                        <option value="all" ${this.brokenStatusFilter === 'all' ? 'selected' : ''}>All Error Codes</option>
                                        <option value="404" ${this.brokenStatusFilter === '404' ? 'selected' : ''}>404 Not Found</option>
                                        <option value="403" ${this.brokenStatusFilter === '403' ? 'selected' : ''}>403 / 401 Blocked</option>
                                        <option value="500" ${this.brokenStatusFilter === '500' ? 'selected' : ''}>5xx Server Errors</option>
                                        <option value="timeout" ${this.brokenStatusFilter === 'timeout' ? 'selected' : ''}>Timeouts / Dead</option>
                                    </select>
                                </div>
                            </div>
                            <div style="display: flex; gap: 10px; align-items: center;">
                                <input type="text" id="broken-search-input" value="${this.escapeHtml(this.brokenSearch)}" placeholder="Search source, target, anchor..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                                <button id="btn-export-broken-csv" class="btn btn-secondary btn-sm" style="font-size: 12px;">Export CSV</button>
                            </div>
                        </div>

                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 14px;">Source Page</th>
                                        <th style="padding: 12px 14px;">Target URL ${renderTooltip('Click target URL to see all source pages referencing it.')}</th>
                                        <th style="padding: 12px 14px;">Anchor Text</th>
                                        <th style="padding: 12px 14px;">Type</th>
                                        <th style="padding: 12px 14px;">HTTP Status</th>
                                        <th style="padding: 12px 14px;">Location</th>
                                        <th style="padding: 12px 14px; text-align: right;">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tableRows.length > 0 ? tableRows : `
                                        <tr>
                                            <td colspan="7" style="padding: 40px; text-align: center; color: var(--text-secondary);">
                                                <div style="font-size: 28px; margin-bottom: 8px;">✓</div>
                                                <div style="font-size: 14px; font-weight: 600; color: var(--text-primary);">No broken links detected!</div>
                                                <div style="font-size: 12.5px; margin-top: 4px;">All verified link targets resolved with healthy status codes.</div>
                                            </td>
                                        </tr>
                                    `}
                                </tbody>
                            </table>
                        </div>
                        <div id="broken-pagination-slot"></div>
                    </div>
                `;

                // Event Listeners
                document.getElementById('filter-broken-all')?.addEventListener('click', () => { this.brokenTypeFilter = 'all'; this.brokenPage = 1; this.mounted(); });
                document.getElementById('filter-broken-internal')?.addEventListener('click', () => { this.brokenTypeFilter = 'internal'; this.brokenPage = 1; this.mounted(); });
                document.getElementById('filter-broken-external')?.addEventListener('click', () => { this.brokenTypeFilter = 'external'; this.brokenPage = 1; this.mounted(); });

                const statusSelect = document.getElementById('select-broken-status');
                if (statusSelect) statusSelect.onchange = (e) => { this.brokenStatusFilter = e.target.value; this.brokenPage = 1; this.mounted(); };

                const searchInput = document.getElementById('broken-search-input');
                if (searchInput) {
                    searchInput.oninput = (e) => {
                        this.brokenSearch = e.target.value;
                        this.brokenPage = 1;
                        this.mounted();
                    };
                }

                // Bind Inspect Link button
                container.querySelectorAll('.btn-inspect-broken-link').forEach(btn => {
                    btn.onclick = (e) => {
                        e.stopPropagation();
                        const idx = parseInt(btn.getAttribute('data-idx'), 10);
                        const record = paginated.items[idx];
                        if (record) GrowthDetailModal.showLinkDetail(record);
                    };
                });

                // Bind Broken Detail button (all source pages)
                container.querySelectorAll('.btn-open-broken-detail').forEach(btn => {
                    btn.onclick = (e) => {
                        e.preventDefault();
                        const idx = parseInt(btn.getAttribute('data-idx'), 10);
                        const record = paginated.items[idx];
                        if (record) GrowthDetailModal.showBrokenLinkDetail(record, allBroken);
                    };
                });

                // Copy buttons
                container.querySelectorAll('.btn-copy-url').forEach(btn => {
                    btn.onclick = async (e) => {
                        e.stopPropagation();
                        const url = btn.getAttribute('data-url');
                        if (url) {
                            try {
                                await navigator.clipboard.writeText(url);
                                const orig = btn.innerText;
                                btn.innerText = '✓';
                                setTimeout(() => btn.innerText = orig, 1200);
                            } catch (err) {}
                        }
                    };
                });

                if (filteredBroken.length > 0) {
                    const pageSlot = container.querySelector('#broken-pagination-slot');
                    if (pageSlot) {
                        const pag = new Pagination({
                            totalItems: filteredBroken.length,
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

            // -------------------------------------------------------------
            // SUB-TAB 3: ORPHAN PAGES (PAGES WITH NO INTERNAL LINKS)
            // -------------------------------------------------------------
            if (this.activeTab === 'orphans') {
                const data = await apiClient.get(`/api/projects/${projectId}/internal-links?limit=5000&offset=0`);
                const orphans = data.orphan_pages || [];

                let filteredOrphans = orphans;
                if (this.orphansSearch.trim()) {
                    const q = this.orphansSearch.toLowerCase().trim();
                    filteredOrphans = orphans.filter(u => u.toLowerCase().includes(q));
                }

                const paginated = Pagination.paginateArray(filteredOrphans, this.orphansPage, this.pageSize);
                this.orphansPage = paginated.currentPage;

                let orphanRows = paginated.items.map((url, idx) => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-family: monospace; font-size: 12.5px; color: var(--primary); padding: 12px 18px; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeHtml(url)}">
                            ${this.escapeHtml(url)}
                        </td>
                        <td style="padding: 12px 14px;">
                            <span class="badge badge-critical" style="font-weight: 700;">0 Inbound Links</span>
                        </td>
                        <td style="padding: 12px 14px; font-size: 12.5px; color: var(--text-secondary);">
                            No internal page points to this URL. Add internal links from your homepage or navigation.
                        </td>
                        <td style="padding: 12px 18px; text-align: right;">
                            <button class="btn btn-secondary btn-sm btn-view-orphan-rel" data-url="${this.escapeHtml(url)}" style="font-size: 11px; padding: 4px 10px;">
                                View Page Relationships
                            </button>
                        </td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Orphan Pages (${orphans.length})</h3>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Pages discovered in the crawl that have zero incoming internal links.</div>
                            </div>
                            <input type="text" id="orphans-search-input" value="${this.escapeHtml(this.orphansSearch)}" placeholder="Search orphan URLs..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; color: var(--text-secondary);">
                                    <th style="padding: 12px 18px;">Page URL</th>
                                    <th style="padding: 12px 14px;">Inbound Links</th>
                                    <th style="padding: 12px 14px;">Diagnosis</th>
                                    <th style="padding: 12px 18px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${orphanRows.length > 0 ? orphanRows : `<tr><td colspan="4" style="padding: 36px; text-align: center; color: var(--text-secondary);">✓ No orphan pages detected. All discovered pages have verified incoming internal links.</td></tr>`}
                            </tbody>
                        </table>
                        <div id="orphans-pagination-slot"></div>
                    </div>
                `;

                const searchInput = document.getElementById('orphans-search-input');
                if (searchInput) {
                    searchInput.oninput = (e) => {
                        this.orphansSearch = e.target.value;
                        this.orphansPage = 1;
                        this.mounted();
                    };
                }

                container.querySelectorAll('.btn-view-orphan-rel').forEach(btn => {
                    btn.onclick = () => {
                        const url = btn.getAttribute('data-url');
                        if (url) PageRelationshipModal.open(url, 'incoming');
                    };
                });

                if (filteredOrphans.length > 0) {
                    const pageSlot = container.querySelector('#orphans-pagination-slot');
                    if (pageSlot) {
                        const pag = new Pagination({
                            totalItems: filteredOrphans.length,
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

            // -------------------------------------------------------------
            // SUB-TAB 4: LINK TEXT (ANCHORS)
            // -------------------------------------------------------------
            if (this.activeTab === 'anchors') {
                const data = await apiClient.get(`/api/projects/${projectId}/internal-links?limit=5000&offset=0`);
                const anchors = data.anchor_texts || [];

                let filteredAnchors = anchors;
                if (this.anchorsSearch.trim()) {
                    const q = this.anchorsSearch.toLowerCase().trim();
                    filteredAnchors = anchors.filter(a => (a.anchor_text || '').toLowerCase().includes(q));
                }

                const paginated = Pagination.paginateArray(filteredAnchors, this.anchorsPage, this.pageSize);
                this.anchorsPage = paginated.currentPage;

                let anchorRows = paginated.items.map(a => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-weight: 600; padding: 12px 18px; color: var(--text-primary);">${this.escapeHtml(a.anchor_text)}</td>
                        <td style="padding: 12px 18px; font-weight: 700; color: var(--primary);">${a.frequency}</td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; max-width: 720px;">
                        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Link Text Usage (${anchors.length})</h3>
                            <input type="text" id="anchors-search-input" value="${this.escapeHtml(this.anchorsSearch)}" placeholder="Search link text..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 200px;" />
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; color: var(--text-secondary);">
                                    <th style="padding: 12px 18px;">Link Text (Anchor)</th>
                                    <th style="padding: 12px 18px;">Frequency</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${anchorRows.length > 0 ? anchorRows : `<tr><td colspan="2" style="padding: 32px; text-align: center; color: var(--text-secondary);">No link text records found.</td></tr>`}
                            </tbody>
                        </table>
                        <div id="anchors-pagination-slot"></div>
                    </div>
                `;

                const searchInput = document.getElementById('anchors-search-input');
                if (searchInput) {
                    searchInput.oninput = (e) => {
                        this.anchorsSearch = e.target.value;
                        this.anchorsPage = 1;
                        this.mounted();
                    };
                }

                if (filteredAnchors.length > 0) {
                    const pageSlot = container.querySelector('#anchors-pagination-slot');
                    if (pageSlot) {
                        const pag = new Pagination({
                            totalItems: filteredAnchors.length,
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

            // -------------------------------------------------------------
            // SUB-TAB 5: SUGGESTED PAGE LINKS (OPPORTUNITIES)
            // -------------------------------------------------------------
            if (this.activeTab === 'opportunities') {
                const oppsData = await apiClient.get(`/api/projects/${projectId}/internal-links/opportunities`);
                const oppList = oppsData.opportunities || [];

                let filteredOpps = oppList;
                if (this.oppsSearch.trim()) {
                    const q = this.oppsSearch.toLowerCase().trim();
                    filteredOpps = oppList.filter(o => {
                        const src = (o.source_page || '').toLowerCase();
                        const tgt = (o.target_page || '').toLowerCase();
                        const anc = (o.suggested_anchor || '').toLowerCase();
                        return src.includes(q) || tgt.includes(q) || anc.includes(q);
                    });
                }

                const paginated = Pagination.paginateArray(filteredOpps, this.opportunitiesPage, this.pageSize);
                this.opportunitiesPage = paginated.currentPage;

                let rows = paginated.items.map(o => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-family: monospace; font-size: 12px; color: var(--primary); padding: 12px 14px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeHtml(o.source_page)}">${this.escapeHtml(o.source_page)}</td>
                        <td style="font-family: monospace; font-size: 12px; padding: 12px 14px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeHtml(o.target_page)}">${this.escapeHtml(o.target_page)}</td>
                        <td style="padding: 12px 14px;">
                            <button class="btn btn-secondary btn-sm btn-view-anchor-suggestions" data-source="${this.escapeHtml(o.source_page)}" data-target="${this.escapeHtml(o.target_page)}" style="display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 600;">
                                ✨ View Suggested Link Text
                            </button>
                        </td>
                        <td style="font-size: 12px; color: var(--text-secondary); padding: 12px 14px;">${this.escapeHtml(o.reason)}</td>
                        <td style="padding: 12px 14px;"><span class="badge ${o.priority === 'HIGH' ? 'badge-critical' : 'badge-warning'}">${this.escapeHtml(o.priority)}</span></td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Suggested Page Links (${oppList.length})</h3>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Opportunities to link between isolated and high-relevance pages.</div>
                            </div>
                            <input type="text" id="opps-search-input" value="${this.escapeHtml(this.oppsSearch)}" placeholder="Search pages, anchors..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 14px;">Source Page</th>
                                        <th style="padding: 12px 14px;">Target Page</th>
                                        <th style="padding: 12px 14px;">Suggested Link Text</th>
                                        <th style="padding: 12px 14px;">Reason</th>
                                        <th style="padding: 12px 14px;">Priority</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${rows.length > 0 ? rows : `<tr><td colspan="5" style="padding: 36px; text-align: center; color: var(--text-secondary);">No link suggestions detected. All pages are well connected.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                        <div id="opps-pagination-slot"></div>
                    </div>
                `;

                const searchInput = document.getElementById('opps-search-input');
                if (searchInput) {
                    searchInput.oninput = (e) => {
                        this.oppsSearch = e.target.value;
                        this.opportunitiesPage = 1;
                        this.mounted();
                    };
                }

                const pageSlot = container.querySelector('#opps-pagination-slot');
                if (pageSlot && filteredOpps.length > 0) {
                    const pag = new Pagination({
                        totalItems: filteredOpps.length,
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

        } catch (e) {
            renderBackendOfflineState(container, `We couldn't load link information right now. Please try again.`, () => this.mounted());
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
