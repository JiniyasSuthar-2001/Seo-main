import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';


export class Keywords {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'keywords-view';
        this.activeTab = 'overview';
        this.researchResults = [];
        this.isSearching = false;
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700;">Keyword Intelligence Workspace</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Explore keyword opportunities, research search terms, organize semantic topic groups, and track keyword rankings.</p>
                </div>
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-secondary btn-sm" id="btn-auto-cluster">⚡ Auto-Cluster Groups</button>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Run Crawl</button>
                </div>
            </div>

            <!-- KEYWORD INTELLIGENCE SUB-TABS -->
            <div style="display: flex; gap: 6px; border-bottom: 1px solid var(--border); margin-bottom: 24px; flex-wrap: wrap;" id="kw-tabs-nav">
                <button class="kw-tab active" data-tab="overview">Overview</button>
                <button class="kw-tab" data-tab="research">Keyword Research</button>
                <button class="kw-tab" data-tab="groups">Keyword Groups</button>
                <button class="kw-tab" data-tab="opportunities">Opportunities</button>
                <button class="kw-tab" data-tab="ranking">Ranking Keywords</button>
                <button class="kw-tab" data-tab="gap">Keyword Gap</button>
            </div>

            <div id="kw-tab-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading Keyword Intelligence workspace...
                </div>
            </div>

            <style>
                .kw-tab {
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
                .kw-tab:hover {
                    color: var(--text-primary);
                }
                .kw-tab.active {
                    color: var(--primary);
                    border-bottom-color: var(--primary);
                }
                .source-tag {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 700;
                    background: var(--bg-subtle);
                    color: var(--text-secondary);
                    border: 1px solid var(--border);
                }
            </style>
        `;

        this.initTabListeners();
        return this.element;
    }

    initTabListeners() {
        setTimeout(() => {
            const tabs = this.element.querySelectorAll('.kw-tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    tabs.forEach(t => t.classList.remove('active'));
                    e.target.classList.add('active');
                    this.activeTab = e.target.dataset.tab;
                    this.mounted();
                });
            });

            const clusterBtn = this.element.querySelector('#btn-auto-cluster');
            if (clusterBtn) {
                clusterBtn.addEventListener('click', () => this.handleAutoCluster());
            }
        }, 50);
    }

    async handleAutoCluster() {
        const projectId = resolveProjectId();
        if (!projectId) return;
        try {
            const res = await apiClient.post(`/api/projects/${projectId}/keywords/groups/auto-cluster`, {});
            alert(res.message || "Auto-clustering complete.");
            this.mounted();
        } catch (e) {
            alert(`Auto-clustering error: ${e.message}`);
        }
    }

    async mounted() {
        const container = document.getElementById('kw-tab-content');
        if (!container) return;

        const projectId = resolveProjectId();
        const selectedProj = projectStore.getSelectedProject();


        if (!projectId || !selectedProj) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select an SEO project workspace.</div>`;
            return;
        }

        try {
            if (this.activeTab === 'overview') {
                await this.renderOverviewTab(container, projectId, selectedProj);
            } else if (this.activeTab === 'research') {
                this.renderResearchTab(container, projectId, selectedProj);
            } else if (this.activeTab === 'groups') {
                await this.renderGroupsTab(container, projectId);
            } else if (this.activeTab === 'opportunities') {
                await this.renderOpportunitiesTab(container, projectId);
            } else if (this.activeTab === 'ranking') {
                await this.renderRankingKeywordsTab(container, projectId);
            } else if (this.activeTab === 'gap') {
                await this.renderKeywordGapTab(container, projectId);
            }
        } catch (e) {
            if (e.isNetworkError || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Keywords Load Error", e.message || "Failed to load keyword intelligence.", () => this.mounted());
            }
        }
    }

    // 1. OVERVIEW SUB-TAB
    async renderOverviewTab(container, projectId, project) {
        const res = await apiClient.get(`/api/projects/${projectId}/keywords?limit=100`);
        const keywords = res.keywords || [];

        const totalKws = keywords.length;
        const top3 = keywords.filter(k => k.position && k.position <= 3).length;
        const top10 = keywords.filter(k => k.position && k.position <= 10).length;
        const top20 = keywords.filter(k => k.position && k.position <= 20).length;

        const groupsRes = await apiClient.get(`/api/projects/${projectId}/keywords/groups`);
        const groups = groupsRes.groups || [];

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div class="kpi-card">
                    <div class="kpi-label">Total Keywords</div>
                    <div class="kpi-value">${totalKws}</div>
                    <div class="kpi-status">Tracked terms</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Top 3 Keywords</div>
                    <div class="kpi-value" style="color: var(--success, #10b981);">${top3}</div>
                    <div class="kpi-status">Position 1-3</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Top 10 Keywords</div>
                    <div class="kpi-value" style="color: var(--primary);">${top10}</div>
                    <div class="kpi-status">Page 1 results</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Top 20 Keywords</div>
                    <div class="kpi-value">${top20}</div>
                    <div class="kpi-status">Striking distance</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Keyword Groups</div>
                    <div class="kpi-value">${groups.length}</div>
                    <div class="kpi-status">Topic clusters</div>
                </div>
            </div>

            <div class="card" style="padding: 24px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div>
                        <h3 style="font-size: 16px; font-weight: 700;">Extracted Content Terms</h3>
                        <div style="font-size: 12px; color: var(--text-secondary);">Extracted from website HTML titles, meta tags, and headings via Local Open-Source NLP</div>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="document.querySelector('[data-tab=research]').click()">Search Autocomplete Ideas &rarr;</button>
                </div>
                
                ${keywords.length === 0 ? `
                    <div style="text-align: center; padding: 24px; color: var(--text-secondary);">
                        No keyword data extracted yet. Run a website crawl or use the Keyword Research tab to find terms.
                    </div>
                ` : `
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 14px;">Keyword Phrase</th>
                                <th style="padding: 10px 14px;">Group</th>
                                <th style="padding: 10px 14px;">Search Volume</th>
                                <th style="padding: 10px 14px;">CPC</th>
                                <th style="padding: 10px 14px;">Position</th>
                                <th style="padding: 10px 14px; text-align: right;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${keywords.slice(0, 15).map(k => `
                                <tr style="border-bottom: 1px solid var(--border);">
                                    <td style="padding: 10px 14px; font-weight: 600;">${k.keyword}</td>
                                    <td style="padding: 10px 14px;"><span class="badge badge-info" style="font-size: 11px;">${k.group_name}</span></td>
                                    <td style="padding: 10px 14px; color: var(--text-secondary);">${k.search_volume}</td>
                                    <td style="padding: 10px 14px; color: var(--text-secondary);">${k.cpc}</td>
                                    <td style="padding: 10px 14px; font-weight: 700; color: var(--primary);">${k.position ? '#' + k.position : 'Unranked'}</td>
                                    <td style="padding: 10px 14px; text-align: right;"><span class="source-tag">${k.source}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `}
            </div>
        `;
    }

    // 2. RESEARCH SUB-TAB
    renderResearchTab(container, projectId, project) {
        container.innerHTML = `
            <div class="card" style="padding: 24px; margin-bottom: 24px;">
                <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">Google Autocomplete Keyword Research</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">
                    Search real-time Google Autocomplete suggestions. Note: Search Volume, CPC, and Difficulty without a connected provider return <strong>Unavailable</strong> in accordance with strict data integrity rules.
                </p>

                <form id="kw-research-form" style="display: flex; gap: 12px; flex-wrap: wrap; align-items: flex-end; margin-bottom: 20px;">
                    <div style="flex: 2; min-width: 240px;">
                        <label style="font-size: 12px; font-weight: 600; display: block; margin-bottom: 4px;">Seed Keyword Phrase</label>
                        <input type="text" id="seed-input" placeholder="e.g. solar panels, seo audit, web development" required style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                    </div>
                    <div style="flex: 1; min-width: 120px;">
                        <label style="font-size: 12px; font-weight: 600; display: block; margin-bottom: 4px;">Country</label>
                        <select id="country-input" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                            <option value="US">United States</option>
                            <option value="AU">Australia</option>
                            <option value="UK">United Kingdom</option>
                            <option value="CA">Canada</option>
                        </select>
                    </div>
                    <div style="flex: 1; min-width: 120px;">
                        <label style="font-size: 12px; font-weight: 600; display: block; margin-bottom: 4px;">Language</label>
                        <select id="lang-input" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                            <option value="en">English</option>
                            <option value="es">Spanish</option>
                            <option value="fr">French</option>
                        </select>
                    </div>
                    <div style="flex: 1; min-width: 120px;">
                        <label style="font-size: 12px; font-weight: 600; display: block; margin-bottom: 4px;">Device</label>
                        <select id="device-input" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                            <option value="desktop">Desktop</option>
                            <option value="mobile">Mobile</option>
                        </select>
                    </div>
                    <div>
                        <button type="submit" class="btn btn-primary" style="padding: 8px 20px;">Search Ideas</button>
                    </div>
                </form>

                <div id="research-results-container">
                    <div style="text-align: center; padding: 32px; color: var(--text-secondary); font-size: 13px;">
                        Enter a seed keyword phrase above to fetch live search engine autocomplete ideas.
                    </div>
                </div>
            </div>
        `;

        const form = container.querySelector('#kw-research-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const seed = container.querySelector('#seed-input').value;
            const country = container.querySelector('#country-input').value;
            const lang = container.querySelector('#lang-input').value;
            const device = container.querySelector('#device-input').value;

            const resDiv = container.querySelector('#research-results-container');
            resDiv.innerHTML = `<div style="text-align: center; padding: 24px; color: var(--text-secondary);">Querying Google Autocomplete API...</div>`;

            try {
                const res = await apiClient.get(`/api/projects/${projectId}/keywords/research?q=${encodeURIComponent(seed)}&country=${country}&language=${lang}&device=${device}`);
                const suggestions = res.results || [];

                if (suggestions.length === 0) {
                    resDiv.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-secondary);">No suggestions returned for query '${seed}'.</div>`;
                } else {
                    const rows = suggestions.map(item => `
                        <tr style="border-bottom: 1px solid var(--border);">
                            <td style="padding: 10px 14px; font-weight: 600;">${item.keyword}</td>
                            <td style="padding: 10px 14px; color: var(--text-tertiary);">${item.search_volume}</td>
                            <td style="padding: 10px 14px; color: var(--text-tertiary);">${item.cpc}</td>
                            <td style="padding: 10px 14px; color: var(--text-tertiary);">${item.difficulty}</td>
                            <td style="padding: 10px 14px;"><span class="badge badge-info" style="font-size: 10px;">${item.intent}</span></td>
                            <td style="padding: 10px 14px; text-align: right;"><span class="source-tag">${item.source}</span></td>
                        </tr>
                    `).join('');

                    resDiv.innerHTML = `
                        <div style="margin-bottom: 12px; font-size: 12px; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center;">
                            <span>Found <strong>${suggestions.length}</strong> real-time autocomplete suggestions for '<strong>${seed}</strong>'</span>
                            <span class="source-tag">Google Autocomplete API</span>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 10px 14px;">Suggested Keyword</th>
                                    <th style="padding: 10px 14px;">Search Volume</th>
                                    <th style="padding: 10px 14px;">CPC</th>
                                    <th style="padding: 10px 14px;">Difficulty</th>
                                    <th style="padding: 10px 14px;">Intent</th>
                                    <th style="padding: 10px 14px; text-align: right;">Data Source</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    `;
                }
            } catch (err) {
                resDiv.innerHTML = `<div style="padding: 20px; color: var(--critical);">Failed to query autocomplete API: ${err.message}</div>`;
            }
        });
    }

    // 3. GROUPS SUB-TAB
    async renderGroupsTab(container, projectId) {
        const groupsRes = await apiClient.get(`/api/projects/${projectId}/keywords/groups`);
        const groups = groupsRes.groups || [];

        const groupRows = groups.map(g => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 16px; font-weight: 700; color: var(--text-primary);">${g.name}</td>
                <td style="padding: 12px 16px; color: var(--text-secondary); font-size: 13px;">${g.description || 'Semantic topic cluster'}</td>
                <td style="padding: 12px 16px; font-weight: 700; color: var(--primary);">${g.keyword_count} keywords</td>
                <td style="padding: 12px 16px; text-align: right;">
                    <button class="btn btn-secondary btn-sm btn-delete-group" data-id="${g.id}">Delete</button>
                </td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div class="card" style="padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <div>
                        <h3 style="font-size: 16px; font-weight: 700;">Semantic Topic Keyword Groups</h3>
                        <div style="font-size: 12px; color: var(--text-secondary);">Organize keywords into topic clusters for structured content mapping.</div>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-secondary btn-sm" id="btn-create-group-modal">+ Create Group</button>
                        <button class="btn btn-primary btn-sm" id="btn-trigger-cluster">⚡ Auto-Cluster Now</button>
                    </div>
                </div>

                ${groups.length === 0 ? `
                    <div style="text-align: center; padding: 36px; color: var(--text-secondary); border: 1px dashed var(--border); border-radius: 8px;">
                        <p style="margin-bottom: 12px; font-size: 14px;">No keyword groups created yet for this project.</p>
                        <button class="btn btn-primary btn-sm" id="btn-trigger-cluster-2">⚡ Auto-Cluster Existing Keywords</button>
                    </div>
                ` : `
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 16px;">Group Name</th>
                                <th style="padding: 10px 16px;">Description</th>
                                <th style="padding: 10px 16px;">Member Keywords</th>
                                <th style="padding: 10px 16px; text-align: right;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${groupRows}
                        </tbody>
                    </table>
                `}
            </div>
        `;

        const clusterBtns = container.querySelectorAll('#btn-trigger-cluster, #btn-trigger-cluster-2');
        clusterBtns.forEach(b => b.addEventListener('click', () => this.handleAutoCluster()));

        const createBtn = container.querySelector('#btn-create-group-modal');
        if (createBtn) {
            createBtn.addEventListener('click', async () => {
                const name = prompt("Enter new keyword group name:");
                if (name && name.trim()) {
                    await apiClient.post(`/api/projects/${projectId}/keywords/groups`, { name: name.trim() });
                    this.mounted();
                }
            });
        }

        const delBtns = container.querySelectorAll('.btn-delete-group');
        delBtns.forEach(b => {
            b.addEventListener('click', async (e) => {
                const gid = e.target.dataset.id;
                if (confirm("Are you sure you want to delete this keyword group?")) {
                    await apiClient.delete(`/api/projects/groups/${gid}`);
                    this.mounted();
                }
            });
        });
    }

    // 4. OPPORTUNITIES SUB-TAB
    async renderOpportunitiesTab(container, projectId) {
        const res = await apiClient.get(`/api/projects/${projectId}/keywords/opportunities`);
        const opps = res.opportunities || [];

        if (opps.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    No keyword opportunities identified yet. Run a website crawl or add target keywords.
                </div>
            `;
            return;
        }

        const oppCards = opps.map(opp => `
            <div class="card" style="padding: 16px 20px; border-left: 4px solid ${opp.priority === 'HIGH' ? 'var(--critical, #ef4444)' : 'var(--warning, #f59e0b)'}; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-weight: 700; font-size: 15px;">${opp.keyword}</span>
                        <span class="badge badge-info" style="font-size: 10px;">${opp.category}</span>
                        <span class="badge" style="background: rgba(239,68,68,0.1); color: var(--critical); font-size: 10px; font-weight: 700;">${opp.priority} PRIORITY</span>
                    </div>
                    <span style="font-weight: 700; font-size: 13px; color: var(--primary);">Current Rank: ${opp.current_position ? '#' + opp.current_position : 'Unranked'}</span>
                </div>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">${opp.evidence}</p>
                <div style="font-size: 12px; background: var(--bg-subtle); padding: 8px 12px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <span><strong>Recommendation:</strong> ${opp.recommendation}</span>
                    <span class="source-tag">${opp.data_source || 'Crawler'}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = `
            <div style="margin-bottom: 16px; font-size: 13px; color: var(--text-secondary);">
                Identified <strong>${opps.length}</strong> keyword opportunity recommendations based on current SERP positions and landing page coverage:
            </div>
            ${oppCards}
        `;
    }

    // 5. RANKING KEYWORDS SUB-TAB
    async renderRankingKeywordsTab(container, projectId) {
        const res = await apiClient.get(`/api/projects/${projectId}/keywords?limit=100`);
        const keywords = res.keywords || [];

        const rows = keywords.map(k => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 10px 14px; font-weight: 600;">${k.keyword}</td>
                <td style="padding: 10px 14px;"><span class="badge badge-info" style="font-size: 10px;">${k.group_name}</span></td>
                <td style="padding: 10px 14px; font-weight: 700; color: var(--primary);">${k.position ? '#' + k.position : 'Unranked'}</td>
                <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${k.target_url || 'Homepage'}</td>
                <td style="padding: 10px 14px; color: var(--text-tertiary);">${k.search_volume}</td>
                <td style="padding: 10px 14px; color: var(--text-tertiary);">${k.difficulty}</td>
                <td style="padding: 10px 14px; text-align: right;"><span class="source-tag">${k.source}</span></td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div class="card" style="padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="font-size: 16px; font-weight: 700;">Project Tracked Keywords</h3>
                    <span class="source-tag">Database Records</span>
                </div>
                ${keywords.length === 0 ? `
                    <div style="padding: 24px; text-align: center; color: var(--text-secondary);">No keywords stored in project database yet.</div>
                ` : `
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 14px;">Keyword</th>
                                <th style="padding: 10px 14px;">Group</th>
                                <th style="padding: 10px 14px;">Rank</th>
                                <th style="padding: 10px 14px;">Target URL</th>
                                <th style="padding: 10px 14px;">Volume</th>
                                <th style="padding: 10px 14px;">Difficulty</th>
                                <th style="padding: 10px 14px; text-align: right;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                `}
            </div>
        `;
    }

    // 6. KEYWORD GAP SUB-TAB
    async renderKeywordGapTab(container, projectId) {
        const res = await apiClient.get(`/api/projects/${projectId}/competitors/gap-analysis`);
        const gapList = res.keyword_gap || [];
        const competitors = res.confirmed_competitors || [];

        if (competitors.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 32px; text-align: center;">
                    <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">No Confirmed Competitors Configured</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 16px; max-width: 480px; margin-left: auto; margin-right: auto;">
                        Add confirmed competitors in the Competitors workspace to perform keyword gap analysis.
                    </p>
                    <a href="/competitors" data-link class="btn btn-primary btn-sm">+ Add Confirmed Competitors</a>
                </div>
            `;
            return;
        }

        const rows = gapList.map(item => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 10px 14px; font-weight: 600;">${item.keyword}</td>
                <td style="padding: 10px 14px; font-weight: 700; color: var(--primary);">${item.target_position}</td>
                <td style="padding: 10px 14px; font-weight: 700; color: var(--warning);">${item.competitor_position}</td>
                <td style="padding: 10px 14px; color: var(--text-tertiary);">${item.search_volume}</td>
                <td style="padding: 10px 14px;"><span class="badge badge-critical" style="font-size: 10px;">${item.opportunity_level}</span></td>
                <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">${item.recommended_action}</td>
                <td style="padding: 10px 14px; text-align: right;"><span class="source-tag">Competitor Gap Analysis</span></td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div class="card" style="padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div>
                        <h3 style="font-size: 16px; font-weight: 700;">Keyword Gap Analysis</h3>
                        <div style="font-size: 12px; color: var(--text-secondary);">Comparing target domain against ${competitors.length} confirmed competitor(s)</div>
                    </div>
                    <a href="/competitors" data-link class="btn btn-secondary btn-sm">Manage Competitors</a>
                </div>

                ${gapList.length === 0 ? `
                    <div style="padding: 24px; text-align: center; color: var(--text-secondary);">No keyword gap entries found. Add keywords to project database.</div>
                ` : `
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 14px;">Keyword</th>
                                <th style="padding: 10px 14px;">Your Rank</th>
                                <th style="padding: 10px 14px;">Competitor Rank</th>
                                <th style="padding: 10px 14px;">Volume</th>
                                <th style="padding: 10px 14px;">Opportunity</th>
                                <th style="padding: 10px 14px;">Recommendation</th>
                                <th style="padding: 10px 14px; text-align: right;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                `}
            </div>
        `;
    }
}
