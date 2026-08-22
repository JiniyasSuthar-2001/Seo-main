import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { crawlProgressOverlay } from '../components/CrawlProgressOverlay.js';

window.startCrawl = async (explicitProjectId, explicitUrl) => {
    let targetId = explicitProjectId || projectStore.getSelectedProjectId();
    let selectedProj = projectStore.getSelectedProject();

    if (explicitProjectId && projectStore.projects) {
        const found = projectStore.projects.find(p => String(p.id) === String(explicitProjectId));
        if (found) {
            selectedProj = found;
            targetId = found.id;
            projectStore.setSelectedProjectId(found.id);
        }
    }

    const urlInput = document.getElementById('project-url');
    const url = explicitUrl || (urlInput ? urlInput.value : (selectedProj ? selectedProj.domain || selectedProj.url : null));
    
    if (!url) {
        alert("Please enter a valid website URL to crawl.");
        return;
    }

    const progressDiv = document.getElementById('crawl-progress');
    if (progressDiv) progressDiv.style.display = 'block';
    
    try {
        const data = await crawlService.startCrawl(targetId, url);
        crawlProgressOverlay.start(targetId, data.session_id, url);

        const interval = setInterval(async () => {
            try {
                const statusData = await crawlService.getCrawlStatus(targetId, data.session_id);
                
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
        alert(`Backend API error: ${e.message || 'Unable to start crawl.'}`);
    }
};

window.navigateToAudit = (projectId) => {
    if (projectId) {
        projectStore.setSelectedProjectId(projectId);
    }
    window.location.href = '/technical';
};

export class Dashboard {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'dashboard-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                Loading Workspace Overview...
            </div>
        `;
        return this.element;
    }

    async mounted() {
        try {
            await projectStore.ensureInitialized();

            const overviewData = await dashboardService.getWorkspaceOverview();
            const summary = overviewData.workspace_summary || {};
            const projects = overviewData.projects || [];
            const recentCrawls = overviewData.recent_crawls || [];
            const accountIssues = overviewData.account_issues_summary || [];

            // Account-level empty state if zero websites exist
            if (!projects || projects.length === 0) {
                this.element.innerHTML = `
                    <div class="header" style="margin-bottom: 24px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ACCOUNT WORKSPACE</div>
                        <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px;">SEO Intelligence Overview</h1>
                    </div>
                    <div class="card" style="padding: 48px 24px; text-align: center; max-width: 560px; margin: 32px auto;">
                        <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(37, 99, 235, 0.1); color: var(--primary); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                        </div>
                        <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 8px;">No Websites in Workspace Yet</h2>
                        <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; line-height: 1.5;">Add your first website domain to begin workspace-wide technical audits, ranking tracking, and SEO health monitoring.</p>
                        <button class="btn btn-primary" onclick="window.showCreateProjectModal()">+ Add Website</button>
                    </div>
                `;
                return;
            }

            const avgHealth = summary.average_health;
            let avgHealthColor = 'var(--success, #10b981)';
            if (avgHealth !== null) {
                if (avgHealth < 70) avgHealthColor = 'var(--critical, #ef4444)';
                else if (avgHealth < 85) avgHealthColor = 'var(--warning, #f59e0b)';
            }

            // Portfolio Websites Grid Cards HTML
            const projectCardsHtml = projects.map(p => {
                const health = p.health_score;
                let hColor = 'var(--text-tertiary)';
                let hBadgeClass = 'badge-info';
                let hText = 'No Crawl';

                if (health !== null && health !== undefined) {
                    if (health >= 85) { hColor = 'var(--success, #10b981)'; hBadgeClass = 'badge-success'; hText = `${health} / 100`; }
                    else if (health >= 70) { hColor = 'var(--warning, #f59e0b)'; hBadgeClass = 'badge-warning'; hText = `${health} / 100`; }
                    else { hColor = 'var(--critical, #ef4444)'; hBadgeClass = 'badge-critical'; hText = `${health} / 100`; }
                }

                const targetUrl = p.domain || p.url || 'unconfigured';

                return `
                    <div class="card website-portfolio-card" style="padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">${p.name}</h3>
                                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 220px;" title="${targetUrl}">
                                        ${targetUrl}
                                    </div>
                                </div>
                                <span class="badge ${hBadgeClass}" style="font-size: 11px; font-weight: 700;">${hText}</span>
                            </div>

                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 16px 0; background: var(--bg-subtle); padding: 10px; border-radius: 8px; text-align: center;">
                                <div>
                                    <div style="font-size: 10px; color: var(--text-secondary); text-transform: uppercase;">Pages</div>
                                    <div style="font-size: 15px; font-weight: 700; color: var(--text-primary);">${p.pages_crawled || 0}</div>
                                </div>
                                <div>
                                    <div style="font-size: 10px; color: var(--text-secondary); text-transform: uppercase;">Critical</div>
                                    <div style="font-size: 15px; font-weight: 700; color: var(--critical, #ef4444);">${p.critical_issues || 0}</div>
                                </div>
                                <div>
                                    <div style="font-size: 10px; color: var(--text-secondary); text-transform: uppercase;">Warnings</div>
                                    <div style="font-size: 15px; font-weight: 700; color: var(--warning, #f59e0b);">${p.warnings || 0}</div>
                                </div>
                            </div>
                        </div>

                        <div style="display: flex; gap: 8px; margin-top: 12px; pt: 12px; border-top: 1px solid var(--border);">
                            <button class="btn btn-secondary btn-sm" style="flex: 1; font-size: 12px;" onclick="window.startCrawl('${p.id}', '${targetUrl}')">Run Crawl</button>
                            <button class="btn btn-primary btn-sm" style="flex: 1; font-size: 12px;" onclick="window.navigateToAudit('${p.id}')">View Audit &rarr;</button>
                        </div>
                    </div>
                `;
            }).join('');

            // Account-Wide Issues Summary HTML
            let issuesTableHtml = '';
            if (!accountIssues || accountIssues.length === 0) {
                issuesTableHtml = `
                    <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                        ✓ Zero aggregated critical technical issues across workspace websites.
                    </div>
                `;
            } else {
                const issueRows = accountIssues.map(iss => {
                    const isCrit = iss.severity === 'critical' || iss.severity === 'error';
                    const badgeClass = isCrit ? 'badge-critical' : (iss.severity === 'warning' ? 'badge-warning' : 'badge-info');

                    return `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 10px 16px;"><span class="badge ${badgeClass}">${iss.severity.toUpperCase()}</span></td>
                            <td style="padding: 10px 16px; font-weight: 600;">${iss.title}</td>
                            <td style="padding: 10px 16px; font-size: 12px;">${iss.affected_websites_count} website${iss.affected_websites_count === 1 ? '' : 's'}</td>
                            <td style="padding: 10px 16px; font-family: monospace; font-size: 12px; color: var(--text-secondary);">${iss.total_urls_count} URLs</td>
                            <td style="padding: 10px 16px; text-align: right;"><a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View in Audit &rarr;</a></td>
                        </tr>
                    `;
                }).join('');

                issuesTableHtml = `
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 16px;">Severity</th>
                                <th style="padding: 10px 16px;">Issue Title</th>
                                <th style="padding: 10px 16px;">Affected Websites</th>
                                <th style="padding: 10px 16px;">Total Affected URLs</th>
                                <th style="padding: 10px 16px; text-align: right;">Action</th>
                            </tr>
                        </thead>
                        <tbody>${issueRows}</tbody>
                    </table>
                `;
            }

            // Portfolio Recent Crawls HTML
            let crawlsListHtml = '';
            if (!recentCrawls || recentCrawls.length === 0) {
                crawlsListHtml = `
                    <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                        No recent crawl history snapshots recorded across workspace websites.
                    </div>
                `;
            } else {
                crawlsListHtml = recentCrawls.slice(0, 5).map(c => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-subtle); border-radius: 8px; font-size: 13px; margin-bottom: 8px;">
                        <div>
                            <strong style="color: var(--text-primary);">${c.project_name || 'Website'}</strong>
                            <span style="color: var(--text-secondary); margin-left: 8px; font-size: 12px;">(${c.domain || 'domain'})</span>
                            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Snapshot: ${c.timestamp || 'Recent'}</div>
                        </div>
                        <div style="display: flex; gap: 12px; align-items: center;">
                            <span style="font-size: 12px; color: var(--text-secondary);">${c.pages_crawled || 0} pages</span>
                            <span class="badge badge-info">${c.total_issues || 0} issues</span>
                            <button class="btn btn-secondary btn-sm" onclick="window.navigateToAudit('${c.project_id}')" style="font-size: 11px;">Audit &rarr;</button>
                        </div>
                    </div>
                `).join('');
            }

            // Main Workspace Portfolio Markup
            this.element.innerHTML = `
                <!-- WORKSPACE HEADER & SUMMARY -->
                <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ACCOUNT WORKSPACE</div>
                        <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px; color: var(--text-primary);">SEO Portfolio Overview</h1>
                        <p style="color: var(--text-secondary); font-size: 13px; margin-top: 2px;">
                            Managing <strong>${summary.total_projects || 0}</strong> websites • <strong>${summary.active_projects || 0}</strong> active audited sites across your SEO suite.
                        </p>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-secondary btn-sm" onclick="window.location.reload()">Refresh Overview</button>
                        <button class="btn btn-primary btn-sm" onclick="window.showCreateProjectModal()">+ Add Website</button>
                    </div>
                </div>

                <!-- 4 WORKSPACE SUMMARY KPI CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px;">
                    <div class="kpi-card">
                        <div class="kpi-label">Total Managed Websites</div>
                        <div class="kpi-value" style="color: var(--primary);">${summary.total_projects || 0}</div>
                        <div class="kpi-status">${summary.active_projects || 0} active audited</div>
                    </div>

                    <div class="kpi-card">
                        <div class="kpi-label">Audited Pages</div>
                        <div class="kpi-value">${summary.total_pages_crawled || 0}</div>
                        <div class="kpi-status">Across portfolio</div>
                    </div>

                    <div class="kpi-card" style="border-left: 4px solid ${avgHealthColor};">
                        <div class="kpi-label">Portfolio Avg Health</div>
                        <div class="kpi-value" style="color: ${avgHealthColor};">${avgHealth !== null ? avgHealth : '—'} <span style="font-size: 13px; color: var(--text-secondary);">/ 100</span></div>
                        <div class="kpi-status">${avgHealth !== null ? 'Evaluated score' : 'No crawl data'}</div>
                    </div>

                    <div class="kpi-card">
                        <div class="kpi-label">Aggregate Critical Errors</div>
                        <div class="kpi-value" style="color: var(--critical, #ef4444);">${summary.critical_issues || 0}</div>
                        <div class="kpi-status">${summary.warnings || 0} warnings</div>
                    </div>
                </div>

                <!-- SECTION 1: ALL WEBSITES PORTFOLIO GRID -->
                <div style="margin-bottom: 32px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <div>
                            <h2 style="font-size: 18px; font-weight: 700; margin: 0;">Portfolio Websites (${projects.length})</h2>
                            <div style="font-size: 12px; color: var(--text-secondary);">Individual site health, audited inventory, and quick crawl actions</div>
                        </div>
                        <button class="btn btn-secondary btn-sm" onclick="window.showCreateProjectModal()">+ Add Website</button>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
                        ${projectCardsHtml}
                    </div>
                </div>

                <!-- SECTION 2 & 3: ACCOUNT-WIDE ISSUES & RECENT CRAWLS GRID -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(440px, 1fr)); gap: 20px; margin-bottom: 28px;">
                    
                    <!-- ACCOUNT-WIDE ISSUES SUMMARY -->
                    <div class="card" style="padding: 0; overflow: hidden;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Account-Wide Technical Issues</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Aggregated across portfolio websites</div>
                            </div>
                            <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View Audits</a>
                        </div>
                        ${issuesTableHtml}
                    </div>

                    <!-- PORTFOLIO RECENT CRAWLS -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Recent Portfolio Crawls</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Audit snapshot timeline</div>
                            </div>
                            <a href="/crawl-history" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Crawl History</a>
                        </div>
                        ${crawlsListHtml}
                    </div>

                </div>
            `;

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "Workspace Overview Error", e.message || "Failed to load workspace overview metrics.", () => this.mounted());
            }
        }
    }
}
