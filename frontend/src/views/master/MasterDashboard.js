import { apiClient } from '../../services/apiClient.js';
import { authStore } from '../../core/authStore.js';

export class MasterDashboard {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-dashboard-view';
        this.rangeType = '30d';
        this.metrics = null;
        this.isLoading = true;
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <!-- MASTER HEADER -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.3); font-weight: 700; font-size: 11px; padding: 3px 8px; border-radius: 6px;">PLATFORM MASTER SPACE</span>
                            <span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; font-size: 11px; font-weight: 600;">Role: ${authStore.user?.platform_role || 'SUPER_ADMIN'}</span>
                        </div>
                        <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 6px 0 0 0;">Platform Observability & Monitoring</h1>
                    </div>

                    <!-- DATE RANGE FILTER -->
                    <div style="display: flex; align-items: center; gap: 8px; background: var(--bg-card); padding: 6px 12px; border-radius: 10px; border: 1px solid var(--border);">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Period:</span>
                        <select id="master-date-range" style="background: none; border: none; font-size: 13px; font-weight: 700; color: var(--primary); cursor: pointer; outline: none;">
                            <option value="today" ${this.rangeType === 'today' ? 'selected' : ''}>Today</option>
                            <option value="7d" ${this.rangeType === '7d' ? 'selected' : ''}>Last 7 Days</option>
                            <option value="30d" ${this.rangeType === '30d' ? 'selected' : ''}>Last 30 Days</option>
                            <option value="this_month" ${this.rangeType === 'this_month' ? 'selected' : ''}>This Month</option>
                            <option value="last_month" ${this.rangeType === 'last_month' ? 'selected' : ''}>Previous Month</option>
                        </select>
                    </div>
                </div>

                <div id="master-dashboard-content">
                    <div style="padding: 40px; text-align: center; color: var(--text-secondary);">Loading platform observability metrics...</div>
                </div>
            </div>
        `;

        this.bindEvents();
        this.fetchMetrics();
        return this.element;
    }

    bindEvents() {
        const select = this.element.querySelector('#master-date-range');
        if (select) {
            select.onchange = (e) => {
                this.rangeType = e.target.value;
                this.fetchMetrics();
            };
        }
    }

    async fetchMetrics() {
        try {
            this.metrics = await apiClient.get(`/api/master/dashboard?range_type=${this.rangeType}`);
            this.renderContent();
        } catch (err) {
            console.error('[MASTER DASHBOARD] Error loading metrics:', err);
            const content = this.element.querySelector('#master-dashboard-content');
            if (content) {
                content.innerHTML = `
                    <div class="card" style="padding: 32px; text-align: center; border-color: rgba(239, 68, 68, 0.3); background: rgba(239, 68, 68, 0.05);">
                        <h3 style="color: #ef4444; margin-bottom: 8px;">Failed to Load Master Metrics</h3>
                        <p style="color: var(--text-secondary); font-size: 13px;">${err.message || 'Authorization error or server unavailable.'}</p>
                    </div>
                `;
            }
        }
    }

    renderContent() {
        const content = this.element.querySelector('#master-dashboard-content');
        if (!content || !this.metrics) return;

        const m = this.metrics;

        content.innerHTML = `
            <!-- TOP KPI GRID -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px;">
                <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Customers</div>
                    <div style="font-size: 28px; font-weight: 800; color: var(--primary); margin-top: 4px;">${m.total_customers}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Active: ${m.active_customers} | Suspended: ${m.suspended_customers}</div>
                </div>

                <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Websites</div>
                    <div style="font-size: 28px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${m.total_websites}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Active last 30d: ${m.active_websites}</div>
                </div>

                <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Crawls Today</div>
                    <div style="font-size: 28px; font-weight: 800; color: #10b981; margin-top: 4px;">${m.crawls_today}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Website audits executed</div>
                </div>

                <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">AI Requests Today</div>
                    <div style="font-size: 28px; font-weight: 800; color: #a855f7; margin-top: 4px;">${m.ai_requests_today}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Tokens: ${m.ai_tokens_today.toLocaleString()}</div>
                </div>

                <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">AI Requests (${m.range_type})</div>
                    <div style="font-size: 28px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${m.ai_requests_this_month}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Tokens: ${m.ai_tokens_this_month.toLocaleString()}</div>
                </div>

                <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Estimated AI Cost</div>
                    <div style="font-size: 28px; font-weight: 800; color: #f59e0b; margin-top: 4px;">$${m.estimated_ai_cost}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Base rate calculation</div>
                </div>
            </div>

            <!-- SECOND ROW: QUICK LINKS & HEALTH SUMMARY -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 14px 0; color: var(--text-primary);">Master Navigation Quick Links</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <a href="/master/customers" data-link style="padding: 12px; border-radius: 8px; background: var(--bg-subtle); text-decoration: none; color: var(--text-primary); font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                            👥 Customers (${m.total_customers})
                        </a>
                        <a href="/master/websites" data-link style="padding: 12px; border-radius: 8px; background: var(--bg-subtle); text-decoration: none; color: var(--text-primary); font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                            🌐 Websites (${m.total_websites})
                        </a>
                        <a href="/master/ai-analytics" data-link style="padding: 12px; border-radius: 8px; background: var(--bg-subtle); text-decoration: none; color: var(--text-primary); font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                            🤖 AI Analytics
                        </a>
                        <a href="/master/providers" data-link style="padding: 12px; border-radius: 8px; background: var(--bg-subtle); text-decoration: none; color: var(--text-primary); font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                            ⚡ Providers
                        </a>
                        <a href="/master/activity" data-link style="padding: 12px; border-radius: 8px; background: var(--bg-subtle); text-decoration: none; color: var(--text-primary); font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                            📜 Global Activity
                        </a>
                        <a href="/master/system-health" data-link style="padding: 12px; border-radius: 8px; background: var(--bg-subtle); text-decoration: none; color: var(--text-primary); font-weight: 600; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                            🩺 System Health
                        </a>
                    </div>
                </div>

                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 14px 0; color: var(--text-primary);">System Health Summary</h3>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px;">
                            <span>Failed AI Requests</span>
                            <span class="badge ${m.failed_ai_requests > 0 ? 'badge-critical' : 'badge-success'}">${m.failed_ai_requests}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px;">
                            <span>System Errors</span>
                            <span class="badge ${m.system_errors > 0 ? 'badge-warning' : 'badge-success'}">${m.system_errors}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px;">
                            <span>Active Platform Users</span>
                            <span class="badge badge-info">${m.active_users}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}
