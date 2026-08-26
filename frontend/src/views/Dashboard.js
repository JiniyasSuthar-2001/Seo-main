import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { crawlConfigModal } from '../components/CrawlConfigModal.js';
import { renderAIBadge, renderSourceBadge, renderViewEvidenceButton } from '../components/AIBadge.js';
import { renderTooltip } from '../components/Tooltip.js';

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
            const healthTrend = overviewData.health_trend || [];

            if (!this.allProjects || this.allProjects.length === 0) {
                this.element.innerHTML = `
                    <div class="header" style="margin-bottom: 24px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">ACCOUNT OVERVIEW</div>
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

            const totalSites = summary.total_websites || this.allProjects.length;
            const avgHealth = summary.average_health_score !== undefined ? summary.average_health_score : 100;
            const totalCrawledPages = summary.total_crawled_pages || 0;
            const totalIssuesCount = summary.total_critical_issues || 0;

            this.element.innerHTML = `
                <!-- HEADER SECTION -->
                <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                    <div>
                        <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">SEO Overview</h1>
                        <p style="color: var(--text-secondary); font-size: 13.5px; margin: 0;">Overview of your connected websites, health summaries, recent activity, and quick actions.</p>
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

                <!-- LEVEL 1: ACCOUNT PORTFOLIO SUMMARY CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px;">
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                                Total Websites ${renderTooltip('Number of websites registered in your account.')}
                            </div>
                            <span class="badge badge-secondary" style="font-size: 10px;">Account</span>
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: var(--text-primary);">${totalSites}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Connected websites</div>
                    </div>

                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                                Average Health Score ${renderTooltip('Overall health score across all your websites (0-100). Higher is better.')}
                            </div>
                            ${renderSourceBadge('crawl')}
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: ${avgHealth >= 80 ? '#10b981' : (avgHealth >= 60 ? '#f59e0b' : '#ef4444')};">${avgHealth}<span style="font-size: 16px; font-weight: 600;">/100</span></div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Overall health across websites</div>
                    </div>

                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                                Pages Found ${renderTooltip('Total number of pages discovered during your latest website scans.')}
                            </div>
                            ${renderSourceBadge('crawl')}
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: #3b82f6;">${totalCrawledPages.toLocaleString()}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Discovered pages on your sites</div>
                    </div>

                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">
                                Critical Problems ${renderTooltip('Problems that may seriously affect your website search visibility or usability.')}
                            </div>
                            ${renderSourceBadge('crawl')}
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: ${totalIssuesCount > 0 ? '#ef4444' : '#10b981'};">${totalIssuesCount}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Problems requiring attention</div>
                    </div>
                </div>

                <!-- LEVEL 2: WEBSITE LIST TABLE -->
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

                <!-- DYNAMIC AI ASSISTANT SECTION -->
                <div class="card" style="padding: 24px; margin-bottom: 28px; border-left: 4px solid #3b82f6; background: var(--bg-card);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <h3 style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary);" id="ai-card-title">AI Assistant</h3>
                                <span id="gemini-status-badge" class="badge badge-secondary" style="font-size: 11px;">Checking status...</span>
                            </div>
                            <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 4px;" id="ai-card-subtext">
                                Automated assistant providing plain-English explanations and step-by-step guidance based on real scan data.
                            </div>
                        </div>

                        <div style="display: flex; gap: 10px;" id="gemini-actions">
                            <button type="button" id="btn-test-gemini" class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                                ⚡ Test Connection
                            </button>
                            <button type="button" id="btn-analyze-gemini" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 6px; background: #2563eb;">
                                ✨ Ask AI Assistant
                            </button>
                        </div>
                    </div>

                    <!-- AI OUTPUT / RESULT BOX -->
                    <div id="gemini-output-box" style="padding: 16px; background: var(--bg-subtle); border-radius: 10px; border: 1px solid var(--border); font-size: 13px; color: var(--text-secondary);">
                        <div id="gemini-default-msg">
                            Click <strong id="ai-test-btn-label">Test Connection</strong> to check your AI connection or <strong id="ai-analyze-btn-label">Ask AI Assistant</strong> to review your selected website.
                        </div>
                    </div>
                </div>

                <!-- WEBSITE HEALTH TREND -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary);">Website Health Progress Over Time</h3>
                            <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Track how your website's health score improves across recent scans.</div>
                        </div>
                        <div id="trend-timeframe-pills" style="display: flex; gap: 4px; background: var(--bg-subtle); padding: 4px; border-radius: 8px; border: 1px solid var(--border);">
                            <button class="pill-btn ${this.trendTimeframe === '7D' ? 'active' : ''}" data-tf="7D" style="padding: 4px 10px; font-size: 11px;">7 Days</button>
                            <button class="pill-btn ${this.trendTimeframe === '30D' ? 'active' : ''}" data-tf="30D" style="padding: 4px 10px; font-size: 11px;">30 Days</button>
                            <button class="pill-btn ${this.trendTimeframe === '90D' ? 'active' : ''}" data-tf="90D" style="padding: 4px 10px; font-size: 11px;">90 Days</button>
                        </div>
                    </div>

                    ${healthTrend.length < 2 ? `
                        <div style="padding: 32px 20px; text-align: center; background: var(--bg-subtle); border-radius: 10px; color: var(--text-secondary); font-size: 13.5px; border: 1px dashed var(--border);">
                            <div style="font-weight: 600; margin-bottom: 4px; color: var(--text-primary);">Building scan history</div>
                            <div>Run additional website scans over time to see health progress trends.</div>
                        </div>
                    ` : `
                        <div style="display: flex; gap: 14px; overflow-x: auto; padding-bottom: 8px;">
                            ${healthTrend.map(t => `
                                <div style="padding: 14px 18px; background: var(--bg-subtle); border-radius: 10px; min-width: 160px; text-align: center; border: 1px solid var(--border);">
                                    <div style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase;">${t.timestamp ? t.timestamp.split('T')[0] : 'Saved Scan'}</div>
                                    <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin: 6px 0;">${t.domain || 'Domain'}</div>
                                    <div style="font-size: 12px; color: var(--primary); font-weight: 600;">${t.pages_crawled} pages • ${t.issues} problems</div>
                                </div>
                            `).join('')}
                        </div>
                    `}
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
            this.bindTrendPills();
            await this.bindGeminiSection();

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, `Unable to connect right now. Please try again.`, () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "Account Overview Error", e.message || "Failed to load account overview.", () => this.mounted());
            }
        }
    }

    async bindGeminiSection() {
        const titleEl = this.element.querySelector('#ai-card-title');
        const badge = this.element.querySelector('#gemini-status-badge');
        const btnTest = this.element.querySelector('#btn-test-gemini');
        const btnAnalyze = this.element.querySelector('#btn-analyze-gemini');
        const outputBox = this.element.querySelector('#gemini-output-box');

        let activeProvider = "groq";
        let testEndpoint = "/api/ai/groq/test";

        try {
            const statusData = await apiClient.get('/api/ai/status');
            activeProvider = (statusData.provider || "groq").toLowerCase();
            let providerTitle = "AI Assistant";

            if (titleEl) titleEl.innerText = providerTitle;
            if (btnTest) btnTest.innerText = `⚡ Test Connection`;
            if (btnAnalyze) btnAnalyze.innerText = `✨ Ask AI Assistant`;

            if (badge) {
                if (statusData && statusData.configured) {
                    badge.className = 'badge badge-success';
                    badge.innerHTML = `✓ Connected`;
                } else {
                    badge.className = 'badge badge-secondary';
                    badge.innerHTML = `Not Configured`;
                }
            }
        } catch (err) {
            if (badge) {
                badge.className = 'badge badge-secondary';
                badge.innerHTML = `Not Configured`;
            }
        }

        if (btnTest) {
            btnTest.addEventListener('click', async (e) => {
                e.preventDefault();
                btnTest.disabled = true;
                const origText = btnTest.innerHTML;
                btnTest.innerText = 'Testing...';

                try {
                    const testRes = await apiClient.post(testEndpoint, {});
                    if (testRes.status === 'connected' || testRes.available) {
                        if (outputBox) {
                            outputBox.innerHTML = `
                                <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); color: #10b981; padding: 14px; border-radius: 8px;">
                                    <strong style="display: block; margin-bottom: 4px; font-size: 14px;">✓ Connection Successful</strong>
                                    <span>AI Assistant is connected and ready to analyze your website scans.</span>
                                </div>
                            `;
                        }
                    } else {
                        if (outputBox) {
                            outputBox.innerHTML = `
                                <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 14px; border-radius: 8px;">
                                    <strong style="display: block; margin-bottom: 4px; font-size: 14px;">✕ Connection Needed</strong>
                                    <span>AI Assistant is not configured yet. You can configure AI settings in Account Settings -> Connected Accounts.</span>
                                </div>
                            `;
                        }
                    }
                } catch (err) {
                    if (outputBox) {
                        outputBox.innerHTML = `
                            <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 14px; border-radius: 8px;">
                                <strong>✕ Connection Error:</strong> Unable to test AI connection right now.
                            </div>
                        `;
                    }
                } finally {
                    btnTest.disabled = false;
                    btnTest.innerHTML = origText;
                }
            });
        }

        if (btnAnalyze) {
            btnAnalyze.addEventListener('click', async (e) => {
                e.preventDefault();
                const selectedProjId = projectStore.getSelectedProjectId();

                if (!selectedProjId) {
                    alert('Please select a website first.');
                    return;
                }

                btnAnalyze.disabled = true;
                const origText = btnAnalyze.innerHTML;
                btnAnalyze.innerText = 'Analyzing Scan Data...';

                if (outputBox) {
                    outputBox.innerHTML = `
                        <div style="padding: 24px; text-align: center; color: var(--primary);">
                            <span class="crawl-spinner" style="width: 20px; height: 20px; border-width: 3px; display: inline-block; vertical-align: middle; margin-right: 8px;"></span>
                            Reviewing scan metrics, health findings, and page signals with AI Assistant...
                        </div>
                    `;
                }

                try {
                    const res = await apiClient.post(`/api/projects/${selectedProjId}/ai/analyze`, {});
                    if (res.status === 'AI_ANALYSIS_COMPLETE' && outputBox) {
                        const insights = res.insights || [];
                        const actions = res.actions || [];

                        let insightsHTML = insights.map(i => `
                            <div style="margin-bottom: 12px; padding: 12px; background: var(--bg-card); border-radius: 8px; border-left: 3px solid ${i.severity === 'Critical' ? '#ef4444' : '#f59e0b'}; border-top: 1px solid var(--border); border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                    <strong style="color: var(--text-primary); font-size: 13.5px;">${this.escapeHtml(i.finding || i.title || 'Finding')}</strong>
                                    <span class="badge ${i.severity === 'Critical' ? 'badge-critical' : 'badge-warning'}" style="font-size: 10px;">${i.severity}</span>
                                </div>
                                <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">${this.escapeHtml(i.impact || i.details || '')}</div>
                                <div style="font-size: 12px; color: #10b981; font-weight: 600;">Recommended Action: ${this.escapeHtml(i.recommendation || '')}</div>
                            </div>
                        `).join('');

                        outputBox.innerHTML = `
                            <div style="color: var(--text-primary);">
                                <div style="font-size: 14px; font-weight: 700; color: #3b82f6; margin-bottom: 8px;">Summary & Recommendations</div>
                                <p style="font-size: 13px; line-height: 1.5; color: var(--text-primary); margin-bottom: 12px;">${this.escapeHtml(res.summary || 'Analysis completed.')}</p>
                                ${insights.length > 0 ? `<div style="margin-top: 12px;">${insightsHTML}</div>` : ''}
                            </div>
                        `;
                    }
                } catch (err) {
                    if (outputBox) {
                        outputBox.innerHTML = `
                            <div style="padding: 14px; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; border-radius: 8px;">
                                <strong>✕ Analysis Error:</strong> ${this.escapeHtml(err.message || 'Unable to complete AI analysis.')}
                            </div>
                        `;
                    }
                } finally {
                    btnAnalyze.disabled = false;
                    btnAnalyze.innerHTML = origText;
                }
            });
        }
    }

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
                this.renderPortfolioTable();
            });
        }
    }

    bindTrendPills() {
        const container = this.element.querySelector('#trend-timeframe-pills');
        if (!container) return;

        const pills = container.querySelectorAll('.pill-btn');
        pills.forEach(pill => {
            pill.addEventListener('click', (e) => {
                pills.forEach(p => p.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.trendTimeframe = e.currentTarget.getAttribute('data-tf');
            });
        });
    }

    renderPortfolioTable() {
        const container = this.element.querySelector('#portfolio-table-container');
        if (!container) return;

        let list = [...this.allProjects];

        if (this.searchQuery) {
            list = list.filter(p => (p.name || '').toLowerCase().includes(this.searchQuery) || (p.domain || '').toLowerCase().includes(this.searchQuery));
        }

        if (this.statusFilter !== 'all') {
            list = list.filter(p => (p.status || 'Never Crawled') === this.statusFilter);
        }

        if (this.sortOption === 'health_desc') {
            list.sort((a, b) => (b.health_score || 0) - (a.health_score || 0));
        } else if (this.sortOption === 'health_asc') {
            list.sort((a, b) => (a.health_score || 0) - (b.health_score || 0));
        } else if (this.sortOption === 'name_asc') {
            list.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        } else if (this.sortOption === 'issues_desc') {
            list.sort((a, b) => (a.critical_issues_count || 0) - (b.critical_issues_count || 0));
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
            const hScore = p.health_score !== undefined ? p.health_score : 100;
            const healthColor = hScore >= 80 ? '#10b981' : (hScore >= 60 ? '#f59e0b' : '#ef4444');
            const st = p.status || 'Never Scanned';
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
                        <div style="font-size: 15px; font-weight: 800; color: ${healthColor};">${hScore}<span style="font-size: 11px; font-weight: 600; color: var(--text-tertiary);">/100</span></div>
                    </td>
                    <td style="padding: 14px 20px; font-weight: 600;">${p.pages_crawled || 0}</td>
                    <td style="padding: 14px 20px;">
                        <span style="font-weight: 700; color: ${(p.critical_issues_count || 0) > 0 ? '#ef4444' : '#10b981'};">${p.critical_issues_count || 0}</span>
                    </td>
                    <td style="padding: 14px 20px; font-size: 12px; color: var(--text-secondary);">${p.last_crawled_at ? p.last_crawled_at.split('T')[0] : 'Never'}</td>
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
