import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { Pagination } from '../components/Pagination.js';

export class CrawlHistory {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'history-view';
        this.currentPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 items per page
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Website Scan History</h1>
                <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Saved scan records for historical website analysis and comparisons.</p>
            </div>
            <div id="history-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading scan history...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('history-content');
        if (!container) return;

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const history = await crawlService.getCrawlHistory(projectStore.getSelectedProjectId());

            if (!history || history.length === 0) {
                container.innerHTML = `
                    <div class="card" style="padding: 40px 24px; text-align: center; max-width: 540px; margin: 24px auto;">
                        <div style="font-size: 36px; margin-bottom: 12px;">🕒</div>
                        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No Saved Website Scans Found</h3>
                        <p style="color: var(--text-secondary); font-size: 13.5px; margin-bottom: 20px;">Scan history records will appear here after you scan your website.</p>
                        <button class="btn btn-primary" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                    </div>
                `;
                return;
            }

            const domainStr = selectedProj ? (selectedProj.domain || selectedProj.url || 'website') : 'website';
            const safeDomain = domainStr.replace("https://", "").replace("http://", "").replace("www.", "").replace(/[^a-zA-Z0-9]/g, "_");

            const paginated = Pagination.paginateArray(history, this.currentPage, this.pageSize);
            this.currentPage = paginated.currentPage;

            let cards = paginated.items.map((snap, idx) => {
                const globalIndex = (paginated.currentPage - 1) * paginated.pageSize + idx;
                return `
                    <div class="card" style="padding: 24px; margin-bottom: 16px; border-radius: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                            <div>
                                <span style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.04em;">
                                    ${globalIndex === 0 ? '● LATEST SAVED SCAN' : `SAVED SCAN #${history.length - globalIndex}`}
                                </span>
                                <h3 style="font-size: 18px; font-weight: 700; margin-top: 4px; color: var(--text-primary);">${snap.timestamp}</h3>
                            </div>
                            <span class="badge ${snap.status === 'completed_with_errors' ? 'badge-warning' : (snap.status === 'failed' ? 'badge-critical' : 'badge-success')}" style="text-transform: uppercase;">
                                ${snap.status === 'completed_with_errors' ? 'Completed with Issues' : (snap.status || 'Completed')}
                            </span>
                        </div>

                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-top: 16px; font-size: 13px;">
                            <div style="background: var(--bg-subtle); padding: 10px; border-radius: 6px;">
                                <span style="color: var(--text-secondary); display: block; font-size: 11px;">PAGES SCANNED</span>
                                <strong style="font-size: 16px; color: var(--text-primary);">${snap.pages_crawled}</strong>
                            </div>
                            <div style="background: var(--bg-subtle); padding: 10px; border-radius: 6px;">
                                <span style="color: var(--text-secondary); display: block; font-size: 11px;">CRITICAL PROBLEMS</span>
                                <strong style="font-size: 16px; color: ${snap.critical_issues > 0 ? 'var(--critical)' : 'var(--text-primary)'};">${snap.critical_issues}</strong>
                            </div>
                            <div style="background: var(--bg-subtle); padding: 10px; border-radius: 6px;">
                                <span style="color: var(--text-secondary); display: block; font-size: 11px;">WARNINGS</span>
                                <strong style="font-size: 16px; color: ${snap.warning_issues > 0 ? 'var(--warning)' : 'var(--text-primary)'};">${snap.warning_issues}</strong>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <div>${cards}</div>
                <div id="history-pagination-slot" style="background: var(--bg-card); border-radius: 12px; margin-top: 12px; border: 1px solid var(--border);"></div>
            `;

            const pageSlot = container.querySelector('#history-pagination-slot');
            if (pageSlot && history.length > 0) {
                const pag = new Pagination({
                    totalItems: history.length,
                    currentPage: this.currentPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.currentPage = newPage;
                        this.mounted();
                    }
                });
                pageSlot.appendChild(pag.render());
            }

        } catch (e) {
            renderBackendOfflineState(container, `We couldn't load this information right now. Please try again.`, () => this.mounted());
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
