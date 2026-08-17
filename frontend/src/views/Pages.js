import { pagesService } from '../services/pages.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState } from '../components/ErrorState.js';

export class Pages {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'pages-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Crawled Pages</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Detailed SEO audit of all discovered URLs from the latest crawl snapshot.</p>
            </div>
            <div id="pages-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading page data...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('pages-content');
        if (!container) return;

        try {
            const pages = await pagesService.getPages(projectStore.getSelectedProjectId(), 100, 0);

            if (!pages || pages.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                        </div>
                        <div class="empty-state-title">No Crawled Pages Yet</div>
                        <div class="empty-state-desc">Run a website crawl from the Dashboard to analyze titles, status codes, H1 headings, word counts, and technical issues.</div>
                        <button class="btn btn-primary" onclick="window.location.href='/'">Go to Dashboard</button>
                    </div>
                `;
                return;
            }

            let rows = pages.map(p => `
                <tr>
                    <td style="font-family: monospace; font-size: 13px;">
                        <a href="${p.url}" target="_blank" style="color: var(--primary); text-decoration: none; font-weight: 500;">${p.url}</a>
                    </td>
                    <td>
                        <span class="badge ${p.status_code === 200 ? 'badge-success' : 'badge-critical'}">
                            ${p.status_code || 'Err'}
                        </span>
                    </td>
                    <td style="max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.title || 'Missing Title'}">
                        ${p.title ? p.title : '<span style="color: var(--critical); font-style: italic;">Missing Title</span>'}
                    </td>
                    <td style="max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${p.h1 || 'Missing H1'}">
                        ${p.h1 ? p.h1 : '<span style="color: var(--warning); font-style: italic;">Missing H1</span>'}
                    </td>
                    <td style="text-align: right; font-variant-numeric: tabular-nums;">
                        ${p.word_count || 0}
                    </td>
                    <td style="text-align: right;">
                        ${p.internal_links_count || 0}
                    </td>
                    <td style="text-align: right; color: var(--text-secondary); font-size: 13px;">
                        ${p.response_time_ms ? p.response_time_ms + 'ms' : '-'}
                    </td>
                </tr>
            `).join('');

            container.innerHTML = `
                <div style="display: flex; gap: 12px; margin-bottom: 20px;">
                    <input type="text" placeholder="Filter by URL or title..." style="flex: 1; max-width: 360px; padding: 8px 14px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-card);">
                    <button class="btn btn-secondary btn-sm">All Statuses (${pages.length})</button>
                </div>

                <div class="data-table-wrapper">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>URL</th>
                                <th>Status</th>
                                <th>Page Title</th>
                                <th>H1 Heading</th>
                                <th style="text-align: right;">Words</th>
                                <th style="text-align: right;">Links</th>
                                <th style="text-align: right;">Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (e) {
            renderBackendOfflineState(container, "Unable to load crawled pages data.");
        }
    }
}
