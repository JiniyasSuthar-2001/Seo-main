import { projectStore } from '../core/projectStore.js';
import { crawlDataService } from '../services/crawlDataService.js';
import { renderFeatureErrorState } from '../components/ErrorState.js';

export class CrawlData {
    constructor() {
        this.element = document.createElement('div');
        this.element.className = 'crawl-data-view';
        
        this.activeTab = 'internal';
        this.selectedCrawlId = null;
        this.searchQuery = '';
        this.filterField = '';
        this.filterValue = '';
        this.sortBy = null;
        this.sortDir = 'asc';
        this.currentPage = 1;
        this.pageSize = 20;

        this.crawls = [];
        this.currentData = null;
        this.isLoading = false;

        this.TABS = [
            { id: 'internal', label: 'Internal' },
            { id: 'response-codes', label: 'Response Codes' },
            { id: 'titles', label: 'Page Titles' },
            { id: 'meta-descriptions', label: 'Meta Descriptions' },
            { id: 'h1', label: 'H1' },
            { id: 'h2', label: 'H2' },
            { id: 'images', label: 'Images' },
            { id: 'canonicals', label: 'Canonicals' },
            { id: 'directives', label: 'Directives' },
            { id: 'hreflang', label: 'Hreflang' },
            { id: 'structured-data', label: 'Structured Data' },
            { id: 'redirects', label: 'Redirects' },
            { id: 'internal-links', label: 'Internal Links' },
            { id: 'external-links', label: 'External Links' },
            { id: 'broken-links', label: 'Broken Links' },
            { id: 'issues', label: 'Issues' }
        ];
    }

    render() {
        this.element.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; flex-wrap: wrap; gap: 16px;">
                <div>
                    <h1 style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">Crawl Data Explorer</h1>
                    <p style="color: var(--text-secondary); margin: 0; font-size: 13.5px;">Structured, evidence-based crawl dataset and granular spreadsheet exports.</p>
                </div>
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <div id="crawl-selector-container" style="display: inline-flex; align-items: center; gap: 8px;">
                        <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Crawl Snapshot:</span>
                        <select id="select-crawl-snapshot" class="input" style="font-size: 12.5px; padding: 6px 10px; border-radius: 6px; background: var(--bg-card); color: var(--text-primary); border: 1px solid var(--border); min-width: 180px;">
                            <option value="">Latest Completed Crawl</option>
                        </select>
                    </div>
                    <button class="btn btn-secondary btn-sm" id="btn-export-tab-csv" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Export Tab CSV
                    </button>
                    <button class="btn btn-primary btn-sm" id="btn-export-crawl-xlsx" style="display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                        Export All Crawl XLSX
                    </button>
                </div>
            </div>

            <!-- TABS SCROLLER -->
            <div style="border-bottom: 1px solid var(--border); margin-bottom: 20px; overflow-x: auto; white-space: nowrap; -webkit-overflow-scrolling: touch;">
                <div style="display: inline-flex; gap: 4px; padding-bottom: 2px;" id="crawl-tabs-nav">
                    ${this.TABS.map(t => `
                        <button type="button" class="tab-btn ${t.id === this.activeTab ? 'active' : ''}" data-tab="${t.id}" style="
                            padding: 8px 14px; font-size: 13px; font-weight: 600; border: none; background: ${t.id === this.activeTab ? 'var(--bg-card)' : 'transparent'};
                            color: ${t.id === this.activeTab ? 'var(--primary, #3b82f6)' : 'var(--text-secondary)'}; border-bottom: 2px solid ${t.id === this.activeTab ? 'var(--primary, #3b82f6)' : 'transparent'};
                            cursor: pointer; transition: all 0.15s ease; border-radius: 6px 6px 0 0;
                        ">
                            ${t.label}
                        </button>
                    `).join('')}
                </div>
            </div>

            <!-- TAB DESCRIPTION & SUMMARY CARDS -->
            <div id="crawl-summary-bar" style="margin-bottom: 16px;"></div>

            <!-- CONTROLS & TABLE CONTAINER -->
            <div class="card" style="padding: 20px; background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border);">
                <!-- TOOLBAR (Search & Filters) -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                    <div style="display: flex; gap: 10px; align-items: center; flex: 1; min-width: 260px;">
                        <div style="position: relative; flex: 1; max-width: 360px;">
                            <input type="text" id="crawl-search-input" class="input" placeholder="Search in this tab..." value="${this.escapeHtml(this.searchQuery)}" style="width: 100%; padding: 7px 12px 7px 32px; font-size: 12.5px; border-radius: 6px; background: var(--bg-subtle); border: 1px solid var(--border); color: var(--text-primary);">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        </div>
                        <div id="tab-filters-slot"></div>
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary);" id="crawl-pagination-counter">
                        Loading...
                    </div>
                </div>

                <!-- TABLE CONTENT -->
                <div id="crawl-table-viewport" style="overflow-x: auto; min-height: 240px;">
                    <div style="padding: 40px; text-align: center; color: var(--text-secondary);">Loading crawl data...</div>
                </div>

                <!-- PAGINATION CONTROLS -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); flex-wrap: wrap; gap: 12px;" id="crawl-pagination-controls">
                </div>
            </div>
        `;

        this.bindEvents();
        return this.element;
    }

    async mounted() {
        await projectStore.ensureInitialized();
        const projectId = projectStore.getSelectedProjectId();
        if (!projectId) {
            const vp = this.element.querySelector('#crawl-table-viewport');
            if (vp) vp.innerHTML = `<div style="padding: 40px; text-align: center; color: var(--text-secondary);">Please select a website project.</div>`;
            return;
        }

        // Fetch available crawls list
        try {
            this.crawls = await crawlDataService.getAvailableCrawls(projectId);
            this.renderCrawlSelector();
        } catch (e) {
            this.crawls = [];
        }

        await this.loadCurrentTabData();
    }

    renderCrawlSelector() {
        const select = this.element.querySelector('#select-crawl-snapshot');
        if (!select) return;

        if (!this.crawls || this.crawls.length === 0) {
            select.innerHTML = `<option value="">No completed crawls</option>`;
            select.disabled = true;
            return;
        }

        select.disabled = false;
        select.innerHTML = `
            <option value="">Latest Crawl (${this.crawls[0]?.timestamp || 'Current'})</option>
            ${this.crawls.slice(1).map(c => `
                <option value="${c.crawl_id}" ${c.crawl_id === this.selectedCrawlId ? 'selected' : ''}>
                    ${c.timestamp} (${c.pages_crawled} pages)
                </option>
            `).join('')}
        `;
    }

    async loadCurrentTabData() {
        const projectId = projectStore.getSelectedProjectId();
        if (!projectId) return;

        const vp = this.element.querySelector('#crawl-table-viewport');
        if (vp) vp.innerHTML = `<div style="padding: 40px; text-align: center; color: var(--text-secondary);">Loading ${this.activeTab} dataset...</div>`;

        try {
            const offset = (this.currentPage - 1) * this.pageSize;
            this.currentData = await crawlDataService.getCrawlDataTab(projectId, this.activeTab, {
                crawl_id: this.selectedCrawlId,
                search: this.searchQuery,
                filter_field: this.filterField,
                filter_value: this.filterValue,
                sort_by: this.sortBy,
                sort_dir: this.sortDir,
                limit: this.pageSize,
                offset: offset
            });

            this.renderSummaryBar();
            this.renderTabFilterControls();
            this.renderTableContent();
            this.renderPagination();
        } catch (err) {
            console.error("[CRAWL DATA VIEW ERROR]", err);
            if (vp) {
                vp.innerHTML = `<div style="padding: 40px; text-align: center; color: #ef4444;">Failed to load crawl data (${err.message || 'Server error'}).</div>`;
            }
        }
    }

    renderSummaryBar() {
        const bar = this.element.querySelector('#crawl-summary-bar');
        if (!bar || !this.currentData) return;

        const summary = this.currentData.summary || {};
        const total = summary.total_count || 0;
        const desc = this.currentData.description || '';

        bar.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle); padding: 10px 16px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px; color: var(--text-secondary); flex-wrap: wrap; gap: 10px;">
                <div>
                    <strong style="color: var(--text-primary); font-size: 14px;">${this.escapeHtml(this.currentData.title || this.activeTab)}:</strong>
                    <span style="margin-left: 6px;">${this.escapeHtml(desc)}</span>
                </div>
                <div style="display: flex; gap: 12px; font-weight: 600; font-size: 12.5px;">
                    <span style="color: var(--text-primary);">Total Records: <strong style="color: #3b82f6;">${total.toLocaleString()}</strong></span>
                    ${summary.indexable_count !== undefined ? `<span style="color: var(--text-primary);">Indexable: <strong style="color: #10b981;">${summary.indexable_count}</strong></span>` : ''}
                    ${summary.missing_count !== undefined ? `<span style="color: var(--text-primary);">Missing: <strong style="color: ${summary.missing_count > 0 ? '#ef4444' : '#10b981'};">${summary.missing_count}</strong></span>` : ''}
                    ${summary.duplicate_count !== undefined ? `<span style="color: var(--text-primary);">Duplicates: <strong style="color: ${summary.duplicate_count > 0 ? '#f59e0b' : '#10b981'};">${summary.duplicate_count}</strong></span>` : ''}
                    ${summary.critical_count !== undefined ? `<span style="color: var(--text-primary);">Critical: <strong style="color: #ef4444;">${summary.critical_count}</strong></span>` : ''}
                </div>
            </div>
        `;
    }

    renderTabFilterControls() {
        const slot = this.element.querySelector('#tab-filters-slot');
        if (!slot) return;

        if (this.activeTab === 'response-codes') {
            slot.innerHTML = `
                <select id="filter-select" class="input" style="font-size: 12px; padding: 6px 10px; border-radius: 6px; background: var(--bg-subtle); border: 1px solid var(--border); color: var(--text-primary);">
                    <option value="">All Status Classes</option>
                    <option value="2xx" ${this.filterValue === '2xx' ? 'selected' : ''}>2xx Success</option>
                    <option value="3xx" ${this.filterValue === '3xx' ? 'selected' : ''}>3xx Redirect</option>
                    <option value="4xx" ${this.filterValue === '4xx' ? 'selected' : ''}>4xx Client Error</option>
                    <option value="5xx" ${this.filterValue === '5xx' ? 'selected' : ''}>5xx Server Error</option>
                </select>
            `;
            this.filterField = 'status_class';
        } else if (['titles', 'meta-descriptions', 'h1', 'h2', 'canonicals'].includes(this.activeTab)) {
            slot.innerHTML = `
                <select id="filter-select" class="input" style="font-size: 12px; padding: 6px 10px; border-radius: 6px; background: var(--bg-subtle); border: 1px solid var(--border); color: var(--text-primary);">
                    <option value="">All Pages</option>
                    <option value="Yes" ${this.filterValue === 'Yes' ? 'selected' : ''}>Missing Only</option>
                    <option value="No" ${this.filterValue === 'No' ? 'selected' : ''}>Present Only</option>
                </select>
            `;
            this.filterField = 'missing';
        } else if (this.activeTab === 'issues') {
            slot.innerHTML = `
                <select id="filter-select" class="input" style="font-size: 12px; padding: 6px 10px; border-radius: 6px; background: var(--bg-subtle); border: 1px solid var(--border); color: var(--text-primary);">
                    <option value="">All Severities</option>
                    <option value="Critical" ${this.filterValue === 'Critical' ? 'selected' : ''}>Critical</option>
                    <option value="Warning" ${this.filterValue === 'Warning' ? 'selected' : ''}>Warning</option>
                    <option value="Notice" ${this.filterValue === 'Notice' ? 'selected' : ''}>Notice</option>
                </select>
            `;
            this.filterField = 'severity';
        } else {
            slot.innerHTML = '';
            this.filterField = '';
        }

        const fSel = slot.querySelector('#filter-select');
        if (fSel) {
            fSel.addEventListener('change', (e) => {
                this.filterValue = e.target.value;
                this.currentPage = 1;
                this.loadCurrentTabData();
            });
        }
    }

    renderTableContent() {
        const vp = this.element.querySelector('#crawl-table-viewport');
        if (!vp || !this.currentData) return;

        const items = this.currentData.items || [];
        const columns = this.currentData.columns || [];

        if (items.length === 0) {
            vp.innerHTML = `
                <div style="padding: 48px 24px; text-align: center; color: var(--text-secondary);">
                    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 10px; opacity: 0.5;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                    <div style="font-weight: 600; font-size: 14.5px; color: var(--text-primary); margin-bottom: 4px;">No records found in this dataset</div>
                    <div style="font-size: 12.5px;">${this.searchQuery || this.filterValue ? 'Try clearing your search query or filter.' : 'This crawl did not produce entries for this category.'}</div>
                </div>
            `;
            return;
        }

        vp.innerHTML = `
            <table class="table" style="width: 100%; border-collapse: collapse; font-size: 12px; white-space: nowrap;">
                <thead>
                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border);">
                        ${columns.map(col => `
                            <th style="padding: 10px 12px; text-align: left; font-weight: 700; color: var(--text-secondary); cursor: pointer; user-select: none;" data-sort="${col.key}">
                                ${col.label} ${this.sortBy === col.key ? (this.sortDir === 'asc' ? '▲' : '▼') : ''}
                            </th>
                        `).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${items.map(row => `
                        <tr style="border-bottom: 1px solid var(--border); transition: background 0.1s ease;" onmouseover="this.style.background='var(--bg-subtle)'" onmouseout="this.style.background='transparent'">
                            ${columns.map(col => `
                                <td style="padding: 8px 12px; max-width: 320px; overflow: hidden; text-overflow: ellipsis; vertical-align: middle;">
                                    ${this.renderCellValue(col.key, row[col.key])}
                                </td>
                            `).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;

        // Bind column sorting
        vp.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const key = th.getAttribute('data-sort');
                if (this.sortBy === key) {
                    this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortBy = key;
                    this.sortDir = 'asc';
                }
                this.loadCurrentTabData();
            });
        });
    }

    renderCellValue(key, val) {
        if (val === null || val === undefined || val === '') {
            return `<span style="color: var(--text-tertiary); font-style: italic;">—</span>`;
        }

        const sVal = String(val);

        if (key === 'url' || key === 'final_url' || key === 'destination_url' || key === 'canonical_url' || key === 'affected_url' || key === 'target_url') {
            return `<a href="${this.escapeHtml(sVal)}" target="_blank" rel="noopener noreferrer" style="color: #3b82f6; text-decoration: none;" title="${this.escapeHtml(sVal)}">${this.escapeHtml(sVal)}</a>`;
        }

        if (key === 'status_code') {
            const num = parseInt(sVal, 10);
            if (num >= 200 && num < 300) return `<span class="badge badge-success" style="font-size: 11px; padding: 2px 6px;">${num}</span>`;
            if (num >= 300 && num < 400) return `<span class="badge badge-warning" style="font-size: 11px; padding: 2px 6px;">${num}</span>`;
            if (num >= 400) return `<span class="badge badge-danger" style="font-size: 11px; padding: 2px 6px;">${num}</span>`;
            return `<span style="color: var(--text-tertiary);">${sVal}</span>`;
        }

        if (key === 'status_class') {
            if (sVal === '2xx') return `<span style="color: #10b981; font-weight: 700;">2xx</span>`;
            if (sVal === '3xx') return `<span style="color: #f59e0b; font-weight: 700;">3xx</span>`;
            if (sVal === '4xx' || sVal === '5xx') return `<span style="color: #ef4444; font-weight: 700;">${sVal}</span>`;
        }

        if (key === 'severity') {
            if (sVal === 'Critical') return `<span class="badge badge-danger" style="font-size: 10.5px;">Critical</span>`;
            if (sVal === 'Warning') return `<span class="badge badge-warning" style="font-size: 10.5px;">Warning</span>`;
            return `<span class="badge badge-secondary" style="font-size: 10.5px;">${sVal}</span>`;
        }

        if (sVal === 'Yes') return `<span style="color: #10b981; font-weight: 700;">✓ Yes</span>`;
        if (sVal === 'No') return `<span style="color: #ef4444; font-weight: 600;">✕ No</span>`;

        return this.escapeHtml(sVal);
    }

    renderPagination() {
        const counter = this.element.querySelector('#crawl-pagination-counter');
        const ctrl = this.element.querySelector('#crawl-pagination-controls');
        if (!this.currentData) return;

        const total = this.currentData.total || 0;
        const start = total === 0 ? 0 : (this.currentPage - 1) * this.pageSize + 1;
        const end = Math.min(this.currentPage * this.pageSize, total);
        const totalPages = Math.ceil(total / this.pageSize) || 1;

        if (counter) {
            counter.innerText = `Showing ${start}–${end} of ${total.toLocaleString()} rows`;
        }

        if (ctrl) {
            ctrl.innerHTML = `
                <div style="font-size: 12px; color: var(--text-secondary);">Page ${this.currentPage} of ${totalPages}</div>
                <div style="display: flex; gap: 6px;">
                    <button class="btn btn-secondary btn-sm" id="btn-page-prev" ${this.currentPage <= 1 ? 'disabled' : ''}>Previous</button>
                    <button class="btn btn-secondary btn-sm" id="btn-page-next" ${this.currentPage >= totalPages ? 'disabled' : ''}>Next</button>
                </div>
            `;

            const btnPrev = ctrl.querySelector('#btn-page-prev');
            const btnNext = ctrl.querySelector('#btn-page-next');
            if (btnPrev) btnPrev.addEventListener('click', () => { if (this.currentPage > 1) { this.currentPage--; this.loadCurrentTabData(); } });
            if (btnNext) btnNext.addEventListener('click', () => { if (this.currentPage < totalPages) { this.currentPage++; this.loadCurrentTabData(); } });
        }
    }

    bindEvents() {
        // Tab click
        this.element.addEventListener('click', (e) => {
            const btn = e.target.closest('.tab-btn[data-tab]');
            if (btn) {
                const targetTab = btn.getAttribute('data-tab');
                if (targetTab !== this.activeTab) {
                    this.activeTab = targetTab;
                    this.currentPage = 1;
                    this.searchQuery = '';
                    this.filterValue = '';
                    this.sortBy = null;
                    
                    this.element.querySelectorAll('.tab-btn').forEach(b => {
                        const isA = b.getAttribute('data-tab') === this.activeTab;
                        b.classList.toggle('active', isA);
                        b.style.color = isA ? 'var(--primary, #3b82f6)' : 'var(--text-secondary)';
                        b.style.borderBottomColor = isA ? 'var(--primary, #3b82f6)' : 'transparent';
                        b.style.background = isA ? 'var(--bg-card)' : 'transparent';
                    });

                    const sInput = this.element.querySelector('#crawl-search-input');
                    if (sInput) sInput.value = '';

                    this.loadCurrentTabData();
                }
            }
        });

        // Search input with debounce
        let debounceTimer;
        this.element.addEventListener('input', (e) => {
            if (e.target && e.target.id === 'crawl-search-input') {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.searchQuery = e.target.value.trim();
                    this.currentPage = 1;
                    this.loadCurrentTabData();
                }, 300);
            }
        });

        // Crawl snapshot selector
        this.element.addEventListener('change', (e) => {
            if (e.target && e.target.id === 'select-crawl-snapshot') {
                this.selectedCrawlId = e.target.value || null;
                this.currentPage = 1;
                this.loadCurrentTabData();
            }
        });

        // Export Tab CSV
        const btnCsv = this.element.querySelector('#btn-export-tab-csv');
        if (btnCsv) {
            btnCsv.addEventListener('click', async () => {
                const projectId = projectStore.getSelectedProjectId();
                if (!projectId) return;
                btnCsv.disabled = true;
                btnCsv.innerText = 'Downloading CSV...';
                try {
                    const url = crawlDataService.getTabCsvExportUrl(projectId, this.activeTab, this.selectedCrawlId);
                    await crawlDataService.downloadFile(url, `${this.activeTab}.csv`);
                } catch (err) {
                    alert(`CSV export failed: ${err.message}`);
                } finally {
                    btnCsv.disabled = false;
                    btnCsv.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                        Export Tab CSV
                    `;
                }
            });
        }

        // Export All Crawl XLSX
        const btnXlsx = this.element.querySelector('#btn-export-crawl-xlsx');
        if (btnXlsx) {
            btnXlsx.addEventListener('click', async () => {
                const projectId = projectStore.getSelectedProjectId();
                if (!projectId) return;
                btnXlsx.disabled = true;
                btnXlsx.innerText = 'Building Workbook (.xlsx)...';
                try {
                    const url = crawlDataService.getCrawlXlsxExportUrl(projectId, this.selectedCrawlId);
                    await crawlDataService.downloadFile(url, `SEO_Crawl_Data.xlsx`);
                } catch (err) {
                    alert(`XLSX export failed: ${err.message}`);
                } finally {
                    btnXlsx.disabled = false;
                    btnXlsx.innerHTML = `
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                        Export All Crawl XLSX
                    `;
                }
            });
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
