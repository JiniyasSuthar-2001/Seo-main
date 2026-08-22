import { projectStore } from '../core/projectStore.js';
import { crawlService } from '../services/crawlService.js';
import { apiClient } from '../services/apiClient.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';

export class Opportunities {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'opportunities-view';
        this.activeTab = 'all';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">SEO Growth Opportunities</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">High-impact optimization recommendations derived from website crawls, technical audits, and keyword gaps.</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">
                    Run Crawl Analysis
                </button>
            </div>

            <!-- OPPORTUNITIES CATEGORY TABS -->
            <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 24px; flex-wrap: wrap;" id="opp-tabs">
                <button class="opp-tab active" data-tab="all">All Opportunities</button>
                <button class="opp-tab" data-tab="technical">Technical Fixes</button>
                <button class="opp-tab" data-tab="content">Content & Meta</button>
                <button class="opp-tab" data-tab="keywords">Keyword Gaps</button>
                <button class="opp-tab" data-tab="links">Internal Link Optimization</button>
            </div>

            <div id="opportunities-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Analyzing website opportunities...
                </div>
            </div>

            <style>
                .opp-tab {
                    padding: 8px 16px;
                    border: none;
                    background: transparent;
                    color: var(--text-secondary);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    border-bottom: 2px solid transparent;
                    transition: all 0.15s ease;
                }
                .opp-tab:hover {
                    color: var(--text-primary);
                }
                .opp-tab.active {
                    color: var(--primary);
                    border-bottom-color: var(--primary);
                }
            </style>
        `;

        this.initTabListeners();
        return this.element;
    }

    initTabListeners() {
        setTimeout(() => {
            const tabs = this.element.querySelectorAll('.opp-tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    tabs.forEach(t => t.classList.remove('active'));
                    e.target.classList.add('active');
                    this.activeTab = e.target.dataset.tab;
                    this.mounted();
                });
            });
        }, 50);
    }

    async mounted() {
        const container = document.getElementById('opportunities-content');
        if (!container) return;

        try {
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create an SEO project workspace.</div>`;
                return;
            }

            // Fetch technical audit & summary data
            const techRes = await apiClient.get(`/api/projects/${projectId}/technical?limit=100`);
            const techIssues = techRes.issues || techRes || [];
            
            const pagesRes = await apiClient.get(`/api/projects/${projectId}/pages?limit=100`);
            const pages = pagesRes.pages || pagesRes || [];

            const keywordsRes = await apiClient.get(`/api/projects/${projectId}/keywords?limit=100`);
            const keywords = keywordsRes.keywords || keywordsRes || [];

            let opportunities = [];

            // 1. Technical Audit Opportunities
            techIssues.forEach(issue => {
                const count = issue.affected_pages_count || (issue.affected_pages ? issue.affected_pages.length : 1);
                opportunities.push({
                    category: 'technical',
                    title: issue.title || issue.issue_type || 'Technical Audit Finding',
                    description: issue.description || 'Audit recommendation requires attention.',
                    impact: (issue.severity === 'critical' || issue.severity === 'error') ? 'HIGH' : (issue.severity === 'warning' ? 'MEDIUM' : 'LOW'),
                    affected_count: count,
                    action_label: 'Fix Technical Issue',
                    link: '/technical'
                });
            });

            // 2. Content Opportunities (Missing titles, short content)
            const missingTitles = pages.filter(p => !p.title || p.title.trim() === '');
            if (missingTitles.length > 0) {
                opportunities.push({
                    category: 'content',
                    title: 'Pages Missing HTML Title Tags',
                    description: `${missingTitles.length} pages are missing primary title tags, impacting search engine indexing.`,
                    impact: 'HIGH',
                    affected_count: missingTitles.length,
                    action_label: 'View Pages',
                    link: '/pages'
                });
            }

            const missingDesc = pages.filter(p => !p.meta_description || p.meta_description.trim() === '');
            if (missingDesc.length > 0) {
                opportunities.push({
                    category: 'content',
                    title: 'Pages Missing Meta Descriptions',
                    description: `${missingDesc.length} pages lack meta descriptions for search snippet optimization.`,
                    impact: 'MEDIUM',
                    affected_count: missingDesc.length,
                    action_label: 'View Pages',
                    link: '/pages'
                });
            }

            // 3. Keyword Opportunities
            if (keywords.length > 0) {
                const unranked = keywords.filter(k => !k.position || k.position > 20);
                if (unranked.length > 0) {
                    opportunities.push({
                        category: 'keywords',
                        title: 'Tracked Keywords Outside Top 20',
                        description: `${unranked.length} target keywords are outside the top 20 rankings. On-page optimization recommended.`,
                        impact: 'HIGH',
                        affected_count: unranked.length,
                        action_label: 'View Keywords',
                        link: '/keywords'
                    });
                }
            }

            // 4. Filter by active tab
            if (this.activeTab !== 'all') {
                opportunities = opportunities.filter(o => o.category === this.activeTab);
            }

            if (opportunities.length === 0) {
                container.innerHTML = `
                    <div class="card" style="padding: 32px; border-left: 4px solid var(--primary); text-align: center;">
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">No ${this.activeTab !== 'all' ? this.activeTab.toUpperCase() : ''} Opportunities Detected</div>
                        <p style="color: var(--text-secondary); font-size: 14px; max-width: 600px; margin: 0 auto 16px;">
                            Run a fresh website crawl or connect Google Search Console to detect actionable SEO growth opportunities for <strong>${selectedProj.name}</strong>.
                        </p>
                        <button class="btn btn-primary btn-sm" onclick="window.startCrawl()">Run Website Crawl</button>
                    </div>
                `;
            } else {
                const cards = opportunities.map(opp => {
                    const impactColor = opp.impact === 'HIGH' ? 'var(--critical, #ef4444)' : (opp.impact === 'MEDIUM' ? 'var(--warning, #f59e0b)' : 'var(--primary)');
                    return `
                        <div class="card" style="padding: 20px; border-left: 4px solid ${impactColor}; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap;">
                            <div style="flex: 1; min-width: 280px;">
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                                    <span style="font-weight: 700; font-size: 15px;">${opp.title}</span>
                                    <span class="badge" style="background: rgba(239,68,68,0.1); color: ${impactColor}; font-size: 10px; font-weight: 700;">${opp.impact} IMPACT</span>
                                    <span class="badge badge-info" style="font-size: 10px;">${opp.affected_count} ${opp.affected_count === 1 ? 'page' : 'pages'}</span>
                                </div>
                                <p style="font-size: 13px; color: var(--text-secondary); margin: 0;">${opp.description}</p>
                            </div>
                            <div>
                                <a href="${opp.link}" data-link class="btn btn-secondary btn-sm">${opp.action_label} &rarr;</a>
                            </div>
                        </div>
                    `;
                }).join('');

                container.innerHTML = `
                    <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center;">
                        <span>Showing <strong>${opportunities.length}</strong> action items derived from website crawl snapshot</span>
                    </div>
                    ${cards}
                `;
            }

        } catch (e) {
            if (e.isNetworkError || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Opportunities Load Error", e.message || "Unable to load SEO opportunities.", () => this.mounted());
            }
        }
    }
}
