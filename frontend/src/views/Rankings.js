import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { GrowthDetailModal } from '../components/GrowthDetailModal.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class Rankings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'rankings-view';
        this.activeTab = 'tracking';
        
        // Tracking filters
        this.rankingsPage = 1;
        this.rankingsSearch = '';
        this.rankingsPosFilter = 'all'; // all, top3, top10, top20, 20plus

        // Winners & Losers filters
        this.winnersTab = 'all'; // all, improved, declined, new, lost
        this.winnersPage = 1;
        this.winnersSearch = '';

        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Search Rankings</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Monitor verified website search engine positions, keyword movement, and ranking changes.</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
            </div>

            <!-- POSITION TRACKING SUB-TABS -->
            <div style="display: flex; gap: 6px; border-bottom: 1px solid var(--border); margin-bottom: 24px; flex-wrap: wrap;" id="rank-tabs-nav">
                <button class="rank-tab ${this.activeTab === 'tracking' ? 'active' : ''}" data-tab="tracking">Search Rankings</button>
                <button class="rank-tab ${this.activeTab === 'winners' ? 'active' : ''}" data-tab="winners">Ranking Changes</button>
                <button class="rank-tab ${this.activeTab === 'config' ? 'active' : ''}" data-tab="config">Settings</button>
            </div>

            <div id="rankings-tab-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading search rankings...
                </div>
            </div>

            <style>
                .rank-tab {
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
                .rank-tab:hover {
                    color: var(--text-primary);
                }
                .rank-tab.active {
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
            const tabs = this.element.querySelectorAll('.rank-tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    tabs.forEach(t => t.classList.remove('active'));
                    e.target.classList.add('active');
                    this.activeTab = e.target.dataset.tab;
                    this.rankingsPage = 1;
                    this.winnersPage = 1;
                    this.mounted();
                });
            });
        }, 50);
    }

    async mounted() {
        const container = document.getElementById('rankings-tab-content');
        if (!container) return;

        await projectStore.ensureInitialized();
        const projectId = resolveProjectId();
        const selectedProj = projectStore.getSelectedProject();

        if (!projectId || !selectedProj) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
            return;
        }

        try {
            if (this.activeTab === 'tracking') {
                await this.renderTrackingTab(container, projectId, selectedProj);
            } else if (this.activeTab === 'winners') {
                await this.renderWinnersTab(container, projectId);
            } else if (this.activeTab === 'config') {
                await this.renderCampaignConfigTab(container, projectId, selectedProj);
            }
        } catch (e) {
            if (e.isNetworkError || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "We couldn't load this information right now. Please try again.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Rankings Load Error", e.message || "Failed to load search rankings.", () => this.mounted());
            }
        }
    }

    // -------------------------------------------------------------------------
    // 1. POSITION TRACKING SUB-TAB
    // -------------------------------------------------------------------------
    async renderTrackingTab(container, projectId, project) {
        const trackingRes = await apiClient.get(`/api/projects/${projectId}/rankings/tracking`);
        const ov = trackingRes.overview || {};
        const config = trackingRes.campaign_config || {};

        const rankRes = await apiClient.get(`/api/projects/${projectId}/rankings?limit=2000`);
        const allRankings = rankRes.rankings || [];

        // Pre-pagination filtering
        let filtered = allRankings;
        if (this.rankingsPosFilter === 'top3') {
            filtered = filtered.filter(r => r.position && r.position <= 3);
        } else if (this.rankingsPosFilter === 'top10') {
            filtered = filtered.filter(r => r.position && r.position <= 10);
        } else if (this.rankingsPosFilter === 'top20') {
            filtered = filtered.filter(r => r.position && r.position <= 20);
        } else if (this.rankingsPosFilter === '20plus') {
            filtered = filtered.filter(r => r.position && r.position > 20);
        }

        if (this.rankingsSearch.trim()) {
            const q = this.rankingsSearch.toLowerCase().trim();
            filtered = filtered.filter(r => {
                const kw = (r.keyword || '').toLowerCase();
                const u = (r.url || r.target_url || '').toLowerCase();
                return kw.includes(q) || u.includes(q);
            });
        }

        const paginated = Pagination.paginateArray(filtered, this.rankingsPage, this.pageSize);
        this.rankingsPage = paginated.currentPage;

        let tableRows = paginated.items.map((r, idx) => {
            const kw = this.escapeHtml(r.keyword);
            const url = this.escapeHtml(r.url || r.target_url || '-');
            const pos = r.position || 'N/A';
            const prev = r.previous_position !== undefined && r.previous_position !== null ? r.previous_position : '-';
            const change = r.change;
            const src = this.escapeHtml(r.data_source || r.provenance || 'Google Search Data');

            let changeHtml = '<span style="color: var(--text-secondary);">-</span>';
            if (change !== undefined && change !== null) {
                if (change > 0) changeHtml = `<span class="badge badge-success" style="font-weight: 700;">+${change}</span>`;
                else if (change < 0) changeHtml = `<span class="badge badge-critical" style="font-weight: 700;">${change}</span>`;
                else changeHtml = `<span class="badge badge-info">0</span>`;
            }

            return `
                <tr style="border-bottom: 1px solid var(--border);" class="rank-row" data-idx="${idx}">
                    <td style="padding: 12px 16px; font-weight: 700; color: var(--text-primary);">${kw}</td>
                    <td style="padding: 12px 14px; font-family: monospace; font-size: 12px; color: var(--primary); max-width: 260px; word-break: break-all;">
                        <a href="${url}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: none;">${url} ↗</a>
                    </td>
                    <td style="padding: 12px 14px; font-weight: 800; font-size: 14px; color: var(--primary);">#${pos}</td>
                    <td style="padding: 12px 14px; color: var(--text-secondary);">${prev !== '-' ? `#${prev}` : '-'}</td>
                    <td style="padding: 12px 14px;">${changeHtml}</td>
                    <td style="padding: 12px 16px; font-size: 11.5px; color: var(--text-secondary);">${src}</td>
                    <td style="padding: 12px 16px; text-align: right;">
                        <button class="btn btn-secondary btn-sm btn-inspect-rank" data-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                            Inspect
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <!-- SUMMARY HEADER -->
            <div style="background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div style="font-size: 13px;">
                    <strong>Website Target:</strong> ${this.escapeHtml(project.name)} (${this.escapeHtml(project.domain)})
                    &nbsp;•&nbsp; <strong>Search Engine:</strong> ${this.escapeHtml(config.search_engine || 'Google')} (${this.escapeHtml(config.target_country || 'Default')})
                </div>
                <button class="btn btn-secondary btn-sm" id="btn-goto-rank-config">⚙ Tracking Settings</button>
            </div>

            <!-- OVERVIEW KPI CARDS -->
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                        Website Visibility ${renderTooltip('How easily your website can currently be found in search based on available search data.')}
                    </div>
                    <div style="font-size: 26px; font-weight: 800; color: var(--primary); margin-top: 4px;">${ov.visibility || '0.0%'}</div>
                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Search presence score</div>
                </div>

                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                        Average Position ${renderTooltip('Your website average position in Google search results.')}
                    </div>
                    <div style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${ov.average_position || 'Not available'}</div>
                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Mean Google rank</div>
                </div>

                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                        Top 3 Positions ${renderTooltip('Keywords ranking in position #1 to #3 on Google.')}
                    </div>
                    <div style="font-size: 26px; font-weight: 800; color: #10b981; margin-top: 4px;">${ov.top_3 || 0}</div>
                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Top 3 Google positions</div>
                </div>

                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                        Top 10 Positions ${renderTooltip('Keywords ranking on Page 1 of Google results.')}
                    </div>
                    <div style="font-size: 26px; font-weight: 800; color: var(--primary); margin-top: 4px;">${ov.top_10 || 0}</div>
                    <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">Page 1 Google results</div>
                </div>
            </div>

            <!-- RANKINGS DATA TABLE -->
            <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Search Rankings (${filtered.length})</h3>
                        <select id="select-rank-pos" style="padding: 4px 8px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                            <option value="all" ${this.rankingsPosFilter === 'all' ? 'selected' : ''}>All Positions</option>
                            <option value="top3" ${this.rankingsPosFilter === 'top3' ? 'selected' : ''}>Top 3 Positions</option>
                            <option value="top10" ${this.rankingsPosFilter === 'top10' ? 'selected' : ''}>Top 10 (Page 1)</option>
                            <option value="top20" ${this.rankingsPosFilter === 'top20' ? 'selected' : ''}>Top 20</option>
                            <option value="20plus" ${this.rankingsPosFilter === '20plus' ? 'selected' : ''}>Position 20+</option>
                        </select>
                    </div>
                    <input type="text" id="rank-search-input" value="${this.escapeHtml(this.rankingsSearch)}" placeholder="Search keyword or URL..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                </div>

                ${allRankings.length === 0 ? `
                    <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 16px auto; background: var(--bg-subtle); border-radius: 12px; border: 1px dashed var(--border);">
                        <div style="font-size: 36px; margin-bottom: 12px;">📊</div>
                        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No Rank Tracking Data Available</h3>
                        <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                            Connect Google Search Console or import search keyword ranking datasets to populate Google position metrics.
                        </p>
                        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                            <a href="/integrations" data-link class="btn btn-primary btn-sm">Connect Data Source</a>
                            <a href="/import" data-link class="btn btn-secondary btn-sm">Import Data</a>
                        </div>
                    </div>
                ` : `
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 16px;">Search Term / Keyword</th>
                                    <th style="padding: 12px 14px;">Target Page URL</th>
                                    <th style="padding: 12px 14px;">Google Position</th>
                                    <th style="padding: 12px 14px;">Previous</th>
                                    <th style="padding: 12px 14px;">Change</th>
                                    <th style="padding: 12px 16px;">Data Source</th>
                                    <th style="padding: 12px 16px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows.length > 0 ? tableRows : `<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--text-secondary);">No keywords match your search.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                    <div id="rankings-pagination-slot"></div>
                `}
            </div>
        `;

        const gotoConfigBtn = container.querySelector('#btn-goto-rank-config');
        if (gotoConfigBtn) gotoConfigBtn.onclick = () => document.querySelector('[data-tab=config]')?.click();

        const posSelect = container.querySelector('#select-rank-pos');
        if (posSelect) posSelect.onchange = (e) => { this.rankingsPosFilter = e.target.value; this.rankingsPage = 1; this.renderTrackingTab(container, projectId, project); };

        const searchInput = container.querySelector('#rank-search-input');
        if (searchInput) {
            searchInput.oninput = (e) => {
                this.rankingsSearch = e.target.value;
                this.rankingsPage = 1;
                this.renderTrackingTab(container, projectId, project);
            };
        }

        container.querySelectorAll('.btn-inspect-rank').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute('data-idx'), 10);
                const record = paginated.items[idx];
                if (record) GrowthDetailModal.showRankingDetail(record);
            };
        });

        if (filtered.length > 0) {
            const pageSlot = container.querySelector('#rankings-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: filtered.length,
                    currentPage: this.rankingsPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.rankingsPage = newPage;
                        this.renderTrackingTab(container, projectId, project);
                    }
                });
                pageSlot.appendChild(pag.render());
            }
        }
    }

    // -------------------------------------------------------------------------
    // 2. RANKING CHANGES (WINNERS & LOSERS)
    // -------------------------------------------------------------------------
    async renderWinnersTab(container, projectId) {
        container.innerHTML = `
            <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                Loading ranking changes...
            </div>
        `;

        try {
            const data = await apiClient.get(`/api/projects/${projectId}/rankings/winners-losers`);
            
            const hasComparison = data && data.has_comparison;
            const improved = (data && data.improved) || [];
            const declined = (data && data.declined) || [];
            const newKws = (data && data.new_keywords) || [];
            const lostKws = (data && data.lost_keywords) || [];
            const totalChanges = improved.length + declined.length + newKws.length + lostKws.length;

            if (!hasComparison || totalChanges === 0) {
                container.innerHTML = `
                    <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 16px auto; background: var(--bg-subtle); border-radius: 12px; border: 1px dashed var(--border);">
                        <div style="font-size: 36px; margin-bottom: 12px;">📈</div>
                        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No Ranking Changes Detected</h3>
                        <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                            ${this.escapeHtml(data && data.message ? data.message : 'Ranking changes will appear after recording multiple search ranking snapshots.')}
                        </p>
                        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                            <a href="/integrations" data-link class="btn btn-primary btn-sm">Connect Data Source</a>
                            <a href="/import" data-link class="btn btn-secondary btn-sm">Import Data</a>
                        </div>
                    </div>
                `;
                return;
            }

            // Determine active list based on sub-filter
            let activeList = [];
            if (this.winnersTab === 'improved') activeList = improved;
            else if (this.winnersTab === 'declined') activeList = declined;
            else if (this.winnersTab === 'new') activeList = newKws;
            else if (this.winnersTab === 'lost') activeList = lostKws;
            else activeList = [...improved, ...declined, ...newKws, ...lostKws];

            if (this.winnersSearch.trim()) {
                const q = this.winnersSearch.toLowerCase().trim();
                activeList = activeList.filter(k => {
                    const kw = (k.keyword || '').toLowerCase();
                    const u = (k.url || '').toLowerCase();
                    return kw.includes(q) || u.includes(q);
                });
            }

            const paginated = Pagination.paginateArray(activeList, this.winnersPage, this.pageSize);
            this.winnersPage = paginated.currentPage;

            let tableRows = paginated.items.map((k, idx) => {
                const kw = this.escapeHtml(k.keyword);
                const curr = k.current_position !== undefined && k.current_position !== null ? `#${k.current_position}` : 'N/A';
                const prev = k.previous_position !== undefined && k.previous_position !== null ? `#${k.previous_position}` : 'N/A';
                const diff = k.change;
                const url = this.escapeHtml(k.url || '-');
                const src = this.escapeHtml(k.data_source || 'Rank Tracker');

                let badgeHtml = '<span class="badge badge-info">No Change</span>';
                if (diff !== undefined && diff !== null) {
                    if (diff > 0) badgeHtml = `<span class="badge badge-success" style="font-weight: 700;">▲ +${diff} Gain</span>`;
                    else if (diff < 0) badgeHtml = `<span class="badge badge-critical" style="font-weight: 700;">▼ ${diff} Drop</span>`;
                } else if (k.current_position && !k.previous_position) {
                    badgeHtml = `<span class="badge" style="background: rgba(59,130,246,0.15); color: #3b82f6; font-weight: 700;">NEW KEYWORD</span>`;
                } else if (!k.current_position && k.previous_position) {
                    badgeHtml = `<span class="badge badge-critical" style="font-weight: 700;">LOST KEYWORD</span>`;
                }

                return `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="padding: 12px 16px; font-weight: 700; color: var(--text-primary);">${kw}</td>
                        <td style="padding: 12px 14px; font-family: monospace; font-size: 12px; color: var(--primary); max-width: 260px; word-break: break-all;">
                            <a href="${url}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: none;">${url} ↗</a>
                        </td>
                        <td style="padding: 12px 14px; color: var(--text-secondary);">${prev}</td>
                        <td style="padding: 12px 14px; font-weight: 800; color: var(--text-primary);">${curr}</td>
                        <td style="padding: 12px 14px;">${badgeHtml}</td>
                        <td style="padding: 12px 16px; font-size: 11.5px; color: var(--text-secondary);">${src}</td>
                        <td style="padding: 12px 16px; text-align: right;">
                            <button class="btn btn-secondary btn-sm btn-inspect-winner" data-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                                Inspect
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            container.innerHTML = `
                <!-- SUMMARY KPI CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
                    <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); cursor: pointer;" id="card-filter-improved">
                        <div style="font-size: 11px; font-weight: 700; color: #10b981; text-transform: uppercase;">Improved Keywords</div>
                        <div style="font-size: 24px; font-weight: 800; color: #10b981; margin-top: 4px;">${improved.length}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Moved up in SERP rankings</div>
                    </div>
                    <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); cursor: pointer;" id="card-filter-declined">
                        <div style="font-size: 11px; font-weight: 700; color: #ef4444; text-transform: uppercase;">Declined Keywords</div>
                        <div style="font-size: 24px; font-weight: 800; color: #ef4444; margin-top: 4px;">${declined.length}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Lost SERP positions</div>
                    </div>
                    <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); cursor: pointer;" id="card-filter-new">
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase;">New Keywords</div>
                        <div style="font-size: 24px; font-weight: 800; color: var(--primary); margin-top: 4px;">${newKws.length}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Newly ranking on Google</div>
                    </div>
                    <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); cursor: pointer;" id="card-filter-lost">
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Lost Keywords</div>
                        <div style="font-size: 24px; font-weight: 800; color: var(--text-secondary); margin-top: 4px;">${lostKws.length}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Dropped out of tracked range</div>
                    </div>
                </div>

                <!-- CONTROLS & TABLE -->
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                    <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                        <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                            <button class="btn btn-sm ${this.winnersTab === 'all' ? 'btn-primary' : 'btn-secondary'} btn-win-tab" data-wtab="all" style="font-size: 12px;">All Changes (${totalChanges})</button>
                            <button class="btn btn-sm ${this.winnersTab === 'improved' ? 'btn-primary' : 'btn-secondary'} btn-win-tab" data-wtab="improved" style="font-size: 12px;">Improved (${improved.length})</button>
                            <button class="btn btn-sm ${this.winnersTab === 'declined' ? 'btn-primary' : 'btn-secondary'} btn-win-tab" data-wtab="declined" style="font-size: 12px;">Declined (${declined.length})</button>
                            <button class="btn btn-sm ${this.winnersTab === 'new' ? 'btn-primary' : 'btn-secondary'} btn-win-tab" data-wtab="new" style="font-size: 12px;">New (${newKws.length})</button>
                            <button class="btn btn-sm ${this.winnersTab === 'lost' ? 'btn-primary' : 'btn-secondary'} btn-win-tab" data-wtab="lost" style="font-size: 12px;">Lost (${lostKws.length})</button>
                        </div>
                        <input type="text" id="winners-search-input" value="${this.escapeHtml(this.winnersSearch)}" placeholder="Search keyword or URL..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                    </div>

                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 16px;">Keyword</th>
                                    <th style="padding: 12px 14px;">Ranking URL</th>
                                    <th style="padding: 12px 14px;">Previous</th>
                                    <th style="padding: 12px 14px;">Current</th>
                                    <th style="padding: 12px 14px;">Change</th>
                                    <th style="padding: 12px 16px;">Source</th>
                                    <th style="padding: 12px 16px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${tableRows.length > 0 ? tableRows : `<tr><td colspan="7" style="padding: 32px; text-align: center; color: var(--text-secondary);">No ranking changes matching your selection.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                    <div id="winners-pagination-slot"></div>
                </div>
            `;

            // Card click handlers
            container.querySelector('#card-filter-improved')?.addEventListener('click', () => { this.winnersTab = 'improved'; this.winnersPage = 1; this.renderWinnersTab(container, projectId); });
            container.querySelector('#card-filter-declined')?.addEventListener('click', () => { this.winnersTab = 'declined'; this.winnersPage = 1; this.renderWinnersTab(container, projectId); });
            container.querySelector('#card-filter-new')?.addEventListener('click', () => { this.winnersTab = 'new'; this.winnersPage = 1; this.renderWinnersTab(container, projectId); });
            container.querySelector('#card-filter-lost')?.addEventListener('click', () => { this.winnersTab = 'lost'; this.winnersPage = 1; this.renderWinnersTab(container, projectId); });

            // Tab button handlers
            container.querySelectorAll('.btn-win-tab').forEach(btn => {
                btn.onclick = () => {
                    this.winnersTab = btn.getAttribute('data-wtab');
                    this.winnersPage = 1;
                    this.renderWinnersTab(container, projectId);
                };
            });

            // Search input
            const searchInput = container.querySelector('#winners-search-input');
            if (searchInput) {
                searchInput.oninput = (e) => {
                    this.winnersSearch = e.target.value;
                    this.winnersPage = 1;
                    this.renderWinnersTab(container, projectId);
                };
            }

            // Inspect buttons
            container.querySelectorAll('.btn-inspect-winner').forEach(btn => {
                btn.onclick = (e) => {
                    e.stopPropagation();
                    const idx = parseInt(btn.getAttribute('data-idx'), 10);
                    const record = paginated.items[idx];
                    if (record) GrowthDetailModal.showRankingDetail(record);
                };
            });

            if (activeList.length > 0) {
                const pageSlot = container.querySelector('#winners-pagination-slot');
                if (pageSlot) {
                    const pag = new Pagination({
                        totalItems: activeList.length,
                        currentPage: this.winnersPage,
                        pageSize: this.pageSize,
                        onPageChange: (newPage) => {
                            this.winnersPage = newPage;
                            this.renderWinnersTab(container, projectId);
                        }
                    });
                    pageSlot.appendChild(pag.render());
                }
            }

        } catch (e) {
            renderFeatureErrorState(container, "Winners / Losers Error", e.message || "Failed to load ranking changes.", () => this.renderWinnersTab(container, projectId));
        }
    }

    // -------------------------------------------------------------------------
    // 3. CAMPAIGN CONFIGURATION SUB-TAB
    // -------------------------------------------------------------------------
    async renderCampaignConfigTab(container, projectId, project) {
        let config = {};
        try {
            const res = await apiClient.get(`/api/projects/${projectId}/rankings/config`);
            config = res.campaign_config || {};
        } catch (e) {
            config = {
                target_type: 'Domain',
                search_engine: 'Google',
                target_country: 'United States',
                target_language: 'English',
                target_device: 'Desktop'
            };
        }

        container.innerHTML = `
            <div class="card" style="padding: 24px; max-width: 680px; margin: 0 auto; background: var(--bg-card); border-radius: 14px;">
                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 16px 0; color: var(--text-primary);">Search Ranking Tracking Configuration</h3>
                <form id="rankings-config-form" style="display: flex; flex-direction: column; gap: 16px;">
                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase;">Search Engine</label>
                        <select name="search_engine" style="width: 100%; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-primary); font-size: 13px;">
                            <option value="Google" ${config.search_engine === 'Google' ? 'selected' : ''}>Google</option>
                            <option value="Bing" ${config.search_engine === 'Bing' ? 'selected' : ''}>Bing</option>
                        </select>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase;">Target Country</label>
                            <input type="text" name="target_country" value="${this.escapeHtml(config.target_country || 'United States')}" style="width: 100%; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-primary); font-size: 13px;" />
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase;">Target Language</label>
                            <input type="text" name="target_language" value="${this.escapeHtml(config.target_language || 'English')}" style="width: 100%; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-primary); font-size: 13px;" />
                        </div>
                    </div>
                    <div>
                        <label style="display: block; font-size: 12px; font-weight: 700; color: var(--text-secondary); margin-bottom: 6px; text-transform: uppercase;">Device Type</label>
                        <select name="target_device" style="width: 100%; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg-subtle); color: var(--text-primary); font-size: 13px;">
                            <option value="Desktop" ${config.target_device === 'Desktop' ? 'selected' : ''}>Desktop</option>
                            <option value="Mobile" ${config.target_device === 'Mobile' ? 'selected' : ''}>Mobile</option>
                        </select>
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
                        <button type="submit" class="btn btn-primary btn-sm">Save Configuration</button>
                    </div>
                </form>
            </div>
        `;

        const form = container.querySelector('#rankings-config-form');
        if (form) {
            form.onsubmit = async (e) => {
                e.preventDefault();
                const formData = new FormData(form);
                const payload = {
                    search_engine: formData.get('search_engine'),
                    target_country: formData.get('target_country'),
                    target_language: formData.get('target_language'),
                    target_device: formData.get('target_device')
                };
                try {
                    await apiClient.post(`/api/projects/${projectId}/rankings/config`, payload);
                    alert("Tracking configuration updated successfully.");
                } catch (err) {
                    alert("Failed to update settings: " + (err.message || 'Unknown error'));
                }
            };
        }
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
