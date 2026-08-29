/**
 * Checks Performed Detail Modal Component
 * Renders an explicit breakdown of all audit checks and rules evaluated across scanned pages.
 */
export class ChecksPerformedDetailModal {
    static open({ totalAuditedPages, htmlPagesCount, evaluatedRulesCount, totalChecks, checksExplanation, categoryTable, onSelectCategory, domain }) {
        const existing = document.getElementById('checks-performed-modal-root');
        if (existing) existing.remove();

        const ruleDescriptions = {
            "Crawlability": "Verifies HTTP status codes, server access, 4xx/5xx errors, and Cloudflare/WAF block status.",
            "Indexability": "Evaluates meta robots noindex directives, robots.txt exclusions, and search engine discoverability.",
            "HTTPS": "Scans for unencrypted HTTP pages, mixed content warnings, and secure transport protocol compliance.",
            "Metadata": "Validates HTML title tags, meta descriptions, length boundaries, and duplicate metadata.",
            "Content": "Detects thin content (<150 words), low text-to-HTML ratio, and missing readable body text.",
            "Headings": "Inspects H1 heading tag presence, structure hierarchy, and missing or duplicate primary headings.",
            "Canonicals": "Checks rel='canonical' tag implementation, self-referential addresses, and canonical mismatches.",
            "Images": "Scans image elements for missing alt descriptions required for accessibility and image search.",
            "Internal Links": "Analyzes internal linking, orphan pages, broken internal links, and link depth hierarchy.",
            "External Links": "Inspects outbound external links, rel attributes (nofollow/sponsored/ugc), and broken outbound targets.",
            "Structured Data": "Verifies Schema.org JSON-LD structured data markups for rich snippet search eligibility.",
            "Mobile": "Checks mobile viewport meta tags and responsive layout readiness.",
            "International SEO": "Evaluates hreflang language annotations and international targeting setup.",
            "Security": "Verifies SSL/TLS certificate validity, expiration, and trusted CA authority verification.",
            "Performance": "Evaluates PageSpeed loading performance (requires PageSpeed API key configured in Integrations)."
        };

        const modalRoot = document.createElement('div');
        modalRoot.id = 'checks-performed-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(5px); display: flex; align-items: center;
            justify-content: center; z-index: 9999; padding: 20px;
        `;

        modalRoot.innerHTML = `
            <div class="card" style="width: 100%; max-width: 860px; max-height: 90vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); overflow: hidden;">
                
                <!-- MODAL HEADER -->
                <div style="padding: 20px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">AUDIT RULE BREAKDOWN</div>
                        <h2 style="font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 2px 0 0 0;">Checks & Rules Evaluated</h2>
                        <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">Domain: <strong>${escapeHtml(domain || 'Target Site')}</strong> • ${escapeHtml(checksExplanation || '')}</div>
                    </div>
                    <button id="btn-close-checks-modal" style="background: none; border: none; font-size: 24px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;">&times;</button>
                </div>

                <!-- HERO STATS BAR -->
                <div style="padding: 16px 24px; background: rgba(59, 130, 246, 0.04); border-bottom: 1px solid var(--border); display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Analyzed Pages</div>
                        <div style="font-size: 22px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${htmlPagesCount || totalAuditedPages}</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Evaluated Rules</div>
                        <div style="font-size: 22px; font-weight: 800; color: var(--primary); margin-top: 2px;">${evaluatedRulesCount || 14} Rules</div>
                    </div>
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Total Checks Performed</div>
                        <div style="font-size: 22px; font-weight: 800; color: var(--text-primary); margin-top: 2px;">${(totalChecks || 0).toLocaleString()}</div>
                    </div>
                </div>

                <!-- RULES TABLE -->
                <div style="padding: 20px 24px; overflow-y: auto;">
                    <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.5;">
                        Below is the complete inventory of technical audit checks evaluated across your scanned pages:
                    </div>

                    <div style="overflow-x: auto; border: 1px solid var(--border); border-radius: 10px;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 10px 14px;">Check / Rule Category</th>
                                    <th style="padding: 10px 14px;">Rule Scope & Purpose</th>
                                    <th style="padding: 10px 14px;">Pages Checked</th>
                                    <th style="padding: 10px 14px;">Status</th>
                                    <th style="padding: 10px 14px; text-align: right;">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(categoryTable || []).map(c => `
                                    <tr style="border-bottom: 1px solid var(--border);">
                                        <td style="padding: 12px 14px; font-weight: 700; color: var(--text-primary); vertical-align: top;">
                                            ${escapeHtml(c.category)}
                                        </td>
                                        <td style="padding: 12px 14px; color: var(--text-secondary); line-height: 1.4; vertical-align: top; max-width: 320px;">
                                            ${ruleDescriptions[c.category] || 'Technical health and search engine compliance verification.'}
                                        </td>
                                        <td style="padding: 12px 14px; vertical-align: top; font-weight: 600;">
                                            ${c.checks_performed || 0} pages
                                        </td>
                                        <td style="padding: 12px 14px; vertical-align: top;">
                                            <span class="badge ${c.issues_count > 0 ? (c.critical > 0 ? 'badge-critical' : 'badge-warning') : 'badge-success'}" style="font-size: 11px;">
                                                ${c.issues_count > 0 ? `${c.issues_count} Problem${c.issues_count === 1 ? '' : 's'}` : '✓ Passed'}
                                            </span>
                                        </td>
                                        <td style="padding: 12px 14px; text-align: right; vertical-align: top;">
                                            ${c.issues_count > 0 ? `
                                                <button class="btn btn-secondary btn-sm btn-filter-cat-modal" 
                                                        data-category="${escapeHtml(c.category)}"
                                                        style="font-size: 11px; padding: 4px 10px;">
                                                    View Problems (${c.issues_count})
                                                </button>
                                            ` : `
                                                <span style="font-size: 11.5px; color: var(--success); font-weight: 600;">Clean</span>
                                            `}
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- FOOTER -->
                <div style="padding: 16px 24px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: flex-end;">
                    <button id="btn-close-checks-modal-footer" class="btn btn-secondary btn-sm">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modalRoot);

        const closeFn = () => modalRoot.remove();
        const closeBtn = modalRoot.querySelector('#btn-close-checks-modal');
        const closeFooterBtn = modalRoot.querySelector('#btn-close-checks-modal-footer');
        if (closeBtn) closeBtn.onclick = closeFn;
        if (closeFooterBtn) closeFooterBtn.onclick = closeFn;
        modalRoot.onclick = (e) => { if (e.target === modalRoot) closeFn(); };

        // Handle category filter clicks inside modal
        modalRoot.querySelectorAll('.btn-filter-cat-modal').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const cat = e.currentTarget.getAttribute('data-category');
                closeFn();
                if (typeof onSelectCategory === 'function') {
                    onSelectCategory(cat);
                }
            });
        });
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
