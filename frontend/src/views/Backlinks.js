import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderTooltip } from '../components/Tooltip.js';

export class Backlinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'backlinks-view';
        this.activeTab = 'outbound'; // 'outbound', 'inbound', 'gap'
        
        // Outbound links state
        this.outboundLinks = [];
        this.outboundSummary = {};
        this.summary = {};
        this.provenance = {};
        this.inboundBacklinks = [];
        
        // Filtering & pagination state
        this.searchQuery = '';
        this.domainFilter = 'all';
        this.typeFilter = 'all';
        this.statusFilter = 'all';
        this.currentPage = 1;
        this.pageSize = 25;
        this.sortBy = 'source';
        this.sortOrder = 'asc';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Website Links</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">View links from other websites pointing to your site and external links found on your site.</p>
                </div>
                <div id="backlinks-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 12px; flex-wrap: wrap;">
                <button class="btn ${this.activeTab === 'outbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-outbound-btn" style="font-size: 13px;">Links Found On Your Website</button>
                <button class="btn ${this.activeTab === 'inbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-inbound-btn" style="font-size: 13px;">Links From Other Websites</button>
                <button class="btn ${this.activeTab === 'gap' ? 'btn-primary' : 'btn-secondary'}" id="tab-gap-btn" style="font-size: 13px;">Competitor Link Comparison</button>
            </div>

            <div id="backlinks-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading website link information...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('backlinks-content');
        const actionsContainer = document.getElementById('backlinks-actions');
        if (!container) return;

        document.getElementById('tab-outbound-btn')?.addEventListener('click', () => { this.activeTab = 'outbound'; this.mounted(); });
        document.getElementById('tab-inbound-btn')?.addEventListener('click', () => { this.activeTab = 'inbound'; this.mounted(); });
        document.getElementById('tab-gap-btn')?.addEventListener('click', () => { this.activeTab = 'gap'; this.mounted(); });

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

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <a href="/import" data-link class="btn btn-secondary btn-sm">Import Link Data</a>
                    <button id="btn-export-backlinks-csv" class="btn btn-secondary btn-sm">Download CSV</button>
                `;

                const csvBtn = document.getElementById('btn-export-backlinks-csv');
                if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/backlinks/export.csv`, `${safeProjName}-Backlinks-${todayStr}.csv`, e.currentTarget);
            }

            if (this.activeTab === 'gap') {
                const gapData = await apiClient.get(`/api/projects/${projectId}/backlinks/gap-analysis`);
                this.renderGapTab(container, gapData);
                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/backlinks`);
            this.outboundLinks = data.outbound_links || [];
            this.outboundSummary = data.outbound_summary || {};
            this.summary = data.summary || {};
            this.provenance = data.provenance || {};
            this.inboundBacklinks = data.backlinks || [];

            if (this.activeTab === 'inbound') {
                this.renderInboundTab(container);
                return;
            }

            // Default 'outbound'
            this.renderOutboundTab(container);

        } catch (e) {
            renderFeatureErrorState(container, "Failed to load link data", e.message || "Unable to load website links.", () => this.mounted());
        }
    }

    renderInboundTab(container) {
        const backlinks = this.inboundBacklinks || [];
        if (backlinks.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 24px auto; background: var(--bg-subtle); border-radius: 14px; border: 1px dashed var(--border);">
                    <div style="font-size: 36px; margin-bottom: 12px;">🔗</div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No links from other websites found yet</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        Your website scan can find links between your own pages. Links from other websites require backlink data from a connected provider or an imported dataset.
                    </p>
                    <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                        <a href="/import" data-link class="btn btn-primary btn-sm">Import Link Data</a>
                        <a href="/integrations" data-link class="btn btn-secondary btn-sm">Connect a Data Source</a>
                    </div>
                </div>
            `;
            return;
        }

        let rows = backlinks.map(b => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 18px; font-family: monospace; font-size: 12px; color: var(--primary);">${this.escapeHtml(b.source_url)}</td>
                <td style="padding: 12px; font-family: monospace; font-size: 12px;">${this.escapeHtml(b.target_url)}</td>
                <td style="padding: 12px; font-weight: 600;">${this.escapeHtml(b.anchor_text || '(No Link Text)')}</td>
                <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">${this.escapeHtml(b.provenance || 'Imported Data')}</td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Links From Other Websites (${backlinks.length})</h3>
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 18px;">Referring Website URL</th>
                                <th style="padding: 12px;">Your Page URL</th>
                                <th style="padding: 12px;">Link Text</th>
                                <th style="padding: 12px 18px;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            </div>
        `;
    }

    renderOutboundTab(container) {
        const links = this.outboundLinks || [];
        let rows = links.map(l => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 18px; font-family: monospace; font-size: 12px; color: var(--primary);">${this.escapeHtml(l.source_page || l.source)}</td>
                <td style="padding: 12px; font-family: monospace; font-size: 12px;">${this.escapeHtml(l.target_url || l.target)}</td>
                <td style="padding: 12px; font-weight: 600;">${this.escapeHtml(l.anchor_text || '(No Link Text)')}</td>
                <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">Website Scan</td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Links Found On Your Website (${links.length})</h3>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">External links found on your website during the latest scan.</div>
                    </div>
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 18px;">Your Page URL</th>
                                <th style="padding: 12px;">External Website Link</th>
                                <th style="padding: 12px;">Link Text ${renderTooltip('Text used to link to the external website.')}</th>
                                <th style="padding: 12px 18px;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.length > 0 ? rows : `<tr><td colspan="4" style="padding: 32px; text-align: center; color: var(--text-secondary);">No external links found on your website.</td></tr>`}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    renderGapTab(container, gapData) {
        container.innerHTML = `
            <div class="card" style="padding: 24px; border-radius: 14px;">
                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 8px 0; color: var(--text-primary);">Competitor Link Comparison</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 16px 0;">Compare websites linking to your competitors against websites linking to your business.</p>
                <div style="padding: 24px; text-align: center; background: var(--bg-subtle); border-radius: 10px; border: 1px dashed var(--border); color: var(--text-secondary); font-size: 13.5px;">
                    Add competitor websites in <strong>Competitors</strong> to compare link profile opportunities.
                </div>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
