import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderSourceBadge } from '../components/AIBadge.js';
import { AuditEvidenceModal } from '../components/AuditEvidenceModal.js';
import { renderTooltip } from '../components/Tooltip.js';

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
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Website Health</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">We checked your website for common issues that can affect search visibility and user experience.</p>
                </div>
                <div id="technical-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- TAB BAR -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <button class="btn ${this.activeTab === 'audit' ? 'btn-primary' : 'btn-secondary'}" id="tab-audit-btn" style="font-size: 13px;">
                    Website Checks
                </button>
                <button class="btn ${this.activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}" id="tab-history-btn" style="font-size: 13px;">
                    Compare Old vs New Results
                </button>
            </div>

            <div id="technical-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Evaluating website health checks...
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
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
                return;
            }

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <button id="btn-export-tech-pdf" class="btn btn-secondary btn-sm">Download Report (PDF)</button>
                    <button id="btn-export-tech-csv" class="btn btn-secondary btn-sm">Download CSV</button>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                `;

                const pdfBtn = document.getElementById('btn-export-tech-pdf');
                const csvBtn = document.getElementById('btn-export-tech-csv');
                if (pdfBtn) pdfBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/technical/report.pdf`, `${selectedProj.name || 'project'}_website_health.pdf`, e.currentTarget);
                if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/technical/export.csv`, `${selectedProj.name || 'project'}_website_health.csv`, e.currentTarget);
            }

            if (this.activeTab === 'history') {
                const histData = await apiClient.get(`/api/projects/${projectId}/technical/issue-history`);
                container.innerHTML = `
                    <div class="card" style="padding: 24px; border-radius: 14px;">
                        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">Compare Old vs New Results</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
                            ${histData.message || "Compare current website scan problems against your previous saved scan."}
                        </p>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                            <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Resolved Problems</div>
                                <div style="font-size: 26px; font-weight: 800; color: var(--success); margin-top: 4px;">${histData.resolved_issues_count || 0}</div>
                            </div>
                            <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">New Problems</div>
                                <div style="font-size: 26px; font-weight: 800; color: var(--critical); margin-top: 4px;">${histData.new_issues_count || 0}</div>
                            </div>
                            <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Active Saved Scan</div>
                                <div style="font-size: 13px; font-weight: 600; margin-top: 8px; color: var(--text-primary);">${histData.current_snapshot || "Active"}</div>
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
            const categoryTable = auditData.category_checks_table || [];
            const totalAuditedPages = auditData.total_audited_pages || 0;
            const htmlPagesCount = auditData.successful_html_pages_count || totalAuditedPages;
            const blockedPagesCount = auditData.blocked_pages_count || 0;
            const totalChecks = auditData.total_evaluated_checks || summary.total_checks || (htmlPagesCount * 14);
            const checksExplanation = auditData.checks_explanation || `${htmlPagesCount} analyzed pages × ${auditData.evaluated_rules_count || 14} evaluated rules`;
            const crawlTimestamp = auditData.crawl_timestamp ? new Date(auditData.crawl_timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '26 Aug 2026';

            // Filter issues by active category filter
            let filteredIssues = allIssues;
            if (this.selectedCategoryFilter !== 'all') {
                filteredIssues = allIssues.filter(i => (i.category || '').toLowerCase() === this.selectedCategoryFilter.toLowerCase());
            }

            // Category Translations for Beginner Usability
            const catTranslations = {
                "Crawlability": "Page Availability",
                "Indexability": "Can Search Engines Find Pages?",
                "HTTPS": "Secure Connections (HTTPS)",
                "Metadata": "Page Titles & Search Descriptions",
                "Content": "Content Length & Depth",
                "Headings": "Main Headings (H1)",
                "Canonicals": "Preferred Page Addresses",
                "Images": "Image Alt Text",
                "Internal Links": "Links Between Your Pages",
                "External Links": "Links to Other Websites",
                "Structured Data": "Rich Snippet Markup",
                "Mobile": "Mobile Experience",
                "International SEO": "Language Tags",
                "Security": "Security Verification",
                "Performance": "Page Speed"
            };

            // Category Checks Table Rows
            const categoryChecksRowsHtml = categoryTable.map(c => {
                const plainCatName = catTranslations[c.category] || c.category;
                let statusBadgeHtml = '<span class="badge badge-success">Passed</span>';
                if (!c.evaluated) {
                    statusBadgeHtml = `<span class="badge badge-secondary" title="${this.escapeHtml(c.reason)}">Not Evaluated</span>`;
                } else if (c.issues_count > 0 || c.status === 'Issues Found') {
                    statusBadgeHtml = `<span class="badge badge-critical">${c.issues_count} Problem${c.issues_count === 1 ? '' : 's'}</span>`;
                }

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 10px 16px; font-weight: 600; color: var(--text-primary);">${plainCatName}</td>
                        <td style="padding: 10px 16px; font-family: monospace;">${c.evaluated ? c.checks_performed : '-'}</td>
                        <td style="padding: 10px 16px; font-family: monospace; color: var(--success);">${c.evaluated ? c.passed : '-'}</td>
                        <td style="padding: 10px 16px; font-family: monospace; color: ${c.issues_count > 0 ? 'var(--critical)' : 'var(--text-secondary)'};">${c.evaluated ? c.issues_count : '-'}</td>
                        <td style="padding: 10px 16px;">${statusBadgeHtml}</td>
                    </tr>
                `;
            }).join('');

            // Table Rows for Findings (Problems We Found)
            let tableRows = filteredIssues.map((iss, idx) => {
                let badgeClass = 'badge-info';
                const sev = (iss.severity || '').toLowerCase();
                if (sev === 'critical') badgeClass = 'badge-critical';
                else if (sev === 'warning') badgeClass = 'badge-warning';

                const urlsList = iss.affected_urls || [];

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 16px;"><span class="badge ${badgeClass}">${(iss.severity || 'HIGH').toUpperCase()}</span></td>
                        <td style="padding: 12px 16px; font-weight: 600;">
                            ${catTranslations[iss.category] || iss.category || 'Website Check'}
                        </td>
                        <td style="padding: 12px 16px;">
                            <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">${this.escapeHtml(iss.title)}</div>
                            <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 6px;">${this.escapeHtml(iss.description || '')}</div>
                            <button class="btn btn-secondary btn-sm btn-open-evidence-modal" 
                                    data-idx="${idx}"
                                    style="font-size: 11.5px; font-weight: 600; padding: 4px 12px;">
                                See What We Found (${urlsList.length} affected page${urlsList.length === 1 ? '' : 's'})
                            </button>
                        </td>
                        <td style="padding: 12px 16px; font-size: 12px;">
                            <span class="badge badge-secondary" style="font-size: 11px;">${urlsList.length} Affected</span>
                        </td>
                        <td style="padding: 12px 16px; font-size: 12.5px; color: var(--text-secondary);">${this.escapeHtml(iss.recommendation || 'Fix identified issue.')}</td>
                    </tr>
                `;
            }).join('');

            container.innerHTML = `
                <!-- TOP SUMMARY KPI BAR -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    <div class="card" style="padding: 20px; background: var(--bg-card);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700;">
                            Website Health Score ${renderTooltip('Overall technical health score for your website (0-100). Higher is better.')}
                        </div>
                        <div style="font-size: 32px; font-weight: 700; color: ${health >= 85 ? 'var(--success)' : (health >= 70 ? 'var(--warning)' : 'var(--critical)')}; margin-top: 4px;">
                            ${health} <span style="font-size: 16px; color: var(--text-tertiary);">/ 100</span>
                        </div>
                    </div>

                    <div class="card" style="padding: 20px; background: var(--bg-card);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700;">Pages Scanned</div>
                        <div style="font-size: 28px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${totalAuditedPages}</div>
                        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${htmlPagesCount} analyzed, ${blockedPagesCount} failed/blocked</div>
                    </div>

                    <div class="card" style="padding: 20px; background: var(--bg-card); border-left: 3px solid var(--primary);">
                        <div style="font-size: 11px; color: var(--primary); text-transform: uppercase; font-weight: 700;">
                            Checks Performed ${renderTooltip('Individual checks performed across your scanned pages.')}
                        </div>
                        <div style="font-size: 28px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${totalChecks.toLocaleString()}</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${checksExplanation}</div>
                    </div>

                    <div class="card" style="padding: 20px; background: var(--bg-card);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700;">Problems Found</div>
                        <div style="font-size: 28px; font-weight: 700; color: var(--critical); margin-top: 4px;">${allIssues.length}</div>
                        <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${summary.critical_errors || 0} critical, ${summary.warnings || 0} warnings</div>
                    </div>
                </div>

                <!-- CHECKS PERFORMED BREAKDOWN TABLE -->
                <div class="card" style="padding: 20px; margin-bottom: 24px; background: var(--bg-card); border-radius: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">What We Checked</h3>
                        ${renderSourceBadge('crawl')}
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 10px 16px;">Category Checked</th>
                                    <th style="padding: 10px 16px;">Checks Performed</th>
                                    <th style="padding: 10px 16px;">Passed</th>
                                    <th style="padding: 10px 16px;">Problems Found</th>
                                    <th style="padding: 10px 16px;">Evaluation Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${categoryChecksRowsHtml}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- PROBLEMS WE FOUND TABLE -->
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">
                            Problems We Found (${filteredIssues.length})
                        </h3>
                        ${renderSourceBadge('crawl')}
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 16px;">Priority</th>
                                    <th style="padding: 12px 16px;">Category</th>
                                    <th style="padding: 12px 16px;">Problem Finding & Action</th>
                                    <th style="padding: 12px 16px;">Affected Pages</th>
                                    <th style="padding: 12px 16px;">Recommended Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows.length > 0 ? tableRows : `<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--text-secondary);">✓ Zero problems detected for this check.</td></tr>`}
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
                            category: catTranslations[iss.category] || iss.category,
                            severity: iss.severity,
                            description: iss.description,
                            recommendation: iss.recommendation,
                            affectedUrls: iss.affected_urls,
                            evidenceText: iss.evidence,
                            provenance: 'Website Scan',
                            scanDate: crawlTimestamp
                        });
                    }
                });
            });

        } catch (e) {
            renderBackendOfflineState(container, `We couldn't load this information right now. Please try again.`, () => this.mounted());
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
