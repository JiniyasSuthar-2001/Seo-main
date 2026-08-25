import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Pages {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'pages-view';
        this.currentPage = 1;
        this.pageSize = 20;
        this.activeStatus = 'all';
        this.projectId = null;
    }

    render() {
        this.element.innerHTML = `
            <div id="pages-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary);">Crawled Page Inventory</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px; font-size: 14px;">Complete server-paginated list of all discovered, crawled, and failed website pages.</p>
                </div>
                <div id="pages-actions" style="display: flex; gap: 10px;">
                </div>
            </div>

            <div id="pages-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading page inventory records...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        await projectStore.ensureInitialized();
        this.projectId = projectStore.getSelectedProjectId();
        const selectedProj = projectStore.getSelectedProject();
        const container = document.getElementById('pages-content');
        const actionsContainer = document.getElementById('pages-actions');

        if (!container) return;

        if (!selectedProj || !this.projectId) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create a project workspace.</div>`;
            return;
        }

        if (actionsContainer) {
            actionsContainer.innerHTML = `
                <a href="${API_BASE_URL}/api/projects/${this.projectId}/pages/report.pdf" target="_blank" class="btn btn-secondary btn-sm">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    Download PDF
                </a>
                <a href="${API_BASE_URL}/api/projects/${this.projectId}/pages/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
            `;
        }

        await this.loadPageInventory(1);
    }

    async loadPageInventory(pageNumber = 1) {
        const container = document.getElementById('pages-content');
        if (!container || !this.projectId) return;

        this.currentPage = pageNumber;
        const offset = (this.currentPage - 1) * this.pageSize;

        try {
            const data = await apiClient.get(`/api/projects/${this.projectId}/pages?limit=${this.pageSize}&offset=${offset}&status=${this.activeStatus}`);
            
            const pages = data.pages || data.items || [];
            const total = data.total || 0;
            const totalAll = data.total_all || total;
            const countCrawled = data.pages_crawled || 0;
            const countFailed = data.pages_failed || 0;
            const countBlocked = data.pages_blocked || 0;
            const countSkipped = data.pages_skipped || 0;

            const totalPages = Math.ceil(total / this.pageSize) || 1;

            if (totalAll === 0) {
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

            let rowsHTML = pages.map(p => {
                const stCode = p.status_code || 0;
                const isSuccess = p.is_success !== false && stCode === 200;
                const fetchSt = p.fetch_status || (stCode > 0 ? `HTTP ${stCode}` : 'FAILED');

                let badgeClass = 'badge-success';
                if ([401, 403].includes(stCode) || fetchSt === 'BLOCKED') badgeClass = 'badge-warning';
                else if (!isSuccess || stCode >= 400 || ['FAILED', 'TIMEOUT', 'DNS_ERROR', 'TLS_ERROR'].includes(fetchSt)) badgeClass = 'badge-danger';
                else if (fetchSt === 'SKIPPED') badgeClass = 'badge-secondary';

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-weight: 500; font-family: monospace; font-size: 12px; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 12px 18px;">
                            <a href="${this.escapeHtml(p.url)}" target="_blank" style="color: var(--primary); text-decoration: none;">${this.escapeHtml(p.url)}</a>
                        </td>
                        <td style="padding: 12px;">
                            <span class="badge ${badgeClass}" style="font-size: 11px; font-weight: 700;">
                                ${stCode > 0 ? stCode : fetchSt}
                            </span>
                        </td>
                        <td style="font-size: 13px; padding: 12px;">${p.title ? this.escapeHtml(p.title) : '<span style="color: var(--text-tertiary);">(Missing Title)</span>'}</td>
                        <td style="font-size: 13px; padding: 12px;">${p.h1 ? this.escapeHtml(p.h1) : '<span style="color: var(--text-tertiary);">(Missing H1)</span>'}</td>
                        <td style="font-weight: 600; padding: 12px;">${(p.word_count || 0).toLocaleString()}</td>
                        <td style="font-size: 12px; font-family: monospace; padding: 12px;">${p.canonical ? this.escapeHtml(p.canonical) : '-'}</td>
                        <td style="padding: 12px;"><span class="badge badge-info" style="font-size: 11px;">${p.robots_meta || 'index, follow'}</span></td>
                        <td style="padding: 12px;">${p.internal_links_count || 0}</td>
                        <td style="padding: 12px 18px; font-size: 12px; color: var(--text-secondary);">${p.response_time_ms ? `${p.response_time_ms}ms` : '-'}</td>
                    </tr>
                `;
            }).join('');

            if (pages.length === 0) {
                rowsHTML = `<tr><td colspan="9" style="text-align: center; padding: 32px; color: var(--text-secondary);">No pages match the selected status filter (${this.activeStatus}).</td></tr>`;
            }

            container.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                    <!-- FILTER TABS & METRICS -->
                    <div style="padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--bg-card); flex-wrap: wrap; gap: 12px;">
                        <div style="display: flex; gap: 8px;">
                            <button type="button" class="btn-filter-tab ${this.activeStatus === 'all' ? 'active' : ''}" data-status="all" style="padding: 6px 14px; border-radius: 20px; font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border); background: ${this.activeStatus === 'all' ? '#2563eb' : 'var(--bg-workspace)'}; color: ${this.activeStatus === 'all' ? '#fff' : 'var(--text-secondary)'};">
                                All Pages (${totalAll})
                            </button>
                            <button type="button" class="btn-filter-tab ${this.activeStatus === 'crawled' ? 'active' : ''}" data-status="crawled" style="padding: 6px 14px; border-radius: 20px; font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border); background: ${this.activeStatus === 'crawled' ? '#2563eb' : 'var(--bg-workspace)'}; color: ${this.activeStatus === 'crawled' ? '#fff' : 'var(--text-secondary)'};">
                                Crawled (${countCrawled})
                            </button>
                            <button type="button" class="btn-filter-tab ${this.activeStatus === 'failed' ? 'active' : ''}" data-status="failed" style="padding: 6px 14px; border-radius: 20px; font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border); background: ${this.activeStatus === 'failed' ? '#ef4444' : 'var(--bg-workspace)'}; color: ${this.activeStatus === 'failed' ? '#fff' : 'var(--text-secondary)'};">
                                Failed / Error (${countFailed})
                            </button>
                            <button type="button" class="btn-filter-tab ${this.activeStatus === 'blocked' ? 'active' : ''}" data-status="blocked" style="padding: 6px 14px; border-radius: 20px; font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid var(--border); background: ${this.activeStatus === 'blocked' ? '#f59e0b' : 'var(--bg-workspace)'}; color: ${this.activeStatus === 'blocked' ? '#fff' : 'var(--text-secondary)'};">
                                Blocked (${countBlocked})
                            </button>
                        </div>
                        <div style="font-size: 12.5px; color: var(--text-secondary);">
                            Showing <strong>${offset + 1}–${Math.min(offset + this.pageSize, total)}</strong> of <strong>${total}</strong> pages
                        </div>
                    </div>

                    <!-- TABLE CONTAINER -->
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-tertiary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 18px;">Page URL</th>
                                    <th style="padding: 12px;">Status</th>
                                    <th style="padding: 12px;">Title Tag</th>
                                    <th style="padding: 12px;">H1 Heading</th>
                                    <th style="padding: 12px;">Words</th>
                                    <th style="padding: 12px;">Canonical</th>
                                    <th style="padding: 12px;">Robots</th>
                                    <th style="padding: 12px;">Links</th>
                                    <th style="padding: 12px 18px;">Response</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rowsHTML}
                            </tbody>
                        </table>
                    </div>

                    <!-- PAGINATION BAR -->
                    <div style="padding: 16px 24px; border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle);">
                        <div style="font-size: 13px; color: var(--text-secondary);">
                            Page <strong>${this.currentPage}</strong> of <strong>${totalPages}</strong>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button type="button" id="btn-prev-page" class="btn btn-secondary btn-sm" ${this.currentPage <= 1 ? 'disabled' : ''}>
                                ← Previous
                            </button>
                            <button type="button" id="btn-next-page" class="btn btn-secondary btn-sm" ${this.currentPage >= totalPages ? 'disabled' : ''}>
                                Next →
                            </button>
                        </div>
                    </div>
                </div>
            `;

            // Bind Event Handlers
            container.querySelectorAll('.btn-filter-tab').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    const statusVal = btn.getAttribute('data-status');
                    if (statusVal && this.activeStatus !== statusVal) {
                        this.activeStatus = statusVal;
                        await this.loadPageInventory(1);
                    }
                });
            });

            container.querySelector('#btn-prev-page')?.addEventListener('click', async (e) => {
                e.preventDefault();
                if (this.currentPage > 1) {
                    await this.loadPageInventory(this.currentPage - 1);
                }
            });

            container.querySelector('#btn-next-page')?.addEventListener('click', async (e) => {
                e.preventDefault();
                if (this.currentPage < totalPages) {
                    await this.loadPageInventory(this.currentPage + 1);
                }
            });

        } catch (e) {
            console.error('[PAGES UI ERROR]', e);
            if (e.isNetworkError) {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else if (e.status === 401) {
                renderFeatureErrorState(container, "Authentication Required (401)", "Please sign in with your Google account to view page inventory.", () => window.location.href = '/login');
            } else if (e.status === 403) {
                renderFeatureErrorState(container, "Access Denied (403)", "You are not authorized to view this project's SEO data.", () => window.location.href = '/');
            } else {
                renderFeatureErrorState(container, "Crawled Pages Error", e.message || "Unable to load page records.", () => this.mounted());
            }
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
