import { projectStore } from '../stores/projectStore.js';
import { getApiBaseUrl } from '../config/api.js';

export class Import {
    constructor() {
        this.selectedDataType = null;
        this.importResults = null;
        this.isUploading = false;
        this.errorMessage = null;
    }

    render() {
        const element = document.createElement('div');
        element.className = 'import-view';

        const projectId = projectStore.getSelectedProjectId();

        element.innerHTML = `
            <div class="header" style="margin-bottom: 24px;">
                <h1 style="font-size: 24px; font-weight: 600;">Data Import Workspace</h1>
                <p style="color: var(--text-secondary); margin-top: 4px;">Upload external CSV datasets to populate keywords, rankings, backlinks, and SERP metrics.</p>
            </div>
            
            ${this.errorMessage ? `
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px;">
                    <strong>Import Error:</strong> ${this.errorMessage}
                </div>
            ` : ''}

            ${this.importResults ? this.renderResultsHTML() : this.renderUploadCardsHTML()}

            <div class="card" style="margin-top: 32px; padding: 24px;">
                <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">Recent Dataset Imports</h3>
                <div id="import-history-list" style="color: var(--text-secondary); font-size: 13px;">
                    Loading import history...
                </div>
            </div>
        `;

        this.attachEvents(element, projectId);
        this.loadImportHistory(element, projectId);

        return element;
    }

    renderUploadCardsHTML() {
        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; max-width: 960px;">
                <input type="file" id="keywords-file-input" accept=".csv" style="display: none;" />
                <input type="file" id="rankings-file-input" accept=".csv" style="display: none;" />
                <input type="file" id="backlinks-file-input" accept=".csv" style="display: none;" />

                <div class="card" style="padding: 24px;">
                    <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Keywords CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; line-height: 1.5;">Import target keyword lists, search volume, CPC, difficulty, and target URLs.</p>
                    <button class="btn btn-secondary" id="btn-upload-keywords" style="width: 100%;" ${this.isUploading ? 'disabled' : ''}>
                        ${this.isUploading && this.selectedDataType === 'keywords' ? 'Importing Keywords...' : 'Upload Keywords CSV'}
                    </button>
                </div>

                <div class="card" style="padding: 24px;">
                    <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Rankings CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; line-height: 1.5;">Import position tracking records, search engine, country, device, and rank history.</p>
                    <button class="btn btn-secondary" id="btn-upload-rankings" style="width: 100%;" ${this.isUploading ? 'disabled' : ''}>
                        ${this.isUploading && this.selectedDataType === 'rankings' ? 'Importing Rankings...' : 'Upload Rankings CSV'}
                    </button>
                </div>

                <div class="card" style="padding: 24px;">
                    <div style="width: 40px; height: 40px; border-radius: 8px; background: var(--primary-light); color: var(--primary); display: flex; align-items: center; justify-content: center; margin-bottom: 16px;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">Backlinks CSV</h3>
                    <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 20px; line-height: 1.5;">Import referring domains, external source URLs, anchor text, and link status.</p>
                    <button class="btn btn-secondary" id="btn-upload-backlinks" style="width: 100%;" ${this.isUploading ? 'disabled' : ''}>
                        ${this.isUploading && this.selectedDataType === 'backlinks' ? 'Importing Backlinks...' : 'Upload Backlinks CSV'}
                    </button>
                </div>
            </div>
        `;
    }

    renderResultsHTML() {
        const res = this.importResults;
        const total = (res.successful_records || 0) + (res.error_records || 0);

        return `
            <div class="card" style="padding: 24px; max-width: 800px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 16px;">
                    <div>
                        <h3 style="font-size: 18px; font-weight: 600;">Import Report</h3>
                        <p style="color: var(--text-secondary); font-size: 13px; margin-top: 2px;">Dataset ID: ${res.dataset_id || 'N/A'}</p>
                    </div>
                    <span class="badge" style="padding: 6px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; background: ${res.error_records === 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(234, 179, 8, 0.1)'}; color: ${res.error_records === 0 ? '#22c55e' : '#eab308'};">
                        Status: ${res.status || 'SUCCESS'}
                    </span>
                </div>

                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
                    <div style="background: var(--bg-tertiary, #f8fafc); padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 700;">${total}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Total Rows</div>
                    </div>
                    <div style="background: rgba(34, 197, 94, 0.05); padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 700; color: #22c55e;">${res.successful_records || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Imported</div>
                    </div>
                    <div style="background: rgba(239, 68, 68, 0.05); padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 700; color: #ef4444;">${res.error_records || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Errors / Skipped</div>
                    </div>
                    <div style="background: var(--bg-tertiary, #f8fafc); padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 20px; font-weight: 700;">${res.additional_errors_count || 0}</div>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">More Errors</div>
                    </div>
                </div>

                ${res.error_details && res.error_details.length > 0 ? `
                    <div style="margin-bottom: 24px;">
                        <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 10px; color: #ef4444;">Row-Level Errors & Diagnostics</h4>
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

    attachEvents(element, projectId) {
        const btnKw = element.querySelector('#btn-upload-keywords');
        const btnRank = element.querySelector('#btn-upload-rankings');
        const btnBack = element.querySelector('#btn-upload-backlinks');

        const inputKw = element.querySelector('#keywords-file-input');
        const inputRank = element.querySelector('#rankings-file-input');
        const inputBack = element.querySelector('#backlinks-file-input');

        if (btnKw && inputKw) {
            btnKw.addEventListener('click', () => inputKw.click());
            inputKw.addEventListener('change', (e) => this.handleFileSelected(e, 'keywords', projectId));
        }

        if (btnRank && inputRank) {
            btnRank.addEventListener('click', () => inputRank.click());
            inputRank.addEventListener('change', (e) => this.handleFileSelected(e, 'rankings', projectId));
        }

        if (btnBack && inputBack) {
            btnBack.addEventListener('click', () => inputBack.click());
            inputBack.addEventListener('change', (e) => this.handleFileSelected(e, 'backlinks', projectId));
        }

        const btnReset = element.querySelector('#btn-reset-import');
        if (btnReset) {
            btnReset.addEventListener('click', () => {
                this.importResults = null;
                this.errorMessage = null;
                window.location.hash = '#/import';
            });
        }
    }

    async handleFileSelected(event, dataType, projectId) {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.csv')) {
            this.errorMessage = 'Invalid file format. Only .csv files are supported.';
            this.reRender();
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            this.errorMessage = 'File size exceeds maximum allowed limit of 10MB.';
            this.reRender();
            return;
        }

        if (!projectId) {
            this.errorMessage = 'No active project selected. Please select a project before uploading data.';
            this.reRender();
            return;
        }

        this.isUploading = true;
        this.selectedDataType = dataType;
        this.errorMessage = null;
        this.reRender();

        const formData = new FormData();
        formData.append('data_type', dataType);
        formData.append('file', file);

        try {
            const token = localStorage.getItem('jwt_token');
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(`${getApiBaseUrl()}/api/projects/${projectId}/imports/upload`, {
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
            this.errorMessage = err.message || 'Failed to upload CSV file.';
        } finally {
            this.isUploading = false;
            this.reRender();
        }
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
                                <td style="padding: 10px;"><span style="color: ${d.status === 'SUCCESS' ? '#22c55e' : '#eab308'};">${d.status}</span></td>
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
