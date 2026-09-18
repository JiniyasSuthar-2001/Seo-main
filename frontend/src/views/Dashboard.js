import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { crawlConfigModal } from '../components/CrawlConfigModal.js';
import { renderAIBadge, renderSourceBadge, renderViewEvidenceButton } from '../components/AIBadge.js';
import { renderTooltip } from '../components/Tooltip.js';
import { uiStateStore } from '../core/uiStateStore.js';

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
        this.healthTrend = [];
        this.crawlIssuesTrend = [];
        this.aggregateHealthTrend = [];
        this.unsubProjectStore = null;
    }

    render() {
        const projectId = projectStore.getSelectedProjectId();
        const savedState = uiStateStore.get(projectId, 'Dashboard');
        if (savedState) {
            if (savedState.trendTimeframe) this.trendTimeframe = savedState.trendTimeframe;
            if (savedState.searchQuery) this.searchQuery = savedState.searchQuery;
            if (savedState.statusFilter) this.statusFilter = savedState.statusFilter;
            if (savedState.sortOption) this.sortOption = savedState.sortOption;
        }

        this.element.innerHTML = `
            <div class="card" style="padding: 40px; text-align: center;">
                <div class="skeleton" style="height: 28px; width: 280px; margin: 0 auto 16px;"></div>
                <div class="skeleton" style="height: 160px; width: 100%; border-radius: 12px;"></div>
            </div>
        `;
        return this.element;
    }

    unmount() {
        if (this.unsubProjectStore) {
            this.unsubProjectStore();
            this.unsubProjectStore = null;
        }
    }

    async mounted() {
        try {
            await projectStore.ensureInitialized();

            // Subscribe to projectStore changes if not already subscribed
            if (!this.unsubProjectStore) {
                this.unsubProjectStore = projectStore.subscribe(() => {
                    this.mounted();
                });
            }

            const selectedProjectId = projectStore.getSelectedProjectId();
            const isWorkspaceContext = !selectedProjectId || selectedProjectId === 'all';

            if (isWorkspaceContext) {
                await this.renderWorkspaceOverview();
            } else {
                await this.renderIndividualProjectOverview(selectedProjectId);
            }
        } catch (e) {
            if (e.name === 'TypeError' || (e.message && e.message.includes('fetch')) || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, `Unable to connect right now. Please try again.`, () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "Overview Error", e.message || "Failed to load overview data.", () => this.mounted());
            }
        }
    }

    // ==========================================
    // ALL WORKSPACES OVERVIEW (Req 3A, 5, 6)
    // ==========================================
    async renderWorkspaceOverview() {
        const overviewData = await dashboardService.getWorkspaceOverview();
        this.allProjects = overviewData.projects || [];
        const accountIssues = overviewData.account_issues_summary || [];
        this.healthTrend = overviewData.health_trend || [];
        this.aggregateHealthTrend = overviewData.aggregate_health_trend || [];
        this.crawlIssuesTrend = overviewData.crawl_issues_trend || [];

        if (!this.allProjects || this.allProjects.length === 0) {
            this.element.innerHTML = `
                <div class="header" style="margin-bottom: 24px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ALL WORKSPACES OVERVIEW</div>
                    <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px;">Your Account Overview</h1>
                </div>
                <div class="card" style="padding: 48px 32px; text-align: center; max-width: 600px; margin: 32px auto;">
                    <div style="width: 64px; height: 64px; border-radius: 16px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin: 0 auto 24px;">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                    </div>
                    <h2 style="font-size: 22px; font-weight: 700; margin-bottom: 10px; color: var(--text-primary);">Add Your First Website</h2>
                    <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; line-height: 1.6;">Add your website domain to begin running scans, discovering pages, identifying technical health issues, and tracking Google search rankings.</p>
                    <button class="btn btn-primary btn-lg" onclick="window.showCreateProjectModal()" style="font-weight: 600;">+ Add Your First Website</button>
                </div>
            `;
            return;
        }

        // REQUIREMENT 5: The 4 KPI cards (Total Websites, Critical Problems, Pages Found, Average Health Score)
        // are explicitly REMOVED from the All Workspaces Overview.
        this.element.innerHTML = `
            <!-- HEADER SECTION -->
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ALL WORKSPACES</div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 2px 0 4px 0;">Portfolio Overview</h1>
                    <p style="color: var(--text-secondary); font-size: 13.5px; margin: 0;">Cross-project health progress, crawl trends, and aggregated site audits across your authorized projects.</p>
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-primary btn-sm" onclick="window.showCreateProjectModal()" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        Add Website
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="window.startCrawlFromOverview()" style="display: inline-flex; align-items: center; gap: 6px;">
                        Scan Website
                    </button>
                    <a href="/import" data-link class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        Import Data
                    </a>
                    <a href="/reports" data-link class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        Download Report
                    </a>
                </div>
            </div>

            <!-- REQUIREMENT 6: GRAPH 1 - WORKSPACE HEALTH TREND -->
            <div class="card" style="padding: 24px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <h2 style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary);">Workspace Health Trend</h2>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Average canonical audit health score across all authorized website scans.</div>
                    </div>
                    <div id="ws-health-timeframe-pills" style="display: flex; gap: 4px; background: var(--bg-subtle); padding: 4px; border-radius: 8px; border: 1px solid var(--border);">
                        <button class="pill-btn ${this.trendTimeframe === '7D' ? 'active' : ''}" data-tf="7D" style="padding: 4px 10px; font-size: 11px;">7 Days</button>
                        <button class="pill-btn ${this.trendTimeframe === '30D' ? 'active' : ''}" data-tf="30D" style="padding: 4px 10px; font-size: 11px;">30 Days</button>
                        <button class="pill-btn ${this.trendTimeframe === '90D' ? 'active' : ''}" data-tf="90D" style="padding: 4px 10px; font-size: 11px;">90 Days</button>
                        <button class="pill-btn ${this.trendTimeframe === 'ALL' ? 'active' : ''}" data-tf="ALL" style="padding: 4px 10px; font-size: 11px;">All Time</button>
                    </div>
                </div>
                <div id="workspace-health-trend-container"></div>
            </div>

            <!-- REQUIREMENT 6: GRAPH 2 - WORKSPACE CRAWL & ISSUES TREND -->
            <div class="card" style="padding: 24px; margin-bottom: 28px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <h2 style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary);">Workspace Crawl & Issues Trend</h2>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Pages crawled and critical issues detected in recent website scan snapshots.</div>
                    </div>
                </div>
                <div id="workspace-crawl-issues-trend-container"></div>
            </div>

            <!-- WEBSITES DIRECTORY TABLE -->
            <div class="card" style="padding: 24px; margin-bottom: 28px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <h2 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Your Websites</h2>
                        <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">Manage and monitor health checks across all your websites.</div>
                    </div>

                    <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                        <input type="text" id="website-search-input" placeholder="Search websites..." style="padding: 7px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; width: 190px; background: var(--bg-subtle); color: var(--text-primary);"/>
                        
                        <select id="website-status-filter" style="padding: 7px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-subtle); color: var(--text-primary); cursor: pointer;">
                            <option value="all">All Statuses</option>
                            <option value="Healthy">Healthy</option>
                            <option value="Needs Attention">Needs Attention</option>
                            <option value="Critical">Critical</option>
                            <option value="Never Crawled">Never Scanned</option>
                        </select>

                        <select id="website-sort-option" style="padding: 7px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-subtle); color: var(--text-primary); cursor: pointer;">
                            <option value="health_desc">Sort: Health (High to Low)</option>
                            <option value="health_asc">Sort: Health (Low to High)</option>
                            <option value="name_asc">Sort: Name (A - Z)</option>
                            <option value="issues_desc">Sort: Critical Problems</option>
                        </select>
                    </div>
                </div>

                <div id="portfolio-table-container"></div>
            </div>

            <!-- TOP PROBLEMS REQUIRING ATTENTION -->
            <div class="card" style="padding: 0; overflow: hidden; margin-bottom: 28px;">
                <div style="padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Top Problems Requiring Attention</h3>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Critical problems detected during website health checks</div>
                    </div>
                    <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11.5px;">View Health Checks &rarr;</a>
                </div>
                ${accountIssues.length === 0 ? `
                    <div style="padding: 28px; text-align: center; color: var(--text-secondary); font-size: 13.5px;">
                        ✓ Zero critical problems detected across your websites.
                    </div>
                ` : `
                    <div style="overflow-x: auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th style="padding: 12px 20px;">Severity</th>
                                    <th style="padding: 12px 20px;">Problem Title</th>
                                    <th style="padding: 12px 20px;">Affected Websites</th>
                                    <th style="padding: 12px 20px;">Affected Pages</th>
                                    <th style="padding: 12px 20px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${accountIssues.map(iss => {
                                    const isCrit = iss.severity === 'critical' || iss.severity === 'error';
                                    const badgeClass = isCrit ? 'badge-critical' : (iss.severity === 'warning' ? 'badge-warning' : 'badge-info');
                                    return `
                                        <tr>
                                            <td style="padding: 13px 20px;"><span class="badge ${badgeClass}">${(iss.severity || 'HIGH').toUpperCase()}</span></td>
                                            <td style="padding: 13px 20px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(iss.title)}</td>
                                            <td style="padding: 13px 20px; font-size: 13px;">${iss.affected_websites_count} ${iss.affected_websites_count === 1 ? 'website' : 'websites'}</td>
                                            <td style="padding: 13px 20px; font-family: monospace; font-size: 12px; color: var(--text-secondary);">${iss.total_urls_count} pages</td>
                                            <td style="padding: 13px 20px; text-align: right;"><a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View Proof &rarr;</a></td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                `}
            </div>
        `;

        this.bindPortfolioControls();
        this.renderPortfolioTable();
        this.bindWorkspaceTrendPills();
        this.renderWorkspaceHealthTrend();
        this.renderWorkspaceCrawlIssuesTrend();
    }

    // ==========================================
    // INDIVIDUAL PROJECT OVERVIEW (Req 3B, 4, 7, 8)
    // ==========================================
    async renderIndividualProjectOverview(projectId) {
        const projData = await dashboardService.getProjectOverview(projectId);
        const p = projData.project || {};
        const kpis = projData.kpis || {};
        const hasCrawl = projData.has_crawl;
        const previews = projData.previews || {};
        const healthTrend = projData.health_trend || [];
        const issuesTrend = projData.issues_trend || [];

        const hScore = kpis.health_score;
        const totalPages = kpis.total_pages;
        const totalRuns = kpis.total_runs || 0;
        const criticalIssues = kpis.critical_problems;

        this.element.innerHTML = `
            <!-- HEADER SECTION -->
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <span class="badge badge-primary" style="font-size: 10px; font-weight: 700; text-transform: uppercase;">PROJECT OVERVIEW</span>
                        <span style="font-size: 12px; color: var(--text-tertiary);">•</span>
                        <span style="font-size: 12.5px; color: var(--text-secondary); font-family: monospace;">${this.escapeHtml(p.domain || p.url || '')}</span>
                    </div>
                    <h1 style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin: 0 0 4px 0;">${this.escapeHtml(p.name || 'Website Overview')}</h1>
                    <p style="color: var(--text-secondary); font-size: 13.5px; margin: 0;">Dedicated audit insights, crawl history, and SEO metrics for this website.</p>
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawlFromOverview('${p.id}', '${p.domain || p.url}')" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                        Scan Website
                    </button>
                    <a href="/technical" data-link class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        Technical Audit
                    </a>
                    <a href="/reports" data-link class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                        Export Report
                    </a>
                </div>
            </div>

            <!-- EMPTY STATE NOTICE IF NO CRAWL AVAILABLE -->
            ${!hasCrawl ? `
                <div class="card" style="padding: 24px; margin-bottom: 24px; border-left: 4px solid var(--primary); background: var(--bg-card); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="width: 44px; height: 44px; border-radius: 10px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                        </div>
                        <div>
                            <strong style="font-size: 15px; color: var(--text-primary); display: block; margin-bottom: 2px;">No crawl data available yet.</strong>
                            <span style="font-size: 13px; color: var(--text-secondary);">Run your first website scan to analyze technical health, discover pages, and find SEO issues.</span>
                        </div>
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawlFromOverview('${p.id}', '${p.domain || p.url}')">Run First Scan Now</button>
                </div>
            ` : ''}

            <!-- REQUIREMENT 4: FOUR PRIMARY PROJECT METRICS -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px;">
                <!-- 1. Health Score -->
                <div class="card" style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                            Health Score ${renderTooltip('Canonical site audit health score (0-100) based on all evaluated SEO rules.')}
                        </div>
                        ${renderSourceBadge('crawl')}
                    </div>
                    ${hScore !== null && hScore !== undefined ? `
                        <div style="font-size: 28px; font-weight: 800; color: ${hScore >= 80 ? '#10b981' : (hScore >= 60 ? '#f59e0b' : '#ef4444')};">
                            ${hScore}<span style="font-size: 16px; font-weight: 600; color: var(--text-tertiary);">/100</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Latest canonical audit score</div>
                    ` : `
                        <div style="font-size: 18px; font-weight: 700; color: var(--text-secondary); margin-top: 6px;">Not yet scored</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Run a scan to calculate</div>
                    `}
                </div>

                <!-- 2. Total Pages -->
                <div class="card" style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                            Total Pages ${renderTooltip('Number of crawled pages found during the latest completed scan.')}
                        </div>
                        ${renderSourceBadge('crawl')}
                    </div>
                    ${totalPages !== null && totalPages !== undefined ? `
                        <div style="font-size: 28px; font-weight: 800; color: #3b82f6;">${totalPages.toLocaleString()}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Pages in latest completed crawl</div>
                    ` : `
                        <div style="font-size: 18px; font-weight: 700; color: var(--text-secondary); margin-top: 6px;">No pages crawled</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Awaiting initial scan</div>
                    `}
                </div>

                <!-- 3. Total Runs -->
                <div class="card" style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                            Total Runs ${renderTooltip('Total number of completed crawl sessions recorded for this website.')}
                        </div>
                        <span class="badge badge-secondary" style="font-size: 10px;">History</span>
                    </div>
                    <div style="font-size: 28px; font-weight: 800; color: var(--text-primary);">${totalRuns}</div>
                    <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Crawl snapshots recorded</div>
                </div>

                <!-- 4. Critical Problems -->
                <div class="card" style="padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                            Critical Problems ${renderTooltip('Critical severity problems found in the latest scan requiring urgent resolution.')}
                        </div>
                        ${renderSourceBadge('crawl')}
                    </div>
                    ${criticalIssues !== null && criticalIssues !== undefined ? `
                        <div style="font-size: 28px; font-weight: 800; color: ${criticalIssues > 0 ? '#ef4444' : '#10b981'};">${criticalIssues}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">${criticalIssues > 0 ? 'Urgent issues detected' : 'Zero critical problems'}</div>
                    ` : `
                        <div style="font-size: 18px; font-weight: 700; color: var(--text-secondary); margin-top: 6px;">None recorded</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Awaiting initial scan</div>
                    `}
                </div>
            </div>

            <!-- REQUIREMENT 7: TWO REAL DATA GRAPHS FOR SELECTED PROJECT -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; margin-bottom: 28px;">
                <!-- Graph 1: Health Score Over Time -->
                <div class="card" style="padding: 24px;">
                    <div style="margin-bottom: 16px;">
                        <h2 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Health Score Over Time</h2>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Canonical site health score across crawl history for ${this.escapeHtml(p.name)}.</div>
                    </div>
                    <div id="project-health-trend-container">
                        ${this.renderSingleLineChart(healthTrend, 'health_score', '#10b981', 'Health Score', 0, 100)}
                    </div>
                </div>

                <!-- Graph 2: Issues / Crawl Trend -->
                <div class="card" style="padding: 24px;">
                    <div style="margin-bottom: 16px;">
                        <h2 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Issues / Crawl Trend</h2>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Pages crawled and critical issues detected across scan runs.</div>
                    </div>
                    <div id="project-issues-trend-container">
                        ${this.renderDualBarChart(issuesTrend)}
                    </div>
                </div>
            </div>

            <!-- REQUIREMENT 8: PREVIEWS OF IMPORTANT PROJECT PAGES -->
            <div style="margin-bottom: 28px;">
                <div style="margin-bottom: 16px;">
                    <h2 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Project Modules & Quick Navigation</h2>
                    <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">Explore deeper SEO audit results, keyword ranks, and technical insights scoped to this website.</div>
                </div>

                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px;">
                    <!-- Technical Audit Preview -->
                    <a href="/technical" data-link class="card" style="padding: 20px; text-decoration: none; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s; border-top: 3px solid #3b82f6;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">Technical Audit</span>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </div>
                            <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.4;">Evaluate HTTP status codes, missing meta tags, canonicals, robots.txt, and structured data.</p>
                        </div>
                        <div style="font-size: 12.5px; font-weight: 600; color: var(--primary);">
                            ${previews.technical_audit?.health_score !== null && previews.technical_audit?.health_score !== undefined
                                ? `Score: ${previews.technical_audit.health_score}/100 • ${previews.technical_audit.critical_issues || 0} critical`
                                : 'Awaiting crawl audit'}
                        </div>
                    </a>

                    <!-- Keywords Preview -->
                    <a href="/keywords" data-link class="card" style="padding: 20px; text-decoration: none; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s; border-top: 3px solid #10b981;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">Keyword Research</span>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </div>
                            <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.4;">Track targeted search terms, discover keyword opportunities, and inspect on-page occurrence evidence.</p>
                        </div>
                        <div style="font-size: 12.5px; font-weight: 600; color: #10b981;">
                            ${previews.keywords?.total_keywords || 0} tracked keywords
                        </div>
                    </a>

                    <!-- Search Rankings Preview -->
                    <a href="/rankings" data-link class="card" style="padding: 20px; text-decoration: none; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s; border-top: 3px solid #8b5cf6;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">Search Rankings</span>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </div>
                            <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.4;">Monitor Google desktop and mobile positions, SERP features, and ranking fluctuations over time.</p>
                        </div>
                        <div style="font-size: 12.5px; font-weight: 600; color: #8b5cf6;">
                            ${previews.rankings?.total_ranked || 0} keywords with rank positions
                        </div>
                    </a>

                    <!-- Crawled Pages Preview -->
                    <a href="/crawl-data" data-link class="card" style="padding: 20px; text-decoration: none; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s; border-top: 3px solid #f59e0b;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">Crawled Pages</span>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </div>
                            <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.4;">Inspect complete URL inventory, response codes, page titles, word counts, and page-level issues.</p>
                        </div>
                        <div style="font-size: 12.5px; font-weight: 600; color: #f59e0b;">
                            ${previews.pages?.total_pages || 0} pages discovered
                        </div>
                    </a>

                    <!-- Internal Links Preview -->
                    <a href="/internal-links" data-link class="card" style="padding: 20px; text-decoration: none; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s; border-top: 3px solid #ec4899;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">Internal Links</span>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </div>
                            <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.4;">Analyze site architecture, inlink distributions, broken internal links, and redirect chains.</p>
                        </div>
                        <div style="font-size: 12.5px; font-weight: 600; color: #ec4899;">
                            ${previews.internal_links?.total_links || 0} total links • ${previews.internal_links?.broken_links || 0} broken
                        </div>
                    </a>

                    <!-- Reports Preview -->
                    <a href="/reports" data-link class="card" style="padding: 20px; text-decoration: none; display: flex; flex-direction: column; justify-content: space-between; transition: transform 0.2s, box-shadow 0.2s; border-top: 3px solid #6366f1;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">Audit Reports</span>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                            </div>
                            <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.4;">Generate and download professional executive client reports in PDF and CSV format.</p>
                        </div>
                        <div style="font-size: 12.5px; font-weight: 600; color: #6366f1;">
                            ${previews.reports?.report_count || 0} generated reports
                        </div>
                    </a>
                </div>
            </div>
        `;
    }

    // ==========================================
    // WORKSPACE TREND CONTROLS & CHARTS
    // ==========================================
    bindWorkspaceTrendPills() {
        const container = this.element.querySelector('#ws-health-timeframe-pills');
        if (!container) return;

        const pills = container.querySelectorAll('.pill-btn');
        pills.forEach(pill => {
            pill.addEventListener('click', (e) => {
                pills.forEach(p => p.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.trendTimeframe = e.currentTarget.getAttribute('data-tf');
                this.renderWorkspaceHealthTrend();
                this.renderWorkspaceCrawlIssuesTrend();
            });
        });
    }

    renderWorkspaceHealthTrend() {
        const container = this.element.querySelector('#workspace-health-trend-container');
        if (!container) return;

        const rawTrend = this.aggregateHealthTrend.length > 0 ? this.aggregateHealthTrend : this.healthTrend;
        const filtered = this.filterTrendByTimeframe(rawTrend);

        if (filtered.length === 0) {
            container.innerHTML = `
                <div style="padding: 36px 20px; text-align: center; background: var(--bg-subtle); border-radius: 10px; color: var(--text-secondary); font-size: 13.5px; border: 1px dashed var(--border);">
                    <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">Building scan history (${this.trendTimeframe})</div>
                    <div>No scans recorded within the selected timeframe. Run website scans across your projects to populate health score trends.</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.renderSingleLineChart(
            filtered,
            filtered[0].average_health_score !== undefined ? 'average_health_score' : 'health_score',
            '#10b981',
            'Average Health Score',
            0,
            100
        );
    }

    renderWorkspaceCrawlIssuesTrend() {
        const container = this.element.querySelector('#workspace-crawl-issues-trend-container');
        if (!container) return;

        const rawTrend = this.crawlIssuesTrend || [];
        const filtered = this.filterTrendByTimeframe(rawTrend);

        if (filtered.length === 0) {
            container.innerHTML = `
                <div style="padding: 36px 20px; text-align: center; background: var(--bg-subtle); border-radius: 10px; color: var(--text-secondary); font-size: 13.5px; border: 1px dashed var(--border);">
                    <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">Building crawl history (${this.trendTimeframe})</div>
                    <div>No crawl snapshots found within the selected timeframe.</div>
                </div>
            `;
            return;
        }

        container.innerHTML = this.renderDualBarChart(filtered);
    }

    filterTrendByTimeframe(trendList) {
        if (!trendList || trendList.length === 0) return [];
        if (this.trendTimeframe === 'ALL') return trendList;

        let daysCutoff = 30;
        if (this.trendTimeframe === '7D') daysCutoff = 7;
        else if (this.trendTimeframe === '90D') daysCutoff = 90;

        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - daysCutoff);

        return trendList.filter(t => {
            if (!t.timestamp) return true;
            const d = new Date(t.timestamp);
            return isNaN(d.getTime()) || d >= cutoffDate;
        });
    }

    // ==========================================
    // REUSABLE REAL-DATA SVG CHARTS
    // ==========================================
    renderSingleLineChart(data, valueKey, strokeColor = '#10b981', label = 'Health Score', minVal = 0, maxVal = 100) {
        if (!data || data.length === 0) {
            return `
                <div style="padding: 32px 20px; text-align: center; background: var(--bg-subtle); border-radius: 10px; color: var(--text-secondary); font-size: 13.5px; border: 1px dashed var(--border);">
                    <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">No scan history available</div>
                    <div>Run your first website scan to generate trend data.</div>
                </div>
            `;
        }

        const width = 600;
        const height = 180;
        const padding = { top: 20, right: 30, bottom: 30, left: 40 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        const values = data.map(d => d[valueKey] !== null && d[valueKey] !== undefined ? Number(d[valueKey]) : 0);
        const yMin = minVal;
        const yMax = maxVal;
        const yRange = yMax - yMin || 1;

        const getX = (idx) => {
            if (data.length === 1) return padding.left + chartW / 2;
            return padding.left + (idx / (data.length - 1)) * chartW;
        };

        const getY = (val) => {
            const clamped = Math.max(yMin, Math.min(yMax, val));
            return padding.top + chartH - ((clamped - yMin) / yRange) * chartH;
        };

        const points = data.map((d, i) => ({
            x: getX(i),
            y: getY(values[i]),
            val: values[i],
            date: d.timestamp ? d.timestamp.split('T')[0] : `Scan #${i + 1}`,
            domain: d.domain || ''
        }));

        const polylinePoints = points.map(p => `${p.x},${p.y}`).join(' ');

        // Area path
        const firstPt = points[0];
        const lastPt = points[points.length - 1];
        const bottomY = padding.top + chartH;
        const areaPath = `M ${firstPt.x},${bottomY} L ${polylinePoints} L ${lastPt.x},${bottomY} Z`;

        const gridLines = [0, 50, 100].map(val => {
            const y = getY(val);
            return `
                <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="var(--border)" stroke-width="1" stroke-dasharray="3,3" />
                <text x="${padding.left - 8}" y="${y + 4}" font-size="10" fill="var(--text-tertiary)" text-anchor="end">${val}</text>
            `;
        }).join('');

        const dots = points.map(p => `
            <g class="chart-point" data-tip="${p.date}: ${p.val}/100">
                <circle cx="${p.x}" cy="${p.y}" r="4.5" fill="${strokeColor}" stroke="#ffffff" stroke-width="2" style="cursor: pointer; transition: transform 0.2s;" />
                <text x="${p.x}" y="${p.y - 10}" font-size="10" font-weight="700" fill="${strokeColor}" text-anchor="middle">${p.val}</text>
            </g>
        `).join('');

        const xLabels = points.map((p, i) => {
            if (data.length > 6 && i % 2 !== 0 && i !== points.length - 1) return '';
            return `<text x="${p.x}" y="${height - 8}" font-size="10" fill="var(--text-tertiary)" text-anchor="middle">${p.date}</text>`;
        }).join('');

        return `
            <div style="width: 100%; overflow-x: auto;">
                <svg viewBox="0 0 ${width} ${height}" style="width: 100%; max-height: ${height}px; overflow: visible;" preserveAspectRatio="none">
                    <defs>
                        <linearGradient id="grad-${strokeColor.replace('#', '')}" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.28" />
                            <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0" />
                        </linearGradient>
                    </defs>
                    ${gridLines}
                    <path d="${areaPath}" fill="url(#grad-${strokeColor.replace('#', '')})" />
                    <polyline points="${polylinePoints}" fill="none" stroke="${strokeColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
                    ${dots}
                    ${xLabels}
                </svg>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 11px; color: var(--text-tertiary);">
                <span>Earliest: ${points[0].date}</span>
                <span style="display: flex; align-items: center; gap: 6px;">
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${strokeColor};"></span>
                    ${label}
                </span>
                <span>Latest: ${points[points.length - 1].date} (${points[points.length - 1].val}/100)</span>
            </div>
        `;
    }

    renderDualBarChart(data) {
        if (!data || data.length === 0) {
            return `
                <div style="padding: 32px 20px; text-align: center; background: var(--bg-subtle); border-radius: 10px; color: var(--text-secondary); font-size: 13.5px; border: 1px dashed var(--border);">
                    <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">No crawl snapshots available</div>
                    <div>Perform scans to see pages audited and critical issues over time.</div>
                </div>
            `;
        }

        const width = 600;
        const height = 180;
        const padding = { top: 20, right: 30, bottom: 30, left: 45 };
        const chartW = width - padding.left - padding.right;
        const chartH = height - padding.top - padding.bottom;

        const maxPages = Math.max(...data.map(d => d.pages_crawled || 0), 10);
        const maxIssues = Math.max(...data.map(d => d.critical_issues || 0), 5);

        const groupCount = data.length;
        const groupWidth = chartW / groupCount;
        const barWidth = Math.min(22, (groupWidth - 12) / 2);

        const barsHtml = data.map((d, i) => {
            const groupX = padding.left + i * groupWidth + (groupWidth - (barWidth * 2 + 4)) / 2;
            const pagesH = ((d.pages_crawled || 0) / maxPages) * chartH;
            const issuesH = ((d.critical_issues || 0) / maxIssues) * chartH;

            const pagesY = padding.top + chartH - pagesH;
            const issuesY = padding.top + chartH - issuesH;

            const dateStr = d.timestamp ? d.timestamp.split('T')[0] : `#${i + 1}`;

            return `
                <g>
                    <!-- Pages crawled bar (Blue) -->
                    <rect x="${groupX}" y="${pagesY}" width="${barWidth}" height="${pagesH}" rx="3" fill="#3b82f6" />
                    ${pagesH > 14 ? `<text x="${groupX + barWidth / 2}" y="${pagesY - 4}" font-size="9" font-weight="700" fill="#3b82f6" text-anchor="middle">${d.pages_crawled || 0}</text>` : ''}
                    
                    <!-- Critical issues bar (Red) -->
                    <rect x="${groupX + barWidth + 4}" y="${issuesY}" width="${barWidth}" height="${issuesH}" rx="3" fill="#ef4444" />
                    ${issuesH > 14 ? `<text x="${groupX + barWidth + 4 + barWidth / 2}" y="${issuesY - 4}" font-size="9" font-weight="700" fill="#ef4444" text-anchor="middle">${d.critical_issues || 0}</text>` : ''}

                    <text x="${groupX + barWidth + 2}" y="${height - 8}" font-size="10" fill="var(--text-tertiary)" text-anchor="middle">${dateStr}</text>
                </g>
            `;
        }).join('');

        return `
            <div style="width: 100%; overflow-x: auto;">
                <svg viewBox="0 0 ${width} ${height}" style="width: 100%; max-height: ${height}px; overflow: visible;" preserveAspectRatio="none">
                    <line x1="${padding.left}" y1="${padding.top + chartH}" x2="${width - padding.right}" y2="${padding.top + chartH}" stroke="var(--border)" stroke-width="1" />
                    ${barsHtml}
                </svg>
            </div>
            <div style="display: flex; justify-content: center; gap: 24px; margin-top: 10px; font-size: 11px;">
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: #3b82f6;"></span>
                    <span style="color: var(--text-secondary); font-weight: 500;">Pages Crawled</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: #ef4444;"></span>
                    <span style="color: var(--text-secondary); font-weight: 500;">Critical Problems</span>
                </div>
            </div>
        `;
    }

    // ==========================================
    // PORTFOLIO DIRECTORY CONTROLS
    // ==========================================
    bindPortfolioControls() {
        const searchInput = this.element.querySelector('#website-search-input');
        const statusFilter = this.element.querySelector('#website-status-filter');
        const sortOption = this.element.querySelector('#website-sort-option');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value.toLowerCase().trim();
                this.renderPortfolioTable();
            });
        }

        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.statusFilter = e.target.value;
                this.renderPortfolioTable();
            });
        }

        if (sortOption) {
            sortOption.addEventListener('change', (e) => {
                this.sortOption = e.target.value;
                const projectId = projectStore.getSelectedProjectId();
                uiStateStore.save(projectId, 'Dashboard', { sortOption: this.sortOption });
                this.renderPortfolioTable();
            });
        }
    }

    renderPortfolioTable() {
        const container = this.element.querySelector('#portfolio-table-container');
        if (!container) return;

        let list = [...this.allProjects];

        if (this.searchQuery) {
            list = list.filter(p => (p.name || '').toLowerCase().includes(this.searchQuery) || (p.domain || '').toLowerCase().includes(this.searchQuery));
        }

        if (this.statusFilter !== 'all') {
            list = list.filter(p => (p.crawl_status || p.status || 'Never Crawled') === this.statusFilter);
        }

        if (this.sortOption === 'health_desc') {
            list.sort((a, b) => (b.health_score || 0) - (a.health_score || 0));
        } else if (this.sortOption === 'health_asc') {
            list.sort((a, b) => (a.health_score || 0) - (b.health_score || 0));
        } else if (this.sortOption === 'name_asc') {
            list.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        } else if (this.sortOption === 'issues_desc') {
            list.sort((a, b) => (b.critical_issues || b.critical_issues_count || 0) - (a.critical_issues || a.critical_issues_count || 0));
        }

        if (list.length === 0) {
            container.innerHTML = `
                <div style="padding: 32px; text-align: center; color: var(--text-secondary); font-size: 13.5px;">
                    No websites match your filter '${this.escapeHtml(this.searchQuery)}'.
                </div>
            `;
            return;
        }

        const rows = list.map(p => {
            const hScore = (p.health_score !== undefined && p.health_score !== null) ? p.health_score : null;
            const healthColor = hScore !== null ? (hScore >= 80 ? '#10b981' : (hScore >= 60 ? '#f59e0b' : '#ef4444')) : 'var(--text-tertiary)';
            const st = p.crawl_status || p.status || 'Never Scanned';
            const badgeClass = st === 'Healthy' ? 'badge-success' : (st === 'Needs Attention' ? 'badge-warning' : (st === 'Critical' ? 'badge-critical' : 'badge-secondary'));

            return `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 14px 20px;">
                        <strong style="color: var(--text-primary); font-size: 14px; display: block;">${this.escapeHtml(p.name)}</strong>
                        <a href="${p.url || '#'}" target="_blank" style="font-size: 12px; color: var(--primary); text-decoration: none; font-family: monospace;">${this.escapeHtml(p.domain || p.url || '-')}</a>
                    </td>
                    <td style="padding: 14px 20px;">
                        <span class="badge ${badgeClass}" style="font-size: 11px;">${st}</span>
                    </td>
                    <td style="padding: 14px 20px;">
                        ${hScore !== null ? `
                            <div style="font-size: 15px; font-weight: 800; color: ${healthColor};">${hScore}<span style="font-size: 11px; font-weight: 600; color: var(--text-tertiary);">/100</span></div>
                        ` : `
                            <span style="font-size: 12px; color: var(--text-tertiary); font-style: italic;">Not yet scored</span>
                        `}
                    </td>
                    <td style="padding: 14px 20px; font-weight: 600;">${p.pages_crawled || 0}</td>
                    <td style="padding: 14px 20px;">
                        <span style="font-weight: 700; color: ${(p.critical_issues || p.critical_issues_count || 0) > 0 ? '#ef4444' : '#10b981'};">${p.critical_issues || p.critical_issues_count || 0}</span>
                    </td>
                    <td style="padding: 14px 20px; font-size: 12px; color: var(--text-secondary);">${(p.last_crawl || p.last_crawled_at) ? (p.last_crawl || p.last_crawled_at).split('T')[0] : 'Never'}</td>
                    <td style="padding: 14px 20px; text-align: right;">
                        <div style="display: flex; gap: 6px; justify-content: flex-end;">
                            <button class="btn btn-secondary btn-sm" onclick="window.startCrawlFromOverview('${p.id}', '${p.domain || p.url}')" style="font-size: 11px; padding: 4px 10px;">Scan My Website</button>
                            <button class="btn btn-primary btn-sm" onclick="window.navigateToAudit('${p.id}')" style="font-size: 11px; padding: 4px 10px;">Health Check &rarr;</button>
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
                            <th style="padding: 12px 20px;">Website Domain</th>
                            <th style="padding: 12px 20px;">Status</th>
                            <th style="padding: 12px 20px;">Website Health</th>
                            <th style="padding: 12px 20px;">Pages Found</th>
                            <th style="padding: 12px 20px;">Critical Problems</th>
                            <th style="padding: 12px 20px;">Last Scanned</th>
                            <th style="padding: 12px 20px; text-align: right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}
