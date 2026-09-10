import { apiClient } from '../../services/apiClient.js';

export class MasterCustomers {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-customers-view';
        this.search = '';
        this.statusFilter = 'all';
        this.page = 1;
        this.data = null;
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">MASTER SPACE</div>
                        <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 2px 0 0 0;">Customer Monitoring</h1>
                    </div>
                </div>

                <!-- CONTROLS -->
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; background: var(--bg-card); border: 1px solid var(--border);">
                    <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <input type="text" id="cust-search-input" value="${this.search}" placeholder="Search customer name or email..." style="padding: 6px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 260px;" />
                            <select id="cust-status-filter" style="padding: 6px 10px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                                <option value="all" ${this.statusFilter === 'all' ? 'selected' : ''}>All Statuses</option>
                                <option value="active" ${this.statusFilter === 'active' ? 'selected' : ''}>Active Only</option>
                                <option value="suspended" ${this.statusFilter === 'suspended' ? 'selected' : ''}>Suspended</option>
                            </select>
                        </div>
                    </div>

                    <div id="customers-table-slot">
                        <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading customers...</div>
                    </div>
                </div>
            </div>
        `;

        this.bindEvents();
        this.fetchData();
        return this.element;
    }

    bindEvents() {
        const searchInput = this.element.querySelector('#cust-search-input');
        if (searchInput) {
            searchInput.oninput = (e) => {
                this.search = e.target.value;
                this.page = 1;
                this.fetchData();
            };
        }

        const statusSelect = this.element.querySelector('#cust-status-filter');
        if (statusSelect) {
            statusSelect.onchange = (e) => {
                this.statusFilter = e.target.value;
                this.page = 1;
                this.fetchData();
            };
        }
    }

    async fetchData() {
        try {
            const query = new URLSearchParams({
                search: this.search,
                status: this.statusFilter,
                page: this.page,
                page_size: 20
            });
            this.data = await apiClient.get(`/api/master/customers?${query.toString()}`);
            this.renderTable();
        } catch (err) {
            console.error('[MASTER CUSTOMERS] Error fetching customers:', err);
        }
    }

    renderTable() {
        const slot = this.element.querySelector('#customers-table-slot');
        if (!slot || !this.data) return;

        const items = this.data.items || [];

        let rows = items.map(c => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 16px;">
                    <div style="font-weight: 700; color: var(--text-primary); font-size: 13.5px;">${this.escapeHtml(c.name)}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); font-family: monospace;">${this.escapeHtml(c.email)}</div>
                </td>
                <td style="padding: 12px 16px;">
                    <span class="badge ${c.platform_role === 'SUPER_ADMIN' ? 'badge-critical' : 'badge-secondary'}" style="font-size: 11px;">${this.escapeHtml(c.platform_role)}</span>
                </td>
                <td style="padding: 12px 16px;">
                    <span class="badge ${c.status === 'SUSPENDED' ? 'badge-warning' : 'badge-success'}" style="font-size: 11px;">${this.escapeHtml(c.status)}</span>
                </td>
                <td style="padding: 12px 16px; font-weight: 700; color: var(--primary);">${c.websites_count}</td>
                <td style="padding: 12px 16px;">${c.ai_requests} reqs (${(c.ai_tokens || 0).toLocaleString()} tok)</td>
                <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${c.created_at ? c.created_at.split('T')[0] : 'N/A'}</td>
                <td style="padding: 12px 16px; text-align: right;">
                    <a href="/master/customers/${c.id}" data-link class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 4px 10px;">
                        Customer 360 ↗
                    </a>
                </td>
            </tr>
        `).join('');

        slot.innerHTML = `
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <thead>
                        <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                            <th style="padding: 12px 16px;">Customer</th>
                            <th style="padding: 12px 16px;">Platform Role</th>
                            <th style="padding: 12px 16px;">Status</th>
                            <th style="padding: 12px 16px;">Websites</th>
                            <th style="padding: 12px 16px;">AI Usage</th>
                            <th style="padding: 12px 16px;">Joined</th>
                            <th style="padding: 12px 16px; text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>${rows.length > 0 ? rows : `<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--text-secondary);">No customers found.</td></tr>`}</tbody>
                </table>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
