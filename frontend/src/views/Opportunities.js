import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderSourceBadge, renderViewEvidenceButton } from '../components/AIBadge.js';

export class Opportunities {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'opportunities-view';
        this.activeCategory = 'all';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">SEO Action Center</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">
                        Your highest-priority SEO actions from the latest website crawl.
                    </p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button id="btn-export-opps-csv" class="btn btn-secondary btn-sm" style="display: flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Export CSV
                    </button>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">
                        Run Crawl Analysis
                    </button>
                </div>
            </div>

            <!-- CATEGORY PILL TABS -->
            <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 20px; padding-bottom: 8px; flex-wrap: wrap;" id="opp-tabs">
                <button class="opp-tab ${this.activeCategory === 'all' ? 'active' : ''}" data-cat="all">All Opportunities</button>
                <button class="opp-tab ${this.activeCategory === 'Technical' ? 'active' : ''}" data-cat="Technical">Technical</button>
                <button class="opp-tab ${this.activeCategory === 'Content' ? 'active' : ''}" data-cat="Content">Content</button>
                <button class="opp-tab ${this.activeCategory === 'Keywords' ? 'active' : ''}" data-cat="Keywords">Keywords</button>
                <button class="opp-tab ${this.activeCategory === 'Internal Links' ? 'active' : ''}" data-cat="Internal Links">Internal Links</button>
                <button class="opp-tab ${this.activeCategory === 'Backlinks' ? 'active' : ''}" data-cat="Backlinks">Backlinks</button>
                <button class="opp-tab ${this.activeCategory === 'Competitors' ? 'active' : ''}" data-cat="Competitors">Competitors</button>
            </div>

            <div id="opportunities-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading SEO action opportunities...
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
                    this.mounted();
                });
            });
        }, 50);
    }

    async updateStatus(oppId, newStatus) {
        try {
            await apiClient.put(`/api/projects/opportunities/${oppId}/status`, { status: newStatus });
            this.mounted();
        } catch (e) {
            alert("Failed to update status: " + e.message);
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
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create an SEO project workspace.</div>`;
                return;
            }

            // Bind export CSV button
            const btnExport = this.element.querySelector('#btn-export-opps-csv');
            if (btnExport) {
                btnExport.onclick = (e) => {
                    apiClient.downloadFile(`/api/projects/${projectId}/opportunities/export.csv`, `${selectedProj.name || 'project'}_opportunities.csv`, e.currentTarget);
                };
            }

            const data = await apiClient.get(`/api/projects/${projectId}/opportunities?category=${this.activeCategory}`);
            const hasCrawl = !!data.has_crawl;
            const crawlStatus = data.status || 'no_crawl';
            const ctx = data.crawl_context || {};
            const opps = data.opportunities || [];

            // STATE A: No crawl has ever been run
            if (!hasCrawl || crawlStatus === 'no_crawl') {
                container.innerHTML = `
                    <div class="card" style="padding: 40px 24px; text-align: center; background: var(--bg-card); border-radius: 14px;">
                        <div style="font-size: 40px; margin-bottom: 12px;">🔍</div>
                        <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px 0;">No Website Crawl Yet</h3>
                        <p style="color: var(--text-secondary); font-size: 13.5px; max-width: 520px; margin: 0 auto 20px; line-height: 1.6;">
                            Run your first website crawl to analyze your domain and generate evidence-based SEO action items.
                        </p>
                        <button class="btn btn-primary" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Run Website Crawl</button>
                    </div>
                `;
                return;
            }

            // STATE C: Crawl exists but has ZERO issues
            if (opps.length === 0) {
                container.innerHTML = `
                    <div class="card" style="padding: 36px 24px; text-align: center; background: var(--bg-card); border-radius: 14px;">
                        <div style="font-size: 36px; margin-bottom: 12px;">🎉</div>
                        <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px 0;">No SEO Issues Found</h3>
                        <p style="color: var(--text-secondary); font-size: 13.5px; max-width: 540px; margin: 0 auto; line-height: 1.6;">
                            The latest crawl did not identify any actionable issues in the analyzed pages. Your website is in excellent technical SEO health!
                        </p>
                    </div>
                `;
                return;
            }

            // STATE B & D: Crawl exists and contains opportunities
            const criticalCount = opps.filter(o => o.priority_level === 'CRITICAL').length;
            const highCount = opps.filter(o => o.priority_level === 'HIGH').length;
            const mediumCount = opps.filter(o => o.priority_level === 'MEDIUM').length;
            const lowCount = opps.filter(o => o.priority_level === 'LOW').length;

            const isErrorsCrawl = crawlStatus === 'completed_with_errors';
            const pagesAnalyzed = ctx.pages_analyzed || 0;
            const pagesFailed = ctx.pages_failed || 0;

            let cards = opps.map((opp, idx) => {
                let badgeStyle = 'background: rgba(239,68,68,0.1); color: var(--critical);';
                if (opp.priority_level === 'HIGH') badgeStyle = 'background: rgba(245,158,11,0.1); color: var(--warning);';
                else if (opp.priority_level === 'MEDIUM') badgeStyle = 'background: rgba(59,130,246,0.1); color: var(--primary);';
                else if (opp.priority_level === 'LOW') badgeStyle = 'background: rgba(16,185,129,0.1); color: #10b981;';

                const urls = opp.affected_urls || [];
                const affectedHtml = urls.length > 0 ? `
                    <div style="margin-top: 10px; background: var(--bg-subtle); padding: 10px 14px; border-radius: 8px; font-size: 12px;">
                        <strong style="color: var(--text-primary); display: block; margin-bottom: 4px;">Affected URLs (${opp.affected_count || urls.length}):</strong>
                        <div style="max-height: 80px; overflow-y: auto; display: flex; flex-direction: column; gap: 2px;">
                            ${urls.slice(0, 5).map(u => `<span style="font-family: monospace; color: var(--text-secondary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">• ${this.escapeHtml(u)}</span>`).join('')}
                            ${urls.length > 5 ? `<span style="color: var(--text-tertiary); font-style: italic;">...and ${urls.length - 5} more URLs</span>` : ''}
                        </div>
                    </div>
                ` : '';

                const evidenceItems = [
                    { label: 'SEO Pillar Category', value: opp.category || 'General', source: 'Crawled Data' },
                    { label: 'Underlying Evidence', value: opp.evidence || 'HTML structure signal', source: 'Crawled Data' },
                    { label: 'Deterministic Score', value: `${opp.priority_score || 0} / 100`, source: 'Crawled Data' }
                ];

                return `
                    <div class="card" style="padding: 20px; margin-bottom: 12px; border-left: 4px solid ${opp.priority_level === 'CRITICAL' ? 'var(--critical)' : (opp.priority_level === 'HIGH' ? 'var(--warning)' : 'var(--primary)')};">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                    <span style="font-weight: 700; font-size: 15px; color: var(--text-primary);">${this.escapeHtml(opp.title)}</span>
                                    <span class="badge" style="${badgeStyle}; font-size: 10px; font-weight: 700;">
                                        ${opp.priority_level} (${opp.priority_score})
                                    </span>
                                    <span class="badge badge-info" style="font-size: 10px;">${opp.category}</span>
                                    ${renderSourceBadge('crawl')}
                                    <span class="badge" style="background: var(--bg-subtle); color: var(--text-secondary); font-size: 10px;">Status: ${opp.status}</span>
                                </div>
                                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.5;">
                                    ${this.escapeHtml(opp.impact || '')}
                                </div>
                                <div style="font-size: 13px; color: var(--primary); font-weight: 600; margin-bottom: 8px;">
                                    Recommendation: ${this.escapeHtml(opp.recommendation)}
                                </div>
                                ${affectedHtml}
                                <div style="margin-top: 10px;">
                                    ${renderViewEvidenceButton(evidenceItems, `opp-ev-${idx}-${Math.random().toString(36).substring(2, 6)}`)}
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                <button class="btn btn-secondary btn-sm" onclick="window.updateOppStatus('${opp.id}', 'In Progress')">Mark In Progress</button>
                                <button class="btn btn-secondary btn-sm" onclick="window.updateOppStatus('${opp.id}', 'Resolved')">Mark Resolved</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            window.updateOppStatus = (id, st) => this.updateStatus(id, st);

            container.innerHTML = `
                <!-- SUMMARY METRICS BAR -->
                <div class="card" style="padding: 16px 20px; margin-bottom: 16px; background: var(--bg-card); border-radius: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${opps.length} Actionable Issues Found</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                            ${isErrorsCrawl ? `Analyzed from latest crawl. <strong>${pagesAnalyzed}</strong> pages analyzed; <strong>${pagesFailed}</strong> pages failed/blocked.` : `Analyzed from latest crawl (${pagesAnalyzed} pages analyzed).`}
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <span class="badge" style="background: rgba(239,68,68,0.1); color: var(--critical); font-weight: 700;">${criticalCount} Critical</span>
                        <span class="badge" style="background: rgba(245,158,11,0.1); color: var(--warning); font-weight: 700;">${highCount} High</span>
                        <span class="badge" style="background: rgba(59,130,246,0.1); color: var(--primary); font-weight: 700;">${mediumCount} Medium</span>
                        <span class="badge" style="background: rgba(16,185,129,0.1); color: #10b981; font-weight: 700;">${lowCount} Low</span>
                    </div>
                </div>

                ${cards}
            `;

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Opportunities Load Error", e.message || "Unable to load SEO opportunities.", () => this.mounted());
            }
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
