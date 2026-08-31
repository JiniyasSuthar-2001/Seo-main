import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class Keywords {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'keywords-view';
        this.activeTab = 'overview';
        this.researchResults = [];
        this.isSearching = false;
        this.overviewPage = 1;
        this.researchPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Keywords</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Discover search suggestions, organize keyword topics, and track how often key terms appear in your content.</p>
                </div>
                <div style="display: flex; gap: 10px;" id="kw-actions-container">
                    <button id="btn-export-kw-csv" class="btn btn-secondary btn-sm">Download CSV</button>
                    <button id="btn-export-kw-pdf" class="btn btn-secondary btn-sm">Download Report (PDF)</button>
                    <button class="btn btn-secondary btn-sm" id="btn-auto-cluster">⚡ Group Keyword Topics</button>
                </div>
            </div>

            <!-- SUB-TABS -->
            <div style="display: flex; gap: 6px; border-bottom: 1px solid var(--border); margin-bottom: 24px; flex-wrap: wrap;" id="kw-tabs-nav">
                <button class="kw-tab active" data-tab="overview">Overview</button>
                <button class="kw-tab" data-tab="research">Search Suggestions</button>
                <button class="kw-tab" data-tab="groups">Keyword Topics</button>
                <button class="kw-tab" data-tab="opportunities">Opportunities</button>
                <button class="kw-tab" data-tab="ranking">Target Keywords</button>
                <button class="kw-tab" data-tab="gap">Competitor Gap</button>
            </div>

            <div id="kw-tab-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading keyword information...
                </div>
            </div>

            <style>
                .kw-tab {
                    padding: 8px 16px;
                    border: none;
                    background: transparent;
                    color: var(--text-secondary);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    border-bottom: 2px solid transparent;
                    transition: all 0.15s ease;
                }
                .kw-tab:hover {
                    color: var(--text-primary);
                }
                .kw-tab.active {
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
            const tabs = this.element.querySelectorAll('.kw-tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    tabs.forEach(t => t.classList.remove('active'));
                    e.target.classList.add('active');
                    this.activeTab = e.target.dataset.tab;
                    this.overviewPage = 1;
                    this.researchPage = 1;
                    this.mounted();
                });
            });

            const clusterBtn = this.element.querySelector('#btn-auto-cluster');
            if (clusterBtn) {
                clusterBtn.addEventListener('click', () => this.handleAutoCluster());
            }
        }, 50);
    }

    async handleAutoCluster() {
        const projectId = projectStore.getSelectedProjectId();
        if (!projectId) return;
        try {
            await apiClient.post(`/api/projects/${projectId}/keywords/groups/auto-cluster`, {});
            alert("Keyword topics grouped successfully!");
            this.mounted();
        } catch (e) {
            alert("Failed to group keyword topics: " + e.message);
        }
    }

    async mounted() {
        const contentContainer = document.getElementById('kw-tab-content');
        if (!contentContainer) return;

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                contentContainer.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
                return;
            }

            const safeProjName = (selectedProj.name || 'website').replace(/[^a-zA-Z0-9_-]/g, '_');
            const todayStr = new Date().toISOString().split('T')[0];

            const pdfBtn = document.getElementById('btn-export-kw-pdf');
            const csvBtn = document.getElementById('btn-export-kw-csv');
            if (pdfBtn) pdfBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/keywords/report.pdf`, `${safeProjName}-Keywords-${todayStr}.pdf`, e.currentTarget);
            if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/keywords/export.csv`, `${safeProjName}-Keywords-${todayStr}.csv`, e.currentTarget);

            if (this.activeTab === 'research') {
                this.renderResearchView(contentContainer, projectId);
                return;
            }

            if (this.activeTab === 'groups') {
                const groupRes = await apiClient.get(`/api/projects/${projectId}/keywords/groups`);
                const groups = groupRes.groups || [];
                let groupRows = groups.map(g => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(g.name)}</td>
                        <td style="padding: 12px; color: var(--text-secondary);">${this.escapeHtml(g.description || 'Topic cluster')}</td>
                        <td style="padding: 12px; font-weight: 600;">${g.keyword_count || 0} keywords</td>
                        <td style="padding: 12px 18px; font-size: 12px; color: var(--text-secondary);">${g.created_at ? new Date(g.created_at).toLocaleDateString() : 'Auto-clustered'}</td>
                    </tr>
                `).join('');

                contentContainer.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Keyword Topic Groups (${groups.length})</h3>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 18px;">Topic Group</th>
                                        <th style="padding: 12px;">Description</th>
                                        <th style="padding: 12px;">Keywords Count</th>
                                        <th style="padding: 12px 18px;">Created Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${groupRows.length > 0 ? groupRows : `<tr><td colspan="4" style="padding: 32px; text-align: center; color: var(--text-secondary);">No topic groups created yet. Click "⚡ Group Keyword Topics" above to auto-cluster terms.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                return;
            }

            if (this.activeTab === 'opportunities') {
                const oppRes = await apiClient.get(`/api/projects/${projectId}/keywords/opportunities`);
                const opps = oppRes.opportunities || [];
                let oppRows = opps.map(o => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(o.keyword)}</td>
                        <td style="padding: 12px;">
                            <span class="badge badge-info" style="font-size: 11px;">${this.escapeHtml(o.category)}</span>
                        </td>
                        <td style="padding: 12px; font-weight: 600;">${this.escapeHtml(String(o.current_position || 'Unranked'))}</td>
                        <td style="padding: 12px; font-size: 12.5px; color: var(--text-secondary);">${this.escapeHtml(o.evidence)}</td>
                        <td style="padding: 12px 18px; font-size: 12.5px; color: var(--primary); font-weight: 600;">${this.escapeHtml(o.recommendation)}</td>
                    </tr>
                `).join('');

                contentContainer.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--bg-subtle);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Keyword Opportunities (${opps.length})</h3>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 18px;">Target Keyword</th>
                                        <th style="padding: 12px;">Opportunity Type</th>
                                        <th style="padding: 12px;">Current Rank</th>
                                        <th style="padding: 12px;">Evidence</th>
                                        <th style="padding: 12px 18px;">Action Recommendation</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${oppRows.length > 0 ? oppRows : `<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--text-secondary);">No keyword opportunities detected yet. Run a website scan or add target keywords.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                return;
            }

            if (this.activeTab === 'gap') {
                const gapRes = await apiClient.get(`/api/projects/${projectId}/keywords/competitor-gap`);
                const gaps = gapRes.gaps || [];
                const hasComp = gapRes.has_competitors !== false;

                let gapRows = gaps.map(g => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(g.keyword)}</td>
                        <td style="padding: 12px;">${this.escapeHtml(g.competitor_domain)}</td>
                        <td style="padding: 12px; color: var(--text-secondary);">${this.escapeHtml(g.our_position)}</td>
                        <td style="padding: 12px; font-weight: 600; color: var(--primary);">${this.escapeHtml(g.competitor_position)}</td>
                        <td style="padding: 12px 18px; font-size: 12.5px; color: var(--text-secondary);">${this.escapeHtml(g.recommendation)}</td>
                    </tr>
                `).join('');

                contentContainer.innerHTML = `
                    <div class="card" style="padding: 24px; border-radius: 14px; margin-bottom: 20px;">
                        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 6px; color: var(--text-primary);">Competitor Keyword Gap</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">
                            ${this.escapeHtml(gapRes.message || "Compare keywords targeted by competitor websites against your domain.")}
                        </p>
                    </div>
                    ${hasComp ? `
                        <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                    <thead>
                                        <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                            <th style="padding: 12px 18px;">Keyword</th>
                                            <th style="padding: 12px;">Competitor Domain</th>
                                            <th style="padding: 12px;">Our Rank</th>
                                            <th style="padding: 12px;">Competitor Rank</th>
                                            <th style="padding: 12px 18px;">Action Strategy</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${gapRows.length > 0 ? gapRows : `<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--text-secondary);">No competitor keyword gaps detected.</td></tr>`}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ` : ''}
                `;
                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/keywords`);
            const keywords = data.keywords || [];

            if (this.activeTab === 'ranking') {
                const targetKws = keywords.filter(k => k.target_url || k.position || (k.source && k.source.includes('Import')));
                const displayKws = targetKws.length > 0 ? targetKws : keywords;

                let targetRows = displayKws.map(k => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(k.keyword)}</td>
                        <td style="padding: 12px; font-family: monospace; font-size: 12px; color: var(--primary);">${this.escapeHtml(k.target_url || selectedProj.domain || 'Homepage')}</td>
                        <td style="padding: 12px;">${this.escapeHtml(String(k.search_volume || 'Unavailable'))}</td>
                        <td style="padding: 12px;">${this.escapeHtml(String(k.difficulty || 'Unavailable'))}</td>
                        <td style="padding: 12px; font-weight: 600;">${this.escapeHtml(k.position_display || (k.position ? `#${k.position}` : 'Not available (Connect Search Data)'))}</td>
                        <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">${this.escapeHtml(k.intent || 'Informational')}</td>
                    </tr>
                `).join('');

                contentContainer.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--bg-subtle);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Target Keywords (${displayKws.length})</h3>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 18px;">Target Keyword</th>
                                        <th style="padding: 12px;">Target Page URL</th>
                                        <th style="padding: 12px;">Search Volume</th>
                                        <th style="padding: 12px;">Difficulty</th>
                                        <th style="padding: 12px;">Google Position</th>
                                        <th style="padding: 12px 18px;">Search Intent</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${targetRows.length > 0 ? targetRows : `<tr><td colspan="6" style="padding: 32px; text-align: center; color: var(--text-secondary);">No target keywords available.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                return;
            }

            // Overview tab (Default)
            const paginated = Pagination.paginateArray(keywords, this.overviewPage, this.pageSize);
            this.overviewPage = paginated.currentPage;

            let rows = paginated.items.map(k => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(k.keyword)}</td>
                    <td style="padding: 12px;">${this.escapeHtml(k.group_name || k.category || k.type || 'Content Keyword')}</td>
                    <td style="padding: 12px; font-weight: 600;">${k.frequency || k.search_volume || 1} times ${renderTooltip('Content Frequency: How often this keyword appears in your scanned website content.')}</td>
                    <td style="padding: 12px;">${k.pages_found || 1} pages</td>
                    <td style="padding: 12px; font-size: 12px; color: var(--text-secondary);">
                        ${k.position_display || (k.position ? `#${k.position}` : '<span style="color: var(--text-tertiary);">Not available (Connect Search Data)</span>')}
                    </td>
                    <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">${this.escapeHtml(k.source || k.provenance || 'Website Scan')}</td>
                </tr>
            `).join('');

            contentContainer.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Keywords Found in Content (${keywords.length})</h3>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 18px;">Keyword</th>
                                    <th style="padding: 12px;">Keyword Topic</th>
                                    <th style="padding: 12px;">Content Frequency</th>
                                    <th style="padding: 12px;">Pages Found</th>
                                    <th style="padding: 12px;">Google Position</th>
                                    <th style="padding: 12px 18px;">Data Source</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows.length > 0 ? rows : `<tr><td colspan="6" style="padding: 32px; text-align: center; color: var(--text-secondary);">No keywords discovered yet. Run a website scan to extract content keywords.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                    <div id="kw-pagination-slot"></div>
                </div>
            `;

            // Append Pagination Controls
            const pageSlot = contentContainer.querySelector('#kw-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: keywords.length,
                    currentPage: this.overviewPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.overviewPage = newPage;
                        this.mounted();
                    }
                });
                pageSlot.appendChild(pag.render());
            }

        } catch (e) {
            renderBackendOfflineState(contentContainer, `We couldn't load this information right now. Please try again.`, () => this.mounted());
        }
    }

    renderResearchView(container, projectId) {
        container.innerHTML = `
            <div class="card" style="padding: 24px; margin-bottom: 20px;">
                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 8px 0; color: var(--text-primary);">Google Search Suggestions</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 16px 0;">Enter a seed term to discover popular Google search suggestions and customer search intent phrases.</p>
                <div style="display: flex; gap: 10px; max-width: 540px;">
                    <input type="text" id="input-seed-kw" placeholder="e.g. electrical services, solar installation..." style="flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; font-size: 13.5px; background: var(--bg-card); color: var(--text-primary);" />
                    <button id="btn-search-suggestions" class="btn btn-primary" style="font-weight: 600;">Get Search Suggestions</button>
                </div>
            </div>
            <div id="research-results-box"></div>
        `;

        const btn = container.querySelector('#btn-search-suggestions');
        const input = container.querySelector('#input-seed-kw');
        const resultsBox = container.querySelector('#research-results-box');

        const renderResearchTable = (suggestions, seed) => {
            const paginated = Pagination.paginateArray(suggestions, this.researchPage, this.pageSize);
            this.researchPage = paginated.currentPage;

            let resRows = paginated.items.map(s => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 10px 16px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(typeof s === 'string' ? s : s.keyword)}</td>
                    <td style="padding: 10px 16px; font-size: 12px; color: var(--text-secondary);">Google Search Suggestion</td>
                </tr>
            `).join('');

            resultsBox.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 12px;">
                    <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); background: var(--bg-subtle);">
                        <h4 style="margin: 0; font-size: 14px; font-weight: 700; color: var(--text-primary);">${suggestions.length} Google Search Suggestions Found</h4>
                    </div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 16px;">Suggested Search Term</th>
                                <th style="padding: 10px 16px;">Source</th>
                            </tr>
                        </thead>
                        <tbody>${resRows.length > 0 ? resRows : `<tr><td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">No suggestions found for '${this.escapeHtml(seed)}'.</td></tr>`}</tbody>
                    </table>
                    <div id="research-pagination-slot"></div>
                </div>
            `;

            const resSlot = resultsBox.querySelector('#research-pagination-slot');
            if (resSlot) {
                const pag = new Pagination({
                    totalItems: suggestions.length,
                    currentPage: this.researchPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.researchPage = newPage;
                        renderResearchTable(suggestions, seed);
                    }
                });
                resSlot.appendChild(pag.render());
            }
        };

        if (btn) {
            btn.onclick = async () => {
                const seed = input.value.trim();
                if (!seed) return;
                btn.disabled = true;
                btn.innerText = 'Searching Google Suggestions...';
                this.researchPage = 1;
                try {
                    const res = await apiClient.get(`/api/projects/${projectId}/keywords/research?q=${encodeURIComponent(seed)}&seed=${encodeURIComponent(seed)}`);
                    const suggestions = res.results || res.suggestions || res.keywords || [];
                    this.researchResults = suggestions;
                    renderResearchTable(suggestions, seed);
                } catch (err) {
                    resultsBox.innerHTML = `<div class="card" style="padding: 20px; color: var(--critical);">Failed to get search suggestions: ${this.escapeHtml(err.message)}</div>`;
                } finally {
                    btn.disabled = false;
                    btn.innerText = 'Get Search Suggestions';
                }
            };
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
