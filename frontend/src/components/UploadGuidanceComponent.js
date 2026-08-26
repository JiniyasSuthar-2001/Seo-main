import { getUploadGuidance } from '../config/uploadGuidance.js';
import { getApiBaseUrl } from '../config/api.js';

export class UploadGuidanceComponent {
    constructor(guidelineId, onFileSelected) {
        this.guidance = getUploadGuidance(guidelineId);
        this.onFileSelected = onFileSelected;
        this.container = document.createElement('div');
        this.container.className = 'upload-guidance-component';
    }

    render() {
        const g = this.guidance;
        const apiBase = getApiBaseUrl();

        this.container.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color, #334155); border-radius: 12px; padding: 24px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary, #3b82f6); text-transform: uppercase; letter-spacing: 0.05em;">DATASET PREPARATION GUIDANCE</div>
                        <h3 style="font-size: 18px; font-weight: 700; margin-top: 2px; color: var(--text-primary, #f8fafc);">${g.title}</h3>
                        <p style="color: var(--text-secondary, #94a3b8); font-size: 13px; margin-top: 4px;">${g.purpose}</p>
                    </div>

                    <!-- GUIDELINE ACTION BUTTONS -->
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button class="btn btn-secondary btn-sm" id="btn-read-guidelines">
                            📄 Read Guidelines
                        </button>
                        <a href="${apiBase}/api/guidelines/${g.id}/pdf" target="_blank" class="btn btn-secondary btn-sm" id="btn-download-pdf-guide">
                            📥 Download PDF
                        </a>
                        <button class="btn btn-secondary btn-sm" id="btn-share-guidelines">
                            🔗 Share
                        </button>
                        <a href="${apiBase}/api/guidelines/${g.id}/template.csv" download="${g.id}-upload-template.csv" class="btn btn-primary btn-sm" id="btn-download-template">
                            📊 Download Sample Template
                        </a>
                    </div>
                </div>

                <!-- DRAG & DROP UPLOAD ZONE -->
                <div id="drop-zone-${g.id}" style="border: 2px dashed var(--primary, #3b82f6); border-radius: 10px; padding: 32px 20px; text-align: center; background: rgba(59, 130, 246, 0.04); cursor: pointer; transition: all 0.2s ease; margin-bottom: 20px;">
                    <input type="file" id="input-file-${g.id}" accept="${g.supported_formats.map(f => '.' + f.toLowerCase()).join(',')}" style="display: none;" />
                    <div style="font-size: 32px; margin-bottom: 8px;">📁</div>
                    <div style="font-size: 15px; font-weight: 600; color: var(--text-primary);">Drag & Drop your ${g.id.toUpperCase()} file here, or click to browse</div>
                    <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 6px;">
                        Supported Formats: <strong>${g.supported_formats.join(', ')}</strong> | Maximum File Size: <strong>${g.max_file_size}</strong>
                    </div>
                </div>

                <!-- DATA PRIVACY WARNING -->
                <div style="background: rgba(245, 158, 11, 0.08); border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 12.5px; color: var(--text-secondary); display: flex; gap: 10px; align-items: center;">
                    <span style="font-size: 16px;">🔒</span>
                    <div>
                        <strong style="color: var(--text-primary);">Data Privacy Reminder:</strong> ${g.privacy_warning}
                    </div>
                </div>

                <!-- EXPECTED COLUMN STRUCTURE PREVIEW TABLE -->
                <div style="margin-top: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Expected Column Structure & Requirements</span>
                        <span style="font-size: 11px; color: var(--text-tertiary);">${g.version}</span>
                    </div>
                    <div style="overflow-x: auto; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
                            <thead>
                                <tr style="background: rgba(255,255,255,0.04); border-bottom: 1px solid var(--border-color); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 8px 12px;">Column Name</th>
                                    <th style="padding: 8px 12px;">Required?</th>
                                    <th style="padding: 8px 12px;">Description</th>
                                    <th style="padding: 8px 12px;">Synthetic Example</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${g.required_columns.map(c => `
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                        <td style="padding: 8px 12px; font-weight: 600; color: var(--text-primary); font-family: monospace;">${c.name}</td>
                                        <td style="padding: 8px 12px;"><span style="color: #ef4444; font-weight: 700;">Required</span></td>
                                        <td style="padding: 8px 12px; color: var(--text-secondary);">${c.description}</td>
                                        <td style="padding: 8px 12px; color: var(--text-tertiary); font-family: monospace;">${c.example}</td>
                                    </tr>
                                `).join('')}
                                ${g.optional_columns.map(c => `
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                                        <td style="padding: 8px 12px; font-weight: 500; color: var(--text-primary); font-family: monospace;">${c.name}</td>
                                        <td style="padding: 8px 12px;"><span style="color: var(--text-tertiary);">Optional</span></td>
                                        <td style="padding: 8px 12px; color: var(--text-secondary);">${c.description}</td>
                                        <td style="padding: 8px 12px; color: var(--text-tertiary); font-family: monospace;">${c.example}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        this.attachEvents();
        return this.container;
    }

    attachEvents() {
        const g = this.guidance;
        const dropZone = this.container.querySelector(`#drop-zone-${g.id}`);
        const fileInput = this.container.querySelector(`#input-file-${g.id}`);

        if (dropZone && fileInput) {
            dropZone.addEventListener('click', () => fileInput.click());

            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.style.background = 'rgba(59, 130, 246, 0.12)';
            });

            dropZone.addEventListener('dragleave', () => {
                dropZone.style.background = 'rgba(59, 130, 246, 0.04)';
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.style.background = 'rgba(59, 130, 246, 0.04)';
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    if (this.onFileSelected) this.onFileSelected(e.dataTransfer.files[0]);
                }
            });

            fileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    if (this.onFileSelected) this.onFileSelected(e.target.files[0]);
                }
            });
        }

        // Read Guidelines Modal
        this.container.querySelector('#btn-read-guidelines')?.addEventListener('click', () => this.showReadGuidelinesModal());

        // Share Guidelines
        this.container.querySelector('#btn-share-guidelines')?.addEventListener('click', () => this.handleShare());
    }

    showReadGuidelinesModal() {
        const g = this.guidance;
        let modal = document.getElementById('guidelines-read-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'guidelines-read-modal';
            document.body.appendChild(modal);
        }

        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 10000; backdrop-filter: blur(4px);';

        modal.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color); border-radius: 14px; max-width: 720px; width: 92%; max-height: 88vh; overflow-y: auto; padding: 28px; color: var(--text-primary);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 14px;">
                    <div>
                        <h3 style="font-size: 20px; font-weight: 700; margin: 0;">📄 ${g.title}</h3>
                        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${g.version}</div>
                    </div>
                    <button class="btn btn-secondary btn-sm" id="btn-close-read-modal">✕</button>
                </div>

                <div style="font-size: 13.5px; line-height: 1.6; color: var(--text-secondary);">
                    <h4 style="color: var(--text-primary); font-size: 15px; font-weight: 600; margin-top: 0;">1. Purpose & Source Data</h4>
                    <p style="margin-top: 4px;">${g.purpose} <strong>Where to get it:</strong> ${g.where_to_get}</p>

                    <h4 style="color: var(--text-primary); font-size: 15px; font-weight: 600; margin-top: 16px;">2. File Specs & Supported Formats</h4>
                    <p style="margin-top: 4px;">Supported Formats: <strong>${g.supported_formats.join(', ')}</strong> | Maximum File Size: <strong>${g.max_file_size}</strong></p>

                    <h4 style="color: var(--text-primary); font-size: 15px; font-weight: 600; margin-top: 16px;">3. Required Columns</h4>
                    <ul style="padding-left: 20px; margin-top: 4px;">
                        ${g.required_columns.map(c => `<li><strong>${c.name}</strong>: ${c.description} (e.g. <code>${c.example}</code>)</li>`).join('')}
                    </ul>

                    <h4 style="color: var(--text-primary); font-size: 15px; font-weight: 600; margin-top: 16px;">4. Recommended Optional Columns</h4>
                    <ul style="padding-left: 20px; margin-top: 4px;">
                        ${g.optional_columns.map(c => `<li><strong>${c.name}</strong>: ${c.description} (e.g. <code>${c.example}</code>)</li>`).join('')}
                    </ul>

                    <h4 style="color: var(--text-primary); font-size: 15px; font-weight: 600; margin-top: 16px;">5. Important Guidelines & Common Misconceptions</h4>
                    <ul style="padding-left: 20px; margin-top: 4px; color: #f59e0b;">
                        ${g.common_errors.map(err => `<li>${err}</li>`).join('')}
                    </ul>

                    <h4 style="color: #ef4444; font-size: 15px; font-weight: 600; margin-top: 16px;">🔒 Data Privacy & Security Warning</h4>
                    <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 6px; margin-top: 4px; color: var(--text-secondary);">
                        ${g.privacy_warning} Never upload passwords, API credentials, OAuth tokens, or confidential database dumps. Use secure OAuth connections for live accounts.
                    </div>
                </div>

                <div style="display: flex; justify-content: flex-end; margin-top: 24px; gap: 10px;">
                    <button class="btn btn-secondary" id="btn-modal-close-action">Close</button>
                    <a href="${getApiBaseUrl()}/api/guidelines/${g.id}/pdf" target="_blank" class="btn btn-primary">Download PDF Guide</a>
                </div>
            </div>
        `;

        const closeModal = () => {
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
        };

        document.getElementById('btn-close-read-modal')?.addEventListener('click', closeModal);
        document.getElementById('btn-modal-close-action')?.addEventListener('click', closeModal);

        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeModal();
        }, { once: true });
    }

    async handleShare() {
        const g = this.guidance;
        const shareData = {
            title: g.title,
            text: `${g.title}: ${g.purpose}. Required columns: ${g.required_columns.map(c => c.name).join(', ')}.`,
            url: `${window.location.origin}/#/import?guideline=${g.id}`
        };

        if (navigator.share) {
            try {
                await navigator.share(shareData);
            } catch (err) {
                this.fallbackCopyLink(shareData.url);
            }
        } else {
            this.fallbackCopyLink(shareData.url);
        }
    }

    fallbackCopyLink(url) {
        navigator.clipboard.writeText(url).then(() => {
            alert(`Guideline shareable link copied to clipboard!\n\nLink: ${url}`);
        }).catch(() => {
            alert(`Shareable Guideline Link:\n${url}`);
        });
    }
}
