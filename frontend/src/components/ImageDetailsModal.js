import { AISuggestModal } from './AISuggestModal.js';

export class ImageDetailsModal {
    static activeModal = null;

    static show({ pageUrl = '', images = [], projectId = '', pageRow = {} } = {}) {
        this.close();

        const modal = new ImageDetailsModal(pageUrl, images, projectId, pageRow);
        modal.render();
        this.activeModal = modal;
    }

    static close() {
        if (this.activeModal) {
            this.activeModal.destroy();
            this.activeModal = null;
        }
    }

    constructor(pageUrl, images, projectId, pageRow) {
        this.pageUrl = pageUrl;
        this.images = Array.isArray(images) ? images : [];
        this.projectId = projectId;
        this.pageRow = pageRow || {};
        this.filter = 'all'; // 'all', 'missing', 'present'

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

        this.updateContent();
        document.body.appendChild(this.element);
        document.addEventListener('keydown', this.handleKeyDown);
    }

    updateContent() {
        const totalCount = this.images.length;
        const missingCount = this.images.filter(img => img.alt_missing || !img.alt_text).length;
        const presentCount = totalCount - missingCount;

        const filteredImages = this.images.filter(img => {
            const isMissing = img.alt_missing || !img.alt_text;
            if (this.filter === 'missing') return isMissing;
            if (this.filter === 'present') return !isMissing;
            return true;
        });

        this.element.innerHTML = `
            <div class="modal-dialog" style="
                background: var(--bg-card, #1e293b); color: var(--text-primary, #f8fafc);
                border: 1px solid var(--border, #334155); border-radius: 14px;
                width: 100%; max-width: 900px; max-height: 85vh; display: flex;
                flex-direction: column; box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                overflow: hidden; animation: slideUp 0.25s ease;
            ">
                <!-- MODAL HEADER -->
                <div style="padding: 18px 24px; border-bottom: 1px solid var(--border, #334155); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle, rgba(255,255,255,0.02));">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span style="font-size: 16px; font-weight: 700;">🖼️ Image Audit Details</span>
                            <span class="badge" style="background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px;">
                                ${totalCount} Total Images
                            </span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary, #94a3b8); font-family: monospace; word-break: break-all;">
                            ${this.escapeHtml(this.pageUrl)}
                        </div>
                    </div>
                    <button type="button" class="btn-close-modal" style="background: transparent; border: none; color: var(--text-tertiary, #64748b); font-size: 20px; cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: color 0.15s;">✕</button>
                </div>

                <!-- METRICS & TOOLBAR -->
                <div style="padding: 14px 24px; border-bottom: 1px solid var(--border, #334155); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; background: rgba(0,0,0,0.1);">
                    <div style="display: flex; gap: 16px; font-size: 12.5px; font-weight: 600;">
                        <span>Total: <strong style="color: #3b82f6;">${totalCount}</strong></span>
                        <span>Alt Present: <strong style="color: #10b981;">${presentCount}</strong></span>
                        <span>Missing Alt: <strong style="color: ${missingCount > 0 ? '#ef4444' : '#10b981'};">${missingCount}</strong></span>
                    </div>

                    <div style="display: flex; gap: 10px; align-items: center;">
                        <select id="img-filter-select" style="font-size: 12px; padding: 5px 10px; border-radius: 6px; background: var(--bg-subtle, #0f172a); color: var(--text-primary, #f8fafc); border: 1px solid var(--border, #334155); cursor: pointer;">
                            <option value="all" ${this.filter === 'all' ? 'selected' : ''}>All Images (${totalCount})</option>
                            <option value="missing" ${this.filter === 'missing' ? 'selected' : ''}>Missing Alt Only (${missingCount})</option>
                            <option value="present" ${this.filter === 'present' ? 'selected' : ''}>Alt Present Only (${presentCount})</option>
                        </select>

                        ${missingCount > 0 ? `
                            <button type="button" class="btn-fix-all-alts" style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 11.5px; font-weight: 700; background: linear-gradient(135deg, #8b5cf6, #3b82f6); color: #ffffff; border: none; border-radius: 6px; cursor: pointer; shadow: 0 2px 6px rgba(139,92,246,0.3);">
                                ✨ Fix All Missing Alts (${missingCount})
                            </button>
                        ` : ''}
                        
                        <button type="button" class="btn-copy-all-urls" style="padding: 6px 10px; font-size: 11.5px; font-weight: 600; background: var(--bg-subtle, #334155); color: var(--text-primary, #f8fafc); border: 1px solid var(--border, #475569); border-radius: 6px; cursor: pointer;">
                            📋 Copy Image URLs
                        </button>
                    </div>
                </div>

                <!-- IMAGE GRID CONTAINER -->
                <div style="padding: 20px 24px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 14px;">
                    ${filteredImages.length === 0 ? `
                        <div style="padding: 40px; text-align: center; color: var(--text-secondary, #94a3b8);">
                            No images match the selected filter.
                        </div>
                    ` : filteredImages.map((img, idx) => {
                        const isMissing = img.alt_missing || !img.alt_text;
                        const imgUrl = img.image_url || img.src || '';
                        const altText = img.alt_text || '';
                        const width = img.width ? `${img.width}px` : 'Auto';
                        const height = img.height ? `${img.height}px` : 'Auto';
                        const loading = img.loading || 'Not specified';

                        return `
                            <div style="display: flex; gap: 16px; background: var(--bg-subtle, rgba(255,255,255,0.03)); border: 1px solid var(--border, #334155); padding: 14px; border-radius: 10px; align-items: flex-start;">
                                <!-- THUMBNAIL -->
                                <div style="width: 80px; height: 80px; min-width: 80px; background: #0f172a; border-radius: 8px; border: 1px solid var(--border, #334155); overflow: hidden; display: flex; align-items: center; justify-content: center; position: relative;">
                                    <img src="${this.escapeHtml(imgUrl)}" alt="${this.escapeHtml(altText)}" 
                                         onerror="this.onerror=null; this.style.display='none'; this.nextElementSibling.style.display='flex';"
                                         style="max-width: 100%; max-height: 100%; object-fit: contain;" />
                                    <div style="display: none; width: 100%; height: 100%; align-items: center; justify-content: center; color: #64748b; font-size: 10px; font-weight: 600; text-align: center; padding: 4px;">
                                        Image Preview Unavailable
                                    </div>
                                </div>

                                <!-- DETAILS -->
                                <div style="flex: 1; display: flex; flex-direction: column; gap: 6px; min-width: 0;">
                                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                                        <a href="${this.escapeHtml(imgUrl)}" target="_blank" rel="noopener noreferrer" 
                                           style="color: #3b82f6; font-family: monospace; font-size: 12px; word-break: break-all; text-decoration: none; font-weight: 600;" 
                                           title="${this.escapeHtml(imgUrl)}">
                                            ${this.escapeHtml(imgUrl)}
                                        </a>
                                        <span class="badge" style="background: ${isMissing ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)'}; color: ${isMissing ? '#f87171' : '#34d399'}; border: 1px solid ${isMissing ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 12px; white-space: nowrap;">
                                            ${isMissing ? '✕ Missing Alt' : '✓ Alt Present'}
                                        </span>
                                    </div>

                                    <!-- ALT TEXT VALUE -->
                                    <div style="font-size: 12px; display: flex; align-items: center; gap: 8px;">
                                        <span style="color: var(--text-secondary, #94a3b8); font-weight: 600;">Alt Text:</span>
                                        ${isMissing ? `
                                            <span style="color: #f87171; font-style: italic;">No alt attribute present</span>
                                        ` : `
                                            <code style="background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #e2e8f0; font-family: monospace; font-size: 11.5px;">${this.escapeHtml(altText)}</code>
                                        `}
                                    </div>

                                    <!-- DIMENSIONS & ATTRIBUTES -->
                                    <div style="display: flex; gap: 14px; font-size: 11px; color: var(--text-tertiary, #64748b); flex-wrap: wrap;">
                                        <span>Dimensions: <strong>${width} × ${height}</strong></span>
                                        <span>Loading: <strong>${this.escapeHtml(loading)}</strong></span>
                                    </div>
                                </div>

                                <!-- ACTION BUTTON -->
                                <div style="display: flex; flex-direction: column; gap: 6px; align-items: flex-end;">
                                    ${isMissing ? `
                                        <button type="button" class="btn-ai-single-image" data-img-url="${this.escapeHtml(imgUrl)}" style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; font-size: 11px; font-weight: 700; background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(59,130,246,0.2)); color: #a78bfa; border: 1px solid rgba(139,92,246,0.4); border-radius: 6px; cursor: pointer; white-space: nowrap;">
                                            ✨ AI Generate Alt
                                        </button>
                                    ` : `
                                        <button type="button" class="btn-ai-single-image" data-img-url="${this.escapeHtml(imgUrl)}" data-current-alt="${this.escapeHtml(altText)}" style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; font-size: 11px; font-weight: 600; background: rgba(255,255,255,0.05); color: var(--text-secondary, #94a3b8); border: 1px solid var(--border, #334155); border-radius: 6px; cursor: pointer; white-space: nowrap;">
                                            ✨ Optimize Alt
                                        </button>
                                    `}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>

                <!-- FOOTER -->
                <div style="padding: 14px 24px; border-top: 1px solid var(--border, #334155); display: flex; justify-content: flex-end; gap: 10px; background: var(--bg-subtle, rgba(255,255,255,0.02));">
                    <button type="button" class="btn-close-modal btn btn-secondary btn-sm" style="padding: 6px 16px; font-weight: 600;">Close</button>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    bindEvents() {
        const modal = this;

        // Filter select
        const fSelect = this.element.querySelector('#img-filter-select');
        if (fSelect) {
            fSelect.addEventListener('change', (e) => {
                modal.filter = e.target.value;
                modal.updateContent();
            });
        }

        // Close buttons
        this.element.querySelectorAll('.btn-close-modal').forEach(btn => {
            btn.addEventListener('click', () => ImageDetailsModal.close());
        });

        // Click backdrop close
        this.element.addEventListener('click', (e) => {
            if (e.target === modal.element) {
                ImageDetailsModal.close();
            }
        });

        // Fix all alts button
        const btnFixAll = this.element.querySelector('.btn-fix-all-alts');
        if (btnFixAll) {
            btnFixAll.addEventListener('click', () => {
                const missingImgs = modal.images.filter(i => i.alt_missing || !i.alt_text);
                const missingUrls = missingImgs.map(i => i.image_url || i.src).join('\n');
                AISuggestModal.show({
                    projectId: modal.projectId,
                    pageUrl: modal.pageUrl,
                    taskType: 'image_alt',
                    currentValue: missingUrls,
                    issue: `Missing alt attributes on ${missingImgs.length} images`
                });
            });
        }

        // Copy all URLs
        const btnCopyAll = this.element.querySelector('.btn-copy-all-urls');
        if (btnCopyAll) {
            btnCopyAll.addEventListener('click', () => {
                const urls = modal.images.map(i => i.image_url || i.src).join('\n');
                navigator.clipboard.writeText(urls).then(() => {
                    btnCopyAll.innerText = '✓ Copied!';
                    setTimeout(() => { btnCopyAll.innerText = '📋 Copy Image URLs'; }, 2000);
                });
            });
        }

        // Single image AI fix
        this.element.querySelectorAll('.btn-ai-single-image').forEach(btn => {
            btn.addEventListener('click', () => {
                const imgUrl = btn.getAttribute('data-img-url') || '';
                const currentAlt = btn.getAttribute('data-current-alt') || '';
                AISuggestModal.show({
                    projectId: modal.projectId,
                    pageUrl: modal.pageUrl,
                    taskType: 'image_alt',
                    currentValue: currentAlt || `Target Image URL: ${imgUrl}`,
                    issue: currentAlt ? 'Optimize existing alt text' : 'Missing alt text for image'
                });
            });
        });
    }

    handleKeyDown(e) {
        if (e.key === 'Escape') {
            ImageDetailsModal.close();
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
