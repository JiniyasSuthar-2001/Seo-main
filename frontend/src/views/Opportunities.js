import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderSourceBadge } from '../components/AIBadge.js';
import { AuditEvidenceModal } from '../components/AuditEvidenceModal.js';
import { renderTooltip } from '../components/Tooltip.js';

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
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Recommended Actions</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">
                        Highest-priority recommended actions for your website based on real scan evidence.
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
                <button class="opp-tab ${this.activeCategory === 'Backlinks' ? 'active' : ''}" data-cat="Backlinks">Links From Other Sites</button>
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

            // STATE A: No scan has ever been run
            if (!hasCrawl || crawlStatus === 'no_crawl') {
                container.innerHTML = `
                    <div class="card" style="padding: 40px 24px; text-align: center; background: var(--bg-card); border-radius: 14px;">
                        <div style="font-size: 40px; margin-bottom: 12px;">🔍</div>
                        <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px 0;">No Website Scan Yet</h3>
                        <p style="color: var(--text-secondary); font-size: 13.5px; max-width: 520px; margin: 0 auto 20px; line-height: 1.6;">
                            Run your first website scan to analyze your website and generate evidence-grounded recommended actions.
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
                            The latest scan did not identify any actionable problems in your analyzed pages. Your website is in excellent health!
                        </p>
                    </div>
                `;
                return;
            }

            // STATE B: Recommended Actions List
            const criticalCount = opps.filter(o => o.priority_level === 'CRITICAL').length;
            const highCount = opps.filter(o => o.priority_level === 'HIGH').length;
            const mediumCount = opps.filter(o => o.priority_level === 'MEDIUM').length;
            const lowCount = opps.filter(o => o.priority_level === 'LOW').length;

            let cards = opps.map((opp, idx) => {
                let badgeStyle = 'background: rgba(239,68,68,0.1); color: var(--critical);';
                if (opp.priority_level === 'HIGH') badgeStyle = 'background: rgba(245,158,11,0.1); color: var(--warning);';
                else if (opp.priority_level === 'MEDIUM') badgeStyle = 'background: rgba(59,130,246,0.1); color: var(--primary);';
                else if (opp.priority_level === 'LOW') badgeStyle = 'background: rgba(16,185,129,0.1); color: #10b981;';

                const urls = opp.affected_urls || [];

                return `
                    <div class="card" style="padding: 20px; margin-bottom: 14px; border-left: 4px solid ${opp.priority_level === 'CRITICAL' ? 'var(--critical)' : (opp.priority_level === 'HIGH' ? 'var(--warning)' : 'var(--primary)')}; border-radius: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                    <span style="font-weight: 700; font-size: 15.5px; color: var(--text-primary);">${this.escapeHtml(opp.title)}</span>
                                    <span class="badge" style="${badgeStyle} font-size: 10.5px; font-weight: 800;">
                                        ${opp.priority_level} PRIORITY
                                    </span>
                                    <span class="badge badge-info" style="font-size: 10px;">${opp.category}</span>
                                    ${renderSourceBadge('crawl')}
                                </div>
                                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.5;">
                                    <strong>Why it matters:</strong> ${this.escapeHtml(opp.impact || opp.evidence || '')}
                                </div>
                                <div style="font-size: 13px; color: var(--primary); font-weight: 600; margin-bottom: 12px;">
                                    <strong>Recommended Action:</strong> ${this.escapeHtml(opp.recommendation)}
                                </div>
                                <button class="btn btn-secondary btn-sm btn-see-action-pages" data-idx="${idx}" style="font-size: 12px; font-weight: 600;">
                                    See Pages (${urls.length || opp.affected_count || 1} affected)
                                </button>
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

                ${cards}
            `;

            // Bind See Pages button triggers
            container.querySelectorAll('.btn-see-action-pages').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                    const opp = opps[idx];
                    if (opp) {
                        AuditEvidenceModal.open({
                            title: opp.title,
                            ruleId: 'ACTION_ITEM',
                            category: opp.category,
                            severity: opp.priority_level,
                            description: opp.impact || opp.evidence,
                            recommendation: opp.recommendation,
                            affectedUrls: opp.affected_urls,
                            evidenceText: opp.evidence,
                            provenance: 'Website Scan',
                            scanDate: 'Latest Scan'
                        });
                    }
                });
            });

        } catch (e) {
            renderBackendOfflineState(container, `We couldn't load this information right now. Please try again.`, () => this.mounted());
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
