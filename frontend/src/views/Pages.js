import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { renderAIBadge, renderSourceBadge, renderViewEvidenceButton } from '../components/AIBadge.js';
import { apiClient } from '../services/apiClient.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class Pages {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'pages-view';
        this.currentPage = 1;
        this.pageSize = 20; // PLATFORM STANDARD: 20 rows per page
        this.activeStatus = 'all';
        this.projectId = null;
    }

    render() {
        this.element.innerHTML = `
            <div id="pages-header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0;">Pages Found on Your Site</h1>
                        ${renderSourceBadge('crawl')}
                    </div>
                    <p style="color: var(--text-secondary); margin-top: 4px; font-size: 14px;">Complete list of all pages discovered on your website during the latest scan.</p>
                </div>
                <div id="pages-actions" style="display: flex; gap: 10px;">
                </div>
            </div>

            <div id="pages-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading pages found on your site...
                </div>
            </div>
        `;

        window.openPageDetailModal = (pageDataJson) => {
            try {
                const p = JSON.parse(decodeURIComponent(pageDataJson));
                this.showPageDetailModal(p);
            } catch(err) {
                console.error("Failed to parse page data", err);
            }
        };

        return this.element;
    }

    showPageDetailModal(p) {
        let modal = document.getElementById('page-detail-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'page-detail-modal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(4px);';
            document.body.appendChild(modal);
        }

        const currentTitle = p.title || '(Missing Page Title)';
        const currentMeta = p.meta_description || '(Missing Search Description)';

        const domainName = p.url ? new URL(p.url).hostname : 'website';
        const suggestedTitle = p.title ? `${p.title} | Improved for Search` : `Optimized Title for ${domainName}`;

        modal.innerHTML = `
            <div style="background: var(--bg-card); width: 90%; max-width: 680px; max-height: 85vh; border-radius: 14px; border: 1px solid var(--border); overflow-y: auto; padding: 24px; box-shadow: var(--shadow-lg);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 14px;">
                    <div>
                        <h3 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Page Information Details</h3>
                        <div style="font-size: 12px; font-family: monospace; color: var(--primary); margin-top: 4px;">${this.escapeHtml(p.url)}</div>
                    </div>
                    <button onclick="document.getElementById('page-detail-modal').style.display='none'" style="font-size: 24px; color: var(--text-tertiary); cursor: pointer; background: none; border: none;">&times;</button>
                </div>

                <!-- TITLE COMPARISON -->
                <div style="margin-bottom: 20px; padding: 14px; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <strong style="font-size: 13px; color: var(--text-primary);">Page Title Tag ${renderTooltip('The primary title tag displayed in Google search results.')}</strong>
                        ${renderSourceBadge('crawl')}
                    </div>
                    <div style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 12px; background: var(--bg-card); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border);">
                        ${this.escapeHtml(currentTitle)}
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <strong style="font-size: 13px; color: #a855f7;">AI Suggested Title Tag</strong>
                        ${renderAIBadge('generated')}
                    </div>
                    <div style="font-size: 12.5px; color: var(--text-primary); font-weight: 600; background: rgba(168, 85, 247, 0.08); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(168, 85, 247, 0.25);">
                        ${this.escapeHtml(suggestedTitle)}
                    </div>
                </div>

                <!-- SEARCH DESCRIPTION -->
                <div style="margin-bottom: 20px; padding: 14px; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <strong style="font-size: 13px; color: var(--text-primary);">Search Description ${renderTooltip('The short description that may appear underneath your page in Google search results.')}</strong>
                        ${renderSourceBadge('crawl')}
                    </div>
                    <div style="font-size: 12.5px; color: var(--text-secondary); background: var(--bg-card); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border);">
                        ${this.escapeHtml(currentMeta)}
                    </div>
                </div>

                <div style="text-align: right;">
                    <button onclick="document.getElementById('page-detail-modal').style.display='none'" class="btn btn-secondary btn-sm">Close</button>
                </div>
            </div>
        `;
        modal.style.display = 'flex';
    }

    async mounted() {
        const container = document.getElementById('pages-content');
        const actionsContainer = document.getElementById('pages-actions');

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            this.projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !this.projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
                return;
            }

            const safeProjName = (selectedProj.name || 'website').replace(/[^a-zA-Z0-9_-]/g, '_');
            const todayStr = new Date().toISOString().split('T')[0];

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <button id="btn-export-pages-csv" class="btn btn-secondary btn-sm">Download CSV</button>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                `;

                const csvBtn = document.getElementById('btn-export-pages-csv');
                if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${this.projectId}/pages/export.csv`, `${safeProjName}-Crawled-Pages-${todayStr}.csv`, e.currentTarget);
            }

            await this.loadPageInventory(1);

        } catch (e) {
            renderBackendOfflineState(container, `We couldn't load this information right now. Please try again.`, () => this.mounted());
        }
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

            if (totalAll === 0) {
                container.innerHTML = `
                    <div class="empty-state" style="padding: 40px; text-align: center;">
                        <div class="empty-state-icon" style="font-size: 36px; margin-bottom: 12px;">📄</div>
                        <div class="empty-state-title" style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No Website Scan Yet</div>
                        <div class="empty-state-desc" style="color: var(--text-secondary); max-width: 500px; margin: 0 auto 20px; font-size: 13.5px; line-height: 1.5;">
                            We haven't checked your website pages yet. Run a website scan to discover your pages, technical problems, links, and content.
                        </div>
                        <button class="btn btn-primary" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                    </div>
                `;
                return;
            }

            let rowsHTML = pages.map(p => {
                const stCode = p.status_code || 0;
                const isSuccess = p.is_success !== false && stCode === 200;

                let statusLabel = 'OK (200)';
                let badgeClass = 'badge-success';

                if (stCode === 404) {
                    statusLabel = 'Broken Page (404)';
                    badgeClass = 'badge-danger';
                } else if (stCode >= 400) {
                    statusLabel = `Page Status ${stCode}`;
                    badgeClass = 'badge-danger';
                } else if (!isSuccess) {
                    statusLabel = 'Failed Load';
                    badgeClass = 'badge-danger';
                }

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-weight: 500; font-family: monospace; font-size: 12px; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 12px 18px;">
                            <a href="${this.escapeHtml(p.url)}" target="_blank" style="color: var(--primary); text-decoration: none;">${this.escapeHtml(p.url)}</a>
                        </td>
                        <td style="padding: 12px;">
                            <span class="badge ${badgeClass}" style="font-size: 11px; font-weight: 700;">
                                ${statusLabel}
                            </span>
                        </td>
                        <td style="font-size: 13px; padding: 12px;">${p.title ? this.escapeHtml(p.title) : '<span style="color: var(--text-tertiary);">(Missing Page Title)</span>'}</td>
                        <td style="font-size: 13px; padding: 12px;">${p.h1 ? this.escapeHtml(p.h1) : '<span style="color: var(--text-tertiary);">(Missing H1 Heading)</span>'}</td>
                        <td style="font-weight: 600; padding: 12px;">${(p.word_count || 0).toLocaleString()} words</td>
                        <td style="font-size: 12px; font-family: monospace; padding: 12px;">${p.canonical ? this.escapeHtml(p.canonical) : '-'}</td>
                        <td style="padding: 12px;">${p.internal_links_count || 0} links</td>
                    </tr>
                `;
            }).join('');

            container.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Pages Found on Your Site (${total})</h3>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 18px;">Page Address / URL</th>
                                    <th style="padding: 12px;">Page Status ${renderTooltip('Whether the page loaded successfully or returned an error status.')}</th>
                                    <th style="padding: 12px;">Page Title ${renderTooltip('The primary title tag displayed in Google search results.')}</th>
                                    <th style="padding: 12px;">Main Heading (H1) ${renderTooltip('The primary heading at the top of the page.')}</th>
                                    <th style="padding: 12px;">Word Count</th>
                                    <th style="padding: 12px;">Preferred Address ${renderTooltip('The preferred version of a page that search engines should index.')}</th>
                                    <th style="padding: 12px;">Internal Links ${renderTooltip('Number of links pointing to other pages on your website.')}</th>
                                </tr>
                            </thead>
                            <tbody>${rowsHTML}</tbody>
                        </table>
                    </div>
                    <div id="pages-pagination-slot"></div>
                </div>
            `;

            // Append Pagination Controls
            const pageSlot = container.querySelector('#pages-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: total,
                    currentPage: this.currentPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => this.loadPageInventory(newPage)
                });
                pageSlot.appendChild(pag.render());
            }

        } catch (err) {
            renderBackendOfflineState(container, `We couldn't load this information right now. Please try again.`, () => this.mounted());
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
