import { apiClient } from '../../services/apiClient.js';

export class MasterSystemHealth {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-system-health-view';
        this.data = null;
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">MASTER SPACE</div>
                    <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 2px 0 0 0;">System Health & Infrastructure</h1>
                </div>

                <div id="system-health-content">
                    <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Checking platform system health...</div>
                </div>
            </div>
        `;

        this.fetchData();
        return this.element;
    }

    async fetchData() {
        try {
            this.data = await apiClient.get('/api/master/system-health');
            this.renderContent();
        } catch (err) {
            console.error('[MASTER SYSTEM HEALTH] Error loading health:', err);
        }
    }

    renderContent() {
        const content = this.element.querySelector('#system-health-content');
        if (!content || !this.data) return;

        const services = this.data.services || {};
        const errors = this.data.recent_errors || [];

        content.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 28px;">
                ${Object.entries(services).map(([key, val]) => `
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; font-size: 14px; text-transform: uppercase; color: var(--text-primary);">${key}</span>
                            <span class="badge ${val.status === 'Healthy' ? 'badge-success' : (val.status === 'Warning' ? 'badge-warning' : 'badge-critical')}">${val.status}</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">${this.escapeHtml(val.message)}</div>
                    </div>
                `).join('')}
            </div>

            <!-- RECENT ERRORS -->
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 14px 0; color: var(--text-primary);">Recent System Error Logs</h3>
                ${errors.length > 0 ? errors.map(e => `
                    <div style="padding: 10px 14px; background: rgba(239, 68, 68, 0.08); border-left: 3px solid #f87171; border-radius: 0 8px 8px 0; margin-bottom: 8px; font-size: 12.5px;">
                        <div style="display: flex; justify-content: space-between;">
                            <strong style="color: #f87171;">${this.escapeHtml(e.type)}</strong>
                            <span style="font-family: monospace; font-size: 11px; color: var(--text-secondary);">${e.timestamp ? e.timestamp.replace('T', ' ').split('.')[0] : ''}</span>
                        </div>
                        <div style="color: var(--text-primary); margin-top: 4px;">${this.escapeHtml(e.message)}</div>
                    </div>
                `).join('') : `<div style="font-size: 12.5px; color: var(--text-secondary);">No recent system error logs recorded.</div>`}
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
