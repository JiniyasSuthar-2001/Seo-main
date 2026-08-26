import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { renderAIBadge, renderSourceBadge } from '../components/AIBadge.js';
import { AuditEvidenceModal } from '../components/AuditEvidenceModal.js';
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

            const auditData = await apiClient.get(`/api/projects/${projectId}/technical?limit=500&offset=0`);

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

            // Render Category Cards (RESTORED CARD-BASED UI WITH RIGHT COLORED STATUS LINE)
            const categoryCardsHtml = categoryTable.map(c => {
                const plainCatName = catTranslations[c.category] || c.category;
                const isSelected = this.selectedCategoryFilter.toLowerCase() === c.category.toLowerCase() || 
                                   this.selectedCategoryFilter.toLowerCase() === plainCatName.toLowerCase();

                let rightLineColor = 'var(--success, #10b981)'; // Green default
                if (c.issues_count > 0 || c.status === 'Issues Found') {
                    if (c.critical > 0 || c.error > 0) {
                        rightLineColor = 'var(--critical, #ef4444)'; // Red for critical/errors
                    } else {
                        rightLineColor = 'var(--warning, #f59e0b)'; // Yellow/orange for warnings
                    }
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
                                <span style="color: var(--success);"><strong>${c.passed || 0}</strong> passed</span>
                            </div>
                            <div style="font-size: 11.5px; margin-top: 4px; font-weight: 600; color: ${c.issues_count > 0 ? (c.critical > 0 ? 'var(--critical)' : 'var(--warning)') : 'var(--text-tertiary)'};">
                                ${c.issues_count > 0 ? `${c.issues_count} problem${c.issues_count === 1 ? '' : 's'}` : '✓ Passed'}
                            </div>
                        </div>
                        <!-- COLORED STATUS LINE ON RIGHT SIDE -->
                        <div style="position: absolute; right: 0; top: 0; bottom: 0; width: 5px; background: ${rightLineColor}; border-top-right-radius: 9px; border-bottom-right-radius: 9px;"></div>
                    </div>
                `;
            }).join('');

            // Table Rows for Findings (Problems We Found) - PAGINATED TO MAXIMUM 20 ROWS PER PAGE
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
                <!-- TOP SUMMARY KPI BAR (RESTORED AND RETAINED) -->
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

                <!-- WHAT WE CHECKED: RESTORED CLICKABLE CATEGORY CARDS GRID -->
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

                <!-- PROBLEMS WE FOUND TABLE (UNTOUCHED STRUCTURE & EVIDENCE SYSTEM, PAGINATED AT 20 ROWS) -->
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
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

            // Bind Category Card Click Events (FILTER / REVEAL INTERACTION)
            container.querySelectorAll('.category-card-item').forEach(card => {
                card.addEventListener('click', (e) => {
                    const cat = e.currentTarget.getAttribute('data-category');
                    if (this.selectedCategoryFilter.toLowerCase() === cat.toLowerCase()) {
                        this.selectedCategoryFilter = 'all'; // Toggle off if clicking active category
                    } else {
                        this.selectedCategoryFilter = cat;
                    }
                    this.issuesPage = 1; // Reset to page 1 on category filter change
                    this.mounted();
                });
            });

            // Bind Filter Reset Badge Click Event
            document.getElementById('btn-reset-category-filter')?.addEventListener('click', () => {
                this.selectedCategoryFilter = 'all';
                this.issuesPage = 1; // Reset to page 1
                this.mounted();
            });

            // Bind Evidence Modal Triggers (UNTOUCHED EVIDENCE MODAL)
            container.querySelectorAll('.btn-open-evidence-modal').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const globalIdx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                    const iss = filteredIssues[globalIdx];
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
