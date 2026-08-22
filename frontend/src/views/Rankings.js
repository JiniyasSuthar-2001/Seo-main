import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Rankings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'rankings-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">Rank Tracking & SERP Positions</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Monitor real-time Google search positions, SERP movements, and ranking URLs.</p>
                </div>
                <div id="rankings-actions" style="display: flex; gap: 10px;"></div>
            </div>
            <div id="rankings-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading rank tracking data...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('rankings-content');
        const actionsContainer = document.getElementById('rankings-actions');
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
                    <a href="${API_BASE_URL}/api/projects/${projectId}/rankings/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/rankings`);
            if (!res.ok) throw new Error("API response error");
            const data = await res.json();

            const rankings = data.rankings || [];

            if (rankings.length === 0) {
                container.innerHTML = `
                    <div class="card" style="padding: 32px; border-left: 4px solid var(--primary);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                            <div>
                                <span style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.04em;">DATA SOURCE STATUS</span>
                                <h3 style="font-size: 18px; font-weight: 600; margin-top: 4px;">Search Console & Rank Tracker Not Connected</h3>
                            </div>
                            <span class="badge badge-info">Connect Source</span>
                        </div>
                        <p style="color: var(--text-secondary); font-size: 14px; line-height: 1.6; margin-bottom: 20px; max-width: 680px;">
                            Rank position tracking requires connecting your Google Search Console account or configuring a SERP rank provider adapter to query Google/Bing SERP positions for your target domain (<strong>${selectedProj.domain || selectedProj.url}</strong>).
                        </p>
                        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                            <a href="/settings" data-link class="btn btn-primary btn-sm">Connect Search Console</a>
                            <a href="/settings" data-link class="btn btn-secondary btn-sm">Configure Rank Tracking</a>
                            <a href="/import" data-link class="btn btn-secondary btn-sm">Import Ranking CSV</a>
                        </div>
                    </div>
                `;
            } else {
                const rows = rankings.map(r => `
                    <tr>
                        <td style="font-weight: 600;">${r.keyword}</td>
                        <td style="font-weight: 700; color: var(--primary);">#${r.position}</td>
                        <td>${r.change ? (r.change > 0 ? `+${r.change}` : r.change) : '-'}</td>
                        <td style="font-size: 12px; font-family: monospace;">${r.url || '-'}</td>
                        <td><span class="badge badge-info">${r.source || 'SERP Tracker'}</span></td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="font-size: 15px; font-weight: 600;">Tracked Keyword Rankings (${rankings.length})</h3>
                            <span class="badge badge-success">Live Tracking Active</span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Keyword</th>
                                    <th style="padding: 12px;">Position</th>
                                    <th style="padding: 12px;">Movement</th>
                                    <th style="padding: 12px;">Ranking URL</th>
                                    <th style="padding: 12px 20px;">Data Source</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                `;
            }

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend API server at http://127.0.0.1:8020.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Rank Tracking Error", e.message || "Unable to load rank tracking data.", () => this.mounted());
            }
        }
    }
}
