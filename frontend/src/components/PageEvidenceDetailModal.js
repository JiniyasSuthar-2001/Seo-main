import { AISuggestModal } from './AISuggestModal.js';

export class PageEvidenceDetailModal {
    static activeModal = null;

    static show({ tabId = '', rowData = {}, projectId = '' } = {}) {
        this.close();
        const modal = new PageEvidenceDetailModal(tabId, rowData, projectId);
        modal.render();
        this.activeModal = modal;
    }

    static close() {
        if (this.activeModal) {
            this.activeModal.destroy();
            this.activeModal = null;
        }
    }

    constructor(tabId, rowData, projectId) {
        this.tabId = tabId;
        this.rowData = rowData || {};
        this.projectId = projectId;
        this.element = null;
        this.handleKeyDown = this.handleKeyDown.bind(this);
    }

    render() {
        this.element = document.createElement('div');
        this.element.className = 'modal-backdrop';
        this.element.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(6px);
            display: flex; align-items: center; justify-content: center;
            z-index: 9999; padding: 20px; animation: fadeIn 0.2s ease;
        `;

        const pageUrl = this.rowData.url || this.rowData.page_url || this.rowData.source_url || '';
        const statusCode = this.rowData.status_code || '200';
        const indexability = this.rowData.indexability || 'Indexable';

        let title = 'Page Details & Evidence';
        let currentValue = '';
        let taskType = 'meta_title';
        let issueSummary = '';
        let detailsHtml = '';

        if (this.tabId === 'titles') {
            title = 'Page Title Tag Evidence';
            currentValue = this.rowData.title || '';
            taskType = 'meta_title';
            const len = this.rowData.title_length || currentValue.length;
            const isMissing = this.rowData.missing === 'Yes' || !currentValue;
            const isDuplicate = this.rowData.duplicate === 'Yes';
            const isShort = this.rowData.too_short === 'Yes';
            const isLong = this.rowData.too_long === 'Yes';

            issueSummary = isMissing ? 'Missing Title Tag' : (isDuplicate ? 'Duplicate Title Tag' : (isShort ? 'Title Too Short (<30 chars)' : (isLong ? 'Title Too Long (>60 chars)' : 'Optimized Title')));

            detailsHtml = `
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #64748b); text-transform: uppercase; margin-bottom: 4px;">Current Title Content</div>
                        <div style="background: #0f172a; border: 1px solid var(--border, #334155); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 13px; color: ${currentValue ? '#e2e8f0' : '#f87171'};">
                            ${currentValue ? this.escapeHtml(currentValue) : '<em>(No Title Tag Present)</em>'}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; font-size: 12px;">
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">Character Length:</span> <strong>${len} characters</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">Missing Flag:</span> <strong style="color: ${isMissing ? '#ef4444' : '#10b981'};">${isMissing ? 'Yes' : 'No'}</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">Duplicate Flag:</span> <strong style="color: ${isDuplicate ? '#f59e0b' : '#10b981'};">${isDuplicate ? 'Yes' : 'No'}</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">SERP Pixel Range:</span> <strong>${len >= 30 && len <= 60 ? '✓ Optimal (30-60)' : '⚠️ Suboptimal'}</strong>
                        </div>
                    </div>
                </div>
            `;
        } else if (this.tabId === 'meta-descriptions') {
            title = 'Meta Description Tag Evidence';
            currentValue = this.rowData.meta_description || '';
            taskType = 'meta_description';
            const len = this.rowData.description_length || currentValue.length;
            const isMissing = this.rowData.missing === 'Yes' || !currentValue;
            const isDuplicate = this.rowData.duplicate === 'Yes';

            issueSummary = isMissing ? 'Missing Meta Description' : (isDuplicate ? 'Duplicate Meta Description' : 'Meta Description Audit');

            detailsHtml = `
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #64748b); text-transform: uppercase; margin-bottom: 4px;">Current Meta Description</div>
                        <div style="background: #0f172a; border: 1px solid var(--border, #334155); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 12.5px; color: ${currentValue ? '#e2e8f0' : '#f87171'}; line-height: 1.5;">
                            ${currentValue ? this.escapeHtml(currentValue) : '<em>(No Meta Description Present)</em>'}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; font-size: 12px;">
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">Character Length:</span> <strong>${len} characters</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">Missing Flag:</span> <strong style="color: ${isMissing ? '#ef4444' : '#10b981'};">${isMissing ? 'Yes' : 'No'}</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">Duplicate Flag:</span> <strong style="color: ${isDuplicate ? '#f59e0b' : '#10b981'};">${isDuplicate ? 'Yes' : 'No'}</strong>
                        </div>
                    </div>
                </div>
            `;
        } else if (this.tabId === 'h1') {
            title = 'H1 Heading Tag Evidence';
            currentValue = this.rowData.h1 || '';
            taskType = 'h1';
            const count = this.rowData.h1_count || (currentValue ? 1 : 0);
            const isMissing = this.rowData.missing === 'Yes' || count === 0;

            issueSummary = isMissing ? 'Missing H1 Heading' : (count > 1 ? 'Multiple H1 Headings Detected' : 'H1 Heading Audit');

            detailsHtml = `
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #64748b); text-transform: uppercase; margin-bottom: 4px;">Primary H1 Tag Content</div>
                        <div style="background: #0f172a; border: 1px solid var(--border, #334155); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 13px; color: ${currentValue ? '#e2e8f0' : '#f87171'};">
                            ${currentValue ? this.escapeHtml(currentValue) : '<em>(No H1 Tag Present)</em>'}
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; font-size: 12px;">
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">H1 Count:</span> <strong style="color: ${count === 1 ? '#10b981' : '#f87171'};">${count}</strong>
                        </div>
                        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; border: 1px solid var(--border, #334155);">
                            <span style="color: var(--text-secondary, #94a3b8);">Missing Flag:</span> <strong style="color: ${isMissing ? '#ef4444' : '#10b981'};">${isMissing ? 'Yes' : 'No'}</strong>
                        </div>
                    </div>
                </div>
            `;
        } else {
            title = `${this.tabId.replace('-', ' ').toUpperCase()} Evidence`;
            currentValue = JSON.stringify(this.rowData, null, 2);
            taskType = 'content_optimization';
            issueSummary = 'Page Attribute Audit';

            detailsHtml = `
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #64748b); text-transform: uppercase; margin-bottom: 4px;">Raw Page Data Evidence</div>
                    <pre style="background: #0f172a; border: 1px solid var(--border, #334155); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 11.5px; color: #e2e8f0; max-height: 240px; overflow: auto;">${this.escapeHtml(currentValue)}</pre>
                </div>
            `;
        }

        this.element.innerHTML = `
            <div class="modal-dialog" style="
                background: var(--bg-card, #1e293b); color: var(--text-primary, #f8fafc);
                border: 1px solid var(--border, #334155); border-radius: 14px;
                width: 100%; max-width: 680px; display: flex; flex-direction: column;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4); overflow: hidden; animation: slideUp 0.25s ease;
            ">
                <!-- HEADER -->
                <div style="padding: 18px 24px; border-bottom: 1px solid var(--border, #334155); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle, rgba(255,255,255,0.02));">
                    <div>
                        <div style="font-size: 16px; font-weight: 700;">${this.escapeHtml(title)}</div>
                        <div style="font-size: 12px; color: var(--text-secondary, #94a3b8); font-family: monospace; word-break: break-all; margin-top: 2px;">
                            ${this.escapeHtml(pageUrl)}
                        </div>
                    </div>
                    <button type="button" class="btn-close-modal" style="background: transparent; border: none; color: var(--text-tertiary, #64748b); font-size: 20px; cursor: pointer; padding: 4px 8px; border-radius: 6px;">✕</button>
                </div>

                <!-- BODY -->
                <div style="padding: 20px 24px; display: flex; flex-direction: column; gap: 16px;">
                    <div style="display: flex; gap: 12px; font-size: 12px; align-items: center;">
                        <span class="badge" style="background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); font-weight: 700; padding: 3px 8px; border-radius: 4px;">
                            HTTP ${statusCode}
                        </span>
                        <span class="badge" style="background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); font-weight: 600; padding: 3px 8px; border-radius: 4px;">
                            ${indexability}
                        </span>
                        <span style="color: var(--text-secondary, #94a3b8);">Status: <strong>${this.escapeHtml(issueSummary)}</strong></span>
                    </div>

                    ${detailsHtml}
                </div>

                <!-- FOOTER -->
                <div style="padding: 16px 24px; border-top: 1px solid var(--border, #334155); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle, rgba(255,255,255,0.02));">
                    <button type="button" class="btn-ai-solve btn btn-primary" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; font-size: 12px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #3b82f6); color: #ffffff; border: none; border-radius: 6px; cursor: pointer;">
                        ✨ Solve with AI
                    </button>
                    <button type="button" class="btn-close-modal btn btn-secondary btn-sm" style="padding: 6px 16px; font-weight: 600;">Close</button>
                </div>
            </div>
        `;

        this.bindEvents(taskType, pageUrl, currentValue, issueSummary);
        document.body.appendChild(this.element);
        document.addEventListener('keydown', this.handleKeyDown);
    }

    bindEvents(taskType, pageUrl, currentValue, issueSummary) {
        const modal = this;

        // Close buttons
        this.element.querySelectorAll('.btn-close-modal').forEach(btn => {
            btn.addEventListener('click', () => PageEvidenceDetailModal.close());
        });

        // Backdrop click
        this.element.addEventListener('click', (e) => {
            if (e.target === modal.element) {
                PageEvidenceDetailModal.close();
            }
        });

        // AI solve button
        const btnAi = this.element.querySelector('.btn-ai-solve');
        if (btnAi) {
            btnAi.addEventListener('click', () => {
                AISuggestModal.show({
                    projectId: modal.projectId,
                    pageUrl: pageUrl,
                    taskType: taskType,
                    currentValue: currentValue,
                    issue: issueSummary
                });
            });
        }
    }

    handleKeyDown(e) {
        if (e.key === 'Escape') {
            PageEvidenceDetailModal.close();
        }
    }

    destroy() {
        document.removeEventListener('keydown', this.handleKeyDown);
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
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
