import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Opportunities {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'opportunities-view';
        this.activeCategory = 'all';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600;">SEO Action Center</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px;">Central opportunity engine with deterministic priority scoring across 6 SEO pillars.</p>
                </div>
                <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">
                    Run Crawl Analysis
                </button>
            </div>

            <!-- CATEGORY PILL TABS -->
            <div style="display: flex; gap: 8px; border-bottom: 1px solid var(--border); margin-bottom: 20px; padding-bottom: 8px; flex-wrap: wrap;" id="opp-tabs">
                <button class="opp-tab ${this.activeCategory === 'all' ? 'active' : ''}" data-cat="all">All Opportunities</button>
                <button class="opp-tab ${this.activeCategory === 'Technical' ? 'active' : ''}" data-cat="Technical">Technical</button>
                <button class="opp-tab ${this.activeCategory === 'Content' ? 'active' : ''}" data-cat="Content">Content</button>
                <button class="opp-tab ${this.activeCategory === 'Keywords' ? 'active' : ''}" data-cat="Keywords">Keywords</button>
                <button class="opp-tab ${this.activeCategory === 'Internal Links' ? 'active' : ''}" data-cat="Internal Links">Internal Links</button>
                <button class="opp-tab ${this.activeCategory === 'Backlinks' ? 'active' : ''}" data-cat="Backlinks">Backlinks</button>
                <button class="opp-tab ${this.activeCategory === 'Competitors' ? 'active' : ''}" data-cat="Competitors">Competitors</button>
            </div>

            <div id="opportunities-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading SEO action opportunities...
                </div>
            </div>

            <style>
                .opp-tab {
                    padding: 6px 14px;
                    border: none;
                    background: transparent;
                    color: var(--text-secondary);
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                    border-bottom: 2px solid transparent;
                    transition: all 0.15s ease;
                }
                .opp-tab:hover { color: var(--text-primary); }
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
                    this.activeCategory = e.target.dataset.cat;
                    this.mounted();
                });
            });
        }, 50);
    }

    async updateStatus(oppId, newStatus) {
        try {
            await apiClient.put(`/api/projects/opportunities/${oppId}/status`, { status: newStatus });

            this.mounted();
        } catch (e) {
            alert("Failed to update status: " + e.message);
        }
    }

    async mounted() {
        const container = document.getElementById('opportunities-content');
        if (!container) return;

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create an SEO project workspace.</div>`;
                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/opportunities?category=${this.activeCategory}`);
            const opps = data.opportunities || data || [];


            if (opps.length === 0) {
                container.innerHTML = `
                    <div class="card" style="padding: 32px; text-align: center;">
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">No ${this.activeCategory !== 'all' ? this.activeCategory : ''} Opportunities Found</div>
                        <p style="color: var(--text-secondary); font-size: 13px; max-width: 500px; margin: 0 auto 16px;">
                            Run a website crawl snapshot to generate deterministic SEO action items.
                        </p>
                        <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Run Website Crawl</button>
                    </div>
                `;
                return;
            }

            let cards = opps.map(opp => {
                let badgeStyle = 'background: rgba(239,68,68,0.1); color: var(--critical);';
                if (opp.priority_level === 'HIGH') badgeStyle = 'background: rgba(245,158,11,0.1); color: var(--warning);';
                else if (opp.priority_level === 'MEDIUM') badgeStyle = 'background: rgba(59,130,246,0.1); color: var(--primary);';

                return `
                    <div class="card" style="padding: 20px; margin-bottom: 12px; border-left: 4px solid ${opp.priority_level === 'CRITICAL' ? 'var(--critical)' : (opp.priority_level === 'HIGH' ? 'var(--warning)' : 'var(--primary)')};">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                            <div style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                                    <span style="font-weight: 700; font-size: 15px;">${opp.title}</span>
                                    <span class="badge" style="${badgeStyle}; font-size: 10px; font-weight: 700;">
                                        ${opp.priority_level} (${opp.priority_score})
                                    </span>
                                    <span class="badge badge-info" style="font-size: 10px;">${opp.category}</span>
                                    <span class="badge" style="background: var(--bg-subtle); color: var(--text-secondary); font-size: 10px;">Status: ${opp.status}</span>
                                </div>
                                <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">
                                    ${opp.impact || ''}
                                </div>
                                ${opp.evidence ? `<div style="font-size: 12px; font-family: monospace; background: var(--bg-subtle); padding: 8px; border-radius: 4px; color: var(--text-secondary); margin-bottom: 8px;">Evidence: ${opp.evidence}</div>` : ''}
                                <div style="font-size: 12px; color: var(--primary); font-weight: 500;">
                                    Recommendation: ${opp.recommendation}
                                </div>
                            </div>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                <button class="btn btn-secondary btn-sm" onclick="window.updateOppStatus('${opp.id}', 'In Progress')">Mark In Progress</button>
                                <button class="btn btn-secondary btn-sm" onclick="window.updateOppStatus('${opp.id}', 'Resolved')">Mark Resolved</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            window.updateOppStatus = (id, st) => this.updateStatus(id, st);

            container.innerHTML = `
                <div style="margin-bottom: 12px; font-size: 12px; color: var(--text-secondary); display: flex; justify-content: space-between;">
                    <span>Showing <strong>${opps.length}</strong> action items derived from deterministic evidence engine.</span>
                </div>
                ${cards}
            `;

        } catch (e) {
            if (e.name === 'TypeError' || e.message.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Opportunities Load Error", e.message || "Unable to load SEO opportunities.", () => this.mounted());
            }
        }
    }
}
