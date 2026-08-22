import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Technical {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'technical-view';
        this.activeTab = 'audit'; // audit, history
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">15-Category Site Audit Workspace</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Deterministic rules and evidence-based SEO audit covering 15 technical categories.</p>
                </div>
                <div id="technical-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- TAB BAR -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <button class="btn ${this.activeTab === 'audit' ? 'btn-primary' : 'btn-secondary'}" id="tab-audit-btn" style="font-size: 13px;">
                    Site Audit Findings
                </button>
                <button class="btn ${this.activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}" id="tab-history-btn" style="font-size: 13px;">
                    Issue History & Comparison
                </button>
            </div>

            <div id="technical-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Evaluating 15 site audit categories...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('technical-content');
        const actionsContainer = document.getElementById('technical-actions');
        if (!container) return;

        document.getElementById('tab-audit-btn')?.addEventListener('click', () => {
            this.activeTab = 'audit';
            this.mounted();
        });

        document.getElementById('tab-history-btn')?.addEventListener('click', () => {
            this.activeTab = 'history';
            this.mounted();
        });

        try {
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create a project workspace.</div>`;
                return;
            }

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <a href="${API_BASE_URL}/api/projects/${projectId}/technical/report.pdf" target="_blank" class="btn btn-secondary btn-sm">Download PDF</a>
                    <a href="${API_BASE_URL}/api/projects/${projectId}/technical/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            if (this.activeTab === 'history') {
                const resHist = await fetch(`${API_BASE_URL}/api/projects/${projectId}/technical/issue-history`);
                const histData = await resHist.json();

                container.innerHTML = `
                    <div class="card" style="padding: 24px;">
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Snapshot Audit Comparison</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
                            ${histData.message || "Compare current crawl issues against previous completed snapshot."}
                        </p>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                            <div class="kpi-card">
                                <div class="kpi-label">RESOLVED ISSUES</div>
                                <div class="kpi-value" style="color: var(--success);">${histData.resolved_issues_count || 0}</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-label">NEW ISSUES</div>
                                <div class="kpi-value" style="color: var(--critical);">${histData.new_issues_count || 0}</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-label">CURRENT SNAPSHOT</div>
                                <div style="font-size: 13px; font-weight: 600; margin-top: 8px;">${histData.current_snapshot || "Active"}</div>
                            </div>
                            <div class="kpi-card">
                                <div class="kpi-label">PREVIOUS SNAPSHOT</div>
                                <div style="font-size: 13px; font-weight: 600; margin-top: 8px;">${histData.previous_snapshot || "None"}</div>
                            </div>
                        </div>
                    </div>
                `;
                return;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/technical?limit=200&offset=0`);
            if (!res.ok) throw new Error("API response error");
            const auditData = await res.json();

            const health = auditData.health_score || 100;
            const issues = auditData.issues || [];
            const summary = auditData.summary || {};
            const categories = auditData.category_breakdown || {};

            let catCardsHtml = Object.entries(categories).map(([catName, stats]) => {
                const isEvaluated = stats.evaluated !== false;
                const total = stats.critical + stats.error + stats.warning + stats.notice;

                let statusBadgeText = "Passed";
                let statusColor = "var(--success, #22c55e)";

                if (!isEvaluated) {
                    statusBadgeText = "Not Evaluated";
                    statusColor = "#94a3b8";
                } else if (total > 0 || stats.status === "Issues Found") {
                    statusBadgeText = `${total} issue${total === 1 ? '' : 's'}`;
                    statusColor = "var(--critical, #ef4444)";
                }

                return `
                    <div class="card" style="padding: 16px; font-size: 13px;">
                        <div style="display: flex; justify-content: space-between; font-weight: 600; margin-bottom: 8px;">
                            <span>${catName}</span>
                            <span style="color: ${statusColor}; font-size: 12px; font-weight: 600;">${statusBadgeText}</span>
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); display: flex; gap: 8px;">
                            ${isEvaluated ? `
                                <span>Crit: ${stats.critical + stats.error}</span>
                                <span>Warn: ${stats.warning}</span>
                                <span>Pass: ${stats.passed}</span>
                            ` : `
                                <span>${stats.reason || 'Data unavailable'}</span>
                            `}
                        </div>
                    </div>
                `;
            }).join('');


            let tableRows = issues.map(iss => {
                let badgeClass = 'badge-info';
                const sev = (iss.severity || '').toLowerCase();
                if (sev === 'critical') badgeClass = 'badge-critical';
                else if (sev === 'warning') badgeClass = 'badge-warning';

                return `
                    <tr>
                        <td style="padding: 12px 20px;"><span class="badge ${badgeClass}">${iss.severity}</span></td>
                        <td style="font-weight: 600;">${iss.category || 'Technical'}</td>
                        <td style="font-weight: 500; font-size: 13px;">${iss.title}</td>
                        <td style="font-size: 12px; color: var(--text-secondary); font-family: monospace;">${(iss.affected_urls || []).length} URLs</td>
                        <td style="font-size: 12px; color: var(--text-secondary);">${iss.recommendation}</td>
                    </tr>
                `;
            }).join('');

            container.innerHTML = `
                <!-- HEALTH SCORE HEADER -->
                <div class="card" style="padding: 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600;">Site Audit Health Score</div>
                        <div style="font-size: 36px; font-weight: 700; color: ${health >= 85 ? 'var(--success)' : (health >= 70 ? 'var(--warning)' : 'var(--critical)')}; font-family: var(--font-heading);">
                            ${health} <span style="font-size: 18px; color: var(--text-secondary);">/ 100</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Audited ${auditData.total_audited_pages || 0} crawled pages.</div>
                    </div>
                    <div style="display: flex; gap: 24px; font-size: 13px;">
                        <div><div style="color: var(--text-secondary);">Critical Errors</div><div style="font-size: 20px; font-weight: 700; color: var(--critical);">${summary.critical_errors || 0}</div></div>
                        <div><div style="color: var(--text-secondary);">Warnings</div><div style="font-size: 20px; font-weight: 700; color: var(--warning);">${summary.warnings || 0}</div></div>
                        <div><div style="color: var(--text-secondary);">Notices</div><div style="font-size: 20px; font-weight: 700;">${summary.notices || 0}</div></div>
                        <div><div style="color: var(--text-secondary);">Passed Checks</div><div style="font-size: 20px; font-weight: 700; color: var(--success);">${summary.passed_checks || 0}</div></div>
                    </div>
                </div>

                <!-- 15 AUDIT CATEGORIES GRID -->
                <h3 style="font-size: 15px; font-weight: 600; margin-bottom: 12px;">15 Audit Categories Breakdown</h3>
                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px;">
                    ${catCardsHtml}
                </div>

                <!-- FINDINGS TABLE -->
                <div class="card" style="padding: 0; overflow: hidden;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-size: 15px; font-weight: 600;">Audit Rule Findings (${issues.length})</h3>
                        <span style="font-size: 12px; color: var(--text-secondary);">Rule Engine Output</span>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Severity</th>
                                    <th style="padding: 12px;">Category</th>
                                    <th style="padding: 12px;">Rule Finding</th>
                                    <th style="padding: 12px;">Affected URLs</th>
                                    <th style="padding: 12px;">Action Recommendation</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows.length > 0 ? tableRows : `<tr><td colspan="5" style="padding: 24px; text-align: center; color: var(--text-secondary);">No site audit issues detected.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {

                renderFeatureErrorState(container, "Technical Audit Error", e.message || "Unable to load technical audit issues.", () => this.mounted());
            }
        }
    }
}
