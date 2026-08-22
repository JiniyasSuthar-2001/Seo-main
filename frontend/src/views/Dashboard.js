import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { crawlProgressOverlay } from '../components/CrawlProgressOverlay.js';

window.startCrawlFromOverview = async (explicitProjectId, explicitUrl) => {
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
        alert("Please enter a valid website URL to crawl.");
        return;
    }

    try {
        const data = await crawlService.startCrawl(targetId, url);
        crawlProgressOverlay.start(targetId, data.session_id, url);
    } catch(e) {
        alert(`Backend API error starting crawl: ${e.message || 'Unable to start crawl.'}`);
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
        this.allProjects = [];
        this.searchQuery = '';
        this.statusFilter = 'all';
        this.sortOption = 'health_desc';
    }

    render() {
        this.element.innerHTML = `
            <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                Loading Workspace Command Center...
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

            // SECTION 9 — ACCOUNT-LEVEL EMPTY WORKSPACE STATE
            if (!this.allProjects || this.allProjects.length === 0) {
                this.element.innerHTML = `
                    <div class="header" style="margin-bottom: 24px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ACCOUNT WORKSPACE</div>
                        <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px;">SEO Intelligence Command Center</h1>
                    </div>
                    <div class="card" style="padding: 48px 24px; text-align: center; max-width: 560px; margin: 32px auto; box-shadow: 0 4px 16px rgba(0,0,0,0.05);">
                        <div style="width: 56px; height: 56px; border-radius: 14px; background: rgba(37, 99, 235, 0.1); color: var(--primary); display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                        </div>
                        <h2 style="font-size: 20px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">Your SEO workspace is empty</h2>
                        <p style="color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; line-height: 1.5;">Add your first website domain to start monitoring SEO performance across your portfolio.</p>
                        <div style="display: flex; gap: 12px; justify-content: center;">
                            <button class="btn btn-primary" onclick="window.showCreateProjectModal()">+ Add Website</button>
                            <a href="/import" data-link class="btn btn-secondary">Import SEO Data</a>
                        </div>
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

            // Filter websites needing attention
            const needingAttention = this.allProjects.filter(p => p.has_crawled && (p.critical_issues > 0 || (p.health_score !== null && p.health_score < 80)));

            // Construct Main View Shell
            this.element.innerHTML = `
                <!-- HEADER -->
                <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ACCOUNT WORKSPACE</div>
                        <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px; color: var(--text-primary);">SEO Overview</h1>
                        <p style="color: var(--text-secondary); font-size: 13px; margin-top: 2px;">
                            Monitor the health and performance of all websites in your workspace.
                        </p>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-secondary btn-sm" onclick="window.location.reload()">Refresh Overview</button>
                        <button class="btn btn-primary btn-sm" onclick="window.showCreateProjectModal()">+ Add Website</button>
                    </div>
                </div>

                <!-- WORKSPACE KPI CARDS (6 COMPACT CARDS) -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; margin-bottom: 28px;">
                    <div class="kpi-card">
                        <div class="kpi-label">Websites</div>
                        <div class="kpi-value" style="color: var(--primary);">${summary.total_projects || 0}</div>
                        <div class="kpi-status">${summary.active_projects || 0} active audited</div>
                    </div>

                    <div class="kpi-card">
                        <div class="kpi-label">Active Crawls</div>
                        <div class="kpi-value">${summary.active_projects || 0}</div>
                        <div class="kpi-status">Audited inventory</div>
                    </div>

                    <div class="kpi-card" style="border-left: 4px solid ${avgHealthColor};">
                        <div class="kpi-label">Average SEO Health</div>
                        <div class="kpi-value" style="color: ${avgHealthColor};">${avgHealth !== null ? avgHealth : 'Unavailable'}</div>
                        <div class="kpi-status">${avgHealth !== null ? 'Portfolio average' : 'No crawl data'}</div>
                    </div>

                    <div class="kpi-card">
                        <div class="kpi-label">Critical Issues</div>
                        <div class="kpi-value" style="color: var(--critical, #ef4444);">${summary.critical_issues || 0}</div>
                        <div class="kpi-status">Across portfolio</div>
                    </div>

                    <div class="kpi-card">
                        <div class="kpi-label">Warnings</div>
                        <div class="kpi-value" style="color: var(--warning, #f59e0b);">${summary.warnings || 0}</div>
                        <div class="kpi-status">Across portfolio</div>
                    </div>

                    <div class="kpi-card">
                        <div class="kpi-label">Recent Crawls</div>
                        <div class="kpi-value">${summary.total_crawls || 0}</div>
                        <div class="kpi-status">Total snapshots</div>
                    </div>
                </div>

                <!-- SECTION 7 — QUICK ACTIONS BAR -->
                <div class="card" style="padding: 16px; margin-bottom: 28px; background: var(--bg-subtle);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 10px;">Quick Workspace Actions</div>
                    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                        <button class="btn btn-primary btn-sm" onclick="window.showCreateProjectModal()">+ Add Website</button>
                        <button class="btn btn-secondary btn-sm" onclick="if(projectStore.projects.length>0){window.startCrawlFromOverview(projectStore.projects[0].id, projectStore.projects[0].domain||projectStore.projects[0].url);}else{window.showCreateProjectModal();}">Run Crawl</button>
                        <a href="/import" data-link class="btn btn-secondary btn-sm">Import Data</a>
                        <a href="/reports" data-link class="btn btn-secondary btn-sm">Generate Report</a>
                        <a href="/crawl-history" data-link class="btn btn-secondary btn-sm">View Crawl History</a>
                        <a href="/integrations" data-link class="btn btn-secondary btn-sm">Connect Integration</a>
                    </div>
                </div>

                <!-- SECTION 1 — WEBSITE PORTFOLIO -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 20px;">
                        <div>
                            <h2 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Your Websites</h2>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Monitor the SEO health of every website in your workspace.</div>
                        </div>

                        <!-- SEARCH, FILTER, SORT CONTROLS -->
                        <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                            <input type="text" id="website-search-input" placeholder="Search websites..." style="padding: 6px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; width: 180px; background: var(--bg-surface); color: var(--text-primary);"/>
                            
                            <select id="website-status-filter" style="padding: 6px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-surface); color: var(--text-primary);">
                                <option value="all">All Statuses</option>
                                <option value="Healthy">Healthy</option>
                                <option value="Needs Attention">Needs Attention</option>
                                <option value="Critical">Critical</option>
                                <option value="Never Crawled">Never Crawled</option>
                            </select>

                            <select id="website-sort-option" style="padding: 6px 12px; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg-surface); color: var(--text-primary);">
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

                <!-- SECTION 2 — WEBSITES NEEDING ATTENTION -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 14px; color: var(--text-primary);">Websites Needing Attention</h3>
                    ${needingAttention.length === 0 ? `
                        <div style="padding: 16px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; color: #10b981; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            <span>All audited websites are currently within healthy thresholds.</span>
                        </div>
                    ` : `
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">
                            ${needingAttention.map(p => `
                                <div style="padding: 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-surface); display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: 700; font-size: 14px;">${p.name}</div>
                                        <div style="font-size: 12px; color: var(--text-secondary);">${p.domain || p.url}</div>
                                        <div style="margin-top: 6px; font-size: 12px; color: var(--critical, #ef4444); font-weight: 600;">
                                            ${p.critical_issues} critical issues • ${p.warnings} warnings
                                        </div>
                                    </div>
                                    <button class="btn btn-primary btn-sm" onclick="window.navigateToAudit('${p.id}')" style="font-size: 11px;">Open Audit &rarr;</button>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>

                <!-- SECTION 4 — WORKSPACE SEO HEALTH TREND -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 12px;">Workspace SEO Health Trend</h3>
                    ${healthTrend.length < 2 ? `
                        <div style="padding: 24px; text-align: center; background: var(--bg-subtle); border-radius: 8px; color: var(--text-secondary); font-size: 13px;">
                            <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">Not enough crawl history to display a trend.</div>
                            <div>Run additional crawls over time to start tracking portfolio health changes.</div>
                        </div>
                    ` : `
                        <div style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px;">
                            ${healthTrend.map(t => `
                                <div style="padding: 12px 16px; background: var(--bg-subtle); border-radius: 8px; min-width: 140px; text-align: center;">
                                    <div style="font-size: 11px; color: var(--text-tertiary);">${t.timestamp || 'Snapshot'}</div>
                                    <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin: 4px 0;">${t.domain || 'Domain'}</div>
                                    <div style="font-size: 12px; color: var(--primary);">${t.pages_crawled} pages • ${t.issues} issues</div>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>

                <!-- SECTION 5 — TOP SEO ISSUES ACROSS YOUR WEBSITES -->
                <div class="card" style="padding: 0; overflow: hidden; margin-bottom: 28px;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Top SEO Issues Across Your Websites</h3>
                            <div style="font-size: 11px; color: var(--text-secondary);">Real aggregated technical findings across portfolio sites</div>
                        </div>
                        <a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View All Audits</a>
                    </div>
                    ${accountIssues.length === 0 ? `
                        <div style="padding: 24px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                            ✓ Zero aggregated critical technical issues across workspace websites.
                        </div>
                    ` : `
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
                            <tbody>
                                ${accountIssues.map(iss => {
                                    const isCrit = iss.severity === 'critical' || iss.severity === 'error';
                                    const badgeClass = isCrit ? 'badge-critical' : (iss.severity === 'warning' ? 'badge-warning' : 'badge-info');
                                    return `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 10px 16px;"><span class="badge ${badgeClass}">${iss.severity.toUpperCase()}</span></td>
                                            <td style="padding: 10px 16px; font-weight: 600;">${iss.title}</td>
                                            <td style="padding: 10px 16px; font-size: 12px;">${iss.affected_websites_count} website${iss.affected_websites_count === 1 ? '' : 's'}</td>
                                            <td style="padding: 10px 16px; font-family: monospace; font-size: 12px; color: var(--text-secondary);">${iss.total_urls_count} URLs</td>
                                            <td style="padding: 10px 16px; text-align: right;"><a href="/technical" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">View Issues &rarr;</a></td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    `}
                </div>

                <!-- SECTION 3 & 6 & 8: RECENT CRAWLS, ACTIVITY & CRAWL HISTORY PREVIEW -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px; margin-bottom: 28px;">
                    
                    <!-- SECTION 3 & 8 — RECENT CRAWLS PREVIEW -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Recent Crawl Activity</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Audit snapshot timeline</div>
                            </div>
                            <a href="/crawl-history" data-link class="btn btn-secondary btn-sm" style="font-size: 11px;">Crawl History</a>
                        </div>
                        ${recentCrawls.length === 0 ? `
                            <div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">No recent crawl records.</div>
                        ` : `
                            <div>
                                ${recentCrawls.slice(0, 5).map(c => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--bg-subtle); border-radius: 6px; font-size: 12px; margin-bottom: 6px;">
                                        <div>
                                            <strong style="color: var(--text-primary);">${c.project_name || 'Website'}</strong>
                                            <div style="font-size: 10px; color: var(--text-tertiary);">${c.timestamp || 'Recent'}</div>
                                        </div>
                                        <div style="display: flex; gap: 8px; align-items: center;">
                                            <span style="font-size: 11px; color: var(--text-secondary);">${c.pages_crawled || 0} p.</span>
                                            <button class="btn btn-secondary btn-sm" onclick="window.navigateToAudit('${c.project_id}')" style="font-size: 10px; padding: 2px 8px;">View Audit</button>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            <div style="margin-top: 12px; text-align: right;">
                                <a href="/crawl-history" data-link style="font-size: 12px; font-weight: 600; color: var(--primary); text-decoration: none;">View Full Crawl History &rarr;</a>
                            </div>
                        `}
                    </div>

                    <!-- SECTION 6 — RECENT ACTIVITY STREAM -->
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 15px; font-weight: 700; margin: 0;">Recent Activity</h3>
                                <div style="font-size: 11px; color: var(--text-secondary);">Real workspace event stream</div>
                            </div>
                        </div>
                        ${recentActivity.length === 0 ? `
                            <div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">No recent activity recorded.</div>
                        ` : `
                            <div style="display: flex; flex-direction: column; gap: 8px;">
                                ${recentActivity.slice(0, 6).map(act => `
                                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px;">
                                        <div style="display: flex; align-items: center; gap: 8px;">
                                            <span style="width: 8px; height: 8px; border-radius: 50%; background: ${act.type==='crawl_completed'?'var(--success)':'var(--primary)'}; display: inline-block;"></span>
                                            <span style="font-weight: 600;">${act.title}</span>
                                        </div>
                                        <span style="font-size: 10px; color: var(--text-tertiary);">${act.timestamp ? act.timestamp.split('T')[0] : 'Recent'}</span>
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

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "Workspace Overview Error", e.message || "Failed to load workspace overview metrics.", () => this.mounted());
            }
        }
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
                <div style="padding: 32px; text-align: center; color: var(--text-secondary); font-size: 13px;">
                    No websites match the selected search/filter criteria.
                </div>
            `;
            return;
        }

        const tableRows = list.map(p => {
            const health = p.health_score;
            let hBadgeClass = 'badge-info';
            let hText = 'Never Crawled';

            if (health !== null && health !== undefined) {
                if (health >= 85) { hBadgeClass = 'badge-success'; hText = `${health} / 100`; }
                else if (health >= 70) { hBadgeClass = 'badge-warning'; hText = `${health} / 100`; }
                else { hBadgeClass = 'badge-critical'; hText = `${health} / 100`; }
            }

            let statusBadgeClass = 'badge-info';
            if (p.crawl_status === 'Healthy') statusBadgeClass = 'badge-success';
            else if (p.crawl_status === 'Needs Attention') statusBadgeClass = 'badge-warning';
            else if (p.crawl_status === 'Critical') statusBadgeClass = 'badge-critical';

            const targetUrl = p.domain || p.url || 'unconfigured';

            return `
                <tr style="border-bottom: 1px solid var(--border); transition: background 0.15s ease;" onmouseover="this.style.background='var(--bg-subtle)'" onmouseout="this.style.background='transparent'">
                    <td style="padding: 12px 16px;">
                        <strong style="font-size: 14px; color: var(--text-primary); display: block;">${p.name}</strong>
                        <span style="font-size: 11px; color: var(--text-secondary);">${targetUrl}</span>
                    </td>
                    <td style="padding: 12px 16px;"><span class="badge ${hBadgeClass}">${hText}</span></td>
                    <td style="padding: 12px 16px; font-weight: 700; color: var(--critical, #ef4444);">${p.critical_issues || 0}</td>
                    <td style="padding: 12px 16px; font-weight: 600; color: var(--warning, #f59e0b);">${p.warnings || 0}</td>
                    <td style="padding: 12px 16px; font-size: 13px;">${p.pages_crawled || 0}</td>
                    <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary);">${p.last_crawl || 'Never'}</td>
                    <td style="padding: 12px 16px;"><span class="badge ${statusBadgeClass}">${p.crawl_status}</span></td>
                    <td style="padding: 12px 16px; text-align: right;">
                        <div style="display: flex; gap: 6px; justify-content: flex-end;">
                            <button class="btn btn-secondary btn-sm" style="font-size: 11px;" onclick="window.startCrawlFromOverview('${p.id}', '${targetUrl}')">Run Crawl</button>
                            <button class="btn btn-primary btn-sm" style="font-size: 11px;" onclick="window.navigateToAudit('${p.id}')">View Audit &rarr;</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                    <thead>
                        <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                            <th style="padding: 10px 16px;">Website</th>
                            <th style="padding: 10px 16px;">SEO Health</th>
                            <th style="padding: 10px 16px;">Critical</th>
                            <th style="padding: 10px 16px;">Warnings</th>
                            <th style="padding: 10px 16px;">Pages</th>
                            <th style="padding: 10px 16px;">Last Crawl</th>
                            <th style="padding: 10px 16px;">Status</th>
                            <th style="padding: 10px 16px; text-align: right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>${tableRows}</tbody>
                </table>
            </div>
        `;
    }
}
