import { internalLinksService } from '../services/internalLinks.js';
import { projectStore } from '../core/projectStore.js';
import { renderBackendOfflineState } from '../components/ErrorState.js';

export class InternalLinks {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'internal-links-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Internal Link Architecture</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Map of internal link relationships and anchor text extracted from the latest crawl snapshot.</p>
            </div>
            <div id="links-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading internal link graph...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('links-content');
        if (!container) return;

        try {
            const links = await internalLinksService.getInternalLinks(projectStore.getSelectedProjectId(), 100, 0);

            if (!links || links.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
                        </div>
                        <div class="empty-state-title">No Internal Links Mapped</div>
                        <div class="empty-state-desc">Run a website crawl to extract internal links, analyze page connectivity, and discover orphan page candidates.</div>
                        <button class="btn btn-primary" onclick="window.location.href='/'">Go to Dashboard</button>
                    </div>
                `;
                return;
            }

            let rows = links.map(l => `
                <tr>
                    <td style="font-family: monospace; font-size: 13px; max-width: 280px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        <a href="${l.source}" target="_blank" style="color: var(--primary); text-decoration: none;">${l.source}</a>
                    </td>
                    <td style="font-family: monospace; font-size: 13px; max-width: 280px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        <a href="${l.target}" target="_blank" style="color: var(--primary); text-decoration: none;">${l.target}</a>
                    </td>
                    <td style="font-size: 13px; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${l.anchor_text || '-'}">
                        ${l.anchor_text ? l.anchor_text : '<span style="color: var(--text-tertiary); font-style: italic;">[Empty / Image Link]</span>'}
                    </td>
                </tr>
            `).join('');

            container.innerHTML = `
                <div class="data-table-wrapper">
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); font-weight: 600; font-size: 14px;">
                        Extracted Internal Link Relationships: ${links.length}
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Source Page</th>
                                <th>Target Page</th>
                                <th>Anchor Text</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (e) {
            renderBackendOfflineState(container, "Unable to load internal link graph.");
        }
    }
}
