import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Technical {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'technical-view';
        this.activeTab = 'audit'; // audit, history
        this.selectedCategoryFilter = 'all';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600; color: var(--text-primary);">15-Category Technical SEO Audit</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px; font-size: 13px;">Individual website technical audit, category evidence drill-down, and snapshot comparisons.</p>
                </div>
                <div id="technical-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- TAB BAR -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <button class="btn ${this.activeTab === 'audit' ? 'btn-primary' : 'btn-secondary'}" id="tab-audit-btn" style="font-size: 13px;">
                    Site Audit Findings
                </button>
                <button class="btn ${this.activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}" id="tab-history-btn" style="font-size: 13px;">
                    Issue History & Snapshot Comparison
                </button>
            </div>

            <div id="technical-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Evaluating 15 technical audit categories...
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
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                const projs = projectStore.projects || [];
                const buttonsHtml = projs.map(p => `
                    <button class="btn btn-secondary btn-sm" onclick="projectStore.setSelectedProjectId('${p.id}'); window.location.reload();" style="margin: 4px;">
                        ${p.name} (${p.domain || p.url || 'website'})
                    </button>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 40px; text-align: center;">
                        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">Select a Website to View Its SEO Audit</h3>
                        <p style="color: var(--text-secondary); margin-bottom: 20px;">Detailed technical SEO audits, page findings, and status codes are specific to individual websites.</p>
                        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;">
                            ${buttonsHtml || '<button class="btn btn-primary" onclick="window.showCreateProjectModal()">+ Add Website</button>'}
                        </div>
                    </div>
                `;
                return;
            }

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <a href="${API_BASE_URL}/api/projects/${projectId}/technical/report.pdf" target="_blank" class="btn btn-secondary btn-sm">Download PDF</a>
                    <a href="${API_BASE_URL}/api/projects/${projectId}/technical/export.csv" target="_blank" class="btn btn-secondary btn-sm">Export CSV</a>
                `;
            }

            if (this.activeTab === 'history') {
                const histData = await apiClient.get(`/api/projects/${projectId}/technical/issue-history`);

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

            const auditData = await apiClient.get(`/api/projects/${projectId}/technical?limit=200&offset=0`);

            const health = auditData.health_score || 100;
            const allIssues = auditData.issues || [];
            const summary = auditData.summary || {};
            const categories = auditData.category_breakdown || {};
            const totalAuditedPages = auditData.total_audited_pages || 0;

            // Filter issues by active category filter
            let filteredIssues = allIssues;
            if (this.selectedCategoryFilter !== 'all') {
                filteredIssues = allIssues.filter(i => (i.category || '').toLowerCase() === this.selectedCategoryFilter.toLowerCase());
            }

            // Category Cards Breakdown
            let catCardsHtml = Object.entries(categories).map(([catName, stats]) => {
                const isEvaluated = stats.evaluated !== false;
                const total = stats.critical + stats.error + stats.warning + stats.notice;
                const isSelected = this.selectedCategoryFilter.toLowerCase() === catName.toLowerCase();

                let statusBadgeText = "Passed";
                let statusColor = "var(--success, #22c55e)";

                if (!isEvaluated) {
                    statusBadgeText = "Not Analyzed";
                    statusColor = "#94a3b8";
                } else if (total > 0 || stats.status === "Issues Found") {
                    statusBadgeText = `${total} issue${total === 1 ? '' : 's'}`;
                    statusColor = "var(--critical, #ef4444)";
                }

                return `
                    <div class="card category-filter-card ${isSelected ? 'selected-cat-card' : ''}" 
                         data-cat="${catName}"
                         style="padding: 14px; font-size: 13px; cursor: pointer; border: ${isSelected ? '2px solid var(--primary)' : '1px solid var(--border)'}; transition: all 0.15s ease;"
                         onclick="window.selectAuditCategoryFilter('${catName}')">
                        <div style="display: flex; justify-content: space-between; font-weight: 600; margin-bottom: 6px;">
                            <span>${catName}</span>
                            <span style="color: ${statusColor}; font-size: 11px; font-weight: 700;">${statusBadgeText}</span>
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); display: flex; gap: 6px; flex-wrap: wrap;">
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

            // Table Rows for Filtered Findings
            let tableRows = filteredIssues.map((iss, idx) => {
                let badgeClass = 'badge-info';
                const sev = (iss.severity || '').toLowerCase();
                if (sev === 'critical') badgeClass = 'badge-critical';
                else if (sev === 'warning') badgeClass = 'badge-warning';

                const urlsList = iss.affected_urls || [];
                const urlsPreview = urlsList.slice(0, 3).map(u => `<div><code>${u}</code></div>`).join('');
                const moreCount = urlsList.length > 3 ? urlsList.length - 3 : 0;

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 16px;"><span class="badge ${badgeClass}">${iss.severity.toUpperCase()}</span></td>
                        <td style="padding: 12px 16px; font-weight: 600;">${iss.category || 'Technical'}</td>
                        <td style="padding: 12px 16px;">
                            <div style="font-weight: 600; color: var(--text-primary);">${iss.title}</div>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${iss.description || ''}</div>
                        </td>
                        <td style="padding: 12px 16px; font-size: 12px;">
                            ${urlsPreview || '<code>All pages</code>'}
                            ${moreCount > 0 ? `<div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">+ ${moreCount} more URLs</div>` : ''}
                        </td>
                        <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${iss.recommendation || 'Fix identified issue.'}</td>
                    </tr>
                `;
            }).join('');

            // Dynamic Window Filter Handler
            window.selectAuditCategoryFilter = (catName) => {
                if (this.selectedCategoryFilter.toLowerCase() === catName.toLowerCase()) {
                    this.selectedCategoryFilter = 'all';
                } else {
                    this.selectedCategoryFilter = catName;
                }
                this.mounted();
            };

            container.innerHTML = `
                <!-- WEBSITE SUMMARY KPI BAR -->
                <div class="card" style="padding: 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700;">Site Audit Health Score</div>
                        <div style="font-size: 36px; font-weight: 700; color: ${health >= 85 ? 'var(--success)' : (health >= 70 ? 'var(--warning)' : 'var(--critical)')}; font-family: var(--font-heading);">
                            ${health} <span style="font-size: 18px; color: var(--text-secondary);">/ 100</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Website: <strong>${selectedProj.name}</strong> (${selectedProj.domain || selectedProj.url})</div>
                    </div>
                    <div style="display: flex; gap: 20px; font-size: 13px; flex-wrap: wrap;">
                        <div><div style="color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">Pages Crawled</div><div style="font-size: 18px; font-weight: 700;">${totalAuditedPages}</div></div>
                        <div><div style="color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">Critical Errors</div><div style="font-size: 18px; font-weight: 700; color: var(--critical);">${summary.critical_errors || 0}</div></div>
                        <div><div style="color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">Warnings</div><div style="font-size: 18px; font-weight: 700; color: var(--warning);">${summary.warnings || 0}</div></div>
                        <div><div style="color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">Notices</div><div style="font-size: 18px; font-weight: 700;">${summary.notices || 0}</div></div>
                        <div><div style="color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">Passed Checks</div><div style="font-size: 18px; font-weight: 700; color: var(--success);">${summary.passed_checks || 0}</div></div>
                    </div>
                </div>

                <!-- 15 AUDIT CATEGORIES GRID -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0;">15 Technical Audit Categories</h3>
                    ${this.selectedCategoryFilter !== 'all' ? `<button class="btn btn-secondary btn-sm" onclick="window.selectAuditCategoryFilter('all')" style="font-size: 11px;">Clear Filter (${this.selectedCategoryFilter})</button>` : '<span style="font-size: 11px; color: var(--text-secondary);">Click any category card to filter drill-down findings below</span>'}
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px;">
                    ${catCardsHtml}
                </div>

                <!-- AUDIT FINDINGS DRILL-DOWN TABLE -->
                <div class="card" style="padding: 0; overflow: hidden;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0;">
                            Audit Rule Findings & Evidence (${filteredIssues.length})
                            ${this.selectedCategoryFilter !== 'all' ? `<span style="font-size: 12px; color: var(--primary); margin-left: 8px;">[Filtered: ${this.selectedCategoryFilter}]</span>` : ''}
                        </h3>
                        <span style="font-size: 12px; color: var(--text-secondary);">Deterministic Rule Engine</span>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 16px;">Severity</th>
                                    <th style="padding: 12px 16px;">Category</th>
                                    <th style="padding: 12px 16px;">Rule Finding & Problem</th>
                                    <th style="padding: 12px 16px;">Affected URLs Evidence</th>
                                    <th style="padding: 12px 16px;">Action Recommendation</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows.length > 0 ? tableRows : `<tr><td colspan="5" style="padding: 24px; text-align: center; color: var(--text-secondary);">No issues detected for the selected filter.</td></tr>`}
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
