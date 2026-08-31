import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

export class Rankings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'rankings-view';
        this.activeTab = 'tracking';
        this.rankingsPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Search Rankings</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Monitor your website search engine positions on Google.</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
            </div>

            <!-- POSITION TRACKING SUB-TABS -->
            <div style="display: flex; gap: 6px; border-bottom: 1px solid var(--border); margin-bottom: 24px; flex-wrap: wrap;" id="rank-tabs-nav">
                <button class="rank-tab active" data-tab="tracking">Search Rankings</button>
                <button class="rank-tab" data-tab="winners">Ranking Changes</button>
                <button class="rank-tab" data-tab="config">Settings</button>
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

    // 1. POSITION TRACKING SUB-TAB
    async renderTrackingTab(container, projectId, project) {
        const trackingRes = await apiClient.get(`/api/projects/${projectId}/rankings/tracking`);
        const ov = trackingRes.overview || {};
        const config = trackingRes.campaign_config || {};

        const rankRes = await apiClient.get(`/api/projects/${projectId}/rankings?limit=500`);
        const rankings = rankRes.rankings || [];

        const paginated = Pagination.paginateArray(rankings, this.rankingsPage, this.pageSize);
        this.rankingsPage = paginated.currentPage;

        container.innerHTML = `
            <!-- SUMMARY HEADER -->
            <div style="background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div style="font-size: 13px;">
                    <strong>Website Target:</strong> ${project.name} (${project.domain})
                    &nbsp;•&nbsp; <strong>Search Engine:</strong> ${config.search_engine || 'Google'} (${config.target_country || 'Default'})
                </div>
                <button class="btn btn-secondary btn-sm" onclick="document.querySelector('[data-tab=config]').click()">⚙ Tracking Settings</button>
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
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0;">Search Rankings (${rankings.length})</h3>
                </div>

                ${rankings.length === 0 ? `
                    <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 16px auto; background: var(--bg-subtle); border-radius: 12px; border: 1px dashed var(--border);">
                        <div style="font-size: 36px; margin-bottom: 12px;">📊</div>
                        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">Not available yet</h3>
                        <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                            Connect or import search data to see your website search rankings on Google.
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
                                    <th style="padding: 12px 18px;">Search Term / Keyword</th>
                                    <th style="padding: 12px;">Target Page URL</th>
                                    <th style="padding: 12px;">Google Position</th>
                                    <th style="padding: 12px;">Previous Position</th>
                                    <th style="padding: 12px;">Position Change</th>
                                    <th style="padding: 12px 18px;">Data Source</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${paginated.items.map(r => `
                                    <tr style="border-bottom: 1px solid var(--border);">
                                        <td style="padding: 12px 18px; font-weight: 700; color: var(--text-primary);">${this.escapeHtml(r.keyword)}</td>
                                        <td style="padding: 12px; font-family: monospace; font-size: 12px;">${this.escapeHtml(r.url || '-')}</td>
                                        <td style="padding: 12px; font-weight: 800; color: var(--primary);">${r.position || 'Not available'}</td>
                                        <td style="padding: 12px; color: var(--text-secondary);">${r.previous_position || '-'}</td>
                                        <td style="padding: 12px;">${r.change ? (r.change > 0 ? `<span style="color: #10b981;">+${r.change}</span>` : `<span style="color: #ef4444;">${r.change}</span>`) : '0'}</td>
                                        <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">${this.escapeHtml(r.provenance || 'Google Search Data')}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div id="rankings-pagination-slot"></div>
                `}
            </div>
        `;

        if (rankings.length > 0) {
            const pageSlot = container.querySelector('#rankings-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: rankings.length,
                    currentPage: this.rankingsPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.rankingsPage = newPage;
                        this.mounted();
                    }
                });
                pageSlot.appendChild(pag.render());
            }
        }
    }

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
                            <a href="/import" data-link class="btn btn-secondary btn-sm">Import Ranking Snapshot</a>
                        </div>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="card" style="padding: 24px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
                        <div>
                            <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Ranking Movements</h3>
                            <div style="font-size: 12px; color: var(--text-secondary);">
                                Comparing snapshot <strong>${data.snapshot_previous || 'Previous'}</strong> vs <strong>${data.snapshot_current || 'Latest'}</strong>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px; font-size: 12px;">
                            <span class="badge badge-success" style="padding: 4px 10px;">+${improved.length} Improved</span>
                            <span class="badge badge-danger" style="padding: 4px 10px;">-${declined.length} Declined</span>
                            <span class="badge badge-info" style="padding: 4px 10px;">${newKws.length} New</span>
                            <span class="badge badge-secondary" style="padding: 4px 10px;">${lostKws.length} Lost</span>
                        </div>
                    </div>

                    ${improved.length > 0 ? `
                        <div style="margin-bottom: 24px;">
                            <h4 style="font-size: 14px; font-weight: 700; color: var(--success, #10b981); margin: 0 0 10px 0;">✓ Improved Keywords (${improved.length})</h4>
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 10px 14px;">Keyword</th>
                                        <th style="padding: 10px 14px;">Previous Rank</th>
                                        <th style="padding: 10px 14px;">Current Rank</th>
                                        <th style="padding: 10px 14px;">Movement</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${improved.map(item => `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 10px 14px; font-weight: 600;">${this.escapeHtml(item.keyword)}</td>
                                            <td style="padding: 10px 14px; color: var(--text-secondary);">#${item.previous_position}</td>
                                            <td style="padding: 10px 14px; font-weight: 700; color: var(--primary);">#${item.current_position}</td>
                                            <td style="padding: 10px 14px; color: var(--success, #10b981); font-weight: 700;">+${item.change || (item.previous_position - item.current_position)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : ''}

                    ${declined.length > 0 ? `
                        <div style="margin-bottom: 24px;">
                            <h4 style="font-size: 14px; font-weight: 700; color: var(--critical, #ef4444); margin: 0 0 10px 0;">⚠ Declined Keywords (${declined.length})</h4>
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 10px 14px;">Keyword</th>
                                        <th style="padding: 10px 14px;">Previous Rank</th>
                                        <th style="padding: 10px 14px;">Current Rank</th>
                                        <th style="padding: 10px 14px;">Movement</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${declined.map(item => `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 10px 14px; font-weight: 600;">${this.escapeHtml(item.keyword)}</td>
                                            <td style="padding: 10px 14px; color: var(--text-secondary);">#${item.previous_position}</td>
                                            <td style="padding: 10px 14px; font-weight: 700; color: var(--critical, #ef4444);">#${item.current_position}</td>
                                            <td style="padding: 10px 14px; color: var(--critical, #ef4444); font-weight: 700;">-${Math.abs(item.change || (item.current_position - item.previous_position))}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : ''}
                </div>
            `;
        } catch (e) {
            container.innerHTML = `
                <div class="card" style="padding: 24px; color: var(--critical); text-align: center;">
                    Failed to load ranking changes: ${this.escapeHtml(e.message || 'An unexpected error occurred.')}
                </div>
            `;
        }
    }

    async renderCampaignConfigTab(container, projectId, project) {
        container.innerHTML = `
            <div class="card" style="padding: 24px; max-width: 600px;">
                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 16px 0;">Tracking Settings</h3>
                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px;">
                    Target Website: <strong>${this.escapeHtml(project.name)}</strong> (${this.escapeHtml(project.domain)})
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="font-size: 12.5px; font-weight: 600; display: block; margin-bottom: 6px;">Target Search Engine</label>
                    <input type="text" value="Google" readonly style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-subtle);" />
                </div>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
