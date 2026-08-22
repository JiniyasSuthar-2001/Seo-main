import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';

export class Reports {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'reports-view';
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">SEO Reports & Data Exports</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Generate executive PDF audit reports, modular CSV datasets, and consolidated project archives.</p>
            </div>
            <div id="reports-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading report options...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('reports-content');
        if (!container) return;

        try {
            await projectStore.fetchProjects();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-title">No Active Project Selected</div>
                        <div class="empty-state-desc">Please select or create an SEO project workspace to generate PDF reports and export CSV datasets.</div>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <!-- EXECUTIVE & FULL DATA EXPORTS -->
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; margin-bottom: 32px;">
                    
                    <div class="card" style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; border-left: 4px solid var(--primary);">
                        <div>
                            <span style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase;">Executive Report</span>
                            <h3 style="font-size: 17px; font-weight: 600; margin: 6px 0 8px;">Full SEO Project PDF Report</h3>
                            <p style="color: var(--text-secondary); font-size: 13px; line-height: 1.5; margin-bottom: 16px;">
                                Executive presentation PDF covering website overview, crawl statistics, technical findings, page audit inventory, and keyword analysis for <strong>${selectedProj.name}</strong>.
                            </p>
                        </div>
                        <a href="${API_BASE_URL}/api/projects/${projectId}/report.pdf" target="_blank" class="btn btn-primary" style="text-decoration: none; text-align: center;">
                            Download Full PDF Report
                        </a>
                    </div>

                    <div class="card" style="padding: 24px; display: flex; flex-direction: column; justify-content: space-between; border-left: 4px solid #10b981;">
                        <div>
                            <span style="font-size: 11px; font-weight: 700; color: #10b981; text-transform: uppercase;">Complete Data Package</span>
                            <h3 style="font-size: 17px; font-weight: 600; margin: 6px 0 8px;">Project ZIP Data Archive</h3>
                            <p style="color: var(--text-secondary); font-size: 13px; line-height: 1.5; margin-bottom: 16px;">
                                Download a comprehensive ZIP file containing all CSV datasets (Pages, Technical Issues, Internal Links, Keywords, Rankings, Backlinks, Competitors, Crawl History).
                            </p>
                        </div>
                        <a href="${API_BASE_URL}/api/projects/${projectId}/export" target="_blank" class="btn btn-secondary" style="text-decoration: none; text-align: center;">
                            Download Complete Data ZIP
                        </a>
                    </div>

                </div>

                <!-- MODULAR REPORT EXPORTS -->
                <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 16px;">Modular Audit Reports & Datasets</h2>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-bottom: 32px;">
                    
                    <div class="card" style="padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h4 style="font-size: 15px; font-weight: 600; margin-bottom: 6px;">Technical SEO Audit</h4>
                            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 16px;">Evidence-based technical findings, affected URLs, and severity ratings.</p>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <a href="${API_BASE_URL}/api/projects/${projectId}/technical/report.pdf" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">PDF</a>
                            <a href="${API_BASE_URL}/api/projects/${projectId}/technical/export.csv" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">CSV</a>
                        </div>
                    </div>

                    <div class="card" style="padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h4 style="font-size: 15px; font-weight: 600; margin-bottom: 6px;">Crawled Pages Inventory</h4>
                            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 16px;">Extracted metadata, title tags, H1s, word counts, and HTTP status codes.</p>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <a href="${API_BASE_URL}/api/projects/${projectId}/pages/report.pdf" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">PDF</a>
                            <a href="${API_BASE_URL}/api/projects/${projectId}/pages/export.csv" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">CSV</a>
                        </div>
                    </div>

                    <div class="card" style="padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h4 style="font-size: 15px; font-weight: 600; margin-bottom: 6px;">Internal Link Graph</h4>
                            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 16px;">Page-to-page link architecture mapping and anchor text graph.</p>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <a href="${API_BASE_URL}/api/projects/${projectId}/internal-links/report.pdf" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">PDF</a>
                            <a href="${API_BASE_URL}/api/projects/${projectId}/internal-links/export.csv" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">CSV</a>
                        </div>
                    </div>

                    <div class="card" style="padding: 20px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <h4 style="font-size: 15px; font-weight: 600; margin-bottom: 6px;">Keyword Intelligence</h4>
                            <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 16px;">NLP content topics, entity terms, and keyword occurrence counts.</p>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <a href="${API_BASE_URL}/api/projects/${projectId}/reports/keywords" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">PDF</a>
                            <a href="${API_BASE_URL}/api/projects/${projectId}/keywords/export.csv" target="_blank" class="btn btn-secondary btn-sm" style="flex: 1; text-align: center;">CSV</a>
                        </div>
                    </div>

                </div>

                <!-- CONSOLIDATED PORTFOLIO EXPORTS -->
                <div class="card" style="padding: 24px; background: var(--bg-subtle);">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
                        <div>
                            <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 4px;">Portfolio-Wide Consolidated Reports</h3>
                            <p style="color: var(--text-secondary); font-size: 13px; margin: 0;">Export high-level summary overview for all managed SEO project workspaces.</p>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <a href="${API_BASE_URL}/api/projects/all/pdf" target="_blank" class="btn btn-secondary btn-sm">All Projects PDF</a>
                            <a href="${API_BASE_URL}/api/projects/all/export" target="_blank" class="btn btn-secondary btn-sm">All Projects ZIP</a>
                        </div>
                    </div>
                </div>
            `;
        } catch (e) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center; color: var(--critical);">Unable to load report options.</div>`;
        }
    }
}
