import { apiClient } from '../../services/apiClient.js';

export class MasterWebsiteDetail {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-website-detail-view';
        this.websiteId = null;
        this.data = null;
    }

    async render() {
        const parts = window.location.pathname.split('/');
        this.websiteId = parts[parts.length - 1];

        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    <a href="/master/websites" data-link style="color: var(--primary); font-size: 12px; font-weight: 700; text-decoration: none;">← Back to Websites</a>
                    <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 6px 0 0 0;">Website 360</h1>
                </div>

                <div id="website-detail-content">
                    <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading Website 360 payload...</div>
                </div>
            </div>
        `;

        this.fetchDetail();
        return this.element;
    }

    async fetchDetail() {
        try {
            this.data = await apiClient.get(`/api/master/websites/${this.websiteId}`);
            this.renderContent();
        } catch (err) {
            console.error('[MASTER WEBSITE DETAIL] Error:', err);
        }
    }

    renderContent() {
        const content = this.element.querySelector('#website-detail-content');
        if (!content || !this.data) return;

        const p = this.data.project || {};
        const cust = this.data.customer || {};
        const m = this.data.metrics || {};
        const timeline = this.data.timeline || [];

        content.innerHTML = `
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border); margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 20px; font-weight: 800; color: var(--text-primary);">${this.escapeHtml(p.name)}</div>
                        <div style="font-size: 12.5px; color: var(--primary); font-family: monospace; margin-top: 3px;">URL: ${this.escapeHtml(p.url)}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Owner: ${this.escapeHtml(cust.name || cust.email || 'Platform System')}</div>
                    </div>
                    <span class="badge ${m.crawl_status === 'completed' ? 'badge-success' : 'badge-secondary'}">${this.escapeHtml(m.crawl_status)}</span>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--border);">
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">Pages Crawled</div>
                        <div style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${m.pages_count}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">Audit Issues</div>
                        <div style="font-size: 20px; font-weight: 800; color: #f87171; margin-top: 2px;">${m.issues_count}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">AI Requests</div>
                        <div style="font-size: 20px; font-weight: 800; color: #a855f7; margin-top: 2px;">${m.ai_requests}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">AI Tokens</div>
                        <div style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${(m.ai_tokens || 0).toLocaleString()}</div>
                    </div>
                </div>
            </div>

            <!-- CHRONOLOGICAL EVENT TIMELINE -->
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 16px 0; color: var(--text-primary);">Chronological Website Event Timeline</h3>
                ${timeline.length > 0 ? timeline.map(t => `
                    <div style="padding: 12px; border-left: 3px solid var(--primary); background: var(--bg-subtle); margin-bottom: 10px; border-radius: 0 8px 8px 0;">
                        <div style="display: flex; justify-content: space-between; font-size: 12px;">
                            <strong style="color: var(--text-primary);">${this.escapeHtml(t.title)}</strong>
                            <span style="color: var(--text-secondary); font-family: monospace;">${t.time ? t.time.replace('T', ' ').split('.')[0] : ''}</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${this.escapeHtml(t.detail)}</div>
                    </div>
                `).join('') : `<div style="font-size: 12px; color: var(--text-secondary);">No timeline events recorded yet.</div>`}
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
