import { apiClient } from '../../services/apiClient.js';

export class MasterActivity {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'master-activity-view';
        this.data = null;
    }

    async render() {
        this.element.innerHTML = `
            <div style="padding: 24px; max-width: 1400px; margin: 0 auto;">
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 11px; font-weight: 700; color: #a855f7; text-transform: uppercase;">MASTER SPACE</div>
                    <h1 style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin: 2px 0 0 0;">Global Activity Timeline</h1>
                </div>

                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <div id="activity-stream-slot">
                        <div style="padding: 32px; text-align: center; color: var(--text-secondary);">Loading global activity stream...</div>
                    </div>
                </div>
            </div>
        `;

        this.fetchData();
        return this.element;
    }

    async fetchData() {
        try {
            this.data = await apiClient.get('/api/master/activity');
            this.renderContent();
        } catch (err) {
            console.error('[MASTER ACTIVITY] Error loading activity:', err);
        }
    }

    renderContent() {
        const slot = this.element.querySelector('#activity-stream-slot');
        if (!slot || !this.data) return;

        const items = this.data.items || [];
        slot.innerHTML = items.length > 0 ? items.map(item => `
            <div style="padding: 12px 16px; border-left: 3px solid ${item.severity === 'critical' ? '#f87171' : (item.severity === 'warning' ? '#f59e0b' : 'var(--primary)')}; background: var(--bg-subtle); border-radius: 0 8px 8px 0; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: var(--text-primary); font-size: 13.5px;">${this.escapeHtml(item.title)}</strong>
                    <span style="font-size: 11.5px; font-family: monospace; color: var(--text-secondary);">${item.created_at ? item.created_at.replace('T', ' ').split('.')[0] : ''}</span>
                </div>
                ${item.description ? `<div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${this.escapeHtml(item.description)}</div>` : ''}
            </div>
        `).join('') : `<div style="font-size: 13px; color: var(--text-secondary);">No platform events recorded yet.</div>`;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
