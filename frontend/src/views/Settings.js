import { settingsService } from '../services/settingsService.js';

export class Settings {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'settings-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Platform Control Center & Settings</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">System architecture configuration, crawl engine rules, and live server health status.</p>
            </div>

            <div style="display: flex; flex-direction: column; gap: 24px; max-width: 960px;">
                
                <!-- SYSTEM STATUS SECTION -->
                <div class="card" style="padding: 24px;">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">API & System Health Status</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px;" id="system-status-grid">
                        <div style="background: var(--bg-subtle); padding: 14px 16px; border-radius: 8px;">
                            <div style="font-size: 12px; color: var(--text-secondary);">Frontend Server</div>
                            <div style="font-weight: 600; color: var(--success); margin-top: 4px;">● Running (:8020)</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 14px 16px; border-radius: 8px;">
                            <div style="font-size: 12px; color: var(--text-secondary);">Backend API</div>
                            <div id="backend-status-badge" style="font-weight: 600; color: var(--text-secondary); margin-top: 4px;">Checking...</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 14px 16px; border-radius: 8px;">
                            <div style="font-size: 12px; color: var(--text-secondary);">Database Engine</div>
                            <div id="db-status-badge" style="font-weight: 600; color: var(--text-secondary); margin-top: 4px;">Checking...</div>
                        </div>
                        <div style="background: var(--bg-subtle); padding: 14px 16px; border-radius: 8px;">
                            <div style="font-size: 12px; color: var(--text-secondary);">Local File Storage</div>
                            <div style="font-weight: 600; color: var(--success); margin-top: 4px;">● Available</div>
                        </div>
                    </div>
                    <div id="backend-error-banner" style="display: none; margin-top: 16px; padding: 12px; background: var(--critical-bg); color: var(--critical); border-radius: 6px; font-size: 13px;">
                        Unable to connect to the SEO backend at ${settingsService.getApiBaseUrl()}. Check that the FastAPI server is running.
                    </div>
                </div>

                <!-- GENERAL CONFIGURATION -->
                <div class="card" style="padding: 24px;">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">General Workspace Configuration</h2>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <tr style="border-bottom: 1px solid var(--border-subtle);">
                            <td style="padding: 12px 0; color: var(--text-secondary); width: 240px;">Application Name</td>
                            <td style="padding: 12px 0; font-weight: 500;">SEO Intelligence Platform</td>
                        </tr>
                        <tr style="border-bottom: 1px solid var(--border-subtle);">
                            <td style="padding: 12px 0; color: var(--text-secondary);">Frontend Location</td>
                            <td style="padding: 12px 0; font-family: monospace;">http://localhost:8020</td>
                        </tr>
                        <tr style="border-bottom: 1px solid var(--border-subtle);">
                            <td style="padding: 12px 0; color: var(--text-secondary);">Backend API Base URL</td>
                            <td style="padding: 12px 0; font-family: monospace;">${settingsService.getApiBaseUrl()}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 0; color: var(--text-secondary);">Storage Root Directory</td>
                            <td style="padding: 12px 0; font-family: monospace;">data/websites/</td>
                        </tr>
                    </table>
                </div>

                <!-- ACTIVE PROJECT WORKSPACE -->
                <div class="card" style="padding: 24px;">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Active Project Workspace Context</h2>
                    <div id="project-settings-content">
                        <div style="color: var(--text-secondary); font-size: 14px;">Loading project context...</div>
                    </div>
                </div>

                <!-- CRAWL ENGINE CONFIGURATION -->
                <div class="card" style="padding: 24px;">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Crawl Engine Configuration</h2>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                        <tr style="border-bottom: 1px solid var(--border-subtle);">
                            <td style="padding: 12px 0; color: var(--text-secondary); width: 240px;">Maximum Pages per Crawl</td>
                            <td style="padding: 12px 0; font-weight: 500;">100 pages</td>
                        </tr>
                        <tr style="border-bottom: 1px solid var(--border-subtle);">
                            <td style="padding: 12px 0; color: var(--text-secondary);">HTTP Request Timeout</td>
                            <td style="padding: 12px 0; font-weight: 500;">10.0 seconds</td>
                        </tr>
                        <tr style="border-bottom: 1px solid var(--border-subtle);">
                            <td style="padding: 12px 0; color: var(--text-secondary);">Batch Size & Throttle</td>
                            <td style="padding: 12px 0; font-weight: 500;">5 concurrent requests / 0.5s delay</td>
                        </tr>
                        <tr style="border-bottom: 1px solid var(--border-subtle);">
                            <td style="padding: 12px 0; color: var(--text-secondary);">Domain Scope Rule</td>
                            <td style="padding: 12px 0; font-weight: 500;">Same-domain restriction enforced</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px 0; color: var(--text-secondary);">Public Safety Mode</td>
                            <td style="padding: 12px 0; font-weight: 500; color: var(--success);">Read-Only Analysis Only (No write/POST/PUT to analyzed site)</td>
                        </tr>
                    </table>
                </div>

                <!-- LOCAL DATA STORAGE ARCHITECTURE -->
                <div class="card" style="padding: 24px;">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Local Data Storage Architecture</h2>
                    <div style="font-size: 14px; display: flex; flex-direction: column; gap: 10px;">
                        <div><strong style="color: var(--text-secondary);">Architecture:</strong> Local Filesystem JSON Snapshots + SQLite Database Index</div>
                        <div><strong style="color: var(--text-secondary);">Website Folder Mapping:</strong> <code style="background: var(--bg-subtle); padding: 3px 8px; border-radius: 4px;">data/websites/[sanitized_domain]/</code></div>
                        <div><strong style="color: var(--text-secondary);">Snapshots Directory:</strong> <code style="background: var(--bg-subtle); padding: 3px 8px; border-radius: 4px;">data/websites/[sanitized_domain]/crawls/[timestamp]/</code></div>
                        <div><strong style="color: var(--text-secondary);">Latest Pointer:</strong> <code style="background: var(--bg-subtle); padding: 3px 8px; border-radius: 4px;">data/websites/[sanitized_domain]/latest.json</code></div>
                    </div>
                </div>

                <!-- APPLICATION METADATA -->
                <div class="card" style="padding: 24px; margin-bottom: 32px;">
                    <h2 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Application Metadata</h2>
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; font-size: 14px;">
                        <div>
                            <span style="color: var(--text-secondary); display: block; font-size: 12px; font-weight: 600;">VERSION</span>
                            <span style="font-weight: 500;">v1.0.0 (Development)</span>
                        </div>
                        <div>
                            <span style="color: var(--text-secondary); display: block; font-size: 12px; font-weight: 600;">BACKEND ENGINE</span>
                            <span style="font-weight: 500;">FastAPI / Python 3.14</span>
                        </div>
                        <div>
                            <span style="color: var(--text-secondary); display: block; font-size: 12px; font-weight: 600;">FRONTEND STACK</span>
                            <span style="font-weight: 500;">Vanilla JS / ES Modules</span>
                        </div>
                        <div>
                            <span style="color: var(--text-secondary); display: block; font-size: 12px; font-weight: 600;">ROUTER</span>
                            <span style="font-weight: 500;">Custom SPA History Router</span>
                        </div>
                    </div>
                </div>

            </div>
        `;
        return this.element;
    }

    async mounted() {
        // 1. Check Health Status
        const health = await settingsService.checkHealth();
        const backendBadge = document.getElementById('backend-status-badge');
        const dbBadge = document.getElementById('db-status-badge');
        const errBanner = document.getElementById('backend-error-banner');

        if (health.status === 'connected') {
            if (backendBadge) {
                backendBadge.innerText = '● Connected';
                backendBadge.style.color = 'var(--success)';
            }
            if (dbBadge) {
                dbBadge.innerText = '● Connected';
                dbBadge.style.color = 'var(--success)';
            }
            if (errBanner) errBanner.style.display = 'none';
        } else {
            if (backendBadge) {
                backendBadge.innerText = '● Offline';
                backendBadge.style.color = 'var(--critical)';
            }
            if (dbBadge) {
                dbBadge.innerText = '● Offline';
                dbBadge.style.color = 'var(--critical)';
            }
            if (errBanner) errBanner.style.display = 'block';
        }

        // 2. Fetch Project Info
        const projContent = document.getElementById('project-settings-content');
        if (!projContent) return;

        const summary = await settingsService.getProjectSummary('1');
        
        if (summary.status === 'success' && summary.latest_crawl) {
            const crawl = summary.latest_crawl;
            projContent.innerHTML = `
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 12px 0; color: var(--text-secondary); width: 240px;">Project Name</td>
                        <td style="padding: 12px 0; font-weight: 600;">UIS Digital</td>
                    </tr>
                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 12px 0; color: var(--text-secondary);">Target Domain</td>
                        <td style="padding: 12px 0;"><a href="${crawl.website}" target="_blank" style="color: var(--primary); text-decoration: none;">${crawl.website}</a></td>
                    </tr>
                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 12px 0; color: var(--text-secondary);">Project ID</td>
                        <td style="padding: 12px 0; font-family: monospace;">1</td>
                    </tr>
                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 12px 0; color: var(--text-secondary);">Latest Crawl Snapshot</td>
                        <td style="padding: 12px 0; font-weight: 500;">${crawl.timestamp} (${crawl.pages_crawled} pages)</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 0; color: var(--text-secondary);">Project Folder Path</td>
                        <td style="padding: 12px 0; font-family: monospace;">data/websites/uisdigital/</td>
                    </tr>
                </table>
            `;
        } else {
            projContent.innerHTML = `
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 12px 0; color: var(--text-secondary); width: 240px;">Project Name</td>
                        <td style="padding: 12px 0; font-weight: 600;">UIS Digital</td>
                    </tr>
                    <tr style="border-bottom: 1px solid var(--border-subtle);">
                        <td style="padding: 12px 0; color: var(--text-secondary);">Target Domain</td>
                        <td style="padding: 12px 0;">https://uisdigital.com/</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 0; color: var(--text-secondary);">Latest Crawl Snapshot</td>
                        <td style="padding: 12px 0; color: var(--text-secondary);">No crawl snapshots available yet.</td>
                    </tr>
                </table>
            `;
        }
    }
}
