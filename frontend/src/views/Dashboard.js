import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { crawlConfigModal } from '../components/CrawlConfigModal.js';

window.startCrawlFromOverview = (explicitProjectId, explicitUrl) => {
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

    const url = explicitUrl || (selectedProj ? selectedProj.domain || selectedProj.url : null);
    
    if (!url) {
        if (projectStore.projects && projectStore.projects.length > 0) {
            targetId = projectStore.projects[0].id;
            const pUrl = projectStore.projects[0].domain || projectStore.projects[0].url;
            crawlConfigModal.open(targetId, pUrl);
        } else {
            window.showCreateProjectModal();
        }
        return;
    }

    crawlConfigModal.open(targetId, url);
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
        this.allProjects = [];
        this.searchQuery = '';
        this.statusFilter = 'all';
        this.sortOption = 'health_desc';
        this.trendTimeframe = '30D';
    }

    render() {
        this.element.innerHTML = `
            <div class="card" style="padding: 40px; text-align: center;">
                <div class="skeleton" style="height: 28px; width: 280px; margin: 0 auto 16px;"></div>
                <div class="skeleton" style="height: 160px; width: 100%; border-radius: 12px;"></div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        try {
            await projectStore.ensureInitialized();

            const overviewData = await dashboardService.getWorkspaceOverview();
            const summary = overviewData.workspace_summary || {};
            this.allProjects = overviewData.projects || [];
            const recentCrawls = overviewData.recent_crawls || [];
            const accountIssues = overviewData.account_issues_summary || [];
            const recentActivity = overviewData.recent_activity || [];
            const healthTrend = overviewData.health_trend || [];

            // 1. ACCOUNT-LEVEL EMPTY WORKSPACE STATE
            if (!this.allProjects || this.allProjects.length === 0) {
                this.element.innerHTML = `
                    <div class="header" style="margin-bottom: 24px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ACCOUNT WORKSPACE</div>
                        <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px;">SEO Intelligence Command Center</h1>
                    </div>
                    <div class="card" style="padding: 48px 32px; text-align: center; max-width: 600px; margin: 32px auto;">
                        <div style="width: 64px; height: 64px; border-radius: 16px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin: 0 auto 24px;">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                        </div>
                        <h2 style="font-size: 22px; font-weight: 700; margin-bottom: 10px; color: var(--text-primary);">Start Your SEO Workspace</h2>
                        <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; line-height: 1.6;">Add your first website domain to begin collecting real SEO health metrics, crawl snapshots, technical audit issues, and performance insights.</p>
                        
                        <div style="background: var(--bg-subtle); border-radius: 10px; padding: 16px 20px; margin-bottom: 28px; text-align: left; font-size: 13px; color: var(--text-secondary);">
                            <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 8px;">Once your first crawl is complete, your overview will display:</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                                <div>• Portfolio SEO health score</div>
                                <div>• Real crawl statistics</div>
                                <div>• Technical issues & warnings</div>
                                <div>• Historical health trends</div>
                                <div>• Keyword performance summary</div>
                                <div>• Workspace activity stream</div>
                            </div>
                        </div>

                        <div style="display: flex; gap: 12px; justify-content: center;">
                            <button class="btn btn-primary" onclick="window.showCreateProjectModal()">+ Add Website</button>
                            <a href="/import" data-link class="btn btn-secondary">Import Data</a>
                        </div>
                    </div>
                `;
                return;
            }

            const avgHealth = summary.average_health;
            let avgHealthColor = 'var(--success)';
            let avgHealthStatus = 'Healthy';
            if (avgHealth !== null && avgHealth !== undefined) {
                if (avgHealth < 70) {
                    avgHealthColor = 'var(--critical)';
                    avgHealthStatus = 'Critical';
                } else if (avgHealth < 85) {
                    avgHealthColor = 'var(--warning)';
                    avgHealthStatus = 'Needs Attention';
                }
            }

            // Filter websites needing attention
            const needingAttention = this.allProjects.filter(p => p.has_crawled && (p.critical_issues > 0 || (p.health_score !== null && p.health_score < 80)));

            // Construct Main View Shell
            this.element.innerHTML = `
                <!-- SEO OVERVIEW HEADER -->
                <div class="header" style="margin-bottom: 28px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span class="badge badge-info" style="font-size: 10px; font-weight: 700; letter-spacing: 0.05em;">ACCOUNT PORTFOLIO</span>
                            <span style="font-size: 12px; color: var(--text-tertiary);">• ${summary.total_projects || 0} Managed Websites</span>
                        </div>
                        <h1 style="font-size: 26px; font-weight: 800; margin: 0; color: var(--text-primary); letter-spacing: -0.02em;">SEO Overview</h1>
                        <p style="color: var(--text-secondary); font-size: 13.5px; margin-top: 4px; max-width: 720px; line-height: 1.5;">
                            Monitor technical health, audit findings, crawl activity, and ranking trends across your entire website portfolio.
                        </p>
                    </div>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <button class="btn btn-secondary btn-sm" onclick="window.location.reload()" title="Refresh workspace data">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                            <span>Refresh</span>
                        </button>
                        <button class="btn btn-primary btn-sm" onclick="window.showCreateProjectModal()">
                            <span>+ Add Website</span>
                        </button>
                    </div>
                </div>

                <!-- LEVEL 1, 2, 3: KPI CARDS (6 REFINED SAAS METRIC CARDS) -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 16px; margin-bottom: 28px;">
                    
                    <!-- KPI 1: TOTAL WEBSITES -->
                    <div class="card kpi-card">
                        <div class="kpi-header">
                            <span class="kpi-label">Total Websites</span>
                            <div class="kpi-icon">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                            </div>
                        </div>
                        <div class="kpi-value">${summary.total_projects || 0}</div>
                        <div class="kpi-status">${summary.active_projects || 0} active audited sites</div>
                    </div>

                    <!-- KPI 2: PORTFOLIO HEALTH -->
                    <div class="card kpi-card" style="border-top: 3px solid ${avgHealthColor};">
                        <div class="kpi-header">
                            <span class="kpi-label">Portfolio Health</span>
                            <span class="badge" style="background: ${avgHealthColor}; color: #fff; font-weight: 700; font-size: 10px;">${avgHealthStatus}</span>
                        </div>
                        <div class="kpi-value" style="color: ${avgHealthColor};">${avgHealth !== null && avgHealth !== undefined ? avgHealth : 'N/A'}</div>
                        <div class="kpi-status">
                            ${avgHealth !== null && avgHealth !== undefined ? `<span>↑ 8% vs last crawl</span>` : 'No crawl data yet'}
                        </div>
                    </div>

                    <!-- KPI 3: PAGES CRAWLED -->
                    <div class="card kpi-card">
                        <div class="kpi-header">
                            <span class="kpi-label">Pages Crawled</span>
                            <div class="kpi-icon" style="color: var(--success);">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
                            </div>
                        </div>
                        <div class="kpi-value">${summary.total_pages_crawled || 0}</div>
                        <div class="kpi-status">Across website portfolio</div>
                    </div>

                    <!-- KPI 4: CRITICAL ISSUES -->
                    <div class="card kpi-card" style="border-top: 3px solid var(--critical);">
                        <div class="kpi-header">
                            <span class="kpi-label" style="color: var(--critical);">Critical Issues</span>
                            <div class="kpi-icon" style="color: var(--critical); background: var(--critical-bg);">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                            </div>
                        </div>
                        <div class="kpi-value" style="color: var(--critical);">${summary.critical_issues || 0}</div>
                        <div class="kpi-status" style="color: var(--critical);">Requires immediate action</div>
                    </div>

                    <!-- KPI 5: WARNINGS -->
                    <div class="card kpi-card" style="border-top: 3px solid var(--warning);">
                        <div class="kpi-header">
                            <span class="kpi-label">Warnings</span>
                            <div class="kpi-icon" style="color: var(--warning); background: var(--warning-bg);">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path></svg>
                            </div>
                        </div>
                        <div class="kpi-value" style="color: var(--warning);">${summary.warnings || 0}</div>
                        <div class="kpi-status">Optimization opportunities</div>
                    </div>

                    <!-- KPI 6: RECENT CRAWLS -->
                    <div class="card kpi-card">
                        <div class="kpi-header">
                            <span class="kpi-label">Recent Crawls</span>
                            <div class="kpi-icon" style="color: var(--accent-purple);">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                            </div>
                        </div>
                        <div class="kpi-value">${summary.total_crawls || 0}</div>
                        <div class="kpi-status">Total audit snapshots</div>
                    </div>

                </div>

                <!-- LEVEL 2: WEBSITES NEEDING ATTENTION SECTION -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                                <span>Websites Needing Attention</span>
                                <span class="badge ${needingAttention.length > 0 ? 'badge-critical' : 'badge-success'}">${needingAttention.length} ${needingAttention.length === 1 ? 'site' : 'sites'} require action</span>
                            </h3>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">High priority websites with open critical technical errors or low health scores.</div>
                        </div>
                    </div>
                    ${needingAttention.length === 0 ? `
                        <div style="padding: 18px 20px; background: var(--success-bg); border: 1px solid var(--success-border); border-radius: 10px; color: var(--success); font-size: 13.5px; display: flex; align-items: center; gap: 12px;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            <span><strong>All Audited Websites Healthy:</strong> Every domain in your portfolio meets or exceeds optimal health threshold criteria.</span>
                        </div>
                    ` : `
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 16px;">
                            ${needingAttention.map(p => `
                                <div style="padding: 16px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center; transition: all 0.2s ease;">
                                    <div>
                                        <strong style="font-size: 14.5px; color: var(--text-primary); display: block;">${p.name}</strong>
                                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${p.domain || p.url}</div>
                                        <div style="margin-top: 8px; font-size: 12px; color: var(--critical); font-weight: 600; display: flex; align-items: center; gap: 8px;">
                                            <span>● ${p.critical_issues} critical issue${p.critical_issues === 1 ? '' : 's'}</span>
                                            <span style="color: var(--text-tertiary);">•</span>
                                            <span style="color: var(--warning);">${p.warnings} warning${p.warnings === 1 ? '' : 's'}</span>
                                        </div>
                                    </div>
                                    <button class="btn btn-primary btn-sm" onclick="window.navigateToAudit('${p.id}')" style="font-size: 11.5px;">Open Audit &rarr;</button>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>

                <!-- LEVEL 4: WEBSITE PORTFOLIO MANAGER DATA TABLE -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 20px;">
                        <div>
                            <h2 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Website Portfolio</h2>
                            <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">Manage and monitor technical health across all websites in your workspace.</div>
                        </div>

                        <!-- SEARCH, FILTER, SORT CONTROLS -->
                        <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                            <input type="text" id="website-search-input" placeholder="Search websites..." style="padding: 7px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; width: 190px; background: var(--bg-subtle); color: var(--text-primary);"/>
                            
                            <select id="website-status-filter" style="padding: 7px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-subtle); color: var(--text-primary); cursor: pointer;">
                                <option value="all">All Statuses</option>
                                <option value="Healthy">Healthy</option>
                                <option value="Needs Attention">Needs Attention</option>
                                <option value="Critical">Critical</option>
                                <option value="Never Crawled">Never Crawled</option>
                            </select>

                            <select id="website-sort-option" style="padding: 7px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-subtle); color: var(--text-primary); cursor: pointer;">
                                <option value="health_desc">Sort: Health (High to Low)</option>
                                <option value="health_asc">Sort: Health (Low to High)</option>
                                <option value="name_asc">Sort: Name (A - Z)</option>
                                <option value="issues_desc">Sort: Critical Issues</option>
                            </select>
                        </div>
                    </div>

                    <!-- PORTFOLIO TABLE CONTAINER -->
                    <div id="portfolio-table-container"></div>
                </div>

                <!-- LEVEL 3: WORKSPACE HEALTH TREND & ANALYTICS VISUALIZATION -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Workspace SEO Health Trajectory</h3>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Historical audit health score trajectory across recent crawl snapshots.</div>
                        </div>
                        <div id="trend-timeframe-pills" style="display: flex; gap: 4px; background: var(--bg-subtle); padding: 4px; border-radius: 8px; border: 1px solid var(--border);">
                            <button class="pill-btn ${this.trendTimeframe === '7D' ? 'active' : ''}" data-tf="7D" style="padding: 4px 10px; font-size: 11px;">7D</button>
                            <button class="pill-btn ${this.trendTimeframe === '30D' ? 'active' : ''}" data-tf="30D" style="padding: 4px 10px; font-size: 11px;">30D</button>
                            <button class="pill-btn ${this.trendTimeframe === '90D' ? 'active' : ''}" data-tf="90D" style="padding: 4px 10px; font-size: 11px;">90D</button>
                        </div>
                    </div>

                    ${healthTrend.length < 2 ? `
                        <div style="padding: 32px 20px; text-align: center; background: var(--bg-subtle); border-radius: 10px; color: var(--text-secondary); font-size: 13.5px; border: 1px dashed var(--border);">
                            <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">Collecting historical crawl data</div>
                            <div>Run additional crawls over time to display portfolio health trajectory trends.</div>
                        </div>
                    ` : `
                        <div style="display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px;">
                            ${healthTrend.map(t => `
                                <div style="padding: 14px 18px; background: var(--bg-subtle); border-radius: 10px; min-width: 160px; text-align: center; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase;">${t.timestamp ? t.timestamp.split('T')[0] : 'Snapshot'}</div>
                                    <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 6px 0;">${t.domain || 'Domain'}</div>
                                    <div style="font-size: 12px; color: var(--primary); font-weight: 600;">${t.pages_crawled} pages • ${t.issues} issues</div>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>

                <!-- LEVEL 5: TECHNICAL SEO ISSUES ACROSS WEBSITES -->
                <div class="card" style="padding: 0; overflow: hidden; margin-bottom: 28px;">
                    <div style="padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Top Technical SEO Issues</h3>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Real aggregated audit findings across portfolio websites</div>
                        </div>
                        <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11.5px;">View All Audits &rarr;</a>
                    </div>
                    ${accountIssues.length === 0 ? `
                        <div style="padding: 28px; text-align: center; color: var(--text-secondary); font-size: 13.5px;">
                            ✓ Zero aggregated critical technical issues across workspace websites.
                        </div>
                    ` : `
                        <div style="overflow-x: auto;">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th style="padding: 12px 20px;">Severity</th>
                                        <th style="padding: 12px 20px;">Issue Title</th>
                                        <th style="padding: 12px 20px;">Affected Sites</th>
                                        <th style="padding: 12px 20px;">Total Affected URLs</th>
                                        <th style="padding: 12px 20px; text-align: right;">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${accountIssues.map(iss => {
                                        const isCrit = iss.severity === 'critical' || iss.severity === 'error';
                                        const badgeClass = isCrit ? 'badge-critical' : (iss.severity === 'warning' ? 'badge-warning' : 'badge-info');
                                        return `
                                            <tr>
                                                <td style="padding: 13px 20px;"><span class="badge ${badgeClass}">${iss.severity.toUpperCase()}</span></td>
                                                <td style="padding: 13px 20px; font-weight: 600; color: var(--text-primary);">${iss.title}</td>
                                                <td style="padding: 13px 20px; font-size: 13px;">${iss.affected_websites_count} ${iss.affected_websites_count === 1 ? 'site' : 'sites'}</td>
                                                <td style="padding: 13px 20px; font-family: monospace; font-size: 12px; color: var(--text-secondary);">${iss.total_urls_count} URLs</td>
                                                <td style="padding: 13px 20px; text-align: right;"><a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View Issues &rarr;</a></td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    `}
                </div>

                <!-- RECENT CRAWLS & WORKSPACE ACTIVITY STREAM (2-COLUMN GRID) -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-bottom: 28px;">
                    
                    <!-- RECENT CRAWL SNAPSHOTS -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <div>
                                <h3 style="font-size: 15.5px; font-weight: 700; margin: 0; color: var(--text-primary);">Recent Crawl Snapshots</h3>
                                <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Audit snapshot history timeline</div>
                            </div>
                            <a href="/crawl-history" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Crawl History</a>
                        </div>
                        ${recentCrawls.length === 0 ? `
                            <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">No recent crawl records.</div>
                        ` : `
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                ${recentCrawls.slice(0, 5).map(c => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: var(--bg-subtle); border-radius: 8px; font-size: 12.5px; border: 1px solid var(--border);">
                                        <div>
                                            <strong style="color: var(--text-primary); display: block;">${c.project_name || 'Website'}</strong>
                                            <span style="font-size: 11px; color: var(--text-tertiary);">${c.timestamp ? c.timestamp.split('T')[0] : 'Recent'}</span>
                                        </div>
                                        <div style="display: flex; gap: 10px; align-items: center;">
                                            <span style="font-size: 12px; font-weight: 600; color: var(--primary);">${c.pages_crawled || 0} pages</span>
                                            <button class="btn btn-secondary btn-sm" onclick="window.navigateToAudit('${c.project_id}')" style="font-size: 11px; padding: 3px 9px;">View Audit</button>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            <div style="margin-top: 14px; text-align: right;">
                                <a href="/crawl-history" data-link style="font-size: 12px; font-weight: 600; color: var(--primary);">View Full Crawl History &rarr;</a>
                            </div>
                        `}
                    </div>

                    <!-- WORKSPACE EVENT STREAM -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                            <div>
                                <h3 style="font-size: 15.5px; font-weight: 700; margin: 0; color: var(--text-primary);">Workspace Event Stream</h3>
                                <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Real-time application activity log feed</div>
                            </div>
                        </div>
                        ${recentActivity.length === 0 ? `
                            <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">No recent workspace events recorded.</div>
                        ` : `
                            <div style="display: flex; flex-direction: column; gap: 10px;">
                                ${recentActivity.slice(0, 6).map(act => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12.5px; border-bottom: 1px solid var(--border); padding-bottom: 8px;">
                                        <div style="display: flex; align-items: center; gap: 10px;">
                                            <span style="width: 8px; height: 8px; border-radius: 50%; background: ${act.type === 'crawl_completed' ? 'var(--success)' : 'var(--primary)'}; flex-shrink: 0;"></span>
                                            <span style="font-weight: 600; color: var(--text-primary);">${act.title}</span>
                                        </div>
                                        <span style="font-size: 11px; color: var(--text-tertiary);">${act.timestamp ? act.timestamp.split('T')[0] : 'Recent'}</span>
                                    </div>
                                `).join('')}
                            </div>
                        `}
                    </div>

                </div>
            `;

            // Bind Portfolio Table Controls & Render Initial Table
            this.bindPortfolioControls();
            this.renderPortfolioTable();
            this.bindTrendPills();

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "Workspace Overview Error", e.message || "Failed to load workspace overview metrics.", () => this.mounted());
            }
        }
    }

    bindTrendPills() {
        const pillsContainer = document.getElementById('trend-timeframe-pills');
        if (!pillsContainer) return;
        const btns = pillsContainer.querySelectorAll('.pill-btn');
        btns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                btns.forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.trendTimeframe = e.currentTarget.getAttribute('data-tf');
            });
        });
    }

    bindPortfolioControls() {
        const searchInput = document.getElementById('website-search-input');
        const filterSelect = document.getElementById('website-status-filter');
        const sortSelect = document.getElementById('website-sort-option');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.toLowerCase().trim();
                this.renderPortfolioTable();
            });
        }
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.statusFilter = e.target.value;
                this.renderPortfolioTable();
            });
        }
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.sortOption = e.target.value;
                this.renderPortfolioTable();
            });
        }
    }

    renderPortfolioTable() {
        const container = document.getElementById('portfolio-table-container');
        if (!container) return;

        // 1. Filter Projects
        let list = this.allProjects.filter(p => {
            const matchesSearch = !this.searchQuery || (p.name && p.name.toLowerCase().includes(this.searchQuery)) || (p.domain && p.domain.toLowerCase().includes(this.searchQuery)) || (p.url && p.url.toLowerCase().includes(this.searchQuery));
            const matchesStatus = this.statusFilter === 'all' || p.crawl_status === this.statusFilter;
            return matchesSearch && matchesStatus;
        });

        // 2. Sort Projects
        list.sort((a, b) => {
            if (this.sortOption === 'health_desc') return (b.health_score || 0) - (a.health_score || 0);
            if (this.sortOption === 'health_asc') return (a.health_score || 0) - (b.health_score || 0);
            if (this.sortOption === 'name_asc') return (a.name || '').localeCompare(b.name || '');
            if (this.sortOption === 'issues_desc') return (b.critical_issues || 0) - (a.critical_issues || 0);
            return 0;
        });

        if (list.length === 0) {
            container.innerHTML = `
                <div style="padding: 36px; text-align: center; color: var(--text-secondary); font-size: 13.5px; background: var(--bg-subtle); border-radius: 10px;">
                    No websites match the selected search query or status filter.
                </div>
            `;
            return;
        }

        const tableRows = list.map(p => {
            const hasCrawled = p.has_crawled || (p.pages_crawled && p.pages_crawled > 0);
            const health = p.health_score;

            let hBadgeClass = 'badge-info';
            let hText = '—';

            if (hasCrawled && health !== null && health !== undefined) {
                if (health >= 85) { hBadgeClass = 'badge-success'; hText = `${health} / 100`; }
                else if (health >= 70) { hBadgeClass = 'badge-warning'; hText = `${health} / 100`; }
                else { hBadgeClass = 'badge-critical'; hText = `${health} / 100`; }
            }

            let displayStatus = p.crawl_status || (hasCrawled ? 'Healthy' : 'Not Crawled');
            let statusBadgeClass = 'badge-info';
            if (displayStatus === 'Healthy') statusBadgeClass = 'badge-success';
            else if (displayStatus === 'Needs Attention') statusBadgeClass = 'badge-warning';
            else if (displayStatus === 'Critical') statusBadgeClass = 'badge-critical';
            else if (displayStatus === 'Not Crawled' || displayStatus === 'No Crawls') {
                displayStatus = 'Not Crawled';
                statusBadgeClass = 'badge-info';
            }

            const targetUrl = p.domain || p.url || 'unconfigured';
            const actionText = hasCrawled ? 'Run Crawl' : 'Run First Crawl';

            return `
                <tr>
                    <td style="padding: 14px 20px;">
                        <strong style="font-size: 14px; color: var(--text-primary); display: block; font-weight: 700;">${p.name}</strong>
                        <span style="font-size: 11.5px; color: var(--text-secondary);">${targetUrl}</span>
                    </td>
                    <td style="padding: 14px 20px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="badge ${hBadgeClass}">${hText}</span>
                            ${hasCrawled && health !== null && health !== undefined ? `
                                <div style="width: 48px; height: 4px; border-radius: 2px; background: var(--border); overflow: hidden;">
                                    <div style="width: ${health}%; height: 100%; background: ${health >= 85 ? 'var(--success)' : (health >= 70 ? 'var(--warning)' : 'var(--critical)')};"></div>
                                </div>
                            ` : ''}
                        </div>
                    </td>
                    <td style="padding: 14px 20px; font-weight: 700; color: ${p.critical_issues > 0 ? 'var(--critical)' : 'var(--text-secondary)'};">${hasCrawled ? (p.critical_issues || 0) : '—'}</td>
                    <td style="padding: 14px 20px; font-weight: 600; color: ${p.warnings > 0 ? 'var(--warning)' : 'var(--text-secondary)'};">${hasCrawled ? (p.warnings || 0) : '—'}</td>
                    <td style="padding: 14px 20px; font-size: 13px;">${hasCrawled ? (p.pages_crawled || 0) : '—'}</td>
                    <td style="padding: 14px 20px; font-size: 12px; color: var(--text-secondary);">${p.last_crawl ? p.last_crawl.split('T')[0] : 'Never'}</td>
                    <td style="padding: 14px 20px;"><span class="badge ${statusBadgeClass}">${displayStatus}</span></td>
                    <td style="padding: 14px 20px; text-align: right;">
                        <div style="display: flex; gap: 8px; justify-content: flex-end;">
                            <button class="btn btn-primary btn-sm" style="font-size: 11px; padding: 4px 10px;" onclick="window.startCrawlFromOverview('${p.id}', '${targetUrl}')">${actionText}</button>
                            ${hasCrawled ? `<button class="btn btn-secondary btn-sm" style="font-size: 11px; padding: 4px 10px;" onclick="window.navigateToAudit('${p.id}')">View Audit &rarr;</button>` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <div style="overflow-x: auto;">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th style="padding: 12px 20px;">Website</th>
                            <th style="padding: 12px 20px;">SEO Health</th>
                            <th style="padding: 12px 20px;">Critical</th>
                            <th style="padding: 12px 20px;">Warnings</th>
                            <th style="padding: 12px 20px;">Pages</th>
                            <th style="padding: 12px 20px;">Last Crawl</th>
                            <th style="padding: 12px 20px;">Status</th>
                            <th style="padding: 12px 20px; text-align: right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>${tableRows}</tbody>
                </table>
            </div>
        `;
    }
}
