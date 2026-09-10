import { apiClient } from '../../services/apiClient.js';

export class MasterCustomerDetail {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-customer-detail-view';
        this.customerId = null;
        this.data = null;
    }

    async render() {
        // Extract customerId from URL path e.g. /master/customers/test_customer
        const parts = window.location.pathname.split('/');
        this.customerId = parts[parts.length - 1];

        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    <a href="/master/customers" data-link style="color: var(--primary); font-size: 12px; font-weight: 700; text-decoration: none;">← Back to Customers</a>
                    <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 6px 0 0 0;">Customer 360</h1>
                </div>

                <div id="customer-detail-content">
                    <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading Customer 360 payload...</div>
                </div>
            </div>
        `;

        this.fetchDetail();
        return this.element;
    }

    async fetchDetail() {
        try {
            this.data = await apiClient.get(`/api/master/customers/${this.customerId}`);
            this.renderContent();
        } catch (err) {
            console.error('[MASTER CUSTOMER DETAIL] Error fetching detail:', err);
            const content = this.element.querySelector('#customer-detail-content');
            if (content) {
                content.innerHTML = `
                    <div class="card" style="padding: 32px; text-align: center; border-color: rgba(239, 68, 68, 0.3);">
                        <h3 style="color: #ef4444; margin-bottom: 8px;">Customer Not Found</h3>
                        <p style="color: var(--text-secondary); font-size: 13px;">Unable to find customer payload for ID: ${this.customerId}</p>
                    </div>
                `;
            }
        }
    }

    renderContent() {
        const content = this.element.querySelector('#customer-detail-content');
        if (!content || !this.data) return;

        const u = this.data.user || {};
        const ov = this.data.overview || {};
        const ai = this.data.ai_analytics || {};
        const websites = this.data.websites || [];
        const reports = this.data.reports || [];
        const integrations = this.data.integrations || [];
        const activity = this.data.activity || [];

        content.innerHTML = `
            <!-- CUSTOMER SUMMARY BANNER -->
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border); margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 20px; font-weight: 800; color: var(--text-primary);">${this.escapeHtml(u.name || u.email)}</div>
                        <div style="font-size: 12.5px; color: var(--text-secondary); font-family: monospace; margin-top: 3px;">Email: ${this.escapeHtml(u.email)} | ID: ${this.escapeHtml(u.id)}</div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span class="badge ${ov.platform_role === 'SUPER_ADMIN' ? 'badge-critical' : 'badge-secondary'}">${this.escapeHtml(ov.platform_role)}</span>
                        <span class="badge ${ov.status === 'SUSPENDED' ? 'badge-warning' : 'badge-success'}">${this.escapeHtml(ov.status)}</span>
                        <button id="btn-toggle-status" class="btn btn-secondary btn-sm" style="font-size: 11px;">
                            ${ov.status === 'SUSPENDED' ? 'Unsuspend Account' : 'Suspend Account'}
                        </button>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--border);">
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">Websites Owned</div>
                        <div style="font-size: 20px; font-weight: 800; color: var(--primary); margin-top: 2px;">${ov.website_count}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">AI Requests</div>
                        <div style="font-size: 20px; font-weight: 800; color: #a855f7; margin-top: 2px;">${ai.requests || 0}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">Total AI Tokens</div>
                        <div style="font-size: 20px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${(ai.total_tokens || 0).toLocaleString()}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); font-weight: 700; text-transform: uppercase;">Estimated AI Cost</div>
                        <div style="font-size: 20px; font-weight: 800; color: #f59e0b; margin-top: 2px;">$${ai.estimated_cost || 0}</div>
                    </div>
                </div>
            </div>

            <!-- CUSTOMER AI CONTROL & WALLET PANEL -->
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border); margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                    <div>
                        <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0;">Customer AI Control Panel</h3>
                        <p style="font-size: 12px; color: var(--text-secondary); margin: 2px 0 0 0;">Manage account kill switch, daily/monthly credit limits, and balance allocations</p>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button id="btn-customer-add-credits" class="btn btn-primary btn-sm">Add Credits</button>
                        <button id="btn-customer-toggle-ai" class="btn btn-${ov.ai_enabled !== false ? 'danger' : 'success'} btn-sm">
                            ${ov.ai_enabled !== false ? 'Disable AI for Customer' : 'Enable AI for Customer'}
                        </button>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
                    <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: var(--text-secondary);">AI Status</div>
                        <div style="font-size: 16px; font-weight: 800; color: ${ov.ai_enabled !== false ? '#10b981' : '#ef4444'}; margin-top: 2px;">
                            ${ov.ai_enabled !== false ? 'ENABLED (Active)' : 'DISABLED (Kill Switch)'}
                        </div>
                    </div>
                    <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: var(--text-secondary);">Allocated Credits</div>
                        <div style="font-size: 16px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${(ov.allocated_credits || 50000).toLocaleString()}</div>
                    </div>
                    <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: var(--text-secondary);">Remaining Credits</div>
                        <div style="font-size: 16px; font-weight: 800; color: #10b981; margin-top: 2px;">${(ov.remaining_credits || 50000).toLocaleString()}</div>
                    </div>
                    <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: var(--text-secondary);">Daily Limit</div>
                        <div style="font-size: 16px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${(ov.daily_limit || 5000).toLocaleString()} / day</div>
                    </div>
                    <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px;">
                        <div style="font-size: 11px; color: var(--text-secondary);">Monthly Limit</div>
                        <div style="font-size: 16px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${(ov.monthly_limit || 50000).toLocaleString()} / mo</div>
                    </div>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px;">
                <!-- WEBSITES -->
                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 12px 0; color: var(--text-primary);">Customer Websites</h3>
                    ${websites.length > 0 ? websites.map(w => `
                        <div style="padding: 10px 12px; background: var(--bg-subtle); border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: 700; font-size: 13px; color: var(--text-primary);">${this.escapeHtml(w.name)}</div>
                                <div style="font-size: 11.5px; font-family: monospace; color: var(--primary);">${this.escapeHtml(w.url)}</div>
                            </div>
                            <a href="/master/websites/${w.id}" data-link class="btn btn-secondary btn-sm" style="font-size: 10.5px;">Website 360 ↗</a>
                        </div>
                    `).join('') : `<div style="font-size: 12px; color: var(--text-secondary);">No websites created yet.</div>`}
                </div>

                <!-- INTEGRATIONS -->
                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 12px 0; color: var(--text-primary);">Connected Data Providers</h3>
                    ${integrations.length > 0 ? integrations.map(i => `
                        <div style="padding: 10px 12px; background: var(--bg-subtle); border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="font-weight: 700; font-size: 13px; color: var(--text-primary);">${this.escapeHtml(i.provider)}</div>
                                <div style="font-size: 11px; color: var(--text-secondary);">${this.escapeHtml(i.account_name)}</div>
                            </div>
                            <span class="badge badge-success" style="font-size: 10.5px;">${this.escapeHtml(i.status)}</span>
                        </div>
                    `).join('') : `<div style="font-size: 12px; color: var(--text-secondary);">No active OAuth integrations.</div>`}
                </div>
            </div>
        `;

        const btnToggleAi = content.querySelector('#btn-customer-toggle-ai');
        if (btnToggleAi) {
            btnToggleAi.onclick = async () => {
                const targetEnabled = ov.ai_enabled === false;
                if (confirm(`Confirm: ${targetEnabled ? 'Enable' : 'Disable'} AI capabilities for customer ${u.email}?`)) {
                    await apiClient.patch(`/api/master/customers/${u.id}/ai-settings`, {
                        is_enabled: targetEnabled,
                        reason: 'Master admin toggle from Customer 360'
                    });
                    this.fetchDetail();
                }
            };
        }

        const btnAddCredits = content.querySelector('#btn-customer-add-credits');
        if (btnAddCredits) {
            btnAddCredits.onclick = async () => {
                const amountStr = prompt(`Enter credits to allocate for ${u.email}:`, '50000');
                if (amountStr) {
                    const amount = parseInt(amountStr);
                    const reason = prompt(`Enter reason for credit allocation:`, 'Admin top-up');
                    if (amount && reason) {
                        await apiClient.post(`/api/master/customers/${u.id}/credits`, {
                            amount,
                            transaction_type: 'allocation',
                            reason
                        });
                        alert("Credits allocated successfully!");
                        this.fetchDetail();
                    }
                }
            };
        }

        const btnStatus = content.querySelector('#btn-toggle-status');
        if (btnStatus) {
            btnStatus.onclick = async () => {
                const targetStatus = ov.status === 'SUSPENDED' ? 'ACTIVE' : 'SUSPENDED';
                if (confirm(`Are you sure you want to change customer status to ${targetStatus}?`)) {
                    await apiClient.post(`/api/master/customers/${u.id}/status`, { status: targetStatus, reason: 'Master admin toggle' });
                    this.fetchDetail();
                }
            };
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
