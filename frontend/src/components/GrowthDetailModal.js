/**
 * GrowthDetailModal.js
 * Universal Reusable Detail Drawer / Modal for Growth SEO Intelligence.
 * 
 * Supports:
 * - Link Record Detail (Internal & Outbound External Links) with exact DOM location, headings, paragraph, context, and HTML snippet.
 * - Broken Link Detail with complete source pages list and drill-down.
 * - Redirect Chain Detail.
 * - Ranking Keyword Detail with historical movement.
 * - Growth Opportunity Detail with deterministic crawl evidence, status lifecycle picker, and optional AI solution.
 */

import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';
import { SolveWithAIModal } from './SolveWithAIModal.js';

export class GrowthDetailModal {
    static getRoot() {
        let root = document.getElementById('growth-detail-modal-root');
        if (!root) {
            root = document.createElement('div');
            root.id = 'growth-detail-modal-root';
            document.body.appendChild(root);
        }
        return root;
    }

    static close() {
        const root = document.getElementById('growth-detail-modal-root');
        if (root) root.innerHTML = '';
    }

    static escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /**
     * Helper to render basic modal frame
     */
    static renderFrame({ title, subtitle, badgeHtml, bodyHtml, footerHtml }) {
        const root = this.getRoot();
        root.innerHTML = `
            <div style="position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 9999; padding: 16px;">
                <div class="card" style="width: 100%; max-width: 780px; max-height: 90vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 14px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); border: 1px solid var(--border); overflow: hidden; animation: growthModalFadeIn 0.2s ease-out;">
                    <!-- HEADER -->
                    <div style="padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: var(--bg-subtle);">
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            <h2 style="font-size: 16px; font-weight: 700; margin: 0; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                                ${title}
                            </h2>
                            ${badgeHtml || ''}
                        </div>
                        <button id="btn-close-growth-modal" style="background: none; border: none; font-size: 20px; color: var(--text-secondary); cursor: pointer; padding: 4px 8px; line-height: 1; border-radius: 6px;" title="Close (Esc)">✕</button>
                    </div>

                    ${subtitle ? `<div style="padding: 8px 20px; background: rgba(0,0,0,0.02); border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text-secondary);">${subtitle}</div>` : ''}

                    <!-- BODY -->
                    <div style="padding: 20px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 16px; font-size: 13px; color: var(--text-primary);">
                        ${bodyHtml}
                    </div>

                    <!-- FOOTER -->
                    ${footerHtml ? `
                        <div style="padding: 12px 20px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: flex-end; align-items: center; gap: 10px;">
                            ${footerHtml}
                        </div>
                    ` : ''}
                </div>
            </div>
            <style>
                @keyframes growthModalFadeIn {
                    from { opacity: 0; transform: scale(0.97); }
                    to { opacity: 1; transform: scale(1); }
                }
            </style>
        `;

        const closeBtn = root.querySelector('#btn-close-growth-modal');
        if (closeBtn) closeBtn.onclick = () => this.close();

        // Close on background click
        root.firstElementChild.addEventListener('click', (e) => {
            if (e.target === root.firstElementChild) this.close();
        });

        // Close on Escape
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.close();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    /**
     * 1. LINK DETAIL MODAL
     * Displays complete link metadata: Source, Target, Anchor, Rel, Status, Section, Nearest Heading, Paragraph, Context & HTML snippet.
     */
    static showLinkDetail(link) {
        if (!link) return;

        const isInternal = link.is_internal !== undefined ? link.is_internal : (link.link_type === 'internal');
        const scopeLabel = isInternal ? 'Internal Link' : 'External Link';
        const scopeBadge = isInternal
            ? `<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); font-weight: 700;">INTERNAL</span>`
            : `<span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); font-weight: 700;">EXTERNAL</span>`;

        const statusCode = link.status_code !== undefined ? link.status_code : (link.target_status_code || 200);
        let statusBadgeClass = 'badge-success';
        if (statusCode >= 400 || statusCode === 0) statusBadgeClass = 'badge-critical';
        else if (statusCode >= 300) statusBadgeClass = 'badge-warning';

        const statusLabel = statusCode === 0 ? 'Unreachable' : `HTTP ${statusCode}`;

        const safeSource = this.escapeHtml(link.source_page || link.source || 'Not Available');
        const safeTarget = this.escapeHtml(link.target_page || link.target || link.url || 'Not Available');
        const safeAnchor = this.escapeHtml(link.anchor_text || '(Empty / Image Link)');
        const section = link.source_section || link.section || 'Not Available';
        const heading = link.nearest_heading ? `${this.escapeHtml(link.nearest_heading)} ${link.heading_level ? `<span style="font-size: 11px; opacity: 0.7;">(${link.heading_level.toUpperCase()})</span>` : ''}` : 'Not Available';
        const paragraph = link.paragraph_index !== undefined && link.paragraph_index !== null ? `Paragraph #${link.paragraph_index + 1}` : 'Not Available';
        const sentence = link.sentence_index !== undefined && link.sentence_index !== null ? `Sentence #${link.sentence_index + 1}` : 'Not Available';
        const rel = link.rel || (link.is_nofollow ? 'nofollow' : 'follow') || 'follow';
        const targetType = link.target_type || (safeTarget.endsWith('.pdf') ? 'PDF Document' : (safeTarget.match(/\.(jpg|jpeg|png|webp|svg)$/i) ? 'Image' : 'HTML Page'));

        const contextBefore = link.context_before ? this.escapeHtml(link.context_before) : '';
        const contextText = link.context_text ? this.escapeHtml(link.context_text) : '';
        const contextAfter = link.context_after ? this.escapeHtml(link.context_after) : '';
        const htmlSnippet = link.html_snippet ? this.escapeHtml(link.html_snippet) : '';

        const bodyHtml = `
            <!-- URL SUMMARY CARDS -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                <div style="background: var(--bg-subtle); padding: 12px 14px; border-radius: 8px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px;">Source Page</div>
                    <div style="font-family: monospace; font-size: 12px; color: var(--primary); word-break: break-all;">
                        <a href="${safeSource}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: none;">${safeSource} ↗</a>
                    </div>
                </div>
                <div style="background: var(--bg-subtle); padding: 12px 14px; border-radius: 8px; border: 1px solid var(--border);">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px;">Target Destination</div>
                    <div style="font-family: monospace; font-size: 12px; color: ${statusCode >= 400 || statusCode === 0 ? '#ef4444' : 'var(--text-primary)'}; word-break: break-all;">
                        <a href="${safeTarget}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">${safeTarget} ↗</a>
                    </div>
                </div>
            </div>

            <!-- LINK PROPERTIES GRID -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border);">
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">HTTP Status</div>
                    <div style="margin-top: 4px;"><span class="badge ${statusBadgeClass}" style="font-size: 11px;">${statusLabel}</span></div>
                </div>
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Link Scope</div>
                    <div style="margin-top: 4px;">${scopeBadge}</div>
                </div>
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Rel Attribute</div>
                    <div style="margin-top: 4px; font-family: monospace; font-size: 12px; font-weight: 600;">${rel}</div>
                </div>
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Target Content Type</div>
                    <div style="margin-top: 4px; font-size: 12px;">${targetType}</div>
                </div>
            </div>

            <!-- ANCHOR TEXT -->
            <div style="background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border);">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px;">Anchor Text</div>
                <div style="font-size: 13.5px; font-weight: 600; color: var(--text-primary);">${safeAnchor}</div>
            </div>

            <!-- EXACT DOM LOCATION -->
            <div>
                <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">DOM & Page Location</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; background: var(--bg-card); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border);">
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Section</div>
                        <div style="font-weight: 600; font-size: 12.5px; margin-top: 2px;">${section}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Nearest Heading</div>
                        <div style="font-weight: 600; font-size: 12.5px; margin-top: 2px;">${heading}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Paragraph</div>
                        <div style="font-weight: 600; font-size: 12.5px; margin-top: 2px;">${paragraph}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Sentence</div>
                        <div style="font-weight: 600; font-size: 12.5px; margin-top: 2px;">${sentence}</div>
                    </div>
                </div>
            </div>

            <!-- CONTEXT SURROUNDING LINK -->
            ${(contextBefore || contextText || contextAfter) ? `
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Surrounding Text Context</div>
                    <div style="background: var(--bg-card); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); font-size: 13px; line-height: 1.6; color: var(--text-secondary); font-style: italic;">
                        ${contextBefore ? `...${contextBefore} ` : ''}
                        <mark style="background: rgba(59, 130, 246, 0.2); color: var(--primary); padding: 2px 4px; border-radius: 4px; font-weight: 600; font-style: normal;">${contextText || safeAnchor}</mark>
                        ${contextAfter ? ` ${contextAfter}...` : ''}
                    </div>
                </div>
            ` : `
                <div style="padding: 10px 14px; background: var(--bg-subtle); border-radius: 8px; border: 1px solid var(--border); font-size: 12px; color: var(--text-secondary);">
                    Surrounding sentence context not recorded during crawl.
                </div>
            `}

            <!-- RAW HTML SNIPPET -->
            ${htmlSnippet ? `
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;">Extracted Link HTML</div>
                    <div style="background: #0f172a; color: #38bdf8; padding: 12px 14px; border-radius: 8px; font-family: monospace; font-size: 12px; overflow-x: auto; border: 1px solid rgba(255,255,255,0.1); white-space: pre-wrap; word-break: break-all;">${htmlSnippet}</div>
                </div>
            ` : ''}
        `;

        const footerHtml = `
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('growth-detail-modal-root').innerHTML=''">Close</button>
        `;

        this.renderFrame({
            title: 'Link Record Evidence',
            subtitle: `${scopeLabel} Verification`,
            badgeHtml: scopeBadge,
            bodyHtml,
            footerHtml
        });
    }

    /**
     * 2. BROKEN LINK DETAIL MODAL
     * Displays target broken URL, error reason, HTTP status, and all source pages where this broken link was found.
     */
    static showBrokenLinkDetail(brokenItem, allBrokenRecords = []) {
        if (!brokenItem) return;

        const targetUrl = brokenItem.target || brokenItem.url || '';
        const statusCode = brokenItem.status_code || 0;
        const isInternal = brokenItem.link_type === 'internal';
        const errorType = brokenItem.error_type || (statusCode === 404 ? '404 Not Found' : (statusCode >= 500 ? 'Server Error' : 'Unreachable'));

        // Filter all records with matching target URL to show all sources
        const sourceMatches = allBrokenRecords.filter(r => (r.target || r.url) === targetUrl);
        const sourcePages = sourceMatches.length > 0 ? sourceMatches : [brokenItem];

        const safeTarget = this.escapeHtml(targetUrl);

        let sourcesHtml = sourcePages.map((src, idx) => {
            const safeSrc = this.escapeHtml(src.source || src.source_page || 'Unknown Source Page');
            const safeAnc = this.escapeHtml(src.anchor_text || '(No Anchor Text)');
            const section = src.source_section || 'Main Content';
            const heading = src.nearest_heading ? this.escapeHtml(src.nearest_heading) : 'Not Available';
            const paragraph = src.paragraph_index !== undefined && src.paragraph_index !== null ? `P #${src.paragraph_index + 1}` : 'N/A';

            return `
                <tr style="border-bottom: 1px solid var(--border);">
                    <td style="padding: 10px 14px;">
                        <div style="font-family: monospace; font-size: 12px; color: var(--primary); word-break: break-all;">
                            ${safeSrc}
                        </div>
                    </td>
                    <td style="padding: 10px 14px; font-weight: 500; font-size: 12.5px;">${safeAnc}</td>
                    <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">${section}</td>
                    <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">${heading}</td>
                    <td style="padding: 10px 14px; font-size: 12px; color: var(--text-secondary);">${paragraph}</td>
                    <td style="padding: 10px 14px; text-align: right;">
                        <button class="btn btn-secondary btn-sm btn-inspect-broken-source" data-src-idx="${idx}" style="font-size: 11px; padding: 3px 8px;">
                            Inspect Link
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        const bodyHtml = `
            <!-- TARGET STATUS BANNER -->
            <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.3); padding: 14px 18px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: #ef4444; text-transform: uppercase;">Broken Target Destination</div>
                    <div style="font-family: monospace; font-size: 13px; font-weight: 700; color: #ef4444; word-break: break-all; margin-top: 4px;">
                        ${safeTarget}
                    </div>
                </div>
                <div style="display: flex; gap: 8px; align-items: center;">
                    <span class="badge badge-critical" style="font-size: 12px; font-weight: 700;">HTTP ${statusCode || 'Dead'}</span>
                    <span class="badge" style="background: ${isInternal ? 'rgba(59,130,246,0.15)' : 'rgba(168,85,247,0.15)'}; color: ${isInternal ? '#3b82f6' : '#c084fc'}; font-size: 11px; font-weight: 700;">${isInternal ? 'INTERNAL' : 'EXTERNAL'}</span>
                </div>
            </div>

            <!-- SOURCE PAGES COUNT -->
            <div>
                <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 8px;">
                    Found on ${sourcePages.length} Source Page${sourcePages.length === 1 ? '' : 's'}:
                </div>
                <div style="background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border); overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                        <thead>
                            <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; color: var(--text-secondary);">
                                <th style="padding: 10px 14px;">Source Page URL</th>
                                <th style="padding: 10px 14px;">Anchor</th>
                                <th style="padding: 10px 14px;">Location</th>
                                <th style="padding: 10px 14px;">Heading</th>
                                <th style="padding: 10px 14px;">Paragraph</th>
                                <th style="padding: 10px 14px; text-align: right;">Evidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${sourcesHtml}
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        const footerHtml = `
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('growth-detail-modal-root').innerHTML=''">Close</button>
        `;

        this.renderFrame({
            title: 'Broken Link Evidence',
            subtitle: `Error Trace: ${errorType}`,
            badgeHtml: `<span class="badge badge-critical">${sourcePages.length} Broken Reference${sourcePages.length === 1 ? '' : 's'}</span>`,
            bodyHtml,
            footerHtml
        });

        // Bind source inspection buttons
        const root = this.getRoot();
        root.querySelectorAll('.btn-inspect-broken-source').forEach(btn => {
            btn.onclick = () => {
                const idx = parseInt(btn.getAttribute('data-src-idx'), 10);
                const record = sourcePages[idx];
                if (record) GrowthDetailModal.showLinkDetail(record);
            };
        });
    }

    /**
     * 2B. GROUPED LINK DETAIL MODAL (External Links, Broken Links, Internal Links)
     * Displays target destination overview, status, Content-Type, final URL / redirect chain,
     * and list of all source pages with exact DOM locations, nearest headings, paragraph/sentence indices,
     * surrounding text context, and HTML snippet.
     */
    static showGroupedLinkDetail(item, tabType = 'external-links') {
        if (!item) return;

        const targetUrl = item.destination_url || item.target_url || item.target || item.url || '';
        const domain = item.destination_domain || (targetUrl ? (() => { try { return new URL(targetUrl).hostname; } catch(e) { return ''; } })() : '');
        const isInternal = item.link_scope === 'internal' || tabType === 'internal-links' || item.link_type === 'internal';
        const isBroken = Boolean(item.is_broken || tabType === 'broken-links' || (item.status_code && (item.status_code >= 400 || item.status_code === 0)));
        
        const rawStatus = item.status || (item.status_code ? `HTTP ${item.status_code}` : 'Not Checked');
        const statusCode = item.status_code !== undefined && item.status_code !== null ? item.status_code : (item.destination_status_code || 0);
        const rawContentType = item.type || item.content_type || 'Not Checked';
        const contentType = rawContentType.includes('/') ? (rawContentType.includes('html') ? 'HTML' : (rawContentType.includes('pdf') ? 'PDF' : rawContentType)) : rawContentType;
        const finalUrl = item.final_url || targetUrl;
        const redirectChain = Array.isArray(item.redirect_chain) ? item.redirect_chain : [];
        const occurrences = Array.isArray(item.occurrences_list) ? item.occurrences_list : [];
        const sourcePagesCount = item.source_pages || item.no_pages || (new Set(occurrences.map(o => o.source_url || o.source_page || o.source))).size || 1;
        const occurrencesCount = item.occurrences || item.total_occurrences || occurrences.length || 1;

        const safeTarget = this.escapeHtml(targetUrl);
        const safeFinal = this.escapeHtml(finalUrl);

        // Status badge
        let statusBadgeHtml = '';
        if (rawStatus === 'Not Checked' || rawStatus === 'Not Available') {
            statusBadgeHtml = `<span class="badge" style="background: rgba(148, 163, 184, 0.15); color: var(--text-secondary); border: 1px solid var(--border); font-weight: 600; font-size: 11px;">Not Checked</span>`;
        } else if (isBroken || (typeof statusCode === 'number' && (statusCode >= 400 || statusCode === 0))) {
            statusBadgeHtml = `<span class="badge badge-critical" style="font-weight: 700; font-size: 11px;">${this.escapeHtml(rawStatus)}</span>`;
        } else if (String(rawStatus).includes('Redirect') || (typeof statusCode === 'number' && statusCode >= 300 && statusCode < 400)) {
            statusBadgeHtml = `<span class="badge badge-warning" style="font-weight: 700; font-size: 11px;">${this.escapeHtml(rawStatus)}</span>`;
        } else {
            statusBadgeHtml = `<span class="badge badge-success" style="font-weight: 700; font-size: 11px;">${this.escapeHtml(rawStatus)}</span>`;
        }

        const scopeBadge = isInternal
            ? `<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); font-weight: 700; font-size: 11px;">INTERNAL</span>`
            : `<span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); font-weight: 700; font-size: 11px;">EXTERNAL</span>`;

        let modalTitle = 'External Link Details';
        if (tabType === 'broken-links' || isBroken) modalTitle = 'Broken Link Details';
        else if (isInternal) modalTitle = 'Internal Link Details';

        // Occurrence items renderer
        let occurrencesHtml = '';
        if (occurrences.length === 0) {
            occurrencesHtml = `
                <div style="padding: 24px; text-align: center; color: var(--text-secondary); background: var(--bg-card); border-radius: 8px; border: 1px solid var(--border);">
                    No individual source page occurrences recorded for this link.
                </div>
            `;
        } else {
            occurrencesHtml = `
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    ${occurrences.map((occ, idx) => {
                        const safeSrc = this.escapeHtml(occ.source_url || occ.source_page || occ.source || 'Unknown Page');
                        const safeAnc = this.escapeHtml(occ.anchor_text || occ.anchor || '(Empty Anchor)');
                        const heading = occ.nearest_heading ? `${this.escapeHtml(occ.nearest_heading)} ${occ.heading_level ? `<span style="font-size: 10px; opacity: 0.75;">(${occ.heading_level.toUpperCase()})</span>` : ''}` : 'Not available';
                        const section = occ.source_section || 'Main Content';
                        
                        let locStr = 'Not available';
                        if (occ.paragraph_index !== undefined && occ.paragraph_index !== null) {
                            locStr = `Paragraph ${occ.paragraph_index + 1}`;
                            if (occ.sentence_index !== undefined && occ.sentence_index !== null) {
                                locStr += `, Sentence ${occ.sentence_index + 1}`;
                            }
                        }

                        const occRel = occ.rel || 'follow';
                        const occType = occ.type || contentType;
                        const contextBefore = occ.context_before ? this.escapeHtml(occ.context_before) : '';
                        const contextText = occ.context_text ? this.escapeHtml(occ.context_text) : '';
                        const contextAfter = occ.context_after ? this.escapeHtml(occ.context_after) : '';
                        const htmlSnippet = occ.html_snippet ? this.escapeHtml(occ.html_snippet) : '';

                        return `
                            <div class="card" style="padding: 16px; background: var(--bg-card); border-radius: 10px; border: 1px solid var(--border);">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 12px; flex-wrap: wrap;">
                                    <div style="flex: 1; min-width: 220px;">
                                        <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em;">Source Page #${idx + 1}</div>
                                        <div style="font-family: monospace; font-size: 12.5px; font-weight: 600; color: var(--primary); word-break: break-all; margin-top: 3px;">
                                            <a href="${safeSrc}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">${safeSrc} ↗</a>
                                        </div>
                                    </div>
                                    <div style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                                        <span class="badge badge-secondary" style="font-size: 10.5px; font-family: monospace;">rel="${this.escapeHtml(occRel)}"</span>
                                        <span class="badge" style="background: rgba(59, 130, 246, 0.1); color: #3b82f6; font-size: 10.5px; font-weight: 600;">${this.escapeHtml(occType)}</span>
                                    </div>
                                </div>

                                <!-- DOM LOCATION METADATA GRID -->
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; background: var(--bg-subtle); padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 12px;">
                                    <div>
                                        <div style="color: var(--text-tertiary); font-size: 10.5px; font-weight: 700; text-transform: uppercase;">Anchor Text</div>
                                        <div style="font-weight: 600; color: var(--text-primary); margin-top: 2px;">${safeAnc}</div>
                                    </div>
                                    <div>
                                        <div style="color: var(--text-tertiary); font-size: 10.5px; font-weight: 700; text-transform: uppercase;">Nearest Heading</div>
                                        <div style="font-weight: 600; color: var(--text-primary); margin-top: 2px;">${heading}</div>
                                    </div>
                                    <div>
                                        <div style="color: var(--text-tertiary); font-size: 10.5px; font-weight: 700; text-transform: uppercase;">DOM & Page Location</div>
                                        <div style="font-weight: 600; color: var(--text-primary); margin-top: 2px;">${locStr}</div>
                                    </div>
                                    <div>
                                        <div style="color: var(--text-tertiary); font-size: 10.5px; font-weight: 700; text-transform: uppercase;">DOM Section</div>
                                        <div style="font-weight: 600; color: var(--text-primary); margin-top: 2px;">${this.escapeHtml(section)}</div>
                                    </div>
                                </div>

                                <!-- SURROUNDING CONTEXT -->
                                <div style="margin-bottom: 10px;">
                                    <div style="color: var(--text-tertiary); font-size: 10.5px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px;">Context / Evidence</div>
                                    ${(contextBefore || contextText || contextAfter) ? `
                                        <div style="background: rgba(0,0,0,0.03); border-left: 3px solid var(--primary); padding: 8px 12px; font-size: 12px; color: var(--text-secondary); line-height: 1.5; font-style: italic; border-radius: 0 6px 6px 0;">
                                            ${contextBefore ? `...${contextBefore} ` : ''}
                                            <mark style="background: rgba(59, 130, 246, 0.25); color: var(--primary); padding: 1px 5px; border-radius: 3px; font-weight: 700; font-style: normal;">${contextText || safeAnc}</mark>
                                            ${contextAfter ? ` ${contextAfter}...` : ''}
                                        </div>
                                    ` : `
                                        <div style="font-size: 11.5px; color: var(--text-tertiary); font-style: italic;">Surrounding context unavailable</div>
                                    `}
                                </div>

                                <!-- EXTRACTED HTML SNIPPET -->
                                <div>
                                    <div style="color: var(--text-tertiary); font-size: 10.5px; font-weight: 700; text-transform: uppercase; margin-bottom: 4px;">HTML / DOM Evidence</div>
                                    ${htmlSnippet ? `
                                        <div style="background: #0f172a; color: #38bdf8; padding: 8px 12px; border-radius: 6px; font-family: monospace; font-size: 11.5px; overflow-x: auto; white-space: pre-wrap; word-break: break-all;">${htmlSnippet}</div>
                                    ` : `
                                        <div style="font-size: 11.5px; color: var(--text-tertiary); font-style: italic;">HTML snippet unavailable</div>
                                    `}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }

        const bodyHtml = `
            <!-- DESTINATION SUMMARY BANNER -->
            <div style="background: var(--bg-subtle); border: 1px solid var(--border); padding: 16px 20px; border-radius: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 14px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 260px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em;">Destination URL</div>
                        <div style="font-family: monospace; font-size: 14px; font-weight: 700; color: var(--primary); word-break: break-all; margin-top: 4px;">
                            <a href="${safeTarget}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">${safeTarget} ↗</a>
                        </div>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                        ${scopeBadge}
                        ${statusBadgeHtml}
                        <span class="badge badge-secondary" style="font-size: 11px; font-weight: 600;">Type: ${this.escapeHtml(contentType)}</span>
                    </div>
                </div>

                <!-- METRICS STRIP -->
                <div style="display: flex; gap: 16px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); font-size: 12.5px; flex-wrap: wrap;">
                    <div>
                        <span style="color: var(--text-secondary);">Total Source Pages:</span>
                        <strong style="color: var(--text-primary); margin-left: 4px;">${sourcePagesCount}</strong>
                    </div>
                    <div>
                        <span style="color: var(--text-secondary);">Total Occurrences:</span>
                        <strong style="color: #3b82f6; margin-left: 4px;">${occurrencesCount}</strong>
                    </div>
                    ${domain ? `
                        <div>
                            <span style="color: var(--text-secondary);">Domain:</span>
                            <span style="font-family: monospace; color: var(--text-primary); margin-left: 4px;">${this.escapeHtml(domain)}</span>
                        </div>
                    ` : ''}
                </div>

                ${(finalUrl && finalUrl !== targetUrl) ? `
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border); font-size: 12px;">
                        <span style="font-weight: 700; color: #f59e0b;">Final Resolved URL (Redirected):</span>
                        <span style="font-family: monospace; color: var(--text-primary); margin-left: 6px; word-break: break-all;">${safeFinal}</span>
                    </div>
                ` : ''}

                ${redirectChain.length > 1 ? `
                    <div style="margin-top: 8px; font-size: 11.5px; color: var(--text-secondary);">
                        <span style="font-weight: 600;">Redirect Chain:</span>
                        <div style="margin-top: 4px; display: flex; flex-direction: column; gap: 2px;">
                            ${redirectChain.map((hop, hIdx) => `
                                <div style="font-family: monospace; font-size: 11px; color: var(--text-primary);">
                                    <span style="color: var(--text-secondary);">${hIdx + 1}.</span> [HTTP ${hop.status_code || 200}] ${this.escapeHtml(hop.url || hop)}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>

            <!-- SOURCE PAGES & OCCURRENCES SECTION TITLE -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em;">
                    Found on ${sourcePagesCount} Source Page${sourcePagesCount === 1 ? '' : 's'} (${occurrencesCount} Total Occurrence${occurrencesCount === 1 ? '' : 's'}):
                </div>
            </div>

            <!-- OCCURRENCES LIST -->
            ${occurrencesHtml}
        `;

        const footerHtml = `
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('growth-detail-modal-root').innerHTML=''">Close</button>
        `;

        this.renderFrame({
            title: modalTitle,
            subtitle: domain ? `Destination Domain: ${domain}` : '',
            badgeHtml: `<span class="badge badge-secondary">${occurrencesCount} Occurrence${occurrencesCount === 1 ? '' : 's'}</span>`,
            bodyHtml,
            footerHtml
        });

        // Bind drill-down buttons
        const root = this.getRoot();
        root.querySelectorAll('.btn-drilldown-occurrence').forEach(btn => {
            btn.onclick = () => {
                const idx = parseInt(btn.getAttribute('data-occ-idx'), 10);
                const occ = occurrences[idx];
                if (occ) GrowthDetailModal.showLinkDetail(occ);
            };
        });
    }

    /**
     * 3. REDIRECT DETAIL MODAL
     */
    static showRedirectDetail(redirectItem) {
        if (!redirectItem) return;

        const origUrl = redirectItem.url || redirectItem.source || '';
        const targetUrl = redirectItem.redirect_target || redirectItem.target || '';
        const statusCode = redirectItem.status_code || 301;
        const hopCount = redirectItem.hop_count || 1;
        const chain = redirectItem.chain || [
            { url: origUrl, status_code: statusCode },
            { url: targetUrl, status_code: 200 }
        ];

        let chainHtml = chain.map((step, idx) => {
            const isLast = idx === chain.length - 1;
            const safeStepUrl = this.escapeHtml(step.url);
            const stepStatus = step.status_code || (isLast ? 200 : 301);

            return `
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 28px; height: 28px; border-radius: 50%; background: ${isLast ? '#10b981' : 'var(--primary)'}; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0;">
                        ${idx + 1}
                    </div>
                    <div style="flex: 1; background: var(--bg-subtle); padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                        <div style="font-family: monospace; font-size: 12px; color: var(--text-primary); word-break: break-all;">
                            ${safeStepUrl}
                        </div>
                        <span class="badge ${isLast ? 'badge-success' : 'badge-warning'}" style="font-size: 11px; font-weight: 700;">
                            HTTP ${stepStatus}
                        </span>
                    </div>
                </div>
                ${!isLast ? `
                    <div style="margin-left: 14px; height: 16px; border-left: 2px dashed var(--border);"></div>
                ` : ''}
            `;
        }).join('');

        const bodyHtml = `
            <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
                Verified Redirect Chain (${hopCount} Hop${hopCount === 1 ? '' : 's'}):
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                ${chainHtml}
            </div>
        `;

        this.renderFrame({
            title: 'Redirect Evidence',
            subtitle: 'Complete Hop Sequence',
            badgeHtml: `<span class="badge badge-warning">HTTP ${statusCode}</span>`,
            bodyHtml,
            footerHtml: `<button class="btn btn-secondary btn-sm" onclick="document.getElementById('growth-detail-modal-root').innerHTML=''">Close</button>`
        });
    }

    /**
     * 4. RANKING DETAIL MODAL
     */
    static showRankingDetail(rankingItem) {
        if (!rankingItem) return;

        const kw = this.escapeHtml(rankingItem.keyword || '');
        const curr = rankingItem.current_position !== undefined ? rankingItem.current_position : (rankingItem.position || 'N/A');
        const prev = rankingItem.previous_position !== undefined ? rankingItem.previous_position : 'N/A';
        const change = rankingItem.change;
        const url = this.escapeHtml(rankingItem.url || rankingItem.target_url || '');
        const vol = rankingItem.search_volume !== undefined ? rankingItem.search_volume : 'Unavailable';
        const src = this.escapeHtml(rankingItem.data_source || rankingItem.source || 'Rank Tracker');

        let changeBadge = `<span class="badge" style="background: var(--bg-subtle); color: var(--text-secondary);">No Previous Snapshot</span>`;
        if (change !== undefined && change !== null) {
            if (change > 0) {
                changeBadge = `<span class="badge badge-success" style="font-weight: 700;">▲ +${change} Positions Improved</span>`;
            } else if (change < 0) {
                changeBadge = `<span class="badge badge-critical" style="font-weight: 700;">▼ ${change} Positions Declined</span>`;
            } else {
                changeBadge = `<span class="badge badge-info" style="font-weight: 700;">No Change</span>`;
            }
        }

        const bodyHtml = `
            <!-- KEYWORD HEADER -->
            <div style="background: var(--bg-subtle); padding: 14px 18px; border-radius: 10px; border: 1px solid var(--border);">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Search Query Keyword</div>
                <div style="font-size: 18px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${kw}</div>
            </div>

            <!-- POSITION CARDS -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                <div style="background: var(--bg-card); padding: 14px; border-radius: 8px; border: 1px solid var(--border); text-align: center;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Current Position</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--primary); margin-top: 4px;">#${curr}</div>
                </div>
                <div style="background: var(--bg-card); padding: 14px; border-radius: 8px; border: 1px solid var(--border); text-align: center;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Previous Position</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--text-secondary); margin-top: 4px;">${prev !== 'N/A' ? `#${prev}` : 'N/A'}</div>
                </div>
                <div style="background: var(--bg-card); padding: 14px; border-radius: 8px; border: 1px solid var(--border); text-align: center;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Search Volume</div>
                    <div style="font-size: 24px; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${vol}</div>
                </div>
            </div>

            <div style="background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border);">
                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px;">Ranking Destination URL</div>
                <div style="font-family: monospace; font-size: 12.5px; color: var(--primary); word-break: break-all;">
                    <a href="${url}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: none;">${url} ↗</a>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-secondary); padding: 0 4px;">
                <div>Data Source: <strong>${src}</strong></div>
                <div>${changeBadge}</div>
            </div>
        `;

        this.renderFrame({
            title: 'Search Ranking Movement',
            subtitle: 'SERP Evidence',
            badgeHtml: changeBadge,
            bodyHtml,
            footerHtml: `<button class="btn btn-secondary btn-sm" onclick="document.getElementById('growth-detail-modal-root').innerHTML=''">Close</button>`
        });
    }

    /**
     * 5. GROWTH OPPORTUNITY DETAIL MODAL
     * Factual evidence + Status lifecycle switcher (persisted) + Optional AI Solution
     */
    static showOpportunityDetail(opp, { onStatusChange, projectId } = {}) {
        if (!opp) return;

        const safeTitle = this.escapeHtml(opp.title || 'Growth Recommendation');
        const safeImpact = this.escapeHtml(opp.impact || opp.why_it_matters || opp.description || 'Not Available');
        const safeRec = this.escapeHtml(opp.recommendation || 'Not Available');
        const safeEvidence = this.escapeHtml(opp.evidence || opp.data_evidence || opp.reason || 'Deterministic Crawl Rule Finding');
        const urls = opp.affected_urls || (opp.target_page ? [opp.target_page] : (opp.source_page ? [opp.source_page] : []));
        const status = opp.status || 'Open';
        const priority = opp.priority_level || opp.priority || 'HIGH';
        const category = opp.category || 'General';

        let prioBadgeStyle = 'background: rgba(239,68,68,0.1); color: var(--critical);';
        if (priority === 'HIGH') prioBadgeStyle = 'background: rgba(245,158,11,0.1); color: var(--warning);';
        else if (priority === 'MEDIUM') prioBadgeStyle = 'background: rgba(59,130,246,0.1); color: var(--primary);';
        else if (priority === 'LOW') prioBadgeStyle = 'background: rgba(16,185,129,0.1); color: #10b981;';

        const bodyHtml = `
            <!-- TITLE & BADGES -->
            <div style="background: var(--bg-subtle); padding: 14px 18px; border-radius: 10px; border: 1px solid var(--border);">
                <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px; flex-wrap: wrap;">
                    <span class="badge" style="${prioBadgeStyle} font-weight: 800; font-size: 11px;">${priority} PRIORITY</span>
                    <span class="badge badge-info" style="font-size: 11px;">${category}</span>
                    <span class="badge" style="background: rgba(16,185,129,0.1); color: #10b981; font-weight: 700; font-size: 11px;">Status: ${status}</span>
                </div>
                <div style="font-size: 16px; font-weight: 700; color: var(--text-primary);">${safeTitle}</div>
            </div>

            <!-- DETERMINISTIC EVIDENCE -->
            <div>
                <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Deterministic Crawl Evidence</div>
                <div style="background: var(--bg-card); border: 1px solid var(--border); padding: 12px 16px; border-radius: 8px; font-size: 13px; color: var(--text-primary); line-height: 1.5;">
                    ${safeEvidence}
                </div>
            </div>

            <!-- WHY IT MATTERS -->
            <div>
                <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Impact & Growth Value</div>
                <div style="background: var(--bg-card); border: 1px solid var(--border); padding: 12px 16px; border-radius: 8px; font-size: 13px; color: var(--text-secondary); line-height: 1.5;">
                    ${safeImpact}
                </div>
            </div>

            <!-- RECOMMENDED ACTION -->
            <div>
                <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Recommended Action</div>
                <div style="background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.2); padding: 12px 16px; border-radius: 8px; font-size: 13.5px; color: var(--primary); font-weight: 600; line-height: 1.5;">
                    ${safeRec}
                </div>
            </div>

            <!-- AFFECTED PAGES -->
            ${urls.length > 0 ? `
                <div>
                    <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">Affected Pages (${urls.length})</div>
                    <div style="max-height: 140px; overflow-y: auto; background: var(--bg-subtle); padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); display: flex; flex-direction: column; gap: 4px;">
                        ${urls.map(u => `<div style="font-family: monospace; font-size: 12px; color: var(--text-primary); word-break: break-all;">${this.escapeHtml(u)}</div>`).join('')}
                    </div>
                </div>
            ` : ''}

            <!-- LIFECYCLE STATUS PICKER -->
            <div style="background: var(--bg-subtle); padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Update Opportunity Status</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">Persists immediately across app reloads.</div>
                </div>
                <div style="display: flex; gap: 6px;">
                    <button class="btn btn-sm ${status === 'Open' ? 'btn-primary' : 'btn-secondary'} btn-opp-status" data-status="Open" style="font-size: 11px;">Open</button>
                    <button class="btn btn-sm ${status === 'In Progress' ? 'btn-primary' : 'btn-secondary'} btn-opp-status" data-status="In Progress" style="font-size: 11px;">In Progress</button>
                    <button class="btn btn-sm ${status === 'Resolved' ? 'btn-primary' : 'btn-secondary'} btn-opp-status" data-status="Resolved" style="font-size: 11px;">Resolved</button>
                    <button class="btn btn-sm ${status === 'Ignored' ? 'btn-primary' : 'btn-secondary'} btn-opp-status" data-status="Ignored" style="font-size: 11px;">Ignored</button>
                </div>
            </div>
        `;

        const footerHtml = `
            <button id="btn-generate-ai-opp" class="btn btn-primary btn-sm" style="display: inline-flex; align-items: center; gap: 6px;">
                ✨ Generate AI Solution
            </button>
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('growth-detail-modal-root').innerHTML=''">Close</button>
        `;

        this.renderFrame({
            title: 'Actionable SEO Opportunity',
            subtitle: 'Traceable Growth Evidence',
            badgeHtml: `<span class="badge badge-info">${category}</span>`,
            bodyHtml,
            footerHtml
        });

        const root = this.getRoot();

        // Status update handlers
        root.querySelectorAll('.btn-opp-status').forEach(btn => {
            btn.onclick = async () => {
                const newStatus = btn.getAttribute('data-status');
                if (onStatusChange) {
                    await onStatusChange(opp.id, newStatus);
                    opp.status = newStatus;
                    GrowthDetailModal.showOpportunityDetail(opp, { onStatusChange, projectId });
                }
            };
        });

        // Generate AI Solution button
        const btnAi = root.querySelector('#btn-generate-ai-opp');
        if (btnAi) {
            btnAi.onclick = () => {
                SolveWithAIModal.open({
                    projectId: projectId || projectStore.getSelectedProjectId(),
                    ruleId: opp.rule_id || 'OPPORTUNITY_FIX',
                    title: opp.title,
                    category: opp.category,
                    severity: opp.priority_level,
                    description: opp.impact || opp.description,
                    recommendation: opp.recommendation,
                    affectedUrl: urls[0] || '',
                    evidenceText: opp.evidence || opp.impact
                });
            };
        }
    }
}
