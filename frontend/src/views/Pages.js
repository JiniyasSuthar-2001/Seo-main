import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

window.exportPagesCSV = () => {
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
    a.download = 'pages_audit.csv';
    a.click();
};

export class Pages {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'pages-view';
    }

    render() {
        this.element.innerHTML = `
            <div id="pages-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">Crawled Pages</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Extracted metadata, headings, indexability signals, and word counts per page.</p>
                </div>
                <div id="pages-actions" style="display: flex; gap: 10px;">
                </div>
            </div>

            <div id="pages-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading page records...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('pages-content');
        const actionsContainer = document.getElementById('pages-actions');
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
                    <a href="${API_BASE_URL}/api/projects/${projectId}/pages/report.pdf" target="_blank" class="btn btn-secondary btn-sm">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Download PDF
                    </a>
                    <a href="${API_BASE_URL}/api/projects/${projectId}/pages/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/pages?limit=100&offset=0`);
            if (!res.ok) throw new Error("API response error");
            const pages = await res.json();

            if (!pages || pages.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path></svg>
                        </div>
                        <div class="empty-state-title">No Crawled Pages Available</div>
                        <div class="empty-state-desc">Start your website crawl from the Dashboard to discover pages and parse HTML metadata.</div>
                        <button class="btn btn-primary" onclick="window.location.href='/'">Run First Crawl</button>
                    </div>
                `;
                return;
            }

            let rows = pages.map(p => `
                <tr>
                    <td style="font-weight: 500; font-family: monospace; font-size: 12px; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="${p.url}" target="_blank" style="color: var(--primary); text-decoration: none;">${p.url}</a>
                    </td>
                    <td>
                        <span class="badge ${p.status_code === 200 ? 'badge-success' : 'badge-warning'}">
                            ${p.status_code || 'Err'}
                        </span>
                    </td>
                    <td style="font-size: 13px;">${p.title || '<span style="color: var(--text-secondary);">(Missing Title)</span>'}</td>
                    <td style="font-size: 13px;">${p.h1 || '<span style="color: var(--text-secondary);">(Missing H1)</span>'}</td>
                    <td style="font-weight: 600;">${p.word_count || 0}</td>
                    <td style="font-size: 12px; font-family: monospace;">${p.canonical || '-'}</td>
                    <td><span class="badge badge-info">${p.robots_meta || 'index, follow'}</span></td>
                    <td style="font-weight: 600;">${p.internal_links_count || 0}</td>
                    <td>${p.response_time_ms ? `${p.response_time_ms}ms` : '-'}</td>
                </tr>
            `).join('');

            container.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-size: 15px; font-weight: 600;">Crawled Page Inventory (${pages.length})</h3>
                        <span style="font-size: 12px; color: var(--text-secondary);">Showing latest snapshot pages</span>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Page URL</th>
                                    <th style="padding: 12px;">Status</th>
                                    <th style="padding: 12px;">Title Tag</th>
                                    <th style="padding: 12px;">H1 Heading</th>
                                    <th style="padding: 12px;">Words</th>
                                    <th style="padding: 12px;">Canonical</th>
                                    <th style="padding: 12px;">Robots</th>
                                    <th style="padding: 12px;">Links</th>
                                    <th style="padding: 12px 20px;">Response</th>
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
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {

                renderFeatureErrorState(container, "Crawled Pages Error", e.message || "Unable to load page records.", () => this.mounted());
            }
        }
    }
}
