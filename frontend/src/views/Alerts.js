import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { Pagination } from '../components/Pagination.js';
import { AuditEvidenceModal } from '../components/AuditEvidenceModal.js';

export class Alerts {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'alerts-view';
        this.alertsData = null;
        this.isLoading = true;
        this.error = null;
        this.alertsPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 items per page
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary);">Website Alerts & Feed</h1>
                <p style="color: var(--text-secondary); margin-top: 4px; font-size: 13.5px;">
                    Real-time alert feed of technical problems, scan failures, and threshold notifications detected on your website.
                </p>
            </div>
            <div id="alerts-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading website alerts...
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
                        Please select a website project workspace to view alerts.
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
                renderBackendOfflineState(container, "We couldn't load your website alerts right now. Please try again.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Alerts Load Error", "We encountered an issue reading active project alerts.", () => this.mounted());
            }
        }
    }

    renderAlertsContent(container) {
        const data = this.alertsData;
        if (!data || !data.has_alerts || !data.alerts || data.alerts.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 24px; text-align: center; background: var(--bg-card); border-radius: 14px;">
                    <div style="font-size: 32px; margin-bottom: 8px; color: var(--success);">✓</div>
                    <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">No Active Alerts Detected</h3>
                    <p style="color: var(--text-secondary); font-size: 13.5px; max-width: 500px; margin: 0 auto 20px; line-height: 1.5;">
                        Your latest website scan identified no critical threshold alerts or broken page issues.
                    </p>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                </div>
            `;
            return;
        }

        const paginated = Pagination.paginateArray(data.alerts, this.alertsPage, this.pageSize);
        this.alertsPage = paginated.currentPage;

        const alertCards = paginated.items.map((alert, idx) => {
            const globalIdx = (paginated.currentPage - 1) * paginated.pageSize + idx;
            const isCrit = (alert.type || alert.severity || '').toLowerCase() === 'critical' || (alert.type || alert.severity || '').toLowerCase() === 'error';
            const borderColor = isCrit ? '#ef4444' : '#f59e0b';
            const badgeBg = isCrit ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)';
            const badgeColor = isCrit ? '#ef4444' : '#f59e0b';
            const displaySeverity = (alert.severity || alert.type || 'Notice').toUpperCase();

            return `
                <div class="card" style="padding: 20px; border-left: 4px solid ${borderColor}; margin-bottom: 14px; border-radius: 12px; background: var(--bg-card);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <span style="font-weight: 700; font-size: 15px; color: var(--text-primary); margin-right: 8px;">${this.escapeHtml(alert.title)}</span>
                            <span style="font-size: 10px; font-weight: 800; background: ${badgeBg}; color: ${badgeColor}; padding: 2px 8px; border-radius: 12px;">
                                ${displaySeverity}
                            </span>
                        </div>
                        <span style="font-size: 11px; color: var(--text-tertiary);">
                            Category: ${this.escapeHtml(alert.category || 'SEO Audit')} • ${alert.timestamp ? new Date(alert.timestamp).toLocaleDateString() : 'Recent Scan'}
                        </span>
                    </div>

                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 12px; line-height: 1.5;">
                        ${this.escapeHtml(alert.message || alert.description || '')}
                    </p>

                    <div style="display: flex; justify-content: space-between; align-items: center; pt-10; border-top: 1px solid var(--border); flex-wrap: wrap; gap: 10px;">
                        <div style="font-size: 12px; color: var(--text-secondary);">
                            <strong>Recommendation:</strong> ${this.escapeHtml(alert.recommendation || 'Inspect website pages.')}
                        </div>
                        <button class="btn btn-secondary btn-sm btn-alert-evidence" data-idx="${globalIdx}" style="font-size: 12px; font-weight: 600;">
                            View Evidence (${alert.affected_count || 1} affected)
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        window.refreshAlertsFeed = async () => {
            await this.mounted();
        };

        container.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
                <div style="font-size: 13.5px; color: var(--text-secondary);">
                    Found <strong style="color: var(--text-primary);">${data.alerts.length}</strong> active website alerts.
                </div>
                <button type="button" class="btn btn-secondary btn-sm" onclick="window.refreshAlertsFeed()">Refresh Feed</button>
            </div>
            ${alertCards}
            <div id="alerts-pagination-slot" style="background: var(--bg-card); border-radius: 12px; margin-top: 12px; border: 1px solid var(--border);"></div>
        `;

        const pageSlot = container.querySelector('#alerts-pagination-slot');
        if (pageSlot && data.alerts.length > 0) {
            const pag = new Pagination({
                totalItems: data.alerts.length,
                currentPage: this.alertsPage,
                pageSize: this.pageSize,
                onPageChange: (newPage) => {
                    this.alertsPage = newPage;
                    this.renderAlertsContent(container);
                }
            });
            pageSlot.appendChild(pag.render());
        }

        container.querySelectorAll('.btn-alert-evidence').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const globalIdx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                const item = data.alerts[globalIdx];
                if (item) {
                    AuditEvidenceModal.open({
                        title: item.title,
                        ruleId: item.id || 'ALERT_ITEM',
                        category: item.category,
                        severity: item.severity || item.type,
                        description: item.description || item.message,
                        recommendation: item.recommendation,
                        affectedUrls: item.affected_urls || [],
                        evidenceText: item.message || item.description,
                        provenance: 'Website Scan',
                        scanDate: item.timestamp ? new Date(item.timestamp).toLocaleDateString() : 'Latest Scan'
                    });
                }
            });
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
