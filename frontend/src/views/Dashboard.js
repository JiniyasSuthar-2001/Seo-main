import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { aiService } from '../services/aiService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { crawlProgressOverlay } from '../components/CrawlProgressOverlay.js';

window.startCrawl = async () => {
    const selectedProj = projectStore.getSelectedProject();
    const urlInput = document.getElementById('project-url');
    const url = urlInput ? urlInput.value : (selectedProj ? selectedProj.domain || selectedProj.url : null);
    
    if (!url) {
        alert("Please enter a valid website URL to crawl.");
        return;
    }

    const progressDiv = document.getElementById('crawl-progress');
    if (progressDiv) progressDiv.style.display = 'block';
    
    try {
        const projectId = selectedProj ? selectedProj.id : null;
        const data = await crawlService.startCrawl(projectId, url);
        
        crawlProgressOverlay.start(projectId, data.session_id, url);

        const interval = setInterval(async () => {
            try {
                const statusData = await crawlService.getCrawlStatus(projectId, data.session_id);
                
                const statsEl = document.getElementById('crawl-stats');
                if (statsEl) statsEl.innerText = `${statusData.pages_crawled} / ${statusData.pages_discovered} pages`;
                
                if (statusData.pages_discovered > 0) {
                    const barEl = document.getElementById('crawl-bar');
                    if (barEl) barEl.style.width = `${(statusData.pages_crawled / statusData.pages_discovered) * 100}%`;
                }
                
                if (statusData.status === 'completed') {
                    clearInterval(interval);
                    const statsEl = document.getElementById('crawl-stats');
                    if (statsEl) statsEl.innerText = "Crawl Complete!";
                    const barEl = document.getElementById('crawl-bar');
                    if (barEl) barEl.style.backgroundColor = 'var(--success)';
                } else if (statusData.status === 'failed') {
                    clearInterval(interval);
                    if (progressDiv) progressDiv.style.display = 'none';
                }
            } catch (pollError) {
                console.error("Status polling failed:", pollError);
                clearInterval(interval);
            }
        }, 1000);
        
    } catch(e) {
        alert(`Backend API unavailable. Please ensure the server is running on ${API_BASE_URL}.`);
    }
};

export class Dashboard {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'dashboard-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                Loading SEO Overview Workspace...
            </div>
        `;
        return this.element;
    }

    async mounted() {
        try {
            await projectStore.ensureInitialized();

            let selectedProj = projectStore.getSelectedProject();
            let projectId = projectStore.getSelectedProjectId();

            if ((!projectId || !selectedProj) && projectStore.projects && projectStore.projects.length > 0) {
                projectStore.setSelectedProjectId(projectStore.projects[0].id);
                selectedProj = projectStore.getSelectedProject();
                projectId = projectStore.getSelectedProjectId();
            }

            if (!projectId || !selectedProj) {
                this.element.innerHTML = `
                    <div class="card" style="padding: 40px; text-align: center;">
                        <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">No SEO Project Selected</h2>
                        <p style="color: var(--text-secondary); margin-bottom: 20px;">Select an existing workspace from the header dropdown or create your first project to get started.</p>
                        <button class="btn btn-primary" onclick="window.showCreateProjectModal()">+ Add New Project</button>
                    </div>
                `;
                return;
            }


            // Fetch primary project data, technical audit, crawl history, and opportunities
            const summary = await dashboardService.getSummary(projectId);
            const history = await crawlService.getCrawlHistory(projectId);
            
            let techRes = { issues: [], category_breakdown: {}, health_score: 100 };
            try {
                techRes = await apiClient.get(`/api/projects/${projectId}/technical?limit=100`);
            } catch (e) {}

            let opportunities = [];
            try {
                const oppRes = await apiClient.get(`/api/projects/${projectId}/opportunities`);
                opportunities = oppRes.opportunities || oppRes || [];
            } catch (e) {}

            let keywordsData = [];
            try {
                const kwRes = await apiClient.get(`/api/projects/${projectId}/keywords`);
                keywordsData = Array.isArray(kwRes) ? kwRes : (kwRes.keywords || []);
            } catch (e) {}

            let backlinksData = [];
            try {
                const blRes = await apiClient.get(`/api/projects/${projectId}/backlinks`);
                backlinksData = Array.isArray(blRes) ? blRes : (blRes.backlinks || []);
            } catch (e) {}

            const targetUrl = selectedProj.domain || selectedProj.url || "unconfigured_domain";
            const crawl = summary.latest_crawl || {};
            const hasCrawled = summary.status === 'success' && crawl.pages_crawled > 0;

            const healthScore = techRes.health_score !== undefined ? techRes.health_score : (hasCrawled ? 85 : null);
            let healthColor = 'var(--success, #10b981)';
            if (healthScore !== null) {
                if (healthScore < 70) healthColor = 'var(--critical, #ef4444)';
                else if (healthScore < 85) healthColor = 'var(--warning, #f59e0b)';
            }

            const issues = techRes.issues || [];
            const summaryStats = techRes.summary || {};
            const criticalCount = summaryStats.critical_errors || issues.filter(i => i.severity === 'critical' || i.severity === 'error').length;
            const warningCount = summaryStats.warnings || issues.filter(i => i.severity === 'warning').length;
            const noticeCount = summaryStats.notices || issues.filter(i => i.severity === 'notice' || i.severity === 'info').length;

            // Categories Breakdown HTML
            const categories = techRes.category_breakdown || {};
            let categoriesGridHtml = '';
            if (Object.keys(categories).length > 0) {
                categoriesGridHtml = Object.entries(categories).map(([catName, stats]) => {
                    const isEvaluated = stats.evaluated !== false;
                    const totalIssues = (stats.critical || 0) + (stats.error || 0) + (stats.warning || 0) + (stats.notice || 0);

                    let statusText = "Passed";
                    let badgeBg = "rgba(16, 185, 129, 0.15)";
                    let statusColor = "#10b981";

                    if (!isEvaluated) {
                        statusText = "Not analyzed";
                        badgeBg = "var(--bg-subtle)";
                        statusColor = "var(--text-tertiary)";
                    } else if (totalIssues > 0 || stats.status === "Issues Found") {
                        statusText = `${totalIssues} issue${totalIssues === 1 ? '' : 's'}`;
                        badgeBg = "rgba(239, 68, 68, 0.15)";
                        statusColor = "#ef4444";
                    }

                    return `
                        <div class="card" style="padding: 14px; font-size: 13px; background: var(--bg-card);">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-weight: 600; color: var(--text-primary);">${catName}</span>
                                <span style="font-size: 11px; font-weight: 700; color: ${statusColor}; background: ${badgeBg}; padding: 2px 8px; border-radius: 12px;">${statusText}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-tertiary);">
                                ${isEvaluated ? `Crit: ${stats.critical + stats.error} • Warn: ${stats.warning} • Pass: ${stats.passed}` : (stats.reason || 'Unevaluated check')}
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // Priority Issues Table HTML
            let topIssuesHtml = '';
            if (issues.length === 0) {
                topIssuesHtml = `
                    <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                        ${hasCrawled ? `✓ Zero critical technical SEO issues detected across ${crawl.pages_crawled || 0} pages.` : 'No crawl analysis available yet.'}
                    </div>
                `;
            } else {
                const topIssues = issues.slice(0, 5);
                const rows = topIssues.map(iss => {
                    const isCrit = iss.severity === 'critical' || iss.severity === 'error';
                    const badgeClass = isCrit ? 'badge-critical' : (iss.severity === 'warning' ? 'badge-warning' : 'badge-info');
                    const urlCount = (iss.affected_urls || []).length || 1;
                    return `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 10px 16px;"><span class="badge ${badgeClass}">${(iss.severity || 'notice').toUpperCase()}</span></td>
                            <td style="padding: 10px 16px; font-weight: 600;">${iss.title}</td>
                            <td style="padding: 10px 16px; font-size: 12px; color: var(--text-secondary); font-family: monospace;">${urlCount} URLs</td>
                            <td style="padding: 10px 16px; font-weight: 700; color: ${isCrit ? '#ef4444' : '#f59e0b'};">${isCrit ? 'HIGH' : 'MEDIUM'}</td>
                            <td style="padding: 10px 16px; text-align: right;"><a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View details &rarr;</a></td>
                        </tr>
                    `;
                }).join('');

                topIssuesHtml = `
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 16px;">Severity</th>
                                <th style="padding: 10px 16px;">Issue Title</th>
                                <th style="padding: 10px 16px;">Affected URLs</th>
                                <th style="padding: 10px 16px;">Impact</th>
                                <th style="padding: 10px 16px; text-align: right;">Action</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                `;
            }

            // Keyword Snapshot Calculations
            let kwSnapshotHtml = '';
            if (keywordsData.length > 0) {
                const totalKw = keywordsData.length;
                const pos1_3 = keywordsData.filter(k => (k.position || 999) <= 3).length;
                const pos4_10 = keywordsData.filter(k => (k.position || 999) >= 4 && (k.position || 999) <= 10).length;
                const pos11_20 = keywordsData.filter(k => (k.position || 999) >= 11 && (k.position || 999) <= 20).length;
                const pos21_50 = keywordsData.filter(k => (k.position || 999) >= 21 && (k.position || 999) <= 50).length;
                const pos51_plus = keywordsData.filter(k => (k.position || 999) > 50).length;

                kwSnapshotHtml = `
                    <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-top: 12px;">
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Total Keywords</div>
                            <div style="font-size: 18px; font-weight: 700; color: var(--primary);">${totalKw}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Pos 1–3</div>
                            <div style="font-size: 18px; font-weight: 700; color: #10b981;">${pos1_3}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Pos 4–10</div>
                            <div style="font-size: 18px; font-weight: 700; color: #3b82f6;">${pos4_10}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Pos 11–20</div>
                            <div style="font-size: 18px; font-weight: 700; color: #f59e0b;">${pos11_20}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Pos 21–50</div>
                            <div style="font-size: 18px; font-weight: 700; color: #8b5cf6;">${pos21_50}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Pos 51+</div>
                            <div style="font-size: 18px; font-weight: 700; color: var(--text-secondary);">${pos51_plus}</div>
                        </div>
                    </div>
                `;
            } else {
                kwSnapshotHtml = `
                    <div style="padding: 20px; text-align: center; color: var(--text-secondary); background: var(--bg-subtle); border-radius: 8px; font-size: 13px;">
                        No keyword data imported yet. <a href="/import" data-link style="color: var(--primary); font-weight: 600;">Import Keywords CSV &rarr;</a>
                    </div>
                `;
            }

            // Backlinks Snapshot Calculations
            let blSnapshotHtml = '';
            if (backlinksData.length > 0) {
                const totalBl = backlinksData.length;
                const refDomains = new Set(backlinksData.map(b => b.source_domain || b.domain)).size;
                const dofollow = backlinksData.filter(b => (b.follow_status || b.type || '').toLowerCase().includes('dofollow')).length;
                const nofollow = backlinksData.filter(b => (b.follow_status || b.type || '').toLowerCase().includes('nofollow')).length;

                blSnapshotHtml = `
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px;">
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Total Backlinks</div>
                            <div style="font-size: 18px; font-weight: 700; color: var(--primary);">${totalBl}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Referring Domains</div>
                            <div style="font-size: 18px; font-weight: 700; color: #10b981;">${refDomains}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Dofollow Links</div>
                            <div style="font-size: 18px; font-weight: 700; color: #3b82f6;">${dofollow}</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; color: var(--text-secondary);">Nofollow Links</div>
                            <div style="font-size: 18px; font-weight: 700; color: var(--text-secondary);">${nofollow}</div>
                        </div>
                    </div>
                `;
            } else {
                blSnapshotHtml = `
                    <div style="padding: 20px; text-align: center; color: var(--text-secondary); background: var(--bg-subtle); border-radius: 8px; font-size: 13px;">
                        No backlink data imported yet. <a href="/import" data-link style="color: var(--primary); font-weight: 600;">Import Backlinks CSV &rarr;</a>
                    </div>
                `;
            }

            // Main Workspace Assembly
            this.element.innerHTML = `
                <!-- TOP HEADER & DOMAIN SUMMARY -->
                <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">SEO OVERVIEW WORKSPACE</div>
                        <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px; color: var(--text-primary);">${selectedProj.name}</h1>
                        <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap;">
                            <span>Target Domain: <strong style="color: var(--text-primary);">${targetUrl}</strong></span>
                            <span>Last Crawl: <strong style="color: var(--text-primary);">${crawl.timestamp || 'Not crawled yet'}</strong></span>
                            <span class="badge ${hasCrawled ? 'badge-success' : 'badge-info'}" style="font-size: 11px;">
                                ${hasCrawled ? 'Crawled' : 'Not Crawled'}
                            </span>
                        </div>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <a href="/crawl-history" data-link class="btn btn-secondary btn-sm">Crawl History</a>
                        <a href="${API_BASE_URL}/api/projects/${selectedProj.id}/report.pdf" target="_blank" class="btn btn-secondary btn-sm">PDF Executive Report</a>
                        <button class="btn btn-primary btn-sm" onclick="window.startCrawl()">Run Crawl</button>
                    </div>
                </div>

                <!-- SECTION 1 — SEO HEALTH SUMMARY KPI CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 28px;">
                    <a href="/technical" data-link class="kpi-card interactive-kpi" style="border-left: 4px solid ${healthColor || 'var(--border)'};">
                        <div class="kpi-label">SEO Health Score</div>
                        <div class="kpi-value" style="color: ${healthColor || 'var(--text-primary)'};">${healthScore !== null ? healthScore : '—'} <span style="font-size: 13px; color: var(--text-secondary);">/ 100</span></div>
                        <div class="kpi-status">${healthScore !== null ? `${criticalCount} Errors • ${warningCount} Warn` : 'No crawl data'}</div>
                    </a>

                    <a href="/pages" data-link class="kpi-card interactive-kpi">
                        <div class="kpi-label">Crawled Pages</div>
                        <div class="kpi-value">${hasCrawled ? (crawl.pages_crawled || 0) : '—'}</div>
                        <div class="kpi-status">${hasCrawled ? 'Audited inventory' : 'Not crawled'}</div>
                    </a>

                    <a href="/technical" data-link class="kpi-card interactive-kpi">
                        <div class="kpi-label">Total Issues</div>
                        <div class="kpi-value">${hasCrawled ? (summaryStats.total_issues !== undefined ? summaryStats.total_issues : issues.length) : '—'}</div>
                        <div class="kpi-status">${hasCrawled ? 'Audit findings' : 'No crawl data'}</div>
                    </a>

                    <div class="kpi-card">
                        <div class="kpi-label">Critical Errors</div>
                        <div class="kpi-value" style="color: var(--critical);">${hasCrawled ? criticalCount : '—'}</div>
                        <div class="kpi-status">${hasCrawled ? 'High priority fixes' : 'No crawl data'}</div>
                    </div>

                    <a href="/keywords" data-link class="kpi-card interactive-kpi">
                        <div class="kpi-label">Organic Keywords</div>
                        <div class="kpi-value">${keywordsData.length > 0 ? keywordsData.length : (selectedProj.keywords_count || '—')}</div>
                        <div class="kpi-status">${keywordsData.length > 0 ? 'Tracked keywords' : 'No data'}</div>
                    </a>

                    <a href="/backlinks" data-link class="kpi-card interactive-kpi">
                        <div class="kpi-label">Backlinks</div>
                        <div class="kpi-value">${backlinksData.length > 0 ? backlinksData.length : (selectedProj.backlinks_count || '—')}</div>
                        <div class="kpi-status">${backlinksData.length > 0 ? 'External backlinks' : 'No data'}</div>
                    </a>
                </div>

                <!-- SECTION 2 — TECHNICAL SEO SUMMARY GRID -->
                <div class="card" style="padding: 20px; margin-bottom: 28px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <div>
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0;">15-Category Technical SEO Summary</h3>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Evaluated deterministic rule breakdown (Unevaluated checks marked 'Not analyzed')</div>
                        </div>
                        <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Open Technical Workspace</a>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 12px;">
                        ${categoriesGridHtml || '<div style="font-size: 13px; color: var(--text-secondary); text-align: center; grid-column: 1/-1; padding: 16px;">Run a website crawl to evaluate 15 technical audit categories.</div>'}
                    </div>
                </div>

                <!-- SECTION 3 & 4 — TOP ISSUES & CRAWL SUMMARY GRID -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 20px; margin-bottom: 28px;">
                    
                    <!-- SECTION 3: TOP SEO ISSUES -->
                    <div class="card" style="padding: 0; overflow: hidden;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Top Priority Technical Issues</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Sorted by Critical Impact</div>
                            </div>
                            <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View All &rarr;</a>
                        </div>
                        ${topIssuesHtml}
                    </div>

                    <!-- SECTION 4: CRAWL SUMMARY -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Crawl Inventory Summary</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Audited pages HTTP status distribution</div>
                            </div>
                            <a href="/pages" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Audited Pages &rarr;</a>
                        </div>

                        ${hasCrawled ? `
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                                <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 11px; color: var(--text-secondary);">Crawled Pages</div>
                                    <div style="font-size: 18px; font-weight: 700; color: var(--text-primary);">${crawl.pages_crawled || 0}</div>
                                </div>
                                <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 11px; color: var(--text-secondary);">4xx / 5xx Broken</div>
                                    <div style="font-size: 18px; font-weight: 700; color: #ef4444;">${criticalCount}</div>
                                </div>
                                <div style="background: var(--bg-subtle); padding: 12px; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 11px; color: var(--text-secondary);">Warnings</div>
                                    <div style="font-size: 18px; font-weight: 700; color: #f59e0b;">${warningCount}</div>
                                </div>
                            </div>
                        ` : `
                            <div style="padding: 24px; text-align: center; color: var(--text-secondary); background: var(--bg-subtle); border-radius: 8px; font-size: 13px;">
                                No crawl inventory data available yet. Start a crawl to inspect page status codes.
                            </div>
                        `}
                    </div>

                </div>

                <!-- SECTION 5 & 6 — OPPORTUNITIES & KEYWORD SNAPSHOT GRID -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 20px; margin-bottom: 28px;">
                    
                    <!-- SECTION 5: SEO GROWTH OPPORTUNITIES -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">SEO Growth Opportunities</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Actionable rank expansion recommendations</div>
                            </div>
                            <a href="/opportunities" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Opportunities Hub</a>
                        </div>
                        ${opportunities.length > 0 ? `
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                ${opportunities.slice(0, 3).map(o => `
                                    <div style="padding: 10px 12px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px;">
                                        <strong style="color: var(--text-primary);">${o.title || o.issue || 'SEO Opportunity'}</strong>
                                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${o.recommendation || o.action || ''}</div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div style="padding: 20px; text-align: center; color: var(--text-secondary); background: var(--bg-subtle); border-radius: 8px; font-size: 13px;">
                                No SEO opportunities available from the current dataset.
                            </div>
                        `}
                    </div>

                    <!-- SECTION 6: KEYWORD SNAPSHOT -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Keyword Ranking Distribution</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Position breakdown across search engine results</div>
                            </div>
                            <a href="/keywords" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Keywords Hub</a>
                        </div>
                        ${kwSnapshotHtml}
                    </div>

                </div>

                <!-- SECTION 7 & 8 — BACKLINK SNAPSHOT & CRAWL HISTORY GRID -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 20px; margin-bottom: 28px;">
                    
                    <!-- SECTION 7: BACKLINK SNAPSHOT -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Backlinks & Referring Domains</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">External link architecture profile</div>
                            </div>
                            <a href="/backlinks" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Backlinks Workspace</a>
                        </div>
                        ${blSnapshotHtml}
                    </div>

                    <!-- SECTION 8: RECENT CRAWL HISTORY -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Recent Crawl History</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Audit snapshot timeline</div>
                            </div>
                            <a href="/crawl-history" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Full History</a>
                        </div>

                        ${Array.isArray(history) && history.length > 0 ? `
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                ${history.slice(0, 3).map(h => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px;">
                                        <div>
                                            <strong style="color: var(--text-primary);">${h.timestamp || 'Crawl Snapshot'}</strong>
                                            <span style="color: var(--text-secondary); margin-left: 10px;">${h.pages_crawled || 0} pages</span>
                                        </div>
                                        <div><span class="badge badge-info">${h.total_issues || 0} issues</span></div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div style="padding: 20px; text-align: center; color: var(--text-secondary); background: var(--bg-subtle); border-radius: 8px; font-size: 13px;">
                                No crawl history snapshots recorded yet.
                            </div>
                        `}
                    </div>

                </div>

                <!-- SECTION 9 — QUICK ACTIONS NAV GRID -->
                <div class="card" style="padding: 20px; margin-bottom: 24px;">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0 0 14px 0;">SEO Workspace Quick Actions</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 12px;">
                        <button class="btn btn-primary btn-sm" onclick="window.startCrawl()" style="padding: 10px;">Run Crawl</button>
                        <a href="/technical" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">Technical Audit</a>
                        <a href="/pages" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">Crawled Pages</a>
                        <a href="/keywords" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">View Keywords</a>
                        <a href="/rankings" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">View Rankings</a>
                        <a href="/backlinks" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">View Backlinks</a>
                        <a href="/opportunities" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">Opportunities</a>
                        <a href="/reports" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">Reports Hub</a>
                        <a href="/import" data-link class="btn btn-secondary btn-sm" style="padding: 10px; text-align: center;">Import Data</a>
                    </div>
                </div>

                <style>
                    .interactive-kpi {
                        text-decoration: none;
                        display: block;
                        transition: all 0.2s ease;
                    }
                    .interactive-kpi:hover {
                        transform: translateY(-2px);
                        border-color: var(--primary) !important;
                        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15);
                    }
                </style>
            `;

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "SEO Overview Error", e.message || "Failed to load SEO overview metrics.", () => this.mounted());
            }
        }
    }
}
