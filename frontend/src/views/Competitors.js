import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';

export class Competitors {
    constructor() {
        this.activeTab = 'suggested'; // 'suggested', 'confirmed', 'gap'
        this.suggestedCompetitors = [];
        this.confirmedCompetitors = [];
        this.gapAnalysis = null;
        this.loading = false;
        this.discovering = false;
        this.error = null;
        this.showModal = false;
        this.editingCompetitor = null;
        this.unsubscribeStore = null;
    }

    render() {
        const element = document.createElement('div');
        element.className = 'competitors-view';
        
        this.container = element;
        this.initProjectListener();
        this.loadData();
        
        return element;
    }

    initProjectListener() {
        if (!this.unsubscribeStore) {
            this.unsubscribeStore = projectStore.subscribe(() => {
                if (this.container && document.body.contains(this.container)) {
                    this.loadData();
                }
            });
        }
    }

    async loadData() {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) {
            this.renderState();
            return;
        }

        this.loading = true;
        this.error = null;
        this.renderState();

        try {
            const projectId = currentProject.id;

            // Fetch suggested & confirmed competitors and keyword gap in parallel
            const [suggestedData, confirmedData, gapData] = await Promise.all([
                apiClient.get(`/api/projects/${projectId}/competitors/discovered`),
                apiClient.get(`/api/projects/${projectId}/competitors?status=Confirmed`),
                apiClient.get(`/api/projects/${projectId}/competitors/gap-analysis`).catch(() => null)
            ]);

            this.suggestedCompetitors = Array.isArray(suggestedData) ? suggestedData : [];
            this.confirmedCompetitors = Array.isArray(confirmedData) ? confirmedData : [];
            this.gapAnalysis = gapData;
            
            // Default to 'confirmed' tab if user already has confirmed competitors
            if (this.confirmedCompetitors.length > 0 && this.activeTab === 'suggested' && this.suggestedCompetitors.length === 0) {
                this.activeTab = 'confirmed';
            }
        } catch (err) {
            console.error('[Competitors View Error]', err);
            this.error = err.message || 'Failed to load competitor data from backend.';
        } finally {
            this.loading = false;
            this.renderState();
        }
    }

    async runAutoDiscovery() {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        this.discovering = true;
        this.renderState();

        try {
            const res = await apiClient.post(`/api/projects/${currentProject.id}/competitors/discover`);
            if (res && res.suggested_competitors) {
                this.suggestedCompetitors = res.suggested_competitors;
            }
            if (res && res.confirmed_competitors) {
                this.confirmedCompetitors = res.confirmed_competitors;
            }
            this.activeTab = 'suggested';
        } catch (err) {
            alert('Competitor discovery failed: ' + err.message);
        } finally {
            this.discovering = false;
            this.loadData();
        }
    }

    async approveCompetitor(competitorId) {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        try {
            await apiClient.post(`/api/projects/${currentProject.id}/competitors/${competitorId}/approve`);
            await this.loadData();
        } catch (err) {
            alert('Failed to approve competitor: ' + err.message);
        }
    }

    async ignoreCompetitor(competitorId) {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        try {
            await apiClient.post(`/api/projects/${currentProject.id}/competitors/${competitorId}/ignore`);
            await this.loadData();
        } catch (err) {
            alert('Failed to ignore competitor: ' + err.message);
        }
    }

    async deleteCompetitor(competitorId) {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        if (!confirm('Are you sure you want to remove this competitor from your project?')) return;

        try {
            await apiClient.delete(`/api/projects/${currentProject.id}/competitors/${competitorId}`);
            await this.loadData();
        } catch (err) {
            alert('Failed to delete competitor: ' + err.message);
        }
    }

    async togglePrimary(competitor) {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        try {
            await apiClient.put(`/api/projects/${currentProject.id}/competitors/${competitor.id}`, {
                is_primary: !competitor.is_primary
            });
            await this.loadData();
        } catch (err) {
            alert('Failed to update primary competitor status: ' + err.message);
        }
    }

    renderState() {
        if (!this.container) return;

        const currentProject = projectStore.getCurrentProject();
        
        if (!currentProject) {
            this.container.innerHTML = `
                <div class="header" style="margin-bottom: 24px;">
                    <h1 style="font-size: 24px; font-weight: 600;">Competitor Analysis</h1>
                </div>
                <div class="empty-state" style="text-align: center; padding: 48px 24px;">
                    <div class="empty-state-title" style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">No Project Selected</div>
                    <div class="empty-state-desc" style="color: var(--text-secondary);">Please select or create an SEO project from the sidebar to view competitors.</div>
                </div>
            `;
            return;
        }

        const projectDomain = currentProject.domain || currentProject.url || 'Target Website';
        const suggestedCount = this.suggestedCompetitors.length;
        const confirmedCount = this.confirmedCompetitors.length;

        this.container.innerHTML = `
            <div class="competitors-header" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600; color: var(--text-primary); margin: 0 0 4px 0;">Competitor Discovery & Ranking Engine</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 14px;">
                        Target Domain: <strong style="color: var(--accent-primary);">${this.escapeHtml(projectDomain)}</strong>
                    </p>
                </div>
                <div style="display: flex; gap: 12px;">
                    <button id="btn-auto-discover" class="btn btn-secondary" style="display: inline-flex; align-items: center; gap: 8px;" ${this.discovering ? 'disabled' : ''}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        ${this.discovering ? 'Discovering Competitors...' : 'Auto-Discover Competitors'}
                    </button>
                    <button id="btn-add-manual" class="btn btn-primary" style="display: inline-flex; align-items: center; gap: 8px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        Add Competitor
                    </button>
                </div>
            </div>

            ${this.error ? `
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 16px; margin-bottom: 24px; color: #ef4444;">
                    <strong>Error:</strong> ${this.escapeHtml(this.error)}
                </div>
            ` : ''}

            <!-- Tabs Navigation -->
            <div class="tabs-nav" style="display: flex; border-bottom: 1px solid var(--border-color); margin-bottom: 24px; gap: 24px;">
                <button class="tab-btn ${this.activeTab === 'suggested' ? 'active' : ''}" data-tab="suggested" style="padding: 12px 4px; font-weight: 500; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'suggested' ? 'var(--accent-primary, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'suggested' ? 'var(--accent-primary, #3b82f6)' : 'var(--text-secondary)'}; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                    Suggested Competitors
                    <span style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">${suggestedCount}</span>
                </button>
                <button class="tab-btn ${this.activeTab === 'confirmed' ? 'active' : ''}" data-tab="confirmed" style="padding: 12px 4px; font-weight: 500; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'confirmed' ? 'var(--accent-primary, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'confirmed' ? 'var(--accent-primary, #3b82f6)' : 'var(--text-secondary)'}; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                    Confirmed Competitors
                    <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">${confirmedCount}</span>
                </button>
                <button class="tab-btn ${this.activeTab === 'gap' ? 'active' : ''}" data-tab="gap" style="padding: 12px 4px; font-weight: 500; background: none; border: none; border-bottom: 2px solid ${this.activeTab === 'gap' ? 'var(--accent-primary, #3b82f6)' : 'transparent'}; color: ${this.activeTab === 'gap' ? 'var(--accent-primary, #3b82f6)' : 'var(--text-secondary)'}; cursor: pointer;">
                    Keyword Gap Analysis
                </button>
            </div>

            <!-- Main Tab Content -->
            <div class="tab-content">
                ${this.loading ? `
                    <div style="text-align: center; padding: 48px;">
                        <div class="spinner" style="width: 32px; height: 32px; border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin 1s infinite linear; margin: 0 auto 16px;"></div>
                        <p style="color: var(--text-secondary);">Analyzing search competitors and location relevance...</p>
                    </div>
                ` : this.renderTabContent()}
            </div>

            <!-- Modal for Manual Add / Edit -->
            ${this.showModal ? this.renderModal() : ''}
        `;

        this.bindEvents();
    }

    renderTabContent() {
        if (this.activeTab === 'suggested') {
            return this.renderSuggestedTab();
        } else if (this.activeTab === 'confirmed') {
            return this.renderConfirmedTab();
        } else if (this.activeTab === 'gap') {
            return this.renderGapTab();
        }
        return '';
    }

    renderSuggestedTab() {
        if (this.suggestedCompetitors.length === 0) {
            return `
                <div class="card" style="text-align: center; padding: 48px 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">No Pending Suggested Competitors</div>
                    <p style="color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px;">
                        All auto-discovered competitors have been approved or ignored. Click <strong>Auto-Discover Competitors</strong> to scan SERPs for new market candidates.
                    </p>
                    <button class="btn btn-primary" onclick="document.getElementById('btn-auto-discover').click()">Scan SERPs for Competitors</button>
                </div>
            `;
        }

        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px;">
                ${this.suggestedCompetitors.map(c => `
                    <div class="card competitor-card" style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 4px 0;">${this.escapeHtml(c.name)}</h3>
                                    <a href="${this.escapeHtml(c.url)}" target="_blank" style="color: var(--accent-primary, #3b82f6); font-size: 13px; text-decoration: none;">${this.escapeHtml(c.domain)} &rarr;</a>
                                </div>
                                <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 13px; font-weight: 700; padding: 4px 10px; border-radius: 20px;">
                                    ${c.relevance_score}% Match
                                </span>
                            </div>

                            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;">
                                <span style="background: rgba(255, 255, 255, 0.06); font-size: 12px; color: var(--text-secondary); padding: 4px 8px; border-radius: 6px;">
                                    📍 ${this.escapeHtml(c.location)}
                                </span>
                                <span style="background: rgba(59, 130, 246, 0.1); color: #60a5fa; font-size: 12px; padding: 4px 8px; border-radius: 6px;">
                                    Level: ${this.escapeHtml(c.geographic_level)}
                                </span>
                            </div>

                            <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                                <div><strong style="color: var(--text-primary);">${c.keyword_overlap}</strong> Overlapping Keywords</div>
                                <div><strong style="color: var(--text-primary);">${c.search_appearances}</strong> SERP Appearances</div>
                            </div>

                            ${c.competing_services && c.competing_services.length > 0 ? `
                                <div style="margin-bottom: 16px;">
                                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">Competing Services:</div>
                                    <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                                        ${c.competing_services.map(svc => `
                                            <span style="font-size: 11px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${this.escapeHtml(svc)}</span>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}

                            <div style="font-size: 12px; color: var(--text-tertiary, #94a3b8); margin-bottom: 16px;">
                                Source: ${this.escapeHtml(c.discovery_source)}
                            </div>
                        </div>

                        <div style="display: flex; gap: 10px; margin-top: 12px; border-top: 1px solid var(--border-color); padding-top: 14px;">
                            <button class="btn btn-primary btn-approve" data-id="${c.id}" style="flex: 1; padding: 8px; font-size: 13px;">
                                + Add Competitor
                            </button>
                            <button class="btn btn-secondary btn-ignore" data-id="${c.id}" style="padding: 8px 12px; font-size: 13px; color: var(--text-secondary);">
                                Ignore
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderConfirmedTab() {
        if (this.confirmedCompetitors.length === 0) {
            return `
                <div class="card" style="text-align: center; padding: 48px 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">No Confirmed Competitors Yet</div>
                    <p style="color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px;">
                        Approve auto-discovered competitors from the <strong>Suggested Competitors</strong> tab or click <strong>Add Competitor</strong> to manually add competitor domains.
                    </p>
                    <button class="btn btn-primary" onclick="document.getElementById('btn-add-manual').click()">+ Add Competitor Manually</button>
                </div>
            `;
        }

        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px;">
                ${this.confirmedCompetitors.map(c => `
                    <div class="card competitor-card" style="background: var(--bg-card, #1e293b); border: 1px solid ${c.is_primary ? 'var(--accent-primary, #3b82f6)' : 'var(--border-color, #334155)'}; border-radius: 12px; padding: 20px; position: relative;">
                        ${c.is_primary ? `
                            <span style="position: absolute; top: -10px; right: 16px; background: var(--accent-primary, #3b82f6); color: #fff; font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 10px;">PRIMARY COMPETITOR</span>
                        ` : ''}

                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                            <div>
                                <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 4px 0;">${this.escapeHtml(c.name)}</h3>
                                <a href="${this.escapeHtml(c.url)}" target="_blank" style="color: var(--accent-primary, #3b82f6); font-size: 13px; text-decoration: none;">${this.escapeHtml(c.domain)} &rarr;</a>
                            </div>
                            <span style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; font-size: 13px; font-weight: 700; padding: 4px 10px; border-radius: 20px;">
                                ${c.relevance_score}% Relevance
                            </span>
                        </div>

                        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;">
                            <span style="background: rgba(255, 255, 255, 0.06); font-size: 12px; color: var(--text-secondary); padding: 4px 8px; border-radius: 6px;">
                                📍 ${this.escapeHtml(c.location)}
                            </span>
                            <span style="background: rgba(16, 185, 129, 0.1); color: #10b981; font-size: 12px; padding: 4px 8px; border-radius: 6px;">
                                Active Competitor
                            </span>
                        </div>

                        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                            <div><strong style="color: var(--text-primary);">${c.keyword_overlap}</strong> Keyword Overlap</div>
                            <div><strong style="color: var(--text-primary);">${c.search_appearances}</strong> SERP Appearances</div>
                        </div>

                        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 14px; gap: 8px;">
                            <button class="btn btn-secondary btn-toggle-primary" data-id="${c.id}" style="font-size: 12px; padding: 6px 10px;">
                                ${c.is_primary ? '★ Primary' : '☆ Set Primary'}
                            </button>
                            <div style="display: flex; gap: 6px;">
                                <button class="btn btn-secondary btn-edit-comp" data-id="${c.id}" style="font-size: 12px; padding: 6px 10px;">Edit</button>
                                <button class="btn btn-secondary btn-delete-comp" data-id="${c.id}" style="font-size: 12px; padding: 6px 10px; color: #ef4444;">Remove</button>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    renderGapTab() {
        if (!this.gapAnalysis || !this.gapAnalysis.keyword_gap || this.gapAnalysis.keyword_gap.length === 0) {
            return `
                <div class="card" style="text-align: center; padding: 48px 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Keyword Gap Analysis</div>
                    <p style="color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px;">
                        Add confirmed competitors to view head-to-head keyword gaps, target vs competitor positions, and high-impact SEO opportunities.
                    </p>
                </div>
            `;
        }

        const items = this.gapAnalysis.keyword_gap;
        const summary = this.gapAnalysis.summary || {};

        return `
            <div style="display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px; background: var(--bg-card); border: 1px solid var(--border-color); padding: 16px; border-radius: 8px;">
                    <div style="font-size: 12px; color: var(--text-secondary);">Target Domain</div>
                    <div style="font-size: 18px; font-weight: 700; color: var(--accent-primary);">${this.escapeHtml(this.gapAnalysis.target_domain)}</div>
                </div>
                <div style="flex: 1; min-width: 200px; background: var(--bg-card); border: 1px solid var(--border-color); padding: 16px; border-radius: 8px;">
                    <div style="font-size: 12px; color: var(--text-secondary);">High-Impact Opportunities</div>
                    <div style="font-size: 18px; font-weight: 700; color: #ef4444;">${summary.high_opportunity_keywords || 0} Keywords</div>
                </div>
                <div style="flex: 1; min-width: 200px; background: var(--bg-card); border: 1px solid var(--border-color); padding: 16px; border-radius: 8px;">
                    <div style="font-size: 12px; color: var(--text-secondary);">Shared Keywords</div>
                    <div style="font-size: 18px; font-weight: 700; color: #10b981;">${summary.shared_keywords || 0} Keywords</div>
                </div>
            </div>

            <div class="table-container" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
                    <thead>
                        <tr style="border-bottom: 1px solid var(--border-color); background: rgba(0,0,0,0.2);">
                            <th style="padding: 12px 16px;">Target Keyword</th>
                            <th style="padding: 12px 16px;">Target Pos</th>
                            <th style="padding: 12px 16px;">Competitor Pos</th>
                            <th style="padding: 12px 16px;">Search Vol</th>
                            <th style="padding: 12px 16px;">Difficulty</th>
                            <th style="padding: 12px 16px;">Opportunity</th>
                            <th style="padding: 12px 16px;">Recommended Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${items.map(row => `
                            <tr style="border-bottom: 1px solid var(--border-color);">
                                <td style="padding: 12px 16px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(row.keyword)}</td>
                                <td style="padding: 12px 16px;">
                                    ${row.target_position === 'Not Ranking' ? 
                                        `<span style="color: #ef4444; font-weight: 600;">Not Ranking</span>` : 
                                        `<strong style="color: #3b82f6;">#${row.target_position}</strong>`}
                                </td>
                                <td style="padding: 12px 16px;"><strong style="color: #10b981;">#${row.competitor_position}</strong></td>
                                <td style="padding: 12px 16px;">${row.search_volume} / mo</td>
                                <td style="padding: 12px 16px;">${row.keyword_difficulty}%</td>
                                <td style="padding: 12px 16px;">
                                    <span style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 12px; background: ${row.opportunity_level === 'HIGH' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)'}; color: ${row.opportunity_level === 'HIGH' ? '#ef4444' : '#f59e0b'};">
                                        ${row.opportunity_level}
                                    </span>
                                </td>
                                <td style="padding: 12px 16px; color: var(--text-secondary); font-size: 13px;">${this.escapeHtml(row.recommended_action)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderModal() {
        const c = this.editingCompetitor || {};
        const isEdit = !!c.id;

        return `
            <div class="modal-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px;">
                <div class="modal-card" style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 12px; width: 100%; max-width: 500px; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h2 style="font-size: 18px; font-weight: 600; margin: 0;">${isEdit ? 'Edit Competitor' : 'Add New Competitor'}</h2>
                        <button id="btn-close-modal" style="background: none; border: none; color: var(--text-secondary); font-size: 20px; cursor: pointer;">&times;</button>
                    </div>

                    <form id="form-competitor">
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px;">Company / Brand Name *</label>
                            <input type="text" name="name" value="${this.escapeHtml(c.name || '')}" placeholder="e.g. Fallon Solutions" required style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                        </div>

                        <div style="margin-bottom: 16px;">
                            <label style="display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px;">Website Domain or URL *</label>
                            <input type="text" name="url" value="${this.escapeHtml(c.url || c.domain || '')}" placeholder="e.g. fallonsolutions.com.au" required style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px;">Location</label>
                                <input type="text" name="location" value="${this.escapeHtml(c.location || 'Brisbane, QLD')}" placeholder="e.g. Brisbane, QLD" style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                            </div>
                            <div>
                                <label style="display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px;">Geographic Level</label>
                                <select name="geographic_level" style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                                    <option value="Town" ${c.geographic_level === 'Town' ? 'selected' : ''}>Town / Suburb</option>
                                    <option value="City" ${!c.geographic_level || c.geographic_level === 'City' ? 'selected' : ''}>City</option>
                                    <option value="State" ${c.geographic_level === 'State' ? 'selected' : ''}>State / Province</option>
                                    <option value="Country" ${c.geographic_level === 'Country' ? 'selected' : ''}>Country</option>
                                    <option value="Global" ${c.geographic_level === 'Global' ? 'selected' : ''}>Global / International</option>
                                </select>
                            </div>
                        </div>

                        <div style="margin-bottom: 16px;">
                            <label style="display: flex; align-items: center; gap: 8px; font-size: 13px; cursor: pointer;">
                                <input type="checkbox" name="is_primary" ${c.is_primary ? 'checked' : ''}>
                                Mark as Primary Competitor
                            </label>
                        </div>

                        <div style="margin-bottom: 20px;">
                            <label style="display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px;">Notes / Strategy</label>
                            <textarea name="notes" rows="3" placeholder="Targeting overlapping battery installation keywords..." style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-family: inherit;">${this.escapeHtml(c.notes || '')}</textarea>
                        </div>

                        <div style="display: flex; justify-content: flex-end; gap: 12px;">
                            <button type="button" id="btn-cancel-modal" class="btn btn-secondary">Cancel</button>
                            <button type="submit" class="btn btn-primary">${isEdit ? 'Save Changes' : 'Add Competitor'}</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    bindEvents() {
        if (!this.container) return;

        // Auto-Discover button
        const btnAuto = this.container.querySelector('#btn-auto-discover');
        if (btnAuto) {
            btnAuto.addEventListener('click', () => this.runAutoDiscovery());
        }

        // Add Manual button
        const btnAdd = this.container.querySelector('#btn-add-manual');
        if (btnAdd) {
            btnAdd.addEventListener('click', () => {
                this.editingCompetitor = null;
                this.showModal = true;
                this.renderState();
            });
        }

        // Tabs navigation
        const tabBtns = this.container.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetTab = e.currentTarget.getAttribute('data-tab');
                if (targetTab) {
                    this.activeTab = targetTab;
                    this.renderState();
                }
            });
        });

        // Approve buttons
        const approveBtns = this.container.querySelectorAll('.btn-approve');
        approveBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.approveCompetitor(id);
            });
        });

        // Ignore buttons
        const ignoreBtns = this.container.querySelectorAll('.btn-ignore');
        ignoreBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.ignoreCompetitor(id);
            });
        });

        // Toggle primary buttons
        const primaryBtns = this.container.querySelectorAll('.btn-toggle-primary');
        primaryBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                const comp = this.confirmedCompetitors.find(c => c.id === id);
                if (comp) this.togglePrimary(comp);
            });
        });

        // Edit buttons
        const editBtns = this.container.querySelectorAll('.btn-edit-comp');
        editBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                const comp = this.confirmedCompetitors.find(c => c.id === id);
                if (comp) {
                    this.editingCompetitor = comp;
                    this.showModal = true;
                    this.renderState();
                }
            });
        });

        // Delete buttons
        const deleteBtns = this.container.querySelectorAll('.btn-delete-comp');
        deleteBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.deleteCompetitor(id);
            });
        });

        // Modal Close/Cancel buttons
        const btnClose = this.container.querySelector('#btn-close-modal');
        if (btnClose) {
            btnClose.addEventListener('click', () => {
                this.showModal = false;
                this.renderState();
            });
        }
        const btnCancel = this.container.querySelector('#btn-cancel-modal');
        if (btnCancel) {
            btnCancel.addEventListener('click', () => {
                this.showModal = false;
                this.renderState();
            });
        }

        // Form Submit
        const formComp = this.container.querySelector('#form-competitor');
        if (formComp) {
            formComp.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(formComp);
                const payload = {
                    name: formData.get('name'),
                    url: formData.get('url'),
                    location: formData.get('location'),
                    geographic_level: formData.get('geographic_level'),
                    is_primary: formData.get('is_primary') === 'on',
                    notes: formData.get('notes')
                };

                const currentProject = projectStore.getCurrentProject();
                if (!currentProject) return;

                try {
                    if (this.editingCompetitor && this.editingCompetitor.id) {
                        await apiClient.put(`/api/projects/${currentProject.id}/competitors/${this.editingCompetitor.id}`, payload);
                    } else {
                        await apiClient.post(`/api/projects/${currentProject.id}/competitors`, payload);
                    }
                    this.showModal = false;
                    this.activeTab = 'confirmed';
                    await this.loadData();
                } catch (err) {
                    alert('Error saving competitor: ' + err.message);
                }
            });
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
