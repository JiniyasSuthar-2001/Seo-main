import { projectStore } from '../core/projectStore.js';
import { getApiBaseUrl } from '../config/api.js';
import { getUploadGuidance } from '../config/uploadGuidance.js';
import { UploadGuidanceComponent } from '../components/UploadGuidanceComponent.js';
import { FileInspectorModal } from '../components/FileInspectorModal.js';

export class Import {
    constructor() {
        this.selectedDataType = 'keywords';
        this.importResults = null;
        this.isUploading = false;
        this.errorMessage = null;
    }

    render() {
        const element = document.createElement('div');
        element.className = 'import-view';

        const projectId = projectStore.getSelectedProjectId();

        element.innerHTML = `
            <div class="header" style="margin-bottom: 20px;">
                <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">OPTIONAL HISTORICAL FALLBACK</div>
                <h1 style="font-size: 24px; font-weight: 700; margin-top: 2px;">Advanced Data Import & File Guidance</h1>
                <p style="color: var(--text-secondary); margin-top: 4px; font-size: 13.5px;">Import historical datasets, agency CSV exports, or legacy rank tracking data with client-side inspection & privacy protections.</p>
            </div>
            
            <div style="background: var(--bg-subtle); border-left: 4px solid var(--primary); padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <div style="font-size: 18px; line-height: 1;">ℹ️</div>
                    <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">
                        <strong style="color: var(--text-primary);">Website crawling is the primary source of truth.</strong> Real website HTML, titles, headings, and internal link graphs are analyzed directly from crawls. CSV import is an optional fallback for historical data.
                    </div>
                </div>
            </div>

            <!-- DATASET SELECTOR TABS -->
            <div style="display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; flex-wrap: wrap;">
                <button class="btn ${this.selectedDataType === 'keywords' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="keywords">Keywords CSV</button>
                <button class="btn ${this.selectedDataType === 'rankings' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="rankings">Rankings CSV</button>
                <button class="btn ${this.selectedDataType === 'backlinks' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="backlinks">Backlinks CSV</button>
                <button class="btn ${this.selectedDataType === 'competitors' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="competitors">Competitors CSV</button>
            </div>
            
            ${this.errorMessage ? `
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px;">
                    <strong>Import Error:</strong> ${this.errorMessage}
                </div>
            ` : ''}

            <div id="import-active-container">
                ${this.importResults ? this.renderResultsHTML() : ''}
            </div>

            <div class="card" style="margin-top: 32px; padding: 24px;">
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">Recent Dataset Imports</h3>
                <div id="import-history-list" style="color: var(--text-secondary); font-size: 13px;">
                    Loading import history...
                </div>
            </div>
        `;

        this.attachTabEvents(element);
        this.renderGuidanceContainer(element);
        this.loadImportHistory(element, projectId);

        return element;
    }

    attachTabEvents(element) {
        element.querySelectorAll('.btn-import-tab').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const dataType = e.target.getAttribute('data-type');
                if (dataType && this.selectedDataType !== dataType) {
                    this.selectedDataType = dataType;
                    this.importResults = null;
                    this.errorMessage = null;
                    this.reRender();
                }
            });
        });
    }

    renderGuidanceContainer(element) {
        const activeContainer = element.querySelector('#import-active-container');
        if (!activeContainer || this.importResults) return;

        const guidanceComp = new UploadGuidanceComponent(this.selectedDataType, (file) => {
            this.handleFileSelected(file);
        });

        activeContainer.appendChild(guidanceComp.render());
    }

    handleFileSelected(file) {
        const guidance = getUploadGuidance(this.selectedDataType);
        FileInspectorModal.inspectFile(
            file,
            guidance,
            () => this.executeUpload(file),
            () => console.log('File import cancelled')
        );
    }

    async executeUpload(file) {
        await projectStore.ensureInitialized();
        const activeProjectId = projectStore.getSelectedProjectId();
        if (!activeProjectId) {
            this.errorMessage = 'No active project selected. Please select a project before uploading data.';
            this.reRender();
            return;
        }

        this.isUploading = true;
        this.errorMessage = null;
        this.reRender();

        const formData = new FormData();
        formData.append('data_type', this.selectedDataType);
        formData.append('file', file);

        try {
            const token = localStorage.getItem('jwt_token');
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(`${getApiBaseUrl()}/api/projects/${activeProjectId}/imports/upload`, {
                method: 'POST',
                headers: headers,
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Server returned status ${response.status}`);
            }

            const data = await response.json();
            this.importResults = data;
        } catch (err) {
            this.errorMessage = err.message || 'Failed to upload file.';
        } finally {
            this.isUploading = false;
            this.reRender();
        }
    }

    renderResultsHTML() {
        const res = this.importResults;
        const total = (res.successful_records || 0) + (res.error_records || 0);

        return `
            <div class="card" style="padding: 24px; max-width: 800px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 16px;">
                    <div>
                        <h3 style="font-size: 18px; font-weight: 600;">Import Diagnostics & Provenance Report</h3>
                        <p style="color: var(--text-secondary); font-size: 13px; margin-top: 2px;">Dataset ID: ${res.dataset_id || 'N/A'} | Source: <strong>Imported CSV File</strong></p>
                    </div>
                    <span class="badge" style="padding: 6px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; background: ${res.error_records === 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(234, 179, 8, 0.1)'}; color: ${res.error_records === 0 ? '#22c55e' : '#eab308'};">
                        Status: ${res.status || 'SUCCESS'}
                    </span>
                </div>

                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
                    <div style="background: var(--bg-tertiary, #f8fafc); padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 700;">${total}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Total Rows Inspected</div>
                    </div>
                    <div style="background: rgba(34, 197, 94, 0.05); padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 700; color: #22c55e;">${res.successful_records || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Successfully Imported</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.05); padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 700; color: #ef4444;">${res.error_records || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Rows Skipped / Errors</div>
                    </div>
                </div>

                ${res.error_details && res.error_details.length > 0 ? `
                    <div style="margin-bottom: 24px;">
                        <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 10px; color: #ef4444;">Row-Level Errors & Explicit Diagnostics</h4>
                        <div style="max-height: 200px; overflow-y: auto; background: var(--bg-tertiary, #f8fafc); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px;">
                            ${res.error_details.map(e => `
                                <div style="font-size: 12px; padding: 6px 0; border-bottom: 1px solid rgba(0,0,0,0.05);">
                                    <strong style="color: #ef4444;">Row ${e.row}:</strong> ${e.message}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <button class="btn btn-primary" id="btn-reset-import">Import Another Dataset</button>
            </div>
        `;
    }

    reRender() {
        const root = document.getElementById('main-content');
        if (root) {
            root.innerHTML = '';
            root.appendChild(this.render());
        }
    }

    async loadImportHistory(element, projectId) {
        const historyContainer = element.querySelector('#import-history-list');
        if (!historyContainer || !projectId) {
            if (historyContainer) historyContainer.innerHTML = 'No project selected.';
            return;
        }

        try {
            const token = localStorage.getItem('jwt_token');
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch(`${getApiBaseUrl()}/api/projects/${projectId}/imports`, { headers });
            if (!res.ok) throw new Error('Failed to fetch history');

            const datasets = await res.json();
            if (!datasets || datasets.length === 0) {
                historyContainer.innerHTML = 'No dataset imports recorded for this project yet.';
                return;
            }

            historyContainer.innerHTML = `
                <table style="width: 100%; border-collapse: collapse; margin-top: 8px;">
                    <thead>
                        <tr style="text-align: left; border-bottom: 1px solid var(--border-color); color: var(--text-secondary);">
                            <th style="padding: 8px 0;">Filename</th>
                            <th style="padding: 8px;">Type</th>
                            <th style="padding: 8px;">Records</th>
                            <th style="padding: 8px;">Provenance</th>
                            <th style="padding: 8px;">Status</th>
                            <th style="padding: 8px; text-align: right;">Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${datasets.map(d => `
                            <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);">
                                <td style="padding: 10px 0; font-weight: 500;">${d.filename || 'Import'}</td>
                                <td style="padding: 10px;"><span class="badge" style="text-transform: capitalize;">${d.data_type}</span></td>
                                <td style="padding: 10px;">${d.record_count || 0}</td>
                                <td style="padding: 10px; font-size: 12px; color: var(--text-secondary);">Imported CSV</td>
                                <td style="padding: 10px;"><span style="color: ${d.status === 'SUCCESS' ? '#22c55e' : '#eab308'}; font-weight: 600;">${d.status}</span></td>
                                <td style="padding: 10px; text-align: right; color: var(--text-secondary);">${d.imported_at ? new Date(d.imported_at).toLocaleDateString() : 'Recent'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
        } catch (err) {
            historyContainer.innerHTML = 'Could not load import history.';
        }
    }
}
