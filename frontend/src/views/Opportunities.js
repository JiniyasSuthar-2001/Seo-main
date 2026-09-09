import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderSourceBadge } from '../components/AIBadge.js';
import { GrowthDetailModal } from '../components/GrowthDetailModal.js';
import { SolveWithAIModal } from '../components/SolveWithAIModal.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class Opportunities {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'opportunities-view';
        this.activeCategory = 'all';
        this.activeStatus = 'all'; // all, Open, In Progress, Resolved, Ignored
        this.oppsSearch = '';
        this.oppsPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 items per page
        this.cachedOpportunities = [];
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Growth Recommended Actions</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">
                        Evidence-grounded SEO recommendations and growth action items with persistent status tracking.
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-export-opps-csv" class="btn btn-secondary btn-sm" style="display: flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Download CSV
                    </button>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">
                        Scan My Website
                    </button>
                </div>
            </div>

            <!-- CATEGORY PILL TABS -->
            <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 20px; padding-bottom: 8px; flex-wrap: wrap;" id="opp-tabs">
                <button class="opp-tab ${this.activeCategory === 'all' ? 'active' : ''}" data-cat="all">All Actions</button>
                <button class="opp-tab ${this.activeCategory === 'Technical' ? 'active' : ''}" data-cat="Technical">Technical</button>
                <button class="opp-tab ${this.activeCategory === 'Content' ? 'active' : ''}" data-cat="Content">Content</button>
                <button class="opp-tab ${this.activeCategory === 'Keywords' ? 'active' : ''}" data-cat="Keywords">Keywords</button>
                <button class="opp-tab ${this.activeCategory === 'Internal Links' ? 'active' : ''}" data-cat="Internal Links">Page Links</button>
                <button class="opp-tab ${this.activeCategory === 'Backlinks' ? 'active' : ''}" data-cat="Backlinks">Backlinks</button>
                <button class="opp-tab ${this.activeCategory === 'Competitors' ? 'active' : ''}" data-cat="Competitors">Competitors</button>
            </div>

            <div id="opportunities-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading recommended actions...
                </div>
            </div>

            <style>
                .opp-tab {
                    padding: 6px 14px;
                    border: none;
                    background: transparent;
                    color: var(--text-secondary);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    border-bottom: 2px solid transparent;
                    transition: all 0.15s ease;
                }
                .opp-tab:hover { color: var(--text-primary); }
                .opp-tab.active {
                    color: var(--primary);
                    border-bottom-color: var(--primary);
                }
            </style>
        `;

        this.initTabListeners();
        return this.element;
    }

    initTabListeners() {
        setTimeout(() => {
            const tabs = this.element.querySelectorAll('.opp-tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    tabs.forEach(t => t.classList.remove('active'));
                    e.target.classList.add('active');
                    this.activeCategory = e.target.dataset.cat;
                    this.oppsPage = 1;
                    this.mounted();
                });
            });
        }, 50);
    }

    async updateStatus(oppId, newStatus) {
        try {
            const projectId = projectStore.getSelectedProjectId();
            await apiClient.put(`/api/projects/${projectId}/opportunities/${oppId}/status`, { status: newStatus });
            
            // Update local memory cache without resetting the whole page
            const item = this.cachedOpportunities.find(o => o.id === oppId);
            if (item) item.status = newStatus;
            
            this.mounted();
        } catch (e) {
            alert("Failed to update status: " + (e.message || 'Unknown error'));
        }
    }

    async mounted() {
        const container = document.getElementById('opportunities-content');
        if (!container) return;

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
                return;
            }

            const btnExport = this.element.querySelector('#btn-export-opps-csv');
            if (btnExport) {
                btnExport.onclick = (e) => {
                    apiClient.downloadFile(`/api/projects/${projectId}/opportunities/export.csv`, `${selectedProj.name || 'project'}_recommended_actions.csv`, e.currentTarget);
                };
            }

            const data = await apiClient.get(`/api/projects/${projectId}/opportunities?category=${this.activeCategory}`);
            const hasCrawl = !!data.has_crawl;
            const crawlStatus = data.status || 'no_crawl';
            const ctx = data.crawl_context || {};
            const opps = data.opportunities || [];
            this.cachedOpportunities = opps;

            // STATE A: No scan has ever been run
            if (!hasCrawl || crawlStatus === 'no_crawl') {
                container.innerHTML = `
                    <div class="card" style="padding: 40px 24px; text-align: center; background: var(--bg-card); border-radius: 14px;">
                        <div style="font-size: 40px; margin-bottom: 12px;">🔍</div>
                        <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px 0;">No Website Scan Yet</h3>
                        <p style="color: var(--text-secondary); font-size: 13.5px; max-width: 520px; margin: 0 auto 20px; line-height: 1.6;">
                            Run your first website scan to evaluate your website and generate evidence-grounded recommended actions.
                        </p>
                        <button class="btn btn-primary" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                    </div>
                `;
                return;
            }

            // STATE C: Scan exists but 0 issues found
            if (opps.length === 0) {
                container.innerHTML = `
                    <div class="card" style="padding: 36px 24px; text-align: center; background: var(--bg-card); border-radius: 14px;">
                        <div style="font-size: 36px; margin-bottom: 12px;">🎉</div>
                        <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px 0;">No Action Needed</h3>
                        <p style="color: var(--text-secondary); font-size: 13.5px; max-width: 540px; margin: 0 auto; line-height: 1.6;">
                            The latest scan did not identify any actionable problems in this category. Your website is in excellent health!
                        </p>
                    </div>
                `;
                return;
            }

            // Pre-pagination filtering by status & search
            let filtered = opps;
            if (this.activeStatus !== 'all') {
                filtered = filtered.filter(o => (o.status || 'Open').toLowerCase() === this.activeStatus.toLowerCase());
            }

            if (this.oppsSearch.trim()) {
                const q = this.oppsSearch.toLowerCase().trim();
                filtered = filtered.filter(o => {
                    const title = (o.title || '').toLowerCase();
                    const imp = (o.impact || '').toLowerCase();
                    const rec = (o.recommendation || '').toLowerCase();
                    const urls = (o.affected_urls || []).join(' ').toLowerCase();
                    return title.includes(q) || imp.includes(q) || rec.includes(q) || urls.includes(q);
                });
            }

            const criticalCount = opps.filter(o => o.priority_level === 'CRITICAL').length;
            const highCount = opps.filter(o => o.priority_level === 'HIGH').length;
            const mediumCount = opps.filter(o => o.priority_level === 'MEDIUM').length;
            const lowCount = opps.filter(o => o.priority_level === 'LOW').length;

            const paginated = Pagination.paginateArray(filtered, this.oppsPage, this.pageSize);
            this.oppsPage = paginated.currentPage;

            let cards = paginated.items.map((opp, idx) => {
                let badgeStyle = 'background: rgba(239,68,68,0.1); color: var(--critical);';
                if (opp.priority_level === 'HIGH') badgeStyle = 'background: rgba(245,158,11,0.1); color: var(--warning);';
                else if (opp.priority_level === 'MEDIUM') badgeStyle = 'background: rgba(59,130,246,0.1); color: var(--primary);';
                else if (opp.priority_level === 'LOW') badgeStyle = 'background: rgba(16,185,129,0.1); color: #10b981;';

                const urls = opp.affected_urls || [];
                const status = opp.status || 'Open';

                let statusBadgeStyle = 'background: rgba(59,130,246,0.1); color: var(--primary);';
                if (status === 'In Progress') statusBadgeStyle = 'background: rgba(245,158,11,0.1); color: var(--warning);';
                else if (status === 'Resolved') statusBadgeStyle = 'background: rgba(16,185,129,0.1); color: #10b981;';
                else if (status === 'Ignored') statusBadgeStyle = 'background: var(--bg-subtle); color: var(--text-secondary);';

                return `
                    <div class="card" style="padding: 20px; margin-bottom: 14px; border-left: 4px solid ${opp.priority_level === 'CRITICAL' ? 'var(--critical)' : (opp.priority_level === 'HIGH' ? 'var(--warning)' : 'var(--primary)')}; border-radius: 12px; background: var(--bg-card);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                    <span style="font-weight: 700; font-size: 15.5px; color: var(--text-primary);">${this.escapeHtml(opp.title)}</span>
                                    <span class="badge" style="${badgeStyle} font-size: 10.5px; font-weight: 800;">
                                        ${opp.priority_level} PRIORITY
                                    </span>
                                    <span class="badge badge-info" style="font-size: 10px;">${opp.category}</span>
                                    <span class="badge" style="${statusBadgeStyle} font-weight: 700; font-size: 10.5px;">Status: ${status}</span>
                                    ${renderSourceBadge('crawl')}
                                </div>
                                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.5;">
                                    <strong>Why it matters:</strong> ${this.escapeHtml(opp.impact || opp.evidence || '')}
                                </div>
                                <div style="font-size: 13px; color: var(--primary); font-weight: 600; margin-bottom: 12px;">
                                    <strong>Recommended Action:</strong> ${this.escapeHtml(opp.recommendation)}
                                </div>
                                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                                    <button class="btn btn-secondary btn-sm btn-inspect-opp-detail" data-idx="${idx}" style="font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
                                        🔍 View Evidence (${urls.length || opp.affected_count || 1} page${(urls.length || opp.affected_count || 1) === 1 ? '' : 's'})
                                    </button>
                                    <button class="btn btn-secondary btn-sm btn-solve-ai-opp" data-idx="${idx}" style="font-size: 12px; font-weight: 600; color: var(--primary);">
                                        ✨ Solve with AI
                                    </button>
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 6px; min-width: 140px;">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 2px;">Change Status</div>
                                <select class="opp-status-dropdown" data-id="${opp.id}" style="padding: 5px 8px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-primary); font-weight: 600;">
                                    <option value="Open" ${status === 'Open' ? 'selected' : ''}>Open</option>
                                    <option value="In Progress" ${status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                                    <option value="Resolved" ${status === 'Resolved' ? 'selected' : ''}>Resolved</option>
                                    <option value="Ignored" ${status === 'Ignored' ? 'selected' : ''}>Ignored</option>
                                </select>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <!-- SUMMARY BAR -->
                <div class="card" style="padding: 16px 20px; margin-bottom: 16px; background: var(--bg-card); border-radius: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${opps.length} Recommended Actions Found</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                            Generated from latest website scan (${ctx.pages_analyzed || 0} pages analyzed).
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <span class="badge" style="background: rgba(239,68,68,0.1); color: var(--critical); font-weight: 700;">${criticalCount} Critical</span>
                        <span class="badge" style="background: rgba(245,158,11,0.1); color: var(--warning); font-weight: 700;">${highCount} High</span>
                        <span class="badge" style="background: rgba(59,130,246,0.1); color: var(--primary); font-weight: 700;">${mediumCount} Medium</span>
                        <span class="badge" style="background: rgba(16,185,129,0.1); color: #10b981; font-weight: 700;">${lowCount} Low</span>
                    </div>
                </div>

                <!-- CONTROLS: STATUS FILTER & SEARCH -->
                <div class="card" style="padding: 12px 18px; margin-bottom: 16px; background: var(--bg-subtle); border-radius: 12px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                        <span style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-right: 4px;">Status Filter:</span>
                        <button class="btn btn-sm ${this.activeStatus === 'all' ? 'btn-primary' : 'btn-secondary'} btn-status-filter" data-st="all" style="font-size: 11.5px; padding: 3px 8px;">All (${opps.length})</button>
                        <button class="btn btn-sm ${this.activeStatus === 'Open' ? 'btn-primary' : 'btn-secondary'} btn-status-filter" data-st="Open" style="font-size: 11.5px; padding: 3px 8px;">Open</button>
                        <button class="btn btn-sm ${this.activeStatus === 'In Progress' ? 'btn-primary' : 'btn-secondary'} btn-status-filter" data-st="In Progress" style="font-size: 11.5px; padding: 3px 8px;">In Progress</button>
                        <button class="btn btn-sm ${this.activeStatus === 'Resolved' ? 'btn-primary' : 'btn-secondary'} btn-status-filter" data-st="Resolved" style="font-size: 11.5px; padding: 3px 8px;">Resolved</button>
                        <button class="btn btn-sm ${this.activeStatus === 'Ignored' ? 'btn-primary' : 'btn-secondary'} btn-status-filter" data-st="Ignored" style="font-size: 11.5px; padding: 3px 8px;">Ignored</button>
                    </div>
                    <input type="text" id="opps-search-input" value="${this.escapeHtml(this.oppsSearch)}" placeholder="Search actions or pages..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                </div>

                ${cards.length > 0 ? cards : `<div class="card" style="padding: 36px; text-align: center; color: var(--text-secondary);">No recommended actions found matching your filters.</div>`}
                <div id="opps-pagination-slot" style="background: var(--bg-card); border-radius: 12px; margin-top: 8px; border: 1px solid var(--border);"></div>
            `;

            // Status filter buttons
            container.querySelectorAll('.btn-status-filter').forEach(btn => {
                btn.onclick = () => {
                    this.activeStatus = btn.getAttribute('data-st');
                    this.oppsPage = 1;
                    this.mounted();
                };
            });

            // Search input
            const searchInput = container.querySelector('#opps-search-input');
            if (searchInput) {
                searchInput.oninput = (e) => {
                    this.oppsSearch = e.target.value;
                    this.oppsPage = 1;
                    this.mounted();
                };
            }

            // Status dropdown changes
            container.querySelectorAll('.opp-status-dropdown').forEach(sel => {
                sel.onchange = (e) => {
                    const oppId = sel.getAttribute('data-id');
                    const newStatus = sel.value;
                    this.updateStatus(oppId, newStatus);
                };
            });

            // Inspect Opportunity Detail modal
            container.querySelectorAll('.btn-inspect-opp-detail').forEach(btn => {
                btn.onclick = (e) => {
                    const idx = parseInt(btn.getAttribute('data-idx'), 10);
                    const opp = paginated.items[idx];
                    if (opp) {
                        GrowthDetailModal.showOpportunityDetail(opp, {
                            onStatusChange: (id, st) => this.updateStatus(id, st),
                            projectId
                        });
                    }
                };
            });

            // Solve with AI button
            container.querySelectorAll('.btn-solve-ai-opp').forEach(btn => {
                btn.onclick = (e) => {
                    const idx = parseInt(btn.getAttribute('data-idx'), 10);
                    const opp = paginated.items[idx];
                    if (opp) {
                        const urls = opp.affected_urls || [];
                        SolveWithAIModal.open({
                            projectId,
                            ruleId: opp.rule_id || 'GROWTH_OPPORTUNITY',
                            title: opp.title,
                            category: opp.category,
                            severity: opp.priority_level,
                            description: opp.impact || opp.description,
                            recommendation: opp.recommendation,
                            affectedUrl: urls[0] || '',
                            evidenceText: opp.evidence || opp.impact
                        });
                    }
                };
            });

            // Append Pagination Controls
            const pageSlot = container.querySelector('#opps-pagination-slot');
            if (pageSlot && filtered.length > 0) {
                const pag = new Pagination({
                    totalItems: filtered.length,
                    currentPage: this.oppsPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.oppsPage = newPage;
                        this.mounted();
                    }
                });
                pageSlot.appendChild(pag.render());
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
