/**
 * File Inspector & Sensitive Data Security Scanner Component
 * Performs client-side file inspection, sensitive data/credential scanning,
 * column header validation, row diagnostics, and pre-import preview.
 */

export class FileInspectorModal {
    static scanForSensitiveData(textContent, headers) {
        const sensitivePatterns = [
            /-----BEGIN (RSA |EC |PGP |OPENSSH )?PRIVATE KEY-----/i,
            /AKIA[0-9A-Z]{16}/,
            /sk_live_[0-9a-zA-Z]{24,}/,
            /ghp_[0-9a-zA-Z]{36}/,
            /eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_=]*/
        ];

        for (const pattern of sensitivePatterns) {
            if (pattern.test(textContent)) {
                return { detected: true, type: 'credential_pattern' };
            }
        }

        const sensitiveHeaderNames = [
            'password', 'passwd', 'secret', 'api_key', 'apikey', 
            'access_token', 'auth_token', 'private_key', 'oauth_token',
            'session_id', 'cookie', 'creditcard', 'card_number', 'cvv'
        ];

        for (const h of headers) {
            const cleanH = String(h || '').toLowerCase().replace(/[^a-z0-9_]/g, '');
            if (sensitiveHeaderNames.includes(cleanH)) {
                return { detected: true, type: 'sensitive_header' };
            }
        }

        return { detected: false };
    }

    static parseCSV(text) {
        const lines = text.split(/\r\n|\n|\r/);
        const rows = [];
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;
            
            // Handle quotes simple splitting
            const cells = line.split(',').map(c => c.trim().replace(/^"|"$/g, ''));
            rows.push(cells);
        }
        return rows;
    }

    static inspectFile(file, guidance, onConfirmImport, onCancel) {
        const reader = new FileReader();

        reader.onload = (e) => {
            const textContent = e.target.result || '';
            const rawRows = FileInspectorModal.parseCSV(textContent);

            if (rawRows.length === 0) {
                FileInspectorModal.renderErrorModal("Empty File Error", "The selected file contains no readable data rows.", onCancel);
                return;
            }

            const headers = rawRows[0] || [];
            const dataRows = rawRows.slice(1);

            // 1. Sensitive Data Scanner
            const scanResult = FileInspectorModal.scanForSensitiveData(textContent, headers);
            if (scanResult.detected) {
                FileInspectorModal.renderSensitiveDataAlertModal(onCancel);
                return;
            }

            // 2. Validate Required Columns
            const lowerHeaders = headers.map(h => String(h).toLowerCase().trim());
            const missingRequired = [];

            guidance.required_columns.forEach(req => {
                const reqName = req.name.toLowerCase().trim();
                const match = lowerHeaders.some(h => h.includes(reqName) || reqName.includes(h));
                if (!match) {
                    missingRequired.push(req.name);
                }
            });

            // 3. Row-level Diagnostics
            const rowDiagnostics = [];
            dataRows.forEach((row, idx) => {
                const rowNum = idx + 2;
                if (row.length === 0 || (row.length === 1 && !row[0])) return;

                // Check numeric position if applicable
                const posColIdx = headers.findIndex(h => String(h).toLowerCase().includes('position'));
                if (posColIdx !== -1 && row[posColIdx]) {
                    const posVal = Number(row[posColIdx]);
                    if (isNaN(posVal)) {
                        rowDiagnostics.push({ row: rowNum, message: `Position must be a valid number (found '${row[posColIdx]}').` });
                    }
                }
            });

            // 4. Render Preview Modal
            FileInspectorModal.renderPreviewModal({
                filename: file.name,
                fileSize: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
                guidance,
                headers,
                dataRows,
                missingRequired,
                rowDiagnostics,
                onConfirmImport,
                onCancel
            });
        };

        reader.readAsText(file);
    }

    static renderSensitiveDataAlertModal(onCancel) {
        let modal = document.getElementById('file-inspector-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'file-inspector-modal';
            document.body.appendChild(modal);
        }

        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 10000; backdrop-filter: blur(4px);';

        modal.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 2px solid #ef4444; border-radius: 12px; max-width: 540px; width: 90%; padding: 28px; color: var(--text-primary);">
                <div style="display: flex; gap: 14px; align-items: flex-start; margin-bottom: 16px;">
                    <div style="font-size: 28px; line-height: 1;">🔒</div>
                    <div>
                        <h3 style="font-size: 18px; font-weight: 700; color: #ef4444; margin: 0;">Potential Sensitive Information Detected</h3>
                        <p style="color: var(--text-secondary); font-size: 13.5px; margin-top: 6px; line-height: 1.5;">
                            This file appears to contain a credential, API key, access token, or sensitive secret field. For your security, we have not imported it.
                        </p>
                    </div>
                </div>

                <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; padding: 14px; border-radius: 6px; margin-bottom: 20px; font-size: 13px; color: var(--text-secondary);">
                    <strong>What should I do?</strong><br/>
                    Remove passwords, secret keys, or authentication tokens from the CSV file and upload the SEO data again.
                </div>

                <div style="display: flex; justify-content: flex-end;">
                    <button class="btn btn-primary" id="btn-close-sec-alert" style="background: #ef4444; border-color: #ef4444;">Acknowledge & Cancel</button>
                </div>
            </div>
        `;

        document.getElementById('btn-close-sec-alert')?.addEventListener('click', () => {
            document.body.removeChild(modal);
            if (onCancel) onCancel();
        });
    }

    static renderErrorModal(title, detail, onCancel) {
        let modal = document.getElementById('file-inspector-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'file-inspector-modal';
            document.body.appendChild(modal);
        }

        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 10000; backdrop-filter: blur(4px);';

        modal.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color); border-radius: 12px; max-width: 500px; width: 90%; padding: 24px; color: var(--text-primary);">
                <h3 style="font-size: 18px; font-weight: 700; color: #ef4444; margin-bottom: 8px;">${title}</h3>
                <p style="color: var(--text-secondary); font-size: 13.5px; margin-bottom: 20px;">${detail}</p>
                <div style="display: flex; justify-content: flex-end;">
                    <button class="btn btn-secondary" id="btn-close-err-modal">Close</button>
                </div>
            </div>
        `;

        document.getElementById('btn-close-err-modal')?.addEventListener('click', () => {
            document.body.removeChild(modal);
            if (onCancel) onCancel();
        });
    }

    static renderPreviewModal({ filename, fileSize, guidance, headers, dataRows, missingRequired, rowDiagnostics, onConfirmImport, onCancel }) {
        let modal = document.getElementById('file-inspector-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'file-inspector-modal';
            document.body.appendChild(modal);
        }

        modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.75); display: flex; align-items: center; justify-content: center; z-index: 10000; backdrop-filter: blur(4px);';

        const previewRows = dataRows.slice(0, 5);
        const hasMissingReq = missingRequired.length > 0;

        modal.innerHTML = `
            <div style="background: var(--bg-card, #1e293b); border: 1px solid var(--border-color); border-radius: 14px; max-width: 780px; width: 92%; max-height: 90vh; overflow-y: auto; padding: 24px; color: var(--text-primary);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px;">
                    <div>
                        <h3 style="font-size: 18px; font-weight: 700; margin: 0;">Pre-Import File Inspection & Preview</h3>
                        <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">
                            File: <strong style="color: var(--text-primary);">${filename}</strong> (${fileSize}) | Rows Detected: <strong>${dataRows.length.toLocaleString()}</strong>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-sm" id="btn-close-inspect">✕</button>
                </div>

                ${hasMissingReq ? `
                    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; padding: 14px; border-radius: 8px; margin-bottom: 18px; font-size: 13px;">
                        <strong>Unable to import file: Missing Required Columns</strong><br/>
                        Missing column(s): <strong>${missingRequired.join(', ')}</strong>.<br/>
                        Your file headers: <code>${headers.join(', ')}</code>.<br/>
                        Please add missing columns or download our sample template before importing.
                    </div>
                ` : `
                    <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); color: #22c55e; padding: 12px 16px; border-radius: 8px; margin-bottom: 18px; font-size: 13px; display: flex; gap: 10px; align-items: center;">
                        <span style="font-size: 16px;">✓</span>
                        <div>
                            <strong>File Headers Verified Cleanly</strong><br/>
                            Required columns present: ${guidance.required_columns.map(c => `✓ ${c.name}`).join(' ')}
                        </div>
                    </div>
                `}

                ${rowDiagnostics.length > 0 ? `
                    <div style="margin-bottom: 18px;">
                        <div style="font-size: 13px; font-weight: 600; color: #f59e0b; margin-bottom: 6px;">
                            ⚠️ Row Diagnostics (${rowDiagnostics.length} rows need attention):
                        </div>
                        <div style="max-height: 90px; overflow-y: auto; background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.2); border-radius: 6px; padding: 8px 12px; font-size: 12px;">
                            ${rowDiagnostics.slice(0, 5).map(d => `<div>Row ${d.row}: ${d.message}</div>`).join('')}
                            ${rowDiagnostics.length > 5 ? `<div style="font-style: italic; margin-top: 4px;">+ ${rowDiagnostics.length - 5} more rows...</div>` : ''}
                        </div>
                    </div>
                ` : ''}

                <!-- PREVIEW TABLE -->
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--text-secondary);">
                        First ${previewRows.length} Rows Sample Preview:
                    </div>
                    <div style="overflow-x: auto; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); border-radius: 8px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left;">
                            <thead>
                                <tr style="background: rgba(255,255,255,0.05); border-bottom: 1px solid var(--border-color);">
                                    ${headers.map(h => `<th style="padding: 8px 12px; color: var(--text-primary);">${h}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${previewRows.map(row => `
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
                                        ${headers.map((_, i) => `<td style="padding: 8px 12px; color: var(--text-secondary);">${row[i] !== undefined ? row[i] : '-'}</td>`).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 12px; color: var(--text-tertiary); display: flex; align-items: center; gap: 6px;">
                        <span>🔒</span> Privacy Check Passed • No credentials detected
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-secondary" id="btn-cancel-inspect">Cancel</button>
                        <button class="btn btn-primary" id="btn-confirm-import" ${hasMissingReq ? 'disabled' : ''}>
                            ${hasMissingReq ? 'Fix Column Errors First' : 'Confirm & Import Data'}
                        </button>
                    </div>
                </div>
            </div>
        `;

        const closeModal = () => {
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
            if (onCancel) onCancel();
        };

        document.getElementById('btn-close-inspect')?.addEventListener('click', closeModal);
        document.getElementById('btn-cancel-inspect')?.addEventListener('click', closeModal);

        document.getElementById('btn-confirm-import')?.addEventListener('click', () => {
            if (document.body.contains(modal)) {
                document.body.removeChild(modal);
            }
            if (onConfirmImport) onConfirmImport();
        });
    }
}
