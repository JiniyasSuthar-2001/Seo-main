/**
 * Health Score Detail Modal
 * Shows complete breakdown of website health score, simple explanation,
 * scoring calculation formula, and category impact breakdown.
 */
export class HealthScoreDetailModal {
    static open({ health, summary, totalAuditedPages, htmlPagesCount, blockedPagesCount, evaluatedRulesCount, totalChecks, categoryTable, crawlTimestamp, domain }) {
        const existing = document.getElementById('health-score-modal-root');
        if (existing) existing.remove();

        const score = typeof health === 'number' ? health : 100;
        let scoreColor = '#10b981'; // Green
        let scoreText = 'Good Technical Health';
        let simpleExplanation = 'Search engines can easily crawl, index, and render your website pages. Technical barriers are minimal.';

        if (score < 70) {
            scoreColor = '#ef4444'; // Red
            scoreText = 'Critical Technical Roadblocks';
            simpleExplanation = 'Major technical issues (such as crawl blocks, server errors, or missing metadata) are hindering search engine indexing and visibility.';
        } else if (score < 85) {
            scoreColor = '#f59e0b'; // Yellow/Orange
            scoreText = 'Needs Technical Optimization';
            simpleExplanation = 'Your website is indexable, but several warnings or missing SEO elements (such as H1 tags, canonicals, or alt text) require attention.';
        }

        const critCnt = summary.critical_errors || 0;
        const errCnt = summary.errors || 0;
        const warnCnt = summary.warnings || 0;
        const notCnt = summary.notices || 0;
        const passedChecks = summary.passed_checks || 0;

        const weightedDeductions = (critCnt * 3.0) + (errCnt * 2.0) + (warnCnt * 1.0) + (notCnt * 0.25);

        const modalRoot = document.createElement('div');
        modalRoot.id = 'health-score-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(5px); display: flex; align-items: center;
            justify-content: center; z-index: 9999; padding: 20px;
        `;

        modalRoot.innerHTML = `
            <div class="card" style="width: 100%; max-width: 780px; max-height: 90vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); overflow: hidden;">
                
                <!-- HEADER -->
                <div style="padding: 20px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.05em;">WEBSITE HEALTH SCORE BREAKDOWN</div>
                        <h2 style="font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 2px 0 0 0;">Website Health Evaluation</h2>
                        <div style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">Domain: <strong>${escapeHtml(domain || 'Target Site')}</strong> • Audit Date: ${escapeHtml(crawlTimestamp || 'Recent Scan')}</div>
                    </div>
                    <button id="btn-close-health-modal" style="background: none; border: none; font-size: 24px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;">&times;</button>
                </div>

                <!-- BODY -->
                <div style="padding: 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 20px;">
                    
                    <!-- SCORE & SIMPLE MEANING HERO CARD -->
                    <div style="background: var(--bg-subtle); border-radius: 12px; padding: 20px; border: 1px solid var(--border); display: flex; align-items: center; gap: 24px; flex-wrap: wrap;">
                        <div style="text-align: center; min-width: 120px;">
                            <div style="font-size: 44px; font-weight: 800; color: ${scoreColor}; line-height: 1;">${score}</div>
                            <div style="font-size: 12px; font-weight: 700; color: var(--text-tertiary); margin-top: 4px;">out of 100</div>
                        </div>
                        <div style="flex: 1; min-width: 240px;">
                            <div style="font-size: 16px; font-weight: 700; color: ${scoreColor}; margin-bottom: 4px;">${scoreText}</div>
                            <p style="font-size: 13px; color: var(--text-secondary); margin: 0; line-height: 1.5;">${simpleExplanation}</p>
                        </div>
                    </div>

                    <!-- HOW SCORE WAS CALCULATED (REAL ALGORITHM EXPLANATION) -->
                    <div style="background: rgba(59, 130, 246, 0.04); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 12px; padding: 18px;">
                        <h4 style="font-size: 13.5px; font-weight: 700; color: var(--text-primary); margin: 0 0 8px 0;">How This Score Was Calculated</h4>
                        <p style="font-size: 12.5px; color: var(--text-secondary); margin: 0 0 12px 0; line-height: 1.5;">
                            The health score starts at <strong>100</strong>. Our site audit engine evaluated <strong>${evaluatedRulesCount || 14} core rule categories</strong> across <strong>${htmlPagesCount || totalAuditedPages} analyzed pages</strong> (total of <strong>${(totalChecks || 0).toLocaleString()} individual checks</strong>).
                        </p>

                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; font-size: 12px; margin-top: 10px;">
                            <div style="background: var(--bg-card); padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                                <div style="color: var(--critical); font-weight: 700;">Critical Issues</div>
                                <div style="font-size: 16px; font-weight: 800; margin-top: 2px;">${critCnt} <span style="font-size: 11px; font-weight: 400; color: var(--text-tertiary);">(×3.0 pts)</span></div>
                            </div>
                            <div style="background: var(--bg-card); padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                                <div style="color: var(--warning); font-weight: 700;">Warnings</div>
                                <div style="font-size: 16px; font-weight: 800; margin-top: 2px;">${warnCnt} <span style="font-size: 11px; font-weight: 400; color: var(--text-tertiary);">(×1.0 pt)</span></div>
                            </div>
                            <div style="background: var(--bg-card); padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                                <div style="color: var(--info); font-weight: 700;">Notices</div>
                                <div style="font-size: 16px; font-weight: 800; margin-top: 2px;">${notCnt} <span style="font-size: 11px; font-weight: 400; color: var(--text-tertiary);">(×0.25 pts)</span></div>
                            </div>
                            <div style="background: var(--bg-card); padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                                <div style="color: var(--success); font-weight: 700;">Passed Checks</div>
                                <div style="font-size: 16px; font-weight: 800; margin-top: 2px;">${passedChecks.toLocaleString()}</div>
                            </div>
                        </div>

                        <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-secondary); font-family: monospace;">
                            Formula: 100 - [ (Weighted Penalties: ${weightedDeductions}) / Total Checks: ${totalChecks || 1} * 100 ] = <strong>${score} / 100</strong>
                        </div>
                    </div>

                    <!-- CATEGORIES AFFECTING SCORE TABLE -->
                    <div>
                        <h4 style="font-size: 13.5px; font-weight: 700; color: var(--text-primary); margin: 0 0 10px 0;">Category Audit Summary</h4>
                        <div style="overflow-x: auto; border: 1px solid var(--border); border-radius: 10px;">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 10px 14px;">Category</th>
                                        <th style="padding: 10px 14px;">Status</th>
                                        <th style="padding: 10px 14px;">Checks</th>
                                        <th style="padding: 10px 14px;">Passed</th>
                                        <th style="padding: 10px 14px;">Problems</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${(categoryTable || []).map(cat => {
                                        let badgeClass = 'badge-secondary';
                                        let statusText = 'Not Evaluated';
                                        if (cat.evaluated === false || cat.status === 'Not Evaluated' || cat.status === 'Not Analyzed') {
                                            badgeClass = 'badge-secondary';
                                            statusText = 'Not Evaluated';
                                        } else if (cat.issues_count > 0 || cat.status === 'Issues Found') {
                                            badgeClass = (cat.critical > 0 || cat.error > 0) ? 'badge-critical' : 'badge-warning';
                                            statusText = `${cat.issues_count} Issue${cat.issues_count === 1 ? '' : 's'}`;
                                        } else {
                                            badgeClass = 'badge-success';
                                            statusText = 'Passed';
                                        }

                                        return `
                                            <tr style="border-bottom: 1px solid var(--border);">
                                                <td style="padding: 10px 14px; font-weight: 600;">${escapeHtml(cat.category)}</td>
                                                <td style="padding: 10px 14px;">
                                                    <span class="badge ${badgeClass}" style="font-size: 11px;">
                                                        ${statusText}
                                                    </span>
                                                </td>
                                                <td style="padding: 10px 14px;">${cat.checks_performed || 0}</td>
                                                <td style="padding: 10px 14px; color: ${cat.evaluated ? 'var(--success)' : 'var(--text-tertiary)'}; font-weight: 600;">${cat.passed || 0}</td>
                                                <td style="padding: 10px 14px; color: ${cat.issues_count > 0 ? 'var(--critical)' : 'var(--text-tertiary)'}; font-weight: 600;">${cat.issues_count || 0}</td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- FOOTER -->
                <div style="padding: 16px 24px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: flex-end;">
                    <button id="btn-close-health-modal-footer" class="btn btn-secondary btn-sm">Close</button>
                </div>
            </div>
        `;

        document.body.appendChild(modalRoot);

        const closeBtn = modalRoot.querySelector('#btn-close-health-modal');
        const closeFooterBtn = modalRoot.querySelector('#btn-close-health-modal-footer');
        const closeFn = () => modalRoot.remove();
        if (closeBtn) closeBtn.onclick = closeFn;
        if (closeFooterBtn) closeFooterBtn.onclick = closeFn;
        modalRoot.onclick = (e) => { if (e.target === modalRoot) closeFn(); };
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
