/**
 * Audit Evidence Modal Component
 * Renders a clean, responsive modal for inspecting detailed audit evidence,
 * affected URLs, observed values, and rule descriptions with client-side search,
 * severity filtering, and pagination.
 */

export class AuditEvidenceModal {
    static open({ title, ruleId, category, severity, description, recommendation, affectedUrls, evidenceText, provenance }) {
        // Remove any existing audit modal
        const existing = document.getElementById('audit-evidence-modal-root');
        if (existing) existing.remove();

        const urls = Array.isArray(affectedUrls) ? affectedUrls : (affectedUrls ? [affectedUrls] : []);
        const totalCount = urls.length;

        let currentPage = 1;
        const pageSize = 10;
        let searchQuery = '';
        let statusFilter = 'all';

        const modalRoot = document.createElement('div');
        modalRoot.id = 'audit-evidence-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.7);
            backdrop-filter: blur(4px); display: flex; align-items: center;
            justify-content: center; z-index: 9999; padding: 20px;
        `;

        const renderModalContent = () => {
            // Filter URLs
            let filteredUrls = urls.filter(url => {
                const matchesSearch = !searchQuery || url.toLowerCase().includes(searchQuery.toLowerCase());
                return matchesSearch;
            });

            const totalFiltered = filteredUrls.length;
            const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize));
            if (currentPage > totalPages) currentPage = totalPages;

            const startIndex = (currentPage - 1) * pageSize;
            const pageUrls = filteredUrls.slice(startIndex, startIndex + pageSize);

            let sevBadgeStyle = 'background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);';
            const sevLower = (severity || '').toLowerCase();
            if (sevLower === 'warning') sevBadgeStyle = 'background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);';
            else if (sevLower === 'notice') sevBadgeStyle = 'background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3);';

            modalRoot.innerHTML = `
                <div class="card" style="width: 100%; max-width: 820px; max-height: 90vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.35); overflow: hidden;">
                    
                    <!-- MODAL HEADER -->
                    <div style="padding: 20px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                <span class="badge" style="${sevBadgeStyle} font-size: 11px; font-weight: 800; text-transform: uppercase;">
                                    ${(severity || 'HIGH').toUpperCase()}
                                </span>
                                <span class="badge badge-info" style="font-size: 11px;">${category || 'Technical'}</span>
                                ${ruleId ? `<span class="badge" style="background: var(--bg-card); border: 1px solid var(--border); font-size: 10.5px; font-family: monospace; color: var(--text-secondary);">${ruleId}</span>` : ''}
                                <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 10.5px;">Source: ${provenance || 'Crawled Data'}</span>
                            </div>
                            <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">${escapeHtml(title)}</h2>
                            <div style="font-size: 12.5px; color: var(--text-secondary);">${totalCount} affected URL${totalCount === 1 ? '' : 's'} detected in latest crawl snapshot</div>
                        </div>
                        <button id="btn-close-evidence-modal" style="background: none; border: none; font-size: 24px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;">&times;</button>
                    </div>

                    <!-- RULE DETAILS & EXPLANATION -->
                    <div style="padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-card);">
                        ${description ? `<div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.5;"><strong>Why it matters:</strong> ${escapeHtml(description)}</div>` : ''}
                        ${recommendation ? `<div style="font-size: 13px; color: var(--primary); font-weight: 600;"><strong>Recommended Action:</strong> ${escapeHtml(recommendation)}</div>` : ''}
                    </div>

                    <!-- SEARCH & FILTER BAR -->
                    <div style="padding: 12px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
                        <div style="position: relative; flex: 1; min-width: 240px;">
                            <input type="text" id="modal-search-input" value="${escapeHtml(searchQuery)}" placeholder="Search affected URLs..." style="width: 100%; padding: 8px 12px 8px 32px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; background: var(--bg-card); color: var(--text-primary); outline: none;" />
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        </div>
                        <div style="font-size: 12px; color: var(--text-secondary);">
                            Showing <strong>${totalFiltered === 0 ? 0 : startIndex + 1}–${Math.min(startIndex + pageSize, totalFiltered)}</strong> of <strong>${totalFiltered}</strong> URLs
                        </div>
                    </div>

                    <!-- EVIDENCE TABLE -->
                    <div style="flex: 1; overflow-y: auto; padding: 0;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 10px 24px; width: 60%;">Affected Page URL</th>
                                    <th style="padding: 10px 16px;">Status</th>
                                    <th style="padding: 10px 16px;">Observed Finding</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${pageUrls.length > 0 ? pageUrls.map(url => `
                                    <tr style="border-bottom: 1px solid var(--border);">
                                        <td style="padding: 10px 24px; font-family: monospace; font-size: 12px; word-break: break-all;">
                                            <a href="${escapeHtml(url)}" target="_blank" style="color: var(--primary); text-decoration: none; font-weight: 600;">${escapeHtml(url)}</a>
                                        </td>
                                        <td style="padding: 10px 16px;">
                                            <span class="badge" style="${sevBadgeStyle} font-size: 10px;">Failed Check</span>
                                        </td>
                                        <td style="padding: 10px 16px; font-size: 12px; color: var(--text-secondary);">
                                            ${escapeHtml(evidenceText || title || 'Rule violation detected')}
                                        </td>
                                    </tr>
                                `).join('') : `
                                    <tr>
                                        <td colspan="3" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                                            ${searchQuery ? 'No affected URLs match your search query.' : 'No evidence records available for this check.'}
                                        </td>
                                    </tr>
                                `}
                            </tbody>
                        </table>
                    </div>

                    <!-- MODAL FOOTER & PAGINATION -->
                    <div style="padding: 14px 24px; border-top: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center;">
                        <div style="font-size: 12px; color: var(--text-tertiary);">
                            Page ${currentPage} of ${totalPages}
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <button id="modal-btn-prev" class="btn btn-secondary btn-sm" ${currentPage <= 1 ? 'disabled' : ''}>Previous</button>
                            <button id="modal-btn-next" class="btn btn-secondary btn-sm" ${currentPage >= totalPages ? 'disabled' : ''}>Next</button>
                            <button id="modal-btn-close-footer" class="btn btn-primary btn-sm" style="margin-left: 8px;">Close</button>
                        </div>
                    </div>

                </div>
            `;

            // Bind handlers
            modalRoot.querySelector('#btn-close-evidence-modal')?.addEventListener('click', () => modalRoot.remove());
            modalRoot.querySelector('#modal-btn-close-footer')?.addEventListener('click', () => modalRoot.remove());

            const searchInput = modalRoot.querySelector('#modal-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    searchQuery = e.target.value;
                    currentPage = 1;
                    renderModalContent();
                });
            }

            modalRoot.querySelector('#modal-btn-prev')?.addEventListener('click', () => {
                if (currentPage > 1) {
                    currentPage--;
                    renderModalContent();
                }
            });

            modalRoot.querySelector('#modal-btn-next')?.addEventListener('click', () => {
                if (currentPage < totalPages) {
                    currentPage++;
                    renderModalContent();
                }
            });
        };

        renderModalContent();
        document.body.appendChild(modalRoot);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
