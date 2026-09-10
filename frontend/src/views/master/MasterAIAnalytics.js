import { apiClient } from '../../services/apiClient.js';

export class MasterAIAnalytics {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-ai-analytics-view';
        this.rangeType = '30d';
        this.data = null;
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">MASTER SPACE</div>
                        <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 2px 0 0 0;">Platform AI Analytics</h1>
                    </div>
                    <select id="ai-date-range" style="padding: 6px 12px; font-size: 13px; font-weight: 700; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                        <option value="today" ${this.rangeType === 'today' ? 'selected' : ''}>Today</option>
                        <option value="7d" ${this.rangeType === '7d' ? 'selected' : ''}>Last 7 Days</option>
                        <option value="30d" ${this.rangeType === '30d' ? 'selected' : ''}>Last 30 Days</option>
                        <option value="this_month" ${this.rangeType === 'this_month' ? 'selected' : ''}>This Month</option>
                    </select>
                </div>

                <div id="ai-analytics-content">
                    <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading platform AI analytics...</div>
                </div>
            </div>
        `;

        this.bindEvents();
        this.fetchData();
        return this.element;
    }

    bindEvents() {
        const select = this.element.querySelector('#ai-date-range');
        if (select) {
            select.onchange = (e) => {
                this.rangeType = e.target.value;
                this.fetchData();
            };
        }
    }

    async fetchData() {
        try {
            this.data = await apiClient.get(`/api/master/ai-analytics?range_type=${this.rangeType}`);
            this.renderContent();
        } catch (err) {
            console.error('[MASTER AI ANALYTICS] Error loading analytics:', err);
        }
    }

    renderContent() {
        const content = this.element.querySelector('#ai-analytics-content');
        if (!content || !this.data) return;

        const s = this.data.summary || {};
        const byCustomer = this.data.by_customer || [];
        const byWebsite = this.data.by_website || [];
        const byProvider = this.data.by_provider || [];
        const byTask = this.data.by_task || [];

        content.innerHTML = `
            <!-- SUMMARY KPI STRIP -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px;">
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Requests</div>
                    <div style="font-size: 24px; font-weight: 800; color: #a855f7; margin-top: 4px;">${s.requests || 0}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Successful: ${s.successful || 0} | Failed: ${s.failed || 0}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Input Tokens</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${(s.input_tokens || 0).toLocaleString()}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Output Tokens</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${(s.output_tokens || 0).toLocaleString()}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Estimated Cost</div>
                    <div style="font-size: 24px; font-weight: 800; color: #f59e0b; margin-top: 4px;">$${s.estimated_cost || 0}</div>
                </div>
            </div>

            <!-- BREAKDOWNS -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px;">
                <!-- BY CUSTOMER -->
                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 14px 0; color: var(--text-primary);">Usage by Customer</h3>
                    ${byCustomer.length > 0 ? byCustomer.map(c => `
                        <div style="padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; font-size: 12.5px;">
                            <div>
                                <strong style="color: var(--text-primary);">${this.escapeHtml(c.customer_name)}</strong>
                                <div style="font-size: 11px; color: var(--text-secondary); font-family: monospace;">${this.escapeHtml(c.email)}</div>
                            </div>
                            <div style="text-align: right;">
                                <strong style="color: #a855f7;">${c.requests} reqs</strong>
                                <div style="font-size: 11px; color: #f59e0b;">$${c.estimated_cost}</div>
                            </div>
                        </div>
                    `).join('') : `<div style="font-size: 12px; color: var(--text-secondary);">No customer AI logs in selected period.</div>`}
                </div>

                <!-- BY PROVIDER & TASK -->
                <div style="display: flex; flex-direction: column; gap: 20px;">
                    <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 14px 0; color: var(--text-primary);">Usage by Provider</h3>
                        ${byProvider.map(p => `
                            <div style="padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; font-size: 12.5px;">
                                <span style="font-weight: 600;">${this.escapeHtml(p.provider)}</span>
                                <span>${p.requests} reqs (${p.tokens.toLocaleString()} tok)</span>
                            </div>
                        `).join('')}
                    </div>

                    <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 14px 0; color: var(--text-primary);">Usage by Task Type</h3>
                        ${byTask.map(t => `
                            <div style="padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; margin-bottom: 6px; display: flex; justify-content: space-between; font-size: 12.5px;">
                                <span style="font-weight: 600; font-family: monospace;">${this.escapeHtml(t.task)}</span>
                                <span>${t.requests} reqs</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
