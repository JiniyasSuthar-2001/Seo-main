/**
 * Crawl Complete Modal
 * Displays real crawl completion statistics returned by the backend.
 * Opens automatically after the crawl progress popup closes and background data refreshes.
 */
export class CrawlCompleteModalManager {
    constructor() {
        this.isOpen = false;
        this.modalElement = null;
        this.completionData = null;
    }

    formatDuration(seconds) {
        if (seconds === null || seconds === undefined || isNaN(seconds)) {
            return null;
        }
        const s = Math.max(0, parseInt(seconds, 10));
        const mins = Math.floor(s / 60);
        const remainingSecs = s % 60;
        const pad = (n) => String(n).padStart(2, '0');
        if (mins >= 60) {
            const hrs = Math.floor(mins / 60);
            const remainingMins = mins % 60;
            return `${pad(hrs)}:${pad(remainingMins)}:${pad(remainingSecs)}`;
        }
        return `${pad(mins)}:${pad(remainingSecs)}`;
    }

    open(data = {}) {
        this.close(); // Clean up any existing instance

        this.isOpen = true;
        this.completionData = data;

        const isPartial = data.status === 'completed_with_errors';
        const pagesFound = typeof data.pages_discovered === 'number' ? data.pages_discovered : null;
        const pagesCrawled = typeof data.pages_crawled === 'number' ? data.pages_crawled : null;
        const issuesFound = typeof data.issues_found === 'number' ? data.issues_found : null;
        const formattedDuration = this.formatDuration(data.duration_seconds);

        const modalRoot = document.createElement('div');
        modalRoot.id = 'crawl-complete-modal-root';
        modalRoot.style.cssText = `
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(8px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 100000;
            padding: 20px;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            animation: fadeInModal 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        `;

        const titleText = isPartial ? 'Crawl Completed with Issues' : 'Crawl Completed';
        const subtitleText = isPartial
            ? 'Your website crawl has finished. Some pages encountered timeouts or connection errors.'
            : 'Your website crawl has finished successfully and your reports have been refreshed.';
        const statusColor = isPartial ? '#f59e0b' : '#10b981';
        const statusBg = isPartial ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.12)';
        const statusBorder = isPartial ? 'rgba(245, 158, 11, 0.3)' : 'rgba(16, 185, 129, 0.3)';

        // Stat cards generation (Only display real metrics supplied by backend)
        let statsHtml = '';

        if (pagesFound !== null) {
            statsHtml += `
                <div style="background: var(--bg-subtle, #1e293b); border: 1px solid var(--border, #334155); border-radius: 12px; padding: 16px; text-align: center; flex: 1; min-width: 110px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #94a3b8); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">Pages Found</div>
                    <div style="font-size: 26px; font-weight: 800; color: var(--text-primary, #f8fafc);">${pagesFound.toLocaleString()}</div>
                </div>
            `;
        }

        if (pagesCrawled !== null) {
            statsHtml += `
                <div style="background: var(--bg-subtle, #1e293b); border: 1px solid var(--border, #334155); border-radius: 12px; padding: 16px; text-align: center; flex: 1; min-width: 110px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #94a3b8); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">Pages Crawled</div>
                    <div style="font-size: 26px; font-weight: 800; color: #38bdf8;">${pagesCrawled.toLocaleString()}</div>
                </div>
            `;
        }

        if (issuesFound !== null) {
            statsHtml += `
                <div style="background: var(--bg-subtle, #1e293b); border: 1px solid var(--border, #334155); border-radius: 12px; padding: 16px; text-align: center; flex: 1; min-width: 110px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #94a3b8); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">Issues Found</div>
                    <div style="font-size: 26px; font-weight: 800; color: ${issuesFound > 0 ? '#f87171' : '#10b981'};">${issuesFound.toLocaleString()}</div>
                </div>
            `;
        }

        if (formattedDuration !== null) {
            statsHtml += `
                <div style="background: var(--bg-subtle, #1e293b); border: 1px solid var(--border, #334155); border-radius: 12px; padding: 16px; text-align: center; flex: 1; min-width: 110px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-tertiary, #94a3b8); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">Duration</div>
                    <div style="font-size: 26px; font-weight: 800; color: var(--text-primary, #f8fafc); font-family: monospace;">${formattedDuration}</div>
                </div>
            `;
        }

        modalRoot.innerHTML = `
            <style>
                @keyframes fadeInModal {
                    from { opacity: 0; transform: scale(0.96); }
                    to { opacity: 1; transform: scale(1); }
                }
            </style>
            <div class="card" style="width: 100%; max-width: 540px; background: var(--bg-card, #0f172a); border-radius: 16px; border: 1px solid var(--border, #334155); box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 30px rgba(16, 185, 129, 0.15); overflow: hidden; display: flex; flex-direction: column;">
                
                <!-- HEADER -->
                <div style="padding: 24px 28px 16px; display: flex; align-items: flex-start; justify-content: space-between; border-bottom: 1px solid var(--border, #334155); background: var(--bg-card, #0f172a);">
                    <div style="display: flex; align-items: center; gap: 14px;">
                        <div style="width: 42px; height: 42px; border-radius: 12px; background: ${statusBg}; border: 1px solid ${statusBorder}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            ${isPartial ? `
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${statusColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                                    <line x1="12" y1="9" x2="12" y2="13"></line>
                                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                                </svg>
                            ` : `
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="${statusColor}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            `}
                        </div>
                        <div>
                            <h3 style="font-size: 19px; font-weight: 700; color: var(--text-primary, #f8fafc); margin: 0;">${titleText}</h3>
                            <div style="font-size: 12px; font-weight: 600; color: ${statusColor}; margin-top: 3px;">
                                ${isPartial ? '✓ Scan finished with notices' : '✓ Scan finished successfully'}
                            </div>
                        </div>
                    </div>
                    <button id="btn-modal-x-close" type="button" style="background: none; border: none; font-size: 22px; color: var(--text-tertiary, #94a3b8); cursor: pointer; padding: 4px; line-height: 1;" title="Close">&times;</button>
                </div>

                <!-- BODY -->
                <div style="padding: 24px 28px; display: flex; flex-direction: column; gap: 20px;">
                    <p style="font-size: 13.5px; color: var(--text-secondary, #cbd5e1); line-height: 1.5; margin: 0;">
                        ${subtitleText}
                    </p>

                    <!-- METRICS GRID -->
                    ${statsHtml ? `
                        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                            ${statsHtml}
                        </div>
                    ` : ''}

                    <div style="background: rgba(37, 99, 235, 0.08); border: 1px solid rgba(37, 99, 235, 0.2); border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; gap: 10px;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                        <span style="font-size: 12.5px; color: #93c5fd;">The dashboard and audit tables behind this window are now updated with the latest crawl snapshot.</span>
                    </div>
                </div>

                <!-- FOOTER ACTIONS -->
                <div style="padding: 16px 28px; border-top: 1px solid var(--border, #334155); background: var(--bg-subtle, #1e293b); display: flex; justify-content: flex-end; gap: 10px;">
                    <button id="btn-close-crawl-complete" class="btn btn-primary" type="button" style="padding: 9px 24px; font-weight: 600; font-size: 13.5px; border-radius: 8px;">
                        Close
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modalRoot);
        this.modalElement = modalRoot;

        // Attach close event handlers
        const handleClose = () => this.close();
        document.getElementById('btn-close-crawl-complete')?.addEventListener('click', handleClose);
        document.getElementById('btn-modal-x-close')?.addEventListener('click', handleClose);
        modalRoot.addEventListener('click', (e) => {
            if (e.target === modalRoot) {
                handleClose();
            }
        });
    }

    close() {
        this.isOpen = false;
        this.completionData = null;
        if (this.modalElement) {
            this.modalElement.remove();
            this.modalElement = null;
        }
        const leftover = document.getElementById('crawl-complete-modal-root');
        if (leftover) leftover.remove();
    }
}

export const crawlCompleteModal = new CrawlCompleteModalManager();
