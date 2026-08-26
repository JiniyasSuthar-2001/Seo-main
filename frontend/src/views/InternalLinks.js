import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { apiClient } from '../services/apiClient.js';
import { AIAnchorModal } from '../components/AIAnchorModal.js';
import { renderTooltip } from '../components/Tooltip.js';

export class InternalLinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'internal-links-view';
        this.activeTab = 'graph'; // graph, orphans, anchors, opportunities
    }

    render() {
        this.element.innerHTML = `
            <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Internal Links</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">View links connecting your website pages together and find opportunities to improve page navigation.</p>
                </div>
                <div id="links-actions" style="display: flex; gap: 10px;"></div>
            </div>

            <!-- SUB TABS -->
            <div style="display: flex; gap: 12px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px; flex-wrap: wrap;">
                <button class="btn ${this.activeTab === 'graph' ? 'btn-primary' : 'btn-secondary'}" id="tab-graph-btn" style="font-size: 13px;">Links Between Your Pages</button>
                <button class="btn ${this.activeTab === 'orphans' ? 'btn-primary' : 'btn-secondary'}" id="tab-orphans-btn" style="font-size: 13px;">Pages With No Links</button>
                <button class="btn ${this.activeTab === 'anchors' ? 'btn-primary' : 'btn-secondary'}" id="tab-anchors-btn" style="font-size: 13px;">Link Text</button>
                <button class="btn ${this.activeTab === 'opportunities' ? 'btn-primary' : 'btn-secondary'}" id="tab-opps-btn" style="font-size: 13px;">Suggested Page Links</button>
            </div>

            <div id="links-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading internal link information...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('links-content');
        const actionsContainer = document.getElementById('links-actions');
        if (!container) return;

        document.getElementById('tab-graph-btn')?.addEventListener('click', () => { this.activeTab = 'graph'; this.mounted(); });
        document.getElementById('tab-orphans-btn')?.addEventListener('click', () => { this.activeTab = 'orphans'; this.mounted(); });
        document.getElementById('tab-anchors-btn')?.addEventListener('click', () => { this.activeTab = 'anchors'; this.mounted(); });
        document.getElementById('tab-opps-btn')?.addEventListener('click', () => { this.activeTab = 'opportunities'; this.mounted(); });

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project workspace.</div>`;
                return;
            }

            const safeProjName = (selectedProj.name || 'website').replace(/[^a-zA-Z0-9_-]/g, '_');
            const todayStr = new Date().toISOString().split('T')[0];

            if (actionsContainer) {
                actionsContainer.innerHTML = `
                    <button id="btn-export-il-pdf" class="btn btn-secondary btn-sm">Download Report (PDF)</button>
                    <button id="btn-export-il-csv" class="btn btn-secondary btn-sm">Download CSV</button>
                `;

                const pdfBtn = document.getElementById('btn-export-il-pdf');
                const csvBtn = document.getElementById('btn-export-il-csv');
                if (pdfBtn) pdfBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/internal-links/report.pdf`, `${safeProjName}-Internal-Links-${todayStr}.pdf`, e.currentTarget);
                if (csvBtn) csvBtn.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/internal-links/export.csv`, `${safeProjName}-Internal-Links-${todayStr}.csv`, e.currentTarget);
            }

            if (this.activeTab === 'opportunities') {
                const oppsData = await apiClient.get(`/api/projects/${projectId}/internal-links/opportunities`);
                const oppList = oppsData.opportunities || [];

                let rows = oppList.map(o => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-family: monospace; font-size: 12px; color: var(--primary); padding: 12px 18px; max-width: 240px; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(o.source_page)}</td>
                        <td style="font-family: monospace; font-size: 12px; padding: 12px; max-width: 240px; overflow: hidden; text-overflow: ellipsis;">${this.escapeHtml(o.target_page)}</td>
                        <td style="padding: 12px;">
                            <button class="btn btn-secondary btn-sm btn-view-anchor-suggestions" data-source="${this.escapeHtml(o.source_page)}" data-target="${this.escapeHtml(o.target_page)}" style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600;">
                                ✨ View Suggested Link Text
                            </button>
                        </td>
                        <td style="font-size: 12px; color: var(--text-secondary); padding: 12px;">${this.escapeHtml(o.reason)}</td>
                        <td style="padding: 12px 18px;"><span class="badge ${o.priority === 'HIGH' ? 'badge-critical' : 'badge-warning'}">${this.escapeHtml(o.priority)}</span></td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Suggested Page Links (${oppList.length})</h3>
                        </div>
                        <div style="overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 12px 20px;">Source Page</th>
                                        <th style="padding: 12px;">Target Page</th>
                                        <th style="padding: 12px;">Suggested Link Text ${renderTooltip('Clickable text to use for the link.')}</th>
                                        <th style="padding: 12px;">Reason</th>
                                        <th style="padding: 12px 20px;">Priority</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${rows.length > 0 ? rows : `<tr><td colspan="5" style="padding: 32px; text-align: center; color: var(--text-secondary);">No link suggestions detected. All pages are well connected.</td></tr>`}
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;

                container.querySelectorAll('.btn-view-anchor-suggestions').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        const src = btn.getAttribute('data-source');
                        const tgt = btn.getAttribute('data-target');
                        if (src && tgt) {
                            AIAnchorModal.show(src, tgt);
                        }
                    });
                });

                return;
            }

            const data = await apiClient.get(`/api/projects/${projectId}/internal-links?limit=200&offset=0`);
            const links = data.internal_links || [];
            const orphans = data.orphan_pages || [];
            const anchors = data.anchor_texts || [];

            if (this.activeTab === 'orphans') {
                let orphanRows = orphans.map(url => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-family: monospace; font-size: 13px; color: var(--primary); padding: 12px 20px;">${this.escapeHtml(url)}</td>
                        <td style="padding: 12px;"><span class="badge badge-critical">0 Links Pointing to This Page</span></td>
                        <td style="padding: 12px; font-size: 12.5px; color: var(--text-secondary);">Add a link from your homepage or main menu to help visitors find this page.</td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Pages With No Links (${orphans.length})</h3>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Page URL</th>
                                    <th style="padding: 12px;">Link Status</th>
                                    <th style="padding: 12px;">Recommended Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${orphanRows.length > 0 ? orphanRows : `<tr><td colspan="3" style="padding: 32px; text-align: center; color: var(--text-secondary);">✓ No pages with missing links found. All discovered pages have links pointing to them.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                `;
                return;
            }

            if (this.activeTab === 'anchors') {
                let anchorRows = anchors.map(a => `
                    <tr style="border-bottom: 1px solid var(--border);">
                        <td style="font-weight: 600; padding: 12px 20px;">${this.escapeHtml(a.anchor_text)}</td>
                        <td style="padding: 12px;">${a.frequency}</td>
                    </tr>
                `).join('');

                container.innerHTML = `
                    <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px; max-width: 650px;">
                        <div style="padding: 16px 20px; border-bottom: 1px solid var(--border);">
                            <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Link Text Usage</h3>
                        </div>
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 20px;">Link Text</th>
                                    <th style="padding: 12px;">Times Used</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${anchorRows.length > 0 ? anchorRows : `<tr><td colspan="2" style="padding: 32px; text-align: center; color: var(--text-secondary);">No link text records found.</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                `;
                return;
            }

            // Default 'graph'
            let graphRows = links.map(l => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="font-family: monospace; font-size: 12px; color: var(--primary); padding: 12px 20px;">${this.escapeHtml(l.source)}</td>
                    <td style="font-family: monospace; font-size: 12px; padding: 12px;">${this.escapeHtml(l.target)}</td>
                    <td style="font-weight: 500; padding: 12px;">${this.escapeHtml(l.anchor_text || '(No Link Text)')}</td>
                </tr>
            `).join('');

            container.innerHTML = `
                <div class="card" style="padding: 0; overflow: hidden; border-radius: 14px;">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between;">
                        <h3 style="font-size: 15px; font-weight: 700; margin: 0; color: var(--text-primary);">Links Between Your Pages (${links.length})</h3>
                    </div>
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase;">
                                <th style="padding: 12px 20px;">Source Page</th>
                                <th style="padding: 12px;">Destination Page</th>
                                <th style="padding: 12px;">Link Text ${renderTooltip('Text that visitors click to navigate between pages.')}</th>
                            </tr>
                        </thead>
                        <tbody>${graphRows.length > 0 ? graphRows : `<tr><td colspan="3" style="padding: 32px; text-align: center; color: var(--text-secondary);">No page links discovered yet. Run a website scan to map your page links.</td></tr>`}</tbody>
                    </table>
                </div>
            `;
        } catch (e) {
            renderBackendOfflineState(container, `We couldn't load this information right now. Please try again.`, () => this.mounted());
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
