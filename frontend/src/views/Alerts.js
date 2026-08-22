import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';

export class Alerts {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'alerts-view';
        this.alertsData = null;
        this.isLoading = true;
        this.error = null;
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 700;">SEO Alerts & Feed</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Real-time feed of critical technical issues, crawl failures, and threshold alerts.</p>
            </div>
            <div id="alerts-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading real-time project alerts...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = this.element.querySelector('#alerts-content');
        if (!container) return;

        try {
            await projectStore.ensureInitialized();
            const projectId = projectStore.getSelectedProjectId();

            if (!projectId) {
                container.innerHTML = `
                    <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                        Please select or create a project workspace to view SEO alerts.
                    </div>
                `;
                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/alerts`);
            this.alertsData = data;
            this.isLoading = false;
            this.renderAlertsContent(container);
        } catch (e) {
            this.isLoading = false;
            if (e.isNetworkError || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Alerts Load Error", e.message || "Failed to load project alerts.", () => this.mounted());
            }
        }
    }

    renderAlertsContent(container) {
        const data = this.alertsData;
        if (!data || !data.has_alerts || !data.alerts || data.alerts.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 32px; text-align: center; background: var(--bg-card);">
                    <div style="font-size: 24px; margin-bottom: 8px; color: var(--success);">✓</div>
                    <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">No Active Alerts Detected</h3>
                    <p style="color: var(--text-secondary); font-size: 13px;">No critical technical threshold alerts detected in the latest audit snapshot for this project.</p>
                </div>
            `;
            return;
        }


        const alertCards = data.alerts.map(alert => {
            const isCrit = alert.type === 'critical' || alert.type === 'error';
            const borderColor = isCrit ? '#ef4444' : '#f59e0b';
            const badgeBg = isCrit ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)';
            const badgeColor = isCrit ? '#ef4444' : '#f59e0b';

            return `
                <div class="card" style="padding: 18px 20px; border-left: 4px solid ${borderColor}; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 700; font-size: 14px; color: var(--text-primary);">${alert.title}</span>
                        <span style="font-size: 10px; font-weight: 700; background: ${badgeBg}; color: ${badgeColor}; padding: 2px 8px; border-radius: 12px; text-transform: uppercase;">
                            ${alert.type}
                        </span>
                    </div>
                    <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">${alert.message}</p>
                    <div style="font-size: 11px; color: var(--text-tertiary);">
                        Category: ${alert.category} • Detected: ${alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'Recent'}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <div style="font-size: 13px; color: var(--text-secondary);">
                    Found <strong style="color: var(--text-primary);">${data.alerts.length}</strong> active project alerts.
                </div>
                <button class="btn btn-secondary btn-sm" onclick="window.location.reload()">Refresh Feed</button>
            </div>
            ${alertCards}
        `;
    }
}
