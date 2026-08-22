import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { getApiBaseUrl } from '../config/api.js';


export class Alerts {
    constructor() {
        this.alertsData = null;
        this.isLoading = true;
        this.error = null;
    }

    render() {
        const element = document.createElement('div');
        element.className = 'alerts-view';

        if (!projectId) {
            element.innerHTML = `
                <div class="header" style="margin-bottom: 24px;">
                    <h1 style="font-size: 24px; font-weight: 600;">SEO Alerts & Feed</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Real-time feed of critical technical issues, crawl failures, and threshold alerts.</p>
                </div>
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Please select or create a project workspace to view SEO alerts.
                </div>
            `;
            return element;
        }

        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">SEO Alerts & Feed</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Real-time feed of critical technical issues, crawl failures, and threshold alerts.</p>
            </div>

            <div id="alerts-content">
                ${this.isLoading ? `
                    <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                        Loading real-time project alerts...
                    </div>
                ` : this.error ? `
                    <div class="card" style="padding: 24px; background: rgba(239, 68, 68, 0.05); color: #ef4444;">
                        <strong>Error loading alerts:</strong> ${this.error}
                    </div>
                ` : this.renderAlertsHTML()}
            </div>
        `;

        if (this.isLoading && projectId) {

            this.fetchAlerts(projectId);
        }

        return element;
    }

    renderAlertsHTML() {
        const data = this.alertsData;
        if (!data || !data.has_alerts || !data.alerts || data.alerts.length === 0) {
            return `
                <div style="max-width: 900px; display: flex; flex-direction: column; gap: 16px;">
                    <div class="card" style="padding: 32px; text-align: center;">
                        <div style="width: 48px; height: 48px; border-radius: 50%; background: rgba(34, 197, 94, 0.1); color: #22c55e; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 12px;">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                        </div>
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">No Active Alerts</h3>
                        <p style="color: var(--text-secondary); font-size: 14px; max-width: 440px; margin: 0 auto;">No unhandled critical issues or warnings detected for ${data?.domain || 'this project'}.</p>
                    </div>
                </div>
            `;
        }

        const summary = data.summary || {};

        return `
            <div style="max-width: 900px; display: flex; flex-direction: column; gap: 20px;">
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
                    <div class="card" style="padding: 16px; border-left: 4px solid #ef4444;">
                        <div style="font-size: 22px; font-weight: 700; color: #ef4444;">${summary.critical || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Critical Errors</div>
                    </div>
                    <div class="card" style="padding: 16px; border-left: 4px solid #eab308;">
                        <div style="font-size: 22px; font-weight: 700; color: #eab308;">${summary.warning || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Warnings</div>
                    </div>
                    <div class="card" style="padding: 16px; border-left: 4px solid #3b82f6;">
                        <div style="font-size: 22px; font-weight: 700; color: #3b82f6;">${summary.notice || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Notices</div>
                    </div>
                </div>

                <div style="display: flex; flex-direction: column; gap: 12px;">
                    ${data.alerts.map(a => {
                        const isCrit = a.severity === 'Critical' || a.severity === 'Error';
                        const isWarn = a.severity === 'Warning';
                        const color = isCrit ? '#ef4444' : (isWarn ? '#eab308' : '#3b82f6');
                        const bg = isCrit ? 'rgba(239, 68, 68, 0.05)' : (isWarn ? 'rgba(234, 179, 8, 0.05)' : 'rgba(59, 130, 246, 0.05)');

                        return `
                            <div class="card" style="padding: 20px; border-left: 4px solid ${color};">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                    <div style="display: flex; align-items: center; gap: 10px;">
                                        <span class="badge" style="background: ${bg}; color: ${color}; font-weight: 600; font-size: 11px; padding: 4px 8px; border-radius: 4px; text-transform: uppercase;">
                                            ${a.severity}
                                        </span>
                                        <h3 style="font-size: 15px; font-weight: 600; margin: 0;">${a.title}</h3>
                                    </div>
                                    ${a.affected_count > 0 ? `<span style="font-size: 12px; color: var(--text-secondary); background: var(--bg-tertiary, #f8fafc); padding: 4px 8px; border-radius: 12px;">${a.affected_count} URLs affected</span>` : ''}
                                </div>
                                <p style="color: var(--text-secondary); font-size: 13px; line-height: 1.5; margin-bottom: 12px;">${a.description}</p>
                                ${a.recommendation ? `
                                    <div style="font-size: 12px; background: var(--bg-tertiary, #f8fafc); padding: 10px; border-radius: 6px; color: var(--text-primary);">
                                        <strong>Recommendation:</strong> ${a.recommendation}
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    async fetchAlerts(projectId) {
        try {
            const data = await apiClient.get(`/api/projects/${projectId}/alerts`);
            this.alertsData = data;
        } catch (err) {
            this.error = err.message || 'Failed to load project alerts.';
        } finally {
            this.isLoading = false;
            this.reRender();
        }
    }


    reRender() {
        const root = document.getElementById('main-content');
        if (root) {
            root.innerHTML = '';
            root.appendChild(this.render());
        }
    }
}
