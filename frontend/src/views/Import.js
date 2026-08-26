import { projectStore } from '../core/projectStore.js';
import { getApiBaseUrl } from '../config/api.js';
import { getUploadGuidance } from '../config/uploadGuidance.js';
import { UploadGuidanceComponent } from '../components/UploadGuidanceComponent.js';
import { FileInspectorModal } from '../components/FileInspectorModal.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';

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
                <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Import Data</h1>
                <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Import historical datasets, CSV exports, or ranking data with step-by-step guidance.</p>
            </div>
            
            <div style="background: var(--bg-subtle); border-left: 4px solid var(--primary); padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <div style="font-size: 18px; line-height: 1;">💡</div>
                    <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">
                        <strong style="color: var(--text-primary);">Website scanning is the main source of truth.</strong> Real website HTML, page titles, headings, and internal links are analyzed directly from website scans. Spreadsheet import is an optional feature for historical data.
                    </div>
                </div>
            </div>

            <!-- DATASET SELECTOR TABS -->
            <div style="display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px; flex-wrap: wrap;">
                <button class="btn ${this.selectedDataType === 'keywords' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="keywords">Keywords</button>
                <button class="btn ${this.selectedDataType === 'rankings' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="rankings">Search Rankings</button>
                <button class="btn ${this.selectedDataType === 'backlinks' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="backlinks">Links</button>
                <button class="btn ${this.selectedDataType === 'competitors' ? 'btn-primary' : 'btn-secondary'} btn-sm btn-import-tab" data-type="competitors">Competitors</button>
            </div>
            
            ${this.errorMessage ? `
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; font-size: 14px;">
                    <strong>Import Error:</strong> ${this.escapeHtml(this.errorMessage)}
                </div>
            ` : ''}

            <div id="import-active-container">
                ${this.importResults ? this.renderResultsHTML() : ''}
            </div>

            <div class="card" style="margin-top: 32px; padding: 24px;">
                <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">Recent Data Imports</h3>
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
            () => {}
        );
    }

    async executeUpload(file) {
        const projectId = projectStore.getSelectedProjectId();
        if (!projectId) {
            alert('Please select a website project first.');
            return;
        }

        this.isUploading = true;
        this.errorMessage = null;
        this.reRender();

        const formData = new FormData();
        formData.append('file', file);

        try {
            const apiBase = getApiBaseUrl();
            const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const response = await fetch(`${apiBase}/api/projects/${projectId}/import/${this.selectedDataType}`, {
                method: 'POST',
                headers: headers,
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Import failed with status ${response.status}`);
            }

            const data = await response.json();
            this.importResults = data;

        } catch (err) {
            this.errorMessage = err.message || 'Data import failed.';
        } finally {
            this.isUploading = false;
            this.reRender();
        }
    }

    renderResultsHTML() {
        const res = this.importResults || {};
        return `
            <div class="card" style="padding: 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--success);">✓ Data Import Successful</h3>
                    <button class="btn btn-secondary btn-sm" id="btn-import-another">Import Another File</button>
                </div>
                <div style="font-size: 13.5px; color: var(--text-secondary); margin-bottom: 12px;">
                    Rows Imported: <strong>${res.imported_count || res.count || 0}</strong>
                </div>
            </div>
        `;
    }

    async loadImportHistory(element, projectId) {
        const historyContainer = element.querySelector('#import-history-list');
        if (!historyContainer || !projectId) return;

        try {
            const apiBase = getApiBaseUrl();
            const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch(`${apiBase}/api/projects/${projectId}/import/history`, { headers });
            if (!res.ok) throw new Error('Failed to load history');
            const history = await res.json();

            if (!Array.isArray(history) || history.length === 0) {
                historyContainer.innerHTML = 'No previous file imports recorded for this website.';
                return;
            }

            const rows = history.map(item => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 8px 12px; font-weight: 600;">${this.escapeHtml(item.filename || 'data.csv')}</td>
                    <td style="padding: 8px 12px;">${this.escapeHtml(item.data_type || 'Data')}</td>
                    <td style="padding: 8px 12px;">${item.rows_imported || 0} rows</td>
                    <td style="padding: 8px 12px; color: var(--text-tertiary);">${item.timestamp ? item.timestamp.split('T')[0] : 'Recently'}</td>
                </tr>
            `).join('');

            historyContainer.innerHTML = `
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                    <thead>
                        <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary);">
                            <th style="padding: 8px 12px;">File Name</th>
                            <th style="padding: 8px 12px;">Type</th>
                            <th style="padding: 8px 12px;">Rows</th>
                            <th style="padding: 8px 12px;">Date</th>
                        </tr>
                    </thead>
                    <tbody>${rows}</tbody>
                </table>
            `;
        } catch (e) {
            historyContainer.innerHTML = 'Import history records available upon next file upload.';
        }
    }

    reRender() {
        const root = document.querySelector('.import-view');
        if (root && root.parentNode) {
            const newEl = this.render();
            root.parentNode.replaceChild(newEl, root);
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}
