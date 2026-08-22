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
        alert("Backend API unavailable. Please ensure the server is running on http://127.0.0.1:8020.");
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
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                this.element.innerHTML = `
                    <div class="card" style="padding: 40px; text-align: center;">
                        <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">No SEO Project Selected</h2>
                        <p style="color: var(--text-secondary); margin-bottom: 20px;">Select an existing workspace from the header dropdown or create your first project to get started.</p>
                        <button class="btn btn-primary" onclick="window.showCreateProjectModal()">+ Add New Project</button>
                    </div>
                `;
                return;
            }

            // Fetch summary metrics & crawl history
            const summary = await dashboardService.getSummary(projectId);
            const history = await crawlService.getCrawlHistory(projectId);
            const competitorsRes = await apiClient.get(`/api/projects/${projectId}/competitors?status=Confirmed`);
            const confirmedCompetitors = Array.isArray(competitorsRes) ? competitorsRes : [];

            const targetUrl = selectedProj.domain || selectedProj.url || 'http://127.0.0.1:8020';
            const hasCrawled = summary.latest_crawl && summary.latest_crawl.pages_crawled > 0;

            if (!hasCrawled) {
                // ELEGANT UNCRAWLED OVERVIEW STATE
                this.element.innerHTML = `
                    <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">SEO OVERVIEW WORKSPACE</div>
                            <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px;">${selectedProj.name}</h1>
                            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">Target Website: <strong style="color: var(--text-primary);">${targetUrl}</strong></div>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <button class="btn btn-secondary btn-sm" onclick="window.location.reload()">Refresh</button>
                            <button class="btn btn-primary btn-sm" onclick="window.startCrawl()">Run Crawl</button>
                        </div>
                    </div>

                    <!-- UNCRAWLED KPI GRID -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px;">
                        <div class="kpi-card" style="border-left: 4px solid var(--border);">
                            <div class="kpi-label">SEO Health</div>
                            <div class="kpi-value" style="color: var(--text-tertiary);">-- / 100</div>
                            <div class="kpi-status">No crawl data</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Organic Visibility</div>
                            <div class="kpi-value" style="font-size: 14px; color: var(--text-secondary); line-height: 1.4;">Connect Search Console</div>
                            <div class="kpi-status">GSC Integration</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Ranking Keywords</div>
                            <div class="kpi-value" style="font-size: 14px; color: var(--text-secondary);">No data available</div>
                            <div class="kpi-status">Rank Tracker</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Top 10 Keywords</div>
                            <div class="kpi-value" style="font-size: 14px; color: var(--text-secondary);">No data available</div>
                            <div class="kpi-status">Rank Tracker</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Backlinks</div>
                            <div class="kpi-value" style="font-size: 14px; color: var(--text-secondary);">No data available</div>
                            <div class="kpi-status">Import Dataset</div>
                        </div>
                        <div class="kpi-card">
                            <div class="kpi-label">Referring Domains</div>
                            <div class="kpi-value" style="font-size: 14px; color: var(--text-secondary);">No data available</div>
                            <div class="kpi-status">Import Dataset</div>
                        </div>
                    </div>

                    <!-- EMPTY CRAWL ACTION CARD -->
                    <div class="empty-state" style="padding: 40px 24px; text-align: center; background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 32px;">
                        <div class="empty-state-icon" style="margin-bottom: 12px;">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--primary)" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                        </div>
                        <h2 style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">Run First Crawl Analysis</h2>
                        <p style="color: var(--text-secondary); font-size: 14px; max-width: 540px; margin: 0 auto 20px; line-height: 1.5;">
                            Start a website crawl to calculate your SEO Health score, discover audited pages, extract HTML meta tags, identify technical findings, and map your link architecture for <strong>${targetUrl}</strong>.
                        </p>
                        
                        <div style="display: flex; gap: 12px; justify-content: center; max-width: 440px; margin: 0 auto 16px;">
                            <input id="project-url" type="url" value="${targetUrl}" style="flex: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: var(--bg-workspace); color: var(--text-primary);">
                            <button class="btn btn-primary" onclick="window.startCrawl()">Start Crawl</button>
                        </div>

                        <div id="crawl-progress" style="display: none; margin: 24px auto 0; max-width: 440px; text-align: left;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px;">
                                <span>Crawling...</span>
                                <span id="crawl-stats">0 pages</span>
                            </div>
                            <div style="width: 100%; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden;">
                                <div id="crawl-bar" style="width: 0%; height: 100%; background: var(--primary); transition: width 0.3s ease;"></div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                // FULL SEMRUSH-STYLE SEO OVERVIEW DASHBOARD
                const crawl = summary.latest_crawl;
                
                // Fetch technical audit issues for Health Score calculation & Priority Issues list
                const techRes = await apiClient.get(`/api/projects/${projectId}/technical?limit=100`);
                const issues = techRes.issues || techRes || [];

                const criticalCount = issues.filter(i => (i.severity === 'critical' || i.severity === 'error')).length;
                const warningCount = issues.filter(i => i.severity === 'warning').length;
                const noticeCount = issues.filter(i => i.severity === 'notice' || i.severity === 'info').length;
                
                const totalCrawledPages = crawl.pages_crawled || 1;
                const totalChecks = totalCrawledPages * 5; // 5 core checks per page
                const totalFailed = criticalCount * 2 + warningCount;
                const passedChecks = Math.max(0, totalChecks - totalFailed);
                const healthScore = Math.min(100, Math.max(0, Math.round((passedChecks / totalChecks) * 100)));

                let healthColor = 'var(--success, #10b981)';
                if (healthScore < 70) healthColor = 'var(--critical, #ef4444)';
                else if (healthScore < 85) healthColor = 'var(--warning, #f59e0b)';

                // Sort Priority Issues by (1) Critical impact, (2) Affected pages count, (3) Severity
                const sortedIssues = [...issues].sort((a, b) => {
                    const sevScore = (i) => (i.severity === 'critical' || i.severity === 'error') ? 3 : (i.severity === 'warning' ? 2 : 1);
                    const scoreA = sevScore(a);
                    const scoreB = sevScore(b);
                    if (scoreA !== scoreB) return scoreB - scoreA;
                    const pagesA = a.affected_pages_count || (a.affected_pages ? a.affected_pages.length : 1);
                    const pagesB = b.affected_pages_count || (b.affected_pages ? b.affected_pages.length : 1);
                    return pagesB - pagesA;
                });

                // Priority issues table markup
                let priorityIssuesHtml = '';
                if (sortedIssues.length === 0) {
                    priorityIssuesHtml = `
                        <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 14px;">
                            ✓ Zero technical SEO issues detected across ${totalCrawledPages} audited pages.
                        </div>
                    `;
                } else {
                    const topIssues = sortedIssues.slice(0, 5);
                    const issueRows = topIssues.map(issue => {
                        const isCritical = (issue.severity === 'critical' || issue.severity === 'error');
                        const sevBadgeClass = isCritical ? 'badge-critical' : (issue.severity === 'warning' ? 'badge-warning' : 'badge-info');
                        const sevText = isCritical ? 'CRITICAL' : (issue.severity === 'warning' ? 'WARNING' : 'NOTICE');
                        const pagesCount = issue.affected_pages_count || (issue.affected_pages ? issue.affected_pages.length : 1);
                        const impactText = isCritical ? 'HIGH' : (issue.severity === 'warning' ? 'MEDIUM' : 'LOW');
                        const impactColor = isCritical ? 'var(--critical, #ef4444)' : (issue.severity === 'warning' ? 'var(--warning, #f59e0b)' : 'var(--text-secondary)');

                        return `
                            <tr style="border-bottom: 1px solid var(--border);">
                                <td style="padding: 12px 16px;">
                                    <span class="badge ${sevBadgeClass}" style="font-size: 10px; font-weight: 700;">${sevText}</span>
                                </td>
                                <td style="padding: 12px 16px; font-weight: 600; color: var(--text-primary);">
                                    ${issue.title || issue.issue_type || 'Technical Audit Issue'}
                                </td>
                                <td style="padding: 12px 16px; font-size: 13px; color: var(--text-secondary);">
                                    ${pagesCount} ${pagesCount === 1 ? 'page' : 'pages'}
                                </td>
                                <td style="padding: 12px 16px; font-weight: 700; font-size: 12px; color: ${impactColor};">
                                    ${impactText}
                                </td>
                                <td style="padding: 12px 16px; text-align: right;">
                                    <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 12px;">View details &rarr;</a>
                                </td>
                            </tr>
                        `;
                    }).join('');

                    priorityIssuesHtml = `
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;">
                                    <th style="padding: 10px 16px;">Severity</th>
                                    <th style="padding: 10px 16px;">Issue Title</th>
                                    <th style="padding: 10px 16px;">Affected Pages</th>
                                    <th style="padding: 10px 16px;">Impact</th>
                                    <th style="padding: 10px 16px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${issueRows}
                            </tbody>
                        </table>
                    `;
                }

                // Confirmed Competitors snapshot markup
                let competitorsSnapshotHtml = '';
                if (confirmedCompetitors.length === 0) {
                    competitorsSnapshotHtml = `
                        <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                            <div style="margin-bottom: 8px; font-weight: 600; color: var(--text-primary);">No Confirmed Competitors Configured</div>
                            <p style="margin-bottom: 16px; max-width: 480px; margin-left: auto; margin-right: auto;">Add confirmed competitors in the Competitors view to compare keyword overlaps and backlink metrics.</p>
                            <a href="/competitors" data-link class="btn btn-secondary btn-sm">+ Add Confirmed Competitors</a>
                        </div>
                    `;
                } else {
                    const compRows = confirmedCompetitors.slice(0, 4).map(c => `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 12px 16px; font-weight: 600;">${c.name}</td>
                            <td style="padding: 12px 16px; font-family: monospace; font-size: 12px;">${c.domain}</td>
                            <td style="padding: 12px 16px;">${c.location || 'Regional'}</td>
                            <td style="padding: 12px 16px; font-weight: 700; color: var(--primary);">${c.relevance_score || 0}%</td>
                            <td style="padding: 12px 16px; text-align: right;"><span class="badge badge-success">Confirmed</span></td>
                        </tr>
                    `).join('');

                    competitorsSnapshotHtml = `
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 10px 16px;">Competitor</th>
                                    <th style="padding: 10px 16px;">Domain</th>
                                    <th style="padding: 10px 16px;">Location</th>
                                    <th style="padding: 10px 16px;">Relevance</th>
                                    <th style="padding: 10px 16px; text-align: right;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${compRows}
                            </tbody>
                        </table>
                    `;
                }

                // AI Insights section
                let aiInsightsHtml = '';
                try {
                    const aiRes = await aiService.getInsights(selectedProj.id);
                    if (aiRes.insights && aiRes.insights.length > 0) {
                        let cards = aiRes.insights.map(ins => `
                            <div class="card" style="padding: 16px 20px; border-left: 4px solid var(--primary);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <span style="font-weight: 600; font-size: 14px;">${ins.finding}</span>
                                    <span class="badge badge-info" style="font-size: 10px;">
                                        AI Confidence: ${(ins.confidence * 100).toFixed(0)}%
                                    </span>
                                </div>
                                <p style="font-size: 13px; color: var(--text-primary); margin-bottom: 8px;">${ins.impact}</p>
                                <div style="font-size: 12px; color: var(--text-secondary); background: var(--bg-subtle); padding: 8px 12px; border-radius: 6px;">
                                    <strong>AI Recommendation:</strong> ${ins.recommendation}
                                </div>
                            </div>
                        `).join('');
                        
                        aiInsightsHtml = `
                            <div style="margin-top: 24px;">
                                <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 12px;">Structured AI SEO Insights</h2>
                                <div style="display: flex; flex-direction: column; gap: 12px;">
                                    ${cards}
                                </div>
                            </div>
                        `;
                    }
                } catch (aierr) {}

                this.element.innerHTML = `
                    <!-- DASHBOARD HEADER TOOLBAR -->
                    <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">SEO OVERVIEW WORKSPACE</div>
                            <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px;">${selectedProj.name}</h1>
                            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">
                                Domain: <strong style="color: var(--text-primary);">${crawl.website || targetUrl}</strong>
                                &nbsp;•&nbsp; Snapshot Date: <strong>${crawl.timestamp || 'Recent'}</strong>
                            </div>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <button class="btn btn-secondary btn-sm" onclick="window.location.reload()">Refresh Data</button>
                            <a href="${API_BASE_URL}/api/projects/${selectedProj.id}/report.pdf" target="_blank" class="btn btn-secondary btn-sm">PDF Executive Report</a>
                            <button class="btn btn-primary btn-sm" onclick="window.startCrawl()">Run Crawl</button>
                        </div>
                    </div>

                    <!-- 6 PRIMARY KPI CARDS (WITH CLICKABLE REAL HEALTH SCORE CARD) -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 16px; margin-bottom: 28px;">
                        
                        <!-- SEO HEALTH CARD (CLICK NAVIGATES TO TECHNICAL AUDIT) -->
                        <a href="/technical" data-link class="kpi-card interactive-kpi" style="border-left: 4px solid ${healthColor};">
                            <div class="kpi-header"><span class="kpi-label">SEO Health</span></div>
                            <div class="kpi-value" style="color: ${healthColor};">${healthScore} <span style="font-size: 14px; font-weight: 500; color: var(--text-secondary);">/ 100</span></div>
                            <div class="kpi-status" style="font-size: 11px;">
                                <span style="color: var(--critical); font-weight: 700;">${criticalCount} Errors</span> &nbsp;•&nbsp;
                                <span style="color: var(--warning); font-weight: 600;">${warningCount} Warn</span> &nbsp;•&nbsp;
                                <span style="color: var(--success); font-weight: 600;">${passedChecks} Pass</span>
                            </div>
                        </a>

                        <div class="kpi-card">
                            <div class="kpi-header"><span class="kpi-label">Organic Visibility</span></div>
                            <div class="kpi-value" style="font-size: 13px; color: var(--text-secondary); line-height: 1.4; margin-top: 4px;">Connect Search Console to calculate</div>
                            <div class="kpi-status"><a href="/settings" data-link style="color: var(--primary); text-decoration: none;">Connect GSC &rarr;</a></div>
                        </div>

                        <a href="/keywords" data-link class="kpi-card interactive-kpi">
                            <div class="kpi-header"><span class="kpi-label">Ranking Keywords</span></div>
                            <div class="kpi-value">${selectedProj.keywords_count || crawl.keywords_count || 0}</div>
                            <div class="kpi-status">Tracked dataset &rarr;</div>
                        </a>

                        <a href="/rankings" data-link class="kpi-card interactive-kpi">
                            <div class="kpi-header"><span class="kpi-label">Top 10 Keywords</span></div>
                            <div class="kpi-value">${selectedProj.top10_count || 0}</div>
                            <div class="kpi-status">Page 1 positions &rarr;</div>
                        </a>

                        <a href="/backlinks" data-link class="kpi-card interactive-kpi">
                            <div class="kpi-header"><span class="kpi-label">Backlinks</span></div>
                            <div class="kpi-value">${selectedProj.backlinks_count || 0}</div>
                            <div class="kpi-status">External links &rarr;</div>
                        </a>

                        <a href="/pages" data-link class="kpi-card interactive-kpi">
                            <div class="kpi-header"><span class="kpi-label">Crawled Pages</span></div>
                            <div class="kpi-value">${crawl.pages_crawled}</div>
                            <div class="kpi-status">Audited inventory &rarr;</div>
                        </a>
                    </div>

                    <!-- PRIORITY ISSUES & OPPORTUNITIES PREVIEW (2-COLUMN GRID) -->
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 20px; margin-bottom: 28px;">
                        
                        <!-- PRIORITY ISSUES CONTAINER -->
                        <div class="card" style="padding: 0; overflow: hidden;">
                            <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h3 style="font-size: 15px; font-weight: 700;">Priority Audit Issues</h3>
                                    <div style="font-size: 11px; color: var(--text-secondary);">Sorted by Critical Impact & Affected Page Count</div>
                                </div>
                                <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View All Issues</a>
                            </div>
                            ${priorityIssuesHtml}
                        </div>

                        <!-- OPPORTUNITIES PREVIEW CONTAINER -->
                        <div class="card" style="padding: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                                <div>
                                    <h3 style="font-size: 15px; font-weight: 700;">SEO Growth Opportunities</h3>
                                    <div style="font-size: 11px; color: var(--text-secondary);">Actionable Optimization Recommendations</div>
                                </div>
                                <a href="/opportunities" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Open Opportunities Hub</a>
                            </div>

                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                <div style="padding: 12px 14px; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: 600; font-size: 13px; color: var(--text-primary);">Technical Audit Fixes</div>
                                        <div style="font-size: 12px; color: var(--text-secondary);">${criticalCount} critical errors & ${warningCount} warnings require attention.</div>
                                    </div>
                                    <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Fix &rarr;</a>
                                </div>

                                <div style="padding: 12px 14px; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: 600; font-size: 13px; color: var(--text-primary);">Content & Meta Tag Optimization</div>
                                        <div style="font-size: 12px; color: var(--text-secondary);">Review crawled pages missing HTML title tags or meta descriptions.</div>
                                    </div>
                                    <a href="/pages" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Audit Pages &rarr;</a>
                                </div>

                                <div style="padding: 12px 14px; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: 600; font-size: 13px; color: var(--text-primary);">Internal Link Graph Optimization</div>
                                        <div style="font-size: 12px; color: var(--text-secondary);">${crawl.internal_links_count || 0} internal links mapped across audited pages.</div>
                                    </div>
                                    <a href="/internal-links" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View Graph &rarr;</a>
                                </div>
                            </div>
                        </div>

                    </div>

                    <!-- CONFIRMED COMPETITOR SNAPSHOT -->
                    <div class="card" style="padding: 0; overflow: hidden; margin-bottom: 28px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700;">Confirmed Competitors Snapshot</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Verified Market Competitors for ${selectedProj.name}</div>
                            </div>
                            <a href="/competitors" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Manage Competitors</a>
                        </div>
                        ${competitorsSnapshotHtml}
                    </div>

                    <!-- TREND & CRAWL HISTORY AREA -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700;">Crawl History & Snapshot Progression</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Audit snapshot timeline for ${crawl.website || targetUrl}</div>
                            </div>
                            <a href="/crawl-history" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Full History</a>
                        </div>

                        ${Array.isArray(history) && history.length > 1 ? `
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                ${history.slice(0, 4).map(h => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-subtle); border-radius: 6px; font-size: 13px;">
                                        <div>
                                            <strong style="color: var(--text-primary);">${h.timestamp || 'Crawl Snapshot'}</strong>
                                            <span style="color: var(--text-secondary); margin-left: 12px;">${h.pages_crawled || 0} pages audited</span>
                                        </div>
                                        <div>
                                            <span class="badge badge-info">${h.total_issues || 0} issues</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        ` : `
                            <div style="padding: 20px; background: var(--bg-subtle); border-radius: 8px; font-size: 13px; color: var(--text-secondary); text-align: center;">
                                ℹ️ Historical trend tracking requires running multiple website crawls over time or connecting Google Search Console integration.
                            </div>
                        `}
                    </div>

                    ${aiInsightsHtml}

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
            }

        } catch (e) {
            if (e.isNetworkError || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, "Unable to connect to backend API server at http://127.0.0.1:8020.", () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "SEO Overview Error", e.message || "Failed to load SEO overview metrics.", () => this.mounted());
            }
        }
    }
}
