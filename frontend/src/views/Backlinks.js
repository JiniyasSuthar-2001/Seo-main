import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Backlinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'backlinks-view';
        this.activeTab = 'outbound'; // outbound, gap
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">Backlink Intelligence & Gap</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Outbound crawl link graph, inbound backlink datasets, and competitor backlink gap analysis.</p>
                </div>
                <div id="backlinks-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <button class="btn ${this.activeTab === 'outbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-outbound-btn" style="font-size: 13px;">Outbound Links Graph</button>
                <button class="btn ${this.activeTab === 'gap' ? 'btn-primary' : 'btn-secondary'}" id="tab-gap-btn" style="font-size: 13px;">Backlink Gap vs Competitors</button>
            </div>

            <div id="backlinks-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading backlink intelligence...
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
        document.getElementById('tab-gap-btn')?.addEventListener('click', () => { this.activeTab = 'gap'; this.mounted(); });

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();


            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create a project workspace.</div>`;
                return;
            }

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <a href="${API_BASE_URL}/api/projects/${projectId}/backlinks/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            if (this.activeTab === 'gap') {
                const gapData = await apiClient.get(`/api/projects/${projectId}/backlinks/gap-analysis`);

                container.innerHTML = `
                    <div class="card" style="padding: 24px;">
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Backlink Gap Analysis vs Confirmed Competitors</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
                            ${gapData.message || "Identifies referring domains linking to competitors but not to your target domain."}
                        </p>
                        <div style="padding: 20px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px; color: var(--text-secondary); text-align: center;">
                            Confirmed Competitors Evaluated: <strong>${gapData.confirmed_competitors_count || 0}</strong>.
                            Import competitor backlink datasets to reveal intersecting link gap opportunities.
                        </div>
                    </div>
                `;
                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/backlinks`);
            const backlinks = data.backlinks || [];
            const summary = data.summary || {};


            container.innerHTML = `
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
                    <div class="kpi-card">
                        <div class="kpi-label">TOTAL BACKLINKS</div>
                        <div class="kpi-value">${summary.total_backlinks || 0}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">REFERRING DOMAINS</div>
                        <div class="kpi-value">${summary.referring_domains_count || 0}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">OUTBOUND EXTERNAL LINKS</div>
                        <div class="kpi-value">${summary.discovered_external_outbound || 0}</div>
                    </div>
                </div>

                <div class="card" style="padding: 24px;">
                    <h3 style="font-size: 15px; font-weight: 600; margin-bottom: 8px;">Inbound Backlink Dataset Status</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
                        ${data.message || "No external backlink dataset active."}
                    </p>
                    <div style="display: flex; gap: 12px;">
                        <a href="/import" data-link class="btn btn-secondary btn-sm">Import Backlink CSV</a>
                    </div>
                </div>
            `;
        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Backlink Intelligence Error", e.message || "Unable to load backlink data.", () => this.mounted());
            }
        }
    }
}
