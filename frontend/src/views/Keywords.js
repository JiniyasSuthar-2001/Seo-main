import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { renderTooltip } from '../components/Tooltip.js';

export class Keywords {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'keywords-view';
        this.activeTab = 'overview';
        this.researchResults = [];
        this.isSearching = false;
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
            await apiClient.post(`/api/projects/${projectId}/keywords/cluster`, {});
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

            const data = await apiClient.get(`/api/projects/${projectId}/keywords`);
            const keywords = data.keywords || [];

            if (this.activeTab === 'research') {
                this.renderResearchView(contentContainer, projectId);
                return;
            }

            let rows = keywords.map(k => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(k.keyword)}</td>
                    <td style="padding: 12px;">${this.escapeHtml(k.category || k.type || 'Content Keyword')}</td>
                    <td style="padding: 12px; font-weight: 600;">${k.frequency || k.search_volume || 1} times ${renderTooltip('Content Frequency: How often this keyword appears in your scanned website content.')}</td>
                    <td style="padding: 12px;">${k.pages_found || 1} pages</td>
                    <td style="padding: 12px; font-size: 12px; color: var(--text-secondary);">
                        ${k.position ? `#${k.position}` : '<span style="color: var(--text-tertiary);">Not available (Connect Search Data)</span>'}
                    </td>
                    <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">${this.escapeHtml(k.provenance || 'Website Scan')}</td>
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
                </div>
            `;
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

        if (btn) {
            btn.onclick = async () => {
                const seed = input.value.trim();
                if (!seed) return;
                btn.disabled = true;
                btn.innerText = 'Searching Google Suggestions...';
                try {
                    const res = await apiClient.get(`/api/projects/${projectId}/keywords/research?seed=${encodeURIComponent(seed)}`);
                    const suggestions = res.suggestions || res.keywords || [];
                    let resRows = suggestions.map(s => `
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
                        </div>
                    `;
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
