import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { apiClient } from '../services/apiClient.js';

export class Reports {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'reports-view';
        this.historyRecords = [];
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600; color: var(--text-primary);">Custom Report Builder & Executive Data Exports</h1>
                <p style="color: var(--text-secondary); margin-top: 4px; font-size: 14px;">Build custom multi-section executive PDF reports, export comprehensive CSV dataset packages, and view generated report logs.</p>
            </div>
            <div id="reports-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading custom report builder...
                </div>
            </div>
        `;
        return this.element;
    }

    async mounted() {
        const container = document.getElementById('reports-content');
        if (!container) return;

        try {
            await projectStore.ensureInitialized();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select an active project workspace.</div>`;
                return;
            }

            const projectDomain = selectedProj.domain || selectedProj.url || 'Target Domain';

            // Fetch report history
            try {
                const historyData = await apiClient.get(`/api/projects/${projectId}/reports/history`);
                this.historyRecords = Array.isArray(historyData) ? historyData : [];
            } catch (hErr) {
                this.historyRecords = [];
            }

            container.innerHTML = `
                <!-- CUSTOM REPORT BUILDER FORM -->
                <div class="card" style="padding: 24px; margin-bottom: 32px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);">
                    <h3 style="font-size: 17px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary);">Interactive Custom Executive Report Builder</h3>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">Report Title</label>
                            <input type="text" id="report-title-input" class="input" value="Custom SEO Executive Audit Report" style="width: 100%; padding: 8px 12px; font-size: 13.5px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">Brand Name / Agency Header</label>
                            <input type="text" id="report-brand-input" class="input" value="SEO Intelligence Platform" style="width: 100%; padding: 8px 12px; font-size: 13.5px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">
                        </div>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">Select Report Sections to Include</label>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; font-size: 13px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Executive Summary" checked> Executive Summary</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="SEO Health" checked> SEO Health Summary</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Technical Audit" checked> Technical Audit Findings</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Pages" checked> Crawled Pages Inventory</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Keywords" checked> Keywords & Topics</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Internal Links" checked> Internal Link Graph</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Opportunities" checked> Growth Opportunities</label>
                        </div>
                    </div>

                    <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                        <button class="btn btn-primary" id="btn-generate-pdf">Generate Custom Executive PDF</button>
                        <button class="btn btn-secondary" id="btn-generate-zip">Download Full Data Package (ZIP)</button>
                    </div>
                </div>

                <!-- PRE-CONFIGURED QUICK DOWNLOADS -->
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary);">Standard Modular Reports & Exports</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 32px;">
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                        <div style="font-weight: 600; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Full SEO Audit Report</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Executive PDF health summary</div>
                        <button id="btn-quick-audit-pdf" class="btn btn-primary btn-sm" style="width: 100%; text-align: center;">Download PDF</button>
                    </div>
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                        <div style="font-weight: 600; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Technical SEO Findings</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Technical audit issues & status</div>
                        <button id="btn-quick-tech-pdf" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center;">Download PDF</button>
                    </div>
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                        <div style="font-weight: 600; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Crawled Pages Inventory</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Complete inventory of crawl URLs</div>
                        <button id="btn-quick-pages-csv" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center;">Export CSV</button>
                    </div>
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border-color);">
                        <div style="font-weight: 600; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Complete ZIP Package</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">11 organized dataset folders + README</div>
                        <button id="btn-quick-zip" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center;">Download Complete ZIP</button>
                    </div>
                </div>

                <!-- REPORT GENERATION HISTORY -->
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary);">Generated Report Log & History</h3>
                <div class="card" style="padding: 0; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); overflow: hidden;">
                    <div style="overflow-x: auto;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13.5px;">
                            <thead>
                                <tr style="background: rgba(0,0,0,0.25); border-bottom: 1px solid var(--border-color); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 16px;">Report Name</th>
                                    <th style="padding: 12px 16px;">Format</th>
                                    <th style="padding: 12px 16px;">Filename</th>
                                    <th style="padding: 12px 16px;">Generated At</th>
                                    <th style="padding: 12px 16px;">Data Source</th>
                                    <th style="padding: 12px 16px;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${this.historyRecords.length === 0 ? `
                                    <tr>
                                        <td colspan="6" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                                            No report generation history logged yet. Generating a report or downloading an export will record history here.
                                        </td>
                                    </tr>
                                ` : this.historyRecords.map(r => `
                                    <tr style="border-bottom: 1px solid var(--border-color);">
                                        <td style="padding: 12px 16px; font-weight: 600; color: var(--text-primary);">${this.escapeHtml(r.report_type)}</td>
                                        <td style="padding: 12px 16px;">
                                            <span style="font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: rgba(59,130,246,0.15); color: #60a5fa; text-transform: uppercase;">${this.escapeHtml(r.file_type)}</span>
                                        </td>
                                        <td style="padding: 12px 16px; color: var(--text-secondary); font-family: monospace; font-size: 12px;">${this.escapeHtml(r.filename)}</td>
                                        <td style="padding: 12px 16px; color: var(--text-secondary);">${r.generated_at ? new Date(r.generated_at).toLocaleString() : 'Recent'}</td>
                                        <td style="padding: 12px 16px; color: var(--text-tertiary); font-size: 12px;">${this.escapeHtml(r.data_sources || 'Crawled Data')}</td>
                                        <td style="padding: 12px 16px;">
                                            <span style="font-size: 11px; font-weight: 600; color: #10b981;">${this.escapeHtml(r.status || 'Completed')}</span>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            document.getElementById('btn-generate-pdf')?.addEventListener('click', () => this.triggerReportDownload('pdf'));
            document.getElementById('btn-generate-zip')?.addEventListener('click', () => this.triggerReportDownload('zip'));

            const quickAudit = document.getElementById('btn-quick-audit-pdf');
            const quickTech = document.getElementById('btn-quick-tech-pdf');
            const quickPages = document.getElementById('btn-quick-pages-csv');
            const quickZip = document.getElementById('btn-quick-zip');

            if (quickAudit) quickAudit.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/reports/audit.pdf`, 'seo-audit.pdf', e.currentTarget);
            if (quickTech) quickTech.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/reports/technical.pdf`, 'technical-seo.pdf', e.currentTarget);
            if (quickPages) quickPages.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/pages/export.csv`, 'pages.csv', e.currentTarget);
            if (quickZip) quickZip.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/reports/complete-export.zip`, 'project-export.zip', e.currentTarget);

        } catch (e) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center; color: var(--critical);">Unable to load report builder options.</div>`;
        }
    }

    async triggerReportDownload(fmt) {
        const projectId = projectStore.getSelectedProjectId();
        if (!projectId) return;

        const btnPdf = document.getElementById('btn-generate-pdf');
        const btnZip = document.getElementById('btn-generate-zip');
        const activeBtn = fmt === 'zip' ? btnZip : btnPdf;

        if (activeBtn) {
            activeBtn.disabled = true;
            activeBtn.innerText = 'Generating Export...';
        }

        const title = document.getElementById('report-title-input')?.value || "Custom SEO Executive Audit Report";
        const brand = document.getElementById('report-brand-input')?.value || "SEO Intelligence Platform";
        
        const chks = document.querySelectorAll('.sec-chk:checked');
        const sections = Array.from(chks).map(c => c.value);

        try {
            const token = localStorage.getItem('seo_auth_token') || localStorage.getItem('jwt_token');
            const headers = { 'Content-Type': 'application/json' };
            if (token && token.trim()) {
                headers['Authorization'] = `Bearer ${token.trim()}`;
            }

            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/reports/builder`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    report_title: title,
                    brand_name: brand,
                    sections: sections,
                    format: fmt
                })
            });

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }

            let filename = fmt === 'zip' ? 'seo-export.zip' : 'seo-report.pdf';
            const contentDisposition = res.headers.get('Content-Disposition');
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="?([^";]+)"?/);
                if (match && match[1]) {
                    filename = match[1];
                }
            }

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            if (activeBtn) {
                activeBtn.innerText = 'Download Ready!';
                setTimeout(() => {
                    activeBtn.disabled = false;
                    activeBtn.innerText = fmt === 'zip' ? 'Download Full Data Package (ZIP)' : 'Generate Custom Executive PDF';
                }, 2000);
            }

            // Refresh history
            setTimeout(() => this.mounted(), 1000);

        } catch (e) {
            alert("Failed to generate report: " + e.message);
            if (activeBtn) {
                activeBtn.disabled = false;
                activeBtn.innerText = 'Export Failed - Try Again';
            }
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
