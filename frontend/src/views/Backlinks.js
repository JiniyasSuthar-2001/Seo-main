import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
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
        this.activeLinkModal = null;
        
        // Pagination state
        this.outboundPage = 1;
        this.inboundPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Website Links</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">View external links discovered on your website and inbound links pointing to your site.</p>
                </div>
                <div id="backlinks-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 12px; flex-wrap: wrap;">
                <button class="btn ${this.activeTab === 'outbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-outbound-btn" style="font-size: 13px;">Links Found On Your Website</button>
                <button class="btn ${this.activeTab === 'inbound' ? 'btn-primary' : 'btn-secondary'}" id="tab-inbound-btn" style="font-size: 13px;">Links From Other Websites</button>
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

    renderInboundTab(container) {
        const backlinks = this.inboundBacklinks || [];
        if (backlinks.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 24px auto; background: var(--bg-card); border-radius: 14px; border: 1px dashed var(--border);">
                    <div style="font-size: 36px; margin-bottom: 12px;">🔗</div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">No links from other websites found yet</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        Your website scan discovers links on your own site. Inbound backlinks from external websites require a connected provider API or an imported dataset.
                    </p>
                    <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                        <a href="/import" data-link class="btn btn-primary btn-sm">Import Link Data</a>
                        <a href="/integrations" data-link class="btn btn-secondary btn-sm">Connect a Data Source</a>
                    </div>
                </div>
            `;
            return;
        }

        const paginated = Pagination.paginateArray(backlinks, this.inboundPage, this.pageSize);
        this.inboundPage = paginated.currentPage;

        let rows = paginated.items.map(b => `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 18px; font-family: monospace; font-size: 12px; color: var(--primary); text-break: break-all;">${this.escapeHtml(b.source_url || b.source || 'Not available')}</td>
                <td style="padding: 12px; font-family: monospace; font-size: 12px; text-break: break-all;">${this.escapeHtml(b.target_url || b.target || b.destination_url || 'Not available')}</td>
                <td style="padding: 12px; font-weight: 600;">${this.escapeHtml(b.anchor_text || 'No anchor text')}</td>
                <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">${this.escapeHtml(b.provenance || b.data_source || 'Imported Data')}</td>
            </tr>
        `).join('');

        container.innerHTML = `
            <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; background: var(--bg-card);">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                    <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Links From Other Websites (${backlinks.length})</h3>
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 18px;">Referring Website URL</th>
                                <th style="padding: 12px;">Your Page URL</th>
                                <th style="padding: 12px;">Link Text</th>
                                <th style="padding: 12px 18px;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
                <div id="inbound-pagination-slot"></div>
            </div>
        `;

        const pageSlot = container.querySelector('#inbound-pagination-slot');
        if (pageSlot) {
            const pag = new Pagination({
                totalItems: backlinks.length,
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

    renderOutboundTab(container) {
        const links = this.outboundLinks || [];

        if (links.length === 0) {
            container.innerHTML = `
                <div class="card" style="padding: 40px 28px; text-align: center; max-width: 580px; margin: 24px auto; background: var(--bg-card); border-radius: 14px; border: 1px dashed var(--border);">
                    <div style="font-size: 36px; margin-bottom: 12px;">🌐</div>
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 8px; color: var(--text-primary);">Link data isn't available yet</h3>
                    <p style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 20px; line-height: 1.6;">
                        Run a website scan to extract external links, social links, and anchor text found across your pages.
                    </p>
                    <button class="btn btn-primary btn-sm" onclick="window.startCrawl ? window.startCrawl() : window.location.href='/'">Scan My Website</button>
                </div>
            `;
            return;
        }

        const paginated = Pagination.paginateArray(links, this.outboundPage, this.pageSize);
        this.outboundPage = paginated.currentPage;

        let rows = paginated.items.map((l, idx) => {
            const globalIdx = (paginated.currentPage - 1) * paginated.pageSize + idx;
            const srcUrl = l.source_url || l.source_page || l.source || 'Not available';
            const destUrl = l.destination_url || l.target_url || l.target || 'Not available';
            const anchorTxt = l.anchor_text || 'No anchor text';
            const linkType = l.link_type || 'External Link';
            const dataSource = l.data_source || 'Website Scan';

            let badgeBg = 'rgba(59, 130, 246, 0.12)';
            let badgeColor = '#3b82f6';
            if (linkType.includes('Social')) { badgeBg = 'rgba(168, 85, 247, 0.15)'; badgeColor = '#a855f7'; }
            else if (linkType.includes('Email') || linkType.includes('Telephone')) { badgeBg = 'rgba(245, 158, 11, 0.15)'; badgeColor = '#f59e0b'; }

            return `
                <tr class="link-row-item" data-idx="${globalIdx}" style="border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.15s ease;">
                    <td style="padding: 12px 18px; font-family: monospace; font-size: 12px; color: var(--primary); word-break: break-all; max-width: 260px;">
                        ${this.escapeHtml(srcUrl)}
                    </td>
                    <td style="padding: 12px; font-family: monospace; font-size: 12px; color: var(--text-primary); word-break: break-all; max-width: 280px;">
                        <a href="${this.escapeHtml(destUrl)}" target="_blank" onclick="event.stopPropagation();" style="color: inherit; text-decoration: none; border-bottom: 1px dotted var(--text-tertiary);">
                            ${this.escapeHtml(destUrl)} ↗
                        </a>
                    </td>
                    <td style="padding: 12px; font-weight: 600; color: var(--text-primary);">
                        ${this.escapeHtml(anchorTxt)}
                    </td>
                    <td style="padding: 12px;">
                        <span style="font-size: 11px; font-weight: 700; background: ${badgeBg}; color: ${badgeColor}; padding: 3px 8px; border-radius: 12px;">
                            ${this.escapeHtml(linkType)}
                        </span>
                    </td>
                    <td style="padding: 12px 18px; font-size: 11.5px; color: var(--text-secondary);">
                        ${this.escapeHtml(dataSource)}
                    </td>
                </tr>
            `;
        }).join('');

        container.innerHTML = `
            <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; background: var(--bg-card);">
                <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Links Found On Your Website (${links.length})</h3>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Outbound and social links discovered on your website during the latest scan. Click any row for details.</div>
                    </div>
                </div>
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 18px;">Your Page URL</th>
                                <th style="padding: 12px;">External Website Link</th>
                                <th style="padding: 12px;">Link Text ${renderTooltip('Visible anchor text used to link to the destination.')}</th>
                                <th style="padding: 12px;">Link Type</th>
                                <th style="padding: 12px 18px;">Data Source</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
                <div id="outbound-pagination-slot"></div>
            </div>
            <div id="link-modal-container"></div>
        `;

        if (links.length > 0) {
            const pageSlot = container.querySelector('#outbound-pagination-slot');
            if (pageSlot) {
                const pag = new Pagination({
                    totalItems: links.length,
                    currentPage: this.outboundPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.outboundPage = newPage;
                        this.renderOutboundTab(container);
                    }
                });
                pageSlot.appendChild(pag.render());
            }

            // Bind Row Click Events for Link Details Modal
            container.querySelectorAll('.link-row-item').forEach(row => {
                row.addEventListener('click', (e) => {
                    const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                    const item = links[idx];
                    if (item) {
                        this.openLinkDetailsModal(item);
                    }
                });
            });
        }
    }

    openLinkDetailsModal(item) {
        const modalContainer = this.element.querySelector('#link-modal-container');
        if (!modalContainer) return;

        const srcUrl = item.source_url || item.source_page || item.source || 'Not available';
        const destUrl = item.destination_url || item.target_url || item.target || 'Not available';
        const anchorTxt = item.anchor_text || 'No anchor text';
        const linkType = item.link_type || 'External Link';
        const statusCode = item.status_code || 'Not checked';
        const relAttr = item.rel || 'None';
        const dataSource = item.data_source || 'Website Scan';
        const scanDate = item.first_discovered || item.last_discovered ? new Date(item.first_discovered || item.last_discovered).toLocaleDateString() : 'Latest Scan';

        modalContainer.innerHTML = `
            <div class="modal-backdrop" style="position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px;">
                <div class="modal-card" style="background: var(--bg-card, #1e293b); border: 1px solid var(--border, #334155); border-radius: 14px; width: 100%; max-width: 600px; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
                        <h2 style="font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary);">Link Details</h2>
                        <button id="btn-close-link-modal" style="background: none; border: none; color: var(--text-secondary); font-size: 22px; cursor: pointer;">&times;</button>
                    </div>

                    <div style="display: flex; flex-direction: column; gap: 14px; font-size: 13.5px;">
                        <div>
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Your Source Page URL</div>
                            <div style="font-family: monospace; font-size: 12.5px; color: var(--primary); margin-top: 4px; word-break: break-all; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px;">
                                ${this.escapeHtml(srcUrl)}
                            </div>
                        </div>

                        <div>
                            <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Destination URL</div>
                            <div style="font-family: monospace; font-size: 12.5px; color: var(--text-primary); margin-top: 4px; word-break: break-all; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px;">
                                <a href="${this.escapeHtml(destUrl)}" target="_blank" style="color: inherit;">${this.escapeHtml(destUrl)} &rarr;</a>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Anchor / Link Text</div>
                                <div style="font-weight: 600; color: var(--text-primary); margin-top: 4px;">${this.escapeHtml(anchorTxt)}</div>
                            </div>
                            <div>
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Link Type</div>
                                <div style="font-weight: 600; color: var(--accent-primary, #3b82f6); margin-top: 4px;">${this.escapeHtml(linkType)}</div>
                            </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <div>
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">HTTP Status</div>
                                <div style="font-weight: 600; color: var(--text-primary); margin-top: 4px;">${this.escapeHtml(String(statusCode))}</div>
                            </div>
                            <div>
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary); text-transform: uppercase;">Data Source</div>
                                <div style="font-weight: 600; color: var(--text-secondary); margin-top: 4px;">${this.escapeHtml(dataSource)} (${this.escapeHtml(scanDate)})</div>
                            </div>
                        </div>
                    </div>

                    <div style="text-align: right; margin-top: 24px; border-top: 1px solid var(--border); padding-top: 14px;">
                        <button id="btn-dismiss-link-modal" class="btn btn-secondary btn-sm">Close</button>
                    </div>
                </div>
            </div>
        `;

        modalContainer.querySelector('#btn-close-link-modal')?.addEventListener('click', () => { modalContainer.innerHTML = ''; });
        modalContainer.querySelector('#btn-dismiss-link-modal')?.addEventListener('click', () => { modalContainer.innerHTML = ''; });
    }

    renderGapTab(container, gapData) {
        container.innerHTML = `
            <div class="card" style="padding: 24px; border-radius: 14px; background: var(--bg-card);">
                <h3 style="font-size: 16px; font-weight: 700; margin: 0 0 8px 0; color: var(--text-primary);">Competitor Link Comparison</h3>
                <p style="font-size: 13px; color: var(--text-secondary); margin: 0 0 16px 0;">Compare websites linking to your competitors against websites linking to your business.</p>
                <div style="padding: 24px; text-align: center; background: var(--bg-subtle); border-radius: 10px; border: 1px dashed var(--border); color: var(--text-secondary); font-size: 13.5px;">
                    Add competitor websites in <strong>Competitors</strong> to compare link profile opportunities.
                </div>
            </div>
        `;
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
