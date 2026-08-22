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
                <span id="crawl-overlay-status-text" style="color: #cbd5e1; font-weight: 500;">Fetching pages & parsing HTML metadata...</span>
                <span id="crawl-overlay-stats" style="font-weight: 700; color: #38bdf8;">Starting...</span>
            </div>

            <!-- Animated Progress Bar Container -->
            <div style="width: 100%; height: 10px; background: rgba(255, 255, 255, 0.12); border-radius: 6px; overflow: hidden; position: relative;">
                <div id="crawl-overlay-bar" class="crawl-progress-striped" style="width: 8%; height: 100%; background-color: #2563eb; border-radius: 6px; transition: width 0.4s ease, background-color 0.4s ease;"></div>
            </div>

            <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 11px; color: #64748b;">
                <span>Local Engine Running</span>
                <span id="crawl-overlay-percent" style="font-weight: 600; color: #94a3b8;">Scanning</span>
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

        // Disable all crawl buttons in DOM & show loading spinners on them
        this.setButtonsState(true);

        this.activeInterval = setInterval(async () => {
            try {
                const statusData = await crawlService.getCrawlStatus(projectId, sessionId);
                
                const statsEl = document.getElementById('crawl-overlay-stats');
                const percentEl = document.getElementById('crawl-overlay-percent');
                const barEl = document.getElementById('crawl-overlay-bar');
                const statusTextEl = document.getElementById('crawl-overlay-status-text');
                const spinnerEl = document.getElementById('crawl-overlay-spinner');
                const titleEl = document.getElementById('crawl-overlay-title');

                const discovered = statusData.pages_discovered || 1;
                const crawled = statusData.pages_crawled || 0;
                
                // Calculate percentage
                let pct = Math.max(8, Math.min(100, Math.round((crawled / Math.max(crawled, discovered)) * 100)));

                if (statsEl) statsEl.innerText = `${crawled} / ${discovered} pages`;
                if (percentEl) percentEl.innerText = `${pct}%`;
                if (barEl) barEl.style.width = `${pct}%`;

                if (crawled > 0 && statusTextEl) {
                    statusTextEl.innerText = `Crawling HTML, extracted internal links & meta tags...`;
                }

                if (statusData.status === 'completed') {
                    clearInterval(this.activeInterval);
                    this.activeInterval = null;

                    if (statsEl) statsEl.innerText = `${crawled} pages audited!`;
                    if (statusTextEl) statusTextEl.innerHTML = `<span style="color: #4ade80; font-weight: 600;">✓ Website audit completed successfully!</span>`;
                    if (titleEl) titleEl.innerText = "Crawl Complete";
                    if (barEl) {
                        barEl.style.width = "100%";
                        barEl.style.backgroundColor = "#10b981";
                        barEl.classList.remove('crawl-progress-striped');
                    }
                    if (spinnerEl) {
                        spinnerEl.outerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4ade80" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
                    }

                    this.setButtonsState(false);

                    setTimeout(() => {
                        window.location.reload();
                    }, 1200);

                } else if (statusData.status === 'failed') {
                    clearInterval(this.activeInterval);
                    this.activeInterval = null;

                    if (statusTextEl) statusTextEl.innerHTML = `<span style="color: #f87171; font-weight: 600;">✕ Crawl encountered an error.</span>`;
                    if (titleEl) titleEl.innerText = "Crawl Failed";
                    if (barEl) {
                        barEl.style.width = "100%";
                        barEl.style.backgroundColor = "#ef4444";
                        barEl.classList.remove('crawl-progress-striped');
                    }

                    this.setButtonsState(false);
                }
            } catch (err) {
                console.error("[CRAWL OVERLAY] Status polling error:", err);
            }
        }, 1200);
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
