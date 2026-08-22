import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Backlinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'backlinks-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">Link Graph & Backlink Intelligence</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Outbound external links mapped by your site crawler, and inbound web-wide backlink intelligence.</p>
                </div>
                <div id="backlinks-actions" style="display: flex; gap: 10px;"></div>
            </div>
            <div id="backlinks-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading link intelligence...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('backlinks-content');
        const actionsContainer = document.getElementById('backlinks-actions');
        if (!container) return;

        try {
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

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/backlinks`);
            if (!res.ok) throw new Error("API response error");
            const data = await res.json();

            const outbound = data.outbound_links || [];

            let outboundTableHtml = '';
            if (outbound.length === 0) {
                outboundTableHtml = `
                    <div class="card" style="padding: 24px; text-align: center; color: var(--text-secondary);">
                        No outbound external links found on crawled pages.
                    </div>
                `;
            } else {
                const rows = outbound.map(l => `
                    <tr>
                        <td style="font-size: 12px; font-family: monospace;">${l.source_url || l.source || '-'}</td>
                        <td style="font-size: 12px; font-family: monospace; color: var(--primary);">${l.target_url || l.target || '-'}</td>
                        <td style="font-weight: 500;">${l.anchor_text || l.anchor || '(No text)'}</td>
                        <td>
                            <span class="badge ${l.nofollow ? 'badge-warning' : 'badge-success'}">
                                ${l.nofollow ? 'Nofollow' : 'Dofollow'}
                            </span>
                        </td>
                    </tr>
                `).join('');

                outboundTableHtml = `
                    <div class="card" style="padding: 0; overflow: hidden; margin-bottom: 32px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="font-size: 15px; font-weight: 600;">Outbound External Links Found On Website (${data.total_outbound_links || outbound.length})</h3>
                            <span class="badge badge-info">Collected via Website Crawler</span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Source Page</th>
                                    <th style="padding: 12px;">Target External Domain</th>
                                    <th style="padding: 12px;">Anchor Text</th>
                                    <th style="padding: 12px 20px;">Link Rel</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                `;
            }

            container.innerHTML = `
                <!-- SECTION 1: OUTBOUND EXTERNAL LINKS -->
                ${outboundTableHtml}

                <!-- SECTION 2: INBOUND BACKLINK PROFILE DATA SOURCE STATE -->
                <div class="card" style="padding: 32px; border-left: 4px solid var(--warning);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div>
                            <span style="font-size: 11px; font-weight: 700; color: var(--warning); text-transform: uppercase; letter-spacing: 0.04em;">DATA SOURCE STATUS</span>
                            <h3 style="font-size: 18px; font-weight: 600; margin-top: 4px;">Inbound Backlink Intelligence Not Connected</h3>
                        </div>
                        <span class="badge badge-warning">Provider / CSV Required</span>
                    </div>
                    <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.6; margin-bottom: 20px; max-width: 680px;">
                        A website crawler discovers outbound links placed <em>on your site</em>. Discovering external websites across the Web linking <em>to your domain</em> requires an external backlink provider adapter or a CSV dataset import.
                    </p>
                    <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                        <a href="/settings" data-link class="btn btn-primary btn-sm">Configure Backlink Source</a>
                        <a href="/import" data-link class="btn btn-secondary btn-sm">Import Backlink CSV</a>
                    </div>
                </div>
            `;

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend API server at http://127.0.0.1:8020.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Backlink Intelligence Error", e.message || "Unable to load backlink data.", () => this.mounted());
            }
        }
    }
}
