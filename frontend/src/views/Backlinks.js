import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';

export class Backlinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'backlinks-view';
        this.activeTab = 'outbound'; // 'outbound', 'inbound', 'gap'
        
        // Outbound links state
        this.outboundLinks = [];
        this.outboundSummary = {};
        this.summary = {};
        this.provenance = {};
        
        // Filtering & pagination state
        this.searchQuery = '';
        this.domainFilter = 'all';
        this.typeFilter = 'all';
        this.statusFilter = 'all';
        this.currentPage = 1;
        this.pageSize = 25;
        this.sortBy = 'source'; // 'source', 'domain'
        this.sortOrder = 'asc';
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 600; color: var(--text-primary);">Backlink & Link Intelligence</h1>
                    <p style="color: var(--text-secondary); margin-top: 4px; font-size: 14px;">Real crawl outbound links, inbound backlink datasets, and competitor link gap analysis.</p>
                </div>
                <div id="backlinks-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                <button class="btn ${this.activeTab === 'outbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-outbound-btn" style="font-size: 13px;">Outbound External Links (Crawled Data)</button>
                <button class="btn ${this.activeTab === 'inbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-inbound-btn" style="font-size: 13px;">Inbound Backlinks</button>
                <button class="btn ${this.activeTab === 'gap' ? 'btn-primary' : 'btn-secondary'}" id="tab-gap-btn" style="font-size: 13px;">Backlink Gap vs Competitors</button>
            </div>

            <div id="backlinks-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading link intelligence...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('backlinks-content');
        const actionsContainer = document.getElementById('backlinks-actions');
        if (!container) return;

        document.getElementById('tab-outbound-btn')?.addEventListener('click', () => { this.activeTab = 'outbound'; this.mounted(); });
        document.getElementById('tab-inbound-btn')?.addEventListener('click', () => { this.activeTab = 'inbound'; this.mounted(); });
        document.getElementById('tab-gap-btn')?.addEventListener('click', () => { this.activeTab = 'gap'; this.mounted(); });

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select or create a project workspace.</div>`;
                return;
            }

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <button id="btn-export-backlinks-pdf" class="btn btn-secondary btn-sm">📄 Guidelines PDF</button>
                    <a href="#/import" class="btn btn-secondary btn-sm">Import Backlinks CSV</a>
                    <button id="btn-export-backlinks-csv" class="btn btn-secondary btn-sm">Export CSV</button>
                `;

                const pdfBtn = document.getElementById('btn-export-backlinks-pdf');
                const csvBtn = document.getElementById('btn-export-backlinks-csv');
                if (pdfBtn) pdfBtn.onclick = (e) => apiClient.downloadFile(`/api/guidelines/backlinks/pdf`, 'backlinks-guidelines.pdf', e.currentTarget);
                if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/backlinks/export.csv`, 'backlinks.csv', e.currentTarget);
            }

            if (this.activeTab === 'gap') {
                const gapData = await apiClient.get(`/api/projects/${projectId}/backlinks/gap-analysis`);
                this.renderGapTab(container, gapData);
                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/backlinks`);
            this.outboundLinks = data.outbound_links || [];
            this.outboundSummary = data.outbound_summary || {};
            this.summary = data.summary || {};
            this.provenance = data.provenance || {};
            this.inboundBacklinks = data.backlinks || [];

            if (this.activeTab === 'inbound') {
                this.renderInboundTab(container);
            } else {
                this.renderOutboundTab(container);
            }

        } catch (e) {
            if (e.name === 'TypeError' || e.message?.includes('fetch') || apiClient.status === 'OFFLINE') {
                renderBackendOfflineState(container, "Unable to connect to backend server.", () => this.mounted());
            } else {
                renderFeatureErrorState(container, "Backlink Intelligence Error", e.message || "Unable to load backlink data.", () => this.mounted());
            }
        }
    }

    renderGapTab(container, gapData) {
        container.innerHTML = `
            <div class="card" style="padding: 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Backlink Gap Analysis vs Confirmed Competitors</h3>
                <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 16px;">
                    ${gapData.message || "Identifies referring domains linking to competitors but not to your target domain."}
                </p>
                <div style="padding: 20px; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 13px; color: var(--text-secondary); text-align: center;">
                    Confirmed Competitors Evaluated: <strong style="color: var(--text-primary);">${gapData.confirmed_competitors_count || 0}</strong>.
                    Import competitor backlink datasets to reveal intersecting link gap opportunities.
                </div>
            </div>
        `;
    }

    renderInboundTab(container) {
        const prov = this.provenance || {};
        const summary = this.summary || {};

        let inboundBody = '';
        if (this.inboundBacklinks.length === 0) {
            inboundBody = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 680px; margin: 0 auto; background: var(--bg-card); border-radius: 12px; border: 1px dashed var(--border-color);">
                    <div style="width: 56px; height: 56px; border-radius: 14px; background: rgba(59, 130, 246, 0.1); color: var(--accent-primary, #3b82f6); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                    </div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No Inbound Backlink Dataset Connected</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        Your website crawler can find links from your website to other websites (outbound links). Discovering external websites linking TO your domain requires backlink data from an external provider, Search Console where applicable, or an imported dataset.
                    </p>
                    <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                        <a href="/integrations" data-link class="btn btn-primary btn-sm">Connect Data Provider</a>
                        <a href="/import" data-link class="btn btn-secondary btn-sm">Import Backlinks CSV</a>
                    </div>
                </div>
            `;
        } else {
            const rowsHtml = this.inboundBacklinks.map(b => `
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: 12px 16px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(b.source_domain || b.source_url || 'External Domain')}</td>
                    <td style="padding: 12px 16px; color: var(--text-secondary);">${this.escapeHtml(b.target_url || '/')}</td>
                    <td style="padding: 12px 16px; color: var(--text-secondary);">${this.escapeHtml(b.anchor_text || 'Generic Link')}</td>
                    <td style="padding: 12px 16px;"><span class="badge" style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(59,130,246,0.15); color: #60a5fa;">${this.escapeHtml(b.link_type || 'Follow')}</span></td>
                </tr>
            `).join('');

            inboundBody = `
                <div class="card" style="padding: 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h3 style="font-size: 16px; font-weight: 700;">Inbound Backlinks</h3>
                        <span style="font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 6px; background: rgba(255,255,255,0.06); color: var(--text-secondary); border: 1px solid var(--border-color);">${this.escapeHtml(prov.source_label || 'Imported Data')}</span>
                    </div>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 13.5px; text-align: left;">
                            <thead>
                                <tr style="background: rgba(0,0,0,0.2); border-bottom: 1px solid var(--border-color); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 16px;">Source Domain</th>
                                    <th style="padding: 12px 16px;">Target URL</th>
                                    <th style="padding: 12px 16px;">Anchor Text</th>
                                    <th style="padding: 12px 16px;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rowsHtml}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        container.innerHTML = `
            <!-- Top KPI Cards -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">INBOUND BACKLINKS</span>
                        <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2);">${this.escapeHtml(prov.source_label || 'Unavailable')}</span>
                    </div>
                    <div style="font-size: 28px; font-weight: 700; color: var(--text-primary);">${summary.inbound_backlinks || 0}</div>
                </div>

                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">REFERRING DOMAINS</span>
                        <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2);">${this.escapeHtml(prov.source_label || 'Unavailable')}</span>
                    </div>
                    <div style="font-size: 28px; font-weight: 700; color: var(--text-primary);">${summary.referring_domains || 0}</div>
                </div>

                <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;">OUTBOUND EXTERNAL LINKS</span>
                        <span style="font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2);">Crawled Data</span>
                    </div>
                    <div style="font-size: 28px; font-weight: 700; color: #10b981;">${summary.outbound_external_links || 0}</div>
                </div>
            </div>

            ${inboundBody}
        `;
    }

    renderOutboundTab(container) {
        const outSummary = this.outboundSummary || {};
        const prov = this.provenance || {};

        // Extract unique domains for dropdown filter
        const domainsSet = new Set();
        this.outboundLinks.forEach(l => {
            if (l.destination_domain && l.destination_domain !== 'Not collected') {
                domainsSet.add(l.destination_domain);
            }
        });
        const domainsList = Array.from(domainsSet).sort();

        // Apply filters & search
        let filtered = this.outboundLinks.filter(l => {
            if (this.searchQuery) {
                const q = this.searchQuery.toLowerCase();
                const matchSrc = (l.source_url || '').toLowerCase().includes(q);
                const matchDest = (l.destination_url || '').toLowerCase().includes(q);
                const matchDom = (l.destination_domain || '').toLowerCase().includes(q);
                const matchAnchor = (l.anchor_text || '').toLowerCase().includes(q);
                if (!matchSrc && !matchDest && !matchDom && !matchAnchor) return false;
            }

            if (this.domainFilter !== 'all') {
                if (l.destination_domain !== this.domainFilter) return false;
            }

            if (this.typeFilter !== 'all') {
                const lType = (l.link_type || '').toLowerCase();
                if (this.typeFilter === 'nofollow' && !lType.includes('nofollow')) return false;
                if (this.typeFilter === 'sponsored' && !lType.includes('sponsored')) return false;
                if (this.typeFilter === 'ugc' && !lType.includes('ugc')) return false;
                if (this.typeFilter === 'follow' && lType.includes('nofollow')) return false;
            }

            if (this.statusFilter !== 'all') {
                if (this.statusFilter === 'ok' && l.status_code !== 200) return false;
                if (this.statusFilter === 'broken' && (typeof l.status_code !== 'number' || l.status_code < 400)) return false;
                if (this.statusFilter === 'unchecked' && l.status_code !== 'Not checked') return false;
            }

            return true;
        });

        // Apply sorting
        filtered.sort((a, b) => {
            let valA = (a[this.sortBy === 'domain' ? 'destination_domain' : 'source_url'] || '').toLowerCase();
            let valB = (b[this.sortBy === 'domain' ? 'destination_domain' : 'source_url'] || '').toLowerCase();
            if (valA < valB) return this.sortOrder === 'asc' ? -1 : 1;
            if (valA > valB) return this.sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        // Pagination
        const totalCount = filtered.length;
        const totalPages = Math.ceil(totalCount / this.pageSize) || 1;
        if (this.currentPage > totalPages) this.currentPage = 1;

        const startIndex = (this.currentPage - 1) * this.pageSize;
        const pageItems = filtered.slice(startIndex, startIndex + this.pageSize);

        // Build HTML
        container.innerHTML = `
            <!-- Provenance Banner -->
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="background: #10b981; color: #fff; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px;">DATA SOURCE</span>
                    <span style="font-size: 13.5px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(prov.outbound_label || 'Crawled Data — Outbound')}</span>
                </div>
                <span style="font-size: 12.5px; color: var(--text-secondary);">Verified from target website crawl storage</span>
            </div>

            <!-- Calculated Summary KPIs -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 24px;">
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Total Outbound</div>
                    <div style="font-size: 22px; font-weight: 700; color: #3b82f6; margin-top: 4px;">${outSummary.total_outbound_links || this.outboundLinks.length}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Unique Target URLs</div>
                    <div style="font-size: 22px; font-weight: 700; color: #10b981; margin-top: 4px;">${outSummary.unique_external_urls || 0}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Unique Domains</div>
                    <div style="font-size: 22px; font-weight: 700; color: #8b5cf6; margin-top: 4px;">${outSummary.unique_external_domains || 0}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Nofollow Links</div>
                    <div style="font-size: 22px; font-weight: 700; color: #f59e0b; margin-top: 4px;">${outSummary.nofollow_count || 0}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Sponsored / UGC</div>
                    <div style="font-size: 22px; font-weight: 700; color: #ec4899; margin-top: 4px;">${(outSummary.sponsored_count || 0) + (outSummary.ugc_count || 0)}</div>
                </div>
                <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                    <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Broken External</div>
                    <div style="font-size: 22px; font-weight: 700; color: ${outSummary.broken_count > 0 ? '#ef4444' : 'var(--text-secondary)'}; margin-top: 4px;">${outSummary.broken_count || 0}</div>
                </div>
            </div>

            <!-- Search & Filter Controls -->
            <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
                <div style="flex: 2; min-width: 220px;">
                    <input type="text" id="input-outbound-search" value="${this.escapeHtml(this.searchQuery)}" placeholder="Search source page, target URL, domain, or anchor..." style="width: 100%; padding: 8px 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 13.5px;">
                </div>
                <div style="flex: 1; min-width: 140px;">
                    <select id="select-domain-filter" style="width: 100%; padding: 8px 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 13px;">
                        <option value="all" ${this.domainFilter === 'all' ? 'selected' : ''}>All Domains (${domainsList.length})</option>
                        ${domainsList.map(d => `<option value="${this.escapeHtml(d)}" ${this.domainFilter === d ? 'selected' : ''}>${this.escapeHtml(d)}</option>`).join('')}
                    </select>
                </div>
                <div style="flex: 1; min-width: 130px;">
                    <select id="select-type-filter" style="width: 100%; padding: 8px 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 13px;">
                        <option value="all" ${this.typeFilter === 'all' ? 'selected' : ''}>All Link Types</option>
                        <option value="follow" ${this.typeFilter === 'follow' ? 'selected' : ''}>Follow</option>
                        <option value="nofollow" ${this.typeFilter === 'nofollow' ? 'selected' : ''}>Nofollow</option>
                        <option value="sponsored" ${this.typeFilter === 'sponsored' ? 'selected' : ''}>Sponsored</option>
                        <option value="ugc" ${this.typeFilter === 'ugc' ? 'selected' : ''}>UGC</option>
                    </select>
                </div>
                <div style="flex: 1; min-width: 130px;">
                    <select id="select-status-filter" style="width: 100%; padding: 8px 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary); font-size: 13px;">
                        <option value="all" ${this.statusFilter === 'all' ? 'selected' : ''}>All Statuses</option>
                        <option value="ok" ${this.statusFilter === 'ok' ? 'selected' : ''}>200 OK</option>
                        <option value="broken" ${this.statusFilter === 'broken' ? 'selected' : ''}>Broken (4xx/5xx)</option>
                        <option value="unchecked" ${this.statusFilter === 'unchecked' ? 'selected' : ''}>Not checked</option>
                    </select>
                </div>
            </div>

            <!-- Outbound Table -->
            <div class="card" style="padding: 0; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); overflow: hidden;">
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13.5px;">
                        <thead>
                            <tr style="background: rgba(0,0,0,0.25); border-bottom: 1px solid var(--border-color); color: var(--text-secondary); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">
                                <th style="padding: 12px 16px;">Source Page</th>
                                <th style="padding: 12px 16px;">Destination Domain</th>
                                <th style="padding: 12px 16px;">Destination URL</th>
                                <th style="padding: 12px 16px;">Anchor Text</th>
                                <th style="padding: 12px 16px;">Link Type</th>
                                <th style="padding: 12px 16px;">HTTP Status</th>
                                <th style="padding: 12px 16px;">Discovered</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${pageItems.length === 0 ? `
                                <tr>
                                    <td colspan="7" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                                        No outbound links match the active search or filter parameters.
                                    </td>
                                </tr>
                            ` : pageItems.map(item => `
                                <tr style="border-bottom: 1px solid var(--border-color);">
                                    <td style="padding: 12px 16px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        <a href="${this.escapeHtml(item.source_url)}" target="_blank" style="color: var(--text-primary); text-decoration: none;" title="${this.escapeHtml(item.source_url)}">
                                            ${this.escapeHtml(item.source_url)}
                                        </a>
                                    </td>
                                    <td style="padding: 12px 16px; font-weight: 600; color: #60a5fa;">
                                        ${this.escapeHtml(item.destination_domain)}
                                    </td>
                                    <td style="padding: 12px 16px; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        <a href="${this.escapeHtml(item.destination_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-primary, #3b82f6); text-decoration: none;" title="${this.escapeHtml(item.destination_url)}">
                                            ${this.escapeHtml(item.destination_url)} &rarr;
                                        </a>
                                    </td>
                                    <td style="padding: 12px 16px; color: var(--text-secondary); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        ${this.escapeHtml(item.anchor_text)}
                                    </td>
                                    <td style="padding: 12px 16px;">
                                        <span style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: ${item.link_type.includes('Nofollow') ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)'}; color: ${item.link_type.includes('Nofollow') ? '#f59e0b' : '#10b981'}; border: 1px solid ${item.link_type.includes('Nofollow') ? 'rgba(245, 158, 11, 0.3)' : 'rgba(16, 185, 129, 0.3)'};">
                                            ${this.escapeHtml(item.link_type)}
                                        </span>
                                    </td>
                                    <td style="padding: 12px 16px;">
                                        <span style="font-size: 11px; font-weight: 600; color: ${typeof item.status_code === 'number' && item.status_code >= 400 ? '#ef4444' : 'var(--text-secondary)'};">
                                            ${this.escapeHtml(String(item.status_code))}
                                        </span>
                                    </td>
                                    <td style="padding: 12px 16px; font-size: 12px; color: var(--text-tertiary);">
                                        ${this.escapeHtml(String(item.first_discovered))}
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <!-- Table Footer Pagination -->
                <div style="padding: 12px 16px; background: rgba(0,0,0,0.15); border-top: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                    <div style="font-size: 13px; color: var(--text-secondary);">
                        Showing <strong>${totalCount > 0 ? startIndex + 1 : 0}</strong> to <strong>${Math.min(startIndex + this.pageSize, totalCount)}</strong> of <strong>${totalCount}</strong> outbound links
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <button id="btn-page-prev" class="btn btn-secondary btn-sm" ${this.currentPage <= 1 ? 'disabled' : ''}>Previous</button>
                        <span style="font-size: 13px; color: var(--text-secondary); padding: 0 4px;">Page ${this.currentPage} of ${totalPages}</span>
                        <button id="btn-page-next" class="btn btn-secondary btn-sm" ${this.currentPage >= totalPages ? 'disabled' : ''}>Next</button>
                    </div>
                </div>
            </div>
        `;

        this.bindOutboundEvents(container);
    }

    bindOutboundEvents(container) {
        const inputSearch = container.querySelector('#input-outbound-search');
        if (inputSearch) {
            inputSearch.addEventListener('input', (e) => {
                this.searchQuery = e.target.value;
                this.currentPage = 1;
                this.renderOutboundTab(container);
                // Maintain focus on search input
                const newInput = container.querySelector('#input-outbound-search');
                if (newInput) {
                    newInput.focus();
                    newInput.setSelectionRange(this.searchQuery.length, this.searchQuery.length);
                }
            });
        }

        const selDomain = container.querySelector('#select-domain-filter');
        if (selDomain) {
            selDomain.addEventListener('change', (e) => {
                this.domainFilter = e.target.value;
                this.currentPage = 1;
                this.renderOutboundTab(container);
            });
        }

        const selType = container.querySelector('#select-type-filter');
        if (selType) {
            selType.addEventListener('change', (e) => {
                this.typeFilter = e.target.value;
                this.currentPage = 1;
                this.renderOutboundTab(container);
            });
        }

        const selStatus = container.querySelector('#select-status-filter');
        if (selStatus) {
            selStatus.addEventListener('change', (e) => {
                this.statusFilter = e.target.value;
                this.currentPage = 1;
                this.renderOutboundTab(container);
            });
        }

        const btnPrev = container.querySelector('#btn-page-prev');
        if (btnPrev) {
            btnPrev.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.renderOutboundTab(container);
                }
            });
        }

        const btnNext = container.querySelector('#btn-page-next');
        if (btnNext) {
            btnNext.addEventListener('click', () => {
                this.currentPage++;
                this.renderOutboundTab(container);
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
