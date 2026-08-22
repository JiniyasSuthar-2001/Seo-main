import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class InternalLinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'internal-links-view';
        this.activeTab = 'graph'; // graph, orphans, anchors, opportunities
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">Internal Link Intelligence</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Link graph architecture, orphan page detection, and internal link opportunity engine.</p>
                </div>
                <div id="links-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <button class="btn ${this.activeTab === 'graph' ? 'btn-primary' : 'btn-secondary'}" id="tab-graph-btn" style="font-size: 13px;">Mapped Link Graph</button>
                <button class="btn ${this.activeTab === 'orphans' ? 'btn-primary' : 'btn-secondary'}" id="tab-orphans-btn" style="font-size: 13px;">Orphan Pages</button>
                <button class="btn ${this.activeTab === 'anchors' ? 'btn-primary' : 'btn-secondary'}" id="tab-anchors-btn" style="font-size: 13px;">Anchor Text Analysis</button>
                <button class="btn ${this.activeTab === 'opportunities' ? 'btn-primary' : 'btn-secondary'}" id="tab-opps-btn" style="font-size: 13px;">Link Opportunities</button>
            </div>

            <div id="links-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading internal link intelligence...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('links-content');
        const actionsContainer = document.getElementById('links-actions');
        if (!container) return;

        document.getElementById('tab-graph-btn')?.addEventListener('click', () => { this.activeTab = 'graph'; this.mounted(); });
        document.getElementById('tab-orphans-btn')?.addEventListener('click', () => { this.activeTab = 'orphans'; this.mounted(); });
        document.getElementById('tab-anchors-btn')?.addEventListener('click', () => { this.activeTab = 'anchors'; this.mounted(); });
        document.getElementById('tab-opps-btn')?.addEventListener('click', () => { this.activeTab = 'opportunities'; this.mounted(); });

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
                    <a href="${API_BASE_URL}/api/projects/${projectId}/internal-links/report.pdf" target="_blank" class="btn btn-secondary btn-sm">Download PDF</a>
                    <a href="${API_BASE_URL}/api/projects/${projectId}/internal-links/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            if (this.activeTab === 'opportunities') {
                const resOpps = await fetch(`${API_BASE_URL}/api/projects/${projectId}/internal-links/opportunities`);
                const oppsData = await resOpps.json();
                const oppList = oppsData.opportunities || [];

                let rows = oppList.map(o => `
                    <tr>
                        <td style="font-family: monospace; font-size: 12px; color: var(--primary);">${o.source_page}</td>
                        <td style="font-family: monospace; font-size: 12px;">${o.target_page}</td>
                        <td style="font-weight: 600;">${o.suggested_anchor}</td>
                        <td style="font-size: 12px; color: var(--text-secondary);">${o.reason}</td>
                        <td><span class="badge ${o.priority === 'HIGH' ? 'badge-critical' : 'badge-warning'}">${o.priority}</span></td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 600;">Internal Link Growth Opportunities (${oppList.length})</h3>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 20px;">Source Page</th>
                                        <th style="padding: 12px;">Target Page</th>
                                        <th style="padding: 12px;">Suggested Anchor</th>
                                        <th style="padding: 12px;">Evidence & Reason</th>
                                        <th style="padding: 12px 20px;">Priority</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${rows.length > 0 ? rows : `<tr><td colspan="5" style="padding: 24px; text-align: center; color: var(--text-secondary);">No internal link opportunities detected.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                return;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/internal-links?limit=200&offset=0`);
            const data = await res.json();
            const links = data.internal_links || [];
            const orphans = data.orphan_pages || [];
            const anchors = data.anchor_texts || [];

            if (this.activeTab === 'orphans') {
                let orphanRows = orphans.map(url => `
                    <tr>
                        <td style="font-family: monospace; font-size: 13px; color: var(--primary); padding: 12px 20px;">${url}</td>
                        <td style="padding: 12px;"><span class="badge badge-critical">0 Incoming Internal Links</span></td>
                        <td style="padding: 12px; font-size: 12px; color: var(--text-secondary);">Add an internal link from the homepage or main menu to index this page.</td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 600;">Orphan Pages Detector (${orphans.length})</h3>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Orphan URL</th>
                                    <th style="padding: 12px;">Link Depth Status</th>
                                    <th style="padding: 12px;">Action Needed</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${orphanRows.length > 0 ? orphanRows : `<tr><td colspan="3" style="padding: 24px; text-align: center; color: var(--text-secondary);">No orphan pages detected. All crawled pages have incoming links.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                `;
                return;
            }

            if (this.activeTab === 'anchors') {
                let anchorRows = anchors.map(a => `
                    <tr>
                        <td style="font-weight: 600; padding: 12px 20px;">${a.anchor_text}</td>
                        <td style="padding: 12px;">${a.frequency}</td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; max-width: 600px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 600;">Anchor Text Frequency Distribution</h3>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Anchor Text</th>
                                    <th style="padding: 12px;">Frequency Count</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${anchorRows.length > 0 ? anchorRows : `<tr><td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">No anchor texts recorded.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                `;
                return;
            }

            // Default 'graph'
            let graphRows = links.map(l => `
                <tr>
                    <td style="font-family: monospace; font-size: 12px; color: var(--primary); padding: 12px 20px;">${l.source}</td>
                    <td style="font-family: monospace; font-size: 12px;">${l.target}</td>
                    <td style="font-weight: 500;">${l.anchor_text || '(No Anchor)'}</td>
                </tr>
            `).join('');

            container.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between;">
                        <h3 style="font-size: 15px; font-weight: 600;">Mapped Internal Link Graph (${links.length})</h3>
                    </div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 20px;">Source Page</th>
                                <th style="padding: 12px;">Target Page</th>
                                <th style="padding: 12px;">Anchor Text</th>
                            </tr>
                        </thead>
                        <tbody>${graphRows}</tbody>
                    </table>
                </div>
            `;
        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Internal Link Intelligence Error", e.message || "Unable to load link graph.", () => this.mounted());
            }
        }
    }
}
