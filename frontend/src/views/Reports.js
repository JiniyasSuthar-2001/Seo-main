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
                <h1 style="font-size: 24px; font-weight: 600;">Custom Report Builder & Executive Data Exports</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Build custom multi-section executive PDF reports and export comprehensive CSV dataset packages.</p>
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
            await projectStore.fetchProjects();
            const selectedProj = projectStore.getSelectedProject();
            const projectId = projectStore.getSelectedProjectId();

            if (!selectedProj || !projectId) {
                container.innerHTML = `<div class="card" style="padding: 32px; text-align: center;">Please select an active project workspace.</div>`;
                return;
            }

            container.innerHTML = `
                <!-- CUSTOM REPORT BUILDER FORM -->
                <div class="card" style="padding: 24px; margin-bottom: 32px;">
                    <h3 style="font-size: 17px; font-weight: 600; margin-bottom: 16px;">Interactive Custom Report Builder</h3>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px;">
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">Report Title</label>
                            <input type="text" id="report-title-input" class="input" value="Custom SEO Executive Audit Report" style="width: 100%; padding: 8px 12px; font-size: 13px;">
                        </div>
                        <div>
                            <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">Brand Name / Agency Header</label>
                            <input type="text" id="report-brand-input" class="input" value="SEO Intelligence Platform" style="width: 100%; padding: 8px 12px; font-size: 13px;">
                        </div>
                    </div>

                    <div style="margin-bottom: 20px;">
                        <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">Select Report Sections to Include</label>
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; font-size: 13px;">
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Executive Summary" checked> Executive Summary</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="SEO Health" checked> SEO Health Score</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Technical Audit" checked> Technical Audit</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Pages" checked> Crawled Pages</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Keywords" checked> Keywords & Topics</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Rankings"> Position Tracking</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Competitors"> Competitors</label>
                            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;"><input type="checkbox" class="sec-chk" value="Opportunities" checked> Growth Opportunities</label>
                        </div>
                    </div>

                    <div style="display: flex; gap: 12px; align-items: center;">
                        <button class="btn btn-primary" id="btn-generate-pdf">Generate Custom Executive PDF</button>
                        <button class="btn btn-secondary" id="btn-generate-zip">Download Full CSV Package (ZIP)</button>
                    </div>
                </div>

                <!-- PRE-CONFIGURED QUICK DOWNLOADS -->
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">Quick Modular Downloads</h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                    <div class="card" style="padding: 16px;">
                        <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px;">Technical Audit</div>
                        <a href="${API_BASE_URL}/api/projects/${projectId}/technical/report.pdf" target="_blank" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center; margin-top: 8px;">Download PDF</a>
                    </div>
                    <div class="card" style="padding: 16px;">
                        <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px;">Crawled Pages</div>
                        <a href="${API_BASE_URL}/api/projects/${projectId}/pages/report.pdf" target="_blank" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center; margin-top: 8px;">Download PDF</a>
                    </div>
                    <div class="card" style="padding: 16px;">
                        <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px;">Internal Links</div>
                        <a href="${API_BASE_URL}/api/projects/${projectId}/internal-links/report.pdf" target="_blank" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center; margin-top: 8px;">Download PDF</a>
                    </div>
                    <div class="card" style="padding: 16px;">
                        <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px;">Keyword Intelligence</div>
                        <a href="${API_BASE_URL}/api/projects/${projectId}/reports/keywords" target="_blank" class="btn btn-secondary btn-sm" style="width: 100%; text-align: center; margin-top: 8px;">Download PDF</a>
                    </div>
                </div>
            `;

            document.getElementById('btn-generate-pdf')?.addEventListener('click', () => this.triggerReportDownload('pdf'));
            document.getElementById('btn-generate-zip')?.addEventListener('click', () => this.triggerReportDownload('zip'));

        } catch (e) {
            container.innerHTML = `<div class="card" style="padding: 32px; text-align: center; color: var(--critical);">Unable to load report builder options.</div>`;
        }
    }

    async triggerReportDownload(fmt) {
        const projectId = projectStore.getSelectedProjectId();
        if (!projectId) return;

        const title = document.getElementById('report-title-input')?.value || "Custom SEO Executive Audit Report";
        const brand = document.getElementById('report-brand-input')?.value || "SEO Intelligence Platform";
        
        const chks = document.querySelectorAll('.sec-chk:checked');
        const sections = Array.from(chks).map(c => c.value);

        try {
            const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/reports/builder`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    report_title: title,
                    brand_name: brand,
                    sections: sections,
                    format: fmt
                })
            });
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = fmt === 'zip' ? 'SEO-Custom-Data-Package.zip' : 'SEO-Custom-Executive-Report.pdf';
            a.click();
        } catch (e) {
            alert("Failed to generate report: " + e.message);
        }
    }
}
