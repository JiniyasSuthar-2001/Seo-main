import { projectStore } from '../core/projectStore.js';
import { apiClient } from '../services/apiClient.js';
import { resolveProjectId } from '../utils/projectResolver.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';

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
                    <h1 style="font-size: 24px; font-weight: 700;">Position Tracking & SERP Rankings</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Monitor website search engine position movements, visibility scores, and winners/losers across crawl snapshots.</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Run Crawl</button>
            </div>

            <!-- POSITION TRACKING SUB-TABS -->
            <div style="display: flex; gap: 6px; border-bottom: 1px solid var(--border); margin-bottom: 24px; flex-wrap: wrap;" id="rank-tabs-nav">
                <button class="rank-tab active" data-tab="tracking">Position Tracking</button>
                <button class="rank-tab" data-tab="winners">Winners & Losers</button>
                <button class="rank-tab" data-tab="config">Campaign Settings</button>
            </div>

            <div id="rankings-tab-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading position tracking workspace...
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

        const projectId = resolveProjectId();
        const selectedProj = projectStore.getSelectedProject();

        if (!projectId || !selectedProj) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select an SEO project workspace.</div>`;
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
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Rankings Load Error", e.message || "Failed to load rankings.", () => this.mounted());
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
            <!-- CAMPAIGN SUMMARY HEADER -->
            <div style="background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div style="font-size: 13px;">
                    <strong>Campaign Target:</strong> ${project.name} (${project.domain})
                    &nbsp;•&nbsp; <strong>Scope:</strong> ${config.target_type}
                    &nbsp;•&nbsp; <strong>Engine:</strong> ${config.search_engine} (${config.target_country})
                    &nbsp;•&nbsp; <strong>Device:</strong> ${config.target_device}
                </div>
                <button class="btn btn-secondary btn-sm" onclick="document.querySelector('[data-tab=config]').click()">⚙ Edit Campaign Config</button>
            </div>

            <!-- OVERVIEW KPI CARDS -->
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px;">
                <div class="kpi-card">
                    <div class="kpi-label">Visibility Score</div>
                    <div class="kpi-value" style="color: var(--primary);">${ov.visibility || '0.0%'}</div>
                    <div class="kpi-status">Search presence</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Average Position</div>
                    <div class="kpi-value">${ov.average_position || 'N/A'}</div>
                    <div class="kpi-status">Mean rank</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Top 3 Positions</div>
                    <div class="kpi-value" style="color: var(--success, #10b981);">${ov.top_3 || 0}</div>
                    <div class="kpi-status">Page 1 Top 3</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Top 10 Positions</div>
                    <div class="kpi-value" style="color: var(--primary);">${ov.top_10 || 0}</div>
                    <div class="kpi-status">Page 1 results</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Top 20 Positions</div>
                    <div class="kpi-value">${ov.top_20 || 0}</div>
                    <div class="kpi-status">Page 2 results</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Total Tracked</div>
                    <div class="kpi-value">${ov.total_tracked || 0}</div>
                    <div class="kpi-status">Tracked terms</div>
                </div>
            </div>

            <!-- HISTORICAL TREND NOTICE -->
            <div class="card" style="padding: 16px 20px; margin-bottom: 24px; background: var(--bg-subtle); border-left: 4px solid var(--primary);">
                <div style="font-size: 13px; color: var(--text-secondary);">
                    ℹ️ <strong>Position Trend Status:</strong> ${trackingRes.trend_message || "Trend data will appear after additional ranking snapshots."}
                </div>
            </div>

            <!-- RANKINGS DATA TABLE -->
            <div class="card" style="padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="font-size: 16px; font-weight: 700;">SERP Keyword Positions</h3>
                    <span class="source-tag">Verified Dataset</span>
                </div>

                ${rankings.length === 0 ? `
                    <div style="padding: 24px; text-align: center; color: var(--text-secondary);">
                        No ranking data available for this domain. Connect Google Search Console or import ranking CSV.
                    </div>
                ` : `
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 10px 14px;">Tracked Keyword</th>
                                <th style="padding: 10px 14px;">Current Rank</th>
                                <th style="padding: 10px 14px;">Ranking URL</th>
                                <th style="padding: 10px 14px;">Search Volume</th>
                                <th style="padding: 10px 14px;">Difficulty</th>
                                <th style="padding: 10px 14px; text-align: right;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rankings.map(item => `
                                <tr style="border-bottom: 1px solid var(--border);">
                                    <td style="padding: 10px 14px; font-weight: 600;">${item.keyword}</td>
                                    <td style="padding: 10px 14px; font-weight: 700; color: var(--primary);">${item.position ? '#' + item.position : 'Unranked'}</td>
                                    <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary); max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${item.url || 'Homepage'}</td>
                                    <td style="padding: 10px 14px; color: var(--text-tertiary);">${item.search_volume !== undefined ? item.search_volume : 'Unavailable'}</td>
                                    <td style="padding: 10px 14px; color: var(--text-tertiary);">${item.difficulty !== undefined ? item.difficulty : 'Unavailable'}</td>
                                    <td style="padding: 10px 14px; text-align: right;"><span class="source-tag">${item.data_source || 'Crawler'}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `}
            </div>
        `;
    }

    // 2. WINNERS & LOSERS SUB-TAB
    async renderWinnersTab(container, projectId) {
        const res = await apiClient.get(`/api/projects/${projectId}/rankings/winners-losers`);
        
        if (!res.has_comparison) {
            container.innerHTML = `
                <div class="card" style="padding: 36px; text-align: center;">
                    <div style="font-size: 16px; font-weight: 700; margin-bottom: 8px;">Single Snapshot Available</div>
                    <p style="color: var(--text-secondary); font-size: 14px; max-width: 500px; margin: 0 auto 16px;">
                        ${res.message || "Trend data will appear after additional ranking snapshots."}
                    </p>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl()">Run Additional Website Crawl</button>
                </div>
            `;
            return;
        }

        const improved = res.improved || [];
        const declined = res.declined || [];

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px;">
                
                <!-- IMPROVED KEYWORDS -->
                <div class="card" style="padding: 20px;">
                    <h3 style="font-size: 16px; font-weight: 700; color: var(--success, #10b981); margin-bottom: 12px;">▲ Improved Keywords (${improved.length})</h3>
                    ${improved.length === 0 ? `<div style="color: var(--text-secondary); font-size: 13px;">No improved keywords in recent snapshot.</div>` : `
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 8px 12px;">Keyword</th>
                                    <th style="padding: 8px 12px;">Prev</th>
                                    <th style="padding: 8px 12px;">Curr</th>
                                    <th style="padding: 8px 12px;">Change</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${improved.map(item => `
                                    <tr style="border-bottom: 1px solid var(--border);">
                                        <td style="padding: 8px 12px; font-weight: 600;">${item.keyword}</td>
                                        <td style="padding: 8px 12px; color: var(--text-secondary);">#${item.previous_position}</td>
                                        <td style="padding: 8px 12px; font-weight: 700; color: var(--success);">#${item.current_position}</td>
                                        <td style="padding: 8px 12px; font-weight: 700; color: var(--success);">${item.change}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `}
                </div>

                <!-- DECLINED KEYWORDS -->
                <div class="card" style="padding: 20px;">
                    <h3 style="font-size: 16px; font-weight: 700; color: var(--critical, #ef4444); margin-bottom: 12px;">▼ Declined Keywords (${declined.length})</h3>
                    ${declined.length === 0 ? `<div style="color: var(--text-secondary); font-size: 13px;">No declined keywords in recent snapshot.</div>` : `
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 8px 12px;">Keyword</th>
                                    <th style="padding: 8px 12px;">Prev</th>
                                    <th style="padding: 8px 12px;">Curr</th>
                                    <th style="padding: 8px 12px;">Change</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${declined.map(item => `
                                    <tr style="border-bottom: 1px solid var(--border);">
                                        <td style="padding: 8px 12px; font-weight: 600;">${item.keyword}</td>
                                        <td style="padding: 8px 12px; color: var(--text-secondary);">#${item.previous_position}</td>
                                        <td style="padding: 8px 12px; font-weight: 700; color: var(--critical);">#${item.current_position}</td>
                                        <td style="padding: 8px 12px; font-weight: 700; color: var(--critical);">${item.change}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `}
                </div>

            </div>
        `;
    }

    // 3. CAMPAIGN CONFIGURATION SUB-TAB
    async renderCampaignConfigTab(container, projectId, project) {
        container.innerHTML = `
            <div class="card" style="padding: 24px; max-width: 680px;">
                <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">Ranking Campaign Configuration</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">Configure project target scope, search engine, country, language, and target device for position tracking.</p>

                <form id="campaign-config-form" style="display: flex; flex-direction: column; gap: 16px;">
                    <div>
                        <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px;">Target Scope</label>
                        <select id="cfg-scope" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                            <option value="Domain" ${project.target_type === 'Domain' ? 'selected' : ''}>Domain (*.example.com)</option>
                            <option value="Subdomain" ${project.target_type === 'Subdomain' ? 'selected' : ''}>Subdomain (blog.example.com)</option>
                            <option value="Exact URL" ${project.target_type === 'Exact URL' ? 'selected' : ''}>Exact URL (example.com/page)</option>
                            <option value="Subfolder" ${project.target_type === 'Subfolder' ? 'selected' : ''}>Subfolder (example.com/store/)</option>
                        </select>
                    </div>

                    <div>
                        <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px;">Search Engine</label>
                        <select id="cfg-engine" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                            <option value="Google">Google Search</option>
                            <option value="Bing">Microsoft Bing</option>
                        </select>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div>
                            <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px;">Target Country</label>
                            <input type="text" id="cfg-country" value="${project.target_country || 'United States'}" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px;">Language</label>
                            <input type="text" id="cfg-lang" value="${project.target_language || 'English'}" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                        </div>
                    </div>

                    <div>
                        <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 4px;">Target Device</label>
                        <select id="cfg-device" style="width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; background: var(--bg-workspace); color: var(--text-primary);">
                            <option value="Desktop" ${project.target_device === 'Desktop' ? 'selected' : ''}>Desktop</option>
                            <option value="Mobile" ${project.target_device === 'Mobile' ? 'selected' : ''}>Mobile</option>
                            <option value="Tablet" ${project.target_device === 'Tablet' ? 'selected' : ''}>Tablet</option>
                        </select>
                    </div>

                    <div style="margin-top: 8px;">
                        <button type="submit" class="btn btn-primary">Save Campaign Settings</button>
                    </div>
                </form>
            </div>
        `;

        const form = container.querySelector('#campaign-config-form');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const scope = container.querySelector('#cfg-scope').value;
            const engine = container.querySelector('#cfg-engine').value;
            const country = container.querySelector('#cfg-country').value;
            const lang = container.querySelector('#cfg-lang').value;
            const device = container.querySelector('#cfg-device').value;

            try {
                await apiClient.post(`/api/projects/${projectId}/campaign-config`, {
                    target_type: scope,
                    search_engine: engine,
                    target_country: country,
                    target_language: lang,
                    target_device: device
                });
                alert("Campaign settings saved successfully.");
                this.mounted();
            } catch (err) {
                alert(`Failed to save settings: ${err.message}`);
            }
        });
    }
}
