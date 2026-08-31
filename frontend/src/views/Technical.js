import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderSourceBadge } from '../components/AIBadge.js';
import { AuditEvidenceModal } from '../components/AuditEvidenceModal.js';
import { HealthScoreDetailModal } from '../components/HealthScoreDetailModal.js';
import { ChecksPerformedDetailModal } from '../components/ChecksPerformedDetailModal.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class Technical {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'technical-view';
        this.activeTab = 'audit'; // audit, history
        this.selectedCategoryFilter = 'all';
        this.issuesPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
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
            this.issuesPage = 1;
            this.mounted();
        });

        document.getElementById('tab-history-btn')?.addEventListener('click', () => {
            this.activeTab = 'history';
            this.issuesPage = 1;
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
                const hasHistory = histData.has_history !== false;
                const compItems = histData.comparison_items || [];

                let tableRows = compItems.map(item => {
                    let badgeStyle = 'background: rgba(100, 116, 139, 0.1); color: var(--text-secondary); border: 1px solid var(--border);';
                    const st = (item.status || '').toUpperCase();
                    if (st === 'RESOLVED') badgeStyle = 'background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);';
                    else if (st === 'NEW') badgeStyle = 'background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);';
                    else if (st === 'IMPROVED') badgeStyle = 'background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3);';
                    else if (st === 'WORSENED') badgeStyle = 'background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);';

                    return `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(item.title)}</td>
                            <td style="padding: 12px;">${item.previous_affected_count} page${item.previous_affected_count === 1 ? '' : 's'}</td>
                            <td style="padding: 12px; font-weight: 600;">${item.current_affected_count} page${item.current_affected_count === 1 ? '' : 's'}</td>
                            <td style="padding: 12px;">
                                <span class="badge" style="${badgeStyle} font-size: 11px; font-weight: 800;">${this.escapeHtml(item.status)}</span>
                            </td>
                            <td style="padding: 12px 18px; font-size: 12.5px; color: var(--text-secondary);">${this.escapeHtml(item.change_summary)}</td>
                        </tr>
                    `;
                }).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 24px; border-radius: 14px; margin-bottom: 20px;">
                        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">Compare Old vs New Results</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
                            ${this.escapeHtml(histData.message || "Compare current website scan problems against your previous saved scan.")}
                        </p>
                        
                        ${hasHistory ? `
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; margin-bottom: 24px;">
                                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Resolved Problems</div>
                                    <div style="font-size: 24px; font-weight: 800; color: #10b981; margin-top: 4px;">${histData.resolved_issues_count || 0}</div>
                                </div>
                                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">New Problems</div>
                                    <div style="font-size: 24px; font-weight: 800; color: #ef4444; margin-top: 4px;">${histData.new_issues_count || 0}</div>
                                </div>
                                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Improved Findings</div>
                                    <div style="font-size: 24px; font-weight: 800; color: #3b82f6; margin-top: 4px;">${histData.improved_issues_count || 0}</div>
                                </div>
                                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Worsened Findings</div>
                                    <div style="font-size: 24px; font-weight: 800; color: #f59e0b; margin-top: 4px;">${histData.worsened_issues_count || 0}</div>
                                </div>
                                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Still Open</div>
                                    <div style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${histData.still_open_issues_count || 0}</div>
                                </div>
                            </div>
                        ` : ''}
                    </div>

                    ${hasHistory ? `
                        <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                            <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--bg-subtle);">
                                <h4 style="margin: 0; font-size: 15px; font-weight: 700; color: var(--text-primary);">Audit Findings Delta Breakdown (${compItems.length})</h4>
                            </div>
                            <div style="overflow-x: auto;">
                                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                    <thead>
                                        <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                            <th style="padding: 12px 18px; width: 30%;">Finding / Check</th>
                                            <th style="padding: 12px;">Previous Crawl</th>
                                            <th style="padding: 12px;">Latest Crawl</th>
                                            <th style="padding: 12px;">Status</th>
                                            <th style="padding: 12px 18px;">Summary</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${tableRows.length > 0 ? tableRows : `<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--text-secondary);">No findings to compare.</td></tr>`}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ` : ''}
                `;
                return;
            }

            const auditData = await apiClient.get(`/api/projects/${projectId}/technical?limit=500&offset=0`);

            const hasCrawl = auditData.crawl_status !== 'no_crawl' && auditData.score_available !== false && auditData.health_score !== null && auditData.health_score !== undefined && (auditData.total_audited_pages > 0 || (auditData.issues && auditData.issues.length > 0));
            const health = (auditData.health_score !== undefined && auditData.health_score !== null) ? auditData.health_score : null;
            const allIssues = auditData.issues || [];
            const summary = auditData.summary || {};
            const categoryTable = auditData.category_checks_table || [];
            const totalAuditedPages = auditData.total_audited_pages || 0;
            const htmlPagesCount = auditData.successful_html_pages_count || totalAuditedPages;
            const blockedPagesCount = auditData.blocked_pages_count || 0;
            const totalChecks = auditData.total_evaluated_checks || summary.total_checks || (htmlPagesCount * 14);
            const checksExplanation = auditData.checks_explanation || `${htmlPagesCount} analyzed pages × ${auditData.evaluated_rules_count || 14} evaluated rules`;
            const crawlTimestamp = auditData.crawl_timestamp ? new Date(auditData.crawl_timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recent Scan';

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

            // Filter issues by active category filter
            let filteredIssues = allIssues;
            if (this.selectedCategoryFilter !== 'all') {
                filteredIssues = allIssues.filter(i => {
                    const rawCat = (i.category || '').toLowerCase();
                    const filterCat = this.selectedCategoryFilter.toLowerCase();
                    const plainCat = (catTranslations[i.category] || i.category || '').toLowerCase();
                    return rawCat === filterCat || plainCat === filterCat;
                });
            }

            // Paginate filtered issues using 20 rows per page standard
            const paginated = Pagination.paginateArray(filteredIssues, this.issuesPage, this.pageSize);
            this.issuesPage = paginated.currentPage;

            // Render Category Cards
            const categoryCardsHtml = categoryTable.map(c => {
                const plainCatName = catTranslations[c.category] || c.category;
                const isSelected = this.selectedCategoryFilter.toLowerCase() === c.category.toLowerCase() || 
                                   this.selectedCategoryFilter.toLowerCase() === plainCatName.toLowerCase();

                let rightLineColor = 'var(--text-tertiary, #94a3b8)';
                let statusText = 'Not Evaluated';
                let statusColor = 'var(--text-tertiary)';

                if (c.evaluated === false || c.status === 'Not Evaluated' || c.status === 'Not Analyzed') {
                    rightLineColor = 'var(--text-tertiary, #94a3b8)';
                    statusText = 'Not Evaluated';
                    statusColor = 'var(--text-tertiary)';
                } else if (c.issues_count > 0 || c.status === 'Issues Found') {
                    if (c.critical > 0 || c.error > 0) {
                        rightLineColor = 'var(--critical, #ef4444)';
                    } else {
                        rightLineColor = 'var(--warning, #f59e0b)';
                    }
                    statusText = `${c.issues_count} problem${c.issues_count === 1 ? '' : 's'}`;
                    statusColor = (c.critical > 0 || c.error > 0) ? 'var(--critical)' : 'var(--warning)';
                } else {
                    rightLineColor = 'var(--success, #10b981)';
                    statusText = '✓ Passed';
                    statusColor = 'var(--success)';
                }

                return `
                    <div class="category-card-item" 
                         data-category="${this.escapeHtml(c.category)}"
                         style="position: relative; padding: 14px 18px 14px 14px; background: var(--bg-card); border-radius: 10px; border: ${isSelected ? '2px solid var(--primary)' : '1px solid var(--border)'}; cursor: pointer; transition: all 0.18s ease; overflow: hidden; display: flex; justify-content: space-between; align-items: center; box-shadow: ${isSelected ? '0 0 0 1px var(--primary)' : 'none'};">
                        <div style="flex: 1; padding-right: 10px;">
                            <div style="font-size: 13.5px; font-weight: 700; color: ${isSelected ? 'var(--primary)' : 'var(--text-primary)'}; margin-bottom: 6px;">
                                ${plainCatName}
                            </div>
                            <div style="display: flex; gap: 10px; font-size: 11.5px; color: var(--text-secondary);">
                                <span><strong>${c.checks_performed || 0}</strong> checked</span>
                                <span style="color: ${c.evaluated ? 'var(--success)' : 'var(--text-tertiary)'};"><strong>${c.passed || 0}</strong> passed</span>
                            </div>
                            <div style="font-size: 11.5px; margin-top: 4px; font-weight: 600; color: ${statusColor};">
                                ${statusText}
                            </div>
                        </div>
                        <div style="position: absolute; right: 0; top: 0; bottom: 0; width: 5px; background: ${rightLineColor}; border-top-right-radius: 9px; border-bottom-right-radius: 9px;"></div>
                    </div>
                `;
            }).join('');

            // Table Rows for Findings (Problems We Found)
            let tableRows = paginated.items.map((iss, idx) => {
                let badgeClass = 'badge-info';
                const sev = (iss.severity || '').toLowerCase();
                if (sev === 'critical') badgeClass = 'badge-critical';
                else if (sev === 'warning') badgeClass = 'badge-warning';

                const urlsList = iss.affected_urls || [];
                const globalIdx = (paginated.currentPage - 1) * paginated.pageSize + idx;

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
                                    data-idx="${globalIdx}"
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
                <!-- TOP SUMMARY KPI BAR (FUNCTIONAL & INTERACTIVE) -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
                    
                    <!-- BOX 1: HEALTH SCORE -->
                    <div class="card kpi-card-clickable" id="kpi-health-score" tabindex="0" role="button" aria-label="Website Health Score Details"
                         style="padding: 20px; background: var(--bg-card); cursor: pointer; transition: all 0.2s ease; border: 1px solid var(--border); position: relative;">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700; display: flex; justify-content: space-between; align-items: center;">
                            <span>Website Health Score ${renderTooltip('Overall technical health score for your website (0-100). Click to view full calculation breakdown.')}</span>
                            <span style="font-size: 10px; color: var(--primary); font-weight: 600;">Details ↗</span>
                        </div>
                        ${hasCrawl && health !== null ? `
                            <div style="font-size: 32px; font-weight: 700; color: ${health >= 85 ? 'var(--success)' : (health >= 70 ? 'var(--warning)' : 'var(--critical)')}; margin-top: 4px;">
                                ${health} <span style="font-size: 16px; color: var(--text-tertiary);">/ 100</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Click to view scoring breakdown</div>
                        ` : `
                            <div style="font-size: 20px; font-weight: 700; color: var(--text-tertiary); margin-top: 6px;">Not yet scored</div>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">No website scan performed yet</div>
                        `}
                    </div>

                    <!-- BOX 2: PAGES SCANNED -->
                    <div class="card kpi-card-clickable" id="kpi-pages-scanned" tabindex="0" role="button" aria-label="View Scanned Pages"
                         style="padding: 20px; background: var(--bg-card); cursor: pointer; transition: all 0.2s ease; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700; display: flex; justify-content: space-between; align-items: center;">
                            <span>Pages Scanned ${renderTooltip('Total website pages scanned during crawl. Click to view scanned pages.')}</span>
                            <span style="font-size: 10px; color: var(--primary); font-weight: 600;">Inspect ↗</span>
                        </div>
                        ${hasCrawl ? `
                            <div style="font-size: 28px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${totalAuditedPages}</div>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${htmlPagesCount} analyzed, ${blockedPagesCount} failed/blocked</div>
                        ` : `
                            <div style="font-size: 20px; font-weight: 700; color: var(--text-tertiary); margin-top: 6px;">No crawl yet</div>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">0 analyzed, 0 failed/blocked</div>
                        `}
                    </div>

                    <!-- BOX 3: CHECKS PERFORMED -->
                    <div class="card kpi-card-clickable" id="kpi-checks-performed" tabindex="0" role="button" aria-label="View Checks Performed"
                         style="padding: 20px; background: var(--bg-card); cursor: pointer; transition: all 0.2s ease; border: 1px solid var(--border); border-left: 3px solid var(--primary);">
                        <div style="font-size: 11px; color: var(--primary); text-transform: uppercase; font-weight: 700; display: flex; justify-content: space-between; align-items: center;">
                            <span>Checks Performed ${renderTooltip('Total rule evaluations across all pages. Click to see all evaluated rules.')}</span>
                            <span style="font-size: 10px; color: var(--primary); font-weight: 600;">Rules ↗</span>
                        </div>
                        ${hasCrawl ? `
                            <div style="font-size: 28px; font-weight: 700; color: var(--text-primary); margin-top: 4px;">${totalChecks.toLocaleString()}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${checksExplanation}</div>
                        ` : `
                            <div style="font-size: 20px; font-weight: 700; color: var(--text-tertiary); margin-top: 6px;">Not available</div>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Run a scan to evaluate 14 site rules</div>
                        `}
                    </div>

                    <!-- BOX 4: PROBLEMS FOUND -->
                    <div class="card kpi-card-clickable" id="kpi-problems-found" tabindex="0" role="button" aria-label="Go to Problems We Found Table"
                         style="padding: 20px; background: var(--bg-card); cursor: pointer; transition: all 0.2s ease; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase; font-weight: 700; display: flex; justify-content: space-between; align-items: center;">
                            <span>Problems Found ${renderTooltip('Total technical problems detected. Click to view table findings.')}</span>
                            <span style="font-size: 10px; color: var(--primary); font-weight: 600;">Table ↓</span>
                        </div>
                        ${hasCrawl ? `
                            <div style="font-size: 28px; font-weight: 700; color: var(--critical); margin-top: 4px;">${allIssues.length}</div>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${summary.critical_errors || 0} critical, ${summary.warnings || 0} warnings</div>
                        ` : `
                            <div style="font-size: 20px; font-weight: 700; color: var(--text-tertiary); margin-top: 6px;">No audit data yet</div>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">0 critical, 0 warnings</div>
                        `}
                    </div>
                </div>

                <!-- WHAT WE CHECKED: CATEGORY CARDS GRID -->
                <div style="margin-bottom: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">What We Checked</h3>
                            ${this.selectedCategoryFilter !== 'all' ? `
                                <span class="badge badge-primary" style="font-size: 11.5px; text-transform: none; cursor: pointer;" id="btn-reset-category-filter">
                                    Filter: ${this.escapeHtml(catTranslations[this.selectedCategoryFilter] || this.selectedCategoryFilter)} ✕
                                </span>
                            ` : ''}
                        </div>
                        ${renderSourceBadge('crawl')}
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px;">
                        ${categoryCardsHtml}
                    </div>
                </div>

                <!-- PROBLEMS WE FOUND TABLE -->
                <div class="card" id="problems-we-found-section" style="padding: 0; overflow: hidden; border-radius: 14px; transition: box-shadow 0.3s ease;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">
                            Problems We Found ${this.selectedCategoryFilter !== 'all' ? `(${filteredIssues.length} of ${allIssues.length})` : `(${allIssues.length})`}
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
                    <div id="technical-pagination-slot"></div>
                </div>
            `;

            // Append Pagination Controls
            const pageSlot = container.querySelector('#technical-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: filteredIssues.length,
                    currentPage: this.issuesPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.issuesPage = newPage;
                        this.mounted();
                    }
                });
                pageSlot.appendChild(pag.render());
            }

            // BIND KPI BOX CLICK EVENTS
            document.getElementById('kpi-health-score')?.addEventListener('click', () => {
                HealthScoreDetailModal.open({
                    health,
                    summary,
                    totalAuditedPages,
                    htmlPagesCount,
                    blockedPagesCount,
                    evaluatedRulesCount: auditData.evaluated_rules_count || 14,
                    totalChecks,
                    categoryTable,
                    crawlTimestamp,
                    domain: selectedProj.domain
                });
            });

            document.getElementById('kpi-pages-scanned')?.addEventListener('click', () => {
                window.location.hash = '#/pages';
            });

            document.getElementById('kpi-checks-performed')?.addEventListener('click', () => {
                ChecksPerformedDetailModal.open({
                    totalAuditedPages,
                    htmlPagesCount,
                    evaluatedRulesCount: auditData.evaluated_rules_count || 14,
                    totalChecks,
                    checksExplanation,
                    categoryTable,
                    domain: selectedProj.domain,
                    onSelectCategory: (cat) => {
                        this.selectedCategoryFilter = cat;
                        this.issuesPage = 1;
                        this.mounted();
                        setTimeout(() => {
                            const section = document.getElementById('problems-we-found-section');
                            if (section) section.scrollIntoView({ behavior: 'smooth' });
                        }, 50);
                    }
                });
            });

            document.getElementById('kpi-problems-found')?.addEventListener('click', () => {
                this.selectedCategoryFilter = 'all';
                this.issuesPage = 1;
                this.mounted();
                setTimeout(() => {
                    const section = document.getElementById('problems-we-found-section');
                    if (section) {
                        section.scrollIntoView({ behavior: 'smooth' });
                        section.style.boxShadow = '0 0 0 2px var(--primary)';
                        setTimeout(() => { section.style.boxShadow = 'none'; }, 1500);
                    }
                }, 50);
            });

            // Bind Category Card Click Events (FILTER / REVEAL INTERACTION)
            container.querySelectorAll('.category-card-item').forEach(card => {
                card.addEventListener('click', (e) => {
                    const cat = e.currentTarget.getAttribute('data-category');
                    if (this.selectedCategoryFilter.toLowerCase() === cat.toLowerCase()) {
                        this.selectedCategoryFilter = 'all';
                    } else {
                        this.selectedCategoryFilter = cat;
                    }
                    this.issuesPage = 1;
                    this.mounted();
                });
            });

            // Bind Filter Reset Badge Click Event
            document.getElementById('btn-reset-category-filter')?.addEventListener('click', () => {
                this.selectedCategoryFilter = 'all';
                this.issuesPage = 1;
                this.mounted();
            });

            // Bind Evidence Modal Triggers
            container.querySelectorAll('.btn-open-evidence-modal').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const globalIdx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                    const iss = filteredIssues[globalIdx];
                    if (iss) {
                        AuditEvidenceModal.open({
                            projectId: projectStore.getSelectedProjectId(),
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
