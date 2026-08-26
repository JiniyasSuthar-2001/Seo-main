import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderSourceBadge } from '../components/AIBadge.js';
import { AuditEvidenceModal } from '../components/AuditEvidenceModal.js';

export class Technical {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'technical-view';
        this.activeTab = 'audit'; // audit, history
        this.selectedCategoryFilter = 'all';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">15-Category Technical SEO Audit</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Deterministic technical checks, category evidence drill-down, and snapshot comparisons.</p>
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
                    Evaluating technical audit categories...
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
                    <button id="btn-export-tech-pdf" class="btn btn-secondary btn-sm">Download PDF</button>
                    <button id="btn-export-tech-csv" class="btn btn-secondary btn-sm">Export CSV</button>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Run New Crawl</button>
                `;

                const pdfBtn = document.getElementById('btn-export-tech-pdf');
                const csvBtn = document.getElementById('btn-export-tech-csv');
                if (pdfBtn) pdfBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/technical/report.pdf`, `${selectedProj.name || 'project'}_technical_audit.pdf`, e.currentTarget);
                if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/technical/export.csv`, `${selectedProj.name || 'project'}_technical_audit.csv`, e.currentTarget);
            }

            if (this.activeTab === 'history') {
                const histData = await apiClient.get(`/api/projects/${projectId}/technical/issue-history`);
                container.innerHTML = `
                    <div class="card" style="padding: 24px;">
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Snapshot Audit Comparison</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
                            ${histData.message || "Compare current crawl issues against previous completed snapshot."}
                        </p>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
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
            const categoryTable = auditData.category_checks_table || [];
            const totalAuditedPages = auditData.total_audited_pages || 0;
            const htmlPagesCount = auditData.successful_html_pages_count || totalAuditedPages;
            const blockedPagesCount = auditData.blocked_pages_count || 0;
            const totalChecks = auditData.total_evaluated_checks || summary.total_checks || (htmlPagesCount * 14);
            const checksExplanation = auditData.checks_explanation || `${htmlPagesCount} analyzed pages × ${auditData.evaluated_rules_count || 14} evaluated rules`;
            const crawlTimestamp = auditData.crawl_timestamp ? new Date(auditData.crawl_timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Latest Crawl Snapshot';
            const crawlStatus = auditData.crawl_status || 'completed';

            // Filter issues by active category filter
            let filteredIssues = allIssues;
            if (this.selectedCategoryFilter !== 'all') {
                filteredIssues = allIssues.filter(i => (i.category || '').toLowerCase() === this.selectedCategoryFilter.toLowerCase());
            }

            // Category Checks Table Rows
            const categoryChecksRowsHtml = categoryTable.map(c => {
                let statusBadgeHtml = '<span class="badge badge-success">Passed</span>';
                if (!c.evaluated) {
                    statusBadgeHtml = `<span class="badge badge-secondary" title="${this.escapeHtml(c.reason)}">Not Evaluated</span>`;
                } else if (c.issues_count > 0 || c.status === 'Issues Found') {
                    statusBadgeHtml = `<span class="badge badge-critical">${c.issues_count} Issue${c.issues_count === 1 ? '' : 's'}</span>`;
                }

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 10px 16px; font-weight: 600; color: var(--text-primary);">${c.category}</td>
                        <td style="padding: 10px 16px; font-family: monospace;">${c.evaluated ? c.checks_performed : '-'}</td>
                        <td style="padding: 10px 16px; font-family: monospace; color: var(--success);">${c.evaluated ? c.passed : '-'}</td>
                        <td style="padding: 10px 16px; font-family: monospace; color: ${c.issues_count > 0 ? 'var(--critical)' : 'var(--text-secondary)'};">${c.evaluated ? c.issues_count : '-'}</td>
                        <td style="padding: 10px 16px;">${statusBadgeHtml}</td>
                    </tr>
                `;
            }).join('');

            // Table Rows for Findings
            let tableRows = filteredIssues.map((iss, idx) => {
                let badgeClass = 'badge-info';
                const sev = (iss.severity || '').toLowerCase();
                if (sev === 'critical') badgeClass = 'badge-critical';
                else if (sev === 'warning') badgeClass = 'badge-warning';

                const urlsList = iss.affected_urls || [];
                const isAIAssisted = iss.is_ai_generated || iss.source_type === 'ai_analysis';

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 16px;"><span class="badge ${badgeClass}">${(iss.severity || 'HIGH').toUpperCase()}</span></td>
                        <td style="padding: 12px 16px; font-weight: 600;">
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span>${iss.category || 'Technical'}</span>
                                ${isAIAssisted ? renderAIBadge('assisted') : renderSourceBadge('crawl')}
                            </div>
                        </td>
                        <td style="padding: 12px 16px;">
                            <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">${this.escapeHtml(iss.title)}</div>
                            <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 6px;">${this.escapeHtml(iss.description || '')}</div>
                            <button class="btn btn-secondary btn-sm btn-open-evidence-modal" 
                                    data-idx="${idx}"
                                    style="font-size: 11.5px; font-weight: 600; padding: 3px 10px;">
                                View Evidence (${urlsList.length} affected URL${urlsList.length === 1 ? '' : 's'})
                            </button>
                        </td>
                        <td style="padding: 12px 16px; font-size: 12px;">
                            <span class="badge badge-secondary" style="font-size: 11px;">${urlsList.length} Affected</span>
                        </td>
                        <td style="padding: 12px 16px; font-size: 12.5px; color: var(--text-secondary);">${this.escapeHtml(iss.recommendation || 'Fix identified issue.')}</td>
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
                <!-- AUDIT CONTEXT BANNER -->
                <div class="card" style="padding: 16px 20px; margin-bottom: 20px; background: var(--bg-card); border-left: 4px solid var(--primary); border-radius: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="font-size: 12px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">AUDIT SNAPSHOT CONTEXT</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-top: 2px;">
                            Website: <strong>${this.escapeHtml(selectedProj.name)}</strong> (${this.escapeHtml(selectedProj.domain || selectedProj.url)})
                        </div>
                        <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">
                            Snapshot Date: <strong>${crawlTimestamp}</strong> &nbsp;•&nbsp; Status: <span class="badge ${crawlStatus === 'completed_with_errors' ? 'badge-warning' : 'badge-success'}">${crawlStatus.replace(/_/g, ' ')}</span>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-secondary btn-sm" onclick="window.location.href='/crawl-history'">View Crawl History</button>
                    </div>
                </div>

                <!-- TOP SUMMARY KPI BAR -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    <div class="card" style="padding: 20px; background: var(--bg-card);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700;">Health Score</div>
                        <div style="font-size: 32px; font-weight: 700; color: ${health >= 85 ? 'var(--success)' : (health >= 70 ? 'var(--warning)' : 'var(--critical)')}; margin-top: 4px;">
                            ${health} <span style="font-size: 16px; color: var(--text-tertiary);">/ 100</span>
                        </div>
                    </div>

                    <div class="card" style="padding: 20px; background: var(--bg-card);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700;">Pages Crawled</div>
                        <div style="font-size: 28px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${totalAuditedPages}</div>
                        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${htmlPagesCount} analyzed, ${blockedPagesCount} failed/blocked</div>
                    </div>

                    <div class="card" style="padding: 20px; background: var(--bg-card); border-left: 3px solid var(--primary);">
                        <div style="font-size: 11px; color: var(--primary); text-transform: uppercase; font-weight: 700;">Assessed Checks</div>
                        <div style="font-size: 28px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${totalChecks.toLocaleString()}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${checksExplanation}</div>
                    </div>

                    <div class="card" style="padding: 20px; background: var(--bg-card);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700;">Issues Detected</div>
                        <div style="font-size: 28px; font-weight: 700; color: var(--critical); margin-top: 4px;">${allIssues.length}</div>
                        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${summary.critical_errors || 0} critical, ${summary.warnings || 0} warnings</div>
                    </div>
                </div>

                <!-- AUDIT METHODOLOGY & COVERAGE PANEL -->
                <div class="card" style="padding: 20px; margin-bottom: 24px; background: var(--bg-card);">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 8px 0; color: var(--text-primary);">Audit Coverage & Methodology</h3>
                    <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 16px 0; line-height: 1.5;">
                        This audit evaluates the pages and signals collected during the latest website crawl. Each check is based on real crawl data and implemented deterministic SEO rules.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; background: var(--bg-subtle); padding: 14px; border-radius: 8px; border: 1px solid var(--border);">
                        <div><span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; display: block;">PAGES CRAWLED</span><strong style="font-size: 15px; color: var(--text-primary);">${totalAuditedPages}</strong></div>
                        <div><span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; display: block;">ANALYZED PAGES</span><strong style="font-size: 15px; color: var(--success);">${htmlPagesCount}</strong></div>
                        <div><span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; display: block;">FAILED / BLOCKED</span><strong style="font-size: 15px; color: ${blockedPagesCount > 0 ? 'var(--critical)' : 'var(--text-secondary)'};">${blockedPagesCount}</strong></div>
                        <div><span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; display: block;">RULES EVALUATED</span><strong style="font-size: 15px; color: var(--text-primary);">${auditData.evaluated_rules_count || 14} Rules</strong></div>
                        <div><span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; display: block;">CHECKS PERFORMED</span><strong style="font-size: 15px; color: var(--primary);">${totalChecks.toLocaleString()}</strong></div>
                        <div><span style="font-size: 11px; color: var(--text-tertiary); font-weight: 600; display: block;">ISSUES DETECTED</span><strong style="font-size: 15px; color: var(--critical);">${allIssues.length}</strong></div>
                    </div>
                </div>

                <!-- CHECKS PERFORMED CATEGORY BREAKDOWN TABLE -->
                <div class="card" style="padding: 20px; margin-bottom: 24px; background: var(--bg-card);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Checks Performed Breakdown</h3>
                        <span style="font-size: 12px; color: var(--text-secondary);">15 Technical Categories</span>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 10px 16px;">Category</th>
                                    <th style="padding: 10px 16px;">Checks Performed</th>
                                    <th style="padding: 10px 16px;">Passed</th>
                                    <th style="padding: 10px 16px;">Issues Found</th>
                                    <th style="padding: 10px 16px;">Evaluation Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${categoryChecksRowsHtml}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- AUDIT FINDINGS DRILL-DOWN TABLE -->
                <div class="card" style="padding: 0; overflow: hidden;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0;">
                            Rule Findings & Problems (${filteredIssues.length})
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
                                    <th style="padding: 12px 16px;">Rule Finding & Evidence</th>
                                    <th style="padding: 12px 16px;">Affected Count</th>
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

            // Bind Evidence Modal Triggers
            container.querySelectorAll('.btn-open-evidence-modal').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                    const iss = filteredIssues[idx];
                    if (iss) {
                        AuditEvidenceModal.open({
                            title: iss.title,
                            ruleId: iss.rule_id,
                            category: iss.category,
                            severity: iss.severity,
                            description: iss.description,
                            recommendation: iss.recommendation,
                            affectedUrls: iss.affected_urls,
                            evidenceText: iss.evidence,
                            provenance: 'Crawled Data'
                        });
                    }
                });
            });

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Technical Audit Error", e.message || "Unable to load technical audit issues.", () => this.mounted());
            }
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
