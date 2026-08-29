/**
 * Audit Evidence Modal Component
 * Renders a clean, responsive modal titled "Why We Flagged This" for inspecting detailed
 * audit evidence, affected URLs, observed values, and rule descriptions.
 * Enforces global 20 rows per page pagination standard.
 */
import { Pagination } from './Pagination.js';
import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';

export class AuditEvidenceModal {
    static open({ projectId, title, ruleId, category, severity, description, recommendation, affectedUrls, evidenceText, provenance, scanDate }) {
        // Remove any existing audit modal
        const existing = document.getElementById('audit-evidence-modal-root');
        if (existing) existing.remove();

        const urls = Array.isArray(affectedUrls) ? affectedUrls : (affectedUrls ? [affectedUrls] : []);
        const totalCount = urls.length;

        let currentPage = 1;
        const pageSize = 20; // MANDATORY PLATFORM STANDARD: 20 rows per page
        let searchQuery = '';
        let pageSolutionsMap = {};
        let defaultSolution = null;
        let aiLoading = true;
        let aiUnavailable = false;

        const modalRoot = document.createElement('div');
        modalRoot.id = 'audit-evidence-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.7);
            backdrop-filter: blur(4px); display: flex; align-items: center;
            justify-content: center; z-index: 9999; padding: 20px;
        `;

        const renderModalContent = () => {
            let filteredUrls = urls.filter(url => {
                return !searchQuery || url.toLowerCase().includes(searchQuery.toLowerCase());
            });

            const paginated = Pagination.paginateArray(filteredUrls, currentPage, pageSize);
            currentPage = paginated.currentPage;

            let sevBadgeStyle = 'background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);';
            const sevLower = (severity || '').toLowerCase();
            if (sevLower === 'warning') sevBadgeStyle = 'background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);';
            else if (sevLower === 'notice') sevBadgeStyle = 'background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3);';

            modalRoot.innerHTML = `
                <div class="card" style="width: 100%; max-width: 960px; max-height: 90vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.35); overflow: hidden;">
                    
                    <!-- MODAL HEADER -->
                    <div style="padding: 20px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                <span style="font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase;">WHY WE FLAGGED THIS</span>
                                <span class="badge" style="${sevBadgeStyle} font-size: 11px; font-weight: 800; text-transform: uppercase;">
                                    ${(severity || 'HIGH').toUpperCase()}
                                </span>
                                <span class="badge badge-info" style="font-size: 11px;">${escapeHtml(category || 'Website Check')}</span>
                                <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 10.5px;">Data Source: ${escapeHtml(provenance || 'Website Scan')}</span>
                            </div>
                            <h2 style="font-size: 18px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">${escapeHtml(title)}</h2>
                            <div style="font-size: 12.5px; color: var(--text-secondary);">${totalCount} affected page${totalCount === 1 ? '' : 's'} detected • Scan Date: ${escapeHtml(scanDate || '26 Aug 2026')}</div>
                        </div>
                        <button id="btn-close-evidence-modal" style="background: none; border: none; font-size: 24px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;">&times;</button>
                    </div>

                    <!-- EXPLANATION BOX -->
                    <div style="padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-card); font-size: 13px;">
                        ${description ? `<div style="margin-bottom: 8px; color: var(--text-secondary); line-height: 1.5;"><strong style="color: var(--text-primary);">Why this matters:</strong> ${escapeHtml(description)}</div>` : ''}
                        ${recommendation ? `<div style="color: var(--primary); font-weight: 600;"><strong style="color: var(--text-primary);">Recommended Action:</strong> ${escapeHtml(recommendation)}</div>` : ''}
                    </div>

                    <!-- SEARCH BAR -->
                    <div style="padding: 12px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
                        <div style="position: relative; flex: 1; min-width: 240px;">
                            <input type="text" id="modal-search-input" value="${escapeHtml(searchQuery)}" placeholder="Search affected pages..." style="width: 100%; padding: 8px 12px 8px 32px; border: 1px solid var(--border); border-radius: 8px; font-size: 13px; background: var(--bg-card); color: var(--text-primary); outline: none;" />
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        </div>
                    </div>

                    <!-- EVIDENCE TABLE WITH AI SOLUTION COLUMN -->
                    <div style="flex: 1; overflow-y: auto; padding: 0;">
                        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                            <thead>
                                <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                    <th style="padding: 12px 18px; width: 36%;">Affected Page URL</th>
                                    <th style="padding: 12px 16px; width: 28%;">What We Found</th>
                                    <th style="padding: 12px 18px; width: 36%;">AI Solution</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${paginated.items.length > 0 ? paginated.items.map(url => {
                                    const pageSol = pageSolutionsMap[url] || defaultSolution;
                                    let aiSolCell = '';
                                    if (pageSol) {
                                        aiSolCell = `<span style="color: var(--text-primary); line-height: 1.45;">${escapeHtml(pageSol)}</span>`;
                                    } else if (aiLoading) {
                                        aiSolCell = `<span style="color: var(--text-tertiary); font-size: 11.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="crawl-spinner" style="width: 10px; height: 10px; border-width: 1.5px;"></span> Analyzing page...</span>`;
                                    } else {
                                        aiSolCell = `<span style="color: var(--text-tertiary); font-size: 11.5px;">AI solution temporarily unavailable.</span>`;
                                    }

                                    return `
                                        <tr style="border-bottom: 1px solid var(--border);">
                                            <td style="padding: 12px 18px; font-family: monospace; font-size: 12px; word-break: break-all; vertical-align: top;">
                                                <a href="${escapeHtml(url)}" target="_blank" style="color: var(--primary); text-decoration: none; font-weight: 600;">${escapeHtml(url)}</a>
                                            </td>
                                            <td style="padding: 12px 16px; font-size: 12px; color: var(--text-secondary); vertical-align: top;">
                                                ${escapeHtml(evidenceText || title || 'Issue detected during website scan')}
                                            </td>
                                            <td style="padding: 12px 18px; font-size: 12px; vertical-align: top;">
                                                ${aiSolCell}
                                            </td>
                                        </tr>
                                    `;
                                }).join('') : `
                                    <tr>
                                        <td colspan="3" style="padding: 32px; text-align: center; color: var(--text-secondary);">
                                            ${searchQuery ? 'No matching pages found for your query.' : 'No detailed evidence records available.'}
                                        </td>
                                    </tr>
                                `}
                            </tbody>
                        </table>
                    </div>

                    <!-- FOOTER WITH GLOBAL PAGINATION CONTROLS -->
                    <div id="modal-pagination-footer"></div>

                </div>
            `;

            // Append Pagination Controls
            const footerSlot = modalRoot.querySelector('#modal-pagination-footer');
            if (footerSlot) {
                const pag = new Pagination({
                    totalItems: paginated.totalItems,
                    currentPage: paginated.currentPage,
                    pageSize: pageSize,
                    onPageChange: (newPage) => {
                        currentPage = newPage;
                        renderModalContent();
                    }
                });
                footerSlot.appendChild(pag.render());
            }

            // Bind handlers
            modalRoot.querySelector('#btn-close-evidence-modal')?.addEventListener('click', () => modalRoot.remove());

            const searchInput = modalRoot.querySelector('#modal-search-input');
            if (searchInput) {
                searchInput.focus();
                searchInput.setSelectionRange(searchQuery.length, searchQuery.length);
                searchInput.addEventListener('input', (e) => {
                    searchQuery = e.target.value;
                    currentPage = 1;
                    renderModalContent();
                });
            }
        };

        renderModalContent();
        document.body.appendChild(modalRoot);

        const fetchAiSolution = async () => {
            try {
                let targetProjectId = projectId;
                if (!targetProjectId) {
                    targetProjectId = projectStore.getSelectedProjectId();
                }
                if (!targetProjectId) {
                    const match = window.location.pathname.match(/\/projects\/([^\/]+)/);
                    if (match) targetProjectId = match[1];
                }
                if (!targetProjectId) {
                    targetProjectId = localStorage.getItem('seo_selected_project_id') || localStorage.getItem('active_project_id') || localStorage.getItem('selected_project_id');
                }
                if (!targetProjectId) {
                    aiLoading = false;
                    aiUnavailable = true;
                    renderModalContent();
                    return;
                }

                const payload = {
                    rule_id: ruleId,
                    title: title,
                    category: category,
                    severity: severity,
                    description: description,
                    recommendation: recommendation,
                    affected_urls: urls,
                    evidence_text: evidenceText
                };

                const res = await apiClient.post(`/api/projects/${targetProjectId}/ai/problem-solution`, payload);

                if (res?.status === 'no_provider' || res?.code === 'NO_PROVIDER_CONFIGURED') {
                    aiLoading = false;
                    aiUnavailable = true;
                    renderModalContent();
                    return;
                }

                pageSolutionsMap = res?.page_solutions || {};
                defaultSolution = res?.default_solution || null;
                aiLoading = false;
                renderModalContent();
            } catch (err) {
                console.warn("[AI SOLUTION FETCH NOTICE]", err);
                aiLoading = false;
                aiUnavailable = true;
                renderModalContent();
            }
        };

        fetchAiSolution();
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
