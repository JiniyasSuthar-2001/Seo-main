import { apiClient } from '../../services/apiClient.js';

export class MasterWebsites {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-websites-view';
        this.search = '';
        this.page = 1;
        this.data = null;
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">MASTER SPACE</div>
                    <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 2px 0 0 0;">Website Monitoring</h1>
                </div>

                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; background: var(--bg-card); border: 1px solid var(--border);">
                    <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); background: var(--bg-subtle);">
                        <input type="text" id="site-search-input" value="${this.search}" placeholder="Search website URL or project name..." style="padding: 6px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 280px;" />
                    </div>

                    <div id="websites-table-slot">
                        <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading website directory...</div>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
        this.fetchData();
        return this.element;
    }

    bindEvents() {
        const input = this.element.querySelector('#site-search-input');
        if (input) {
            input.oninput = (e) => {
                this.search = e.target.value;
                this.page = 1;
                this.fetchData();
            };
        }
    }

    async fetchData() {
        try {
            const query = new URLSearchParams({ search: this.search, page: this.page, page_size: 20 });
            this.data = await apiClient.get(`/api/master/websites?${query.toString()}`);
            this.renderTable();
        } catch (err) {
            console.error('[MASTER WEBSITES] Error loading websites:', err);
        }
    }

    renderTable() {
        const slot = this.element.querySelector('#websites-table-slot');
        if (!slot || !this.data) return;

        const items = this.data.items || [];
        let rows = items.map(w => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 16px;">
                    <div style="font-weight: 700; color: var(--text-primary); font-size: 13.5px;">${this.escapeHtml(w.name)}</div>
                    <div style="font-size: 11.5px; font-family: monospace; color: var(--primary);">${this.escapeHtml(w.url)}</div>
                </td>
                <td style="padding: 12px 16px;">
                    <span class="badge ${w.crawl_status === 'completed' ? 'badge-success' : 'badge-secondary'}" style="font-size: 11px;">${this.escapeHtml(w.crawl_status)}</span>
                </td>
                <td style="padding: 12px 16px; font-weight: 600;">${w.pages}</td>
                <td style="padding: 12px 16px; font-weight: 600; color: #f87171;">${w.issues}</td>
                <td style="padding: 12px 16px;">${w.ai_requests} reqs (${(w.ai_tokens || 0).toLocaleString()} tok)</td>
                <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${w.last_crawl ? w.last_crawl.split('T')[0] : 'Never'}</td>
                <td style="padding: 12px 16px; text-align: right;">
                    <a href="/master/websites/${w.id}" data-link class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 4px 10px;">
                        Website 360 ↗
                    </a>
                </td>
            </tr>
        `).join('');

        slot.innerHTML = `
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <thead>
                        <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                            <th style="padding: 12px 16px;">Website / Domain</th>
                            <th style="padding: 12px 16px;">Crawl Status</th>
                            <th style="padding: 12px 16px;">Pages</th>
                            <th style="padding: 12px 16px;">Issues</th>
                            <th style="padding: 12px 16px;">AI Usage</th>
                            <th style="padding: 12px 16px;">Last Crawl</th>
                            <th style="padding: 12px 16px; text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>${rows.length > 0 ? rows : `<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--text-secondary);">No websites found.</td></tr>`}</tbody>
                </table>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
