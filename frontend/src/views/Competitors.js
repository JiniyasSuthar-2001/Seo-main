import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';
import { Pagination } from '../components/Pagination.js';

export class Competitors {
    constructor() {
        this.activeTab = 'suggested'; // 'suggested', 'confirmed', 'ignored', 'gap'
        this.suggestedCompetitors = [];
        this.confirmedCompetitors = [];
        this.ignoredCompetitors = [];
        this.gapAnalysis = null;
        this.hasSerpProvider = false;
        this.serpProviderMessage = '';
        this.loading = false;
        this.discovering = false;
        this.error = null;
        this.showModal = false;
        this.showLearnModal = false;
        this.editingCompetitor = null;
        this.unsubscribeStore = null;

        // Pagination state
        this.suggestedPage = 1;
        this.confirmedPage = 1;
        this.ignoredPage = 1;
        this.gapPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
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
        await projectStore.ensureInitialized();
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

            const [suggestedRes, confirmedData, ignoredData, gapData] = await Promise.all([
                apiClient.get(`/api/projects/${projectId}/competitors/discovered`),
                apiClient.get(`/api/projects/${projectId}/competitors?status=Confirmed`),
                apiClient.get(`/api/projects/${projectId}/competitors?status=Ignored`).catch(() => []),
                apiClient.get(`/api/projects/${projectId}/competitors/gap-analysis`).catch(() => null)
            ]);

            if (Array.isArray(suggestedRes)) {
                this.suggestedCompetitors = suggestedRes;
                this.hasSerpProvider = false;
            } else if (suggestedRes && typeof suggestedRes === 'object') {
                this.suggestedCompetitors = suggestedRes.suggested_competitors || [];
                this.hasSerpProvider = !!suggestedRes.has_serp_provider;
                this.serpProviderMessage = suggestedRes.message || '';
            } else {
                this.suggestedCompetitors = [];
                this.hasSerpProvider = false;
            }

            this.confirmedCompetitors = Array.isArray(confirmedData) ? confirmedData : [];
            this.ignoredCompetitors = Array.isArray(ignoredData) ? ignoredData : [];
            this.gapAnalysis = gapData;
            
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
            if (res) {
                this.hasSerpProvider = !!res.has_serp_provider;
                this.serpProviderMessage = res.message || '';
                if (res.suggested_competitors) {
                    this.suggestedCompetitors = res.suggested_competitors;
                }
                if (res.confirmed_competitors) {
                    this.confirmedCompetitors = res.confirmed_competitors;
                }
            }
            this.activeTab = 'suggested';
            this.suggestedPage = 1;
        } catch (err) {
            alert('Competitor discovery notice: ' + err.message);
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

    async unignoreCompetitor(competitorId) {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        try {
            await apiClient.post(`/api/projects/${currentProject.id}/competitors/${competitorId}/unignore`);
            await this.loadData();
        } catch (err) {
            alert('Failed to restore competitor: ' + err.message);
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
            alert('Failed to remove competitor: ' + err.message);
        }
    }

    async togglePrimary(competitorId) {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        try {
            await apiClient.post(`/api/projects/${currentProject.id}/competitors/${competitorId}/toggle-primary`);
            await this.loadData();
        } catch (err) {
            alert('Failed to update primary competitor: ' + err.message);
        }
    }

    async handleSaveCompetitor(formData) {
        const currentProject = projectStore.getCurrentProject();
        if (!currentProject) return;

        try {
            if (this.editingCompetitor && this.editingCompetitor.id) {
                await apiClient.put(`/api/projects/${currentProject.id}/competitors/${this.editingCompetitor.id}`, formData);
            } else {
                await apiClient.post(`/api/projects/${currentProject.id}/competitors`, formData);
            }
            this.showModal = false;
            this.editingCompetitor = null;
            await this.loadData();
        } catch (err) {
            alert('Failed to save competitor: ' + err.message);
        }
    }

    renderState() {
        if (!this.container) return;

        if (this.loading) {
            this.container.innerHTML = `
                <div class="card" style="text-align: center; padding: 48px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px;">Loading Competitor Intelligence...</div>
                    <div style="font-size: 13px; color: var(--text-secondary);">Analyzing search overlap and competitor rankings...</div>
                </div>
            `;
            return;
        }

        if (this.error) {
            this.container.innerHTML = `
                <div class="card" style="text-align: center; padding: 48px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 16px; font-weight: 600; color: #ef4444; margin-bottom: 8px;">Unable to load competitors</div>
                    <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 20px;">${this.escapeHtml(this.error)}</div>
                    <button class="btn btn-primary btn-sm" id="btn-retry-comp">Retry</button>
                </div>
            `;
            this.container.querySelector('#btn-retry-comp')?.addEventListener('click', () => this.loadData());
            return;
        }

        const serpMsg = !this.hasSerpProvider 
            ? "SERP data is not connected. Connect a search-result provider or import competitor SERP data to discover market candidates."
            : (this.serpProviderMessage || "Active SERP provider connected.");

        this.container.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Competitors</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Identify and monitor websites competing for the same search keywords and customers.</p>
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button class="btn btn-secondary btn-sm" id="btn-learn-discovery" style="display: flex; align-items: center; gap: 6px;">
                        <span>💡</span> How It Works
                    </button>
                    <button class="btn btn-secondary btn-sm" id="btn-auto-discover" ${this.discovering ? 'disabled' : ''}>
                        ${this.discovering ? 'Finding Competitors...' : '⚡ Find Competitors'}
                    </button>
                    <button class="btn btn-primary btn-sm" id="btn-add-manual">
                        + Add Competitor
                    </button>
                </div>
            </div>

            <!-- TABS -->
            <div style="display: flex; gap: 12px; border-bottom: 1px solid var(--border-color); margin-bottom: 24px; flex-wrap: wrap;">
                <button class="comp-tab ${this.activeTab === 'suggested' ? 'active' : ''}" data-tab="suggested">
                    Suggested Competitors
                    ${this.suggestedCompetitors.length > 0 ? `<span class="badge" style="margin-left: 6px; background: rgba(59,130,246,0.2); color: #60a5fa;">${this.suggestedCompetitors.length}</span>` : ''}
                </button>
                <button class="comp-tab ${this.activeTab === 'confirmed' ? 'active' : ''}" data-tab="confirmed">
                    Confirmed Competitors
                    <span class="badge" style="margin-left: 6px; background: rgba(16,185,129,0.2); color: #34d399;">${this.confirmedCompetitors.length}</span>
                </button>
                <button class="comp-tab ${this.activeTab === 'ignored' ? 'active' : ''}" data-tab="ignored">
                    Ignored
                    ${this.ignoredCompetitors.length > 0 ? `<span class="badge" style="margin-left: 6px; background: rgba(245,158,11,0.2); color: #f59e0b;">${this.ignoredCompetitors.length}</span>` : ''}
                </button>
                <button class="comp-tab ${this.activeTab === 'gap' ? 'active' : ''}" data-tab="gap">
                    Keyword Gap Analysis
                </button>
            </div>

            <div style="margin-bottom: 20px; padding: 12px 16px; background: ${this.hasSerpProvider ? 'rgba(16, 185, 129, 0.08)' : 'rgba(245, 158, 11, 0.08)'}; border: 1px solid ${this.hasSerpProvider ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)'}; border-radius: 8px; font-size: 13px; color: var(--text-secondary); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <span>ℹ️ ${this.escapeHtml(serpMsg)}</span>
                <a href="/integrations" data-link style="color: var(--accent-primary, #3b82f6); text-decoration: none; font-weight: 600;">Manage Integrations &rarr;</a>
            </div>

            <!-- TAB CONTENT -->
            <div id="competitor-tab-content">
                ${this.renderTabContent()}
            </div>

            <!-- MODALS -->
            ${this.showModal ? this.renderModal() : ''}
            ${this.showLearnModal ? this.renderLearnModal() : ''}
        `;

        // Append Pagination Controls if slot exists
        const sugSlot = this.container.querySelector('#suggested-pagination-slot');
        if (sugSlot && this.suggestedCompetitors.length > 0) {
            const pag = new Pagination({
                totalItems: this.suggestedCompetitors.length,
                currentPage: this.suggestedPage,
                pageSize: this.pageSize,
                onPageChange: (newPage) => {
                    this.suggestedPage = newPage;
                    this.renderState();
                }
            });
            sugSlot.appendChild(pag.render());
        }

        const confSlot = this.container.querySelector('#confirmed-pagination-slot');
        if (confSlot && this.confirmedCompetitors.length > 0) {
            const pag = new Pagination({
                totalItems: this.confirmedCompetitors.length,
                currentPage: this.confirmedPage,
                pageSize: this.pageSize,
                onPageChange: (newPage) => {
                    this.confirmedPage = newPage;
                    this.renderState();
                }
            });
            confSlot.appendChild(pag.render());
        }

        const ignSlot = this.container.querySelector('#ignored-pagination-slot');
        if (ignSlot && this.ignoredCompetitors.length > 0) {
            const pag = new Pagination({
                totalItems: this.ignoredCompetitors.length,
                currentPage: this.ignoredPage,
                pageSize: this.pageSize,
                onPageChange: (newPage) => {
                    this.ignoredPage = newPage;
                    this.renderState();
                }
            });
            ignSlot.appendChild(pag.render());
        }

        const gapSlot = this.container.querySelector('#gap-pagination-slot');
        if (gapSlot && this.gapAnalysis && this.gapAnalysis.keyword_gap) {
            const items = this.gapAnalysis.keyword_gap;
            const pag = new Pagination({
                totalItems: items.length,
                currentPage: this.gapPage,
                pageSize: this.pageSize,
                onPageChange: (newPage) => {
                    this.gapPage = newPage;
                    this.renderState();
                }
            });
            gapSlot.appendChild(pag.render());
        }

        this.bindEvents();
    }

    renderTabContent() {
        if (this.activeTab === 'suggested') {
            return this.renderSuggestedTab();
        } else if (this.activeTab === 'confirmed') {
            return this.renderConfirmedTab();
        } else if (this.activeTab === 'ignored') {
            return this.renderIgnoredTab();
        } else if (this.activeTab === 'gap') {
            return this.renderGapTab();
        }
        return '';
    }

    renderSuggestedTab() {
        if (this.suggestedCompetitors.length === 0) {
            if (!this.hasSerpProvider) {
                return `
                    <div class="card" style="text-align: center; padding: 48px 24px; background: var(--bg-card); border-radius: 12px; border: 1px dashed var(--border-color); max-width: 680px; margin: 0 auto;">
                        <div style="width: 56px; height: 56px; border-radius: 14px; background: rgba(59, 130, 246, 0.1); color: var(--accent-primary, #3b82f6); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        </div>
                        <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">SERP Data Is Not Connected</h3>
                        <p style="font-size: 13.5px; color: var(--text-secondary); margin: 0 auto 20px; line-height: 1.6;">
                            Auto-discovering competitors requires a connected search-result provider or an imported SERP dataset.
                        </p>
                        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                            <button class="btn btn-primary btn-sm" id="btn-add-manual-empty" onclick="document.getElementById('btn-add-manual').click()">+ Add Competitor Manually</button>
                            <a href="/integrations" data-link class="btn btn-secondary btn-sm">Connect Integration</a>
                            <a href="/import" data-link class="btn btn-secondary btn-sm">Import Data</a>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="card" style="text-align: center; padding: 48px 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">No Pending Suggested Competitors</div>
                    <p style="color: var(--text-secondary); max-width: 480px; margin: 0 auto 20px;">
                        All auto-discovered competitors have been approved or ignored. Click <strong>Find Competitors</strong> to scan SERPs for new market candidates.
                    </p>
                    <button class="btn btn-primary" id="btn-scan-serps">Find Competitors</button>
                </div>
            `;
        }

        const paginated = Pagination.paginateArray(this.suggestedCompetitors, this.suggestedPage, this.pageSize);
        this.suggestedPage = paginated.currentPage;

        return `
            <div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; margin-bottom: 16px;">
                    ${paginated.items.map(c => `
                        <div class="card competitor-card" style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                    <div>
                                        <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 4px 0;">${this.escapeHtml(c.name)}</h3>
                                        <a href="${this.escapeHtml(c.url)}" target="_blank" style="color: var(--accent-primary, #3b82f6); font-size: 13px; text-decoration: none;">${this.escapeHtml(c.domain)} &rarr;</a>
                                    </div>
                                    <span style="background: ${c.relevance_score != null ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255, 255, 255, 0.08)'}; color: ${c.relevance_score != null ? '#10b981' : 'var(--text-secondary)'}; border: 1px solid ${c.relevance_score != null ? 'rgba(16, 185, 129, 0.3)' : 'var(--border-color)'}; font-size: 13px; font-weight: 700; padding: 4px 10px; border-radius: 20px;">
                                        ${c.relevance_score != null ? `${c.relevance_score}% Match` : 'Match: Not available'}
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
                                    <div><strong style="color: var(--text-primary);">${c.keyword_overlap != null ? c.keyword_overlap : 'Not available'}</strong> Overlapping Keywords</div>
                                    <div><strong style="color: var(--text-primary);">${c.search_appearances != null ? c.search_appearances : 'Not available'}</strong> SERP Appearances</div>
                                </div>

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
                <div id="suggested-pagination-slot" style="background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);"></div>
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

        const paginated = Pagination.paginateArray(this.confirmedCompetitors, this.confirmedPage, this.pageSize);
        this.confirmedPage = paginated.currentPage;

        return `
            <div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; margin-bottom: 16px;">
                    ${paginated.items.map(c => `
                        <div class="card competitor-card" style="background: var(--bg-card, #1e293b); border: 1px solid ${c.is_primary ? 'var(--accent-primary, #3b82f6)' : 'var(--border-color, #334155)'}; border-radius: 12px; padding: 20px; position: relative;">
                            ${c.is_primary ? `
                                <span style="position: absolute; top: -10px; right: 16px; background: var(--accent-primary, #3b82f6); color: #fff; font-size: 11px; font-weight: 700; padding: 2px 10px; border-radius: 10px;">PRIMARY COMPETITOR</span>
                            ` : ''}

                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                <div>
                                    <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 4px 0;">${this.escapeHtml(c.name)}</h3>
                                    <a href="${this.escapeHtml(c.url)}" target="_blank" style="color: var(--accent-primary, #3b82f6); font-size: 13px; text-decoration: none;">${this.escapeHtml(c.domain)} &rarr;</a>
                                </div>
                                <span style="background: ${c.relevance_score != null ? 'rgba(59, 130, 246, 0.15)' : 'rgba(255, 255, 255, 0.08)'}; color: ${c.relevance_score != null ? '#60a5fa' : 'var(--text-secondary)'}; font-size: 13px; font-weight: 700; padding: 4px 10px; border-radius: 20px;">
                                    ${c.relevance_score != null ? `${c.relevance_score}% Relevance` : 'Relevance: Not available'}
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
                                <div><strong style="color: var(--text-primary);">${c.keyword_overlap != null ? c.keyword_overlap : 'Not available'}</strong> Keyword Overlap</div>
                                <div><strong style="color: var(--text-primary);">${c.search_appearances != null ? c.search_appearances : 'Not available'}</strong> SERP Appearances</div>
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
                <div id="confirmed-pagination-slot" style="background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);"></div>
            </div>
        `;
    }

    renderIgnoredTab() {
        if (this.ignoredCompetitors.length === 0) {
            return `
                <div class="card" style="text-align: center; padding: 48px 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">No Ignored Competitors</div>
                    <p style="color: var(--text-secondary); max-width: 480px; margin: 0 auto;">
                        Any competitors you ignore from the Suggested tab will appear here. You can restore them to your active suggestions anytime.
                    </p>
                </div>
            `;
        }

        const paginated = Pagination.paginateArray(this.ignoredCompetitors, this.ignoredPage, this.pageSize);
        this.ignoredPage = paginated.currentPage;

        return `
            <div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 20px; margin-bottom: 16px;">
                    ${paginated.items.map(c => `
                        <div class="card competitor-card" style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; opacity: 0.85;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                    <div>
                                        <h3 style="font-size: 16px; font-weight: 600; margin: 0 0 4px 0;">${this.escapeHtml(c.name)}</h3>
                                        <a href="${this.escapeHtml(c.url)}" target="_blank" style="color: var(--accent-primary, #3b82f6); font-size: 13px; text-decoration: none;">${this.escapeHtml(c.domain)} &rarr;</a>
                                    </div>
                                    <span style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 20px;">
                                        Ignored
                                    </span>
                                </div>
                                <div style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 16px;">
                                    Domain: <strong>${this.escapeHtml(c.domain)}</strong>
                                </div>
                            </div>
                            <div style="display: flex; gap: 10px; margin-top: 12px; border-top: 1px solid var(--border-color); padding-top: 14px;">
                                <button class="btn btn-secondary btn-unignore" data-id="${c.id}" style="flex: 1; padding: 8px; font-size: 13px;">
                                    ↩ Restore to Suggested
                                </button>
                                <button class="btn btn-secondary btn-delete-comp" data-id="${c.id}" style="padding: 8px 12px; font-size: 13px; color: #ef4444;">
                                    Delete
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div id="ignored-pagination-slot" style="background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);"></div>
            </div>
        `;
    }

    renderGapTab() {
        if (!this.gapAnalysis || !this.gapAnalysis.keyword_gap || this.gapAnalysis.keyword_gap.length === 0) {
            return `
                <div class="card" style="text-align: center; padding: 48px 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">Keyword Gap & Competitor Rankings</div>
                    <p style="color: var(--text-secondary); max-width: 520px; margin: 0 auto 20px;">
                        Add confirmed competitors and import competitor rankings or connect a SERP provider to view real head-to-head ranking gaps.
                    </p>
                    <div style="display: flex; justify-content: center; gap: 10px;">
                        <a href="/import" data-link class="btn btn-secondary btn-sm">Import Competitor Rankings CSV</a>
                        <a href="/integrations" data-link class="btn btn-primary btn-sm">Configure SERP Provider</a>
                    </div>
                </div>
            `;
        }

        const items = this.gapAnalysis.keyword_gap;
        const summary = this.gapAnalysis.summary || {};
        const paginated = Pagination.paginateArray(items, this.gapPage, this.pageSize);
        this.gapPage = paginated.currentPage;

        return `
            <div>
                <!-- KPI SUMMARY CARDS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
                    <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 16px; border-radius: 10px;">
                        <div style="font-size: 12px; color: var(--text-secondary);">Target Website</div>
                        <div style="font-size: 16px; font-weight: 700; color: var(--accent-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(this.gapAnalysis.target_domain)}</div>
                    </div>
                    <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 16px; border-radius: 10px;">
                        <div style="font-size: 12px; color: var(--text-secondary);">High-Impact Opportunities</div>
                        <div style="font-size: 18px; font-weight: 700; color: #ef4444;">${summary.high_opportunity_keywords || 0} Keywords</div>
                    </div>
                    <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 16px; border-radius: 10px;">
                        <div style="font-size: 12px; color: var(--text-secondary);">Your Ranking Leads</div>
                        <div style="font-size: 18px; font-weight: 700; color: #10b981;">${summary.winning_keywords || 0} Keywords</div>
                    </div>
                    <div style="background: var(--bg-card); border: 1px solid var(--border-color); padding: 16px; border-radius: 10px;">
                        <div style="font-size: 12px; color: var(--text-secondary);">Shared Head-to-Head</div>
                        <div style="font-size: 18px; font-weight: 700; color: #3b82f6;">${summary.shared_keywords || 0} Keywords</div>
                    </div>
                </div>

                <!-- TABLE HEADER CONTROLS -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                    <div style="font-size: 13.5px; color: var(--text-secondary);">
                        Showing verified search ranking positions and mathematical gap analysis.
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <a href="/import" data-link class="btn btn-secondary btn-sm" title="Upload Competitor Rankings CSV">
                            <span>📥</span> Import Rankings CSV
                        </a>
                    </div>
                </div>

                <div class="table-container" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden;">
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13.5px;">
                            <thead>
                                <tr style="border-bottom: 1px solid var(--border-color); background: rgba(0,0,0,0.2);">
                                    <th style="padding: 12px 14px;">Keyword</th>
                                    <th style="padding: 12px 14px;">Your Position</th>
                                    <th style="padding: 12px 14px;">Competitor</th>
                                    <th style="padding: 12px 14px;">Competitor Pos</th>
                                    <th style="padding: 12px 14px;">Gap</th>
                                    <th style="padding: 12px 14px;">Data Source</th>
                                    <th style="padding: 12px 14px;">Opportunity</th>
                                    <th style="padding: 12px 14px;">Recommended Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${paginated.items.map(row => {
                                    const hasTarget = row.target_position !== null && row.target_position !== undefined;
                                    const hasComp = row.competitor_position !== null && row.competitor_position !== undefined;
                                    const diff = row.position_difference;

                                    let gapBadge = '<span style="color: var(--text-tertiary); font-size: 12px;">N/A</span>';
                                    if (diff !== null && diff !== undefined) {
                                        if (diff > 0) {
                                            gapBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 10px; background: rgba(16, 185, 129, 0.15); color: #10b981; font-weight: 700; font-size: 11.5px;">+${diff} (Lead)</span>`;
                                        } else if (diff < 0) {
                                            gapBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 10px; background: rgba(239, 68, 68, 0.15); color: #ef4444; font-weight: 700; font-size: 11.5px;">${diff} (Behind)</span>`;
                                        } else {
                                            gapBadge = `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 10px; background: var(--bg-subtle); color: var(--text-secondary); font-weight: 700; font-size: 11.5px;">0 (Tied)</span>`;
                                        }
                                    }

                                    const sourceName = row.source_display || (row.source ? row.source.replace('_', ' ') : 'Not Checked');
                                    const isSerp = row.source === 'serp_provider';
                                    const isCsv = row.source === 'csv_import';

                                    return `
                                        <tr style="border-bottom: 1px solid var(--border-color);">
                                            <td style="padding: 12px 14px; font-weight: 600; color: var(--text-primary);">
                                                ${this.escapeHtml(row.keyword)}
                                            </td>
                                            <td style="padding: 12px 14px;">
                                                ${hasTarget ? 
                                                    `<strong style="color: #3b82f6; font-size: 14px;">#${row.target_position}</strong>` : 
                                                    `<span style="color: var(--text-tertiary); font-size: 12px;">Not Ranking</span>`}
                                            </td>
                                            <td style="padding: 12px 14px; color: var(--text-secondary);">
                                                <div style="font-weight: 600; color: var(--text-primary);">${this.escapeHtml(row.competitor_name || 'Competitor')}</div>
                                                ${row.competitor_domain ? `<div style="font-size: 11px; color: var(--text-tertiary);">${this.escapeHtml(row.competitor_domain)}</div>` : ''}
                                            </td>
                                            <td style="padding: 12px 14px;">
                                                ${hasComp ? 
                                                    `<strong style="color: #10b981; font-size: 14px;">#${row.competitor_position}</strong>` : 
                                                    `<span style="color: var(--text-tertiary); font-size: 12px;">Data Unavailable</span>`}
                                            </td>
                                            <td style="padding: 12px 14px;">
                                                ${gapBadge}
                                            </td>
                                            <td style="padding: 12px 14px;">
                                                <span class="badge ${isSerp ? 'badge-success' : (isCsv ? 'badge-secondary' : 'badge-subtle')}" style="font-size: 10.5px; text-transform: uppercase;">
                                                    ${this.escapeHtml(sourceName)}
                                                </span>
                                            </td>
                                            <td style="padding: 12px 14px;">
                                                <span style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 12px; background: ${row.opportunity_level === 'HIGH' ? 'rgba(239, 68, 68, 0.15)' : (row.opportunity_level === 'LOW' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)')}; color: ${row.opportunity_level === 'HIGH' ? '#ef4444' : (row.opportunity_level === 'LOW' ? '#10b981' : '#f59e0b')};">
                                                    ${row.opportunity_level}
                                                </span>
                                            </td>
                                            <td style="padding: 12px 14px; color: var(--text-secondary); font-size: 12.5px;">
                                                ${this.escapeHtml(row.recommended_action || '')}
                                            </td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                    <div id="gap-pagination-slot"></div>
                </div>
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
                            <input type="text" name="name" value="${this.escapeHtml(c.name || '')}" placeholder="e.g. Competitor Brand" required style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                        </div>

                        <div style="margin-bottom: 16px;">
                            <label style="display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px;">Website Domain or URL *</label>
                            <input type="text" name="url" value="${this.escapeHtml(c.url || c.domain || '')}" placeholder="e.g. competitor.com" required style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <label style="display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px;">Location</label>
                                <input type="text" name="location" value="${this.escapeHtml(c.location || 'Local Market')}" placeholder="e.g. Local Market" style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
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
                            <textarea name="notes" rows="3" placeholder="Targeting overlapping keywords..." style="width: 100%; padding: 10px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-family: inherit;">${this.escapeHtml(c.notes || '')}</textarea>
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

    renderLearnModal() {
        return `
            <div class="modal-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px;">
                <div class="modal-card" style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 12px; width: 100%; max-width: 580px; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h2 style="font-size: 18px; font-weight: 600; margin: 0; color: var(--text-primary);">How Competitor Discovery Works</h2>
                        <button id="btn-close-learn-modal" style="background: none; border: none; color: var(--text-secondary); font-size: 20px; cursor: pointer;">&times;</button>
                    </div>

                    <div style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 20px;">
                        <p style="margin-bottom: 12px;">
                            Our platform analyzes search engine results pages (SERPs) and website content overlap to discover businesses competing for the exact same target keywords in your market.
                        </p>
                    </div>

                    <div style="text-align: right;">
                        <button id="btn-dismiss-learn-modal" class="btn btn-primary btn-sm">Got It</button>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        if (!this.container) return;

        this.container.querySelectorAll('.comp-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const targetTab = e.currentTarget.getAttribute('data-tab');
                if (targetTab && targetTab !== this.activeTab) {
                    this.activeTab = targetTab;
                    this.renderState();
                }
            });
        });

        this.container.querySelector('#btn-learn-discovery')?.addEventListener('click', () => {
            this.showLearnModal = true;
            this.renderState();
        });

        this.container.querySelector('#btn-close-learn-modal')?.addEventListener('click', () => {
            this.showLearnModal = false;
            this.renderState();
        });

        this.container.querySelector('#btn-dismiss-learn-modal')?.addEventListener('click', () => {
            this.showLearnModal = false;
            this.renderState();
        });

        this.container.querySelector('#btn-auto-discover')?.addEventListener('click', () => this.runAutoDiscovery());
        this.container.querySelector('#btn-scan-serps')?.addEventListener('click', () => this.runAutoDiscovery());

        this.container.querySelector('#btn-add-manual')?.addEventListener('click', () => {
            this.editingCompetitor = null;
            this.showModal = true;
            this.renderState();
        });

        this.container.querySelector('#btn-close-modal')?.addEventListener('click', () => {
            this.showModal = false;
            this.editingCompetitor = null;
            this.renderState();
        });

        this.container.querySelector('#btn-cancel-modal')?.addEventListener('click', () => {
            this.showModal = false;
            this.editingCompetitor = null;
            this.renderState();
        });

        const form = this.container.querySelector('#form-competitor');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = {
                    name: form.name.value.trim(),
                    url: form.url.value.trim(),
                    location: form.location.value.trim() || 'Local Market',
                    geographic_level: form.geographic_level.value,
                    is_primary: form.is_primary.checked,
                    notes: form.notes.value.trim()
                };
                this.handleSaveCompetitor(formData);
            });
        }

        this.container.querySelectorAll('.btn-approve').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.approveCompetitor(id);
            });
        });

        this.container.querySelectorAll('.btn-ignore').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.ignoreCompetitor(id);
            });
        });

        this.container.querySelectorAll('.btn-unignore').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.unignoreCompetitor(id);
            });
        });

        this.container.querySelectorAll('.btn-toggle-primary').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.togglePrimary(id);
            });
        });

        this.container.querySelectorAll('.btn-edit-comp').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                const comp = this.confirmedCompetitors.find(c => String(c.id) === String(id));
                if (comp) {
                    this.editingCompetitor = comp;
                    this.showModal = true;
                    this.renderState();
                }
            });
        });

        this.container.querySelectorAll('.btn-delete-comp').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (id) this.deleteCompetitor(id);
            });
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
