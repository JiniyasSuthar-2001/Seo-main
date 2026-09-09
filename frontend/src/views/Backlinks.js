import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { GrowthDetailModal } from '../components/GrowthDetailModal.js';
import { renderTooltip } from '../components/Tooltip.js';
import { Pagination } from '../components/Pagination.js';

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
        this.inboundBacklinks = [];
        
        // Outbound search & filters
        this.outboundPage = 1;
        this.outboundSearch = '';
        this.outboundRelFilter = 'all'; // all, follow, nofollow, sponsored, ugc
        this.outboundStatusFilter = 'all'; // all, 200, 301, 404, 500
        this.outboundTypeFilter = 'all'; // all, html, pdf, image, social

        // Inbound search & filters
        this.inboundPage = 1;
        this.inboundSearch = '';

        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Website Links & Backlinks</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Inspect external links discovered on your website (outbound) and inbound links pointing to your site (backlinks).</p>
                </div>
                <div id="backlinks-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px; flex-wrap: wrap;">
                <button class="btn ${this.activeTab === 'outbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-outbound-btn" style="font-size: 13px;">Links Found On Your Website (Outbound External)</button>
                <button class="btn ${this.activeTab === 'inbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-inbound-btn" style="font-size: 13px;">Links From Other Websites (Inbound Backlinks)</button>
                <button class="btn ${this.activeTab === 'gap' ? 'btn-primary' : 'btn-secondary'}" id="tab-gap-btn" style="font-size: 13px;">Competitor Link Comparison</button>
            </div>

            <div id="backlinks-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading website link information...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('backlinks-content');
        const actionsContainer = document.getElementById('backlinks-actions');
        if (!container) return;

        document.getElementById('tab-outbound-btn')?.addEventListener('click', () => { this.activeTab = 'outbound'; this.outboundPage = 1; this.mounted(); });
        document.getElementById('tab-inbound-btn')?.addEventListener('click', () => { this.activeTab = 'inbound'; this.inboundPage = 1; this.mounted(); });
        document.getElementById('tab-gap-btn')?.addEventListener('click', () => { this.activeTab = 'gap'; this.mounted(); });

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
                return;
            }

            const safeProjName = (selectedProj.name || selectedProj.domain || 'website').replace(/[^a-zA-Z0-9_-]/g, '_');
            const todayStr = new Date().toISOString().split('T')[0];

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <a href="/import" data-link class="btn btn-secondary btn-sm">Import Link Data</a>
                    <button id="btn-export-backlinks-csv" class="btn btn-secondary btn-sm">Download CSV</button>
                `;

                const csvBtn = document.getElementById('btn-export-backlinks-csv');
                if (csvBtn) {
                    csvBtn.onclick = (e) => apiClient.downloadFile(
                        `/api/projects/${projectId}/backlinks/export.csv`, 
                        `${safeProjName}_website_links_${todayStr}.csv`, 
                        e.currentTarget
                    );
                }
            }

            if (this.activeTab === 'gap') {
                const gapData = await apiClient.get(`/api/projects/${projectId}/backlinks/gap-analysis`).catch(() => null);
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
                return;
            }

            // Default 'outbound'
            this.renderOutboundTab(container);

        } catch (e) {
            renderFeatureErrorState(container, "Failed to load link data", e.message || "Unable to load website links.", () => this.mounted());
        }
    }

    // -------------------------------------------------------------------------
    // TAB 1: OUTBOUND EXTERNAL LINKS (YOUR SITE -> EXTERNAL SITE)
    // -------------------------------------------------------------------------
    renderOutboundTab(container) {
        const links = this.outboundLinks || [];

        if (links.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 24px auto; background: var(--bg-card); border-radius: 14px; border: 1px dashed var(--border);">
                    <div style="font-size: 36px; margin-bottom: 12px;">🌐</div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No External Links Discovered</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        Run a website scan to extract and verify external links, social links, and anchor text pointing from your website to external destinations.
                    </p>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                </div>
            `;
            return;
        }

        // Summary metrics
        const totalOutbound = links.length;
        const domains = new Set(links.map(l => {
            try {
                return new URL(l.destination_url || l.target_url || l.target || '').hostname;
            } catch (e) {
                return '';
            }
        }).filter(Boolean));
        const followCount = links.filter(l => !l.is_nofollow && (l.rel || '').toLowerCase() !== 'nofollow').length;
        const nofollowCount = links.filter(l => l.is_nofollow || (l.rel || '').toLowerCase().includes('nofollow')).length;

        // Pre-pagination filtering
        let filtered = links;
        if (this.outboundRelFilter === 'follow') {
            filtered = filtered.filter(l => !l.is_nofollow && !(l.rel || '').toLowerCase().includes('nofollow'));
        } else if (this.outboundRelFilter === 'nofollow') {
            filtered = filtered.filter(l => l.is_nofollow || (l.rel || '').toLowerCase().includes('nofollow'));
        } else if (this.outboundRelFilter === 'sponsored') {
            filtered = filtered.filter(l => (l.rel || '').toLowerCase().includes('sponsored'));
        } else if (this.outboundRelFilter === 'ugc') {
            filtered = filtered.filter(l => (l.rel || '').toLowerCase().includes('ugc'));
        }

        if (this.outboundStatusFilter === '200') {
            filtered = filtered.filter(l => (l.status_code || 200) === 200);
        } else if (this.outboundStatusFilter === '301') {
            filtered = filtered.filter(l => (l.status_code || 0) >= 300 && (l.status_code || 0) < 400);
        } else if (this.outboundStatusFilter === '404') {
            filtered = filtered.filter(l => (l.status_code || 0) === 404);
        } else if (this.outboundStatusFilter === '500') {
            filtered = filtered.filter(l => (l.status_code || 0) >= 500);
        }

        if (this.outboundSearch.trim()) {
            const q = this.outboundSearch.toLowerCase().trim();
            filtered = filtered.filter(l => {
                const src = (l.source_url || l.source_page || l.source || '').toLowerCase();
                const dest = (l.destination_url || l.target_url || l.target || '').toLowerCase();
                const anc = (l.anchor_text || '').toLowerCase();
                const typ = (l.link_type || '').toLowerCase();
                return src.includes(q) || dest.includes(q) || anc.includes(q) || typ.includes(q);
            });
        }

        const paginated = Pagination.paginateArray(filtered, this.outboundPage, this.pageSize);
        this.outboundPage = paginated.currentPage;

        let rows = paginated.items.map((l, idx) => {
            const srcUrl = l.source_url || l.source_page || l.source || 'Not available';
            const destUrl = l.destination_url || l.target_url || l.target || 'Not available';
            const anchorTxt = l.anchor_text || '(No anchor text)';
            const section = l.source_section || 'Main Content';
            const heading = l.nearest_heading ? this.escapeHtml(l.nearest_heading) : 'Not Available';
            const rel = l.rel || (l.is_nofollow ? 'nofollow' : 'follow');
            const statusCode = l.status_code !== undefined ? l.status_code : 200;

            let statusBadge = '<span class="badge badge-success" style="font-size: 11px;">200 OK</span>';
            if (statusCode >= 400 || statusCode === 0) {
                statusBadge = `<span class="badge badge-critical" style="font-size: 11px;">${statusCode === 0 ? 'Dead' : `HTTP ${statusCode}`}</span>`;
            } else if (statusCode >= 300) {
                statusBadge = `<span class="badge badge-warning" style="font-size: 11px;">HTTP ${statusCode}</span>`;
            }

            let domainStr = '';
            try { domainStr = new URL(destUrl).hostname; } catch (e) { domainStr = 'External'; }

            return `
                <tr style="border-bottom: 1px solid var(--border);" class="outbound-row" data-idx="${idx}">
                    <td style="padding: 12px 14px; max-width: 260px;">
                        <div style="font-family: monospace; font-size: 12px; color: var(--text-primary); word-break: break-all;">
                            <a href="${this.escapeHtml(destUrl)}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">
                                ${this.escapeHtml(destUrl)} ↗
                            </a>
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">${this.escapeHtml(domainStr)}</div>
                    </td>
                    <td style="padding: 12px 14px; max-width: 220px;">
                        <div style="font-family: monospace; font-size: 12px; color: var(--primary); word-break: break-all;">
                            ${this.escapeHtml(srcUrl)}
                        </div>
                    </td>
                    <td style="padding: 12px 14px; font-weight: 500; font-size: 12.5px; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this.escapeHtml(anchorTxt)}">
                        ${this.escapeHtml(anchorTxt)}
                    </td>
                    <td style="padding: 12px 14px; font-family: monospace; font-size: 11px; color: var(--text-secondary);">${this.escapeHtml(rel)}</td>
                    <td style="padding: 12px 14px;">${statusBadge}</td>
                    <td style="padding: 12px 14px; font-size: 12px; color: var(--text-secondary);">${this.escapeHtml(section)}</td>
                    <td style="padding: 12px 14px; text-align: right;">
                        <button class="btn btn-secondary btn-sm btn-inspect-outbound" data-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                            Inspect Link
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <!-- SUMMARY KPI CARDS -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 20px;">
                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Outbound Links</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--primary); margin-top: 4px;">${totalOutbound}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">External destinations found</div>
                </div>
                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Destination Domains</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${domains.size}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Unique external websites</div>
                </div>
                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Follow Links</div>
                    <div style="font-size: 24px; font-weight: 800; color: #10b981; margin-top: 4px;">${followCount}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Passing PageRank authority</div>
                </div>
                <div class="kpi-card" style="padding: 16px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Nofollow / UGC / Sponsored</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--text-secondary); margin-top: 4px;">${nofollowCount}</div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); margin-top: 2px;">Annotated external links</div>
                </div>
            </div>

            <!-- CONTROLS: FILTER & SEARCH -->
            <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; background: var(--bg-card);">
                <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">External Links Directory (${filtered.length})</h3>
                        <div style="display: flex; gap: 6px;">
                            <select id="select-outbound-rel" style="padding: 4px 8px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                                <option value="all" ${this.outboundRelFilter === 'all' ? 'selected' : ''}>All Rel Types</option>
                                <option value="follow" ${this.outboundRelFilter === 'follow' ? 'selected' : ''}>Follow</option>
                                <option value="nofollow" ${this.outboundRelFilter === 'nofollow' ? 'selected' : ''}>Nofollow</option>
                                <option value="sponsored" ${this.outboundRelFilter === 'sponsored' ? 'selected' : ''}>Sponsored</option>
                                <option value="ugc" ${this.outboundRelFilter === 'ugc' ? 'selected' : ''}>UGC</option>
                            </select>
                            <select id="select-outbound-status" style="padding: 4px 8px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary);">
                                <option value="all" ${this.outboundStatusFilter === 'all' ? 'selected' : ''}>All HTTP Statuses</option>
                                <option value="200" ${this.outboundStatusFilter === '200' ? 'selected' : ''}>200 OK</option>
                                <option value="301" ${this.outboundStatusFilter === '301' ? 'selected' : ''}>3xx Redirects</option>
                                <option value="404" ${this.outboundStatusFilter === '404' ? 'selected' : ''}>404 Not Found</option>
                                <option value="500" ${this.outboundStatusFilter === '500' ? 'selected' : ''}>5xx Server Error</option>
                            </select>
                        </div>
                    </div>
                    <input type="text" id="outbound-search-input" value="${this.escapeHtml(this.outboundSearch)}" placeholder="Search destination, source, anchor..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                </div>

                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 14px;">Destination URL</th>
                                <th style="padding: 12px 14px;">Found On (Source Page)</th>
                                <th style="padding: 12px 14px;">Anchor Text</th>
                                <th style="padding: 12px 14px;">Rel</th>
                                <th style="padding: 12px 14px;">Status</th>
                                <th style="padding: 12px 14px;">Location</th>
                                <th style="padding: 12px 14px; text-align: right;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows.length > 0 ? rows : `<tr><td colspan="7" style="padding: 36px; text-align: center; color: var(--text-secondary);">No external links found matching your filters.</td></tr>`}
                        </tbody>
                    </table>
                </div>
                <div id="outbound-pagination-slot"></div>
            </div>
        `;

        // Bind filter & search
        const relSelect = container.querySelector('#select-outbound-rel');
        if (relSelect) relSelect.onchange = (e) => { this.outboundRelFilter = e.target.value; this.outboundPage = 1; this.renderOutboundTab(container); };

        const statusSelect = container.querySelector('#select-outbound-status');
        if (statusSelect) statusSelect.onchange = (e) => { this.outboundStatusFilter = e.target.value; this.outboundPage = 1; this.renderOutboundTab(container); };

        const searchInput = container.querySelector('#outbound-search-input');
        if (searchInput) {
            searchInput.oninput = (e) => {
                this.outboundSearch = e.target.value;
                this.outboundPage = 1;
                this.renderOutboundTab(container);
            };
        }

        // Bind inspect buttons
        container.querySelectorAll('.btn-inspect-outbound').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute('data-idx'), 10);
                const record = paginated.items[idx];
                if (record) GrowthDetailModal.showLinkDetail(record);
            };
        });

        if (filtered.length > 0) {
            const pageSlot = container.querySelector('#outbound-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: filtered.length,
                    currentPage: this.outboundPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.outboundPage = newPage;
                        this.renderOutboundTab(container);
                    }
                });
                pageSlot.appendChild(pag.render());
            }
        }
    }

    // -------------------------------------------------------------------------
    // TAB 2: INBOUND BACKLINKS (OTHER SITES -> YOUR SITE)
    // -------------------------------------------------------------------------
    renderInboundTab(container) {
        const backlinks = this.inboundBacklinks || [];
        const provenance = this.provenance || {};

        if (backlinks.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 24px auto; background: var(--bg-card); border-radius: 14px; border: 1px dashed var(--border);">
                    <div style="font-size: 36px; margin-bottom: 12px;">🔗</div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No backlink data available</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        Your website crawler maps links from your website to other websites, but detecting external websites that link back to your domain requires connecting Google Search Console or importing a backlink CSV export.
                    </p>
                    <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                        <a href="/import" data-link class="btn btn-primary btn-sm">Import Backlink CSV</a>
                        <a href="/integrations" data-link class="btn btn-secondary btn-sm">Connect Google Search Console</a>
                    </div>
                </div>
            `;
            return;
        }

        let filtered = backlinks;
        if (this.inboundSearch.trim()) {
            const q = this.inboundSearch.toLowerCase().trim();
            filtered = filtered.filter(b => {
                const src = (b.source_url || b.source || b.referring_url || '').toLowerCase();
                const tgt = (b.target_url || b.target || b.destination_url || '').toLowerCase();
                const anc = (b.anchor_text || '').toLowerCase();
                const dom = (b.referring_domain || '').toLowerCase();
                return src.includes(q) || tgt.includes(q) || anc.includes(q) || dom.includes(q);
            });
        }

        const paginated = Pagination.paginateArray(filtered, this.inboundPage, this.pageSize);
        this.inboundPage = paginated.currentPage;

        let rows = paginated.items.map((b, idx) => {
            const srcUrl = b.source_url || b.source || b.referring_url || 'Not available';
            const tgtUrl = b.target_url || b.target || b.destination_url || 'Not available';
            const anchor = b.anchor_text || '(No anchor text)';
            const sourceLabel = b.provenance || b.data_source || provenance.source_label || 'Google Search Console';

            return `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 12px 16px; font-family: monospace; font-size: 12px; color: var(--primary); max-width: 280px; word-break: break-all;">
                        <a href="${this.escapeHtml(srcUrl)}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: none;">
                            ${this.escapeHtml(srcUrl)} ↗
                        </a>
                    </td>
                    <td style="padding: 12px 16px; font-family: monospace; font-size: 12px; max-width: 260px; word-break: break-all;">
                        ${this.escapeHtml(tgtUrl)}
                    </td>
                    <td style="padding: 12px 16px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(anchor)}</td>
                    <td style="padding: 12px 16px;">
                        <span class="badge badge-info" style="font-size: 11px;">${this.escapeHtml(sourceLabel)}</span>
                    </td>
                    <td style="padding: 12px 16px; text-align: right;">
                        <button class="btn btn-secondary btn-sm btn-inspect-inbound" data-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                            Inspect Link
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; background: var(--bg-card);">
                <div style="padding: 14px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: var(--bg-subtle);">
                    <div>
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Inbound Backlinks (${filtered.length})</h3>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Verified inbound links pointing to your website. Source: ${this.escapeHtml(provenance.source_label || 'Connected Data Provider')}</div>
                    </div>
                    <input type="text" id="inbound-search-input" value="${this.escapeHtml(this.inboundSearch)}" placeholder="Search referring URL, target..." style="padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-primary); width: 220px;" />
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 16px;">Referring Website URL</th>
                                <th style="padding: 12px 16px;">Your Destination Page URL</th>
                                <th style="padding: 12px 16px;">Anchor Text</th>
                                <th style="padding: 12px 16px;">Data Source</th>
                                <th style="padding: 12px 16px; text-align: right;">Action</th>
                            </tr>
                        </thead>
                        <tbody>${rows.length > 0 ? rows : `<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--text-secondary);">No backlinks matching search.</td></tr>`}</tbody>
                    </table>
                </div>
                <div id="inbound-pagination-slot"></div>
            </div>
        `;

        const searchInput = container.querySelector('#inbound-search-input');
        if (searchInput) {
            searchInput.oninput = (e) => {
                this.inboundSearch = e.target.value;
                this.inboundPage = 1;
                this.renderInboundTab(container);
            };
        }

        container.querySelectorAll('.btn-inspect-inbound').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute('data-idx'), 10);
                const record = paginated.items[idx];
                if (record) GrowthDetailModal.showLinkDetail(record);
            };
        });

        if (filtered.length > 0) {
            const pageSlot = container.querySelector('#inbound-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: filtered.length,
                    currentPage: this.inboundPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.inboundPage = newPage;
                        this.renderInboundTab(container);
                    }
                });
                pageSlot.appendChild(pag.render());
            }
        }
    }

    // -------------------------------------------------------------------------
    // TAB 3: COMPETITOR LINK GAP COMPARISON
    // -------------------------------------------------------------------------
    renderGapTab(container, gapData) {
        const competitors = gapData?.confirmed_competitors_count || 0;
        const gaps = gapData?.backlink_gap || [];

        if (competitors === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 24px auto; background: var(--bg-card); border-radius: 14px; border: 1px dashed var(--border);">
                    <div style="font-size: 36px; margin-bottom: 12px;">⚔️</div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No Confirmed Competitors</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        Add and confirm competitor domains to unlock backlink gap analysis and discover high-authority domains linking to your competitors.
                    </p>
                    <a href="/competitors" data-link class="btn btn-primary btn-sm">Manage Competitors</a>
                </div>
            `;
            return;
        }

        if (gaps.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 24px auto; background: var(--bg-card); border-radius: 14px; border: 1px dashed var(--border);">
                    <div style="font-size: 36px; margin-bottom: 12px;">📊</div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">Competitor Link Datasets Not Configured</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        You have ${competitors} confirmed competitor${competitors === 1 ? '' : 's'}. Import competitor backlink CSV exports to calculate linking domain intersections.
                    </p>
                    <a href="/import" data-link class="btn btn-primary btn-sm">Import Competitor Backlink Data</a>
                </div>
            `;
            return;
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
