import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class CrawlHistory {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'history-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Crawl History & Snapshots</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Immutable local filesystem snapshots for historical SEO analysis and comparisons.</p>
            </div>
            <div id="history-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading crawl history...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('history-content');
        if (!container) return;

        try {
            const selectedProj = projectStore.getSelectedProject();
            const history = await crawlService.getCrawlHistory(projectStore.getSelectedProjectId());

            if (!history || history.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        </div>
                        <div class="empty-state-title">No Crawl Snapshots Found</div>
                        <div class="empty-state-desc">Crawl history snapshots will appear here as immutable records after you run website crawls.</div>
                        <button class="btn btn-primary" onclick="window.location.href='/'">Run First Crawl</button>
                    </div>
                `;
                return;
            }

            const domainStr = selectedProj ? (selectedProj.domain || selectedProj.url || 'website') : 'website';
            const safeDomain = domainStr.replace("https://", "").replace("http://", "").replace("www.", "").replace(/[^a-zA-Z0-9]/g, "_");

            let cards = history.map((snap, idx) => `
                <div class="card" style="padding: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                        <div>
                            <span style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.04em;">
                                ${idx === 0 ? '● LATEST COMPLETED CRAWL' : `SNAPSHOT #${history.length - idx}`}
                            </span>
                            <h3 style="font-size: 18px; font-weight: 600; margin-top: 4px;">${snap.timestamp}</h3>
                        </div>
                        <span class="badge badge-success" style="text-transform: uppercase;">
                            ${snap.status}
                        </span>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; margin-top: 16px; font-size: 13px;">
                        <div style="background: var(--bg-subtle); padding: 10px; border-radius: 6px;">
                            <span style="color: var(--text-secondary); display: block; font-size: 11px;">PAGES CRAWLED</span>
                            <strong style="font-size: 16px;">${snap.pages_crawled}</strong>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 10px; border-radius: 6px;">
                            <span style="color: var(--text-secondary); display: block; font-size: 11px;">CRITICAL ISSUES</span>
                            <strong style="font-size: 16px; color: ${snap.critical_issues > 0 ? 'var(--critical)' : 'inherit'};">${snap.critical_issues}</strong>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 10px; border-radius: 6px;">
                            <span style="color: var(--text-secondary); display: block; font-size: 11px;">WARNINGS</span>
                            <strong style="font-size: 16px; color: ${snap.warning_issues > 0 ? 'var(--warning)' : 'inherit'};">${snap.warning_issues}</strong>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 10px; border-radius: 6px;">
                            <span style="color: var(--text-secondary); display: block; font-size: 11px;">INTERNAL LINKS</span>
                            <strong style="font-size: 16px;">${snap.internal_links_count}</strong>
                        </div>
                    </div>

                    <div style="margin-top: 16px; font-size: 12px; font-family: monospace; color: var(--text-secondary);">
                        Storage Path: data/websites/${safeDomain}/crawls/${snap.folder_name}/
                    </div>
                </div>
            `).join('');

            container.innerHTML = `
                <div style="display: flex; flex-direction: column; gap: 16px;">
                    ${cards}
                </div>
            `;
        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {

                renderFeatureErrorState(container, "Crawl History Error", e.message || "Unable to load crawl history.", () => this.mounted());
            }
        }
    }
}
