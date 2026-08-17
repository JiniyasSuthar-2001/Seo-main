import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { renderBackendOfflineState } from '../components/ErrorState.js';

export class Settings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'settings-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Project Settings & Data Source Center</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Configure workspace projects, local storage paths, and first-party API connections.</p>
            </div>
            <div id="settings-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading settings & data sources...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('settings-content');
        if (!container) return;

        try {
            await projectStore.fetchProjects();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            let dsData = {};
            if (projectId) {
                try {
                    const dsRes = await fetch(`${API_BASE_URL}/api/projects/${projectId}/datasources`);
                    if (dsRes.ok) {
                        const resJson = await dsRes.json();
                        dsData = resJson.datasources || {};
                    }
                } catch(err) {}
            }

            const projName = selectedProj ? selectedProj.name : 'No active project';
            const projDomain = selectedProj ? (selectedProj.domain || selectedProj.url) : 'https://example.com/';
            const safeDomain = projDomain.replace("https://", "").replace("http://", "").replace("www.", "").replace(/[^a-zA-Z0-9]/g, "_");

            const sourceKeys = Object.keys(dsData);
            let dsCardsHtml = '';
            if (sourceKeys.length > 0) {
                dsCardsHtml = sourceKeys.map(k => {
                    const src = dsData[k];
                    const isConnected = src.status.toLowerCase().includes('connected');
                    return `
                        <div class="card" style="padding: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                <div>
                                    <h4 style="font-size: 15px; font-weight: 600;">${src.name}</h4>
                                    <span style="font-size: 11px; color: var(--text-secondary);">${src.type}</span>
                                </div>
                                <span class="badge ${isConnected ? 'badge-success' : 'badge-info'}">
                                    ${src.status}
                                </span>
                            </div>
                            <p style="font-size: 13px; color: var(--text-secondary); margin: 8px 0 12px; line-height: 1.5;">${src.description}</p>
                            <div style="font-size: 11px; font-family: monospace; color: var(--text-secondary);">
                                ${src.local_only ? '● Runs 100% locally on your computer' : 'Requires API connection / OAuth'}
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                dsCardsHtml = `
                    <div class="card" style="padding: 20px;">
                        <h4 style="font-size: 15px; font-weight: 600;">Website Crawler & HTML Parser</h4>
                        <span class="badge badge-success" style="margin-top: 4px;">Connected (Local)</span>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">Directly crawls HTML, sitemaps, canonicals, and metadata.</p>
                    </div>
                    <div class="card" style="padding: 20px;">
                        <h4 style="font-size: 15px; font-weight: 600;">Google Search Console API</h4>
                        <span class="badge badge-info" style="margin-top: 4px;">Available (OAuth)</span>
                        <p style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">Fetches clicks, impressions, CTR, and search queries directly from Google.</p>
                    </div>
                `;
            }

            container.innerHTML = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px;">
                    <!-- ACTIVE PROJECT INFO -->
                    <div class="card" style="padding: 24px;">
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Selected Project Details</h3>
                        <div style="display: flex; flex-direction: column; gap: 12px; font-size: 14px;">
                            <div>
                                <span style="color: var(--text-secondary); font-size: 12px; display: block;">PROJECT NAME</span>
                                <strong style="font-size: 16px;">${projName}</strong>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); font-size: 12px; display: block;">TARGET DOMAIN</span>
                                <a href="${projDomain}" target="_blank" style="color: var(--primary); text-decoration: none;">${projDomain}</a>
                            </div>
                            <div>
                                <span style="color: var(--text-secondary); font-size: 12px; display: block;">LOCAL STORAGE DIRECTORY</span>
                                <code style="background: var(--bg-subtle); padding: 4px 8px; border-radius: 4px; font-size: 12px;">data/websites/${safeDomain}/</code>
                            </div>
                        </div>
                    </div>

                    <!-- LOCAL PERSISTENCE SETTINGS -->
                    <div class="card" style="padding: 24px;">
                        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Local Privacy & Storage</h3>
                        <p style="font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 16px;">
                            All website crawl snapshots, technical audit issues, internal link graphs, and provider settings remain stored 100% on your local machine. No external SaaS databases are used.
                        </p>
                        <span class="badge badge-success">Self-Hosted Local Storage Active</span>
                    </div>
                </div>

                <!-- DATA SOURCE CENTER -->
                <div style="margin-top: 32px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h2 style="font-size: 18px; font-weight: 600;">Data Source Center</h2>
                        <span style="font-size: 13px; color: var(--text-secondary);">Hierarchy: Local Engine → Direct Crawl → Free APIs → Public Sources → Adapters → CSV</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
                        ${dsCardsHtml}
                    </div>
                </div>
            `;

        } catch (e) {
            renderBackendOfflineState(container, "Unable to load settings from backend API.");
        }
    }
}
