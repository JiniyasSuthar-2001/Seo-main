import { dashboardService } from '../services/dashboard.js';
import { crawlService } from '../services/crawlService.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { API_BASE_URL } from '../config/api.js';
import { crawlConfigModal } from '../components/CrawlConfigModal.js';
import { renderAIBadge, renderSourceBadge, renderViewEvidenceButton } from '../components/AIBadge.js';

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
        this.geminiStatus = { configured: false, available: false };
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
                        <button class="btn btn-primary btn-lg" onclick="window.showCreateProjectModal()" style="font-weight: 600;">+ Create First Project</button>
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
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.06em;">SEO INTELLIGENCE DASHBOARD</div>
                        <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px; color: var(--text-primary);">Workspace Command Center</h1>
                        <p style="color: var(--text-secondary); font-size: 13.5px; margin-top: 4px;">Real-time portfolio SEO health metrics, crawl progress, and AI recommendations.</p>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-primary btn-sm" onclick="window.showCreateProjectModal()" style="display: inline-flex; align-items: center; gap: 6px;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                            Add Website
                        </button>
                    </div>
                </div>

                <!-- LEVEL 1: ACCOUNT PORTFOLIO SUMMARY CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px;">
                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Portfolio Websites</div>
                            <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: var(--bg-subtle); color: var(--text-tertiary); border: 1px solid var(--border);">Active Projects</span>
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: var(--text-primary);">${totalSites}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Active projects in workspace</div>
                    </div>

                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Average SEO Health</div>
                            <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: var(--bg-subtle); color: var(--primary); border: 1px solid var(--border);">Crawled Data</span>
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: ${avgHealth >= 80 ? '#10b981' : (avgHealth >= 60 ? '#f59e0b' : '#ef4444')};">${avgHealth}<span style="font-size: 16px; font-weight: 600;">/100</span></div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Weighted portfolio audit score</div>
                    </div>

                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Total Crawled Pages</div>
                            <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: var(--bg-subtle); color: var(--primary); border: 1px solid var(--border);">Crawled Data</span>
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: #3b82f6;">${totalCrawledPages.toLocaleString()}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Discovered HTML pages</div>
                    </div>

                    <div class="card" style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Critical Audit Issues</div>
                            <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: var(--bg-subtle); color: var(--primary); border: 1px solid var(--border);">Crawled Data</span>
                        </div>
                        <div style="font-size: 28px; font-weight: 800; color: ${totalIssuesCount > 0 ? '#ef4444' : '#10b981'};">${totalIssuesCount}</div>
                        <div style="font-size: 12px; color: var(--text-tertiary); margin-top: 4px;">Aggregated technical findings</div>
                    </div>
                </div>

                <!-- LEVEL 2: WEBSITE PORTFOLIO TABLE -->
                <div class="card" style="padding: 24px; margin-bottom: 28px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h2 style="font-size: 18px; font-weight: 700; margin: 0; color: var(--text-primary);">Website Portfolio</h2>
                            <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">Manage and monitor technical health across all websites in your workspace.</div>
                        </div>

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

                    <div id="portfolio-table-container"></div>
                </div>

                <!-- DYNAMIC AI INTEGRATION SECTION -->
                <div class="card" style="padding: 24px; margin-bottom: 28px; border-left: 4px solid #3b82f6; background: var(--bg-card);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <h3 style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary);" id="ai-card-title">AI Intelligence Engine</h3>
                                <span id="gemini-status-badge" class="badge badge-secondary" style="font-size: 11px;">Checking status...</span>
                            </div>
                            <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 4px;" id="ai-card-subtext">
                                High-performance LLM reasoning engine for automated SEO analysis using real workspace crawl evidence.
                            </div>
                        </div>

                        <div style="display: flex; gap: 10px;" id="gemini-actions">
                            <button type="button" id="btn-test-gemini" class="btn btn-secondary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                                ⚡ Test Connection
                            </button>
                            <button type="button" id="btn-analyze-gemini" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 6px; background: #2563eb;">
                                ✨ Analyze SEO with AI
                            </button>
                        </div>
                    </div>

                    <!-- AI OUTPUT / RESULT BOX -->
                    <div id="gemini-output-box" style="padding: 16px; background: var(--bg-subtle); border-radius: 10px; border: 1px solid var(--border); font-size: 13px; color: var(--text-secondary);">
                        <div id="gemini-default-msg">
                            Click <strong id="ai-test-btn-label">Test Connection</strong> to verify backend API configuration or <strong id="ai-analyze-btn-label">Analyze SEO with AI</strong> to run real AI audit reasoning on your active project.
                        </div>
                    </div>
                </div>

                <!-- WORKSPACE HEALTH TREND & ANALYTICS VISUALIZATION -->
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

                <!-- TOP TECHNICAL SEO ISSUES -->
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
            `;

            this.bindPortfolioControls();
            this.renderPortfolioTable();
            this.bindTrendPills();
            await this.bindGeminiSection();

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(this.element, `Unable to connect to backend API server at ${API_BASE_URL}.`, () => this.mounted());
            } else {
                renderFeatureErrorState(this.element, "Workspace Overview Error", e.message || "Failed to load workspace overview metrics.", () => this.mounted());
            }
        }
    }

    async bindGeminiSection() {
        const titleEl = this.element.querySelector('#ai-card-title');
        const subtextEl = this.element.querySelector('#ai-card-subtext');
        const badge = this.element.querySelector('#gemini-status-badge');
        const btnTest = this.element.querySelector('#btn-test-gemini');
        const btnAnalyze = this.element.querySelector('#btn-analyze-gemini');
        const outputBox = this.element.querySelector('#gemini-output-box');

        let activeProvider = "groq";
        let testEndpoint = "/api/ai/groq/test";

        try {
            const statusData = await apiClient.get('/api/ai/status');
            this.aiStatus = statusData;
            activeProvider = (statusData.provider || "groq").toLowerCase();

            let providerTitle = "Groq AI Intelligence";
            if (activeProvider === 'gemini') {
                providerTitle = "Google Gemini AI Intelligence";
                testEndpoint = "/api/ai/gemini/test";
            } else if (activeProvider === 'ollama') {
                providerTitle = "Ollama Local AI Intelligence";
                testEndpoint = "/api/ai/ollama/test";
            } else if (activeProvider === 'openai') {
                providerTitle = "OpenAI Intelligence";
                testEndpoint = "/api/ai/status";
            } else if (activeProvider === 'groq') {
                providerTitle = "Groq AI Intelligence";
                testEndpoint = "/api/ai/groq/test";
            }

            if (titleEl) titleEl.innerText = providerTitle;
            if (btnTest) btnTest.innerText = `⚡ Test ${providerTitle.split(' ')[0]} Connection`;
            if (btnAnalyze) btnAnalyze.innerText = `✨ Analyze SEO with ${providerTitle.split(' ')[0]}`;

            if (badge) {
                if (statusData && statusData.configured) {
                    badge.className = 'badge badge-success';
                    badge.innerHTML = `✓ Available (${statusData.model || 'active'})`;
                } else {
                    badge.className = 'badge badge-secondary';
                    badge.innerHTML = `Not Configured`;
                }
            }
        } catch (err) {
            console.warn('[AI UI] Failed to check status:', err);
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
                                    <span>Provider: <code>${testRes.provider || activeProvider}</code> • Model: <code>${testRes.model || 'active'}</code> • ${this.escapeHtml(testRes.message || 'AI engine is connected.')}</span>
                                </div>
                            `;
                        }
                    } else {
                        if (outputBox) {
                            outputBox.innerHTML = `
                                <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 14px; border-radius: 8px;">
                                    <strong style="display: block; margin-bottom: 4px; font-size: 14px;">✕ Connection Failed</strong>
                                    <span>${this.escapeHtml(testRes.message || 'AI API provider is not configured in environment.')}</span>
                                </div>
                            `;
                        }
                    }
                } catch (err) {
                    if (outputBox) {
                        outputBox.innerHTML = `
                            <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 14px; border-radius: 8px;">
                                <strong>✕ Connection Error:</strong> ${this.escapeHtml(err.message || 'Unable to test AI provider connection.')}
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
                    alert('Please select a project to run AI analysis.');
                    return;
                }

                btnAnalyze.disabled = true;
                const origText = btnAnalyze.innerHTML;
                btnAnalyze.innerText = 'Analyzing Real Evidence...';

                if (outputBox) {
                    outputBox.innerHTML = `
                        <div style="padding: 24px; text-align: center; color: var(--primary);">
                            <span class="crawl-spinner" style="width: 20px; height: 20px; border-width: 3px; display: inline-block; vertical-align: middle; margin-right: 8px;"></span>
                            Evaluating crawl metrics, technical findings, and content signals with Gemini AI...
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
                                <div style="font-size: 12px; color: #10b981; font-weight: 600;">Recommendation: ${this.escapeHtml(i.recommendation || '')}</div>
                            </div>
                        `).join('');

                        let actionsHTML = actions.map(a => `
                            <div style="padding: 8px 12px; background: var(--bg-card); border-radius: 6px; border: 1px solid var(--border); font-size: 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <strong style="color: var(--text-primary);">${this.escapeHtml(a.title || 'Action')}</strong>
                                    <div style="color: var(--text-secondary); font-size: 11.5px;">${this.escapeHtml(a.description || '')}</div>
                                </div>
                                <span class="badge badge-primary" style="font-size: 10px;">${a.priority || 'High'}</span>
                            </div>
                        `).join('');

                        const domainEv = selectedProj ? (selectedProj.domain || selectedProj.url) : 'Target Domain';
                        const summaryEvidence = [
                            { label: 'Target Domain', value: domainEv, source: 'Crawled Data' },
                            { label: 'Pages Analyzed', value: `${res.total_pages_analyzed || 'Crawl snapshot'} pages`, source: 'Crawled Data' },
                            { label: 'Audit Timestamp', value: res.timestamp || new Date().toISOString().split('T')[0], source: 'Crawled Data' }
                        ];

                        outputBox.innerHTML = `
                            <div style="color: var(--text-primary);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <div style="font-size: 14px; font-weight: 700; color: #3b82f6;">Executive Summary</div>
                                    ${renderAIBadge('analysis')}
                                </div>
                                <p style="font-size: 13px; line-height: 1.5; color: var(--text-primary); margin-bottom: 10px;">${this.escapeHtml(res.summary || 'Analysis completed successfully.')}</p>
                                ${renderViewEvidenceButton(summaryEvidence, 'dash-summary-ev')}

                                ${insights.length > 0 ? `
                                    <div style="font-size: 13px; font-weight: 700; margin: 20px 0 10px; color: var(--text-primary); display: flex; justify-content: space-between; align-items: center;">
                                        <span>Key Audit Insights (${insights.length})</span>
                                        ${renderAIBadge('assisted')}
                                    </div>
                                    <div style="margin-bottom: 16px;">${insightsHTML}</div>
                                ` : ''}

                                ${actions.length > 0 ? `
                                    <div style="font-size: 13px; font-weight: 700; margin: 20px 0 10px; color: var(--text-primary); display: flex; justify-content: space-between; align-items: center;">
                                        <span>Recommended Actions (${actions.length})</span>
                                        ${renderAIBadge('assisted')}
                                    </div>
                                    <div>${actionsHTML}</div>
                                ` : ''}
                            </div>
                        `;

                    } else if (outputBox) {
                        outputBox.innerHTML = `
                            <div style="padding: 14px; background: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.3); color: #f59e0b; border-radius: 8px;">
                                <strong>Notice:</strong> ${this.escapeHtml(res.message || res.summary || 'Gemini AI analysis is currently unavailable.')}
                            </div>
                        `;
                    }
                } catch (err) {
                    if (outputBox) {
                        outputBox.innerHTML = `
                            <div style="padding: 14px; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; border-radius: 8px;">
                                <strong>✕ Analysis Failed:</strong> ${this.escapeHtml(err.message || 'Unable to complete AI analysis.')}
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
            list.sort((a, b) => (b.critical_issues_count || 0) - (a.critical_issues_count || 0));
        }

        if (list.length === 0) {
            container.innerHTML = `
                <div style="padding: 32px; text-align: center; color: var(--text-secondary); font-size: 13.5px;">
                    No websites match your filter query '${this.escapeHtml(this.searchQuery)}'.
                </div>
            `;
            return;
        }

        const rows = list.map(p => {
            const hScore = p.health_score !== undefined ? p.health_score : 100;
            const healthColor = hScore >= 80 ? '#10b981' : (hScore >= 60 ? '#f59e0b' : '#ef4444');
            const st = p.status || 'Never Crawled';
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
                            <button class="btn btn-secondary btn-sm" onclick="window.startCrawlFromOverview('${p.id}', '${p.domain || p.url}')" style="font-size: 11px; padding: 4px 10px;">Crawl</button>
                            <button class="btn btn-primary btn-sm" onclick="window.navigateToAudit('${p.id}')" style="font-size: 11px; padding: 4px 10px;">Audit &rarr;</button>
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
                            <th style="padding: 12px 20px;">SEO Health</th>
                            <th style="padding: 12px 20px;">Pages</th>
                            <th style="padding: 12px 20px;">Critical Issues</th>
                            <th style="padding: 12px 20px;">Last Crawled</th>
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
