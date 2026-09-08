import { projectStore } from '../core/projectStore.js';
import { getApiBaseUrl } from '../config/api.js';
import { UploadGuidanceComponent } from '../components/UploadGuidanceComponent.js';
import { FileInspectorModal } from '../components/FileInspectorModal.js';
import { renderBackendOfflineState, renderFeatureErrorState } from '../components/ErrorState.js';
import { Pagination } from '../components/Pagination.js';
import { apiClient } from '../services/apiClient.js';

export class Import {
    constructor() {
        this.selectedDataType = 'keywords';
        this.importResults = null;
        this.isUploading = false;
        this.errorMessage = null;
        this.historyPage = 1;
        this.pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
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
            
            <div class="import-content">
                <!-- Guidance Box -->
                <div id="guidance-container" style="margin-bottom: 24px;"></div>

                <!-- Main Import Card -->
                <div class="card" style="padding: 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border); margin-bottom: 24px;">
                    <h2 style="font-size: 16px; font-weight: 700; margin: 0 0 16px 0; color: var(--text-primary);">Upload File</h2>
                    
                    ${this.errorMessage ? `
                        <div style="padding: 12px 16px; background: rgba(239, 68, 68, 0.1); border: 1px solid var(--danger); border-radius: 8px; color: var(--danger); font-size: 13.5px; margin-bottom: 16px;">
                            ${this.escapeHtml(this.errorMessage)}
                        </div>
                    ` : ''}

                    <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 20px; flex-wrap: wrap;">
                        <label style="font-size: 13.5px; font-weight: 600; color: var(--text-primary);">Data Type:</label>
                        <select id="import-data-type" style="padding: 8px 12px; background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 6px; color: var(--text-primary); font-size: 13.5px;">
                            <option value="keywords" ${this.selectedDataType === 'keywords' ? 'selected' : ''}>Keywords</option>
                            <option value="rankings" ${this.selectedDataType === 'rankings' ? 'selected' : ''}>Search Rankings</option>
                            <option value="backlinks" ${this.selectedDataType === 'backlinks' ? 'selected' : ''}>Links</option>
                            <option value="competitors" ${this.selectedDataType === 'competitors' ? 'selected' : ''}>Competitors</option>
                        </select>
                    </div>

                    <div id="dropzone" style="border: 2px dashed var(--border); border-radius: 10px; padding: 36px 20px; text-align: center; background: var(--bg-secondary); cursor: pointer; transition: all 0.2s ease;">
                        <input type="file" id="file-input" accept=".csv,.xlsx,.xls,.json" style="display: none;" />
                        <div style="font-size: 32px; margin-bottom: 12px; color: var(--text-tertiary);">📁</div>
                        <div style="font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">
                            Click to upload or drag & drop CSV / Excel file
                        </div>
                        <div style="font-size: 12.5px; color: var(--text-tertiary);">
                            Supported formats: .csv, .xlsx, .xls, .json (max 10MB)
                        </div>
                    </div>
                </div>

                <!-- Results / History Container -->
                <div id="results-container" style="margin-bottom: 24px;">
                    ${this.importResults ? this.renderResultsHTML() : ''}
                </div>

                <!-- Import History Card -->
                <div class="card" style="padding: 24px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                    <h2 style="font-size: 16px; font-weight: 700; margin: 0 0 16px 0; color: var(--text-primary);">Recent Imports</h2>
                    <div id="import-history-list" style="font-size: 13.5px; color: var(--text-secondary);">
                        <div style="padding: 20px; text-align: center;">Loading import history...</div>
                    </div>
                    <div id="import-history-pagination" style="margin-top: 16px;"></div>
                </div>
            </div>
        `;

        this.bindEvents(element, projectId);
        this.renderGuidance(element);
        this.loadImportHistory(element, projectId);

        return element;
    }

    bindEvents(element, projectId) {
        const dropzone = element.querySelector('#dropzone');
        const fileInput = element.querySelector('#file-input');
        const dataTypeSelect = element.querySelector('#import-data-type');

        if (dataTypeSelect) {
            dataTypeSelect.addEventListener('change', (e) => {
                this.selectedDataType = e.target.value;
                this.renderGuidance(element);
            });
        }

        if (dropzone && fileInput) {
            dropzone.addEventListener('click', () => fileInput.click());
            dropzone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropzone.style.borderColor = 'var(--accent-primary)';
                dropzone.style.background = 'var(--bg-hover)';
            });
            dropzone.addEventListener('dragleave', () => {
                dropzone.style.borderColor = 'var(--border)';
                dropzone.style.background = 'var(--bg-secondary)';
            });
            dropzone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropzone.style.borderColor = 'var(--border)';
                dropzone.style.background = 'var(--bg-secondary)';
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    this.handleFileSelected(e.dataTransfer.files[0]);
                }
            });

            fileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    this.handleFileSelected(e.target.files[0]);
                }
            });
        }

        const btnImportAnother = element.querySelector('#btn-import-another');
        if (btnImportAnother) {
            btnImportAnother.addEventListener('click', () => {
                this.importResults = null;
                this.reRender();
            });
        }
    }

    renderGuidance(element) {
        const container = element.querySelector('#guidance-container');
        if (!container) return;
        container.innerHTML = '';
        const guidanceComponent = new UploadGuidanceComponent(
            this.selectedDataType,
            (file) => {
                this.handleFileSelected(file);
            }
        );
        container.appendChild(guidanceComponent.render());
    }

    handleFileSelected(file) {
        const modal = new FileInspectorModal({
            file,
            dataType: this.selectedDataType,
            onConfirm: (confirmedFile) => {
                this.executeUpload(confirmedFile);
            }
        });
        modal.open();
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
        formData.append('data_type', this.selectedDataType);

        try {
            const data = await apiClient.upload(`/api/projects/${projectId}/import/upload`, formData);
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
        const paginationContainer = element.querySelector('#import-history-pagination');
        if (!historyContainer || !projectId) return;

        try {
            const history = await apiClient.get(`/api/projects/${projectId}/import/history`);

            if (!Array.isArray(history) || history.length === 0) {
                historyContainer.innerHTML = '<div style="padding: 20px; text-align: center;">No previous file imports recorded for this website.</div>';
                return;
            }

            const paginated = Pagination.paginateArray(history, this.historyPage, this.pageSize);
            this.historyPage = paginated.currentPage;

            const rows = paginated.items.map(item => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 10px 16px; font-weight: 600;">${this.escapeHtml(item.filename || 'data.csv')}</td>
                    <td style="padding: 10px 16px;">${this.escapeHtml(item.data_type || 'Data')}</td>
                    <td style="padding: 10px 16px;">${item.rows_imported || 0} rows</td>
                    <td style="padding: 10px 16px; color: var(--text-tertiary);">${item.timestamp ? item.timestamp.split('T')[0] : 'Recently'}</td>
                </tr>
            `).join('');

            historyContainer.innerHTML = `
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary);">
                                <th style="padding: 10px 16px;">File Name</th>
                                <th style="padding: 10px 16px;">Type</th>
                                <th style="padding: 10px 16px;">Rows</th>
                                <th style="padding: 10px 16px;">Date</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
                <div id="import-pagination-slot"></div>
            `;

            const pageSlot = historyContainer.querySelector('#import-pagination-slot');
            if (pageSlot && history.length > 0) {
                const pag = new Pagination({
                    totalItems: history.length,
                    currentPage: this.historyPage,
                    pageSize: this.pageSize,
                    onPageChange: (newPage) => {
                        this.historyPage = newPage;
                        this.loadImportHistory(element, projectId);
                    }
                });
                pageSlot.appendChild(pag.render());
            }

        } catch (e) {
            historyContainer.innerHTML = '<div style="padding: 20px;">Import history records available upon next file upload.</div>';
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
