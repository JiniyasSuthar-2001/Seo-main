/**
 * Audit Evidence Modal Component
 * Renders the "WHY WE FLAGGED THIS" modal for inspecting detailed audit evidence,
 * affected pages, deterministic recommendations, and an actionable AI Solution implementation assistant.
 * Enforces global 20 rows per page pagination standard and zero fabrication.
 */
import { Pagination } from './Pagination.js';
import { apiClient } from '../services/apiClient.js';
import { projectStore } from '../core/projectStore.js';

export class AuditEvidenceModal {
    static open({ projectId, title, ruleId, category, severity, description, recommendation, affectedUrls, evidenceText, provenance, scanDate }) {
        // Remove any existing audit modal
        const existing = document.getElementById('audit-evidence-modal-root');
        if (existing) existing.remove();

        let targetProjectId = projectId || projectStore.getSelectedProjectId();
        if (!targetProjectId) {
            const match = window.location.pathname.match(/\/projects\/([^\/]+)/);
            if (match) targetProjectId = match[1];
        }
        if (!targetProjectId) {
            targetProjectId = localStorage.getItem('seo_selected_project_id') || localStorage.getItem('active_project_id') || localStorage.getItem('selected_project_id');
        }

        const urls = Array.isArray(affectedUrls) ? affectedUrls : (affectedUrls ? [affectedUrls] : []);
        const totalCount = urls.length;

        let selectedUrl = urls.length > 0 ? urls[0] : '';
        let currentPage = 1;
        const pageSize = 20; // Mandatory Platform Standard: 20 rows per page
        let searchQuery = '';
        
        let aiSolutionState = {
            loading: false,
            error: null,
            solution: null,
            activeUrl: selectedUrl
        };

        let abortController = null;

        const closeModal = () => {
            if (abortController) {
                abortController.abort();
                abortController = null;
            }
            if (document.body.contains(modalRoot)) {
                modalRoot.remove();
            }
        };

        const modalRoot = document.createElement('div');
        modalRoot.id = 'audit-evidence-modal-root';
        modalRoot.style.cssText = `
            position: fixed; inset: 0; background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(6px); display: flex; align-items: center;
            justify-content: center; z-index: 9999; padding: 20px;
        `;

        modalRoot.onclick = (e) => {
            if (e.target === modalRoot) closeModal();
        };

        const onKeyDown = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', onKeyDown);
            }
        };
        document.addEventListener('keydown', onKeyDown);

        const renderModalContent = () => {
            let filteredUrls = urls.filter(url => {
                return !searchQuery || url.toLowerCase().includes(searchQuery.toLowerCase());
            });

            const paginated = Pagination.paginateArray(filteredUrls, currentPage, pageSize);
            currentPage = paginated.currentPage;

            let sevBadgeStyle = 'background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);';
            const sevLower = (severity || '').toLowerCase();
            if (sevLower === 'warning' || sevLower === 'medium') {
                sevBadgeStyle = 'background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3);';
            } else if (sevLower === 'notice' || sevLower === 'low' || sevLower === 'informational') {
                sevBadgeStyle = 'background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3);';
            }

            modalRoot.innerHTML = `
                <div class="card" style="width: 100%; max-width: 1020px; max-height: 92vh; display: flex; flex-direction: column; background: var(--bg-card); border-radius: 16px; border: 1px solid var(--border); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); overflow: hidden;">
                    
                    <!-- MODAL HEADER -->
                    <div style="padding: 18px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                                <span style="font-size: 11px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px;">WHY WE FLAGGED THIS</span>
                                <span class="badge" style="${sevBadgeStyle} font-size: 11px; font-weight: 800; text-transform: uppercase;">
                                    ${escapeHtml((severity || 'HIGH').toUpperCase())}
                                </span>
                                <span class="badge badge-info" style="font-size: 11px;">${escapeHtml(category || 'Website Health')}</span>
                                <span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 10.5px;">Data Source: ${escapeHtml(provenance || 'Website Scan')}</span>
                            </div>
                            <h2 style="font-size: 19px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0;">${escapeHtml(title)}</h2>
                            <div style="font-size: 12.5px; color: var(--text-secondary);">
                                <strong>${totalCount}</strong> affected page${totalCount === 1 ? '' : 's'} detected • Scan Date: ${escapeHtml(scanDate || 'Latest Completed Crawl')}
                            </div>
                        </div>
                        <button id="btn-close-evidence-modal" style="background: none; border: none; font-size: 26px; line-height: 1; color: var(--text-tertiary); cursor: pointer; padding: 4px;" title="Close">&times;</button>
                    </div>

                    <!-- SCROLLABLE BODY -->
                    <div style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0;">
                        
                        <!-- UPPER EXPLANATION BOX (WHY THIS MATTERS & RECOMMENDED ACTION - STATIC) -->
                        <div style="padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-card); font-size: 13px;">
                            ${description ? `
                                <div style="margin-bottom: 8px; color: var(--text-secondary); line-height: 1.5;">
                                    <strong style="color: var(--text-primary);">Why this matters:</strong> ${escapeHtml(description)}
                                </div>
                            ` : ''}
                            ${recommendation ? `
                                <div style="color: var(--primary); font-weight: 600; line-height: 1.4;">
                                    <strong style="color: var(--text-primary);">Recommended Action:</strong> ${escapeHtml(recommendation)}
                                </div>
                            ` : ''}
                        </div>

                        <!-- SEARCH BAR -->
                        <div style="padding: 12px 24px; border-bottom: 1px solid var(--border); background: var(--bg-subtle); display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                                Affected Pages Evidence (${filteredUrls.length})
                            </div>
                            <div style="position: relative; flex: 1; max-width: 320px;">
                                <input type="text" id="modal-search-input" value="${escapeHtml(searchQuery)}" placeholder="Search affected pages..." style="width: 100%; padding: 6px 12px 6px 30px; border: 1px solid var(--border); border-radius: 6px; font-size: 12px; background: var(--bg-card); color: var(--text-primary); outline: none;" />
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-tertiary);"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                            </div>
                        </div>

                        <!-- EVIDENCE TABLE -->
                        <div style="max-height: 240px; overflow-y: auto; border-bottom: 1px solid var(--border);">
                            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px;">
                                <thead>
                                    <tr style="background: var(--bg-subtle); border-bottom: 1px solid var(--border); color: var(--text-secondary); font-size: 11px; text-transform: uppercase;">
                                        <th style="padding: 10px 18px; width: 55%;">Affected Page URL</th>
                                        <th style="padding: 10px 16px; width: 45%;">What We Found</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${paginated.items.length > 0 ? paginated.items.map(url => {
                                        const isSelected = (url === selectedUrl);
                                        return `
                                            <tr class="evidence-row" data-url="${escapeHtml(url)}" style="border-bottom: 1px solid var(--border); cursor: pointer; background: ${isSelected ? 'rgba(79, 70, 229, 0.08)' : 'transparent'};">
                                                <td style="padding: 10px 18px; font-family: monospace; font-size: 12px; word-break: break-all; vertical-align: top;">
                                                    <div style="display: flex; align-items: center; gap: 8px;">
                                                        <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${isSelected ? 'var(--primary)' : 'var(--border)'}; flex-shrink: 0;"></span>
                                                        <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); text-decoration: none; font-weight: ${isSelected ? '700' : '500'};">${escapeHtml(url)}</a>
                                                    </div>
                                                </td>
                                                <td style="padding: 10px 16px; font-size: 12px; color: var(--text-secondary); vertical-align: top;">
                                                    ${escapeHtml(evidenceText || title || 'Issue detected during website scan')}
                                                </td>
                                            </tr>
                                        `;
                                    }).join('') : `
                                        <tr>
                                            <td colspan="2" style="padding: 24px; text-align: center; color: var(--text-secondary);">
                                                ${searchQuery ? 'No matching pages found for your query.' : 'No detailed evidence records available.'}
                                            </td>
                                        </tr>
                                    `}
                                </tbody>
                            </table>
                        </div>

                        <!-- PAGINATION FOOTER (FOR EVIDENCE TABLE) -->
                        <div id="modal-pagination-footer" style="padding: 8px 18px; border-bottom: 1px solid var(--border); background: var(--bg-subtle);"></div>

                        <!-- AI SOLUTION SECTION (ACTIONABLE IMPLEMENTATION ASSISTANT) -->
                        <div id="ai-solution-container" style="padding: 20px 24px; background: var(--bg-card); flex: 1;">
                            ${renderAiSolutionSection()}
                        </div>

                    </div>
                </div>
            `;

            // Append Pagination Controls
            const footerSlot = modalRoot.querySelector('#modal-pagination-footer');
            if (footerSlot && paginated.totalPages > 1) {
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

            // Bind Modal Close
            modalRoot.querySelector('#btn-close-evidence-modal')?.addEventListener('click', () => modalRoot.remove());

            // Bind Row Selection
            modalRoot.querySelectorAll('.evidence-row').forEach(row => {
                row.addEventListener('click', (e) => {
                    if (e.target.tagName.toLowerCase() === 'a') return;
                    selectedUrl = row.getAttribute('data-url');
                    aiSolutionState.activeUrl = selectedUrl;
                    renderModalContent();
                });
            });

            // Bind Search Input
            const searchInput = modalRoot.querySelector('#modal-search-input');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    searchQuery = e.target.value;
                    currentPage = 1;
                    renderModalContent();
                });
            }

            // Bind AI Solution Buttons
            bindAiSolutionEvents();
        };

        const renderAiSolutionSection = () => {
            const currentUrl = selectedUrl || (urls.length > 0 ? urls[0] : '');

            if (aiSolutionState.loading) {
                return `
                    <div style="border: 1px solid rgba(79, 70, 229, 0.3); border-radius: 12px; padding: 28px; background: linear-gradient(135deg, rgba(79, 70, 229, 0.03), rgba(147, 51, 234, 0.03)); text-align: center;">
                        <div class="crawl-spinner" style="width: 28px; height: 28px; border-width: 3px; margin: 0 auto 14px auto; border-color: rgba(79, 70, 229, 0.2); border-top-color: var(--primary);"></div>
                        <div style="font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">Analyzing crawl evidence and preparing an implementation-ready solution…</div>
                        <div style="font-size: 12px; color: var(--text-secondary); max-width: 500px; margin: 0 auto;">Evaluating page markup, character counts, and metadata for <code style="font-family: monospace; color: var(--primary);">${escapeHtml(currentUrl)}</code></div>
                    </div>
                `;
            }

            if (aiSolutionState.error) {
                return `
                    <div style="border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px; padding: 20px 24px; background: rgba(239, 68, 68, 0.04);">
                        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
                            <div>
                                <div style="font-weight: 700; color: #ef4444; font-size: 13.5px; margin-bottom: 4px;">AI solution could not be generated for this issue. Please try again.</div>
                                <div style="font-size: 12px; color: var(--text-secondary);">${escapeHtml(aiSolutionState.error)}</div>
                            </div>
                            <button id="btn-retry-ai-solve" class="btn btn-primary btn-sm" style="font-size: 12px; font-weight: 700; padding: 6px 14px;">
                                🔄 Try Again
                            </button>
                        </div>
                    </div>
                `;
            }

            const sol = aiSolutionState.solution;
            if (!sol) {
                // Initial State: Section with prominent Solve with AI button
                return `
                    <div style="border: 1px solid rgba(79, 70, 229, 0.25); border-radius: 12px; padding: 22px 24px; background: linear-gradient(135deg, rgba(79, 70, 229, 0.04), rgba(147, 51, 234, 0.04));">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 14px;">
                            <div>
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                    <span style="font-size: 15px;">✨</span>
                                    <h3 style="font-size: 14px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px; margin: 0;">AI SOLUTION</h3>
                                    <span class="badge" style="background: rgba(79, 70, 229, 0.12); color: var(--primary); font-size: 10px; font-weight: 700;">ACTIONABLE ASSISTANT</span>
                                </div>
                                <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.45; max-width: 620px;">
                                    Generate an exact, implementation-ready solution grounded in live crawl data. Includes replacement code, character count metrics, and verification steps.
                                </div>
                            </div>
                            <button id="btn-generate-ai-solution" class="btn btn-primary" style="font-size: 13px; font-weight: 700; padding: 8px 18px; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25); border-radius: 8px;">
                                <span>✨</span> Solve with AI
                            </button>
                        </div>

                        ${urls.length > 1 ? `
                            <div style="display: flex; align-items: center; gap: 10px; padding-top: 12px; border-top: 1px solid rgba(79, 70, 229, 0.15); font-size: 12px;">
                                <span style="color: var(--text-secondary); font-weight: 600;">Target Page:</span>
                                <select id="select-ai-target-url" style="padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border); font-size: 11.5px; font-family: monospace; background: var(--bg-card); color: var(--text-primary); max-width: 500px;">
                                    ${urls.map(u => `<option value="${escapeHtml(u)}" ${u === currentUrl ? 'selected' : ''}>${escapeHtml(u)}</option>`).join('')}
                                </select>
                            </div>
                        ` : ''}
                    </div>
                `;
            }

            // Render Generated Actionable Solution
            const whatWrong = sol.what_is_wrong || sol.what_we_found || 'Detected problem during crawl.';
            const whyMatters = sol.why_it_matters || description || 'Affects search ranking signals and user CTR.';
            const whatShouldChange = sol.what_should_change || sol.what_needs_to_change || recommendation || 'Apply recommended replacement.';
            const curVal = sol.current_value || 'Not configured';
            const repVal = sol.recommended_replacement || sol.replacement_value || '';
            const charCount = sol.character_count || (typeof repVal === 'string' ? repVal.length : 0);
            const whereChange = sol.where_to_change || 'Inside the `<head>` section of the affected page HTML.';
            const implCode = sol.implementation || repVal || '';
            const whyBetter = sol.why_this_version_is_better || sol.why_this_fixes_problem || sol.why_this_fix || 'Optimizes keyword relevance and SERP presentation.';
            const verif = sol.verification || 'Re-crawl the page to confirm the updated content is active.';

            return `
                <div style="border: 1px solid rgba(79, 70, 229, 0.35); border-radius: 14px; background: var(--bg-card); box-shadow: 0 8px 24px -4px rgba(79, 70, 229, 0.08); overflow: hidden;">
                    
                    <!-- AI HEADER BAR -->
                    <div style="padding: 14px 20px; background: linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(147, 51, 234, 0.06)); border-bottom: 1px solid rgba(79, 70, 229, 0.2); display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 16px;">✨</span>
                            <span style="font-size: 13px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px;">AI SOLUTION</span>
                            <span class="badge" style="background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 10.5px; font-weight: 700;">
                                ${escapeHtml(sol.source || 'Evidence-Grounded Engine')}
                            </span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            ${urls.length > 1 ? `
                                <select id="select-ai-target-url-solved" style="padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border); font-size: 11px; font-family: monospace; background: var(--bg-card); color: var(--text-primary); max-width: 320px;">
                                    ${urls.map(u => `<option value="${escapeHtml(u)}" ${u === currentUrl ? 'selected' : ''}>${escapeHtml(u)}</option>`).join('')}
                                </select>
                            ` : `
                                <span style="font-size: 11.5px; font-family: monospace; color: var(--text-secondary); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    ${escapeHtml(currentUrl)}
                                </span>
                            `}
                            <button id="btn-regenerate-ai-solution" class="btn btn-secondary btn-sm" style="font-size: 11px; font-weight: 600; padding: 4px 10px; display: inline-flex; align-items: center; gap: 4px;" title="Regenerate Solution">
                                <span>🔄</span> Re-generate
                            </button>
                        </div>
                    </div>

                    <!-- AI CONTENT GRID -->
                    <div style="padding: 18px 20px; display: flex; flex-direction: column; gap: 14px; font-size: 12.5px;">
                        
                        <!-- 1. WHAT IS WRONG -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: #ef4444; text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.3px;">What is wrong</div>
                            <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 10px 14px; color: var(--text-primary); line-height: 1.45;">
                                ${escapeHtml(whatWrong)}
                            </div>
                        </div>

                        <!-- 2. WHY IT MATTERS -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.3px;">Why it matters</div>
                            <div style="color: var(--text-secondary); line-height: 1.45; padding-left: 2px;">
                                ${escapeHtml(whyMatters)}
                            </div>
                        </div>

                        <!-- 3. WHAT SHOULD CHANGE -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--primary); text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.3px;">What needs to change</div>
                            <div style="font-weight: 600; color: var(--text-primary); line-height: 1.45; padding-left: 2px;">
                                ${escapeHtml(whatShouldChange)}
                            </div>
                        </div>

                        <!-- 4. CURRENT VS RECOMMENDED REPLACEMENT -->
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px;">
                            
                            <!-- Current Value -->
                            <div style="border: 1px solid var(--border); border-radius: 8px; padding: 12px; background: var(--bg-subtle);">
                                <div style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 6px;">Current Value</div>
                                <div style="font-family: monospace; font-size: 12px; color: var(--text-primary); word-break: break-all; max-height: 100px; overflow-y: auto;">
                                    ${escapeHtml(curVal)}
                                </div>
                            </div>

                            <!-- Recommended Replacement -->
                            <div style="border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 8px; padding: 12px; background: rgba(16, 185, 129, 0.05);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <span style="font-size: 11px; font-weight: 800; color: #10b981; text-transform: uppercase;">Recommended Replacement</span>
                                    ${charCount > 0 ? `
                                        <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-size: 10.5px; font-weight: 700;">
                                            ${charCount} chars
                                        </span>
                                    ` : ''}
                                </div>
                                <div style="font-family: monospace; font-size: 12px; color: var(--text-primary); word-break: break-all; max-height: 100px; overflow-y: auto; font-weight: 600;">
                                    ${escapeHtml(repVal)}
                                </div>
                            </div>
                        </div>

                        <!-- 5. WHERE TO CHANGE IT -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.3px;">Where to change it</div>
                            <div style="color: var(--text-primary); font-weight: 600; line-height: 1.45;">
                                📍 ${escapeHtml(whereChange)}
                            </div>
                        </div>

                        <!-- 6. IMPLEMENTATION / CODE SNIPPET -->
                        <div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 11px; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 0.3px;">Implementation Code</span>
                                <button id="btn-copy-code-snippet" class="btn btn-secondary btn-sm" style="font-size: 11px; font-weight: 700; padding: 2px 8px; display: inline-flex; align-items: center; gap: 4px;">
                                    📋 Copy Code
                                </button>
                            </div>
                            <div style="position: relative;">
                                <pre style="margin: 0; padding: 12px 14px; background: #0f172a; color: #38bdf8; border-radius: 8px; font-family: monospace; font-size: 12px; line-height: 1.45; overflow-x: auto; white-space: pre-wrap; word-break: break-all; border: 1px solid rgba(56, 189, 248, 0.2);">${escapeHtml(implCode)}</pre>
                            </div>
                        </div>

                        <!-- 7. WHY THIS FIXES THE PROBLEM -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.3px;">Why this version is better</div>
                            <div style="color: var(--text-secondary); line-height: 1.45; padding-left: 2px;">
                                ${escapeHtml(whyBetter)}
                            </div>
                        </div>

                        <!-- 8. VERIFICATION -->
                        <div>
                            <div style="font-size: 11px; font-weight: 800; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px; letter-spacing: 0.3px;">Verification</div>
                            <div style="background: var(--bg-subtle); border-left: 3px solid var(--primary); padding: 8px 12px; border-radius: 0 6px 6px 0; color: var(--text-primary); line-height: 1.45;">
                                🔍 ${escapeHtml(verif)}
                            </div>
                        </div>

                    </div>

                    <!-- AI FOOTER ACTIONS -->
                    <div style="padding: 12px 20px; background: var(--bg-subtle); border-top: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
                        <button id="btn-copy-full-solution" class="btn btn-secondary btn-sm" style="font-size: 12px; font-weight: 700; padding: 6px 14px; display: inline-flex; align-items: center; gap: 5px;">
                            📋 Copy Full Solution
                        </button>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <button id="btn-done-modal" class="btn btn-primary btn-sm" style="font-size: 12px; font-weight: 700; padding: 6px 18px;">
                                Done
                            </button>
                        </div>
                    </div>

                </div>
            `;
        };

        const bindAiSolutionEvents = () => {
            const currentUrl = selectedUrl || (urls.length > 0 ? urls[0] : '');

            // Solve with AI Trigger Button
            modalRoot.querySelector('#btn-generate-ai-solution')?.addEventListener('click', () => {
                executeSolveWithAi(false);
            });

            // Re-generate Button
            modalRoot.querySelector('#btn-regenerate-ai-solution')?.addEventListener('click', () => {
                executeSolveWithAi(true);
            });

            // Retry Button
            modalRoot.querySelector('#btn-retry-ai-solve')?.addEventListener('click', () => {
                executeSolveWithAi(false);
            });

            // Target URL Selectors
            modalRoot.querySelector('#select-ai-target-url')?.addEventListener('change', (e) => {
                selectedUrl = e.target.value;
                aiSolutionState.activeUrl = selectedUrl;
                renderModalContent();
            });

            modalRoot.querySelector('#select-ai-target-url-solved')?.addEventListener('change', (e) => {
                selectedUrl = e.target.value;
                aiSolutionState.activeUrl = selectedUrl;
                executeSolveWithAi(false);
            });

            // Copy Code Snippet
            modalRoot.querySelector('#btn-copy-code-snippet')?.addEventListener('click', (e) => {
                const sol = aiSolutionState.solution;
                const code = sol?.implementation || sol?.recommended_replacement || '';
                navigator.clipboard.writeText(code).then(() => {
                    const btn = e.currentTarget;
                    const origText = btn.innerHTML;
                    btn.innerHTML = '✅ Copied!';
                    setTimeout(() => { btn.innerHTML = origText; }, 2000);
                });
            });

            // Copy Full Solution
            modalRoot.querySelector('#btn-copy-full-solution')?.addEventListener('click', (e) => {
                const sol = aiSolutionState.solution;
                if (!sol) return;
                const fullText = [
                    `SEO PROBLEM: ${title}`,
                    `AFFECTED PAGE: ${sol.affected_url}`,
                    `WHAT IS WRONG: ${sol.what_is_wrong || sol.what_we_found}`,
                    `WHY IT MATTERS: ${sol.why_it_matters || description}`,
                    `WHAT NEEDS TO CHANGE: ${sol.what_should_change}`,
                    `CURRENT VALUE: ${sol.current_value}`,
                    `RECOMMENDED REPLACEMENT: ${sol.recommended_replacement}`,
                    `WHERE TO CHANGE: ${sol.where_to_change}`,
                    `IMPLEMENTATION:\n${sol.implementation}`,
                    `WHY THIS VERSION IS BETTER: ${sol.why_this_version_is_better}`,
                    `VERIFICATION: ${sol.verification}`
                ].join('\n\n');

                navigator.clipboard.writeText(fullText).then(() => {
                    const btn = e.currentTarget;
                    const origText = btn.innerHTML;
                    btn.innerHTML = '✅ Solution Copied!';
                    setTimeout(() => { btn.innerHTML = origText; }, 2000);
                });
            });

            // Close / Done Buttons
            modalRoot.querySelector('#btn-close-evidence-modal')?.addEventListener('click', closeModal);
            modalRoot.querySelector('#btn-done-modal')?.addEventListener('click', closeModal);
        };

        const executeSolveWithAi = async (forceRegenerate = false) => {
            const currentUrl = selectedUrl || (urls.length > 0 ? urls[0] : '');
            aiSolutionState.loading = true;
            aiSolutionState.error = null;
            renderModalContent();

            if (abortController) {
                abortController.abort();
            }
            abortController = new AbortController();

            try {
                const payload = {
                    rule_id: ruleId,
                    title: title,
                    category: category,
                    severity: severity,
                    description: description,
                    recommendation: recommendation,
                    affected_url: currentUrl,
                    evidence_text: evidenceText,
                    force_regenerate: forceRegenerate
                };

                const res = await apiClient.post(`/api/projects/${targetProjectId}/ai/solve`, payload, { signal: abortController.signal });

                if (res && res.solution) {
                    aiSolutionState.solution = res.solution;
                } else {
                    aiSolutionState.error = 'Unable to generate solution from crawl evidence.';
                }
            } catch (err) {
                if (err.name === 'AbortError' || err.message === 'canceled') {
                    return;
                }
                console.error("[AI SOLUTION GENERATION ERROR]", err);
                aiSolutionState.error = err.message || 'AI service execution encountered an error.';
            } finally {
                aiSolutionState.loading = false;
                if (document.body.contains(modalRoot)) {
                    renderModalContent();
                }
            }
        };

        renderModalContent();
        document.body.appendChild(modalRoot);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
