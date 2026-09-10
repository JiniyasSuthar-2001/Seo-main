import { apiClient } from '../../services/apiClient.js';

export class MasterAuditLogs {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-audit-logs-view';
        this.search = '';
        this.page = 1;
        this.data = null;
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">MASTER SPACE</div>
                    <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 2px 0 0 0;">Platform Audit Logs</h1>
                </div>

                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; background: var(--bg-card); border: 1px solid var(--border);">
                    <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); background: var(--bg-subtle);">
                        <input type="text" id="audit-search-input" value="${this.search}" placeholder="Search admin email, action, or target..." style="padding: 6px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 280px;" />
                    </div>

                    <div id="audit-table-slot">
                        <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading audit logs...</div>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
        this.fetchData();
        return this.element;
    }

    bindEvents() {
        const input = this.element.querySelector('#audit-search-input');
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
            this.data = await apiClient.get(`/api/master/audit-logs?${query.toString()}`);
            this.renderTable();
        } catch (err) {
            console.error('[MASTER AUDIT LOGS] Error loading logs:', err);
        }
    }

    renderTable() {
        const slot = this.element.querySelector('#audit-table-slot');
        if (!slot || !this.data) return;

        const items = this.data.items || [];
        let rows = items.map(a => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 16px; font-size: 12px; font-family: monospace; color: var(--text-secondary);">${a.created_at ? a.created_at.replace('T', ' ').split('.')[0] : ''}</td>
                <td style="padding: 12px 16px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(a.actor_email || a.actor_id)}</td>
                <td style="padding: 12px 16px;"><span class="badge badge-secondary" style="font-family: monospace; font-size: 11px;">${this.escapeHtml(a.action)}</span></td>
                <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${this.escapeHtml(a.target_type || '-')}: ${this.escapeHtml(a.target_id || '-')}</td>
                <td style="padding: 12px 16px;"><span class="badge ${a.status === 'SUCCESS' ? 'badge-success' : 'badge-critical'}">${this.escapeHtml(a.status)}</span></td>
                <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${this.escapeHtml(a.reason || '-')}</td>
            </tr>
        `).join('');

        slot.innerHTML = `
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <thead>
                        <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                            <th style="padding: 12px 16px;">Timestamp</th>
                            <th style="padding: 12px 16px;">Actor / Admin</th>
                            <th style="padding: 12px 16px;">Action</th>
                            <th style="padding: 12px 16px;">Target</th>
                            <th style="padding: 12px 16px;">Status</th>
                            <th style="padding: 12px 16px;">Reason</th>
                        </tr>
                    </thead>
                    <tbody>${rows.length > 0 ? rows : `<tr><td colspan="6" style="padding: 32px; text-align: center; color: var(--text-secondary);">No audit logs recorded.</td></tr>`}</tbody>
                </table>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
