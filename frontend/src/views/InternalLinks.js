import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

window.exportInternalLinksCSV = () => {
    const table = document.querySelector('table');
    if (!table) return;
    let csv = [];
    for (let i = 0; i < table.rows.length; i++) {
        let row = [], cols = table.rows[i].querySelectorAll('td, th');
        for (let j = 0; j < cols.length; j++) 
            row.push('"' + cols[j].innerText.replace(/"/g, '""') + '"');
        csv.push(row.join(','));
    }
    const blob = new Blob([csv.join('\n')], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'internal_link_graph.csv';
    a.click();
};

export class InternalLinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'internal-links-view';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">Internal Link Graph</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Page-to-page link architecture, in-scope & out-of-scope link targets, and anchor text.</p>
                </div>
                <div id="links-actions" style="display: flex; gap: 10px;">
                </div>
            </div>

            <div id="links-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading internal link graph...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('links-content');
        const actionsContainer = document.getElementById('links-actions');
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
                    <a href="${API_BASE_URL}/api/projects/${projectId}/internal-links/report.pdf" target="_blank" class="btn btn-secondary btn-sm">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Download PDF
                    </a>
                    <a href="${API_BASE_URL}/api/projects/${projectId}/internal-links/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/internal-links?limit=200&offset=0`);
            if (!res.ok) throw new Error("API response error");
            const links = await res.json();

            if (!links || links.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle></svg>
                        </div>
                        <div class="empty-state-title">No Internal Links Mapped</div>
                        <div class="empty-state-desc">Start a crawl from the Dashboard to extract HTML link relationships across pages for <strong>${selectedProj.name}</strong>.</div>
                        <button class="btn btn-primary" onclick="window.location.href='/'">Run Website Crawl</button>
                    </div>
                `;
                return;
            }

            const uniqueSources = new Set(links.map(l => l.source)).size;
            const uniqueTargets = new Set(links.map(l => l.target)).size;

            let rows = links.map(l => `
                <tr>
                    <td style="font-family: monospace; font-size: 12px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="${l.source}" target="_blank" style="color: var(--primary); text-decoration: none;">${l.source}</a>
                    </td>
                    <td style="font-family: monospace; font-size: 12px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="${l.target}" target="_blank" style="color: var(--text-primary); text-decoration: none;">${l.target}</a>
                    </td>
                    <td style="font-weight: 500;">${l.anchor_text || '<span style="color: var(--text-secondary);">(No Anchor Text)</span>'}</td>
                    <td><span class="badge badge-success">In Scope</span></td>
                </tr>
            `).join('');

            container.innerHTML = `
                <!-- SUMMARY KPI METRICS -->
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
                    <div class="kpi-card">
                        <div class="kpi-label">TOTAL INTERNAL LINKS</div>
                        <div class="kpi-value">${links.length}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">Source: Website Crawl</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">UNIQUE SOURCE PAGES</div>
                        <div class="kpi-value">${uniqueSources}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">Linking URLs</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-label">UNIQUE TARGET PAGES</div>
                        <div class="kpi-value">${uniqueTargets}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">Destination URLs</div>
                    </div>
                </div>

                <div class="card" style="padding: 0; overflow: hidden;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-size: 15px; font-weight: 600;">Mapped Internal Links (${links.length})</h3>
                        <span class="badge badge-info">Source: Website Crawl</span>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Source Page</th>
                                    <th style="padding: 12px;">Target Page</th>
                                    <th style="padding: 12px;">Anchor Text</th>
                                    <th style="padding: 12px 20px;">Scope Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend API server at http://127.0.0.1:8020.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Internal Link Graph Error", e.message || "Unable to load internal link graph.", () => this.mounted());
            }
        }
    }
}
