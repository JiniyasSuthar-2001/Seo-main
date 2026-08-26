import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { renderTooltip } from '../components/Tooltip.js';

export class Rankings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'rankings-view';
        this.activeTab = 'tracking';
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

        const rankRes = await apiClient.get(`/api/projects/${projectId}/rankings?limit=100`);
        const rankings = rankRes.rankings || [];

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
            <div class="card" style="padding: 24px; border-radius: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0;">Search Rankings</h3>
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
                                ${rankings.map(r => `
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
                `}
            </div>
        `;
    }

    async renderWinnersTab(container, projectId) {
        container.innerHTML = `
            <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                Ranking changes will appear after connecting a search data source or importing ranking data.
            </div>
        `;
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
