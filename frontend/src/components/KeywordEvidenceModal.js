/**
 * Keyword Evidence Modal Component
 * Displays real on-page keyword occurrences from crawl data across:
 * - Page title
 * - Meta description
 * - H1
 * - H2/H3
 * - First paragraph
 * - Body content
 * - Image alt text
 * - Anchor text
 * - Schema / structured data
 */
import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';

export class KeywordEvidenceModal {
    static async open({ projectId, keywordId, keywordText }) {
        const existing = document.getElementById('keyword-evidence-modal-root');
        if (existing) existing.remove();

        let targetProjectId = projectId || projectStore.getSelectedProjectId();
        if (!targetProjectId) {
            targetProjectId = localStorage.getItem('seo_selected_project_id');
        }

        const modalRoot = document.createElement('div');
        modalRoot.id = 'keyword-evidence-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(6px); display: flex; align-items: center;
            justify-content: center; z-index: 99999; padding: 20px;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            animation: fadeInModal 0.2s ease-out;
        `;

        modalRoot.innerHTML = `
            <div class="card" style="width: 100%; max-width: 800px; max-height: 85vh; background: var(--bg-card, #0f172a); border-radius: 14px; border: 1px solid var(--border, #334155); display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);">
                <!-- HEADER -->
                <div style="padding: 20px 24px; border-bottom: 1px solid var(--border, #334155); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle, #1e293b);">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span class="badge badge-primary" style="font-size: 10px; font-weight: 700; text-transform: uppercase;">CONTENT EVIDENCE</span>
                            <span style="font-size: 12px; color: var(--text-tertiary);">•</span>
                            <span style="font-size: 12px; color: var(--text-secondary);">Real Crawl Verification</span>
                        </div>
                        <h3 style="font-size: 18px; font-weight: 700; color: var(--text-primary, #f8fafc); margin: 0;" id="modal-kw-title">
                            "${escapeHtml(keywordText || 'Keyword')}" Content Occurrences
                        </h3>
                    </div>
                    <button id="btn-close-kw-evidence-x" type="button" style="background: none; border: none; font-size: 22px; color: var(--text-tertiary); cursor: pointer; padding: 4px; line-height: 1;">&times;</button>
                </div>

                <!-- BODY -->
                <div id="kw-evidence-body" style="padding: 24px; overflow-y: auto; flex: 1;">
                    <div style="padding: 40px; text-align: center; color: var(--text-secondary);">
                        <span class="crawl-spinner" style="width: 20px; height: 20px; border-width: 3px; display: inline-block; vertical-align: middle; margin-right: 8px;"></span>
                        Scanning crawl snapshot for real on-page keyword evidence...
                    </div>
                </div>

                <!-- FOOTER -->
                <div style="padding: 14px 24px; border-top: 1px solid var(--border, #334155); background: var(--bg-subtle, #1e293b); display: flex; justify-content: space-between; align-items: center;">
                    <div id="kw-evidence-summary" style="font-size: 12px; color: var(--text-secondary);"></div>
                    <button id="btn-close-kw-evidence" class="btn btn-secondary btn-sm" type="button">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modalRoot);

        const closeModal = () => modalRoot.remove();
        document.getElementById('btn-close-kw-evidence-x')?.addEventListener('click', closeModal);
        document.getElementById('btn-close-kw-evidence')?.addEventListener('click', closeModal);
        modalRoot.addEventListener('click', (e) => {
            if (e.target === modalRoot) closeModal();
        });

        // Fetch real evidence
        try {
            const url = keywordId 
                ? `/api/projects/${targetProjectId}/keywords/${keywordId}/evidence`
                : `/api/projects/${targetProjectId}/keywords/evidence?keyword=${encodeURIComponent(keywordText)}`;
            
            const res = await apiClient.get(url);
            const evidenceItems = res.evidence || [];
            const totalFreq = res.total_frequency || 0;
            const pagesCount = res.pages_count || 0;

            const bodyEl = document.getElementById('kw-evidence-body');
            const summaryEl = document.getElementById('kw-evidence-summary');

            if (summaryEl) {
                summaryEl.innerHTML = `Total Occurrences: <strong style="color: var(--text-primary);">${totalFreq}</strong> across <strong style="color: var(--text-primary);">${pagesCount}</strong> page${pagesCount === 1 ? '' : 's'}`;
            }

            if (!bodyEl) return;

            if (evidenceItems.length === 0) {
                bodyEl.innerHTML = `
                    <div style="padding: 40px 20px; text-align: center; color: var(--text-secondary);">
                        <div style="width: 48px; height: 48px; border-radius: 12px; background: var(--bg-subtle); color: var(--text-tertiary); display: flex; align-items: center; justify-content: center; margin: 0 auto 16px;">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        </div>
                        <h4 style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">No Occurrences in Latest Crawl</h4>
                        <p style="font-size: 13px; max-width: 480px; margin: 0 auto; line-height: 1.5;">
                            This keyword was not found in the HTML titles, headings, body text, image alt tags, or structured data of the latest scan.
                            Run a website scan to refresh crawl evidence.
                        </p>
                    </div>
                `;
                return;
            }

            const getLocationBadge = (loc) => {
                const l = (loc || '').toLowerCase();
                if (l.includes('title')) return `<span class="badge badge-primary" style="font-size: 10px;">Page Title</span>`;
                if (l.includes('meta')) return `<span class="badge badge-info" style="font-size: 10px;">Meta Description</span>`;
                if (l === 'h1') return `<span class="badge badge-success" style="font-size: 10px;">H1 Heading</span>`;
                if (l.includes('h2') || l.includes('h3')) return `<span class="badge badge-secondary" style="font-size: 10px;">${loc}</span>`;
                if (l.includes('first')) return `<span class="badge badge-warning" style="font-size: 10px;">First Paragraph</span>`;
                if (l.includes('image')) return `<span class="badge badge-info" style="font-size: 10px;">Image Alt</span>`;
                if (l.includes('anchor')) return `<span class="badge badge-secondary" style="font-size: 10px;">Anchor Text</span>`;
                if (l.includes('schema')) return `<span class="badge badge-primary" style="font-size: 10px;">Schema</span>`;
                return `<span class="badge badge-secondary" style="font-size: 10px;">Body Content</span>`;
            };

            const rowsHtml = evidenceItems.map(item => `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 12px 16px; vertical-align: top;">
                        <a href="${escapeHtml(item.page_url)}" target="_blank" style="font-size: 12.5px; font-weight: 600; color: var(--primary); text-decoration: none; display: block; margin-bottom: 2px;">
                            ${escapeHtml(item.page_title || item.page_url)}
                        </a>
                        <span style="font-family: monospace; font-size: 11px; color: var(--text-tertiary); word-break: break-all;">
                            ${escapeHtml(item.page_url)}
                        </span>
                    </td>
                    <td style="padding: 12px 16px; vertical-align: top; white-space: nowrap;">
                        ${getLocationBadge(item.location)}
                    </td>
                    <td style="padding: 12px 16px; vertical-align: top; font-weight: 700; text-align: center; color: var(--text-primary);">
                        ${item.occurrences}
                    </td>
                    <td style="padding: 12px 16px; vertical-align: top;">
                        <div style="font-size: 12px; color: var(--text-secondary); background: var(--bg-subtle); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border); font-family: sans-serif; line-height: 1.4;">
                            ${escapeHtml(item.snippet || item.location)}
                        </div>
                    </td>
                </tr>
            `).join('');

            bodyEl.innerHTML = `
                <div style="margin-bottom: 16px;">
                    <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">
                        Found <strong style="color: var(--text-primary);">${totalFreq} occurrences</strong> of "<strong>${escapeHtml(res.keyword)}</strong>" across ${pagesCount} crawled page${pagesCount === 1 ? '' : 's'}.
                    </div>
                </div>

                <div style="overflow-x: auto; border: 1px solid var(--border); border-radius: 10px;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; color: var(--text-secondary);">
                                <th style="padding: 10px 16px;">Page</th>
                                <th style="padding: 10px 16px;">Location</th>
                                <th style="padding: 10px 16px; text-align: center;">Occurrences</th>
                                <th style="padding: 10px 16px;">Evidence / Snippet</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rowsHtml}
                        </tbody>
                    </table>
                </div>
            `;
        } catch (err) {
            const bodyEl = document.getElementById('kw-evidence-body');
            if (bodyEl) {
                bodyEl.innerHTML = `
                    <div style="padding: 24px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #ef4444; font-size: 13px;">
                        <strong>Error loading keyword evidence:</strong> ${escapeHtml(err.message || 'Unable to load evidence data.')}
                    </div>
                `;
            }
        }
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
