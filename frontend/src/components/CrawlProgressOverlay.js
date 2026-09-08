import { crawlService } from '../services/crawlService.js';

class CrawlProgressOverlayManager {
    constructor() {
        this.activeInterval = null;
        this.overlayElement = null;
    }

    createOverlayElement(targetUrl) {
        if (this.overlayElement) {
            this.overlayElement.remove();
        }

        const container = document.createElement('div');
        container.id = 'global-crawl-overlay';
        container.style.cssText = `
            position: fixed;
            top: 72px;
            right: 32px;
            z-index: 99999;
            width: 420px;
            background: rgba(15, 23, 42, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid var(--primary, #2563eb);
            border-radius: 12px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 0 25px rgba(37, 99, 235, 0.3);
            padding: 20px;
            color: #fff;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            animation: slideInDown 0.3s ease-out;
        `;

        container.innerHTML = `
            <style>
                @keyframes slideInDown {
                    from { transform: translateY(-20px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                @keyframes progressShimmer {
                    0% { background-position: 0 0; }
                    100% { background-position: 40px 0; }
                }
                .crawl-spinner {
                    width: 18px;
                    height: 18px;
                    border: 3px solid rgba(255, 255, 255, 0.2);
                    border-top-color: #3b82f6;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                    display: inline-block;
                    vertical-align: middle;
                }
                .crawl-progress-striped {
                    background-image: linear-gradient(
                        45deg,
                        rgba(255, 255, 255, 0.2) 25%,
                        transparent 25%,
                        transparent 50%,
                        rgba(255, 255, 255, 0.2) 50%,
                        rgba(255, 255, 255, 0.2) 75%,
                        transparent 75%,
                        transparent
                    );
                    background-size: 40px 40px;
                    animation: progressShimmer 1s linear infinite;
                }
            </style>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span id="crawl-overlay-spinner" class="crawl-spinner"></span>
                    <span style="font-weight: 700; font-size: 15px; color: #f8fafc;" id="crawl-overlay-title">Website Crawl Active</span>
                </div>
                <button id="crawl-overlay-close" style="background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer; padding: 0 4px; line-height: 1;" title="Dismiss">&times;</button>
            </div>
            
            <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px; word-break: break-all; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" id="crawl-overlay-url">
                Crawling: <strong style="color: #60a5fa;">${targetUrl}</strong>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 12px;">
                <span id="crawl-overlay-status-text" style="color: #cbd5e1; font-weight: 500;">Queuing URLs & scanning HTTP headers...</span>
                <span id="crawl-overlay-stats" style="font-weight: 700; color: #38bdf8;">Starting...</span>
            </div>

            <!-- Animated Progress Bar Container -->
            <div style="width: 100%; height: 10px; background: rgba(255, 255, 255, 0.12); border-radius: 6px; overflow: hidden; position: relative;">
                <div id="crawl-overlay-bar" class="crawl-progress-striped" style="width: 10%; height: 100%; background-color: #2563eb; border-radius: 6px; transition: width 0.4s ease, background-color 0.4s ease;"></div>
            </div>

            <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 11px; color: #64748b;">
                <span>Local Engine Running</span>
                <span id="crawl-overlay-percent" style="font-weight: 600; color: #94a3b8;">Scanning</span>
            </div>

            <div id="crawl-overlay-actions" style="margin-top: 14px; display: flex; justify-content: flex-end; gap: 8px;">
                <button id="btn-cancel-crawl" style="background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s ease;">
                    Cancel Crawl
                </button>
            </div>
        `;

        document.body.appendChild(container);
        this.overlayElement = container;

        document.getElementById('crawl-overlay-close')?.addEventListener('click', () => {
            container.style.display = 'none';
        });
    }

    start(projectId, sessionId, targetUrl) {
        this.createOverlayElement(targetUrl);

        if (this.activeInterval) {
            clearInterval(this.activeInterval);
        }

        this.setButtonsState(true);

        const cancelBtn = document.getElementById('btn-cancel-crawl');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', async () => {
                if (cancelBtn.disabled) return;
                cancelBtn.disabled = true;
                cancelBtn.style.opacity = '0.7';
                cancelBtn.style.cursor = 'not-allowed';
                cancelBtn.innerHTML = `<span class="crawl-spinner" style="width: 10px; height: 10px; border-width: 2px; margin-right: 6px;"></span> Cancelling...`;

                const statusTextEl = document.getElementById('crawl-overlay-status-text');
                if (statusTextEl) {
                    statusTextEl.innerHTML = `<span style="color: #f59e0b; font-weight: 500;">Safely stopping current scan...</span>`;
                }

                try {
                    await crawlService.cancelCrawl(projectId, sessionId);
                } catch (err) {
                    console.error("[CRAWL CANCEL ERROR]", err);
                    if (statusTextEl) {
                        statusTextEl.innerHTML = `<span style="color: #cbd5e1; font-weight: 500;">We couldn't stop the crawl immediately. The system will stop it as soon as the current operation finishes.</span>`;
                    }
                }
            });
        }

        this.activeInterval = setInterval(async () => {
            try {
                const statusData = await crawlService.getCrawlStatus(projectId, sessionId);
                
                const statsEl = document.getElementById('crawl-overlay-stats');
                const percentEl = document.getElementById('crawl-overlay-percent');
                const barEl = document.getElementById('crawl-overlay-bar');
                const statusTextEl = document.getElementById('crawl-overlay-status-text');
                const spinnerEl = document.getElementById('crawl-overlay-spinner');
                const titleEl = document.getElementById('crawl-overlay-title');
                const actionsEl = document.getElementById('crawl-overlay-actions');

                const discovered = statusData.pages_discovered || 1;
                const crawled = statusData.pages_crawled || 0;
                const maxCfg = statusData.max_pages;
                const is5000Plus = (maxCfg === '5000+' || maxCfg === 0 || maxCfg === '0' || maxCfg === null || maxCfg === undefined);
                
                let pct = 10;
                if (crawled > 0) {
                    pct = Math.min(100, Math.round((crawled / Math.max(crawled, discovered)) * 100));
                }

                if (is5000Plus) {
                    if (statsEl) statsEl.innerText = `${crawled.toLocaleString()} pages scanned`;
                    if (percentEl) percentEl.innerText = `Unlimited Scope`;
                    if (barEl) barEl.style.width = `100%`;
                    if (crawled > 0 && statusTextEl && statusData.status !== 'cancelling' && statusData.status !== 'cancelled') {
                        if (statusData.status_message) {
                            statusTextEl.innerText = statusData.status_message;
                        } else {
                            statusTextEl.innerText = `Crawling HTML... Continuing until crawl scope is exhausted.`;
                        }
                    }
                } else {
                    if (statsEl) statsEl.innerText = `${crawled.toLocaleString()} / ${discovered.toLocaleString()} pages`;
                    if (percentEl) percentEl.innerText = `${pct}%`;
                    if (barEl) barEl.style.width = `${pct}%`;
                    if (crawled > 0 && statusTextEl && statusData.status !== 'cancelling' && statusData.status !== 'cancelled') {
                        if (statusData.status_message) {
                            statusTextEl.innerText = statusData.status_message;
                        } else {
                            statusTextEl.innerText = `Crawling HTML, extracting links & meta tags...`;
                        }
                    }
                }

                if (statusData.status === 'cancelled') {
                    clearInterval(this.activeInterval);
                    this.activeInterval = null;

                    if (statsEl) statsEl.innerText = `${crawled} page(s) audited before cancellation`;
                    if (statusTextEl) {
                        statusTextEl.innerHTML = `<span style="color: #f59e0b; font-weight: 600;">Crawl cancelled by user after ${crawled} pages.</span>`;
                    }
                    if (titleEl) titleEl.innerText = "Crawl Cancelled";
                    if (barEl) {
                        barEl.style.width = "100%";
                        barEl.style.backgroundColor = "#f59e0b";
                        barEl.classList.remove('crawl-progress-striped');
                    }
                    if (spinnerEl) {
                        spinnerEl.outerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
                    }
                    if (actionsEl) {
                        actionsEl.innerHTML = `
                            <button id="btn-overlay-view-results" style="background: #2563eb; color: #fff; border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer;">View Results</button>
                            <button id="btn-overlay-new-crawl" style="background: rgba(255, 255, 255, 0.1); color: #e2e8f0; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; cursor: pointer;">Start New Crawl</button>
                        `;
                        document.getElementById('btn-overlay-view-results')?.addEventListener('click', () => window.location.href = '/technical');
                        document.getElementById('btn-overlay-new-crawl')?.addEventListener('click', () => {
                            document.getElementById('global-crawl-overlay')?.remove();
                            window.dispatchEvent(new CustomEvent('seo:open-crawl-config'));
                        });
                    }

                    this.setButtonsState(false);
                    projectStore.fetchProjects().catch(() => {});
                    window.dispatchEvent(new CustomEvent('seo:crawl-completed', { detail: { projectId, sessionId } }));

                } else if (statusData.status === 'completed' || statusData.status === 'completed_with_errors') {
                    clearInterval(this.activeInterval);
                    this.activeInterval = null;

                    const isPartial = statusData.status === 'completed_with_errors';

                    if (statsEl) statsEl.innerText = `${crawled} / ${discovered} page(s) audited`;
                    if (statusTextEl) {
                        statusTextEl.innerHTML = isPartial
                            ? `<span style="color: #f59e0b; font-weight: 600;">⚠ Crawl completed with issues (page timeouts/errors skipped).</span>`
                            : `<span style="color: #4ade80; font-weight: 600;">✓ Website audit completed successfully!</span>`;
                    }
                    if (titleEl) {
                        titleEl.innerText = isPartial ? "Crawl Completed with Issues" : "Crawl Complete";
                    }
                    if (barEl) {
                        barEl.style.width = "100%";
                        barEl.style.backgroundColor = isPartial ? "#f59e0b" : "#10b981";
                        barEl.classList.remove('crawl-progress-striped');
                    }
                    if (spinnerEl) {
                        spinnerEl.outerHTML = isPartial
                            ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`
                            : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                    }
                    if (actionsEl) {
                        actionsEl.innerHTML = ``;
                    }

                    this.setButtonsState(false);

                    // Notify store and dispatch async event without page reload
                    projectStore.fetchProjects().catch(() => {});
                    window.dispatchEvent(new CustomEvent('seo:crawl-completed', { detail: { projectId, sessionId } }));

                } else if (statusData.status === 'failed') {
                    clearInterval(this.activeInterval);
                    this.activeInterval = null;

                    if (statusTextEl) statusTextEl.innerHTML = `<span style="color: #f87171; font-weight: 600;">✕ Crawl failed (website connection unreachable).</span>`;
                    if (titleEl) titleEl.innerText = "Crawl Failed";
                    if (barEl) {
                        barEl.style.width = "100%";
                        barEl.style.backgroundColor = "#ef4444";
                        barEl.classList.remove('crawl-progress-striped');
                    }
                    if (actionsEl) {
                        actionsEl.innerHTML = ``;
                    }

                    this.setButtonsState(false);
                }
            } catch (err) {
                console.error("[CRAWL OVERLAY] Status polling error:", err);
            }
        }, 1000);
    }

    setButtonsState(isCrawling) {
        const buttons = document.querySelectorAll('button[onclick*="startCrawl"]');
        buttons.forEach(btn => {
            if (isCrawling) {
                btn.disabled = true;
                if (!btn.dataset.origText) {
                    btn.dataset.origText = btn.innerHTML;
                }
                btn.innerHTML = `<span class="crawl-spinner" style="width: 12px; height: 12px; border-width: 2px; margin-right: 6px;"></span> Crawling...`;
                btn.style.opacity = '0.75';
                btn.style.cursor = 'not-allowed';
            } else if (btn.dataset.origText) {
                btn.disabled = false;
                btn.innerHTML = btn.dataset.origText;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            }
        });
    }
}

export const crawlProgressOverlay = new CrawlProgressOverlayManager();
