import { projectStore } from '../core/projectStore.js';
import { API_BASE_URL } from '../config/api.js';
import { apiClient } from '../services/apiClient.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';

export class Reports {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'reports-view';
        this.historyRecords = [];
    }

    render() {
        this.element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Reports & Data Exports</h1>
                <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Download PDF reports or export your website data into spreadsheets.</p>
            </div>
            <div id="reports-content">
                <div class="card" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                    Loading reports...
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
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select a website project.</div>`;
                return;
            }

            const projectDomain = selectedProj.domain || selectedProj.url || 'Target Website';
            const safeProjName = (selectedProj.name || 'website').replace(/[^a-zA-Z0-9_-]/g, '_');
            const todayStr = new Date().toISOString().split('T')[0];

            // Fetch report history
            try {
                const historyData = await apiClient.get(`/api/projects/${projectId}/reports/history`);
                this.historyRecords = Array.isArray(historyData) ? historyData : [];
            } catch (hErr) {
                this.historyRecords = [];
            }

            container.innerHTML = `
                <!-- CUSTOM REPORT BUILDER FORM -->
                <div class="card" style="padding: 24px; margin-bottom: 32px; background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border);">
                    <h3 style="font-size: 17px; font-weight: 700; margin: 0 0 16px 0; color: var(--text-primary);">Custom PDF Report Generator</h3>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; margin-bottom: 20px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">Report Title</label>
                            <input type="text" id="report-title-input" class="input" value="Website Health & Search Report" style="width: 100%; padding: 8px 12px; font-size: 13.5px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 6px; color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">Company / Brand Header</label>
                            <input type="text" id="report-brand-input" class="input" value="SEO Intelligence Platform" style="width: 100%; padding: 8px 12px; font-size: 13.5px; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 6px; color: var(--text-primary);">
                        </div>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">Select Sections to Include</label>
                        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; font-size: 13px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Executive Summary" checked> Executive Summary</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="SEO Health" checked> Website Health Summary</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Technical Audit" checked> Technical Problems & Proof</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Pages" checked> Pages Found on Your Site</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Keywords" checked> Target Keywords</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Internal Links" checked> Page Links</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Opportunities" checked> Action Opportunities</label>
                        </div>
                    </div>

                    <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                        <button class="btn btn-primary" id="btn-generate-pdf">Download Custom Executive PDF</button>
                        <button class="btn btn-secondary" id="btn-generate-xlsx">Download Master Excel Workbook (.xlsx)</button>
                        <button class="btn btn-secondary" id="btn-generate-pptx">Download Executive Presentation (.pptx)</button>
                        <button class="btn btn-secondary" id="btn-generate-zip">Download All My Data (ZIP)</button>
                    </div>
                </div>

                <!-- PRE-CONFIGURED QUICK DOWNLOADS -->
                <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 16px; color: var(--text-primary);">Quick Report Downloads</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; margin-bottom: 32px;">
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                        <div style="font-weight: 700; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Full Website Health Report</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Complete PDF report summary</div>
                        <button id="btn-quick-audit-pdf" class="btn btn-primary btn-sm" style="width: 100%; text-align: center;">Download PDF</button>
                    </div>
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                        <div style="font-weight: 700; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Master Excel Workbook</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">10 Structured Worksheets (.xlsx)</div>
                        <button id="btn-quick-master-xlsx" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center;">Download XLSX</button>
                    </div>
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                        <div style="font-weight: 700; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Executive Presentation</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">14 Client Slides (.pptx)</div>
                        <button id="btn-quick-master-pptx" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center;">Download PPTX</button>
                    </div>
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                        <div style="font-weight: 700; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Technical Health Checks</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Detailed check findings</div>
                        <button id="btn-quick-tech-pdf" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center;">Download PDF</button>
                    </div>
                    <div class="card" style="padding: 18px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                        <div style="font-weight: 700; font-size: 14.5px; margin-bottom: 4px; color: var(--text-primary);">Pages Discovered (CSV)</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 12px;">Spreadsheet of website pages</div>
                        <button id="btn-quick-pages-csv" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center;">Download CSV</button>
                    </div>
                </div>
            `;

            // Bind download buttons with standardized filenames
            const btnPdf = container.querySelector('#btn-generate-pdf');
            const btnXlsx = container.querySelector('#btn-generate-xlsx');
            const btnPptx = container.querySelector('#btn-generate-pptx');
            const btnZip = container.querySelector('#btn-generate-zip');
            const btnQuickAudit = container.querySelector('#btn-quick-audit-pdf');
            const btnQuickXlsx = container.querySelector('#btn-quick-master-xlsx');
            const btnQuickPptx = container.querySelector('#btn-quick-master-pptx');
            const btnQuickTech = container.querySelector('#btn-quick-tech-pdf');
            const btnQuickPages = container.querySelector('#btn-quick-pages-csv');

            if (btnPdf) {
                btnPdf.onclick = (e) => {
                    const title = container.querySelector('#report-title-input')?.value || 'Website Health & Search Report';
                    const brand_name = container.querySelector('#report-brand-input')?.value || 'SEO Intelligence Platform';
                    const sections = Array.from(container.querySelectorAll('.sec-chk:checked')).map(c => c.value);

                    apiClient.downloadFile(
                        `/api/projects/${projectId}/reports/builder`,
                        `${safeProjName}-SEO-Custom-Report-${todayStr}.pdf`,
                        e.currentTarget,
                        {
                            method: 'POST',
                            body: JSON.stringify({ title, brand_name, sections })
                        }
                    );
                };
            }

            if (btnXlsx) btnXlsx.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/export.xlsx`, `${safeProjName}_SEO_Master_Export_${todayStr}.xlsx`, e.currentTarget);
            if (btnPptx) btnPptx.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/export.pptx`, `${safeProjName}_SEO_Executive_Presentation_${todayStr}.pptx`, e.currentTarget);
            if (btnZip) btnZip.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/reports/complete-export.zip`, `${safeProjName}_SEO_Master_Export_${todayStr}.zip`, e.currentTarget);
            if (btnQuickAudit) btnQuickAudit.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/report.pdf`, `${safeProjName}_Full_Website_Health_Report_${todayStr}.pdf`, e.currentTarget);
            if (btnQuickXlsx) btnQuickXlsx.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/export.xlsx`, `${safeProjName}_SEO_Master_Export_${todayStr}.xlsx`, e.currentTarget);
            if (btnQuickPptx) btnQuickPptx.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/export.pptx`, `${safeProjName}_SEO_Executive_Presentation_${todayStr}.pptx`, e.currentTarget);
            if (btnQuickTech) btnQuickTech.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/technical/report.pdf`, `${safeProjName}_Technical_Issues_${todayStr}.pdf`, e.currentTarget);
            if (btnQuickPages) btnQuickPages.onclick = (e) => apiClient.downloadFile(`/api/projects/${projectId}/pages/export.csv`, `${safeProjName}_Pages_Inventory_${todayStr}.csv`, e.currentTarget);

        } catch (e) {
            renderFeatureErrorState(container, "Failed to load reports", e.message || "Unable to load report generator.", () => this.mounted());
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
