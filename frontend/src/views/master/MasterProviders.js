import { apiClient } from '../../services/apiClient.js';

export class MasterProviders {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-providers-view';
        this.providers = [];
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">MASTER SPACE</div>
                    <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 2px 0 0 0;">Provider Monitoring</h1>
                </div>

                <div id="providers-content">
                    <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading provider monitoring summary...</div>
                </div>
            </div>
        `;

        this.fetchData();
        return this.element;
    }

    async fetchData() {
        try {
            this.providers = await apiClient.get('/api/master/providers');
            this.renderContent();
        } catch (err) {
            console.error('[MASTER PROVIDERS] Error loading providers:', err);
        }
    }

    renderContent() {
        const content = this.element.querySelector('#providers-content');
        if (!content || !this.providers) return;

        content.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
                ${this.providers.map(p => `
                    <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 16px; font-weight: 800; margin: 0; color: var(--text-primary);">${this.escapeHtml(p.name)}</h3>
                                ${p.is_primary ? `<span class="badge badge-info" style="font-size: 10px; margin-top: 4px;">Primary Provider</span>` : ''}
                            </div>
                            <span class="badge ${p.status === 'Healthy' ? 'badge-success' : (p.status === 'Warning' ? 'badge-warning' : 'badge-critical')}">${this.escapeHtml(p.status)}</span>
                        </div>

                        <div style="display: flex; flex-direction: column; gap: 8px; font-size: 12.5px; border-top: 1px solid var(--border); padding-top: 12px;">
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Total Requests:</span>
                                <strong>${p.requests}</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Successful:</span>
                                <span style="color: #10b981; font-weight: 700;">${p.successful}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Failed:</span>
                                <span style="color: #f87171; font-weight: 700;">${p.failed}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Total Tokens:</span>
                                <strong>${(p.tokens || 0).toLocaleString()}</strong>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-secondary);">Estimated Cost:</span>
                                <strong style="color: #f59e0b;">$${p.estimated_cost}</strong>
                            </div>
                        </div>

                        <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end;">
                            <button class="btn btn-secondary btn-sm btn-test-health" data-key="${p.key}" style="font-size: 11px;">Test Connection ↗</button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        content.querySelectorAll('.btn-test-health').forEach(btn => {
            btn.onclick = async () => {
                const key = btn.getAttribute('data-key');
                try {
                    const health = await apiClient.get(`/api/master/providers/${key}/health`);
                    alert(`[HEALTH CHECK - ${health.provider}]\nStatus: ${health.status}\nMessage: ${health.message}`);
                } catch (e) {
                    alert(`Failed to execute health check for ${key}`);
                }
            };
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
